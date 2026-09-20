"""
Execution simulator — candle-level fill simulation.

Simulates order fills from OHLC candle data. All methods are stateless
pure functions operating on candle data + configuration.

Signal timing:
━━━━━━━━━━━━━

    Default behavior (allow_same_close_execution = False):
        A signal generated from candle C's CLOSE cannot execute at C's close.
        The engine marks the signal and executes it at C+1's OPEN.

    This prevents look-ahead bias at OHLC resolution because:
        - The close price is the LAST price in the candle period.
        - Executing at that price assumes perfect market timing.
        - In practice, a trader sees the close and submits an order for the
          next period's open.

Intrabar ambiguity:
━━━━━━━━━━━━━━━━━━

    When a candle has: High >= target AND Low <= stop
    OHLC data cannot tell us which was reached first.
    Three configurable policies:
        STOP_FIRST       — assume stop hit first (conservative)
        TARGET_FIRST     — assume target hit first (optimistic)
        REJECT_AMBIGUOUS — record neither, skip

    CRITICAL: None of these is factually correct at OHLC resolution.
    Research output must document the configured policy explicitly.

Gap handling:
━━━━━━━━━━━━

    Scenario: stop = 100, previous candle close = 102, next candle open = 97.
    The market "gapped" through the stop. Filling at 100 is unrealistic
    because the market never traded at that price during normal hours.

    FILL_AT_OPEN: Fill at candle open (97). Realistic.
    FILL_AT_LEVEL: Fill at stop level (100). Unrealistic — not used by default.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from crypto_research.backtest.cost_model import CostModel
from crypto_research.core.domain import (
    ExitReason,
    Fill,
    GapPolicy,
    IntrabarFillPolicy,
    OrderSide,
    Position,
    PositionSide,
)
from crypto_research.utils.logging import get_logger

logger = get_logger(__name__)


class ExecutionSimulator:
    """
    Stateless candle-level fill simulator.

    All methods are pure: given a candle and a position/order, they return
    the fill (or None if the level was not reached).
    """

    def __init__(
        self,
        cost_model: CostModel,
        intrabar_policy: IntrabarFillPolicy = IntrabarFillPolicy.STOP_FIRST,
        gap_policy: GapPolicy = GapPolicy.FILL_AT_OPEN,
    ) -> None:
        self._cost_model = cost_model
        self._intrabar_policy = intrabar_policy
        self._gap_policy = gap_policy

    # ------------------------------------------------------------------
    # Entry fills
    # ------------------------------------------------------------------

    def simulate_market_entry(
        self,
        order_id: str,
        timestamp: datetime,
        symbol: str,
        side: PositionSide,
        quantity: float,
        candle_open: float,
    ) -> Fill:
        """
        Simulate a market entry fill at the candle open.

        Market entries execute at the next candle's OPEN (signal timing rule).
        Costs: execution_price = candle_open + slippage + half-spread (BUY)
                                = candle_open - slippage - half-spread (SELL)

        Args:
            order_id:     Order to fill.
            timestamp:    Simulation timestamp of the fill.
            symbol:       Asset symbol.
            side:         Position side (LONG → BUY, SHORT → SELL).
            quantity:     Position size.
            candle_open:  Open price of the execution candle.

        Returns:
            Fill with calculated execution price and costs.
        """
        order_side = OrderSide.BUY if side == PositionSide.LONG else OrderSide.SELL
        exec_price, fee, slippage, spread = self._cost_model.compute_entry_costs(
            mid_price=candle_open,
            quantity=quantity,
            side=order_side,
            is_maker=False,  # Market orders are taker
        )

        fill = Fill.create(
            order_id=order_id,
            timestamp=timestamp,
            asset=symbol,
            side=order_side,
            fill_price=exec_price,
            quantity=quantity,
            fees=fee,
            slippage=slippage,
            spread_cost=spread,
        )
        logger.debug(
            "Entry fill simulated",
            symbol=symbol,
            side=order_side.value,
            candle_open=candle_open,
            exec_price=round(exec_price, 6),
            quantity=quantity,
            fee=round(fee, 6),
        )
        return fill

    # ------------------------------------------------------------------
    # Exit fills — stop and target management
    # ------------------------------------------------------------------

    def check_and_simulate_exits(
        self,
        position: Position,
        candle_open: float,
        candle_high: float,
        candle_low: float,
        candle_close: float,
        candle_timestamp: datetime,
        run_id: str,
    ) -> tuple[Fill | None, ExitReason | None]:
        """
        Check whether a stop or target was triggered on this candle.

        Returns the exit fill and reason, or (None, None) if no exit occurred.

        Logic:
            1. Gap check — did candle open beyond stop or target?
            2. Intrabar check — did stop or target get touched during candle?
            3. Ambiguity check — both touched (apply configured policy)?

        Args:
            position:         Open position to evaluate.
            candle_open/high/low/close: OHLC values for the current candle.
            candle_timestamp: Open timestamp of the current candle.
            run_id:           Run ID for the fill.

        Returns:
            (Fill, ExitReason) if exit triggered, else (None, None).
        """
        if position.stop_price is None and position.target_price is None:
            return None, None

        stop = position.stop_price
        target = position.target_price
        is_long = position.side == PositionSide.LONG

        # --- Gap check: candle opened through stop or target ---
        if stop is not None and self._is_gap_through_stop(candle_open, stop, is_long):
            fill_price = self._gap_fill_price(candle_open, stop)
            return self._create_exit_fill(
                position, fill_price, candle_timestamp, ExitReason.STOP
            ), ExitReason.STOP

        if target is not None and self._is_gap_through_target(candle_open, target, is_long):
            fill_price = self._gap_fill_price(candle_open, target)
            return self._create_exit_fill(
                position, fill_price, candle_timestamp, ExitReason.TARGET
            ), ExitReason.TARGET

        # --- Intrabar check ---
        stop_touched = stop is not None and self._stop_touched(
            candle_high, candle_low, stop, is_long
        )
        target_touched = target is not None and self._target_touched(
            candle_high, candle_low, target, is_long
        )

        if stop_touched and target_touched:
            # Ambiguous candle — both levels touched
            return self._handle_ambiguity(position, stop, target, candle_timestamp)

        if stop_touched:
            return self._create_exit_fill(
                position, stop, candle_timestamp, ExitReason.STOP
            ), ExitReason.STOP

        if target_touched:
            return self._create_exit_fill(
                position, target, candle_timestamp, ExitReason.TARGET
            ), ExitReason.TARGET

        return None, None

    def _is_gap_through_stop(self, open_price: float, stop: float, is_long: bool) -> bool:
        """True if candle opened beyond the stop level (unfavorable gap)."""
        if is_long:
            return open_price <= stop  # Gapped down through stop
        else:
            return open_price >= stop  # Gapped up through stop

    def _is_gap_through_target(
        self, open_price: float, target: float, is_long: bool
    ) -> bool:
        """True if candle opened beyond the target level (favorable gap)."""
        if is_long:
            return open_price >= target  # Gapped up through target
        else:
            return open_price <= target  # Gapped down through target

    def _gap_fill_price(self, open_price: float, level: float) -> float:
        """
        Return the actual fill price given a gap.

        FILL_AT_OPEN: Fill at candle open (realistic).
        FILL_AT_LEVEL: Fill at the stop/target level (unrealistic).
        """
        if self._gap_policy == GapPolicy.FILL_AT_OPEN:
            return open_price
        else:
            return level

    def _stop_touched(
        self, high: float, low: float, stop: float, is_long: bool
    ) -> bool:
        """True if the stop level was touched within the candle."""
        if is_long:
            return low <= stop
        else:
            return high >= stop

    def _target_touched(
        self, high: float, low: float, target: float, is_long: bool
    ) -> bool:
        """True if the target level was touched within the candle."""
        if is_long:
            return high >= target
        else:
            return low <= target

    def _handle_ambiguity(
        self,
        position: Position,
        stop: float,
        target: float,
        timestamp: datetime,
    ) -> tuple[Fill | None, ExitReason | None]:
        """
        Handle the case where both stop and target were touched in the same candle.

        This is OHLC intrabar ambiguity — we cannot know from OHLC data alone
        which was reached first. The configured policy determines behavior.
        """
        policy = self._intrabar_policy

        if policy == IntrabarFillPolicy.STOP_FIRST:
            logger.debug(
                "Intrabar ambiguity: applying stop_first policy",
                symbol=position.asset,
                stop=stop,
                target=target,
            )
            return self._create_exit_fill(
                position, stop, timestamp, ExitReason.STOP
            ), ExitReason.STOP

        elif policy == IntrabarFillPolicy.TARGET_FIRST:
            logger.debug(
                "Intrabar ambiguity: applying target_first policy",
                symbol=position.asset,
                stop=stop,
                target=target,
            )
            return self._create_exit_fill(
                position, target, timestamp, ExitReason.TARGET
            ), ExitReason.TARGET

        else:  # REJECT_AMBIGUOUS
            logger.info(
                "Intrabar ambiguity: rejecting ambiguous candle (no exit recorded)",
                symbol=position.asset,
                stop=stop,
                target=target,
            )
            return None, None

    def _create_exit_fill(
        self,
        position: Position,
        exit_level: float,
        timestamp: datetime,
        reason: ExitReason,
    ) -> Fill:
        """
        Create an exit fill at the given price level.

        Exit side: LONG position exits with SELL; SHORT exits with BUY.
        Costs applied: slippage + half-spread + fee (taker, market order).
        """
        exit_side = (
            OrderSide.SELL if position.side == PositionSide.LONG else OrderSide.BUY
        )
        exec_price, fee, slippage, spread = self._cost_model.compute_entry_costs(
            mid_price=exit_level,
            quantity=position.quantity,
            side=exit_side,
            is_maker=False,
        )

        fill = Fill.create(
            order_id=str(uuid.uuid4()),  # Exit order auto-ID
            timestamp=timestamp,
            asset=position.asset,
            side=exit_side,
            fill_price=exec_price,
            quantity=position.quantity,
            fees=fee,
            slippage=slippage,
            spread_cost=spread,
        )
        logger.debug(
            "Exit fill simulated",
            symbol=position.asset,
            reason=reason.value,
            exit_level=exit_level,
            exec_price=round(exec_price, 6),
            fee=round(fee, 6),
        )
        return fill
