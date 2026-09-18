"""
Environment and Git utilities for reproducibility metadata.

Captures the complete execution environment at research run creation time.
This information is stored in run metadata and enables future reproduction.

Principles:
    - Git information is captured when available, explicitly marked "unavailable"
      when not. We NEVER fabricate commit hashes.
    - All dependency versions are captured verbatim from importlib.metadata.
    - Platform information is captured for cross-environment debugging.
"""

from __future__ import annotations

import platform
import subprocess
import sys
from importlib.metadata import PackageNotFoundError, version
from typing import Any


# Packages whose versions are always recorded
_CRITICAL_PACKAGES = [
    "pydantic",
    "pyyaml",
    "structlog",
    "rich",
    "numpy",       # may not be installed yet; will be noted as "not installed"
    "pandas",
    "pytest",
]


def get_git_commit() -> str:
    """
    Return the current Git commit hash.

    Attempts to run `git rev-parse HEAD`.

    Returns:
        The full 40-character commit hash, or the string "unavailable" if:
            - The working directory is not a Git repository.
            - The git command is not found.
            - The repository has no commits.
            - Any other error occurs.

    IMPORTANT: This function NEVER raises an exception.
    IMPORTANT: This function NEVER fabricates a commit hash.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            commit = result.stdout.strip()
            if commit:
                return commit
        return "unavailable"
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return "unavailable"


def get_git_branch() -> str:
    """
    Return the current Git branch name.

    Returns:
        The branch name, or "unavailable" if not in a Git repository.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            branch = result.stdout.strip()
            if branch:
                return branch
        return "unavailable"
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return "unavailable"


def get_python_version() -> str:
    """Return the full Python version string, e.g. '3.14.6 (main, ...)'."""
    return sys.version


def get_python_version_short() -> str:
    """Return a short Python version string, e.g. '3.14.6'."""
    info = sys.version_info
    return f"{info.major}.{info.minor}.{info.micro}"


def get_package_versions(packages: list[str] | None = None) -> dict[str, str]:
    """
    Return installed versions for the specified packages.

    Args:
        packages: List of package names to check. Defaults to _CRITICAL_PACKAGES.

    Returns:
        Dict of package_name → version_string.
        Packages that are not installed are recorded as "not installed".
    """
    if packages is None:
        packages = _CRITICAL_PACKAGES

    versions: dict[str, str] = {}
    for pkg in packages:
        try:
            versions[pkg] = version(pkg)
        except PackageNotFoundError:
            versions[pkg] = "not installed"

    return versions


def get_platform_info() -> dict[str, Any]:
    """
    Return a dict of platform/OS information for environment metadata.

    Returns:
        Dict with system, node, release, machine, processor, python fields.
    """
    return {
        "system": platform.system(),
        "node": platform.node(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python_implementation": platform.python_implementation(),
        "python_version": get_python_version_short(),
    }


def get_full_environment_info() -> dict[str, Any]:
    """
    Collect complete environment information for research run metadata.

    Returns:
        A dict suitable for inclusion in ResearchRun.environment_info.
    """
    return {
        "python_version": get_python_version(),
        "python_version_short": get_python_version_short(),
        "git_commit": get_git_commit(),
        "git_branch": get_git_branch(),
        "platform": get_platform_info(),
        "package_versions": get_package_versions(),
    }
