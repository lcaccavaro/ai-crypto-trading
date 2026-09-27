"""
Report Exporter for Prompt 06.
Writes daily, weekly, monthly aggregations and the full trade diary to disk.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from dataclasses import asdict

from crypto_research.reporting.models import (
    TradeDiaryRecord, DailyReportRecord, WeeklyReportRecord, MonthlyReportRecord
)
from crypto_research.utils.logging import get_logger

logger = get_logger(__name__)

class ReportExporter:
    """Exports structured reporting artifacts to disk."""
    
    def __init__(self, output_dir: str | Path):
        self.output_dir = Path(output_dir)
        self.reports_dir = self.output_dir / "reports"
        self.summaries_dir = self.output_dir / "summaries"
        
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.summaries_dir.mkdir(parents=True, exist_ok=True)

    def export_trade_diary(self, records: list[TradeDiaryRecord]) -> None:
        """Export the full trade diary to CSV."""
        path = self.output_dir / "trade_diary.csv"
        if not records:
            path.write_text("No trades recorded.\n")
            return
            
        with path.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(asdict(records[0]).keys()))
            writer.writeheader()
            for r in records:
                writer.writerow(asdict(r))
        logger.info(f"Exported trade diary: {path}")

    def export_daily_reports(self, records: list[DailyReportRecord]) -> None:
        """Export daily reports to CSV."""
        path = self.summaries_dir / "daily_summary.csv"
        if not records:
            return
            
        with path.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(asdict(records[0]).keys()))
            writer.writeheader()
            for r in records:
                writer.writerow(asdict(r))
        logger.info(f"Exported daily reports: {path}")

    def export_weekly_reports(self, records: list[WeeklyReportRecord]) -> None:
        """Export weekly reports to CSV."""
        path = self.summaries_dir / "weekly_summary.csv"
        if not records:
            return
            
        with path.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(asdict(records[0]).keys()))
            writer.writeheader()
            for r in records:
                writer.writerow(asdict(r))

    def export_monthly_reports(self, records: list[MonthlyReportRecord]) -> None:
        """Export monthly reports to CSV."""
        path = self.summaries_dir / "monthly_summary.csv"
        if not records:
            return
            
        with path.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(asdict(records[0]).keys()))
            writer.writeheader()
            for r in records:
                writer.writerow(asdict(r))

    def export_markdown_summary(
        self,
        trades: list[TradeDiaryRecord],
        daily: list[DailyReportRecord],
        weekly: list[WeeklyReportRecord],
        monthly: list[MonthlyReportRecord]
    ) -> None:
        """Generate high-level markdown reports."""
        path = self.reports_dir / "RUN_SUMMARY.md"
        
        total_trades = len(trades)
        wins = len([t for t in trades if t.net_pnl > 0])
        losses = len([t for t in trades if t.net_pnl < 0])
        total_net_pnl = sum(t.net_pnl for t in trades)
        total_costs = sum(t.total_cost for t in trades)
        
        md = [
            "# Execution Run Summary",
            "",
            "## Overall Performance",
            f"- **Total Trades**: {total_trades}",
            f"- **Wins**: {wins}",
            f"- **Losses**: {losses}",
            f"- **Net P&L**: {total_net_pnl:.2f}",
            f"- **Total Costs**: {total_costs:.2f}",
            "",
            "## Daily Breakdown",
            "| Date | Trades | Net P&L | Win Rate |",
            "|---|---|---|---|"
        ]
        
        for d in daily:
            md.append(f"| {d.date} | {d.executed_trades} | {d.net_pnl:.2f} | {d.win_rate:.2%} |")
            
        path.write_text("\n".join(md))
        logger.info(f"Exported RUN_SUMMARY.md: {path}")
