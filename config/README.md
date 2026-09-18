# Configuration Reference

This directory contains the central configuration for the **Crypto Market Research Laboratory**.

## Files

| File | Purpose |
|------|---------|
| `config.yaml` | Main configuration file — the single source of truth for all research parameters |

## Structure

```yaml
project:
  name: string          # Project identifier (no spaces)
  version: string       # Semantic version, e.g. "1.0.0"

research:
  market: string        # Market type: "crypto"
  data_source: string   # Data source: "binance"

assets:                 # List of asset symbols (min 1)
  - BTCUSDT
  - ETHUSDT

timeframes:             # List of candlestick timeframes (min 1)
  - 1m                  # Valid: 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h

risk:
  risk_reward_ratio: float       # > 0
  risk_per_trade_pct: float      # > 0, ≤ 100
  max_concurrent_positions: int  # > 0
  max_daily_loss_pct: float      # > 0, ≤ 100
  daily_profit_target_pct: float | null  # Optional

execution:
  fee_rate: float | null         # null until Prompt 03
  slippage_model: string | null  # null until Prompt 03

logging:
  level: string                  # DEBUG | INFO | WARNING | ERROR
  format: string                 # console | structured
```

## Validation

Configuration is validated at startup by `src/crypto_research/config/schema.py` using Pydantic v2.

- **Extra keys are forbidden** — unknown keys raise `ConfigurationError`
- **Required fields must be present** — missing fields raise `ConfigurationError`
- **Invalid values raise `ConfigurationError`** — execution stops immediately

## Adding New Assets

Edit `config.yaml`:

```yaml
assets:
  - BTCUSDT
  - ETHUSDT
  - SOLUSDT
  - XRPUSDT   # ← add here
```

Do NOT modify Python source code to add assets.

## Adding New Timeframes

Edit `config.yaml`:

```yaml
timeframes:
  - 1m
  - 5m
  - 30m       # ← add here
  - 1h
```

Valid values: `1m`, `3m`, `5m`, `15m`, `30m`, `1h`, `2h`, `4h`
