# Prompt 04 Execution Guide

## What Was Built

Prompt 04 delivers a standardized, extensible strategy research library
containing **26 strategies across 8 categories**, a shared indicator library,
a strategy registry, a signal ledger, and a batch runner.

---

## Directory Structure

```
src/crypto_research/strategies/
├── __init__.py                  # Imports all groups → registers all 26 strategies
├── base.py                      # BaseStrategy abstract class
├── registry.py                  # StrategyRegistry + global REGISTRY singleton
├── context.py                   # StrategyInstance (deterministic ID) + StrategyContext
├── signal_ledger.py             # Append-only signal log + CSV export
├── batch_runner.py              # Multi-instance batch execution
│
├── indicators/
│   ├── __init__.py              # Public API (14 functions)
│   ├── moving_averages.py       # sma, ema, ema_series, wma
│   ├── momentum.py              # rsi, roc, macd
│   ├── volatility.py            # atr, rolling_std, bollinger_bands, bb_width
│   ├── volume.py                # relative_volume, volume_sma
│   └── statistical.py           # zscore, donchian_channels, rolling_high, rolling_low
│
├── trend/                       # EMA_CROSS_001, TRIPLE_EMA_001, PRICE_VS_EMA_001, EMA_SLOPE_001
├── momentum/                    # RSI_MOMENTUM_001, ROC_MOMENTUM_001, MACD_MOMENTUM_001, MULTI_MOM_001
├── mean_reversion/              # BB_REVERSION_001, RSI_EXTREME_001, ZSCORE_REV_001, EMA_DISTANCE_001
├── breakout/                    # DONCHIAN_001, RANGE_BREAK_001, VOL_BREAK_001, ATR_CHANNEL_001
├── volatility/                  # ATR_EXPAND_001, VOL_COMPRESS_001, BB_WIDTH_001
├── volume/                      # VOL_SPIKE_001, VOL_WGT_MOM_001, VOL_BREAK_CONF_001
├── multi_indicator/             # TREND_MOM_VOL_001, TREND_VOL_MOM_001
└── market_structure/            # HH_HL_001, VOL_REGIME_001
```

---

## The 26 Strategies

| ID | Category | Warmup | Event-Based |
|---|---|---|---|
| EMA_CROSS_001 | trend | 22 | Yes |
| TRIPLE_EMA_001 | trend | 35 | Yes |
| PRICE_VS_EMA_001 | trend | 54 | No |
| EMA_SLOPE_001 | trend | 25 | Yes |
| RSI_MOMENTUM_001 | momentum | 15 | Yes |
| ROC_MOMENTUM_001 | momentum | 11 | Yes |
| MACD_MOMENTUM_001 | momentum | 35 | Yes |
| MULTI_MOM_001 | momentum | 16 | Yes |
| BB_REVERSION_001 | mean_reversion | 21 | Yes |
| RSI_EXTREME_001 | mean_reversion | 15 | Yes |
| ZSCORE_REV_001 | mean_reversion | 21 | Yes |
| EMA_DISTANCE_001 | mean_reversion | 21 | Yes |
| DONCHIAN_001 | breakout | 22 | Yes |
| RANGE_BREAK_001 | breakout | 17 | Yes |
| VOL_BREAK_001 | breakout | 40 | Yes |
| ATR_CHANNEL_001 | breakout | 22 | Yes |
| ATR_EXPAND_001 | volatility | 36 | Yes |
| VOL_COMPRESS_001 | volatility | 21 | Yes |
| BB_WIDTH_001 | volatility | 42 | Yes |
| VOL_SPIKE_001 | volume | 22 | Yes |
| VOL_WGT_MOM_001 | volume | 22 | Yes |
| VOL_BREAK_CONF_001 | volume | 23 | Yes |
| TREND_MOM_VOL_001 | multi_indicator | 24 | Yes |
| TREND_VOL_MOM_001 | multi_indicator | 40 | Yes |
| HH_HL_001 | market_structure | 7 | Yes |
| VOL_REGIME_001 | market_structure | 22 | Yes |

---

## How to Use the Registry

```python
import crypto_research.strategies  # Triggers all 26 registrations
from crypto_research.strategies import REGISTRY

# List all strategies
for info in REGISTRY.list():
    print(info.strategy_id, info.category)

# Get a strategy class
cls = REGISTRY.get("EMA_CROSS_001")

# Instantiate with defaults
strategy = REGISTRY.instantiate("EMA_CROSS_001")

# Instantiate with custom params
strategy = REGISTRY.instantiate("EMA_CROSS_001", fast_period=5, slow_period=15)

# Filter by category
trend_strategies = REGISTRY.filter_by_category("trend")
```

---

## How to Use the Signal Ledger

```python
from crypto_research.strategies.signal_ledger import SignalLedger
from crypto_research.strategies.context import StrategyInstance

ledger = SignalLedger(run_id="RUN_2024_001")
instance = StrategyInstance(
    strategy_id="EMA_CROSS_001",
    symbol="BTCUSDT",
    timeframe="15m",
    version="1.0.0",
    parameters={"fast_period": 9, "slow_period": 21},
)

# Record a signal
ledger.record(signal, instance)

# Export to CSV
ledger.to_csv("results/run_001/signals.csv")
```

---

## Test Suite

```bash
# Run only Prompt 04 strategy tests
python3 -m pytest tests/unit/strategies/ -v

# Run full suite (all 537 tests)
python3 -m pytest tests/ -q
```

### Test file inventory

| File | Purpose |
|---|---|
| `test_indicators.py` | 70+ indicator unit tests |
| `test_all_strategies.py` | 105+ per-strategy behavioral tests |
| `test_strategy_base.py` | StrategyInfo + StrategyRegistry |
| `test_strategy_isolation.py` | State isolation + StrategyInstance ID |
| `test_pit_mutations.py` | PIT correctness / no future data |
| `test_signal_ledger.py` | SignalLedger CRUD + CSV export |

---

## Design Decisions

### Why `StrategyInfo` instead of extending `StrategyMetadata`?

`StrategyMetadata` is frozen and used by 330 Prompt 03 tests. Modifying it
would require updating every test fixture. `StrategyInfo` is a new dataclass
that extends the metadata concept without breaking backward compatibility.

### Why is D4 replaced?

The specification listed "Session Range Breakout" for D4 but noted it should
only be implemented if session semantics are supported. Binance is 24/7 — there
are no natural session boundaries. `ATR_CHANNEL_001` provides the same
"dynamic envelope breakout" hypothesis without undocumented session assumptions.
See `docs/research/STRATEGY_LIBRARY_POLICY.md §8`.

### Why are defaults not "optimal"?

Per the Prompt 04 rules: "Do not optimize parameters." Default parameters
exist only to make strategies executable for research. They are not trained
or backtested to maximize performance.
