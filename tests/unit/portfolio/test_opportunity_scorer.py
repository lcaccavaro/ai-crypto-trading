import pytest
from datetime import datetime, timezone

from crypto_research.config.schema import OpportunityScoreConfig, ScoreComponentConfig
from crypto_research.core.domain import Candle, Signal, SignalDirection, Timeframe, DecisionOutcome
from crypto_research.portfolio.opportunity_scorer import OpportunityScorer

def test_opportunity_scorer_trend_alignment():
    cfg = OpportunityScoreConfig(
        enabled=True,
        minimum_score=40.0,
        components={
            "trend_alignment": ScoreComponentConfig(weight=100.0, enabled=True)
        }
    )
    scorer = OpportunityScorer(cfg)
    
    # 50 candles with increasing close prices to guarantee EMA < current close (uptrend)
    candles = []
    for i in range(50):
        c = Candle(
            asset="BTC",
            timeframe=Timeframe.M15,
            timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
            open=float(i), high=float(i*2 + 1), low=float(i - 1), close=float(i + 1), volume=100.0
        )
        candles.append(c)
        
    sig = Signal(
        timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        asset="BTC",
        timeframe=Timeframe.M15,
        direction=SignalDirection.LONG,
        strategy_name="test"
    )
    
    score = scorer.score(sig, "I1", candles)
    assert score.total_score == 100.0
    assert score.decision == DecisionOutcome.ACCEPTED
    
    # Same trend, but SHORT signal -> 0 score -> REJECTED
    sig_short = Signal(
        timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        asset="BTC",
        timeframe=Timeframe.M15,
        direction=SignalDirection.SHORT,
        strategy_name="test"
    )
    score2 = scorer.score(sig_short, "I1", candles)
    assert score2.total_score == 0.0
    assert score2.decision == DecisionOutcome.REJECTED

def test_scorer_disabled():
    cfg = OpportunityScoreConfig(enabled=False, minimum_score=90.0, components={})
    scorer = OpportunityScorer(cfg)
    
    sig = Signal(
        timestamp=datetime.now(timezone.utc),
        asset="BTC",
        timeframe=Timeframe.M15,
        direction=SignalDirection.LONG,
        strategy_name="test"
    )
    score = scorer.score(sig, "I1", [])
    assert score.total_score == 100.0
    assert score.decision == DecisionOutcome.ACCEPTED
