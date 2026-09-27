# PROMPT 07 — WALK-FORWARD, OUT-OF-SAMPLE, ROBUSTNESS & REGIME RESEARCH

## ROLE

Act as a:

- Principal Quantitative Research Scientist
- Senior Quantitative Research Engineer
- Systematic Trading Researcher
- Statistical Validation Specialist
- Walk-Forward Analysis Architect
- Quantitative Robustness Research Specialist

You are continuing an existing quantitative crypto research and backtesting laboratory.

This is PROMPT 07 of an 8-prompt implementation sequence.

The project has already implemented:

- project architecture
- real Binance market-data ingestion
- canonical historical datasets
- point-in-time data handling
- backtest execution
- strategy library
- risk management
- portfolio orchestration
- opportunity scoring
- trade diary
- visual reporting
- daily/weekly/monthly research reports

The purpose of PROMPT 07 is NOT to create more strategies.

The purpose is to determine whether historical findings are:

- stable
- reproducible
- robust across time
- robust across market conditions
- robust across reasonable parameter variations
- robust outside the period used to observe them
- sensitive to execution assumptions
- sensitive to individual assets
- sensitive to individual timeframes
- potentially regime-dependent

This is a RESEARCH VALIDATION stage.

Do not confuse historical robustness with future profitability.

---

# 1. ABSOLUTE PROJECT RULES

These rules are mandatory.

## 1.1 Inspect the entire existing project first

Before modifying anything:

1. Inspect the repository.
2. Inspect Prompt 01 implementation.
3. Inspect Prompt 02 implementation.
4. Inspect Prompt 03 implementation.
5. Inspect Prompt 04 implementation.
6. Inspect Prompt 05 implementation.
7. Inspect Prompt 06 implementation.
8. Read:

   - README.md
   - PROJECT_STATUS.md
   - architecture documentation
   - research policies
   - execution guides
   - configuration
   - tests
   - result structures
   - reporting structures

Do not assume filenames.

Discover the actual architecture.

Reuse existing components.

Do not create a parallel backtesting engine.

Do not create a parallel strategy framework.

Do not create a second risk engine.

Do not create a second reporting system.

---

# 2. STOP CONDITIONS

If Prompt 01–06 are broken or incomplete:

STOP.

Do not continue by creating workarounds.

Report:

- which component is broken
- where it is broken
- why Prompt 07 cannot safely proceed
- what must be fixed

Do not fabricate research results.

---

# 3. NO MOCKS / NO SYNTHETIC RESEARCH

Do NOT use:

- synthetic market data
- fake trades
- fabricated performance
- simulated strategy results presented as research
- fake out-of-sample results
- fake walk-forward results
- placeholder robustness statistics

Synthetic data is allowed only for isolated unit tests where required to validate mathematical logic.

Such data must never appear in the final research conclusions.

---

# 4. PURPOSE OF PROMPT 07

Prompt 07 adds:

