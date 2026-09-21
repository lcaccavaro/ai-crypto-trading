# PROMPT 04 — STRATEGY LIBRARY & MULTI-ASSET / MULTI-TIMEFRAME RESEARCH

## ROLE

You are acting as a:

- Principal Quantitative Research Engineer
- Senior Quantitative Strategy Researcher
- Python Architecture Specialist
- Systematic Trading Research Engineer

You are continuing the implementation of the existing quantitative research laboratory.

The project has already completed:

- Prompt 01 — Project Foundation / Architecture / Reproducibility
- Prompt 02 — Binance Market Data Ingestion / Normalization / Data Quality
- Prompt 03 — Point-in-Time Backtest Engine / Historical Execution Simulator

Your responsibility in this prompt is to implement:

> A standardized, extensible, point-in-time strategy library capable of evaluating many different short-term trading hypotheses across multiple assets and timeframes using the exact same validated backtest engine.

---

# 1. ABSOLUTE PROJECT RULES

These rules are mandatory.

## 1.1 Inspect Before Modifying

Before writing code:

1. Inspect the complete existing repository.
2. Inspect Prompt 01 implementation.
3. Inspect Prompt 02 implementation.
4. Inspect Prompt 03 implementation.
5. Inspect:
   - README.md
   - PROJECT_STATUS.md
   - configuration files
   - architecture documentation
   - research principles
   - data policy
   - backtest engine policy
   - existing tests
   - notebooks
   - data catalog
   - result structure
6. Verify that Prompt 03 is actually functional.

Do not create a parallel architecture.

Extend the existing architecture.

---

# 2. DO NOT PROCEED IF PROMPT 03 IS NOT VALIDATED

Before implementing the strategy library, verify that:

- Prompt 03 acceptance criteria passed;
- the backtest engine works;
- point-in-time tests pass;
- future-data mutation tests pass;
- execution tests pass;
- cost tests pass;
- deterministic tests pass;
- real Binance data can run through the engine.

If Prompt 03 is broken:

STOP.

Do not work around it.

Do not create another backtest engine.

Do not create fake results.

Do not mock the engine.

Report the actual failure.

---

# 3. PRIMARY OBJECTIVE

Implement a standardized strategy framework and an initial research library containing approximately:

> 20–30 distinct strategy implementations.

These strategies must be:

- modular;
- independently identifiable;
- configurable;
- reproducible;
- point-in-time safe;
- compatible with multiple assets;
- compatible with multiple timeframes;
- executable through the existing Prompt 03 engine;
- independently testable;
- comparable using the same execution assumptions.

The purpose is NOT to prove that any strategy is profitable.

The purpose is to create a broad, structured research universe that can later be evaluated objectively.

---

# 4. IMPORTANT RESEARCH PHILOSOPHY

Do NOT build 30 cosmetic variations of the same strategy.

The initial library should contain different classes of hypotheses.

We want to investigate whether different forms of market information produce different short-term behavior.

The library should therefore contain diversity across:

- trend;
- momentum;
- mean reversion;
- volatility;
- breakout;
- volume;
- price/volume interaction;
- multi-indicator confirmation;
- market structure;
- regime-aware behavior.

Do not use future information to classify regimes.

---

# 5. STRATEGY LIBRARY IS A RESEARCH TOOL

Do not optimize strategies to produce attractive backtest results.

Do not:

- search thousands of parameters;
- select the best parameters;
- select the best strategies;
- remove losing strategies;
- tune strategies against the final test period;
- rank strategies by profitability;
- optimize specifically for historical data.

Those activities belong to later research stages.

Prompt 04 is about:

> Building a broad and controlled strategy universe.

---

# 6. STRATEGY INTERFACE

Every strategy MUST implement the same interface established by Prompt 01/03.

If the existing interface is inadequate, extend it rather than creating a second strategy interface.

Conceptually:

