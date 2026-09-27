"""
Unit tests for the WalkForwardSplitter.

Tests:
    - Rolling mode generates correct windows
    - Expanding mode grows the training window
    - Temporal ordering is always correct (no look-ahead)
    - OOS does not overlap between consecutive windows (default)
    - Insufficient data returns empty list
    - Timezone-naive inputs are made UTC-aware
"""

from __future__ import annotations

import pytest
from datetime import datetime, timedelta, timezone

from crypto_research.config.schema import WalkForwardConfig, WalkForwardPeriodConfig
from crypto_research.research.walk_forward.splitter import WalkForwardSplitter, WalkForwardWindow


def make_config(
    mode: str = "rolling",
    train_days: int = 90,
    val_days: int = 30,
    oos_days: int = 30,
    step_days: int = 30,
) -> WalkForwardConfig:
    return WalkForwardConfig(
        enabled=True,
        mode=mode,
        train_period=WalkForwardPeriodConfig(value=train_days),
        validation_period=WalkForwardPeriodConfig(value=val_days),
        test_period=WalkForwardPeriodConfig(value=oos_days),
        step=WalkForwardPeriodConfig(value=step_days),
    )


START = datetime(2023, 1, 1, tzinfo=timezone.utc)
END = datetime(2024, 1, 1, tzinfo=timezone.utc)  # 365 days


class TestRollingMode:
    def test_generates_windows(self):
        cfg = make_config(mode="rolling", train_days=90, val_days=30, oos_days=30, step_days=30)
        splitter = WalkForwardSplitter(cfg)
        windows = splitter.generate(START, END)
        assert len(windows) > 0

    def test_temporal_ordering(self):
        cfg = make_config(mode="rolling")
        splitter = WalkForwardSplitter(cfg)
        windows = splitter.generate(START, END)
        for w in windows:
            assert w.train_start <= w.train_end
            assert w.train_end <= w.val_start
            assert w.val_start <= w.val_end
            assert w.val_end <= w.oos_start
            assert w.oos_start < w.oos_end

    def test_train_window_is_fixed_size(self):
        cfg = make_config(mode="rolling", train_days=90)
        splitter = WalkForwardSplitter(cfg)
        windows = splitter.generate(START, END)
        for w in windows:
            assert (w.train_end - w.train_start).days == 90

    def test_no_oos_overlap(self):
        cfg = make_config(mode="rolling")
        splitter = WalkForwardSplitter(cfg)
        windows = splitter.generate(START, END)
        assert splitter.validate_no_oos_overlap(windows) is True

    def test_window_ids_are_sequential(self):
        cfg = make_config(mode="rolling")
        splitter = WalkForwardSplitter(cfg)
        windows = splitter.generate(START, END)
        for i, w in enumerate(windows):
            assert w.window_id == i

    def test_windows_advance_by_step(self):
        cfg = make_config(mode="rolling", step_days=30)
        splitter = WalkForwardSplitter(cfg)
        windows = splitter.generate(START, END)
        if len(windows) >= 2:
            diff = (windows[1].train_start - windows[0].train_start).days
            assert diff == 30


class TestExpandingMode:
    def test_generates_windows(self):
        cfg = make_config(mode="expanding")
        splitter = WalkForwardSplitter(cfg)
        windows = splitter.generate(START, END)
        assert len(windows) > 0

    def test_train_always_starts_at_global_start(self):
        cfg = make_config(mode="expanding")
        splitter = WalkForwardSplitter(cfg)
        windows = splitter.generate(START, END)
        for w in windows:
            assert w.train_start == START

    def test_train_window_grows_with_each_step(self):
        cfg = make_config(mode="expanding", step_days=30)
        splitter = WalkForwardSplitter(cfg)
        windows = splitter.generate(START, END)
        if len(windows) >= 2:
            train_len_0 = (windows[0].train_end - windows[0].train_start).days
            train_len_1 = (windows[1].train_end - windows[1].train_start).days
            assert train_len_1 > train_len_0

    def test_temporal_ordering(self):
        cfg = make_config(mode="expanding")
        splitter = WalkForwardSplitter(cfg)
        windows = splitter.generate(START, END)
        for w in windows:
            assert w.train_end <= w.val_start
            assert w.val_end <= w.oos_start
            assert w.oos_start < w.oos_end


class TestEdgeCases:
    def test_insufficient_data_returns_empty(self):
        # Range shorter than one window
        cfg = make_config(train_days=90, val_days=30, oos_days=30)
        splitter = WalkForwardSplitter(cfg)
        short_end = START + timedelta(days=100)
        windows = splitter.generate(START, short_end)
        assert windows == []

    def test_start_equals_end_raises(self):
        cfg = make_config()
        splitter = WalkForwardSplitter(cfg)
        with pytest.raises(ValueError):
            splitter.generate(START, START)

    def test_start_after_end_raises(self):
        cfg = make_config()
        splitter = WalkForwardSplitter(cfg)
        with pytest.raises(ValueError):
            splitter.generate(END, START)

    def test_naive_timestamps_become_utc(self):
        naive_start = datetime(2023, 1, 1)
        naive_end = datetime(2024, 1, 1)
        cfg = make_config()
        splitter = WalkForwardSplitter(cfg)
        windows = splitter.generate(naive_start, naive_end)
        for w in windows:
            assert w.train_start.tzinfo is not None
            assert w.oos_end.tzinfo is not None

    def test_validate_returns_false_on_overlap(self):
        """Manually create overlapping windows to test the validator."""
        cfg = make_config()
        splitter = WalkForwardSplitter(cfg)
        w1 = WalkForwardWindow(
            window_id=0, mode="rolling",
            train_start=START, train_end=START + timedelta(days=90),
            val_start=START + timedelta(days=90), val_end=START + timedelta(days=120),
            oos_start=START + timedelta(days=120), oos_end=START + timedelta(days=150),
        )
        w2 = WalkForwardWindow(
            window_id=1, mode="rolling",
            train_start=START + timedelta(days=30), train_end=START + timedelta(days=120),
            val_start=START + timedelta(days=120), val_end=START + timedelta(days=150),
            # OOS overlaps with w1's OOS
            oos_start=START + timedelta(days=140), oos_end=START + timedelta(days=170),
        )
        assert splitter.validate_no_oos_overlap([w1, w2]) is False

    def test_to_dict_keys(self):
        cfg = make_config()
        splitter = WalkForwardSplitter(cfg)
        windows = splitter.generate(START, END)
        if windows:
            d = windows[0].to_dict()
            required_keys = {
                "window_id", "mode", "train_start", "train_end",
                "val_start", "val_end", "oos_start", "oos_end",
                "train_days", "val_days", "oos_days",
            }
            assert required_keys.issubset(set(d.keys()))
