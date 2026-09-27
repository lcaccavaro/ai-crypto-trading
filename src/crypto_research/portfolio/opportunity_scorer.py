"""
Opportunity Scorer.

Computes a configurable 0-100 score for a strategy signal using PIT features.
Does NOT use future information, previous-day PnL, or any external state.
"""

from __future__ import annotations

from typing import Any

from crypto_research.config.schema import OpportunityScoreConfig
from crypto_research.core.domain import Candle, DecisionOutcome, OpportunityScore, Signal, SignalDirection
from crypto_research.strategies.indicators.momentum import roc
from crypto_research.strategies.indicators.moving_averages import ema_series
from crypto_research.strategies.indicators.volatility import bb_width
from crypto_research.strategies.indicators.volume import relative_volume
from crypto_research.utils.logging import get_logger

logger = get_logger(__name__)


class OpportunityScorer:
    """
    Evaluates trading opportunities by calculating a configurable score [0, 100].
    """

    def __init__(self, config: OpportunityScoreConfig) -> None:
        self._config = config
        self._components = config.components
        self._total_weight = sum(
            c.weight for c in self._components.values() if c.enabled
        )

    def score(
        self, signal: Signal, instance_id: str, candles: list[Candle]
    ) -> OpportunityScore:
        """
        Calculate score for a signal based on recent candles.
        
        Args:
            signal: The strategy signal to evaluate.
            instance_id: Unique strategy instance ID.
            candles: List of candles ending at the signal timestamp. Must contain
                     enough history to compute the required indicators.
                     
        Returns:
            OpportunityScore object with component breakdown.
        """
        if not self._config.enabled or not candles or self._total_weight == 0:
            return self._build_empty_score(signal, instance_id, decision=DecisionOutcome.ACCEPTED)

        # Basic extracted series
        closes = [c.close for c in candles]
        volumes = [c.volume for c in candles]
        current_close = closes[-1]
        
        scores: dict[str, float] = {}
        raw: dict[str, Any] = {}
        
        # 1. Trend Alignment
        if self._is_enabled("trend_alignment"):
            # Use 50-period EMA to determine macro trend
            try:
                # We need at least 50 candles for a decent EMA
                ema_50 = ema_series(closes, period=50)[-1]
                trend_is_up = current_close > ema_50
                
                if signal.direction == SignalDirection.LONG:
                    scores["trend_alignment"] = 100.0 if trend_is_up else 0.0
                elif signal.direction == SignalDirection.SHORT:
                    scores["trend_alignment"] = 0.0 if trend_is_up else 100.0
                else:
                    scores["trend_alignment"] = 50.0
                
                raw["ema_50"] = ema_50
            except (ValueError, IndexError, TypeError):
                scores["trend_alignment"] = 50.0
                
        # 2. Momentum
        if self._is_enabled("momentum"):
            try:
                # Use 14-period ROC
                r = roc(closes, period=14)
                if r is not None:
                    # Normalize ROC: roughly [-5, 5] -> [0, 100]
                    # Cap at +/- 5% for normalization
                    capped = max(min(r, 5.0), -5.0)
                    if signal.direction == SignalDirection.LONG:
                        scores["momentum"] = ((capped + 5.0) / 10.0) * 100.0
                    elif signal.direction == SignalDirection.SHORT:
                        scores["momentum"] = ((-capped + 5.0) / 10.0) * 100.0
                    else:
                        scores["momentum"] = 50.0
                    raw["roc_14"] = r
                else:
                    scores["momentum"] = 50.0
            except Exception:
                scores["momentum"] = 50.0

        # 3. Volatility
        if self._is_enabled("volatility"):
            try:
                # Use 20-period BB width
                w = bb_width(closes, period=20)
                if w is not None:
                    # Prefer moderate to high volatility: width [0, 10%] -> [0, 100]
                    capped = min(w, 10.0)
                    scores["volatility"] = (capped / 10.0) * 100.0
                    raw["bb_width_20"] = w
                else:
                    scores["volatility"] = 50.0
            except Exception:
                scores["volatility"] = 50.0

        # 4. Volume
        if self._is_enabled("volume"):
            try:
                # Relative volume (14-period SMA)
                rv = relative_volume(volumes, period=14)
                if rv is not None:
                    # Prefer high volume: RV [0, 3] -> [0, 100]
                    capped = min(rv, 3.0)
                    scores["volume"] = (capped / 3.0) * 100.0
                    raw["relative_volume_14"] = rv
                else:
                    scores["volume"] = 50.0
            except Exception:
                scores["volume"] = 50.0
                
        # 5. Risk / Reward
        if self._is_enabled("risk_reward"):
            if signal.stop_price and signal.target_price:
                # Compute implied RR
                risk = abs(current_close - signal.stop_price)
                reward = abs(signal.target_price - current_close)
                if risk > 0:
                    rr = reward / risk
                    # Cap RR at 5 for scoring: RR [0, 5] -> [0, 100]
                    capped = min(rr, 5.0)
                    scores["risk_reward"] = (capped / 5.0) * 100.0
                    raw["implied_rr"] = rr
                else:
                    scores["risk_reward"] = 0.0
            else:
                # Neutral if not provided
                scores["risk_reward"] = 50.0

        # 6. Multi-Timeframe (using proxy: signal strength)
        if self._is_enabled("multi_timeframe"):
            scores["multi_timeframe"] = signal.strength * 100.0

        # Compute final weighted score
        total_score = 0.0
        weights: dict[str, float] = {}
        for comp_name, comp_score in scores.items():
            w = self._components[comp_name].weight
            weights[comp_name] = w
            total_score += comp_score * (w / self._total_weight)

        # Decision
        threshold = self._config.minimum_score
        decision = DecisionOutcome.ACCEPTED if total_score >= threshold else DecisionOutcome.REJECTED

        return OpportunityScore(
            timestamp=signal.timestamp,
            strategy_id=signal.strategy_name,
            instance_id=instance_id,
            symbol=signal.asset,
            timeframe=signal.timeframe,
            score_version=self._config.version,
            total_score=total_score,
            component_scores=scores,
            component_weights=weights,
            raw_features=raw,
            threshold=threshold,
            decision=decision,
        )

    def _is_enabled(self, name: str) -> bool:
        comp = self._components.get(name)
        return comp is not None and comp.enabled

    def _build_empty_score(
        self, signal: Signal, instance_id: str, decision: DecisionOutcome
    ) -> OpportunityScore:
        return OpportunityScore(
            timestamp=signal.timestamp,
            strategy_id=signal.strategy_name,
            instance_id=instance_id,
            symbol=signal.asset,
            timeframe=signal.timeframe,
            score_version=self._config.version,
            total_score=100.0 if decision == DecisionOutcome.ACCEPTED else 0.0,
            component_scores={},
            component_weights={},
            raw_features={},
            threshold=self._config.minimum_score,
            decision=decision,
        )
