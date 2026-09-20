# Backtest Engine Policy

**Version:** 1.0.0  
**Applies to:** Prompt 03 — Point-in-Time Backtest Engine & Execution Simulator  
**Status:** Enforced — these are hard constraints, not preferences.

---

> [!CAUTION]
> Backtest results produced by this engine have **no predictive value** by themselves.
> They are a necessary first step to validate that the engine operates correctly — not evidence of a trading edge.

---

## 1. Core Principles

### 1.1 Point-in-Time Integrity

The engine operates a deterministic simulation where **every decision at time T uses only information that was available at time T**.

- A candle at timestamp `T` is considered available when its `close_time < T`.
- The strategy receives a `HistoricalDataView` that enforces this constraint by construction.
- Any attempt to access future data raises `LookAheadBiasError` immediately (not silently ignored).

**This is non-negotiable.** Violating PIT integrity invalidates the entire backtest and every downstream analysis.

### 1.2 Signal Timing — Next Candle Open

A signal generated from the **close** of candle at time T is **not executed at T**.

The engine queues the entry and executes it at the **open of candle T+1**.

```
Candle T closes  →  Strategy generates signal  →  Signal queued
Candle T+1 opens →  Engine executes entry at T+1's OPEN price
```

This is the only PIT-correct behavior at OHLC resolution. Any other execution assumption introduces look-ahead bias.

### 1.3 Determinism

The same inputs (data + config + strategy) **always produce identical outputs**:
- Identical trade ledger
- Identical equity curve
- Identical metrics

Determinism is required for reproducibility. Any randomness in the engine is a bug.

---

## 2. OHLC Simulation Limitations

### 2.1 Intrabar Ambiguity

When a candle has `High >= target AND Low <= stop`, OHLC data **cannot tell us which was reached first**.

The engine applies a configurable policy (`intrabar_fill_policy`):

| Policy | Behavior | Use case |
|--------|----------|----------|
| `stop_first` | Stop triggered, trade closed at loss | **Default — conservative** |
| `target_first` | Target triggered, trade closed at profit | Optimistic upper bound |
| `reject_ambiguous` | Neither exit recorded | Research into candle behavior |

> [!IMPORTANT]
> **The policy you choose is not factually correct.** It is an assumption. All research output must document which policy was used.

### 2.2 Gap Fills

If a candle opens **beyond** a stop or target level (the market gapped):

| Gap policy | Fill price | Realistic? |
|------------|------------|------------|
| `fill_at_open` | Candle open price | **Yes — this is what actually happened** |
| `fill_at_level` | Stop/target level | No — the market never traded at that level |

**Default policy is `fill_at_open`.** Using `fill_at_level` for gaps is not permitted in primary research.

---

## 3. Cost Model

All costs are applied on every fill. There are **no cost-free fills** in a properly configured run.

**Cost components (applied separately and tracked independently):**

| Component | Description |
|-----------|-------------|
| `taker_fee_rate` | Fee for market orders (both entry and exit) |
| `slippage_bps` | Slippage in basis points applied to execution price |
| `spread_bps` | Half-spread cost (bid-ask spread) |

**All three components affect:**
1. The actual execution price (slippage + spread)
2. The reported fee cost (fee rate × notional)
3. The net PnL of every trade

> [!WARNING]
> Gross PnL and Net PnL are always distinct numbers when costs exist. Using gross PnL for any analysis is prohibited.

---

## 4. Capital and Risk Management

### 4.1 Position Sizing

| Mode | Formula | Notes |
|------|---------|-------|
| `risk_based` | `qty = (equity × risk_pct/100) / \|entry - stop\|` | Default — requires stop price |
| `fixed` | `qty = fixed_quantity` | Only for diagnostic runs |

### 4.2 Risk Gate Checks (pre-entry)

All checks are hard limits — if **any check fails**, the order is rejected and logged.

| Check | Reject Reason |
|-------|--------------|
| Max concurrent positions reached | `MAX_CONCURRENT_POSITIONS` |
| Gross exposure > `max_total_exposure_pct` | `MAX_TOTAL_EXPOSURE` |
| Asset exposure > `max_asset_exposure_pct` | `MAX_ASSET_EXPOSURE` |
| Daily profit target reached | `DAILY_PROFIT_TARGET_REACHED` |
| Daily loss limit exceeded | `DAILY_LOSS_LIMIT_REACHED` |
| Available capital < notional | `INSUFFICIENT_CAPITAL` |
| Short side (Prompt 03) | `SHORT_NOT_ALLOWED` |

All rejected orders are recorded in `orders.csv` with their rejection reason.

---

## 5. Accounting Integrity

### 5.1 Definitions

```
cash           = initial_balance - sum(entry notional) + sum(exit notional) - sum(fees)
equity         = cash + unrealized_pnl
net_pnl        = gross_pnl - fees - slippage_cost - spread_cost
daily_pnl      = realized pnl since last UTC midnight
drawdown       = (equity - peak_equity) / peak_equity
peak_equity    = max(equity seen so far) — NEVER uses future values
```

### 5.2 Drawdown Calculation

Drawdown is computed from the **historical equity peak only** — never the global maximum.

This means:
- At candle 100, drawdown uses max(equity[0..100]) as the peak.
- The global maximum at candle 500 is **never used** when computing drawdown at candle 100.

This is the PIT-correct method. Using global max introduces look-ahead bias into drawdown statistics.

---

## 6. Output Files

A completed backtest produces these files in `results/backtests/<run_id>/`:

| File | Contents |
|------|---------|
| `run_metadata.json` | Run ID, timestamp, symbol, timeframe |
| `config_snapshot.yaml` | Exact config used for this run |
| `trades.csv` | All completed trades with full cost breakdown |
| `orders.csv` | All orders (filled + rejected) |
| `fills.csv` | All individual fills (entry + exit) |
| `equity_curve.csv` | Timestamped equity, cash, drawdown |
| `execution_events.csv` | Full event ledger |
| `metrics.json` | Computed performance metrics |
| `summary.json` | Human-readable summary with WARNING label |

> [!CAUTION]
> `summary.json` always contains the warning: `"WARNING": "ENGINE_VALIDATION_ONLY strategy results. DO NOT interpret as research findings or evidence of edge."`

---

## 7. ENGINE_VALIDATION_ONLY Strategy

The `EngineValidationStrategy` class exists **solely to exercise all engine code paths**.

Properties:
- Generates a LONG signal every N candles (default: 20)
- Stop = 1% below entry
- Target = stop_distance × R:R above entry
- Deterministic: same data → same signals → same trades

> [!CAUTION]
> **Do NOT use this strategy in any Prompt 04+ research.**  
> All output files produced by this strategy are labeled `ENGINE_VALIDATION_ONLY`.  
> Results have zero research value.

---

## 8. Forbidden Operations

The following operations are forbidden in the backtest engine:

| Forbidden | Why |
|-----------|-----|
| Using today's close to execute today's trade | Look-ahead bias |
| Calculating drawdown using future equity peak | Look-ahead bias |
| Using global dataset max when computing PIT statistics | Look-ahead bias |
| Silent exception swallowing | Hides failures |
| Fallback data (synthetic/mocked candles) | Destroys PIT integrity |
| Randomness in fill prices | Destroys determinism |
| Unreported costs (zero-cost fills without explicit zero-cost config) | Optimistic bias |
