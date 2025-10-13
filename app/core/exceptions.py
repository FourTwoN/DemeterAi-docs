"""Application exception taxonomy for DemeterAI v2.0.

This module provides a centralized exception hierarchy for all business logic errors,
ensuring consistent error handling, logging, and API responses across the application.

Key features:
- Base AppBaseException with technical + user-friendly messages
- HTTP status codes embedded in exceptions
- Automatic logging with correlation IDs
- Extra metadata support for structured logging
- Debug mode control for exposing technical details

Usage:
    from app.core.exceptions import ProductMismatchException

    if config.product_id != request.product_id:
        raise ProductMismatchException(
            expected=config.product_id,
            actual=request.product_id
        )

    # Exception is automatically logged and converted to JSON response
"""

from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)


class AppBaseException(Exception):
    """Base exception for all application errors.

    All custom exceptions should inherit from this class to ensure
    consistent error handling, logging, and API responses.

    Attributes:
        technical_message: Detailed error message for logs/debugging
        user_message: User-friendly message for API responses
        code: HTTP status code (default: 500)
        extra: Additional metadata for structured logging
    """

    def __init__(
        self,
        technical_message: str,
        user_message: str,
        code: int = 500,
        extra: dict[str, Any] | None = None,
    ):
        """Initialize exception with messages and metadata.

        Args:
            technical_message: Technical details for logs (internal use)
            user_message: User-friendly message for API response
            code: HTTP status code (400, 404, 500, etc.)
            extra: Additional context for structured logging
        """
        self.technical_message = technical_message
        self.user_message = user_message
        self.code = code
        self.extra = extra or {}

        # Log exception with appropriate level
        # 5xx errors include stack trace (server errors)
        # 4xx errors are warnings (client errors)
        if code >= 500:
            logger.error(
                f"Server error: {self.__class__.__name__}",
                technical_message=technical_message,
                user_message=user_message,
                code=code,
                exc_info=True,
                **self.extra,
            )
        else:
            logger.warning(
                f"Client error: {self.__class__.__name__}",
                technical_message=technical_message,
                user_message=user_message,
                code=code,
                **self.extra,
            )

        super().__init__(technical_message)


# =============================================================================
# 4xx Client Errors - Issues with the request
# =============================================================================


class NotFoundException(AppBaseException):
    """Raised when a requested resource cannot be found.

    HTTP Status: 404 Not Found

    Example:
        raise NotFoundException(resource="Product", identifier=123)
    """

    def __init__(self, resource: str, identifier: Any):
        """Initialize NotFoundException.

        Args:
            resource: Type of resource (e.g., "Product", "Location", "User")
            identifier: Resource identifier (ID, name, UUID, etc.)
        """
        super().__init__(
            technical_message=f"{resource} not found: {identifier}",
            user_message=f"The {resource.lower()} you requested could not be found",
            code=404,
            extra={"resource": resource, "identifier": str(identifier)},
        )


class ValidationException(AppBaseException):
    """Raised when request validation fails.

    HTTP Status: 422 Unprocessable Entity

    Example:
        raise ValidationException(
            field="quantity",
            message="Quantity must be positive",
            value=-100
        )
    """

    def __init__(self, field: str, message: str, value: Any = None):
        """Initialize ValidationException.

        Args:
            field: Field name that failed validation
            message: Validation error message
            value: Invalid value (optional)
        """
        extra_dict = {"field": field}
        if value is not None:
            extra_dict["value"] = str(value)

        super().__init__(
            technical_message=f"Validation failed for {field}: {message} (value: {value})",
            user_message=f"Invalid value for {field}: {message}",
            code=422,
            extra=extra_dict,
        )


class ProductMismatchException(AppBaseException):
    """Raised when manual initialization product doesn't match location config.

    HTTP Status: 400 Bad Request

    This is a critical validation for manual stock initialization:
    - Storage locations have configured product_id
    - Manual init must specify matching product_id
    - Prevents accidental data corruption

    Example:
        raise ProductMismatchException(expected=45, actual=50)
    """

    def __init__(self, expected: int, actual: int):
        """Initialize ProductMismatchException.

        Args:
            expected: Product ID configured for the location
            actual: Product ID provided in manual init request
        """
        super().__init__(
            technical_message=f"Product mismatch: expected {expected}, got {actual}",
            user_message=(
                f"The product you entered (ID: {actual}) does not match the "
                f"configured product (ID: {expected}) for this location"
            ),
            code=400,
            extra={"expected_product_id": expected, "actual_product_id": actual},
        )


class ConfigNotFoundException(AppBaseException):
    """Raised when storage location configuration is missing.

    HTTP Status: 404 Not Found

    Storage locations require configuration before use:
    - product_id (what grows here)
    - band-based capacity thresholds
    - plant type configuration

    Example:
        raise ConfigNotFoundException(location_id=789)
    """

    def __init__(self, location_id: int):
        """Initialize ConfigNotFoundException.

        Args:
            location_id: Storage location ID missing configuration
        """
        super().__init__(
            technical_message=f"Configuration not found for location {location_id}",
            user_message=(
                "This storage location is not configured. "
                "Please configure it before initializing stock."
            ),
            code=404,
            extra={"location_id": location_id},
        )


class UnauthorizedException(AppBaseException):
    """Raised when authentication is required but missing or invalid.

    HTTP Status: 401 Unauthorized

    Example:
        raise UnauthorizedException(reason="Invalid JWT token")
    """

    def __init__(self, reason: str = "Authentication required"):
        """Initialize UnauthorizedException.

        Args:
            reason: Reason for authentication failure
        """
        super().__init__(
            technical_message=f"Authentication failed: {reason}",
            user_message="Authentication required. Please log in.",
            code=401,
            extra={"reason": reason},
        )


