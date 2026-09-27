"""
Configuration schema using Pydantic v2.

All configuration fields are strongly typed and validated at load time.
Missing required fields raise ConfigurationError immediately — no fallbacks.

Design decisions:
    - Pydantic v2 `model_config = ConfigDict(extra="forbid")` prevents
      typos in the YAML from being silently ignored.
    - All Prompt 03 execution, cost, capital, risk, and position-sizing
      sections are now fully typed and validated.
    - The nullable placeholders from Prompt 01 (fee_rate, slippage_model)
      have been replaced with proper typed fields.
"""

from __future__ import annotations

from datetime import date
from typing import Literal, Optional

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


class BacktestConfig(BaseModel):
    """
    Backtest run configuration for Prompt 03.

    Defines which date range, symbols, and timeframes are used in a
    backtest run. Must be a subset of what has been ingested by Prompt 02.
    The engine will validate data availability before running.
    """

    model_config = ConfigDict(extra="forbid")

    start_date: str = Field(
        ...,
        description="Backtest start date (ISO format: YYYY-MM-DD)",
    )
    end_date: str = Field(
        ...,
        description="Backtest end date (ISO format: YYYY-MM-DD, exclusive)",
    )
    symbols: list[str] = Field(
        ...,
        min_length=1,
        description="List of asset symbols to backtest (e.g. ['BTCUSDT'])",
    )
    timeframes: list[str] = Field(
        ...,
        min_length=1,
        description="List of timeframes to use in this backtest run",
    )

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
    def validate_date_range(self) -> "BacktestConfig":
        start = date.fromisoformat(self.start_date)
        end = date.fromisoformat(self.end_date)
        if end <= start:
            raise ValueError(
                f"backtest.end_date ({self.end_date}) must be after "
                f"backtest.start_date ({self.start_date})"
            )
        return self

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
            raise ValueError("Duplicate timeframes found in backtest.timeframes.")
        return validated


class ExecutionConfig(BaseModel):
    """
    Execution simulation parameters for Prompt 03.

    All parameters are explicit configuration — no magic defaults embedded
    in the engine. Change these deliberately and document the reason.

    Signal timing semantics:
        allow_same_close_execution = false (default, required for integrity)
        → Signals from candle C execute at earliest at C+1 open.

    Intrabar ambiguity (both stop and target touched in same candle):
        stop_first      = conservative default
        target_first    = optimistic
        reject_ambiguous = record neither, skip candle

    Gap policy (price gaps past stop/target between candles):
        fill_at_open    = fill at candle open (realistic)
        fill_at_level   = fill at stop/target level (unrealistic)
    """

    model_config = ConfigDict(extra="forbid")

    order_model: Literal["market"] = Field(
        default="market",
        description="Order execution model. Only 'market' supported in Prompt 03.",
    )
    slippage_bps: float = Field(
        ...,
        ge=0,
        description="Slippage assumption in basis points (applied per side of trade)",
    )
    spread_bps: float = Field(
        ...,
        ge=0,
        description="Half-spread assumption in basis points",
    )
    intrabar_fill_policy: Literal["stop_first", "target_first", "reject_ambiguous"] = Field(
        default="stop_first",
        description=(
            "Policy when both stop and target are touched in the same candle. "
            "stop_first is conservative and the default."
        ),
    )
    gap_policy: Literal["fill_at_open", "fill_at_level"] = Field(
        default="fill_at_open",
        description=(
            "Policy when price gaps beyond stop/target. "
            "fill_at_open is realistic (cannot assume execution at gapped price)."
        ),
    )
    allow_same_close_execution: bool = Field(
        default=False,
        description=(
            "If true, a signal generated from candle C can execute at C's close. "
            "This introduces look-ahead bias and must remain false for valid research."
        ),
    )


class CostsConfig(BaseModel):
    """
    Trading cost assumptions for the backtest engine.

    These are EXPLICIT research parameters. They do NOT auto-update if
    Binance changes its fee schedule.

    Binance Futures reference fees (BTC/USDT, VIP 0):
        Maker: 0.0200% = 0.00020
        Taker: 0.0500% = 0.00050
    """

    model_config = ConfigDict(extra="forbid")

    maker_fee_rate: float = Field(
        ...,
        ge=0,
        le=0.01,
        description="Maker fee as a fraction (e.g. 0.0002 = 0.02%)",
    )
    taker_fee_rate: float = Field(
        ...,
        ge=0,
        le=0.01,
        description="Taker fee as a fraction (e.g. 0.0005 = 0.05%)",
    )


class CapitalConfig(BaseModel):
    """
    Portfolio capital configuration for the backtest engine.

    initial_balance: Starting capital in USDT (quote currency).
    risk_per_trade_pct: Percentage of equity at risk per trade.
        This is the maximum loss if a trade hits its stop-loss.
        Example: 1.0 means max 1% of equity lost if stop is hit.
    """

    model_config = ConfigDict(extra="forbid")

    initial_balance: float = Field(
        ...,
        gt=0,
        description="Starting capital in quote currency (USDT)",
    )
    risk_per_trade_pct: float = Field(
        ...,
        gt=0,
        le=10,
        description="Maximum percentage of equity at risk per trade (e.g. 1.0 = 1%)",
    )


class CooldownConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool = True
    value: int = 4
    unit: Literal["hours", "candles"] = "hours"


class StrategyManagementConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    consecutive_loss_limit: int = 3
    cooldown: CooldownConfig = Field(default_factory=CooldownConfig)
    break_even_resets_losses: bool = True


class ScoreComponentConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    weight: float = Field(ge=0, le=100)
    enabled: bool = True


class OpportunityScoreConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool = True
    minimum_score: float = 40.0
    version: str = "1.0.0"
    components: dict[str, ScoreComponentConfig]


class RiskConfig(BaseModel):
    """
    Risk management parameters for Prompt 03.

    Daily limits affect new position entry only:
        - When daily_profit_target_pct is reached: stop opening new positions.
          Existing positions continue under their configured management rules.
        - When daily_loss_limit_pct is exceeded: stop opening new positions.
          Existing positions continue under their configured management rules.

    Exposure limits:
        max_total_exposure_pct: sum(|notional|) / equity × 100
        max_asset_exposure_pct: |notional for symbol| / equity × 100
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
    max_total_exposure_pct: float = Field(
        ...,
        gt=0,
        le=500,
        description="Max sum(|notional|) / equity as percentage",
    )
    max_asset_exposure_pct: float = Field(
        ...,
        gt=0,
        le=500,
        description="Max |notional per symbol| / equity as percentage",
    )
    daily_profit_target_pct: float = Field(
        ...,
        gt=0,
        description=(
            "Stop opening new positions when daily PnL reaches this % of equity. "
            "This is a research parameter, NOT evidence that this target is achievable."
        ),
    )
    daily_loss_limit_pct: float = Field(
        ...,
        gt=0,
        le=100,
        description=(
            "Stop opening new positions when daily loss reaches this % of equity. "
            "Expressed as a positive number (e.g. 3.0 means stop at -3% daily)."
        ),
    )
    max_strategy_exposure_pct: float = Field(
        default=15.0,
        gt=0,
        le=500,
        description="Max |notional per strategy| / equity as percentage",
    )
    strategy_management: StrategyManagementConfig = Field(
        default_factory=StrategyManagementConfig
    )
    opportunity_score: OpportunityScoreConfig = Field(
        default_factory=lambda: OpportunityScoreConfig(
            enabled=False,
            minimum_score=40.0,
            version="1.0.0",
            components={},
        ),
        description="Opportunity scoring configuration. Disabled by default for backward compatibility.",
    )


class PositionSizingConfig(BaseModel):
    """
    Position sizing configuration for the backtest engine.

    mode: 'risk_based' (default) or 'fixed'
        risk_based: qty = (equity × risk_per_trade_pct/100) / |entry - stop|
        fixed: use fixed_quantity regardless of stop distance
               (for unit testing / validation only)

    fixed_quantity: only used when mode = 'fixed'. Must be set if mode is fixed.
    """

    model_config = ConfigDict(extra="forbid")

    mode: Literal["risk_based", "fixed"] = Field(
        default="risk_based",
        description="Position sizing mode: 'risk_based' or 'fixed'",
    )
    fixed_quantity: Optional[float] = Field(
        default=None,
        gt=0,
        description="Fixed quantity per trade. Required only when mode = 'fixed'.",
    )

    @model_validator(mode="after")
    def validate_fixed_quantity(self) -> "PositionSizingConfig":
        if self.mode == "fixed" and self.fixed_quantity is None:
            raise ValueError(
                "position_sizing.fixed_quantity must be set when mode = 'fixed'."
            )
        return self


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


class FormatsConfig(BaseModel):
    csv: bool = True
    json_format: bool = Field(default=True, alias="json")
    markdown: bool = True
    html: bool = True

    model_config = ConfigDict(populate_by_name=True)

class TradeChartConfig(BaseModel):
    enabled: bool = True
    bars_before_entry: int = Field(100, ge=10)
    bars_after_entry: int = Field(100, ge=10)
    show_indicators: bool = True
    show_entry: bool = True
    show_stop: bool = True
    show_target: bool = True
    show_exit: bool = True

class ReportingFiltersConfig(BaseModel):
    minimum_score: float | None = None
    strategies: list[str] = Field(default_factory=list)
    symbols: list[str] = Field(default_factory=list)
    timeframes: list[str] = Field(default_factory=list)

class ReportingConfig(BaseModel):
    """Configuration for Prompt 06 reporting."""
    enabled: bool = True
    formats: FormatsConfig = Field(default_factory=FormatsConfig)
    trade_diary: dict[str, bool] = Field(default_factory=lambda: {"enabled": True})
    trade_charts: TradeChartConfig = Field(default_factory=TradeChartConfig)
    aggregation: dict[str, str] = Field(default_factory=lambda: {"timezone": "UTC"})
    filters: ReportingFiltersConfig = Field(default_factory=ReportingFiltersConfig)
    html: dict[str, bool] = Field(default_factory=lambda: {"enabled": True})



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
    backtest: BacktestConfig
    execution: ExecutionConfig
    costs: CostsConfig
    capital: CapitalConfig
    risk: RiskConfig
    position_sizing: PositionSizingConfig
    logging: LoggingConfig
    reporting: ReportingConfig = Field(default_factory=ReportingConfig)

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
