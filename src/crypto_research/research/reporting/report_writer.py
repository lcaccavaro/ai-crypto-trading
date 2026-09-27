"""
Prompt 07 Research Report Writer.

Writes all robustness research artifacts to the run's output directory:

    results/<run_id>/robustness/
        experiment_registry.csv
        experiment_registry.json
        walk_forward/
            windows.csv
            train_results.csv
            oos_results.csv
            summary.json
        sensitivity/
            parameter_sensitivity.csv
            cost_sensitivity.csv
            summary.json
        regimes/
            regime_definitions.json
            regime_periods.csv
            regime_trade_metrics.csv
            regime_summary.json
        warnings/
            robustness_warnings.csv
        robustness_summary.json
    reports/
        ROBUSTNESS_REPORT.md

Does NOT build a second reporting system — integrates with the existing
results/ directory structure from Prompt 03's BacktestResultWriter.
"""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_research.research.experiments.registry import ExperimentRegistry
from crypto_research.research.regimes.analyzer import RegimeTradeStats
from crypto_research.research.robustness.metrics import OOSStabilityMetrics
from crypto_research.research.robustness.warnings import ResearchWarning
from crypto_research.research.sensitivity.runner import SensitivityResult
from crypto_research.research.walk_forward.runner import WindowResult
from crypto_research.research.walk_forward.splitter import WalkForwardWindow
from crypto_research.utils.logging import get_logger

logger = get_logger(__name__)


def _write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        json.dump(data, f, indent=2, default=str)


