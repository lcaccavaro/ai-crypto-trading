"""
pytest configuration for the test suite.

Defines custom markers:
    live: Tests that require a live internet connection to Binance.
          Run with: pytest -m live
          Skip with: pytest -m "not live"

Offline tests (-m "not live") must run without any network access.
"""

import pytest


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "live: mark test as requiring live Binance API access (skip when offline)",
    )