```python
class Strategy(ABC):

    @property
    def metadata(self) -> StrategyMetadata:
        ...

    def initialize(self, context: StrategyContext) -> None:
        ...

    def on_market_event(
        self,
        context: StrategyContext
    ) -> Signal | None:
        ...

    def reset(self) -> None:
        ...

Adapt this to the actual project architecture.

Do not blindly copy this example if Prompt 01 already defines a better interface.

7. STRATEGY MUST NOT CONTROL EXECUTION

Strategies should answer:

"Is there a trading opportunity?"

They should NOT directly control:

fills;
fees;
slippage;
account balance;
portfolio accounting;
order execution;
future candles.

The separation must remain:

Strategy
    ↓
Signal
    ↓
Risk Layer
    ↓
Order
    ↓
Execution Engine
    ↓
Fill
    ↓
Position
    ↓
Trade
8. STRATEGY MUST NOT ACCESS THE FULL DATASET

A strategy must never receive the entire historical DataFrame.

Bad:

strategy.evaluate(full_dataframe)

Good:

strategy.evaluate(point_in_time_context)

The strategy must only receive information available at the simulated timestamp.

9. POINT-IN-TIME REQUIREMENT

Every indicator must be calculated using information available at or before the current decision point.

Examples:

Allowed:

EMA(t)
RSI(t)
ATR(t)
Volume(t)
RollingMean(t)
RollingStd(t)

if these values are calculated exclusively from data available at t.

Forbidden:

EMA(t+1)
RSI(t+1)
future volatility
future volume
future high/low
future strategy performance
future regime
future trade outcome
10. INDICATOR CALCULATION

Indicators must be calculated in a point-in-time-safe manner.

Do not calculate indicators on the entire dataset and then accidentally expose future-derived values.

The architecture should preferably support:

historical state
+
incremental indicator update

or an equivalent safe mechanism.

If indicators are precomputed for performance reasons, the implementation must prove that each indicator value at timestamp t depends only on observations available at or before t.

11. WARM-UP PERIOD

Indicators requiring historical observations must have an explicit warm-up period.

Example:

EMA(200)

cannot generate a valid signal before sufficient historical data exists.

Do NOT:

fill unavailable indicators with arbitrary values;
generate signals during invalid warm-up periods;
silently forward-fill indicator values.

The strategy should explicitly return:

NO_SIGNAL / NOT_READY

until the required history exists.

12. STRATEGY METADATA

Every strategy must expose metadata.

At minimum:

strategy_id
name
version
category
description
required_features
required_timeframes
supported_sides
default_parameters
parameter_schema
warmup_period
research_hypothesis

Example:

strategy_id: EMA_CROSS_001
version: "1.0.0"
category: trend
supported_sides:
  - long
required_timeframes:
  - 5m
13. STRATEGY VERSIONING

Every strategy must have an explicit version.

Example:

EMA_CROSS_001 v1.0.0

If logic changes materially:

v1.1.0

or:

v2.0.0

depending on the nature of the change.

A backtest must record the exact strategy version.

14. NO HIDDEN PARAMETERS

Every strategy parameter must be visible in configuration.

Do not bury values such as:

EMA fast = 9
EMA slow = 21
RSI = 70
ATR multiplier = 2

inside implementation code.

Parameters must be:

explicit;
configurable;
recorded in the run metadata.
15. INITIAL STRATEGY UNIVERSE

Implement approximately 20–30 strategies.

Target:

24 strategies

unless the existing architecture makes another number more appropriate.

The strategies should be distributed across different hypothesis families.

Recommended initial distribution:

Trend Following:              4
Momentum:                     4
Mean Reversion:               4
Breakout:                     4
Volatility:                   3
Volume / Price-Volume:        3
Multi-Indicator Confirmation: 2
Market Structure / Regime:    2
--------------------------------
Total:                       26

The exact number can vary slightly, but the final library must contain genuine diversity.

16. STRATEGY GROUP A — TREND FOLLOWING

Implement approximately four trend-following strategies.

Examples:

A1 — EMA Crossover

Concept:

Fast EMA crosses above Slow EMA
→ long

and optionally:

Fast EMA crosses below Slow EMA
→ short

respecting market-side configuration.

Parameters:

fast_period
slow_period
A2 — Triple EMA Alignment

Example hypothesis:

EMA_fast > EMA_medium > EMA_slow

for bullish alignment.

Parameters:

fast_period
medium_period
slow_period
A3 — Price vs Long-Term EMA

Example:

price > EMA_long
AND
short-term momentum confirms

Keep the logic explicit.

A4 — EMA Slope Trend

Measure whether an EMA is rising/falling.

Example:

EMA(t) > EMA(t-n)

for bullish trend confirmation.

Do not use future values.

17. STRATEGY GROUP B — MOMENTUM

Implement approximately four momentum strategies.

Examples:

B1 — RSI Momentum

Use RSI to identify directional momentum.

Do not automatically assume conventional thresholds are optimal.

Keep thresholds configurable.

B2 — ROC Momentum

Use Rate of Change.

Parameters:

lookback
threshold
B3 — MACD Momentum

Use:

MACD
signal line
histogram

for directional momentum.

B4 — Multi-Period Momentum

Combine short and medium momentum measurements.

Example:

ROC_short > threshold
AND
ROC_medium > threshold

The exact formula must be documented.

18. STRATEGY GROUP C — MEAN REVERSION

Implement approximately four mean-reversion strategies.

Examples:

C1 — Bollinger Band Reversion

Hypothesis:

Price moving significantly away from a rolling mean may revert.

Parameters:

period
standard_deviation_multiplier
C2 — RSI Extreme Reversion

Use extreme RSI conditions as a mean-reversion hypothesis.

Do not assume the hypothesis is valid.

C3 — Z-Score Mean Reversion

Calculate:

z_score =
(price - rolling_mean)
/
rolling_std

Use configurable thresholds.

C4 — Distance From EMA

Measure standardized or percentage distance from a moving average.

Do not use future information.

19. STRATEGY GROUP D — BREAKOUT

Implement approximately four breakout strategies.

Examples:

D1 — Donchian Breakout

Long when price breaks the previous rolling high.

CRITICAL:

The breakout threshold must use the PREVIOUS completed window.

For example:

rolling_high.shift(1)

or equivalent point-in-time-safe logic.

Do NOT compare price against a window that includes the current breakout candle in a way that creates look-ahead or invalid signal semantics.

D2 — Range Breakout

Detect breakouts from a configurable rolling range.

D3 — Volatility Breakout

Breakout combined with an expansion in volatility.

D4 — Opening/Session Range Breakout

Only implement if the project's market/session model supports it correctly.

If Binance 24/7 session semantics make this inappropriate, replace it with another objectively defined breakout hypothesis.

Do not invent arbitrary session boundaries without documentation.

20. STRATEGY GROUP E — VOLATILITY

Implement approximately three volatility-based strategies.

Examples:

E1 — ATR Expansion

Detect an unusual increase in ATR/volatility.

E2 — Volatility Compression → Expansion

Detect compressed volatility followed by expansion.

E3 — Bollinger Band Width Expansion

Use Bollinger Band width as a volatility regime/expansion feature.

21. STRATEGY GROUP F — VOLUME / PRICE-VOLUME

Implement approximately three strategies.

Examples:

F1 — Volume Spike Confirmation

Price movement combined with unusually high volume.

F2 — Volume-Weighted Momentum

Combine price momentum with relative volume.

F3 — Volume Breakout Confirmation

Breakout only when volume exceeds a rolling baseline.

All rolling baselines must be point-in-time safe.

22. STRATEGY GROUP G — MULTI-INDICATOR CONFIRMATION

Implement approximately two strategies.

Examples:

G1 — Trend + Momentum Confirmation

Example conceptual structure:

trend condition
AND
momentum condition
AND
volume confirmation
G2 — Trend + Volatility + Momentum

Combine independent dimensions.

The purpose is to test whether confirmation improves selectivity.

Do not optimize the combination yet.

23. STRATEGY GROUP H — MARKET STRUCTURE / REGIME

Implement approximately two strategies.

These must remain strictly point-in-time.

Possible examples:

H1 — Higher-High / Higher-Low Structure

Use only completed historical observations.

H2 — Volatility-Regime Conditional Strategy

Example:

if current volatility regime == expansion:
    use breakout behavior
else:
    no signal

The regime must be calculated using only information available at the current timestamp.

Do not use future volatility.

24. STRATEGY DIVERSITY REQUIREMENT

After implementation, produce a table showing:

strategy_id
category
core hypothesis
indicators/features
timeframe requirements
long/short support
parameter count
warmup period

This table must demonstrate that the library is not merely 20 variations of EMA crossover.

25. ENTRY SIGNAL ONLY

Prompt 04 strategies should primarily generate:

ENTRY_SIGNAL

They should not independently implement:

portfolio risk management;
account-level daily stops;
capital allocation;
strategy shutdown;
global exposure;
order execution.

Those belong to the existing engine and Prompt 05.

26. STOP AND TARGET HANDLING

Strategies may provide an initial stop reference if the architecture requires it.

For example:

stop_distance

or:

stop_price

However:

Execution of stop-loss and take-profit remains the responsibility of the backtest/execution layer.

Do not duplicate execution logic inside each strategy.

27. INITIAL RISK/REWARD

Prompt 03 already supports configurable RR.

The strategy should NOT hard-code:

3:1

unless that is explicitly part of the strategy hypothesis.

Prefer:

signal
+
initial risk reference

with the execution/risk layer determining:

target = entry ± risk × RR

where appropriate.

28. SIGNAL QUALITY

Every generated signal should contain enough information to explain why it happened.

For example:

{
  "strategy_id": "EMA_CROSS_001",
  "signal": "LONG",
  "timestamp": "...",
  "reason": "fast EMA crossed above slow EMA",
  "features": {
    "ema_fast": ...,
    "ema_slow": ...
  }
}

The exact schema should follow the existing domain model.

Do not generate verbose text unnecessarily.

The information should be structured and machine-readable.

29. NO FUTURE PERFORMANCE IN SIGNALS

A strategy MUST NOT use:

previous backtest result
future trade outcome
future strategy win rate
future strategy ranking
future regime classification
future volatility
future candle

to create a signal.

Prompt 05 will later introduce dynamic strategy management, but it must still remain point-in-time.

30. NO ADAPTIVE OPTIMIZATION

Do not implement:

auto-tuning
parameter optimization
genetic optimization
grid search
Bayesian optimization
machine learning optimization

in Prompt 04.

Every strategy must use explicit configured parameters.

31. DEFAULT PARAMETERS

Every strategy needs a reasonable default parameter set.

These defaults are NOT claimed to be optimal.

They exist to make the strategy executable.

Document this clearly.

Example:

EMA_CROSS_001:
  fast_period: 9
  slow_period: 21

The values must not be presented as empirically optimized.

32. PARAMETER SCHEMA

Every strategy must expose its parameters programmatically.

Example:

strategy.parameters

should allow the system to determine:

parameter name;
type;
default;
allowed range if applicable;
description.

This will later support Prompt 07 sensitivity analysis.

33. MULTIPLE ASSETS

Every strategy must be capable of running independently on:

BTCUSDT
ETHUSDT
SOLUSDT

or any other configured symbol for which the dataset exists.

Do not hard-code BTC.

34. MULTIPLE TIMEFRAMES

Strategies must support configurable timeframes where logically appropriate.

At minimum the framework must be capable of:

1m
3m
5m
15m
30m
1h
2h
4h

The actual supported timeframes may vary by strategy.

Do not force a strategy onto an inappropriate timeframe merely to fill a matrix.

35. STRATEGY COMPATIBILITY

Every strategy must explicitly expose:

supported_timeframes
supported_market_types
supported_sides
required_features

If a strategy cannot operate under a given configuration:

reject it explicitly.

Do not silently skip it.

36. STRATEGY REGISTRY

Implement a central strategy registry.

Conceptually:

strategy_registry.register(...)
strategy_registry.get(...)
strategy_registry.list(...)

It must support:

get strategy by ID
list all strategies
filter by category
inspect metadata
instantiate configured strategy

Avoid dynamic magic that makes debugging difficult.

37. CONFIGURATION-DRIVEN STRATEGY SELECTION

The backtest should be able to receive configuration such as:

strategies:
  enabled:
    - EMA_CROSS_001
    - RSI_MOMENTUM_001
    - DONCHIAN_BREAKOUT_001

Do not hard-code the enabled strategy list in Python.

38. STRATEGY MATRIX

Create a configuration mechanism capable of expressing:

strategy
+
symbol
+
timeframe
+
parameters

Example:

strategy_instances:

  - strategy_id: EMA_CROSS_001
    symbol: BTCUSDT
    timeframe: 5m

  - strategy_id: EMA_CROSS_001
    symbol: ETHUSDT
    timeframe: 15m

  - strategy_id: RSI_MOMENTUM_001
    symbol: SOLUSDT
    timeframe: 5m

This is important.

The same strategy is a separate research instance when applied to a different:

asset;
timeframe;
parameter configuration.
39. STRATEGY INSTANCE ID

Generate a deterministic strategy instance identifier.

Example:

EMA_CROSS_001__BTCUSDT__5m__v1.0.0

The exact naming scheme can differ.

It must be:

unique;
deterministic;
human-readable.
40. STRATEGY STATE ISOLATION

Every strategy instance must maintain independent state.

For example:

BTCUSDT / EMA / 5m

must not accidentally share:

ETHUSDT / EMA / 15m

state.

This includes:

indicator state;
warm-up state;
previous signal state;
crossover state;
internal buffers.
41. NO CROSS-CONTAMINATION

Create tests proving that:

running BTC does not change ETH results;
running 5m does not modify 15m state;
strategy instance A does not modify strategy instance B.
42. INDICATOR LIBRARY

If the project does not already have one, create a reusable indicator layer.

Do not implement indicator formulas independently inside every strategy.

Possible indicators:

SMA
EMA
WMA
RSI
MACD
ATR
Bollinger Bands
Rolling Std
ROC
Z-Score
Donchian Channels
Relative Volume

Use a consistent interface.

43. INDICATOR VALIDATION

Each indicator should have unit tests against independently calculated expected values.

Tests should include:

normal values;
warm-up;
NaN handling;
insufficient history;
constant price;
zero volatility;
zero volume where applicable.

Do not silently replace mathematically undefined values with arbitrary numbers.

44. ZERO-VOLATILITY HANDLING

For calculations such as:

z-score

where:

rolling_std = 0

do not divide by zero.

The strategy should produce:

NOT_READY

or:

NO_SIGNAL

according to the defined semantics.

Do not inject arbitrary epsilon values unless mathematically justified and documented.

45. SIGNAL DUPLICATION

Prevent accidental repeated signals on every candle when the strategy is intended to signal only on a transition.

For example:

EMA crossover

should generally signal on the crossing event, not every candle while:

EMA_fast > EMA_slow

unless explicitly designed as a state-based strategy.

Document the distinction between:

event-based signal

and:

state-based signal
46. SIGNAL DEBOUNCING

Do not add arbitrary cooldowns simply to reduce trade count.

If a strategy requires a cooldown, it must be:

part of the explicit strategy hypothesis;
configurable;
documented.

Do not use cooldowns to artificially improve historical results.

47. POSITION-AWARE SIGNALS

Strategies should know enough about their current position state to avoid obviously invalid duplicate entries.

However:

Portfolio-level position/risk decisions remain outside the strategy.

For example, the strategy may know:

currently long

but should not decide:

portfolio exposure is 83%, therefore reject another strategy

That belongs to risk management.

48. LONG / SHORT

Where supported, strategies may generate:

LONG
SHORT

But market configuration controls whether the side is actually permitted.

For Binance Spot:

SHORT

must be rejected unless the architecture explicitly models another market type.

Do not pretend Spot shorting is native.

49. STRATEGY RESEARCH LABEL

Every strategy must have a research hypothesis.

Example:

Hypothesis:
Short-term momentum following may persist after a statistically significant
directional move accompanied by confirmation from relative volume.

This is a research hypothesis, not a claim.

50. STRATEGY IMPLEMENTATION QUALITY

Each strategy must be:

readable;
deterministic;
testable;
independently executable;
documented;
small enough to understand;
free of hidden global state.

Avoid giant strategy classes containing dozens of unrelated conditions.

51. NO "MAGIC" STRATEGY

Do not create one giant strategy with dozens of indicators and call it:

AI strategy

or:

Ultimate strategy

The purpose is scientific comparison of distinct hypotheses.

52. STRATEGY UNIT TESTS

Every strategy must have tests covering at minimum:

Initialization.
Metadata.
Required warm-up.
No signal during insufficient history.
Correct signal generation for a deterministic fixture.
No future data dependency.
Parameter validation.
Reset behavior.
State isolation.

Do not test only that the class imports.

53. FUTURE DATA MUTATION TEST

For representative strategies from EACH strategy category:

Run the strategy over a historical fixture.
Modify only future candles.
Re-run.
Compare signals before the mutation point.

Expected:

All earlier signals remain identical.

This test is mandatory.

54. STRATEGY PARAMETER VALIDATION

Reject invalid parameters.

Examples:

fast_period <= 0
slow_period <= fast_period
negative threshold
invalid timeframe
unsupported side

Do not silently correct invalid parameters.

Raise a clear error.

55. NO AUTOMATIC PARAMETER CORRECTION

Bad:

if fast_period >= slow_period:
    slow_period = fast_period + 1

Do not do this.

Instead:

INVALID_CONFIGURATION

with a clear explanation.

The researcher must know the configuration is invalid.

56. STRATEGY BATCH EXECUTION

Implement the ability to execute multiple strategy instances through the same backtest framework.

For example:

26 strategies
×
3 symbols
×
multiple timeframes

The exact number of combinations should be configuration-driven.

Do not assume that every strategy must run on every combination.

57. IMPORTANT — DO NOT OPTIMIZE THE MATRIX

Do not automatically choose combinations based on:

highest profit;
highest win rate;
lowest drawdown;
highest Sharpe;
previous results.

Prompt 05/07 will address research selection.

Prompt 04 only creates and executes the defined research universe.

58. RESEARCH RUN IDENTIFICATION

Every strategy batch run must preserve:

run_id
strategy_id
strategy_version
strategy_instance_id
symbol
timeframe
parameters

in the output.

59. OUTPUTS

Extend the existing results architecture.

Produce machine-readable strategy-level outputs.

At minimum:

strategy_results.csv
strategy_instances.csv
signals.csv
trades.csv
equity_curve.csv
metrics.json
run_metadata.json

Reuse Prompt 03 output mechanisms where possible.

Do not create an incompatible second reporting format.

60. SIGNAL LEDGER

Create a structured signal ledger.

At minimum:

timestamp
strategy_id
strategy_version
strategy_instance_id
symbol
timeframe
signal
reason
indicator_snapshot
parameters

This will be critical later for diagnosing why trades happened.

61. STRATEGY-LEVEL RESULTS

For each strategy instance calculate at least:

strategy_id
strategy_version
symbol
timeframe
parameter_hash
trade_count
winning_trades
losing_trades
gross_pnl
net_pnl
total_R
average_R
win_rate
profit_factor
max_drawdown
average_holding_duration

Do not rank them.

Do not call one "best".

These are raw research measurements.

62. COMPARABILITY

All strategies must use the same:

market data;
date range;
execution model;
fees;
spread assumptions;
slippage assumptions;
capital model;
risk model;

when comparison is intended.

Otherwise results are not directly comparable.

Document this principle.

63. EXPOSURE TO DIFFERENT MARKET CONDITIONS

The initial strategy universe should not be intentionally designed only for bullish markets.

The research period should use the configured historical range from Prompt 02/03.

Do not cherry-pick dates where a strategy looks good.

64. NO DATA SNOOPING

Do not inspect the final results and then modify strategy rules during the same Prompt 04 execution to improve them.

If an implementation bug is discovered:

fix the bug;
document the change;
rerun;
report the new run.

Do not silently iterate until results look good.

65. STRATEGY CHANGES DURING IMPLEMENTATION

If a strategy cannot be implemented as originally planned because the hypothesis is ambiguous:

STOP and document the issue.

Do not silently transform:

strategy A

into:

strategy B

If replacement is genuinely necessary, explain:

original hypothesis;
reason it could not be implemented;
replacement hypothesis;
exact change.
66. NOTEBOOK

Create:

notebooks/04_strategy_library_validation.ipynb

The notebook must be executable from beginning to end.

Required sections:

Section 1 — Environment

Display:

Python version;
project version;
Git commit if available;
run ID.
Section 2 — Data

Display:

symbols;
timeframes;
dataset IDs;
actual date ranges;
quality status.
Section 3 — Strategy Registry

Display the complete strategy catalog.

Section 4 — Strategy Metadata

Display:

strategy ID;
category;
hypothesis;
parameters;
warm-up;
supported sides;
supported timeframes.
Section 5 — Single Strategy Validation

Run representative strategies individually.

Section 6 — Batch Validation

Execute the configured strategy matrix.

Section 7 — Signal Inspection

Show samples from the signal ledger.

Section 8 — Trade Inspection

Show samples from the trade ledger.

Section 9 — Results

Display descriptive metrics for every strategy instance.

DO NOT rank them.

Section 10 — Point-in-Time Validation

Run representative future-data mutation checks.

Section 11 — Final Validation

Run assertions and tests.

Any error must stop execution visibly.

67. BASIC VISUAL VALIDATION

For representative strategies, create charts showing:

price;
relevant indicators;
signal timestamps;
entry;
exit.

Do not create the complete trade diary yet.

Prompt 06 will build the complete visual research/reporting layer.

The purpose here is only to confirm:

the strategy generated the signal where the implementation says it should.

68. TEST MATRIX

Create tests covering:

Framework
strategy interface;
registry;
metadata;
configuration;
instance isolation.
Indicators
EMA;
SMA;
RSI;
MACD;
ATR;
Bollinger;
ROC;
Z-score;
Donchian;
relative volume.
Strategies

Every implemented strategy must have dedicated tests.

Point-in-Time
future mutation;
warm-up;
current candle semantics;
multi-timeframe semantics.
Integration
real Binance data;
Prompt 03 engine;
multiple strategy instances;
multiple symbols;
multiple timeframes.
69. TEST FIXTURES

Controlled synthetic fixtures are allowed ONLY for deterministic unit tests.

They must never be presented as market research.

Use them to test specific conditions such as:

EMA crossover
RSI threshold
Donchian breakout
Bollinger excursion
volume spike

The fixtures must be:

deterministic;
minimal;
documented;
isolated from research output.
70. REAL DATA INTEGRATION TEST

At least one complete integration test must execute:

real Binance canonical dataset
→
strategy
→
Prompt 03 backtest engine
→
signals
→
orders
→
fills
→
trades
→
metrics

No mocked engine.

No mocked market data.

71. MULTI-ASSET VALIDATION

Run at least one strategy across:

BTCUSDT
ETHUSDT
SOLUSDT

where the configured datasets are available.

Verify that:

states remain isolated;
signals are associated with the correct symbol;
trades remain associated with the correct strategy instance;
portfolio accounting remains correct.
72. MULTI-TIMEFRAME VALIDATION

Run at least one strategy across multiple configured timeframes.

Verify:

correct dataset;
correct timeframe;
correct indicator calculation;
correct strategy instance;
no state contamination.
73. STRATEGY INSTANCE ISOLATION TEST

Create a test proving:

EMA/BTC/5m

does not affect:

EMA/ETH/5m

and:

EMA/BTC/15m
74. REPRODUCIBILITY

Run the same strategy batch twice.

The outputs must be deterministic.

At minimum:

signal ledger;
trade ledger;
metrics;
strategy instance definitions.

must match.

75. NO RANDOMIZATION

Do not introduce random sampling.

Do not randomly select:

strategies;
assets;
timeframes;
parameters;
trades.

The research universe must be deterministic.

76. PERFORMANCE

The architecture must be capable of running many strategy instances without duplicating all market data unnecessarily.

Do not prematurely optimize.

But avoid obvious inefficiencies such as:

loading the same Parquet dataset independently for every strategy instance

if the existing architecture can safely share immutable market data.

77. MEMORY SAFETY

Strategy instances must not maintain unbounded historical copies of the entire dataset.

Use:

controlled rolling windows;
incremental state;
bounded history;

where appropriate.

The exact implementation depends on the indicator requirements.

78. NO FRONTEND

Do not build:

web application;
dashboard frontend;
API server;
React interface.

Prompt 06 will focus on research reporting.

79. NO LIVE TRADING

Do not implement:

Binance authentication;
live orders;
account management;
real-money execution.

This remains historical research.

80. DOCUMENTATION

Create:

docs/research/STRATEGY_LIBRARY_POLICY.md

Document:

strategy philosophy;
strategy interface;
metadata;
point-in-time rules;
indicator rules;
warm-up;
signal semantics;
strategy categories;
parameter handling;
strategy versioning;
state isolation;
supported market types;
supported timeframes;
research limitations.
81. STRATEGY CATALOG

Create a machine-readable catalog.

For example:

data/metadata/strategy_catalog.json

or the equivalent location established by the existing architecture.

It must contain every strategy.

Example structure:

{
  "strategy_id": "EMA_CROSS_001",
  "version": "1.0.0",
  "category": "trend",
  "hypothesis": "...",
  "parameters": {},
  "supported_timeframes": [],
  "supported_sides": [],
  "required_features": []
}
82. EXECUTION GUIDE

Create:

docs/execution/PROMPT_04_EXECUTION_GUIDE.md

The guide must explain:

Purpose

What Prompt 04 adds.

Prerequisites

Prompt 01–03 requirements.

Strategy catalog

How strategies are organized.

Configuration

How to enable strategies.

Strategy matrix

How to configure:

strategy × asset × timeframe
Notebook

How to execute:

notebooks/04_strategy_library_validation.ipynb
Tests

Exact commands.

Results

Where outputs are stored.

Reproducibility

How to repeat the same experiment.

Interpretation

Explain that raw strategy results are descriptive research outputs, NOT proof of future profitability.

Known limitations

Explain:

no optimization;
no walk-forward;
no strategy ranking;
no regime optimization;
no parameter search.
Next step

Prompt 05.

83. README UPDATE

Update:

README.md

with:

Prompt 04 — Strategy Library
STATUS: ...

Do not mark complete until validation succeeds.

84. PROJECT_STATUS.md UPDATE

Update:

PROJECT_STATUS.md

Record:

Prompt 01 status;
Prompt 02 status;
Prompt 03 status;
Prompt 04 status;
strategy count;
categories;
tests;
integration run;
real datasets used;
result location;
known limitations;
next step.
85. ACCEPTANCE CRITERIA

Prompt 04 is complete ONLY if:

Framework
 Existing strategy interface reused/extended.
 Strategy registry implemented.
 Strategy metadata implemented.
 Strategy versioning implemented.
 Strategy instance IDs implemented.
 Configuration-driven strategy selection implemented.
Strategy Library
 Approximately 20–30 strategies implemented.
 At least ~6 distinct strategy families represented.
 Strategies are genuinely different hypotheses.
 No giant "ultimate strategy".
 No automatic parameter optimization.
Indicators
 Reusable indicator layer implemented.
 Indicators have tests.
 Warm-up behavior is explicit.
 Zero-volatility behavior is explicit.
Point-in-Time
 Strategies receive point-in-time data only.
 No future data access.
 No future indicator values.
 Multi-timeframe PIT semantics preserved.
 Future-data mutation tests pass.
Multi-Asset
 Multiple symbols supported.
 Strategy state isolated.
 BTC/ETH/SOL integration validated where data exists.
Multi-Timeframe
 Multiple timeframes supported.
 Strategy instances isolated by timeframe.
Backtest Integration
 Strategies use Prompt 03 engine.
 No second backtest engine created.
 Costs remain controlled by execution layer.
 Risk remains controlled by risk/execution layer.
Reproducibility
 Strategy versions recorded.
 Parameters recorded.
 Strategy instances recorded.
 Same run produces deterministic results.
Documentation
 STRATEGY_LIBRARY_POLICY.md created.
 PROMPT_04_EXECUTION_GUIDE.md created.
 README updated.
 PROJECT_STATUS.md updated.
 Strategy catalog generated.
86. IMPORTANT RESEARCH OUTPUT RULE

Do NOT produce a table such as:

1. Best strategy
2. Second best strategy
3. Worst strategy

Do not rank strategies.

Instead produce a neutral research table:

strategy_id
category
symbol
timeframe
trade_count
win_rate
net_pnl
total_R
max_drawdown
profit_factor
average_duration

The purpose is to expose the raw evidence.

Prompt 07 will later define the formal methodology for robustness and strategy evaluation.

87. DO NOT REMOVE STRATEGIES BECAUSE THEY LOSE

A strategy generating negative results is still a valid research result if:

the implementation is correct;
the hypothesis is clearly defined;
the data is valid;
the execution model is consistent.

Do not remove a strategy simply because the initial backtest is negative.

The objective is to understand the research space.

88. DO NOT IMPROVE STRATEGIES BASED ON INITIAL RESULTS

After seeing the first results:

DO NOT immediately:

change thresholds;
add indicators;
remove filters;
alter stop logic;
change entry timing;
change timeframes;
modify parameters;

just because results look poor.

If an implementation bug exists, fix the bug.

If the hypothesis itself needs revision, that should become a separately documented research iteration.

Do not mix implementation and optimization.

89. FINAL ENGINEERING REPORT

At the end of implementation provide:

1. STATUS

One of:

COMPLETE
PARTIAL
BLOCKED

Never claim COMPLETE if acceptance criteria are not satisfied.

2. STRATEGY COUNT

Report:

total strategies
total categories
total strategy instances executed
3. STRATEGY CATALOG

Provide the actual catalog with:

strategy_id
category
hypothesis
parameters
timeframes
supported sides
warmup
4. TEST RESULTS

Report:

total tests
passed
failed
skipped

Do not hide failures.

5. INTEGRATION VALIDATION

Report:

real dataset(s)
symbols
timeframes
date range
strategy instances
run_id
6. POINT-IN-TIME VALIDATION

Explicitly report:

future-data mutation tests
multi-timeframe tests
warm-up tests
state-isolation tests
determinism tests
7. RESULTS LOCATION

List actual output paths.

8. KNOWN LIMITATIONS

Clearly state:

no parameter optimization;
no strategy ranking;
no walk-forward;
no regime optimization;
no machine learning;
no live trading;
no profitability claim.
9. NEXT STEP

If and ONLY IF Prompt 04 acceptance criteria pass:

READY FOR PROMPT 05

Otherwise:

NOT READY FOR PROMPT 05

and identify exactly what must be fixed.

90. FINAL INSTRUCTION

Do not optimize for attractive results.

Do not optimize for a high win rate.

Do not optimize for a high profit factor.

Do not optimize for a high net PnL.

The objective of Prompt 04 is:

Build a broad, clean, reproducible and point-in-time-safe strategy research universe that can later be evaluated objectively.

The system should allow us to ask, in later prompts:

Which hypotheses survive realistic costs?
Which strategies behave differently from each other?
Which strategies work in different market conditions?
Which strategies are redundant?
Which strategies have unstable performance?
Which strategies complement one another?
Which strategies fail under specific regimes?
Which strategies remain robust out-of-sample?

But DO NOT answer those questions yet.

Prompt 04 builds the research universe.

Prompt 05 will introduce portfolio-level risk management, strategy state management, strategy scoring and controlled activation/deactivation.

Prompt 06 will build the research diary and visualization layer.

Prompt 07 will perform robustness and out-of-sample research.

Prompt 08 will introduce paper-trading/realtime validation using the same validated core.

Do not skip steps.
Do not change the architecture.
Do not optimize prematurely.
Do not use future information.
Do not fabricate results.
Do not hide failures.