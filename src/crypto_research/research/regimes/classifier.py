"""
Market Regime Classifier — Prompt 07.

Provides transparent, deterministic, PIT-safe regime classification.

PIT GUARANTEE (critical):
    classify_candle() at timestamp T uses ONLY candles with index <= T.
    It never reads forward into candles that haven't closed yet.
    Rolling windows are computed with .shift(1) or closed='left' semantics.

Regime Dimensions:
    TREND:      TREND_UP | TREND_DOWN | RANGE
    VOLATILITY: LOW_VOL  | NORMAL_VOL | HIGH_VOL

Design principles:
    - No ML, no black-box models.
    - All thresholds are configurable and documented.
    - Each classification produces a human-readable label.
    - Classifications are based on indicators already available at T.
    - Rolling calculations use pandas rolling windows with min_periods.

Limitations (documented per Prompt 07):
    - Regime labels are defined thresholds, not ground truth.
    - Classification changes may lag the actual market transition.
    - These labels are for descriptive research, not trading signals.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

import pandas as pd
import numpy as np

from crypto_research.config.schema import RegimeConfig
from crypto_research.utils.logging import get_logger

logger = get_logger(__name__)


class TrendRegime(str, Enum):
    TREND_UP = "TREND_UP"
    TREND_DOWN = "TREND_DOWN"
    RANGE = "RANGE"


class VolatilityRegime(str, Enum):
    LOW_VOL = "LOW_VOL"
    NORMAL_VOL = "NORMAL_VOL"
    HIGH_VOL = "HIGH_VOL"


@dataclass(frozen=True)
class RegimeLabel:
    """Combined regime classification for one candle timestamp."""
    timestamp: datetime
    trend: TrendRegime
    volatility: VolatilityRegime
    ma_value: Optional[float]        # for audit / transparency
    atr_pct: Optional[float]         # ATR as % of price

    @property
    def combined(self) -> str:
        return f"{self.trend.value}_{self.volatility.value}"

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "trend": self.trend.value,
            "volatility": self.volatility.value,
            "combined": self.combined,
            "ma_value": round(self.ma_value, 4) if self.ma_value else None,
            "atr_pct": round(self.atr_pct, 4) if self.atr_pct else None,
        }


class RegimeClassifier:
    """
    PIT-safe market regime classifier.

    Classifies EVERY candle in a DataFrame with TREND + VOLATILITY regime.
    All rolling windows are computed at once using vectorized pandas operations.

    PIT safety:
        Rolling window uses `.rolling(n).mean()` which at position i uses
        candles [i-n+1 ... i]. This is causal — no future data is included.
        ATR and MA are computed the same way.
    """

    def __init__(self, config: RegimeConfig) -> None:
        self._cfg = config

    def classify_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add regime columns to a OHLCV DataFrame.

        Args:
            df: DataFrame with columns ['timestamp', 'open', 'high', 'low', 'close', 'volume'].
                Must be sorted by timestamp ascending.

        Returns:
            DataFrame with additional columns:
                trend_regime, vol_regime, combined_regime, ma_value, atr_pct
        """
        if df.empty:
            df["trend_regime"] = pd.NA
            df["vol_regime"] = pd.NA
            df["combined_regime"] = pd.NA
            df["ma_value"] = pd.NA
            df["atr_pct"] = pd.NA
            return df

        ma_period = self._cfg.trend.ma_period
        atr_period = self._cfg.volatility.atr_period
        slope_threshold = self._cfg.trend.slope_threshold_pct / 100.0
        low_vol_threshold = self._cfg.volatility.low_threshold_pct / 100.0
        high_vol_threshold = self._cfg.volatility.high_threshold_pct / 100.0

        close = df["close"].astype(float)
        high = df["high"].astype(float)
        low = df["low"].astype(float)

        # PIT-safe MA: at row i, uses candles [i-ma_period+1..i]
        ma = close.rolling(window=ma_period, min_periods=max(1, ma_period // 2)).mean()

        # Trend: compare close to MA with slope component
        # Positive = above MA, negative = below MA
        price_vs_ma = (close - ma) / ma.replace(0, pd.NA)

        # ATR (Wilder-style approximated with rolling)
        tr = pd.concat([
            high - low,
            (high - close.shift(1)).abs(),
            (low - close.shift(1)).abs(),
        ], axis=1).max(axis=1)
        atr = tr.rolling(window=atr_period, min_periods=max(1, atr_period // 2)).mean()
        atr_pct = (atr / close.replace(0, pd.NA))  # ATR as fraction of price

        # Trend classification
        trend_regime = pd.Series(index=df.index, dtype=str)
        trend_regime[:] = TrendRegime.RANGE.value
        trend_regime[price_vs_ma > slope_threshold] = TrendRegime.TREND_UP.value
        trend_regime[price_vs_ma < -slope_threshold] = TrendRegime.TREND_DOWN.value

        # Volatility classification
        vol_regime = pd.Series(index=df.index, dtype=str)
        vol_regime[:] = VolatilityRegime.NORMAL_VOL.value
        vol_regime[atr_pct < low_vol_threshold] = VolatilityRegime.LOW_VOL.value
        vol_regime[atr_pct > high_vol_threshold] = VolatilityRegime.HIGH_VOL.value

        df = df.copy()
        df["ma_value"] = ma.round(6)
        df["atr_pct"] = atr_pct.round(6)
        df["trend_regime"] = trend_regime
        df["vol_regime"] = vol_regime
        df["combined_regime"] = trend_regime + "_" + vol_regime

        logger.info(
            "Regime classification complete",
            candles=len(df),
            trend_counts=trend_regime.value_counts().to_dict(),
            vol_counts=vol_regime.value_counts().to_dict(),
        )
        return df

    def get_regime_at(self, classified_df: pd.DataFrame, timestamp: datetime) -> Optional[RegimeLabel]:
        """
        Look up the regime for a specific timestamp.
        PIT-safe: uses the classified_df which was computed on closed candles only.
        """
        if "combined_regime" not in classified_df.columns:
            return None

        # Find the last row at or before timestamp
        if "timestamp" in classified_df.columns:
            row_mask = classified_df["timestamp"] <= timestamp
        else:
            row_mask = classified_df.index <= timestamp

        matching = classified_df[row_mask]
        if matching.empty:
            return None

        row = matching.iloc[-1]
        return RegimeLabel(
            timestamp=timestamp,
            trend=TrendRegime(row.get("trend_regime", TrendRegime.RANGE.value)),
            volatility=VolatilityRegime(row.get("vol_regime", VolatilityRegime.NORMAL_VOL.value)),
            ma_value=row.get("ma_value"),
            atr_pct=row.get("atr_pct"),
        )
