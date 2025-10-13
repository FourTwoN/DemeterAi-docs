"""Structured logging configuration with correlation IDs.

This module provides centralized logging configuration for DemeterAI v2.0,
supporting structured JSON output for production log aggregation and
correlation ID tracking for request tracing across services.

Key features:
- Structured JSON logging (compatible with Prometheus/Loki/CloudWatch)
- Correlation ID tracking (trace API → Celery → Database)
- Environment-based log levels (DEBUG/INFO/WARNING/ERROR)
- Thread-safe context variables for async operations
- Extra fields support for rich contextual logging

Usage:
    from app.core.logging import setup_logging, get_logger

    # Setup (typically in main.py)
    setup_logging(log_level="INFO")

    # Get logger instance
    logger = get_logger(__name__)

    # Log with extra context
    logger.info("Processing photo", photo_id=123, user_id=45)
    logger.warning("Missing config", location_id=789)
    logger.error("S3 upload failed", error=str(e), exc_info=True)
"""

import logging
import sys
from contextvars import ContextVar
from typing import Any
from uuid import uuid4

import structlog
from structlog.typing import EventDict, Processor

# Correlation ID context variable (thread-safe for async)
correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")


def add_correlation_id(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Add correlation_id from context to log event.

    Args:
        logger: Logger instance
        method_name: Logging method name
        event_dict: Event dictionary being logged

    Returns:
        Event dictionary with correlation_id added
    """
    correlation_id = correlation_id_var.get()
    if correlation_id:
        event_dict["correlation_id"] = correlation_id
    return event_dict


def setup_logging(log_level: str = "INFO") -> structlog.BoundLogger:
    """Configure structured logging for the application.

    Sets up structlog with JSON output format, correlation ID support,
    and appropriate log levels for the environment.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
                  Defaults to INFO if not specified.

    Returns:
        Configured structlog BoundLogger instance

    Example:
        >>> logger = setup_logging("DEBUG")
        >>> logger.info("Application started", version="2.0.0")
    """
    # Convert string level to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=numeric_level,
    )

    # Configure structlog processors
    processors: list[Processor] = [
        # Add log level to event dict
        structlog.stdlib.add_log_level,
        # Add timestamp in ISO format
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        # Add correlation_id from context
        add_correlation_id,
        # Format stack info if present
        structlog.processors.StackInfoRenderer(),
        # Format exception info if present
        structlog.processors.format_exc_info,
        # Render as JSON for production
        structlog.processors.JSONRenderer(),
    ]

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    return structlog.get_logger()


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a logger instance for the specified module.

    Args:
        name: Logger name (typically __name__ of the calling module)

    Returns:
        Configured structlog BoundLogger instance

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Service started", service="StockMovementService")
    """
    return structlog.get_logger(name)


def set_correlation_id(correlation_id: str | None = None) -> str:
    """Set correlation ID in context for request tracing.

    If no correlation_id is provided, generates a new UUID.
    This correlation_id will be automatically added to all log statements
    within the current context (thread/async task).

    Args:
        correlation_id: Correlation ID to set. If None, generates new UUID.

    Returns:
        The correlation ID that was set

    Example:
        >>> # In FastAPI middleware
        >>> correlation_id = set_correlation_id()
        >>> logger.info("Request received")  # Will include correlation_id
        >>>
        >>> # In Celery task
        >>> set_correlation_id(task_correlation_id)  # Propagate from API
        >>> logger.info("Task started")  # Will include same correlation_id
    """
    if correlation_id is None:
        correlation_id = str(uuid4())

    correlation_id_var.set(correlation_id)
    return correlation_id


def get_correlation_id() -> str:
    """Get current correlation ID from context.

    Returns:
        Current correlation ID or empty string if not set

    Example:
        >>> correlation_id = get_correlation_id()
        >>> if correlation_id:
        ...     logger.info("Current request", correlation_id=correlation_id)
    """
    return correlation_id_var.get()


def clear_correlation_id() -> None:
    """Clear correlation ID from context.

    Useful for cleanup in long-running workers or tests.

    Example:
        >>> # In test teardown
        >>> clear_correlation_id()
    """
    correlation_id_var.set("")
