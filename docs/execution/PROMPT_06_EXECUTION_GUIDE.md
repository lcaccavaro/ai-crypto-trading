# Execution Guide: Prompt 06

## What was implemented
Prompt 06 introduces a comprehensive reporting and observability layer. It translates raw execution data (Trades, Signals, Risk Decisions) into structured diaries, CSV exports, Markdown summaries, and temporal aggregations (Daily/Weekly/Monthly).

## Prerequisites
- Completed Prompt 05.
- Required python packages: `matplotlib`, `pandas`.

## Running the Reports
Reports are generated automatically by passing the results of a backtest run to `ReportingRunner.generate_all()`.

## Validation
Execute the Jupyter notebook:
`jupyter notebook notebooks/06_trade_diary_and_reporting_validation.ipynb`

## Output Artifacts
For a given `run_id`, outputs are saved to `results/<run_id>/`:
- `trade_diary.csv`
- `summaries/daily_summary.csv`
- `summaries/weekly_summary.csv`
- `summaries/monthly_summary.csv`
- `reports/RUN_SUMMARY.md`

## Next Steps
If validation passes, the system is ready for **Prompt 07**.
