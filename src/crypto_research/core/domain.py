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

Prompt 03 additions:
    - New enums: OrderStatus, ExitReason, RejectionReason, PositionSizingMode,
                 IntrabarFillPolicy, GapPolicy, MarketType
    - Extended: Order (stop_price, target_price, timeframe, status, etc.)
    - Extended: Fill (spread_cost)
    - Extended: Trade (gross_pnl, fees, slippage_cost, spread_cost, net_pnl,
                       risk_amount, r_multiple, initial_stop, holding_duration_seconds)
    - New: PortfolioState, EquityCurvePoint, ExecutionEvent
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

    def to_seconds(self) -> int:
        """Return the timeframe duration in seconds."""
        mapping = {
            "1m": 60,
            "3m": 180,
            "5m": 300,
            "15m": 900,
            "30m": 1800,
            "1h": 3600,
            "2h": 7200,
            "4h": 14400,
        }
        return mapping[self.value]


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


class OrderStatus(str, Enum):
    """
    Lifecycle status of an order.

    PENDING     — Order created, not yet activated.
    ACTIVE      — Order is live and awaiting execution.
    FILLED      — Order was fully executed.
    REJECTED    — Order was rejected before activation (risk/capital limits).
    CANCELLED   — Order was cancelled after activation but before fill.
    """

    PENDING = "pending"
    ACTIVE = "active"
    FILLED = "filled"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class PositionSide(str, Enum):
    """Whether the position is long or short."""

    LONG = "long"
    SHORT = "short"


class MarketType(str, Enum):
    """
    Type of market this position/order is in.

    SPOT       — Cash market (no leverage, no shorting by default).
    FUTURES    — Dated futures contracts.
    PERPETUAL  — Perpetual (USDT-margined) futures.
    """

    SPOT = "spot"
    FUTURES = "futures"
    PERPETUAL = "perpetual"


class ExitReason(str, Enum):
    """
    Reason a position was closed.

    STOP                  — Stop-loss was hit.
    TARGET                — Take-profit target was reached.
    DAILY_PROFIT_TARGET   — Position closed because daily profit target reached.
    DAILY_LOSS_LIMIT      — Position closed because daily loss limit reached.
    MANUAL                — Manually closed (not used in Prompt 03 backtesting).
    END_OF_DATA           — Simulation ended while position was open.
    """

    STOP = "stop"
    TARGET = "target"
    DAILY_PROFIT_TARGET = "daily_profit_target"
    DAILY_LOSS_LIMIT = "daily_loss_limit"
    MANUAL = "manual"
    END_OF_DATA = "end_of_data"


class RejectionReason(str, Enum):
    """
    Reason an order was rejected by the risk gate.

    These are logged and included in the execution ledger.
    No rejected order is silently discarded.
    """

    MAX_CONCURRENT_POSITIONS = "max_concurrent_positions"
    MAX_TOTAL_EXPOSURE = "max_total_exposure"
    MAX_ASSET_EXPOSURE = "max_asset_exposure"
    DAILY_PROFIT_TARGET_REACHED = "daily_profit_target_reached"
    DAILY_LOSS_LIMIT_REACHED = "daily_loss_limit_reached"
    INSUFFICIENT_CAPITAL = "insufficient_capital"
    INVALID_ORDER = "invalid_order"
    SHORT_NOT_ALLOWED = "short_not_allowed"
    MARKET_NOT_AVAILABLE = "market_not_available"
    STRATEGY_PAUSED = "strategy_paused"
    STRATEGY_DISABLED = "strategy_disabled"
    COOLDOWN_ACTIVE = "cooldown_active"
    MAX_STRATEGY_EXPOSURE = "max_strategy_exposure"
    LOW_SCORE = "low_score"
    DUPLICATE_SIGNAL = "duplicate_signal"
    CONFLICTING_SIGNAL = "conflicting_signal"
    INVALID_CONFIGURATION = "invalid_configuration"
    INVALID_STOP = "invalid_stop"
    INVALID_RISK = "invalid_risk"


