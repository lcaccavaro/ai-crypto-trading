# PROMPT 02 — REAL BINANCE MARKET DATA INGESTION
## Historical Data Acquisition, Normalization, Storage and Data Quality

---

## 1. ROLE

You are acting as a **Principal Quantitative Data Engineer and Senior Python Engineer specialized in financial market-data infrastructure**.

You are continuing the development of the existing quantitative research laboratory created in PROMPT 01.

Your task is to implement the **real historical market-data layer using Binance public market data**.

This stage must produce a reliable, reproducible, auditable historical dataset that will later be consumed by the backtesting engine.

This is NOT the backtesting stage.

This is NOT the strategy stage.

This is NOT the risk-management stage.

This is NOT live trading.

The purpose of this prompt is:

> Acquire real Binance historical market data, validate it rigorously, normalize it into a research-friendly format, store it efficiently, and create sufficient metadata to make every dataset traceable and reproducible.

---

# 2. IMPORTANT — INSPECT PROMPT 01 FIRST

Before changing anything:

1. Inspect the complete repository.
2. Read `PROJECT_STATUS.md`.
3. Read `README.md`.
4. Read the Prompt 01 execution guide.
5. Inspect the existing architecture.
6. Inspect existing configuration.
7. Inspect existing tests.
8. Inspect the existing research-run infrastructure.
9. Inspect existing dependencies.
10. Inspect Git status.

Do NOT assume the architecture.

Do NOT recreate existing components.

Do NOT replace working components unnecessarily.

Extend the architecture created by Prompt 01.

If Prompt 01 is incomplete or broken:

**STOP.**

Do not create a parallel architecture to work around it.

Report the actual problem.

---

# 3. SCOPE OF PROMPT 02

Implement the following:

