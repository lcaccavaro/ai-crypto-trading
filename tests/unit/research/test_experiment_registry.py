"""
Unit tests for ExperimentRegistry.
"""

from __future__ import annotations

import json
import pytest
import tempfile
from pathlib import Path

from crypto_research.research.experiments.registry import ExperimentRegistry, VALID_EXPERIMENT_TYPES


class TestRegistration:
    def test_register_creates_record(self):
        reg = ExperimentRegistry(run_id="test_run")
        rec = reg.register(
            experiment_type="WALK_FORWARD",
            description="Rolling walk-forward",
            assets=["BTCUSDT"],
            timeframes=["15m"],
            strategies=["strat_a"],
            date_range_start="2024-01-01",
            date_range_end="2024-06-01",
        )
        assert rec.experiment_id.startswith("exp-")
        assert rec.status == "RUNNING"
        assert len(reg) == 1

    def test_invalid_type_raises(self):
        reg = ExperimentRegistry(run_id="test_run")
        with pytest.raises(ValueError):
            reg.register(
                experiment_type="INVALID_TYPE",
                description="test",
                assets=["BTCUSDT"],
                timeframes=["15m"],
                strategies=["s"],
                date_range_start="2024-01-01",
                date_range_end="2024-06-01",
            )

    def test_all_valid_types_accepted(self):
        reg = ExperimentRegistry(run_id="test_run")
        for exp_type in VALID_EXPERIMENT_TYPES:
            rec = reg.register(
                experiment_type=exp_type,
                description=f"Test {exp_type}",
                assets=["BTCUSDT"],
                timeframes=["15m"],
                strategies=["s"],
                date_range_start="2024-01-01",
                date_range_end="2024-06-01",
            )
            assert rec.status == "RUNNING"


class TestCompletion:
    def test_mark_complete(self):
        reg = ExperimentRegistry(run_id="test_run")
        rec = reg.register(
            experiment_type="BASELINE",
            description="test",
            assets=["BTCUSDT"],
            timeframes=["15m"],
            strategies=["s"],
            date_range_start="2024-01-01",
            date_range_end="2024-06-01",
        )
        reg.complete(rec, metrics={"net_pnl": 123.4})
        assert rec.status == "COMPLETE"
        assert rec.completed_at is not None
        assert "net_pnl" in rec.metrics_json

    def test_mark_failed(self):
        reg = ExperimentRegistry(run_id="test_run")
        rec = reg.register(
            experiment_type="BASELINE",
            description="test",
            assets=["BTCUSDT"],
            timeframes=["15m"],
            strategies=["s"],
            date_range_start="2024-01-01",
            date_range_end="2024-06-01",
        )
        reg.fail(rec, error="something broke")
        assert rec.status == "FAILED"
        assert "something broke" in rec.error

    def test_add_warning_to_record(self):
        reg = ExperimentRegistry(run_id="test_run")
        rec = reg.register(
            experiment_type="BASELINE",
            description="test",
            assets=["BTCUSDT"],
            timeframes=["15m"],
            strategies=["s"],
            date_range_start="2024-01-01",
            date_range_end="2024-06-01",
        )
        rec.add_warning("LOW_SAMPLE_WARNING")
        assert "LOW_SAMPLE_WARNING" in rec.warnings


class TestPersistence:
    def test_csv_export(self, tmp_path):
        reg = ExperimentRegistry(run_id="test_run")
        rec = reg.register(
            experiment_type="WALK_FORWARD",
            description="test",
            assets=["BTCUSDT"],
            timeframes=["15m"],
            strategies=["s"],
            date_range_start="2024-01-01",
            date_range_end="2024-06-01",
        )
        reg.complete(rec)
        csv_path = tmp_path / "registry.csv"
        reg.to_csv(csv_path)
        assert csv_path.exists()
        content = csv_path.read_text()
        assert "WALK_FORWARD" in content
        assert "test_run" in content

    def test_json_export(self, tmp_path):
        reg = ExperimentRegistry(run_id="test_run")
        rec = reg.register(
            experiment_type="REGIME_ANALYSIS",
            description="regime test",
            assets=["BTCUSDT"],
            timeframes=["15m"],
            strategies=["s"],
            date_range_start="2024-01-01",
            date_range_end="2024-06-01",
        )
        reg.complete(rec)
        json_path = tmp_path / "registry.json"
        reg.to_json(json_path)
        data = json.loads(json_path.read_text())
        assert isinstance(data, list)
        assert data[0]["experiment_type"] == "REGIME_ANALYSIS"

    def test_empty_csv_export(self, tmp_path):
        reg = ExperimentRegistry(run_id="test_run")
        csv_path = tmp_path / "empty_registry.csv"
        reg.to_csv(csv_path)
        assert csv_path.exists()


class TestSummary:
    def test_summary_counts(self):
        reg = ExperimentRegistry(run_id="test_run")
        for exp_type in ["WALK_FORWARD", "COST_SENSITIVITY", "WALK_FORWARD"]:
            rec = reg.register(
                experiment_type=exp_type,
                description="test",
                assets=["BTCUSDT"],
                timeframes=["15m"],
                strategies=["s"],
                date_range_start="2024-01-01",
                date_range_end="2024-06-01",
            )
            if exp_type == "WALK_FORWARD":
                reg.complete(rec)
            else:
                reg.fail(rec, "test_fail")

        summary = reg.summary()
        assert summary["total_experiments"] == 3
        assert summary["by_type"]["WALK_FORWARD"] == 2
        assert summary["by_type"]["COST_SENSITIVITY"] == 1

    def test_summary_contains_multiple_testing_note(self):
        reg = ExperimentRegistry(run_id="test_run")
        summary = reg.summary()
        assert "multiple" in summary["multiple_testing_note"].lower()
