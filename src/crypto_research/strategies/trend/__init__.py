"""Trend strategy group — EMA Crossover, Triple EMA, Price vs EMA, EMA Slope."""

from crypto_research.strategies.trend.ema_crossover import EMACrossover
from crypto_research.strategies.trend.ema_slope import EMASlope
from crypto_research.strategies.trend.price_vs_ema import PriceVsEMA
from crypto_research.strategies.trend.triple_ema import TripleEMA

__all__ = ["EMACrossover", "TripleEMA", "PriceVsEMA", "EMASlope"]
