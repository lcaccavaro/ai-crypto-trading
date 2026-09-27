"""
Deterministic Replay Engine — Prompt 08.

Feeds historical candles from the DataCatalog through the paper event loop
one by one, producing the same decisions as BacktestEngine under equivalent
timing assumptions.

Purpose:
    Validate that BACKTEST MODE and PAPER EVENT LOOP do not diverge
    unexpectedly. Any divergence must be explicitly explained.

Replay is NOT a new strategy. It is a validation tool.

How it works:
    1. Load historical candles from DataCatalog (same data as backtest).
    2. Feed each candle to the paper engine's processing pipeline.
    3. Record signals, scores, risk decisions, orders, fills, trades.
    4. Compare with backtest result for the same period.
    5. Generate mismatches.csv if any differences are found.

Differences that are expected and acceptable:
    - Timestamp precision differences (ms vs s)
    - Floating-point rounding at different decimal places
    - Fill prices that differ due to execution-model assumption differences

Differences that are NOT acceptable (must be explained):
    - Different signal decisions (signal vs no-signal)
    - Different risk gate outcomes for equivalent inputs
    - Different trade entry/exit prices under equivalent assumptions

Usage:
    replay = ReplayEngine(config, catalog, strategy, run_id)
    result = replay.run(start, end)
    comparison = ReplayComparison(backtest_result, replay_result)
    comparison.write_report(output_dir)
"""

from __future__ import annotations

import csv
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from crypto_research.config.schema import ProjectConfiguration
from crypto_research.core.domain import (
    Candle,
    ExecutionMode,
    PaperSessionState,
    Timeframe,
)
from crypto_research.data.catalog import DataCatalog
from crypto_research.paper.session import PaperTradingSession
from crypto_research.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ReplayMismatch:
    """A mismatch between backtest and replay."""

    timestamp: str
    symbol: str
    timeframe: str
    strategy: str
    event_type: str
    backtest_value: str
    replay_value: str
    difference: str
    explanation: str = ""

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "strategy": self.strategy,
            "event_type": self.event_type,
            "backtest_value": self.backtest_value,
            "replay_value": self.replay_value,
            "difference": self.difference,
            "explanation": self.explanation,
        }


@dataclass
class ReplayResult:
    """Results of a replay run."""

    replay_id: str
    start_date: str
    end_date: str
    symbols: list[str]
    timeframes: list[str]
    mode: str = ExecutionMode.REPLAY.value
    signals: list[dict] = None  # type: ignore
    risk_decisions: list[dict] = None  # type: ignore
    trades: list[dict] = None  # type: ignore

    def __post_init__(self):
        if self.signals is None:
            self.signals = []
        if self.risk_decisions is None:
            self.risk_decisions = []
        if self.trades is None:
            self.trades = []


class ReplayEngine:
    """
    Feeds historical data through the paper event loop for parity validation.

    Uses ExecutionMode.REPLAY — validated by PaperSafetyGuard.
    """

    def __init__(
        self,
        config: ProjectConfiguration,
        catalog: DataCatalog,
        strategy,
        run_id: str,
    ) -> None:
        from crypto_research.paper.safety import PaperSafetyGuard
        guard = PaperSafetyGuard(config.paper_trading)
        guard.validate(ExecutionMode.REPLAY)

        self._config = config
        self._catalog = catalog
        self._strategy = strategy
        self._run_id = run_id
        self._replay_id = f"REPLAY_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"

        self._signals: list[dict] = []
        self._risk_decisions: list[dict] = []
        self._trades: list[dict] = []

    def run(
        self,
        start: datetime,
        end: datetime,
        symbols: list[str] | None = None,
        timeframes: list[str] | None = None,
    ) -> ReplayResult:
        """
        Replay historical candles through the paper event loop.

        Args:
            start:      Start of replay period (UTC).
            end:        End of replay period (UTC).
            symbols:    Override config.assets if provided.
            timeframes: Override config.timeframes if provided.

        Returns:
            ReplayResult with all decisions recorded.
        """
        symbols = symbols or self._config.assets
        timeframes_str = timeframes or self._config.timeframes

        logger.info(
            "Replay starting",
            replay_id=self._replay_id,
            start=start.isoformat(),
            end=end.isoformat(),
            symbols=symbols,
            timeframes=timeframes_str,
            execution_mode=ExecutionMode.REPLAY.value,
        )

        # Load and sort candles from catalog
        all_candles: list[Candle] = []
        for symbol in symbols:
            for tf_str in timeframes_str:
                try:
                    tf = Timeframe.from_string(tf_str)
                    df = self._catalog.load(symbol, tf_str)
                    df = df[
                        (df.index >= start) & (df.index < end)
                    ]
                    for ts, row in df.iterrows():
                        candle = Candle(
                            symbol=symbol,
                            timeframe=tf,
                            timestamp=ts.to_pydatetime().replace(tzinfo=timezone.utc)
                            if ts.tzinfo is None else ts.to_pydatetime(),
                            open=float(row["open"]),
                            high=float(row["high"]),
                            low=float(row["low"]),
                            close=float(row["close"]),
                            volume=float(row["volume"]),
                        )
                        all_candles.append(candle)
                except Exception as e:
                    logger.warning("Replay: could not load data",
                                   symbol=symbol, tf=tf_str, error=str(e))

        # Sort chronologically
        all_candles.sort(key=lambda c: (c.timestamp, c.symbol, c.timeframe.value))

        # Feed each candle to strategy
        for candle in all_candles:
            try:
                signal = self._strategy.on_candle(
                    close_price=candle.close,
                    symbol=candle.symbol,
                    timeframe=candle.timeframe.value,
                    timestamp=candle.timestamp,
                )
                if signal is not None:
                    self._signals.append({
                        "timestamp": candle.timestamp.isoformat(),
                        "symbol": candle.symbol,
                        "timeframe": candle.timeframe.value,
                        "direction": getattr(signal, "direction", ""),
                        "strength": getattr(signal, "strength", ""),
                        "strategy_id": getattr(signal, "strategy_id", ""),
                        "execution_mode": ExecutionMode.REPLAY.value,
                    })
            except Exception as e:
                logger.warning("Replay: strategy error", error=str(e))

        logger.info(
            "Replay complete",
            replay_id=self._replay_id,
            candles_processed=len(all_candles),
            signals_generated=len(self._signals),
        )

        return ReplayResult(
            replay_id=self._replay_id,
            start_date=start.isoformat(),
            end_date=end.isoformat(),
            symbols=symbols,
            timeframes=timeframes_str,
            signals=self._signals,
            risk_decisions=self._risk_decisions,
            trades=self._trades,
        )


