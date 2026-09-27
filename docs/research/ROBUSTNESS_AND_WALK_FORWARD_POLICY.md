# Walk-Forward & Robustness Research Policy

## Purpose

This document describes the research validation methodology implemented in
Prompt 07. It is the canonical reference for understanding how the system
avoids look-ahead bias, handles out-of-sample evaluation, and characterizes
robustness across time, parameters, assets, timeframes, and market regimes.

---

## 1. Fundamental Principle: No Look-Ahead

Information must flow **only forward in time**.

At every point in the analysis, a decision at timestamp `T` may use only
information available at or before `T`.

This applies to:
- Walk-forward windows (train → val → OOS, never reversed)
- Regime classification (uses only candles closed before `T`)
- Opportunity scoring (uses PIT candle views)
- Strategy state (no future trade outcomes influence current decisions)

**Violation detection**: The experiment registry records when OOS inspection
influenced configuration. The framework warns on overlapping OOS periods.

---

## 2. Walk-Forward Methodology

### 2.1 Window Structure

Every walk-forward window has three non-overlapping, chronologically ordered
periods:

```
TRAIN          VALIDATION       OOS
[t0 ... t1)    [t1 ... t2)     [t2 ... t3)
```

- **TRAIN**: The engine runs the full backtest. Results are used for learning
  (if strategy selection is enabled) but never injected back into the engine.
- **VALIDATION**: A confirmation period before OOS. May be used to freeze
  configuration. **Must not be treated as OOS.**
- **OOS (Out-of-Sample)**: The genuinely held-out period. Results here are
  the primary evaluation metric.

### 2.2 Rolling Mode

```
Window 0:  [Jan–Jun  TRAIN] [Jul  VAL] [Aug  OOS]
Window 1:  [Feb–Jul  TRAIN] [Aug  VAL] [Sep  OOS]
Window 2:  [Mar–Aug  TRAIN] [Sep  VAL] [Oct  OOS]
```

The training window has a fixed length. Older data is dropped.

### 2.3 Expanding Mode

```
Window 0:  [Jan–Jun      TRAIN] [Jul  VAL] [Aug  OOS]
Window 1:  [Jan–Jul      TRAIN] [Aug  VAL] [Sep  OOS]
Window 2:  [Jan–Aug      TRAIN] [Sep  VAL] [Oct  OOS]
```

The training window starts from the global start and grows with each step.

### 2.4 Non-overlapping OOS (Default)

OOS periods do not overlap between consecutive windows by default. This ensures
that the primary OOS aggregate does not double-count any trade.

---

## 3. OOS Integrity Rules

The OOS period **must not** be used to:

- Choose strategies
- Choose parameters
- Choose score thresholds
- Choose risk configuration
- Choose assets or timeframes

Any configuration change after inspecting OOS results invalidates the OOS
evaluation and must be documented as a post-OOS modification.

---

## 4. Strategy Selection (Optional, Disabled by Default)

Strategy selection research (`robustness.strategy_selection = true`) is
disabled by default to prevent accidental overfitting.

When enabled, selection happens **strictly inside the TRAIN period**:

```
TRAIN
  ↓
Selection rule applied (using only train data)
  ↓
Configuration frozen
  ↓
VALIDATION
  ↓
Final freeze
  ↓
OOS (no further modification)
```

The exact selection rule must be documented per experiment.

---

## 5. Sensitivity Analysis

### What It Is

Sensitivity analysis tests whether behavior remains reasonably stable when
a parameter changes within a **pre-defined, economically motivated neighborhood**.

### What It Is NOT

Sensitivity analysis is **not optimization**. It does not search for the
parameter that produces the highest return.

| | Sensitivity | Optimization |
|---|---|---|
| Question | "Is this stable?" | "What's the best?" |
| Allowed in P07? | ✅ Yes | ❌ No |

### Configurable Parameters

- Risk-reward ratio neighborhood (e.g., 2.0, 2.5, 3.0, 3.5, 4.0)
- Cost multipliers (e.g., 1.0x, 1.25x, 1.5x, 2.0x)
- Score thresholds (e.g., 40, 50, 60, 70)

---

## 6. Regime Analysis

Regime classification is **transparent, deterministic, and PIT-safe**.

### Regime Dimensions

| Dimension | Labels | Method |
|-----------|--------|--------|
| Trend | TREND_UP, TREND_DOWN, RANGE | Close vs. rolling MA |
| Volatility | LOW_VOL, NORMAL_VOL, HIGH_VOL | ATR as % of price |

### PIT Guarantee

At timestamp `T`:
- MA uses candles `[T-period+1 ... T]` (closed-left rolling window)
- ATR uses the same causal window
- No future candle is accessed

### Limitations

- Regime labels are defined thresholds, not ground truth
- Trades are assigned to the regime at their entry timestamp
- Trades spanning regime transitions are assigned to entry regime
- Classifications describe observed patterns, not causes

---

## 7. Robustness Warnings

Warning flags are **diagnostic signals**, not verdicts.

| Code | Triggered When |
|------|---------------|
| `LOW_SAMPLE_WARNING` | Trade count below configured minimum |
| `LOW_OOS_SAMPLE` | OOS window count below configured minimum |
| `HIGH_PARAMETER_SENSITIVITY` | Metric varies >30% across parameter neighborhood |
| `HIGH_COST_SENSITIVITY` | P&L degrades >50% under adverse cost scenario |
| `SINGLE_ASSET_DEPENDENCY` | One asset accounts for >70% of P&L |
| `SINGLE_TIMEFRAME_DEPENDENCY` | One timeframe accounts for >70% of P&L |
| `SINGLE_PERIOD_DEPENDENCY` | One period accounts for >70% of P&L |
| `REGIME_DEPENDENCY` | One regime accounts for >70% of P&L |

These thresholds are **research heuristics**, not statistical laws.
They are configurable. Their presence does not prove overfitting.

---

## 8. Experiment Registry

Every experiment is recorded in the registry before it starts. Failures are
explicitly logged with status `FAILED`, never silently dropped.

The registry documents the full experiment matrix, making the
**multiple-comparison problem** visible and transparent.

---

## 9. Multiple Testing Awareness

The research framework explicitly documents that testing many:
- strategies
- parameters
- assets
- timeframes
- regimes
- cost assumptions

...creates a multiple-comparison problem. The probability of observing a
spuriously positive result increases with the number of tests.

**Findings must not be interpreted as statistically significant** without
accounting for this. All results are hypotheses for further investigation.

---

## 10. Prohibited Actions

The following are strictly prohibited:

1. Strategy ranking ("Strategy A is best")
2. Overall robustness score ("87/100")
3. Future-based strategy selection
4. Injecting OOS results backward into configuration
5. Silently ignoring experiment failures
6. Presenting bootstrap output as proof of future performance
7. Calling a result "robust" based solely on positive P&L

---

## 11. Known Limitations

- Walk-forward with short date ranges produces few windows (LOW_OOS_SAMPLE)
- Regime classification uses rolling windows that produce NaN for the first
  `min_periods` candles
- Leave-one-period-out is computationally expensive and disabled by default
- Bootstrap confidence intervals are documented as future enhancement
- Monte Carlo trade-order reshuffling is documented as future enhancement
