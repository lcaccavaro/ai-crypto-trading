# PROMPT 06 — TRADE DIARY, VISUAL ANALYSIS & RESEARCH REPORTING

## ROLE

Act as a:

- Principal Quantitative Research Engineer
- Senior Python Data Visualization Engineer
- Quantitative Research Reporting Architect
- Systematic Trading Analytics Engineer
- Research Reproducibility Specialist

You are continuing an existing quantitative research/backtesting project.

This is PROMPT 06 of an 8-prompt implementation sequence.

The project is a research-oriented crypto intraday backtesting laboratory focused on short-duration "snipe" strategies across multiple assets and timeframes.

The objective of this prompt is to build a robust:

1. Trade Diary
2. Trade Visualization System
3. Daily Research Report
4. Weekly Research Report
5. Monthly Research Report
6. Decision-Quality Analysis
7. Signal/Rejection Audit
8. Reproducible Research Reporting Layer

Do NOT redesign the architecture.

Do NOT create a new parallel reporting architecture.

Do NOT modify the strategy definitions from Prompt 04.

Do NOT modify the risk-management rules from Prompt 05.

Do NOT modify the execution engine from Prompt 03 unless a genuine integration bug is discovered.

Do NOT optimize strategies.

Do NOT rank strategies.

Do NOT select "the best strategy".

Do NOT introduce future information.

The purpose of this prompt is to make the existing research results observable, auditable, explainable, and visually analyzable.

---

# 1. CRITICAL PROJECT RULES

These rules are mandatory.

## 1.1 Inspect the existing project first

Before modifying anything:

1. Inspect the repository.
2. Inspect Prompt 01 implementation.
3. Inspect Prompt 02 implementation.
4. Inspect Prompt 03 implementation.
5. Inspect Prompt 04 implementation.
6. Inspect Prompt 05 implementation.
7. Read:

   - README.md
   - PROJECT_STATUS.md
   - architecture documentation
   - research policies
   - execution guides
   - configuration
   - existing tests
   - existing result structures

Do not assume filenames or interfaces.

Discover the actual implementation first.

Reuse existing structures whenever possible.

---

# 2. STOP CONDITIONS

If Prompt 01–05 are incomplete, broken, or inconsistent:

STOP.

Do not build a parallel architecture.

Do not silently repair major architectural problems.

Report:

- what is broken
- where it is broken
- why Prompt 06 cannot safely continue
- what must be fixed before Prompt 06

Do not fabricate outputs.

Do not create synthetic research results to make the notebook appear successful.

---

# 3. NO FALLBACKS / NO MOCKS

This project requires real execution.

Do NOT use:

- mock trades
- fake Binance data
- synthetic research results
- fabricated performance
- placeholder charts presented as real results
- silently skipped trades
- silently dropped rows
- silent exception handling
- fake successful reports

Test fixtures may be synthetic only when required for deterministic unit tests.

Such fixtures must be explicitly labeled as TEST FIXTURES and must never be presented as research results.

If a real-data execution fails:

STOP and expose the actual error.

Do not replace the failed data with something else.

---

# 4. OBJECTIVE OF PROMPT 06

Prompt 06 transforms the outputs from:

MARKET DATA
    ↓
STRATEGY
    ↓
SIGNAL
    ↓
OPPORTUNITY SCORE
    ↓
RISK MANAGER
    ↓
ORCHESTRATOR
    ↓
EXECUTION ENGINE
    ↓
POSITION
    ↓
TRADE

into:

TRADE DIARY
    ↓
TRADE VISUALIZATION
    ↓
DAILY REPORT
    ↓
WEEKLY REPORT
    ↓
MONTHLY REPORT
    ↓
RESEARCH ANALYTICS
    ↓
AUDITABLE RESEARCH ARTIFACTS

The reporting layer must remain downstream from the research engine.

Reporting must NEVER influence historical decisions.

---

# 5. CORE RESEARCH PRINCIPLE

The diary must answer:

> "What happened, what did the system know at the time, why did it take or reject the opportunity, and what happened afterward?"

It must NOT answer using hindsight:

> "Knowing what happened later, should the system have taken the trade?"

Those are different concepts.

The system must preserve the distinction between:

1. Decision quality
2. Trade outcome

A good decision can lose.

