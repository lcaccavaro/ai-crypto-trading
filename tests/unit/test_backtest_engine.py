"""
Unit tests for backtest metrics computation.

Tests:
    - Win rate is correct.
    - Net PnL = sum(trade.net_pnl).
    - Max drawdown is non-positive and from equity curve.
    - Profit factor is correct.
    - R-multiple totals are correct.
    - Empty trade list returns zeros.
    - Total return percent is calculated correctly.
"""

from datetime import datetime, timezone

import pytest

from crypto_research.backtest.metrics import BacktestMetrics, compute_metrics
from crypto_research.core.domain import (
    EquityCurvePoint,
    ExitReason,
    Fill,
    OrderSide,
    PositionSide,
    Trade,
)


def make_trade(net_pnl: float, gross_pnl: float = None, fees: float = 0.0,
               r_multiple: float = None, duration: float = 900.0) -> Trade:
    ts = datetime(2026, 8, 1, 10, 0, tzinfo=timezone.utc)
    entry = Fill.create("ord-1", ts, "BTCUSDT", OrderSide.BUY, 50_000.0, 0.001, 0.0)
    exit_ts = datetime(2026, 8, 1, 10, 15, tzinfo=timezone.utc)
    exit_f = Fill.create("ord-2", exit_ts, "BTCUSDT", OrderSide.SELL, 50_000.0, 0.001, 0.0)

    if gross_pnl is None:
        gross_pnl = net_pnl + fees

    return Trade.create(
        asset="BTCUSDT",
        side=PositionSide.LONG,
        entry_fill=entry,
        exit_fill=exit_f,
        strategy_name="test",
        run_id="run1",
        exit_reason=ExitReason.TARGET.value,
        gross_pnl=gross_pnl,
        fees=fees,
        slippage_cost=0.0,
        spread_cost=0.0,
        net_pnl=net_pnl,
        r_multiple=r_multiple,
        holding_duration_seconds=duration,
    )


def make_equity_point(ts, equity, cash=None, drawdown=0.0):
    return EquityCurvePoint(
        timestamp=ts,
        cash=cash or equity,
        equity=equity,
        realized_pnl=0.0,
        unrealized_pnl=0.0,
        gross_exposure=0.0,
        net_exposure=0.0,
        drawdown=drawdown,
    )


class TestEmptyTrades:
    def test_no_trades_zeros(self):
        m = compute_metrics([], [], 10_000.0)
        assert m.total_trades == 0
        assert m.win_rate == pytest.approx(0.0)
        assert m.net_pnl == pytest.approx(0.0)
        assert m.total_R is None

    def test_initial_balance_returned(self):
        m = compute_metrics([], [], 10_000.0)
        assert m.initial_balance == pytest.approx(10_000.0)
        assert m.final_equity == pytest.approx(10_000.0)  # no equity curve → same as balance


class TestWinRate:
    def test_all_winners(self):
        trades = [make_trade(100.0), make_trade(50.0), make_trade(200.0)]
        m = compute_metrics(trades, [], 10_000.0)
        assert m.win_rate == pytest.approx(1.0)
        assert m.winning_trades == 3
        assert m.losing_trades == 0

    def test_all_losers(self):
        trades = [make_trade(-100.0), make_trade(-50.0)]
        m = compute_metrics(trades, [], 10_000.0)
        assert m.win_rate == pytest.approx(0.0)
        assert m.winning_trades == 0

    def test_mixed(self):
        trades = [make_trade(100.0), make_trade(-50.0), make_trade(200.0), make_trade(-75.0)]
        m = compute_metrics(trades, [], 10_000.0)
        assert m.win_rate == pytest.approx(0.5)


class TestNetPnL:
    def test_net_pnl_sum(self):
        trades = [make_trade(100.0), make_trade(-30.0), make_trade(50.0)]
        m = compute_metrics(trades, [], 10_000.0)
        assert m.net_pnl == pytest.approx(120.0)

    def test_fees_tracked(self):
        trades = [make_trade(100.0, fees=5.0), make_trade(50.0, fees=2.5)]
        m = compute_metrics(trades, [], 10_000.0)
        assert m.total_fees == pytest.approx(7.5)


class TestDrawdown:
    def test_max_drawdown_from_equity_curve(self):
        ts = datetime(2026, 8, 1, 0, 0, tzinfo=timezone.utc)
        curve = [
            make_equity_point(ts, 10_000.0, drawdown=0.0),
            make_equity_point(ts, 10_500.0, drawdown=0.0),
            make_equity_point(ts, 9_500.0, drawdown=-0.0952),  # ~-9.5%
        ]
        m = compute_metrics([], curve, 10_000.0)
        assert m.max_drawdown == pytest.approx(-0.0952)
        assert m.max_drawdown < 0

    def test_no_equity_curve_zero_drawdown(self):
        m = compute_metrics([], [], 10_000.0)
        assert m.max_drawdown == pytest.approx(0.0)


class TestProfitFactor:
    def test_profit_factor_correct(self):
        trades = [make_trade(300.0), make_trade(-100.0)]
        m = compute_metrics(trades, [], 10_000.0)
        assert m.profit_factor == pytest.approx(3.0)

    def test_all_winners_infinite(self):
        trades = [make_trade(100.0), make_trade(200.0)]
        m = compute_metrics(trades, [], 10_000.0)
        assert m.profit_factor == float("inf")

    def test_all_losers_zero(self):
        trades = [make_trade(-100.0), make_trade(-200.0)]
        m = compute_metrics(trades, [], 10_000.0)
        assert m.profit_factor == pytest.approx(0.0) or m.profit_factor is None


class TestRMultiple:
    def test_total_R_sum(self):
        trades = [make_trade(100.0, r_multiple=1.5), make_trade(-50.0, r_multiple=-0.5)]
        m = compute_metrics(trades, [], 10_000.0)
        assert m.total_R == pytest.approx(1.0)
        assert m.average_R == pytest.approx(0.5)

    def test_no_r_multiple_returns_none(self):
        trades = [make_trade(100.0)]  # r_multiple=None
        m = compute_metrics(trades, [], 10_000.0)
        assert m.total_R is None
        assert m.average_R is None


class TestTotalReturn:
    def test_total_return_from_equity_curve(self):
        ts = datetime(2026, 8, 1, 0, 0, tzinfo=timezone.utc)
        curve = [make_equity_point(ts, 11_000.0)]
        m = compute_metrics([], curve, 10_000.0)
        assert m.total_return_pct == pytest.approx(10.0)

    def test_negative_return(self):
        ts = datetime(2026, 8, 1, 0, 0, tzinfo=timezone.utc)
        curve = [make_equity_point(ts, 9_500.0)]
        m = compute_metrics([], curve, 10_000.0)
        assert m.total_return_pct == pytest.approx(-5.0)
