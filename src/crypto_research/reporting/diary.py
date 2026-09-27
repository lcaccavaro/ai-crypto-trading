"""
Trade Diary Generation for Prompt 06.
Constructs enriched trade records and decision explanations.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Optional

from crypto_research.core.domain import (
    Trade, Signal, RiskDecisionRecord, StrategyState, PortfolioState
)
from crypto_research.reporting.models import TradeDiaryRecord, DecisionQuality
from crypto_research.utils.logging import get_logger

logger = get_logger(__name__)

class TradeDiaryBuilder:
    """Builds structured diary records from execution results."""
    
    def __init__(self, run_id: str):
        self.run_id = run_id

    def build_record(
        self,
        trade: Trade,
        signal: Optional[Signal] = None,
        risk_decision: Optional[RiskDecisionRecord] = None,
        state_at_entry: Optional[StrategyState] = None,
        portfolio_at_entry: Optional[PortfolioState] = None,
    ) -> TradeDiaryRecord:
        """
        Merge core engine artifacts into a single TradeDiaryRecord.
        Answers: What happened, why was it taken, what was the outcome?
        """
        
        # Calculate Risk and R
        risk_amount = 0.0
        risk_pct = 0.0
        realized_R = 0.0
        configured_RR = 0.0
        
        if risk_decision and risk_decision.risk_budget:
            risk_amount = risk_decision.risk_budget
            if portfolio_at_entry and portfolio_at_entry.equity > 0:
                risk_pct = (risk_amount / portfolio_at_entry.equity) * 100.0
            
            if risk_amount > 0:
                realized_R = trade.net_pnl / risk_amount
                
        # Basic Trade Stats
        holding_duration = 0.0
        if trade.entry_fill and trade.exit_fill:
            delta = trade.exit_fill.timestamp - trade.entry_fill.timestamp
            holding_duration = delta.total_seconds()
            
        # Explanations
        decision_exp = self._generate_decision_explanation(signal, risk_decision)
        outcome_exp = self._generate_outcome_explanation(trade)
        
        # Decision Quality
        dq = self._evaluate_decision_quality(trade, signal, risk_decision)
        
        return TradeDiaryRecord(
            run_id=self.run_id,
            trade_id=trade.trade_id,
            strategy_id=trade.strategy_name,
            strategy_version=risk_decision.strategy_version if risk_decision else "unknown",
            symbol=trade.asset,
            market_type="futures", # Default for prompt 03/06 context
            timeframe=trade.timeframe.value if trade.timeframe else "unknown",
            side=trade.side.value,
            
            signal_timestamp=signal.timestamp if signal else trade.entry_fill.timestamp if trade.entry_fill else datetime.min,
            entry_timestamp=trade.entry_fill.timestamp if trade.entry_fill else datetime.min,
            entry_price=trade.entry_fill.fill_price if trade.entry_fill else 0.0,
            initial_stop_price=signal.stop_price if signal and signal.stop_price else 0.0,
            target_price=signal.target_price if signal and signal.target_price else 0.0,
            final_exit_timestamp=trade.exit_fill.timestamp if trade.exit_fill else datetime.min,
            final_exit_price=trade.exit_fill.fill_price if trade.exit_fill else 0.0,
            
            position_size=trade.entry_fill.quantity if trade.entry_fill else 0.0,
            notional_value=(trade.entry_fill.fill_price * trade.entry_fill.quantity) if trade.entry_fill else 0.0,
            risk_amount=risk_amount,
            risk_pct=risk_pct,
            configured_RR=configured_RR,
            realized_R=realized_R,
            
            gross_pnl=trade.gross_pnl,
            fees=trade.fees,
            spread_cost=trade.spread_cost,
            slippage_cost=trade.slippage_cost,
            total_cost=trade.fees + trade.spread_cost + trade.slippage_cost,
            net_pnl=trade.net_pnl,
            net_return_pct=(trade.net_pnl / portfolio_at_entry.equity * 100.0) if portfolio_at_entry and portfolio_at_entry.equity > 0 else 0.0,
            
            holding_duration_seconds=holding_duration,
            opportunity_score=risk_decision.score if risk_decision else None,
            opportunity_score_version=risk_decision.score_version if risk_decision else None,
            score_components="", # Not deeply tracked yet
            risk_decision=risk_decision.decision.value if risk_decision else "UNKNOWN",
            risk_rejection_reason=risk_decision.primary_reason if risk_decision else "",
            
            strategy_state_at_entry=risk_decision.strategy_state.value if risk_decision else "ACTIVE",
            daily_pnl_before_trade=portfolio_at_entry.daily_pnl if portfolio_at_entry else None,
            daily_pnl_after_trade=None, # Computed in aggregation
            
            exit_reason=trade.exit_reason,
            stop_hit=(trade.exit_reason == "STOP"),
            target_hit=(trade.exit_reason == "TARGET"),
            
            decision_quality=dq,
            decision_explanation=decision_exp,
            outcome_explanation=outcome_exp,
        )

    def _generate_decision_explanation(self, signal: Optional[Signal], risk_decision: Optional[RiskDecisionRecord]) -> str:
        """What was known when the trade was entered."""
        if not signal or not risk_decision:
            return "Missing signal or risk decision audit data."
            
        return (
            f"Strategy '{signal.strategy_name}' generated {signal.direction.value} signal on {signal.asset} {signal.timeframe}. "
            f"Opportunity score was {risk_decision.score}/100. "
            f"Risk manager approved trade: {risk_decision.primary_reason}."
        )
        
    def _generate_outcome_explanation(self, trade: Trade) -> str:
        """What happened after entry."""
        if trade.exit_reason == "STOP":
            return "Stop loss level was reached and trade was exited."
        elif trade.exit_reason == "TARGET":
            return "Profit target level was reached and trade was exited."
        elif trade.exit_reason == "EOD":
            return "Trade exited due to end-of-day condition."
        else:
            return f"Trade exited for reason: {trade.exit_reason}."

    def _evaluate_decision_quality(self, trade: Trade, signal: Optional[Signal], risk_decision: Optional[RiskDecisionRecord]) -> DecisionQuality:
        """Did the decision follow the rules available at the time?"""
        if not signal or not risk_decision:
            return DecisionQuality.INCOMPLETE_AUDIT
            
        if str(risk_decision.decision.value).upper() != "ACCEPTED":
            return DecisionQuality.INVALID_DECISION
            
        if not signal.stop_price or not signal.target_price:
            return DecisionQuality.INVALID_DECISION
            
        return DecisionQuality.VALID_DECISION