class PositionSizingMode(str, Enum):
    """Position sizing algorithm."""

    RISK_BASED = "risk_based"
    FIXED = "fixed"


class IntrabarFillPolicy(str, Enum):
    """
    Policy for handling candles where both stop and target are touched.

    When a single OHLC candle's high >= target AND low <= stop, we cannot
    know from OHLC data alone which was hit first. This policy determines
    the engine's behavior in that case.

    STOP_FIRST       — Assume the stop was hit first (conservative, default).
    TARGET_FIRST     — Assume the target was hit first (optimistic).
    REJECT_AMBIGUOUS — Record neither; log the ambiguity and skip the candle.

    IMPORTANT: None of these interpretations is factually correct at OHLC
    resolution. The correct interpretation requires tick data. Document this
    limitation clearly in research outputs.
    """

    STOP_FIRST = "stop_first"
    TARGET_FIRST = "target_first"
    REJECT_AMBIGUOUS = "reject_ambiguous"


class GapPolicy(str, Enum):
    """
    Policy for handling price gaps beyond stop or target.

    When a candle opens beyond a stop or target level (gap), the engine
    cannot fill at the stop/target price because the market never traded
    there during normal hours.

    FILL_AT_OPEN  — Fill at the candle's open price (realistic, default).
    FILL_AT_LEVEL — Fill at the stop/target level (unrealistic, optimistic).

    Default: FILL_AT_OPEN. A realistic backtest must use FILL_AT_OPEN.
    """

    FILL_AT_OPEN = "fill_at_open"
    FILL_AT_LEVEL = "fill_at_level"




class StrategyLifecycleState(str, Enum):
    """
    Lifecycle state of a strategy instance in the portfolio orchestrator.

    ACTIVE   — Strategy is operating normally and may generate/accept entries.
    PAUSED   — Temporarily paused (e.g. consecutive loss limit). New entries
               blocked. Existing positions continue under execution management.
    DISABLED — Permanently disabled for this run (manual/configured). No entries.
    COOLDOWN — Alias for PAUSED during a timed cooldown period.
               The system uses PAUSED as the canonical state; COOLDOWN indicates
               the specific sub-reason. Recorded in the strategy state ledger.
    """

    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"
    COOLDOWN = "cooldown"


class DailyLimitState(str, Enum):
    """
    Portfolio-level daily limit status.

    OPEN                  — No daily limit has been reached. New entries allowed.
    PROFIT_TARGET_REACHED — Daily profit target reached. New entries blocked.
    LOSS_LIMIT_REACHED    — Daily loss limit reached. New entries blocked.

    Resets at UTC midnight (start of each UTC calendar day).
    """

    OPEN = "open"
    PROFIT_TARGET_REACHED = "profit_target_reached"
    LOSS_LIMIT_REACHED = "loss_limit_reached"


class DecisionOutcome(str, Enum):
    """Outcome of a portfolio risk decision for a strategy signal."""

    ACCEPTED = "accepted"
    REJECTED = "rejected"

