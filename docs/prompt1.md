# PROMPT 01 — QUANTITATIVE DAY-TRADING RESEARCH LAB
## Project Foundation, Architecture, Reproducibility and Execution Framework

---

## 1. ROLE

You are acting as a **Principal Quantitative Research Engineer, Senior Python Architect, and Quantitative Backtesting Infrastructure Specialist**.

Your responsibility is to build the foundation of a serious, reproducible quantitative research laboratory for short-term/day-trading research.

This is NOT a production trading bot yet.

This is NOT a frontend application.

This is NOT an optimization exercise.

This is NOT a request to create trading signals at this stage.

The objective of this prompt is to create the **complete and executable foundation** that will support the next seven development stages.

You must behave as if this project will eventually be used for serious quantitative research where:

- reproducibility matters;
- historical information must be respected exactly as it was available at the time;
- look-ahead bias is unacceptable;
- survivorship bias must be considered;
- transaction costs must eventually be included;
- every experiment must be reproducible;
- every failure must be visible;
- no fake results are acceptable;
- no hidden assumptions are acceptable;
- no silent fallback behavior is acceptable.

---

# 2. PROJECT OBJECTIVE

We are building a Python/Jupyter quantitative research laboratory for **short-term cryptocurrency day-trading research**, initially using Binance market data.

The research will eventually evaluate many independent strategies simultaneously across:

### Assets
Initially:

- BTC
- ETH
- SOL
- and other liquid Binance pairs later

The architecture MUST NOT hard-code these assets.

The system must support adding new assets through configuration rather than modifying core code.

### Timeframes

The research must eventually support multiple timeframes, including:

- 1m
- 3m
- 5m
- 15m
- 30m
- 1h
- 2h
- 4h

The architecture must NOT assume that one timeframe is universally superior.

A strategy may perform differently depending on:

- asset;
- timeframe;
- market regime;
- volatility;
- liquidity;
- transaction costs;
- execution assumptions.

---

# 3. CORE RESEARCH PHILOSOPHY

The most important concept of this project is:

> We are NOT trying to discover one magical trading strategy.

We want to investigate whether a **portfolio of different short-term strategies**, combined with disciplined risk management and strategy activation/deactivation logic, can produce a robust risk-adjusted result.

The primary research hypothesis is:

> A diversified set of strategies may have different periods of effectiveness depending on market conditions, and a systematic strategy-management layer may improve robustness compared with permanently running every strategy.

The system must therefore eventually support:

- many strategies;
- many assets;
- many timeframes;
- multiple market regimes;
- configurable risk/reward ratios;
- configurable position sizing;
- configurable exposure limits;
- configurable trade protection;
- strategy scoring;
- strategy activation/deactivation;
- daily stop conditions;
- transaction costs;
- slippage;
- detailed trade journals;
- visual analysis;
- walk-forward validation;
- out-of-sample validation.

However, these features will be implemented in later prompts.

---

# 4. DEVELOPMENT ROADMAP

This project will be developed in exactly **8 major prompts**.

Do NOT redesign this roadmap during Prompt 01.

Do NOT implement future stages prematurely unless required to create a clean architectural interface.

### Prompt 01
Project foundation, architecture, configuration, reproducibility, testing, logging, notebook execution framework and documentation.

### Prompt 02
Real Binance data ingestion, normalization, storage and data-quality infrastructure.

### Prompt 03
Core backtesting engine with candle-by-candle execution, order simulation, costs, slippage, stops, targets and trade lifecycle.

### Prompt 04
Strategy library containing approximately 15–30 strategies, from simple to complex, using a common strategy interface.

### Prompt 05
Risk management, capital management, position sizing, exposure management, strategy scoring and strategy activation/deactivation.

### Prompt 06
Trade journal, visualizations, daily/weekly/monthly reports and research dashboard.

### Prompt 07
Quantitative research, walk-forward validation, robustness testing, sensitivity analysis, regime analysis and out-of-sample evaluation.

### Prompt 08
Paper-trading/realtime research mode using the same strategy and execution architecture as the backtester, replacing historical data with realtime data.