A bad decision can win.

Do not classify decisions based simply on P&L.

---

# 6. TRADE DIARY

Implement a structured Trade Diary.

Each completed trade should have a machine-readable record containing, where available:

- run_id
- trade_id
- strategy_id
- strategy_version
- symbol
- market_type
- timeframe
- side
- signal_timestamp
- signal_candle_timestamp
- entry_timestamp
- entry_price
- initial_stop_price
- target_price
- final_exit_timestamp
- final_exit_price
- position_size
- notional_value
- risk_amount
- risk_pct
- configured_RR
- realized_R
- gross_pnl
- fees
- spread_cost
- slippage_cost
- total_cost
- net_pnl
- net_return_pct
- holding_duration
- maximum_adverse_excursion
- maximum_favorable_excursion
- opportunity_score
- opportunity_score_version
- score_components
- risk_decision
- risk_rejection_reason if applicable
- strategy_state_at_entry
- daily_pnl_before_trade
- daily_pnl_after_trade
- consecutive_losses_before_trade
- consecutive_losses_after_trade
- exit_reason
- stop_hit
- target_hit
- break_even_exit if supported
- time_exit if supported
- gap_execution if applicable
- ambiguous_candle_event if applicable

Use the existing domain model wherever possible.

Do not duplicate business logic merely to generate the diary.

---

# 7. SIGNAL / DECISION DIARY

The diary must not contain only executed trades.

Also preserve information about rejected opportunities.

Create an auditable decision record for every strategy signal evaluated by the orchestration/risk layer.

Each decision record should include, where available:

- run_id
- decision_id
- timestamp
- symbol
- timeframe
- strategy_id
- strategy_version
- signal_direction
- signal_reason
- strategy_state
- opportunity_score
- opportunity_score_version
- score_components
- minimum_score_threshold
- risk_decision
- accepted/rejected
- rejection_code
- rejection_reason
- requested_quantity
- approved_quantity
- requested_risk
- approved_risk
- portfolio_state_snapshot
- daily_state_snapshot
- consecutive_loss_state
- active_position_count
- total_exposure
- asset_exposure
- strategy_exposure

This is important.

The research system must allow later analysis of:

"Did the opportunity fail because the strategy was wrong?"

versus:

"Did the strategy produce an opportunity that was rejected by risk controls?"

These are fundamentally different research questions.

---

# 8. TRADE EXPLANATION

Every executed trade should have an automatically generated concise explanation.

Example structure:

### Why was this trade taken?

Use only information available at entry time.

Possible components:

- strategy triggered
- trend condition
- momentum condition
- volatility condition
- volume/liquidity condition
- multi-timeframe confirmation
- opportunity score
- RR feasibility
- risk approval
- portfolio availability

Example:

"EMA trend-alignment condition triggered on BTCUSDT 5m. The opportunity score was 78/100, volatility was within the configured range, and the risk manager approved the position within portfolio exposure limits."

Do NOT generate explanations based on the eventual outcome.

---

# 9. TRADE OUTCOME EXPLANATION

After the trade is closed, generate a separate factual outcome explanation.

Examples:

- target reached
- stop reached
- gap caused worse execution
- trailing protection exited
- break-even protection exited
- time-based exit
- daily rule affected future entries
- ambiguous OHLC event handled using configured execution policy

The explanation must distinguish:

## Decision explanation

What was known when the trade was entered.

from:

## Outcome explanation

What happened after entry.

Never mix these.

---

# 10. DECISION QUALITY VS OUTCOME

Implement a research-oriented decision-quality framework.

This must NOT become a hindsight classifier.

The system should evaluate whether the trade decision followed the rules that were available at the time.

Possible decision-quality checks:

### A. Strategy validity

Did the strategy actually produce the configured signal?

### B. Point-in-time validity

Did the strategy use only information available at the signal timestamp?

### C. Risk validity

Was the trade accepted according to the configured risk rules?

### D. Score validity

Was the opportunity score calculated correctly from point-in-time information?

### E. Execution validity

Was the trade executed according to the configured execution model?

### F. Configuration validity

Was the trade consistent with the configured strategy/risk parameters?

### G. Portfolio validity

Was the trade consistent with portfolio constraints?

Create an internal decision-quality classification such as:

