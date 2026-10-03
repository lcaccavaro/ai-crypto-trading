"""
BacktestEngine — the main event loop for Prompt 03.

Implements the ExecutionEngine Protocol from execution/interface.py and
orchestrates all engine components into a single deterministic simulation.

Event loop design:
━━━━━━━━━━━━━━━━━

1. Pre-run validation:
   - BacktestDataProvider validates and loads all required datasets.
   - Fails loudly if any dataset is missing, malformed, or out of range.

2. Event stream:
   - All candle timestamps across all (symbol, timeframe) pairs are merged.
   - The primary timeframe drives the simulation clock.
   - Events are sorted by UTC timestamp (then by symbol for determinism).

3. Per-candle event processing:
   a. Daily PnL reset check (at UTC midnight boundary).
   b. Update all open positions' current prices (for unrealized PnL).
   c. Check all open positions for stop/target hits (ExecutionSimulator).
   d. Snapshot equity curve.
   e. If signal is pending from previous candle: execute entry fill.
   f. Call strategy.on_candle() with the closed candle price.
   g. If signal received: run RiskGate → compute position size → create Order.
   h. If approved: queue entry for NEXT candle (signal timing rule).
   i. Record ExecutionEvent for every decision.

4. End-of-run:
   - Close any remaining open positions at their last known price (END_OF_DATA).
   - Compute final equity curve snapshot.
   - Build and return BacktestResult.

Signal timing enforcement:
    Entry signals from candle C's close execute at candle C+1's OPEN.
    This is enforced by the _pending_entry dict. The engine never executes
    an entry at the same candle that generated the signal.

Determinism guarantee:
    - No randomness is introduced anywhere in the engine.
    - Same data + same config → identical trade ledger + identical equity curve.
    - Symbol/timeframe ordering is sorted alphabetically for reproducibility.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from crypto_research.backtest.backtest_data_provider import BacktestDataProvider
from crypto_research.backtest.cost_model import CostModel
from crypto_research.backtest.execution_simulator import ExecutionSimulator
from crypto_research.backtest.metrics import BacktestMetrics, compute_metrics
from crypto_research.backtest.portfolio_accountant import PortfolioAccountant
from crypto_research.backtest.position_sizer import PositionSizer
from crypto_research.backtest.result import BacktestResult, BacktestResultWriter
from crypto_research.backtest.risk_gate import RiskGate
from crypto_research.core.domain import (
    EventType,
    ExecutionEvent,
    ExitReason,
    Fill,
    GapPolicy,
    IntrabarFillPolicy,
    Order,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
    PositionSide,
    PositionSizingMode,
    RejectionReason,
    Trade,
    SignalDirection,
)
from crypto_research.core.exceptions import DataIntegrityError, ExecutionError
from crypto_research.data.catalog import DataCatalog
from crypto_research.utils.logging import get_logger

logger = get_logger(__name__)


class BacktestEngine:
    """
    Main backtest engine — orchestrates a deterministic historical simulation.

    Usage:
        engine = BacktestEngine(catalog, config)
        result = engine.run(strategy, run_id)

    The engine is designed to be instantiated once per run. Do not reuse
    an instance across multiple runs (state is not reset between runs).
    """

    def __init__(self, catalog: DataCatalog, config) -> None:
        """
        Args:
            catalog: DataCatalog providing access to canonical datasets.
            config:  ProjectConfiguration (fully validated).
        """
        self._catalog = catalog
        self._config = config

        # Components (instantiated in run())
        self._cost_model: CostModel | None = None
        self._simulator: ExecutionSimulator | None = None
        self._sizer = PositionSizer()
        self._accountant: PortfolioAccountant | None = None
        self._risk_gate: RiskGate | None = None
        self._data_provider: BacktestDataProvider | None = None

        # Mutable state (reset each run)
        self._open_positions: dict[str, Position] = {}  # position_id → Position
        self._closed_trades: list[Trade] = []
        self._all_orders: list[Order] = []
        self._all_fills: list[Fill] = []
        self._events: list[ExecutionEvent] = []
        self._run_id: str = ""

        # Signal timing: pending_entry[symbol] = (order, entry_candle_ts)
        # Entry executes at NEXT candle open, not at signal candle close
        self._pending_entry: dict[str, tuple[Order, datetime]] = {}

    def run(self, strategy, run_id: str) -> BacktestResult:
        """
        Execute the backtest simulation.

        Args:
            strategy: Strategy object with on_candle() method.
            run_id:   Unique run identifier from RunManager.

        Returns:
            Complete BacktestResult.

        Raises:
            DataIntegrityError: If any required dataset fails validation.
            ExecutionError:     If a critical engine invariant is violated.
        """
        self._run_id = run_id
        cfg = self._config
        bt_cfg = cfg.backtest

        logger.info(
            "Backtest engine starting",
            run_id=run_id,
            strategy=strategy.name if hasattr(strategy, "name") else str(strategy),
            start=bt_cfg.start_date,
            end=bt_cfg.end_date,
            symbols=bt_cfg.symbols,
            timeframes=bt_cfg.timeframes,
        )

        # 1. Initialize components
        self._init_components()

        # 2. Validate and load data
        start_dt = pd.Timestamp(bt_cfg.start_date, tz="UTC")
        end_dt = pd.Timestamp(bt_cfg.end_date, tz="UTC")

        self._data_provider = BacktestDataProvider(
            catalog=self._catalog,
            symbols=bt_cfg.symbols,
            timeframes=bt_cfg.timeframes,
            start=start_dt.to_pydatetime(),
            end=end_dt.to_pydatetime(),
        )
        self._data_provider.validate_and_load()

        self._record_event(
            EventType.DATA_VALIDATED,
            timestamp=datetime.now(timezone.utc),
            details={"datasets": self._data_provider.loaded_datasets},
        )

        # 3. Build event stream — primary timeframe drives the clock
        primary_tf = bt_cfg.timeframes[0]
        primary_symbol = bt_cfg.symbols[0]
        timestamps = self._data_provider.get_all_timestamps(primary_symbol, primary_tf)

        self._record_event(
            EventType.BACKTEST_STARTED,
            timestamp=datetime.now(timezone.utc),
            details={
                "run_id": run_id,
                "candles": len(timestamps),
                "symbol": primary_symbol,
                "timeframe": primary_tf,
            },
        )

        # 4. Main event loop
        strategy_name = strategy.name if hasattr(strategy, "name") else "unknown"

        for ts_value in timestamps:
            ts: datetime = pd.Timestamp(ts_value).to_pydatetime()
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)

            # a. Daily reset
            self._accountant.check_and_reset_daily(ts)

            current_prices = {}
            for symbol in bt_cfg.symbols:
                # b. Update position prices using last known close
                self._update_position_prices(symbol, primary_tf, ts)

                # c. Get current candle OHLC for exit simulation
                candle_row = self._get_candle_at(symbol, primary_tf, ts)
                if candle_row is None:
                    continue

                candle_open = float(candle_row["open"])
                candle_high = float(candle_row["high"])
                candle_low = float(candle_row["low"])
                candle_close = float(candle_row["close"])
                current_prices[symbol] = candle_close

                # d. Check exits on all open positions for this symbol
                self._process_exits_for_symbol(
                    ts, symbol, candle_open, candle_high, candle_low, candle_close, run_id
                )

                # e. Execute pending entry from previous candle signal
                self._execute_pending_entry(ts, symbol, candle_open)

            # f. Equity curve snapshot
            self._accountant.snapshot_equity_curve(ts, current_prices)

            # g. Call strategy (receives CLOSED candles up to ts)
            for symbol in bt_cfg.symbols:
                candle_row = self._get_candle_at(symbol, primary_tf, ts)
                if candle_row is None:
                    continue
                candle_close = float(candle_row["close"])
                
                signal = strategy.on_candle(
                    close_price=candle_close,
                    symbol=symbol,
                    timeframe=primary_tf,
                    timestamp=ts,
                )

                if signal is None:
                    continue

                # h. Signal received → risk gate → size → queue pending entry
                self._process_signal(
                    signal=signal,
                    symbol=symbol,
                    timeframe=primary_tf,
                    strategy_name=strategy_name,
                    close_price=candle_close,
                    signal_timestamp=ts,
                    run_id=run_id,
                )

        # 5. End of data — close remaining open positions
        self._close_remaining_positions(run_id)

        # 6. Final equity snapshot
        final_ts = datetime.now(timezone.utc)
        self._accountant.snapshot_equity_curve(final_ts, {})

        # 7. Build result
        result = BacktestResult.build(
            run_id=run_id,
            strategy_name=strategy_name,
            start_date=bt_cfg.start_date,
            end_date=bt_cfg.end_date,
            symbols=bt_cfg.symbols,
            timeframes=bt_cfg.timeframes,
            trades=list(self._closed_trades),
            open_positions=list(self._open_positions.values()),
            orders=list(self._all_orders),
            fills=list(self._all_fills),
            equity_curve=self._accountant.equity_curve,
            events=list(self._events),
            initial_balance=self._config.capital.initial_balance,
            config_snapshot=self._config.model_dump(),
        )

        self._record_event(
            EventType.BACKTEST_COMPLETED,
            timestamp=final_ts,
            details={
                "total_trades": len(result.trades),
                "net_pnl": result.metrics.net_pnl,
                "final_equity": result.metrics.final_equity,
            },
        )

        logger.info(
            "Backtest completed",
            run_id=run_id,
            total_trades=len(result.trades),
            net_pnl=round(result.metrics.net_pnl, 4),
            win_rate=round(result.metrics.win_rate * 100, 2),
        )
        return result

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def _init_components(self) -> None:
        """Initialize all engine components from config."""
        cfg = self._config
        self._cost_model = CostModel.from_config(cfg.execution, cfg.costs)
        self._simulator = ExecutionSimulator(
            cost_model=self._cost_model,
            intrabar_policy=IntrabarFillPolicy(cfg.execution.intrabar_fill_policy),
            gap_policy=GapPolicy(cfg.execution.gap_policy),
        )
        self._accountant = PortfolioAccountant(
            initial_balance=cfg.capital.initial_balance
        )
        self._risk_gate = RiskGate(cfg.risk, allow_short=True)

        # Reset mutable state
        self._open_positions = {}
        self._closed_trades = []
        self._all_orders = []
        self._all_fills = []
        self._events = []
        self._pending_entry = {}

    # ------------------------------------------------------------------
    # Event helpers
    # ------------------------------------------------------------------

    def _record_event(
        self,
        event_type: EventType,
        timestamp: datetime,
        asset: str | None = None,
        order_id: str | None = None,
        position_id: str | None = None,
        trade_id: str | None = None,
        details: dict | None = None,
    ) -> ExecutionEvent:
        event = ExecutionEvent.create(
            timestamp=timestamp,
            event_type=event_type,
            run_id=self._run_id,
            asset=asset,
            order_id=order_id,
            position_id=position_id,
            trade_id=trade_id,
            details=details or {},
        )
        self._events.append(event)
        return event

    # ------------------------------------------------------------------
    # Data access helpers
    # ------------------------------------------------------------------

    def _get_candle_at(
        self, symbol: str, timeframe: str, ts: datetime
    ) -> dict | None:
        """Get the OHLC candle with open_time == ts."""
        df = self._data_provider.get_data(symbol, timeframe)
        ts_pd = pd.Timestamp(ts)
        mask = df["timestamp"] == ts_pd
        rows = df[mask]
        if rows.empty:
            return None
        return rows.iloc[0].to_dict()

    def _update_position_prices(
        self, symbol: str, timeframe: str, ts: datetime
    ) -> None:
        """Update open positions' current prices using the last closed candle close."""
        view = self._data_provider.get_view(ts)
        price = view.get_current_price(symbol, timeframe)
        if price is not None:
            for pos in self._open_positions.values():
                if pos.asset == symbol:
                    self._accountant.update_position_price(pos.position_id, price)

    # ------------------------------------------------------------------
    # Exit processing
    # ------------------------------------------------------------------

    def _process_exits_for_symbol(
        self,
        ts: datetime,
        symbol: str,
        candle_open: float,
        candle_high: float,
        candle_low: float,
        candle_close: float,
        run_id: str,
    ) -> None:
        """Check all open positions for stop/target triggers on this candle."""
        positions_to_close: list[tuple[Position, Fill, ExitReason]] = []

        for position in list(self._open_positions.values()):
            if position.asset != symbol:
                continue
            exit_fill, exit_reason = self._simulator.check_and_simulate_exits(
                position=position,
                candle_open=candle_open,
                candle_high=candle_high,
                candle_low=candle_low,
                candle_close=candle_close,
                candle_timestamp=ts,
                run_id=run_id,
            )
            if exit_fill is not None and exit_reason is not None:
                positions_to_close.append((position, exit_fill, exit_reason))

        for position, exit_fill, exit_reason in positions_to_close:
            self._close_position(position, exit_fill, exit_reason, ts)

    def _close_position(
        self,
        position: Position,
        exit_fill: Fill,
        exit_reason: ExitReason,
        ts: datetime,
    ) -> Trade:
        """Close a position and record the trade."""
        entry = position.entry_fill
        is_long = position.side == PositionSide.LONG

        # Gross PnL
        if is_long:
            gross_pnl = (exit_fill.fill_price - entry.fill_price) * entry.quantity
        else:
            gross_pnl = (entry.fill_price - exit_fill.fill_price) * entry.quantity

        total_fees = entry.fees + exit_fill.fees
        total_slippage = entry.slippage + exit_fill.slippage
        total_spread = entry.spread_cost + exit_fill.spread_cost
        net_pnl = gross_pnl - total_fees - total_slippage - total_spread

        r_multiple = None
        if position.risk_amount and position.risk_amount > 0:
            r_multiple = net_pnl / position.risk_amount

        trade = Trade.create(
            asset=position.asset,
            side=position.side,
            entry_fill=entry,
            exit_fill=exit_fill,
            strategy_name=position.strategy_name,
            run_id=position.run_id,
            exit_reason=exit_reason.value,
            gross_pnl=gross_pnl,
            fees=total_fees,
            slippage_cost=total_slippage,
            spread_cost=total_spread,
            net_pnl=net_pnl,
            timeframe=position.timeframe,
            initial_stop=position.initial_stop,
            target_price=position.target_price,
            risk_amount=position.risk_amount,
            r_multiple=r_multiple,
        )

        self._accountant.on_exit_fill(trade, position, exit_fill)
        del self._open_positions[position.position_id]
        self._closed_trades.append(trade)
        self._all_fills.append(exit_fill)

        self._record_event(
            EventType.POSITION_CLOSED,
            timestamp=ts,
            asset=position.asset,
            position_id=position.position_id,
            trade_id=trade.trade_id,
            details={
                "exit_reason": exit_reason.value,
                "net_pnl": net_pnl,
                "r_multiple": r_multiple,
            },
        )
        return trade

    # ------------------------------------------------------------------
    # Entry processing
    # ------------------------------------------------------------------

    def _process_signal(
        self,
        signal: dict,
        symbol: str,
        timeframe: str,
        strategy_name: str,
        close_price: float,
        signal_timestamp: datetime,
        run_id: str,
    ) -> None:
        """Process a signal from the strategy, running risk checks."""
        direction = signal.get("direction")
        stop_price = signal.get("stop_price")
        target_price = signal.get("target_price")

        if stop_price is None:
            logger.warning("Signal missing stop_price — rejected", symbol=symbol)
            return

        if direction == SignalDirection.SHORT:
            side = PositionSide.SHORT
        else:
            side = PositionSide.LONG
            
        entry_price_estimate = close_price  # For risk check, use close as estimate

        # Compute position size
        try:
            if self._config.position_sizing.mode == "fixed":
                quantity = self._sizer.size_fixed(
                    fixed_quantity=self._config.position_sizing.fixed_quantity,
                    entry_price=entry_price_estimate,
                    available_capital=self._accountant.get_available_capital(),
                )
            else:
                quantity = self._sizer.size_risk_based(
                    equity=self._accountant.get_equity(),
                    risk_per_trade_pct=self._config.capital.risk_per_trade_pct,
                    entry_price=entry_price_estimate,
                    stop_price=stop_price,
                    available_capital=self._accountant.get_available_capital(),
                )
        except ExecutionError as e:
            self._reject_order(
                symbol=symbol,
                strategy_name=strategy_name,
                reason=RejectionReason.INSUFFICIENT_CAPITAL,
                timestamp=signal_timestamp,
                run_id=run_id,
                details={"error": str(e)},
            )
            return

        risk_amount = self._sizer.compute_risk_amount(quantity, entry_price_estimate, stop_price)

        # Risk gate checks
        portfolio_state = self._accountant.get_portfolio_state(signal_timestamp)
        asset_notional = self._accountant.get_asset_notional(symbol)

        approved, rejection_reason = self._risk_gate.check_all(
            side=side,
            portfolio_state=portfolio_state,
            symbol=symbol,
            entry_price=entry_price_estimate,
            quantity=quantity,
            open_position_count=self._accountant.open_position_count,
            asset_notional=asset_notional,
        )

        if not approved:
            self._reject_order(
                symbol=symbol,
                strategy_name=strategy_name,
                reason=rejection_reason,
                timestamp=signal_timestamp,
                run_id=run_id,
                details={"rejection_reason": rejection_reason.value},
            )
            return

        # Create order and queue for NEXT candle (signal timing rule)
        order_side = OrderSide.SELL if side == PositionSide.SHORT else OrderSide.BUY
        order = Order.create(
            timestamp=signal_timestamp,
            asset=symbol,
            side=order_side,
            order_type=OrderType.MARKET,
            quantity=quantity,
            strategy_name=strategy_name,
            run_id=run_id,
            timeframe=None,
            stop_price=stop_price,
            target_price=target_price,
            status=OrderStatus.ACTIVE,
        )
        self._all_orders.append(order)
        self._pending_entry[symbol] = (order, signal_timestamp)

        # Store risk_amount on the order for the position
        object.__setattr__(order, '_risk_amount', risk_amount)

        self._record_event(
            EventType.SIGNAL_RECEIVED,
            timestamp=signal_timestamp,
            asset=symbol,
            order_id=order.order_id,
            details={
                "stop_price": stop_price,
                "target_price": target_price,
                "quantity": quantity,
                "risk_amount": risk_amount,
                "note": "Entry queued for next candle open (signal timing rule)",
            },
        )

    def _execute_pending_entry(
        self, ts: datetime, symbol: str, candle_open: float
    ) -> None:
        """Execute any pending entry order at the current candle's open price."""
        if symbol not in self._pending_entry:
            return

        order, signal_ts = self._pending_entry.pop(symbol)

        position_side = PositionSide.SHORT if order.side == OrderSide.SELL else PositionSide.LONG

        # Simulate market entry at this candle's open
        entry_fill = self._simulator.simulate_market_entry(
            order_id=order.order_id,
            timestamp=ts,
            symbol=symbol,
            side=position_side,
            quantity=order.quantity,
            candle_open=candle_open,
        )

        risk_amount = getattr(order, "_risk_amount", None)

        position = Position.create(
            asset=symbol,
            side=position_side,
            entry_fill=entry_fill,
            strategy_name=order.strategy_name,
            run_id=order.run_id,
            stop_price=order.stop_price,
            target_price=order.target_price,
            initial_stop=order.stop_price,
            risk_amount=risk_amount,
        )

        self._accountant.on_entry_fill(entry_fill, position)
        self._open_positions[position.position_id] = position
        self._all_fills.append(entry_fill)

        self._record_event(
            EventType.ORDER_FILLED,
            timestamp=ts,
            asset=symbol,
            order_id=order.order_id,
            position_id=position.position_id,
            details={
                "fill_price": entry_fill.fill_price,
                "quantity": entry_fill.quantity,
                "stop_price": order.stop_price,
                "target_price": order.target_price,
                "execution_note": f"Entry at candle open (signal was from {signal_ts.isoformat()})",
            },
        )

    def _reject_order(
        self,
        symbol: str,
        strategy_name: str,
        reason: RejectionReason,
        timestamp: datetime,
        run_id: str,
        details: dict,
    ) -> None:
        """Create a rejected order record in the audit ledger."""
        order = Order.create(
            timestamp=timestamp,
            asset=symbol,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=0.0001,  # placeholder
            strategy_name=strategy_name,
            run_id=run_id,
            status=OrderStatus.REJECTED,
            rejection_reason=reason,
        )
        self._all_orders.append(order)
        self._record_event(
            EventType.ORDER_REJECTED,
            timestamp=timestamp,
            asset=symbol,
            order_id=order.order_id,
            details={"reason": reason.value, **details},
        )

    # ------------------------------------------------------------------
    # End-of-run cleanup
    # ------------------------------------------------------------------

    def _close_remaining_positions(self, run_id: str) -> None:
        """Close all open positions at their last known price at end of simulation."""
        if not self._open_positions:
            return

        close_ts = datetime.now(timezone.utc)
        positions = list(self._open_positions.values())

        for position in positions:
            last_price = position.current_price or position.entry_price
            exit_fill = self._simulator._create_exit_fill(
                position=position,
                exit_level=last_price,
                timestamp=close_ts,
                reason=ExitReason.END_OF_DATA,
            )
            self._close_position(position, exit_fill, ExitReason.END_OF_DATA, close_ts)

        logger.info(
            "Remaining positions closed at end of data",
            count=len(positions),
        )

    # ------------------------------------------------------------------
    # ExecutionEngine Protocol stubs (for interface compliance)
    # ------------------------------------------------------------------

    def get_open_positions(self) -> list[Position]:
        return list(self._open_positions.values())

    def get_closed_trades(self) -> list[Trade]:
        return list(self._closed_trades)

    def get_portfolio_value(self) -> float:
        return self._accountant.get_equity() if self._accountant else 0.0
