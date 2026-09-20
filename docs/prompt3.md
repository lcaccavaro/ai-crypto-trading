# PROMPT 03 — POINT-IN-TIME BACKTEST ENGINE & EXECUTION SIMULATOR

## ROLE

You are acting as a:

- Principal Quantitative Research Engineer
- Senior Python Architect
- Quantitative Backtesting Infrastructure Specialist
- Market Microstructure / Execution Modeling Engineer

You are continuing the implementation of an existing quantitative research laboratory.

The project already contains:

- Prompt 01 — Project Foundation / Architecture / Reproducibility
- Prompt 02 — Binance Market Data Ingestion / Normalization / Data Quality

Your responsibility in this prompt is to implement and VALIDATE the core:

> POINT-IN-TIME BACKTEST ENGINE + HISTORICAL EXECUTION SIMULATOR

This engine will become the foundation used by all future strategies.

---

# 1. ABSOLUTE PROJECT RULES

These rules are mandatory.

## 1.1 DO NOT redesign the project

Before changing anything:

1. Inspect the existing repository.
2. Inspect Prompt 01 implementation.
3. Inspect Prompt 02 implementation.
4. Inspect:
   - README.md
   - PROJECT_STATUS.md
   - configuration files
   - architecture documentation
   - data policy
   - existing tests
   - existing notebooks
   - existing data catalog/manifest
5. Reuse the existing architecture.

DO NOT create a parallel architecture.

DO NOT duplicate modules that already exist.

DO NOT rename major existing components unless absolutely necessary.

If a required component already exists, extend it rather than replacing it.

---

# 2. DO NOT PROCEED IF PROMPT 01 OR PROMPT 02 IS BROKEN

Before implementing Prompt 03, verify that:

- project imports correctly;
- configuration loads correctly;
- tests from Prompt 01 pass;
- Prompt 02 data infrastructure is functional;
- at least one real Binance dataset exists;
- the dataset can be loaded from the canonical data layer;
- dataset metadata exists;
- data-quality status is known;
- timestamps are normalized and documented.

If a prerequisite is broken:

STOP.

Do not create workarounds.

Do not mock the missing component.

Do not generate synthetic market data to pretend that the prerequisite works.

Report the real error.

---

# 3. NO FALLBACKS / NO MOCKS / NO SILENT FAILURES

This is a strict requirement.

DO NOT:

- create fake market data for research;
- create fake trades;
- silently skip missing datasets;
- silently replace Binance data;
- silently repair invalid data;
- silently ignore execution errors;
- catch exceptions and continue;
- return partial results as successful;
- fabricate metrics;
- fabricate profitability;
- fabricate validation results;
- use random data as a substitute;
- use future data;
- use future strategy performance;
- use future candles;
- use future indicators.

For transient network operations, bounded retries may exist only where already allowed by Prompt 02.

For the backtest engine itself:

> If a required condition fails, the run must fail visibly.

The user needs to see the real problem.

---

# 4. PRIMARY OBJECTIVE

Build a deterministic, point-in-time historical backtesting engine capable of:

1. Loading canonical Binance historical datasets.
2. Processing market events strictly in chronological order.
3. Receiving strategy decisions without exposing future information.
4. Creating simulated orders.
5. Simulating order execution.
6. Opening and closing positions.
7. Managing stop-loss.
8. Managing take-profit.
9. Applying configurable fees.
10. Applying configurable spread assumptions.
11. Applying configurable slippage.
12. Handling execution gaps.
13. Calculating position size.
14. Tracking capital.
15. Tracking equity.
16. Tracking realized PnL.
17. Tracking unrealized PnL.
18. Tracking exposure.
19. Tracking concurrent positions.
20. Applying configurable risk limits.
21. Producing a complete machine-readable trade ledger.
22. Producing an equity curve.
23. Producing execution logs.
24. Producing reproducible run metadata.
25. Proving that future information cannot influence historical decisions.

The engine must be designed so that Prompt 04 can plug in many strategies without rewriting the engine.

---

# 5. WHAT THIS PROMPT IS NOT

DO NOT implement the complete strategy library yet.

Do not build:

- 20–30 trading strategies;
- optimization;
- strategy ranking;
- strategy selection;
- machine learning;
- regime detection;
- strategy score;
- strategy performance-based activation;
- walk-forward optimization;
- hyperparameter optimization;
- live trading;
- paper trading infrastructure;
- Binance authenticated trading;
- production execution;
- frontend.

Those belong to later prompts.