class EventType(str, Enum):
    """Type of execution event recorded in the audit ledger."""

    BACKTEST_STARTED = "backtest_started"
    DATA_VALIDATED = "data_validated"
    SIGNAL_RECEIVED = "signal_received"
    ORDER_CREATED = "order_created"
    ORDER_REJECTED = "order_rejected"
    ORDER_FILLED = "order_filled"
    STOP_TRIGGERED = "stop_triggered"
    TARGET_TRIGGERED = "target_triggered"
    POSITION_OPENED = "position_opened"
    POSITION_CLOSED = "position_closed"
    RISK_LIMIT_REACHED = "risk_limit_reached"
    DAILY_RESET = "daily_reset"
    BACKTEST_COMPLETED = "backtest_completed"
    BACKTEST_FAILED = "backtest_failed"
    GAP_FILL = "gap_fill"
    INTRABAR_AMBIGUITY = "intrabar_ambiguity"


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
        close_time: UTC close timestamp of the candle (= timestamp + timeframe - 1ms).
    """

    timestamp: datetime
    asset: str
    timeframe: Timeframe
    open: float
    high: float
    low: float
    close: float
    volume: float
    close_time: datetime | None = None

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
        stop_price:     Suggested stop-loss price (strategy hint, not required).
        target_price:   Suggested take-profit price (strategy hint, not required).
        metadata:       Optional free-form dict for strategy-specific extras.
                        Must never contain future information.
    """

    timestamp: datetime
    strategy_name: str
    asset: str
    timeframe: Timeframe
    direction: SignalDirection
    strength: float = 1.0
    stop_price: float | None = None
    target_price: float | None = None
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
        order_id:         Unique identifier for this order.
        timestamp:        UTC time at which the order was submitted.
        asset:            Trading symbol.
        side:             Buy or sell.
        order_type:       Market, limit, stop, etc.
        quantity:         Order size in base asset units.
        strategy_name:    The strategy that generated this order.
        run_id:           Research run identifier for traceability.
        timeframe:        Timeframe of the strategy signal.
        price:            Limit price (None for market orders).
        stop_price:       Stop-loss level for the position (not a stop order price).
        target_price:     Take-profit level for the position.
        activation_time:  When this order becomes active (None = immediately).
        status:           Current lifecycle status.
        rejection_reason: If rejected, the reason (for audit log).
    """

    order_id: str
    timestamp: datetime
    asset: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    strategy_name: str
    run_id: str
    timeframe: Timeframe | None = None
    price: float | None = None
    stop_price: float | None = None
    target_price: float | None = None
    activation_time: datetime | None = None
    status: OrderStatus = OrderStatus.PENDING
    rejection_reason: RejectionReason | None = None

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
        timeframe: Timeframe | None = None,
        price: float | None = None,
        stop_price: float | None = None,
        target_price: float | None = None,
        activation_time: datetime | None = None,
        status: OrderStatus = OrderStatus.PENDING,
        rejection_reason: RejectionReason | None = None,
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
            timeframe=timeframe,
            price=price,
            stop_price=stop_price,
            target_price=target_price,
            activation_time=activation_time,
            status=status,
            rejection_reason=rejection_reason,
        )


@dataclass(frozen=True)
class Fill:
    """
    The execution result of an Order.

    A Fill represents that an order was actually executed at a specific price
    and time, with associated costs.

    Cost breakdown (no double-counting):
        execution_price = requested_price
                         + slippage (directional, adverse to trader)
                         + spread   (half-spread, cost of crossing bid/ask)
        fee             = execution_price × quantity × fee_rate
        gross_value     = requested_price × quantity
        net_cost        = execution_price × quantity + fee  (for buys)

    Fields:
        fill_id:          Unique identifier for this fill.
        order_id:         The order that was filled.
        timestamp:        UTC time the fill occurred.
        asset:            Trading symbol.
        side:             Buy or sell.
        fill_price:       Actual execution price (including slippage + spread).
        quantity:         Filled quantity.
        fees:             Total fees paid in quote asset.
        slippage:         Slippage cost in quote asset (informational).
        spread_cost:      Spread cost in quote asset (informational).
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
    spread_cost: float = 0.0

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
        """Total value of the fill at execution price, before fees."""
        return self.fill_price * self.quantity

    @property
    def net_value(self) -> float:
        """Net value after fees (from buyer's perspective: cost + fees)."""
        return self.gross_value + self.fees

    @classmethod
    def create(
        cls,
        order_id: str,
        timestamp: datetime,
        asset: str,
        side: OrderSide,
        fill_price: float,
        quantity: float,
        fees: float,
        slippage: float = 0.0,
        spread_cost: float = 0.0,
    ) -> "Fill":
        """Factory method that auto-generates a unique fill_id."""
        return cls(
            fill_id=str(uuid.uuid4()),
            order_id=order_id,
            timestamp=timestamp,
            asset=asset,
            side=side,
            fill_price=fill_price,
            quantity=quantity,
            fees=fees,
            slippage=slippage,
            spread_cost=spread_cost,
        )


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
        timeframe:      Timeframe of the strategy signal.
        stop_price:     Current stop-loss price.
        target_price:   Current take-profit target price.
        current_price:  Last known market price (updated by simulation).
        initial_stop:   Original stop-loss price (for R-multiple calculation).
        risk_amount:    Dollar amount at risk (entry notional × stop distance %).
    """

    position_id: str
    asset: str
    side: PositionSide
    entry_fill: Fill
    strategy_name: str
    run_id: str
    timeframe: Timeframe | None = None
    stop_price: float | None = None
    target_price: float | None = None
    current_price: float | None = None
    initial_stop: float | None = None
    risk_amount: float | None = None

    @property
    def entry_price(self) -> float:
        return self.entry_fill.fill_price

    @property
    def quantity(self) -> float:
        return self.entry_fill.quantity

    @property
    def notional(self) -> float:
        """Current notional value = quantity × current_price (or entry_price if unknown)."""
        price = self.current_price if self.current_price is not None else self.entry_price
        return price * self.quantity

    @property
    def unrealized_pnl(self) -> float | None:
        """
        Unrealized P&L at current_price. Returns None if price is unknown.

        For long positions:  (current - entry) × quantity
        For short positions: (entry - current) × quantity
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
        timeframe: Timeframe | None = None,
        stop_price: float | None = None,
        target_price: float | None = None,
        initial_stop: float | None = None,
        risk_amount: float | None = None,
    ) -> "Position":
        """Factory method that auto-generates a unique position_id."""
        return cls(
            position_id=str(uuid.uuid4()),
            asset=asset,
            side=side,
            entry_fill=entry_fill,
            strategy_name=strategy_name,
            run_id=run_id,
            timeframe=timeframe,
            stop_price=stop_price,
            target_price=target_price,
            initial_stop=initial_stop or stop_price,
            risk_amount=risk_amount,
        )


