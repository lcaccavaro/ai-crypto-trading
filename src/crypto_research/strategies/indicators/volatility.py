"""
Volatility indicators — ATR, Bollinger Bands, BB Width, Rolling Std.

All functions are pure and stateless.

Zero-volatility handling:
    rolling_std: returns 0.0 when all prices in the window are identical.
    bollinger_bands: returns (mean, mean, mean) when std == 0.
    bb_width: returns 0.0 when std == 0.
"""

from __future__ import annotations

import math


def atr(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    period: int = 14,
) -> float | None:
    """
    Average True Range (Wilder's smoothing method).

    True Range = max(
        high - low,
        abs(high - prev_close),
        abs(low  - prev_close)
    )

    Seeding: first ATR value = simple average of first `period` TRs.
    Subsequent: Wilder's smoothing = (prev_atr * (period - 1) + TR) / period.

    Args:
        highs:  High prices (most recent last).
        lows:   Low prices (most recent last).
        closes: Close prices (most recent last).
        period: ATR lookback period (default 14).

    Returns:
        ATR value, or None if insufficient history (< period + 1 candles).
    """
    if period <= 0:
        raise ValueError(f"period must be > 0, got {period}")
    n = len(closes)
    if n != len(highs) or n != len(lows):
        raise ValueError("highs, lows, closes must have the same length")
    if n < period + 1:
        return None

    # Compute true ranges (needs prev close, so starts at index 1)
    true_ranges: list[float] = []
    for i in range(1, n):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        true_ranges.append(tr)

    if len(true_ranges) < period:
        return None

    # Seed with simple average
    atr_val = sum(true_ranges[:period]) / period
    # Apply Wilder smoothing over remaining
    for tr in true_ranges[period:]:
        atr_val = (atr_val * (period - 1) + tr) / period
    return atr_val


def rolling_std(prices: list[float], period: int) -> float | None:
    """
    Rolling population standard deviation over the last `period` prices.

    Uses population std (divides by N, not N-1) to match common TA platforms.

    Special case: constant prices → returns 0.0 (not None).

    Args:
        prices: Price series (most recent last).
        period: Lookback period.

    Returns:
        Standard deviation, or None if len(prices) < period.
    """
    if period <= 0:
        raise ValueError(f"period must be > 0, got {period}")
    if len(prices) < period:
        return None
    window = prices[-period:]
    mean = sum(window) / period
    variance = sum((p - mean) ** 2 for p in window) / period
    return math.sqrt(variance)


def bollinger_bands(
    prices: list[float],
    period: int = 20,
    num_std: float = 2.0,
) -> tuple[float | None, float | None, float | None]:
    """
    Bollinger Bands: (upper, middle, lower).

    middle = SMA(period)
    upper  = middle + num_std * rolling_std(period)
    lower  = middle - num_std * rolling_std(period)

    Zero-volatility: when std == 0, all three bands equal the middle.

    Args:
        prices:  Price series (most recent last).
        period:  SMA period (default 20).
        num_std: Standard deviation multiplier (default 2.0).

    Returns:
        (upper, middle, lower) or (None, None, None) if insufficient history.
    """
    if period <= 0:
        raise ValueError(f"period must be > 0, got {period}")
    if num_std <= 0:
        raise ValueError(f"num_std must be > 0, got {num_std}")
    if len(prices) < period:
        return (None, None, None)

    window = prices[-period:]
    middle = sum(window) / period
    std = rolling_std(prices, period)
    if std is None:
        return (None, None, None)

    upper = middle + num_std * std
    lower = middle - num_std * std
    return (upper, middle, lower)


def bb_width(
    prices: list[float],
    period: int = 20,
    num_std: float = 2.0,
) -> float | None:
    """
    Bollinger Band Width: (upper - lower) / middle.

    Normalized width as a fraction of the middle band.
    Returns 0.0 when std == 0 (constant prices).

    Args:
        prices:  Price series (most recent last).
        period:  SMA period (default 20).
        num_std: Standard deviation multiplier (default 2.0).

    Returns:
        Band width, or None if insufficient history.
    """
    upper, middle, lower = bollinger_bands(prices, period, num_std)
    if upper is None or middle is None or lower is None:
        return None
    if middle == 0.0:
        return None  # undefined: division by zero
    return (upper - lower) / middle
