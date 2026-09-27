# PROMPT 05 — PORTFOLIO RISK MANAGEMENT, STRATEGY ORCHESTRATION & POINT-IN-TIME DECISION CONTROL

## ROLE

You are acting as a:

- Principal Quantitative Research Engineer
- Senior Systematic Trading Researcher
- Portfolio Risk Architecture Specialist
- Quantitative Strategy Orchestration Engineer
- Market Risk / Position Sizing Engineer

You are continuing the implementation of the existing quantitative research laboratory.

The project has already completed:

- Prompt 01 — Project Foundation / Architecture / Reproducibility
- Prompt 02 — Binance Market Data Ingestion / Normalization / Data Quality
- Prompt 03 — Point-in-Time Backtest Engine / Historical Execution Simulator
- Prompt 04 — Strategy Library / Multi-Asset / Multi-Timeframe Strategy Research

Your responsibility in this prompt is to implement:

> PORTFOLIO-LEVEL RISK MANAGEMENT + STRATEGY ORCHESTRATION + POINT-IN-TIME STRATEGY STATE MANAGEMENT + OPPORTUNITY SCORING

The objective is to allow many strategy instances to operate simultaneously while the system controls:

- capital;
- risk;
- exposure;
- daily limits;
- strategy state;
- consecutive losses;
- opportunity quality;
- conflicting signals;
- portfolio concentration.

---

# 1. ABSOLUTE PROJECT RULES

These rules are mandatory.

## 1.1 Inspect Before Modifying

Before writing code:

1. Inspect the complete repository.
2. Inspect Prompt 01.
3. Inspect Prompt 02.
4. Inspect Prompt 03.
5. Inspect Prompt 04.
6. Inspect:
   - README.md
   - PROJECT_STATUS.md
   - configuration
   - architecture documentation
   - research principles
   - data policy
   - backtest engine policy
   - strategy library policy
   - strategy catalog
   - existing tests
   - notebooks
   - results
   - existing risk-related components
7. Understand how the current strategy → signal → order → execution flow works.

Do not create a parallel architecture.

Extend the existing architecture.

---

# 2. DO NOT PROCEED IF PROMPT 04 IS NOT VALIDATED

Before implementation verify:

- Prompt 04 acceptance criteria passed;
- strategy registry works;
- strategy instances work;
- point-in-time tests pass;
- strategy state isolation tests pass;
- real Binance integration works;
- Prompt 03 engine is still passing;
- strategy signals are being generated correctly.

If Prompt 04 is broken:

STOP.

Do not work around the problem.

Do not create duplicate strategy infrastructure.

Do not fabricate results.

---

# 3. PRIMARY OBJECTIVE

Implement the portfolio decision layer responsible for answering:

> Given a strategy signal at time T, should the system allow this opportunity?

The system must evaluate:

1. Is the strategy active?
2. Is the strategy temporarily paused?
3. Is the asset allowed?
4. Is the timeframe allowed?
5. Is the market side allowed?
6. Is there enough capital?
7. Is risk-per-trade within limits?
8. Is portfolio exposure within limits?
9. Is asset exposure within limits?
10. Is strategy exposure within limits?
11. Has the daily profit target been reached?
12. Has the daily loss limit been reached?
13. Has the strategy reached its consecutive-loss limit?
14. Does the opportunity satisfy the configured score threshold?
15. Would the trade conflict with existing portfolio constraints?
16. What position size is allowed?
17. Should the signal be accepted, rejected, or deferred?

The output must be a deterministic:

