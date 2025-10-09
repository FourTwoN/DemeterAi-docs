# [F005] Exception Taxonomy - Centralized Error Handling

## Metadata
- **Epic**: epic-001-foundation.md
- **Sprint**: Sprint-00 (Week 1-2)
- **Status**: `backlog`
- **Priority**: `high`
- **Complexity**: M (5 story points)
- **Area**: `foundation`
- **Assignee**: TBD
- **Dependencies**:
  - Blocks: [All cards requiring error handling]
  - Blocked by: [F001, F002, F004]

## Related Documentation
- **Architecture**: ../../engineering_plan/03_architecture_overview.md#error-handling-strategy
- **Workflows**: ../../engineering_plan/workflows/manual_initialization.md (ProductMismatchException example)
- **Template**: ../../backlog/04_templates/starter-code/base_exception.py

## Description

Create centralized exception taxonomy with custom exception classes for all business logic errors, global FastAPI exception handlers, and consistent error response format.

**What**: Implement `app/core/exceptions.py` with base `AppBaseException` class and 10+ subclasses covering all error scenarios (not found, validation, permission, external service failures). Add FastAPI global exception handlers for consistent JSON error responses.

**Why**: Scattered try/catch blocks with generic exceptions create inconsistent error handling. Users receive cryptic error messages. Developers can't distinguish business errors from system errors. Centralized exceptions ensure consistent error responses, better logging, and easier debugging.

**Context**: DemeterAI has critical validation logic (e.g., manual initialization must match configured product). Without specific exceptions, errors like "Product mismatch" appear as generic 500 errors instead of actionable 400 errors.

## Acceptance Criteria

- [ ] **AC1**: Base exception class `AppBaseException` created:
  ```python
  class AppBaseException(Exception):
      def __init__(
          self,
          technical_message: str,
          user_message: str,
          code: int = 500,
          extra: dict = None
      ):
          self.technical_message = technical_message
          self.user_message = user_message
          self.code = code
          self.extra = extra or {}
  ```

- [ ] **AC2**: Exception subclasses for all scenarios:
  - `NotFoundException` (404) - Resource not found
  - `ValidationException` (422) - Pydantic validation failed
  - `ProductMismatchException` (400) - Manual init product != config
  - `ConfigNotFoundException` (404) - Location config missing
  - `UnauthorizedException` (401) - Invalid JWT token
  - `ForbiddenException` (403) - Insufficient permissions
  - `S3UploadException` (500) - S3 upload failed
  - `MLProcessingException` (500) - YOLO/SAHI failure
  - `DatabaseException` (500) - Database connection/query error
  - `ExternalServiceException` (503) - External API unavailable

- [ ] **AC3**: Global exception handlers in FastAPI:
  ```python
  @app.exception_handler(AppBaseException)
  async def app_exception_handler(request, exc: AppBaseException):
      return JSONResponse(
          status_code=exc.code,
          content={
              "error": exc.user_message,
              "code": exc.__class__.__name__,
              "correlation_id": get_correlation_id(),
              "detail": exc.technical_message if DEBUG else None
          }
      )
  ```

- [ ] **AC4**: Consistent error response format:
  ```json
  {
    "error": "The product you entered does not match the configured product",
    "code": "ProductMismatchException",
    "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
    "detail": "Product 50 != expected 45" // Only in DEBUG mode
  }
  ```

- [ ] **AC5**: Exception logging integration:
  - All exceptions logged with correlation ID
  - Technical details logged at ERROR level
  - User messages logged at WARNING level
  - Stack traces included for 500 errors

- [ ] **AC6**: Usage in services:
  ```python
  from app.core.exceptions import ProductMismatchException

  if config.product_id != request.product_id:
      raise ProductMismatchException(
          expected=config.product_id,
          actual=request.product_id
      )
  ```

## Technical Implementation Notes

### Architecture
- Layer: Foundation (Core Infrastructure)
- Dependencies: FastAPI, logging (from F004)
- Design pattern: Exception hierarchy, global exception handlers

### Code Hints

