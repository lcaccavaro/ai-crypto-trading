# PROMPT 08 — PAPER TRADING, REAL-TIME RESEARCH & V1 COMPLETION

## ROLE

Act as a:

- Principal Quantitative Research Engineer
- Senior Systematic Trading Infrastructure Engineer
- Real-Time Market Data Architect
- Paper Trading Systems Engineer
- Quantitative Research Reproducibility Specialist
- Production-Grade Simulation Engineer

You are completing an existing quantitative crypto research and backtesting laboratory.

This is PROMPT 08 of an 8-prompt V1 implementation sequence.

The project already contains:

- project architecture
- configuration management
- reproducibility infrastructure
- Binance historical market-data ingestion
- canonical market datasets
- data-quality validation
- point-in-time data handling
- backtest engine
- execution simulation
- strategy library
- portfolio risk management
- opportunity scoring
- strategy state management
- trade diary
- visualization
- daily/weekly/monthly reporting
- walk-forward research
- out-of-sample analysis
- robustness analysis
- regime analysis

The purpose of Prompt 08 is to create a:

# PAPER TRADING / REAL-TIME RESEARCH MODE

using the SAME:

- strategy interfaces
- signal logic
- opportunity scoring
- risk management
- portfolio orchestration
- execution semantics
- position model
- trade model
- state management
- reporting
- trade diary

already validated in Prompts 01–07.

The system must simulate trading decisions using current/recent market data without placing real orders.

---

# 1. CRITICAL OBJECTIVE

The architecture must become:

