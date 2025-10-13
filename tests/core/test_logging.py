"""Tests for structured logging configuration.

Tests verify:
- Logger configuration with different log levels
- Structured JSON output format
- Correlation ID generation and propagation
- Thread-safe context variables
"""

import json

import pytest

from app.core.logging import (
    clear_correlation_id,
    get_correlation_id,
    get_logger,
    set_correlation_id,
    setup_logging,
)


class TestLoggingConfiguration:
    """Test logging setup and configuration."""

    def test_setup_logging_default_level(self):
        """Test logging setup with default INFO level."""
        logger = setup_logging()
        assert logger is not None

    def test_setup_logging_debug_level(self):
        """Test logging setup with DEBUG level."""
        logger = setup_logging("DEBUG")
        assert logger is not None

    def test_setup_logging_warning_level(self):
        """Test logging setup with WARNING level."""
        logger = setup_logging("WARNING")
        assert logger is not None

    def test_get_logger_returns_bound_logger(self):
        """Test get_logger returns a bound logger instance."""
        logger = get_logger(__name__)
        assert logger is not None
        assert hasattr(logger, "info")
        assert hasattr(logger, "warning")
        assert hasattr(logger, "error")


class TestCorrelationId:
    """Test correlation ID management."""

    def test_set_correlation_id_with_value(self):
        """Test setting correlation ID with explicit value."""
        test_id = "test-correlation-id-123"
        result = set_correlation_id(test_id)
        assert result == test_id
        assert get_correlation_id() == test_id
        clear_correlation_id()

    def test_set_correlation_id_generates_uuid(self):
        """Test setting correlation ID generates UUID when not provided."""
        result = set_correlation_id()
        assert result != ""
        assert len(result) == 36  # UUID format: 8-4-4-4-12
        assert get_correlation_id() == result
        clear_correlation_id()

    def test_get_correlation_id_empty_by_default(self):
        """Test get_correlation_id returns empty string when not set."""
        clear_correlation_id()
        assert get_correlation_id() == ""

    def test_clear_correlation_id(self):
        """Test clearing correlation ID resets to empty string."""
        set_correlation_id("test-id")
        assert get_correlation_id() != ""
        clear_correlation_id()
        assert get_correlation_id() == ""


class TestStructuredLogging:
    """Test structured JSON logging output."""

    def test_logger_outputs_json(self, capfd):
        """Test logger outputs valid JSON format."""
        setup_logging("INFO")
        logger = get_logger(__name__)

        # Set correlation ID for testing
        set_correlation_id("test-correlation-123")

        # Log a message
        logger.info("Test message", extra_field="test_value")

        # Capture output
        captured = capfd.readouterr()
        output = captured.out.strip()

        # Verify it's valid JSON
        try:
            log_entry = json.loads(output.split("\n")[-1])  # Get last line
            assert log_entry["event"] == "Test message"
            assert log_entry["level"] == "info"
            assert "timestamp" in log_entry
            assert log_entry["correlation_id"] == "test-correlation-123"
            assert log_entry["extra_field"] == "test_value"
        except json.JSONDecodeError as e:
            pytest.fail(f"Log output is not valid JSON: {e}")
        finally:
            clear_correlation_id()

    def test_logger_includes_timestamp(self, capfd):
        """Test logger includes ISO format timestamp."""
        setup_logging("INFO")
        logger = get_logger(__name__)

        logger.info("Timestamp test")

        captured = capfd.readouterr()
        output = captured.out.strip()

        log_entry = json.loads(output.split("\n")[-1])
        assert "timestamp" in log_entry
        # ISO format contains 'T' separator
        assert "T" in log_entry["timestamp"]

    def test_logger_includes_log_level(self, capfd):
        """Test logger includes log level in output."""
        setup_logging("DEBUG")
        logger = get_logger(__name__)

        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")

        captured = capfd.readouterr()
        output_lines = [line for line in captured.out.strip().split("\n") if line]

        # Check each log level
        debug_entry = json.loads(output_lines[-3])
        info_entry = json.loads(output_lines[-2])
        warning_entry = json.loads(output_lines[-1])

        assert debug_entry["level"] == "debug"
        assert info_entry["level"] == "info"
        assert warning_entry["level"] == "warning"

    def test_logger_includes_correlation_id(self, capfd):
        """Test logger includes correlation ID when set."""
        setup_logging("INFO")
        logger = get_logger(__name__)

        correlation_id = "test-uuid-12345"
        set_correlation_id(correlation_id)

        logger.info("Message with correlation ID")

        captured = capfd.readouterr()
        output = captured.out.strip()

        log_entry = json.loads(output.split("\n")[-1])
        assert log_entry["correlation_id"] == correlation_id

        clear_correlation_id()

    def test_logger_without_correlation_id(self, capfd):
        """Test logger works without correlation ID set."""
        setup_logging("INFO")
        logger = get_logger(__name__)

        clear_correlation_id()
        logger.info("Message without correlation ID")

        captured = capfd.readouterr()
        output = captured.out.strip()

        log_entry = json.loads(output.split("\n")[-1])
        # correlation_id should not be present if not set
        assert "correlation_id" not in log_entry or log_entry["correlation_id"] == ""


