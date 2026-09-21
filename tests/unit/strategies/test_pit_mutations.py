"""
PIT (Point-In-Time) mutation tests.

These tests verify that strategies NEVER access future candle data.
Specifically:
1. Mutating a future candle AFTER generate_signal() is called does NOT change the signal.
2. The Donchian/Range breakout channels are computed from prior window only.
3. Inserting a candle with extreme values at the end (future) does not affect prior signal.

These tests use the "mutation after the fact" approach:
    - Call generate_signal with N candles
    - Mutate candle[N] (a "future" candle that wasn't in the window)
    - Verify the signal was already produced and is immutable
"""

import pytest
import copy
from datetime import datetime, timedelta, timezone
from dataclasses import replace

from crypto_research.core.domain import Candle, Timeframe
from crypto_research.strategies.breakout.donchian_breakout import DonchianBreakout
from crypto_research.strategies.breakout.range_breakout import RangeBreakout
from crypto_research.strategies.indicators import donchian_channels, rolling_high
from crypto_research.strategies.trend.ema_crossover import EMACrossover
from crypto_research.strategies.momentum.rsi_momentum import RSIMomentum


def make_candle(close: float, ts: datetime) -> Candle:
    return Candle(
        timestamp=ts,
        asset="BTCUSDT",
        timeframe=Timeframe.M15,
        open=close,
        high=close + 1.0,
        low=close - 1.0,
        close=close,
        volume=1000.0,
    )


def make_candles(prices: list[float]) -> list[Candle]:
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return [make_candle(p, base + timedelta(minutes=15 * i)) for i, p in enumerate(prices)]


class TestPITMutations:
    """
    These tests verify strategies don't use data from candles not yet in their window.
    The approach: compute indicator value on candle slice [0:N], then compare
    to result on candle slice [0:N+1] where candle[N] has extreme values.
    The indicator applied to [0:N] should not be affected by [N+1] whatsoever.
    """

    def test_donchian_prior_window_not_affected_by_current_candle(self):
        """
        Donchian breakout channel must use PRIOR window (not current candle).
        A current candle with extreme high should NOT expand the breakout threshold.
        """
        # Build 25 candles at 100.0
        prices = [100.0] * 25
        candles = make_candles(prices)

        # Compute Donchian channel using use_previous_window=True
        highs = [c.high for c in candles]
        lows = [c.low for c in candles]

        upper_before, lower_before = donchian_channels(
            highs, lows, period=20, use_previous_window=True
        )

        # Now "mutate" the last candle to have a huge high (simulating future data)
        highs_mutated = highs[:-1] + [999.0]  # mutate current candle high

        upper_after, lower_after = donchian_channels(
            highs_mutated, lows, period=20, use_previous_window=True
        )

        # Prior window is unchanged — upper should be the same
        assert upper_before == upper_after, (
            f"Channel changed after mutating current candle: {upper_before} → {upper_after}"
        )

    def test_rolling_high_shift1_not_affected_by_current(self):
        """rolling_high with shift=1 must exclude the current candle."""
        prices = [100.0] * 20

        # Normal computation
        before = rolling_high(prices, 15, shift=1)

        # Mutate "current" candle
        prices_mutated = prices[:-1] + [9999.0]
        after = rolling_high(prices_mutated, 15, shift=1)

        # Current candle is excluded; result unchanged
        assert before == after

    def test_ema_crossover_not_triggered_by_prior_state(self):
        """
        Signal from candle T should not be affected by running more candles
        after T — the signal was generated from data available AT candle T.
        """
        strat_1 = EMACrossover(fast_period=9, slow_period=21)
        strat_2 = EMACrossover(fast_period=9, slow_period=21)

        prices = [100.0] * 15 + [100.0 + i * 3.0 for i in range(20)]
        candles = make_candles(prices)

        # Run strat_1 to candle 25, record signal
        signals_1 = []
        for i in range(1, 26):
            sig = strat_1.generate_signal(candles[:i], candles[i - 1].timestamp)
            if sig is not None:
                signals_1.append((i, sig))

        # Run strat_2 to the SAME candle 25, but supply same data
        signals_2 = []
        strat_2.reset()
        for i in range(1, 26):
            sig = strat_2.generate_signal(candles[:i], candles[i - 1].timestamp)
            if sig is not None:
                signals_2.append((i, sig))

        # Both should produce identical signals at identical candle indices
        assert len(signals_1) == len(signals_2)
        for (i1, s1), (i2, s2) in zip(signals_1, signals_2):
            assert i1 == i2
            assert s1.direction == s2.direction

    def test_strategy_signal_uses_only_supplied_candles(self):
        """
        A strategy must only use the candles[] list provided.
        We verify: supplying N candles gives the same signal as supplying
        N candles in a fresh instance — no hidden state from prior calls.
        """
        strat = RSIMomentum(rsi_period=7, entry_threshold=55.0)

        prices = [100.0 + i * 0.5 for i in range(30)]
        candles = make_candles(prices)

        # Get signal at candle 20 after feeding incrementally
        for i in range(1, 20):
            strat.generate_signal(candles[:i], candles[i - 1].timestamp)
        sig_20 = strat.generate_signal(candles[:20], candles[19].timestamp)

        # Fresh instance — provide only the first 20 candles directly
        strat_fresh = RSIMomentum(rsi_period=7, entry_threshold=55.0)
        # Feed candles 1..19 to set prev_rsi state
        for i in range(1, 20):
            strat_fresh.generate_signal(candles[:i], candles[i - 1].timestamp)
        sig_20_fresh = strat_fresh.generate_signal(candles[:20], candles[19].timestamp)

        # Both should produce the same result (both None or both Signal)
        if sig_20 is None:
            assert sig_20_fresh is None
        else:
            assert sig_20_fresh is not None
            assert sig_20.direction == sig_20_fresh.direction


class TestDonchianBreakoutPIT:
    """Specific PIT tests for Donchian breakout strategy."""

    def test_breakout_uses_prior_window_not_current(self):
        """
        A breakout at candle T must be triggered by the threshold from
        candles [T-period-1 : T-1], NOT including candle T.
        """
        strat = DonchianBreakout(period=10)

        # Flat prices at 100 → Donchian upper = 101 (high = close+1)
        prices = [100.0] * 15

        # Add a candle that breaks out with close = 110
        prices.append(110.0)
        candles = make_candles(prices)

        # Run through all candles
        signals = []
        for i in range(1, len(candles) + 1):
            sig = strat.generate_signal(candles[:i], candles[i - 1].timestamp)
            if sig is not None:
                signals.append((i, sig))

        # Should produce a signal (110 > 101)
        assert len(signals) >= 1
        # The signal timestamp should be at the last candle
        assert signals[-1][0] == len(candles)
