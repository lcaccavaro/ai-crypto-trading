"""
Unit tests for the risk gate (pre-entry portfolio checks).

Tests:
    - Max concurrent positions rejection.
    - Max total exposure rejection.
    - Max asset exposure rejection.
    - Daily profit target reached — new positions blocked.
    - Daily loss limit exceeded — new positions blocked.
    - Insufficient capital rejection.
    - Short not allowed rejection (Prompt 03).
    - All checks pass → approved.
"""

from datetime import datetime, timezone

import pytest

from crypto_research.backtest.risk_gate import RiskGate
from crypto_research.core.domain import (
    PortfolioState,
    PositionSide,
    RejectionReason,
)


def make_config(
    max_concurrent=5,
    max_total_exposure=50.0,
    max_asset_exposure=20.0,
    daily_profit_target=2.0,
    daily_loss_limit=3.0,
    risk_per_trade=1.0,
    rr=3.0,
):
    class Cfg:
        max_concurrent_positions = max_concurrent
        max_total_exposure_pct = max_total_exposure
        max_asset_exposure_pct = max_asset_exposure
        daily_profit_target_pct = daily_profit_target
        daily_loss_limit_pct = daily_loss_limit
        risk_per_trade_pct = risk_per_trade
        risk_reward_ratio = rr

    return Cfg()


def make_portfolio_state(
    equity=10_000.0,
    cash=10_000.0,
    gross_exposure=0.0,
    net_exposure=0.0,
    daily_pnl=0.0,
    available_capital=10_000.0,
):
    return PortfolioState(
        timestamp=datetime(2026, 8, 1, 10, tzinfo=timezone.utc),
        cash=cash,
        equity=equity,
        used_capital=gross_exposure,
        available_capital=available_capital,
        gross_exposure=gross_exposure,
        net_exposure=net_exposure,
        realized_pnl=0.0,
        unrealized_pnl=0.0,
        total_fees=0.0,
        total_slippage=0.0,
        total_spread_cost=0.0,
        daily_pnl=daily_pnl,
    )


@pytest.fixture
def gate():
    return RiskGate(make_config(), allow_short=False)


class TestAllChecksPass:
    def test_all_pass_returns_approved(self, gate):
        state = make_portfolio_state()
        approved, reason = gate.check_all(
            side=PositionSide.LONG,
            portfolio_state=state,
            symbol="BTCUSDT",
            entry_price=50_000.0,
            quantity=0.001,
            open_position_count=0,
            asset_notional=0.0,
        )
        assert approved is True
        assert reason is None


class TestShortNotAllowed:
    def test_short_rejected_when_not_allowed(self, gate):
        state = make_portfolio_state()
        approved, reason = gate.check_all(
            side=PositionSide.SHORT,
            portfolio_state=state,
            symbol="BTCUSDT",
            entry_price=50_000.0,
            quantity=0.001,
            open_position_count=0,
            asset_notional=0.0,
        )
        assert approved is False
        assert reason == RejectionReason.SHORT_NOT_ALLOWED

    def test_short_allowed_when_configured(self):
        gate_with_short = RiskGate(make_config(), allow_short=True)
        state = make_portfolio_state()
        approved, reason = gate_with_short.check_all(
            side=PositionSide.SHORT,
            portfolio_state=state,
            symbol="BTCUSDT",
            entry_price=50_000.0,
            quantity=0.001,
            open_position_count=0,
            asset_notional=0.0,
        )
        assert approved is True


class TestMaxConcurrentPositions:
    def test_at_limit_rejected(self):
        gate = RiskGate(make_config(max_concurrent=3), allow_short=False)
        state = make_portfolio_state()
        approved, reason = gate.check_all(
            side=PositionSide.LONG,
            portfolio_state=state,
            symbol="BTCUSDT",
            entry_price=50_000.0,
            quantity=0.001,
            open_position_count=3,  # already at limit
            asset_notional=0.0,
        )
        assert approved is False
        assert reason == RejectionReason.MAX_CONCURRENT_POSITIONS

    def test_under_limit_approved(self):
        gate = RiskGate(make_config(max_concurrent=3), allow_short=False)
        state = make_portfolio_state()
        approved, _ = gate.check_all(
            side=PositionSide.LONG,
            portfolio_state=state,
            symbol="BTCUSDT",
            entry_price=50_000.0,
            quantity=0.001,
            open_position_count=2,
            asset_notional=0.0,
        )
        assert approved is True


