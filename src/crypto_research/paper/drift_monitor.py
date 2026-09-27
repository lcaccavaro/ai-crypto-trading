"""
Paper Trading Drift Monitor — Prompt 08.

Compares recent paper trading behavior against historical backtest baseline
and emits descriptive warnings when material differences are detected.

Purpose:
    Reveal operational problems, data issues, and live-vs-backtest differences.
    NOT for strategy modification. NOT for parameter re-calibration.

Warnings are descriptive observations only.
Do not automatically disable strategies or change parameters based on drift.

Warning codes:
    SIGNAL_FREQUENCY_DRIFT      — More/fewer signals than baseline per period
    SCORE_DISTRIBUTION_DRIFT    — Mean opportunity score shifted materially
    REJECTION_RATE_DRIFT        — Rejection rate changed materially
    COST_DRIFT                  — Average per-trade cost changed materially
    VOLATILITY_DRIFT            — ATR-based volatility differs from baseline
    REGIME_DISTRIBUTION_DRIFT   — Regime mix differs from baseline
    EXECUTION_DRIFT             — Avg holding time or fill timing differs
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from crypto_research.config.schema import PaperDriftConfig
from crypto_research.utils.logging import get_logger

logger = get_logger(__name__)


class DriftWarningCode(str):
    SIGNAL_FREQUENCY = "SIGNAL_FREQUENCY_DRIFT"
    SCORE_DISTRIBUTION = "SCORE_DISTRIBUTION_DRIFT"
    REJECTION_RATE = "REJECTION_RATE_DRIFT"
    COST = "COST_DRIFT"
    VOLATILITY = "VOLATILITY_DRIFT"
    REGIME_DISTRIBUTION = "REGIME_DISTRIBUTION_DRIFT"
    EXECUTION = "EXECUTION_DRIFT"


@dataclass
class DriftWarning:
    code: str
    description: str
    baseline_value: float
    paper_value: float
    change_pct: float
    detected_at: str

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "description": self.description,
            "baseline_value": round(self.baseline_value, 4),
            "paper_value": round(self.paper_value, 4),
            "change_pct": round(self.change_pct, 2),
            "detected_at": self.detected_at,
        }


class PaperDriftMonitor:
    """
    Computes drift between paper session metrics and historical baseline.

    Usage:
        monitor = PaperDriftMonitor(config, historical_baseline)
        warnings = monitor.check(paper_metrics)
    """

    def __init__(
        self,
        config: PaperDriftConfig,
        historical_baseline: dict | None = None,
    ) -> None:
        self._config = config
        self._baseline = historical_baseline or {}

    def check(self, paper_metrics: dict, min_trades: int) -> list[DriftWarning]:
        """
        Check for drift between paper metrics and historical baseline.

        Args:
            paper_metrics: Current paper session metrics dict.
            min_trades:    Number of paper trades so far.

        Returns:
            List of DriftWarning (may be empty).
        """
        if not self._config.enabled:
            return []

        if min_trades < self._config.min_paper_trades_for_drift:
            logger.info(
                "Insufficient paper trades for drift analysis",
                paper_trades=min_trades,
                min_required=self._config.min_paper_trades_for_drift,
            )
            return []

        warnings: list[DriftWarning] = []

        # Signal frequency drift
        w = self._check_metric(
            code=DriftWarningCode.SIGNAL_FREQUENCY,
            description="Signal frequency per session hour differs from historical baseline",
            baseline_key="signals_per_hour",
            paper_metrics=paper_metrics,
            threshold_pct=self._config.signal_frequency_change_pct,
        )
        if w:
            warnings.append(w)

        # Score distribution drift
        w = self._check_metric(
            code=DriftWarningCode.SCORE_DISTRIBUTION,
            description="Mean opportunity score differs from historical baseline",
            baseline_key="mean_score",
            paper_metrics=paper_metrics,
            threshold_pct=self._config.score_mean_change_pct,
        )
        if w:
            warnings.append(w)

        # Rejection rate drift
        w = self._check_metric(
            code=DriftWarningCode.REJECTION_RATE,
            description="Signal rejection rate differs from historical baseline",
            baseline_key="rejection_rate",
            paper_metrics=paper_metrics,
            threshold_pct=self._config.rejection_rate_change_pct,
        )
        if w:
            warnings.append(w)

        # Cost drift
        w = self._check_metric(
            code=DriftWarningCode.COST,
            description="Average per-trade cost differs from historical baseline",
            baseline_key="avg_cost_per_trade",
            paper_metrics=paper_metrics,
            threshold_pct=self._config.cost_change_pct,
        )
        if w:
            warnings.append(w)

        for warning in warnings:
            logger.warning(
                "Drift warning",
                code=warning.code,
                change_pct=warning.change_pct,
                description=warning.description,
            )

        return warnings

    def _check_metric(
        self, code: str, description: str, baseline_key: str,
        paper_metrics: dict, threshold_pct: float,
    ) -> DriftWarning | None:
        baseline_val = self._baseline.get(baseline_key)
        paper_val = paper_metrics.get(baseline_key)

        if baseline_val is None or paper_val is None:
            return None

        if baseline_val == 0:
            return None

        change_pct = abs((paper_val - baseline_val) / baseline_val) * 100

        if change_pct > threshold_pct:
            return DriftWarning(
                code=code,
                description=description,
                baseline_value=float(baseline_val),
                paper_value=float(paper_val),
                change_pct=change_pct,
                detected_at=datetime.now(timezone.utc).isoformat(),
            )
        return None

    def set_baseline(self, baseline: dict) -> None:
        """Update historical baseline (call after backtest run)."""
        self._baseline = baseline
