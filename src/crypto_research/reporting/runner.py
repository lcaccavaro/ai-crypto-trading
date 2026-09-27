"""
Orchestrator for the reporting layer (Prompt 06).
Ties together Diary Builders, Aggregators, Exporters, and Charts.
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence, Optional

from crypto_research.config.schema import ReportingConfig
from crypto_research.core.domain import Trade, Signal, RiskDecisionRecord, PortfolioState
from crypto_research.reporting.diary import TradeDiaryBuilder
from crypto_research.reporting.aggregator import ReportAggregator
from crypto_research.reporting.exporter import ReportExporter
from crypto_research.reporting.charts import ChartGenerator
from crypto_research.utils.logging import get_logger

logger = get_logger(__name__)

class ReportingRunner:
    """Main entrypoint for generating all reports for a backtest run."""
    
    def __init__(self, run_id: str, config: ReportingConfig, output_dir: str | Path):
        self.run_id = run_id
        self.config = config
        self.output_dir = Path(output_dir) / run_id
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.diary_builder = TradeDiaryBuilder(run_id=self.run_id)
        self.exporter = ReportExporter(output_dir=self.output_dir)
        self.chart_gen = ChartGenerator(output_dir=self.output_dir) if self.config.trade_charts.enabled else None

    def generate_all(
        self,
        trades: Sequence[Trade],
        signals: Sequence[Signal],
        risk_decisions: Sequence[RiskDecisionRecord],
        portfolio_states: Sequence[PortfolioState]
    ) -> None:
        """Execute the full reporting pipeline."""
        
        if not self.config.enabled:
            logger.info("Reporting is disabled in config.")
            return
            
        logger.info(f"Generating reports for run {self.run_id}")
        
        # 1. Build Trade Diary
        diary_records = []
        for trade in trades:
            # Find matching signal and decision
            # Note: In a real environment, we'd join on trade_id/signal_id.
            # Assuming trade.signal_id exists, or we match by timestamp/asset.
            # For this MVP, we match by closest timestamp and asset for demonstration.
            sig = next((s for s in signals if s.asset == trade.asset and s.timestamp <= trade.entry_fill.timestamp), None) if trade.entry_fill else None
            dec = next((d for d in risk_decisions if d.signal_id == (sig.signal_id if hasattr(sig, 'signal_id') else getattr(sig, 'id', None))), None) if sig else None
            
            p_state = next((p for p in portfolio_states if p.timestamp <= trade.entry_fill.timestamp), None) if trade.entry_fill else None
            
            record = self.diary_builder.build_record(
                trade=trade,
                signal=sig,
                risk_decision=dec,
                state_at_entry=dec.strategy_state if dec else None,
                portfolio_at_entry=p_state
            )
            diary_records.append(record)
            
        # 2. Aggregations
        aggregator = ReportAggregator(portfolio_states=list(portfolio_states))
        daily = aggregator.aggregate_daily(diary_records)
        weekly = aggregator.aggregate_weekly(diary_records)
        monthly = aggregator.aggregate_monthly(diary_records)
        
        # 3. Export Data
        if self.config.formats.csv:
            self.exporter.export_trade_diary(diary_records)
            self.exporter.export_daily_reports(daily)
            self.exporter.export_weekly_reports(weekly)
            self.exporter.export_monthly_reports(monthly)
            
        if self.config.formats.markdown:
            self.exporter.export_markdown_summary(diary_records, daily, weekly, monthly)
            
        # 4. Generate Charts
        if self.chart_gen:
            self.chart_gen.generate_equity_curve(daily)
            # Individual trade charts require candles, which we don't pass explicitly here yet.
            # In a full run, we would inject candles for the chart generator.
            
        logger.info(f"Reporting complete for {self.run_id}. Outputs saved to {self.output_dir}")
