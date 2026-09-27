"""
Paper Trading Package — Prompt 08.

Provides simulated trading on live Binance public market data using the
SAME strategy interfaces, risk management, execution semantics, and
reporting infrastructure as the historical backtest engine.

Key constraint: NO real orders. NO trading credentials. PAPER only.

Package structure:
    safety.py       — Hard guard: rejects ExecutionMode.LIVE
    data_provider.py— Public Binance REST polling provider
    session.py      — PaperTradingSession (lifecycle, state machine)
    engine.py       — Paper event loop + orchestration
    checkpoint.py   — Atomic state persistence / restore
    audit_writer.py — Writes all audit CSV files
    drift_monitor.py— Signal/score/cost drift detection
    heartbeat.py    — Periodic operational metrics
    session_report.py — Final session summary report
    replay.py       — Deterministic historical replay mode
"""
