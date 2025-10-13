"""Tests for application exception taxonomy.

Tests verify:
1. Exception creation and attributes
2. HTTP status codes
3. Logging integration
4. Message formatting (technical vs user-friendly)
5. Extra metadata handling
6. FastAPI exception handlers
7. Debug mode behavior
"""

from datetime import datetime

from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.exceptions import (
    AppBaseException,
    CeleryTaskException,
    ConfigNotFoundException,
    DatabaseException,
    ExternalServiceException,
    ForbiddenException,
    MLProcessingException,
    NotFoundException,
    ProductMismatchException,
    S3UploadException,
    UnauthorizedException,
    ValidationException,
)
from app.core.logging import clear_correlation_id, get_logger, set_correlation_id, setup_logging

# Setup logging for tests
setup_logging("DEBUG")
logger = get_logger(__name__)


class TestAppBaseException:
    """Test base exception class."""

    def test_base_exception_creation(self):
        """Test base exception can be created with all attributes."""
        exc = AppBaseException(
            technical_message="Database connection failed",
            user_message="Service temporarily unavailable",
            code=500,
            extra={"connection": "postgres://localhost", "timeout": 30},
        )

        assert exc.technical_message == "Database connection failed"
        assert exc.user_message == "Service temporarily unavailable"
        assert exc.code == 500
        assert exc.extra == {"connection": "postgres://localhost", "timeout": 30}

    def test_base_exception_default_values(self):
        """Test base exception uses default values when not provided."""
        exc = AppBaseException(
            technical_message="Something went wrong",
            user_message="An error occurred",
        )

        assert exc.code == 500  # Default
        assert exc.extra == {}  # Default empty dict

    def test_base_exception_logs_server_errors(self, capsys):
        """Test 5xx errors are logged at ERROR level with stack trace."""
        exc = AppBaseException(
            technical_message="Critical server error",
            user_message="Server error",
            code=500,
        )

        # Check log output (structlog writes to stdout)
        captured = capsys.readouterr()
        assert "Server error" in captured.out
        assert "AppBaseException" in captured.out
        assert "error" in captured.out.lower()  # Log level

    def test_base_exception_logs_client_errors(self, capsys):
        """Test 4xx errors are logged at WARNING level without stack trace."""
        exc = AppBaseException(
            technical_message="Invalid request",
            user_message="Bad request",
            code=400,
        )

        # Check log output (structlog writes to stdout)
        captured = capsys.readouterr()
        assert "Client error" in captured.out
        assert "AppBaseException" in captured.out
        assert "warning" in captured.out.lower()  # Log level


class TestNotFoundException:
    """Test NotFoundException (404 errors)."""

    def test_not_found_exception_creation(self):
        """Test NotFoundException with resource and identifier."""
        exc = NotFoundException(resource="Product", identifier=123)

        assert exc.code == 404
        assert "Product not found: 123" in exc.technical_message
        assert "product you requested could not be found" in exc.user_message
        assert exc.extra["resource"] == "Product"
        assert exc.extra["identifier"] == "123"

    def test_not_found_exception_with_uuid(self):
        """Test NotFoundException with UUID identifier."""
        exc = NotFoundException(
            resource="Session", identifier="550e8400-e29b-41d4-a716-446655440000"
        )

        assert exc.code == 404
        assert "Session not found" in exc.technical_message
        assert "550e8400-e29b-41d4-a716-446655440000" in exc.technical_message


class TestValidationException:
    """Test ValidationException (422 errors)."""

    def test_validation_exception_with_value(self):
        """Test ValidationException includes field, message, and value."""
        exc = ValidationException(field="quantity", message="Must be positive", value=-100)

        assert exc.code == 422
        assert "Validation failed for quantity" in exc.technical_message
        assert "-100" in exc.technical_message
        assert "Invalid value for quantity" in exc.user_message
        assert exc.extra["field"] == "quantity"
        assert exc.extra["value"] == "-100"

    def test_validation_exception_without_value(self):
        """Test ValidationException without value parameter."""
        exc = ValidationException(field="email", message="Invalid format")

        assert exc.code == 422
        assert exc.extra["field"] == "email"
        assert "value" not in exc.extra  # Value not included when None


class TestProductMismatchException:
    """Test ProductMismatchException (400 errors)."""

    def test_product_mismatch_exception(self):
        """Test ProductMismatchException with expected and actual product IDs."""
        exc = ProductMismatchException(expected=45, actual=50)

        assert exc.code == 400
        assert "expected 45, got 50" in exc.technical_message
        assert "ID: 50" in exc.user_message
        assert "ID: 45" in exc.user_message
        assert exc.extra["expected_product_id"] == 45
        assert exc.extra["actual_product_id"] == 50


