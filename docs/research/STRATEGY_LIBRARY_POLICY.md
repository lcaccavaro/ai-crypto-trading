# Strategy Library Policy

## Purpose

This document defines the governing rules for the Prompt 04 strategy library.
All contributors and reviewers must understand and adhere to these policies.

---

## 1. Core Principle: Research Library, Not Signal Generator

The strategy library is a **research universe**. Its purpose is to generate
a broad, structurally diverse set of signals across 8 distinct strategy families.

**The library is NOT:**
- A signal generation service for live trading
- A ranking of "good" vs "bad" strategies
- An optimized parameter set
- A guarantee of profitability

---

## 2. Strategy Neutrality

### 2.1 No Strategy Ranking
Strategies must not be ranked by performance within this library.
All 26 strategies are peers in the research universe.

### 2.2 No Parameter Optimization
Default parameters are **research defaults** only. They exist to make
strategies executable, not to maximize profitability. The parameter schema
documents valid ranges but makes no claim about optimal values.

### 2.3 No Selection Based on Profitability
Strategies are not removed from the library because they underperform.
The library's value is its diversity, not its aggregate return.

---

## 3. Point-In-Time (PIT) Integrity

### 3.1 Mandatory Prior-Window Rule
Breakout strategies (DONCHIAN_001, RANGE_BREAK_001, etc.) must compute
their threshold from the **previous completed window**, not the current candle.

At candle T, the breakout level = max(highs[T-period-1 : T-1]).
Candle T itself is NEVER included in the breakout threshold computation.

### 3.2 No Future Information
Strategies may only read data from the `candles[]` list passed to
`generate_signal()`. They must not access external mutable state,
system time, or any data beyond what is in the provided candle list.

### 3.3 Zero-Volatility Handling
When a rolling standard deviation is 0 (constant prices):
- Return `None`, not 0.0
- Do NOT inject epsilon to avoid division by zero
- Let the strategy return NOT_READY

---

## 4. State Isolation

Each strategy instance is independently stateful. The following guarantee
must hold at all times:

> Running `EMA_CROSS_001` on `BTCUSDT/5m` must NEVER affect the state
> of any other `EMA_CROSS_001` instance (e.g., `ETHUSDT/15m`).

### 4.1 Instance Isolation Test
The `tests/unit/strategies/test_strategy_isolation.py` suite enforces this.
All state isolation tests must pass before any strategy is added to the library.

### 4.2 reset() Contract
Every strategy that maintains internal state must implement `reset()`.
`reset()` must restore the instance to its pre-warmup state.

---

## 5. Adding New Strategies

To add a new strategy to the library:

1. **Create** `src/crypto_research/strategies/<group>/<name>.py`
2. **Define** `_info: StrategyInfo` as a class attribute
3. **Implement** `_compute_signal()` and `parameters`
4. **Decorate** with `@REGISTRY.register`
5. **Import** in the group `__init__.py`
6. **Add tests** covering: default init, invalid params, warmup, signal direction
7. **Update** `strategy_catalog.json` (auto-generated: `python3 scripts/generate_catalog.py`)
8. **Update** this policy if the new strategy introduces a new pattern

---

## 6. Hypothesis Documentation

Every strategy must document its research hypothesis in `StrategyInfo.hypothesis`.
The hypothesis must be:
- Falsifiable (can be tested empirically)
- Not a trading claim ("this strategy is profitable")
- Describing what market behavior is being tested

**Good:** "When a faster EMA crosses above a slower EMA, this may indicate emerging directional momentum."

**Bad:** "EMA crossovers are profitable."

---

## 7. Category Taxonomy

| Category | Description |
|---|---|
| `trend` | Directional trend-following based on moving averages |
| `momentum` | Rate of change, RSI, or MACD-based momentum |
| `mean_reversion` | Statistical extreme and reversion hypotheses |
| `breakout` | Price level breakouts from prior consolidation ranges |
| `volatility` | ATR or Bollinger Band volatility regime changes |
| `volume` | Volume-based confirmation or anomaly detection |
| `multi_indicator` | Cross-family indicator confirmation combinations |
| `market_structure` | Price structure patterns (HH/HL, regime detection) |

---

## 8. Session Range Breakout (D4 Substitution)

Prompt 04 specified D4 as "Session Range Breakout." This was substituted
with `ATR_CHANNEL_001` because:

- Binance operates 24/7 without native session boundaries
- Arbitrary session definitions (e.g., 00:00-08:00 UTC) are undocumented assumptions
- ATR Channel Breakout provides an equivalent "dynamic envelope breakout" hypothesis
  without requiring session semantics

This decision is documented in `strategies/breakout/atr_channel_break.py`.