- VALID_DECISION
- INVALID_DECISION
- INCOMPLETE_AUDIT

Do NOT classify a trade as good or bad simply because it won or lost.

For example:

VALID_DECISION + LOSS

is a completely valid research outcome.

Likewise:

VALID_DECISION + WIN

does not prove that the strategy was correct in a causal sense.

---

# 11. TRADE VISUALIZATION

Implement automatic chart generation for executed trades.

Each trade should generate a chart containing:

- asset
- timeframe
- strategy
- entry
- initial stop
- target
- exit
- relevant indicator(s)
- signal timestamp
- entry timestamp
- exit timestamp
- trade direction
- realized R
- net P&L
- opportunity score
- outcome
- exit reason

The chart must show enough historical context around the trade to understand the setup.

Do not show future information that would not have been available at the entry point as if it were part of the decision.

It is acceptable for a post-trade chart to show what happened after entry, because this is a retrospective research visualization.

Clearly distinguish:

PRE-ENTRY INFORMATION

from:

POST-ENTRY OUTCOME.

---

# 12. TRADE CHART WINDOW

Make the chart window configurable.

Example configuration:

```yaml
reporting:
  trade_chart:
    enabled: true
    bars_before_entry: 100
    bars_after_entry: 100
    show_indicators: true
    show_entry: true
    show_stop: true
    show_target: true
    show_exit: true

Do not hard-code these values.

The configuration must be documented.

13. CHART SAFETY

Do not introduce look-ahead into calculations merely because the chart is retrospective.

Indicators shown before entry must correspond to their actual point-in-time values.

Do not recalculate historical indicators using future data in a way that changes their pre-entry values.

If an indicator requires warmup:

respect the strategy's warmup rules
do not fabricate missing values
do not silently fill missing values
14. TRADE CHART OUTPUT

Organize charts by:

results/
  <run_id>/
    trade_charts/
      BTCUSDT/
        5m/
          strategy_name/
            trade_<trade_id>.png

The exact structure may be adapted to the existing project conventions.

Do not create redundant storage systems if the project already has an established result layout.

15. DAILY REPORT

Implement a daily research report.

For each UTC day, calculate and report:

starting equity
ending equity
gross P&L
total costs
net P&L
net return %
number of executed trades
number of rejected signals
wins
losses
break-even trades
win rate
average R
total R
average winning R
average losing R
largest win
largest loss
maximum drawdown during the day
average holding duration
median holding duration
maximum adverse excursion
maximum favorable excursion
strategy count
asset count
timeframe count
opportunity score statistics
decision-quality statistics
rejection reasons
exit reasons
exposure statistics

Do not hide days with zero trades.

A day with no trades is still part of the research period.

16. DAILY TRADE TABLE

Each daily report should include a detailed trade table.

Columns should include at minimum:

trade_id
time
symbol
timeframe
strategy
side
entry
stop
target
exit
realized_R
gross_pnl
costs
net_pnl
score
duration
exit_reason
decision_quality
17. WEEKLY REPORT

Aggregate daily results into calendar weeks.

The weekly report should contain:

period
starting equity
ending equity
net P&L
net return %
total trades
wins
losses
average R
total R
maximum drawdown
average holding time
total costs
rejected opportunities
decision-quality distribution
strategy activity
asset activity
timeframe activity
score distribution
exit-reason distribution

Do not rank strategies.

The report may show grouped statistics by strategy, but must not declare a "best strategy".

18. MONTHLY REPORT

Aggregate weekly/daily information into calendar months.

Include:

starting equity
ending equity
net P&L
net return %
total trades
wins
losses
average R
total R
maximum drawdown
total costs
average holding duration
opportunity-score distribution
decision-quality distribution
rejection distribution
strategy activity
asset activity
timeframe activity
daily return distribution
number of active trading days
number of zero-trade days

Again:

DO NOT rank strategies.

DO NOT declare winners.

DO NOT optimize.

19. EQUITY CURVE

Generate an equity curve from the actual backtest results.

Include:

equity
cumulative net P&L
drawdown
daily return

The equity curve must be based on actual realized results.

No smoothing that changes the underlying data.

20. DRAWDOWN ANALYSIS

Generate a drawdown series.

At minimum:

drawdown = equity - running_peak_equity

Also provide drawdown percentage when appropriate.

Report:

maximum drawdown
drawdown duration
recovery duration when available
number of drawdown periods

Do not use future data to alter historical decisions.

This is retrospective reporting only.

21. COST ANALYSIS

Provide a clear cost breakdown.

At minimum:

trading fees
spread cost
slippage cost
total cost

Show:

gross P&L
- fees
- spread
- slippage
= net P&L

Where the existing engine provides more detailed costs, preserve them.

Do not estimate missing costs during reporting.

22. STRATEGY ACTIVITY REPORT

Create descriptive statistics by strategy.

For each strategy:

number of signals
accepted signals
rejected signals
executed trades
wins
losses
average R
total R
net P&L
costs
average score
average holding duration
decision-quality distribution
exit-reason distribution
strategy state changes

This is descriptive only.

Do NOT:

rank strategies
select strategies
disable strategies
modify strategy parameters
optimize based on these results

Strategy selection/optimization belongs to later research prompts.

23. ASSET REPORT

Provide descriptive statistics by asset.

Examples:

BTCUSDT
ETHUSDT
SOLUSDT

Include:

signals
accepted signals
rejected signals
trades
wins/losses
net P&L
realized R
costs
average score
average duration
exposure

Do not rank assets.

24. TIMEFRAME REPORT

Provide descriptive statistics by timeframe.

Examples:

1m
3m
5m
15m
30m
1h
2h
4h

Include:

signals
trades
accepted/rejected
net P&L
realized R
costs
duration
score
decision quality

Do not rank timeframes.

25. REJECTION ANALYSIS

The system must make rejected signals visible.

Create a rejection summary such as:

rejection_code
count
percentage
strategy
asset
timeframe

Examples:

LOW_SCORE
MAX_CONCURRENT_POSITIONS
MAX_TOTAL_EXPOSURE
MAX_ASSET_EXPOSURE
MAX_STRATEGY_EXPOSURE
DAILY_PROFIT_TARGET_REACHED
DAILY_LOSS_LIMIT_REACHED
COOLDOWN_ACTIVE
STRATEGY_PAUSED
SHORT_NOT_ALLOWED
INSUFFICIENT_CAPITAL
DUPLICATE_SIGNAL
CONFLICTING_SIGNAL

The report should help answer:

"How many opportunities were rejected, and why?"

Do not interpret rejection as strategy failure.

26. OPPORTUNITY SCORE ANALYSIS

Analyze the opportunity score descriptively.

Provide:

score distribution
average score
median score
accepted score distribution
rejected score distribution
score by strategy
score by asset
score by timeframe
score by outcome

Important:

Do NOT state that:

score = probability of winning

unless such calibration has been formally researched later.

At this stage, score is an opportunity-quality measure.

27. SCORE VS OUTCOME

It is acceptable to show retrospective descriptive relationships such as:

average score of winning trades
average score of losing trades
score distribution by outcome

However:

Do NOT infer causality.

Do NOT optimize the score threshold.

Do NOT change the threshold based on the results.

Do NOT claim that a higher score guarantees better performance.

Prompt 07 will handle robustness and out-of-sample research.

28. DAILY STRATEGY STATE ANALYSIS

Visualize strategy state transitions where available.

For example:

ACTIVE
  ↓
LOSS
  ↓
LOSS
  ↓
LOSS
  ↓
COOLDOWN
  ↓
ACTIVE

Show:

timestamp
strategy
previous state
new state
reason
consecutive losses
cooldown start
cooldown end

This should come directly from the Prompt 05 state ledger.

Do not reconstruct state retrospectively from trade outcomes if the actual state ledger exists.

29. REPORTING DATA CONTRACT

Define a clear reporting data contract.

Reporting should consume:

trades
fills
signals
risk decisions
opportunity scores
strategy states
portfolio states
equity curve
execution logs
run metadata

Do not recompute core trading logic in the reporting layer.

Reporting is an observer.

It should not become a second backtest engine.

30. REPORT FORMAT

Generate both machine-readable and human-readable outputs.

At minimum:

results/
  <run_id>/
    trades.csv
    signals.csv
    risk_decisions.csv
    opportunity_scores.csv
    strategy_state_history.csv
    portfolio_state.csv

    reports/
      daily/
      weekly/
      monthly/

    trade_charts/

    summaries/
      run_summary.json
      daily_summary.csv
      weekly_summary.csv
      monthly_summary.csv
      rejection_summary.csv
      strategy_activity.csv
      asset_activity.csv
      timeframe_activity.csv

Adapt to existing structures when appropriate.

31. HTML REPORT

Create a self-contained HTML research report when practical.

The HTML report should include:

Executive research summary
run ID
dataset
date range
assets
timeframes
strategies
configuration version
Performance overview
starting equity
ending equity
net P&L
total R
drawdown
number of trades
total costs
Equity curve
Drawdown
Daily performance
Weekly performance
Monthly performance
Trade distribution
Rejection analysis
Opportunity score analysis
Strategy activity
Asset activity
Timeframe activity
Decision-quality analysis
Trade diary index

The report should link to individual trade charts where possible.

Do not create a frontend application.

This is a static research report.

32. MARKDOWN REPORT

Also generate Markdown reports suitable for Git/version control.

Example:

reports/
  <run_id>/
    DAILY_REPORT.md
    WEEKLY_REPORT.md
    MONTHLY_REPORT.md
    TRADE_DIARY.md
    DECISION_QUALITY_REPORT.md
    REJECTION_ANALYSIS.md
    RUN_SUMMARY.md

Do not duplicate enormous datasets inside Markdown.

Use CSV/JSON for machine-readable data.

33. TRADE DIARY INDEX

Create an index of all executed trades.

Example fields:

trade_id
timestamp
symbol
timeframe
strategy
side
score
realized_R
net_pnl
duration
decision_quality
exit_reason
chart_path

The diary should make it easy to move from:

Trade ID

to:

Trade metadata

to:

Trade chart

to:

Strategy

to:

Daily report

to:

Run summary

34. REPORT FILTERING

Reporting should support configurable filters.

At minimum:

date range
strategy
symbol
timeframe
side
outcome
decision quality
score range
exit reason

Filters must not alter the underlying source data.

They only change the report view.

35. CONFIGURATION

Extend the existing configuration system.

Example:

reporting:
  enabled: true

  formats:
    csv: true
    json: true
    markdown: true
    html: true

  trade_diary:
    enabled: true

  trade_charts:
    enabled: true
    bars_before_entry: 100
    bars_after_entry: 100

  aggregation:
    timezone: UTC

  filters:
    minimum_score: null
    strategies: []
    symbols: []
    timeframes: []

  html:
    enabled: true

Do not blindly copy this structure.

Integrate it with the existing configuration architecture.

Every configurable value must be documented.

36. REPRODUCIBILITY

Every report must identify:

run_id
timestamp of report generation
code version
Git commit if available
configuration snapshot
dataset identifiers
data version
symbols
timeframes
date range
strategy versions
risk configuration
execution configuration
reporting configuration

If Git metadata is unavailable:

record that explicitly.

Never fabricate Git information.

37. POINT-IN-TIME INTEGRITY

This is mandatory.

Reporting calculations may use post-trade information because the reports are retrospective.

However, any field describing the original decision must come from the state that existed at the decision timestamp.

For example:

The trade explanation cannot say:

"the strategy entered because BTC subsequently rose."

That would be hindsight.

It must say:

"the strategy entered because conditions X/Y/Z were satisfied at timestamp T."

38. FUTURE-DATA TEST

Add tests specifically targeting reporting integrity.

Example:

Run the same historical dataset.
Generate reports.
Modify data strictly after timestamp T.
Re-run all decision-related fields for trades before T.
Verify that:
strategy metadata does not change
signal explanation does not change
score at T does not change
risk decision at T does not change
entry decision does not change

Retrospective outcome charts may change if future candles are intentionally modified, but the pre-entry decision information must not change.

39. DETERMINISM

Running the same:

data
configuration
code version

must produce identical reporting outputs, except for explicitly documented metadata such as report-generation timestamp.

Where appropriate, normalize timestamps and ordering so CSV/JSON comparisons remain deterministic.

40. TESTING

Implement unit and integration tests.

At minimum test:

Trade diary
correct trade extraction
correct P&L
correct R
correct costs
correct duration
Decision diary
accepted signal recorded
rejected signal recorded
rejection reason preserved
score preserved
strategy state preserved
Aggregation
daily aggregation
weekly aggregation
monthly aggregation
Equity
equity curve
cumulative P&L
drawdown
Decision quality
valid decision
invalid decision
incomplete audit
Point-in-time
pre-entry data cannot change because of future data
Reproducibility
identical input produces deterministic report data
Filtering
filters do not mutate source data
Missing data
missing report fields are explicit
no fabricated values
Empty periods
zero-trade days/weeks/months handled correctly
41. REAL-DATA INTEGRATION TEST

Run at least one integration test using the real historical datasets produced by Prompt 02.

The integration flow must be:

REAL BINANCE DATA
↓
PROMPT 04 STRATEGIES
↓
PROMPT 05 RISK / ORCHESTRATION
↓
PROMPT 03 EXECUTION
↓
REAL BACKTEST RESULTS
↓
PROMPT 06 REPORTING
↓
TRADE DIARY / REPORTS / CHARTS

Do not replace real data with mocks.

If network access is not needed because the dataset already exists locally, use the real local dataset.

42. JUPYTER NOTEBOOK

Create:

notebooks/06_trade_diary_and_reporting_validation.ipynb

The notebook must be runnable from beginning to end.

It must:

Section 1 — Environment

Display:

Python version
project version
dependency information where useful
run ID
Section 2 — Configuration

Display:

date range
assets
timeframes
strategies
risk configuration
reporting configuration
Section 3 — Input validation

Verify that Prompt 03/05 outputs exist and are internally consistent.

Section 4 — Trade diary

Load real trades.

Display:

trade count
sample trade records
basic statistics
Section 5 — Decision diary

Display:

accepted signals
rejected signals
rejection reasons
Section 6 — Trade visualization

Generate and display representative real trade charts.

Include examples from:

winning trade
losing trade
if available, protected/break-even trade
rejected opportunity where appropriate

Do not fabricate examples.

If a category does not exist in the dataset, explicitly report that it is unavailable.

Section 7 — Daily report

Generate and display daily summary.

Section 8 — Weekly report

Generate and display weekly summary.

Section 9 — Monthly report

Generate and display monthly summary.

Section 10 — Equity curve

Display actual equity curve.

Section 11 — Drawdown

Display actual drawdown.

Section 12 — Cost analysis

Display actual cost breakdown.

Section 13 — Opportunity score

Display score distribution and descriptive statistics.

Section 14 — Decision quality

Display:

valid decisions
invalid decisions
incomplete audits
outcome by decision quality

Do not call any category "best".

Section 15 — Rejection analysis

Display rejection counts by reason.

Section 16 — Artifact verification

Verify that expected files were created.

Section 17 — Reproducibility

Display:

run ID
config hash if available
dataset identifiers
code version
report paths
Section 18 — Final validation

Print:

PROMPT 06 VALIDATION STATUS: PASS

only if all acceptance criteria pass.

Otherwise:

PROMPT 06 VALIDATION STATUS: FAIL

and expose the actual failures.

Never print PASS when validation failed.

43. VISUALIZATION REQUIREMENTS

Use a reliable Python visualization stack already compatible with the project.

Prefer:

matplotlib
plotly

or the project's existing visualization library.

Do not introduce unnecessary dependencies.

Charts should be readable and reproducible.

At minimum implement:

Equity curve
Drawdown
Daily net P&L
Weekly net P&L
Monthly net P&L
Trade outcome distribution
Realized R distribution
Holding-duration distribution
Opportunity-score distribution
Rejection reasons
Strategy activity
Asset activity
Timeframe activity
Cost breakdown

Do not use charts to imply statistical significance that has not been tested.

Prompt 07 will handle deeper statistical robustness.

44. NO STRATEGY OPTIMIZATION

This prompt must NOT:

optimize indicators
optimize RR
optimize score threshold
optimize risk percentage
optimize cooldown duration
select top strategies
eliminate weak strategies
modify entry rules
modify exit rules
modify strategy parameters

The purpose is observation and reporting.

Optimization belongs to later research.

45. NO PERFORMANCE CLAIMS

The report must clearly distinguish:

historical backtest
descriptive statistics
research observations
hypotheses

Do not state:

"this strategy works."

Do not state:

"this strategy is profitable in the future."

Do not state:

"3:1 RR guarantees profitability."

Do not state:

"score X guarantees better trades."

Do not state:

"strategy X is the best."

Historical backtest results are not guarantees of future performance.

46. IMPORTANT INTERPRETATION RULE

The system should help answer:

Question A

"What happened?"

Question B

"What did the system know at the time?"

Question C

"Why was the opportunity accepted or rejected?"

Question D

"How was the trade executed?"

Question E

"What was the outcome?"

Question F

"Was the decision consistent with the rules?"

It should NOT prematurely answer:

"Which strategy should we trade?"

That belongs to later research.

47. DOCUMENTATION

Create:

docs/research/TRADE_DIARY_AND_REPORTING_POLICY.md

Document:

reporting architecture
data sources
trade diary schema
decision diary schema
decision-quality methodology
daily aggregation
weekly aggregation
monthly aggregation
equity calculation
drawdown calculation
cost calculation
visualization rules
point-in-time principles
reproducibility
limitations
known ambiguities

Create:

docs/execution/PROMPT_06_EXECUTION_GUIDE.md

The execution guide must explain:

What Prompt 06 implemented
Prerequisites
Exact commands to run
Notebook execution
How to validate the outputs
Expected files
Where reports are stored
Where trade charts are stored
How to inspect a single trade
How to inspect daily reports
How to inspect weekly reports
How to inspect monthly reports
How to inspect rejected signals
How to rerun the reporting process
How to reproduce a run
Known limitations
Known issues
Acceptance criteria
Troubleshooting
Next prompt
48. README UPDATE

Update:

README.md

to explain the reporting layer.

Include an updated architecture:

Market Data
    ↓
Strategies
    ↓
Signals
    ↓
Opportunity Score
    ↓
Risk Manager
    ↓
Portfolio Orchestrator
    ↓
Execution Engine
    ↓
Positions
    ↓
Trades
    ↓
Trade Diary
    ↓
Research Reports

Explain that reporting is downstream and does not influence decisions.

49. PROJECT_STATUS UPDATE

Update:

PROJECT_STATUS.md

Include:

Prompt 06 status
implementation date
components implemented
tests executed
integration validation
notebook validation
reports generated
known limitations
known issues
exact run ID(s)
next step

Use one of:

COMPLETE
PARTIAL
BLOCKED

Only mark:

COMPLETE

if the acceptance criteria actually passed.

Only state:

READY FOR PROMPT 07

if the validation genuinely passes.

50. RESULT DIRECTORY

Use the existing run/result architecture.

Each reporting run should have a reproducible directory containing, at minimum:

results/
  <run_id>/
    config_snapshot.yaml
    run_metadata.json

    trades.csv
    signals.csv
    risk_decisions.csv
    opportunity_scores.csv
    strategy_state_history.csv
    portfolio_state.csv

    summaries/
      run_summary.json
      daily_summary.csv
      weekly_summary.csv
      monthly_summary.csv
      rejection_summary.csv
      strategy_activity.csv
      asset_activity.csv
      timeframe_activity.csv

    reports/
      RUN_SUMMARY.md
      TRADE_DIARY.md
      DAILY_REPORT.md
      WEEKLY_REPORT.md
      MONTHLY_REPORT.md
      DECISION_QUALITY_REPORT.md
      REJECTION_ANALYSIS.md

    html/
      research_report.html

    trade_charts/
      ...
    
    logs/
      ...

Adapt this to the existing project architecture instead of blindly duplicating files.

51. QUALITY CONTROL

Before declaring Prompt 06 complete, verify:

Data
all reports derive from real backtest outputs
no fabricated trades
no missing trades silently discarded
Accounting
gross P&L reconciles
costs reconcile
net P&L reconciles
equity curve reconciles with trades
Decisions
accepted signals are auditable
rejected signals are auditable
rejection reasons are preserved
Point-in-time
decision information is PIT-safe
future mutation tests pass
Visuals
trade charts correspond to real trades
entry/stop/target/exit are correct
timestamps are correct
Aggregation
daily totals reconcile with trade data
weekly totals reconcile with daily data
monthly totals reconcile with daily/weekly data
Reproducibility
same input produces same analytical outputs
configuration is captured
dataset identity is captured
code version is captured where available
52. RECONCILIATION TESTS

Implement explicit reconciliation tests.

For example:

sum(daily_net_pnl)
==
total_net_pnl

and:

sum(weekly_net_pnl)
==
total_net_pnl

and:

sum(monthly_net_pnl)
==
total_net_pnl

within explicitly documented floating-point tolerances.

Likewise verify:

trade_count
==
sum(daily_trade_count)

and equivalent weekly/monthly totals.

No unexplained discrepancies.

53. REPORTING FAILURE POLICY

If any of the following occurs:

missing trade records
inconsistent P&L
inconsistent equity
missing decision data
corrupted chart input
failed reconciliation
future-data integrity failure
nondeterministic analytical result
broken report generation

DO NOT declare success.

Stop the relevant execution stage.

Expose:

error
affected run
affected artifact
affected trade/report
likely root cause if directly observable

Do not hide the problem.

54. ACCEPTANCE CRITERIA

Prompt 06 is COMPLETE only if all of the following are true:

Architecture
existing architecture reused
no parallel reporting architecture created
reporting remains downstream
Trade Diary
all real executed trades can be inspected
trade metadata is complete
trade outcome is auditable
trade chart is available
Decision Diary
accepted signals are recorded
rejected signals are recorded
rejection reasons are preserved
Decision Quality
decision quality is separated from outcome
no hindsight classification is used
Reporting
daily reports work
weekly reports work
monthly reports work
equity curve works
drawdown works
cost analysis works
Visualization
trade charts work
summary charts work
charts use real data
Reproducibility
run metadata exists
configuration snapshot exists
dataset identity exists
code version is recorded when available
Integrity
no future information influences historical decisions
future mutation test passes
Reconciliation
daily/weekly/monthly reports reconcile with trades
P&L reconciles
equity reconciles
Documentation
README updated
PROJECT_STATUS updated
TRADE_DIARY_AND_REPORTING_POLICY.md created
PROMPT_06_EXECUTION_GUIDE.md created
Validation
unit tests pass
integration tests pass where executable
notebook executes successfully
real-data reporting run completes
55. FINAL EXECUTION REPORT

At the end of the implementation, provide a concise but complete final report containing:

1. Implementation status
COMPLETE / PARTIAL / BLOCKED
2. Files created

List them.

3. Files modified

List them.

4. Tests executed

List:

test command
number passed
number failed
number skipped
reason for skips
5. Real-data validation

State:

dataset used
symbols
timeframes
date range
number of signals
number of accepted signals
number of rejected signals
number of executed trades

These must be actual values from the execution.

6. Reporting artifacts

List:

trade diary
trade charts
daily reports
weekly reports
monthly reports
HTML report
JSON summaries
CSV summaries
7. Reconciliation

Report whether:

P&L reconciles
equity reconciles
daily/weekly/monthly totals reconcile
8. Point-in-time validation

Report whether future-mutation tests passed.

9. Known limitations

List them honestly.

10. Known issues

List them honestly.

11. Next step

If and only if all acceptance criteria pass:

READY FOR PROMPT 07

Otherwise:

NOT READY FOR PROMPT 07
56. ABSOLUTE PROHIBITIONS

Do NOT:

create a frontend application
create live trading
connect trading accounts
add exchange authentication
place real orders
optimize strategies
rank strategies
select winning strategies
modify strategy rules
modify risk rules
modify execution assumptions
introduce look-ahead
fabricate data
fabricate results
use mock research results
silently suppress errors
silently drop trades
silently repair inconsistencies
present retrospective information as if it were available at entry
declare historical profitability as future certainty
57. RESEARCH PHILOSOPHY

This project is not trying to prove that a particular strategy is profitable.

Prompt 06 exists to make the research process observable.

The goal is to answer:

"Can we inspect every decision the system made and understand exactly what happened?"

A strong research system must allow us to inspect:

Opportunity
    ↓
Signal
    ↓
Score
    ↓
Risk Decision
    ↓
Execution
    ↓
Trade
    ↓
Outcome

and later:

Trade
    ↓
Chart
    ↓
Daily Context
    ↓
Weekly Context
    ↓
Monthly Context
    ↓
Research Hypothesis

without contaminating the original decision process.

Do not jump ahead to optimization.

Do not optimize based on this report.

Do not select winners.

Build the observability layer correctly.

END OF PROMPT 06