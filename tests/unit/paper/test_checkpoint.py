"""
Unit tests for PaperCheckpoint — Prompt 08.

Tests:
    - save() writes a valid JSON checkpoint
    - restore() reads and validates the checkpoint
    - restore() returns None if no checkpoint exists
    - Atomic write: .tmp is used and renamed
    - Partial .tmp file (interrupted write) raises CheckpointError
    - validate_session_id() raises if session ID does not match
"""

from __future__ import annotations

import json
import os
import pytest
from pathlib import Path
from unittest.mock import MagicMock

from crypto_research.config.schema import PaperTradingConfig
from crypto_research.core.domain import ExecutionMode, PaperSessionState
from crypto_research.paper.checkpoint import CheckpointError, PaperCheckpoint


def _make_session(initial_balance: float = 10_000.0, tmp_path: Path | None = None):
    """Create a minimal mock session for checkpoint tests."""
    session = MagicMock()
    session.session_id = "PAPER_TEST_001"
    session.run_id = "run_001"
    session.state = PaperSessionState.RUNNING
    session.execution_mode = ExecutionMode.PAPER
    session.start_time = None
    session.shutdown_reason = None

    acct = MagicMock()
    acct.to_dict.return_value = {"initial_balance": initial_balance, "equity": initial_balance}
    session.accounting = acct

    counters = MagicMock()
    counters.to_dict.return_value = {"trades_completed": 5, "errors": 0}
    counters.checkpoints_saved = 0
    session.counters = counters

    session.closed_trades = []
    session.open_positions = {}
    return session


class TestPaperCheckpointSaveRestore:
    def test_save_creates_json_file(self, tmp_path):
        cp = PaperCheckpoint(tmp_path)
        session = _make_session(tmp_path=tmp_path)
        cp.save(session)

        checkpoint_file = tmp_path / "checkpoint.json"
        assert checkpoint_file.exists()

    def test_restore_returns_none_when_no_file(self, tmp_path):
        cp = PaperCheckpoint(tmp_path)
        result = cp.restore()
        assert result is None

    def test_save_and_restore_roundtrip(self, tmp_path):
        cp = PaperCheckpoint(tmp_path)
        session = _make_session(tmp_path=tmp_path)
        cp.save(session)

        data = cp.restore()
        assert data is not None
        assert data["session_id"] == "PAPER_TEST_001"
        assert data["run_id"] == "run_001"

    def test_save_increments_checkpoint_counter(self, tmp_path):
        cp = PaperCheckpoint(tmp_path)
        session = _make_session(tmp_path=tmp_path)
        initial = session.counters.checkpoints_saved
        cp.save(session)
        assert session.counters.checkpoints_saved == initial + 1

    def test_exists_false_before_save(self, tmp_path):
        cp = PaperCheckpoint(tmp_path)
        assert cp.exists() is False

    def test_exists_true_after_save(self, tmp_path):
        cp = PaperCheckpoint(tmp_path)
        session = _make_session(tmp_path=tmp_path)
        cp.save(session)
        assert cp.exists() is True

    def test_tmp_file_cleaned_up_after_save(self, tmp_path):
        cp = PaperCheckpoint(tmp_path)
        session = _make_session(tmp_path=tmp_path)
        cp.save(session)
        # .tmp file should be gone after atomic rename
        tmp_file = tmp_path / "checkpoint.json.tmp"
        assert not tmp_file.exists()

    def test_partial_tmp_raises_checkpoint_error(self, tmp_path):
        """If .tmp exists but .json does not, restore must raise."""
        cp = PaperCheckpoint(tmp_path)
        tmp_file = tmp_path / "checkpoint.json.tmp"
        tmp_file.write_text('{"partial": true}')

        with pytest.raises(CheckpointError, match="interrupted"):
            cp.restore()

    def test_corrupt_json_raises_checkpoint_error(self, tmp_path):
        cp = PaperCheckpoint(tmp_path)
        checkpoint_file = tmp_path / "checkpoint.json"
        checkpoint_file.write_text("{invalid json{{")

        with pytest.raises(CheckpointError):
            cp.restore()

    def test_saved_checkpoint_has_execution_mode(self, tmp_path):
        cp = PaperCheckpoint(tmp_path)
        session = _make_session(tmp_path=tmp_path)
        cp.save(session)
        data = cp.restore()
        assert data["execution_mode"] == ExecutionMode.PAPER.value

    def test_saved_checkpoint_has_state(self, tmp_path):
        cp = PaperCheckpoint(tmp_path)
        session = _make_session(tmp_path=tmp_path)
        cp.save(session)
        data = cp.restore()
        assert data["state"] == PaperSessionState.RUNNING.value


class TestPaperCheckpointValidation:
    def test_validate_session_id_passes_correct_id(self, tmp_path):
        cp = PaperCheckpoint(tmp_path)
        session = _make_session(tmp_path=tmp_path)
        cp.save(session)
        data = cp.restore()
        cp.validate_session_id(data, "PAPER_TEST_001")  # Should not raise

    def test_validate_session_id_raises_on_mismatch(self, tmp_path):
        cp = PaperCheckpoint(tmp_path)
        session = _make_session(tmp_path=tmp_path)
        cp.save(session)
        data = cp.restore()

        with pytest.raises(CheckpointError, match="mismatch"):
            cp.validate_session_id(data, "DIFFERENT_SESSION")