@dataclass(frozen=True)
class Trade:
    """
    A completed trade — the full lifecycle of a position from entry to exit.

    Cost accounting:
        gross_pnl    = (exit_price - entry_price) × quantity  [for LONG]
                     = (entry_price - exit_price) × quantity  [for SHORT]
        net_pnl      = gross_pnl - fees - slippage_cost - spread_cost
        R_multiple   = net_pnl / risk_amount
                     (positive = winner, negative = loser, -1R = full stop hit)

    Fields:
        trade_id:               Unique identifier.
        asset:                  Trading symbol.
        side:                   Long or short.
        entry_fill:             Fill that opened the position.
        exit_fill:              Fill that closed the position.
        strategy_name:          Strategy that generated the trade.
        timeframe:              Timeframe of the strategy signal.
        run_id:                 Research run for traceability.
        initial_stop:           Stop-loss price at entry (for R-multiple).
        target_price:           Take-profit price.
        gross_pnl:              PnL before costs.
        fees:                   Total fees paid (entry + exit).
        slippage_cost:          Total slippage cost (entry + exit).
        spread_cost:            Total spread cost (entry + exit).
        net_pnl:                PnL after all costs.
        risk_amount:            Dollar risk at entry (qty × |entry - stop|).
        r_multiple:             net_pnl / risk_amount.
        exit_reason:            Why the trade was closed.
        holding_duration_seconds: Trade duration in seconds.
    """

    trade_id: str
    asset: str
    side: PositionSide
    entry_fill: Fill
    exit_fill: Fill
    strategy_name: str
    timeframe: Timeframe | None
    run_id: str
    exit_reason: str
    gross_pnl: float
    fees: float
    slippage_cost: float
    spread_cost: float
    net_pnl: float
    initial_stop: float | None = None
    target_price: float | None = None
    risk_amount: float | None = None
    r_multiple: float | None = None
    holding_duration_seconds: float | None = None

    # Deprecated: kept for backward compatibility with existing tests.
    # Use net_pnl instead.
    @property
    def realized_pnl(self) -> float:
        return self.net_pnl

    @property
    def duration(self):
        """Duration of the trade as a timedelta."""
        return self.exit_fill.timestamp - self.entry_fill.timestamp

    @property
    def is_winner(self) -> bool:
        return self.net_pnl > 0

    @classmethod
    def create(
        cls,
        asset: str,
        side: PositionSide,
        entry_fill: Fill,
        exit_fill: Fill,
        strategy_name: str,
        run_id: str,
        exit_reason: str,
        gross_pnl: float,
        fees: float,
        slippage_cost: float,
        spread_cost: float,
        net_pnl: float,
        timeframe: Timeframe | None = None,
        initial_stop: float | None = None,
        target_price: float | None = None,
        risk_amount: float | None = None,
        r_multiple: float | None = None,
        holding_duration_seconds: float | None = None,
    ) -> "Trade":
        """Factory method that auto-generates a unique trade_id."""
        if holding_duration_seconds is None:
            delta = exit_fill.timestamp - entry_fill.timestamp
            holding_duration_seconds = delta.total_seconds()
        return cls(
            trade_id=str(uuid.uuid4()),
            asset=asset,
            side=side,
            entry_fill=entry_fill,
            exit_fill=exit_fill,
            strategy_name=strategy_name,
            timeframe=timeframe,
            run_id=run_id,
            exit_reason=exit_reason,
            gross_pnl=gross_pnl,
            fees=fees,
            slippage_cost=slippage_cost,
            spread_cost=spread_cost,
            net_pnl=net_pnl,
            initial_stop=initial_stop,
            target_price=target_price,
            risk_amount=risk_amount,
            r_multiple=r_multiple,
            holding_duration_seconds=holding_duration_seconds,
        )


