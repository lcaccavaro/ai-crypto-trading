import pytest
from datetime import datetime, timezone
import yaml

from crypto_research.config.schema import ProjectConfiguration
from crypto_research.core.domain import (
    Candle, Signal, SignalDirection, Timeframe, RejectionReason, DecisionOutcome,
    PortfolioState, StrategyLifecycleState
)
from crypto_research.backtest.risk_gate import RiskGate
from crypto_research.backtest.position_sizer import PositionSizer
from crypto_research.portfolio.portfolio_state_manager import PortfolioStateManager
from crypto_research.backtest.portfolio_accountant import PortfolioAccountant
from crypto_research.portfolio.orchestrator import PortfolioOrchestrator
from crypto_research.portfolio.strategy_state_machine import StrategyStateMachine
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
    enabled: false
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

def test_orchestrator_approves_valid_signal(base_config):
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
    
    sig = Signal(
        timestamp=datetime.now(timezone.utc),
        asset="BTCUSDT",
        timeframe=Timeframe.M15,
        direction=SignalDirection.LONG,
        strategy_name="test_strat",
        stop_price=9000.0,
        target_price=12000.0
    )
    
    inst = StrategyInstance(
        strategy_id="test_strat",
        version="1.0",
        parameters={},
        timeframe="15m",
        symbol="BTCUSDT"
    )
    
    decision = orch.evaluate_signal(sig, inst, [], [], 10000.0)
    assert decision.approved is True
    assert decision.max_position_size > 0

def test_orchestrator_rejects_paused_strategy(base_config):
    accountant = PortfolioAccountant(base_config.capital.initial_balance)
    state_manager = PortfolioStateManager(accountant, base_config.risk)
    risk_gate = RiskGate(base_config.risk, allow_short=True)
    position_sizer = PositionSizer()
    
    sm = StrategyStateMachine("test_strat", "inst1", base_config.risk.strategy_management)
    sm.force_state(StrategyLifecycleState.PAUSED, "MANUAL", datetime.now(timezone.utc))
    
    inst = StrategyInstance(
        strategy_id="test_strat",
        version="1.0",
        parameters={},
        timeframe="15m",
        symbol="BTCUSDT"
    )

    orch = PortfolioOrchestrator(
        run_id="run1",
        config=base_config,
        state_manager=state_manager,
        risk_gate=risk_gate,
        position_sizer=position_sizer,
        strategy_machines={inst.instance_id: sm}
    )
    
    sig = Signal(
        timestamp=datetime.now(timezone.utc),
        asset="BTCUSDT",
        timeframe=Timeframe.M15,
        direction=SignalDirection.LONG,
        strategy_name="test_strat",
        stop_price=9000.0,
        target_price=12000.0
    )
    

    decision = orch.evaluate_signal(sig, inst, [], [], 10000.0)
    assert decision.approved is False
    assert RejectionReason.STRATEGY_PAUSED in decision.rejection_codes
