"""
crypto_research.backtest — Point-In-Time Backtest Engine (Prompt 03)

Public API:
    BacktestEngine          — Main engine that runs a strategy over historical data.
    BacktestDataProvider    — Validates and loads canonical datasets.
    HistoricalDataView      — Point-in-time gated data access for strategies.
    CostModel               — Fee, slippage, and spread calculations.
    PositionSizer           — Risk-based and fixed position sizing.
    RiskGate                — Pre-entry portfolio and risk limit checks.
    ExecutionSimulator      — Candle-level fill simulation.
    PortfolioAccountant     — Capital, equity, and PnL tracking.
    BacktestResult          — Complete result container.
    BacktestMetrics         — Computed performance metrics.
    EngineValidationStrategy — Deterministic ENGINE_VALIDATION_ONLY strategy.

WARNING: This is a HISTORICAL SIMULATION engine. Results do not predict
future performance. No strategy edge has been established.

The engine is designed so that Prompt 04 can plug in many strategies without
rewriting any engine code.
"""

from crypto_research.backtest.backtest_data_provider import (
    BacktestDataProvider,
    HistoricalDataView,
)
from crypto_research.backtest.cost_model import CostModel
from crypto_research.backtest.engine import BacktestEngine
from crypto_research.backtest.execution_simulator import ExecutionSimulator
from crypto_research.backtest.metrics import BacktestMetrics, compute_metrics
from crypto_research.backtest.portfolio_accountant import PortfolioAccountant
from crypto_research.backtest.position_sizer import PositionSizer
from crypto_research.backtest.result import BacktestResult, BacktestResultWriter
from crypto_research.backtest.risk_gate import RiskGate
from crypto_research.backtest.validation_strategy import EngineValidationStrategy

__all__ = [
    "BacktestDataProvider",
    "BacktestEngine",
    "BacktestMetrics",
    "BacktestResult",
    "BacktestResultWriter",
    "CostModel",
    "EngineValidationStrategy",
    "ExecutionSimulator",
    "HistoricalDataView",
    "PortfolioAccountant",
    "PositionSizer",
    "RiskGate",
    "compute_metrics",
]
