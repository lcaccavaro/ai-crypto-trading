"""
Unit tests for core domain objects.

Tests:
    - Candle OHLC integrity validation.
    - Signal strength range validation.
    - Order validation (quantity, price requirements).
    - Fill validation (positive price, non-negative fees).
    - RiskDecision validation.
    - Timeframe enum parsing.
    - Domain object immutability (frozen dataclasses).
"""

from datetime import datetime, timezone

import pytest

from crypto_research.core.domain import (
    Candle,
    Fill,
    Order,
    OrderSide,
    OrderType,
    Position,
    PositionSide,
    RiskDecision,
    Signal,
    SignalDirection,
    StrategyMetadata,
    Timeframe,
    Trade,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

NOW = datetime(2026, 9, 15, 0, 0, 0, tzinfo=timezone.utc)


def make_candle(**overrides) -> Candle:
    defaults = dict(
        timestamp=NOW,
        asset="BTCUSDT",
        timeframe=Timeframe.M1,
        open=50000.0,
        high=50500.0,
        low=49500.0,
        close=50200.0,
        volume=100.0,
    )
    defaults.update(overrides)
    return Candle(**defaults)


def make_fill(**overrides) -> Fill:
    defaults = dict(
        fill_id="fill-001",
        order_id="order-001",
        timestamp=NOW,
        asset="BTCUSDT",
        side=OrderSide.BUY,
        fill_price=50000.0,
        quantity=0.1,
        fees=5.0,
    )
    defaults.update(overrides)
    return Fill(**defaults)


# ---------------------------------------------------------------------------
# Candle
# ---------------------------------------------------------------------------


class TestCandle:
    def test_valid_candle(self):
        candle = make_candle()
        assert candle.open == 50000.0
        assert candle.high == 50500.0

    def test_candle_is_frozen(self):
        candle = make_candle()
        with pytest.raises(Exception):  # FrozenInstanceError
            candle.close = 99999.0  # type: ignore[misc]

    def test_high_less_than_low_raises(self):
        with pytest.raises(ValueError, match="high"):
            make_candle(high=49000.0, low=50000.0)

    def test_high_less_than_open_raises(self):
        with pytest.raises(ValueError, match="high"):
            make_candle(open=51000.0, high=50000.0, low=49000.0)

    def test_low_greater_than_close_raises(self):
        with pytest.raises(ValueError, match="low"):
            make_candle(low=51000.0, close=50000.0)

    def test_negative_volume_raises(self):
        with pytest.raises(ValueError, match="volume"):
            make_candle(volume=-1.0)

    def test_equal_ohlc_valid(self):
        """A doji candle (open == high == low == close) must be valid."""
        candle = make_candle(open=50000.0, high=50000.0, low=50000.0, close=50000.0)
        assert candle.open == 50000.0


# ---------------------------------------------------------------------------
# Signal
# ---------------------------------------------------------------------------


class TestSignal:
    def test_valid_signal(self):
        signal = Signal(
            timestamp=NOW,
            strategy_name="test_strategy",
            asset="BTCUSDT",
            timeframe=Timeframe.M5,
            direction=SignalDirection.LONG,
            strength=0.8,
        )
        assert signal.direction == SignalDirection.LONG

    def test_strength_above_one_raises(self):
        with pytest.raises(ValueError, match="strength"):
            Signal(
                timestamp=NOW,
                strategy_name="s",
                asset="BTCUSDT",
                timeframe=Timeframe.M1,
                direction=SignalDirection.LONG,
                strength=1.1,
            )

    def test_strength_below_zero_raises(self):
        with pytest.raises(ValueError, match="strength"):
            Signal(
                timestamp=NOW,
                strategy_name="s",
                asset="BTCUSDT",
                timeframe=Timeframe.M1,
                direction=SignalDirection.LONG,
                strength=-0.1,
            )

    def test_signal_is_frozen(self):
        signal = Signal(
            timestamp=NOW,
            strategy_name="s",
            asset="BTCUSDT",
            timeframe=Timeframe.M1,
            direction=SignalDirection.LONG,
        )
        with pytest.raises(Exception):
            signal.direction = SignalDirection.SHORT  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Order
# ---------------------------------------------------------------------------


class TestOrder:
    def test_create_market_order(self):
        order = Order.create(
            timestamp=NOW,
            asset="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=0.1,
            strategy_name="test",
            run_id="RUN_001",
        )
        assert order.order_id is not None
        assert order.quantity == 0.1

    def test_zero_quantity_raises(self):
        with pytest.raises(ValueError, match="quantity"):
            Order.create(
                timestamp=NOW,
                asset="BTCUSDT",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=0.0,
                strategy_name="test",
                run_id="RUN_001",
            )

    def test_limit_order_without_price_raises(self):
        with pytest.raises(ValueError, match="price"):
            Order.create(
                timestamp=NOW,
                asset="BTCUSDT",
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                quantity=0.1,
                strategy_name="test",
                run_id="RUN_001",
                price=None,
            )

    def test_stop_order_without_stop_price_raises(self):
        with pytest.raises(ValueError, match="stop_price"):
            Order.create(
                timestamp=NOW,
                asset="BTCUSDT",
                side=OrderSide.SELL,
                order_type=OrderType.STOP_MARKET,
                quantity=0.1,
                strategy_name="test",
                run_id="RUN_001",
            )


# ---------------------------------------------------------------------------
# Fill
# ---------------------------------------------------------------------------


class TestFill:
    def test_valid_fill(self):
        fill = make_fill()
        assert fill.gross_value == 50000.0 * 0.1
        assert fill.net_value == fill.gross_value + fill.fees

    def test_zero_fill_price_raises(self):
        with pytest.raises(ValueError, match="price"):
            make_fill(fill_price=0.0)

    def test_negative_fees_raises(self):
        with pytest.raises(ValueError, match="fees"):
            make_fill(fees=-1.0)

    def test_zero_quantity_raises(self):
        with pytest.raises(ValueError, match="quantity"):
            make_fill(quantity=0.0)


# ---------------------------------------------------------------------------
# Position
# ---------------------------------------------------------------------------


class TestPosition:
    def test_position_unrealized_pnl_long(self):
        fill = make_fill(fill_price=50000.0, quantity=1.0)
        pos = Position.create(
            asset="BTCUSDT",
            side=PositionSide.LONG,
            entry_fill=fill,
            strategy_name="test",
            run_id="RUN_001",
        )
        pos.current_price = 51000.0
        assert pos.unrealized_pnl == pytest.approx(1000.0)

    def test_position_unrealized_pnl_short(self):
        fill = make_fill(fill_price=50000.0, quantity=1.0, side=OrderSide.SELL)
        pos = Position.create(
            asset="BTCUSDT",
            side=PositionSide.SHORT,
            entry_fill=fill,
            strategy_name="test",
            run_id="RUN_001",
        )
        pos.current_price = 49000.0
        assert pos.unrealized_pnl == pytest.approx(1000.0)

    def test_position_unrealized_pnl_none_when_no_price(self):
        fill = make_fill()
        pos = Position.create(
            asset="BTCUSDT",
            side=PositionSide.LONG,
            entry_fill=fill,
            strategy_name="test",
            run_id="RUN_001",
        )
        assert pos.unrealized_pnl is None


# ---------------------------------------------------------------------------
# RiskDecision
# ---------------------------------------------------------------------------


class TestRiskDecision:
    def test_approved_requires_max_position_size(self):
        with pytest.raises(ValueError, match="max_position_size"):
            RiskDecision(approved=True, reason="ok", max_position_size=None)

    def test_reason_required(self):
        with pytest.raises(ValueError, match="reason"):
            RiskDecision(approved=False, reason="")

    def test_rejected_without_size_is_valid(self):
        decision = RiskDecision(approved=False, reason="Daily loss limit reached")
        assert not decision.approved

    def test_approved_with_size_is_valid(self):
        decision = RiskDecision(
            approved=True, reason="All checks passed", max_position_size=0.1
        )
        assert decision.approved


# ---------------------------------------------------------------------------
# Timeframe
# ---------------------------------------------------------------------------


class TestTimeframe:
    def test_valid_timeframe_parsing(self):
        assert Timeframe.from_string("1m") == Timeframe.M1
        assert Timeframe.from_string("4h") == Timeframe.H4

    def test_invalid_timeframe_raises(self):
        with pytest.raises(ValueError, match="Unknown timeframe"):
            Timeframe.from_string("99x")

    def test_timeframe_string_value(self):
        assert Timeframe.M15.value == "15m"
        assert Timeframe.H1.value == "1h"
