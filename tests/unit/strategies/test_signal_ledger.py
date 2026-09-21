"""Tests for SignalLedger and SignalEntry."""

import json
import pytest
from datetime import datetime, timezone
from pathlib import Path

from crypto_research.core.domain import Candle, Signal, SignalDirection, Timeframe
from crypto_research.strategies.context import StrategyInstance
from crypto_research.strategies.signal_ledger import SignalLedger, SignalEntry


def make_signal(direction: SignalDirection = SignalDirection.LONG) -> Signal:
    return Signal(
        timestamp=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
        strategy_name="EMA_CROSS_001",
        asset="BTCUSDT",
        timeframe=Timeframe.M15,
        direction=direction,
        strength=1.0,
        metadata={
            "reason": "fast EMA crossed above slow EMA",
            "fast_ema": 100.5,
            "slow_ema": 100.0,
        },
    )


def make_instance() -> StrategyInstance:
    return StrategyInstance(
        strategy_id="EMA_CROSS_001",
        symbol="BTCUSDT",
        timeframe="15m",
        version="1.0.0",
        parameters={"fast_period": 9, "slow_period": 21},
    )


class TestSignalLedger:
    def test_empty_ledger(self):
        ledger = SignalLedger(run_id="RUN_001")
        assert len(ledger) == 0
        assert ledger.entries() == []

    def test_invalid_run_id(self):
        with pytest.raises(ValueError):
            SignalLedger(run_id="")

    def test_record_one_entry(self):
        ledger = SignalLedger(run_id="RUN_001")
        instance = make_instance()
        signal = make_signal()
        entry = ledger.record(signal, instance)
        assert len(ledger) == 1
        assert entry.strategy_id == "EMA_CROSS_001"
        assert entry.direction == "long"
        assert entry.run_id == "RUN_001"

    def test_entries_returns_copy(self):
        ledger = SignalLedger(run_id="RUN_001")
        ledger.record(make_signal(), make_instance())
        entries_1 = ledger.entries()
        entries_2 = ledger.entries()
        assert entries_1 is not entries_2  # copy
        assert len(entries_1) == len(entries_2)

    def test_filter_by_instance(self):
        ledger = SignalLedger(run_id="RUN_001")
        inst = make_instance()
        ledger.record(make_signal(), inst)
        result = ledger.entries_for_instance(inst.instance_id)
        assert len(result) == 1

    def test_filter_by_symbol(self):
        ledger = SignalLedger(run_id="RUN_001")
        ledger.record(make_signal(), make_instance())
        result = ledger.entries_for_symbol("BTCUSDT")
        assert len(result) == 1
        result_empty = ledger.entries_for_symbol("ETHUSDT")
        assert len(result_empty) == 0

    def test_reason_extracted(self):
        ledger = SignalLedger(run_id="RUN_001")
        entry = ledger.record(make_signal(), make_instance())
        assert entry.reason == "fast EMA crossed above slow EMA"

    def test_indicator_snapshot_excludes_reason(self):
        ledger = SignalLedger(run_id="RUN_001")
        entry = ledger.record(make_signal(), make_instance())
        assert "reason" not in entry.indicator_snapshot
        assert "fast_ema" in entry.indicator_snapshot

    def test_to_csv(self, tmp_path: Path):
        ledger = SignalLedger(run_id="RUN_001")
        ledger.record(make_signal(), make_instance())
        out = tmp_path / "signals.csv"
        written = ledger.to_csv(out)
        assert written.exists()
        content = written.read_text()
        assert "EMA_CROSS_001" in content
        assert "long" in content

    def test_to_dict_json_serializable(self):
        ledger = SignalLedger(run_id="RUN_001")
        entry = ledger.record(make_signal(), make_instance())
        d = entry.to_dict()
        # indicator_snapshot should be JSON string in the dict
        parsed = json.loads(d["indicator_snapshot"])
        assert "fast_ema" in parsed

    def test_repr(self):
        ledger = SignalLedger(run_id="RUN_001")
        assert "RUN_001" in repr(ledger)
