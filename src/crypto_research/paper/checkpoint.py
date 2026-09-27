"""
Paper Trading Checkpoint — Prompt 08.

Persists and restores paper session state atomically.

Design:
    - Checkpoint = JSON file + position CSV, written atomically via rename.
    - On restore, validates that session_id matches.
    - If checkpoint is corrupt: raises explicitly (never silently resumes wrong state).
    - Positions, strategy states, and accounting are all restored.

Atomic write:
    1. Write to <checkpoint_path>.tmp
    2. os.replace(<tmp>, <checkpoint_path>)  — atomic on POSIX

Recovery:
    If .tmp file exists and .json does not → previous write was interrupted.
    Raise explicitly: user must decide whether to use .tmp or start fresh.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_research.core.domain import PaperSessionState
from crypto_research.utils.logging import get_logger

logger = get_logger(__name__)

CHECKPOINT_FILENAME = "checkpoint.json"
CHECKPOINT_TMP_SUFFIX = ".tmp"


class CheckpointError(Exception):
    """Raised when checkpoint save or restore fails."""


class PaperCheckpoint:
    """
    Saves and restores paper session state.

    Usage:
        cp = PaperCheckpoint(session_dir)
        cp.save(session)
        state = cp.restore()   # returns dict or None if no checkpoint exists
    """

    def __init__(self, session_dir: str | Path) -> None:
        self._dir = Path(session_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._path = self._dir / CHECKPOINT_FILENAME
        self._tmp_path = self._dir / (CHECKPOINT_FILENAME + CHECKPOINT_TMP_SUFFIX)

    def save(self, session) -> None:
        """
        Atomically persist session state.

        Args:
            session: PaperTradingSession — current state.
        """
        from crypto_research.paper.session import PaperTradingSession

        payload = {
            "checkpoint_ts": datetime.now(timezone.utc).isoformat(),
            "session_id": session.session_id,
            "run_id": session.run_id,
            "state": session.state.value,
            "execution_mode": session.execution_mode.value,
            "accounting": session.accounting.to_dict(),
            "counters": session.counters.to_dict(),
            "start_time": session.start_time.isoformat() if session.start_time else None,
            "shutdown_reason": session.shutdown_reason,
            "closed_trade_count": len(session.closed_trades),
            "open_positions": [
                {
                    "position_id": pos.position_id,
                    "symbol": pos.symbol,
                    "side": pos.side.value,
                    "quantity": pos.quantity,
                    "entry_price": pos.entry_price,
                    "stop_price": pos.stop_price,
                    "target_price": pos.target_price,
                    "entry_timestamp": pos.entry_timestamp.isoformat(),
                }
                for pos in session.open_positions.values()
            ],
        }

        # Write to temp file first
        with open(self._tmp_path, "w") as f:
            json.dump(payload, f, indent=2, default=str)

        # Atomic rename
        os.replace(self._tmp_path, self._path)
        session.counters.checkpoints_saved += 1

        logger.info(
            "Checkpoint saved",
            session_id=session.session_id,
            path=str(self._path),
        )

    def restore(self) -> dict | None:
        """
        Load the most recent checkpoint.

        Returns:
            Checkpoint dict, or None if no checkpoint exists.

        Raises:
            CheckpointError: If a partial (tmp) file exists without a valid
                completed checkpoint — indicates a previous interrupted write.
        """
        # Check for interrupted write
        if self._tmp_path.exists() and not self._path.exists():
            raise CheckpointError(
                f"Partial checkpoint found at {self._tmp_path}. "
                "The previous save was interrupted. "
                "Delete the .tmp file and start a new session, or recover manually."
            )

        if not self._path.exists():
            return None

        try:
            with open(self._path) as f:
                data = json.load(f)
            logger.info("Checkpoint loaded", path=str(self._path),
                        session_id=data.get("session_id"),
                        checkpoint_ts=data.get("checkpoint_ts"))
            return data
        except Exception as e:
            raise CheckpointError(f"Failed to load checkpoint: {e}") from e

    def exists(self) -> bool:
        return self._path.exists()

    def validate_session_id(self, checkpoint: dict, expected_session_id: str) -> None:
        """Raise if the checkpoint belongs to a different session."""
        found = checkpoint.get("session_id")
        if found != expected_session_id:
            raise CheckpointError(
                f"Checkpoint session_id mismatch: "
                f"expected {expected_session_id!r}, found {found!r}. "
                "Cannot resume from a different session."
            )
