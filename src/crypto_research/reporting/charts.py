"""
Chart Generation for Prompt 06.
Provides visualizations for individual trades and portfolio summaries.
"""

from __future__ import annotations

import matplotlib
matplotlib.use("Agg") # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
from pathlib import Path

from crypto_research.reporting.models import TradeDiaryRecord, DailyReportRecord
from crypto_research.core.domain import Candle
from crypto_research.utils.logging import get_logger

logger = get_logger(__name__)

class ChartGenerator:
    """Generates analytical charts."""
    
    def __init__(self, output_dir: str | Path):
        self.output_dir = Path(output_dir)
        self.charts_dir = self.output_dir / "trade_charts"
        self.summary_dir = self.output_dir / "summaries"
        
        self.charts_dir.mkdir(parents=True, exist_ok=True)
        self.summary_dir.mkdir(parents=True, exist_ok=True)

    def generate_equity_curve(self, daily_reports: list[DailyReportRecord]) -> None:
        """Plot the equity curve from daily reports."""
        if not daily_reports:
            return
            
        dates = [pd.to_datetime(d.date) for d in daily_reports]
        equity = [d.ending_equity for d in daily_reports]
        
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(dates, equity, label="Equity", color="blue", linewidth=2)
        ax.set_title("Portfolio Equity Curve")
        ax.set_xlabel("Date")
        ax.set_ylabel("Equity (USDT)")
        ax.grid(True, alpha=0.3)
        ax.legend()
        
        # Format dates
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        fig.autofmt_xdate()
        
        path = self.summary_dir / "equity_curve.png"
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        logger.info(f"Generated equity curve: {path}")

    def generate_trade_chart(
        self,
        trade: TradeDiaryRecord,
        candles: list[Candle]
    ) -> None:
        """
        Plot an individual trade on a price chart.
        This represents a simplified visualization using matplotlib.
        """
        if not candles:
            return
            
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # Plot closing prices as a simple line for now
        # A more advanced version would use mplfinance for candlesticks
        times = [c.timestamp for c in candles]
        closes = [c.close for c in candles]
        
        ax.plot(times, closes, label=f"{trade.symbol} Price", color="black", alpha=0.6)
        
        # Mark Entry
        ax.scatter(trade.entry_timestamp, trade.entry_price, color="green" if trade.side=="LONG" else "red", 
                   marker="^" if trade.side=="LONG" else "v", s=150, label="Entry", zorder=5)
                   
        # Mark Exit
        ax.scatter(trade.final_exit_timestamp, trade.final_exit_price, color="blue", 
                   marker="x", s=150, label="Exit", zorder=5)
                   
        # Plot lines for Stop and Target if they exist within the visible range
        if trade.initial_stop_price > 0:
            ax.axhline(trade.initial_stop_price, color="red", linestyle="--", alpha=0.5, label="Initial Stop")
        if trade.target_price > 0:
            ax.axhline(trade.target_price, color="green", linestyle="--", alpha=0.5, label="Target")
            
        ax.set_title(f"Trade {trade.trade_id} | {trade.symbol} {trade.timeframe} | {trade.side} | PnL: {trade.net_pnl:.2f}")
        ax.set_ylabel("Price")
        ax.grid(True, alpha=0.3)
        ax.legend()
        
        # Create strategy specific subfolder
        strat_dir = self.charts_dir / trade.symbol / trade.timeframe / trade.strategy_id
        strat_dir.mkdir(parents=True, exist_ok=True)
        
        path = strat_dir / f"trade_{trade.trade_id}.png"
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
