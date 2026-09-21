"""
Volume indicators — Relative Volume.

All functions are pure and stateless.

Zero-volume handling:
    relative_volume: returns None when the rolling average volume is 0.
"""

from __future__ import annotations


def relative_volume(
    volumes: list[float],
    period: int = 20,
) -> float | None:
    """
    Relative Volume: current volume / rolling average volume.

    RV = volume[t] / mean(volume[t-period : t])

    A value > 1.0 means above-average volume.
    A value < 1.0 means below-average volume.

    Note: The current candle's volume (volumes[-1]) is compared against
    the rolling average of the PREVIOUS `period` candles (volumes[-period-1:-1]).
    This ensures PIT correctness — we do not include the current candle
    in its own baseline.

    Special cases:
        - avg_volume == 0: returns None (undefined, not 0).
        - insufficient history (< period + 1): returns None.

    Args:
        volumes: Volume series (most recent last). Must contain closed candles only.
        period:  Rolling average lookback period (default 20).

    Returns:
        Relative volume ratio, or None if undefined.
    """
    if period <= 0:
        raise ValueError(f"period must be > 0, got {period}")
    # Need current + period previous values
    if len(volumes) < period + 1:
        return None

    current_vol = volumes[-1]
    baseline_vols = volumes[-(period + 1):-1]  # previous `period` candles

    avg_vol = sum(baseline_vols) / period
    if avg_vol == 0.0:
        return None  # undefined: division by zero

    return current_vol / avg_vol


def volume_sma(volumes: list[float], period: int = 20) -> float | None:
    """
    Simple moving average of volume.

    Args:
        volumes: Volume series (most recent last).
        period:  Lookback period.

    Returns:
        SMA of volume, or None if insufficient history.
    """
    if period <= 0:
        raise ValueError(f"period must be > 0, got {period}")
    if len(volumes) < period:
        return None
    return sum(volumes[-period:]) / period
