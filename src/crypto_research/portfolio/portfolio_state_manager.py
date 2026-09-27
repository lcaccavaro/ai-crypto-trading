"""
Portfolio State Manager.

Wraps PortfolioAccountant with Prompt 05 portfolio tracking features:
- Tracks UTC daily reset for daily_start_equity and daily_limit_state.
- Tracks asset_exposures (per symbol notional).
- Tracks strategy_exposures (per strategy_id notional).
"""

from __future__ import annotations

from datetime import datetime, timezone

from crypto_research.backtest.portfolio_accountant import PortfolioAccountant
from crypto_research.config.schema import RiskConfig
from crypto_research.core.domain import DailyLimitState, PortfolioState, Position, Trade
from crypto_research.utils.logging import get_logger

logger = get_logger(__name__)


class PortfolioStateManager:
    """
    Maintains the extended PortfolioState for orchestration.
    """

    def __init__(self, accountant: PortfolioAccountant, risk_config: RiskConfig):
        self._accountant = accountant
        self._cfg = risk_config
        
        self._current_utc_date = None
        self._daily_start_equity = accountant.get_portfolio_state(datetime.now(timezone.utc)).equity
        self._daily_limit_state = DailyLimitState.OPEN
        
        self._asset_exposures: dict[str, float] = {}
        self._strategy_exposures: dict[str, float] = {}

    def update_from_positions(self, timestamp: datetime, open_positions: list[Position]) -> PortfolioState:
        """
        Updates exposures from current open positions and handles daily boundaries.
        Returns the new extended PortfolioState.
        """
        # 1. Handle UTC daily boundary
        # If timestamp crosses UTC midnight, reset daily state
        utc_date = timestamp.date()
        if self._current_utc_date is None:
            self._current_utc_date = utc_date
            # Base equity is already set from init

        if utc_date > self._current_utc_date:
            logger.info("UTC Midnight boundary crossed", date=utc_date.isoformat())
            self._current_utc_date = utc_date
            
            # The base accountant must also reset its daily PnL
            # (Accountant should have a method for this, or we just rely on its daily_pnl calculation)
            # Accountant handles daily_pnl based on UTC day internally if implemented,
            # or we proxy it here. Assuming accountant.daily_pnl works or we just use current equity.
            
            base_state = self._accountant.get_portfolio_state(timestamp)
            self._daily_start_equity = base_state.equity
            self._daily_limit_state = DailyLimitState.OPEN
            logger.info("Daily limits reset", start_equity=self._daily_start_equity)

        # 2. Recalculate exposures
        self._asset_exposures.clear()
        self._strategy_exposures.clear()
        
        for pos in open_positions:
            notional = pos.notional
            self._asset_exposures[pos.asset] = self._asset_exposures.get(pos.asset, 0.0) + notional
            self._strategy_exposures[pos.strategy_name] = self._strategy_exposures.get(pos.strategy_name, 0.0) + notional

        # 3. Retrieve base state
        base_state = self._accountant.get_portfolio_state(timestamp)
        
        # 4. Check if daily limits were hit
        if self._daily_limit_state == DailyLimitState.OPEN and base_state.equity > 0:
            # We use daily_pnl from accountant if available, or compute from _daily_start_equity
            # If accountant doesn't have daily_pnl, we compute it.
            daily_pnl = base_state.equity - self._daily_start_equity
            daily_ret_pct = (daily_pnl / self._daily_start_equity) * 100.0
            
            if daily_ret_pct >= self._cfg.daily_profit_target_pct:
                self._daily_limit_state = DailyLimitState.PROFIT_TARGET_REACHED
                logger.info("Daily profit target reached", daily_ret=round(daily_ret_pct, 2))
            elif daily_ret_pct <= -self._cfg.daily_loss_limit_pct:
                self._daily_limit_state = DailyLimitState.LOSS_LIMIT_REACHED
                logger.info("Daily loss limit reached", daily_ret=round(daily_ret_pct, 2))

        # 5. Return extended state
        # Create a new PortfolioState matching the base but with extended fields
        # Note: In Python 3.10+, dataclasses.replace could be used, but since PortfolioState 
        # is just a mutable dataclass, we can modify the instance or create a copy.
        
        base_state.daily_start_equity = self._daily_start_equity
        base_state.daily_limit_state = self._daily_limit_state.value
        base_state.asset_exposures = dict(self._asset_exposures)
        base_state.strategy_exposures = dict(self._strategy_exposures)
        
        # Override daily_pnl to ensure it matches our start equity calculation
        base_state.daily_pnl = base_state.equity - self._daily_start_equity
        
        return base_state

    def get_asset_exposure(self, asset: str) -> float:
        return self._asset_exposures.get(asset, 0.0)

    def get_strategy_exposure(self, strategy_id: str) -> float:
        return self._strategy_exposures.get(strategy_id, 0.0)
