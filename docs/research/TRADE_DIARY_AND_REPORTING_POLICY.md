# Trade Diary & Reporting Policy

## Overview
This document defines the reporting policy for the AI Crypto Trading project. The reporting layer is strictly an **observer** and does not influence historical decisions. It is downstream from the core backtest engine.

## Data Sources
The reporting layer consumes artifacts emitted by the engine:
1. `Trade` models.
2. `Signal` events.
3. `RiskDecisionRecord`s.
4. `PortfolioState`s.

## Diary Schema
The `TradeDiaryRecord` flattens execution metadata, signal details, and risk explanations into a single auditable row.
Fields include: `run_id`, `trade_id`, `strategy_id`, `signal_timestamp`, `entry_price`, `exit_price`, `realized_R`, `decision_quality`.

## Decision Quality Methodology
Decision quality distinguishes whether a trade correctly followed historical rules, separate from its financial outcome (profit/loss).
- `VALID_DECISION`: The trade followed the active strategy, scoring, and risk constraints.
- `INVALID_DECISION`: A constraint was bypassed.
- `INCOMPLETE_AUDIT`: Insufficient artifact data exists to audit the trade.

## Aggregations
- **Daily**: Grouped by UTC day.
- **Weekly**: Grouped by ISO Calendar Week.
- **Monthly**: Grouped by Calendar Month.
All aggregations track net PnL, average R, and win rate.

## Reproducibility and Point-In-Time
All reports derive from explicit run metadata. Decisions are logged exactly as they occurred historically. Any charting that uses "future" data explicitly separates the pre-entry decision information from the retrospective post-entry outcome visualization.
