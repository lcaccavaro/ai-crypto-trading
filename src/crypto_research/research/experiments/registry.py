"""
Experiment Registry.

Append-only ledger of every research experiment executed in Prompt 07.

Design:
    - Every experiment writes exactly one record before starting and updates
      it when complete (or on failure).
    - Failures are recorded with status=FAILED, never silently skipped.
    - The registry is the audit trail for multiple-testing awareness.
    - Each row stores a configuration snapshot for reproducibility.

Experiment types (from prompt 07):
    WALK_FORWARD
    COST_SENSITIVITY
    PARAMETER_SENSITIVITY
    REGIME_ANALYSIS
    ASSET_ROBUSTNESS
    TIMEFRAME_ROBUSTNESS
    LEAVE_ONE_OUT
"""

from __future__ import annotations

import csv
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_research.utils.logging import get_logger

logger = get_logger(__name__)

VALID_EXPERIMENT_TYPES = {
    "WALK_FORWARD",
    "COST_SENSITIVITY",
    "PARAMETER_SENSITIVITY",
    "REGIME_ANALYSIS",
    "ASSET_ROBUSTNESS",
    "TIMEFRAME_ROBUSTNESS",
    "LEAVE_ONE_OUT",
    "BASELINE",
}


@dataclass
class ExperimentRecord:
    """A single experiment record in the registry."""

    experiment_id: str
    run_id: str
    experiment_type: str
    description: str
    started_at: datetime
    assets: list[str]
    timeframes: list[str]
    strategies: list[str]
    date_range_start: str
    date_range_end: str
    baseline_config_json: str  # JSON snapshot of the baseline config
    modified_config_json: str  # JSON snapshot of experiment-specific overrides
    status: str = "RUNNING"   # RUNNING | COMPLETE | FAILED
    completed_at: datetime | None = None
    error: str = ""
    warnings: list[str] = field(default_factory=list)
    metrics_json: str = "{}"  # JSON of key metrics

    def mark_complete(self, metrics: dict[str, Any] | None = None) -> None:
        self.status = "COMPLETE"
        self.completed_at = datetime.now(timezone.utc)
        if metrics:
            self.metrics_json = json.dumps(metrics, default=str)

    def mark_failed(self, error: str) -> None:
        self.status = "FAILED"
        self.completed_at = datetime.now(timezone.utc)
        self.error = error

    def add_warning(self, warning: str) -> None:
        self.warnings.append(warning)

    def to_dict(self) -> dict:
        return {
            "experiment_id": self.experiment_id,
            "run_id": self.run_id,
            "experiment_type": self.experiment_type,
            "description": self.description,
            "status": self.status,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else "",
            "assets": "|".join(self.assets),
            "timeframes": "|".join(self.timeframes),
            "strategies": "|".join(self.strategies),
            "date_range_start": self.date_range_start,
            "date_range_end": self.date_range_end,
            "error": self.error,
            "warnings": "|".join(self.warnings),
            "metrics_json": self.metrics_json,
        }


class ExperimentRegistry:
    """
    Append-only in-memory ledger with CSV/JSON persistence.

    Every experiment must call `register()` before starting.
    On completion, call `complete()` or `fail()`.
    The registry explicitly records all experiments, making the full
    experiment matrix visible for multiple-testing awareness.
    """

    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        self._records: list[ExperimentRecord] = []

    def register(
        self,
        experiment_type: str,
        description: str,
        assets: list[str],
        timeframes: list[str],
        strategies: list[str],
        date_range_start: str,
        date_range_end: str,
        baseline_config: dict | None = None,
        modified_config: dict | None = None,
    ) -> ExperimentRecord:
        """Register a new experiment and return its record."""
        if experiment_type not in VALID_EXPERIMENT_TYPES:
            raise ValueError(
                f"Invalid experiment_type '{experiment_type}'. "
                f"Must be one of {VALID_EXPERIMENT_TYPES}"
            )

        rec = ExperimentRecord(
            experiment_id=f"exp-{uuid.uuid4().hex[:12]}",
            run_id=self.run_id,
            experiment_type=experiment_type,
            description=description,
            started_at=datetime.now(timezone.utc),
            assets=list(assets),
            timeframes=list(timeframes),
            strategies=list(strategies),
            date_range_start=date_range_start,
            date_range_end=date_range_end,
            baseline_config_json=json.dumps(baseline_config or {}, default=str),
            modified_config_json=json.dumps(modified_config or {}, default=str),
        )
        self._records.append(rec)
        logger.info(
            "Experiment registered",
            experiment_id=rec.experiment_id,
            type=experiment_type,
            description=description,
        )
        return rec

    def complete(self, rec: ExperimentRecord, metrics: dict | None = None) -> None:
        rec.mark_complete(metrics)
        logger.info("Experiment complete", experiment_id=rec.experiment_id, status="COMPLETE")

    def fail(self, rec: ExperimentRecord, error: str) -> None:
        rec.mark_failed(error)
        logger.error("Experiment FAILED", experiment_id=rec.experiment_id, error=error)

    def records(self) -> list[ExperimentRecord]:
        return list(self._records)

    def to_csv(self, path: str | Path) -> Path:
        """Export registry to CSV."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        if not self._records:
            path.write_text("experiment_id,run_id,experiment_type,status,description\n")
            return path

        fieldnames = list(self._records[0].to_dict().keys())
        with path.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for rec in self._records:
                writer.writerow(rec.to_dict())

        logger.info(f"Experiment registry exported to {path.name}", count=len(self._records))
        return path

    def to_json(self, path: str | Path) -> Path:
        """Export registry to JSON."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w") as f:
            json.dump([r.to_dict() for r in self._records], f, indent=2, default=str)
        return path

    def summary(self) -> dict:
        """Return a summary dict for robustness_summary.json."""
        total = len(self._records)
        by_type: dict[str, int] = {}
        for r in self._records:
            by_type[r.experiment_type] = by_type.get(r.experiment_type, 0) + 1

        return {
            "total_experiments": total,
            "complete": sum(1 for r in self._records if r.status == "COMPLETE"),
            "failed": sum(1 for r in self._records if r.status == "FAILED"),
            "running": sum(1 for r in self._records if r.status == "RUNNING"),
            "by_type": by_type,
            "multiple_testing_note": (
                "This registry documents all experiments run. Testing multiple "
                "strategies, parameters, assets, and timeframes creates a "
                "multiple-comparison problem. Findings must not be interpreted "
                "as statistically significant without accounting for this."
            ),
        }

    def __len__(self) -> int:
        return len(self._records)
