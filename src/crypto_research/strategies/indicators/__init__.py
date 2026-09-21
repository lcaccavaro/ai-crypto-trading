"""
Indicator library for the crypto research strategy framework.

All indicators are pure, stateless functions:
    - Input: price/volume series + parameters
    - Output: float | None (None = insufficient history or undefined)
    - Never raise on insufficient data — always return None
    - Point-in-time safe: computed from closed candles only

Public API
----------
Moving Averages:
    sma(prices, period) -> float | None
    ema(prices, period) -> float | None
    ema_series(prices, period) -> list[float | None]
    wma(prices, period) -> float | None

Momentum:
    rsi(prices, period=14) -> float | None
    roc(prices, period=10) -> float | None
    macd(prices, fast=12, slow=26, signal=9) -> tuple[float|None, float|None, float|None]

Volatility:
    atr(highs, lows, closes, period=14) -> float | None
    rolling_std(prices, period) -> float | None
    bollinger_bands(prices, period=20, num_std=2.0) -> tuple[float|None, float|None, float|None]
    bb_width(prices, period=20, num_std=2.0) -> float | None

Volume:
    relative_volume(volumes, period=20) -> float | None
    volume_sma(volumes, period=20) -> float | None

Statistical:
    zscore(prices, period=20) -> float | None
    donchian_channels(highs, lows, period=20, use_previous_window=True) -> tuple[float|None, float|None]
    rolling_high(prices, period, shift=0) -> float | None
    rolling_low(prices, period, shift=0) -> float | None
"""

from crypto_research.strategies.indicators.momentum import macd, roc, rsi
from crypto_research.strategies.indicators.moving_averages import ema, ema_series, sma, wma
from crypto_research.strategies.indicators.statistical import (
    donchian_channels,
    rolling_high,
    rolling_low,
    zscore,
)
from crypto_research.strategies.indicators.volatility import (
    atr,
    bb_width,
    bollinger_bands,
    rolling_std,
)
from crypto_research.strategies.indicators.volume import relative_volume, volume_sma

__all__ = [
    # Moving averages
    "sma",
    "ema",
    "ema_series",
    "wma",
    # Momentum
    "rsi",
    "roc",
    "macd",
    # Volatility
    "atr",
    "rolling_std",
    "bollinger_bands",
    "bb_width",
    # Volume
    "relative_volume",
    "volume_sma",
    # Statistical
    "zscore",
    "donchian_channels",
    "rolling_high",
    "rolling_low",
]
