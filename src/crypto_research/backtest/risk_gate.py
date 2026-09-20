"""
Risk gate — pre-entry portfolio and risk limit checks.

Every check returns a tuple of (approved: bool, reason: RejectionReason | None).
A rejection is NEVER silent: all rejections are logged and recorded in the
execution event ledger.

Checks performed before opening any position:
    1. Max concurrent positions
    2. Max total exposure (portfolio level)
    3. Max asset exposure (per symbol)
    4. Daily profit target
    5. Daily loss limit
    6. Available capital
    7. Short not allowed (Spot / Prompt 03)

Design:
    - All checks are pure functions of current state and config.
    - No side effects. Callers record the result.
    - Order of checks: limits checked before capital, stops before adds.
"""

from __future__ import annotations

from typing import Optional

from crypto_research.core.domain import PortfolioState, PositionSide, RejectionReason
from crypto_research.utils.logging import get_logger

logger = get_logger(__name__)


class RiskGate:
    """
    Pre-entry risk gate for the backtest engine.

    Instantiated once per backtest run with the risk configuration.

    Usage:
        gate = RiskGate(config.risk, allow_short=False)
        approved, reason = gate.check_all(
            side=PositionSide.LONG,
            portfolio_state=state,
            symbol="BTCUSDT",
            entry_price=50000,
            quantity=0.01,
        )
    """

    def __init__(self, risk_cfg, allow_short: bool = False) -> None:
        """
        Args:
            risk_cfg:    RiskConfig from project configuration.
            allow_short: Whether short positions are permitted.
                         Default False (Spot / Prompt 03 restriction).
        """
        self._cfg = risk_cfg
        self._allow_short = allow_short

    def check_all(
        self,
        side: PositionSide,
        portfolio_state: PortfolioState,
        symbol: str,
        entry_price: float,
        quantity: float,
        open_position_count: int,
        asset_notional: float,
    ) -> tuple[bool, Optional[RejectionReason]]:
        """
        Run all pre-entry checks in priority order.

        Args:
            side:                 Proposed position side (LONG or SHORT).
            portfolio_state:      Current portfolio accounting snapshot.
            symbol:               Asset symbol for the proposed position.
            entry_price:          Anticipated entry price.
            quantity:             Proposed position quantity.
            open_position_count:  Number of currently open positions.
            asset_notional:       Current notional exposure in this symbol.

        Returns:
            (True, None)              — approved.
            (False, RejectionReason)  — rejected with explicit reason.
        """
        new_notional = entry_price * quantity

        # 1. Short not allowed
        approved, reason = self.check_short_allowed(side)
        if not approved:
            return False, reason

        # 2. Daily loss limit
        approved, reason = self.check_daily_loss_limit(
            daily_pnl=portfolio_state.daily_pnl,
            equity=portfolio_state.equity,
        )
        if not approved:
            return False, reason

        # 3. Daily profit target
        approved, reason = self.check_daily_profit_target(
            daily_pnl=portfolio_state.daily_pnl,
            equity=portfolio_state.equity,
        )
        if not approved:
            return False, reason

        # 4. Max concurrent positions
        approved, reason = self.check_max_concurrent_positions(open_position_count)
        if not approved:
            return False, reason

        # 5. Max total exposure
        approved, reason = self.check_max_total_exposure(
            current_gross_exposure=portfolio_state.gross_exposure,
            new_notional=new_notional,
            equity=portfolio_state.equity,
        )
        if not approved:
            return False, reason

        # 6. Max asset exposure
        approved, reason = self.check_max_asset_exposure(
            current_asset_notional=asset_notional,
            new_notional=new_notional,
            equity=portfolio_state.equity,
        )
        if not approved:
            return False, reason

        # 7. Available capital
        approved, reason = self.check_available_capital(
            available_capital=portfolio_state.available_capital,
            required_capital=new_notional,
        )
        if not approved:
            return False, reason

        return True, None

    def check_short_allowed(
        self, side: PositionSide
    ) -> tuple[bool, Optional[RejectionReason]]:
        """Reject short positions if not permitted (Spot / Prompt 03)."""
        if side == PositionSide.SHORT and not self._allow_short:
            logger.info(
                "Order rejected: short not allowed",
                side=side.value,
            )
            return False, RejectionReason.SHORT_NOT_ALLOWED
        return True, None

    def check_max_concurrent_positions(
        self, open_position_count: int
    ) -> tuple[bool, Optional[RejectionReason]]:
        """Reject if opening another position would exceed the configured limit."""
        limit = self._cfg.max_concurrent_positions
        if open_position_count >= limit:
            logger.info(
                "Order rejected: max concurrent positions",
                open=open_position_count,
                limit=limit,
            )
            return False, RejectionReason.MAX_CONCURRENT_POSITIONS
        return True, None

    def check_max_total_exposure(
        self,
        current_gross_exposure: float,
        new_notional: float,
        equity: float,
    ) -> tuple[bool, Optional[RejectionReason]]:
        """
        Reject if total exposure after entry would exceed the configured limit.

        Exposure definition:
            exposure_pct = (gross_exposure + new_notional) / equity × 100
        """
        if equity <= 0:
            return False, RejectionReason.INSUFFICIENT_CAPITAL

        projected_exposure_pct = (current_gross_exposure + new_notional) / equity * 100.0
        limit = self._cfg.max_total_exposure_pct

        if projected_exposure_pct > limit:
            logger.info(
                "Order rejected: max total exposure",
                projected_pct=round(projected_exposure_pct, 2),
                limit_pct=limit,
            )
            return False, RejectionReason.MAX_TOTAL_EXPOSURE
        return True, None

    def check_max_asset_exposure(
        self,
        current_asset_notional: float,
        new_notional: float,
        equity: float,
    ) -> tuple[bool, Optional[RejectionReason]]:
        """
        Reject if per-symbol exposure after entry would exceed the configured limit.

        Exposure definition:
            asset_exposure_pct = (current_asset_notional + new_notional) / equity × 100
        """
        if equity <= 0:
            return False, RejectionReason.INSUFFICIENT_CAPITAL

        projected_pct = (current_asset_notional + new_notional) / equity * 100.0
        limit = self._cfg.max_asset_exposure_pct

        if projected_pct > limit:
            logger.info(
                "Order rejected: max asset exposure",
                projected_pct=round(projected_pct, 2),
                limit_pct=limit,
            )
            return False, RejectionReason.MAX_ASSET_EXPOSURE
        return True, None

    def check_daily_profit_target(
        self, daily_pnl: float, equity: float
    ) -> tuple[bool, Optional[RejectionReason]]:
        """
        Stop opening new positions if daily profit target has been reached.

        Condition: daily_pnl / equity_at_day_start >= daily_profit_target_pct / 100
        We use current equity as a proxy for day-start equity (conservative).

        Existing positions are NOT closed — they follow their management rules.
        """
        if equity <= 0:
            return True, None  # Let capital check handle this

        target_pct = self._cfg.daily_profit_target_pct
        if target_pct is None:
            return True, None

        daily_return_pct = daily_pnl / equity * 100.0
        if daily_return_pct >= target_pct:
            logger.info(
                "Order rejected: daily profit target reached",
                daily_pnl=round(daily_pnl, 4),
                daily_return_pct=round(daily_return_pct, 4),
                target_pct=target_pct,
            )
            return False, RejectionReason.DAILY_PROFIT_TARGET_REACHED
        return True, None

    def check_daily_loss_limit(
        self, daily_pnl: float, equity: float
    ) -> tuple[bool, Optional[RejectionReason]]:
        """
        Stop opening new positions if daily loss limit has been exceeded.

        daily_pnl is negative when a loss has occurred.
        Condition: daily_pnl / equity <= -daily_loss_limit_pct / 100

        Existing positions are NOT closed — they follow their management rules.
        """
        if equity <= 0:
            return False, RejectionReason.INSUFFICIENT_CAPITAL

        limit_pct = self._cfg.daily_loss_limit_pct
        daily_return_pct = daily_pnl / equity * 100.0

        if daily_return_pct <= -limit_pct:
            logger.info(
                "Order rejected: daily loss limit reached",
                daily_pnl=round(daily_pnl, 4),
                daily_return_pct=round(daily_return_pct, 4),
                limit_pct=limit_pct,
            )
            return False, RejectionReason.DAILY_LOSS_LIMIT_REACHED
        return True, None

    def check_available_capital(
        self, available_capital: float, required_capital: float
    ) -> tuple[bool, Optional[RejectionReason]]:
        """Reject if the required capital for this trade exceeds available capital."""
        if required_capital > available_capital:
            logger.info(
                "Order rejected: insufficient capital",
                required=round(required_capital, 4),
                available=round(available_capital, 4),
            )
            return False, RejectionReason.INSUFFICIENT_CAPITAL
        return True, None
