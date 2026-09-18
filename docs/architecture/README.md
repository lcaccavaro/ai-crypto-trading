# Architecture — Crypto Market Research Laboratory

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Research Orchestrator                     │
│                   (future: Prompt 07)                        │
└───────────────────────────┬─────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│  Data Layer  │   │Strategy Layer│   │  Risk Layer  │
│  (Prompt 02) │   │  (Prompt 04) │   │  (Prompt 05) │
└──────┬───────┘   └──────┬───────┘   └──────┬───────┘
       │                  │                  │
       └──────────────────┼──────────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │   Execution Engine    │
              │     (Prompt 03)       │
              └───────────┬───────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │    Research Results   │
              │  (ResearchRun + logs) │
              └───────────┬───────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │    Reporting Layer    │
              │     (Prompt 06)       │
              └───────────────────────┘
```

---

## Component Responsibilities

### Configuration (`src/crypto_research/config/`)

**Responsibility:** Load and validate all research parameters from `config/config.yaml`.

- `schema.py` — Pydantic v2 models defining the exact shape of the config. `extra='forbid'` prevents unknown keys from being silently ignored.
- `loader.py` — Reads YAML, validates against schema, raises `ConfigurationError` on any problem. No silent fallbacks.

**Extension point:** Add new config sections by extending `ProjectConfiguration` in `schema.py`. The YAML file is the source of truth.

---

### Core (`src/crypto_research/core/`)

**Responsibility:** Define the shared domain language used by every other layer.

- `domain.py` — Immutable dataclasses and enums: `Candle`, `Signal`, `Order`, `Fill`, `Position`, `Trade`, `ResearchRun`, `RiskDecision`, `StrategyMetadata`.
- `exceptions.py` — Custom exception hierarchy ensuring errors are always identifiable.

**Principle:** Core objects flow through the system in one direction. They carry timestamps and identifiers for point-in-time traceability.

---

### Data Layer (`src/crypto_research/data/`)

**Responsibility:** Provide market data to the strategy and backtesting layers.

- `interface.py` — `DataProvider` Protocol. All implementations must satisfy this contract.

**Implementations (Prompt 02):**
- `BinanceDataProvider` — fetches from Binance API
- `FileDataProvider` — reads from local Parquet cache

**Point-in-time contract:** `get_candles(asset, timeframe, start, end)` must NEVER return candles beyond `end`. Violation = look-ahead bias.

---

### Strategy Layer (`src/crypto_research/strategies/`)

**Responsibility:** Generate trading signals from historical data.

- `interface.py` — `Strategy` Protocol. All strategies must implement `generate_signal(candles, timestamp)`.

**Implementations (Prompt 04):** 15–30 strategies from simple to complex.

**Key constraint:** `generate_signal()` receives only candles up to the current simulation timestamp. It must be a pure function — same inputs always produce same output.

---

### Execution Layer (`src/crypto_research/execution/`)

**Responsibility:** Simulate order lifecycle (Order → Fill → Position → Trade).

- `interface.py` — `ExecutionEngine` Protocol.

**Implementations:**
- `BacktestExecutionEngine` (Prompt 03) — candle-by-candle simulation
- `PaperTradingExecutionEngine` (Prompt 08) — real-time paper trading

**Design principle:** Both implementations use the same interface and the same domain objects (`Order`, `Fill`, `Position`, `Trade`). Strategy code is fully reusable in both modes.

---

### Risk Layer (`src/crypto_research/risk/`)

**Responsibility:** Approve or reject trade signals based on portfolio state and risk parameters.

- `interface.py` — `RiskManager` Protocol.

**Implementation (Prompt 05):** Full risk manager with:
- Risk per trade
- Maximum concurrent positions
- Maximum total exposure
- Daily loss limit / daily profit target
- Risk/reward enforcement

---

### Research Management (`src/crypto_research/research/`)

**Responsibility:** Manage the lifecycle of research experiments.

- `run_manager.py` — `RunManager`:
  - Generates unique run IDs (`RUN_YYYYMMDD_HHMMSS_<hex6>`)
  - Creates run directories with standard structure
  - Captures full environment metadata (Python, packages, OS, git)
  - Saves `config_snapshot.yaml` and `metadata.json`

**Future (Prompt 07):** Research orchestrator, walk-forward framework, experiment comparison.

---

### Reporting Layer (`src/crypto_research/reporting/`)

**Responsibility:** Generate trade journals, charts, and research reports.

**Implementation (Prompt 06):** Trade diary, visual P&L analysis, drawdown charts, daily/weekly summaries.

---

### Utilities (`src/crypto_research/utils/`)

**Responsibility:** Shared infrastructure: logging, environment capture.

- `logging.py` — Structured logging with structlog + rich. Every event carries `run_id`.
- `environment.py` — Python version, package versions, git commit, platform info.

---

## Data Flow (Future State)

```
Historical OHLCV data
       ↓ (DataProvider)
CandleStore (local cache)
       ↓
Research Orchestrator iterates timestamps
       ↓
[for each timestamp]
  Candles up to timestamp
       ↓ (Strategy.generate_signal)
  Signal | None
       ↓ (RiskManager.evaluate)
  RiskDecision (approved / rejected)
       ↓ (if approved)
  Order
       ↓ (ExecutionEngine.submit_order)
  Fill
       ↓
  Position (open)
       ↓ (position management: stop / target / time)
  Trade (closed)
       ↓
  ResearchResults
       ↓ (Reporting)
  Report, charts, trade journal
```

---

## Backtest vs. Paper Trading

The architecture is designed so both modes share the same core:

| Component | Backtest Mode | Paper Trading Mode |
|-----------|--------------|-------------------|
| Data | `FileDataProvider` (historical) | Real-time Binance WebSocket |
| Strategy | `Strategy.generate_signal()` | Same |
| Risk | `RiskManager.evaluate()` | Same |
| Execution | `BacktestExecutionEngine` | `PaperTradingExecutionEngine` |
| Domain objects | Same (`Order`, `Fill`, `Trade`) | Same |

Only the data source and execution environment differ. All strategy logic is reusable without modification.

---

## Dependency Rules

- `core` depends on nothing else in the package.
- `config` depends on `core.exceptions` only.
- `data`, `strategies`, `execution`, `risk` depend on `core` only.
- `research` depends on `core`, `config`, `utils`.
- `utils` depends on nothing else in the package.
- `reporting` depends on `core` only (reads results).

This prevents circular imports and keeps the architecture clean.
