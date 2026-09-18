# Research Principles

> These principles are non-negotiable. They apply to every prompt, every experiment, every result.

---

## 1. No Look-Ahead Bias

**Definition:** Using information from the future to influence a past decision.

**In backtesting, this is fatal.** Look-ahead bias produces results that cannot be reproduced in live trading because the information used was not actually available at the time of the decision.

**Examples of look-ahead bias:**
- Using tomorrow's high to set today's stop loss
- Computing a rolling indicator that includes future values
- Selecting strategies based on their future performance
- Using the final close price of a candle to trigger an entry at its open

**How this system prevents it:**
- `Strategy.generate_signal(candles, timestamp)` receives ONLY candles up to `timestamp`
- `DataProvider.get_candles(asset, tf, start, end)` must NEVER return candles beyond `end`
- `LookAheadBiasError` is a distinct exception type for explicit detection
- The `Candle.timestamp` field represents the candle OPEN, not the close
- The backtesting engine (Prompt 03) will iterate strictly forward in time

---

## 2. No Survivorship Bias

**Definition:** Studying only assets that survived (performed well) and ignoring those that delisted, crashed, or became illiquid.

**This produces an optimistic picture of market opportunity that did not exist at the time.**

**Examples:**
- Backtesting on the top 10 coins today as if they were available in 2020
- Selecting assets because they are now well-known successes

**How this system addresses it:**
- Asset universe is configured explicitly and must be justified
- Asset selection must reflect what was known and available at the time of the research
- Future prompts must document the universe selection rationale
- This cannot be fully solved automatically — it requires researcher discipline

---

## 3. No Data Snooping

**Definition:** Choosing strategies or parameters specifically because they worked on past data, without out-of-sample validation.

**Also known as:** overfitting, curve-fitting, p-hacking.

**Examples:**
- Trying 1000 parameter combinations and reporting the best
- Selecting the best-performing strategy from a large library without holdout testing
- Running the backtest and then adjusting parameters until it "works"

**How this system addresses it:**
- Walk-forward validation (Prompt 07) ensures parameters are selected in-sample and tested out-of-sample
- Research runs record every parameter for full traceability
- No parameter optimization is performed in Prompt 01
- Results are always presented with full methodology documentation

---

## 4. No Hidden Parameter Optimization

**Every parameter used in a research experiment must be explicitly recorded.**

Parameters that affect results but are not recorded make reproducibility impossible.

**Examples of hidden parameters:**
- Hardcoded constants in strategy code
- Filter thresholds chosen informally
- Lookback windows chosen by trial and error without recording
- Risk/reward ratios adjusted after seeing results

**How this system addresses it:**
- All strategy parameters live in `StrategyMetadata.parameters` (Prompt 04)
- All risk parameters live in `config.yaml`
- Every research run saves a full config snapshot
- Parameters must be fixed before the backtest begins

---

## 5. Full Reproducibility

**Every research result must be exactly reproducible.**

Given the same code version, configuration, and data, every experiment must produce identical results.

**Required for reproducibility:**
- Deterministic code (no hidden random seeds)
- Pinned dependency versions (recorded in `metadata.json`)
- Immutable input data (raw data is never modified)
- Complete parameter records
- Git commit hash (recorded in `metadata.json`)

**This system provides:**
- `ResearchRun` with run_id, created_at, python_version, package_versions, git_commit
- `config_snapshot.yaml` — exact config at run time
- `metadata.json` — full environment
- Run directory isolation — each run produces its own artifacts

---

## 6. Point-in-Time Integrity

**Information must only become available to the simulation when it would actually have been available.**

This goes beyond basic look-ahead bias. It means:

- Indicator values computed at time T must use only data available at T
- Orders must execute at realistic prices (not the exact high/low of a candle)
- Signal selection must use only the performance history available at T
- Strategy activation/deactivation logic must use only information available at T

**The correct mental model:**
```
We are sitting at timestamp T.
We only know what we would have known at T.
We cannot peek at T+1, T+2, or any future candle.
```

---

## 7. Fail Fast — No Silent Errors

**Every unexpected error must stop execution visibly.**

Silent errors produce misleading results. A backtest that continues despite data corruption produces fake performance metrics.

**Forbidden patterns:**
```python
# FORBIDDEN
except Exception:
    pass  # silently continue

# FORBIDDEN
except Exception:
    use_default_value()  # silent fallback

# FORBIDDEN
if data is None:
    data = generate_synthetic_data()  # fake data
```

**Required pattern:**
```python
# CORRECT
if data is None:
    raise DataIntegrityError(
        f"Required data not available for {asset} {timeframe} at {timestamp}.\n"
        f"Execution stopped. Investigate the data source."
    )
```

---

## 8. Separation of Research and Infrastructure Results

**Prompt 01 produces infrastructure validation results, not trading research results.**

There is a fundamental distinction:

| Type | What it measures | Examples |
|------|-----------------|---------|
| **Research result** | Does this strategy produce alpha? | Win rate, Sharpe ratio, max drawdown |
| **Infrastructure result** | Does the system work correctly? | Tests pass, config loads, run created |

Prompt 01 produces only infrastructure results.

**It is prohibited to claim:**
- "This strategy is profitable"
- "Expected return: X%"
- "Win rate: Y%"
- "Sharpe ratio: Z"

until real backtesting (Prompt 03) with real data (Prompt 02) has been performed.

---

## 9. No Fake Market Data

The system must never generate synthetic market data to demonstrate that pipelines "work."

**Permitted in tests:**
- Deterministic fixtures with clearly labeled test data
- OHLCV values constructed by hand for unit tests (labeled as `TEST FIXTURE`)
- Mathematical scenarios designed to test edge cases

**Never permitted:**
- Random OHLCV generation presented as market data
- Simulated Binance responses presented as real
- Strategy signals generated from fake prices

---

## 10. Documented Limitations

Every research output must clearly state its limitations.

**Required disclosures:**
- Data range used
- Assets in scope
- Transaction cost assumptions
- Slippage assumptions
- Universe selection method
- Known biases
- Out-of-sample validation status

**Do not present results as more robust than they are.**