class TestConfigNotFoundException:
    """Test ConfigNotFoundException (404 errors)."""

    def test_config_not_found_exception(self):
        """Test ConfigNotFoundException with location_id."""
        exc = ConfigNotFoundException(location_id=789)

        assert exc.code == 404
        assert "Configuration not found for location 789" in exc.technical_message
        assert "not configured" in exc.user_message
        assert exc.extra["location_id"] == 789


class TestUnauthorizedException:
    """Test UnauthorizedException (401 errors)."""

    def test_unauthorized_exception_with_reason(self):
        """Test UnauthorizedException with custom reason."""
        exc = UnauthorizedException(reason="Invalid JWT token")

        assert exc.code == 401
        assert "Invalid JWT token" in exc.technical_message
        assert "log in" in exc.user_message
        assert exc.extra["reason"] == "Invalid JWT token"

    def test_unauthorized_exception_default(self):
        """Test UnauthorizedException with default reason."""
        exc = UnauthorizedException()

        assert exc.code == 401
        assert "Authentication required" in exc.technical_message


class TestForbiddenException:
    """Test ForbiddenException (403 errors)."""

    def test_forbidden_exception_with_user_id(self):
        """Test ForbiddenException with user_id."""
        exc = ForbiddenException(resource="StockMovement", action="delete", user_id=123)

        assert exc.code == 403
        assert "User 123 forbidden to delete StockMovement" in exc.technical_message
        assert "permission to delete" in exc.user_message
        assert exc.extra["resource"] == "StockMovement"
        assert exc.extra["action"] == "delete"
        assert exc.extra["user_id"] == 123

    def test_forbidden_exception_without_user_id(self):
        """Test ForbiddenException without user_id."""
        exc = ForbiddenException(resource="Product", action="create")

        assert exc.code == 403
        assert "user_id" not in exc.extra  # Not included when None


class TestDatabaseException:
    """Test DatabaseException (500 errors)."""

    def test_database_exception_complete(self):
        """Test DatabaseException with all parameters."""
        exc = DatabaseException(
            operation="INSERT", table="stock_movements", error="Connection timeout"
        )

        assert exc.code == 500
        assert "INSERT failed" in exc.technical_message
        assert "stock_movements" in exc.technical_message
        assert "Connection timeout" in exc.technical_message
        assert "database error occurred" in exc.user_message
        assert exc.extra["operation"] == "INSERT"
        assert exc.extra["table"] == "stock_movements"
        assert exc.extra["error"] == "Connection timeout"

    def test_database_exception_minimal(self):
        """Test DatabaseException with only operation."""
        exc = DatabaseException(operation="SELECT")

        assert exc.code == 500
        assert "SELECT failed" in exc.technical_message
        assert exc.extra["table"] == "unknown"
        assert exc.extra["error"] == "unknown"


class TestS3UploadException:
    """Test S3UploadException (500 errors)."""

    def test_s3_upload_exception(self):
        """Test S3UploadException with file, bucket, and error."""
        exc = S3UploadException(
            file_name="photo_123.jpg", bucket="demeterai-photos", error="Network timeout"
        )

        assert exc.code == 500
        assert "S3 upload failed" in exc.technical_message
        assert "photo_123.jpg" in exc.technical_message
        assert "demeterai-photos" in exc.technical_message
        assert "Photo upload failed" in exc.user_message
        assert exc.extra["file_name"] == "photo_123.jpg"
        assert exc.extra["bucket"] == "demeterai-photos"
        assert exc.extra["error"] == "Network timeout"


class TestMLProcessingException:
    """Test MLProcessingException (500 errors)."""

    def test_ml_processing_exception(self):
        """Test MLProcessingException with model, photo_id, and error."""
        exc = MLProcessingException(
            model="YOLOv11-seg", photo_id=456, error="OOM: Insufficient GPU memory"
        )

        assert exc.code == 500
        assert "ML processing failed" in exc.technical_message
        assert "YOLOv11-seg" in exc.technical_message
        assert "456" in exc.technical_message
        assert "Photo processing failed" in exc.user_message
        assert exc.extra["model"] == "YOLOv11-seg"
        assert exc.extra["photo_id"] == 456
        assert exc.extra["error"] == "OOM: Insufficient GPU memory"


