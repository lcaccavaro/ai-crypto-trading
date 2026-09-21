"""
Abstract base class for all Prompt 04 strategy implementations.

Design:
    BaseStrategy enforces the warm-up contract, parameter validation,
    and the generate_signal() interface from strategies/interface.py.

    Every concrete strategy subclasses BaseStrategy and:
    1. Defines `_info` (StrategyInfo) as a class attribute.
    2. Implements `_compute_signal(candles, timestamp) -> Signal | None`.
    3. Optionally validates parameters in `__init__`.

Signal semantics:
    - Event-based strategies (is_event_based=True): signal only on transition
      (e.g. EMA crossover — only when fast crosses above slow, not every
      candle where fast > slow). These strategies track previous state.
    - State-based strategies (is_event_based=False): signal whenever the
      current state meets conditions (e.g. Z-score below threshold).

Warm-up enforcement:
    generate_signal() returns None when len(candles) < minimum_candles_required.
    This is enforced at the base class level — concrete strategies do not
    need to re-check warm-up.

State isolation:
    Each BaseStrategy instance carries independent state. Multiple instances
    (BTC/5m, ETH/15m) must NEVER share state — they are separate objects.

Parameter validation:
    Subclasses must call _validate_params() in __init__.
    Invalid parameters raise ValueError immediately — no silent corrections.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from crypto_research.core.domain import Candle, Signal, StrategyInfo, StrategyMetadata
from crypto_research.core.exceptions import LookAheadBiasError


class BaseStrategy(ABC):
    """
    Abstract base for all Prompt 04 strategy implementations.

    Subclasses must:
    1. Set `_info: StrategyInfo` as a class-level attribute (not instance).
    2. Implement `_compute_signal(candles, timestamp) -> Signal | None`.
    3. Call `super().__init__()` in their `__init__`.

    Example:
        class EMACrossover(BaseStrategy):
            _info = StrategyInfo(
                strategy_id="EMA_CROSS_001",
                name="EMA Crossover",
                ...
            )
            def __init__(self, fast_period=9, slow_period=21):
                super().__init__()
                if fast_period >= slow_period:
                    raise ValueError(...)
                self._fast = fast_period
                self._slow = slow_period
                self._prev_fast_above: bool | None = None  # crossover state
    """

    _info: StrategyInfo  # Must be set by every concrete subclass

    def __init__(self) -> None:
        # Verify subclass has defined _info
        if not hasattr(self, "_info"):
            raise TypeError(
                f"{type(self).__name__} must define class attribute `_info: StrategyInfo`"
            )

    # ------------------------------------------------------------------
    # Strategy Protocol properties (satisfies strategies/interface.py)
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        """Unique strategy identifier."""
        return self._info.strategy_id

    @property
    def version(self) -> str:
        """Strategy semantic version."""
        return self._info.version

    @property
    def info(self) -> StrategyInfo:
        """Full Prompt 04 strategy metadata."""
        return self._info

    @property
    def metadata(self) -> StrategyMetadata:
        """
        Prompt 01/03 compatible StrategyMetadata.
        Bridges to the existing interface without breaking backward compat.
        """
        return StrategyMetadata(
            name=self._info.strategy_id,
            version=self._info.version,
            description=self._info.description,
            parameters=self.parameters,
        )

    @property
    def minimum_candles_required(self) -> int:
        """Minimum candles needed before signals are valid (= warmup_period)."""
        return self._info.warmup_period

    @property
    @abstractmethod
    def parameters(self) -> dict:
        """
        Current parameter values for this instance.
        All configurable values that affect signal generation must appear here.
        This dict is recorded in every research run for reproducibility.
        """

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def generate_signal(
        self,
        candles: list[Candle],
        timestamp: datetime,
    ) -> Signal | None:
        """
        Evaluate historical data and produce a trading signal.

        Warm-up enforcement: returns None if len(candles) < warmup_period.

        Args:
            candles:   Ordered historical candles (ascending timestamp).
                       Contains only data available at `timestamp` (PIT-safe).
            timestamp: Current simulation timestamp.

        Returns:
            Signal or None.
        """
        if len(candles) < self.minimum_candles_required:
            return None
        return self._compute_signal(candles, timestamp)

    @abstractmethod
    def _compute_signal(
        self,
        candles: list[Candle],
        timestamp: datetime,
    ) -> Signal | None:
        """
        Core signal logic. Only called when warm-up is satisfied.

        Implementations must:
        - Only use data from `candles` (no external mutable state).
        - Return Signal or None.
        - Never access future candles.
        """

    def reset(self) -> None:
        """
        Reset all internal state.

        Called between backtest runs or when resetting instance state.
        Concrete strategies must override this if they maintain state
        (e.g. crossover tracking, previous values).
        """
        # Default: no state to reset

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}("
            f"id={self._info.strategy_id!r}, "
            f"v={self._info.version!r}, "
            f"params={self.parameters!r})"
        )
