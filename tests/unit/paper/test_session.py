"""
Unit tests for PaperTradingSession — Prompt 08.

Tests:
    - Session lifecycle state machine
    - Accounting: realized PnL, equity, unrealized PnL
    - Accounting reconciliation
    - Trade recording (wins/losses)
    - Counters
    - Metadata export
"""

from __future__ import annotations

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from crypto_research.config.schema import PaperTradingConfig, ProjectConfiguration
from crypto_research.core.domain import ExecutionMode, PaperSessionState, PositionSide
from crypto_research.paper.session import (
    MANUAL_STOP,
    PaperAccountingState,
    PaperTradingSession,
)


def _make_config() -> ProjectConfiguration:
    """Minimal config for session tests."""
    return MagicMock(
        spec=ProjectConfiguration,
        paper_trading=PaperTradingConfig(initial_balance=10_000.0),
        assets=["BTCUSDT"],
        timeframes=["1h"],
        data=MagicMock(market_type="futures"),
    )


def _make_trade(net_pnl: float):
    """Create a minimal Trade mock."""
    t = MagicMock()
    t.net_pnl = net_pnl
    t.gross_pnl = net_pnl + 10.0
    t.fees = 5.0
    t.slippage_cost = 3.0
    t.spread_cost = 2.0
    return t


class TestPaperTradingSessionLifecycle:
    """State machine transitions must be valid and logged."""

    def setup_method(self):
        self.cfg = _make_config()
        self.session = PaperTradingSession(self.cfg, run_id="test_run_001")

    def test_initial_state_is_initializing(self):
        assert self.session.state == PaperSessionState.INITIALIZING

    def test_start_transitions_to_running(self):
        self.session.start()
        assert self.session.state == PaperSessionState.RUNNING

    def test_start_records_start_time(self):
        self.session.start()
        assert self.session.start_time is not None

    def test_is_running_true_when_running(self):
        self.session.start()
        assert self.session.is_running() is True

    def test_is_running_false_when_stopped(self):
        self.session.start()
        self.session.request_stop()
        self.session.mark_stopped()
        assert self.session.is_running() is False

    def test_request_stop_transitions_to_stopping(self):
        self.session.start()
        self.session.request_stop(MANUAL_STOP)
        assert self.session.state == PaperSessionState.STOPPING

    def test_mark_stopped_transitions_to_stopped(self):
        self.session.start()
        self.session.request_stop()
        self.session.mark_stopped()
        assert self.session.state == PaperSessionState.STOPPED

    def test_mark_failed_transitions_to_failed(self):
        self.session.start()
        self.session.mark_failed("test error")
        assert self.session.state == PaperSessionState.FAILED

    def test_mark_failed_increments_error_counter(self):
        self.session.start()
        initial = self.session.counters.errors
        self.session.mark_failed("test error")
        assert self.session.counters.errors == initial + 1

    def test_is_stopping_or_stopped(self):
        self.session.start()
        self.session.request_stop()
        assert self.session.is_stopping_or_stopped() is True

    def test_transition_history_recorded(self):
        self.session.start()
        self.session.request_stop()
        self.session.mark_stopped()
        transitions = self.session._state_transitions
        assert len(transitions) >= 3

    def test_uptime_seconds_returns_zero_before_start(self):
        assert self.session.uptime_seconds() == 0.0

    def test_uptime_seconds_positive_after_start(self):
        self.session.start()
        assert self.session.uptime_seconds() >= 0


class TestPaperTradingSessionAccounting:
    """Accounting and reconciliation tests."""

    def setup_method(self):
        self.cfg = _make_config()
        self.session = PaperTradingSession(self.cfg, run_id="test_acc")

    def test_initial_balance_set_correctly(self):
        assert self.session.accounting.initial_balance == 10_000.0
        assert self.session.accounting.cash == 10_000.0

    def test_equity_equals_cash_plus_unrealized(self):
        self.session.accounting.cash = 9_500.0
        self.session.accounting.unrealized_pnl = 300.0
        assert self.session.accounting.equity == 9_800.0

    def test_net_pnl_subtracts_all_costs(self):
        acct = self.session.accounting
        acct.realized_pnl = 500.0
        acct.total_fees = 20.0
        acct.total_slippage = 5.0
        acct.total_spread = 3.0
        assert acct.net_pnl == 472.0

    def test_record_winning_trade(self):
        trade = _make_trade(net_pnl=100.0)
        self.session.record_trade_closed(trade)
        assert self.session.counters.wins == 1
        assert self.session.counters.losses == 0
        assert self.session.accounting.realized_pnl == 100.0

    def test_record_losing_trade(self):
        trade = _make_trade(net_pnl=-50.0)
        self.session.record_trade_closed(trade)
        assert self.session.counters.losses == 1
        assert self.session.counters.wins == 0

    def test_record_multiple_trades_accumulate_pnl(self):
        self.session.record_trade_closed(_make_trade(100.0))
        self.session.record_trade_closed(_make_trade(50.0))
        self.session.record_trade_closed(_make_trade(-30.0))
        assert self.session.counters.trades_completed == 3
        assert self.session.accounting.realized_pnl == pytest.approx(120.0)

    def test_reconciliation_matches_clean_state(self):
        result = self.session.reconcile()
        assert result["reconciled"] is True
        assert result["discrepancy"] < 0.01

    def test_reconciliation_detects_discrepancy(self):
        # Force an inconsistent state
        self.session.accounting.cash = 5_000.0  # Mismatch
        result = self.session.reconcile()
        # Discrepancy should be large
        assert result["discrepancy"] > 0.01
        assert result["reconciled"] is False


class TestPaperTradingSessionMetadata:
    """Metadata export for audit files."""

    def test_to_metadata_dict_contains_required_fields(self):
        cfg = _make_config()
        session = PaperTradingSession(cfg, run_id="test_meta")
        meta = session.to_metadata_dict()

        required = {
            "session_id", "run_id", "execution_mode", "state",
            "initial_balance", "accounting", "counters",
            "reconciliation", "paper_label",
        }
        assert required.issubset(meta.keys())

    def test_paper_label_present(self):
        cfg = _make_config()
        session = PaperTradingSession(cfg, run_id="test_label")
        meta = session.to_metadata_dict()
        assert "PAPER" in meta["paper_label"]
        assert "NO REAL ORDERS" in meta["paper_label"]

    def test_execution_mode_is_paper(self):
        cfg = _make_config()
        session = PaperTradingSession(cfg, run_id="test_mode")
        meta = session.to_metadata_dict()
        assert meta["execution_mode"] == ExecutionMode.PAPER.value


class TestPaperAccountingState:
    """Isolated unit tests for PaperAccountingState."""

    def test_equity_calculation(self):
        acct = PaperAccountingState(initial_balance=10_000, cash=9_000)
        acct.unrealized_pnl = 500.0
        assert acct.equity == 9_500.0

    def test_net_pnl_calculation(self):
        acct = PaperAccountingState(initial_balance=10_000, cash=10_000)
        acct.realized_pnl = 200.0
        acct.total_fees = 10.0
        acct.total_slippage = 5.0
        acct.total_spread = 3.0
        assert acct.net_pnl == 182.0

    def test_to_dict_returns_expected_keys(self):
        acct = PaperAccountingState(initial_balance=5000, cash=5000)
        d = acct.to_dict()
        assert "initial_balance" in d
        assert "equity" in d
        assert "net_pnl" in d
        assert "realized_pnl" in d
