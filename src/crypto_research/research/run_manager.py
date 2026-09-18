"""
Research Run Manager for the crypto research laboratory.

Responsibilities:
    - Generate unique, reproducible run identifiers.
    - Create the run output directory structure.
    - Capture and persist complete run metadata (environment, config, git).
    - Provide a central record for every research execution.

Run ID format:
    RUN_YYYYMMDD_HHMMSS_<6-char-hex>
    Example: RUN_20260915_000158_a3f9c2

    The datetime component ensures chronological ordering.
    The hex suffix ensures uniqueness when multiple runs start in the same second.

Run directory structure:
    results/
    └── RUN_20260915_000158_a3f9c2/
        ├── config_snapshot.yaml      ← exact config used for this run
        ├── metadata.json             ← full environment + run metadata
        ├── logs/                     ← structured log files
        ├── trades/                   ← trade records (Prompt 03+)
        ├── charts/                   ← visual outputs (Prompt 06+)
        ├── reports/                  ← research reports (Prompt 06+)
        └── summary/                  ← summary metrics (Prompt 06+)

FAIL FAST: Any failure during run creation raises ResearchRunError.
"""

from __future__ import annotations

import json
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from crypto_research.config.loader import config_to_dict, find_project_root
from crypto_research.config.schema import ProjectConfiguration
from crypto_research.core.domain import ResearchRun
from crypto_research.core.exceptions import ResearchRunError
from crypto_research.utils.environment import get_full_environment_info

# Subdirectories created inside every run directory
_RUN_SUBDIRS = ["logs", "trades", "charts", "reports", "summary"]


