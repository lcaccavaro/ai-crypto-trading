"""
Momentum indicators — RSI, ROC, MACD.

All functions are pure and stateless:
    - Input: list of float prices (most recent last), parameters
    - Output: float | None (or tuple for multi-value indicators)
    - Returns None when insufficient history
    - Never raises on insufficient data

Zero-volatility / constant-price handling:
    RSI: returns None when average_loss == 0 AND average_gain == 0 (no moves).
    MACD: returns (None, None, None) when EMAs are not yet calculable.
"""

from __future__ import annotations

from crypto_research.strategies.indicators.moving_averages import ema, ema_series


def rsi(prices: list[float], period: int = 14) -> float | None:
    """
    Relative Strength Index (Wilder's method).

    RSI = 100 - (100 / (1 + RS))
    where RS = average_gain / average_loss over `period` candles.

    Seeding: the first RSI value uses the simple average of gains/losses
    over the first `period` changes. Subsequent values use Wilder's
    exponential smoothing.

    Special cases:
        - Constant prices (no moves): returns None (undefined).
        - All gains (no losses): returns 100.0.
        - All losses (no gains): returns 0.0.

    Args:
        prices: Price series (most recent last). Needs period + 1 prices minimum.
        period: RSI lookback period (default 14).

    Returns:
        RSI value in [0.0, 100.0], or None if insufficient history.
    """
    if period <= 0:
        raise ValueError(f"period must be > 0, got {period}")
    if len(prices) < period + 1:
        return None

    # Compute all price changes
    changes = [prices[i] - prices[i - 1] for i in range(1, len(prices))]

    # Seed from first `period` changes
    gains_seed = [max(c, 0.0) for c in changes[:period]]
    losses_seed = [abs(min(c, 0.0)) for c in changes[:period]]

    avg_gain = sum(gains_seed) / period
    avg_loss = sum(losses_seed) / period

    # Apply Wilder smoothing over remaining changes
    for change in changes[period:]:
        gain = max(change, 0.0)
        loss = abs(min(change, 0.0))
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period

    # Handle special cases
    if avg_gain == 0.0 and avg_loss == 0.0:
        return None  # constant price — undefined
    if avg_loss == 0.0:
        return 100.0  # all gains
    if avg_gain == 0.0:
        return 0.0   # all losses

    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def roc(prices: list[float], period: int = 10) -> float | None:
    """
    Rate of Change (percentage).

    ROC = (price[t] - price[t-period]) / price[t-period] * 100

    Args:
        prices: Price series (most recent last).
        period: Lookback period (default 10).

    Returns:
        ROC as a percentage (e.g. 2.5 = 2.5%), or None if insufficient history.
    """
    if period <= 0:
        raise ValueError(f"period must be > 0, got {period}")
    if len(prices) < period + 1:
        return None
    past_price = prices[-(period + 1)]
    if past_price == 0.0:
        return None  # undefined: division by zero
    return (prices[-1] - past_price) / past_price * 100.0


def macd(
    prices: list[float],
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
) -> tuple[float | None, float | None, float | None]:
    """
    MACD (Moving Average Convergence/Divergence).

    Returns:
        (macd_line, signal_line, histogram)
        Any component is None if insufficient history exists.

    macd_line  = EMA(fast) - EMA(slow)
    signal_line = EMA(macd_line, signal_period)
    histogram  = macd_line - signal_line

    Args:
        prices:        Price series (most recent last).
        fast_period:   Fast EMA period (default 12).
        slow_period:   Slow EMA period (default 26).
        signal_period: Signal EMA period (default 9).

    Returns:
        Tuple (macd_line, signal_line, histogram). Any value is None on
        insufficient history.
    """
    if fast_period <= 0 or slow_period <= 0 or signal_period <= 0:
        raise ValueError("All periods must be > 0")
    if fast_period >= slow_period:
        raise ValueError(f"fast_period ({fast_period}) must be < slow_period ({slow_period})")

    # Need at least slow_period prices for first macd_line value
    if len(prices) < slow_period:
        return (None, None, None)

    # Compute full EMA series for fast and slow
    fast_series = ema_series(prices, fast_period)
    slow_series = ema_series(prices, slow_period)

    # MACD line = fast_ema - slow_ema (only where both are defined)
    macd_values: list[float | None] = []
    for f, s in zip(fast_series, slow_series):
        if f is None or s is None:
            macd_values.append(None)
        else:
            macd_values.append(f - s)

    # Signal line = EMA of macd_line values (drop leading Nones first)
    valid_macd = [v for v in macd_values if v is not None]
    if len(valid_macd) < signal_period:
        return (macd_values[-1], None, None)

    # Compute EMA of the valid macd values for the signal line
    signal_ema = _ema_of_series(valid_macd, signal_period)
    if signal_ema is None:
        return (macd_values[-1], None, None)

    current_macd = macd_values[-1]
    if current_macd is None:
        return (None, None, None)

    histogram_val = current_macd - signal_ema
    return (current_macd, signal_ema, histogram_val)


def _ema_of_series(values: list[float], period: int) -> float | None:
    """Compute EMA of a list with no None values."""
    if len(values) < period:
        return None
    k = 2.0 / (period + 1)
    current = sum(values[:period]) / period
    for v in values[period:]:
        current = v * k + current * (1.0 - k)
    return current
