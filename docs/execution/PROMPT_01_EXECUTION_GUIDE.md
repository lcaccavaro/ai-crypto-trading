# PROMPT 01 — Execution Guide

## Objective

This document describes everything implemented in Prompt 01 and provides exact instructions for installation, execution, validation, and re-execution.

Prompt 01 establishes the **complete foundational infrastructure** for the quantitative research laboratory. It does NOT implement trading logic, market data ingestion, or backtesting.

---

## What Prompt 01 Implemented

| Component | Files |
|-----------|-------|
| Git repository | `.git/`, `.gitignore` |
| Project configuration | `pyproject.toml` |
| YAML configuration system | `config/config.yaml`, `src/crypto_research/config/` |
| Core domain objects | `src/crypto_research/core/domain.py` |
| Exception hierarchy | `src/crypto_research/core/exceptions.py` |
| Data provider interface | `src/crypto_research/data/interface.py` |
| Strategy interface | `src/crypto_research/strategies/interface.py` |
| Execution engine interface | `src/crypto_research/execution/interface.py` |
| Risk manager interface | `src/crypto_research/risk/interface.py` |
| Research run manager | `src/crypto_research/research/run_manager.py` |
| Structured logging | `src/crypto_research/utils/logging.py` |
| Environment capture | `src/crypto_research/utils/environment.py` |
| Unit tests (86 tests) | `tests/unit/` |
| Integration tests | `tests/integration/` |
| Validation notebook | `notebooks/01_project_validation.ipynb` |
| Documentation | `docs/`, `README.md`, `PROJECT_STATUS.md` |

---

## Prerequisites

| Requirement | Minimum |
|-------------|---------|
| Python | 3.11+ |
| pip | Any recent version |
| git | Any version |
| macOS / Linux | Supported |
| Windows | Should work, not tested |

---

## Installation

### Step 1: Navigate to the project directory

```bash
cd /path/to/ai-crypto-trading
```

### Step 2: (Optional) Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate   # macOS / Linux
# .venv\Scripts\activate    # Windows
```

### Step 3: Install the package and all dependencies

```bash
python3 -m pip install -e ".[dev]"
```

This installs:
- `crypto-research` (editable — changes to `src/` take effect immediately)
- `pydantic`, `pyyaml`, `structlog`, `rich` (runtime)
- `pytest`, `pytest-cov`, `nbmake`, `nbconvert`, `ipykernel`, `jupyter` (dev)

---

## Execution

### Run unit tests

```bash
python3 -m pytest tests/unit/ -v
```

**Expected:** All 76 unit tests PASS.

### Run integration tests

```bash
python3 -m pytest tests/integration/ -v
```

**Expected:** All 13 integration tests PASS.

### Run all tests with coverage

```bash
python3 -m pytest tests/ -v --cov=crypto_research --cov-report=term-missing
```

### Execute the validation notebook

```bash
python3 -m jupyter nbconvert \
  --to notebook \
  --execute notebooks/01_project_validation.ipynb \
  --output 01_project_validation_executed.ipynb \
  --output-dir notebooks/ \
  --ExecutePreprocessor.timeout=120
```

### Open the notebook interactively (optional)

```bash
python3 -m jupyter notebook notebooks/01_project_validation.ipynb
```

---

## Expected Output

### Tests

```
=================== 86 passed in X.XXs ====================
```

### Notebook

The final cell of the executed notebook should display:

```
============================================================
✅ ALL CHECKS PASSED (XX/XX)

Prompt 01 is COMPLETE.
Research run ID: RUN_YYYYMMDD_HHMMSS_xxxxxx

The project is ready for:
  PROMPT 02 — REAL BINANCE DATA INGESTION AND DATA QUALITY
============================================================
```

---

## Generated Files

After running the validation notebook, the following files are created:

```
results/
└── RUN_YYYYMMDD_HHMMSS_xxxxxx/
    ├── config_snapshot.yaml    ← Exact config used for this run
    ├── metadata.json           ← Full environment + run metadata
    ├── logs/
    │   └── research.log        ← Structured log file
    ├── trades/                 ← Empty in Prompt 01 (populated in Prompt 03)
    ├── charts/                 ← Empty in Prompt 01
    ├── reports/                ← Empty in Prompt 01
    └── summary/                ← Empty in Prompt 01

