"""
Integration test: Full Prompt 01 startup pipeline.

Tests that the complete sequence works end-to-end:
    project startup
        ↓
    configuration loading
        ↓
    validation
        ↓
    research run creation
        ↓
    metadata generation
        ↓
    logging initialization
        ↓
    successful completion (all artifacts verified)

This test does NOT use any fake market data.
It validates infrastructure only — not trading logic.
"""

import json
import re
import tempfile
from pathlib import Path

import pytest
import yaml

from crypto_research.config.loader import load_config
from crypto_research.core.exceptions import ConfigurationError
from crypto_research.research.run_manager import RunManager
from crypto_research.utils.logging import setup_logging

RUN_ID_PATTERN = re.compile(r"^RUN_\d{8}_\d{6}_[0-9a-f]{6}$")

VALID_CONFIG_DATA = """
project:
  name: integration_test_lab
  version: "1.0.0"

research:
  market: crypto
  data_source: binance

assets:
  - BTCUSDT
  - ETHUSDT
  - SOLUSDT

timeframes:
  - 1m
  - 5m
  - 15m
  - 1h

risk:
  risk_reward_ratio: 3.0
  risk_per_trade_pct: 1.0
  max_concurrent_positions: 5
  max_daily_loss_pct: 3.0
  daily_profit_target_pct: 2.0

execution:
  fee_rate: null
  slippage_model: null

logging:
  level: INFO
  format: console
"""


