"""
Data aggregation for Prompt 06 reporting.
Groups trade diary records into daily, weekly, and monthly summaries.
"""

from __future__ import annotations

from typing import Iterable, Sequence
from datetime import datetime, timezone
from collections import defaultdict
import statistics

from crypto_research.reporting.models import (
    TradeDiaryRecord, DailyReportRecord, WeeklyReportRecord, MonthlyReportRecord
)
from crypto_research.core.domain import PortfolioState

class ReportAggregator:
    """Aggregates trade diaries and portfolio states into temporal reports."""
    
    def __init__(self, portfolio_states: list[PortfolioState]):
        # We assume portfolio states are recorded periodically (e.g. daily boundaries or trade events)
        self._portfolio_states = sorted(portfolio_states, key=lambda x: x.timestamp)
        
    def _get_equity_at_start(self, dt: datetime) -> float:
        """Find the equity at or just before the start of the period."""
        last_eq = 0.0
        for ps in self._portfolio_states:
            if ps.timestamp <= dt:
                last_eq = ps.equity
            else:
                break
        return last_eq

    def _get_equity_at_end(self, dt: datetime) -> float:
        """Find the equity at or just before the end of the period."""
        last_eq = 0.0
        for ps in self._portfolio_states:
            if ps.timestamp <= dt:
                last_eq = ps.equity
            else:
                break
        return last_eq

    def aggregate_daily(self, trades: Sequence[TradeDiaryRecord], rejected_signals: int = 0) -> list[DailyReportRecord]:
        """Aggregate trades by UTC day."""
        days = defaultdict(list)
        for t in trades:
            day_str = t.entry_timestamp.date().isoformat()
            days[day_str].append(t)
            
        reports = []
        for day_str, day_trades in sorted(days.items()):
            dt_start = datetime.fromisoformat(day_str).replace(tzinfo=timezone.utc)
            dt_end = datetime.fromisoformat(day_str).replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
            
            start_eq = self._get_equity_at_start(dt_start)
            end_eq = self._get_equity_at_end(dt_end)
            
            net_pnl = sum(t.net_pnl for t in day_trades)
            gross_pnl = sum(t.gross_pnl for t in day_trades)
            costs = sum(t.total_cost for t in day_trades)
            
            wins = [t for t in day_trades if t.net_pnl > 0]
            losses = [t for t in day_trades if t.net_pnl < 0]
            bes = [t for t in day_trades if t.net_pnl == 0]
            
            win_r = [t.realized_R for t in wins]
            loss_r = [t.realized_R for t in losses]
            
            reports.append(DailyReportRecord(
                date=day_str,
                starting_equity=start_eq,
                ending_equity=end_eq,
                gross_pnl=gross_pnl,
                total_costs=costs,
                net_pnl=net_pnl,
                net_return_pct=(net_pnl / start_eq * 100.0) if start_eq > 0 else 0.0,
                executed_trades=len(day_trades),
                rejected_signals=rejected_signals, # Simplified for now
                wins=len(wins),
                losses=len(losses),
                break_even=len(bes),
                win_rate=len(wins)/len(day_trades) if day_trades else 0.0,
                average_R=statistics.mean([t.realized_R for t in day_trades]) if day_trades else 0.0,
                total_R=sum([t.realized_R for t in day_trades]),
                average_winning_R=statistics.mean(win_r) if win_r else 0.0,
                average_losing_R=statistics.mean(loss_r) if loss_r else 0.0,
                largest_win=max([t.net_pnl for t in wins]) if wins else 0.0,
                largest_loss=min([t.net_pnl for t in losses]) if losses else 0.0,
                max_drawdown=0.0, # Requires intrabar equity curve
                average_holding_duration=statistics.mean([t.holding_duration_seconds for t in day_trades]) if day_trades else 0.0,
                strategy_count=len(set(t.strategy_id for t in day_trades)),
                asset_count=len(set(t.symbol for t in day_trades)),
                timeframe_count=len(set(t.timeframe for t in day_trades)),
            ))
            
        return reports

    def aggregate_weekly(self, trades: Sequence[TradeDiaryRecord]) -> list[WeeklyReportRecord]:
        """Aggregate trades by ISO calendar week."""
        weeks: dict[str, list[TradeDiaryRecord]] = defaultdict(list)
        for t in trades:
            iso_year, iso_week, _ = t.entry_timestamp.isocalendar()
            week_str = f"{iso_year}-W{iso_week:02d}"
            weeks[week_str].append(t)

        reports = []
        for week_str, week_trades in sorted(weeks.items()):
            # Derive date boundaries from the trades themselves
            first_entry = min(t.entry_timestamp for t in week_trades)
            last_exit = max(t.final_exit_timestamp for t in week_trades)

            start_eq = self._get_equity_at_start(first_entry)
            end_eq = self._get_equity_at_end(last_exit)

            net_pnl = sum(t.net_pnl for t in week_trades)
            wins = [t for t in week_trades if t.net_pnl > 0]
            losses = [t for t in week_trades if t.net_pnl < 0]

            reports.append(WeeklyReportRecord(
                period=week_str,
                starting_equity=start_eq,
                ending_equity=end_eq,
                net_pnl=net_pnl,
                net_return_pct=(net_pnl / start_eq * 100.0) if start_eq > 0 else 0.0,
                total_trades=len(week_trades),
                wins=len(wins),
                losses=len(losses),
                average_R=statistics.mean([t.realized_R for t in week_trades]) if week_trades else 0.0,
                total_R=sum(t.realized_R for t in week_trades),
                max_drawdown=0.0,
                average_holding_time=statistics.mean([t.holding_duration_seconds for t in week_trades]) if week_trades else 0.0,
                total_costs=sum(t.total_cost for t in week_trades),
                rejected_opportunities=0,
            ))
        return reports

    def aggregate_monthly(self, trades: Sequence[TradeDiaryRecord]) -> list[MonthlyReportRecord]:
        """Aggregate trades by calendar month."""
        months: dict[str, list[TradeDiaryRecord]] = defaultdict(list)
        for t in trades:
            month_str = t.entry_timestamp.strftime("%Y-%m")
            months[month_str].append(t)

        reports = []
        for month_str, month_trades in sorted(months.items()):
            first_entry = min(t.entry_timestamp for t in month_trades)
            last_exit = max(t.final_exit_timestamp for t in month_trades)

            start_eq = self._get_equity_at_start(first_entry)
            end_eq = self._get_equity_at_end(last_exit)

            net_pnl = sum(t.net_pnl for t in month_trades)
            wins = [t for t in month_trades if t.net_pnl > 0]
            losses = [t for t in month_trades if t.net_pnl < 0]

            # Count active days (days on which at least one trade was entered)
            active_days = len(set(t.entry_timestamp.date() for t in month_trades))

            reports.append(MonthlyReportRecord(
                period=month_str,
                starting_equity=start_eq,
                ending_equity=end_eq,
                net_pnl=net_pnl,
                net_return_pct=(net_pnl / start_eq * 100.0) if start_eq > 0 else 0.0,
                total_trades=len(month_trades),
                wins=len(wins),
                losses=len(losses),
                average_R=statistics.mean([t.realized_R for t in month_trades]) if month_trades else 0.0,
                total_R=sum(t.realized_R for t in month_trades),
                max_drawdown=0.0,
                total_costs=sum(t.total_cost for t in month_trades),
                average_holding_duration=statistics.mean([t.holding_duration_seconds for t in month_trades]) if month_trades else 0.0,
                active_trading_days=active_days,
                zero_trade_days=0,  # Cannot compute without full calendar; document as limitation
            ))
        return reports
