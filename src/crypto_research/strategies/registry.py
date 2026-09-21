"""
Strategy registry — central catalog and factory for all Prompt 04 strategies.

The registry is the single source of truth for:
    - Which strategies exist
    - Their metadata
    - How to instantiate them with parameters

Usage:
    # Register (done in each strategy module via decorator):
    @REGISTRY.register
    class EMACrossover(BaseStrategy):
        ...

    # Query:
    strategies = REGISTRY.list()
    strategy = REGISTRY.get("EMA_CROSS_001")
    trend_strategies = REGISTRY.filter_by_category("trend")
    instance = REGISTRY.instantiate("EMA_CROSS_001", fast_period=9, slow_period=21)
"""

from __future__ import annotations

from typing import Type

from crypto_research.core.domain import StrategyInfo
from crypto_research.strategies.base import BaseStrategy


class StrategyRegistry:
    """
    Central registry for all Prompt 04 strategy implementations.

    Thread safety: This registry is designed for single-threaded research use.
    No locking is implemented. Do not share across threads.
    """

    def __init__(self) -> None:
        self._registry: dict[str, Type[BaseStrategy]] = {}

    def register(self, strategy_class: Type[BaseStrategy]) -> Type[BaseStrategy]:
        """
        Register a strategy class.

        Can be used as a decorator:
            @REGISTRY.register
            class MyStrategy(BaseStrategy):
                ...

        Args:
            strategy_class: Concrete subclass of BaseStrategy.

        Returns:
            The same strategy_class (for use as a decorator).

        Raises:
            TypeError: If strategy_class is not a BaseStrategy subclass.
            ValueError: If a strategy with the same ID is already registered.
        """
        if not (isinstance(strategy_class, type) and issubclass(strategy_class, BaseStrategy)):
            raise TypeError(
                f"registry.register() requires a BaseStrategy subclass, "
                f"got {strategy_class!r}"
            )
        if not hasattr(strategy_class, "_info"):
            raise TypeError(
                f"{strategy_class.__name__} must define class attribute `_info: StrategyInfo` "
                f"before registration."
            )

        sid = strategy_class._info.strategy_id
        if sid in self._registry:
            raise ValueError(
                f"Strategy '{sid}' is already registered. "
                f"Use a unique strategy_id for each strategy."
            )
        self._registry[sid] = strategy_class
        return strategy_class

    def get(self, strategy_id: str) -> Type[BaseStrategy]:
        """
        Return the strategy class for a given strategy_id.

        Args:
            strategy_id: Unique strategy identifier (e.g. "EMA_CROSS_001").

        Returns:
            Strategy class.

        Raises:
            KeyError: If strategy_id is not registered.
        """
        if strategy_id not in self._registry:
            available = sorted(self._registry.keys())
            raise KeyError(
                f"Strategy '{strategy_id}' not found in registry. "
                f"Available: {available}"
            )
        return self._registry[strategy_id]

    def list(self) -> list[StrategyInfo]:
        """
        Return metadata for all registered strategies, sorted by strategy_id.

        Returns:
            List of StrategyInfo objects.
        """
        return [cls._info for cls in sorted(self._registry.values(), key=lambda c: c._info.strategy_id)]

    def filter_by_category(self, category: str) -> list[StrategyInfo]:
        """
        Return metadata for all strategies in a given category.

        Args:
            category: Strategy category (e.g. "trend", "momentum").

        Returns:
            List of StrategyInfo objects matching the category.
        """
        return [
            cls._info
            for cls in sorted(self._registry.values(), key=lambda c: c._info.strategy_id)
            if cls._info.category == category
        ]

    def instantiate(
        self,
        strategy_id: str,
        **parameters,
    ) -> BaseStrategy:
        """
        Instantiate a strategy with the given parameters.

        If no parameters are provided, the strategy's default parameters are used.

        Args:
            strategy_id: Strategy identifier.
            **parameters: Strategy-specific parameter overrides.

        Returns:
            Configured strategy instance.

        Raises:
            KeyError:    If strategy_id is not registered.
            ValueError:  If parameters are invalid for the strategy.
        """
        cls = self.get(strategy_id)
        if parameters:
            return cls(**parameters)
        return cls()

    def strategy_ids(self) -> list[str]:
        """Return sorted list of all registered strategy IDs."""
        return sorted(self._registry.keys())

    def categories(self) -> list[str]:
        """Return sorted list of unique categories."""
        return sorted({cls._info.category for cls in self._registry.values()})

    def __len__(self) -> int:
        return len(self._registry)

    def __contains__(self, strategy_id: str) -> bool:
        return strategy_id in self._registry

    def __repr__(self) -> str:
        return f"StrategyRegistry({len(self._registry)} strategies)"


# Global singleton registry — all strategies register into this instance
REGISTRY = StrategyRegistry()