notebooks/
└── 01_project_validation_executed.ipynb  ← Executed notebook with outputs
```

---

## How to Analyze the Result

### Verify the run metadata

```bash
cat results/RUN_<your_run_id>/metadata.json
```

Check:
- `run_id` matches the directory name
- `git_commit` is either `"unavailable"` (no commits yet) or a 40-character hex hash
- `python_version` matches your interpreter
- `package_versions` shows correct versions
- `assets` and `timeframes` match `config/config.yaml`

### Verify the config snapshot

```bash
cat results/RUN_<your_run_id>/config_snapshot.yaml
```

This should be an exact copy of the configuration that was active during the run.

### Inspect the log file

```bash
cat results/RUN_<your_run_id>/logs/research.log
```

---

## Re-Run Instructions

To re-execute Prompt 01 validation from scratch:

```bash
# Run all tests
python3 -m pytest tests/ -v

# Re-execute the notebook (creates a new run in results/)
python3 -m jupyter nbconvert \
  --to notebook \
  --execute notebooks/01_project_validation.ipynb \
  --output 01_project_validation_executed.ipynb \
  --output-dir notebooks/ \
  --ExecutePreprocessor.timeout=120
```

Each notebook execution creates a new research run with a unique ID.

---

## Failure Troubleshooting

### `ModuleNotFoundError: No module named 'crypto_research'`

**Cause:** Package not installed in editable mode.

**Fix:**
```bash
python3 -m pip install -e ".[dev]"
```

### `ConfigurationError: Required configuration file not found`

**Cause:** `config/config.yaml` does not exist or the project root was not found.

**Fix:** Ensure you are running from the project root and that `config/config.yaml` exists.

### `pip._vendor.pyproject_hooks._impl.BackendUnavailable: Cannot import 'setuptools.backends.legacy'`

**Cause:** Old setuptools version. The project uses `setuptools.build_meta`.

**Fix:**
```bash
python3 -m pip install --upgrade setuptools
python3 -m pip install -e ".[dev]"
```

### Tests fail with `pydantic` errors

**Cause:** Wrong pydantic version (must be v2).

**Fix:**
```bash
python3 -m pip install "pydantic>=2.7"
```

### Notebook fails with `FileNotFoundError` on output path

**Cause:** Using `--output` with a path that includes the directory.

**Fix:** Use `--output-dir` and `--output` separately:
```bash
python3 -m jupyter nbconvert \
  --to notebook --execute notebooks/01_project_validation.ipynb \
  --output 01_project_validation_executed.ipynb \
  --output-dir notebooks/
```

---

## Success Checklist

Use this to verify Prompt 01 is complete before proceeding to Prompt 02.

- [ ] **Environment installed** — `pip install -e ".[dev]"` completed without error
- [ ] **Tests pass** — `pytest tests/ -v` shows 86/86 PASSED
- [ ] **Configuration loads** — `load_config("config/config.yaml")` returns without error
- [ ] **Configuration validation passes** — Valid config validates; invalid config raises `ConfigurationError`
- [ ] **Research run created** — `RunManager().create_run(config)` creates a directory under `results/`
- [ ] **Metadata generated** — `results/<run_id>/metadata.json` exists with all required fields
- [ ] **Config snapshot saved** — `results/<run_id>/config_snapshot.yaml` exists
- [ ] **Log file created** — `results/<run_id>/logs/research.log` exists
- [ ] **Notebook executes** — `01_project_validation.ipynb` runs without error
- [ ] **No errors in notebook** — Final cell shows `✅ ALL CHECKS PASSED`
- [ ] **No fake market data** — `trades/` directory is empty
- [ ] **Git commit integrity** — `git_commit` is real hash or `"unavailable"`, never fabricated
- [ ] **Documentation exists** — README.md, PROJECT_STATUS.md, architecture, research principles, this guide

---

## Acceptance Criteria

Prompt 01 is complete when ALL of the following are true:

1. **Infrastructure:** Project structure, pyproject.toml, gitignore are correct.
2. **Configuration:** YAML loads, validates, and fails fast on errors.
3. **Domain objects:** Candle, Signal, Order, Fill, Position, Trade, ResearchRun instantiate and validate correctly.
4. **Interfaces:** DataProvider, Strategy, ExecutionEngine, RiskManager Protocols are defined.
5. **Run manager:** Creates unique run IDs, directories, metadata.json, config_snapshot.yaml.
6. **Logging:** Initializes to console and file, carries run_id.
7. **Tests:** 86/86 tests PASS.
8. **Notebook:** Executes successfully end-to-end with clear `✅ ALL CHECKS PASSED`.
9. **Documentation:** All five required documents exist.
10. **Fail-fast:** Invalid config, missing files, data errors raise exceptions and stop execution.

---

## Next Step

Once all acceptance criteria pass:

> **PROMPT 02 — REAL BINANCE DATA INGESTION AND DATA QUALITY**
>
> Implements the `BinanceDataProvider` using the `DataProvider` interface defined in Prompt 01.
> Downloads, normalizes, and stores historical OHLCV data with full data quality checks.