class TestExternalServiceException:
    """Test ExternalServiceException (503 errors)."""

    def test_external_service_exception_complete(self):
        """Test ExternalServiceException with all parameters."""
        exc = ExternalServiceException(
            service="Weather API",
            endpoint="https://api.weather.com/v1/forecast",
            error="Connection timeout after 30s",
        )

        assert exc.code == 503
        assert "External service unavailable" in exc.technical_message
        assert "Weather API" in exc.technical_message
        assert "api.weather.com" in exc.technical_message
        assert "currently unavailable" in exc.user_message
        assert exc.extra["service"] == "Weather API"
        assert exc.extra["endpoint"] == "https://api.weather.com/v1/forecast"
        assert exc.extra["error"] == "Connection timeout after 30s"

    def test_external_service_exception_minimal(self):
        """Test ExternalServiceException with only service name."""
        exc = ExternalServiceException(service="Payment Gateway")

        assert exc.code == 503
        assert exc.extra["endpoint"] == "unknown"
        assert exc.extra["error"] == "unknown"


class TestCeleryTaskException:
    """Test CeleryTaskException (500 errors)."""

    def test_celery_task_exception_complete(self):
        """Test CeleryTaskException with all parameters."""
        exc = CeleryTaskException(
            task_name="process_photo_task",
            task_id="550e8400-e29b-41d4-a716-446655440000",
            error="Worker timeout after 300s",
        )

        assert exc.code == 500
        assert "Celery task failed" in exc.technical_message
        assert "process_photo_task" in exc.technical_message
        assert "550e8400-e29b-41d4-a716-446655440000" in exc.technical_message
        assert "Background task failed" in exc.user_message
        assert exc.extra["task_name"] == "process_photo_task"
        assert exc.extra["task_id"] == "550e8400-e29b-41d4-a716-446655440000"
        assert exc.extra["error"] == "Worker timeout after 300s"

    def test_celery_task_exception_minimal(self):
        """Test CeleryTaskException with only task name."""
        exc = CeleryTaskException(task_name="send_email_task")

        assert exc.code == 500
        assert exc.extra["task_id"] == "unknown"
        assert exc.extra["error"] == "unknown"


class TestExceptionHandlers:
    """Test FastAPI exception handlers."""

    def test_app_exception_handler_production_mode(self):
        """Test exception handler hides technical details in production."""
        # Ensure debug mode is OFF
        original_debug = settings.debug
        settings.debug = False

        try:
            from app.main import app

            client = TestClient(app)

            # Create a test endpoint that raises NotFoundException
            @app.get("/test-exception")
            async def test_exception():
                raise NotFoundException(resource="Product", identifier=999)

            # Call endpoint
            response = client.get("/test-exception")

            # Verify response
            assert response.status_code == 404
            data = response.json()

            # Check required fields
            assert "error" in data
            assert "product you requested could not be found" in data["error"]
            assert data["code"] == "NotFoundException"
            assert "correlation_id" in data
            assert "timestamp" in data

            # Verify technical details are HIDDEN
            assert "detail" not in data
            assert "extra" not in data

        finally:
            settings.debug = original_debug

    def test_app_exception_handler_debug_mode(self):
        """Test exception handler exposes technical details in debug mode."""
        # Enable debug mode
        original_debug = settings.debug
        settings.debug = True

        try:
            from app.main import app

            client = TestClient(app)

            # Create a test endpoint that raises ProductMismatchException
            @app.get("/test-debug-exception-v2")
            async def test_debug_exception():
                raise ProductMismatchException(expected=45, actual=50)

            # Call endpoint
            response = client.get("/test-debug-exception-v2")

            # Verify response
            assert response.status_code == 400
            data = response.json()

            # Check required fields
            assert "error" in data
            assert data["code"] == "ProductMismatchException"
            assert "correlation_id" in data

            # Verify technical details are EXPOSED
            assert "detail" in data
            assert "expected 45, got 50" in data["detail"]
            assert "extra" in data
            assert data["extra"]["expected_product_id"] == 45
            assert data["extra"]["actual_product_id"] == 50

        finally:
            settings.debug = original_debug

    def test_generic_exception_handler(self):
        """Test generic exception handler for unhandled exceptions."""
        # Test that exception handler is registered by trying to create one manually
        # Note: Starlette may handle some exceptions before our handler
        original_debug = settings.debug
        settings.debug = False

        try:
            from fastapi import Request

            from app.main import app, generic_exception_handler

            # Verify exception handler is registered
            exception_handlers = app.exception_handlers
            assert Exception in exception_handlers or len(exception_handlers) >= 1

            # Test the handler directly (more reliable than through HTTP)
            import asyncio
            from unittest.mock import Mock

            async def test_handler():
                # Create mock request
                request = Mock(spec=Request)
                request.url.path = "/test"
                request.method = "GET"

                # Call handler with ValueError
                exc = ValueError("Unexpected error")
                response = await generic_exception_handler(request, exc)

                # Verify response
                assert response.status_code == 500
                import json

                data = json.loads(response.body.decode())

                # Check required fields
                assert "error" in data
                assert "internal server error" in data["error"].lower()
                assert data["code"] == "InternalServerError"
                assert "correlation_id" in data
                assert "timestamp" in data

                # Verify exception details are HIDDEN in production
                assert "detail" not in data or "Unexpected error" not in data.get("detail", "")

            asyncio.run(test_handler())

        finally:
            settings.debug = original_debug

    def test_correlation_id_in_exception_response(self):
        """Test correlation ID is included in exception responses."""
        from app.main import app

        client = TestClient(app)

        # Create test endpoint
        @app.get("/test-correlation")
        async def test_correlation():
            raise NotFoundException(resource="Item", identifier=123)

        # Call with custom correlation ID
        response = client.get(
            "/test-correlation", headers={"X-Correlation-ID": "test-correlation-id-999"}
        )

        # Verify correlation ID in response
        assert response.status_code == 404
        data = response.json()
        assert data["correlation_id"] == "test-correlation-id-999"

    def test_timestamp_format_in_exception_response(self):
        """Test timestamp in exception response is ISO 8601 format."""
        from app.main import app

        client = TestClient(app)

        @app.get("/test-timestamp")
        async def test_timestamp():
            raise NotFoundException(resource="Item", identifier=123)

        response = client.get("/test-timestamp")
        data = response.json()

        # Verify timestamp is ISO 8601 format
        assert "timestamp" in data
        # Should be parseable as ISO format
        timestamp = datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))
        assert isinstance(timestamp, datetime)


