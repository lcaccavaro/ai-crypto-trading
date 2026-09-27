"""
Portfolio Orchestrator.

The core decision layer of Prompt 05. Coordinates all strategy signals through
a deterministic evaluation flow:
1. Strategy State check
2. Opportunity Score check
3. Portfolio Risk Gate check (daily limits, exposure, capital)
4. Position Sizing

Records all decisions in a DecisionLedger.
"""

from __future__ import annotations

from datetime import datetime

from crypto_research.backtest.position_sizer import PositionSizer
from crypto_research.backtest.risk_gate import RiskGate
from crypto_research.config.schema import ProjectConfiguration
from crypto_research.core.domain import (
    Candle,
    DecisionOutcome,
    OrderSide,
    PortfolioState,
    PositionSide,
    RejectionReason,
    RiskDecision,
    RiskDecisionRecord,
    Signal,
    SignalDirection,
    StrategyLifecycleState,
)
from crypto_research.portfolio.decision_ledger import DecisionLedger
from crypto_research.portfolio.opportunity_scorer import OpportunityScorer
from crypto_research.portfolio.portfolio_state_manager import PortfolioStateManager
from crypto_research.portfolio.strategy_state_ledger import StrategyStateLedger
from crypto_research.portfolio.strategy_state_machine import StrategyStateMachine
from crypto_research.strategies.context import StrategyInstance
from crypto_research.utils.logging import get_logger

logger = get_logger(__name__)