**app/core/exceptions.py structure:**
```python
from app.core.logging import get_logger

logger = get_logger(__name__)

class AppBaseException(Exception):
    """Base exception for all application errors."""

    def __init__(
        self,
        technical_message: str,
        user_message: str,
        code: int = 500,
        extra: dict = None
    ):
        self.technical_message = technical_message
        self.user_message = user_message
        self.code = code
        self.extra = extra or {}

        # Log technical details
        logger.error(
            f"Exception raised: {self.__class__.__name__}",
            extra={
                "technical_message": technical_message,
                "user_message": user_message,
                "code": code,
                **self.extra
            },
            exc_info=True if code >= 500 else False
        )

        super().__init__(technical_message)


class ProductMismatchException(AppBaseException):
    """Raised when manual init product doesn't match location config."""

    def __init__(self, expected: int, actual: int):
        super().__init__(
            technical_message=f"Product mismatch: expected {expected}, got {actual}",
            user_message=f"The product you entered (ID: {actual}) does not match the configured product (ID: {expected}) for this location",
            code=400,
            extra={"expected_product_id": expected, "actual_product_id": actual}
        )


class NotFoundException(AppBaseException):
    """Raised when a resource is not found."""

    def __init__(self, resource: str, identifier: any):
        super().__init__(
            technical_message=f"{resource} not found: {identifier}",
            user_message=f"The {resource.lower()} you requested could not be found",
            code=404,
            extra={"resource": resource, "identifier": identifier}
        )
```

**FastAPI integration (app/main.py):**
```python
from app.core.exceptions import AppBaseException
from app.core.logging import get_correlation_id
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

@app.exception_handler(AppBaseException)
async def app_exception_handler(request: Request, exc: AppBaseException):
    return JSONResponse(
        status_code=exc.code,
        content={
            "error": exc.user_message,
            "code": exc.__class__.__name__,
            "correlation_id": get_correlation_id(),
            "detail": exc.technical_message if DEBUG else None,
            "timestamp": datetime.utcnow().isoformat()
        }
    )
```

### Testing Requirements

**Unit Tests**:
- [ ] Test exception creation:
  ```python
  def test_product_mismatch_exception():
      exc = ProductMismatchException(expected=45, actual=50)
      assert exc.code == 400
      assert "45" in exc.user_message
      assert "50" in exc.user_message
  ```

- [ ] Test exception logging:
  ```python
  def test_exception_logs_technical_details(caplog):
      try:
          raise NotFoundException("Product", 123)
      except NotFoundException as e:
          assert "Product not found: 123" in caplog.text
  ```

**Integration Tests**:
- [ ] Test FastAPI exception handler:
  ```python
  @pytest.mark.asyncio
  async def test_exception_handler_returns_json(client):
      # Trigger NotFoundException in endpoint
      response = await client.get("/api/products/99999")
      assert response.status_code == 404
      assert "error" in response.json()
      assert "correlation_id" in response.json()
  ```

- [ ] Test DEBUG vs PROD mode:
  ```python
  def test_exception_detail_only_in_debug(client):
      # DEBUG=False
      response = client.get("/api/products/99999")
      assert "detail" not in response.json()

      # DEBUG=True
      response = client.get("/api/products/99999")
      assert "detail" in response.json()
  ```

**Test Command**:
```bash
pytest tests/core/test_exceptions.py -v --cov=app/core/exceptions
```

### Performance Expectations
- Exception creation overhead: <0.1ms
- Logging overhead: <1ms (from F004)
- Exception handler overhead: <0.2ms

## Handover Briefing

**For the next developer:**
- **Context**: This is the foundation for all error handling - every business error uses these exceptions
- **Key decisions**:
  - Two-message pattern: technical (for logs) + user-friendly (for API response)
  - HTTP status codes embedded in exceptions (not in controllers)
  - Global exception handlers in FastAPI (consistency)
  - Extra dict for structured logging context
  - Debug mode shows technical details (production hides them)
- **Known limitations**:
  - Celery task exceptions handled separately (different serialization)
  - Pydantic validation errors handled by FastAPI (not custom)
- **Next steps after this card**:
  - All services will raise these exceptions (not generic Exception)
  - Controllers should NOT catch exceptions (let global handler do it)
  - S001-S042: Service cards will use ProductMismatchException, etc.
- **Questions to ask**:
  - Should we add exception ID for tracking? (in addition to correlation_id)
  - Should we send exceptions to Sentry? (Sprint 05 decision)

## Definition of Done Checklist

- [ ] Code passes all tests (pytest)
- [ ] All 10 exception classes created
- [ ] FastAPI exception handler works
- [ ] Error responses follow consistent format
- [ ] Debug mode hides technical details in prod
- [ ] PR approved by 2+ reviewers
- [ ] Documentation updated (README.md with exception usage examples)
- [ ] No generic `raise Exception()` in app/ directory

## Time Tracking
- **Estimated**: 5 story points
- **Actual**: TBD (fill after completion)
- **Started**: TBD
- **Completed**: TBD

---

**Card Created**: 2025-10-09
**Last Updated**: 2025-10-09
**Card Owner**: TBD (assign during sprint planning)
