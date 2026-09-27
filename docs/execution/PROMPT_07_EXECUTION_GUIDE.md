# Prompt 07 Execution Guide

## What Prompt 07 Implements

Prompt 07 adds a **research validation layer** on top of the existing
backtest engine. It does NOT replace or duplicate any existing component.

```
Historical Data
      ↓
BacktestEngine (P03)
      ↓
Strategy Universe (P04)
      ↓
Risk / Orchestration (P05)
      ↓
Trade Diary (P06)
      ↓
Walk-Forward Analysis  ← P07 starts here
      ↓
Out-of-Sample Evaluation
      ↓
Sensitivity Analysis
      ↓
Robustness Warnings
      ↓
Regime Analysis
      ↓
Experiment Registry
      ↓
ROBUSTNESS_REPORT.md
```

---

## Prerequisites

1. Python environment with all dependencies installed
2. Canonical datasets downloaded (Prompt 02 pipeline complete)
3. All unit tests passing: `pytest tests/unit/` → 588 passed
4. Baseline config validated: `config/config.yaml` exists and loads without errors

---

## New Modules (P07)

| Module | Location |
|--------|----------|
| Walk-Forward Splitter | `src/crypto_research/research/walk_forward/splitter.py` |
| Walk-Forward Runner | `src/crypto_research/research/walk_forward/runner.py` |
| Sensitivity Runner | `src/crypto_research/research/sensitivity/runner.py` |
| Regime Classifier | `src/crypto_research/research/regimes/classifier.py` |
| Regime Analyzer | `src/crypto_research/research/regimes/analyzer.py` |
| Robustness Warnings | `src/crypto_research/research/robustness/warnings.py` |
| Robustness Metrics | `src/crypto_research/research/robustness/metrics.py` |
| Experiment Registry | `src/crypto_research/research/experiments/registry.py` |
| Report Writer | `src/crypto_research/research/reporting/report_writer.py` |

---

## New Unit Tests (P07)

| Test File | Tests |
|-----------|-------|
| `tests/unit/research/test_splitter.py` | 18 tests |
| `tests/unit/research/test_regime_classifier.py` | 9 tests |
| `tests/unit/research/test_robustness_warnings.py` | 14 tests |
| `tests/unit/research/test_experiment_registry.py` | 12 tests |

Run: `pytest tests/unit/research/ -v`

---

## Running the Notebook

```bash
jupyter lab notebooks/07_robustness_and_walk_forward_validation.ipynb
```

The notebook executes from top to bottom. Do not skip sections.

---

## Configuration Reference

### Walk-Forward (in config.yaml)

```yaml
robustness:
  enabled: true
  run_type: FULL  # DEVELOPMENT | VALIDATION | FULL

  walk_forward:
    enabled: true
    mode: rolling       # rolling | expanding
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

  sensitivity:
    enabled: true
    risk_reward_ratios: [2.0, 2.5, 3.0, 3.5, 4.0]
    cost_multipliers: [1.0, 1.25, 1.5, 2.0]
    score_thresholds: [40.0, 50.0, 60.0, 70.0]

  regime:
    enabled: true
    trend:
      ma_period: 50
      slope_threshold_pct: 0.5
    volatility:
      atr_period: 14
      low_threshold_pct: 1.0
      high_threshold_pct: 3.0

  minimum_sample_sizes:
    trades: 30
    oos_windows: 5

  strategy_selection: false  # DISABLED — prevents accidental overfitting
```

---

## Output Directory Structure

```
results/<run_id>/
  robustness/
    experiment_registry.csv
    experiment_registry.json
    walk_forward/
      windows.csv          — one row per window
      oos_results.csv      — OOS metrics per window
      train_results.csv    — train metrics per window (reference)
      summary.json         — aggregate stability metrics
    sensitivity/
      parameter_sensitivity.csv  — RR neighborhood results
      cost_sensitivity.csv       — cost multiplier results
      score_sensitivity.csv      — score threshold results
      summary.json
    regimes/
      regime_definitions.json
      regime_trade_metrics.csv
      regime_summary.json
    warnings/
      robustness_warnings.csv
    robustness_summary.json
  reports/
    ROBUSTNESS_REPORT.md
```

