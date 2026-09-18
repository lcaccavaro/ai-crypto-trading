# PROMPT 02 EXECUTION GUIDE
## Binance Futures Market Data Ingestion

**Status:** ✅ COMPLETE | **Validated:** 2026-09-18

---

## What Was Built

Prompt 02 implements the full data ingestion layer for the Crypto Market Research Laboratory.
Real Binance Futures OHLCV data is downloaded, validated, and stored in canonical Parquet format
with complete provenance metadata.

### Components

| File | Purpose |
|------|---------|
| `src/crypto_research/data/binance_client.py` | Low-level Binance Futures REST API client |
| `src/crypto_research/data/validators.py` | 5 data quality validators (OHLC, timestamps, nulls...) |
| `src/crypto_research/data/store.py` | Parquet read/write with atomic writes and UTC enforcement |
| `src/crypto_research/data/metadata.py` | Dataset provenance records (SHA-256, run_id, etc.) |
| `src/crypto_research/data/quality.py` | Quality reporter — JSON + CSV reports + printed table |
| `src/crypto_research/data/catalog.py` | Discovery and load API for the backtesting engine |
| `src/crypto_research/data/ingestion.py` | Orchestration pipeline + CLI entry point |
| `src/crypto_research/data/binance_provider.py` | DataProvider implementation for backtester |
| `config/config.yaml` | Extended with `data:` section (market_type, dates, rate limits) |

---

## How to Run

### Step 1: Verify Installation
```bash
cd /Users/lucascaccavaro/Documents/dev/ai-crypto-trading
python3 -m pytest tests/ -m "not live" -v
# Expected: 186+ PASSED

python3 -m pytest tests/integration/test_binance_live.py -v -m live
# Expected: 9 PASSED
```

### Step 2: Demo Ingestion (30-day range — recommended for first run)
```bash
python3 -m crypto_research.data.ingestion --demo
```
Downloads the last 30 days of 1m, 5m, 15m, and 1h data for BTCUSDT, ETHUSDT, SOLUSDT.
Takes ~3-5 minutes. No API key required.

### Step 3: Verify Data Was Downloaded
```bash
python3 -c "
from crypto_research.data.catalog import DataCatalog
cat = DataCatalog()
for ds in cat.list_datasets():
    print(f'{ds.symbol}/{ds.timeframe}: {ds.row_count:,} rows, status={ds.quality_status}')
"
```

### Step 4: Open the Validation Notebook
```bash
jupyter lab notebooks/02_binance_data_ingestion.ipynb
```
Run all cells to produce validation charts, quality table, and a data loading demo.

---

## Downloading the Full Research Range

> ⚠️ **Read before proceeding.** This downloads 2+ years of 1m data for 3 assets.
> Estimated time: **15-25 minutes per asset** for 1m data.

**1. Open `config/config.yaml` and review:**
```yaml
data:
  market_type: futures
  start_date: "2024-01-01"   # ← adjust as needed
  end_date: "2026-09-01"     # ← adjust as needed
```

**2. Run without `--demo`:**
```bash
python3 -m crypto_research.data.ingestion
```

**3. Verify with the catalog:**
```python
from crypto_research.data.catalog import DataCatalog
cat = DataCatalog()
for ds in cat.list_datasets():
    print(ds.symbol, ds.timeframe, ds.row_count, ds.actual_start[:10], ds.actual_end[:10])
```

---

## Data Architecture

### Storage Layout
```
data/
├── raw/
│   └── binance/futures/BTCUSDT/1m/
│       └── raw_1704067200000.json.gz    ← unmodified Binance response
├── processed/
│   └── binance/futures/BTCUSDT/1m/
│       ├── BTCUSDT_1m.parquet           ← canonical dataset (ZSTD)
│       └── BTCUSDT_1m_metadata.json    ← provenance record
└── metadata/
    └── dataset_manifest.json           ← global catalog
```

### Validation Rules
| Check | If Violated | Action |
|-------|------------|--------|
| Schema/dtypes | **FAIL** | Do not use for research |
| OHLC invariants (high≥max(o,c), etc.) | **FAIL** | Do not use for research |
| Duplicate timestamps | **FAIL** | Do not use for research |
| Non-UTC timestamps | **FAIL** | Do not use for research |
| Null values | **FAIL** | Do not use for research |
| Missing candles (gaps) | **WARNING** | Usable with awareness |

---

## Loading Data (for Prompt 03)

The `DataCatalog` is the only sanctioned way to access data in the backtester:

```python
from crypto_research.data.catalog import DataCatalog
from datetime import datetime, timezone

catalog = DataCatalog()

# Point-in-time load — candles BEFORE end only (no look-ahead)
df = catalog.load(
    "BTCUSDT", "1m",
    start=datetime(2024, 6, 1, tzinfo=timezone.utc),
    end=datetime(2024, 6, 2, tzinfo=timezone.utc),   # exclusive
)

# Or use BinanceDataProvider (satisfies DataProvider Protocol)
from crypto_research.data.binance_provider import BinanceDataProvider
from crypto_research.config.loader import load_config, find_project_root
from crypto_research.core.domain import Timeframe

config = load_config(find_project_root() / "config/config.yaml")
provider = BinanceDataProvider.from_config(config)
candles = provider.get_candles(
    "BTCUSDT", Timeframe.M1,
    start=datetime(2024, 6, 1, tzinfo=timezone.utc),
    end=datetime(2024, 6, 2, tzinfo=timezone.utc),
)
```

---

## Test Commands

```bash
# All offline tests (should always pass — no network needed)
python3 -m pytest tests/ -m "not live" -v

# Live Binance tests (requires internet)
python3 -m pytest tests/integration/test_binance_live.py -v -m live

# Data config only
python3 -m pytest tests/unit/test_data_config.py -v

# Validator tests
python3 -m pytest tests/unit/test_validators.py -v

# Parquet store tests
python3 -m pytest tests/unit/test_store.py -v

# Catalog tests
python3 -m pytest tests/unit/test_catalog.py -v

# Metadata tests
python3 -m pytest tests/unit/test_metadata.py -v
```

---

## Acceptance Criteria Verification

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Real Binance Futures data (no fake data) | ✅ | Live test output — `9 passed` |
| OHLC validation | ✅ | `test_validators.py` — all cases pass |
| Timestamp ordering/duplicates | ✅ | `test_validators.py` — strict UTC/mono checks |
| Missing candle detection | ✅ | WARNING (not FAIL) — legitimate gaps recorded |
| Parquet canonical storage | ✅ | ZSTD, UTC, PyArrow schema enforcement |
| Per-dataset provenance (SHA-256, run_id, git) | ✅ | `DatasetMetadata` — `test_metadata.py` |
| DataQualityReporter (JSON + CSV + table) | ✅ | Runs automatically on ingestion |
| Dataset manifest | ✅ | `data/metadata/dataset_manifest.json` |
| CLI entry point (`--demo` / full range) | ✅ | `python3 -m crypto_research.data.ingestion --demo` |
| DataProvider Protocol implementation | ✅ | `BinanceDataProvider` — look-ahead bias check |
| 186 offline tests pass | ✅ | `186 passed, 9 deselected` |
| 9 live integration tests pass | ✅ | `9 passed in 12.26s` |
| Jupyter notebook | ✅ | `notebooks/02_binance_data_ingestion.ipynb` |
| DATA_POLICY.md | ✅ | `docs/research/DATA_POLICY.md` |
| This guide | ✅ | `docs/execution/PROMPT_02_EXECUTION_GUIDE.md` |
