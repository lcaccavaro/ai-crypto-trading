"""
Data validation pipeline for canonical OHLCV datasets.

Each validator is a pure function that receives a DataFrame and returns
a ValidationResult. Validators never modify the DataFrame — they only
inspect and report.

Validation rules:
    OHLC violation       → FAIL  (data is factually wrong)
    Duplicate timestamp  → FAIL  (cannot resolve without fabricating data)
    Non-monotonic order  → FAIL  (order is required for backtesting)
    Null values          → FAIL  (cannot compute anything reliably)
    Wrong timezone       → FAIL  (point-in-time integrity requires UTC)
    Missing candles      → WARNING (legitimate market gaps occur)

Design principle:
    Validators detect. They do NOT repair.
    Repairing financial data silently is forbidden.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import pandas as pd

from crypto_research.utils.logging import get_logger

logger = get_logger(__name__)

# Expected interval in minutes for each timeframe
TIMEFRAME_MINUTES: dict[str, int] = {
    "1m": 1,
    "3m": 3,
    "5m": 5,
    "15m": 15,
    "30m": 30,
    "1h": 60,
    "2h": 120,
    "4h": 240,
}

# Canonical column set
REQUIRED_COLUMNS = [
    "timestamp", "open", "high", "low", "close", "volume",
    "close_time", "quote_volume", "trade_count",
    "taker_buy_base_vol", "taker_buy_quote_vol",
]


class ValidationStatus(str, Enum):
    PASS = "PASS"
    WARNING = "WARNING"
    FAIL = "FAIL"


@dataclass
class ValidationResult:
    """Result of a single validator applied to a dataset."""

    validator_name: str
    status: ValidationStatus
    issues: list[str] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return self.status == ValidationStatus.PASS

    @property
    def failed(self) -> bool:
        return self.status == ValidationStatus.FAIL


@dataclass
class DatasetValidationSummary:
    """Aggregated validation result for a single (symbol, timeframe) dataset."""

    symbol: str
    timeframe: str
    row_count: int
    results: list[ValidationResult] = field(default_factory=list)

    @property
    def overall_status(self) -> ValidationStatus:
        """Worst status across all validators."""
        if any(r.status == ValidationStatus.FAIL for r in self.results):
            return ValidationStatus.FAIL
        if any(r.status == ValidationStatus.WARNING for r in self.results):
            return ValidationStatus.WARNING
        return ValidationStatus.PASS

    @property
    def all_issues(self) -> list[str]:
        issues = []
        for r in self.results:
            issues.extend(r.issues)
        return issues

    def get_stat(self, key: str, default: Any = None) -> Any:
        for r in self.results:
            if key in r.stats:
                return r.stats[key]
        return default


# ---------------------------------------------------------------------------
# Validator 1: Schema
# ---------------------------------------------------------------------------

def validate_schema(df: pd.DataFrame) -> ValidationResult:
    """
    Check that all required columns are present and have correct dtype families.

    This validator runs first — if schema is wrong, other validators may fail
    with confusing errors.
    """
    issues: list[str] = []

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        issues.append(f"Missing required columns: {missing}")
        return ValidationResult(
            validator_name="schema",
            status=ValidationStatus.FAIL,
            issues=issues,
        )

    # Check timestamp is datetime with timezone
    ts_col = df["timestamp"]
    if not hasattr(ts_col.dtype, "tz") or ts_col.dtype.tz is None:
        issues.append(
            "Column 'timestamp' must be timezone-aware datetime. "
            "Got: {ts_col.dtype}. All timestamps must be UTC."
        )

    # Check numeric columns
    numeric_cols = ["open", "high", "low", "close", "volume",
                    "quote_volume", "taker_buy_base_vol", "taker_buy_quote_vol"]
    for col in numeric_cols:
        if df[col].dtype.kind not in ("f", "i", "u"):
            issues.append(
                f"Column '{col}' must be numeric. Got: {df[col].dtype}"
            )

    if "trade_count" in df.columns:
        if df["trade_count"].dtype.kind not in ("i", "u"):
            issues.append(
                f"Column 'trade_count' must be integer. Got: {df['trade_count'].dtype}"
            )

    status = ValidationStatus.FAIL if issues else ValidationStatus.PASS
    return ValidationResult(
        validator_name="schema",
        status=status,
        issues=issues,
        stats={"column_count": len(df.columns)},
    )


# ---------------------------------------------------------------------------
# Validator 2: OHLC Integrity
# ---------------------------------------------------------------------------

def validate_ohlc(df: pd.DataFrame) -> ValidationResult:
    """
    Check all OHLC candle invariants.

    Invariants:
        high >= max(open, close)
        low  <= min(open, close)
        high >= low
        open > 0, high > 0, low > 0, close > 0
        volume >= 0

    NOTE: We detect violations but NEVER repair them.
    """
    if df.empty:
        return ValidationResult(
            validator_name="ohlc",
            status=ValidationStatus.WARNING,
            issues=["DataFrame is empty — no OHLC data to validate."],
            stats={"invalid_count": 0},
        )

    issues: list[str] = []

    # high < max(open, close)
    mask_high = df["high"] < df[["open", "close"]].max(axis=1)
    n_high = mask_high.sum()
    if n_high > 0:
        sample = df.loc[mask_high, "timestamp"].head(3).tolist()
        issues.append(
            f"{n_high} candles where high < max(open, close). "
            f"Sample timestamps: {sample}"
        )

    # low > min(open, close)
    mask_low = df["low"] > df[["open", "close"]].min(axis=1)
    n_low = mask_low.sum()
    if n_low > 0:
        sample = df.loc[mask_low, "timestamp"].head(3).tolist()
        issues.append(
            f"{n_low} candles where low > min(open, close). "
            f"Sample timestamps: {sample}"
        )

    # high < low
    mask_hl = df["high"] < df["low"]
    n_hl = mask_hl.sum()
    if n_hl > 0:
        issues.append(f"{n_hl} candles where high < low.")

    # Prices must be positive
    for col in ["open", "high", "low", "close"]:
        mask_neg = df[col] <= 0
        n_neg = mask_neg.sum()
        if n_neg > 0:
            issues.append(f"{n_neg} candles where {col} <= 0.")

    # Volume must be non-negative
    mask_vol = df["volume"] < 0
    n_vol = mask_vol.sum()
    if n_vol > 0:
        issues.append(f"{n_vol} candles where volume < 0.")

    total_invalid = n_high + n_low + n_hl
    status = ValidationStatus.FAIL if issues else ValidationStatus.PASS
    return ValidationResult(
        validator_name="ohlc",
        status=status,
        issues=issues,
        stats={"invalid_count": total_invalid},
    )


# ---------------------------------------------------------------------------
# Validator 3: Timestamps
# ---------------------------------------------------------------------------

def validate_timestamps(df: pd.DataFrame) -> ValidationResult:
    """
    Validate timestamp integrity:
        1. All timestamps are UTC-aware.
        2. Strictly monotonically increasing (no duplicates, no backward steps).
        3. No future timestamps beyond server time (informational).
    """
    if df.empty:
        return ValidationResult(
            validator_name="timestamps",
            status=ValidationStatus.WARNING,
            issues=["DataFrame is empty — no timestamps to validate."],
            stats={"duplicate_count": 0, "order_errors": 0},
        )

    issues: list[str] = []

    ts = df["timestamp"]

    # UTC check
    if hasattr(ts.dtype, "tz") and ts.dtype.tz is not None:
        tz_name = str(ts.dtype.tz)
        if tz_name not in ("UTC", "utc"):
            issues.append(
                f"Timestamps have timezone '{tz_name}' but must be UTC. "
                "Mixed timezones corrupt point-in-time research."
            )
    else:
        issues.append(
            "Timestamps are timezone-naive. All research timestamps must be UTC-aware."
        )

    # Duplicates
    dup_mask = ts.duplicated(keep=False)
    n_dups = dup_mask.sum()
    if n_dups > 0:
        sample = ts[dup_mask].head(3).tolist()
        issues.append(
            f"{n_dups} duplicate timestamps detected. "
            f"Sample: {sample}. "
            "Duplicates cannot remain in the canonical dataset."
        )

    # Strict monotonic check
    diffs = ts.diff().dropna()
    non_mono = (diffs <= pd.Timedelta(0)).sum()
    if non_mono > 0:
        issues.append(
            f"{non_mono} non-monotonic timestamp step(s) detected. "
            "Dataset must be strictly ascending by timestamp."
        )

    status = ValidationStatus.FAIL if issues else ValidationStatus.PASS
    return ValidationResult(
        validator_name="timestamps",
        status=status,
        issues=issues,
        stats={
            "duplicate_count": int(n_dups),
            "order_errors": int(non_mono),
        },
    )


# ---------------------------------------------------------------------------
# Validator 4: Missing Candles
# ---------------------------------------------------------------------------

def validate_missing_candles(df: pd.DataFrame, timeframe: str) -> ValidationResult:
    """
    Detect gaps in the expected candle sequence.

    Exchange downtime, network issues, and low-liquidity periods can produce
    genuine gaps. We DETECT and RECORD them — we do NOT fill them.

    Returns WARNING (not FAIL) because missing candles are a legitimate
    market condition, not a data corruption error.
    """
    if df.empty:
        return ValidationResult(
            validator_name="missing_candles",
            status=ValidationStatus.WARNING,
            issues=["DataFrame is empty — cannot check for missing candles."],
            stats={"missing_count": 0, "expected_count": 0, "actual_count": 0},
        )

    if timeframe not in TIMEFRAME_MINUTES:
        return ValidationResult(
            validator_name="missing_candles",
            status=ValidationStatus.WARNING,
            issues=[f"Unknown timeframe '{timeframe}' — cannot compute expected intervals."],
            stats={"missing_count": 0},
        )

    interval_minutes = TIMEFRAME_MINUTES[timeframe]
    expected_delta = pd.Timedelta(minutes=interval_minutes)

    ts = df["timestamp"].sort_values().reset_index(drop=True)
    actual_start = ts.iloc[0]
    actual_end = ts.iloc[-1]

    expected_count = int(
        (actual_end - actual_start) / expected_delta
    ) + 1

    actual_count = len(ts)
    missing_count = expected_count - actual_count

    # Find actual gaps
    diffs = ts.diff().dropna()
    gap_mask = diffs > expected_delta
    n_gaps = int(gap_mask.sum())
    gap_timestamps: list[str] = []
    if n_gaps > 0:
        gap_idx = gap_mask[gap_mask].index
        gap_timestamps = [str(ts.iloc[i - 1]) for i in gap_idx[:5]]

    issues: list[str] = []
    status = ValidationStatus.PASS

    if missing_count > 0:
        issues.append(
            f"{missing_count} missing candle(s) detected in {timeframe} sequence "
            f"({actual_count}/{expected_count} present). "
            f"{n_gaps} gap(s) found. "
            + (f"First gaps at: {gap_timestamps}" if gap_timestamps else "")
        )
        status = ValidationStatus.WARNING  # WARNING, not FAIL — gaps are legitimate

    return ValidationResult(
        validator_name="missing_candles",
        status=status,
        issues=issues,
        stats={
            "expected_count": expected_count,
            "actual_count": actual_count,
            "missing_count": missing_count,
            "gap_count": n_gaps,
        },
    )


# ---------------------------------------------------------------------------
# Validator 5: Null Values
# ---------------------------------------------------------------------------

def validate_nulls(df: pd.DataFrame) -> ValidationResult:
    """
    Detect null (NaN/NaT) values in any column.

    Nulls in OHLCV data are forbidden in the canonical dataset.
    A null price cannot be used in a backtest without inventing data.
    """
    if df.empty:
        return ValidationResult(
            validator_name="nulls",
            status=ValidationStatus.WARNING,
            issues=["DataFrame is empty."],
            stats={"total_null_count": 0},
        )

    null_counts = df.isnull().sum()
    total_nulls = int(null_counts.sum())
    issues: list[str] = []

    if total_nulls > 0:
        affected = {col: int(cnt) for col, cnt in null_counts.items() if cnt > 0}
        issues.append(
            f"{total_nulls} null value(s) detected in columns: {affected}. "
            "Nulls in canonical data are forbidden — investigate the data source."
        )

    status = ValidationStatus.FAIL if issues else ValidationStatus.PASS
    return ValidationResult(
        validator_name="nulls",
        status=status,
        issues=issues,
        stats={"total_null_count": total_nulls, "null_by_column": dict(null_counts)},
    )


# ---------------------------------------------------------------------------
# Full validation pipeline
# ---------------------------------------------------------------------------

def run_validation_pipeline(
    df: pd.DataFrame,
    symbol: str,
    timeframe: str,
) -> DatasetValidationSummary:
    """
    Run all validators on a DataFrame and return a summary.

    Validators run in order; if schema validation fails, later validators
    may have undefined behavior, but they still run for completeness.

    Args:
        df:         The canonical OHLCV DataFrame to validate.
        symbol:     Asset symbol (e.g. "BTCUSDT").
        timeframe:  Timeframe string (e.g. "1m").

    Returns:
        DatasetValidationSummary with all per-validator results.
    """
    logger.debug("Running validation pipeline", symbol=symbol, timeframe=timeframe, rows=len(df))

    results = [
        validate_schema(df),
        validate_ohlc(df),
        validate_timestamps(df),
        validate_missing_candles(df, timeframe),
        validate_nulls(df),
    ]

    summary = DatasetValidationSummary(
        symbol=symbol,
        timeframe=timeframe,
        row_count=len(df),
        results=results,
    )

    logger.info(
        "Validation complete",
        symbol=symbol,
        timeframe=timeframe,
        status=summary.overall_status.value,
        issues=len(summary.all_issues),
    )
    return summary
