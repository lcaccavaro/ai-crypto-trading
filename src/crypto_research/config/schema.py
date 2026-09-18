"""
Configuration schema using Pydantic v2.

All configuration fields are strongly typed and validated at load time.
Missing required fields raise ConfigurationError immediately — no fallbacks.

Design decisions:
    - Pydantic v2 `model_config = ConfigDict(extra="forbid")` prevents
      typos in the YAML from being silently ignored.
    - Fields that will be used in future prompts are included here with
      appropriate Optional types so the YAML can carry them.
    - No default values are provided for critical research parameters
      (assets, timeframes) to force explicit configuration.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from crypto_research.core.domain import Timeframe

_VALID_MARKET_TYPES = {"futures", "spot"}


class ProjectConfig(BaseModel):
    """Top-level project identification."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., description="Project name (no spaces recommended)")
    version: str = Field(..., description="Project version string")


class ResearchConfig(BaseModel):
    """Research domain configuration."""

    model_config = ConfigDict(extra="forbid")

    market: str = Field(..., description="Market type, e.g. 'crypto'")
    data_source: str = Field(..., description="Primary data source, e.g. 'binance'")


class DataConfig(BaseModel):
    """
    Data ingestion configuration for Prompt 02.

    Controls which market type is used, the historical date range,
    storage directories, and API behavior.

    NOTE on date range:
        start_date / end_date define the FULL research period you eventually
        want to build. For the initial validation notebook a shorter demo
        period is used (see notebooks/02_binance_data_ingestion.ipynb).
        When you are ready to download the full historical dataset,
        set start_date and end_date in config.yaml and re-run the pipeline.
    """

    model_config = ConfigDict(extra="forbid")

    market_type: str = Field(
        ...,
        description="Exchange market type: 'futures' or 'spot'",
    )
    start_date: str = Field(
        ...,
        description="Start date for full historical download (ISO format: YYYY-MM-DD)",
    )
    end_date: str = Field(
        ...,
        description="End date for full historical download (ISO format: YYYY-MM-DD)",
    )
    raw_dir: str = Field(
        default="data/raw",
        description="Directory for raw downloaded data",
    )
    processed_dir: str = Field(
        default="data/processed",
        description="Directory for canonical Parquet datasets",
    )
    metadata_dir: str = Field(
        default="data/metadata",
        description="Directory for dataset metadata and manifests",
    )
    request_delay_ms: int = Field(
        default=250,
        ge=0,
        description="Milliseconds to wait between API requests (rate-limit safety)",
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum retry attempts for transient API failures",
    )
    retry_delay_s: int = Field(
        default=5,
        ge=1,
        description="Seconds to wait between retries",
    )
    schema_version: str = Field(
        default="1.0",
        description="Dataset schema version (increment when canonical schema changes)",
    )

    @field_validator("market_type")
    @classmethod
    def validate_market_type(cls, v: str) -> str:
        if v not in _VALID_MARKET_TYPES:
            raise ValueError(
                f"Invalid market_type '{v}'. Must be one of {_VALID_MARKET_TYPES}"
            )
        return v

    @field_validator("start_date", "end_date")
    @classmethod
    def validate_date_format(cls, v: str) -> str:
        try:
            date.fromisoformat(v)
        except ValueError:
            raise ValueError(
                f"Invalid date '{v}'. Must be ISO format YYYY-MM-DD."
            ) from None
        return v

    @model_validator(mode="after")
    def validate_date_range(self) -> "DataConfig":
        start = date.fromisoformat(self.start_date)
        end = date.fromisoformat(self.end_date)
        if end <= start:
            raise ValueError(
                f"end_date ({self.end_date}) must be after start_date ({self.start_date})"
            )
        return self


