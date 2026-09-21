"""
Strategy instance identity and context.

StrategyInstance:
    Binds (strategy_id, symbol, timeframe, parameters, version) into a
    deterministic, human-readable instance ID.

    Format: EMA_CROSS_001__BTCUSDT__15m__v1.0.0
    With custom params: EMA_CROSS_001__BTCUSDT__15m__v1.0.0__p7a3f2c1 (param hash suffix)

    State isolation: each StrategyInstance object is independent. Running
    BTC/5m and ETH/15m creates two objects with no shared state.

StrategyContext:
    Passed to the strategy during backtesting. Wraps the strategy instance
    metadata alongside the HistoricalDataView from the backtest engine.
    Strategies receive this to access their identity metadata if needed.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field


@dataclass(frozen=True)
class StrategyInstance:
    """
    Deterministic identity for a strategy instance.

    A strategy instance is uniquely defined by:
        strategy_id + symbol + timeframe + parameters + version

    The instance_id is computed deterministically from these fields.
    Same inputs always produce the same instance_id.

    Fields:
        strategy_id:  Strategy identifier, e.g. "EMA_CROSS_001".
        symbol:       Asset symbol, e.g. "BTCUSDT".
        timeframe:    Timeframe string, e.g. "15m".
        version:      Strategy version, e.g. "1.0.0".
        parameters:   Configured parameters for this instance.
        instance_id:  Deterministic unique ID (computed in __post_init__).
    """

    strategy_id: str
    symbol: str
    timeframe: str
    version: str
    parameters: dict = field(default_factory=dict)

    # Computed in __post_init__ — not set by caller
    instance_id: str = field(init=False, compare=False)

    def __post_init__(self) -> None:
        if not self.strategy_id:
            raise ValueError("strategy_id must not be empty")
        if not self.symbol:
            raise ValueError("symbol must not be empty")
        if not self.timeframe:
            raise ValueError("timeframe must not be empty")
        if not self.version:
            raise ValueError("version must not be empty")

        # Build the instance_id
        base_id = f"{self.strategy_id}__{self.symbol}__{self.timeframe}__v{self.version}"

        if self.parameters:
            # Deterministic parameter hash: sort keys, serialize to JSON, SHA256 prefix
            param_str = json.dumps(self.parameters, sort_keys=True, separators=(",", ":"))
            param_hash = hashlib.sha256(param_str.encode()).hexdigest()[:8]
            computed_id = f"{base_id}__{param_hash}"
        else:
            computed_id = base_id

        # frozen=True requires object.__setattr__
        object.__setattr__(self, "instance_id", computed_id)

    def __str__(self) -> str:
        return self.instance_id

    def __repr__(self) -> str:
        return (
            f"StrategyInstance("
            f"id={self.instance_id!r}, "
            f"strategy={self.strategy_id!r}, "
            f"symbol={self.symbol!r}, "
            f"timeframe={self.timeframe!r}"
            f")"
        )


@dataclass
class StrategyContext:
    """
    Context object passed to strategies during execution.

    Contains the strategy's instance identity metadata.
    The actual candle data is passed directly to generate_signal().

    This object is informational — strategies should not use it to access
    portfolio state or future information.

    Fields:
        instance:    The StrategyInstance defining this execution context.
        run_id:      Research run identifier for traceability.
    """

    instance: StrategyInstance
    run_id: str

    @property
    def strategy_id(self) -> str:
        return self.instance.strategy_id

    @property
    def symbol(self) -> str:
        return self.instance.symbol

    @property
    def timeframe(self) -> str:
        return self.instance.timeframe

    @property
    def instance_id(self) -> str:
        return self.instance.instance_id
