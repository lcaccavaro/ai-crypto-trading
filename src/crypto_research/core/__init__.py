"""Core package — domain models and exceptions."""
from crypto_research.core.domain import (
    Candle,
    Fill,
    Order,
    OrderSide,
    OrderType,
    Position,
    PositionSide,
    ResearchRun,
    RiskDecision,
    Signal,
    SignalDirection,
    StrategyMetadata,
    Timeframe,
    Trade,
)
from crypto_research.core.exceptions import (
    ConfigurationError,
    CryptoResearchError,
    DataIntegrityError,
    ExecutionError,
    LookAheadBiasError,
    ReproducibilityError,
    ResearchRunError,
)

__all__ = [
    # Domain
    "Candle",
    "Fill",
    "Order",
    "OrderSide",
    "OrderType",
    "Position",
    "PositionSide",
    "ResearchRun",
    "RiskDecision",
    "Signal",
    "SignalDirection",
    "StrategyMetadata",
    "Timeframe",
    "Trade",
    # Exceptions
    "ConfigurationError",
    "CryptoResearchError",
    "DataIntegrityError",
    "ExecutionError",
    "LookAheadBiasError",
    "ReproducibilityError",
    "ResearchRunError",
]
