"""
Unit tests for the configuration system.

Tests:
    - Valid configuration loads correctly.
    - Missing required fields raise ConfigurationError.
    - Invalid field values raise ConfigurationError.
    - Unknown/extra fields raise ConfigurationError (extra='forbid').
    - Invalid timeframe strings raise ConfigurationError.
    - Duplicate assets raise ConfigurationError.
    - Empty configuration file raises ConfigurationError.
    - Missing configuration file raises ConfigurationError.
    - config_to_dict() produces a serializable dict.
"""

import tempfile
from pathlib import Path

import pytest
import yaml

from crypto_research.config.loader import config_to_dict, load_config
from crypto_research.core.exceptions import ConfigurationError

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

VALID_CONFIG: dict = {
    "project": {"name": "test_lab", "version": "1.0.0"},
    "research": {"market": "crypto", "data_source": "binance"},
    "assets": ["BTCUSDT", "ETHUSDT"],
    "timeframes": ["1m", "5m", "1h"],
    "risk": {
        "risk_reward_ratio": 3.0,
        "risk_per_trade_pct": 1.0,
        "max_concurrent_positions": 5,
        "max_daily_loss_pct": 3.0,
        "daily_profit_target_pct": 2.0,
    },
    "execution": {"fee_rate": None, "slippage_model": None},
    "logging": {"level": "INFO", "format": "console"},
}


def write_config(tmp_path: Path, data: dict) -> Path:
    """Write a YAML config to a temp file and return its path."""
    config_file = tmp_path / "config.yaml"
    with open(config_file, "w") as f:
        yaml.dump(data, f)
    return config_file


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


class TestValidConfig:
    def test_load_valid_config(self, tmp_path):
        path = write_config(tmp_path, VALID_CONFIG)
        config = load_config(path)
        assert config.project.name == "test_lab"
        assert config.project.version == "1.0.0"
        assert config.research.market == "crypto"
        assert config.research.data_source == "binance"
        assert "BTCUSDT" in config.assets
        assert "ETHUSDT" in config.assets
        assert "1m" in config.timeframes

    def test_timeframes_normalized(self, tmp_path):
        """Timeframe values should be normalized to their Enum string values."""
        path = write_config(tmp_path, VALID_CONFIG)
        config = load_config(path)
        assert all(isinstance(tf, str) for tf in config.timeframes)

    def test_risk_values_stored(self, tmp_path):
        path = write_config(tmp_path, VALID_CONFIG)
        config = load_config(path)
        assert config.risk.risk_reward_ratio == 3.0
        assert config.risk.risk_per_trade_pct == 1.0
        assert config.risk.max_concurrent_positions == 5

    def test_execution_nulls_allowed(self, tmp_path):
        path = write_config(tmp_path, VALID_CONFIG)
        config = load_config(path)
        assert config.execution.fee_rate is None
        assert config.execution.slippage_model is None

    def test_config_to_dict_is_serializable(self, tmp_path):
        import json
        path = write_config(tmp_path, VALID_CONFIG)
        config = load_config(path)
        d = config_to_dict(config)
        # Must be JSON-serializable
        json.dumps(d)
        assert isinstance(d, dict)
        assert "project" in d
        assert "assets" in d


# ---------------------------------------------------------------------------
# File-level errors
# ---------------------------------------------------------------------------


class TestFileErrors:
    def test_missing_file_raises_config_error(self, tmp_path):
        missing = tmp_path / "nonexistent.yaml"
        with pytest.raises(ConfigurationError, match="not found"):
            load_config(missing)

    def test_empty_file_raises_config_error(self, tmp_path):
        empty_file = tmp_path / "empty.yaml"
        empty_file.write_text("")
        with pytest.raises(ConfigurationError, match="empty"):
            load_config(empty_file)

    def test_invalid_yaml_raises_config_error(self, tmp_path):
        bad_yaml = tmp_path / "bad.yaml"
        bad_yaml.write_text("key: [unclosed bracket\n  - item")
        with pytest.raises(ConfigurationError, match="parse"):
            load_config(bad_yaml)

    def test_non_dict_yaml_raises_config_error(self, tmp_path):
        list_yaml = tmp_path / "list.yaml"
        list_yaml.write_text("- item1\n- item2\n")
        with pytest.raises(ConfigurationError, match="mapping"):
            load_config(list_yaml)


# ---------------------------------------------------------------------------
# Missing required fields
# ---------------------------------------------------------------------------


class TestMissingFields:
    def _config_without(self, key: str) -> dict:
        import copy
        cfg = copy.deepcopy(VALID_CONFIG)
        del cfg[key]
        return cfg

    def test_missing_project_raises(self, tmp_path):
        path = write_config(tmp_path, self._config_without("project"))
        with pytest.raises(ConfigurationError):
            load_config(path)

    def test_missing_assets_raises(self, tmp_path):
        path = write_config(tmp_path, self._config_without("assets"))
        with pytest.raises(ConfigurationError):
            load_config(path)

    def test_missing_timeframes_raises(self, tmp_path):
        path = write_config(tmp_path, self._config_without("timeframes"))
        with pytest.raises(ConfigurationError):
            load_config(path)

    def test_missing_risk_raises(self, tmp_path):
        path = write_config(tmp_path, self._config_without("risk"))
        with pytest.raises(ConfigurationError):
            load_config(path)

    def test_empty_assets_list_raises(self, tmp_path):
        import copy
        cfg = copy.deepcopy(VALID_CONFIG)
        cfg["assets"] = []
        path = write_config(tmp_path, cfg)
        with pytest.raises(ConfigurationError):
            load_config(path)


# ---------------------------------------------------------------------------
# Invalid field values
# ---------------------------------------------------------------------------


class TestInvalidValues:
    def test_invalid_timeframe_raises(self, tmp_path):
        import copy
        cfg = copy.deepcopy(VALID_CONFIG)
        cfg["timeframes"] = ["1m", "99x"]  # 99x is not valid
        path = write_config(tmp_path, cfg)
        with pytest.raises(ConfigurationError):
            load_config(path)

    def test_duplicate_assets_raises(self, tmp_path):
        import copy
        cfg = copy.deepcopy(VALID_CONFIG)
        cfg["assets"] = ["BTCUSDT", "BTCUSDT"]
        path = write_config(tmp_path, cfg)
        with pytest.raises(ConfigurationError):
            load_config(path)

    def test_negative_risk_reward_raises(self, tmp_path):
        import copy
        cfg = copy.deepcopy(VALID_CONFIG)
        cfg["risk"]["risk_reward_ratio"] = -1.0
        path = write_config(tmp_path, cfg)
        with pytest.raises(ConfigurationError):
            load_config(path)

    def test_invalid_log_level_raises(self, tmp_path):
        import copy
        cfg = copy.deepcopy(VALID_CONFIG)
        cfg["logging"]["level"] = "VERBOSE"  # not a valid level
        path = write_config(tmp_path, cfg)
        with pytest.raises(ConfigurationError):
            load_config(path)

    def test_extra_unknown_key_raises(self, tmp_path):
        """Extra keys must not be silently ignored — extra='forbid'."""
        import copy
        cfg = copy.deepcopy(VALID_CONFIG)
        cfg["unexpected_top_level_key"] = "should_fail"
        path = write_config(tmp_path, cfg)
        with pytest.raises(ConfigurationError):
            load_config(path)
