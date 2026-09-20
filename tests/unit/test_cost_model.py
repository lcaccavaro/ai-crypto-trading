"""
Unit tests for the cost model.

Tests:
    - Execution price is adverse to the trader (buy: higher, sell: lower).
    - Fee calculation is correct.
    - Slippage and spread costs are tracked separately.
    - Zero slippage/spread returns mid price.
    - compute_entry_costs() totals are self-consistent.
    - Gross PnL != Net PnL when costs are applied.
"""

import pytest

from crypto_research.backtest.cost_model import CostModel
from crypto_research.core.domain import OrderSide


@pytest.fixture
def cost_model():
    return CostModel(
        slippage_bps=2.0,
        spread_bps=1.0,
        taker_fee_rate=0.0005,
        maker_fee_rate=0.0002,
    )


@pytest.fixture
def zero_cost_model():
    return CostModel(
        slippage_bps=0.0,
        spread_bps=0.0,
        taker_fee_rate=0.0,
        maker_fee_rate=0.0,
    )


class TestExecutionPrice:
    def test_buy_execution_price_above_mid(self, cost_model):
        price = cost_model.calculate_execution_price(50_000.0, OrderSide.BUY)
        assert price > 50_000.0, "BUY execution price must be above mid (adverse)"

    def test_sell_execution_price_below_mid(self, cost_model):
        price = cost_model.calculate_execution_price(50_000.0, OrderSide.SELL)
        assert price < 50_000.0, "SELL execution price must be below mid (adverse)"

    def test_zero_cost_buy_equals_mid(self, zero_cost_model):
        price = zero_cost_model.calculate_execution_price(50_000.0, OrderSide.BUY)
        assert price == pytest.approx(50_000.0)

    def test_zero_cost_sell_equals_mid(self, zero_cost_model):
        price = zero_cost_model.calculate_execution_price(50_000.0, OrderSide.SELL)
        assert price == pytest.approx(50_000.0)

    def test_buy_sell_are_symmetric_cost(self, cost_model):
        """Buyer and seller pay the same cost amount (half-spread + slippage each)."""
        mid = 100.0
        buy_price = cost_model.calculate_execution_price(mid, OrderSide.BUY)
        sell_price = cost_model.calculate_execution_price(mid, OrderSide.SELL)
        # Both prices are equally far from mid
        assert abs(buy_price - mid) == pytest.approx(abs(sell_price - mid))


class TestSlippageAndSpread:
    def test_slippage_amount_correct(self, cost_model):
        slippage = cost_model.calculate_slippage_amount(50_000.0, 0.001)
        expected = 50_000.0 * (2.0 / 10_000) * 0.001
        assert slippage == pytest.approx(expected)

    def test_spread_cost_correct(self, cost_model):
        spread = cost_model.calculate_spread_cost(50_000.0, 0.001)
        # half-spread = price * spread_bps / 10_000 / 2
        expected = 50_000.0 * (1.0 / 10_000) / 2 * 0.001
        assert spread == pytest.approx(expected)

    def test_costs_tracked_separately(self, cost_model):
        """Slippage and spread are distinct cost components."""
        slippage = cost_model.calculate_slippage_amount(50_000.0, 1.0)
        spread = cost_model.calculate_spread_cost(50_000.0, 1.0)
        # They should not be equal unless slippage_bps == spread_bps/2
        assert slippage != spread


class TestFee:
    def test_taker_fee_correct(self, cost_model):
        fee = cost_model.calculate_fee(50_000.0, 1.0, is_maker=False)
        expected = 50_000.0 * 1.0 * 0.0005
        assert fee == pytest.approx(expected)

    def test_maker_fee_lower_than_taker(self, cost_model):
        taker_fee = cost_model.calculate_fee(50_000.0, 1.0, is_maker=False)
        maker_fee = cost_model.calculate_fee(50_000.0, 1.0, is_maker=True)
        assert maker_fee < taker_fee

    def test_zero_fee_returns_zero(self, zero_cost_model):
        fee = zero_cost_model.calculate_fee(50_000.0, 1.0)
        assert fee == pytest.approx(0.0)


class TestComputeEntryCosts:
    def test_returns_four_values(self, cost_model):
        result = cost_model.compute_entry_costs(50_000.0, 1.0, OrderSide.BUY)
        assert len(result) == 4

    def test_execution_price_is_first(self, cost_model):
        exec_price, fee, slippage, spread = cost_model.compute_entry_costs(
            50_000.0, 1.0, OrderSide.BUY
        )
        assert exec_price > 50_000.0

    def test_fee_computed_on_execution_price_not_mid(self, cost_model):
        """Fee must be computed on execution_price, not mid_price."""
        exec_price, fee, slippage, spread = cost_model.compute_entry_costs(
            50_000.0, 1.0, OrderSide.BUY
        )
        expected_fee = exec_price * 1.0 * 0.0005
        assert fee == pytest.approx(expected_fee)

    def test_gross_ne_net_with_costs(self, cost_model):
        """Gross PnL != Net PnL when costs exist."""
        exec_price, fee, slippage, spread = cost_model.compute_entry_costs(
            50_000.0, 0.001, OrderSide.BUY
        )
        total_cost = fee + slippage + spread
        assert total_cost > 0, "Total cost must be positive with non-zero cost model"


class TestFromConfig:
    def test_from_config_constructs_correctly(self):
        class FakeExec:
            slippage_bps = 3.0
            spread_bps = 2.0

        class FakeCosts:
            taker_fee_rate = 0.0005
            maker_fee_rate = 0.0002

        model = CostModel.from_config(FakeExec(), FakeCosts())
        assert model.slippage_bps == 3.0
        assert model.spread_bps == 2.0
        assert model.taker_fee_rate == 0.0005
