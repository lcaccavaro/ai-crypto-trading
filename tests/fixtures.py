"""
Shared test configuration fixtures for Prompt 03+.

Provides a canonical VALID_CONFIG dict that matches the current schema
(ProjectConfiguration with all Prompt 03 sections: backtest, costs, capital,
execution, risk with full fields, position_sizing).

ALL test files that build a full ProjectConfiguration must import from here
so that schema changes only need to be made in one place.
"""

from __future__ import annotations

VALID_CONFIG: dict = {
    "project": {"name": "test_lab", "version": "1.0.0"},
    "research": {"market": "crypto", "data_source": "binance"},
    "assets": ["BTCUSDT", "ETHUSDT"],
    "timeframes": ["1m", "5m", "1h"],
    "data": {
        "market_type": "futures",
        "start_date": "2024-01-01",
        "end_date": "2024-03-01",
    },
    "backtest": {
        "start_date": "2024-01-01",
        "end_date": "2024-02-01",
        "symbols": ["BTCUSDT"],
        "timeframes": ["1m"],
    },
    "execution": {
        "order_model": "market",
        "slippage_bps": 2.0,
        "spread_bps": 1.0,
        "intrabar_fill_policy": "stop_first",
        "gap_policy": "fill_at_open",
        "allow_same_close_execution": False,
    },
    "costs": {
        "maker_fee_rate": 0.0002,
        "taker_fee_rate": 0.0005,
    },
    "capital": {
        "initial_balance": 10000.0,
        "risk_per_trade_pct": 1.0,
    },
    "risk": {
        "risk_reward_ratio": 3.0,
        "risk_per_trade_pct": 1.0,
        "max_concurrent_positions": 5,
        "max_total_exposure_pct": 50.0,
        "max_asset_exposure_pct": 20.0,
        "daily_profit_target_pct": 2.0,
        "daily_loss_limit_pct": 3.0,
    },
    "position_sizing": {
        "mode": "risk_based",
        "fixed_quantity": None,
    },
    "logging": {"level": "INFO", "format": "console"},
}

# YAML string version for tests that write config to a file
VALID_CONFIG_YAML = """\
project:
  name: test_lab
  version: "1.0.0"

research:
  market: crypto
  data_source: binance

assets:
  - BTCUSDT
  - ETHUSDT

timeframes:
  - 1m
  - 5m
  - 1h

data:
  market_type: futures
  start_date: "2024-01-01"
  end_date: "2024-03-01"

backtest:
  start_date: "2024-01-01"
  end_date: "2024-02-01"
  symbols:
    - BTCUSDT
  timeframes:
    - 1m

execution:
  order_model: market
  slippage_bps: 2.0
  spread_bps: 1.0
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
  daily_profit_target_pct: 2.0
  daily_loss_limit_pct: 3.0

position_sizing:
  mode: risk_based
  fixed_quantity: null

logging:
  level: INFO
  format: console
"""