---

# 5. CRITICAL RULE — DO NOT BREAK THE ROADMAP

The system must be designed so that Prompts 02–08 can extend it cleanly.

Do NOT create temporary architecture that will need to be thrown away later.

Do NOT build a second architecture for future stages.

Do NOT create shortcuts that will force a rewrite of the backtesting engine later.

At the same time:

**DO NOT implement Prompt 02–08 functionality now.**

Create interfaces and extension points where appropriate, but keep the implementation scope of Prompt 01 under control.

---

# 6. ABSOLUTE RULE — NO FALLBACKS

This is one of the most important requirements of the entire project.

## NEVER implement silent fallbacks.

The system MUST NOT:

- silently replace missing data;
- generate fake market data;
- generate synthetic candles;
- generate mock trades;
- generate placeholder results;
- fabricate metrics;
- silently skip failed operations;
- silently use another data source;
- silently change configuration;
- silently change parameters;
- silently downgrade functionality;
- silently catch exceptions and continue;
- create fake Binance responses;
- pretend that an external dependency worked when it did not.

If a required operation fails:

> FAIL FAST.

The error must be exposed clearly.

Execution must stop.

The error must contain enough information to diagnose the problem.

For example:

```text
ERROR: Required configuration file not found.
Path: config/config.yaml
Execution stopped.
No fallback configuration was generated.

Do NOT do this:

try:
    load_config()
except:
    use_default_config()

That behavior is forbidden.

7. NO MOCK DATA

The project must NOT use fake or synthetic market data to demonstrate that the pipeline works.

Do not generate:

fake OHLCV;
fake trades;
fake Binance responses;
fake strategy signals;
fake performance;
fake backtest results.

If Prompt 01 requires testing architecture without real market data, test the architecture itself using deterministic unit-test fixtures where appropriate.

However:

Never present test fixtures as market research results.

Clearly separate:

unit test fixtures

from:

real research data

The distinction must be obvious in both code and documentation.

8. FAIL-FAST ENGINEERING PHILOSOPHY

Any unexpected error must stop execution.

Do not hide exceptions.

Do not use broad exception handling such as:

except Exception:
    pass

or:

except:
    continue

Do not create "best effort" pipelines.

Do not continue execution after data integrity failures.

Do not produce a successful-looking report if any mandatory stage failed.

A failed experiment must be clearly marked as failed.

9. LOOK-AHEAD BIAS — FOUNDATIONAL REQUIREMENT

Although the actual backtesting engine will be implemented in Prompt 03, the architecture created in Prompt 01 must explicitly enforce the principle that:

No component may use information that would not have been available at the exact simulated point in time.

The future research system must operate conceptually like this:

Historical data
      ↓
Current timestamp
      ↓
Information available up to that timestamp
      ↓
Strategy decision
      ↓
Order
      ↓
Execution simulation
      ↓
Position management
      ↓
Result
      ↓
Next timestamp

Never:

Future candle
Future high
Future low
Future close
Future indicator
Future strategy performance
Future regime
Future winning strategy

to influence an earlier decision.

Create the architecture so this principle is difficult to violate accidentally.

10. POINT-IN-TIME DESIGN

The future system must support point-in-time research.

Design interfaces around timestamps.

Every important research object should eventually be traceable to:

timestamp;
asset;
timeframe;
strategy;
configuration;
data source;
execution assumptions;
research run ID.

The architecture should make it possible to answer:

"What information did the system know at this exact moment?"

11. REPRODUCIBILITY

Every research execution must be reproducible.

Create a concept of:

research_run_id

Every execution should eventually have a unique identifier.

A research run must eventually record:

run ID;
execution timestamp;
project version;
Git commit hash when available;
Python version;
dependency versions;
configuration;
assets;
timeframes;
date range;
data source;
strategy version;
risk configuration;
execution assumptions.

Prompt 01 must establish the infrastructure for this metadata.

12. CONFIGURATION

Do NOT hard-code research parameters throughout Python modules.

Create a centralized configuration system.

Use a human-readable configuration format such as YAML.

Example conceptual structure:

project:
  name: crypto_market_research_lab
  version: "1.0"

research:
  market: crypto
  data_source: binance

assets:
  - BTCUSDT
  - ETHUSDT

timeframes:
  - 1m
  - 5m
  - 15m
  - 1h

risk:
  risk_reward_ratio: 3.0
  risk_per_trade_pct: 1.0

execution:
  fee_rate: null
  slippage_model: null

These are examples only.

Do not pretend that values are already validated market assumptions.

Clearly distinguish:

configuration structure;
actual configured values;
future parameters.

Configuration must be validated at startup.

Invalid configuration must stop execution.

13. DIRECTORY ARCHITECTURE

Create a clean research-oriented directory structure.

Use a structure similar to:

crypto-market-research-lab/
│
├── README.md
├── PROJECT_STATUS.md
├── pyproject.toml
├── .gitignore
│
├── config/
│   ├── config.yaml
│   └── README.md
│
├── src/
│   └── crypto_research/
│       ├── __init__.py
│       ├── config/
│       ├── core/
│       ├── data/
│       ├── strategies/
│       ├── execution/
│       ├── risk/
│       ├── research/
│       ├── reporting/
│       └── utils/
│
├── notebooks/
│   └── 01_project_validation.ipynb
│
├── tests/
│   ├── unit/
│   └── integration/
│
├── data/
│   ├── raw/
│   ├── processed/
│   └── metadata/
│
├── results/
│   └── .gitkeep
│
├── reports/
│   └── .gitkeep
│
├── logs/
│   └── .gitkeep
│
├── docs/
│   ├── architecture/
│   ├── research/
│   └── execution/
│
└── scripts/

You may improve this structure if you have a strong architectural reason.

If you change it, explain why.

Do not create unnecessary folders.

14. SEPARATION OF RESPONSIBILITIES

Create clear boundaries between:

Configuration

Responsible for loading and validating configuration.

Data

Responsible for future market-data ingestion and normalization.

Strategies

Responsible for future strategy logic.

Execution

Responsible for future order/position simulation.

Risk

Responsible for future risk-management logic.

Research

Responsible for future experiment orchestration.

Reporting

Responsible for future reports and visualizations.

Core

Responsible for shared domain objects and contracts.

The architecture must prevent strategy logic from becoming mixed with:

data downloading;
portfolio management;
visualization;
file-system operations;
logging implementation.
15. DOMAIN OBJECTS

Create clean foundational domain models/interfaces where appropriate.

Examples:

MarketData
Candle
Signal
Order
Fill
Position
Trade
StrategyMetadata
ResearchRun
RiskDecision

However, do NOT overbuild them.

Only implement what is necessary for the foundation.

Use strongly typed Python models where appropriate.

Prefer explicit structures over dictionaries everywhere.

Use:

dataclasses;
enums;
typing;
protocols/interfaces;

when they improve correctness and maintainability.

16. STRATEGY INTERFACE

Create a future-proof strategy interface.

A strategy should conceptually receive historical information available up to the current timestamp and produce a decision.

Example conceptual interface:

class Strategy(Protocol):
    name: str

    def generate_signal(...):
        ...

Do NOT implement the 15–30 strategies yet.

Do NOT create fake strategy performance.

The objective is only to establish the contract that Prompt 04 will use.

17. DATA PROVIDER INTERFACE

Create an abstraction for market-data providers.

Conceptually:

DataProvider
      │
      ├── BinanceDataProvider
      │
      └── Future providers

Prompt 01 does not need to implement full Binance ingestion.

However, the architecture must allow Prompt 02 to add Binance without restructuring the entire application.

18. EXECUTION INTERFACE

Create an abstraction for simulated execution.

Conceptually:

ExecutionEngine
      ↓
Order
      ↓
Fill
      ↓
Position
      ↓
Trade

Prompt 03 will implement the real backtesting execution engine.

Prompt 01 should only establish the appropriate boundaries.

19. RISK INTERFACE

Create the future interface for risk management.

The system must eventually support configurable:

risk per trade;
maximum simultaneous positions;
maximum total exposure;
daily loss limit;
daily profit target;
risk/reward ratio;
stop-loss;
take-profit;
break-even;
trailing stop;
time-based exit;
strategy-level exposure;
asset-level exposure.

Do NOT implement all of this now.

Create clean extension points.

20. RESEARCH RUN MANAGEMENT

Create a basic research-run management component.

It must be able to generate a unique run identifier and record metadata.

For example:

RUN_20260914_235501_abc123

The exact format is your decision.

The important requirement is uniqueness and reproducibility.

A run directory should eventually look conceptually like:

results/
└── RUN_20260914_235501_abc123/
    ├── config_snapshot.yaml
    ├── metadata.json
    ├── logs/
    ├── trades/
    ├── charts/
    ├── reports/
    └── summary/

Prompt 01 only needs to establish the infrastructure and demonstrate that a run can be created.

21. LOGGING

Implement proper structured logging.

Logs should clearly indicate:

INFO;
WARNING;
ERROR;
execution start;
execution end;
configuration loading;
validation;
run ID;
failures.

Do not spam logs.

Do not hide errors.

Logs should be written to the run directory where appropriate.

22. TESTING

Create automated tests.

At minimum:

Unit tests

Test:

configuration loading;
configuration validation;
invalid configuration behavior;
run ID generation;
metadata generation;
directory creation;
logging initialization;
domain-object validation;
fail-fast behavior.
Integration test

Create at least one integration test proving that:

project startup
        ↓
configuration loading
        ↓
validation
        ↓
research run creation
        ↓
metadata generation
        ↓
successful completion

works end-to-end.

Do not use fake trading results.

23. JUPYTER NOTEBOOK

Create:

notebooks/01_project_validation.ipynb

This notebook must be genuinely executable.

It must:

Load the project configuration.
Validate the environment.
Display the project version.
Display Python version.
Display configuration summary.
Create a research run.
Generate run metadata.
Validate the expected directory structure.
Execute automated validation checks.
Display a clear SUCCESS result if everything passes.

If something fails:

the notebook must fail visibly.

Do not catch the error merely to display:

FAILED

and continue pretending execution succeeded.

24. NOTEBOOK QUALITY

The notebook must be useful for a researcher, not just a technical test.

Include Markdown explanations for:

what is being validated;
why it matters;
what files are generated;
what success means;
what failure means.

Keep the notebook clean.

Do not put the entire application implementation inside the notebook.

The notebook should call the Python package.

25. ENVIRONMENT MANAGEMENT

Create a professional Python project configuration.

Use:

pyproject.toml

Choose an appropriate modern dependency-management approach.

The project must clearly define:

Python version;
runtime dependencies;
development dependencies;
test dependencies.

Avoid unnecessary dependencies.

Do not add large frameworks without justification.

The project should be easy to reproduce on another machine.

26. CODE QUALITY

Follow modern Python engineering practices.

Use:

Python type hints;
clear module boundaries;
small functions;
meaningful names;
docstrings where useful;
deterministic behavior;
explicit errors;
no hidden global state.

Avoid:

giant files;
giant functions;
notebook-only logic;
duplicated configuration;
magic constants;
hidden side effects.
27. GIT

The project is expected to be version-controlled.

Create mechanisms to capture:

git commit hash

when available.

If the Git repository is not available or the command fails:

DO NOT fabricate a commit hash.

Record:

git_commit: unavailable

or an equivalent explicit status.

Do not treat missing Git metadata as a successful commit.

28. DATA INTEGRITY PRINCIPLES

Document the following principles explicitly:

No Look-Ahead Bias

Future information cannot influence past decisions.

No Survivorship Bias

The research must eventually consider the asset universe carefully.

No Data Snooping

Do not select strategies based on future performance.

No Hidden Parameter Optimization

Every parameter used in a research experiment must be explicitly recorded.

Reproducibility

Every result must be traceable to code version + configuration + data.

Point-in-Time

Information must only become available to the simulation when it would actually have been available.

29. RESULTS PHILOSOPHY

The project must distinguish clearly between:

research result

and:

software validation result

Prompt 01 does NOT produce trading profitability results.

Do not claim:

profitable strategy;
expected return;
win rate;
Sharpe ratio;
drawdown;
alpha;
trading edge.

Those belong to future research stages.

Prompt 01 validates infrastructure.

30. DOCUMENTATION REQUIREMENTS

Create:

README.md
PROJECT_STATUS.md
docs/architecture/README.md
docs/research/RESEARCH_PRINCIPLES.md
docs/execution/PROMPT_01_EXECUTION_GUIDE.md
31. PROMPT_01_EXECUTION_GUIDE.md

This file is mandatory.

It must contain:

Objective

What Prompt 01 implemented.

Prerequisites

Everything required before execution.

Installation

Exact commands.

Execution

Exact commands to run:

tests;
notebook;
validation.
Expected output

What the user should see.

Generated files

Explain exactly where they are.

How to analyze the result

Explain what the user should inspect.

Re-run instructions

Explain how the user can execute Prompt 01 again manually.

Success checklist

Example:

[ ] Environment installed
[ ] Tests pass
[ ] Configuration loads
[ ] Configuration validation passes
[ ] Research run created
[ ] Metadata generated
[ ] Notebook executes
[ ] No errors
[ ] Results directory created
Failure troubleshooting

Explain common failures without hiding them.

Acceptance criteria

Clearly define what must be true before Prompt 01 can be considered complete.

32. PROJECT_STATUS.md

Create a living status file.

It should clearly state:

Prompt 01 — COMPLETE / IN PROGRESS / FAILED
Prompt 02 — NOT STARTED
Prompt 03 — NOT STARTED
Prompt 04 — NOT STARTED
Prompt 05 — NOT STARTED
Prompt 06 — NOT STARTED
Prompt 07 — NOT STARTED
Prompt 08 — NOT STARTED

Also include:

implemented components;
pending components;
known limitations;
environment information;
last validation date;
latest research run ID.

Do not mark Prompt 01 as COMPLETE until its acceptance criteria have actually been executed.

33. ARCHITECTURE DOCUMENT

Create a concise architecture document containing:

System Overview

                    Research Orchestrator
                            │
          ┌─────────────────┼─────────────────┐
          │                 │                 │
       Data Layer      Strategy Layer     Risk Layer
          │                 │                 │
          └─────────────────┼─────────────────┘
                            │
                    Execution Engine
                            │
                    Research Results
                            │
                     Reporting Layer

This is conceptual only.

Adapt it to the actual implementation.

Explain:

responsibilities;
dependencies;
boundaries;
future extension points.
34. IMPORTANT DESIGN PRINCIPLE — BACKTEST AND LIVE MODE

The eventual system must allow:

Historical Data
       ↓
Research/Backtest

and later:

Realtime Data
       ↓
Paper Trading

to use the same:

strategy interfaces;
risk interfaces;
execution concepts;
position models;
trade models.

Only the data source and execution environment should differ.

Design Prompt 01 with this future requirement in mind.

35. IMPORTANT DESIGN PRINCIPLE — STRATEGY SELECTION

Eventually, there may be 15–30 strategies.

At any historical timestamp, the system must NOT be allowed to choose strategies simply because they performed well later.

For example, this is forbidden:

Look at 2024 results
        ↓
Select best 15 strategies
        ↓
Pretend those 15 were selected in 2023

This is look-ahead bias.

The architecture must support future strategy-selection logic where decisions are made only using information available at the simulated timestamp.

This is a foundational research constraint.

36. CAPITAL MANAGEMENT — FUTURE REQUIREMENT

The eventual system must support configurable capital allocation.

Examples:

Starting capital
Risk per trade
Position size
Maximum concurrent positions
Maximum asset exposure
Maximum strategy exposure
Daily profit target
Daily loss limit

The eventual objective may investigate a target such as:

1% daily return

but:

DO NOT assume that 1% per day is achievable.

It is a research hypothesis/target to evaluate, not a guaranteed requirement.

Do not optimize the system specifically to manufacture 1% daily returns.

37. RISK/REWARD — FUTURE REQUIREMENT

The initial research hypothesis will use:

Risk : Reward = 1 : 3

or equivalently:

3R reward for 1R risk

But this must remain configurable.

The architecture must eventually allow testing:

1:1
1:1.5
1:2
1:2.5
1:3
1:4
1:5

without rewriting strategy logic.

Do NOT implement the full backtesting behavior in Prompt 01.

38. TRADE PROTECTION — FUTURE REQUIREMENT

The eventual execution engine must support multiple configurable protection mechanisms.

Examples:

initial stop;
take-profit;
break-even;
trailing stop;
partial protection;
time-based exit;
maximum adverse excursion protection.

These mechanisms must eventually be separable from strategy-entry logic.

The architecture should therefore avoid coupling:

ENTRY STRATEGY

with:

POSITION MANAGEMENT
39. DAILY STOP — FUTURE REQUIREMENT

The future system may stop opening new positions after:

daily profit target reached

and/or:

daily maximum loss reached

These must be configurable.

The backtest must eventually simulate this behavior exactly.

Do not implement it now.

40. MULTI-ASSET CONCURRENCY — FUTURE REQUIREMENT

The system must eventually be capable of evaluating multiple assets simultaneously.

Example:

BTCUSDT 1m Strategy A
ETHUSDT 5m Strategy C
SOLUSDT 15m Strategy F
BTCUSDT 15m Strategy H

These opportunities must eventually compete for available capital.

The architecture must therefore avoid assumptions such as:

one asset = one strategy = one position
41. VISUAL RESEARCH — FUTURE REQUIREMENT

Future reports should eventually produce visual trade diaries.

A trade visualization should eventually be able to show:

asset;
timeframe;
strategy;
entry;
stop;
target;
position lifecycle;
relevant indicators;
result;
timestamp;
short explanation.

Prompt 01 does not need to generate trading charts.

But the project structure must provide a clean location for them.

42. EXPERIMENT VERSIONING

Every meaningful research experiment must eventually be identifiable.

Use a concept such as:

experiment_id
run_id
strategy_version
configuration_version

This allows us to compare:

Experiment A
vs
Experiment B

without ambiguity.

43. NO PREMATURE OPTIMIZATION

Do not optimize performance prematurely.

First prioritize:

correctness;
reproducibility;
transparency;
testability;
maintainability;
performance.

Only optimize bottlenecks after they are measured.

44. NO FRONTEND

Do NOT build:

React;
Next.js;
Streamlit application;
web application;
production dashboard;
authentication;
cloud infrastructure.

The current project is:

Python + Jupyter + files + reports

A frontend may be considered later after the research engine has demonstrated value.

45. NO LIVE TRADING

Do NOT:

place real Binance orders;
request trading permissions;
require API keys;
connect to a trading account;
simulate that a real order was placed.

Prompt 01 is research infrastructure only.

Prompt 02 will handle market-data acquisition.

46. ACCEPTANCE TESTS

Prompt 01 is complete ONLY if all of the following are true:

Project
 Project structure exists.
 Python environment is documented.
 Dependencies are declared.
 Configuration system works.
 Configuration validation works.
Architecture
 Core domain boundaries exist.
 Data-provider interface exists.
 Strategy interface exists.
 Execution interface exists.
 Risk interface exists.
 Research-run infrastructure exists.
Reproducibility
 Run ID is generated.
 Configuration snapshot is generated.
 Environment metadata is captured.
 Git metadata is captured when available.
 Missing Git metadata is never fabricated.
Fail Fast
 Invalid configuration stops execution.
 Missing required resources stop execution.
 Unexpected errors are visible.
 No silent fallback exists.
 No fake market data exists.
 No fake trading results exist.
Testing
 Unit tests execute.
 Integration test executes.
 All tests pass.
Notebook
 01_project_validation.ipynb executes successfully.
 Notebook calls project modules instead of duplicating application logic.
 Notebook creates a research run.
 Notebook validates the environment.
 Notebook produces a clear success state.
Documentation
 README.md exists.
 PROJECT_STATUS.md exists.
 Architecture documentation exists.
 Research principles documentation exists.
 PROMPT_01_EXECUTION_GUIDE.md exists.
47. REQUIRED FINAL VALIDATION

Do not tell me that the implementation works simply because the files were created.

Actually execute the validation.

At minimum:

1. Install dependencies.
2. Run unit tests.
3. Run integration tests.
4. Execute the Jupyter notebook.
5. Verify generated artifacts.
6. Verify the research run metadata.
7. Verify fail-fast behavior.
8. Verify there are no mock market-data results.
9. Verify documentation exists.

If anything fails:

STOP.

Do not patch around the failure with a fallback.

Diagnose the actual problem.

Fix the actual problem.

Run the validation again.

48. FINAL DELIVERABLES

At the end of Prompt 01, the repository must contain:

Working Python project
+
Working configuration system
+
Working architecture foundation
+
Working tests
+
Working Jupyter validation notebook
+
Working research-run metadata system
+
Working logging
+
Complete documentation
+
PROJECT_STATUS.md
+
PROMPT_01_EXECUTION_GUIDE.md

The deliverable must be executable.

49. FINAL RESPONSE FORMAT

After implementation and validation, provide a concise final report containing:

1. Implementation Summary

What was actually implemented.

2. Files Created/Modified

List the important files.

3. Validation Performed

Show exactly what was executed.

Example:

pytest ........ PASSED
integration test ........ PASSED
Jupyter validation ........ PASSED

Do not claim PASSED if it was not actually executed.

4. Research Run

Show the generated run ID.

5. Results Location

Show exactly where the generated artifacts are stored.

6. Known Limitations

Be explicit.

7. Prompt 01 Acceptance Checklist

Mark each item:

PASS
FAIL
NOT APPLICABLE

Do not hide failures.

8. Next Step

State clearly that the project is ready for:

PROMPT 02 — REAL BINANCE DATA INGESTION AND DATA QUALITY

ONLY if all Prompt 01 acceptance criteria pass.

50. FINAL NON-NEGOTIABLE RULES

These rules apply to the entire project and must be preserved in future prompts:

NO look-ahead bias.
NO future information leakage.
NO survivorship bias where avoidable.
NO data snooping.
NO fake market data.
NO fake trading results.
NO silent fallbacks.
NO hidden exceptions.
NO silent parameter changes.
NO real-money trading.
NO premature frontend.
NO unnecessary architecture complexity.
Every research run must be reproducible.
Every configuration must be recorded.
Every meaningful failure must stop execution.
Every result must be traceable to code + configuration + data.
Backtest logic must eventually operate candle-by-candle/point-in-time.
Strategy selection must eventually use only information available at the simulated timestamp.
Transaction costs and slippage must eventually be included.
Risk management must be configurable.
Risk/reward must be configurable.
Multiple assets must be supported.
Multiple timeframes must be supported.
Multiple strategies must be supported.
Backtest and future paper-trading modes must share the same core logic.
Every prompt must produce executable artifacts.
Every prompt must produce a Markdown execution guide.
Every prompt must produce measurable validation evidence.
Do not mark an incomplete implementation as complete.
Do not redesign the project roadmap during Prompt 01.
START NOW

First inspect the existing repository and environment.

Do not assume that the repository is empty.

Do not delete existing work without understanding it.

Determine:

current repository structure;
existing Python version;
existing dependencies;
existing notebooks;
existing configuration;
existing tests;
existing Git status.

Then implement Prompt 01.

Do not ask unnecessary clarification questions.

Make reasonable engineering decisions when the requirements are already clear.

If a decision materially affects the architecture, document the decision and proceed.

Most importantly:

BUILD IT, RUN IT, TEST IT, VALIDATE IT, AND DOCUMENT IT.

Do not stop after generating code.