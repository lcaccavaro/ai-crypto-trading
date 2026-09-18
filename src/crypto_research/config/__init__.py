"""Configuration package — schema and loader."""
from crypto_research.config.loader import (
    config_to_dict,
    find_project_root,
    get_default_config_path,
    load_config,
    load_default_config,
)
from crypto_research.config.schema import (
    ExecutionConfig,
    LoggingConfig,
    ProjectConfig,
    ProjectConfiguration,
    ResearchConfig,
    RiskConfig,
)

__all__ = [
    # Loader
    "config_to_dict",
    "find_project_root",
    "get_default_config_path",
    "load_config",
    "load_default_config",
    # Schema
    "ExecutionConfig",
    "LoggingConfig",
    "ProjectConfig",
    "ProjectConfiguration",
    "ResearchConfig",
    "RiskConfig",
]