Prompt 03 is infrastructure.

The objective is:

> Make the backtest engine trustworthy before strategies are introduced.

---

# 6. CORE PRINCIPLE — POINT-IN-TIME SIMULATION

This is the most important requirement of Prompt 03.

At any simulated timestamp:

> The engine and strategy may only access information that would have been available at that timestamp.

Nothing else.

---

# 7. LOOK-AHEAD BIAS MUST BE IMPOSSIBLE BY DESIGN

Do not rely only on developer discipline.

Design APIs that make accidental future access difficult or impossible.

For example, instead of exposing an entire DataFrame:

```python
strategy.on_candle(full_dataframe)

prefer a controlled historical view such as:

strategy.on_candle(
    market_context=HistoricalDataView(...)
)

where the view only exposes information available up to the current simulation timestamp.

The strategy must not receive future rows.

8. FUTURE DATA ACCESS RULE

Suppose the dataset contains:

09:00
09:01
09:02
09:03
09:04
09:05
...

When simulation time is:

09:03

the strategy may access:

09:00
09:01
09:02
09:03

but NOT:

09:04
09:05
...

This restriction must be enforced by the engine/data-access layer.

9. MULTI-TIMEFRAME POINT-IN-TIME RULE

This is extremely important.

Suppose a strategy uses:

5-minute candles
1-hour candles

At:

10:15

the strategy may use the last fully closed 1-hour candle.

It must NOT use the partially formed:

10:00–11:00

candle.

Therefore:

A candle becomes available to strategy logic only when its information is actually known.

Do not expose an incomplete higher-timeframe candle as if it were closed.

Document this behavior.

10. SIGNAL TIMING

Define and implement an explicit signal timing model.

Default behavior:

If a strategy generates a signal using a candle's close:

Candle closes at 10:05

the signal becomes actionable after the candle closes.

The earliest normal market execution should therefore occur on the next available execution event, typically:

10:06

or the next candle's open, depending on the execution model.

Do NOT allow:

calculate signal using close
+
execute at the same historical close

unless the engine explicitly models that execution behavior and the information availability is valid.

The default configuration should avoid same-close look-ahead.

Document the exact semantics.

11. MARKET DATA SOURCE

The engine must consume the canonical datasets produced by Prompt 02.

Do not bypass the canonical data layer.

Example conceptual flow:

Binance Raw Data
        ↓
Prompt 02 Normalization
        ↓
Canonical Parquet
        ↓
Data Catalog
        ↓
Backtest Data Provider
        ↓
Point-In-Time Data View
        ↓
Backtest Engine
12. MARKET TYPE

Prompt 02 initially uses:

Binance Spot

The engine should therefore support Spot semantics by default.

However, design the domain model so that future market types can be added:

SPOT
FUTURES
PERPETUAL

Do not implement futures execution yet.

Do not pretend Spot supports native short selling.

The engine may have a generic PositionSide model:

LONG
SHORT

but the market configuration must determine which sides are permitted.

For Binance Spot:

allow_short = false

by default.

If a future market type supports shorting, that capability can be enabled later.

13. MULTI-ASSET SUPPORT

The engine must support simultaneous assets.

Example:

BTCUSDT
ETHUSDT
SOLUSDT

The engine must not assume that only one symbol exists.

Each symbol must maintain independent:

market state;
positions;
orders;
execution history;
exposure;
PnL.

The portfolio-level engine must aggregate them.

14. MULTI-TIMEFRAME SUPPORT

The engine must support multiple timeframes.

Example:

1m
5m
15m
1h

Do not hard-code these values.

Use configuration.

The architecture must support a future strategy consuming multiple timeframes.

15. EVENT-DRIVEN BACKTEST LOOP

Implement an event-driven simulation architecture.

Conceptually:

Historical Data
      ↓
Chronological Event Stream
      ↓
Market Event
      ↓
Point-In-Time State Update
      ↓
Strategy Evaluation
      ↓
Risk Evaluation
      ↓
Order Creation
      ↓
Execution Simulation
      ↓
Position Update
      ↓
Portfolio Update
      ↓
Trade/Event Recording

The engine must process events in strictly chronological order.

16. CHRONOLOGICAL ORDERING

All events must be ordered by:

UTC timestamp;
deterministic secondary ordering when timestamps are equal.

Define the secondary ordering explicitly.

For example:

market update
↓
order activation
↓
execution
↓
position update
↓
risk/account update

The exact implementation is your architectural decision, but it must be deterministic and documented.

17. DETERMINISM

Running the same:

code;
configuration;
dataset;
date range;
strategy version;
execution assumptions;

must produce the same:

trades;
fills;
PnL;
equity curve;
metrics.

Do not introduce random behavior.

If randomness is ever introduced in the future, it must be explicitly seeded and recorded.

18. DOMAIN OBJECTS

Use the domain architecture established in Prompt 01.

Extend it if necessary.

At minimum, the engine needs robust representations for:

MarketEvent

Fields should include concepts such as:

timestamp
symbol
timeframe
OHLCV
market_type
Signal

Should represent a strategy decision.

Potential fields:

timestamp
strategy_id
symbol
timeframe
side
signal_type
confidence / score if applicable
reason
metadata

Do not implement the final strategy scoring system yet.

Order

Must include concepts such as:

order_id
strategy_id
symbol
side
order_type
quantity
requested_price
created_at
activation_time
stop_price
target_price
status

Support at minimum the order concepts required for:

market entry;
stop-loss;
take-profit.
Fill

Must represent actual simulated execution:

fill_id
order_id
timestamp
symbol
side
quantity
price
fee
slippage
spread_cost
Position

Must track:

position_id
strategy_id
symbol
side
quantity
entry_price
entry_timestamp
stop_price
target_price
realized_pnl
unrealized_pnl
status
Trade

A completed logical trade.

Include:

trade_id
strategy_id
symbol
timeframe
side
entry_timestamp
entry_price
exit_timestamp
exit_price
quantity
initial_stop
target_price
gross_pnl
fees
slippage_cost
spread_cost
net_pnl
risk_amount
R_multiple
exit_reason
holding_duration

Additional fields may be added if useful.

19. TRADE LIFECYCLE

Implement a clear lifecycle.

Example:

SIGNAL
  ↓
ORDER_CREATED
  ↓
ORDER_ACTIVE
  ↓
FILLED
  ↓
POSITION_OPEN
  ↓
POSITION_MANAGED
  ↓
EXIT_TRIGGERED
  ↓
EXIT_ORDER
  ↓
FILLED
  ↓
POSITION_CLOSED
  ↓
TRADE_RECORDED

The lifecycle must be auditable.

20. ENTRY

The engine must support a strategy creating an entry order.

The entry order must contain enough information to calculate:

quantity;
execution price;
stop;
target;
risk.

The engine must distinguish:

requested entry price

from:

actual fill price

because execution costs may modify the final price.

21. STOP-LOSS

The engine must support an initial stop-loss.

Example:

Entry = 100
Stop = 98

Risk:

2 price units

The exact implementation must work for different assets and prices.

Stop distance must never use future market information.

22. TAKE-PROFIT

The engine must support configurable risk/reward.

Initial default:

RR = 3.0

Meaning:

Risk = 1R
Target = +3R

For a long example:

Entry = 100
Stop = 98

Risk = 2

Target = 106

For a short example:

Entry = 100
Stop = 102

Risk = 2

Target = 94

Do not hard-code 3:1.

Configuration must allow:

1:1
1.5:1
2:1
3:1
4:1
...
23. IMPORTANT RR MATHEMATICS

The engine must calculate R correctly.

At:

+3R = +3 units of initial risk
-1R = -1 unit of initial risk

Therefore:

1 win + 3 losses
=
+3R - 3R
=
0R

before costs.

This is the theoretical 25% break-even win rate for a fixed 3:1 payoff structure before costs.

Do not confuse this with:

3 wins + 1 loss
=
+9R - 1R
=
+8R

before costs.

The engine must calculate these values programmatically rather than relying on hard-coded assumptions.

24. INTRABAR AMBIGUITY

This is a critical limitation of OHLC backtesting.

Suppose a candle contains:

High >= Target
AND
Low <= Stop

The OHLC candle tells us both levels were touched.

It does NOT tell us which happened first.

Do NOT pretend that the order is known.

Implement an explicit configurable policy.

Example:

execution:
  intrabar_fill_policy: stop_first

Possible policies:

stop_first
target_first
reject_ambiguous

The default should be conservative:

stop_first

unless the existing project architecture establishes another explicit policy.

Document:

why the ambiguity exists;
which policy is used;
how changing the policy affects results;
why the result should not be interpreted as tick-level truth.
25. GAP HANDLING

If price gaps beyond a stop or target:

Example:

Stop = 100
Previous close = 102
Next open = 97

Do not automatically fill at:

100

if the simulated execution model says the market opened at:

97

Define and implement an explicit gap execution policy.

Execution must not magically obtain a better price than the market path provides.

Document the policy.

26. SLIPPAGE

Implement configurable slippage.

At minimum support:

basis points

Example:

execution:
  slippage_bps: 2

The engine must apply slippage consistently according to:

buy;
sell;
long;
short.

Do not hard-code a magic value inside the engine.

27. SPREAD

Implement a configurable spread assumption.

Example:

execution:
  spread_bps: 1

Clearly distinguish:

market price
spread
slippage
execution price

Avoid double-counting costs.

Document the exact calculation.

28. FEES

Implement configurable trading fees.

At minimum:

costs:
  maker_fee_rate: ...
  taker_fee_rate: ...

or an equivalent architecture.

The default backtest should use an explicitly configured fee assumption.

Do NOT silently assume Binance's current fee schedule.

Do NOT require authenticated Binance access for Prompt 03.

The fee assumption must be visible in the run configuration.

29. NET PNL

The most important PnL number for research is:

NET PNL

not gross PnL.

At minimum:

Net PnL
=
Gross PnL
-
Fees
-
Spread Costs
-
Slippage Costs

Make sure costs are not accidentally counted twice.

30. POSITION SIZING

Implement configurable position sizing.

At minimum support:

fixed quantity

and:

risk-per-trade sizing

For risk-based sizing, conceptually:

risk_budget
=
equity × risk_per_trade

and:

position_size
=
risk_budget / stop_distance

The implementation must account for execution costs appropriately.

Do not allow the engine to silently exceed available capital.

31. CAPITAL MANAGEMENT

Implement portfolio-level capital tracking.

Configuration must support concepts such as:

capital:
  initial_balance: ...
  risk_per_trade_pct: ...
  max_concurrent_positions: ...
  max_total_exposure_pct: ...
  max_asset_exposure_pct: ...

Do not hard-code these values.

32. DAILY PROFIT TARGET

The engine must support a configurable daily profit target.

Example:

risk:
  daily_profit_target_pct: 1.0

IMPORTANT:

The 1% number is a research parameter, NOT an assumption that 1% per day is realistically sustainable.

The engine must simply test the configured rule.

When the daily target is reached, the default behavior should be:

stop opening new positions

Do not automatically fabricate a forced exit unless explicitly configured.

Existing positions must follow their configured management rules.

Document this behavior.

33. DAILY LOSS LIMIT

Implement a configurable daily loss limit.

Example:

risk:
  daily_loss_limit_pct: 2.0

When the limit is reached:

stop opening new positions

Again, existing positions should follow explicit configuration.

Do not silently close everything unless configured.

34. MAX CONCURRENT POSITIONS

Support:

risk:
  max_concurrent_positions: ...

The engine must reject a new position if opening it would violate the configured limit.

The rejection must be logged.

Do not silently ignore the attempted order.

35. TOTAL EXPOSURE

Support portfolio-level exposure controls.

For example:

risk:
  max_total_exposure_pct: ...

The exact exposure definition must be documented.

Possible definition:

sum(abs(notional exposure))
/
current equity

Use one clear definition consistently.

36. ASSET EXPOSURE

Support a per-symbol exposure limit.

Example:

risk:
  max_asset_exposure_pct: ...

This is necessary because future Prompt 04 will allow many strategies to trade the same asset simultaneously.

37. STRATEGY EXPOSURE

Design the architecture so future versions can restrict exposure by strategy.

Prompt 03 does not need the complete strategy-selection logic.

But the portfolio model should not make strategy-level exposure impossible.

38. NO STRATEGY PERFORMANCE SELECTION YET

DO NOT implement:

choose the best strategies

or:

disable strategy after 3 losses

or:

select strategies based on historical winners

Those belong to Prompt 05.

The engine only needs the infrastructure required to enforce generic limits.

39. NO FUTURE STRATEGY INFORMATION

The engine must not allow:

future strategy win rate
future PnL
future drawdown
future regime
future ranking
future trade results

to influence a historical decision.

This must be explicitly documented.

40. ACCOUNTING MODEL

Implement a proper portfolio/accounting ledger.

Track at minimum:

cash balance
equity
used capital
available capital
gross exposure
net exposure
realized PnL
unrealized PnL
fees
slippage
spread costs

The exact terminology must be documented.

41. EQUITY CURVE

Produce a machine-readable equity curve.

At minimum:

timestamp
cash
equity
realized_pnl
unrealized_pnl
gross_exposure
net_exposure
drawdown

Drawdown should be calculated from the historical equity curve without future leakage.

42. TRADE LEDGER

Produce a complete trade ledger.

At minimum:

trade_id
run_id
strategy_id
symbol
timeframe
side
entry_timestamp
entry_price
exit_timestamp
exit_price
quantity
initial_stop
target
risk_amount
gross_pnl
fees
slippage
spread_cost
net_pnl
R_multiple
holding_duration
exit_reason

This file will become the primary input for Prompt 06 reporting.

43. ORDER / EXECUTION LEDGER

Also produce an execution-level ledger.

It should allow investigation of:

order created
order activated
order rejected
order filled
stop triggered
target triggered
position closed

Every execution event should be traceable.

44. REJECTION REASONS

Orders rejected by risk/execution constraints must have explicit reasons.

Examples:

MAX_CONCURRENT_POSITIONS
MAX_TOTAL_EXPOSURE
MAX_ASSET_EXPOSURE
DAILY_PROFIT_TARGET_REACHED
DAILY_LOSS_LIMIT_REACHED
INSUFFICIENT_CAPITAL
INVALID_ORDER
MARKET_NOT_AVAILABLE
SHORT_NOT_ALLOWED

Do not silently discard rejected orders.

45. ENGINE VALIDATION STRATEGY

Prompt 03 does NOT implement the actual strategy library.

However, a deterministic minimal strategy is allowed exclusively for engine validation.

It must be explicitly named something like:

ENGINE_VALIDATION_ONLY

It must NOT be presented as:

a profitable strategy;
a trading recommendation;
evidence of market edge;
a candidate production strategy.

Its only purpose is to exercise:

entries;
exits;
stops;
targets;
position sizing;
accounting;
costs;
risk limits.
46. REAL MARKET DATA VALIDATION

The validation notebook must use at least one real canonical Binance dataset from Prompt 02.

Do not use synthetic market data as the research dataset.

You may use deterministic synthetic fixtures ONLY inside isolated unit tests where necessary to test edge cases that are difficult to reproduce naturally.

Those fixtures must be clearly marked:

UNIT TEST FIXTURE — NOT RESEARCH DATA

Never mix them with research results.

47. CRITICAL LOOK-AHEAD TEST

Create an automated regression test for look-ahead bias.

Conceptually:

Run the same historical dataset.
Modify only candles AFTER timestamp T.
Re-run the backtest.
Compare all decisions/trades/results BEFORE T.

Expected:

Everything before T must be identical.

If modifying future data changes earlier decisions:

FAIL.

This test is mandatory.

48. SIGNAL TIMING TEST

Create a test proving:

signal generated from candle close

cannot execute at an invalid earlier timestamp.

Test that execution occurs only according to the configured activation/execution semantics.

49. FUTURE CANDLE ACCESS TEST

Create a test demonstrating that a strategy cannot access future rows through the normal historical-data API.

The API should expose only data available at the current point in time.

50. MULTI-TIMEFRAME TEST

Create a test proving that an unclosed higher-timeframe candle is not available to strategy logic.

Example:

At:

10:15

the strategy must not see the incomplete:

10:00–11:00

1-hour candle as closed information.

51. STOP / TARGET TEST

Create tests for:

Stop hit.
Target hit.
Neither hit.
Both hit within same candle.
Gap through stop.
Gap through target.

Verify that the configured execution policy is respected.

52. COST TEST

Create tests proving that:

gross PnL

and:

net PnL

are different when costs are configured.

Verify:

fees
spread
slippage

are correctly included.

53. POSITION-SIZING TEST

Create deterministic tests for:

risk budget
stop distance
position quantity

and verify that the calculated risk is consistent with configuration.

54. CAPITAL LIMIT TEST

Test that the engine rejects trades that would violate:

available capital
max exposure
max concurrent positions
55. DAILY LIMIT TEST

Test:

daily profit target
daily loss limit

and verify that new entries are blocked after the configured threshold.

56. DETERMINISM TEST

Run the exact same backtest twice.

Expected:

identical trade ledger
identical equity curve
identical PnL
identical execution sequence

Any difference must fail the test.

57. TIMEZONE TEST

All internal timestamps must remain UTC.

Create a test verifying that:

input timestamps are interpreted correctly;
no accidental local timezone conversion occurs;
chronological ordering remains correct.
58. MULTI-ASSET EVENT ORDER TEST

Create a test where two assets have events at the same timestamp.

Verify that event processing remains deterministic.

The exact ordering policy must be documented.

59. DATA VALIDATION BEFORE BACKTEST

Before a backtest starts, validate:

dataset exists;
dataset metadata exists;
quality status is acceptable;
schema is correct;
timestamps are valid;
timestamps are UTC;
data is chronologically ordered;
duplicates are absent;
required columns exist.

If validation fails:

STOP.

Do not run a partial backtest.

60. CONFIGURATION

Extend the existing configuration system from Prompt 01.

Do not create a second configuration framework.

Add explicit configuration for:

backtest:
  start_date:
  end_date:
  symbols:
  timeframes:

execution:
  order_model:
  slippage_bps:
  spread_bps:
  intrabar_fill_policy:
  gap_policy:

costs:
  maker_fee_rate:
  taker_fee_rate:

capital:
  initial_balance:
  risk_per_trade_pct:

risk:
  max_concurrent_positions:
  max_total_exposure_pct:
  max_asset_exposure_pct:
  daily_profit_target_pct:
  daily_loss_limit_pct:

position_sizing:
  mode:

The exact schema may differ according to the architecture already created in Prompt 01.

Do not duplicate configuration systems.

61. BACKTEST RUN ID

Every backtest must create a unique run ID.

Example:

20260919_182300_abc123

The exact format is your architectural choice.

Every result must be associated with:

run_id
62. RUN REPRODUCIBILITY METADATA

Save:

run_id
timestamp
project version
git commit if available
Python version
dependency versions
configuration snapshot
data identifiers
dataset versions
symbols
timeframes
date range
execution assumptions
fee assumptions
slippage assumptions
spread assumptions
risk assumptions
strategy identifier/version

Never fabricate Git information.

If Git metadata is unavailable:

git_commit: unavailable
63. RESULT DIRECTORY

Create an organized result structure.

For example:

results/
└── backtests/
    └── <run_id>/
        ├── config_snapshot.yaml
        ├── run_metadata.json
        ├── trades.csv
        ├── orders.csv
        ├── fills.csv
        ├── equity_curve.csv
        ├── positions.csv
        ├── execution_events.csv
        ├── metrics.json
        ├── summary.json
        └── logs/

Adapt this to the existing project architecture if Prompt 01 already defines an equivalent structure.

Do not create duplicate result systems.

64. BASIC METRICS

Prompt 03 should calculate basic engine-level metrics.

At minimum:

total_trades
winning_trades
losing_trades
win_rate
gross_pnl
fees
spread_cost
slippage_cost
net_pnl
average_trade_net_pnl
total_R
average_R
max_drawdown
profit_factor
average_holding_duration

These are descriptive engine outputs.

Do not optimize strategies against them yet.

65. METRIC DEFINITIONS

Document every metric.

Especially:

win rate
profit factor
drawdown
R multiple
net PnL

Avoid ambiguous definitions.

For example:

win_rate =
winning_closed_trades / total_closed_trades

unless a different explicit definition is required.

66. HOLDING DURATION

Calculate actual trade holding duration.

Do NOT enforce:

minimum holding time

or:

maximum holding time

in Prompt 03 unless explicitly configured as an execution constraint.

The research objective is to measure how long trades naturally remain open.

67. BASIC VALIDATION PLOTS

Prompt 03 may generate basic technical validation plots.

At minimum:

Equity curve.
Drawdown curve.
Optional trade-entry/exit validation chart.

Do NOT create the complete trade diary yet.

That belongs to Prompt 06.

68. NOTEBOOK

Create:

notebooks/03_backtest_engine_validation.ipynb

The notebook must be executable from beginning to end.

It should:

Section 1 — Environment

Display:

Python version;
project version;
run ID.
Section 2 — Configuration

Load and display:

backtest date range;
symbols;
timeframe;
capital;
risk;
execution assumptions;
fees;
slippage;
spread.
Section 3 — Data

Load real canonical Binance data.

Display:

dataset ID;
symbol;
timeframe;
actual range;
row count;
quality status.
Section 4 — Engine

Instantiate the real backtest engine.

Section 5 — Validation Strategy

Use:

ENGINE_VALIDATION_ONLY

Clearly label it.

Section 6 — Execute

Run the backtest.

Section 7 — Results

Display:

number of trades;
gross PnL;
costs;
net PnL;
win rate;
total R;
drawdown;
average duration.
Section 8 — Equity

Plot the equity curve.

Section 9 — Execution Validation

Show a small sample of:

orders;
fills;
trades.
Section 10 — Final Validation

Run assertions verifying:

no future timestamps were used;
no invalid trades exist;
no impossible negative quantity;
no missing required fields;
accounting is internally consistent.

If any assertion fails:

FAIL

Do not suppress the exception.

69. TEST SUITE

Add unit and integration tests.

At minimum:

tests/unit/test_backtest_engine.py
tests/unit/test_execution_engine.py
tests/unit/test_position_sizing.py
tests/unit/test_accounting.py
tests/unit/test_point_in_time.py
tests/unit/test_intrabar_execution.py
tests/unit/test_cost_model.py
tests/unit/test_risk_limits.py
tests/unit/test_determinism.py

Use the existing project test architecture if different.

Add integration tests for:

real canonical Binance dataset
+
real backtest engine

Do not mock the entire integration test.

70. RESEARCH DATA VS TEST FIXTURES

This distinction must be explicit.

Research data:

REAL BINANCE DATA

Unit-test fixtures:

CONTROLLED TEST DATA

Test fixtures are allowed only to prove deterministic engine behavior.

Never report fixture results as market research.

71. ERROR HANDLING

The engine must fail loudly.

Bad:

try:
    run_backtest()
except Exception:
    return empty_result()

Absolutely prohibited.

Good:

try:
    run_backtest()
except Exception:
    logger.exception(...)
    raise

The user must receive the real exception and traceback.

72. LOGGING

Use the project's existing structured logging system.

Log important events:

BACKTEST_STARTED
DATA_VALIDATED
SIGNAL_RECEIVED
ORDER_CREATED
ORDER_REJECTED
ORDER_FILLED
STOP_TRIGGERED
TARGET_TRIGGERED
POSITION_OPENED
POSITION_CLOSED
RISK_LIMIT_REACHED
BACKTEST_COMPLETED
BACKTEST_FAILED

Do not log sensitive credentials.

73. PERFORMANCE

Do not prematurely optimize.

Correctness is more important than speed.

However, avoid obvious anti-patterns such as:

reloading entire Parquet files for every candle

or:

recomputing the same state unnecessarily

Design the engine so that future Prompt 04 can run many strategies across many assets/timeframes without requiring a complete rewrite.

74. MEMORY SAFETY

The architecture should be compatible with larger datasets.

Avoid unnecessarily duplicating entire datasets in memory.

Use the project's existing data layer where possible.

If the implementation loads a dataset fully into memory for Prompt 03, document why and ensure the architecture can later be optimized.

Do not introduce complexity solely for theoretical scalability.

75. NO LIVE TRADING

Do not implement:

Binance API keys;
account authentication;
real orders;
real deposits;
real withdrawals;
live execution.

Prompt 03 is historical simulation only.

76. NO REAL-MONEY CLAIMS

Do not claim that any strategy is profitable.

Do not claim that the backtest proves future profitability.

Do not claim that a 1% daily target is achievable.

The purpose is to validate the research infrastructure.

77. DOCUMENTATION

Create:

docs/research/BACKTEST_ENGINE_POLICY.md

Document:

point-in-time principles;
event model;
signal timing;
execution timing;
order lifecycle;
stop/target behavior;
intrabar ambiguity;
gap handling;
spread;
slippage;
fees;
position sizing;
capital accounting;
daily limits;
exposure limits;
market-type restrictions;
determinism;
limitations.
78. EXECUTION GUIDE

Create:

docs/execution/PROMPT_03_EXECUTION_GUIDE.md

The guide must explain:

Purpose

What Prompt 03 implements.

Prerequisites

What Prompt 01 and Prompt 02 must have completed.

How to run

Exact commands.

Notebook

Exact notebook to execute.

Configuration

Which values can be changed.

Expected output

What files should be generated.

Validation

How to verify success.

Tests

Exact test commands.

Failure handling

Explain that failures must be investigated rather than bypassed.

Results interpretation

Explain what:

PnL;
R;
win rate;
drawdown;
costs;

mean.

Re-run procedure

How to reproduce the same run.

Known limitations

Especially:

OHLC intrabar ambiguity;
historical execution assumptions;
spread/slippage assumptions;
Spot market restrictions.
Next step

Explain that Prompt 04 will introduce the actual strategy library.

79. README UPDATE

Update:

README.md

with the current project status.

Clearly state:

Prompt 03 — Backtest Engine
STATUS: ...

Do not claim completion until the validation actually passes.

80. PROJECT_STATUS.md UPDATE

Update:

PROJECT_STATUS.md

Include:

Prompt 01: status
Prompt 02: status
Prompt 03: status

For Prompt 03 record:

implementation status;
tests executed;
tests passed;
integration validation;
real dataset used;
run ID;
result location;
known limitations;
next step.

Do not mark Prompt 03 as complete if validation failed.

81. ACCEPTANCE CRITERIA

Prompt 03 is complete ONLY if all applicable criteria below pass.

Architecture
 Existing architecture reused.
 No parallel architecture created.
 No unnecessary duplicate configuration system.
 No strategy-library implementation yet.
Data
 Canonical Prompt 02 data is used.
 Dataset validation runs before backtest.
 Real Binance data is used for integration validation.
Point-in-Time
 No future rows exposed to strategy.
 Multi-timeframe availability is point-in-time correct.
 Signal timing is documented.
 Future-candle mutation test passes.
Execution
 Entry orders work.
 Stop-loss works.
 Take-profit works.
 Gap behavior is explicit.
 Intrabar ambiguity is explicit.
 Slippage is configurable.
 Spread is configurable.
 Fees are configurable.
Accounting
 Cash tracking works.
 Equity tracking works.
 Realized PnL works.
 Unrealized PnL works.
 Net PnL includes costs.
 R multiple is correct.
 Drawdown is correct.
Risk
 Risk-per-trade sizing works.
 Maximum concurrent positions works.
 Total exposure limit works.
 Asset exposure limit works.
 Daily profit target works.
 Daily loss limit works.
 Capital validation works.
Reproducibility
 Same input produces same output.
 Run metadata is stored.
 Configuration snapshot is stored.
 Dataset identifiers are stored.
 Git metadata is recorded when available.
Testing
 Unit tests pass.
 Integration tests pass.
 Look-ahead test passes.
 Future-data access test passes.
 Multi-timeframe test passes.
 Intrabar test passes.
 Cost test passes.
 Position-sizing test passes.
 Risk-limit tests pass.
 Determinism test passes.
Documentation
 BACKTEST_ENGINE_POLICY.md created.
 PROMPT_03_EXECUTION_GUIDE.md created.
 README updated.
 PROJECT_STATUS.md updated.
82. REQUIRED FINAL REPORT

At the end of implementation, provide a concise engineering report containing:

1. IMPLEMENTATION STATUS

State:

COMPLETE

or:

BLOCKED

or:

PARTIAL

Never claim COMPLETE if acceptance criteria failed.

2. COMPONENTS IMPLEMENTED

List the actual components created or modified.

3. TEST RESULTS

Report:

total tests
passed
failed
skipped

Do not hide failures.

4. REAL DATA VALIDATION

Report:

dataset
symbol
timeframe
date range
row count
quality status
5. BACKTEST RUN

Report:

run_id
strategy = ENGINE_VALIDATION_ONLY
trade count
gross PnL
fees
spread cost
slippage cost
net PnL
total R
max drawdown

Clearly state that this is engine validation and NOT strategy research evidence.

6. LOOK-AHEAD VALIDATION

Explicitly report:

Future-data mutation test: PASS/FAIL
Future candle access test: PASS/FAIL
Multi-timeframe PIT test: PASS/FAIL
Signal timing test: PASS/FAIL
7. RESULT FILES

List the actual generated files and paths.

8. KNOWN LIMITATIONS

Be explicit.

Especially:

OHLC cannot reveal exact intrabar order of events;
spread/slippage are assumptions;
Spot does not provide native short selling;
historical simulation is not live execution;
no strategy edge has been established.
9. NEXT STEP

If and ONLY IF Prompt 03 acceptance criteria pass:

READY FOR PROMPT 04

Prompt 04 will implement the strategy library.

If criteria do not pass:

NOT READY FOR PROMPT 04

and clearly identify what must be fixed.

83. FINAL INSTRUCTION

Do not optimize for making the backtest look good.

Optimize for:

CORRECTNESS
REPRODUCIBILITY
POINT-IN-TIME INTEGRITY
EXECUTION REALISM
AUDITABILITY
FAIL-FAST BEHAVIOR

The most important outcome of Prompt 03 is NOT profitability.

The most important outcome is:

We can trust that when Prompt 04 introduces 20–30 strategies, the engine will evaluate them using only information that would actually have been available at each historical moment.

Do not move to Prompt 04 until this foundation is validated.
