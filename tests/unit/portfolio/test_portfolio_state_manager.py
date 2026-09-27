import pytest
from datetime import datetime, timezone, timedelta

from crypto_research.config.schema import RiskConfig, StrategyManagementConfig, OpportunityScoreConfig
from crypto_research.core.domain import DailyLimitState, PortfolioState, Position, PositionSide, Fill
from crypto_research.portfolio.portfolio_state_manager import PortfolioStateManager
from crypto_research.backtest.portfolio_accountant import PortfolioAccountant

@pytest.fixture
def risk_cfg():
    return RiskConfig(
        risk_reward_ratio=3.0,
        risk_per_trade_pct=1.0,
        max_concurrent_positions=5,
        max_total_exposure_pct=50.0,
        max_asset_exposure_pct=20.0,
        max_strategy_exposure_pct=15.0,
        daily_profit_target_pct=2.0,
        daily_loss_limit_pct=3.0,
        strategy_management=StrategyManagementConfig(),
        opportunity_score=OpportunityScoreConfig(components={})
    )

def test_portfolio_state_manager_daily_reset(risk_cfg):
    accountant = PortfolioAccountant(10000.0)
    manager = PortfolioStateManager(accountant, risk_cfg)
    
    t0 = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)
    state = manager.update_from_positions(t0, [])
    assert state.daily_start_equity == 10000.0
    assert state.daily_limit_state == DailyLimitState.OPEN.value
    
    # Simulate some PnL but no reset yet
    t1 = datetime(2026, 1, 1, 23, tzinfo=timezone.utc)
    # Inject fake unrealized PnL via accountant
    # Actually accountant relies on positions passed in
    fill = Fill("f1", "o1", t0, "BTC", PositionSide.LONG, 100.0, 1.0, 0.0)
    pos = Position("p1", "BTC", PositionSide.LONG, fill, "S1", "run1")
    pos.current_price = 400.0 # 300 PnL
    accountant.on_entry_fill(fill, pos)
    accountant.get_unrealized_pnl({"BTC": 400.0})
    
    state1 = manager.update_from_positions(t1, [pos])
    assert state1.equity == 10200.0
    assert state1.daily_start_equity == 10000.0
    assert state1.daily_limit_state == DailyLimitState.PROFIT_TARGET_REACHED.value # 500 / 10000 = 5% > 2% target
    
    # Next day -> reset
    t2 = datetime(2026, 1, 2, 1, tzinfo=timezone.utc)
    state2 = manager.update_from_positions(t2, [pos])
    assert state2.daily_start_equity == 10200.0
    assert state2.daily_limit_state == DailyLimitState.OPEN.value
    assert state2.daily_pnl == 0.0
