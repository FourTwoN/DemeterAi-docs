# [F004] Logging Configuration - Structured JSON + Correlation IDs

## Metadata
- **Epic**: epic-001-foundation.md
- **Sprint**: Sprint-00 (Week 1-2)
- **Status**: `backlog`
- **Priority**: `high`
- **Complexity**: M (5 story points)
- **Area**: `foundation`
- **Assignee**: TBD
- **Dependencies**:
  - Blocks**: [All cards requiring logging]
  - Blocked by: [F001, F002, F003]

## Related Documentation
- **Architecture**: ../../engineering_plan/03_architecture_overview.md#error-handling-strategy
- **Tech Stack**: ../../backlog/00_foundation/tech-stack.md#monitoring--observability
- **Conventions**: ../../backlog/00_foundation/conventions.md#logging-standards

## Description

Implement centralized logging configuration with structured JSON output, correlation IDs for request tracing, and configurable log levels for different environments.

**What**: Create `app/core/logging.py` with logging setup supporting structured JSON format (for Prometheus/Loki), correlation ID injection (trace requests across services), and environment-based log levels (DEBUG in dev, INFO in prod).

**Why**: Structured logging enables automated log parsing and filtering in production. Correlation IDs allow tracing a single request through the entire system (API → Celery → Database). Centralized config prevents scattered print() statements.

**Context**: DemeterAI processes photos asynchronously (API → Celery workers → Database). Without correlation IDs, debugging a failed photo is impossible. Structured JSON logs integrate with Prometheus/Grafana stack (Sprint 05).

## Acceptance Criteria

- [ ] **AC1**: `app/core/logging.py` created with `setup_logging()` function:
  - Accepts `log_level` parameter (DEBUG, INFO, WARNING, ERROR)
  - Configures root logger and all app loggers
  - Returns configured logger instance

- [ ] **AC2**: Structured JSON output format:
  ```json
  {
    "timestamp": "2025-10-09T14:30:00.123Z",
    "level": "INFO",
    "logger": "app.services.stock_service",
    "message": "Stock movement created",
    "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
    "user_id": 123,
    "extra": {"movement_type": "manual_init", "quantity": 1500}
  }
  ```

- [ ] **AC3**: Correlation ID middleware for FastAPI:
  - Generates UUID for each request
  - Injects into logger context
  - Returns in response header: `X-Correlation-ID`
  - Propagates to Celery tasks

- [ ] **AC4**: Environment-based log levels:
  - Development: DEBUG (all logs)
  - Staging: INFO (exclude debug)
  - Production: WARNING (only warnings/errors)
  - Configured via `.env`: `LOG_LEVEL=DEBUG`

- [ ] **AC5**: Logger usage in code:
  ```python
  from app.core.logging import get_logger

  logger = get_logger(__name__)

  logger.info("Processing photo", extra={"photo_id": 123, "user_id": 45})
  logger.warning("Missing config", extra={"location_id": 789})
  logger.error("S3 upload failed", extra={"error": str(e)}, exc_info=True)
  ```

- [ ] **AC6**: No print() statements allowed:
  - Pre-commit hook blocks print() in `app/` directory
  - All output via logger only

## Technical Implementation Notes

### Architecture
- Layer: Foundation (Core Infrastructure)
- Dependencies: Python logging, structlog (structured logging), FastAPI middleware
- Design pattern: Singleton logger factory, middleware injection

### Code Hints

**app/core/logging.py structure:**
```python
import logging
import structlog
from uuid import uuid4
from contextvars import ContextVar

# Correlation ID context (thread-safe)
correlation_id_var: ContextVar[str] = ContextVar('correlation_id', default='')

def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """
    Configure structured logging for the application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)

    Returns:
        Configured logger instance
    """
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(log_level)),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )

    return structlog.get_logger()

def get_logger(name: str) -> structlog.BoundLogger:
    """Get logger for specific module."""
    return structlog.get_logger(name)

def set_correlation_id(correlation_id: str):
    """Set correlation ID in context."""
    correlation_id_var.set(correlation_id)
    structlog.contextvars.bind_contextvars(correlation_id=correlation_id)
```

**FastAPI middleware (app/main.py):**
```python
from app.core.logging import set_correlation_id

@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid4()))
    set_correlation_id(correlation_id)

    response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id
    return response
```

**Celery task integration:**
```python
from app.core.logging import set_correlation_id

@celery_app.task(bind=True)
def process_photo(self, photo_id: int, correlation_id: str):
    set_correlation_id(correlation_id)  # Propagate from API
    logger.info("Processing photo", photo_id=photo_id)
    # ... task logic
```

### Testing Requirements

**Unit Tests**:
- [ ] Test logger configuration:
  ```python
  def test_setup_logging_debug_level():
      logger = setup_logging("DEBUG")
      assert logger.getEffectiveLevel() == logging.DEBUG
  ```

- [ ] Test structured output:
  ```python
  def test_logger_json_output(caplog):
      logger = get_logger(__name__)
      logger.info("test message", extra={"key": "value"})
      assert '"message": "test message"' in caplog.text
      assert '"key": "value"' in caplog.text
  ```

**Integration Tests**:
- [ ] Test correlation ID middleware:
  ```python
  @pytest.mark.asyncio
  async def test_correlation_id_middleware(client):
      response = await client.get("/health")
      assert "X-Correlation-ID" in response.headers
  ```

- [ ] Test correlation ID propagation to Celery:
  ```python
  def test_celery_correlation_id():
      task = process_photo.delay(123, correlation_id="test-uuid")
      # Verify correlation_id in task logs
  ```

**Test Command**:
```bash
pytest tests/core/test_logging.py -v --cov=app/core/logging
```

### Performance Expectations
- Logging overhead: <1ms per log statement
- JSON serialization: <0.5ms
- Middleware overhead: <0.2ms per request

## Handover Briefing

**For the next developer:**
- **Context**: This is the foundation for observability - all logs go through this system
- **Key decisions**:
  - Using `structlog` (structured logging) instead of stdlib logging (better JSON support)
  - Correlation IDs use Python `contextvars` (thread-safe for async)
  - Log levels controlled by environment variable (12-factor app principle)
  - OpenTelemetry integration deferred to Sprint 05 (OBS cards)
- **Known limitations**:
  - Celery workers need manual correlation ID propagation (passed as task arg)
  - Log rotation handled by container orchestration (not application)
- **Next steps after this card**:
  - F005: Exception taxonomy (uses this logging system)
  - All services will import `get_logger(__name__)` for logging
  - OBS001-OBS010: Integrate with Prometheus/Loki/Grafana
- **Questions to ask**:
  - Should we add log sampling for high-volume operations? (reduce costs)
  - Should we redact sensitive fields automatically? (e.g., passwords in logs)

## Definition of Done Checklist

- [ ] Code passes all tests (pytest)
- [ ] Logging works in FastAPI app (tested via `/health`)
- [ ] Correlation IDs appear in logs
- [ ] No print() statements in app/ directory
- [ ] PR approved by 2+ reviewers
- [ ] Documentation updated (README.md with logging examples)
- [ ] Pre-commit hook blocks print() statements

## Time Tracking
- **Estimated**: 5 story points
- **Actual**: TBD (fill after completion)
- **Started**: TBD
- **Completed**: TBD

---

**Card Created**: 2025-10-09
**Last Updated**: 2025-10-09
**Card Owner**: TBD (assign during sprint planning)
