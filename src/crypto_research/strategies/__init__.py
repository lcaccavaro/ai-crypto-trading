"""
Strategy library for the crypto research laboratory (Prompt 04).

Imports all 26 strategies, triggering their registration into REGISTRY.

Usage:
    from crypto_research.strategies import REGISTRY
    strategies = REGISTRY.list()                    # all 26 StrategyInfo
    cls = REGISTRY.get("EMA_CROSS_001")
    instance = REGISTRY.instantiate("EMA_CROSS_001", fast_period=9, slow_period=21)
"""

# Import all strategy groups — this triggers @REGISTRY.register decorators
from crypto_research.strategies import (
    breakout,
    market_structure,
    mean_reversion,
    momentum,
    multi_indicator,
    trend,
    volatility,
    volume,
)
from crypto_research.strategies.base import BaseStrategy
from crypto_research.strategies.context import StrategyContext, StrategyInstance
from crypto_research.strategies.registry import REGISTRY, StrategyRegistry

__all__ = [
    "REGISTRY",
    "StrategyRegistry",
    "BaseStrategy",
    "StrategyInstance",
    "StrategyContext",
    # Strategy groups (for direct import)
    "trend",
    "momentum",
    "breakout",
    "volatility",
    "volume",
    "multi_indicator",
    "market_structure",
    "mean_reversion",
]
