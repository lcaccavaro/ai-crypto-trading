"""
Strategy State Machine.

Tracks the lifecycle of a strategy instance (ACTIVE, PAUSED, DISABLED)
and manages consecutive loss limits and cooldown periods.

Point-In-Time (PIT) Guarantee:
- State updates only occur when a trade is closed.
- `update_from_trade()` processes the trade outcome based on the trade's exit timestamp.
- `check_cooldown()` checks if a cooldown has expired relative to the current simulation time.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from crypto_research.config.schema import StrategyManagementConfig
from crypto_research.core.domain import StrategyLifecycleState, StrategyState, Trade
from crypto_research.utils.logging import get_logger

logger = get_logger(__name__)


class StrategyStateMachine:
    """
    Manages the lifecycle state of a single strategy instance.
    """

    def __init__(
        self,
        strategy_id: str,
        instance_id: str,
        config: StrategyManagementConfig,
        initial_state: StrategyLifecycleState = StrategyLifecycleState.ACTIVE,
    ) -> None:
        self.strategy_id = strategy_id
        self.instance_id = instance_id
        self._config = config
        
        self._state = initial_state
        self._reason = "INITIALIZED"
        self._consecutive_losses = 0
        self._last_trade_result: Optional[str] = None
        self._cooldown_start: Optional[datetime] = None
        self._cooldown_until: Optional[datetime] = None

        self._last_update_time: Optional[datetime] = None

    @property
    def current_state(self) -> StrategyLifecycleState:
        return self._state

    @property
    def consecutive_losses(self) -> int:
        return self._consecutive_losses

    def get_snapshot(self, timestamp: datetime) -> StrategyState:
        """Returns a snapshot of the current state for the given timestamp."""
        return StrategyState(
            timestamp=timestamp,
            strategy_id=self.strategy_id,
            instance_id=self.instance_id,
            state=self._state,
            reason=self._reason,
            consecutive_losses=self._consecutive_losses,
            last_trade_result=self._last_trade_result,
            cooldown_start=self._cooldown_start,
            cooldown_until=self._cooldown_until,
        )

    def update_from_trade(self, trade: Trade) -> Optional[StrategyState]:
        """
        Update state based on a closed trade.

        A closed trade can trigger a reset of consecutive losses (if WIN or BREAK-EVEN)
        or increment consecutive losses (if LOSS).
        If consecutive losses hit the limit, transitions to PAUSED (COOLDOWN).
        
        Returns the new state snapshot if a transition occurred, else None.
        """
        # Ensure PIT: trades must be processed in chronological order
        trade_time = trade.exit_fill.timestamp
        if self._last_update_time and trade_time < self._last_update_time:
            raise ValueError(f"Out of order trade update: {trade_time} < {self._last_update_time}")
        self._last_update_time = trade_time

        # Ignore if permanently disabled
        if self._state == StrategyLifecycleState.DISABLED:
            return None

        # Determine trade result
        if trade.net_pnl > 0:
            result = "WIN"
        elif trade.net_pnl < 0:
            result = "LOSS"
        else:
            result = "BREAK_EVEN"

        self._last_trade_result = result
        state_changed = False

        if result == "LOSS":
            self._consecutive_losses += 1
        elif result == "WIN":
            self._consecutive_losses = 0
        elif result == "BREAK_EVEN" and self._config.break_even_resets_losses:
            self._consecutive_losses = 0
            
        # Check for cooldown trigger
        if (
            self._state == StrategyLifecycleState.ACTIVE
            and self._consecutive_losses >= self._config.consecutive_loss_limit
            and self._config.cooldown.enabled
        ):
            self._state = StrategyLifecycleState.PAUSED
            self._reason = "CONSECUTIVE_LOSS_LIMIT"
            self._cooldown_start = trade_time
            
            # Calculate cooldown expiry
            duration = self._config.cooldown.value
            if self._config.cooldown.unit == "hours":
                self._cooldown_until = trade_time + timedelta(hours=duration)
            else:
                # "candles" is harder to compute here without knowing the exact timeframe calendar.
                # Assuming hours is the default as per Prompt 05.
                # For a full implementation of "candles", the engine would need to advance this based on candle ticks.
                # Fallback to hours if unit not implemented perfectly.
                logger.warning("Cooldown unit 'candles' requested but mapped to hours in state machine.")
                self._cooldown_until = trade_time + timedelta(hours=duration)
                
            state_changed = True

        if state_changed:
            return self.get_snapshot(trade_time)
        return None

    def check_cooldown(self, current_timestamp: datetime) -> Optional[StrategyState]:
        """
        Check if a cooldown period has expired at the current simulation time.
        If expired, transitions from PAUSED back to ACTIVE.
        
        Returns the new state snapshot if a transition occurred, else None.
        """
        if self._state == StrategyLifecycleState.PAUSED and self._reason == "CONSECUTIVE_LOSS_LIMIT":
            if self._cooldown_until and current_timestamp >= self._cooldown_until:
                self._state = StrategyLifecycleState.ACTIVE
                self._reason = "COOLDOWN_EXPIRED"
                self._cooldown_start = None
                self._cooldown_until = None
                # Reset consecutive losses when re-entering ACTIVE from cooldown
                self._consecutive_losses = 0
                return self.get_snapshot(current_timestamp)
        return None

    def force_state(self, state: StrategyLifecycleState, reason: str, timestamp: datetime) -> StrategyState:
        """Manually force a state transition (e.g., DISABLED)."""
        self._state = state
        self._reason = reason
        return self.get_snapshot(timestamp)
