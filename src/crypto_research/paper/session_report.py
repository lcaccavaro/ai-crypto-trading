"""
Paper Session Report Writer — Prompt 08.

Generates the final PAPER_SESSION_REPORT.md at session end.

Report contents:
    Session metadata (ID, duration, mode, assets)
    Accounting summary (balance, equity, P&L, costs)
    Trade statistics (count, wins, losses, avg R)
    Risk event summary (rejections, reasons, cooldowns)
    Data health (gaps, duplicates, errors)
    Drift warnings (if any)
    Disclaimer: PAPER TRADING — SIMULATED — NO REAL ORDERS

Clearly labeled as PAPER in all headers and footers.
Historical backtest data is NOT included.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_research.utils.logging import get_logger

logger = get_logger(__name__)


class PaperSessionReportWriter:
    """Writes the end-of-session Markdown summary report."""

    def __init__(self, session_dir: str | Path) -> None:
        self._dir = Path(session_dir)
        self._reports_dir = self._dir / "reports"
        self._reports_dir.mkdir(parents=True, exist_ok=True)

    def write(
        self,
        session,
        drift_warnings: list,
        rejection_summary: dict | None = None,
    ) -> Path:
        """
        Generate PAPER_SESSION_REPORT.md.

        Args:
            session:            PaperTradingSession — final state.
            drift_warnings:     List of DriftWarning objects.
            rejection_summary:  Optional dict of rejection_reason → count.

        Returns:
            Path to the generated report file.
        """
        acct = session.accounting
        cnt = session.counters
        recon = session.reconcile()

        lines = [
            "# PAPER SESSION REPORT",
            "",
            "> ⚠️ **PAPER TRADING — SIMULATED EXECUTION — NO REAL ORDERS PLACED**  ",
            "> Results do NOT represent real trading performance.  ",
            "> Do NOT interpret as evidence of future profitability.",
            "",
            "---",
            "",
            "## 1. Session Identity",
            "",
            f"| Field | Value |",
            f"|-------|-------|",
            f"| Session ID | `{session.session_id}` |",
            f"| Run ID | `{session.run_id}` |",
            f"| Execution Mode | **{session.execution_mode.value}** |",
            f"| State | {session.state.value} |",
            f"| Start | {session.start_time.isoformat() if session.start_time else 'N/A'} |",
            f"| End | {session.end_time.isoformat() if session.end_time else 'N/A'} |",
            f"| Duration | {self._format_duration(session.uptime_seconds())} |",
            f"| Shutdown Reason | {session.shutdown_reason or 'N/A'} |",
            "",
            "---",
            "",
            "## 2. Accounting Summary",
            "",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Initial Balance | {acct.initial_balance:.4f} |",
            f"| Ending Cash | {acct.cash:.4f} |",
            f"| Realized P&L | {acct.realized_pnl:.4f} |",
            f"| Unrealized P&L | {acct.unrealized_pnl:.4f} |",
            f"| Gross P&L | {acct.gross_pnl:.4f} |",
            f"| Total Fees | {acct.total_fees:.4f} |",
            f"| Total Slippage | {acct.total_slippage:.4f} |",
            f"| Total Spread | {acct.total_spread:.4f} |",
            f"| **Net P&L** | **{acct.net_pnl:.4f}** |",
            f"| **Equity** | **{acct.equity:.4f}** |",
            "",
            "### Accounting Reconciliation",
            "",
            f"| Check | Result |",
            f"|-------|--------|",
            f"| Expected Equity | {recon['expected_equity']:.6f} |",
            f"| Actual Equity | {recon['actual_equity']:.6f} |",
            f"| Discrepancy | {recon['discrepancy']:.6f} |",
            f"| Reconciled | {'✅' if recon['reconciled'] else '❌'} |",
            "",
            "---",
            "",
            "## 3. Trade Statistics",
            "",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Trades Completed | {cnt.trades_completed} |",
            f"| Wins | {cnt.wins} |",
            f"| Losses | {cnt.losses} |",
            f"| Win Rate | {cnt.wins / cnt.trades_completed:.1%} if cnt.trades_completed > 0 else N/A |",
            f"| Open Positions | {len(session.open_positions)} |",
            f"| Orders Created | {cnt.orders_created} |",
            f"| Fills Executed | {cnt.fills_executed} |",
            "",
            "---",
            "",
            "## 4. Signal Statistics",
            "",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Signals Generated | {cnt.signals_generated} |",
            f"| Signals Accepted | {cnt.signals_accepted} |",
            f"| Signals Rejected | {cnt.signals_rejected} |",
            f"| Rejection Rate | {cnt.signals_rejected / cnt.signals_generated:.1%} if cnt.signals_generated > 0 else N/A |",
        ]

        if rejection_summary:
            lines += [
                "",
                "### Rejection Reasons",
                "",
                "| Reason | Count |",
                "|--------|-------|",
            ]
            for reason, count in sorted(rejection_summary.items()):
                lines.append(f"| {reason} | {count} |")

        lines += [
            "",
            "---",
            "",
            "## 5. Data Health",
            "",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Market Events Received | {cnt.market_events_received} |",
            f"| Market Events Rejected | {cnt.market_events_rejected} |",
            f"| Duplicate Events | {cnt.market_events_duplicate} |",
            f"| Data Gaps | {cnt.data_gaps} |",
            f"| Candles Processed | {cnt.candles_processed} |",
            f"| Errors | {cnt.errors} |",
            f"| Warnings | {cnt.warnings} |",
            f"| Checkpoints Saved | {cnt.checkpoints_saved} |",
            "",
            "---",
            "",
            "## 6. Drift Warnings",
            "",
        ]

        if drift_warnings:
            lines += [
                "| Code | Change % | Baseline | Paper Value |",
                "|------|----------|----------|-------------|",
            ]
            for w in drift_warnings:
                d = w.to_dict()
                lines.append(
                    f"| {d['code']} | {d['change_pct']:.1f}% | "
                    f"{d['baseline_value']:.4f} | {d['paper_value']:.4f} |"
                )
        else:
            lines.append("No drift warnings generated.")
            if cnt.trades_completed < 20:
                lines.append("")
                lines.append("*Insufficient paper trades for drift analysis.*")

        lines += [
            "",
            "---",
            "",
            "## 7. Disclaimer",
            "",
            "```",
            "PAPER TRADING SESSION",
            "SIMULATED EXECUTION ONLY",
            "NO REAL ORDERS WERE PLACED",
            "NO REAL MONEY WAS AT RISK",
            "RESULTS DO NOT REPRESENT REAL TRADING PERFORMANCE",
            "DO NOT INTERPRET AS EVIDENCE OF FUTURE PROFITABILITY",
            "```",
            "",
            f"*Report generated: {datetime.now(timezone.utc).isoformat()}*",
        ]

        report_path = self._reports_dir / "PAPER_SESSION_REPORT.md"
        report_path.write_text("\n".join(lines))
        logger.info("Paper session report written", path=str(report_path))
        return report_path

    @staticmethod
    def _format_duration(seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        return f"{h:02d}h {m:02d}m {s:02d}s"