class RunManager:
    """
    Manages the lifecycle of a research run.

    Creates run directories, generates unique IDs, captures metadata,
    and provides the ResearchRun domain object.

    Usage:
        manager = RunManager()
        run = manager.create_run(config)
        # run.run_id, run.run_directory, run.metadata.json are now available
    """

    def __init__(self, results_dir: Path | None = None) -> None:
        """
        Initialize the RunManager.

        Args:
            results_dir: Directory under which all run directories are created.
                         Defaults to <project_root>/results/.
        """
        if results_dir is not None:
            self._results_dir = Path(results_dir).resolve()
        else:
            project_root = find_project_root()
            self._results_dir = project_root / "results"

    def generate_run_id(self) -> str:
        """
        Generate a unique, chronologically-sortable run identifier.

        Format: RUN_YYYYMMDD_HHMMSS_<6-char-hex>

        The timestamp component is always UTC.
        The hex suffix (3 random bytes = 6 hex chars) prevents collisions.

        Returns:
            A string run ID, e.g. "RUN_20260915_000158_a3f9c2"
        """
        now = datetime.now(tz=timezone.utc)
        timestamp_part = now.strftime("%Y%m%d_%H%M%S")
        hex_suffix = secrets.token_hex(3)  # 3 bytes = 6 hex characters
        return f"RUN_{timestamp_part}_{hex_suffix}"

    def create_run(
        self,
        config: ProjectConfiguration,
        config_path: str | Path | None = None,
    ) -> ResearchRun:
        """
        Create a new research run with full metadata.

        This method:
            1. Generates a unique run_id.
            2. Creates the run directory and all subdirectories.
            3. Captures full environment metadata (Python, packages, git, OS).
            4. Saves config_snapshot.yaml to the run directory.
            5. Saves metadata.json to the run directory.
            6. Returns a ResearchRun domain object.

        Args:
            config:       The validated project configuration for this run.
            config_path:  Path to the config file (for metadata only).
                          If None, attempts to find the default config path.

        Returns:
            A ResearchRun with all metadata populated.

        Raises:
            ResearchRunError: If the run directory cannot be created.
            ResearchRunError: If metadata cannot be serialized or written.
        """
        run_id = self.generate_run_id()
        created_at = datetime.now(tz=timezone.utc)

        # --- Determine config path ---
        if config_path is None:
            try:
                from crypto_research.config.loader import get_default_config_path
                config_path = str(get_default_config_path())
            except Exception:
                config_path = "unknown"
        else:
            config_path = str(Path(config_path).resolve())

        # --- Create run directory ---
        run_dir = self._results_dir / run_id
        try:
            run_dir.mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            raise ResearchRunError(
                f"Run directory already exists (run ID collision?).\n"
                f"Path: {run_dir}\n"
                f"This should not happen with the current ID generation scheme."
            ) from None
        except OSError as exc:
            raise ResearchRunError(
                f"Failed to create run directory.\n"
                f"Path: {run_dir}\n"
                f"Error: {exc}"
            ) from exc

        # --- Create subdirectories ---
        for subdir in _RUN_SUBDIRS:
            try:
                (run_dir / subdir).mkdir()
            except OSError as exc:
                raise ResearchRunError(
                    f"Failed to create run subdirectory '{subdir}'.\n"
                    f"Run directory: {run_dir}\n"
                    f"Error: {exc}"
                ) from exc

        # --- Capture environment ---
        env_info = get_full_environment_info()

        # --- Build ResearchRun ---
        config_snapshot = config_to_dict(config)
        run = ResearchRun(
            run_id=run_id,
            created_at=created_at,
            python_version=env_info["python_version"],
            package_versions=env_info["package_versions"],
            git_commit=env_info["git_commit"],
            config_path=config_path,
            config_snapshot=config_snapshot,
            assets=list(config.assets),
            timeframes=list(config.timeframes),
            run_directory=str(run_dir),
            environment_info=env_info,
        )

        # --- Save config snapshot ---
        self._save_config_snapshot(run_dir, config_snapshot)

        # --- Save metadata ---
        self._save_metadata(run_dir, run)

        return run

    def _save_config_snapshot(
        self, run_dir: Path, config_snapshot: dict[str, Any]
    ) -> None:
        """Write config_snapshot.yaml to the run directory."""
        snapshot_path = run_dir / "config_snapshot.yaml"
        try:
            with open(snapshot_path, "w", encoding="utf-8") as fh:
                yaml.dump(
                    config_snapshot,
                    fh,
                    default_flow_style=False,
                    allow_unicode=True,
                    sort_keys=True,
                )
        except (OSError, yaml.YAMLError) as exc:
            raise ResearchRunError(
                f"Failed to write config snapshot.\n"
                f"Path: {snapshot_path}\n"
                f"Error: {exc}"
            ) from exc

    def _save_metadata(self, run_dir: Path, run: ResearchRun) -> None:
        """Write metadata.json to the run directory."""
        metadata_path = run_dir / "metadata.json"
        metadata = _run_to_dict(run)
        try:
            with open(metadata_path, "w", encoding="utf-8") as fh:
                json.dump(metadata, fh, indent=2, default=str)
        except (OSError, TypeError) as exc:
            raise ResearchRunError(
                f"Failed to write run metadata.\n"
                f"Path: {metadata_path}\n"
                f"Error: {exc}"
            ) from exc

    def load_run_metadata(self, run_id: str) -> dict[str, Any]:
        """
        Load previously saved run metadata from disk.

        Args:
            run_id: The run ID to load.

        Returns:
            The metadata dict as written in metadata.json.

        Raises:
            ResearchRunError: If the run directory or metadata file is missing.
        """
        run_dir = self._results_dir / run_id
        metadata_path = run_dir / "metadata.json"

        if not run_dir.exists():
            raise ResearchRunError(
                f"Run directory not found.\n"
                f"Run ID: {run_id}\n"
                f"Expected path: {run_dir}"
            )

        if not metadata_path.exists():
            raise ResearchRunError(
                f"Run metadata file not found.\n"
                f"Run ID: {run_id}\n"
                f"Expected path: {metadata_path}"
            )

        try:
            with open(metadata_path, encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, json.JSONDecodeError) as exc:
            raise ResearchRunError(
                f"Failed to read run metadata.\n"
                f"Path: {metadata_path}\n"
                f"Error: {exc}"
            ) from exc

    def list_runs(self) -> list[str]:
        """
        Return a sorted list of existing run IDs.

        Returns:
            List of run ID strings, sorted chronologically (ascending).
            Returns an empty list if the results directory has no runs.
        """
        if not self._results_dir.exists():
            return []

        runs = [
            d.name
            for d in self._results_dir.iterdir()
            if d.is_dir() and d.name.startswith("RUN_")
        ]
        return sorted(runs)


def _run_to_dict(run: ResearchRun) -> dict[str, Any]:
    """Convert a ResearchRun to a JSON-serializable dict."""
    return {
        "run_id": run.run_id,
        "created_at": run.created_at.isoformat(),
        "python_version": run.python_version,
        "package_versions": run.package_versions,
        "git_commit": run.git_commit,
        "config_path": run.config_path,
        "config_snapshot": run.config_snapshot,
        "assets": run.assets,
        "timeframes": run.timeframes,
        "run_directory": run.run_directory,
        "environment_info": run.environment_info,
    }
