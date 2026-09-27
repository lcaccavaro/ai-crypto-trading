"""
Paper Trading Heartbeat — Prompt 08.

Emits periodic operational status logs and CSV rows.

Heartbeat data is operational only:
    - It does NOT affect trading decisions.
    - It does NOT imply trading results.
    - It is NOT a performance metric.

The heartbeat should be emitted at a configurable interval (e.g. every 60s)
regardless of whether any market events have been received.
"""

from __future__ import annotations

from datetime import datetime, timezone

from crypto_research.utils.logging import get_logger

logger = get_logger(__name__)


class PaperHeartbeat:
    """
    Emits periodic operational heartbeat for a paper trading session.

    Usage:
        hb = PaperHeartbeat(session, interval_seconds=60)
        # Inside event loop:
        if hb.should_emit():
            hb.emit(audit_writer)
    """

    def __init__(self, session, interval_seconds: int = 60) -> None:
        self._session = session
        self._interval = interval_seconds
        self._last_emit: datetime | None = None

    def should_emit(self) -> bool:
        """Return True if it is time to emit a heartbeat."""
        now = datetime.now(timezone.utc)
        if self._last_emit is None:
            return True
        elapsed = (now - self._last_emit).total_seconds()
        return elapsed >= self._interval

    def emit(self, audit_writer=None) -> dict:
        """
        Build and emit a heartbeat payload.

        Args:
            audit_writer: Optional PaperAuditWriter — if provided, writes to CSV.

        Returns:
            Heartbeat payload dict.
        """
        session = self._session
        now = datetime.now(timezone.utc)
        self._last_emit = now

        payload = {
            "timestamp": now.isoformat(),
            "session_id": session.session_id,
            "state": session.state.value,
            "uptime_seconds": round(session.uptime_seconds(), 1),
            "equity": round(session.accounting.equity, 4),
            "realized_pnl": round(session.accounting.realized_pnl, 4),
            "unrealized_pnl": round(session.accounting.unrealized_pnl, 4),
            "net_pnl": round(session.accounting.net_pnl, 4),
            "open_positions": len(session.open_positions),
            "trades_completed": session.counters.trades_completed,
            "signals_generated": session.counters.signals_generated,
            "signals_accepted": session.counters.signals_accepted,
            "signals_rejected": session.counters.signals_rejected,
            "errors": session.counters.errors,
            "warnings": session.counters.warnings,
            "checkpoints_saved": session.counters.checkpoints_saved,
            "execution_mode": session.execution_mode.value,
        }

        logger.info(
            "HEARTBEAT",
            **{k: v for k, v in payload.items() if k != "session_id"},
        )

        if audit_writer is not None:
            audit_writer.write_heartbeat(payload)

        return payload
