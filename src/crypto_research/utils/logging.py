"""
Structured logging setup for the crypto research laboratory.

Uses structlog for structured, context-rich logging with rich console output.

Design decisions:
    - Logs are structured: every log event has machine-readable fields.
    - Every log event carries the run_id for traceability.
    - Console output is colorized via rich (when format='console').
    - File output is always plain structured text.
    - Errors are NEVER swallowed — this logging setup must be transparent.

IMPORTANT: Never catch and suppress log errors. If logging fails,
the program should fail, not silently continue without logs.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional

import structlog
from rich.logging import RichHandler


def setup_logging(
    run_id: str,
    log_dir: Optional[Path] = None,
    level: str = "INFO",
    format: str = "console",
) -> structlog.stdlib.BoundLogger:
    """
    Configure and return a structured logger for a research run.

    Sets up both console output (via rich) and optional file output.
    Must be called once at the start of each research run.

    Args:
        run_id:   Research run identifier, included in every log event.
        log_dir:  Directory where log files are written. If None, only
                  console logging is configured. The directory must exist.
        level:    Log level string: 'DEBUG', 'INFO', 'WARNING', 'ERROR'.
        format:   'console' for colored human-readable, 'structured' for JSON.

    Returns:
        A structlog BoundLogger pre-bound with the run_id context.

    Raises:
        ValueError: If level or format are invalid.
        OSError: If log_dir is provided but cannot be written to.
    """
    numeric_level = _parse_level(level)

    handlers: list[logging.Handler] = []

    # Console handler
    if format == "console":
        console_handler = RichHandler(
            level=numeric_level,
            rich_tracebacks=True,
            show_time=True,
            show_path=False,
            markup=True,
        )
        handlers.append(console_handler)
    else:
        # Structured / JSON: plain stdout handler
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setLevel(numeric_level)
        handlers.append(stream_handler)

    # File handler
    if log_dir is not None:
        log_dir = Path(log_dir)
        if not log_dir.exists():
            # Fail fast — never create missing log directories silently here;
            # the caller (RunManager) is responsible for creating the log dir.
            raise OSError(
                f"Log directory does not exist: {log_dir}\n"
                f"Ensure RunManager creates the directory before calling setup_logging."
            )
        log_file = log_dir / "research.log"
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(numeric_level)
        file_formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_formatter)
        handlers.append(file_handler)

    # Configure stdlib logging root
    logging.basicConfig(
        level=numeric_level,
        handlers=handlers,
        force=True,  # Replace any previously configured handlers
    )

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer() if format == "console"
            else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Return a logger bound with run_id for all subsequent calls
    logger: structlog.stdlib.BoundLogger = structlog.get_logger("crypto_research").bind(
        run_id=run_id
    )

    logger.info(
        "Logging initialized",
        level=level,
        format=format,
        log_dir=str(log_dir) if log_dir else None,
    )

    return logger


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Get a named structlog logger without configuring handlers.

    Useful for module-level loggers. setup_logging() must have been called
    first to configure the handlers and processors.

    Args:
        name: Logger name, conventionally the module __name__.

    Returns:
        A structlog BoundLogger.
    """
    return structlog.get_logger(name)


def _parse_level(level: str) -> int:
    """
    Parse a log level string to the stdlib numeric constant.

    Raises:
        ValueError: If the level string is not recognized.
    """
    mapping = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    upper = level.upper()
    if upper not in mapping:
        raise ValueError(
            f"Invalid log level '{level}'. Valid values: {list(mapping.keys())}"
        )
    return mapping[upper]
