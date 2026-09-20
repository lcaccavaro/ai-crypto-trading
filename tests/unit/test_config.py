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

import copy
import tempfile
from pathlib import Path

import pytest
import yaml

from crypto_research.config.loader import config_to_dict, load_config
from crypto_research.core.exceptions import ConfigurationError
from tests.fixtures import VALID_CONFIG


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
        # New Prompt 03 risk fields
        assert config.risk.max_total_exposure_pct == 50.0
        assert config.risk.max_asset_exposure_pct == 20.0
        assert config.risk.daily_loss_limit_pct == 3.0

    def test_execution_config_loaded(self, tmp_path):
        """Execution config should have all Prompt 03 fields."""
        path = write_config(tmp_path, VALID_CONFIG)
        config = load_config(path)
        assert config.execution.slippage_bps == 2.0
        assert config.execution.spread_bps == 1.0
        assert config.execution.intrabar_fill_policy == "stop_first"
        assert config.execution.gap_policy == "fill_at_open"
        assert config.execution.allow_same_close_execution is False

    def test_costs_config_loaded(self, tmp_path):
        path = write_config(tmp_path, VALID_CONFIG)
        config = load_config(path)
        assert config.costs.taker_fee_rate == 0.0005
        assert config.costs.maker_fee_rate == 0.0002

    def test_capital_config_loaded(self, tmp_path):
        path = write_config(tmp_path, VALID_CONFIG)
        config = load_config(path)
        assert config.capital.initial_balance == 10000.0
        assert config.capital.risk_per_trade_pct == 1.0

    def test_backtest_config_loaded(self, tmp_path):
        path = write_config(tmp_path, VALID_CONFIG)
        config = load_config(path)
        assert config.backtest.start_date == "2024-01-01"
        assert config.backtest.end_date == "2024-02-01"
        assert "BTCUSDT" in config.backtest.symbols

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

    def test_missing_backtest_raises(self, tmp_path):
        path = write_config(tmp_path, self._config_without("backtest"))
        with pytest.raises(ConfigurationError):
            load_config(path)

    def test_missing_costs_raises(self, tmp_path):
        path = write_config(tmp_path, self._config_without("costs"))
        with pytest.raises(ConfigurationError):
            load_config(path)

    def test_missing_capital_raises(self, tmp_path):
        path = write_config(tmp_path, self._config_without("capital"))
        with pytest.raises(ConfigurationError):
            load_config(path)

    def test_empty_assets_list_raises(self, tmp_path):
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
        cfg = copy.deepcopy(VALID_CONFIG)
        cfg["timeframes"] = ["1m", "99x"]  # 99x is not valid
        path = write_config(tmp_path, cfg)
        with pytest.raises(ConfigurationError):
            load_config(path)

    def test_duplicate_assets_raises(self, tmp_path):
        cfg = copy.deepcopy(VALID_CONFIG)
        cfg["assets"] = ["BTCUSDT", "BTCUSDT"]
        path = write_config(tmp_path, cfg)
        with pytest.raises(ConfigurationError):
            load_config(path)

    def test_negative_risk_reward_raises(self, tmp_path):
        cfg = copy.deepcopy(VALID_CONFIG)
        cfg["risk"]["risk_reward_ratio"] = -1.0
        path = write_config(tmp_path, cfg)
        with pytest.raises(ConfigurationError):
            load_config(path)

    def test_invalid_log_level_raises(self, tmp_path):
        cfg = copy.deepcopy(VALID_CONFIG)
        cfg["logging"]["level"] = "VERBOSE"  # not a valid level
        path = write_config(tmp_path, cfg)
        with pytest.raises(ConfigurationError):
            load_config(path)

    def test_extra_unknown_key_raises(self, tmp_path):
        """Extra keys must not be silently ignored — extra='forbid'."""
        cfg = copy.deepcopy(VALID_CONFIG)
        cfg["unexpected_top_level_key"] = "should_fail"
        path = write_config(tmp_path, cfg)
        with pytest.raises(ConfigurationError):
            load_config(path)

    def test_negative_initial_balance_raises(self, tmp_path):
        cfg = copy.deepcopy(VALID_CONFIG)
        cfg["capital"]["initial_balance"] = -500.0
        path = write_config(tmp_path, cfg)
        with pytest.raises(ConfigurationError):
            load_config(path)

    def test_invalid_intrabar_policy_raises(self, tmp_path):
        cfg = copy.deepcopy(VALID_CONFIG)
        cfg["execution"]["intrabar_fill_policy"] = "random_guess"
        path = write_config(tmp_path, cfg)
        with pytest.raises(ConfigurationError):
            load_config(path)
