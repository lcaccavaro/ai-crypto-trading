"""
Signal ledger — structured, append-only log of all strategy signals.

The signal ledger records every signal generated during a backtest run
with enough context to diagnose why it happened and replay it.

Fields per entry:
    timestamp         : When the signal was generated (simulation time)
    strategy_id       : Strategy identifier
    strategy_version  : Strategy version
    instance_id       : Full strategy instance ID
    symbol            : Asset symbol
    timeframe         : Timeframe string
    direction         : "long" / "short" / "neutral"
    strength          : Signal strength [0.0, 1.0]
    reason            : Human-readable reason from signal metadata
    indicator_snapshot: Dict of indicator values at signal time
    parameters        : Strategy parameters for this instance
    run_id            : Research run ID

Usage:
    ledger = SignalLedger(run_id="RUN_...")
    ledger.record(signal, instance)
    ledger.to_csv("results/.../signals.csv")
    entries = ledger.entries()
"""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from crypto_research.core.domain import Signal
from crypto_research.strategies.context import StrategyInstance


@dataclass
class SignalEntry:
    """
    A single record in the signal ledger.

    Immutable after creation. All fields are serializable to CSV/JSON.
    """

    timestamp: str           # ISO format UTC
    strategy_id: str
    strategy_version: str
    instance_id: str
    symbol: str
    timeframe: str
    direction: str
    strength: float
    reason: str
    indicator_snapshot: dict[str, Any]
    parameters: dict[str, Any]
    run_id: str

    def to_dict(self) -> dict[str, Any]:
        """Flat dict for CSV writing."""
        d = asdict(self)
        # Flatten nested dicts to JSON strings for CSV compatibility
        import json
        d["indicator_snapshot"] = json.dumps(d["indicator_snapshot"])
        d["parameters"] = json.dumps(d["parameters"])
        return d

    @classmethod
    def from_signal(
        cls,
        signal: Signal,
        instance: StrategyInstance,
        run_id: str,
    ) -> "SignalEntry":
        """Create a SignalEntry from a Signal and its instance metadata."""
        metadata = signal.metadata or {}
        reason = metadata.get("reason", "")
        # Everything except 'reason' is indicator data
        indicator_snapshot = {k: v for k, v in metadata.items() if k != "reason"}

        return cls(
            timestamp=signal.timestamp.isoformat(),
            strategy_id=instance.strategy_id,
            strategy_version=instance.version,
            instance_id=instance.instance_id,
            symbol=signal.asset,
            timeframe=signal.timeframe.value if hasattr(signal.timeframe, "value") else str(signal.timeframe),
            direction=signal.direction.value if hasattr(signal.direction, "value") else str(signal.direction),
            strength=signal.strength,
            reason=reason,
            indicator_snapshot=indicator_snapshot,
            parameters=instance.parameters,
            run_id=run_id,
        )


class SignalLedger:
    """
    Append-only in-memory signal log with CSV export.

    Thread safety: not thread-safe. Designed for single-threaded research use.
    """

    # CSV column order
    _COLUMNS = [
        "timestamp",
        "strategy_id",
        "strategy_version",
        "instance_id",
        "symbol",
        "timeframe",
        "direction",
        "strength",
        "reason",
        "indicator_snapshot",
        "parameters",
        "run_id",
    ]

    def __init__(self, run_id: str) -> None:
        if not run_id:
            raise ValueError("run_id must not be empty")
        self._run_id = run_id
        self._entries: list[SignalEntry] = []

    def record(self, signal: Signal, instance: StrategyInstance) -> SignalEntry:
        """
        Record a signal from a strategy instance.

        Args:
            signal:   The Signal produced by the strategy.
            instance: The StrategyInstance that produced the signal.

        Returns:
            The created SignalEntry.
        """
        entry = SignalEntry.from_signal(signal, instance, self._run_id)
        self._entries.append(entry)
        return entry

    def entries(self) -> list[SignalEntry]:
        """Return all recorded entries (read-only copy)."""
        return list(self._entries)

    def entries_for_instance(self, instance_id: str) -> list[SignalEntry]:
        """Return all entries for a specific strategy instance."""
        return [e for e in self._entries if e.instance_id == instance_id]

    def entries_for_symbol(self, symbol: str) -> list[SignalEntry]:
        """Return all entries for a specific symbol."""
        return [e for e in self._entries if e.symbol == symbol]

    def __len__(self) -> int:
        return len(self._entries)

    def to_csv(self, path: str | Path) -> Path:
        """
        Write all entries to a CSV file.

        Args:
            path: Target file path.

        Returns:
            Path to the written file.
        """
        out_path = Path(path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        with open(out_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=self._COLUMNS)
            writer.writeheader()
            for entry in self._entries:
                writer.writerow(entry.to_dict())

        return out_path

    def __repr__(self) -> str:
        return f"SignalLedger(run_id={self._run_id!r}, entries={len(self._entries)})"
