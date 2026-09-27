import pytest
from datetime import datetime, timezone
import yaml

from crypto_research.config.schema import ProjectConfiguration
from crypto_research.core.domain import PortfolioState, PositionSide, RejectionReason
from crypto_research.backtest.risk_gate import RiskGate

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

def test_risk_gate_extended_strategy_state(base_config):
    gate = RiskGate(base_config.risk, allow_short=True)
    state = PortfolioState(
        timestamp=datetime.now(timezone.utc),
        cash=10000.0,
        equity=10000.0,
        used_capital=0.0,
        available_capital=10000.0,
        gross_exposure=0.0,
        net_exposure=0.0,
        realized_pnl=0.0,
        unrealized_pnl=0.0,
        total_fees=0.0,
        total_slippage=0.0,
        total_spread_cost=0.0,
        daily_pnl=0.0,
        daily_start_equity=10000.0,
        daily_limit_state="open",
        asset_exposures={},
        strategy_exposures={}
    )
    
    # Paused strategy
    ok, rejections = gate.check_all_extended(
        side=PositionSide.LONG,
        portfolio_state=state,
        symbol="BTCUSDT",
        entry_price=100.0,
        quantity=1.0,
        open_position_count=0,
        asset_notional=0.0,
        strategy_notional=0.0,
        strategy_state_str="paused",
        score=50.0
    )
    assert not ok
    assert RejectionReason.STRATEGY_PAUSED in rejections
    
def test_risk_gate_extended_low_score(base_config):
    gate = RiskGate(base_config.risk, allow_short=True)
    state = PortfolioState(
        timestamp=datetime.now(timezone.utc),
        cash=10000.0,
        equity=10000.0,
        used_capital=0.0,
        available_capital=10000.0,
        gross_exposure=0.0,
        net_exposure=0.0,
        realized_pnl=0.0,
        unrealized_pnl=0.0,
        total_fees=0.0,
        total_slippage=0.0,
        total_spread_cost=0.0,
        daily_pnl=0.0,
        daily_start_equity=10000.0,
        daily_limit_state="open",
        asset_exposures={},
        strategy_exposures={}
    )
    
    # Low score
    ok, rejections = gate.check_all_extended(
        side=PositionSide.LONG,
        portfolio_state=state,
        symbol="BTCUSDT",
        entry_price=100.0,
        quantity=1.0,
        open_position_count=0,
        asset_notional=0.0,
        strategy_notional=0.0,
        strategy_state_str="active",
        score=39.0
    )
    assert not ok
    assert RejectionReason.LOW_SCORE in rejections

def test_risk_gate_extended_max_strategy_exposure(base_config):
    gate = RiskGate(base_config.risk, allow_short=True)
    state = PortfolioState(
        timestamp=datetime.now(timezone.utc),
        cash=10000.0,
        equity=10000.0,
        used_capital=0.0,
        available_capital=10000.0,
        gross_exposure=0.0,
        net_exposure=0.0,
        realized_pnl=0.0,
        unrealized_pnl=0.0,
        total_fees=0.0,
        total_slippage=0.0,
        total_spread_cost=0.0,
        daily_pnl=0.0,
        daily_start_equity=10000.0,
        daily_limit_state="open",
        asset_exposures={},
        strategy_exposures={}
    )
    
    # 15% limit -> max 1500 notional.
    # We ask for 1600 notional
    ok, rejections = gate.check_all_extended(
        side=PositionSide.LONG,
        portfolio_state=state,
        symbol="BTCUSDT",
        entry_price=1600.0,
        quantity=1.0,
        open_position_count=0,
        asset_notional=0.0,
        strategy_notional=0.0,
        strategy_state_str="active",
        score=50.0
    )
    assert not ok
    assert RejectionReason.MAX_STRATEGY_EXPOSURE in rejections
