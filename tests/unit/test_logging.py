"""
Unit tests for logging utilities.

Tests:
    - Logging initializes without error.
    - Log file is created when log_dir is provided.
    - Invalid log level raises ValueError (fail-fast).
    - setup_logging with missing log_dir raises OSError.
    - get_logger returns a usable logger.
"""

import tempfile
from pathlib import Path

import pytest

from crypto_research.utils.logging import get_logger, setup_logging


class TestLoggingSetup:
    def test_console_logger_initializes(self):
        """Console-only logging should initialize without error."""
        logger = setup_logging(run_id="RUN_TEST_001", level="INFO", format="console")
        assert logger is not None

    def test_file_logger_creates_log_file(self, tmp_path):
        """When log_dir is provided, a log file must be created."""
        log_dir = tmp_path / "logs"
        log_dir.mkdir()
        logger = setup_logging(
            run_id="RUN_TEST_002",
            log_dir=log_dir,
            level="INFO",
            format="console",
        )
        assert logger is not None
        log_file = log_dir / "research.log"
        assert log_file.exists()

    def test_missing_log_dir_raises(self, tmp_path):
        """If log_dir does not exist, fail fast with OSError."""
        nonexistent = tmp_path / "does_not_exist"
        with pytest.raises(OSError, match="does not exist"):
            setup_logging(
                run_id="RUN_TEST_003",
                log_dir=nonexistent,
                level="INFO",
                format="console",
            )

    def test_invalid_level_raises(self):
        """Invalid log level should raise ValueError immediately."""
        with pytest.raises(ValueError, match="Invalid log level"):
            setup_logging(run_id="RUN_TEST_004", level="VERBOSE", format="console")

    def test_get_logger_returns_logger(self):
        """get_logger should return a usable logger object."""
        logger = get_logger("test.module")
        assert logger is not None
        # Should not raise
        logger.info("test message from unit test")