class PortfolioOrchestrator:
    """
    Evaluates incoming strategy signals against portfolio constraints and strategy states.
    """

    def __init__(
        self,
        run_id: str,
        config: ProjectConfiguration,
        state_manager: PortfolioStateManager,
        risk_gate: RiskGate,
        position_sizer: PositionSizer,
        strategy_machines: dict[str, StrategyStateMachine],
    ) -> None:
        self.run_id = run_id
        self._config = config
        self._state_manager = state_manager
        self._risk_gate = risk_gate
        self._position_sizer = position_sizer
        self._strategy_machines = strategy_machines

        self._scorer = OpportunityScorer(config.risk.opportunity_score)
        
        self.decision_ledger = DecisionLedger(run_id)
        self.state_ledger = StrategyStateLedger(run_id)

    def evaluate_signal(
        self,
        signal: Signal,
        instance: StrategyInstance,
        candles: list[Candle],
        open_positions: list,  # list[Position] — avoid circular import
        entry_price: float,
    ) -> RiskDecision:
        """
        Evaluate a signal through the complete risk and orchestration pipeline.

        Args:
            signal: The strategy signal to evaluate.
            instance: The strategy instance generating the signal.
            candles: Recent candles for scoring (PIT: all candles must be <= signal.timestamp).
            open_positions: Current open positions in the portfolio (used for exposure checks).
            entry_price: The expected execution entry price (usually next open).

        Returns:
            RiskDecision: Approved or rejected, with reasons and sizing.
        """
        rejections: list[RejectionReason] = []

        # 0. Get current portfolio state with real open positions for accurate exposure tracking.
        # This is critical: passing open_positions ensures asset_exposures and strategy_exposures
        # are populated correctly before the exposure limit checks.
        portfolio_state = self._state_manager.update_from_positions(
            signal.timestamp, open_positions
        )
        open_position_count = len(open_positions)

        # Determine strategy state machine
        machine = self._strategy_machines.get(instance.instance_id)
        if machine:
            # Check cooldown expiry before evaluating
            new_state_snapshot = machine.check_cooldown(signal.timestamp)
            if new_state_snapshot:
                self.state_ledger.record(new_state_snapshot)
                logger.info(f"Strategy {instance.instance_id} cooldown expired.")
                
            state_str = machine.current_state.value
            consecutive_losses = machine.consecutive_losses
        else:
            state_str = StrategyLifecycleState.ACTIVE.value
            consecutive_losses = 0

        # Convert SignalDirection to PositionSide
        if signal.direction == SignalDirection.NEUTRAL:
            # Neutral signals are technically not entry signals, should not arrive here for sizing.
            return self._reject_and_record(signal, instance, portfolio_state, 
                                           [RejectionReason.INVALID_ORDER], consecutive_losses, state_str)

        side = PositionSide.LONG if signal.direction == SignalDirection.LONG else PositionSide.SHORT
        
        # 1. Opportunity Score
        score_obj = self._scorer.score(signal, instance.instance_id, candles)
        score_val = score_obj.total_score
        
        # 2. Pre-sizing RiskGate (Extended)
        # Since quantity is not yet known, we check limits with a nominal 0 notional first,
        # but wait, max total exposure and max asset exposure need the new notional.
        # We need a risk budget first.
        
        # 3. Position Sizing
        if not signal.stop_price:
            rejections.append(RejectionReason.INVALID_STOP)
            return self._reject_and_record(signal, instance, portfolio_state, rejections, consecutive_losses, state_str, score_val)

        try:
            quantity = self._position_sizer.size_risk_based(
                equity=portfolio_state.equity,
                risk_per_trade_pct=self._config.risk.risk_per_trade_pct,
                entry_price=entry_price,
                stop_price=signal.stop_price,
                available_capital=portfolio_state.available_capital,
            )
        except Exception as e:
            logger.info("Order rejected: sizing failed", error=str(e))
            rejections.append(RejectionReason.INVALID_RISK)
            return self._reject_and_record(signal, instance, portfolio_state, rejections, consecutive_losses, state_str, score_val)

        # 4. Full Extended RiskGate Check
        asset_notional = portfolio_state.asset_exposures.get(signal.asset, 0.0)
        strategy_notional = portfolio_state.strategy_exposures.get(instance.strategy_id, 0.0)

        ok, gate_rejections = self._risk_gate.check_all_extended(
            side=side,
            portfolio_state=portfolio_state,
            symbol=signal.asset,
            entry_price=entry_price,
            quantity=quantity,
            open_position_count=open_position_count,
            asset_notional=asset_notional,
            strategy_notional=strategy_notional,
            strategy_state_str=state_str,
            score=score_val,
        )
        
        if not ok:
            return self._reject_and_record(signal, instance, portfolio_state, gate_rejections, consecutive_losses, state_str, score_val, quantity=quantity)

        # 5. Accepted
        risk_budget = self._position_sizer.compute_risk_amount(quantity, entry_price, signal.stop_price)
        
        decision_rec = RiskDecisionRecord(
            timestamp=signal.timestamp,
            run_id=self.run_id,
            strategy_id=instance.strategy_id,
            strategy_version=instance.version,
            instance_id=instance.instance_id,
            symbol=signal.asset,
            timeframe=signal.timeframe,
            signal=signal.direction,
            score=score_val,
            score_version=self._config.risk.opportunity_score.version,
            risk_budget=risk_budget,
            approved_quantity=quantity,
            portfolio_equity=portfolio_state.equity,
            daily_return_pct=portfolio_state.daily_pnl / max(portfolio_state.daily_start_equity, 1e-6) * 100.0,
            consecutive_losses=consecutive_losses,
            strategy_state=StrategyLifecycleState(state_str),
            decision=DecisionOutcome.ACCEPTED,
            primary_reason="ALL_CHECKS_PASSED",
            rejection_reasons=[],
        )
        self.decision_ledger.record(decision_rec)

        return RiskDecision(
            approved=True,
            reason="ALL_CHECKS_PASSED",
            max_position_size=quantity,
            risk_amount=risk_budget,
            rejection_codes=[],
            score=score_val,
            score_version=self._config.risk.opportunity_score.version,
            approved_quantity=quantity,
        )

    def _reject_and_record(
        self,
        signal: Signal,
        instance: StrategyInstance,
        portfolio_state: PortfolioState,
        rejections: list[RejectionReason],
        consecutive_losses: int,
        state_str: str,
        score_val: float | None = None,
        quantity: float | None = None,
    ) -> RiskDecision:
        primary_reason = rejections[0].value if rejections else "UNKNOWN_REJECTION"
        
        decision_rec = RiskDecisionRecord(
            timestamp=signal.timestamp,
            run_id=self.run_id,
            strategy_id=instance.strategy_id,
            strategy_version=instance.version,
            instance_id=instance.instance_id,
            symbol=signal.asset,
            timeframe=signal.timeframe,
            signal=signal.direction,
            score=score_val,
            score_version=self._config.risk.opportunity_score.version,
            risk_budget=None,
            approved_quantity=None,
            portfolio_equity=portfolio_state.equity,
            daily_return_pct=portfolio_state.daily_pnl / max(portfolio_state.daily_start_equity, 1e-6) * 100.0,
            consecutive_losses=consecutive_losses,
            strategy_state=StrategyLifecycleState(state_str),
            decision=DecisionOutcome.REJECTED,
            primary_reason=primary_reason,
            rejection_reasons=rejections,
        )
        self.decision_ledger.record(decision_rec)

        return RiskDecision(
            approved=False,
            reason=primary_reason,
            max_position_size=None,
            risk_amount=None,
            rejection_codes=rejections,
            score=score_val,
            score_version=self._config.risk.opportunity_score.version,
            approved_quantity=None,
        )