```text
RiskDecision

or equivalent domain object.

4. IMPORTANT — STRATEGY VS RISK VS EXECUTION

Maintain strict separation.

The architecture should remain conceptually:

MARKET DATA
     ↓
STRATEGY
     ↓
SIGNAL
     ↓
OPPORTUNITY / SCORE
     ↓
RISK MANAGER
     ↓
PORTFOLIO ORCHESTRATOR
     ↓
ORDER
     ↓
EXECUTION ENGINE
     ↓
POSITION
     ↓
TRADE
     ↓
RISK STATE UPDATE

Do not move execution logic into the strategy.

Do not move strategy logic into the risk manager.

Do not move portfolio logic into the execution engine.

5. NO FUTURE INFORMATION

This is the most important requirement of Prompt 05.

Every decision must use only information available at the simulated timestamp.

The system MUST NOT use:

future trade outcome;
future strategy performance;
future win rate;
future drawdown;
future strategy ranking;
future market regime;
future volatility;
future candles;
future prices;
future portfolio equity;
future number of trades;
future strategy activation state.
6. CRITICAL RULE — STRATEGY STATE

A strategy's state at timestamp T must be derived exclusively from:

information <= T

Examples:

Allowed:

number of previous losses
previous trades
previous realized PnL
current exposure
current active state
historical score observations
current market data

Forbidden:

future losses
future wins
future profitability
future regime
future drawdown
future ranking
7. STRATEGY ACTIVATION / DEACTIVATION

Implement explicit strategy lifecycle states.

At minimum:

ACTIVE
PAUSED
DISABLED

Optionally:

COOLDOWN

if useful.

The state machine must be deterministic.

8. STRATEGY STATE MACHINE

Implement a clear transition model.

Conceptually:

ACTIVE
  ↓
LOSS LIMIT / COOLDOWN
  ↓
PAUSED
  ↓
COOLDOWN EXPIRES
  ↓
ACTIVE

and:

ACTIVE
  ↓
MANUAL / CONFIGURED DISABLE
  ↓
DISABLED

Do not allow hidden state transitions.

Every transition must be recorded.

9. THREE CONSECUTIVE LOSSES RULE

Implement the previously defined research hypothesis:

If a strategy experiences 3 consecutive losing trades, it should be temporarily paused.

This must be configurable.

Example:

strategy_management:
  consecutive_loss_limit: 3
  cooldown_after_loss_limit:
    enabled: true
    duration: ...

Do not hard-code 3.

10. IMPORTANT DEFINITION OF CONSECUTIVE LOSS

A consecutive loss sequence must be based on CLOSED TRADES.

Example:

Trade 1 = LOSS
Trade 2 = LOSS
Trade 3 = LOSS

→ strategy enters cooldown.

An open position must NOT count as a loss.

A rejected signal must NOT count as a loss.

A skipped signal must NOT count as a loss.

11. RESET OF CONSECUTIVE LOSS COUNTER

When a strategy closes a profitable trade:

consecutive_losses = 0

Example:

LOSS
LOSS
WIN

After the WIN:

consecutive_losses = 0

A break-even trade must have explicit configurable semantics.

Default:

break_even does NOT increase consecutive_losses
break_even resets consecutive_losses

if this is consistent with the existing architecture.

Document the choice.

12. LOSS SEQUENCE MUST BE POINT-IN-TIME

At timestamp T:

consecutive_losses

must include only trades closed before or at T.

Never use later trades to determine whether the strategy should have been paused earlier.

13. COOLDOWN

After the configured loss limit is reached:

strategy_state = PAUSED

for a configurable duration.

Example:

strategy_management:
  cooldown_duration:
    value: 4
    unit: hours

Do not hard-code the duration.

14. COOLDOWN TIMING

If the third loss closes at:

2026-01-10 14:32 UTC

and cooldown is 4 hours:

the strategy cannot generate/accept new entries until:

2026-01-10 18:32 UTC

according to the chosen boundary semantics.

Existing positions must continue to be managed by the execution engine unless a separate configured rule explicitly says otherwise.

The cooldown should affect NEW ENTRIES only.

15. COOLDOWN MUST NOT CREATE LOOK-AHEAD

The strategy cannot know:

"I will lose three times in the future."

It only enters cooldown after the third loss actually occurs in simulated time.

16. DAILY CAPITAL MANAGEMENT

Implement portfolio-level daily controls.

At minimum:

daily profit target
daily loss limit

These values must be configurable.

Example:

daily_limits:
  profit_target_pct: 1.0
  loss_limit_pct: 2.0

These are research parameters.

Do not claim that any specific daily return is achievable or sustainable.

17. DAILY BASE EQUITY

Define precisely how the daily percentage is calculated.

Default:

day_start_equity

should be captured at the start of the simulated trading day.

Then:

daily_return_pct =
(current_equity - day_start_equity)
/
day_start_equity
× 100

Document the exact definition.

18. DAILY PROFIT TARGET

If:

daily_return_pct >= daily_profit_target_pct

then:

allow_new_entries = false

by default.

Do NOT automatically close open positions.

Open positions continue according to their existing execution/risk rules.

19. DAILY LOSS LIMIT

If:

daily_return_pct <= -daily_loss_limit_pct

then:

allow_new_entries = false

by default.

Existing positions continue unless an explicit configured emergency-close policy exists.

Do not invent such behavior.

20. DAILY RESET

At the beginning of each new trading day:

day_start_equity = current_equity
daily_return = 0
daily_limit_state = OPEN

The reset must be deterministic.

Document timezone.

Because crypto trades 24/7, define the research day explicitly.

Default:

UTC calendar day

unless the existing project configuration defines another explicit day boundary.

21. DAILY LIMIT STATE

Use explicit states such as:

OPEN
PROFIT_TARGET_REACHED
LOSS_LIMIT_REACHED

Do not repeatedly evaluate the same limit in ways that can create inconsistent state.

22. RISK-PER-TRADE

Implement risk-per-trade as a portfolio-level constraint.

Example:

risk:
  risk_per_trade_pct: 0.5

Conceptually:

risk_budget =
current_equity × risk_per_trade_pct

Position size must then be derived from:

entry price
stop distance
cost assumptions

using the Prompt 03 execution model.

23. RISK MUST BE BASED ON CURRENT EQUITY

Use information available at the current timestamp.

Do not use:

future end-of-day equity
future peak equity
future final balance

to calculate position size.

24. RISK BUDGET MUST INCLUDE EXECUTION REALITY

Where appropriate, position sizing must consider:

stop distance;
fees;
spread;
slippage;
gap assumptions.

The goal is to avoid calculating:

exactly 1R

from an idealized price and then discovering that actual execution creates materially greater risk.

Use the existing Prompt 03 cost model rather than creating a duplicate.

25. MAX CONCURRENT POSITIONS

Enforce:

portfolio_limits:
  max_concurrent_positions: ...

The count must be based on currently OPEN positions.

Closed positions do not count.

Rejected orders do not count.

26. TOTAL PORTFOLIO EXPOSURE

Implement:

portfolio_limits:
  max_total_exposure_pct: ...

Define exposure explicitly.

For example:

gross_notional_exposure / current_equity

The exact definition must be consistent with Prompt 03.

27. ASSET EXPOSURE

Implement:

portfolio_limits:
  max_asset_exposure_pct: ...

Example:

If:

BTCUSDT

already consumes 40% of permitted exposure, another BTC strategy must be rejected if it would exceed the configured limit.

Do not use future information.

28. STRATEGY EXPOSURE

Implement:

portfolio_limits:
  max_strategy_exposure_pct: ...

This prevents one strategy family or instance from consuming all available capital.

Define precisely whether the limit applies to:

strategy ID;
strategy instance;
strategy family.

Prefer supporting explicit configuration for the desired scope.

29. CORRELATION IS NOT REQUIRED YET

Do NOT implement sophisticated portfolio correlation optimization in Prompt 05.

Do not calculate:

covariance matrices;
dynamic correlation clustering;
portfolio optimization;
risk parity;
Kelly optimization.

Those are not required here.

However, the architecture should not make future correlation-aware risk management impossible.

30. CONFLICTING SIGNALS

Multiple strategies may produce signals for:

same symbol
same timestamp
same side
opposite sides

The orchestrator must handle these deterministically.

31. SAME-SIDE SIGNALS

Example:

EMA strategy → LONG BTC
Momentum strategy → LONG BTC
Breakout strategy → LONG BTC

The system must evaluate each signal independently through risk controls.

It must then enforce:

asset exposure
portfolio exposure
concurrent position limits

Do not automatically merge them into one trade unless the architecture explicitly supports aggregation.

32. OPPOSING SIGNALS

Example:

Strategy A → LONG BTC
Strategy B → SHORT BTC

If both are submitted at the same timestamp:

The orchestrator must have explicit deterministic behavior.

For Spot:

SHORT

must be rejected if shorting is not permitted.

For future market types where both sides are permitted:

the system should support explicit configuration such as:

conflicting_signals:
  policy: independent

or another clearly documented policy.

Do not silently let one signal overwrite the other.

33. SIGNAL ACCEPTANCE DECISION

Create a structured decision object.

Conceptually:

RiskDecision(
    accepted=True/False,
    reason=...,
    rejection_codes=[...],
    approved_quantity=...,
    approved_risk=...,
    score=...,
)

Adapt to the project's domain model.

34. REJECTION REASONS

At minimum support:

STRATEGY_PAUSED
STRATEGY_DISABLED
COOLDOWN_ACTIVE
DAILY_PROFIT_TARGET_REACHED
DAILY_LOSS_LIMIT_REACHED
MAX_CONCURRENT_POSITIONS
MAX_TOTAL_EXPOSURE
MAX_ASSET_EXPOSURE
MAX_STRATEGY_EXPOSURE
INSUFFICIENT_CAPITAL
INVALID_STOP
INVALID_RISK
SHORT_NOT_ALLOWED
LOW_SCORE
DUPLICATE_SIGNAL
CONFLICTING_SIGNAL
INVALID_CONFIGURATION

Every rejection must be auditable.

35. NO SILENT REJECTIONS

A rejected signal must appear in an audit/event ledger.

Do not simply return:

None

without explanation.

The researcher must be able to determine why a signal did not become a trade.

36. OPPORTUNITY SCORE

Implement a configurable opportunity scoring framework.

Important:

The score measures characteristics of the CURRENT opportunity.

It must NOT directly represent:

yesterday's profit/loss;
emotional state;
whether the previous trade won;
whether the strategy has recently made money.
37. SCORE OBJECTIVE

The score should answer:

"How strong are the currently observable conditions for this strategy's hypothesis?"

It is not:

"How much money will this trade make?"

It is not:

"What will happen next?"

38. SCORE RANGE

Use:

0–100

where:

0 = conditions do not satisfy the opportunity criteria
100 = all configured scoring components are maximally satisfied

Do not interpret the score as a probability.

A score of 80 does NOT mean:

80% probability of winning

unless a future calibrated probabilistic model explicitly establishes that relationship.

39. SCORE COMPONENTS

Create an extensible scoring framework.

Possible components:

trend alignment
momentum quality
volatility suitability
liquidity / volume quality
signal strength
distance from invalidation
risk/reward feasibility
market structure alignment
multi-timeframe confirmation

Only use features actually available at the current timestamp.

40. SCORE WEIGHTS

Make score weights configurable.

Example:

opportunity_score:
  enabled: true

  components:
    trend_alignment:
      weight: 20

    momentum:
      weight: 20

    volatility:
      weight: 15

    volume:
      weight: 15

    risk_reward:
      weight: 20

    multi_timeframe:
      weight: 10

The exact initial weights are research parameters.

Do not claim they are optimized.

41. SCORE NORMALIZATION

All score components must have a well-defined range.

For example:

0–100

or:

0–1

with a final conversion to 0–100.

Document every component.

Do not mix incompatible scales.

42. SCORE THRESHOLD

Allow configuration:

opportunity_score:
  minimum_score: 40

Signals below the threshold can be rejected:

LOW_SCORE

The threshold must be explicit.

43. IMPORTANT — DO NOT CHANGE SCORE BASED ON PREVIOUS DAY RESULT

Do NOT implement:

if yesterday was negative:
    require score > 80
else:
    require score > 40

as a hidden emotional/risk rule.

This was discussed as a hypothesis, but it should NOT be embedded into the score itself.

Instead:

Separate opportunity quality from portfolio risk state.

If a future research experiment wants different thresholds under different portfolio states, that should be an explicit point-in-time policy and tested separately.

44. SCORE MUST NOT LEAK FUTURE INFORMATION

Do not use:

future return
future MFE
future MAE
future trade outcome
future volatility
future strategy performance

to calculate the score.

45. SCORE EXPLANATION

Every score must be auditable.

Store:

total_score
component_scores
component_weights
raw_features
threshold
decision

Example:

{
  "total_score": 82.5,
  "components": {
    "trend_alignment": 90,
    "momentum": 85,
    "volatility": 75,
    "volume": 80
  }
}

The exact schema should follow the existing architecture.

46. SCORE VERSION

The scoring model must have its own version.

Example:

opportunity_score_version = 1.0.0

Changing score methodology requires a new version.

Record it in the run metadata.

47. SCORE CALIBRATION IS NOT PART OF PROMPT 05

Do not claim:

80 score = 80% probability

Do not calibrate score against future outcomes yet.

Prompt 07 will address proper out-of-sample validation and robustness.

48. STRATEGY SCORE VS OPPORTUNITY SCORE

Keep these concepts separate.

Strategy state

Answers:

Is this strategy currently allowed to operate?

Opportunity score

Answers:

How strong is the current opportunity?

Portfolio risk

Answers:

Can the portfolio accept this trade?

These are three separate dimensions.

49. DECISION FLOW

The orchestrator should conceptually follow:

SIGNAL
  ↓
Is strategy configured?
  ↓
Is strategy ACTIVE?
  ↓
Is cooldown inactive?
  ↓
Is market side allowed?
  ↓
Calculate opportunity score
  ↓
Does score meet threshold?
  ↓
Check daily limits
  ↓
Check concurrent positions
  ↓
Check total exposure
  ↓
Check asset exposure
  ↓
Check strategy exposure
  ↓
Calculate risk budget
  ↓
Calculate approved position size
  ↓
Create RiskDecision
  ↓
ORDER

The exact implementation may vary, but the logic must be explicit.

50. DECISION ORDER MUST BE DETERMINISTIC

The same:

signal
+
portfolio state
+
configuration

must always produce the same:

RiskDecision

No randomness.

51. PORTFOLIO STATE SNAPSHOT

At every decision point, maintain a point-in-time portfolio state.

It should include:

timestamp
equity
cash
open_positions
gross_exposure
net_exposure
daily_return
daily_limit_state
strategy_states
asset_exposures
strategy_exposures

This snapshot is important for later research.

52. STRATEGY STATE LEDGER

Create a ledger tracking strategy state transitions.

At minimum:

timestamp
strategy_id
strategy_instance_id
previous_state
new_state
reason
consecutive_losses
cooldown_until

Example:

2026-02-10 15:31
EMA_CROSS_001__BTCUSDT__5m
ACTIVE → PAUSED
reason = CONSECUTIVE_LOSS_LIMIT
consecutive_losses = 3
cooldown_until = 19:31
53. DECISION LEDGER

Create a complete decision ledger.

Every strategy signal should produce one decision record.

For accepted signals:

ACCEPTED

For rejected signals:

REJECTED

Include:

timestamp
strategy
symbol
timeframe
signal
score
risk_budget
approved_quantity
portfolio_state
decision
rejection_reason
54. RISK AUDITABILITY

A researcher must be able to answer:

"Why did this signal become a trade?"

and:

"Why was this signal rejected?"

without reading source code.

This is mandatory.

55. POSITION SIZING

Reuse the Prompt 03 position sizing implementation.

Do not create a second position sizing engine.

The risk manager should provide:

risk budget
approved constraints

and Prompt 03 execution/accounting should perform the actual execution calculations according to the established architecture.

56. RISK APPROVAL VS EXECUTION

Do not treat:

RiskDecision.accepted = True

as:

trade definitely filled

It means:

The opportunity passed portfolio-level controls and may proceed to execution.

The execution engine determines the actual fill.

57. RISK STATE UPDATE TIMING

Strategy state must update only when the underlying event occurs.

For example:

trade closes
↓
trade result becomes known
↓
consecutive loss counter updates
↓
if threshold reached:
    strategy enters cooldown

Do not update strategy state when the trade is merely opened.

58. OPEN POSITION MANAGEMENT

A strategy entering cooldown does NOT automatically close an existing position.

The default policy is:

cooldown affects NEW ENTRIES only

Existing positions continue under Prompt 03 execution management.

59. DAILY LIMIT INTERACTION WITH OPEN POSITIONS

When the daily profit/loss limit is reached:

Default:

new entries blocked
existing positions continue

This must be configurable if the architecture supports it.

Do not silently force-close positions.

60. STRATEGY COOLDOWN INTERACTION

When a strategy is paused:

new entries blocked
existing positions continue

Do not cancel existing positions unless explicitly configured.

61. DAILY LIMIT AND STRATEGY COOLDOWN PRIORITY

Define deterministic priority.

For example:

portfolio emergency restriction
>
daily limit
>
strategy state
>
score threshold
>
signal acceptance

The exact order may differ, but it must be documented and deterministic.

62. PORTFOLIO RISK SHOULD DOMINATE STRATEGY SIGNALS

A strong strategy signal does not override a hard portfolio risk constraint.

For example:

score = 100

must NOT override:

MAX_TOTAL_EXPOSURE

or:

DAILY_LOSS_LIMIT
63. SCORE SHOULD NOT OVERRIDE HARD LIMITS

The score is a filter.

It is NOT permission to bypass:

capital limits;
exposure limits;
market restrictions;
daily limits;
strategy cooldown.
64. RESEARCH CONFIGURATION

Extend the existing configuration system.

Example:

strategy_management:

  consecutive_loss_limit: 3

  cooldown:
    enabled: true
    duration:
      value: 4
      unit: hours

portfolio_limits:

  max_concurrent_positions: 10

  max_total_exposure_pct: 50

  max_asset_exposure_pct: 20

  max_strategy_exposure_pct: 15

daily_limits:

  profit_target_pct: 1.0

  loss_limit_pct: 2.0

opportunity_score:

  enabled: true

  minimum_score: 40

  version: "1.0.0"

  components:

    trend_alignment:
      weight: 20

    momentum:
      weight: 20

    volatility:
      weight: 15

    volume:
      weight: 15

    risk_reward:
      weight: 20

    multi_timeframe:
      weight: 10

Adapt to the existing configuration architecture.

Do not create another configuration framework.

65. STRATEGY-SPECIFIC SCORE REQUIREMENTS

Different strategies may require different score components.

For example:

trend strategy

may prioritize:

trend alignment
momentum

while:

mean reversion strategy

may prioritize:

distance from mean
volatility

Design the score framework so strategy-specific scoring is possible without duplicating the entire scoring engine.

66. DO NOT OVER-COMPLICATE THE FIRST VERSION

Prompt 05 should establish the framework.

Do not implement:

machine learning score;
neural networks;
reinforcement learning;
Bayesian strategy selection;
Kelly criterion;
dynamic portfolio optimization;
covariance optimization;
advanced factor models.

These may be researched later.

67. TESTING — CONSECUTIVE LOSSES

Create deterministic tests:

LOSS
LOSS
LOSS

Expected:

strategy → PAUSED

Then verify:

new signal during cooldown
→ REJECTED

Then:

cooldown expires
→ ACTIVE
68. TESTING — LOSS RESET

Test:

LOSS
LOSS
WIN

Expected:

consecutive_losses = 0
strategy remains ACTIVE

assuming the configured default semantics.

69. TESTING — DAILY PROFIT TARGET

Create a deterministic fixture where equity reaches:

daily_profit_target_pct

Expected:

new signal → REJECTED
reason = DAILY_PROFIT_TARGET_REACHED

Existing position behavior must match configuration.

70. TESTING — DAILY LOSS LIMIT

Create a deterministic fixture where:

daily_return <= -daily_loss_limit

Expected:

new signal → REJECTED
reason = DAILY_LOSS_LIMIT_REACHED
71. TESTING — EXPOSURE

Test:

max concurrent positions
max total exposure
max asset exposure
max strategy exposure

Each must reject trades independently when the relevant limit is exceeded.

72. TESTING — SCORE

Create deterministic tests for:

score component calculation;
weighting;
normalization;
final score;
threshold;
rejection;
accepted signal.
73. SCORE FUTURE-MUTATION TEST

This is mandatory.

Calculate score at timestamp T.
Modify only future market data.
Recalculate score at T.
Compare.

Expected:

score(T) must remain identical.

If it changes:

FAIL.

74. STRATEGY STATE FUTURE-MUTATION TEST
Run strategy/orchestrator through timestamp T.
Modify only data after T.
Re-run.
Compare strategy state at T.

Expected:

state(T) must remain identical.
75. PORTFOLIO DECISION FUTURE-MUTATION TEST

This is one of the most important tests in Prompt 05.

Run the portfolio decision system.
Record all decisions before timestamp T.
Modify only data after T.
Re-run.
Compare all decisions before T.

Expected:

ALL DECISIONS BEFORE T MUST BE IDENTICAL.
76. NO FUTURE PERFORMANCE SELECTION TEST

Explicitly test that a strategy is NOT activated/deactivated because of future performance.

Example:

If a strategy has:

future profitability = very high

that information must have zero influence on decisions before that future period.

77. TESTING — MULTIPLE STRATEGIES

Create a deterministic scenario:

Strategy A → LONG BTC
Strategy B → LONG BTC
Strategy C → LONG ETH

Verify:

all signals are evaluated;
exposure limits apply;
accepted/rejected decisions are auditable;
no state contamination occurs.
78. TESTING — OPPOSING SIGNALS

Create:

Strategy A → LONG BTC
Strategy B → SHORT BTC

Verify configured behavior.

For Spot:

SHORT → rejected

with:

SHORT_NOT_ALLOWED
79. TESTING — DETERMINISM

Run the same orchestration twice.

Expected:

identical strategy states
identical score values
identical decisions
identical accepted orders
identical rejection reasons
80. TESTING — ORDER OF DECISION

Create a test where multiple constraints fail simultaneously.

Verify that the documented priority produces the same deterministic primary rejection reason.

81. TESTING — REJECTION AUDIT

Every rejected signal must appear in the decision ledger.

No signal should disappear without an explicit reason.

82. TESTING — RISK ACCOUNTING

Verify:

risk budget
approved position size
exposure after acceptance

are internally consistent.

83. INTEGRATION TEST

The complete integration path must be:

REAL BINANCE DATA
        ↓
STRATEGY LIBRARY
        ↓
SIGNALS
        ↓
OPPORTUNITY SCORE
        ↓
RISK MANAGER
        ↓
PORTFOLIO ORCHESTRATOR
        ↓
PROMPT 03 BACKTEST ENGINE
        ↓
ORDERS
        ↓
FILLS
        ↓
TRADES
        ↓
STRATEGY STATE UPDATE
        ↓
PORTFOLIO STATE UPDATE

Use real canonical Binance data.

Do not mock the complete pipeline.

84. NOTEBOOK

Create:

notebooks/05_portfolio_risk_and_orchestration_validation.ipynb

The notebook must execute from beginning to end.

Required sections:

Section 1 — Environment

Display:

Python version;
project version;
Git commit if available;
run ID.
Section 2 — Configuration

Display:

capital;
risk-per-trade;
exposure limits;
daily limits;
consecutive-loss rule;
cooldown;
score configuration.
Section 3 — Strategy Universe

Display:

configured strategies;
strategy instances;
symbols;
timeframes.
Section 4 — Portfolio State

Show:

initial equity;
cash;
exposure;
open positions.
Section 5 — Opportunity Score

Display representative signals with:

component scores;
total score;
threshold;
decision.
Section 6 — Risk Decisions

Show examples of:

accepted signals;
rejected signals;
rejection reasons.
Section 7 — Strategy State

Show:

ACTIVE;
PAUSED;
cooldown;
reactivation.
Section 8 — Consecutive Loss Validation

Show an actual deterministic validation example.

Section 9 — Daily Limits

Show validation of:

profit target;
loss limit.
Section 10 — Multi-Strategy Run

Run multiple strategy instances across multiple assets/timeframes.

Section 11 — Results

Display descriptive aggregate outputs.

Do NOT rank strategies.

Section 12 — Point-in-Time Validation

Run:

future score mutation test;
future state mutation test;
future decision mutation test.
Section 13 — Final Assertions

Any failure must stop the notebook.

85. BASIC REPORTING

Prompt 05 should produce machine-readable outputs.

Extend the existing result structure.

At minimum:

risk_decisions.csv
strategy_state_history.csv
opportunity_scores.csv
portfolio_state.csv
rejections.csv
run_metadata.json
metrics.json

Reuse existing ledgers from Prompt 03/04 where possible.

Do not duplicate information unnecessarily.

86. DECISION LEDGER SCHEMA

At minimum:

timestamp
run_id
strategy_id
strategy_version
strategy_instance_id
symbol
timeframe
signal
score
score_version
risk_budget
approved_quantity
portfolio_equity
daily_return_pct
consecutive_losses
strategy_state
decision
primary_reason
rejection_reasons
87. STRATEGY STATE HISTORY SCHEMA

At minimum:

timestamp
strategy_id
strategy_instance_id
previous_state
new_state
reason
consecutive_losses
last_trade_result
cooldown_start
cooldown_until
88. OPPORTUNITY SCORE SCHEMA

At minimum:

timestamp
strategy_id
strategy_instance_id
symbol
timeframe
score_version
total_score
component_scores
component_weights
raw_features
threshold
decision
89. PORTFOLIO STATE SCHEMA

At minimum:

timestamp
equity
cash
gross_exposure
net_exposure
open_positions
daily_start_equity
daily_return_pct
daily_limit_state
90. SCORE VERSIONING

Store:

strategy_version
score_version
risk_policy_version

in every research run.

A future methodology change must produce a distinguishable version.

91. RESEARCH RUN METADATA

Every Prompt 05 run must record:

run_id
code_version
git_commit
python_version
dependency_versions
dataset_ids
date_range
symbols
timeframes
strategy_versions
score_version
risk_policy_version
configuration_snapshot

Do not fabricate unavailable values.

92. DOCUMENTATION

Create:

docs/research/RISK_AND_ORCHESTRATION_POLICY.md

Document:

strategy states;
cooldown;
consecutive losses;
daily limits;
risk-per-trade;
portfolio exposure;
asset exposure;
strategy exposure;
opportunity score;
decision order;
rejection reasons;
point-in-time requirements;
score limitations;
state transition rules.
93. EXECUTION GUIDE

Create:

docs/execution/PROMPT_05_EXECUTION_GUIDE.md

Include:

Purpose

What Prompt 05 adds.

Prerequisites

Prompts 01–04.

Configuration

Explain every major parameter.

Strategy state

Explain:

ACTIVE;
PAUSED;
DISABLED;
cooldown.
Consecutive losses

Explain exact semantics.

Daily limits

Explain exact semantics.

Opportunity score

Explain:

components;
weights;
threshold;
limitations.
Portfolio limits

Explain:

concurrent positions;
total exposure;
asset exposure;
strategy exposure.
Decision flow

Explain the exact order of evaluation.

Notebook

How to execute.

Tests

Exact commands.

Output files

Where they are stored.

Reproducibility

How to rerun.

Known limitations

Especially:

score is not a probability;
no score calibration;
no optimization;
no correlation optimization;
no future information;
no live trading.
Next step

Prompt 06.

94. README UPDATE

Update:

README.md

with:

Prompt 05 — Portfolio Risk & Strategy Orchestration
STATUS: ...

Do not claim complete until validation succeeds.

95. PROJECT_STATUS.md UPDATE

Update:

PROJECT_STATUS.md

Record:

Prompt 01 status;
Prompt 02 status;
Prompt 03 status;
Prompt 04 status;
Prompt 05 status;
number of strategies;
number of strategy instances;
score version;
risk policy version;
tests;
integration run;
results;
known limitations;
next step.
96. ACCEPTANCE CRITERIA

Prompt 05 is complete ONLY if all applicable criteria pass.

Architecture
 Existing Prompt 03/04 architecture reused.
 No parallel risk engine created.
 No parallel execution engine created.
 Strategy/execution/risk separation preserved.
Strategy State
 ACTIVE state implemented.
 PAUSED state implemented.
 DISABLED state implemented.
 Consecutive loss limit configurable.
 Cooldown configurable.
 State transitions auditable.
 Existing positions continue after cooldown unless explicitly configured otherwise.
Daily Controls
 Daily profit target implemented.
 Daily loss limit implemented.
 Daily reset implemented.
 UTC day definition documented.
 New entries blocked after limit.
 Existing positions behavior documented.
Portfolio Risk
 Risk-per-trade implemented.
 Max concurrent positions implemented.
 Max total exposure implemented.
 Max asset exposure implemented.
 Max strategy exposure implemented.
 Position sizing integrates with Prompt 03.
Opportunity Score
 Score implemented.
 Score range is defined.
 Components documented.
 Weights configurable.
 Threshold configurable.
 Score versioned.
 Score is not presented as probability.
 Score does not use previous-day PnL.
 Score uses only point-in-time information.
Orchestration
 Multiple strategy signals supported.
 Same-asset signals handled deterministically.
 Opposing signals handled deterministically.
 Rejections are auditable.
 Decision order is documented.
Point-in-Time Integrity
 Future score mutation test passes.
 Future strategy state mutation test passes.
 Future decision mutation test passes.
 No future strategy performance used.
 No future portfolio information used.
Reproducibility
 Same inputs produce same decisions.
 Strategy versions recorded.
 Score version recorded.
 Risk policy version recorded.
 Configuration snapshot recorded.
Integration
 Real Binance data used.
 Prompt 04 strategies used.
 Prompt 03 execution engine used.
 Complete signal → risk → execution pipeline validated.
Documentation
 RISK_AND_ORCHESTRATION_POLICY.md created.
 PROMPT_05_EXECUTION_GUIDE.md created.
 README updated.
 PROJECT_STATUS.md updated.
97. IMPORTANT — DO NOT OPTIMIZE

Do NOT:

optimize the score;
optimize the loss limit;
optimize cooldown;
optimize daily target;
optimize daily loss limit;
optimize risk percentage;
optimize exposure limits;
optimize strategy thresholds;
rank strategies;
choose the best configuration;
remove strategies because of poor performance.

Those are research questions for later validation.

Prompt 05 implements the control framework.

98. IMPORTANT — DO NOT USE PREVIOUS DAY PERFORMANCE AS A PSYCHOLOGICAL SWITCH

Do not implement logic such as:

if previous_day_was_loss:
    score_threshold = 80
else:
    score_threshold = 40

unless explicitly modeled later as a formal, point-in-time research policy.

The default system must treat:

opportunity quality

and:

portfolio state

as separate concepts.

This distinction is fundamental.

99. IMPORTANT — 1% DAILY TARGET

The configuration may contain:

daily_profit_target_pct = 1.0

because this is one of the research hypotheses being investigated.

However:

DO NOT:

assume 1% daily is achievable;
optimize the system to hit 1%;
manipulate position size to force 1%;
increase leverage to reach 1%;
claim that 1% daily is sustainable.

The system must simply measure what happens under the configured rule.

100. IMPORTANT — 3 LOSS RULE

The three-loss cooldown is also a research hypothesis.

Do not claim that:

3 consecutive losses

necessarily means the strategy is broken.

It is simply an explicit state-management hypothesis that will later be evaluated empirically.

101. IMPORTANT — STRATEGY SELECTION

Do not implement:

if strategy has high historical profit:
    activate

because that creates severe selection bias if used incorrectly.

Future Prompt 07 will establish proper:

walk-forward;
training;
validation;
out-of-sample;
robustness;

methodology.

102. FINAL ENGINEERING REPORT

At the end of implementation provide:

1. STATUS

One of:

COMPLETE
PARTIAL
BLOCKED

Never claim COMPLETE if acceptance criteria are not satisfied.

2. COMPONENTS IMPLEMENTED

List actual files/modules changed.

3. STRATEGY STATE

Report:

total strategy instances
active
paused
disabled
cooldowns triggered
4. RISK VALIDATION

Report:

risk-per-trade tests
concurrent position tests
total exposure tests
asset exposure tests
strategy exposure tests
daily target tests
daily loss tests
5. SCORE VALIDATION

Report:

score version
components
weights
threshold
point-in-time validation
future mutation test
6. POINT-IN-TIME VALIDATION

Explicitly report:

future score mutation: PASS/FAIL
future strategy state mutation: PASS/FAIL
future decision mutation: PASS/FAIL
determinism: PASS/FAIL
7. INTEGRATION VALIDATION

Report:

real dataset
symbols
timeframes
strategy instances
run_id
8. OUTPUT FILES

List actual generated paths.

9. KNOWN LIMITATIONS

Clearly state:

opportunity score is not a probability;
score has not been calibrated;
risk parameters have not been optimized;
no strategy ranking has been performed;
no walk-forward validation has been performed;
no out-of-sample validation has been performed;
no correlation optimization has been performed;
no live trading exists.
10. NEXT STEP

If AND ONLY IF Prompt 05 acceptance criteria pass:

READY FOR PROMPT 06

Otherwise:

NOT READY FOR PROMPT 06

and clearly identify what must be fixed.

103. FINAL INSTRUCTION

The purpose of Prompt 05 is NOT to make the system profitable.

The purpose is to make the research engine capable of answering:

"Given many simultaneous strategy opportunities, how would a disciplined portfolio-level decision system have allocated risk using only information available at that moment?"

The implementation must therefore prioritize:

Point-in-time integrity.
Deterministic decisions.
Capital protection.
Exposure control.
Auditable strategy state.
Explicit opportunity scoring.
Reproducibility.
Clear rejection reasons.
Separation between signal, risk and execution.
Fail-fast behavior.

Do not optimize prematurely.

Do not rank strategies.

Do not use future information.

Do not fabricate results.

Do not hide failures.

Do not create a second backtest engine.

Do not create a second execution engine.

Do not move to Prompt 06 until Prompt 05 has been actually executed and validated.