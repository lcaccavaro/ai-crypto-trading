import pytest
from datetime import datetime, timedelta, timezone

from crypto_research.config.schema import StrategyManagementConfig, CooldownConfig
from crypto_research.core.domain import StrategyLifecycleState, Trade, Fill, PositionSide, Timeframe
from crypto_research.portfolio.strategy_state_machine import StrategyStateMachine

def make_trade(net_pnl: float, exit_time: datetime) -> Trade:
    fill = Fill(
        fill_id="f1",
        order_id="o1",
        timestamp=exit_time,
        asset="BTC",
        side=PositionSide.LONG,
        fill_price=100.0,
        quantity=1.0,
        fees=0.0
    )
    return Trade(
        trade_id="t1",
        asset="BTC",
        side=PositionSide.LONG,
        entry_fill=fill,  # Just mock it
        exit_fill=fill,
        strategy_name="S1",
        timeframe=None,
        run_id="run1",
        exit_reason="STOP",
        gross_pnl=net_pnl,
        fees=0.0,
        slippage_cost=0.0,
        spread_cost=0.0,
        net_pnl=net_pnl,
    )

def test_initial_state():
    cfg = StrategyManagementConfig(consecutive_loss_limit=3)
    sm = StrategyStateMachine("S1", "I1", cfg)
    assert sm.current_state == StrategyLifecycleState.ACTIVE
    assert sm.consecutive_losses == 0

def test_loss_accumulation_and_cooldown():
    cfg = StrategyManagementConfig(
        consecutive_loss_limit=3, 
        cooldown=CooldownConfig(enabled=True, value=4, unit="hours")
    )
    sm = StrategyStateMachine("S1", "I1", cfg)
    
    t0 = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)
    
    # Loss 1
    sm.update_from_trade(make_trade(-10.0, t0))
    assert sm.current_state == StrategyLifecycleState.ACTIVE
    assert sm.consecutive_losses == 1
    
    # Loss 2
    sm.update_from_trade(make_trade(-10.0, t0 + timedelta(hours=1)))
    assert sm.consecutive_losses == 2
    
    # Loss 3 -> PAUSED (Cooldown)
    t_loss3 = t0 + timedelta(hours=2)
    state_snap = sm.update_from_trade(make_trade(-10.0, t_loss3))
    assert sm.current_state == StrategyLifecycleState.PAUSED
    assert sm.consecutive_losses == 3
    assert state_snap is not None
    assert state_snap.state == StrategyLifecycleState.PAUSED
    assert state_snap.cooldown_until == t_loss3 + timedelta(hours=4)
    
    # Cooldown check early
    assert sm.check_cooldown(t_loss3 + timedelta(hours=2)) is None
    assert sm.current_state == StrategyLifecycleState.PAUSED
    
    # Cooldown check expired
    t_expired = t_loss3 + timedelta(hours=4, minutes=1)
    snap2 = sm.check_cooldown(t_expired)
    assert snap2 is not None
    assert sm.current_state == StrategyLifecycleState.ACTIVE
    assert sm.consecutive_losses == 0

def test_win_resets_losses():
    cfg = StrategyManagementConfig(consecutive_loss_limit=3)
    sm = StrategyStateMachine("S1", "I1", cfg)
    t0 = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)
    
    sm.update_from_trade(make_trade(-10.0, t0))
    assert sm.consecutive_losses == 1
    
    sm.update_from_trade(make_trade(5.0, t0 + timedelta(hours=1)))
    assert sm.consecutive_losses == 0

def test_pit_enforcement():
    cfg = StrategyManagementConfig()
    sm = StrategyStateMachine("S1", "I1", cfg)
    t0 = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)
    
    sm.update_from_trade(make_trade(-10.0, t0))
    
    with pytest.raises(ValueError, match="Out of order trade update"):
        sm.update_from_trade(make_trade(-10.0, t0 - timedelta(hours=1)))