class TestMaxTotalExposure:
    def test_exceeds_limit_rejected(self):
        # equity=10,000, max_total=50% → limit is 5,000 notional
        # current_gross=4,900 + new notional 200 = 5,100 → 51% > 50% → reject
        gate = RiskGate(make_config(max_total_exposure=50.0), allow_short=False)
        state = make_portfolio_state(equity=10_000.0, gross_exposure=4_900.0, available_capital=10_000.0)
        approved, reason = gate.check_all(
            side=PositionSide.LONG,
            portfolio_state=state,
            symbol="BTCUSDT",
            entry_price=200.0,
            quantity=1.0,
            open_position_count=1,
            asset_notional=0.0,
        )
        assert approved is False
        assert reason == RejectionReason.MAX_TOTAL_EXPOSURE


class TestMaxAssetExposure:
    def test_exceeds_asset_limit_rejected(self):
        # equity=10,000, max_asset=20% → limit is 2,000 notional per asset
        # current_asset_notional=1,900 + new 200 = 2,100 → 21% > 20% → reject
        gate = RiskGate(make_config(max_asset_exposure=20.0), allow_short=False)
        state = make_portfolio_state(equity=10_000.0, available_capital=10_000.0)
        approved, reason = gate.check_all(
            side=PositionSide.LONG,
            portfolio_state=state,
            symbol="BTCUSDT",
            entry_price=200.0,
            quantity=1.0,
            open_position_count=0,
            asset_notional=1_900.0,  # already 19% in BTCUSDT
        )
        assert approved is False
        assert reason == RejectionReason.MAX_ASSET_EXPOSURE


class TestDailyProfitTarget:
    def test_profit_target_reached_rejects(self):
        # daily_pnl = 250 on equity 10,000 = 2.5% > 2.0% target → reject
        gate = RiskGate(make_config(daily_profit_target=2.0), allow_short=False)
        state = make_portfolio_state(equity=10_000.0, daily_pnl=250.0, available_capital=10_000.0)
        approved, reason = gate.check_all(
            side=PositionSide.LONG,
            portfolio_state=state,
            symbol="BTCUSDT",
            entry_price=50_000.0,
            quantity=0.001,
            open_position_count=0,
            asset_notional=0.0,
        )
        assert approved is False
        assert reason == RejectionReason.DAILY_PROFIT_TARGET_REACHED

    def test_below_profit_target_approved(self, gate):
        state = make_portfolio_state(equity=10_000.0, daily_pnl=10.0, available_capital=10_000.0)
        approved, _ = gate.check_all(
            side=PositionSide.LONG,
            portfolio_state=state,
            symbol="BTCUSDT",
            entry_price=50_000.0,
            quantity=0.001,
            open_position_count=0,
            asset_notional=0.0,
        )
        assert approved is True


class TestDailyLossLimit:
    def test_loss_limit_exceeded_rejects(self):
        # daily_pnl = -350 on equity 10,000 = -3.5% < -3.0% limit → reject
        gate = RiskGate(make_config(daily_loss_limit=3.0), allow_short=False)
        state = make_portfolio_state(equity=10_000.0, daily_pnl=-350.0, available_capital=10_000.0)
        approved, reason = gate.check_all(
            side=PositionSide.LONG,
            portfolio_state=state,
            symbol="BTCUSDT",
            entry_price=50_000.0,
            quantity=0.001,
            open_position_count=0,
            asset_notional=0.0,
        )
        assert approved is False
        assert reason == RejectionReason.DAILY_LOSS_LIMIT_REACHED


class TestAvailableCapital:
    def test_insufficient_capital_rejects(self, gate):
        # entry costs $500, only $100 available
        state = make_portfolio_state(equity=10_000.0, available_capital=100.0)
        approved, reason = gate.check_all(
            side=PositionSide.LONG,
            portfolio_state=state,
            symbol="BTCUSDT",
            entry_price=50_000.0,
            quantity=0.01,  # = $500 notional
            open_position_count=0,
            asset_notional=0.0,
        )
        assert approved is False
        assert reason == RejectionReason.INSUFFICIENT_CAPITAL