class TestFullStartupPipeline:
    """
    End-to-end integration test for the Prompt 01 pipeline.

    All steps must pass for this test to succeed.
    Any single failure causes the entire test to fail visibly.
    No silent fallbacks are applied at any stage.
    """

    @pytest.fixture
    def config_file(self, tmp_path):
        """Write a valid config YAML to a temporary directory."""
        config_path = tmp_path / "config.yaml"
        config_path.write_text(VALID_CONFIG_DATA.strip())
        return config_path

    @pytest.fixture
    def results_dir(self, tmp_path):
        """Isolated results directory for this test."""
        results = tmp_path / "results"
        results.mkdir()
        return results

    def test_step_01_config_loads(self, config_file):
        """Step 1: Configuration must load from the YAML file."""
        config = load_config(config_file)
        assert config is not None
        assert config.project.name == "integration_test_lab"

    def test_step_02_config_validation_passes(self, config_file):
        """Step 2: Validated config must have correct field types and values."""
        config = load_config(config_file)
        assert isinstance(config.assets, list)
        assert len(config.assets) == 3
        assert "BTCUSDT" in config.assets
        assert isinstance(config.timeframes, list)
        assert len(config.timeframes) == 4
        assert config.risk.risk_reward_ratio == 3.0

    def test_step_03_run_created(self, config_file, results_dir):
        """Step 3: Research run must be created successfully."""
        config = load_config(config_file)
        manager = RunManager(results_dir=results_dir)
        run = manager.create_run(config, config_path=config_file)
        assert run is not None
        assert RUN_ID_PATTERN.match(run.run_id)

    def test_step_04_metadata_generated(self, config_file, results_dir):
        """Step 4: metadata.json must exist with all required fields."""
        config = load_config(config_file)
        manager = RunManager(results_dir=results_dir)
        run = manager.create_run(config, config_path=config_file)

        metadata_file = Path(run.run_directory) / "metadata.json"
        assert metadata_file.exists()

        with open(metadata_file) as f:
            metadata = json.load(f)

        # All required fields must be present
        for field in [
            "run_id", "created_at", "python_version", "package_versions",
            "git_commit", "config_path", "config_snapshot", "assets",
            "timeframes", "run_directory", "environment_info",
        ]:
            assert field in metadata, f"Required field '{field}' missing from metadata.json"

    def test_step_05_config_snapshot_matches_input(self, config_file, results_dir):
        """Step 5: Config snapshot must match the loaded config."""
        config = load_config(config_file)
        manager = RunManager(results_dir=results_dir)
        run = manager.create_run(config, config_path=config_file)

        snapshot_file = Path(run.run_directory) / "config_snapshot.yaml"
        with open(snapshot_file) as f:
            snapshot = yaml.safe_load(f)

        assert snapshot["project"]["name"] == "integration_test_lab"
        assert set(snapshot["assets"]) == {"BTCUSDT", "ETHUSDT", "SOLUSDT"}

    def test_step_06_directory_structure_complete(self, config_file, results_dir):
        """Step 6: All required subdirectories must exist."""
        config = load_config(config_file)
        manager = RunManager(results_dir=results_dir)
        run = manager.create_run(config, config_path=config_file)

        run_dir = Path(run.run_directory)
        assert run_dir.is_dir()
        for subdir in ["logs", "trades", "charts", "reports", "summary"]:
            assert (run_dir / subdir).is_dir(), f"Missing: {subdir}/"

    def test_step_07_logging_initializes(self, config_file, results_dir):
        """Step 7: Logging must initialize and write to log file."""
        config = load_config(config_file)
        manager = RunManager(results_dir=results_dir)
        run = manager.create_run(config, config_path=config_file)

        log_dir = Path(run.run_directory) / "logs"
        logger = setup_logging(
            run_id=run.run_id,
            log_dir=log_dir,
            level=config.logging.level,
            format=config.logging.format,
        )
        logger.info("Integration test: logging step", step=7)

        log_file = log_dir / "research.log"
        assert log_file.exists()

    def test_step_08_run_loadable_after_creation(self, config_file, results_dir):
        """Step 8: Created run metadata must be loadable from disk."""
        config = load_config(config_file)
        manager = RunManager(results_dir=results_dir)
        run = manager.create_run(config, config_path=config_file)

        loaded = manager.load_run_metadata(run.run_id)
        assert loaded["run_id"] == run.run_id

    def test_step_09_git_commit_integrity(self, config_file, results_dir):
        """Step 9: Git commit must be 'unavailable' or a real 40-char hash. Never fabricated."""
        valid_hash = re.compile(r"^[0-9a-f]{40}$")
        config = load_config(config_file)
        manager = RunManager(results_dir=results_dir)
        run = manager.create_run(config, config_path=config_file)

        assert run.git_commit == "unavailable" or valid_hash.match(run.git_commit), (
            f"Git commit '{run.git_commit}' is fabricated (not a real hash or 'unavailable')"
        )

    def test_step_10_no_fake_market_data(self, config_file, results_dir):
        """
        Step 10: Confirm no fake market data was generated.

        Prompt 01 must not produce any trading results.
        The results directory should contain only metadata, no trade files.
        """
        config = load_config(config_file)
        manager = RunManager(results_dir=results_dir)
        run = manager.create_run(config, config_path=config_file)

        trades_dir = Path(run.run_directory) / "trades"
        # trades/ must exist but be empty in Prompt 01
        trade_files = list(trades_dir.iterdir())
        assert len(trade_files) == 0, (
            f"Prompt 01 must not produce trade files. Found: {trade_files}"
        )


class TestFailFastBehavior:
    """
    Tests that the system fails fast on invalid inputs.

    These tests verify that there are NO silent fallbacks anywhere in
    the Prompt 01 pipeline.
    """

    def test_invalid_config_stops_execution(self, tmp_path):
        """Invalid configuration must raise ConfigurationError, not silently continue."""
        bad_config = tmp_path / "bad.yaml"
        bad_config.write_text("project:\n  name: ok\n  # missing version\n")
        with pytest.raises(ConfigurationError):
            load_config(bad_config)

    def test_missing_config_file_stops_execution(self, tmp_path):
        """Missing config file must raise ConfigurationError immediately."""
        missing = tmp_path / "no_such_file.yaml"
        with pytest.raises(ConfigurationError, match="not found"):
            load_config(missing)

    def test_no_silent_exception_swallowing(self, tmp_path):
        """
        Verify that our ConfigurationError propagates correctly.
        The system must not catch and swallow the exception.
        """
        empty = tmp_path / "empty.yaml"
        empty.write_text("")
        raised = False
        try:
            load_config(empty)
        except ConfigurationError:
            raised = True
        assert raised, "ConfigurationError was swallowed — fail-fast violated"
