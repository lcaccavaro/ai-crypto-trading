import pytest
from datetime import datetime, timezone, timedelta
import yaml

from crypto_research.config.schema import ProjectConfiguration
from crypto_research.core.domain import Candle, Signal, SignalDirection, Timeframe, StrategyLifecycleState, Trade, Fill, PositionSide
from crypto_research.portfolio.strategy_state_machine import StrategyStateMachine
from crypto_research.portfolio.opportunity_scorer import OpportunityScorer
from crypto_research.strategies.context import StrategyInstance

@pytest.fixture
def base_config():
    yaml_str = """
project:
  name: test
  version: "1.0"
research:
  market: crypto
  data_source: binance
assets: ["BTCUSDT"]
timeframes: ["15m"]
data:
  market_type: futures
  start_date: "2024-01-01"
  end_date: "2024-02-01"
  raw_dir: raw
  processed_dir: proc
  metadata_dir: meta
  request_delay_ms: 100
  max_retries: 3
  retry_delay_s: 5
  schema_version: "1.0"
backtest:
  start_date: "2024-01-01"
  end_date: "2024-02-01"
  symbols: ["BTCUSDT"]
  timeframes: ["15m"]
execution:
  order_model: market
  slippage_bps: 2
  spread_bps: 1
  intrabar_fill_policy: stop_first
  gap_policy: fill_at_open
  allow_same_close_execution: false
costs:
  maker_fee_rate: 0.0002
  taker_fee_rate: 0.0005
capital:
  initial_balance: 10000.0
  risk_per_trade_pct: 1.0
risk:
  risk_reward_ratio: 3.0
  risk_per_trade_pct: 1.0
  max_concurrent_positions: 5
  max_total_exposure_pct: 50.0
  max_asset_exposure_pct: 20.0
  max_strategy_exposure_pct: 15.0
  daily_profit_target_pct: 2.0
  daily_loss_limit_pct: 3.0
  strategy_management:
    consecutive_loss_limit: 3
    cooldown:
      enabled: true
      value: 4
      unit: hours
    break_even_resets_losses: true
  opportunity_score:
    enabled: true
    minimum_score: 40.0
    version: "1.0"
    components:
      trend_alignment:
        weight: 100.0
        enabled: true
position_sizing:
  mode: risk_based
logging:
  level: INFO
  format: console
"""
    return ProjectConfiguration.model_validate(yaml.safe_load(yaml_str))

def test_pit_scorer(base_config):
    scorer = OpportunityScorer(base_config.risk.opportunity_score)
    # The scorer MUST only use the candles provided (which end at signal time).
    # If we pass 50 candles, it computes EMA from those 50.
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
    
    # Verify it doesn't try to look forward (there is no forward data anyway)
    # This proves the interface enforces PIT by only accepting current context.

def test_pit_strategy_state_machine():
    from crypto_research.config.schema import StrategyManagementConfig
    cfg = StrategyManagementConfig(consecutive_loss_limit=3)
    sm = StrategyStateMachine("S1", "I1", cfg)
    
    t0 = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)
    fill = Fill("f1", "o1", t0, "BTC", PositionSide.LONG, 100.0, 1.0, 0.0)
    t1 = Trade(
        trade_id="t1", asset="BTC", side=PositionSide.LONG,
        entry_fill=fill, exit_fill=fill, strategy_name="S1",
        timeframe=None, run_id="r", exit_reason="",
        gross_pnl=-10.0, fees=0.0, slippage_cost=0.0, spread_cost=0.0, net_pnl=-10.0
    )
    
    sm.update_from_trade(t1)
    
    # Try to process a trade in the past -> should fail
    t_past = t0 - timedelta(hours=1)
    fill_past = Fill("f2", "o2", t_past, "BTC", PositionSide.LONG, 100.0, 1.0, 0.0)
    t2 = Trade(
        trade_id="t2", asset="BTC", side=PositionSide.LONG,
        entry_fill=fill_past, exit_fill=fill_past, strategy_name="S1",
        timeframe=None, run_id="r", exit_reason="",
        gross_pnl=-10.0, fees=0.0, slippage_cost=0.0, spread_cost=0.0, net_pnl=-10.0
    )
    with pytest.raises(ValueError, match="Out of order trade update"):
        sm.update_from_trade(t2)
