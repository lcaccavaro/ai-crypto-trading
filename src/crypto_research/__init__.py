"""
crypto_research — Quantitative Research Laboratory for Cryptocurrency Markets.

This package is the foundational infrastructure for reproducible quantitative
research. It provides:

  - Configuration management (config/)
  - Core domain models and exceptions (core/)
  - Data provider interface (data/)
  - Strategy interface (strategies/)
  - Execution engine interface (execution/)
  - Risk manager interface (risk/)
  - Research run management (research/)
  - Reporting infrastructure (reporting/)
  - Utilities: logging, git, environment (utils/)

IMPORTANT: This package does NOT contain:
  - Real Binance data ingestion (Prompt 02)
  - Strategy implementations (Prompt 04)
  - Backtesting execution engine (Prompt 03)
  - Risk management logic (Prompt 05)
  - Frontend or dashboard (not in this project)

Design principles enforced throughout:
  - No look-ahead bias
  - No silent fallbacks
  - Fail fast on errors
  - Every run is reproducible and traceable
"""

__version__ = "1.0.0"
