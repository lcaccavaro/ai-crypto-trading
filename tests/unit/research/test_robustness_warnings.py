"""
Unit tests for RobustnessWarningEngine.

Tests:
    - Trade count warning fires below threshold
    - OOS window count warning fires correctly
    - Parameter sensitivity warning fires when deviation > threshold
    - Cost sensitivity warning fires when degradation > threshold
    - Asset dependency warning fires when one asset dominates
    - Timeframe dependency warning fires when one timeframe dominates
    - Regime dependency warning fires when one regime dominates
    - No warnings when within thresholds
"""

from __future__ import annotations

import pytest

from crypto_research.research.robustness.warnings import (
    RobustnessWarningEngine,
    WarningCode,
)


class TestTradeCountWarning:
    def test_fires_below_threshold(self):
        engine = RobustnessWarningEngine(min_trades=30)
        warnings = engine.check_trade_count(10)
        assert len(warnings) == 1
        assert warnings[0].code == WarningCode.LOW_SAMPLE_WARNING

    def test_no_warning_at_threshold(self):
        engine = RobustnessWarningEngine(min_trades=30)
        warnings = engine.check_trade_count(30)
        assert len(warnings) == 0

    def test_no_warning_above_threshold(self):
        engine = RobustnessWarningEngine(min_trades=30)
        warnings = engine.check_trade_count(100)
        assert len(warnings) == 0

    def test_context_recorded(self):
        engine = RobustnessWarningEngine(min_trades=30)
        warnings = engine.check_trade_count(5, context="BTCUSDT")
        assert warnings[0].context == "BTCUSDT"


class TestOOSWindowWarning:
    def test_fires_below_threshold(self):
        engine = RobustnessWarningEngine(min_oos_windows=5)
        warnings = engine.check_oos_window_count(3)
        assert len(warnings) == 1
        assert warnings[0].code == WarningCode.LOW_OOS_SAMPLE

    def test_no_warning_at_threshold(self):
        engine = RobustnessWarningEngine(min_oos_windows=5)
        warnings = engine.check_oos_window_count(5)
        assert len(warnings) == 0


class TestParameterSensitivityWarning:
    def test_fires_when_deviation_large(self):
        engine = RobustnessWarningEngine()
        # baseline=100, variant=200 → 100% deviation → fires at 30% threshold
        warnings = engine.check_parameter_sensitivity(
            param_name="RR",
            baseline_metric=100.0,
            variant_metrics=[200.0, 90.0],
            sensitivity_threshold_pct=30.0,
        )
        assert len(warnings) == 1
        assert warnings[0].code == WarningCode.HIGH_PARAMETER_SENSITIVITY

    def test_no_warning_when_stable(self):
        engine = RobustnessWarningEngine()
        # baseline=100, variants all within ±10% → no warning at 30% threshold
        warnings = engine.check_parameter_sensitivity(
            param_name="RR",
            baseline_metric=100.0,
            variant_metrics=[95.0, 105.0, 102.0],
            sensitivity_threshold_pct=30.0,
        )
        assert len(warnings) == 0

    def test_no_warning_with_zero_baseline(self):
        engine = RobustnessWarningEngine()
        warnings = engine.check_parameter_sensitivity("RR", 0.0, [10.0, 20.0])
        assert len(warnings) == 0  # Prevents division by zero


class TestCostSensitivityWarning:
    def test_fires_when_degradation_high(self):
        engine = RobustnessWarningEngine()
        warnings = engine.check_cost_sensitivity(
            baseline_pnl=100.0,
            adverse_pnl=10.0,  # 90% degradation
            adverse_label="cost_x2",
            degradation_threshold_pct=50.0,
        )
        assert len(warnings) == 1
        assert warnings[0].code == WarningCode.HIGH_COST_SENSITIVITY

    def test_no_warning_when_stable(self):
        engine = RobustnessWarningEngine()
        warnings = engine.check_cost_sensitivity(
            baseline_pnl=100.0,
            adverse_pnl=80.0,  # 20% degradation
            adverse_label="cost_x1.5",
            degradation_threshold_pct=50.0,
        )
        assert len(warnings) == 0

    def test_no_warning_with_zero_baseline(self):
        engine = RobustnessWarningEngine()
        warnings = engine.check_cost_sensitivity(0.0, 50.0, "cost_x2")
        assert len(warnings) == 0


class TestAssetDependencyWarning:
    def test_fires_when_one_asset_dominates(self):
        engine = RobustnessWarningEngine()
        contributions = {"BTCUSDT": 900.0, "ETHUSDT": 100.0}
        warnings = engine.check_asset_dependency(contributions, total_pnl=1000.0)
        assert any(w.code == WarningCode.SINGLE_ASSET_DEPENDENCY for w in warnings)

    def test_no_warning_when_spread_even(self):
        engine = RobustnessWarningEngine()
        contributions = {"BTCUSDT": 50.0, "ETHUSDT": 50.0}
        warnings = engine.check_asset_dependency(contributions, total_pnl=100.0)
        assert len(warnings) == 0

    def test_no_warning_with_zero_total(self):
        engine = RobustnessWarningEngine()
        warnings = engine.check_asset_dependency({"BTCUSDT": 100.0}, total_pnl=0.0)
        assert len(warnings) == 0


class TestRegimeDependencyWarning:
    def test_fires_when_concentrated(self):
        engine = RobustnessWarningEngine()
        contributions = {"TREND_UP_LOW_VOL": 950.0, "RANGE_NORMAL_VOL": 50.0}
        warnings = engine.check_regime_dependency(contributions, total_pnl=1000.0)
        assert any(w.code == WarningCode.REGIME_DEPENDENCY for w in warnings)

    def test_no_warning_when_spread(self):
        engine = RobustnessWarningEngine()
        contributions = {"TREND_UP": 40.0, "RANGE": 30.0, "TREND_DOWN": 30.0}
        warnings = engine.check_regime_dependency(contributions, total_pnl=100.0)
        assert len(warnings) == 0