# ---------------------------------------------------------------------------
# Portfolio State (Prompt 03)
# ---------------------------------------------------------------------------


@dataclass
class PortfolioState:
    """
    A point-in-time snapshot of the portfolio accounting state.

    Definitions:
        cash:              Uninvested USDT (not used in any open position).
        equity:            cash + sum(unrealized_pnl of open positions).
        used_capital:      Sum of notional values of open positions.
        available_capital: cash - used_capital (capital free for new positions).
        gross_exposure:    sum(|notional|) — does not net longs vs shorts.
        net_exposure:      sum(notional × side_sign) — longs positive, shorts negative.
        realized_pnl:      Cumulative net PnL of all closed trades.
        unrealized_pnl:    Cumulative unrealized PnL of all open positions.
        total_fees:        Cumulative fees paid since run start.
        total_slippage:    Cumulative slippage cost since run start.
        total_spread_cost: Cumulative spread cost since run start.
        daily_pnl:         Net PnL since last UTC day boundary.
    """

    timestamp: datetime
    cash: float
    equity: float
    used_capital: float
    available_capital: float
    gross_exposure: float
    net_exposure: float
    realized_pnl: float
    unrealized_pnl: float
    total_fees: float
    total_slippage: float
    total_spread_cost: float
    daily_pnl: float = 0.0
    # Prompt 05 extensions
    daily_start_equity: float = 0.0
    daily_limit_state: str = "open"  # DailyLimitState value
    strategy_states: dict = field(default_factory=dict)   # instance_id → StrategyLifecycleState
    asset_exposures: dict = field(default_factory=dict)   # symbol → notional
    strategy_exposures: dict = field(default_factory=dict) # strategy_id → notional


@dataclass(frozen=True)
class EquityCurvePoint:
    """
    A single point on the equity curve.

    Drawdown is calculated as:
        drawdown = (equity - peak_equity_so_far) / peak_equity_so_far
    where peak_equity_so_far is the maximum equity observed up to this
    point in time — NEVER using future equity values.

    Fields:
        timestamp:      UTC time of this snapshot.
        cash:           Cash balance.
        equity:         Total portfolio equity.
        realized_pnl:   Cumulative realized PnL.
        unrealized_pnl: Cumulative unrealized PnL.
        gross_exposure: Sum of absolute notional values.
        net_exposure:   Net directional exposure.
        drawdown:       Current drawdown from historical peak (negative or zero).
    """

    timestamp: datetime
    cash: float
    equity: float
    realized_pnl: float
    unrealized_pnl: float
    gross_exposure: float
    net_exposure: float
    drawdown: float