class RiskConfig(BaseModel):
    """
    Risk management parameters.

    Note: These are configuration placeholders for future prompts.
    The actual risk logic will be implemented in Prompt 05.
    """

    model_config = ConfigDict(extra="forbid")

    risk_reward_ratio: float = Field(
        ...,
        gt=0,
        description="Target reward-to-risk ratio (e.g. 3.0 means 1R risk for 3R reward)",
    )
    risk_per_trade_pct: float = Field(
        ...,
        gt=0,
        le=100,
        description="Maximum percentage of capital to risk per trade",
    )
    max_concurrent_positions: int = Field(
        ...,
        gt=0,
        description="Maximum number of simultaneously open positions",
    )
    max_daily_loss_pct: float = Field(
        ...,
        gt=0,
        le=100,
        description="Daily loss limit as percentage of capital",
    )
    daily_profit_target_pct: Optional[float] = Field(
        None,
        gt=0,
        description="Optional daily profit target (stop opening new positions when reached)",
    )


class ExecutionConfig(BaseModel):
    """
    Execution simulation parameters.

    Note: fee_rate and slippage_model are null in Prompt 01.
    They will be populated and enforced in Prompt 03.
    """

    model_config = ConfigDict(extra="forbid")

    fee_rate: Optional[float] = Field(
        None,
        ge=0,
        description="Fee rate as a fraction (e.g. 0.001 = 0.1%). Null until Prompt 03.",
    )
    slippage_model: Optional[str] = Field(
        None,
        description="Slippage model identifier. Null until Prompt 03.",
    )


class LoggingConfig(BaseModel):
    """Logging configuration."""

    model_config = ConfigDict(extra="forbid")

    level: str = Field(
        ...,
        description="Log level: DEBUG, INFO, WARNING, ERROR",
    )
    format: str = Field(
        ...,
        description="Log format: 'structured' (JSON) or 'console' (human-readable)",
    )

    @field_validator("level")
    @classmethod
    def validate_level(cls, v: str) -> str:
        valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in valid:
            raise ValueError(f"Invalid log level '{v}'. Must be one of {valid}")
        return upper

    @field_validator("format")
    @classmethod
    def validate_format(cls, v: str) -> str:
        valid = {"structured", "console"}
        lower = v.lower()
        if lower not in valid:
            raise ValueError(f"Invalid log format '{v}'. Must be one of {valid}")
        return lower


class ProjectConfiguration(BaseModel):
    """
    Root configuration model for the entire research system.

    This is the single source of truth for all research parameters.
    Every field is validated at startup. Invalid configuration stops execution.

    Usage:
        config = load_config("config/config.yaml")
        # config is a fully validated ProjectConfiguration instance
    """

    model_config = ConfigDict(extra="forbid")

    project: ProjectConfig
    research: ResearchConfig
    assets: list[str] = Field(
        ...,
        min_length=1,
        description="List of asset symbols to include in research (e.g. BTCUSDT)",
    )
    timeframes: list[str] = Field(
        ...,
        min_length=1,
        description="List of timeframes to include in research",
    )
    data: DataConfig
    risk: RiskConfig
    execution: ExecutionConfig
    logging: LoggingConfig

    @field_validator("assets")
    @classmethod
    def validate_assets(cls, assets: list[str]) -> list[str]:
        """Ensure asset list contains no duplicates and no empty strings."""
        for asset in assets:
            if not asset or not asset.strip():
                raise ValueError("Asset symbols must not be empty strings.")
        if len(assets) != len(set(assets)):
            seen = set()
            duplicates = [a for a in assets if a in seen or seen.add(a)]  # type: ignore[func-returns-value]
            raise ValueError(f"Duplicate assets found in configuration: {duplicates}")
        return assets

    @field_validator("timeframes")
    @classmethod
    def validate_timeframes(cls, timeframes: list[str]) -> list[str]:
        """Ensure all timeframes are valid and deduplicated."""
        validated: list[str] = []
        for tf in timeframes:
            try:
                parsed = Timeframe.from_string(tf)
                validated.append(parsed.value)
            except ValueError as exc:
                raise ValueError(str(exc)) from exc
        if len(validated) != len(set(validated)):
            raise ValueError("Duplicate timeframes found in configuration.")
        return validated
