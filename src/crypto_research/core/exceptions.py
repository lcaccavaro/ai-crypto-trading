"""
Custom exception hierarchy for the crypto research laboratory.

Design principle: FAIL FAST.

All unexpected errors must propagate visibly. No silent catch-and-continue.
No fallback behavior. Errors must expose enough information to diagnose the
root cause.

Exception hierarchy:
    CryptoResearchError          (base for all project exceptions)
    ├── ConfigurationError       (config loading / validation failures)
    ├── DataIntegrityError       (data quality / point-in-time violations)
    │   └── LookAheadBiasError   (attempted use of future information)
    ├── ExecutionError           (order / position simulation failures)
    ├── ResearchRunError         (run management / metadata failures)
    └── ReproducibilityError     (reproducibility-related violations)
"""


class CryptoResearchError(Exception):
    """
    Base exception for all errors raised by the crypto_research package.

    Every intentional error in this project should inherit from this class
    so that callers can catch project errors specifically if needed.
    """


class ConfigurationError(CryptoResearchError):
    """
    Raised when configuration cannot be loaded or fails validation.

    Examples:
        - Configuration file not found.
        - Required field missing.
        - Field value fails schema validation.
        - Unknown configuration key in strict mode.

    Execution MUST stop when this is raised.
    No fallback configuration is acceptable.
    """


class DataIntegrityError(CryptoResearchError):
    """
    Raised when a data integrity violation is detected.

    Examples:
        - Candle timestamps are out of order.
        - OHLC relationships are violated (high < low, etc.).
        - Missing mandatory data fields.
        - Data source returns unexpected format.

    Execution MUST stop when this is raised.
    """


class LookAheadBiasError(DataIntegrityError):
    """
    Raised when a component attempts to use information from the future.

    This is one of the most critical errors in a backtesting system.

    Examples:
        - Strategy accesses a candle beyond the simulation timestamp.
        - Indicator computed using future prices.
        - Strategy selected based on future performance metrics.

    Execution MUST stop immediately when this is raised.
    """


class ExecutionError(CryptoResearchError):
    """
    Raised when order submission or position management fails.

    Examples:
        - Invalid order parameters.
        - Attempt to close a position that does not exist.
        - Fill price outside realistic bounds.

    Execution MUST stop when this is raised.
    """


class ResearchRunError(CryptoResearchError):
    """
    Raised when research run management encounters an error.

    Examples:
        - Cannot create run directory.
        - Metadata serialization fails.
        - Run ID collision.
        - Missing required environment information.

    Execution MUST stop when this is raised.
    """


class ReproducibilityError(CryptoResearchError):
    """
    Raised when a reproducibility requirement is violated.

    Examples:
        - Random seed not set when required.
        - Non-deterministic operation detected in deterministic context.
        - Configuration hash mismatch between runs.

    Execution MUST stop when this is raised.
    """