@dataclass(frozen=True)
class ExecutionEvent:
    """
    A single entry in the execution audit ledger.

    Every significant engine event is recorded as an ExecutionEvent.
    This provides a complete, traceable history of the backtest simulation.

    Fields:
        event_id:       Unique identifier for this event.
        timestamp:      UTC simulation timestamp when the event occurred.
        event_type:     Type of event (see EventType enum).
        run_id:         Research run identifier.
        asset:          Asset involved (None for portfolio-level events).
        order_id:       Related order (if applicable).
        position_id:    Related position (if applicable).
        trade_id:       Related trade (if applicable).
        details:        Free-form dict with event-specific information.
    """

    event_id: str
    timestamp: datetime
    event_type: EventType
    run_id: str
    asset: str | None = None
    order_id: str | None = None
    position_id: str | None = None
    trade_id: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        timestamp: datetime,
        event_type: EventType,
        run_id: str,
        asset: str | None = None,
        order_id: str | None = None,
        position_id: str | None = None,
        trade_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> "ExecutionEvent":
        """Factory method that auto-generates a unique event_id."""
        return cls(
            event_id=str(uuid.uuid4()),
            timestamp=timestamp,
            event_type=event_type,
            run_id=run_id,
            asset=asset,
            order_id=order_id,
            position_id=position_id,
            trade_id=trade_id,
            details=details or {},
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

    Prompt 03 fields (unchanged, backward compatible):
        approved:           True if the trade is permitted.
        reason:             Explanation of the decision (always required).
        max_position_size:  Maximum allowed position size if approved.
        risk_amount:        Maximum capital at risk for this trade.

    Prompt 05 extensions (all optional, default None/[]):
        rejection_codes:    Ordered list of all rejection reasons (first = primary).
        score:              Opportunity score at decision time (None if scoring disabled).
        score_version:      Version of the scoring model used.
        approved_quantity:  Approved position quantity (may differ from max_position_size
                            if capital constraints were binding).
    """

    approved: bool
    reason: str
    max_position_size: float | None = None
    risk_amount: float | None = None
    # Prompt 05 extensions
    rejection_codes: list = field(default_factory=list)
    score: float | None = None
    score_version: str | None = None
    approved_quantity: float | None = None

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


# ---------------------------------------------------------------------------
# Prompt 04 — Strategy Library
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StrategyInfo:
    """
    Full metadata for a Prompt 04 strategy implementation.

    Extends StrategyMetadata with additional fields for the strategy library.
    StrategyMetadata is preserved unchanged for backward compatibility.

    Fields:
        strategy_id:          Unique identifier, e.g. "EMA_CROSS_001".
        name:                 Human-readable display name.
        version:              Semantic version string, e.g. "1.0.0".
        category:             Strategy family: trend, momentum, mean_reversion,
                              breakout, volatility, volume, multi_indicator,
                              market_structure.
        hypothesis:           Research hypothesis.
        description:          Implementation description.
        default_parameters:   Default parameter values (not claimed optimal).
        parameter_schema:     Parameter constraints map.
        supported_timeframes: Timeframe strings this strategy supports.
        supported_sides:      Signal direction strings (long/short/neutral).
        required_features:    OHLCV features required.
        warmup_period:        Minimum candles before signals are valid.
        is_event_based:       True = signals only on transitions (crossover).
                              False = signals based on current state.
        notes:                Optional research notes.
    """

    strategy_id: str
    name: str
    version: str
    category: str
    hypothesis: str
    description: str
    default_parameters: dict[str, Any] = field(default_factory=dict)
    parameter_schema: dict[str, dict[str, Any]] = field(default_factory=dict)
    supported_timeframes: list[str] = field(default_factory=list)
    supported_sides: list[str] = field(default_factory=list)
    required_features: list[str] = field(default_factory=list)
    warmup_period: int = 0
    is_event_based: bool = True
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.strategy_id:
            raise ValueError("strategy_id must not be empty")
        if not self.version:
            raise ValueError("version must not be empty")
        if self.warmup_period < 0:
            raise ValueError(f"warmup_period must be >= 0, got {self.warmup_period}")
        valid_categories = {
            "trend", "momentum", "mean_reversion", "breakout",
            "volatility", "volume", "multi_indicator", "market_structure",
        }
        if self.category not in valid_categories:
            raise ValueError(
                f"Invalid category '{self.category}'. "
                f"Must be one of: {sorted(valid_categories)}"
            )


# ---------------------------------------------------------------------------
# Prompt 05 — Portfolio & Risk Orchestration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StrategyState:
    """
    A point-in-time snapshot of a strategy instance's lifecycle state.

    Fields:
        timestamp:          UTC timestamp of the transition or snapshot.
        strategy_id:        ID of the strategy (e.g., 'EMA_CROSS_001').
        instance_id:        Unique ID of the strategy instance.
        state:              Current Lifecycle state (ACTIVE, PAUSED, DISABLED).
        reason:             Reason for current state (e.g., 'CONSECUTIVE_LOSS_LIMIT').
        consecutive_losses: Number of consecutive losses at this point in time.
        last_trade_result:  Result of the last evaluated trade (e.g., 'LOSS', 'WIN').
        cooldown_start:     UTC timestamp when cooldown started (if applicable).
        cooldown_until:     UTC timestamp when cooldown expires (if applicable).
    """

    timestamp: datetime
    strategy_id: str
    instance_id: str
    state: StrategyLifecycleState
    reason: str
    consecutive_losses: int = 0
    last_trade_result: str | None = None
    cooldown_start: datetime | None = None
    cooldown_until: datetime | None = None


@dataclass(frozen=True)
class OpportunityScore:
    """
    A computed opportunity score for a strategy signal.

    Fields:
        timestamp:          UTC timestamp of the score calculation.
        strategy_id:        ID of the strategy generating the signal.
        instance_id:        Unique ID of the strategy instance.
        symbol:             Asset symbol.
        timeframe:          Timeframe of the signal.
        score_version:      Version of the scoring model.
        total_score:        Final computed score [0.0 - 100.0].
        component_scores:   Individual score components.
        component_weights:  Weights applied to each component.
        raw_features:       Raw features used for scoring (auditability).
        threshold:          Configured minimum threshold for acceptance.
        decision:           ACCEPTED or REJECTED based purely on score.
    """

    timestamp: datetime
    strategy_id: str
    instance_id: str
    symbol: str
    timeframe: Timeframe
    score_version: str
    total_score: float
    component_scores: dict[str, float]
    component_weights: dict[str, float]
    raw_features: dict[str, Any]
    threshold: float
    decision: DecisionOutcome


@dataclass(frozen=True)
class RiskDecisionRecord:
    """
    A complete ledger record of a risk orchestration decision.

    Fields:
        timestamp:          UTC timestamp of the decision.
        run_id:             Research run ID.
        strategy_id:        Strategy ID.
        strategy_version:   Strategy version.
        instance_id:        Strategy instance ID.
        symbol:             Asset symbol.
        timeframe:          Timeframe of the signal.
        signal:             Signal direction (long/short).
        score:              Computed opportunity score (if enabled).
        score_version:      Version of the scoring model.
        risk_budget:        Calculated dollar risk budget.
        approved_quantity:  Approved position size (base asset).
        portfolio_equity:   Portfolio equity at decision time.
        daily_return_pct:   Portfolio daily return percentage at decision time.
        consecutive_losses: Strategy's current consecutive loss count.
        strategy_state:     Strategy's state at decision time.
        decision:           ACCEPTED or REJECTED.
        primary_reason:     Main reason for the decision.
        rejection_reasons:  List of all rejection reasons (if any).
    """

    timestamp: datetime
    run_id: str
    strategy_id: str
    strategy_version: str
    instance_id: str
    symbol: str
    timeframe: Timeframe
    signal: SignalDirection
    score: float | None
    score_version: str | None
    risk_budget: float | None
    approved_quantity: float | None
    portfolio_equity: float
    daily_return_pct: float
    consecutive_losses: int
    strategy_state: StrategyLifecycleState
    decision: DecisionOutcome
    primary_reason: str
    rejection_reasons: list[RejectionReason]