```text
Binance public market-data acquisition
        ↓
Raw data storage
        ↓
Data integrity validation
        ↓
Normalization
        ↓
Canonical historical dataset
        ↓
Parquet storage
        ↓
Metadata / provenance
        ↓
Research-ready dataset

The output of Prompt 02 becomes the primary historical market-data input for Prompt 03.

4. ABSOLUTE RULE — REAL DATA ONLY

This stage must use real Binance market data.

Do NOT generate:

synthetic candles;
fake OHLCV;
fake trades;
random data;
fabricated Binance responses;
placeholder market data.

If Binance cannot be reached:

FAIL FAST.

Do not continue using fake data.

Do not create a successful-looking dataset.

Do not silently switch to another provider.

5. ABSOLUTE RULE — NO FALLBACKS

The project has a strict fail-fast philosophy.

Forbidden:

try:
    download_binance_data()
except Exception:
    use_sample_data()

Also forbidden:

except:
    continue

Also forbidden:

if download_failed:
    create_dummy_dataset()

If an operation fails:

expose the actual error;
identify the failing asset/timeframe/date range;
stop the affected execution;
do not fabricate success.
6. DATA SOURCE

Use Binance's publicly accessible market-data infrastructure wherever possible.

The initial implementation must not require trading authentication.

Do NOT request:

trading permissions;
withdrawal permissions;
account access;
real trading credentials.

API keys must NOT be required for the initial historical market-data pipeline if the selected Binance endpoint/data source provides the required public data without authentication.

If the chosen Binance interface has a rate limit or access restriction:

respect it;
implement controlled request pacing;
expose errors;
do not bypass restrictions improperly.

Document the exact Binance data source/API endpoints actually used.

7. MARKET TYPE

The initial implementation should target:

Binance Spot

unless the existing project configuration explicitly establishes another market.

Design the data-provider abstraction so that Futures/Perpetual data can be added later without rewriting the data layer.

Do NOT mix Spot and Futures data into the same dataset without explicit market-type metadata.

Every dataset must identify its market type.

8. INITIAL ASSETS

The configuration must support multiple assets.

Initial research configuration should include at least:

BTCUSDT
ETHUSDT
SOLUSDT

Do NOT hard-code these symbols inside the ingestion engine.

They must come from configuration.

The architecture must allow adding:

BNBUSDT
XRPUSDT
DOGEUSDT
ADAUSDT
...

without changing core ingestion code.

9. INITIAL TIMEFRAMES

The system must support configurable timeframes.

At minimum:

1m
3m
5m
15m
30m
1h
2h
4h

Do not assume every timeframe needs to be downloaded independently if Binance can provide an efficient source from which deterministic resampling is possible.

However:

DO NOT silently mix exchange-native candles with locally resampled candles.

Metadata must clearly identify whether a dataset is:

native Binance interval

or:

locally resampled interval

For the initial implementation, prioritize correctness and simplicity.

10. INITIAL HISTORICAL RANGE

Make the date range configurable.

The initial configuration should allow:

start_date
end_date

Do not hard-code a permanent research period into the Python code.

The system must support rerunning the same ingestion process with different ranges.

Example:

data:
  start_date: "2020-01-01"
  end_date: "2026-09-01"

The exact initial dates should be selected based on actual Binance data availability.

Do not assume that every asset has existed since 2020.

11. LISTING-DATE AWARENESS

Different Binance symbols have different listing dates.

The ingestion system must NOT manufacture candles before the asset actually existed.

If a requested period begins before a symbol was listed:

The system should clearly record the absence of data.

Do NOT silently interpret missing pre-listing history as zero values.

Do NOT forward-fill pre-listing data.

Do NOT fabricate history.

The metadata should eventually allow us to distinguish:

requested period

from:

available period
12. RAW DATA

Keep a raw representation of downloaded data.

The purpose is reproducibility and auditability.

Conceptually:

data/
├── raw/
│   └── binance/
│       └── spot/
│           ├── BTCUSDT/
│           ├── ETHUSDT/
│           └── SOLUSDT/
│
├── processed/
│   └── ...
│
└── metadata/
    └── ...

Adapt the exact structure to the architecture from Prompt 01.

Do not store everything in one enormous file if partitioning is more appropriate.

13. CANONICAL DATA FORMAT

Use Parquet as the canonical research format.

Reasons:

columnar;
efficient;
typed;
compressed;
suitable for Pandas/Polars;
appropriate for large historical datasets.

The canonical candle schema should contain at minimum:

timestamp
open
high
low
close
volume

Preferably also:

close_time
quote_volume
trade_count
taker_buy_base_volume
taker_buy_quote_volume

if these are provided by the selected Binance source.

Do not discard useful exchange-provided fields without documenting why.

14. DATA TYPES

Use explicit data types.

Do not leave financial numerical fields as arbitrary Python objects or strings.

Prefer:

timestamp → timezone-aware datetime
prices → float64 or appropriate numeric representation
volume → float64
trade_count → integer

Document any precision decisions.

Avoid unnecessary conversion to low-precision floating-point formats.

15. TIMESTAMP STANDARDIZATION

All timestamps must use:

UTC

internally.

Never mix:

UTC
America/Sao_Paulo
local machine time

inside the canonical dataset.

The dataset must have an explicit timezone convention.

Document this prominently.

16. CANDLE SEMANTICS

Document exactly what each candle represents.

For example:

timestamp
open
high
low
close
volume

must have an unambiguous interpretation.

Pay particular attention to:

candle open time;
candle close time;
interval boundaries;
inclusive/exclusive ranges;
duplicate timestamps.

This is critical because Prompt 03 will simulate trading candle by candle.

17. NO LOOK-AHEAD THROUGH DATA ENGINEERING

Even though this is not the backtest engine, the data layer must preserve the information needed for point-in-time research.

Do not perform transformations that could accidentally leak future information into historical observations.

Examples of dangerous behavior include:

future-based filling;
centered rolling calculations;
future-dependent normalization;
future-dependent filtering.

Data cleaning must never modify historical values using information from future timestamps unless the operation is explicitly documented and proven safe.

18. MISSING CANDLES

Create robust detection for missing intervals.

For each:

symbol
timeframe

calculate the expected candle sequence.

Detect:

missing candles;
duplicate candles;
irregular timestamps;
unexpected intervals.

Do NOT automatically fill missing candles.

This is extremely important.

If Binance has no candle for a period, do not automatically invent one.

Record the gap.

19. DUPLICATES

Detect duplicate timestamps.

Duplicates must not silently remain in the canonical dataset.

If duplicates are encountered:

determine whether they are exact duplicates;
determine whether they conflict;
document the behavior.

Do not silently discard conflicting records.

If the conflict cannot be resolved deterministically:

FAIL FAST.

20. OHLC CONSISTENCY

Validate basic candle invariants.

For every candle:

high >= max(open, close)
low <= min(open, close)
high >= low
open > 0
high > 0
low > 0
close > 0
volume >= 0

Any violation must be investigated.

Do not silently "repair" financial data.

If repair is ever introduced in a future stage, it must be explicitly documented and separately versioned.

21. CHRONOLOGICAL ORDER

Every canonical dataset must be strictly ordered by timestamp.

Validate:

timestamp[i] < timestamp[i+1]

No duplicate or backward timestamps are permitted.

22. CROSS-TIMEFRAME CONSISTENCY

Where appropriate, validate consistency between timeframes.

For example:

1m
5m
15m
1h

must have compatible time boundaries.

Do not assume that locally resampled candles are identical to Binance-native candles.

If both are used, document the difference.

23. RESAMPLING POLICY

If local resampling is implemented:

Use mathematically correct OHLCV aggregation.

For example:

open  = first
high  = max
low   = min
close = last
volume = sum

For additional fields:

define explicit aggregation rules;
document them;
test them.

Do not use generic mean() or arbitrary aggregation.

24. DATA QUALITY REPORT

Every ingestion run must generate a data-quality report.

The report should contain, at minimum:

symbol
timeframe
requested_start
requested_end
actual_start
actual_end
row_count
duplicate_count
missing_candle_count
invalid_ohlc_count
null_count
timestamp_order_errors

Also include:

data_source
market_type
download_timestamp
dataset_version
25. QUALITY STATUS

Each dataset should receive an explicit quality status.

For example:

PASS
WARNING
FAIL

The exact classification rules must be documented.

Important:

A warning must not silently become a pass.

A failure must not produce a successful research dataset.

26. DATASET METADATA

For every dataset, record metadata including:

dataset_id
symbol
market_type
timeframe
data_source
source_endpoint
requested_start
requested_end
actual_start
actual_end
download_timestamp
row_count
schema_version
data_version
quality_status

Also record:

code_version
git_commit

when available.

Never fabricate Git information.

27. CHECKSUM / INTEGRITY

Where practical, generate checksums for raw files and/or canonical datasets.

This allows us to detect accidental modification.

Record:

sha256

or another cryptographic checksum.

The checksum must correspond to the actual file.

Do not fake checksums.

28. IDEMPOTENT DOWNLOADS

The ingestion system should be safely rerunnable.

If data already exists:

detect it;
determine whether it matches the requested dataset;
avoid unnecessary redownloads when safe.

However:

Do not blindly trust existing files.

Validate metadata and integrity before treating them as valid.

If an existing file is corrupted:

report the problem;
redownload only if the behavior is explicitly deterministic and configured;
otherwise fail fast.

Do not silently overwrite research data without recording what happened.

29. INCREMENTAL DOWNLOAD SUPPORT

Design the ingestion layer so that future runs can extend a dataset.

Example:

2020-01-01 → 2026-08-31

followed by:

2026-09-01 → 2026-09-15

must not require downloading the entire historical dataset again unnecessarily.

However, correctness takes priority over performance.

Never append data without validating boundaries and duplicates.

30. DATA VERSIONING

Create a clear concept of dataset version.

Example:

dataset_version
schema_version

These must not be confused.

For example:

schema_version = 1.0
dataset_version = generated timestamp / content hash

Document the semantics.

31. RESEARCH RUN INTEGRATION

Use the research-run infrastructure created in Prompt 01.

Every ingestion execution must generate or associate with a:

research_run_id

The run must record:

configuration snapshot;
requested symbols;
requested timeframes;
requested date range;
actual downloaded ranges;
source metadata;
quality results;
generated datasets.
32. DATA MANIFEST

Generate a machine-readable manifest.

For example:

data/metadata/dataset_manifest.json

The manifest should make it possible to discover:

What datasets exist?
Where are they?
Which symbol?
Which timeframe?
What period?
How many rows?
What quality status?
Which version?
Which source?
Which run created it?

The manifest must be generated from actual files.

Never hard-code its contents.

33. DATA CATALOG

Create a simple programmatic data catalog.

It should eventually allow queries such as:

catalog.list_datasets()
catalog.get_dataset("BTCUSDT", "1m")
catalog.validate_dataset(...)

Keep the implementation simple.

Do not build a database unless there is a strong reason.

Parquet + metadata is sufficient for this stage.

34. PANDAS / POLARS

You may use Pandas or Polars.

Choose one as the primary data-processing library.

Document the decision.

Avoid introducing both unless there is a concrete reason.

The data layer must remain easy to use from Jupyter.

35. DATA LOADING API

Create a clean interface such as:

data = data_catalog.load(
    symbol="BTCUSDT",
    timeframe="1m",
    start=...,
    end=...
)

The exact API is your architectural decision.

The important requirement is that Prompt 03 should be able to consume canonical datasets without knowing:

Binance API details;
raw file format;
download logic;
HTTP implementation.
36. NETWORK BEHAVIOR

Implement robust handling for:

connection errors;
HTTP errors;
API errors;
rate limits;
malformed responses;
timeouts.

Do NOT hide these failures.

Retry behavior may be used for transient network failures if:

it is bounded;
it is explicit;
it is logged;
it does not hide persistent failures.

A bounded retry mechanism is acceptable.

An infinite retry loop is forbidden.

37. RATE LIMITING

Respect Binance rate limits.

Do not attempt to bypass them.

The system should:

throttle requests where appropriate;
detect rate-limit responses;
wait according to the documented behavior;
fail clearly if the problem persists.

Do not implement aggressive parallel downloading without understanding the API limits.

Correctness and responsible API usage take priority over download speed.

38. ERROR REPORTING

If one dataset fails, the final report must make this obvious.

Example:

BTCUSDT 1m   PASS
BTCUSDT 5m   PASS
ETHUSDT 1m   PASS
SOLUSDT 1m   FAIL

Do not report:

Download completed successfully

when one required dataset failed.

39. NO SILENT PARTIAL SUCCESS

This is mandatory.

If the configuration requests:

3 assets × 8 timeframes

then the system must explicitly report the state of all requested datasets.

A partial result must be clearly classified as partial.

Do not silently proceed as though all requested data were successfully downloaded.

40. JUPYTER NOTEBOOK

Create:

notebooks/02_binance_data_ingestion.ipynb

The notebook must:

Load configuration.
Display the requested assets.
Display requested timeframes.
Display requested date range.
Create/associate a research run.
Execute the Binance ingestion pipeline.
Validate datasets.
Display a data-quality summary.
Display dataset inventory.
Display row counts.
Display actual available date ranges.
Display missing-candle statistics.
Display validation status.
Demonstrate loading a real canonical dataset.
Display a small sample of the real data.
Generate a final execution summary.

The notebook must use actual Binance data.

41. NOTEBOOK MUST NOT HIDE ERRORS

Do not write:

try:
    ingest()
except Exception as e:
    print(e)

and then continue.

If ingestion fails:

The notebook must fail.

The user must be able to see where and why it failed.

42. VISUAL VALIDATION

The notebook should include basic visual validation.

For example:

close-price plot;
volume plot;
timestamp continuity visualization if useful.

These are data validation charts, not trading charts.

Do not interpret them as strategy performance.

Do not generate entry/exit signals.

43. TESTING

Add automated tests for:

Configuration
valid symbols;
valid timeframes;
valid dates;
invalid configuration.
Data schema
expected columns;
expected types;
timezone consistency.
Candle validation
OHLC invariants;
positive prices;
volume validation;
timestamp ordering.
Duplicate detection
exact duplicates;
conflicting duplicates.
Missing candles
correct expected interval calculation.
Resampling

If implemented:

correct open;
correct high;
correct low;
correct close;
correct volume.
Metadata
required metadata fields;
run ID;
dataset ID;
checksum.
Data catalog
dataset discovery;
dataset loading.
44. INTEGRATION TEST

Create at least one integration test that uses the real Binance public interface.

Do not replace this with a fake Binance response.

If network access is unavailable during test execution:

The test must clearly indicate that the external integration test could not execute.

Do not convert it into a fake successful test.

Where appropriate, separate:

offline unit tests

from:

live Binance integration tests

so the distinction is explicit.

45. DATA QUALITY THRESHOLDS

Do not arbitrarily delete data simply to improve quality statistics.

Define explicit validation rules.

Examples:

duplicate candles → FAIL
invalid OHLC → FAIL
non-monotonic timestamps → FAIL
unexpected timezone → FAIL
missing candles → WARNING or FAIL depending on context

The exact thresholds must be justified and documented.

A missing candle may have a different meaning from a corrupted candle.

Do not treat them as equivalent.

46. IMPORTANT — DO NOT FORWARD-FILL MARKET DATA

Never use:

df.ffill()

to hide missing market candles.

Do not transform:

missing market observation

into:

apparently valid market observation

This can materially distort future backtests.

47. IMPORTANT — DO NOT DROP BAD DATA SILENTLY

Do not do:

df = df.dropna()

without first identifying:

how many rows were removed;
why;
whether removal is valid;
whether it changes the historical dataset.

Financial data cleaning must be explicit and auditable.

48. DATA STORAGE STRATEGY

Use a partitioning strategy that balances:

query speed;
storage;
maintainability;
reproducibility.

A reasonable design could be:

processed/
└── binance/
    └── spot/
        └── symbol=BTCUSDT/
            └── timeframe=1m/
                └── year=2024/
                    └── data.parquet

You may choose another structure if technically superior.

Explain the decision.

49. RAW VS PROCESSED

Clearly distinguish:

RAW

Data as received from Binance, with minimal transformation.

PROCESSED

Validated, normalized, canonical research format.

Never overwrite raw data with processed data.

Never pretend processed data is raw exchange data.

50. DATA PROVENANCE

Every processed dataset must be traceable back to:

source
raw file(s)
download timestamp
processing code version
configuration
research run
dataset version

This is essential for future reproducibility.

51. README DOCUMENTATION

Update the main README with:

how the data layer works;
supported assets;
supported timeframes;
supported market type;
storage format;
data directory structure;
how to configure date ranges;
how to execute ingestion;
how to validate data.
52. DATA DOCUMENTATION

Create:

docs/research/DATA_POLICY.md

Document:

timestamp convention;
candle semantics;
missing-data policy;
duplicate policy;
OHLC validation;
resampling policy;
raw/processed distinction;
data provenance;
listing-date behavior;
no-forward-fill rule;
no-fabrication rule.
53. EXECUTION GUIDE

Create:

docs/execution/PROMPT_02_EXECUTION_GUIDE.md

It MUST contain:

Objective

What Prompt 02 implemented.

Prerequisites

Required environment.

Configuration

Where to configure:

symbols;
timeframes;
date ranges;
market type.
Installation

Exact commands.

Execution

Exact commands to run the ingestion.

Jupyter

Exact command to launch and execute:

02_binance_data_ingestion.ipynb
Generated Files

Explain every important output directory.

Dataset Discovery

Explain how to find downloaded datasets.

Data Quality

Explain how to interpret:

PASS;
WARNING;
FAIL.
Re-run

Explain exactly how to run the ingestion again.

Incremental Update

Explain how to extend the historical range.

Troubleshooting

Explain real errors without hiding them.

Acceptance Checklist

Provide a checklist.

54. PROJECT_STATUS.md

Update the existing status file.

Prompt 01 should remain marked according to its actual status.

Prompt 02 may only be marked:

COMPLETE

after all acceptance criteria have actually passed.

Prompt 03–08 must remain:

NOT STARTED

unless explicitly implemented later.

55. RESULTS DIRECTORY

Every ingestion run must create a clearly identifiable result directory.

For example:

results/
└── RUN_YYYYMMDD_HHMMSS_ID/
    ├── config_snapshot.yaml
    ├── metadata.json
    ├── data_quality_report.json
    ├── data_quality_report.csv
    ├── dataset_manifest.json
    ├── logs/
    └── summary/

Adapt this to the existing run architecture.

Do not duplicate run-management logic from Prompt 01.

56. NO TRADING RESULTS

Prompt 02 must NOT generate:

win rate;
profit factor;
Sharpe ratio;
drawdown;
strategy performance;
trade signals;
entries;
exits;
profitability.

Those belong to later prompts.

The purpose here is:

Build trustworthy historical market data.

57. ACCEPTANCE CRITERIA

Prompt 02 is complete only when:

Binance
 Real Binance public data can be retrieved.
 Authentication is not required for the initial public-data flow.
 Rate limits are respected.
 Network errors are visible.
Assets
 Multiple symbols are configurable.
 BTCUSDT works.
 ETHUSDT works.
 SOLUSDT works.
 Symbols are not hard-coded inside ingestion logic.
Timeframes
 Multiple timeframes are configurable.
 Timeframe handling is validated.
 Native vs resampled data is explicit.
Storage
 Raw data is preserved.
 Canonical Parquet data is generated.
 Raw and processed data are separated.
Quality
 Duplicate detection works.
 Missing-candle detection works.
 OHLC validation works.
 Timestamp validation works.
 Null detection works.
 Quality report is generated.
Provenance
 Dataset metadata exists.
 Dataset manifest exists.
 Research run is recorded.
 Configuration snapshot exists.
 Git metadata is captured when available.
 Checksums are generated where applicable.
Reproducibility
 Existing datasets can be discovered.
 Dataset loading is deterministic.
 The same configuration can be rerun.
 Incremental ingestion is supported or clearly documented.
Fail Fast
 No fake data.
 No synthetic market data.
 No silent fallback.
 No silent partial success.
 No silent data repair.
 No silent forward-fill.
 No hidden exceptions.
Jupyter
 Notebook exists.
 Notebook executes.
 Notebook uses real Binance data.
 Notebook produces data-quality summary.
 Notebook demonstrates real dataset loading.
 Notebook produces validation artifacts.
Documentation
 README updated.
 DATA_POLICY.md exists.
 PROMPT_02_EXECUTION_GUIDE.md exists.
 PROJECT_STATUS.md updated.
58. REQUIRED FINAL VALIDATION

You MUST actually execute the implementation.

Do not stop after writing code.

Run:

1. Unit tests
2. Integration tests
3. Binance ingestion
4. Dataset validation
5. Data catalog validation
6. Jupyter notebook
7. Artifact verification
8. Metadata verification
9. Manifest verification
10. Fail-fast validation

Verify that the resulting Parquet files contain actual Binance market data.

Inspect:

first rows;
last rows;
row count;
timestamps;
OHLC;
volume;
timezone;
continuity.

Do not merely check that files exist.

59. FINAL REPORT

At the end, provide:

1. Implementation Summary

What was actually implemented.

2. Binance Data Source

State exactly which public Binance source/endpoints were used.

3. Assets Downloaded

Show the actual symbols successfully processed.

4. Timeframes Downloaded

Show the actual intervals successfully processed.

5. Historical Coverage

Show:

requested period
actual period

for each dataset.

6. Data Quality

Show:

rows
duplicates
missing candles
invalid candles
nulls
quality status
7. Files Created

Show the important generated files/directories.

8. Validation Performed

Show actual commands/tests and their real results.

Do NOT claim a test passed if it was not executed.

9. Research Run ID

Show the actual run ID.

10. Known Limitations

Be explicit.

11. Prompt 02 Acceptance Checklist

Use:

PASS
FAIL
NOT APPLICABLE
12. Next Step

Only if Prompt 02 is genuinely complete:

READY FOR PROMPT 03

The next stage will be:

PROMPT 03 — POINT-IN-TIME BACKTEST ENGINE
60. NON-NEGOTIABLE RULES FOR THE ENTIRE PROJECT

These rules must remain active in Prompt 02 and all future prompts:

NO look-ahead bias.
NO future information leakage.
NO fake market data.
NO synthetic candles.
NO fake trading results.
NO silent fallbacks.
NO hidden exceptions.
NO silent data repair.
NO silent forward-fill.
NO silent partial success.
NO fabricated metadata.
NO fabricated Git information.
NO unauthorized real trading.
No trading API credentials required for this stage.
Every dataset must be traceable.
Every research run must be reproducible.
Every configuration must be recorded.
All timestamps must be UTC internally.
Raw data must remain distinguishable from processed data.
Data quality failures must be visible.
Prompt 02 must not implement the backtesting engine.
Prompt 02 must not implement trading strategies.
Prompt 02 must not implement risk management.
Prompt 02 must not implement live trading.
Prompt 02 must not build a frontend.
Do not redesign Prompt 01 unnecessarily.
Do not modify future roadmap requirements.
Do not mark the stage complete without executing validation.
Every prompt must produce executable artifacts.
Every prompt must produce an execution/analysis Markdown guide.
START NOW

Inspect the existing repository and Prompt 01 implementation first.

Then implement Prompt 02 completely.

Use real Binance public market data.

Do not use mocks.

Do not use synthetic market data.

Do not use silent fallbacks.

Do not hide errors.

Do not stop after generating code.

BUILD IT.

RUN IT.

DOWNLOAD REAL DATA.

VALIDATE IT.

TEST IT.

DOCUMENT IT.

Only declare Prompt 02 complete after the acceptance criteria have actually been executed and verified.
