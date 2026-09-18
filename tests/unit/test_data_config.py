"""
Unit tests for the DataConfig configuration extension (Prompt 02).

Tests:
    - Valid data config loads correctly.
    - Invalid market_type raises ConfigurationError.
    - Invalid date format raises ConfigurationError.
    - end_date before start_date raises ConfigurationError.
    - end_date equal to start_date raises ConfigurationError.
    - Extra unknown keys in data section raise ConfigurationError.
    - Full ProjectConfiguration with data section loads correctly.
    - Missing data section raises ConfigurationError.
"""

import tempfile
from pathlib import Path

import pytest
import yaml

from crypto_research.config.loader import load_config
from crypto_research.config.schema import DataConfig, ProjectConfiguration
from crypto_research.core.exceptions import ConfigurationError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

BASE_CONFIG = {
    "project": {"name": "test_lab", "version": "1.0.0"},
    "research": {"market": "crypto", "data_source": "binance"},
    "assets": ["BTCUSDT"],
    "timeframes": ["1m"],
    "data": {
        "market_type": "futures",
        "start_date": "2024-01-01",
        "end_date": "2024-03-01",
    },
    "risk": {
        "risk_reward_ratio": 3.0,
        "risk_per_trade_pct": 1.0,
        "max_concurrent_positions": 5,
        "max_daily_loss_pct": 3.0,
        "daily_profit_target_pct": None,
    },
    "execution": {"fee_rate": None, "slippage_model": None},
    "logging": {"level": "INFO", "format": "console"},
}


def write_config(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / "config.yaml"
    with open(path, "w") as f:
        yaml.dump(data, f)
    return path


# ---------------------------------------------------------------------------
# DataConfig unit tests
# ---------------------------------------------------------------------------


class TestDataConfig:
    def test_valid_data_config(self):
        cfg = DataConfig(
            market_type="futures",
            start_date="2024-01-01",
            end_date="2024-06-01",
        )
        assert cfg.market_type == "futures"
        assert cfg.start_date == "2024-01-01"

    def test_spot_is_valid(self):
        cfg = DataConfig(
            market_type="spot",
            start_date="2024-01-01",
            end_date="2024-02-01",
        )
        assert cfg.market_type == "spot"

    def test_invalid_market_type_raises(self):
        with pytest.raises(Exception, match="market_type"):
            DataConfig(
                market_type="perpetual",
                start_date="2024-01-01",
                end_date="2024-06-01",
            )

    def test_invalid_start_date_format_raises(self):
        with pytest.raises(Exception, match="date"):
            DataConfig(
                market_type="futures",
                start_date="01/01/2024",  # wrong format
                end_date="2024-06-01",
            )

    def test_invalid_end_date_format_raises(self):
        with pytest.raises(Exception, match="date"):
            DataConfig(
                market_type="futures",
                start_date="2024-01-01",
                end_date="2024/06/01",  # wrong format
            )

    def test_end_before_start_raises(self):
        with pytest.raises(Exception, match="end_date"):
            DataConfig(
                market_type="futures",
                start_date="2024-06-01",
                end_date="2024-01-01",
            )

    def test_end_equal_start_raises(self):
        with pytest.raises(Exception, match="end_date"):
            DataConfig(
                market_type="futures",
                start_date="2024-01-01",
                end_date="2024-01-01",
            )

    def test_defaults_are_set(self):
        cfg = DataConfig(
            market_type="futures",
            start_date="2024-01-01",
            end_date="2024-02-01",
        )
        assert cfg.request_delay_ms == 250
        assert cfg.max_retries == 3
        assert cfg.retry_delay_s == 5
        assert cfg.schema_version == "1.0"
        assert cfg.raw_dir == "data/raw"
        assert cfg.processed_dir == "data/processed"
        assert cfg.metadata_dir == "data/metadata"

    def test_extra_key_raises(self):
        with pytest.raises(Exception):
            DataConfig(
                market_type="futures",
                start_date="2024-01-01",
                end_date="2024-02-01",
                unknown_field="should_fail",
            )


# ---------------------------------------------------------------------------
# Full config YAML loading tests (with data section)
# ---------------------------------------------------------------------------


class TestFullConfigWithData:
    def test_full_config_loads_with_data_section(self, tmp_path):
        path = write_config(tmp_path, BASE_CONFIG)
        config = load_config(path)
        assert config.data.market_type == "futures"
        assert config.data.start_date == "2024-01-01"
        assert config.data.end_date == "2024-03-01"

    def test_missing_data_section_raises(self, tmp_path):
        import copy
        cfg = copy.deepcopy(BASE_CONFIG)
        del cfg["data"]
        path = write_config(tmp_path, cfg)
        with pytest.raises(ConfigurationError):
            load_config(path)

    def test_invalid_market_type_in_yaml_raises(self, tmp_path):
        import copy
        cfg = copy.deepcopy(BASE_CONFIG)
        cfg["data"]["market_type"] = "swaps"
        path = write_config(tmp_path, cfg)
        with pytest.raises(ConfigurationError):
            load_config(path)

    def test_end_before_start_in_yaml_raises(self, tmp_path):
        import copy
        cfg = copy.deepcopy(BASE_CONFIG)
        cfg["data"]["start_date"] = "2025-01-01"
        cfg["data"]["end_date"] = "2024-01-01"
        path = write_config(tmp_path, cfg)
        with pytest.raises(ConfigurationError):
            load_config(path)
