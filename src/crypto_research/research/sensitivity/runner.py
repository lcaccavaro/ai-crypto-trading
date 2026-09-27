"""
Sensitivity Analysis Runner — Prompt 07.

Tests a PRE-DEFINED NEIGHBORHOOD of parameter values to assess stability.
This is NOT optimization. The runner does NOT search for the best value.

Key distinctions (per Prompt 07):
    Sensitivity analysis:   "Does behavior remain stable when parameter changes slightly?"
    Optimization:           "What parameter produces the highest return?"

This runner performs the first ONLY.

Design:
    - Each sensitivity experiment creates an isolated config clone.
    - Baseline config is NEVER mutated.
    - Results are collected for comparison, never re-ranked.
    - Cost sensitivity multiplies existing fee/slippage/spread by a factor.
"""

from __future__ import annotations

import copy
import traceback
from dataclasses import dataclass
from typing import Callable

from crypto_research.backtest.engine import BacktestEngine
from crypto_research.backtest.result import BacktestResult
from crypto_research.config.schema import ProjectConfiguration, SensitivityConfig
from crypto_research.data.catalog import DataCatalog
from crypto_research.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class SensitivityResult:
    """Result of one sensitivity experiment variant."""
    label: str                # e.g. "RR=2.5" or "cost_x1.5"
    parameter: str            # what was changed
    baseline_value: float     # the baseline parameter value
    tested_value: float       # the value used in this variant
    result: BacktestResult | None
    error: str = ""

    def to_dict(self) -> dict:
        m = self.result.metrics if self.result else None
        return {
            "label": self.label,
            "parameter": self.parameter,
            "baseline_value": self.baseline_value,
            "tested_value": self.tested_value,
            "status": "COMPLETE" if self.result else "FAILED",
            "error": self.error,
            "trades": m.total_trades if m else None,
            "net_pnl": round(m.net_pnl, 4) if m else None,
            "total_R": round(m.total_R, 4) if m and m.total_R is not None else None,
            "avg_R": round(m.average_R, 4) if m and m.average_R is not None else None,
            "win_rate": round(m.win_rate, 4) if m else None,
            "max_drawdown": round(m.max_drawdown, 4) if m else None,
            "profit_factor": round(m.profit_factor, 4) if m and m.profit_factor is not None else None,
        }


def _clone_with_rr(config: ProjectConfiguration, rr: float) -> ProjectConfiguration:
    raw = config.model_dump()
    raw["risk"]["risk_reward_ratio"] = rr
    return ProjectConfiguration.model_validate(raw)


def _clone_with_cost_multiplier(config: ProjectConfiguration, multiplier: float) -> ProjectConfiguration:
    raw = config.model_dump()
    raw["costs"]["maker_fee_rate"] = round(raw["costs"]["maker_fee_rate"] * multiplier, 8)
    raw["costs"]["taker_fee_rate"] = round(raw["costs"]["taker_fee_rate"] * multiplier, 8)
    raw["execution"]["slippage_bps"] = round(raw["execution"]["slippage_bps"] * multiplier, 4)
    raw["execution"]["spread_bps"] = round(raw["execution"]["spread_bps"] * multiplier, 4)
    return ProjectConfiguration.model_validate(raw)


def _clone_with_score_threshold(config: ProjectConfiguration, threshold: float) -> ProjectConfiguration:
    raw = config.model_dump()
    raw["risk"]["opportunity_score"]["minimum_score"] = threshold
    if not raw["risk"]["opportunity_score"]["enabled"]:
        raw["risk"]["opportunity_score"]["enabled"] = True
    return ProjectConfiguration.model_validate(raw)


class SensitivityRunner:
    """
    Runs a pre-defined sensitivity neighborhood for configured parameters.

    One config clone per variant; baseline config is never mutated.
    """

    def __init__(
        self,
        base_config: ProjectConfiguration,
        catalog: DataCatalog,
        strategy_factory: Callable,
        run_id_prefix: str = "sens",
    ) -> None:
        self._base_config = base_config
        self._catalog = catalog
        self._strategy_factory = strategy_factory
        self._prefix = run_id_prefix

    def _run_variant(
        self,
        config: ProjectConfiguration,
        label: str,
        parameter: str,
        baseline_value: float,
        tested_value: float,
    ) -> SensitivityResult:
        """Execute one variant. Returns SensitivityResult regardless of success/failure."""
        import uuid
        run_id = f"{self._prefix}-{label.replace('=', '').replace('.', 'p')}-{uuid.uuid4().hex[:6]}"
        try:
            strategy = self._strategy_factory()
            engine = BacktestEngine(self._catalog, config)
            result = engine.run(strategy, run_id)
            logger.info(f"Sensitivity variant '{label}' complete", net_pnl=round(result.metrics.net_pnl, 2))
            return SensitivityResult(
                label=label,
                parameter=parameter,
                baseline_value=baseline_value,
                tested_value=tested_value,
                result=result,
            )
        except Exception:
            err = traceback.format_exc()
            logger.error(f"Sensitivity variant '{label}' failed", error=err)
            return SensitivityResult(
                label=label,
                parameter=parameter,
                baseline_value=baseline_value,
                tested_value=tested_value,
                result=None,
                error=f"ENGINE_FAILED: {err}",
            )

    def run_rr_sensitivity(self, sensitivity_cfg: SensitivityConfig) -> list[SensitivityResult]:
        """Test a neighborhood of risk-reward ratios (no optimization)."""
        baseline_rr = self._base_config.risk.risk_reward_ratio
        results = []
        for rr in sensitivity_cfg.risk_reward_ratios:
            config = _clone_with_rr(self._base_config, rr)
            label = f"RR={rr}"
            results.append(self._run_variant(config, label, "risk_reward_ratio", baseline_rr, rr))
        return results

    def run_cost_sensitivity(self, sensitivity_cfg: SensitivityConfig) -> list[SensitivityResult]:
        """Test multiple cost multipliers (adverse cost scenarios)."""
        results = []
        for multiplier in sensitivity_cfg.cost_multipliers:
            config = _clone_with_cost_multiplier(self._base_config, multiplier)
            label = f"cost_x{multiplier}"
            results.append(self._run_variant(config, label, "cost_multiplier", 1.0, multiplier))
        return results

    def run_score_threshold_sensitivity(self, sensitivity_cfg: SensitivityConfig) -> list[SensitivityResult]:
        """Test different opportunity score thresholds."""
        baseline_threshold = self._base_config.risk.opportunity_score.minimum_score
        results = []
        for threshold in sensitivity_cfg.score_thresholds:
            config = _clone_with_score_threshold(self._base_config, threshold)
            label = f"score_threshold={threshold}"
            results.append(
                self._run_variant(config, label, "opportunity_score.minimum_score", baseline_threshold, threshold)
            )
        return results

    def run_all(self, sensitivity_cfg: SensitivityConfig) -> dict[str, list[SensitivityResult]]:
        """Run all configured sensitivity experiments. Returns results grouped by parameter."""
        return {
            "risk_reward": self.run_rr_sensitivity(sensitivity_cfg),
            "cost": self.run_cost_sensitivity(sensitivity_cfg),
            "score_threshold": self.run_score_threshold_sensitivity(sensitivity_cfg),
        }
