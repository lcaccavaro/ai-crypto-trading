"""
Paper Trading Safety Guard — Prompt 08.

Implements the hard architectural constraint that V1 cannot place real orders.

Design:
    PaperSafetyGuard must be called at PaperEngine.__init__().
    If the configuration allows real orders or requests LIVE mode, it raises
    ConfigurationError immediately — before any market data is fetched.

This guard is NOT a soft warning. It is a hard gate.

Unit tested in tests/unit/paper/test_safety.py.
"""

from __future__ import annotations

from crypto_research.config.schema import PaperTradingConfig
from crypto_research.core.domain import ExecutionMode
from crypto_research.core.exceptions import ConfigurationError
from crypto_research.utils.logging import get_logger

logger = get_logger(__name__)

# The one and only legal execution mode for Prompt 08
_ALLOWED_MODES: frozenset[ExecutionMode] = frozenset({
    ExecutionMode.PAPER,
    ExecutionMode.REPLAY,
})


class PaperSafetyGuard:
    """
    Hard safety guard enforcing paper-only execution in Prompt 08.

    Raises ConfigurationError immediately on any violation.
    No recovery path is offered — the caller must fix configuration.

    Usage:
        guard = PaperSafetyGuard(config.paper_trading)
        guard.validate(ExecutionMode.PAPER)   # passes
        guard.validate(ExecutionMode.LIVE)    # raises ConfigurationError
    """

    def __init__(self, config: PaperTradingConfig) -> None:
        self._config = config

    def validate(self, mode: ExecutionMode) -> None:
        """
        Validate execution mode and configuration safety flags.

        Args:
            mode: The execution mode requested by the caller.

        Raises:
            ConfigurationError: If real orders are enabled, or if the
                requested mode is not PAPER or REPLAY.
        """
        # Check 1: allow_real_orders must be False
        if self._config.safety.allow_real_orders:
            raise ConfigurationError(
                "SAFETY VIOLATION: paper_trading.safety.allow_real_orders is True. "
                "Real orders are PROHIBITED in V1. "
                "Set allow_real_orders: false to proceed."
            )

        # Check 2: require_paper_mode enforces no LIVE mode
        if self._config.safety.require_paper_mode and mode not in _ALLOWED_MODES:
            raise ConfigurationError(
                f"SAFETY VIOLATION: execution_mode={mode.value!r} is not allowed. "
                f"Only {[m.value for m in _ALLOWED_MODES]} are permitted in Prompt 08. "
                f"LIVE execution is PROHIBITED in V1."
            )

        # Check 3: explicit LIVE rejection (belt-and-suspenders)
        if mode == ExecutionMode.LIVE:
            raise ConfigurationError(
                "SAFETY VIOLATION: ExecutionMode.LIVE is explicitly prohibited in V1. "
                "This system is PAPER TRADING ONLY. "
                "No real orders will ever be placed through this interface."
            )

        logger.info(
            "Safety guard passed",
            execution_mode=mode.value,
            allow_real_orders=self._config.safety.allow_real_orders,
        )


def reject_live_mode(mode: ExecutionMode) -> None:
    """
    Standalone function to reject LIVE mode at any call site.
    Can be used as a guard in any layer that receives an ExecutionMode.

    Raises:
        ConfigurationError: If mode is ExecutionMode.LIVE.
    """
    if mode == ExecutionMode.LIVE:
        raise ConfigurationError(
            f"ExecutionMode.LIVE is prohibited in V1. "
            f"Use ExecutionMode.PAPER or ExecutionMode.REPLAY."
        )
