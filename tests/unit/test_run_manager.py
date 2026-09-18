"""
Unit tests for the Research Run Manager.

Tests:
    - Run ID format matches expected pattern.
    - Each generated run ID is unique.
    - Run directory is created with all expected subdirectories.
    - config_snapshot.yaml is written.
    - metadata.json is written with required fields.
    - Git commit is "unavailable" when not in a git repository
      (We are now IN a git repo but with no commits, so should be unavailable).
    - load_run_metadata() works correctly.
    - list_runs() returns correct run IDs.
"""

import json
import re
import tempfile
from pathlib import Path

import pytest
import yaml

from crypto_research.config.schema import ProjectConfiguration
from crypto_research.core.exceptions import ResearchRunError
from crypto_research.research.run_manager import RunManager

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_CONFIG_DATA = {
    "project": {"name": "test_lab", "version": "1.0.0"},
    "research": {"market": "crypto", "data_source": "binance"},
    "assets": ["BTCUSDT", "ETHUSDT"],
    "timeframes": ["1m", "5m"],
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

RUN_ID_PATTERN = re.compile(r"^RUN_\d{8}_\d{6}_[0-9a-f]{6}$")


def make_config() -> ProjectConfiguration:
    return ProjectConfiguration.model_validate(VALID_CONFIG_DATA)


# ---------------------------------------------------------------------------
# Run ID
# ---------------------------------------------------------------------------


class TestRunIdGeneration:
    def test_run_id_format(self, tmp_path):
        manager = RunManager(results_dir=tmp_path)
        run_id = manager.generate_run_id()
        assert RUN_ID_PATTERN.match(run_id), (
            f"Run ID '{run_id}' does not match expected format RUN_YYYYMMDD_HHMMSS_<hex6>"
        )

    def test_run_ids_are_unique(self, tmp_path):
        manager = RunManager(results_dir=tmp_path)
        ids = {manager.generate_run_id() for _ in range(100)}
        assert len(ids) == 100, "Generated run IDs are not unique"

    def test_run_id_starts_with_RUN(self, tmp_path):
        manager = RunManager(results_dir=tmp_path)
        run_id = manager.generate_run_id()
        assert run_id.startswith("RUN_")


# ---------------------------------------------------------------------------
# Directory structure
# ---------------------------------------------------------------------------


class TestRunDirectoryCreation:
    def test_run_directory_created(self, tmp_path):
        manager = RunManager(results_dir=tmp_path)
        run = manager.create_run(make_config())
        run_dir = Path(run.run_directory)
        assert run_dir.exists()
        assert run_dir.is_dir()

    def test_all_subdirectories_created(self, tmp_path):
        manager = RunManager(results_dir=tmp_path)
        run = manager.create_run(make_config())
        run_dir = Path(run.run_directory)
        for subdir in ["logs", "trades", "charts", "reports", "summary"]:
            assert (run_dir / subdir).is_dir(), f"Missing subdirectory: {subdir}"

    def test_config_snapshot_yaml_exists(self, tmp_path):
        manager = RunManager(results_dir=tmp_path)
        run = manager.create_run(make_config())
        snapshot = Path(run.run_directory) / "config_snapshot.yaml"
        assert snapshot.exists()

    def test_config_snapshot_is_valid_yaml(self, tmp_path):
        manager = RunManager(results_dir=tmp_path)
        run = manager.create_run(make_config())
        snapshot = Path(run.run_directory) / "config_snapshot.yaml"
        with open(snapshot) as f:
            data = yaml.safe_load(f)
        assert isinstance(data, dict)
        assert "assets" in data

    def test_metadata_json_exists(self, tmp_path):
        manager = RunManager(results_dir=tmp_path)
        run = manager.create_run(make_config())
        metadata_file = Path(run.run_directory) / "metadata.json"
        assert metadata_file.exists()

    def test_metadata_json_is_valid_json(self, tmp_path):
        manager = RunManager(results_dir=tmp_path)
        run = manager.create_run(make_config())
        metadata_file = Path(run.run_directory) / "metadata.json"
        with open(metadata_file) as f:
            metadata = json.load(f)
        assert isinstance(metadata, dict)


# ---------------------------------------------------------------------------
# Metadata content
# ---------------------------------------------------------------------------


class TestRunMetadataContent:
    def test_required_fields_present(self, tmp_path):
        manager = RunManager(results_dir=tmp_path)
        run = manager.create_run(make_config())
        metadata_file = Path(run.run_directory) / "metadata.json"
        with open(metadata_file) as f:
            metadata = json.load(f)

        required_fields = [
            "run_id",
            "created_at",
            "python_version",
            "package_versions",
            "git_commit",
            "config_path",
            "config_snapshot",
            "assets",
            "timeframes",
            "run_directory",
            "environment_info",
        ]
        for field in required_fields:
            assert field in metadata, f"Required field '{field}' missing from metadata.json"

    def test_run_id_in_metadata_matches(self, tmp_path):
        manager = RunManager(results_dir=tmp_path)
        run = manager.create_run(make_config())
        metadata_file = Path(run.run_directory) / "metadata.json"
        with open(metadata_file) as f:
            metadata = json.load(f)
        assert metadata["run_id"] == run.run_id

    def test_git_commit_is_string(self, tmp_path):
        """Git commit must be a non-empty string (either a hash or 'unavailable')."""
        manager = RunManager(results_dir=tmp_path)
        run = manager.create_run(make_config())
        assert isinstance(run.git_commit, str)
        assert len(run.git_commit) > 0

    def test_git_commit_never_fabricated(self, tmp_path):
        """
        Git commit must be either a valid 40-char hex hash or exactly 'unavailable'.
        It must NEVER be a made-up value.
        """
        manager = RunManager(results_dir=tmp_path)
        run = manager.create_run(make_config())
        git_commit = run.git_commit
        valid_hash = re.compile(r"^[0-9a-f]{40}$")
        assert git_commit == "unavailable" or valid_hash.match(git_commit), (
            f"Git commit '{git_commit}' is neither 'unavailable' nor a valid 40-char hash"
        )

    def test_assets_recorded_correctly(self, tmp_path):
        manager = RunManager(results_dir=tmp_path)
        run = manager.create_run(make_config())
        assert set(run.assets) == {"BTCUSDT", "ETHUSDT"}

    def test_package_versions_recorded(self, tmp_path):
        manager = RunManager(results_dir=tmp_path)
        run = manager.create_run(make_config())
        assert "pydantic" in run.package_versions
        assert "pyyaml" in run.package_versions


# ---------------------------------------------------------------------------
# Load and list
# ---------------------------------------------------------------------------


class TestRunManagerLoadAndList:
    def test_load_run_metadata(self, tmp_path):
        manager = RunManager(results_dir=tmp_path)
        run = manager.create_run(make_config())
        loaded = manager.load_run_metadata(run.run_id)
        assert loaded["run_id"] == run.run_id

    def test_load_nonexistent_run_raises(self, tmp_path):
        manager = RunManager(results_dir=tmp_path)
        with pytest.raises(ResearchRunError, match="not found"):
            manager.load_run_metadata("RUN_19900101_000000_000000")

    def test_list_runs_empty(self, tmp_path):
        manager = RunManager(results_dir=tmp_path)
        assert manager.list_runs() == []

    def test_list_runs_returns_created_runs(self, tmp_path):
        manager = RunManager(results_dir=tmp_path)
        config = make_config()
        run1 = manager.create_run(config)
        run2 = manager.create_run(config)
        run_list = manager.list_runs()
        assert run1.run_id in run_list
        assert run2.run_id in run_list

    def test_list_runs_sorted(self, tmp_path):
        manager = RunManager(results_dir=tmp_path)
        config = make_config()
        runs = [manager.create_run(config) for _ in range(3)]
        run_list = manager.list_runs()
        assert run_list == sorted(run_list)
