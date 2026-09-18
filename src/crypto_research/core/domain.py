"""
Core domain objects for the crypto research laboratory.

These are the foundational data structures that flow through every layer of
the system — from data ingestion through strategy evaluation, risk management,
execution simulation, and reporting.

Design principles:
    - Strongly typed using dataclasses, enums and typing.
    - Immutable where practical (frozen=True).
    - Explicit field names — no generic dicts for research objects.
    - Every object carries the timestamp/asset/timeframe context needed for
      point-in-time research.

IMPORTANT: These are domain MODELS, not implementations.
    The actual ingestion, strategy logic, execution and risk logic live in
    their respective packages and are added in later prompts.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class Timeframe(str, Enum):
    """
    Supported candlestick timeframes.

    Using str mixin allows direct YAML/JSON serialization of enum values.
    """

    M1 = "1m"
    M3 = "3m"
    M5 = "5m"
    M15 = "15m"
    M30 = "30m"
    H1 = "1h"
    H2 = "2h"
    H4 = "4h"

    @classmethod
    def from_string(cls, value: str) -> "Timeframe":
        """
        Parse a timeframe string.

        Raises:
            ValueError: If the string does not map to a known timeframe.
        """
        try:
            return cls(value)
        except ValueError:
            valid = [e.value for e in cls]
            raise ValueError(
                f"Unknown timeframe '{value}'. Valid values: {valid}"
            ) from None


class SignalDirection(str, Enum):
    """Direction of a trading signal produced by a strategy."""

    LONG = "long"
    SHORT = "short"
    NEUTRAL = "neutral"


class OrderSide(str, Enum):
    """Side of an order (buy or sell)."""

    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    """Type of order to be submitted to the execution engine."""

    MARKET = "market"
    LIMIT = "limit"
    STOP_MARKET = "stop_market"
    STOP_LIMIT = "stop_limit"


class PositionSide(str, Enum):
    """Whether the position is long or short."""

    LONG = "long"
    SHORT = "short"


# ---------------------------------------------------------------------------
# Market Data
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Candle:
    """
    A single OHLCV candlestick.

    The timestamp represents the OPEN of the candle (start of the period).
    Using the open timestamp prevents any look-ahead bias — the close price
    is information that only becomes available at timestamp + timeframe.

    Fields:
        timestamp:  UTC open timestamp of the candle.
        asset:      Trading symbol, e.g. "BTCUSDT".
        timeframe:  Candlestick period.
        open:       Open price.
        high:       High price during the period.
        low:        Low price during the period.
        close:      Close price (available only at period end).
        volume:     Base asset volume traded during the period.
    """

    timestamp: datetime
    asset: str
    timeframe: Timeframe
    open: float
    high: float
    low: float
    close: float
    volume: float

    def __post_init__(self) -> None:
        """Validate OHLC relationships on construction."""
        if self.high < self.low:
            raise ValueError(
                f"Candle integrity violation: high ({self.high}) < low ({self.low}) "
                f"for {self.asset} {self.timeframe.value} @ {self.timestamp}"
            )
        if self.high < self.open or self.high < self.close:
            raise ValueError(
                f"Candle integrity violation: high ({self.high}) is below open "
                f"({self.open}) or close ({self.close}) "
                f"for {self.asset} {self.timeframe.value} @ {self.timestamp}"
            )
        if self.low > self.open or self.low > self.close:
            raise ValueError(
                f"Candle integrity violation: low ({self.low}) is above open "
                f"({self.open}) or close ({self.close}) "
                f"for {self.asset} {self.timeframe.value} @ {self.timestamp}"
            )
        if self.volume < 0:
            raise ValueError(
                f"Candle integrity violation: negative volume ({self.volume}) "
                f"for {self.asset} {self.timeframe.value} @ {self.timestamp}"
            )


# ---------------------------------------------------------------------------
# Strategy Signals
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Signal:
    """
    A trading signal produced by a strategy at a specific point in time.

    The timestamp is the simulation timestamp at which the signal was
    generated — it must NEVER exceed the current simulation point in time.

    Fields:
        timestamp:      UTC timestamp when the signal was generated.
        strategy_name:  Name of the strategy that produced it.
        asset:          Target asset symbol.
        timeframe:      Timeframe the strategy operated on.
        direction:      Long, short, or neutral.
        strength:       Optional normalized signal strength in [0.0, 1.0].
        metadata:       Optional free-form dict for strategy-specific extras.
                        Must never contain future information.
    """

    timestamp: datetime
    strategy_name: str
    asset: str
    timeframe: Timeframe
    direction: SignalDirection
    strength: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not (0.0 <= self.strength <= 1.0):
            raise ValueError(
                f"Signal strength must be in [0.0, 1.0], got {self.strength}"
            )


# ---------------------------------------------------------------------------
# Orders & Fills
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Order:
    """
    An order request submitted to the execution engine.

    Fields:
        order_id:   Unique identifier for this order.
        timestamp:  UTC time at which the order was submitted.
        asset:      Trading symbol.
        side:       Buy or sell.
        order_type: Market, limit, stop, etc.
        quantity:   Order size in base asset units.
        price:      Limit price (None for market orders).
        stop_price: Stop trigger price (for stop orders).
        strategy_name: The strategy that generated this order.
        run_id:     Research run identifier for traceability.
    """

    order_id: str
    timestamp: datetime
    asset: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    strategy_name: str
    run_id: str
    price: float | None = None
    stop_price: float | None = None

    def __post_init__(self) -> None:
        if self.quantity <= 0:
            raise ValueError(
                f"Order quantity must be positive, got {self.quantity}"
            )
        if self.order_type == OrderType.LIMIT and self.price is None:
            raise ValueError("Limit orders require a price.")
        if self.order_type in (OrderType.STOP_MARKET, OrderType.STOP_LIMIT):
            if self.stop_price is None:
                raise ValueError(
                    f"Stop orders require a stop_price. Got None for {self.order_type}"
                )

    @classmethod
    def create(
        cls,
        timestamp: datetime,
        asset: str,
        side: OrderSide,
        order_type: OrderType,
        quantity: float,
        strategy_name: str,
        run_id: str,
        price: float | None = None,
        stop_price: float | None = None,
    ) -> "Order":
        """Factory method that auto-generates a unique order_id."""
        return cls(
            order_id=str(uuid.uuid4()),
            timestamp=timestamp,
            asset=asset,
            side=side,
            order_type=order_type,
            quantity=quantity,
            strategy_name=strategy_name,
            run_id=run_id,
            price=price,
            stop_price=stop_price,
        )


@dataclass(frozen=True)
class Fill:
    """
    The execution result of an Order.

    A Fill represents that an order was actually executed at a specific price
    and time, with associated fees.

    Fields:
        fill_id:        Unique identifier for this fill.
        order_id:       The order that was filled.
        timestamp:      UTC time the fill occurred.
        asset:          Trading symbol.
        side:           Buy or sell.
        fill_price:     Actual execution price.
        quantity:       Filled quantity.
        fees:           Total fees paid in quote asset.
        slippage:       Slippage from requested price (informational).
    """

    fill_id: str
    order_id: str
    timestamp: datetime
    asset: str
    side: OrderSide
    fill_price: float
    quantity: float
    fees: float
    slippage: float = 0.0

    def __post_init__(self) -> None:
        if self.fill_price <= 0:
            raise ValueError(
                f"Fill price must be positive, got {self.fill_price}"
            )
        if self.quantity <= 0:
            raise ValueError(
                f"Fill quantity must be positive, got {self.quantity}"
            )
        if self.fees < 0:
            raise ValueError(
                f"Fill fees cannot be negative, got {self.fees}"
            )

    @property
    def gross_value(self) -> float:
        """Total value of the fill before fees."""
        return self.fill_price * self.quantity

    @property
    def net_value(self) -> float:
        """Net value after fees (from buyer's perspective: cost + fees)."""
        return self.gross_value + self.fees


# ---------------------------------------------------------------------------
# Positions & Trades
# ---------------------------------------------------------------------------


@dataclass
class Position:
    """
    An open position resulting from one or more fills.

    Unlike Candle/Signal/Order/Fill which are frozen (immutable), Position
    is mutable because it updates as prices move and management decisions
    are applied.

    Fields:
        position_id:    Unique identifier.
        asset:          Trading symbol.
        side:           Long or short.
        entry_fill:     The fill that opened the position.
        strategy_name:  Strategy that generated this position.
        run_id:         Research run for traceability.
        stop_price:     Current stop-loss price (updated as position evolves).
        target_price:   Current take-profit target price.
        current_price:  Last known market price (updated by simulation).
    """

    position_id: str
    asset: str
    side: PositionSide
    entry_fill: Fill
    strategy_name: str
    run_id: str
    stop_price: float | None = None
    target_price: float | None = None
    current_price: float | None = None

    @property
    def entry_price(self) -> float:
        return self.entry_fill.fill_price

    @property
    def quantity(self) -> float:
        return self.entry_fill.quantity

    @property
    def unrealized_pnl(self) -> float | None:
        """
        Unrealized P&L at current_price. Returns None if price is unknown.

        For long positions: (current - entry) * quantity
        For short positions: (entry - current) * quantity
        """
        if self.current_price is None:
            return None
        if self.side == PositionSide.LONG:
            return (self.current_price - self.entry_price) * self.quantity
        return (self.entry_price - self.current_price) * self.quantity

    @classmethod
    def create(
        cls,
        asset: str,
        side: PositionSide,
        entry_fill: Fill,
        strategy_name: str,
        run_id: str,
        stop_price: float | None = None,
        target_price: float | None = None,
    ) -> "Position":
        """Factory method that auto-generates a unique position_id."""
        return cls(
            position_id=str(uuid.uuid4()),
            asset=asset,
            side=side,
            entry_fill=entry_fill,
            strategy_name=strategy_name,
            run_id=run_id,
            stop_price=stop_price,
            target_price=target_price,
        )


@dataclass(frozen=True)
class Trade:
    """
    A completed trade — the full lifecycle of a position from entry to exit.

    Fields:
        trade_id:       Unique identifier.
        asset:          Trading symbol.
        side:           Long or short.
        entry_fill:     Fill that opened the position.
        exit_fill:      Fill that closed the position.
        strategy_name:  Strategy that generated the trade.
        timeframe:      Timeframe of the strategy signal.
        run_id:         Research run for traceability.
        realized_pnl:   Realized profit/loss (after fees).
        exit_reason:    Why the trade was closed (target/stop/time/manual).
    """

    trade_id: str
    asset: str
    side: PositionSide
    entry_fill: Fill
    exit_fill: Fill
    strategy_name: str
    timeframe: Timeframe
    run_id: str
    realized_pnl: float
    exit_reason: str

    @property
    def duration(self):
        """Duration of the trade as a timedelta."""
        return self.exit_fill.timestamp - self.entry_fill.timestamp

    @property
    def is_winner(self) -> bool:
        return self.realized_pnl > 0

    @classmethod
    def create(
        cls,
        asset: str,
        side: PositionSide,
        entry_fill: Fill,
        exit_fill: Fill,
        strategy_name: str,
        timeframe: Timeframe,
        run_id: str,
        realized_pnl: float,
        exit_reason: str,
    ) -> "Trade":
        """Factory method that auto-generates a unique trade_id."""
        return cls(
            trade_id=str(uuid.uuid4()),
            asset=asset,
            side=side,
            entry_fill=entry_fill,
            exit_fill=exit_fill,
            strategy_name=strategy_name,
            timeframe=timeframe,
            run_id=run_id,
            realized_pnl=realized_pnl,
            exit_reason=exit_reason,
        )


# ---------------------------------------------------------------------------
# Strategy & Risk Metadata
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StrategyMetadata:
    """
    Descriptive metadata for a strategy implementation.

    This metadata is recorded in each research run for reproducibility.
    Every parameter that can affect strategy behavior MUST be included.

    Fields:
        name:        Unique strategy identifier.
        version:     Strategy version string.
        description: Human-readable description.
        parameters:  All configurable parameters (key → value).
                     Must not contain any mutable state.
    """

    name: str
    version: str
    description: str
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RiskDecision:
    """
    A risk management decision in response to a trading signal.

    The risk manager evaluates each signal against portfolio state and
    returns a decision: approved or rejected, with reason and sizing.

    Fields:
        approved:           True if the trade is permitted.
        reason:             Explanation of the decision (always required).
        max_position_size:  Maximum allowed position size if approved.
        risk_amount:        Maximum capital at risk for this trade.
    """

    approved: bool
    reason: str
    max_position_size: float | None = None
    risk_amount: float | None = None

    def __post_init__(self) -> None:
        if not self.reason:
            raise ValueError("RiskDecision must always include a reason.")
        if self.approved and self.max_position_size is None:
            raise ValueError(
                "Approved RiskDecision must specify max_position_size."
            )


# ---------------------------------------------------------------------------
# Research Run
# ---------------------------------------------------------------------------


@dataclass
class ResearchRun:
    """
    Metadata record for a single research execution.

    Every time the system runs a backtest, validation, or experiment, a
    ResearchRun is created. This enables full reproducibility — any past
    run can be re-executed given the same run metadata.

    Fields:
        run_id:              Unique identifier, e.g. RUN_20260915_000000_abc123.
        created_at:          UTC timestamp of run creation.
        python_version:      Python version string.
        package_versions:    Dict of package name → version.
        git_commit:          Git commit hash, or "unavailable" if not in a repo.
        config_path:         Absolute path to the config file used.
        config_snapshot:     Full copy of the configuration at run time.
        assets:              List of asset symbols in scope.
        timeframes:          List of timeframe strings in scope.
        run_directory:       Absolute path to the run output directory.
        environment_info:    Additional environment metadata (OS, etc.).
    """

    run_id: str
    created_at: datetime
    python_version: str
    package_versions: dict[str, str]
    git_commit: str
    config_path: str
    config_snapshot: dict[str, Any]
    assets: list[str]
    timeframes: list[str]
    run_directory: str
    environment_info: dict[str, Any] = field(default_factory=dict)
