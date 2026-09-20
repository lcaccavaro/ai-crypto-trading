"""
Unit tests for position sizing.

Tests:
    - Risk-based sizing produces correct quantity.
    - Fixed sizing returns the fixed quantity.
    - Risk-based rejects when notional > available capital.
    - Fixed rejects when notional > available capital.
    - Zero stop distance raises ExecutionError.
    - Risk amount is correctly computed.
    - R-multiple is correctly computed.
"""

import pytest

from crypto_research.backtest.position_sizer import PositionSizer
from crypto_research.core.exceptions import ExecutionError


@pytest.fixture
def sizer():
    return PositionSizer()


class TestRiskBasedSizing:
    def test_correct_quantity(self, sizer):
        """qty = (equity * risk_pct / 100) / stop_distance"""
        equity = 10_000.0
        risk_pct = 1.0
        entry = 50_000.0
        stop = 49_000.0
        available = 10_000.0

        qty = sizer.size_risk_based(equity, risk_pct, entry, stop, available)

        risk_budget = equity * risk_pct / 100   # = 100
        stop_distance = abs(entry - stop)        # = 1000
        expected_qty = risk_budget / stop_distance  # = 0.1
        assert qty == pytest.approx(expected_qty)

    def test_notional_within_available_capital(self, sizer):
        """Sized position notional must be <= available capital."""
        qty = sizer.size_risk_based(
            equity=10_000.0,
            risk_per_trade_pct=1.0,
            entry_price=50_000.0,
            stop_price=49_000.0,
            available_capital=10_000.0,
        )
        notional = qty * 50_000.0
        assert notional <= 10_000.0

    def test_insufficient_capital_raises(self, sizer):
        """When notional > available_capital, must raise ExecutionError."""
        with pytest.raises(ExecutionError, match="INSUFFICIENT_CAPITAL"):
            sizer.size_risk_based(
                equity=10_000.0,
                risk_per_trade_pct=100.0,  # huge risk = huge size
                entry_price=50_000.0,
                stop_price=49_000.0,
                available_capital=100.0,   # tiny capital
            )

    def test_zero_stop_distance_raises(self, sizer):
        """Stop == entry → zero distance → undefined sizing."""
        with pytest.raises(ExecutionError, match="distance"):
            sizer.size_risk_based(
                equity=10_000.0,
                risk_per_trade_pct=1.0,
                entry_price=50_000.0,
                stop_price=50_000.0,  # same as entry!
                available_capital=10_000.0,
            )

    def test_tight_stop_larger_size(self, sizer):
        """Tighter stop → larger position size (same risk budget)."""
        available = 50_000.0
        qty_wide = sizer.size_risk_based(10_000, 1.0, 50_000, 49_000, available)  # 1000 distance
        qty_tight = sizer.size_risk_based(10_000, 1.0, 50_000, 49_500, available)  # 500 distance
        assert qty_tight > qty_wide

    def test_negative_equity_raises(self, sizer):
        with pytest.raises(ExecutionError):
            sizer.size_risk_based(-1000, 1.0, 50_000, 49_000, 10_000)


class TestFixedSizing:
    def test_returns_fixed_quantity(self, sizer):
        qty = sizer.size_fixed(0.01, 50_000.0, 10_000.0)
        assert qty == pytest.approx(0.01)

    def test_insufficient_capital_raises(self, sizer):
        with pytest.raises(ExecutionError, match="INSUFFICIENT_CAPITAL"):
            sizer.size_fixed(
                fixed_quantity=1.0,       # 1 BTC
                entry_price=50_000.0,     # = $50,000 notional
                available_capital=100.0,  # only $100 available
            )

    def test_zero_quantity_raises(self, sizer):
        with pytest.raises(ExecutionError):
            sizer.size_fixed(0.0, 50_000.0, 10_000.0)

    def test_negative_quantity_raises(self, sizer):
        with pytest.raises(ExecutionError):
            sizer.size_fixed(-0.01, 50_000.0, 10_000.0)


class TestRiskAmount:
    def test_risk_amount_correct(self, sizer):
        """risk_amount = qty * |entry - stop|"""
        qty = 0.1
        entry = 50_000.0
        stop = 49_000.0
        risk = sizer.compute_risk_amount(qty, entry, stop)
        assert risk == pytest.approx(0.1 * 1000.0)

    def test_risk_amount_same_stop_above(self, sizer):
        """Risk amount is always positive regardless of stop direction."""
        risk = sizer.compute_risk_amount(0.1, 50_000.0, 51_000.0)
        assert risk == pytest.approx(100.0)


class TestRMultiple:
    def test_full_stop_is_negative_1R(self, sizer):
        """If the trade loses exactly risk_amount, R = -1."""
        risk_amount = 100.0
        r = sizer.compute_r_multiple(-100.0, risk_amount)
        assert r == pytest.approx(-1.0)

    def test_3x_winner_is_plus_3R(self, sizer):
        risk_amount = 100.0
        r = sizer.compute_r_multiple(300.0, risk_amount)
        assert r == pytest.approx(3.0)

    def test_breakeven_is_zero_R(self, sizer):
        r = sizer.compute_r_multiple(0.0, 100.0)
        assert r == pytest.approx(0.0)

    def test_zero_risk_amount_raises(self, sizer):
        with pytest.raises(ExecutionError, match="risk_amount"):
            sizer.compute_r_multiple(100.0, 0.0)
