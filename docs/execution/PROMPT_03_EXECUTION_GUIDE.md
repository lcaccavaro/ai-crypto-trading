# Prompt 03 Execution Guide

**Prompt:** 03 — Point-in-Time Backtest Engine & Execution Simulator  
**Status:** Complete  
**Prerequisite:** Prompt 01 (infrastructure) and Prompt 02 (data ingestion) must be completed first.

---

## Overview

Prompt 03 implements a deterministic, point-in-time correct historical backtesting engine.

The engine simulates strategy execution over historical OHLCV candle data, tracking fills, positions, PnL, and equity — without ever using future information.

---

## Prerequisites

```bash
# Verify Prompt 01 + 02 infrastructure is complete
python3 -m pytest tests/ -q

# Ensure data has been ingested for your symbols
python3 -c "
from crypto_research.data.catalog import DataCatalog
c = DataCatalog()
print(c.available_datasets())
"
```

---

## Running a Backtest

### Step 1: Configure

Ensure `config/config.yaml` has the `backtest`, `execution`, `costs`, `capital`, and `position_sizing` sections:

```yaml
backtest:
  start_date: "2024-01-01"
  end_date:   "2024-06-01"
  symbols:    ["BTCUSDT"]
  timeframes: ["15m"]

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
  max_concurrent_positions: 5
  max_total_exposure_pct: 50.0
  max_asset_exposure_pct: 20.0
  daily_profit_target_pct: 2.0
  daily_loss_limit_pct: 3.0

position_sizing:
  mode: risk_based
  fixed_quantity: null
```

### Step 2: Validate the Engine

Run the engine validation notebook to confirm the engine works correctly:

```bash
jupyter nbconvert --to notebook --execute notebooks/03_backtest_engine_validation.ipynb
```

Or open it in JupyterLab.

### Step 3: Run a Backtest (Python API)

```python
from crypto_research.config.loader import load_config
from crypto_research.data.catalog import DataCatalog
from crypto_research.backtest import BacktestEngine, EngineValidationStrategy
from crypto_research.research.run_manager import RunManager

# Load config and catalog
config = load_config("config/config.yaml")
catalog = DataCatalog()
manager = RunManager()

# Create a run
run = manager.create_run(config, config_path="config/config.yaml")

# Initialize engine
engine = BacktestEngine(catalog=catalog, config=config)

# Run with ENGINE_VALIDATION_ONLY strategy
strategy = EngineValidationStrategy(signal_every_n_candles=20, rr_ratio=3.0)
result = engine.run(strategy=strategy, run_id=run.run_id)

print(f"Total trades: {result.metrics.total_trades}")
print(f"Win rate: {result.metrics.win_rate:.1%}")
print(f"Net PnL: {result.metrics.net_pnl:.2f} USDT")
print(f"Max drawdown: {result.metrics.max_drawdown_pct:.2f}%")
```

### Step 4: Write Results to Disk

```python
from crypto_research.backtest import BacktestResultWriter

writer = BacktestResultWriter(base_dir="results/backtests")
run_dir = writer.write(result)
print(f"Results written to: {run_dir}")
```

---

## Output Files

After writing results, find these files in `results/backtests/<run_id>/`:

| File | Contents |
|------|---------|
| `run_metadata.json` | Run summary |
| `config_snapshot.yaml` | Config used |
| `trades.csv` | All completed trades |
| `orders.csv` | All orders (filled + rejected) |
| `fills.csv` | All fills |
| `equity_curve.csv` | Equity over time |
| `execution_events.csv` | Full event ledger |
| `metrics.json` | Performance metrics |
| `summary.json` | Human-readable summary |

---

## Engine Validation Checklist

After running the engine validation notebook, verify:

- [ ] `DataIntegrityError` raised for missing/bad-quality datasets
- [ ] Signal timing: all entry fills use next-candle open, not signal close
- [ ] Stop fills: SELL side at `stop_price` (or candle open if gapped)
- [ ] Target fills: SELL side at `target_price` (or candle open if gapped)
- [ ] Intrabar ambiguity: stop_first gives stop fills on ambiguous candles
- [ ] Cost model: entry price is above mid for LONG (adverse execution)
- [ ] Drawdown: computed from historical peak (never future)
- [ ] Daily PnL: resets at UTC midnight
- [ ] Determinism: two runs produce identical metrics

---

## Key Constraints (from BACKTEST_ENGINE_POLICY.md)

1. **No look-ahead bias** — `HistoricalDataView` enforces PIT strictly
2. **Signal timing** — signals execute at T+1 open, never at T close
3. **Costs always applied** — no zero-cost fills without explicit config
4. **STOP_FIRST is the default** intrabar policy (conservative)
5. **FILL_AT_OPEN is the default** gap policy (realistic)
6. **SHORT not allowed** in Prompt 03 (`allow_short = False` hardcoded)
7. **ENGINE_VALIDATION_ONLY** results are not research findings

---

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `DataIntegrityError: Dataset not found` | Data not ingested | Run Prompt 02 ingestion |
| `DataIntegrityError: quality_status != PASS` | Bad data quality | Re-run data quality validation |
| `LookAheadBiasError` | Engine bug — future data accessed | File a bug, DO NOT suppress |
| `ExecutionError: zero stop distance` | Strategy set stop == entry | Fix strategy signal logic |
| `ExecutionError: INSUFFICIENT_CAPITAL` | Position size > available cash | Reduce `risk_per_trade_pct` or `initial_balance` |

---

## Running Tests

```bash
# All Prompt 03 unit tests
python3 -m pytest tests/unit/test_cost_model.py \
                  tests/unit/test_position_sizing.py \
                  tests/unit/test_accounting.py \
                  tests/unit/test_point_in_time.py \
                  tests/unit/test_intrabar_execution.py \
                  tests/unit/test_risk_limits.py \
                  tests/unit/test_backtest_engine.py \
                  tests/unit/test_execution_engine.py \
                  tests/unit/test_determinism.py \
                  tests/unit/test_signal_timing.py \
                  -v

# Full suite (must be 330+ passing)
python3 -m pytest tests/ -q
```
