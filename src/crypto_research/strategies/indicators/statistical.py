"""
Statistical indicators — Z-Score, Donchian Channels.

All functions are pure and stateless.

Zero-volatility handling:
    zscore: returns None when rolling_std == 0 (constant price window).
            No epsilon injection — the strategy must handle None as NOT_READY.

Donchian channels:
    Uses PREVIOUS completed window (shift=1) to avoid look-ahead bias.
    The breakout signal at candle T uses the channel computed from
    candles [T-period-1 : T-1], not including candle T itself.
"""

from __future__ import annotations

from crypto_research.strategies.indicators.volatility import rolling_std


def zscore(prices: list[float], period: int = 20) -> float | None:
    """
    Z-Score: (current_price - rolling_mean) / rolling_std.

    Measures how many standard deviations the current price is from
    the rolling mean.

    Zero-volatility: returns None when rolling_std == 0.
    DO NOT inject epsilon — the strategy must treat None as NOT_READY.

    Args:
        prices: Price series (most recent last). Closed candles only.
        period: Rolling window period (default 20).

    Returns:
        Z-score float, or None if insufficient history or zero std.
    """
    if period <= 0:
        raise ValueError(f"period must be > 0, got {period}")
    if len(prices) < period:
        return None

    window = prices[-period:]
    mean = sum(window) / period
    std = rolling_std(prices, period)

    if std is None or std == 0.0:
        return None  # constant prices — undefined z-score

    return (prices[-1] - mean) / std


def donchian_channels(
    highs: list[float],
    lows: list[float],
    period: int = 20,
    use_previous_window: bool = True,
) -> tuple[float | None, float | None]:
    """
    Donchian Channels: (upper, lower) = (rolling_high, rolling_low).

    CRITICAL PIT RULE:
        use_previous_window=True (default): The channel is computed from
        the PREVIOUS completed period, i.e. highs/lows[-(period+1):-1].
        This ensures the current candle is NOT included in the breakout
        threshold — the signal is generated when the current close exceeds
        the prior window's high/low.

        use_previous_window=False: Uses the current window highs/lows[-period:].
        This is the "state" form, useful for visualizing the channel,
        but NOT appropriate for breakout signal generation.

    Args:
        highs:               High prices (most recent last).
        lows:                Low prices (most recent last).
        period:              Lookback period (default 20).
        use_previous_window: True = use prior window (PIT-safe for breakouts).

    Returns:
        (upper, lower) = (rolling max of highs, rolling min of lows),
        or (None, None) if insufficient history.
    """
    if period <= 0:
        raise ValueError(f"period must be > 0, got {period}")
    if len(highs) != len(lows):
        raise ValueError("highs and lows must have the same length")

    if use_previous_window:
        # Require period + 1 candles: current + period previous
        if len(highs) < period + 1:
            return (None, None)
        h_window = highs[-(period + 1):-1]  # previous period
        l_window = lows[-(period + 1):-1]
    else:
        if len(highs) < period:
            return (None, None)
        h_window = highs[-period:]
        l_window = lows[-period:]

    return (max(h_window), min(l_window))


def rolling_high(prices: list[float], period: int, shift: int = 0) -> float | None:
    """
    Rolling maximum over `period` candles, optionally shifted.

    shift=0: includes the current candle.
    shift=1: uses the previous completed window (PIT-safe for breakouts).

    Args:
        prices: Price series (most recent last).
        period: Lookback period.
        shift:  Number of candles to shift the window backward (default 0).

    Returns:
        Maximum value, or None if insufficient history.
    """
    if period <= 0:
        raise ValueError(f"period must be > 0, got {period}")
    required = period + shift
    if len(prices) < required:
        return None
    if shift == 0:
        window = prices[-period:]
    else:
        window = prices[-(period + shift):-shift]
    return max(window)


def rolling_low(prices: list[float], period: int, shift: int = 0) -> float | None:
    """
    Rolling minimum over `period` candles, optionally shifted.

    shift=0: includes the current candle.
    shift=1: uses the previous completed window (PIT-safe for breakouts).

    Args:
        prices: Price series (most recent last).
        period: Lookback period.
        shift:  Number of candles to shift the window backward (default 0).

    Returns:
        Minimum value, or None if insufficient history.
    """
    if period <= 0:
        raise ValueError(f"period must be > 0, got {period}")
    required = period + shift
    if len(prices) < required:
        return None
    if shift == 0:
        window = prices[-period:]
    else:
        window = prices[-(period + shift):-shift]
    return min(window)
