"""
Paper Trading Engine — Prompt 08.

The PaperEngine orchestrates the paper trading event loop.

CRITICAL DESIGN CONSTRAINT:
    This engine does NOT implement strategy logic, risk logic, or execution
    logic. It reuses — exactly as-is — the following existing components:

    - ExecutionSimulator  (backtest/execution_simulator.py)  — fills, costs
    - CostModel           (backtest/cost_model.py)           — fees/spread/slippage
    - PositionSizer       (backtest/position_sizer.py)       — sizing
    - RiskGate            (backtest/risk_gate.py)            — daily limits, exposure
    - PortfolioAccountant (backtest/portfolio_accountant.py) — equity/balance

The paper engine is a thin orchestration shell — NOT a parallel implementation.

Event loop:
    1. Poll market data (PaperMarketDataProvider)
    2. Validate each new candle
    3. Deliver only CLOSED candles to strategies (PIT rule)
    4. Check stop/target hits on open positions (ExecutionSimulator)
    5. Execute pending entries from previous tick
    6. Call strategy.on_candle()
    7. Run opportunity score + risk gate
    8. Create paper order + queue entry for NEXT candle
    9. Write audit rows
    10. Checkpoint if interval elapsed
    11. Emit heartbeat if interval elapsed
    12. Sleep until next poll

PIT guarantee:
    Strategy receives candle only after close_time < utcnow().
    No future candle is ever delivered.

Duplicate guarantee:
    Data provider deduplicates by open_time. Engine never double-signals.
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import Optional

from crypto_research.backtest.cost_model import CostModel
from crypto_research.backtest.execution_simulator import ExecutionSimulator
from crypto_research.backtest.portfolio_accountant import PortfolioAccountant
from crypto_research.backtest.position_sizer import PositionSizer
from crypto_research.backtest.risk_gate import RiskGate
from crypto_research.config.schema import ProjectConfiguration
from crypto_research.core.domain import (
    Candle,
    ExecutionMode,
    ExitReason,
    Fill,
    GapPolicy,
    IntrabarFillPolicy,
    Order,
    OrderSide,
    OrderStatus,
    OrderType,
    PaperAuditEventType,
    PaperSessionState,
    Position,
    PositionSide,
    Timeframe,
    Trade,
)
from crypto_research.core.exceptions import ConfigurationError
from crypto_research.paper.audit_writer import PaperAuditWriter
from crypto_research.paper.checkpoint import PaperCheckpoint
from crypto_research.paper.data_provider import PaperMarketDataProvider
from crypto_research.paper.drift_monitor import PaperDriftMonitor
from crypto_research.paper.heartbeat import PaperHeartbeat
from crypto_research.paper.safety import PaperSafetyGuard
from crypto_research.paper.session import (
    MANUAL_STOP, SCHEDULED_STOP, STATE_ERROR, UNEXPECTED_ERROR,
    PaperTradingSession,
)
from crypto_research.paper.session_report import PaperSessionReportWriter
from crypto_research.utils.logging import get_logger

logger = get_logger(__name__)


class PaperEngine:
    """
    Paper trading event loop orchestrator.

    Uses the same execution and risk components as BacktestEngine.
    Does NOT duplicate any business logic.

    Usage:
        engine = PaperEngine(config, strategy, run_id)
        session = engine.run(max_duration_minutes=30)
    """

    def __init__(
        self,
        config: ProjectConfiguration,
        strategy,
        run_id: str,
        session_id: str | None = None,
    ) -> None:
        self._config = config
        self._strategy = strategy
        self._run_id = run_id

        pt_cfg = config.paper_trading

        # ── Safety guard — checked FIRST ─────────────────────────────────────
        guard = PaperSafetyGuard(pt_cfg)
        guard.validate(ExecutionMode.PAPER)

        # ── Session ──────────────────────────────────────────────────────────
        self.session = PaperTradingSession(config, run_id, session_id)

        # Session directory
        session_dir = f"{pt_cfg.persistence.results_dir}/{self.session.session_id}"

        # ── Infrastructure ───────────────────────────────────────────────────
        self._audit = PaperAuditWriter(session_dir, self.session.session_id)
        self._checkpoint = PaperCheckpoint(session_dir)
        self._report_writer = PaperSessionReportWriter(session_dir)

        # ── Reuse backtest execution components (no duplication) ─────────────
        cost_cfg = config.costs
        exec_cfg = config.execution
        self._cost_model = CostModel(
            maker_fee_rate=cost_cfg.maker_fee_rate,
            taker_fee_rate=cost_cfg.taker_fee_rate,
            slippage_bps=exec_cfg.slippage_bps,
            spread_bps=exec_cfg.spread_bps,
        )
        self._simulator = ExecutionSimulator(
            cost_model=self._cost_model,
            intrabar_policy=IntrabarFillPolicy.STOP_FIRST,
            gap_policy=GapPolicy.FILL_AT_OPEN,
        )
        self._sizer = PositionSizer()
        self._accountant = PortfolioAccountant(
            initial_balance=pt_cfg.initial_balance,
        )
        self._risk_gate = RiskGate(config)

        # ── Paper data provider ──────────────────────────────────────────────
        self._data_provider = PaperMarketDataProvider(
            config=pt_cfg.market_data,
            symbols=config.assets,
            timeframes=config.timeframes,
        )

        # ── Monitoring ───────────────────────────────────────────────────────
        self._heartbeat = PaperHeartbeat(self.session, interval_seconds=60)
        self._drift_monitor = PaperDriftMonitor(pt_cfg.drift)
        self._drift_warnings: list = []

        # ── State ────────────────────────────────────────────────────────────
        # Pending entry: asset → (order, signal_candle_ts)
        # Entry executes at NEXT candle open (same PIT rule as BacktestEngine)
        self._pending_entry: dict[str, tuple[Order, datetime]] = {}

        # Open positions by position_id
        self._open_positions: dict[str, Position] = {}

        # Rejection summary for final report
        self._rejection_summary: dict[str, int] = {}

        self._stop_requested = False

        logger.info(
            "PaperEngine initialized",
            session_id=self.session.session_id,
            run_id=run_id,
            symbols=config.assets,
            timeframes=config.timeframes,
            initial_balance=pt_cfg.initial_balance,
            execution_mode=ExecutionMode.PAPER.value,
        )

    # ─── Public API ─────────────────────────────────────────────────────────────

    def run(self, max_duration_minutes: float | None = None) -> PaperTradingSession:
        """
        Start the paper trading event loop and block until complete.

        Returns:
            The completed PaperTradingSession.
        """
        try:
            self._initialize()
            self._loop(max_duration_minutes)
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt — stopping paper session")
            self.stop(MANUAL_STOP)
        except Exception as exc:
            logger.exception("Unexpected error in paper engine", error=str(exc))
            self.session.mark_failed(f"{UNEXPECTED_ERROR}: {exc}")
        finally:
            self._shutdown()
        return self.session

    def stop(self, reason: str = MANUAL_STOP) -> None:
        """Request a clean stop of the event loop."""
        self._stop_requested = True
        self.session.request_stop(reason)

    # ─── Lifecycle ───────────────────────────────────────────────────────────────

    def _initialize(self) -> None:
        self.session.transition_to(PaperSessionState.INITIALIZING, "Loading data provider")

        # Load warmup candles and feed to strategy (no signals generated)
        warmup = self._data_provider.initialize(
            warmup_candles=self._config.paper_trading.market_data.warmup_candles
        )
        for (symbol, tf_str), candles in warmup.items():
            for candle in candles:
                try:
                    self._strategy.on_candle(
                        close_price=candle.close,
                        symbol=symbol,
                        timeframe=tf_str,
                        timestamp=candle.timestamp,
                    )
                except Exception:
                    pass  # Non-fatal during warmup

        # Write config snapshot
        try:
            import yaml
            self._audit.write_config_snapshot(
                yaml.dump(self._config.model_dump(), default_flow_style=False)
            )
        except Exception:
            pass

        self._audit.write_session_metadata(self.session.to_metadata_dict())
        self._audit.write_market_event(
            PaperAuditEventType.SESSION_START,
            detail=f"session_id={self.session.session_id}",
        )
        self.session.start()

    def _loop(self, max_duration_minutes: float | None) -> None:
        poll_interval = self._config.paper_trading.market_data.poll_interval_seconds
        checkpoint_interval = self._config.paper_trading.persistence.checkpoint_interval_seconds
        last_checkpoint = datetime.now(timezone.utc)

        while not self._stop_requested:
            # Duration limit check
            if max_duration_minutes and self.session.uptime_seconds() > max_duration_minutes * 60:
                logger.info("Maximum session duration reached")
                self.stop(SCHEDULED_STOP)
                break

            # Poll for new closed candles
            try:
                new_candles_by_key = self._data_provider.poll()
                gaps = self._data_provider.consume_gaps()
                self.session.counters.data_gaps += len(gaps)

                for (symbol, tf_str), candles in new_candles_by_key.items():
                    for candle in candles:
                        self._process_candle(candle, symbol, tf_str)

            except Exception as exc:
                logger.error("Error in poll cycle", error=str(exc))
                self.session.counters.errors += 1
                if self.session.counters.errors > 50:
                    self.session.mark_failed(f"{STATE_ERROR}: Too many errors")
                    return

            # Heartbeat
            if self._heartbeat.should_emit():
                self._heartbeat.emit(self._audit)

            # Checkpoint
            now = datetime.now(timezone.utc)
            if (now - last_checkpoint).total_seconds() >= checkpoint_interval:
                self._save_checkpoint()
                last_checkpoint = now

            # Drift check
            if self.session.counters.trades_completed >= 5:
                paper_metrics = self._build_paper_metrics()
                new_warnings = self._drift_monitor.check(
                    paper_metrics,
                    min_trades=self.session.counters.trades_completed,
                )
                self._drift_warnings.extend(new_warnings)
                self.session.counters.warnings += len(new_warnings)

            time.sleep(poll_interval)

    def _process_candle(self, candle: Candle, symbol: str, tf_str: str) -> None:
        """Process one newly closed candle through the full pipeline."""
        self.session.counters.candles_processed += 1
        self.session.counters.market_events_received += 1
        self._audit.write_market_event(PaperAuditEventType.CANDLE_CLOSED, candle=candle)

        # ── Update position prices ────────────────────────────────────────────
        for pos in list(self._open_positions.values()):
            if pos.asset == symbol:
                pos.current_price = candle.close
        self.session.update_unrealized_pnl()

        # ── Check stop/target on open positions ───────────────────────────────
        for pos in list(self._open_positions.values()):
            if pos.asset != symbol:
                continue
            exit_fill, exit_reason = self._simulator.check_and_simulate_exits(
                position=pos,
                candle_open=candle.open,
                candle_high=candle.high,
                candle_low=candle.low,
                candle_close=candle.close,
                candle_timestamp=candle.timestamp,
                run_id=self._run_id,
            )
            if exit_fill is not None and exit_reason is not None:
                self._close_position(pos, exit_fill, exit_reason)

        # ── Execute pending entry (from previous candle signal) ───────────────
        pending = self._pending_entry.pop(symbol, None)
        if pending is not None:
            order, signal_ts = pending
            tf_enum = Timeframe.from_string(tf_str)
            entry_fill = self._simulator.simulate_market_entry(
                order_id=order.order_id,
                timestamp=candle.timestamp,
                symbol=symbol,
                side=PositionSide.LONG if order.side == OrderSide.BUY else PositionSide.SHORT,
                quantity=order.quantity,
                candle_open=candle.open,
            )
            pos = Position.create(
                asset=symbol,
                side=PositionSide.LONG if order.side == OrderSide.BUY else PositionSide.SHORT,
                entry_fill=entry_fill,
                strategy_name=order.strategy_name,
                run_id=self._run_id,
                timeframe=tf_enum,
                stop_price=order.stop_price,
                target_price=order.target_price,
            )
            self._open_positions[pos.position_id] = pos
            self.session.open_positions[pos.position_id] = pos
            self.session.counters.positions_opened += 1
            self.session.counters.fills_executed += 1
            self._audit.write_fill(entry_fill)
            self._audit.write_position_snapshot(pos, "OPENED")

        # ── Strategy signal ───────────────────────────────────────────────────
        try:
            signal = self._strategy.on_candle(
                close_price=candle.close,
                symbol=symbol,
                timeframe=tf_str,
                timestamp=candle.timestamp,
            )
        except Exception as exc:
            logger.error("Strategy error", symbol=symbol, error=str(exc))
            self.session.counters.errors += 1
            return

        if signal is None:
            return

        self.session.counters.signals_generated += 1
        self._audit.write_signal(signal)

        # Skip: already have open position in this asset
        if any(p.asset == symbol for p in self._open_positions.values()):
            self._record_rejection("ALREADY_HAVE_POSITION")
            return

        # ── Opportunity score ─────────────────────────────────────────────────
        if self._config.risk.opportunity_score.enabled:
            from crypto_research.portfolio.opportunity_scorer import OpportunityScorer
            scorer = OpportunityScorer(self._config.risk.opportunity_score)
            score = scorer.score(signal)
            self._audit.write_signal(signal, score=score)
            if score < self._config.risk.opportunity_score.minimum_score:
                self._record_rejection("LOW_SCORE")
                self.session.counters.signals_rejected += 1
                return
        else:
            score = None

        # ── Risk gate ─────────────────────────────────────────────────────────
        open_pos_list = list(self._open_positions.values())
        risk_decision = self._risk_gate.evaluate(
            signal=signal,
            open_positions=open_pos_list,
            accountant=self._accountant,
            timestamp=candle.timestamp,
        )
        self._audit.write_risk_decision(risk_decision)

        if not risk_decision.approved:
            reason = (
                risk_decision.rejection_reason.value
                if risk_decision.rejection_reason else "UNKNOWN"
            )
            self._record_rejection(reason)
            self.session.counters.signals_rejected += 1
            return

        self.session.counters.signals_accepted += 1

        # ── Position sizing ───────────────────────────────────────────────────
        quantity = self._sizer.calculate(
            signal=signal,
            entry_price=candle.close,
            capital=self._accountant.current_balance,
            config=self._config,
        )
        if quantity <= 0:
            self._record_rejection("INSUFFICIENT_CAPITAL")
            return

        # ── Create paper order ────────────────────────────────────────────────
        tf_enum = Timeframe.from_string(tf_str)
        order = Order.create(
            timestamp=candle.timestamp,
            asset=symbol,
            side=OrderSide.BUY if getattr(signal, "direction", None) and
                 signal.direction.value == "long" else OrderSide.SELL,
            order_type=OrderType.MARKET,
            quantity=quantity,
            strategy_name=getattr(signal, "strategy_id", "unknown"),
            run_id=self._run_id,
            timeframe=tf_enum,
            stop_price=getattr(signal, "stop_price", None),
            target_price=getattr(signal, "target_price", None),
        )
        self.session.counters.orders_created += 1
        self._audit.write_order(order)

        # Queue for NEXT candle open — same PIT rule as BacktestEngine
        self._pending_entry[symbol] = (order, candle.timestamp)

    # ─── Position management ─────────────────────────────────────────────────────

    def _close_position(
        self, position: Position, exit_fill: Fill, exit_reason: ExitReason
    ) -> None:
        """Close a position, build the Trade record, update accounting."""
        entry_fill = position.entry_fill
        gross = self._compute_gross_pnl(position, exit_fill.fill_price)
        costs = exit_fill.fees + exit_fill.slippage + exit_fill.spread_cost
        net = gross - costs
        risk_amount = position.risk_amount
        r_multiple = (net / risk_amount) if risk_amount and risk_amount > 0 else None
        duration = (exit_fill.timestamp - entry_fill.timestamp).total_seconds()

        trade = Trade.create(
            asset=position.asset,
            side=position.side,
            entry_fill=entry_fill,
            exit_fill=exit_fill,
            strategy_name=position.strategy_name,
            run_id=self._run_id,
            exit_reason=exit_reason.value if hasattr(exit_reason, "value") else str(exit_reason),
            gross_pnl=gross,
            fees=entry_fill.fees + exit_fill.fees,
            slippage_cost=entry_fill.slippage + exit_fill.slippage,
            spread_cost=entry_fill.spread_cost + exit_fill.spread_cost,
            net_pnl=net,
            timeframe=position.timeframe,
            initial_stop=position.initial_stop,
            target_price=position.target_price,
            risk_amount=risk_amount,
            r_multiple=r_multiple,
            holding_duration_seconds=duration,
        )

        self._open_positions.pop(position.position_id, None)
        self.session.open_positions.pop(position.position_id, None)
        self.session.record_trade_closed(trade)
        self.session.counters.positions_closed += 1

        self._audit.write_fill(exit_fill)
        self._audit.write_position_snapshot(position, "CLOSED")
        self._audit.write_trade(trade)

        logger.info(
            "Paper trade closed",
            asset=trade.asset,
            net_pnl=round(trade.net_pnl, 4),
            r_multiple=round(r_multiple, 4) if r_multiple else None,
            exit_reason=exit_reason,
            execution_mode=ExecutionMode.PAPER.value,
        )

    def _compute_gross_pnl(self, position: Position, exit_price: float) -> float:
        if position.side == PositionSide.LONG:
            return (exit_price - position.entry_price) * position.quantity
        return (position.entry_price - exit_price) * position.quantity

    # ─── Shutdown ────────────────────────────────────────────────────────────────

    def _shutdown(self) -> None:
        logger.info("Paper engine shutting down", session_id=self.session.session_id)
        self._save_checkpoint()
        self._audit.write_session_metadata(self.session.to_metadata_dict())
        self._audit.write_market_event(
            PaperAuditEventType.SESSION_STOP,
            detail=f"reason={self.session.shutdown_reason}",
        )
        self._report_writer.write(
            session=self.session,
            drift_warnings=self._drift_warnings,
            rejection_summary=self._rejection_summary,
        )
        self._data_provider.close()

        if self.session.state == PaperSessionState.STOPPING:
            self.session.mark_stopped()

    def _save_checkpoint(self) -> None:
        try:
            self._checkpoint.save(self.session)
        except Exception as e:
            logger.error("Checkpoint save failed", error=str(e))

    def _record_rejection(self, reason: str) -> None:
        self._rejection_summary[reason] = self._rejection_summary.get(reason, 0) + 1

    def _build_paper_metrics(self) -> dict:
        uptime_hours = self.session.uptime_seconds() / 3600 or 1
        cnt = self.session.counters
        trades = cnt.trades_completed
        return {
            "signals_per_hour": cnt.signals_generated / uptime_hours,
            "mean_score": 0.0,
            "rejection_rate": cnt.signals_rejected / max(cnt.signals_generated, 1),
            "avg_cost_per_trade": self.session.accounting.total_fees / max(trades, 1),
        }