```text
                    ┌─────────────────────┐
                    │   HISTORICAL DATA   │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  MARKET DATA LAYER  │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ STRATEGY / SIGNAL   │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ OPPORTUNITY SCORE   │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   RISK MANAGER      │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ PORTFOLIO ORCHESTR. │
                    └──────────┬──────────┘
                               │
                 ┌─────────────┴─────────────┐
                 │                           │
                 ▼                           ▼
        ┌─────────────────┐        ┌─────────────────┐
        │ BACKTEST MODE   │        │ PAPER MODE      │
        └────────┬────────┘        └────────┬────────┘
                 │                           │
                 ▼                           ▼
        Historical candles          Current market data
                 │                           │
                 ▼                           ▼
        Simulated execution        Simulated execution
                 │                           │
                 └─────────────┬─────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ POSITION / TRADE    │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ TRADE DIARY / P&L   │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ REPORTING / AUDIT   │
                    └─────────────────────┘

There must NOT be separate strategy implementations for backtest and paper trading.

2. ABSOLUTE RULES

These rules are mandatory.

2.1 Inspect the entire project first

Before changing anything:

Inspect the repository.
Inspect Prompt 01 implementation.
Inspect Prompt 02 implementation.
Inspect Prompt 03 implementation.
Inspect Prompt 04 implementation.
Inspect Prompt 05 implementation.
Inspect Prompt 06 implementation.
Inspect Prompt 07 implementation.
Read:
README.md
PROJECT_STATUS.md
architecture documentation
research policies
execution guides
configuration
tests
reporting implementation
trade diary implementation
backtest engine
execution engine
strategy interfaces
risk manager
portfolio orchestrator
data providers

Do not assume architecture.

Reuse what already exists.

3. STOP CONDITIONS

If any previous prompt is broken:

STOP.

Do not build a second architecture.

Do not work around broken interfaces.

Do not create a fake paper-trading layer.

Report:

component
file
failure
impact
required fix

Prompt 08 may only proceed after the existing system is internally consistent.

4. NO REAL TRADING

This is a strict requirement.

Prompt 08 must NOT:

place real orders
cancel real orders
modify real positions
connect to Binance trading endpoints
request trading permissions
use API keys for trading
request withdrawal permissions
connect to a real trading account
submit authenticated trading requests

The system is PAPER TRADING ONLY.

Public market-data access is acceptable.

Trading authentication is not required.

5. NO REAL-MONEY CLAIMS

Paper trading results must not be presented as:

guaranteed profit
real trading performance
proof of future profitability
evidence that live deployment is safe

Clearly label:

PAPER TRADING
SIMULATED EXECUTION
NO REAL ORDERS

in reports and logs.

6. NO STRATEGY CHANGES

Prompt 08 must NOT:

add new strategies
remove strategies
change strategy rules
optimize strategy parameters
change indicators
change signal definitions
change score logic
change risk logic
change cooldown logic
change RR to improve results

The V1 strategy universe is frozen.

Any modification discovered to be necessary must be documented as a V2 research item.

7. NO FUTURE INFORMATION

The paper-trading engine must preserve the same point-in-time rules as the historical engine.

At time T, the system may only use:

information available at or before T

Never:

future candles
future candle close
future high/low
future strategy performance
future trade outcomes
future regime classification
future P&L
future score values
8. LIVE DATA SOURCE

Use Binance public market data.

The initial implementation should prefer public endpoints that do not require authentication.

The initial market type should remain consistent with the historical project.

If Prompt 02 established Binance Spot as the initial market:

continue using Binance Spot.

Do NOT silently mix:

Spot
Futures
Perpetuals

as if they were equivalent.

9. DATA PROVIDER ABSTRACTION

Create or extend the existing market-data provider interface.

The system should support a paper-data provider such as:

HistoricalDataProvider
PaperMarketDataProvider

Both must expose compatible market-data contracts.

Do not duplicate strategy logic.

10. PAPER DATA MODES

Implement configurable paper-data modes where practical.

At minimum:

LIVE_STREAM

and:

POLLING

if supported cleanly by the existing architecture.

The default implementation should choose the simplest reliable public Binance data mechanism.

Do not over-engineer WebSocket infrastructure if it is unnecessary for the first working V1.

11. CANDLE-CLOSE EXECUTION

For strategies operating on candles:

A signal based on a candle close may only be generated after that candle is complete.

For example:

10:00–10:05 candle

cannot generate a close-based signal before:

10:05

If the strategy generates a signal at candle close:

the earliest simulated execution must follow the same timing rules established in Prompt 03.

Do not introduce:

same-candle hindsight execution
12. REAL-TIME EVENT LOOP

Implement a controlled paper-trading event loop.

Conceptually:

WAIT FOR NEW MARKET DATA
        ↓
VALIDATE DATA
        ↓
UPDATE MARKET STATE
        ↓
UPDATE CLOSED CANDLES
        ↓
UPDATE STRATEGIES
        ↓
GENERATE SIGNALS
        ↓
CALCULATE SCORE
        ↓
RISK DECISION
        ↓
PAPER ORDER
        ↓
SIMULATED FILL
        ↓
POSITION UPDATE
        ↓
TRADE STATE UPDATE
        ↓
REPORTING
        ↓
WAIT FOR NEXT EVENT

The event loop must be deterministic where the data stream is deterministic.

13. MULTI-ASSET SUPPORT

Paper mode must support multiple configured assets.

Example:

BTCUSDT
ETHUSDT
SOLUSDT

Do not hard-code these symbols.

Use the existing configuration.

14. MULTI-TIMEFRAME SUPPORT

Paper mode must support the same configured timeframes used by the strategy layer.

Example:

1m
3m
5m
15m
30m
1h

A strategy must only receive a timeframe candle once that candle is actually closed.

15. MULTI-TIMEFRAME POINT-IN-TIME EXAMPLE

At:

10:15 UTC

the system may use:

10:00–10:15 15m candle

only if it has actually closed.

It may NOT use:

10:15–10:30

because that candle does not exist yet.

Likewise, an:

10:00–11:00 1h candle

is not available as a completed candle at 10:15.

This rule must be explicitly tested.

16. MARKET DATA VALIDATION

Every incoming candle/update must pass validation.

Validate:

timestamp
symbol
timeframe
open
high
low
close
volume
chronological ordering
duplicates
OHLC invariants
timestamp consistency

Reuse Prompt 02 validation logic.

Do not create a weaker validation path for paper trading.

17. DATA GAP HANDLING

If expected market data is missing:

do NOT:

invent candles
forward-fill prices
create synthetic candles
silently continue

The system should:

detect the gap
record it
determine whether the affected strategy can safely continue
follow an explicit configured policy

Default should be conservative.

If a decision cannot safely be evaluated because required market data is unavailable:

do not fabricate the decision.

Record the event.

18. RECONNECTION HANDLING

If the market-data connection is interrupted:

implement bounded, observable recovery.

The system may:

reconnect
reinitialize the public market-data stream
synchronize missing data

But:

Do not silently resume as if nothing happened.

Record:

disconnect timestamp
reconnect timestamp
affected symbols
affected timeframes
recovered candles
unrecoverable gaps
19. NO SILENT DATA LOSS

Every paper session must have an audit trail.

At minimum:

session_start
market_data_received
market_data_rejected
connection_lost
connection_restored
candle_closed
signal_generated
score_calculated
risk_decision
paper_order_created
paper_fill
position_opened
position_updated
position_closed
trade_completed
session_end
error
20. PAPER ORDER MODEL

Reuse the existing Order model.

A paper order must include:

order_id
timestamp
symbol
side
quantity
order_type
requested_price
expected_price
simulated_fill_price
slippage
fees
status
strategy_id
run_id
session_id

Clearly identify:

execution_mode = PAPER
21. PAPER FILL MODEL

Reuse the existing Fill model.

Every simulated fill must contain:

fill_id
order_id
timestamp
symbol
side
quantity
price
fee
slippage
spread assumption
execution_mode

No real exchange order ID should exist.

22. PAPER EXECUTION MODEL

Paper execution must reuse the execution semantics from Prompt 03.

This includes:

fees
spread
slippage
stop
target
gap behavior
ambiguous candle policy
position sizing
execution assumptions

Do not create a second execution model.

23. LIVE PRICE VS CLOSED-CANDLE PRICE

Clearly distinguish:

market update

from:

closed candle

Strategies using candle-close logic must receive only completed candles.

Position monitoring may use the latest available market information where appropriate.

Document the distinction.

24. OPEN POSITION MONITORING

Paper mode must continue monitoring open positions.

For each open position track:

current price
unrealized P&L
current R
stop distance
target distance
maximum favorable excursion
maximum adverse excursion
duration
current exposure

Use the existing position model.

25. STOP / TARGET MONITORING

Use the same execution rules from Prompt 03.

If the paper market-data stream provides insufficient granularity to determine intrabar ordering:

use the same conservative ambiguity policy already established.

Do not pretend to know the exact order of stop and target hits when the available data cannot establish it.

26. DAILY RISK RULES

Reuse Prompt 05.

Paper mode must support:

daily profit target
daily loss limit
maximum concurrent positions
maximum total exposure
maximum asset exposure
maximum strategy exposure
risk per trade
strategy cooldown
strategy state

Do not create separate paper-only risk rules.

27. STRATEGY COOLDOWN

Reuse Prompt 05 strategy-state logic.

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

Cooldown must:

block new entries
not automatically close existing positions
remain auditable
expire according to configured time

Do not modify the threshold in Prompt 08.

28. OPPORTUNITY SCORE

Reuse Prompt 05.

The same score must be used in paper mode.

Record:

score
score version
component values
threshold
decision

Do not recalibrate the score using paper results.

29. PAPER SESSION

Introduce the concept of a:

PaperTradingSession

Each session should have:

session_id
run_id
start timestamp
end timestamp
execution_mode
market_type
symbols
timeframes
strategy universe
configuration snapshot
initial paper balance
current balance
realized P&L
unrealized P&L
fees
slippage
state
shutdown reason
30. SESSION STATES

Support explicit session states:

INITIALIZING
RUNNING
PAUSED
STOPPING
STOPPED
FAILED

Transitions must be logged.

31. SAFE SHUTDOWN

Implement a controlled shutdown.

On shutdown:

stop new signals
stop new paper orders
preserve current state
record open positions
flush logs
persist session state
generate final session report
exit cleanly

Do NOT automatically close open paper positions unless explicitly configured.

32. SESSION RESUME

Where practical, support session persistence and resume.

A resumed session must restore:

balance
open positions
strategy states
cooldowns
daily risk state
portfolio exposure
trade counters
session metadata

Do not silently restart from zero.

If safe resume is not possible:

fail explicitly and require a new session.

33. PAPER CAPITAL

Paper capital must be configurable.

Example:

paper_trading:
  initial_balance: 10000

Do not interpret this as a recommended real trading balance.

It is purely a simulation parameter.

34. PAPER P&L

Track:

Realized P&L

from closed paper trades.

Unrealized P&L

from open positions.

Gross P&L

before costs.

Costs
fees
spread
slippage
Net P&L

after costs.

Use the same accounting conventions as the historical backtest.

35. PAPER EQUITY

Track:

equity =
cash
+ unrealized position value

according to the existing portfolio accounting model.

Do not create inconsistent accounting between backtest and paper mode.

36. PAPER TRADE DIARY

Every paper trade must automatically enter the same Trade Diary architecture from Prompt 06.

The diary must clearly indicate:

execution_mode = PAPER

The same fields should be available:

strategy
asset
timeframe
signal
score
risk decision
entry
stop
target
exit
realized R
gross P&L
costs
net P&L
duration
decision quality
exit reason
37. PAPER TRADE CHARTS

Reuse Prompt 06 visualization.

When a paper trade closes, optionally generate a trade chart.

The chart must distinguish:

PAPER TRADING

from historical backtest results.

Do not mix them in aggregate historical reports.

38. PAPER SESSION REPORT

At session end generate:

PAPER SESSION REPORT

including:

session ID
duration
assets
timeframes
strategies
initial balance
ending balance
realized P&L
unrealized P&L
net P&L
fees
spread
slippage
trades
wins
losses
average R
drawdown
max concurrent positions
rejected signals
rejection reasons
strategy state changes
data interruptions
errors
warnings
39. PAPER DAILY REPORT

Reuse Prompt 06 daily reporting.

Add:

execution_mode = PAPER

Do not mix paper and historical trades.

40. PAPER REPORT SEPARATION

Historical:

BACKTEST

Paper:

PAPER

must be separate datasets.

Never merge them into one performance series.

41. LIVE SESSION AUDIT

Create a session audit log.

Example:

results/
  paper/
    <session_id>/
      session_metadata.json
      market_events.csv
      signals.csv
      opportunity_scores.csv
      risk_decisions.csv
      orders.csv
      fills.csv
      positions.csv
      trades.csv
      strategy_state_history.csv
      portfolio_state.csv
      logs/
      reports/
      trade_charts/

Adapt to the existing project structure.

42. PAPER DATA SNAPSHOT

At session start record:

configured assets
configured timeframes
strategies
configuration hash
code version
Git commit if available
market type
data source
session timestamp

Do not fabricate metadata.

43. MARKET DATA LATENCY

Where possible, measure:

market data receive timestamp
candle timestamp
processing timestamp
signal timestamp
paper order timestamp
simulated fill timestamp

Calculate:

data_latency
processing_latency
decision_latency

These are operational metrics.

Do not interpret them as profitability metrics.

44. CLOCK SYNCHRONIZATION

All internal timestamps must use UTC.

Record local machine time only as optional metadata.

Detect obviously invalid timestamp behavior.

Document clock assumptions.

45. DUPLICATE EVENTS

The paper engine must be idempotent.

If the same candle/update is received twice:

do not:

generate duplicate signals
create duplicate orders
duplicate fills
duplicate trades

Record duplicate events when useful.

46. EVENT IDS

Where possible assign deterministic IDs to events.

Examples:

market_event_id
signal_id
order_id
fill_id
position_event_id
trade_id

This enables auditability.

47. ERROR HANDLING

Errors must be visible.

Do NOT:

try:
    ...
except Exception:
    pass

Do NOT silently continue after a critical accounting or state error.

Classify errors:

DATA_ERROR
STATE_ERROR
EXECUTION_ERROR
CONFIGURATION_ERROR
INTEGRATION_ERROR
UNEXPECTED_ERROR

Critical errors must transition the session to:

FAILED

when continuing would make results unreliable.

48. FAIL-SAFE PRINCIPLE

If the system cannot determine the state of:

an order
a fill
a position
portfolio exposure
strategy state

it must NOT invent the state.

Stop or pause according to explicit policy.

Preserve the error.

49. PAPER TRADING CONFIGURATION

Extend the existing configuration system.

Example:

paper_trading:
  enabled: true

  execution_mode: PAPER

  initial_balance: 10000

  market_data:
    provider: binance_public
    mode: polling

  session:
    auto_start: false
    resume_enabled: true

  safety:
    allow_real_orders: false
    require_paper_mode: true

  persistence:
    checkpoint_interval_seconds: 30

  reporting:
    generate_trade_charts: true
    generate_session_report: true

Do not blindly use these exact values.

Integrate them with the existing configuration system.

50. HARD SAFETY GUARD

Implement an explicit safety guard preventing real order execution.

For example, the execution layer must reject any attempt to use a real trading adapter from Prompt 08.

The paper environment should require:

execution_mode = PAPER

and reject:

execution_mode = LIVE

in this implementation.

This must be tested.

51. NO API TRADING CREDENTIALS

The paper implementation must not require:

API key
API secret
trading permission
account permission

Public market-data access should be sufficient.

If the existing project contains credential configuration for another future stage:

do not activate it.

52. PAPER BACKTEST PARITY

The same strategy/risk/execution configuration should behave consistently when fed equivalent market events.

Create a parity test where possible.

Conceptually:

Historical event stream
        ↓
Backtest engine

Equivalent event stream
        ↓
Paper engine

Under equivalent data and timing assumptions:

core decision logic should produce equivalent:

signals
scores
risk decisions
order decisions

where differences are only due to intentionally different runtime/data-source mechanics.

53. DETERMINISTIC REPLAY MODE

This is strongly recommended.

Implement a:

REPLAY

mode using historical market data but feeding it through the paper-trading event loop one event at a time.

Purpose:

Validate that:

BACKTEST MODE

and:

PAPER EVENT LOOP

do not diverge unexpectedly.

Replay is not a new strategy.

It is a validation tool.

54. REPLAY MODE

Example:

paper_trading:
  mode: replay
  replay:
    dataset_id: ...
    speed: 0

Where:

speed = 0

means process as fast as possible.

Optional:

speed > 0

may simulate time progression.

Do not make wall-clock timing part of trading logic.

55. REPLAY ACCEPTANCE TEST

Run the same historical period through:

BACKTEST

and:

PAPER REPLAY

Compare:

signals
score
risk decisions
entries
exits
trades
realized R
P&L
costs

Differences must be:

zero
or explicitly explained

Do not accept unexplained divergence.

56. LIVE VS REPLAY DIFFERENCE

If live public market data has characteristics that cannot be reproduced exactly:

document:

latency
partial updates
exchange stream behavior
reconnect behavior
candle construction differences

Do not claim exact live equivalence.

57. SESSION MONITORING

Implement a simple terminal/Jupyter status view.

At minimum display:

SESSION
STATUS
UPTIME

BALANCE
EQUITY
REALIZED P&L
UNREALIZED P&L
NET P&L

OPEN POSITIONS
EXPOSURE

SIGNALS
ACCEPTED
REJECTED

TRADES
WINS
LOSSES

STRATEGIES ACTIVE
STRATEGIES PAUSED
STRATEGIES COOLDOWN

LAST MARKET EVENT
LAST SIGNAL
LAST ORDER
LAST FILL

Do not build a frontend application.

A terminal or notebook interface is sufficient.

58. NO PERFORMANCE OPTIMIZATION

Prompt 08 must NOT:

optimize strategy parameters
optimize risk
optimize score
optimize RR
optimize cooldown
optimize polling interval to improve trading results
optimize asset selection

Operational configuration may be adjusted for reliability, but not to manufacture performance.

59. PAPER TRADING PERFORMANCE INTERPRETATION

Paper results are observational.

The system must explicitly distinguish:

BACKTEST RESULT

from:

PAPER RESULT

Paper trading can reveal:

operational problems
data issues
signal timing problems
state-management bugs
unexpected execution assumptions
live-market behavior differences
latency effects
strategy activation behavior

It does NOT prove future live profitability.

60. PAPER VS BACKTEST COMPARISON

Create a report comparing:

BACKTEST
vs
PAPER

only where comparable.

Compare:

signal count
accepted signals
rejected signals
trade count
average duration
costs
realized R
P&L
data interruptions
execution differences

Do not force the results to match.

Explain discrepancies.

61. DRIFT DETECTION

Implement descriptive monitoring for differences between recent paper behavior and historical research.

Examples:

signal frequency drift
opportunity score drift
rejection-rate drift
holding-time drift
cost drift
volatility drift
regime distribution drift

Do not automatically disable strategies based on drift.

Do not automatically modify parameters.

Create warnings for research.

62. PAPER DRIFT WARNINGS

Possible warnings:

SIGNAL_FREQUENCY_DRIFT
SCORE_DISTRIBUTION_DRIFT
COST_DRIFT
VOLATILITY_DRIFT
REGIME_DISTRIBUTION_DRIFT
EXECUTION_DRIFT

Thresholds must be configurable.

These are monitoring warnings, not trading signals.

63. PAPER SESSION HEALTH

Implement session-health checks.

At minimum:

data freshness
last event age
duplicate events
missing events
state consistency
portfolio accounting consistency
open-position consistency
strategy-state consistency
disk persistence
error count
64. HEARTBEAT

Implement a configurable heartbeat.

Example:

HEARTBEAT
timestamp
session_id
last_market_event
open_positions
equity
realized_pnl
unrealized_pnl
errors
warnings

The heartbeat is operational only.

65. CHECKPOINTING

Persist paper session state periodically.

Checkpoint:

balance
positions
strategy states
portfolio state
risk state
last processed event
session metadata

The checkpoint must be atomic where practical.

Do not leave corrupted partial state silently.

66. RECOVERY TEST

Simulate:

Start paper session.
Process events.
Create positions.
Stop session.
Persist checkpoint.
Restart.
Resume.
Continue processing.

Verify:

no duplicate trades
no duplicate fills
no duplicate signals
balance preserved
position preserved
strategy state preserved
cooldown preserved
event ordering preserved
67. PAPER SESSION LOGGING

Use structured logs.

At minimum:

timestamp
session_id
run_id
event_type
symbol
timeframe
strategy_id
event_id
message
severity

Do not log secrets because no trading credentials should be used.

68. PAPER SESSION REPORTING

Reuse Prompt 06 reporting infrastructure.

Do not create a second reporting engine.

The reporting layer should accept:

execution_mode = PAPER

and generate the same analytical structures.

69. JUPYTER NOTEBOOK

Create:

notebooks/08_paper_trading_validation.ipynb

The notebook must validate the complete V1 system.

70. NOTEBOOK SECTION 1 — ENVIRONMENT

Display:

Python version
project version
Git commit if available
configuration version
timestamp
71. NOTEBOOK SECTION 2 — SYSTEM STATUS

Verify:

Prompt 01 status
Prompt 02 status
Prompt 03 status
Prompt 04 status
Prompt 05 status
Prompt 06 status
Prompt 07 status

Stop if a prerequisite is invalid.

72. NOTEBOOK SECTION 3 — CONFIGURATION

Display:

assets
timeframes
strategies
RR
risk
score
cooldown
costs
paper initial balance
execution mode

Explicitly display:

EXECUTION MODE: PAPER
REAL ORDERS: DISABLED
73. NOTEBOOK SECTION 4 — SAFETY TEST

Attempt to validate that:

LIVE

execution is impossible through the Prompt 08 interface.

The test must confirm that real trading is rejected.

Do not actually attempt to send an order.

74. NOTEBOOK SECTION 5 — DATA PROVIDER

Initialize the public Binance market-data provider.

Verify:

connection
symbol availability
timeframe availability
timestamps
candle structure

Use real public market data.

75. NOTEBOOK SECTION 6 — HISTORICAL REPLAY

Run a deterministic replay using an actual historical dataset.

Compare:

BACKTEST
vs
PAPER REPLAY
76. NOTEBOOK SECTION 7 — PARITY VALIDATION

Display comparison:

signals
scores
risk decisions
orders
fills
trades
P&L

Report:

MATCH
MISMATCH

for each category.

Any mismatch must be explained.

77. NOTEBOOK SECTION 8 — PAPER SESSION

Start a paper session using public Binance market data.

The implementation must use a controlled test duration or explicit stop condition.

Do not create an endless notebook cell.

The notebook must be able to stop cleanly.

78. NOTEBOOK SECTION 9 — SESSION MONITOR

Display session state:

balance
equity
P&L
positions
signals
trades
strategy states
last market event
warnings
79. NOTEBOOK SECTION 10 — TRADE VALIDATION

If trades occur, display:

trade ID
strategy
asset
timeframe
entry
stop
target
exit
R
P&L
costs
decision quality

If no trades occur during the validation window:

DO NOT fabricate trades.

Report:

NO PAPER TRADES OCCURRED DURING THE VALIDATION WINDOW

and continue validating the rest of the system.

80. NOTEBOOK SECTION 11 — SESSION SHUTDOWN

Perform a controlled shutdown.

Verify:

logs flushed
state persisted
open positions recorded
report generated
session state = STOPPED
81. NOTEBOOK SECTION 12 — RECOVERY

Restart from the persisted checkpoint where practical.

Verify:

session state restored
positions restored
balance restored
strategy states restored
no duplicate events
82. NOTEBOOK SECTION 13 — REPORTING

Generate:

paper session summary
paper trade diary
paper charts
rejection report
strategy-state report
equity curve
drawdown

All must be clearly marked:

PAPER
83. NOTEBOOK SECTION 14 — DRIFT

Display any observed:

signal-frequency drift
score drift
cost drift
volatility drift
regime drift
execution drift

If there is insufficient paper history:

report:

INSUFFICIENT PAPER HISTORY FOR DRIFT ANALYSIS

Do not fabricate conclusions.

84. NOTEBOOK SECTION 15 — FINAL V1 VALIDATION

Validate:

data
strategy
score
risk
execution
portfolio
state
persistence
reporting
audit
safety

Only if all mandatory criteria pass:

PROMPT 08 VALIDATION STATUS: PASS
V1 STATUS: COMPLETE

Otherwise:

PROMPT 08 VALIDATION STATUS: FAIL
V1 STATUS: INCOMPLETE
85. TESTING

Implement unit and integration tests.

At minimum:

Safety
real execution mode rejected
paper mode enforced
Data
valid candle accepted
invalid candle rejected
duplicate candle handled
missing data detected
Timing
closed candle required
future candle rejected
multi-timeframe PIT enforced
Signals
signal generated once
duplicate event does not duplicate signal
Risk
Prompt 05 rules reused
cooldown works
daily limits work
exposure limits work
Execution
paper order generated
paper fill generated
costs applied
stop/target semantics preserved
Accounting
P&L reconciles
equity reconciles
fees reconcile
State
position state preserved
strategy state preserved
portfolio state preserved
Recovery
checkpoint restore works
no duplicate trades after restart
Reporting
paper trades enter trade diary
reports are generated
execution_mode = PAPER
Replay
backtest and replay decisions match
86. REAL MARKET-DATA TEST

The validation must use real Binance public market data.

Do not replace it with mock data.

If network access is temporarily unavailable:

clearly report that the live-data validation could not execute.

Do not claim PASS.

Do not create fake results.

87. PAPER SESSION DURATION

Do not hard-code a specific duration.

Make the validation period configurable.

For example:

paper_trading:
  validation:
    duration_minutes: 30

The exact value should be chosen based on practical validation needs.

The system must support clean manual termination.

88. MANUAL STOP

Provide a safe way to stop a paper session manually.

The stop must:

prevent new entries
preserve open positions
flush state
generate final report
mark session STOPPED

Do not automatically close positions unless configured.

89. SESSION TERMINATION REASONS

Record:

MANUAL_STOP
SCHEDULED_STOP
DATA_ERROR
STATE_ERROR
CONFIGURATION_ERROR
UNEXPECTED_ERROR
SYSTEM_SHUTDOWN
90. SESSION DATA RETENTION

Never overwrite previous paper sessions.

Every session must have a unique:

session_id

and separate result directory.

91. RESEARCH REPRODUCIBILITY

For every paper session record:

session ID
run ID
configuration
code version
Git commit
strategy versions
risk version/configuration
score version
data provider
market type
assets
timeframes
start/end
initial paper balance
92. PAPER VS HISTORICAL DATA LINEAGE

Clearly distinguish:

HISTORICAL_DATASET

from:

PUBLIC_MARKET_DATA_STREAM

Do not combine them without recording lineage.

93. V1 ARCHITECTURE FREEZE

At the end of Prompt 08:

The V1 architecture should be considered frozen.

Any future changes must be treated as:

V2 RESEARCH

or:

V2 ENGINEERING

and must not silently modify V1 results.

94. V1 COMPLETION DOCUMENT

Create:

docs/research/V1_RESEARCH_SYSTEM.md

This document must explain:

Objective

What the V1 system was designed to research.

Architecture

Complete architecture from:

Data
→ Strategy
→ Score
→ Risk
→ Orchestration
→ Execution
→ Trade
→ Reporting
→ Robustness
→ Paper
Data

Sources and limitations.

Strategies

How the strategy universe works.

Risk

Risk and portfolio controls.

Execution

Execution assumptions.

Research

Walk-forward/OOS methodology.

Reporting

Trade diary and reports.

Paper

Paper trading architecture.

Limitations

Known limitations.

V2 candidates

Future research ideas without implementing them.

95. FINAL README UPDATE

Update README.md with the complete V1 architecture:

                         ┌─────────────────────┐
                         │    MARKET DATA      │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │     STRATEGIES      │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │ OPPORTUNITY SCORE   │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │   RISK MANAGER      │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │ PORTFOLIO ORCHESTR. │
                         └──────────┬──────────┘
                                    │
                       ┌────────────┴────────────┐
                       │                         │
                       ▼                         ▼
               ┌──────────────┐          ┌──────────────┐
               │  BACKTEST    │          │    PAPER     │
               └──────┬───────┘          └──────┬───────┘
                      │                         │
                      └────────────┬────────────┘
                                   ▼
                         ┌─────────────────────┐
                         │ POSITIONS / TRADES  │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │   TRADE DIARY       │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │ REPORTING           │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │ ROBUSTNESS / OOS    │
                         └─────────────────────┘
96. PROJECT_STATUS UPDATE

Update:

PROJECT_STATUS.md

with:

Prompt 08 status
V1 completion status
paper session IDs
replay validation IDs
tests
real-data validation
safety validation
recovery validation
known limitations
unresolved issues
V2 candidates

Use:

COMPLETE
PARTIAL
BLOCKED

Only mark V1:

COMPLETE

if all mandatory acceptance criteria pass.

97. EXECUTION GUIDE

Create:

docs/execution/PROMPT_08_EXECUTION_GUIDE.md

It must contain:

What Prompt 08 implemented
Prerequisites
Configuration
Safety model
How to run paper mode
How to run replay mode
How to stop a session
How to resume a session
How to inspect logs
How to inspect trades
How to inspect paper reports
How to inspect charts
How to compare paper vs backtest
How to interpret drift warnings
How to reproduce a session
Known limitations
Known issues
Troubleshooting
V1 acceptance criteria
V2 recommendations
98. PAPER RESULT DIRECTORY

Use the existing result architecture.

A possible structure:

results/
  paper/
    <session_id>/
      session_metadata.json
      config_snapshot.yaml

      market_events.csv
      signals.csv
      opportunity_scores.csv
      risk_decisions.csv

      orders.csv
      fills.csv
      positions.csv
      trades.csv

      strategy_state_history.csv
      portfolio_state.csv

      checkpoints/
        ...

      logs/
        ...

      reports/
        SESSION_SUMMARY.md
        PAPER_TRADE_DIARY.md
        DAILY_REPORT.md

      html/
        session_report.html

      trade_charts/
        ...

Adapt to existing architecture.

Do not create redundant storage systems.

99. REPLAY RESULT DIRECTORY

Example:

results/
  replay/
    <run_id>/
      replay_metadata.json
      comparison/
        signals.csv
        scores.csv
        risk_decisions.csv
        trades.csv
        mismatches.csv
        summary.json
100. MISMATCH REPORT

If backtest vs replay differs, generate:

mismatches.csv

Each mismatch should contain:

timestamp
symbol
timeframe
strategy
event type
backtest value
replay value
difference
explanation if known

Do not hide mismatches.

101. PARITY ACCEPTANCE

Replay is considered valid only if:

signal timing matches
score values match
risk decisions match
orders match
fills match under equivalent assumptions
trade lifecycle matches
P&L reconciles

Any legitimate difference must be explicitly documented.

102. PAPER ACCOUNTING RECONCILIATION

At session end verify:

starting_balance
+ realized_net_pnl
+ unrealized_pnl
- withdrawals
+ deposits
=
ending_equity

For this system, deposits and withdrawals should normally be zero.

Do not invent them.

103. POSITION RECONCILIATION

Verify:

open positions
+
closed positions
=
all position lifecycle events

No position may disappear from the ledger.

104. ORDER RECONCILIATION

Verify:

paper orders
→ fills
→ positions
→ trades

Any rejected order must have an explicit reason.

105. SIGNAL RECONCILIATION

Verify:

signals
→ risk decisions
→ accepted/rejected
→ orders

No signal should silently disappear.

106. FINAL V1 AUDIT

Before declaring V1 complete, perform a final audit covering:

Data
real source
quality
PIT
Strategy
deterministic
versioned
no future data
Score
versioned
PIT
auditable
Risk
deterministic
auditable
Execution
costs
slippage
spread
stop
target
ambiguity
Portfolio
exposure
state
cooldown
Reporting
trade diary
charts
daily
weekly
monthly
Research
walk-forward
OOS
sensitivity
regimes
Paper
public data
simulated orders
no real trading
persistence
recovery
audit
107. V1 ACCEPTANCE CRITERIA

Prompt 08 is COMPLETE only if all mandatory criteria pass.

Architecture
existing architecture reused
no duplicate strategy engine
no duplicate risk engine
no duplicate execution engine
no duplicate reporting engine
Safety
real trading impossible through Prompt 08
paper mode explicitly enforced
no trading credentials required
Data
real Binance public market data works
data validation works
gaps are observable
duplicates are handled
Timing
candle-close semantics preserved
multi-timeframe PIT preserved
no future data
Paper Execution
paper orders work
paper fills work
costs work
stops work
targets work
positions work
trades work
Risk
daily limits work
exposure limits work
strategy cooldown works
score works
State
strategy state persists
portfolio state persists
position state persists
checkpoint works
Recovery
session can resume
no duplicate events
no duplicate trades
Replay
backtest vs replay parity validated
unexplained mismatches = failure
Reporting
paper trade diary works
charts work
session report works
paper data remains separate from historical data
Monitoring
session health works
heartbeat works
operational warnings work
Documentation
README updated
PROJECT_STATUS updated
V1_RESEARCH_SYSTEM.md created
PROMPT_08_EXECUTION_GUIDE.md created
108. FINAL EXECUTION REPORT

At the end of implementation provide:

1. Prompt 08 status
COMPLETE / PARTIAL / BLOCKED
2. V1 status
COMPLETE / INCOMPLETE
3. Files created

List all important files.

4. Files modified

List all important files.

5. Tests

Report:

total
passed
failed
skipped
reasons
6. Replay validation

Report actual:

period
symbols
timeframes
signals
risk decisions
trades
mismatches
7. Paper validation

Report actual:

session ID
duration
symbols
timeframes
strategies
market events
signals
accepted signals
rejected signals
trades
open positions
realized P&L
unrealized P&L
costs
errors
warnings

If no trades occurred:

say so explicitly.

Do not fabricate trades.

8. Safety validation

Confirm:

real trading disabled
trading authentication unused
paper mode enforced
9. Recovery validation

Report whether checkpoint/recovery passed.

10. Reporting validation

Report whether:

trade diary
charts
session report
daily report

were generated successfully.

11. Known limitations

List them honestly.

12. Known issues

List them honestly.

13. V1 conclusion

Do NOT say:

"the system is profitable."

Instead describe:

whether the complete research pipeline executes
whether historical validation works
whether OOS research works
whether paper mode works
whether replay parity works
remaining limitations

Only if ALL mandatory criteria pass:

V1 STATUS: COMPLETE

Otherwise:

V1 STATUS: INCOMPLETE
109. V2 RESEARCH BACKLOG

Do not implement V2 features in Prompt 08.

Instead create a backlog of possible future research areas.

Examples:

B3 market integration
Binance Futures/Perpetuals
order-book data
tick-level execution
deeper liquidity modeling
advanced regime models
statistical calibration of opportunity score
portfolio correlation
dynamic capital allocation
more sophisticated execution models
additional datasets
alternative market data providers
advanced walk-forward methodologies
multiple-testing corrections
feature research
machine-learning experiments
live/paper monitoring improvements

These are future research ideas.

Do not implement them now.

110. FINAL RESEARCH PHILOSOPHY

The purpose of Prompt 08 is NOT:

"Make the strategy trade real money."

The purpose is:

"Prove that the entire research system can operate consistently on current market data without changing the research logic."

The V1 system should therefore establish:

HISTORICAL DATA
       ↓
BACKTEST
       ↓
TRADE DIARY
       ↓
WALK-FORWARD
       ↓
OUT-OF-SAMPLE
       ↓
ROBUSTNESS
       ↓
PAPER TRADING
       ↓
OBSERVATION

The final question is not:

"Did we make money?"

The more important V1 question is:

"Can we trust the research pipeline enough to continue investigating it?"

That requires:

reproducibility
point-in-time integrity
deterministic behavior
realistic costs
auditable decisions
explicit risk controls
robust historical validation
out-of-sample validation
operational paper testing
transparent failures

If the evidence is weak:

say so.

If the system fails:

stop.

If paper trading produces no trades:

report that.

If backtest and replay diverge:

show the mismatch.

If robustness fails:

document the failure.

Do not force a positive conclusion.

Do not optimize until the results look good.

Do not hide instability.

Do not connect real trading.

The objective is a scientifically auditable V1 research system.

END OF PROMPT 08