class TestLogLevels:
    """Test different log levels and filtering."""

    def test_info_level_filters_debug(self, capfd):
        """Test INFO level filters out DEBUG messages."""
        setup_logging("INFO")
        logger = get_logger(__name__)

        logger.debug("Debug message - should not appear")
        logger.info("Info message - should appear")

        captured = capfd.readouterr()
        output = captured.out

        # Debug message should not be in output
        assert "Debug message" not in output
        # Info message should be in output
        assert "Info message" in output

    def test_warning_level_filters_info(self, capfd):
        """Test WARNING level filters out INFO and DEBUG messages."""
        setup_logging("WARNING")
        logger = get_logger(__name__)

        logger.debug("Debug message - should not appear")
        logger.info("Info message - should not appear")
        logger.warning("Warning message - should appear")

        captured = capfd.readouterr()
        output = captured.out

        # Debug and Info should not be in output
        assert "Debug message" not in output
        assert "Info message" not in output
        # Warning should be in output
        assert "Warning message" in output

    def test_debug_level_shows_all(self, capfd):
        """Test DEBUG level shows all messages."""
        setup_logging("DEBUG")
        logger = get_logger(__name__)

        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")

        captured = capfd.readouterr()
        output = captured.out

        # All messages should be in output
        assert "Debug message" in output
        assert "Info message" in output
        assert "Warning message" in output
        assert "Error message" in output


class TestExtraFields:
    """Test logging with extra contextual fields."""

    def test_logger_accepts_extra_fields(self, capfd):
        """Test logger accepts and includes extra keyword arguments."""
        setup_logging("INFO")
        logger = get_logger(__name__)

        logger.info(
            "Processing photo",
            photo_id=123,
            user_id=45,
            location="warehouse-1",
        )

        captured = capfd.readouterr()
        output = captured.out.strip()

        log_entry = json.loads(output.split("\n")[-1])
        assert log_entry["photo_id"] == 123
        assert log_entry["user_id"] == 45
        assert log_entry["location"] == "warehouse-1"

    def test_logger_with_complex_extra_fields(self, capfd):
        """Test logger with complex data types in extra fields."""
        setup_logging("INFO")
        logger = get_logger(__name__)

        logger.info(
            "Complex data",
            metadata={"key1": "value1", "key2": "value2"},
            tags=["tag1", "tag2", "tag3"],
        )

        captured = capfd.readouterr()
        output = captured.out.strip()

        log_entry = json.loads(output.split("\n")[-1])
        assert log_entry["metadata"] == {"key1": "value1", "key2": "value2"}
        assert log_entry["tags"] == ["tag1", "tag2", "tag3"]
