"""
Unit tests for PaperDriftMonitor — Prompt 08.

Tests:
    - No warnings when disabled
    - No warnings with insufficient trades
    - Warning generated when metric exceeds threshold
    - No warning when metric is within threshold
    - set_baseline() updates baseline correctly
    - DriftWarning serialization
"""

from __future__ import annotations

import pytest

from crypto_research.config.schema import PaperDriftConfig
from crypto_research.paper.drift_monitor import DriftWarning, DriftWarningCode, PaperDriftMonitor


def _make_config(**kwargs) -> PaperDriftConfig:
    defaults = {
        "enabled": True,
        "signal_frequency_change_pct": 50.0,
        "score_mean_change_pct": 30.0,
        "rejection_rate_change_pct": 50.0,
        "cost_change_pct": 40.0,
        "min_paper_trades_for_drift": 20,
    }
    defaults.update(kwargs)
    return PaperDriftConfig(**defaults)


def _metrics(
    signals_per_hour: float = 2.0,
    mean_score: float = 0.7,
    rejection_rate: float = 0.3,
    avg_cost_per_trade: float = 5.0,
) -> dict:
    return {
        "signals_per_hour": signals_per_hour,
        "mean_score": mean_score,
        "rejection_rate": rejection_rate,
        "avg_cost_per_trade": avg_cost_per_trade,
    }


def _baseline(
    signals_per_hour: float = 2.0,
    mean_score: float = 0.7,
    rejection_rate: float = 0.3,
    avg_cost_per_trade: float = 5.0,
) -> dict:
    return {
        "signals_per_hour": signals_per_hour,
        "mean_score": mean_score,
        "rejection_rate": rejection_rate,
        "avg_cost_per_trade": avg_cost_per_trade,
    }


class TestPaperDriftMonitorDisabled:
    def test_disabled_returns_no_warnings(self):
        config = _make_config(enabled=False)
        monitor = PaperDriftMonitor(config, _baseline())
        warnings = monitor.check(_metrics(), min_trades=100)
        assert warnings == []


class TestPaperDriftMonitorInsufficientTrades:
    def test_insufficient_trades_returns_no_warnings(self):
        config = _make_config(min_paper_trades_for_drift=20)
        monitor = PaperDriftMonitor(config, _baseline())
        warnings = monitor.check(_metrics(), min_trades=5)
        assert warnings == []

    def test_exactly_min_trades_is_evaluated(self):
        """min_paper_trades_for_drift is a minimum — at exactly min trades, warnings may fire."""
        config = _make_config(min_paper_trades_for_drift=20)
        # Huge drift in signals_per_hour to force a warning
        monitor = PaperDriftMonitor(config, _baseline(signals_per_hour=2.0))
        paper = _metrics(signals_per_hour=10.0)  # +400% — well above 50%
        warnings = monitor.check(paper, min_trades=20)
        assert len(warnings) >= 1


class TestPaperDriftMonitorWarnings:
    def test_signal_frequency_drift_detected(self):
        config = _make_config(signal_frequency_change_pct=50.0)
        baseline = _baseline(signals_per_hour=2.0)
        monitor = PaperDriftMonitor(config, baseline)
        # 300% change — well above 50% threshold
        paper = _metrics(signals_per_hour=8.0)
        warnings = monitor.check(paper, min_trades=50)
        codes = [w.code for w in warnings]
        assert DriftWarningCode.SIGNAL_FREQUENCY in codes

    def test_score_distribution_drift_detected(self):
        config = _make_config(score_mean_change_pct=30.0)
        baseline = _baseline(mean_score=0.7)
        monitor = PaperDriftMonitor(config, baseline)
        # mean_score dropped from 0.7 to 0.3 — 57% change
        paper = _metrics(mean_score=0.3)
        warnings = monitor.check(paper, min_trades=50)
        codes = [w.code for w in warnings]
        assert DriftWarningCode.SCORE_DISTRIBUTION in codes

    def test_rejection_rate_drift_detected(self):
        config = _make_config(rejection_rate_change_pct=50.0)
        baseline = _baseline(rejection_rate=0.2)
        monitor = PaperDriftMonitor(config, baseline)
        # 200% change
        paper = _metrics(rejection_rate=0.6)
        warnings = monitor.check(paper, min_trades=50)
        codes = [w.code for w in warnings]
        assert DriftWarningCode.REJECTION_RATE in codes

    def test_cost_drift_detected(self):
        config = _make_config(cost_change_pct=40.0)
        baseline = _baseline(avg_cost_per_trade=5.0)
        monitor = PaperDriftMonitor(config, baseline)
        # 100% change
        paper = _metrics(avg_cost_per_trade=10.0)
        warnings = monitor.check(paper, min_trades=50)
        codes = [w.code for w in warnings]
        assert DriftWarningCode.COST in codes

    def test_no_warning_within_threshold(self):
        """Metrics within threshold should produce no warnings."""
        config = _make_config(
            signal_frequency_change_pct=50.0,
            score_mean_change_pct=30.0,
            rejection_rate_change_pct=50.0,
            cost_change_pct=40.0,
        )
        baseline = _baseline()
        monitor = PaperDriftMonitor(config, baseline)
        # All identical to baseline — 0% change
        paper = _metrics()
        warnings = monitor.check(paper, min_trades=50)
        assert warnings == []

    def test_no_warning_when_baseline_key_missing(self):
        """Missing baseline key should not cause an error or produce a warning."""
        config = _make_config()
        monitor = PaperDriftMonitor(config, {})  # empty baseline
        warnings = monitor.check(_metrics(), min_trades=50)
        assert warnings == []


class TestDriftWarning:
    def test_to_dict_has_required_fields(self):
        w = DriftWarning(
            code=DriftWarningCode.SIGNAL_FREQUENCY,
            description="Test drift",
            baseline_value=2.0,
            paper_value=6.0,
            change_pct=200.0,
            detected_at="2024-01-01T00:00:00+00:00",
        )
        d = w.to_dict()
        assert "code" in d
        assert "description" in d
        assert "baseline_value" in d
        assert "paper_value" in d
        assert "change_pct" in d
        assert "detected_at" in d


class TestDriftMonitorBaseline:
    def test_set_baseline_updates_correctly(self):
        config = _make_config()
        monitor = PaperDriftMonitor(config, {})
        monitor.set_baseline({"signals_per_hour": 3.0})
        assert monitor._baseline["signals_per_hour"] == 3.0
