import pytest
from datetime import datetime, timezone
import yaml

from crypto_research.config.schema import ProjectConfiguration
from crypto_research.core.domain import Candle, Signal, SignalDirection, Timeframe, PositionSide
from crypto_research.portfolio.orchestrator import PortfolioOrchestrator
from crypto_research.backtest.portfolio_accountant import PortfolioAccountant
from crypto_research.portfolio.portfolio_state_manager import PortfolioStateManager
from crypto_research.backtest.risk_gate import RiskGate
from crypto_research.backtest.position_sizer import PositionSizer
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
    components: {}
position_sizing:
  mode: risk_based
logging:
  level: INFO
  format: console
"""
    return ProjectConfiguration.model_validate(yaml.safe_load(yaml_str))

def test_multi_strategy_opposing_signals(base_config):
    accountant = PortfolioAccountant(base_config.capital.initial_balance)
    state_manager = PortfolioStateManager(accountant, base_config.risk)
    risk_gate = RiskGate(base_config.risk, allow_short=True)
    position_sizer = PositionSizer()
    
    orch = PortfolioOrchestrator(
        run_id="run1",
        config=base_config,
        state_manager=state_manager,
        risk_gate=risk_gate,
        position_sizer=position_sizer,
        strategy_machines={}
    )
    
    # Strategy 1 goes LONG
    sig_long = Signal(
        timestamp=datetime.now(timezone.utc),
        asset="BTCUSDT",
        timeframe=Timeframe.M15,
        direction=SignalDirection.LONG,
        strategy_name="strat_long",
        stop_price=9000.0,
        target_price=12000.0
    )
    inst_long = StrategyInstance(
        strategy_id="strat_long",
        version="1.0",
        parameters={},
        timeframe="15m",
        symbol="BTCUSDT"
    )
    
    # Strategy 2 goes SHORT
    sig_short = Signal(
        timestamp=datetime.now(timezone.utc),
        asset="BTCUSDT",
        timeframe=Timeframe.M15,
        direction=SignalDirection.SHORT,
        strategy_name="strat_short",
        stop_price=11000.0,
        target_price=8000.0
    )
    inst_short = StrategyInstance(
        strategy_id="strat_short",
        version="1.0",
        parameters={},
        timeframe="15m",
        symbol="BTCUSDT"
    )
    
    # Evaluate LONG
    decision_long = orch.evaluate_signal(sig_long, inst_long, [], 0, 10000.0)
    assert decision_long.approved is True
    
    # If the engine opens the LONG position, the next evaluation will see it.
    # We will simulate the engine creating the position and updating the accountant.
    # Note: in this test we don't simulate the engine's position update, but we test that 
    # the orchestrator evaluates opposing signals independently and correctly.
    decision_short = orch.evaluate_signal(sig_short, inst_short, [], 0, 10000.0)
    assert decision_short.approved is True
    
    # Both are approved. The Orchestrator does not cancel opposing signals (conflicting signals policy: independent).