```text
HISTORICAL BACKTEST
        ↓
TEMPORAL SPLITS
        ↓
TRAIN / DEVELOPMENT PERIOD
        ↓
VALIDATION PERIOD
        ↓
OUT-OF-SAMPLE PERIOD
        ↓
WALK-FORWARD ANALYSIS
        ↓
SENSITIVITY ANALYSIS
        ↓
ROBUSTNESS ANALYSIS
        ↓
REGIME ANALYSIS
        ↓
COST / EXECUTION SENSITIVITY
        ↓
RESEARCH CONCLUSIONS

The goal is not to maximize historical performance.

The goal is to determine whether observed behavior survives reasonable changes in:

time
market conditions
parameters
costs
assets
timeframes
execution assumptions
5. CRITICAL PRINCIPLE: NO LOOK-AHEAD

This is the most important requirement of Prompt 07.

A future observation must NEVER influence an earlier decision.

For every walk-forward window:

TRAIN / DEVELOPMENT
        ↓
VALIDATION
        ↓
OUT-OF-SAMPLE

information must flow only forward in time.

Example:

2022 ──────────────── 2023
 TRAIN                 OOS

Information from 2023 cannot affect decisions in 2022.

6. IMPORTANT DISTINCTION: RESEARCH VS TRADING LOGIC

Prompt 07 is allowed to analyze historical data retrospectively.

However:

Research conclusions must never be injected backward into the historical trading engine.

For example:

INVALID:

"Strategy A performed best from 2023–2025, therefore use Strategy A during 2023."

VALID:

"Using only information available before each walk-forward period, the research framework evaluated the configured strategy universe."

The system must preserve this distinction.

7. WALK-FORWARD FRAMEWORK

Implement a configurable walk-forward framework.

The framework should support:

expanding window
rolling window

Both should be configurable.

Example:

research:
  walk_forward:
    enabled: true

    mode: expanding

    train_period:
      value: 180
      unit: days

    validation_period:
      value: 30
      unit: days

    test_period:
      value: 30
      unit: days

    step:
      value: 30
      unit: days

Do not blindly use these values.

Integrate with the project's existing configuration architecture.

8. WALK-FORWARD EXAMPLE

A rolling example could look like:

TRAIN        VALIDATION       OOS
Jan-Jun      Jul              Aug
Feb-Jul      Aug              Sep
Mar-Aug      Sep              Oct
Apr-Sep      Oct              Nov
...

An expanding example:

TRAIN             VALIDATION       OOS
Jan-Jun           Jul              Aug
Jan-Jul           Aug              Sep
Jan-Aug           Sep              Oct
Jan-Sep           Oct              Nov
...

The implementation must explicitly document the difference.

9. MINIMUM TEMPORAL SEPARATION

Avoid accidental overlap between training/development and OOS periods.

The framework must clearly define:

training start
training end
validation start
validation end
OOS start
OOS end

All timestamps must be timezone-aware.

Use UTC internally.

10. OOS IS ACTUALLY OUT OF SAMPLE

An OOS period must not be used to:

choose strategies
choose parameters
choose score thresholds
choose RR
choose risk percentage
choose cooldown
choose assets
choose timeframes

The OOS period exists to evaluate decisions made without knowledge of that future period.

11. STRATEGY UNIVERSE HANDLING

The system already contains multiple strategies.

Prompt 07 must NOT simply:

Backtest all history.
Rank strategies.
Select the best.
Pretend that selection was known historically.

Instead, if strategy selection is researched, it must be performed strictly inside each training/development period.

For example:

TRAIN
  ↓
Research selection
  ↓
Freeze selection/configuration
  ↓
OOS

The OOS period must not influence selection.

However, unless strategy-selection research is necessary for a specific experiment, prefer evaluating the configured strategy universe without selection.

Document the distinction.

12. STRATEGY SELECTION MUST BE OPTIONAL

Implement strategy-selection research as an optional research module.

Default:

strategy_selection:
  enabled: false

The default Prompt 07 validation should evaluate the existing strategy universe without selecting winners.

This prevents accidental overfitting.

13. NO OPTIMIZATION BY DEFAULT

Prompt 07 must NOT perform unrestricted parameter optimization.

Sensitivity analysis is NOT optimization.

The difference must be documented.

Sensitivity analysis

Question:

"Does behavior remain reasonably stable when the parameter changes within a predefined neighborhood?"

Optimization

Question:

"What parameter produces the highest historical return?"

Prompt 07 is allowed to perform the first.

Prompt 07 must NOT perform the second by default.

14. PARAMETER SENSITIVITY ANALYSIS

Implement configurable sensitivity analysis.

Examples:

RR
2:1
2.5:1
3:1
3.5:1
4:1
Risk per trade

Use a small predefined neighborhood around the baseline.

Stop parameters

Where strategy-specific and already configurable.

Opportunity score threshold

Example:

40
50
60
70
80

Only if the existing score architecture supports this safely.

Cooldown

Test reasonable predefined values if configured.

Do NOT search an enormous parameter grid.

Do NOT optimize.

The purpose is to identify:

stable regions
unstable regions
highly sensitive parameters
15. PARAMETER NEIGHBORHOOD

For each parameter tested, clearly define:

BASELINE
LOW
BASELINE
HIGH

Prefer small, economically reasonable neighborhoods.

Avoid testing hundreds or thousands of combinations.

Document why each tested value exists.

16. ROBUSTNESS CONCEPT

A result should not be called robust simply because:

Net P&L > 0

Consider:

consistency across periods
consistency across OOS windows
sensitivity to parameters
sensitivity to costs
sensitivity to assets
sensitivity to timeframes
drawdown behavior
trade-count stability
dependence on a small number of trades
dependence on a small number of days
dependence on a single asset
dependence on a single market regime
17. COST SENSITIVITY

Re-run research under multiple realistic execution-cost assumptions.

At minimum support:

baseline costs
higher fee scenario
higher spread scenario
higher slippage scenario
combined adverse-cost scenario

Example concept:

BASE
+25% cost
+50% cost
+100% cost

Do not assume these exact values are correct.

Make them configurable.

The purpose is to determine:

"Does the historical result disappear under modestly worse execution assumptions?"

18. EXECUTION SENSITIVITY

Where supported by the existing execution engine, test:

baseline slippage
increased slippage
wider spread
conservative execution

Preserve the existing execution semantics.

Do not invent unrealistic execution models.

Do not change the core execution engine merely for research reporting.

Use configuration overrides where possible.

19. ASSET ROBUSTNESS

Analyze whether findings depend excessively on one asset.

For each configured asset:

BTCUSDT
ETHUSDT
SOLUSDT
etc.

Calculate descriptive statistics.

Questions to investigate:

Does the behavior exist across multiple assets?
Is it concentrated in one asset?
Does removing one asset materially change the aggregate result?

Do not rank assets.

Do not declare a "best asset."

20. TIMEFRAME ROBUSTNESS

Analyze:

1m
3m
5m
15m
30m
1h
2h
4h

or whatever is actually configured.

Questions:

Is behavior concentrated in one timeframe?
Does the effect survive across adjacent timeframes?
Does performance collapse when timeframe changes slightly?

Do not rank timeframes.

21. LEAVE-ONE-ASSET-OUT ANALYSIS

Implement optional leave-one-asset-out analysis.

Example:

All assets
minus BTC
minus ETH
minus SOL
...

The purpose is to determine whether aggregate behavior depends disproportionately on one asset.

This is descriptive robustness research.

Do not interpret it as proof of generalization.

22. LEAVE-ONE-STRATEGY-OUT ANALYSIS

If computationally reasonable, support:

All strategies
minus Strategy A
minus Strategy B
...

This helps determine whether aggregate portfolio behavior is dominated by a single strategy.

Do not use this to declare a strategy "best".

23. LEAVE-ONE-PERIOD-OUT ANALYSIS

Analyze whether conclusions depend excessively on one historical period.

Examples:

remove one month
remove one quarter
remove one year

Use only periods actually available.

This should be optional because of computational cost.

24. MARKET REGIME ANALYSIS

Prompt 07 should introduce descriptive market-regime analysis.

The goal is NOT to build a perfect regime classifier.

The goal is to determine whether observed strategy behavior differs under different market conditions.

Possible regime dimensions:

volatility
trend strength
realized volatility
market direction
volume/liquidity conditions
BTC trend
cross-asset dispersion

Use only data available at the relevant timestamp.

25. REGIME FEATURES

Possible features:

Trend
rolling return
moving-average slope
price relative to moving average
Volatility
ATR
realized volatility
rolling standard deviation
Volume
relative volume
rolling volume percentile
Market structure
distance from recent high
distance from recent low

Do not create a huge regime feature library.

Start with a small, interpretable set.

26. REGIME CLASSIFICATION

Use transparent deterministic classifications.

Example:

TREND_UP
TREND_DOWN
RANGE

LOW_VOL
NORMAL_VOL
HIGH_VOL

The exact classification must be configurable and documented.

Avoid machine-learning regime classification in Prompt 07.

Do not create a black-box regime model.

27. REGIME PIT REQUIREMENT

Regime classification at timestamp T may only use information available at or before T.

For example:

INVALID:

"Classify January as HIGH_VOL because February volatility was high."

VALID:

"At each timestamp, classify volatility using the rolling information available up to that timestamp."

28. REGIME PERFORMANCE ANALYSIS

For each regime, provide descriptive statistics:

trade count
signals
accepted signals
rejected signals
net P&L
realized R
win rate
average R
drawdown
costs
average duration
opportunity score

Do not claim that a strategy "works only in regime X" unless the evidence supports a careful descriptive statement.

Use language such as:

"Historical results in this sample differed across the defined regimes."

Do not turn descriptive differences into causal claims.

29. REGIME TRANSITIONS

Where practical, identify:

regime start
regime end
duration
strategy activity during the regime
performance during the regime

This should be descriptive.

Do not create a future-aware regime predictor.

30. STABILITY METRICS

Implement a research metrics module.

At minimum calculate:

Performance
net P&L
total R
average R
median R
win rate
profit factor where mathematically appropriate
Risk
maximum drawdown
drawdown duration
return / drawdown ratio
volatility of returns
Trade distribution
trade count
average duration
median duration
average winning trade
average losing trade
largest win
largest loss
Temporal stability
percentage of positive OOS windows
median OOS R
dispersion of OOS results
worst OOS window
best OOS window

Do not use these metrics to produce an overall strategy ranking.

31. TRADE COUNT REQUIREMENT

Always report trade count alongside performance.

A result based on:

5 trades

must not be presented with the same confidence as:

5,000 trades

Do not invent statistical significance.

32. SAMPLE-SIZE WARNINGS

Implement warnings for small samples.

Example configuration:

research:
  minimum_sample_sizes:
    trades: 30
    oos_windows: 5

These are warnings, not universal statistical laws.

Document that thresholds are research heuristics.

A small sample should be explicitly labeled:

LOW_SAMPLE_WARNING
33. OVERFITTING WARNING

Create automated warnings for obvious research risks.

Examples:

HIGH_PARAMETER_SENSITIVITY
LOW_OOS_SAMPLE
LOW_TRADE_COUNT
SINGLE_ASSET_DEPENDENCY
SINGLE_TIMEFRAME_DEPENDENCY
SINGLE_PERIOD_DEPENDENCY
HIGH_COST_SENSITIVITY
REGIME_DEPENDENCY

These are diagnostic flags.

They are not automatic proof of overfitting.

34. MULTIPLE TESTING AWARENESS

The system must explicitly document that testing many:

strategies
parameters
assets
timeframes
regimes
cost assumptions

creates a multiple-comparison / research-selection problem.

Do not claim statistical significance simply because one result looks strong.

Prompt 07 should preserve the full experiment matrix.

35. EXPERIMENT REGISTRY

Implement an experiment registry.

Every robustness experiment should record:

experiment_id
run_id
experiment_type
baseline_configuration
modified_configuration
dataset
date range
assets
timeframes
strategies
train period
validation period
OOS period
metrics
warnings
code version
timestamp

Example:

experiment_type:
  WALK_FORWARD
  COST_SENSITIVITY
  PARAMETER_SENSITIVITY
  REGIME_ANALYSIS
  ASSET_ROBUSTNESS
  TIMEFRAME_ROBUSTNESS
  LEAVE_ONE_OUT
36. EXPERIMENT REPRODUCIBILITY

Every experiment must be reproducible.

Store:

configuration snapshot
dataset identifiers
strategy versions
risk configuration
execution configuration
code version
Git commit when available
experiment ID

Never fabricate missing metadata.

37. BASELINE CONFIGURATION

Define a single baseline research configuration.

The baseline must correspond to the configuration used in Prompt 06 unless explicitly changed and documented.

Do not silently change:

RR
risk
score threshold
cooldown
fees
slippage
strategies
assets
timeframes

The baseline must be explicit.

38. BASELINE VS EXPERIMENT

Every experiment must clearly identify:

BASELINE
vs
EXPERIMENT

Example:

Baseline:
RR = 3.0

Experiment:
RR = 2.5

Do not mix results.

39. WALK-FORWARD OUTPUT

Generate machine-readable results.

Example:

results/
  <run_id>/
    robustness/
      walk_forward/
        windows.csv
        oos_results.csv
        train_results.csv
        validation_results.csv
        summary.json

Each window should contain:

window_id
train_start
train_end
validation_start
validation_end
oos_start
oos_end
strategies
assets
timeframes
trades
net_pnl
total_R
max_drawdown
costs
warnings
40. SENSITIVITY OUTPUT

Example:

results/
  <run_id>/
    robustness/
      sensitivity/
        parameter_matrix.csv
        cost_sensitivity.csv
        execution_sensitivity.csv
        summary.json
41. REGIME OUTPUT

Example:

results/
  <run_id>/
    robustness/
      regimes/
        regime_definitions.json
        regime_periods.csv
        regime_trade_metrics.csv
        regime_summary.json
42. ROBUSTNESS SUMMARY

Generate:

robustness_summary.json

and:

ROBUSTNESS_REPORT.md

The report must contain:

Dataset
period
assets
timeframes
Baseline
configuration
assumptions
Walk-forward
number of windows
OOS coverage
OOS results
stability
Sensitivity
tested parameters
observed sensitivity
Costs
baseline
adverse scenarios
Assets
cross-asset behavior
Timeframes
cross-timeframe behavior
Regimes
regime definitions
behavior by regime
Warnings
low sample
concentration
sensitivity
instability
43. NO RANKING

This is mandatory.

Do not produce:

1. Strategy A
2. Strategy B
3. Strategy C

Do not produce:

Best strategy
Worst strategy
Winner
Champion
Top strategy

The report may provide tables grouped by strategy.

It must not turn the research into a ranking.

44. NO OVERALL SCORE

Do not create:

Robustness Score = 87/100

or any similar single-number ranking.

Robustness is multidimensional.

Present the evidence by dimension.

45. NO FUTURE-BASED STRATEGY SELECTION

This is forbidden:

2022–2025 results
        ↓
choose best strategies
        ↓
pretend those strategies were selected in 2022

If strategy selection is tested, the selection must happen inside each training period.

46. WALK-FORWARD STRATEGY SELECTION

If the optional strategy-selection experiment is enabled:

For each window:

TRAIN
  ↓
evaluate candidates
  ↓
selection rule
  ↓
freeze selected universe/configuration
  ↓
VALIDATION
  ↓
freeze final configuration
  ↓
OOS

The OOS period must never influence:

selection
parameters
thresholds
strategy universe
risk configuration

Document the exact selection rule.

47. VALIDATION PERIOD PURPOSE

If a validation period is used:

The validation period may be used for model/configuration confirmation before OOS.

However:

It must not be treated as OOS.

Clearly distinguish:

TRAIN
VALIDATION
OOS

in every report.

48. NO DATA SNOOPING

The research layer must detect and warn about:

overlapping OOS periods
accidental reuse of OOS results
parameter changes after OOS inspection
strategy selection using OOS
repeated testing without experiment registration

Where automatic detection is not possible, document the limitation.

49. DATA AVAILABILITY

Respect actual Binance data availability.

Do not:

fabricate pre-listing data
fill unavailable history
backfill future data
mix datasets with incompatible definitions

Each experiment must record the actual available period.

50. MISSING DATA

Missing market data must not silently become:

zero
flat candles
forward-filled candles
synthetic candles

Reuse Prompt 02 data-quality policies.

If a required experiment cannot be executed because of missing data:

report it as unavailable.

Do not fabricate completeness.

51. MULTI-TIMEFRAME PIT

If multiple timeframes are used:

At timestamp T, a strategy may only access candles whose information was available by T.

Example:

At:

10:15 UTC

the system cannot use the final close of:

10:00–11:00

because that candle has not closed yet.

This must be tested.

52. RESEARCH ENGINE DESIGN

Create a modular research framework.

Possible structure:

src/crypto_research/
    research/
        walk_forward/
        robustness/
        sensitivity/
        regimes/
        experiments/

Adapt to the existing architecture.

Do not duplicate existing research components.

53. RESEARCH INTERFACES

Create reusable interfaces where appropriate.

For example:

WalkForwardRunner
SensitivityRunner
RobustnessAnalyzer
RegimeAnalyzer
ExperimentRegistry
ResearchResult
ResearchWarning

Do not over-engineer.

Follow the existing project architecture.

54. NOTEBOOK

Create:

notebooks/07_robustness_and_walk_forward_validation.ipynb

The notebook must execute from beginning to end.

55. NOTEBOOK SECTION 1 — ENVIRONMENT

Display:

Python version
project version
Git commit if available
experiment timestamp
run ID
56. NOTEBOOK SECTION 2 — BASELINE

Display:

baseline configuration
assets
timeframes
strategies
RR
risk configuration
costs
score threshold
cooldown
date range
57. NOTEBOOK SECTION 3 — DATA VALIDATION

Verify:

datasets exist
data-quality status
actual ranges
symbols
timeframes
no invalid data

Stop on failure.

58. NOTEBOOK SECTION 4 — WALK-FORWARD WINDOWS

Display generated windows.

For each window show:

train
validation
OOS

Verify chronological ordering.

59. NOTEBOOK SECTION 5 — WALK-FORWARD EXECUTION

Run the real backtest engine through the configured walk-forward windows.

Use real historical data.

Display:

window count
train metrics
validation metrics
OOS metrics

Do not fabricate missing windows.

60. NOTEBOOK SECTION 6 — OOS ANALYSIS

Display:

OOS trade count
OOS net P&L
OOS total R
OOS drawdown
OOS costs
OOS return distribution
OOS window distribution

Do not rank strategies.

61. NOTEBOOK SECTION 7 — PARAMETER SENSITIVITY

Run the configured sensitivity experiments.

Display:

baseline
tested values
metrics
warnings

Do not optimize.

62. NOTEBOOK SECTION 8 — COST SENSITIVITY

Display:

baseline cost
adverse cost scenarios
resulting metrics
change in net P&L
change in R
change in drawdown
63. NOTEBOOK SECTION 9 — ASSET ROBUSTNESS

Display descriptive results by asset.

Include leave-one-out if enabled.

64. NOTEBOOK SECTION 10 — TIMEFRAME ROBUSTNESS

Display descriptive results by timeframe.

Include adjacent-timeframe comparisons where available.

65. NOTEBOOK SECTION 11 — REGIME ANALYSIS

Display:

regime definitions
regime frequency
strategy activity
trade count
R
P&L
drawdown
score
duration
66. NOTEBOOK SECTION 12 — ROBUSTNESS WARNINGS

Display:

LOW_OOS_SAMPLE
LOW_TRADE_COUNT
HIGH_PARAMETER_SENSITIVITY
HIGH_COST_SENSITIVITY
SINGLE_ASSET_DEPENDENCY
SINGLE_TIMEFRAME_DEPENDENCY
SINGLE_PERIOD_DEPENDENCY
REGIME_DEPENDENCY

where applicable.

67. NOTEBOOK SECTION 13 — RESEARCH INTERPRETATION

Generate a factual summary.

Example:

Historical observation:
The aggregate result remained positive in 6 of 8 OOS windows.

Observation:
Performance was materially weaker under the highest tested cost assumption.

Observation:
Trade activity was concentrated in two assets.

Warning:
The OOS sample contains fewer than the configured minimum number of windows.

Do not write:

Therefore the strategy will work.

Do not write:

This is a profitable system.

Do not write:

Strategy A is the best.
68. NOTEBOOK SECTION 14 — ARTIFACT VALIDATION

Verify that:

experiment registry exists
walk-forward files exist
sensitivity files exist
regime files exist
robustness summary exists
report exists
configuration snapshots exist
69. NOTEBOOK SECTION 15 — FINAL STATUS

Only print:

PROMPT 07 VALIDATION STATUS: PASS

if all mandatory acceptance criteria pass.

Otherwise:

PROMPT 07 VALIDATION STATUS: FAIL

Never report PASS after a failed experiment.

70. STATISTICAL CAUTION

Do not overstate statistical conclusions.

This project evaluates many hypotheses.

The research system must explicitly acknowledge:

multiple testing
selection bias
data-mining risk
regime dependence
transaction-cost uncertainty
market microstructure limitations
historical sample limitations
non-stationarity
execution-model limitations

These are research limitations, not reasons to fabricate certainty.

71. OPTIONAL ADVANCED TESTS

If the existing architecture supports them cleanly, implement optional:

bootstrap confidence intervals for selected descriptive metrics
block bootstrap for time-series returns
Monte Carlo trade-order reshuffling for drawdown analysis
return distribution analysis
probability of drawdown exceedance under resampling

These must be clearly labeled as statistical research experiments.

Do NOT assume independent trades when that assumption is invalid.

Do NOT present bootstrap output as proof of future performance.

If implementation would require substantial new infrastructure, document it as a future enhancement instead of destabilizing Prompt 07.

72. MONTE CARLO TRADE ORDER TEST

If implemented:

Use historical trade outcomes and test sensitivity of:

drawdown
losing streaks
equity path

to trade ordering.

This does NOT create new trades.

It only studies path dependency of the observed trade distribution.

Clearly label this as a resampling analysis.

73. REGIME DEPENDENCY WARNING

If a strategy or aggregate result is heavily concentrated in one regime:

flag:

REGIME_DEPENDENCY

Do not automatically disable the strategy.

Do not automatically change parameters.

The purpose is to identify a research hypothesis for future investigation.

74. COST DEPENDENCY WARNING

If a historical result becomes materially weaker under modest adverse cost assumptions:

flag:

HIGH_COST_SENSITIVITY

Do not modify the execution model.

Do not hide the result.

75. PERIOD DEPENDENCY WARNING

If most of the aggregate result comes from one historical period:

flag:

SINGLE_PERIOD_DEPENDENCY

Provide descriptive evidence.

Do not automatically discard the strategy.

76. ASSET DEPENDENCY WARNING

If removing one asset materially changes the aggregate result:

flag:

SINGLE_ASSET_DEPENDENCY
77. TIMEFRAME DEPENDENCY WARNING

If behavior is heavily concentrated in one timeframe:

flag:

SINGLE_TIMEFRAME_DEPENDENCY
78. PARAMETER SENSITIVITY WARNING

If small parameter changes produce large outcome changes:

flag:

HIGH_PARAMETER_SENSITIVITY

This is a warning about robustness, not proof of overfitting.

79. RESEARCH REPORT STRUCTURE

Create:

docs/research/ROBUSTNESS_AND_WALK_FORWARD_POLICY.md

Document:

walk-forward methodology
temporal splits
OOS methodology
validation methodology
sensitivity analysis
cost analysis
asset analysis
timeframe analysis
regime analysis
experiment registry
multiple testing
limitations

Create:

docs/execution/PROMPT_07_EXECUTION_GUIDE.md

The guide must contain:

What Prompt 07 implemented
Prerequisites
Exact execution commands
Notebook execution
Baseline configuration
Walk-forward configuration
Sensitivity configuration
Regime configuration
Output directories
How to interpret reports
What counts as a warning
What does not count as proof
Reproducibility procedure
Known limitations
Known issues
Acceptance criteria
Troubleshooting
Next prompt
80. README UPDATE

Update README.md with the research-validation architecture:

Historical Data
      ↓
Backtest Engine
      ↓
Strategy Universe
      ↓
Risk / Orchestration
      ↓
Trade Diary
      ↓
Walk-Forward
      ↓
Out-of-Sample
      ↓
Sensitivity
      ↓
Robustness
      ↓
Regime Analysis

Explain that Prompt 07 does not optimize or rank strategies.

81. PROJECT_STATUS UPDATE

Update:

PROJECT_STATUS.md

with:

Prompt 07 status
implementation date
experiment IDs
datasets used
walk-forward configuration
OOS windows
sensitivity experiments
regime analysis
tests
validation results
warnings
known limitations
next step

Use:

COMPLETE
PARTIAL
BLOCKED

Only mark COMPLETE if all mandatory acceptance criteria pass.

Only state:

READY FOR PROMPT 08

if the project genuinely passes validation.

82. RESULT DIRECTORY

Use the existing result/run architecture.

Suggested structure:

results/
  <run_id>/
    robustness/

      experiment_registry.csv
      experiment_registry.json

      walk_forward/
        windows.csv
        train_results.csv
        validation_results.csv
        oos_results.csv
        summary.json

      sensitivity/
        parameter_sensitivity.csv
        cost_sensitivity.csv
        execution_sensitivity.csv
        summary.json

      assets/
        asset_summary.csv
        leave_one_asset_out.csv

      timeframes/
        timeframe_summary.csv

      regimes/
        regime_definitions.json
        regime_periods.csv
        regime_trade_metrics.csv
        regime_summary.json

      warnings/
        robustness_warnings.csv

      robustness_summary.json

    reports/
      ROBUSTNESS_REPORT.md
      WALK_FORWARD_REPORT.md
      SENSITIVITY_REPORT.md
      REGIME_REPORT.md

    html/
      robustness_report.html

Adapt this to the existing project architecture.

Do not create duplicate data stores.

83. DETERMINISM

The same:

dataset
baseline configuration
code version
experiment configuration

must produce the same analytical results.

Any randomness must be:

explicit
seeded
recorded

If an experiment is stochastic:

record the seed.

84. RECONCILIATION

Verify:

all OOS trade results
        ↓
aggregate OOS results

and:

all walk-forward windows
        ↓
reported summary

No unexplained differences.

If windows overlap intentionally, document how aggregate results are constructed to avoid double counting.

85. OVERLAPPING OOS WINDOWS

If walk-forward windows produce overlapping OOS periods:

DO NOT simply sum all OOS P&L.

This can double-count trades.

The system must explicitly handle:

non-overlapping OOS
overlapping OOS

and document the aggregation method.

Prefer non-overlapping OOS evaluation for the primary aggregate unless there is a clear research reason otherwise.

86. PRIMARY OOS SERIES

Create a clearly identified:

PRIMARY_OOS_SERIES

This should contain only observations considered valid for the primary OOS evaluation.

Document:

inclusion rule
overlap handling
duplicate trade handling
temporal ordering
87. RESEARCH EXPERIMENT SEPARATION

Each experiment must be isolated.

For example:

Baseline
Experiment A — RR sensitivity
Experiment B — cost sensitivity
Experiment C — regime analysis

Experiment B must not inherit modifications from Experiment A unless explicitly defined.

Avoid accidental cumulative configuration mutation.

88. CONFIGURATION IMMUTABILITY

When an experiment begins:

capture a configuration snapshot.

Do not mutate the baseline configuration in place.

Create experiment-specific configurations.

89. NO SILENT EXPERIMENT FAILURE

If an experiment fails:

record:

FAILED

with:

error
traceback
configuration
experiment ID

Do not mark it as successful.

Do not silently skip it.

90. COMPUTATIONAL COST CONTROL

Prompt 07 may be computationally expensive.

Implement controlled execution.

Configuration should allow:

subset of strategies
subset of assets
subset of timeframes
subset of experiments

for development/testing.

However:

A development subset must be explicitly labeled:

DEVELOPMENT_RUN

and must not be confused with the complete research run.

The final validation must use the configured full research universe unless impossible due to documented constraints.

91. RESEARCH RUN TYPES

Support:

DEVELOPMENT
VALIDATION
FULL

Example:

research:
  run_type: FULL

The final Prompt 07 validation should use:

FULL

unless a documented resource limitation prevents it.

92. NO REAL-MONEY TRADING

Prompt 07 is strictly historical research.

Do NOT connect:

Binance trading authentication
real trading accounts
order placement
live execution

Prompt 08 will address paper trading/realtime research only.

93. ACCEPTANCE CRITERIA

Prompt 07 is COMPLETE only if:

Architecture
Prompt 01–06 architecture reused
no duplicate backtest engine
no duplicate strategy engine
no duplicate risk engine
Walk-forward
rolling supported
expanding supported or explicitly documented if deferred
temporal ordering validated
OOS separated from training/validation
overlap handled correctly
OOS
genuine historical OOS evaluation exists
no future leakage
OOS results reproducible
Sensitivity
parameter sensitivity implemented
cost sensitivity implemented
execution sensitivity implemented where supported
no optimization
Robustness
asset analysis
timeframe analysis
period analysis
trade-count analysis
drawdown analysis
Regimes
transparent regime definitions
PIT-safe regime features
regime statistics
regime warnings
Research Integrity
experiment registry
configuration snapshots
multiple-testing awareness
no ranking
no future strategy selection
Validation
unit tests
integration tests
real historical datasets
notebook execution
reconciliation
Documentation
README updated
PROJECT_STATUS updated
ROBUSTNESS_AND_WALK_FORWARD_POLICY.md
PROMPT_07_EXECUTION_GUIDE.md
94. FINAL EXECUTION REPORT

At the end, provide:

1. Status
COMPLETE / PARTIAL / BLOCKED
2. Files created

List them.

3. Files modified

List them.

4. Tests

Report:

executed
passed
failed
skipped
reason for skipped
5. Dataset

Report actual:

date range
assets
timeframes
row counts where useful
6. Walk-forward

Report:

mode
train duration
validation duration
OOS duration
step
number of windows
number of valid OOS windows
7. Sensitivity

Report actual experiments executed.

8. Regimes

Report actual regime definitions used.

9. Warnings

List actual warnings generated.

10. Known limitations

List honestly.

11. Research interpretation

Provide descriptive findings only.

Do NOT:

rank strategies
declare winners
predict future performance
recommend real-money deployment
12. Final state

Only if all mandatory criteria pass:

READY FOR PROMPT 08

Otherwise:

NOT READY FOR PROMPT 08
95. FINAL RESEARCH PHILOSOPHY

Prompt 07 must answer:

"Do the historical observations survive reasonable attempts to break them?"

It should investigate:

Does it survive time?
Does it survive unseen periods?
Does it survive different assets?
Does it survive different timeframes?
Does it survive reasonable cost increases?
Does it survive reasonable parameter changes?
Does it survive different market regimes?
Does it depend on a small number of trades?
Does it depend on one asset?
Does it depend on one timeframe?
Does it depend on one historical period?

The correct outcome is not necessarily:

ROBUST

The correct outcome may be:

ROBUST IN SOME DIMENSIONS
SENSITIVE IN OTHERS
INSUFFICIENT EVIDENCE IN OTHERS

That is valuable research.

Do not force a positive conclusion.

Do not optimize until the system "looks good."

Do not hide instability.

Do not select winners.

The purpose of Prompt 07 is to discover what survives scrutiny.

END OF PROMPT 07