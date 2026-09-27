"""
Data models for the reporting layer (Prompt 06).
These models preserve historical decisions and outcomes without modifying
the core execution engine's models.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class DecisionQuality(str, Enum):
    """Classification of how a trade decision was made."""
    VALID_DECISION = "VALID_DECISION"
    INVALID_DECISION = "INVALID_DECISION"
    INCOMPLETE_AUDIT = "INCOMPLETE_AUDIT"


@dataclass
class TradeDiaryRecord:
    """A comprehensive record of a single trade (decision + outcome)."""
    # Identifiers
    run_id: str
    trade_id: str
    strategy_id: str
    strategy_version: str
    symbol: str
    market_type: str
    timeframe: str
    
    # Timing & Execution
    side: str
    signal_timestamp: datetime
    entry_timestamp: datetime
    entry_price: float
    initial_stop_price: float
    target_price: float
    final_exit_timestamp: datetime
    final_exit_price: float
    
    # Sizing
    position_size: float
    notional_value: float
    risk_amount: float
    risk_pct: float
    
    # Economics
    configured_RR: float
    realized_R: float
    gross_pnl: float
    fees: float
    spread_cost: float
    slippage_cost: float
    total_cost: float
    net_pnl: float
    net_return_pct: float
    
    # Meta / Stats
    holding_duration_seconds: float
    maximum_adverse_excursion: Optional[float] = None
    maximum_favorable_excursion: Optional[float] = None
    
    # Decision Quality & State
    opportunity_score: Optional[float] = None
    opportunity_score_version: Optional[str] = None
    score_components: str = ""
    risk_decision: str = ""
    risk_rejection_reason: str = ""
    strategy_state_at_entry: str = ""
    daily_pnl_before_trade: Optional[float] = None
    daily_pnl_after_trade: Optional[float] = None
    consecutive_losses_before_trade: int = 0
    consecutive_losses_after_trade: int = 0
    
    # Outcome
    exit_reason: str = ""
    stop_hit: bool = False
    target_hit: bool = False
    decision_quality: DecisionQuality = DecisionQuality.VALID_DECISION
    decision_explanation: str = ""
    outcome_explanation: str = ""
    chart_path: str = ""

@dataclass
class DailyReportRecord:
    """Aggregated stats for a single UTC day."""
    date: str
    starting_equity: float
    ending_equity: float
    gross_pnl: float
    total_costs: float
    net_pnl: float
    net_return_pct: float
    
    executed_trades: int
    rejected_signals: int
    wins: int
    losses: int
    break_even: int
    win_rate: float
    
    average_R: float
    total_R: float
    average_winning_R: float
    average_losing_R: float
    largest_win: float
    largest_loss: float
    max_drawdown: float
    
    average_holding_duration: float
    strategy_count: int
    asset_count: int
    timeframe_count: int

@dataclass
class WeeklyReportRecord:
    """Aggregated stats for a calendar week."""
    period: str
    starting_equity: float
    ending_equity: float
    net_pnl: float
    net_return_pct: float
    total_trades: int
    wins: int
    losses: int
    average_R: float
    total_R: float
    max_drawdown: float
    average_holding_time: float
    total_costs: float
    rejected_opportunities: int

@dataclass
class MonthlyReportRecord:
    """Aggregated stats for a calendar month."""
    period: str
    starting_equity: float
    ending_equity: float
    net_pnl: float
    net_return_pct: float
    total_trades: int
    wins: int
    losses: int
    average_R: float
    total_R: float
    max_drawdown: float
    total_costs: float
    average_holding_duration: float
    active_trading_days: int
    zero_trade_days: int

@dataclass
class RejectionSummaryRecord:
    rejection_code: str
    count: int
    percentage: float
    strategy: str
    asset: str
    timeframe: str
