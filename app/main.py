"""FastAPI application entry point for DemeterAI v2.0."""

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.exceptions import AppBaseException
from app.core.logging import get_correlation_id, get_logger, set_correlation_id, setup_logging

# Setup logging with level from environment
setup_logging(log_level=settings.log_level)
logger = get_logger(__name__)

app = FastAPI(
    title="DemeterAI v2.0",
    version="2.0.0",
    description="Automated plant counting and inventory management system",
)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Middleware to inject correlation IDs into requests.

    Generates a unique UUID for each request (or uses existing X-Correlation-ID header),
    sets it in the logging context, and returns it in the response headers.

    This enables request tracing across the entire system:
    API request → Celery task → Database operation → Logs
    """

    async def dispatch(self, request: Request, call_next: Any) -> Any:
        """Process request with correlation ID injection."""
        # Get correlation ID from header or generate new one
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid4()))

        # Set in logging context
        set_correlation_id(correlation_id)

        # Log request
        logger.info(
            "Request received",
            method=request.method,
            path=request.url.path,
            correlation_id=correlation_id,
        )

        # Process request
        response = await call_next(request)

        # Add correlation ID to response headers
        response.headers["X-Correlation-ID"] = correlation_id

        # Log response
        logger.info(
            "Request completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            correlation_id=correlation_id,
        )

        return response


# Register middleware
app.add_middleware(CorrelationIdMiddleware)


# =============================================================================
# Exception Handlers - Consistent error responses
# =============================================================================


@app.exception_handler(AppBaseException)
async def app_exception_handler(request: Request, exc: AppBaseException) -> JSONResponse:
    """Handle all AppBaseException instances with consistent JSON response.

    Converts exceptions to JSON format with:
    - User-friendly error message (always)
    - Exception code/type (always)
    - Correlation ID for tracing (always)
    - Technical details (only in DEBUG mode)
    - Timestamp (always)

    Args:
        request: FastAPI request object
        exc: AppBaseException instance

    Returns:
        JSONResponse with error details and appropriate HTTP status code
    """
    correlation_id = get_correlation_id()

    response_data: dict[str, Any] = {
        "error": exc.user_message,
        "code": exc.__class__.__name__,
        "correlation_id": correlation_id,
        "timestamp": datetime.now(UTC).isoformat(),
    }

    # Only expose technical details in debug mode
    if settings.debug:
        response_data["detail"] = exc.technical_message
        response_data["extra"] = exc.extra

    return JSONResponse(
        status_code=exc.code,
        content=response_data,
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle all unhandled exceptions with generic 500 response.

    This catches any exception not explicitly handled by other handlers,
    preventing stack traces from leaking to the client in production.

    Args:
        request: FastAPI request object
        exc: Any unhandled exception

    Returns:
        JSONResponse with generic error message
    """
    correlation_id = get_correlation_id()

    # Log the unhandled exception with full stack trace
    logger.error(
        "Unhandled exception",
        exception_type=type(exc).__name__,
        exception_message=str(exc),
        path=request.url.path,
        method=request.method,
        correlation_id=correlation_id,
        exc_info=True,
    )

    response_data: dict[str, Any] = {
        "error": "An internal server error occurred. Our team has been notified.",
        "code": "InternalServerError",
        "correlation_id": correlation_id,
        "timestamp": datetime.now(UTC).isoformat(),
    }

    # Only expose exception details in debug mode
    if settings.debug:
        response_data["detail"] = f"{type(exc).__name__}: {str(exc)}"

    return JSONResponse(
        status_code=500,
        content=response_data,
    )


# =============================================================================
# Router Registration - Sprint 04 (26 endpoints)
# =============================================================================

from app.controllers import (
    analytics_router,
    config_router,
    location_router,
    product_router,
    stock_router,
)

# Register all API routers
app.include_router(stock_router)  # C001-C007: Stock management
app.include_router(location_router)  # C008-C013: Location hierarchy
app.include_router(product_router)  # C014-C020: Product management
app.include_router(config_router)  # C021-C023: Configuration
app.include_router(analytics_router)  # C024-C026: Analytics


# =============================================================================
# Health Check Endpoint
# =============================================================================


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint.

    Returns:
        dict: Health status with correlation ID in response headers
    """
    logger.info("Health check endpoint called")
    return {"status": "healthy", "service": "DemeterAI v2.0"}
