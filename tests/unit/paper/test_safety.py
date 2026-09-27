"""
Unit tests for PaperSafetyGuard — Prompt 08.

Tests:
    - PAPER mode passes validation
    - REPLAY mode passes validation
    - LIVE mode raises ConfigurationError
    - allow_real_orders=True raises ConfigurationError
    - reject_live_mode() utility function
"""

from __future__ import annotations

import pytest

from crypto_research.config.schema import PaperSafetyConfig, PaperTradingConfig
from crypto_research.core.domain import ExecutionMode
from crypto_research.core.exceptions import ConfigurationError
from crypto_research.paper.safety import PaperSafetyGuard, reject_live_mode


def _make_config(**safety_kwargs) -> PaperTradingConfig:
    """Helper: create PaperTradingConfig with custom safety settings."""
    return PaperTradingConfig(
        safety=PaperSafetyConfig(**safety_kwargs),
    )


class TestPaperSafetyGuard:
    """Safety guard must block LIVE mode unconditionally."""

    def test_paper_mode_passes(self):
        """PAPER is a valid execution mode — no exception raised."""
        config = _make_config(allow_real_orders=False, require_paper_mode=True)
        guard = PaperSafetyGuard(config)
        guard.validate(ExecutionMode.PAPER)  # Should not raise

    def test_replay_mode_passes(self):
        """REPLAY is a valid execution mode — no exception raised."""
        config = _make_config(allow_real_orders=False, require_paper_mode=True)
        guard = PaperSafetyGuard(config)
        guard.validate(ExecutionMode.REPLAY)  # Should not raise

    def test_live_mode_raises(self):
        """LIVE mode must always raise ConfigurationError — belt-and-suspenders."""
        config = _make_config(allow_real_orders=False, require_paper_mode=True)
        guard = PaperSafetyGuard(config)
        with pytest.raises(ConfigurationError, match="LIVE"):
            guard.validate(ExecutionMode.LIVE)

    def test_live_mode_raises_even_without_require_paper_mode(self):
        """LIVE must be rejected regardless of require_paper_mode flag."""
        config = _make_config(allow_real_orders=False, require_paper_mode=False)
        guard = PaperSafetyGuard(config)
        with pytest.raises(ConfigurationError, match="LIVE"):
            guard.validate(ExecutionMode.LIVE)

    def test_allow_real_orders_true_raises(self):
        """allow_real_orders=True must always raise, before mode is checked."""
        config = _make_config(allow_real_orders=True, require_paper_mode=True)
        guard = PaperSafetyGuard(config)
        with pytest.raises(ConfigurationError, match="allow_real_orders"):
            guard.validate(ExecutionMode.PAPER)

    def test_allow_real_orders_true_raises_on_paper_mode(self):
        """Even with a valid mode, allow_real_orders=True must be rejected."""
        config = _make_config(allow_real_orders=True, require_paper_mode=False)
        guard = PaperSafetyGuard(config)
        with pytest.raises(ConfigurationError, match="allow_real_orders"):
            guard.validate(ExecutionMode.PAPER)

    def test_backtest_mode_rejected_when_require_paper_mode_true(self):
        """BACKTEST is not PAPER — should be rejected when require_paper_mode is True."""
        config = _make_config(allow_real_orders=False, require_paper_mode=True)
        guard = PaperSafetyGuard(config)
        with pytest.raises(ConfigurationError):
            guard.validate(ExecutionMode.BACKTEST)

    def test_backtest_mode_passes_when_require_paper_mode_false(self):
        """When require_paper_mode is False, BACKTEST is not explicitly blocked."""
        config = _make_config(allow_real_orders=False, require_paper_mode=False)
        guard = PaperSafetyGuard(config)
        # BACKTEST is not LIVE — should pass when require_paper_mode is False
        guard.validate(ExecutionMode.BACKTEST)  # Should not raise


class TestRejectLiveMode:
    """Standalone reject_live_mode() function tests."""

    def test_live_raises(self):
        with pytest.raises(ConfigurationError, match="LIVE"):
            reject_live_mode(ExecutionMode.LIVE)

    def test_paper_passes(self):
        reject_live_mode(ExecutionMode.PAPER)  # Should not raise

    def test_replay_passes(self):
        reject_live_mode(ExecutionMode.REPLAY)  # Should not raise

    def test_backtest_passes(self):
        reject_live_mode(ExecutionMode.BACKTEST)  # Should not raise


class TestSafetyConfigDefaults:
    """Default config must be safe."""

    def test_default_config_is_safe(self):
        """Default PaperTradingConfig must not allow real orders."""
        cfg = PaperTradingConfig()
        assert cfg.safety.allow_real_orders is False
        assert cfg.safety.require_paper_mode is True

    def test_default_config_allows_paper(self):
        """Default config must allow PAPER mode."""
        cfg = PaperTradingConfig()
        guard = PaperSafetyGuard(cfg)
        guard.validate(ExecutionMode.PAPER)  # Should not raise

    def test_default_config_blocks_live(self):
        """Default config must block LIVE mode."""
        cfg = PaperTradingConfig()
        guard = PaperSafetyGuard(cfg)
        with pytest.raises(ConfigurationError):
            guard.validate(ExecutionMode.LIVE)
