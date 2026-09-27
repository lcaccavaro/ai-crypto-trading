# Crypto Market Research Laboratory

> **A serious, reproducible quantitative research platform for short-term cryptocurrency day-trading research.**

---

## Overview

This project is a Python/Jupyter quantitative research laboratory built on first principles of reproducibility, transparency, and rigorous bias prevention. It is designed to eventually support a portfolio of trading strategies across multiple assets and timeframes.

**This is NOT a trading bot.** This is a research platform.

---

## Project Status

See [PROJECT_STATUS.md](PROJECT_STATUS.md) for current development status.

## Development Roadmap

| Prompt | Description | Status |
|--------|-------------|--------|
| **01** | Foundation: architecture, config, reproducibility, logging, testing | ✅ COMPLETE |
| 02 | Real Binance data ingestion, normalization, storage, data quality | ⏳ NOT STARTED |
| 03 | Backtesting engine: candle-by-candle execution, orders, costs, slippage | ⏳ NOT STARTED |
| 04 | Strategy library: 15–30 strategies with common interface | ⏳ NOT STARTED |
| 05 | Risk management, capital management, strategy scoring | ⏳ NOT STARTED |
| 06 | Trade journal, visualizations, research dashboard | ⏳ NOT STARTED |
| 07 | Walk-forward validation, robustness testing, regime analysis | ⏳ NOT STARTED |
| 08 | Paper trading using real-time data with same architecture | ⏳ NOT STARTED |

---

## Prerequisites

- Python 3.11+
- Git

## Quick Start

```bash
# 1. Clone / navigate to the project
cd ai-crypto-trading

# 2. Install dependencies
python3 -m pip install -e ".[dev]"

# 3. Run tests
python3 -m pytest tests/ -v

# 4. Execute validation notebook
python3 -m jupyter nbconvert --to notebook --execute \
  notebooks/01_project_validation.ipynb \
  --output notebooks/01_project_validation_executed.ipynb
```

For detailed instructions, see [docs/execution/PROMPT_01_EXECUTION_GUIDE.md](docs/execution/PROMPT_01_EXECUTION_GUIDE.md).

---

## Project Structure

```
ai-crypto-trading/
│
├── README.md
├── PROJECT_STATUS.md
├── pyproject.toml
├── .gitignore
│
├── config/
│   ├── config.yaml              ← Central configuration file
│   └── README.md
│
├── src/
│   └── crypto_research/
│       ├── config/              ← Configuration loading & validation
│       ├── core/                ← Domain objects & exceptions
│       ├── data/                ← Data provider interface
│       ├── strategies/          ← Strategy interface
│       ├── execution/           ← Execution engine interface
│       ├── risk/                ← Risk manager interface
│       ├── research/            ← Run management & orchestration
│       ├── reporting/           ← Reports & visualizations (future)
│       └── utils/               ← Logging, environment, git utilities
│
├── notebooks/
│   └── 01_project_validation.ipynb
│
├── tests/
│   ├── unit/
│   └── integration/
│
├── data/
│   ├── raw/                     ← Raw market data (never committed)
│   ├── processed/               ← Processed data (never committed)
│   └── metadata/
│
├── results/                     ← Research run outputs (never committed)
├── reports/                     ← Generated reports
├── logs/                        ← Application logs
│
└── docs/
    ├── architecture/
    ├── research/
    └── execution/
```

---

## Core Design Principles

This project is built around six non-negotiable principles:

1. **No Look-Ahead Bias** — Strategies may only use information available at the simulated timestamp.
2. **No Silent Fallbacks** — Every error stops execution with a clear message.
3. **No Fake Data** — No synthetic market data, no placeholder trading results.
4. **Full Reproducibility** — Every run is uniquely identified and its full environment is recorded.
5. **Fail Fast** — Errors propagate immediately and visibly.
6. **Separation of Concerns** — Configuration, data, strategy, execution, risk, and reporting are distinct layers.

See [docs/research/RESEARCH_PRINCIPLES.md](docs/research/RESEARCH_PRINCIPLES.md) for full details.

---

## Configuration

All research parameters live in `config/config.yaml`. No parameters should be hard-coded in Python modules. See [config/README.md](config/README.md) for documentation.

---

## License

MIT

## Reporting & Observability (Prompt 06)
The reporting layer operates entirely downstream of the core backtest execution. It takes the output (Trades, Signals, Risk Decisions, and Portfolio State) and generates:
- `Trade Diary`
- `Trade Charts`
- Daily, Weekly, and Monthly `Research Reports`

These reports provide full auditability of the decision-making process, including `Decision Quality` assessment (was the trade valid?) and rejection analysis.
