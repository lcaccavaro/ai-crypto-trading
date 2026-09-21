"""
Moving average indicators — SMA, EMA, WMA.

All functions are pure and stateless:
    - Input: list of float prices (most recent last), period: int
    - Output: float | None
    - Returns None when insufficient history (< period candles)
    - Never raises on insufficient data — always returns None

Point-in-time safe: each function computes from a slice of
already-closed candles, no future values can leak in.
"""

from __future__ import annotations


def sma(prices: list[float], period: int) -> float | None:
    """
    Simple Moving Average.

    Args:
        prices: Price series (most recent last). Must contain closed candles only.
        period: Lookback period.

    Returns:
        SMA value, or None if len(prices) < period.
    """
    if period <= 0:
        raise ValueError(f"period must be > 0, got {period}")
    if len(prices) < period:
        return None
    window = prices[-period:]
    return sum(window) / period


def ema(prices: list[float], period: int) -> float | None:
    """
    Exponential Moving Average (Wilder smoothing: k = 2 / (period + 1)).

    This is the standard Wilder EMA used by most technical analysis platforms.
    The first EMA value is seeded as the SMA of the first `period` values.

    Args:
        prices: Price series (most recent last). Must contain closed candles only.
        period: Lookback period.

    Returns:
        EMA value, or None if len(prices) < period.
    """
    if period <= 0:
        raise ValueError(f"period must be > 0, got {period}")
    if len(prices) < period:
        return None

    k = 2.0 / (period + 1)
    # Seed with first SMA
    current_ema = sum(prices[:period]) / period
    # Apply EMA over remaining prices
    for price in prices[period:]:
        current_ema = price * k + current_ema * (1.0 - k)
    return current_ema


def ema_series(prices: list[float], period: int) -> list[float | None]:
    """
    Compute EMA for every position in prices (aligned with input).

    Returns list of same length as prices. Leading values (< period) are None.

    Args:
        prices: Price series (most recent last).
        period: Lookback period.

    Returns:
        List of EMA values aligned with prices.
    """
    if period <= 0:
        raise ValueError(f"period must be > 0, got {period}")

    result: list[float | None] = [None] * len(prices)
    if len(prices) < period:
        return result

    k = 2.0 / (period + 1)
    seed = sum(prices[:period]) / period
    result[period - 1] = seed

    current_ema = seed
    for i in range(period, len(prices)):
        current_ema = prices[i] * k + current_ema * (1.0 - k)
        result[i] = current_ema

    return result


def wma(prices: list[float], period: int) -> float | None:
    """
    Weighted Moving Average (linearly decreasing weights, most recent = highest).

    Weight of observation at index i (0 = oldest in window) = i + 1.
    WMA = sum(price[i] * weight[i]) / sum(weights)

    Args:
        prices: Price series (most recent last). Must contain closed candles only.
        period: Lookback period.

    Returns:
        WMA value, or None if len(prices) < period.
    """
    if period <= 0:
        raise ValueError(f"period must be > 0, got {period}")
    if len(prices) < period:
        return None

    window = prices[-period:]
    weights = list(range(1, period + 1))  # [1, 2, ..., period]
    total_weight = sum(weights)
    weighted_sum = sum(p * w for p, w in zip(window, weights))
    return weighted_sum / total_weight
