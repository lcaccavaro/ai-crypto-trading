"""
Walk-Forward Window Splitter.

Generates non-overlapping (by default) TRAIN / VALIDATION / OOS windows
from a date range, supporting both rolling and expanding window modes.

Temporal Guarantee:
    For every window:
        train_start ≤ train_end < val_start ≤ val_end < oos_start ≤ oos_end

    Information flows ONLY forward. Nothing from OOS or validation can
    influence the training period decision.

PIT Safety:
    The splitter only uses the calendar. It never reads market data.
    It cannot leak future information through window construction.

Non-overlapping OOS:
    By default, OOS periods do not overlap between consecutive windows.
    This is enforced by advancing the start date by `step` after each window.

Rolling vs Expanding:
    rolling:   train window has fixed length (train_period). Oldest data dropped.
    expanding: train window starts from the global start and grows with each step.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Iterator

from crypto_research.config.schema import WalkForwardConfig
from crypto_research.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class WalkForwardWindow:
    """
    A single train/validation/OOS window.

    All timestamps are UTC-aware. Boundaries are inclusive on the left,
    exclusive on the right (standard Python date slice convention).
    """

    window_id: int
    mode: str  # "rolling" or "expanding"

    train_start: datetime
    train_end: datetime        # exclusive upper bound

    val_start: datetime
    val_end: datetime          # exclusive upper bound

    oos_start: datetime
    oos_end: datetime          # exclusive upper bound

    def validate(self) -> None:
        """Raise ValueError if temporal ordering is violated."""
        if not (self.train_start <= self.train_end):
            raise ValueError(f"Window {self.window_id}: train_start > train_end")
        if not (self.train_end <= self.val_start):
            raise ValueError(f"Window {self.window_id}: train_end > val_start — overlap!")
        if not (self.val_start <= self.val_end):
            raise ValueError(f"Window {self.window_id}: val_start > val_end")
        if not (self.val_end <= self.oos_start):
            raise ValueError(f"Window {self.window_id}: val_end > oos_start — overlap!")
        if not (self.oos_start < self.oos_end):
            raise ValueError(f"Window {self.window_id}: oos_start >= oos_end — no OOS data")

    def to_dict(self) -> dict:
        return {
            "window_id": self.window_id,
            "mode": self.mode,
            "train_start": self.train_start.isoformat(),
            "train_end": self.train_end.isoformat(),
            "val_start": self.val_start.isoformat(),
            "val_end": self.val_end.isoformat(),
            "oos_start": self.oos_start.isoformat(),
            "oos_end": self.oos_end.isoformat(),
            "train_days": (self.train_end - self.train_start).days,
            "val_days": (self.val_end - self.val_start).days,
            "oos_days": (self.oos_end - self.oos_start).days,
        }


class WalkForwardSplitter:
    """
    Generates walk-forward windows from a date range and a WalkForwardConfig.

    Usage:
        splitter = WalkForwardSplitter(config.robustness.walk_forward)
        windows = splitter.generate(start=datetime(...), end=datetime(...))

    The splitter does NOT access any market data. It is a pure calendar computation.
    """

    def __init__(self, config: WalkForwardConfig) -> None:
        self._cfg = config

    def _to_days(self, period_cfg) -> int:
        """Convert a period config to calendar days. Only 'days' unit supported in P07."""
        if period_cfg.unit == "days":
            return period_cfg.value
        # "candles" requires knowing the timeframe — not available here.
        # Document this as a known limitation; default to treating value as days.
        logger.warning(
            "WalkForwardSplitter: unit='candles' not supported without timeframe context. "
            "Treating value as days.",
            value=period_cfg.value,
        )
        return period_cfg.value

    def generate(self, start: datetime, end: datetime) -> list[WalkForwardWindow]:
        """
        Generate all walk-forward windows between `start` and `end`.

        Args:
            start: Inclusive global start (UTC-aware).
            end:   Exclusive global end (UTC-aware).

        Returns:
            List of WalkForwardWindow in chronological order.
            Empty list if not enough data for even one window.

        Raises:
            ValueError: If start >= end or configuration is inconsistent.
        """
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        if start >= end:
            raise ValueError(f"start ({start}) must be before end ({end})")

        train_days = self._to_days(self._cfg.train_period)
        val_days = self._to_days(self._cfg.validation_period)
        oos_days = self._to_days(self._cfg.test_period)
        step_days = self._to_days(self._cfg.step)
        mode = self._cfg.mode

        total_window = train_days + val_days + oos_days
        global_start = start

        windows: list[WalkForwardWindow] = []
        window_id = 0

        # The anchor is where training begins for the current iteration
        anchor = global_start

        while True:
            # Safety guard: prevent infinite loop / overflow
            if anchor >= end:
                break

            if mode == "rolling":
                train_start = anchor
            else:  # expanding
                train_start = global_start

            train_end = train_start + timedelta(days=train_days)
            val_start = train_end
            val_end = val_start + timedelta(days=val_days)
            oos_start = val_end
            oos_end = oos_start + timedelta(days=oos_days)

            # In expanding mode, the OOS window is anchored at the end of the growing train+val.
            # Recompute for expanding: OOS starts after train (which grows) + val.
            if mode == "expanding":
                # The OOS anchor position advances by step, starting from the first OOS start.
                # train_end grows as anchor advances step_days each iteration.
                first_oos_start = global_start + timedelta(days=train_days + val_days)
                oos_offset = window_id * step_days
                train_end_expanding = global_start + timedelta(days=train_days) + timedelta(days=oos_offset)
                val_start_expanding = train_end_expanding
                val_end_expanding = val_start_expanding + timedelta(days=val_days)
                oos_start_expanding = val_end_expanding
                oos_end_expanding = oos_start_expanding + timedelta(days=oos_days)

                if oos_end_expanding > end:
                    break

                w = WalkForwardWindow(
                    window_id=window_id,
                    mode=mode,
                    train_start=global_start,
                    train_end=train_end_expanding,
                    val_start=val_start_expanding,
                    val_end=val_end_expanding,
                    oos_start=oos_start_expanding,
                    oos_end=oos_end_expanding,
                )
            else:
                # Rolling mode
                if oos_end > end:
                    break
                w = WalkForwardWindow(
                    window_id=window_id,
                    mode=mode,
                    train_start=train_start,
                    train_end=train_end,
                    val_start=val_start,
                    val_end=val_end,
                    oos_start=oos_start,
                    oos_end=oos_end,
                )

            w.validate()  # Strict temporal check — raises if violated
            windows.append(w)

            # Advance anchor by step (non-overlapping OOS by default)
            anchor = anchor + timedelta(days=step_days)
            window_id += 1

        logger.info(
            "Walk-forward windows generated",
            mode=mode,
            total_windows=len(windows),
            train_days=train_days,
            val_days=val_days,
            oos_days=oos_days,
        )
        return windows

    def validate_no_oos_overlap(self, windows: list[WalkForwardWindow]) -> bool:
        """
        Verify that OOS periods do not overlap between consecutive windows.
        Returns True if clean, False if overlap detected.
        """
        for i in range(1, len(windows)):
            prev = windows[i - 1]
            curr = windows[i]
            if curr.oos_start < prev.oos_end:
                logger.warning(
                    "OOS overlap detected between windows",
                    window_a=prev.window_id,
                    window_b=curr.window_id,
                    overlap_start=curr.oos_start.isoformat(),
                    overlap_end=prev.oos_end.isoformat(),
                )
                return False
        return True