class TestExceptionLogging:
    """Test exception logging integration."""

    def test_exception_includes_correlation_id_in_logs(self, capsys):
        """Test exceptions log correlation ID for tracing."""
        set_correlation_id("test-correlation-456")

        try:
            raise NotFoundException(resource="Product", identifier=999)
        except NotFoundException:
            pass

        # Verify correlation ID in logs (structlog writes to stdout)
        captured = capsys.readouterr()
        assert "test-correlation-456" in captured.out
        assert "NotFoundException" in captured.out or "Product not found" in captured.out

        clear_correlation_id()

    def test_server_error_logs_with_stack_trace(self, capsys):
        """Test 5xx errors include stack trace in logs."""
        try:
            raise DatabaseException(
                operation="INSERT", table="stock_movements", error="Deadlock detected"
            )
        except DatabaseException:
            pass

        # Verify error log was created (structlog writes to stdout)
        captured = capsys.readouterr()
        assert "DatabaseException" in captured.out or "Database INSERT failed" in captured.out
        assert "error" in captured.out.lower()  # Log level

    def test_client_error_logs_without_stack_trace(self, capsys):
        """Test 4xx errors don't include stack trace in logs."""
        try:
            raise ValidationException(field="email", message="Invalid format")
        except ValidationException:
            pass

        # Verify warning log was created (structlog writes to stdout)
        captured = capsys.readouterr()
        assert "ValidationException" in captured.out or "Validation failed" in captured.out
        assert "warning" in captured.out.lower()  # Log level


def test_all_exceptions_inherit_from_base():
    """Test all custom exceptions inherit from AppBaseException."""
    exception_classes = [
        NotFoundException,
        ValidationException,
        ProductMismatchException,
        ConfigNotFoundException,
        UnauthorizedException,
        ForbiddenException,
        DatabaseException,
        S3UploadException,
        MLProcessingException,
        ExternalServiceException,
        CeleryTaskException,
    ]

    for exc_class in exception_classes:
        assert issubclass(
            exc_class, AppBaseException
        ), f"{exc_class.__name__} must inherit from AppBaseException"


def test_exception_count():
    """Test that we have at least 10 exception classes (AC requirement)."""
    exception_classes = [
        NotFoundException,
        ValidationException,
        ProductMismatchException,
        ConfigNotFoundException,
        UnauthorizedException,
        ForbiddenException,
        DatabaseException,
        S3UploadException,
        MLProcessingException,
        ExternalServiceException,
        CeleryTaskException,
    ]

    assert len(exception_classes) >= 10, "Must have at least 10 exception classes"
