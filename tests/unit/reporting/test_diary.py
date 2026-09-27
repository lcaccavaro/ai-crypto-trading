"""Unit tests for Trade Diary."""
from datetime import datetime, timezone
import pytest

from crypto_research.core.domain import Trade, Fill, PositionSide, Signal, SignalDirection, Timeframe, RiskDecisionRecord, DecisionOutcome, StrategyLifecycleState
from crypto_research.reporting.diary import TradeDiaryBuilder
from crypto_research.reporting.models import DecisionQuality

def test_trade_diary_valid_decision():
    builder = TradeDiaryBuilder("run_1")
    
    t0 = datetime(2026, 1, 1, 10, tzinfo=timezone.utc)
    t1 = datetime(2026, 1, 1, 11, tzinfo=timezone.utc)
    
    entry = Fill("f1", "o1", t0, "BTC", PositionSide.LONG, 10000.0, 1.0, 5.0)
    exit = Fill("f2", "o2", t1, "BTC", PositionSide.LONG, 11000.0, 1.0, 5.5)
    trade = Trade(
        trade_id="t1", run_id="r1", asset="BTC", side=PositionSide.LONG, timeframe=Timeframe.M15,
        strategy_name="test", entry_fill=entry, exit_fill=exit, exit_reason="TARGET",
        gross_pnl=1000.0, fees=10.5, spread_cost=0.0, slippage_cost=0.0, net_pnl=989.5
    )
    
    sig = Signal(timestamp=t0, asset="BTC", timeframe=Timeframe.M15, direction=SignalDirection.LONG, strategy_name="test", stop_price=9500.0, target_price=11000.0)
    risk = RiskDecisionRecord(
        timestamp=t0, run_id="r1", strategy_id="test", strategy_version="1.0",
        instance_id="inst1", symbol="BTC", timeframe="15m", signal="LONG",
        score=80.0, score_version="1", decision=DecisionOutcome.ACCEPTED,
        strategy_state=StrategyLifecycleState.ACTIVE, risk_budget=100.0,
        approved_quantity=1.0, portfolio_equity=10000.0, daily_return_pct=0.0,
        consecutive_losses=0, primary_reason="", rejection_reasons=[]
    )
    
    rec = builder.build_record(trade, sig, risk)
    
    assert rec.trade_id == "t1"
    assert rec.decision_quality == DecisionQuality.VALID_DECISION
    assert rec.stop_hit is False
    assert rec.target_hit is True
    assert rec.realized_R == 9.895 # 989.5 / 100
    assert "Risk manager approved" in rec.decision_explanation

def test_trade_diary_missing_audit():
    builder = TradeDiaryBuilder("run_1")
    
    t0 = datetime(2026, 1, 1, 10, tzinfo=timezone.utc)
    entry = Fill("f1", "o1", t0, "BTC", PositionSide.LONG, 10000.0, 1.0, 0.0)
    trade = Trade(
        trade_id="t1", run_id="r1", asset="BTC", side=PositionSide.LONG, timeframe=Timeframe.M15,
        strategy_name="test", entry_fill=entry, exit_fill=entry, exit_reason="STOP",
        gross_pnl=-500.0, fees=0, spread_cost=0.0, slippage_cost=0.0, net_pnl=-500.0
    )
    
    rec = builder.build_record(trade)
    assert rec.decision_quality == DecisionQuality.INCOMPLETE_AUDIT