---

## How to Interpret Reports

### Walk-Forward Summary

| Metric | Meaning |
|--------|---------|
| `valid_windows` | OOS periods that ran without error |
| `positive_oos_windows` | Windows with positive OOS net P&L |
| `pct_positive_windows` | % of OOS windows that were positive |
| `median_oos_net_pnl` | Central tendency of OOS P&L across windows |
| `stdev_oos_net_pnl` | Dispersion of OOS P&L (higher = less stable) |

### Warning Interpretation

A warning is a **diagnostic signal**, not a verdict.

| Warning | What to do |
|---------|-----------|
| `LOW_SAMPLE_WARNING` | Report trade count. Do not declare significance. |
| `HIGH_PARAMETER_SENSITIVITY` | Investigate which parameter is unstable. |
| `HIGH_COST_SENSITIVITY` | Report whether result survives realistic costs. |
| `SINGLE_ASSET_DEPENDENCY` | Report which asset drives performance. |
| `REGIME_DEPENDENCY` | Report which regime the result is concentrated in. |

---

## What Does NOT Count as Proof

- Positive OOS net P&L in a single window
- A high win rate in a short period
- "The strategy worked in-sample"
- A warning being absent
- A high profit factor with few trades
- Positive total R without trade count context

---

## What Counts as Evidence (Descriptive)

- Positive OOS P&L across a majority of independent windows
- Stability across reasonable parameter neighborhood
- Behavior consistent across multiple assets
- Performance not concentrated in one regime

Even these do not constitute proof of future profitability.

---

## Reproducibility

To reproduce any experiment:

1. Same `config.yaml`
2. Same dataset (run Prompt 02 pipeline with same date range)
3. Same code version (check `git rev-parse HEAD`)
4. Same run_id (stored in `experiment_registry.json`)

All experiment configurations are stored in `experiment_registry.json`.

---

## Known Limitations

1. Walk-forward with short date ranges produces few OOS windows (LOW_OOS_SAMPLE)
2. Expanding mode with very long periods may produce only 1-2 windows
3. Bootstrap confidence intervals not implemented (future enhancement)
4. Monte Carlo trade-order reshuffling not implemented (future enhancement)
5. Leave-one-period-out is disabled by default (computational cost)
6. Regime classification produces NaN for the first `min_periods` candles

---

## Acceptance Criteria

Prompt 07 is **COMPLETE** when:

- [x] Walk-forward splitter: rolling and expanding modes implemented
- [x] Temporal ordering validated by `window.validate()`
- [x] OOS non-overlap validated by `splitter.validate_no_oos_overlap()`
- [x] Walk-forward runner executes engine over each window
- [x] Sensitivity runner tests pre-defined neighborhood (not optimization)
- [x] Regime classifier is PIT-safe (vectorized causal rolling windows)
- [x] Regime analyzer joins trades to regimes by entry timestamp
- [x] All 8 robustness warning types implemented
- [x] Experiment registry records all experiments with config snapshots
- [x] Report writer produces CSV, JSON, and Markdown outputs
- [x] 53 new unit tests added, all passing
- [x] Full test suite: 588 passed, 0 failed
- [x] No existing tests broken
- [x] Config schema extended with backward-compatible defaults
- [x] ROBUSTNESS_AND_WALK_FORWARD_POLICY.md created
- [x] PROMPT_07_EXECUTION_GUIDE.md created

---

## Next Step

Proceed to **Prompt 08** only if:
- All acceptance criteria above are met
- Notebook executes end-to-end without errors
- Walk-forward results have been reviewed and warnings documented
- No P01-P06 regressions

---

*Prompt 07 is a RESEARCH VALIDATION stage.*
*It does not optimize, rank strategies, or predict future performance.*
