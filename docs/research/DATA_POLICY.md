# DATA POLICY

**Version:** 1.0 | **Effective from:** Prompt 02 | **Applies to:** All research data

---

## Core Principles

### 1. Real Data Only — No Exceptions

All market data used in this research laboratory is sourced directly from the
**Binance USDT-margined Futures public REST API**. Synthetic, interpolated,
or forward-filled data is **categorically prohibited**.

**No exceptions exist for:**
- Unit tests (use real compact synthetic DataFrames clearly labeled as TEST FIXTURE)
- Development/debugging (use the `--demo` flag for a 30-day real-data download)
- Network outages (fail fast with `DataIngestionError` — never fall back to fake data)

### 2. Fail Fast, Never Silently Succeed

If Binance cannot be reached, the ingestion pipeline raises `DataIngestionError`
and stops immediately. It does **NOT**:
- Fall back to cached or approximate data without disclosure
- Substitute synthetic prices
- Generate placeholder candles

### 3. No Look-Ahead Bias

All data access through `DataCatalog.load(end=t)` enforces strict exclusion of
candles at or after time `t`. The `BinanceDataProvider` performs an additional
defensive check and raises `LookAheadBiasError` if this contract is violated.

### 4. Preserve Raw Data

Every API batch response is saved as a gzip-compressed JSON file before any
transformation. Raw data is the primary audit record and must not be modified.

Path: `data/raw/binance/futures/<SYMBOL>/<TF>/raw_<starttime_ms>.json.gz`

### 5. No Forward-Filling

Missing candles (detected by the `validate_missing_candles` validator) are
recorded as `WARNING` in the quality report and **never filled**. A missing
candle represents genuine market absence — inventing a price introduces
fabricated information into the research.

---

## Data Provenance Chain

```
Binance Futures API
    ↓  (HTTP GET /fapi/v1/klines)
data/raw/binance/futures/<SYMBOL>/<TF>/raw_<ms>.json.gz      ← audit record
    ↓  (ParquetDataStore.raw_klines_to_dataframe)
Canonical DataFrame (typed, UTC timestamps)
    ↓  (run_validation_pipeline)
5 validators: schema, OHLC, timestamps, missing_candles, nulls
    ↓  (ParquetDataStore.save — atomic write)
data/processed/binance/futures/<SYMBOL>/<TF>/<SYMBOL>_<TF>.parquet
    ↓
data/processed/binance/futures/<SYMBOL>/<TF>/<SYMBOL>_<TF>_metadata.json
    ↓  (DataQualityReporter.finalize)
results/<run_id>/data_quality_report.json
results/<run_id>/data_quality_report.csv
results/<run_id>/dataset_manifest.json
```

---

## Data Source

| Field | Value |
|-------|-------|
| Exchange | Binance |
| Market type | USDT-margined perpetual futures |
| Endpoint | `https://fapi.binance.com/fapi/v1/klines` |
| Authentication | None required (public data) |
| Max candles/request | 1500 |
| Rate limit weight | 10 per klines request |
| Budget | 2400 weight/minute |
| Request delay | 250ms (default — ~240 calls/min) |

---

## Canonical Parquet Schema

Version `1.0` — increment `schema_version` in `config.yaml` when any column changes.

| Column | Type | Description |
|--------|------|-------------|
| `timestamp` | `datetime64[ns, UTC]` | Candle OPEN time |
| `open` | `float64` | Opening price |
| `high` | `float64` | Period high |
| `low` | `float64` | Period low |
| `close` | `float64` | Closing price |
| `volume` | `float64` | Base-asset volume |
| `close_time` | `datetime64[ns, UTC]` | Candle CLOSE time |
| `quote_volume` | `float64` | Quote-asset volume |
| `trade_count` | `int64` | Number of trades |
| `taker_buy_base_vol` | `float64` | Taker buy base volume |
| `taker_buy_quote_vol` | `float64` | Taker buy quote volume |

**Timezone:** All timestamps are UTC. Naive timestamps are rejected at write time.

---

## Validation Rules

| Validator | Trigger | Outcome |
|-----------|---------|---------|
| `validate_schema` | Missing columns, wrong dtype | **FAIL** |
| `validate_ohlc` | high < max(o,c), low > min(o,c), prices ≤ 0 | **FAIL** |
| `validate_timestamps` | Duplicates, non-monotonic, non-UTC | **FAIL** |
| `validate_nulls` | Any NaN/NaT in any column | **FAIL** |
| `validate_missing_candles` | Gaps in expected sequence | **WARNING** |

**FAIL** datasets must not be used for research. Investigate and re-download.
**WARNING** datasets are usable with documented awareness of gaps.

---

## Storage Layout

```
data/
├── raw/
│   └── binance/futures/<SYMBOL>/<TF>/
│       └── raw_<starttime_ms>.json.gz     ← unmodified API responses
├── processed/
│   └── binance/futures/<SYMBOL>/<TF>/
│       ├── <SYMBOL>_<TF>.parquet           ← canonical dataset
│       └── <SYMBOL>_<TF>_metadata.json    ← provenance record
└── metadata/
    └── dataset_manifest.json              ← global catalog
```

---

## Downloading Data

### Demo run (last 30 days — for validation):
```bash
python3 -m crypto_research.data.ingestion --demo
```

### Full research range:
```bash
# ⚠️ Read first: this downloads years of 1m data per asset (15-25 min)
# 1. Set start_date and end_date in config/config.yaml under `data:` section
# 2. Run:
python3 -m crypto_research.data.ingestion
```

### Via Python:
```python
from crypto_research.config.loader import load_config, find_project_root
from crypto_research.data.ingestion import DataIngestionPipeline

root = find_project_root()
config = load_config(root / "config/config.yaml")
pipeline = DataIngestionPipeline(config=config, project_root=root)

# Demo mode (last 30 days)
result = pipeline.run(use_full_range=False)

# Full range (reads start_date/end_date from config.yaml)
result = pipeline.run(use_full_range=True)
```

---

## Loading Data

```python
from crypto_research.data.catalog import DataCatalog
from datetime import datetime, timezone

catalog = DataCatalog()

# List all available datasets
datasets = catalog.list_datasets()

# Load with point-in-time filter (required for backtesting)
df = catalog.load(
    "BTCUSDT", "1m",
    start=datetime(2024, 8, 1, tzinfo=timezone.utc),
    end=datetime(2024, 9, 1, tzinfo=timezone.utc),  # exclusive
)

# Validate a dataset
summary = catalog.validate_dataset("BTCUSDT", "1m")
print(summary.overall_status)
```

---

## Survivorship Bias Warning

The research universe (BTCUSDT, ETHUSDT, SOLUSDT) was chosen before any
backtesting results were known. Adding assets post-hoc based on observed
performance constitutes data snooping and is prohibited.

When adding new assets to the universe:
1. Document the addition date and the reason
2. Only use data from after the asset's Binance Futures listing date
3. Never cherry-pick assets based on their known historical performance

---

## Change Log

| Date | Version | Change |
|------|---------|--------|
| 2026-09-18 | 1.0 | Initial data policy — Prompt 02 |
