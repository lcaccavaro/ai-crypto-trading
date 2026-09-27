import pytest
from datetime import datetime, timezone
from pathlib import Path

from crypto_research.core.domain import (
    RiskDecisionRecord, Timeframe, SignalDirection, StrategyLifecycleState, DecisionOutcome
)
from crypto_research.portfolio.decision_ledger import DecisionLedger
from crypto_research.portfolio.strategy_state_ledger import StrategyStateLedger
from crypto_research.core.domain import StrategyState

def test_decision_ledger(tmp_path):
    ledger = DecisionLedger("run1")
    
    rec = RiskDecisionRecord(
        timestamp=datetime.now(timezone.utc),
        run_id="run1",
        strategy_id="strat1",
        strategy_version="1.0",
        instance_id="inst1",
        symbol="BTCUSDT",
        timeframe=Timeframe.M15,
        signal=SignalDirection.LONG,
        score=95.0,
        score_version="1.0",
        risk_budget=100.0,
        approved_quantity=0.1,
        portfolio_equity=10000.0,
        daily_return_pct=1.5,
        consecutive_losses=0,
        strategy_state=StrategyLifecycleState.ACTIVE,
        decision=DecisionOutcome.ACCEPTED,
        primary_reason="ALL_CHECKS_PASSED",
        rejection_reasons=[]
    )
    
    ledger.record(rec)
    assert len(ledger) == 1
    
    csv_path = tmp_path / "decisions.csv"
    ledger.to_csv(csv_path)
    
    content = csv_path.read_text()
    assert "strat1" in content
    assert "100.0" in content

def test_strategy_state_ledger(tmp_path):
    ledger = StrategyStateLedger("run1")
    
    rec = StrategyState(
        timestamp=datetime.now(timezone.utc),
        strategy_id="strat1",
        instance_id="inst1",
        state=StrategyLifecycleState.PAUSED,
        reason="LOSS_LIMIT",
        consecutive_losses=3
    )
    
    ledger.record(rec)
    assert len(ledger) == 1
    
    csv_path = tmp_path / "states.csv"
    ledger.to_csv(csv_path)
    
    content = csv_path.read_text()
    assert "strat1" in content
    assert "LOSS_LIMIT" in content
