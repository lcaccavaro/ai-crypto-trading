"""
Configuration loader for the crypto research laboratory.

Responsibilities:
    - Read YAML configuration from disk.
    - Validate the configuration against the Pydantic schema.
    - Raise ConfigurationError with a clear message if anything is wrong.
    - Never fall back to default configuration silently.
    - Never generate configuration from code.

FAIL FAST: Any configuration problem raises ConfigurationError immediately.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from crypto_research.config.schema import ProjectConfiguration
from crypto_research.core.exceptions import ConfigurationError


def load_config(config_path: str | Path) -> ProjectConfiguration:
    """
    Load and validate the project configuration from a YAML file.

    This is the single entry point for all configuration loading.
    It performs a complete validation pass and fails fast on any error.

    Args:
        config_path: Absolute or relative path to the YAML configuration file.

    Returns:
        A fully validated ProjectConfiguration instance.

    Raises:
        ConfigurationError: If the file does not exist, cannot be parsed,
            or fails schema validation.
        ConfigurationError: If the file is empty or contains no data.

    Note:
        NO fallback configuration is generated.
        NO default values are silently applied for missing required fields.
        If this function returns, the configuration is fully valid.
    """
    path = Path(config_path).resolve()

    # --- File existence check ---
    if not path.exists():
        raise ConfigurationError(
            f"Required configuration file not found.\n"
            f"Path: {path}\n"
            f"Execution stopped. No fallback configuration was generated.\n"
            f"Create the file at the expected path and try again."
        )

    if not path.is_file():
        raise ConfigurationError(
            f"Configuration path exists but is not a file.\n"
            f"Path: {path}"
        )

    # --- YAML parsing ---
    raw: Any
    try:
        with open(path, encoding="utf-8") as fh:
            raw = yaml.safe_load(fh)
    except yaml.YAMLError as exc:
        raise ConfigurationError(
            f"Failed to parse YAML configuration.\n"
            f"Path: {path}\n"
            f"YAML error: {exc}"
        ) from exc

    if raw is None:
        raise ConfigurationError(
            f"Configuration file is empty.\n"
            f"Path: {path}\n"
            f"Execution stopped. Populate the configuration file and try again."
        )

    if not isinstance(raw, dict):
        raise ConfigurationError(
            f"Configuration file must contain a YAML mapping (dict) at the top level.\n"
            f"Path: {path}\n"
            f"Got type: {type(raw).__name__}"
        )

    # --- Schema validation ---
    try:
        config = ProjectConfiguration.model_validate(raw)
    except ValidationError as exc:
        errors = _format_validation_errors(exc)
        raise ConfigurationError(
            f"Configuration validation failed.\n"
            f"Path: {path}\n"
            f"Errors found:\n{errors}\n"
            f"Fix the errors above and try again."
        ) from exc

    return config


def _format_validation_errors(exc: ValidationError) -> str:
    """
    Format Pydantic validation errors into a human-readable string.

    Each error is presented as:
        [field.path]: error description
    """
    lines: list[str] = []
    for error in exc.errors():
        loc = " → ".join(str(part) for part in error["loc"])
        msg = error["msg"]
        lines.append(f"  [{loc}]: {msg}")
    return "\n".join(lines)


def config_to_dict(config: ProjectConfiguration) -> dict[str, Any]:
    """
    Serialize a validated configuration to a plain Python dict.

    This is used when saving config snapshots to research run metadata.
    The result is suitable for YAML or JSON serialization.

    Args:
        config: A validated ProjectConfiguration instance.

    Returns:
        A plain dict representation of the configuration.
    """
    return config.model_dump()


def find_project_root() -> Path:
    """
    Locate the project root by searching upward for pyproject.toml.

    Starts from the directory of this source file and walks up the
    directory tree.

    Returns:
        Path to the directory containing pyproject.toml.

    Raises:
        ConfigurationError: If pyproject.toml is not found.
    """
    current = Path(__file__).resolve()
    for parent in [current, *current.parents]:
        if (parent / "pyproject.toml").exists():
            return parent

    raise ConfigurationError(
        "Could not locate project root (pyproject.toml not found).\n"
        f"Searched from: {Path(__file__).resolve()}\n"
        "Ensure the project is installed in editable mode: pip install -e ."
    )


def get_default_config_path() -> Path:
    """
    Return the canonical path to the default configuration file.

    Returns:
        <project_root>/config/config.yaml

    Raises:
        ConfigurationError: If the project root cannot be located.
    """
    root = find_project_root()
    return root / "config" / "config.yaml"


def load_default_config() -> ProjectConfiguration:
    """
    Load configuration from the canonical default location.

    Convenience wrapper around load_config() for the common case.

    Returns:
        A fully validated ProjectConfiguration instance.

    Raises:
        ConfigurationError: If the default config cannot be found or is invalid.
    """
    config_path = get_default_config_path()
    return load_config(config_path)


def resolve_env_vars(data: dict) -> dict:
    """
    Resolve environment variable references in configuration values.

    Convention: String values starting with '$' are treated as environment
    variable names and replaced with their values.

    This is primarily useful for sensitive values (API keys, etc.) in
    future prompts. In Prompt 01, no sensitive values exist.

    Args:
        data: Raw configuration dict (before schema validation).

    Returns:
        Dict with environment variable references resolved.

    Raises:
        ConfigurationError: If a referenced environment variable is not set.
    """
    result: dict = {}
    for key, value in data.items():
        if isinstance(value, str) and value.startswith("$"):
            env_var = value[1:]
            env_value = os.environ.get(env_var)
            if env_value is None:
                raise ConfigurationError(
                    f"Configuration references environment variable '{env_var}' "
                    f"(key: '{key}') but it is not set.\n"
                    f"Set the environment variable and try again."
                )
            result[key] = env_value
        elif isinstance(value, dict):
            result[key] = resolve_env_vars(value)
        else:
            result[key] = value
    return result