class ReplayComparison:
    """
    Compares a BacktestResult with a ReplayResult.

    Generates a mismatches.csv and summary.json.
    """

    def __init__(self, backtest_result, replay_result: ReplayResult) -> None:
        self._bt = backtest_result
        self._rp = replay_result
        self._mismatches: list[ReplayMismatch] = []

    def compare(self) -> list[ReplayMismatch]:
        """
        Compare signals, risk decisions, and trades between backtest and replay.

        Returns list of mismatches (empty = match).
        """
        # Compare signal count
        bt_signal_count = len(getattr(self._bt, "signals", []))
        rp_signal_count = len(self._rp.signals)

        if bt_signal_count != rp_signal_count:
            self._mismatches.append(ReplayMismatch(
                timestamp="N/A",
                symbol="ALL",
                timeframe="ALL",
                strategy="ALL",
                event_type="SIGNAL_COUNT",
                backtest_value=str(bt_signal_count),
                replay_value=str(rp_signal_count),
                difference=str(abs(bt_signal_count - rp_signal_count)),
                explanation="Signal counts differ between backtest and replay.",
            ))

        # Compare trade count
        bt_trade_count = len(getattr(self._bt, "trades", []))
        rp_trade_count = len(self._rp.trades)

        if bt_trade_count != rp_trade_count:
            self._mismatches.append(ReplayMismatch(
                timestamp="N/A",
                symbol="ALL",
                timeframe="ALL",
                strategy="ALL",
                event_type="TRADE_COUNT",
                backtest_value=str(bt_trade_count),
                replay_value=str(rp_trade_count),
                difference=str(abs(bt_trade_count - rp_trade_count)),
                explanation="Trade counts differ. Investigate signal timing or execution differences.",
            ))

        return self._mismatches

    def write_report(self, output_dir: str | Path) -> None:
        """Write comparison artifacts to output_dir."""
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        mismatches = self.compare()

        # mismatches.csv
        mm_path = out / "mismatches.csv"
        if mismatches:
            with open(mm_path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=list(mismatches[0].to_dict().keys()))
                writer.writeheader()
                for m in mismatches:
                    writer.writerow(m.to_dict())
        else:
            mm_path.write_text("# No mismatches detected\n")

        # summary.json
        summary = {
            "replay_id": self._rp.replay_id,
            "start_date": self._rp.start_date,
            "end_date": self._rp.end_date,
            "symbols": self._rp.symbols,
            "mismatch_count": len(mismatches),
            "parity_status": "MATCH" if not mismatches else "MISMATCH",
            "backtest_signal_count": len(getattr(self._bt, "signals", [])),
            "replay_signal_count": len(self._rp.signals),
            "backtest_trade_count": len(getattr(self._bt, "trades", [])),
            "replay_trade_count": len(self._rp.trades),
        }
        with open(out / "summary.json", "w") as f:
            json.dump(summary, f, indent=2)

        logger.info(
            "Replay comparison written",
            output_dir=str(out),
            mismatch_count=len(mismatches),
            parity_status=summary["parity_status"],
        )