class RobustnessReportWriter:
    """
    Writes all Prompt 07 research outputs to the run's result directory.

    Usage:
        writer = RobustnessReportWriter(run_id="run_xyz", results_root="results/")
        writer.write_walk_forward(windows, window_results, stability_metrics)
        writer.write_sensitivity(rr_results, cost_results)
        writer.write_regime(regime_stats)
        writer.write_warnings(warnings)
        writer.write_experiment_registry(registry)
        writer.write_robustness_summary(...)
        writer.write_markdown_report(...)
    """

    def __init__(self, run_id: str, results_root: str | Path = "results") -> None:
        self._run_id = run_id
        self._root = Path(results_root) / run_id / "robustness"
        self._reports_root = Path(results_root) / run_id / "reports"

    # ─── Walk-Forward ────────────────────────────────────────────────────────

    def write_walk_forward(
        self,
        windows: list[WalkForwardWindow],
        results: list[WindowResult],
        stability: OOSStabilityMetrics,
    ) -> None:
        wf_dir = self._root / "walk_forward"

        # windows.csv
        _write_csv(wf_dir / "windows.csv", [w.to_dict() for w in windows])

        # oos_results.csv and train_results.csv
        _write_csv(wf_dir / "oos_results.csv", [r.to_summary_dict() for r in results])
        _write_csv(wf_dir / "train_results.csv", [r.to_summary_dict() for r in results])

        # summary.json
        _write_json(wf_dir / "summary.json", {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "run_id": self._run_id,
            "total_windows": len(windows),
            "stability": stability.to_dict(),
        })
        logger.info(f"Walk-forward artifacts written to {wf_dir}")

    # ─── Sensitivity ─────────────────────────────────────────────────────────

    def write_sensitivity(
        self,
        rr_results: list[SensitivityResult],
        cost_results: list[SensitivityResult],
        score_results: list[SensitivityResult] | None = None,
    ) -> None:
        sens_dir = self._root / "sensitivity"

        _write_csv(sens_dir / "parameter_sensitivity.csv", [r.to_dict() for r in rr_results])
        _write_csv(sens_dir / "cost_sensitivity.csv", [r.to_dict() for r in cost_results])
        if score_results:
            _write_csv(sens_dir / "score_sensitivity.csv", [r.to_dict() for r in score_results])

        _write_json(sens_dir / "summary.json", {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "run_id": self._run_id,
            "rr_variants": len(rr_results),
            "cost_variants": len(cost_results),
            "score_variants": len(score_results) if score_results else 0,
            "sensitivity_disclaimer": (
                "Sensitivity analysis is NOT optimization. "
                "These results show stability of a pre-defined neighborhood, "
                "not the optimal parameter value."
            ),
        })
        logger.info(f"Sensitivity artifacts written to {sens_dir}")

    # ─── Regimes ─────────────────────────────────────────────────────────────

    def write_regime(
        self,
        regime_stats: list[RegimeTradeStats],
        regime_definitions: dict,
    ) -> None:
        reg_dir = self._root / "regimes"
        _write_json(reg_dir / "regime_definitions.json", regime_definitions)
        _write_csv(reg_dir / "regime_trade_metrics.csv", [s.to_dict() for s in regime_stats])

        total_pnl = sum(s.net_pnl for s in regime_stats)
        summary = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "run_id": self._run_id,
            "regimes_observed": [s.regime for s in regime_stats],
            "total_pnl_across_regimes": round(total_pnl, 4),
            "regime_pnl_shares": {
                s.regime: round(s.net_pnl / total_pnl * 100, 2) if total_pnl != 0 else 0
                for s in regime_stats
            },
        }
        _write_json(reg_dir / "regime_summary.json", summary)
        logger.info(f"Regime artifacts written to {reg_dir}")

    # ─── Warnings ────────────────────────────────────────────────────────────

    def write_warnings(self, warnings: list[ResearchWarning]) -> None:
        warn_dir = self._root / "warnings"
        _write_csv(warn_dir / "robustness_warnings.csv", [w.to_dict() for w in warnings])
        logger.info(f"Robustness warnings written: {len(warnings)} warning(s)")

    # ─── Registry ────────────────────────────────────────────────────────────

    def write_experiment_registry(self, registry: ExperimentRegistry) -> None:
        registry.to_csv(self._root / "experiment_registry.csv")
        registry.to_json(self._root / "experiment_registry.json")

    # ─── Summary ─────────────────────────────────────────────────────────────

    def write_robustness_summary(
        self,
        stability: OOSStabilityMetrics,
        all_warnings: list[ResearchWarning],
        experiment_summary: dict,
        baseline_config_summary: dict,
    ) -> None:
        summary = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "run_id": self._run_id,
            "baseline": baseline_config_summary,
            "oos_stability": stability.to_dict(),
            "warnings": [w.to_dict() for w in all_warnings],
            "warning_count": len(all_warnings),
            "experiments": experiment_summary,
            "multiple_testing_disclosure": (
                "This research evaluated multiple strategies, parameters, assets, "
                "timeframes, and cost assumptions. Each additional test increases "
                "the probability of observing a spuriously good result by chance. "
                "Treat all findings as hypotheses for further investigation, "
                "not as evidence of future profitability."
            ),
        }
        _write_json(self._root / "robustness_summary.json", summary)
        logger.info(f"Robustness summary written to {self._root / 'robustness_summary.json'}")

    # ─── Markdown Report ─────────────────────────────────────────────────────

    def write_markdown_report(
        self,
        windows: list[WalkForwardWindow],
        stability: OOSStabilityMetrics,
        rr_results: list[SensitivityResult],
        cost_results: list[SensitivityResult],
        regime_stats: list[RegimeTradeStats],
        all_warnings: list[ResearchWarning],
        baseline_config_summary: dict,
        run_type: str = "DEVELOPMENT",
    ) -> None:
        report_path = self._reports_root / "ROBUSTNESS_REPORT.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)

        lines = [
            f"# Robustness & Walk-Forward Report",
            f"",
            f"**Run ID:** `{self._run_id}`  ",
            f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}  ",
            f"**Run Type:** `{run_type}`  ",
            f"",
            f"> **Disclaimer:** This report is a historical research summary.",
            f"> It does not constitute evidence of future profitability.",
            f"> Do not interpret any finding as a recommendation for live trading.",
            f"",
            f"---",
            f"",
            f"## 1. Baseline Configuration",
            f"",
            f"```json",
            json.dumps(baseline_config_summary, indent=2),
            f"```",
            f"",
            f"---",
            f"",
            f"## 2. Walk-Forward Analysis",
            f"",
            f"| Parameter | Value |",
            f"|-----------|-------|",
            f"| Mode | `{windows[0].mode if windows else 'N/A'}` |",
            f"| Total Windows | {stability.total_windows} |",
            f"| Valid OOS Windows | {stability.valid_windows} |",
            f"| Positive OOS Windows | {stability.positive_oos_windows} ({stability.pct_positive_windows:.1%}) |",
            f"| Total OOS Trades | {stability.total_oos_trades} |",
            f"| Median OOS Net P&L | {stability.median_oos_net_pnl:.4f} |" if stability.median_oos_net_pnl is not None else "| Median OOS Net P&L | N/A |",
            f"| Worst OOS Window P&L | {stability.min_oos_net_pnl:.4f} |" if stability.min_oos_net_pnl is not None else "| Worst OOS Window P&L | N/A |",
            f"| Best OOS Window P&L | {stability.max_oos_net_pnl:.4f} |" if stability.max_oos_net_pnl is not None else "| Best OOS Window P&L | N/A |",
            f"",
            f"---",
            f"",
            f"## 3. Parameter Sensitivity (Risk-Reward)",
            f"",
            f"*Sensitivity analysis tests a pre-defined neighborhood.*",
            f"*It is NOT optimization. No parameter is selected as 'best'.*",
            f"",
            f"| Label | Tested RR | Trades | Net P&L | Win Rate |",
            f"|-------|-----------|--------|---------|----------|",
        ]

        for r in rr_results:
            m = r.result.metrics if r.result else None
            pnl_str = f"{m.net_pnl:.4f}" if m else "ERR"
            wr_str = f"{m.win_rate:.2%}" if m else "ERR"
            trades_str = str(m.total_trades) if m else "ERR"
            lines.append(
                f"| {r.label} | {r.tested_value} | {trades_str} | {pnl_str} | {wr_str} |"
            )

        lines += [
            f"",
            f"---",
            f"",
            f"## 4. Cost Sensitivity",
            f"",
            f"| Label | Cost Multiplier | Trades | Net P&L | Win Rate |",
            f"|-------|-----------------|--------|---------|----------|",
        ]

        for r in cost_results:
            m = r.result.metrics if r.result else None
            pnl_str = f"{m.net_pnl:.4f}" if m else "ERR"
            wr_str = f"{m.win_rate:.2%}" if m else "ERR"
            trades_str = str(m.total_trades) if m else "ERR"
            lines.append(
                f"| {r.label} | {r.tested_value}x | {trades_str} | {pnl_str} | {wr_str} |"
            )

        lines += [
            f"",
            f"---",
            f"",
            f"## 5. Regime Analysis",
            f"",
            f"| Regime | Trades | Net P&L | Win Rate | Avg R |",
            f"|--------|--------|---------|----------|-------|",
        ]

        for s in regime_stats:
            lines.append(
                f"| {s.regime} | {s.trade_count} | {s.net_pnl:.4f} | "
                f"{s.win_rate:.2%} | {s.avg_R:.4f if s.avg_R is not None else 'N/A'} |"
            )

        lines += [
            f"",
            f"---",
            f"",
            f"## 6. Robustness Warnings",
            f"",
            f"*Warnings are diagnostic flags, not proof of failure or overfitting.*",
            f"",
        ]

        if not all_warnings:
            lines.append("*No warnings generated.*")
        else:
            for w in all_warnings:
                lines.append(f"- **{w.code.value}** — {w.description}")
                lines.append(f"  - Evidence: `{w.evidence}`")

        lines += [
            f"",
            f"---",
            f"",
            f"## 7. Research Interpretation",
            f"",
            f"*The following is a factual summary of historical observations.*",
            f"*No future performance is implied. No strategy is ranked or selected.*",
            f"",
            f"- Walk-forward analysis evaluated {stability.total_windows} windows "
            f"with {stability.valid_windows} valid OOS periods.",
            f"- {stability.positive_oos_windows} of {stability.valid_windows} valid OOS windows "
            f"produced positive net P&L ({stability.pct_positive_windows:.1%}).",
        ]

        if all_warnings:
            lines.append(f"- {len(all_warnings)} robustness warning(s) were generated. See section 6.")

        lines += [
            f"",
            f"---",
            f"",
            f"## 8. Multiple Testing Disclosure",
            f"",
            f"This research evaluated multiple parameters, cost assumptions, assets, and regimes.",
            f"Each additional test increases the probability of observing a spuriously positive",
            f"result by chance. The experiment registry documents all experiments run.",
            f"Findings should be treated as hypotheses for further investigation,",
            f"not as evidence of future profitability.",
            f"",
            f"---",
            f"",
            f"*END OF ROBUSTNESS REPORT*",
        ]

        report_path.write_text("\n".join(lines))
        logger.info(f"Robustness Markdown report written to {report_path}")
