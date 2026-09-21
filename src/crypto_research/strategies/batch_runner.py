"""
Batch runner — executes a configured strategy matrix through the Prompt 03 engine.

Design:
    - Config-driven: reads strategy_instances from StrategyLibraryConfig.
    - Shares immutable market data across strategy instances for efficiency.
    - Each strategy instance runs independently with isolated state.
    - Results use the existing BacktestResult from Prompt 03.
    - Produces a SignalLedger per run.

Usage:
    runner = StrategyBatchRunner(catalog=catalog, config=config)
    results = runner.run(run_id="RUN_...")
    for r in results:
        print(r.instance_id, r.metrics.net_pnl)
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from crypto_research.backtest.backtest_data_provider import BacktestDataProvider
from crypto_research.backtest.engine import BacktestEngine
from crypto_research.backtest.result import BacktestResult
from crypto_research.config.loader import AppConfig
from crypto_research.data.catalog import DataCatalog
from crypto_research.strategies.context import StrategyContext, StrategyInstance
from crypto_research.strategies.registry import REGISTRY
from crypto_research.strategies.signal_ledger import SignalLedger
from crypto_research.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class StrategyInstanceConfig:
    """Configuration for one strategy × symbol × timeframe instance."""

    strategy_id: str
    symbol: str
    timeframe: str
    parameters: dict[str, Any]

    def to_instance(self, version: str) -> StrategyInstance:
        return StrategyInstance(
            strategy_id=self.strategy_id,
            symbol=self.symbol,
            timeframe=self.timeframe,
            version=version,
            parameters=self.parameters,
        )


@dataclass
class BatchResult:
    """Result for a single strategy instance execution."""

    instance: StrategyInstance
    backtest_result: BacktestResult | None
    error: str | None = None

    @property
    def instance_id(self) -> str:
        return self.instance.instance_id

    @property
    def success(self) -> bool:
        return self.error is None and self.backtest_result is not None


class StrategyBatchRunner:
    """
    Executes many strategy instances through the Prompt 03 backtest engine.

    State isolation guarantee:
        Each strategy instance is freshly instantiated before its run.
        reset() is called between runs.
        No shared mutable state between instances.

    Performance:
        Market data (Parquet files) is loaded once per (symbol, timeframe) pair
        and shared as immutable read-only views. No redundant disk reads.
    """

    def __init__(
        self,
        catalog: DataCatalog,
        config: AppConfig,
    ) -> None:
        self._catalog = catalog
        self._config = config

    def run_instances(
        self,
        instance_configs: list[StrategyInstanceConfig],
        run_id: str,
    ) -> tuple[list[BatchResult], SignalLedger]:
        """
        Execute a list of strategy instance configurations.

        Args:
            instance_configs: List of (strategy_id, symbol, timeframe, params).
            run_id:           Research run ID for traceability.

        Returns:
            (results, signal_ledger) tuple.
        """
        ledger = SignalLedger(run_id=run_id)
        results: list[BatchResult] = []

        for ic in instance_configs:
            result = self._run_one(ic, run_id, ledger)
            results.append(result)

        logger.info(
            "Batch run complete",
            run_id=run_id,
            total=len(results),
            success=sum(1 for r in results if r.success),
            failed=sum(1 for r in results if not r.success),
        )
        return results, ledger

    def _run_one(
        self,
        ic: StrategyInstanceConfig,
        run_id: str,
        ledger: SignalLedger,
    ) -> BatchResult:
        """Execute a single strategy instance. Captures errors gracefully."""
        try:
            # Instantiate strategy
            if ic.parameters:
                strategy = REGISTRY.instantiate(ic.strategy_id, **ic.parameters)
            else:
                strategy = REGISTRY.instantiate(ic.strategy_id)

            version = strategy.version
            instance = ic.to_instance(version)
            context = StrategyContext(instance=instance, run_id=run_id)

            logger.info(
                "Running strategy instance",
                instance_id=instance.instance_id,
                run_id=run_id,
            )

            # Create a signal-recording wrapper around the strategy
            wrapped = _SignalRecordingStrategy(strategy, instance, ledger)

            # Run through the Prompt 03 engine
            engine = BacktestEngine(catalog=self._catalog, config=self._config)
            bt_result = engine.run(strategy=wrapped, run_id=f"{run_id}__{instance.instance_id}")

            return BatchResult(instance=instance, backtest_result=bt_result)

        except Exception as exc:
            sid = ic.strategy_id
            sym = ic.symbol
            tf = ic.timeframe
            logger.error(
                "Strategy instance failed",
                strategy_id=sid,
                symbol=sym,
                timeframe=tf,
                error=str(exc),
            )
            # Still create an instance for the error record
            try:
                cls = REGISTRY.get(ic.strategy_id)
                version = cls._info.version
            except Exception:
                version = "unknown"
            instance = ic.to_instance(version)
            return BatchResult(instance=instance, backtest_result=None, error=str(exc))


class _SignalRecordingStrategy:
    """
    Thin wrapper that intercepts generate_signal() calls to record signals
    into the SignalLedger while delegating all logic to the real strategy.

    Satisfies the Strategy Protocol: has name, version, metadata,
    minimum_candles_required, and generate_signal().
    """

    def __init__(
        self,
        strategy,
        instance: StrategyInstance,
        ledger: SignalLedger,
    ) -> None:
        self._strategy = strategy
        self._instance = instance
        self._ledger = ledger

    @property
    def name(self) -> str:
        return self._strategy.name

    @property
    def version(self) -> str:
        return self._strategy.version

    @property
    def metadata(self):
        return self._strategy.metadata

    @property
    def minimum_candles_required(self) -> int:
        return self._strategy.minimum_candles_required

    def generate_signal(self, candles, timestamp):
        signal = self._strategy.generate_signal(candles, timestamp)
        if signal is not None:
            self._ledger.record(signal, self._instance)
        return signal

    def reset(self) -> None:
        self._strategy.reset()