class ForbiddenException(AppBaseException):
    """Raised when user lacks permissions for the requested operation.

    HTTP Status: 403 Forbidden

    Example:
        raise ForbiddenException(
            resource="StockMovement",
            action="delete",
            user_id=123
        )
    """

    def __init__(self, resource: str, action: str, user_id: int | None = None):
        """Initialize ForbiddenException.

        Args:
            resource: Resource type (e.g., "StockMovement", "Product")
            action: Attempted action (e.g., "create", "delete", "update")
            user_id: User ID attempting the action (optional)
        """
        extra_dict: dict[str, Any] = {"resource": resource, "action": action}
        if user_id is not None:
            extra_dict["user_id"] = user_id

        super().__init__(
            technical_message=f"User {user_id} forbidden to {action} {resource}",
            user_message=f"You do not have permission to {action} this {resource.lower()}",
            code=403,
            extra=extra_dict,
        )


# =============================================================================
# 5xx Server Errors - Internal application issues
# =============================================================================


class DatabaseException(AppBaseException):
    """Raised when database operation fails.

    HTTP Status: 500 Internal Server Error

    Example:
        try:
            await session.execute(query)
        except SQLAlchemyError as e:
            raise DatabaseException(
                operation="INSERT",
                table="stock_movements",
                error=str(e)
            )
    """

    def __init__(self, operation: str, table: str | None = None, error: str | None = None):
        """Initialize DatabaseException.

        Args:
            operation: Database operation (SELECT, INSERT, UPDATE, DELETE)
            table: Table name involved in operation (optional)
            error: Original error message (optional)
        """
        table_info = f" on table {table}" if table else ""
        error_info = f": {error}" if error else ""

        super().__init__(
            technical_message=f"Database {operation} failed{table_info}{error_info}",
            user_message="A database error occurred. Please try again later.",
            code=500,
            extra={
                "operation": operation,
                "table": table or "unknown",
                "error": error or "unknown",
            },
        )


class S3UploadException(AppBaseException):
    """Raised when S3 upload operation fails.

    HTTP Status: 500 Internal Server Error (or 503 if S3 unavailable)

    Example:
        raise S3UploadException(
            file_name="photo_123.jpg",
            bucket="demeterai-photos",
            error="Network timeout"
        )
    """

    def __init__(self, file_name: str, bucket: str, error: str):
        """Initialize S3UploadException.

        Args:
            file_name: Name of file being uploaded
            bucket: S3 bucket name
            error: Error message from S3 client
        """
        super().__init__(
            technical_message=f"S3 upload failed: {file_name} to {bucket} - {error}",
            user_message="Photo upload failed. Please try again later.",
            code=500,
            extra={"file_name": file_name, "bucket": bucket, "error": error},
        )


class MLProcessingException(AppBaseException):
    """Raised when ML pipeline (YOLO/SAHI) processing fails.

    HTTP Status: 500 Internal Server Error

    Example:
        raise MLProcessingException(
            model="YOLOv11-seg",
            photo_id=123,
            error="OOM: Insufficient GPU memory"
        )
    """

    def __init__(self, model: str, photo_id: int, error: str):
        """Initialize MLProcessingException.

        Args:
            model: ML model name (e.g., "YOLOv11-seg", "SAHI")
            photo_id: Photo ID being processed
            error: Error message from ML pipeline
        """
        super().__init__(
            technical_message=f"ML processing failed: {model} on photo {photo_id} - {error}",
            user_message="Photo processing failed. Our team has been notified.",
            code=500,
            extra={"model": model, "photo_id": photo_id, "error": error},
        )


class ExternalServiceException(AppBaseException):
    """Raised when external service (API, third-party) is unavailable.

    HTTP Status: 503 Service Unavailable

    Example:
        raise ExternalServiceException(
            service="Weather API",
            endpoint="https://api.weather.com/v1/forecast",
            error="Connection timeout after 30s"
        )
    """

    def __init__(self, service: str, endpoint: str | None = None, error: str | None = None):
        """Initialize ExternalServiceException.

        Args:
            service: External service name
            endpoint: API endpoint URL (optional)
            error: Error message (optional)
        """
        endpoint_info = f" ({endpoint})" if endpoint else ""
        error_info = f": {error}" if error else ""

        super().__init__(
            technical_message=f"External service unavailable: {service}{endpoint_info}{error_info}",
            user_message=f"{service} is currently unavailable. Please try again later.",
            code=503,
            extra={
                "service": service,
                "endpoint": endpoint or "unknown",
                "error": error or "unknown",
            },
        )


class CeleryTaskException(AppBaseException):
    """Raised when Celery background task fails.

    HTTP Status: 500 Internal Server Error

    Example:
        raise CeleryTaskException(
            task_name="process_photo_task",
            task_id="550e8400-e29b-41d4-a716-446655440000",
            error="Worker timeout after 300s"
        )
    """

    def __init__(self, task_name: str, task_id: str | None = None, error: str | None = None):
        """Initialize CeleryTaskException.

        Args:
            task_name: Celery task name
            task_id: Task UUID (optional)
            error: Error message (optional)
        """
        task_id_info = f" (task_id: {task_id})" if task_id else ""
        error_info = f": {error}" if error else ""

        super().__init__(
            technical_message=f"Celery task failed: {task_name}{task_id_info}{error_info}",
            user_message="Background task failed. Please check task status or retry.",
            code=500,
            extra={
                "task_name": task_name,
                "task_id": task_id or "unknown",
                "error": error or "unknown",
            },
        )
