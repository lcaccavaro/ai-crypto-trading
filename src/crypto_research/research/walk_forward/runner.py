"""
Walk-Forward Runner.

Executes the BacktestEngine over each walk-forward window (TRAIN, VALIDATION, OOS)
and collects results per period.

Design:
    - The runner receives a strategy factory (callable → strategy instance) so
      a fresh strategy state is created for every window.
    - Config is cloned per window to ensure immutability between experiments.
    - Engine state is NOT shared between windows.
    - Each window execution records its own BacktestResult.
    - Failures are recorded, never silently ignored.

PIT Guarantee:
    The runner passes `window.train_start / train_end` as `backtest.start_date /
    end_date` in the config clone. The engine loads ONLY data in that range.
    No future OOS information is accessible.
"""

from __future__ import annotations

import copy
import traceback
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable

from crypto_research.backtest.engine import BacktestEngine
from crypto_research.backtest.metrics import BacktestMetrics, compute_metrics
from crypto_research.backtest.result import BacktestResult
from crypto_research.config.schema import ProjectConfiguration
from crypto_research.data.catalog import DataCatalog
from crypto_research.research.walk_forward.splitter import WalkForwardWindow
from crypto_research.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class WindowResult:
    """Result of one walk-forward window across all three periods."""

    window: WalkForwardWindow
    run_id: str

    train_result: BacktestResult | None = None
    val_result: BacktestResult | None = None
    oos_result: BacktestResult | None = None

    train_error: str | None = None
    val_error: str | None = None
    oos_error: str | None = None

    status: str = "PENDING"  # PENDING | COMPLETE | FAILED

    @property
    def oos_metrics(self) -> BacktestMetrics | None:
        if self.oos_result is not None:
            return self.oos_result.metrics
        return None

    @property
    def train_metrics(self) -> BacktestMetrics | None:
        if self.train_result is not None:
            return self.train_result.metrics
        return None

    def to_summary_dict(self) -> dict:
        """Flat dict for CSV export."""
        w = self.window
        oos = self.oos_metrics
        train = self.train_metrics
        return {
            "window_id": w.window_id,
            "run_id": self.run_id,
            "mode": w.mode,
            "status": self.status,
            "train_start": w.train_start.isoformat(),
            "train_end": w.train_end.isoformat(),
            "val_start": w.val_start.isoformat(),
            "val_end": w.val_end.isoformat(),
            "oos_start": w.oos_start.isoformat(),
            "oos_end": w.oos_end.isoformat(),
            # OOS metrics
            "oos_trades": oos.total_trades if oos else 0,
            "oos_net_pnl": round(oos.net_pnl, 4) if oos else None,
            "oos_total_R": round(oos.total_R, 4) if oos and oos.total_R is not None else None,
            "oos_avg_R": round(oos.average_R, 4) if oos and oos.average_R is not None else None,
            "oos_win_rate": round(oos.win_rate, 4) if oos else None,
            "oos_max_drawdown": round(oos.max_drawdown, 4) if oos else None,
            "oos_profit_factor": round(oos.profit_factor, 4) if oos and oos.profit_factor is not None else None,
            # Train metrics (reference)
            "train_trades": train.total_trades if train else 0,
            "train_net_pnl": round(train.net_pnl, 4) if train else None,
            "train_win_rate": round(train.win_rate, 4) if train else None,
            # Errors
            "train_error": self.train_error or "",
            "oos_error": self.oos_error or "",
        }


def _clone_config_for_window(
    base_config: ProjectConfiguration,
    start_date: str,
    end_date: str,
) -> ProjectConfiguration:
    """
    Return a config clone with backtest dates overridden.
    Does NOT mutate base_config.
    """
    raw = base_config.model_dump()
    raw["backtest"]["start_date"] = start_date
    raw["backtest"]["end_date"] = end_date
    return ProjectConfiguration.model_validate(raw)


class WalkForwardRunner:
    """
    Executes the BacktestEngine over walk-forward windows.

    Usage:
        runner = WalkForwardRunner(
            base_config=config,
            catalog=catalog,
            strategy_factory=lambda: MyStrategy(config),
        )
        results = runner.run_all(windows)
    """

    def __init__(
        self,
        base_config: ProjectConfiguration,
        catalog: DataCatalog,
        strategy_factory: Callable,
    ) -> None:
        self._base_config = base_config
        self._catalog = catalog
        self._strategy_factory = strategy_factory

    def _run_period(
        self,
        window_id: int,
        period_name: str,
        start: datetime,
        end: datetime,
    ) -> tuple[BacktestResult | None, str | None]:
        """
        Execute engine for a single period. Returns (result, error_str).
        Never raises — errors are captured and returned as strings.
        """
        start_str = start.strftime("%Y-%m-%d")
        end_str = end.strftime("%Y-%m-%d")

        try:
            config = _clone_config_for_window(self._base_config, start_str, end_str)
        except Exception:
            err = traceback.format_exc()
            logger.error(
                f"Window {window_id} {period_name}: config clone failed",
                error=err,
            )
            return None, f"CONFIG_CLONE_FAILED: {err}"

        run_id = f"wf-w{window_id:03d}-{period_name.lower()}-{uuid.uuid4().hex[:8]}"

        try:
            strategy = self._strategy_factory()
            engine = BacktestEngine(self._catalog, config)
            result = engine.run(strategy, run_id)
            logger.info(
                f"Window {window_id} {period_name} complete",
                trades=result.metrics.total_trades,
                net_pnl=round(result.metrics.net_pnl, 2),
            )
            return result, None
        except Exception:
            err = traceback.format_exc()
            logger.error(
                f"Window {window_id} {period_name}: engine failed",
                run_id=run_id,
                error=err,
            )
            return None, f"ENGINE_FAILED: {err}"

    def run_window(self, window: WalkForwardWindow, run_id_prefix: str) -> WindowResult:
        """
        Execute TRAIN, VALIDATION, and OOS periods for one window.
        Failures in one period do not abort the others.
        """
        wr = WindowResult(
            window=window,
            run_id=f"{run_id_prefix}-w{window.window_id:03d}",
        )

        # TRAIN
        wr.train_result, wr.train_error = self._run_period(
            window.window_id, "TRAIN", window.train_start, window.train_end
        )

        # VALIDATION
        wr.val_result, wr.val_error = self._run_period(
            window.window_id, "VAL", window.val_start, window.val_end
        )

        # OOS
        wr.oos_result, wr.oos_error = self._run_period(
            window.window_id, "OOS", window.oos_start, window.oos_end
        )

        if wr.oos_error:
            wr.status = "FAILED"
        else:
            wr.status = "COMPLETE"

        return wr

    def run_all(
        self, windows: list[WalkForwardWindow], run_id_prefix: str = "wf"
    ) -> list[WindowResult]:
        """
        Execute all windows. Returns results in chronological order.
        Never raises — individual window failures are recorded in WindowResult.
        """
        results: list[WindowResult] = []

        for window in windows:
            logger.info(
                "Starting walk-forward window",
                window_id=window.window_id,
                oos_start=window.oos_start.isoformat(),
                oos_end=window.oos_end.isoformat(),
            )
            wr = self.run_window(window, run_id_prefix)
            results.append(wr)

        complete = sum(1 for r in results if r.status == "COMPLETE")
        failed = sum(1 for r in results if r.status == "FAILED")
        logger.info(
            "Walk-forward run complete",
            total=len(results),
            complete=complete,
            failed=failed,
        )
        return results
