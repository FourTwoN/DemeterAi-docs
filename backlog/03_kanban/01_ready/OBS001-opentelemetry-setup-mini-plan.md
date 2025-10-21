# Mini-Plan B: OpenTelemetry Exporter Setup (OTEL → OTLP LGTM Stack)

**Created**: 2025-10-21
**Team Leader**: Orchestration Agent
**Epic**: sprint-05-deployment
**Priority**: HIGH (observability critical for production)
**Complexity**: 10 points (Medium)

---

## Task Overview

Implement OpenTelemetry instrumentation for FastAPI, SQLAlchemy, and Celery to export traces, logs, and metrics to existing OTLP LGTM stack (user already has running stack).

---

## Current State Analysis

**Existing Observability**:
- Structured JSON logging with correlation IDs (app/core/logging.py)
- CorrelationIdMiddleware in app/main.py
- Health check endpoint at /health

**Missing**:
- OpenTelemetry SDK integration
- OTLP exporter configuration
- Automatic instrumentation for FastAPI, SQLAlchemy
- Trace/span creation
- Metrics collection
- Connection to user's existing OTLP receiver

**User Context**:
- User has OTLP LGTM stack running (docker ps shows active containers)
- Need to export to existing stack (NOT deploy new Grafana/Prometheus)
- Stack likely listening on standard OTLP ports (4317 gRPC, 4318 HTTP)

---

## Architecture

**Layer**: Infrastructure (Observability Layer)
**Pattern**: OpenTelemetry SDK → OTLP Exporter → External LGTM Stack

**Dependencies**:
- New packages: `opentelemetry-api`, `opentelemetry-sdk`, `opentelemetry-exporter-otlp`, `opentelemetry-instrumentation-fastapi`, `opentelemetry-instrumentation-sqlalchemy`, `opentelemetry-instrumentation-celery`
- Environment variables: OTEL_EXPORTER_OTLP_ENDPOINT, OTEL_SERVICE_NAME

**Files to Create/Modify**:
- [ ] `app/core/telemetry.py` (create - OpenTelemetry setup)
- [ ] `app/main.py` (modify - integrate OTEL middleware)
- [ ] `requirements.txt` (modify - add OTEL dependencies)
- [ ] `.env.example` (modify - add OTEL configuration)
- [ ] `docker-compose.yml` (modify - add OTEL env vars)
- [ ] `tests/integration/test_telemetry.py` (create - verify OTEL setup)

---

## Implementation Strategy

### Phase 1: Add Dependencies

**Add to requirements.txt**:
```
opentelemetry-api==1.25.0
opentelemetry-sdk==1.25.0
opentelemetry-exporter-otlp==1.25.0
opentelemetry-instrumentation-fastapi==0.46b0
opentelemetry-instrumentation-sqlalchemy==0.46b0
opentelemetry-instrumentation-celery==0.46b0
opentelemetry-instrumentation-requests==0.46b0
```

### Phase 2: Create app/core/telemetry.py

**Responsibilities**:
- Initialize OpenTelemetry SDK
- Configure OTLP exporter (gRPC or HTTP)
- Set up TracerProvider, MeterProvider
- Configure resource attributes (service.name, service.version)
- Export to user's OTLP endpoint

**Key Functions**:
```python
def setup_telemetry(app: FastAPI) -> None:
    """Initialize OpenTelemetry instrumentation for FastAPI."""
    # Configure resource attributes
    resource = Resource.create({
        "service.name": "demeterai-api",
        "service.version": "2.0.0",
        "deployment.environment": settings.APP_ENV
    })

    # Setup TracerProvider with OTLP exporter
    tracer_provider = TracerProvider(resource=resource)
    otlp_exporter = OTLPSpanExporter(
        endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
        # User's OTLP receiver endpoint
    )
    tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
    trace.set_tracer_provider(tracer_provider)

    # Instrument FastAPI
    FastAPIInstrumentor.instrument_app(app)

    # Instrument SQLAlchemy (for database traces)
    SQLAlchemyInstrumentor().instrument()
```

### Phase 3: Update app/core/config.py

**Add OTEL configuration**:
```python
class Settings(BaseSettings):
    # ... existing fields ...

    # OpenTelemetry configuration
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://localhost:4318"  # Default HTTP
    OTEL_SERVICE_NAME: str = "demeterai-api"
    OTEL_ENABLED: bool = True
    APP_ENV: str = "development"  # For resource attributes
```

### Phase 4: Integrate into app/main.py

**Add after app creation, before middleware registration**:
```python
from app.core.telemetry import setup_telemetry

# Setup logging (existing)
setup_logging(log_level=settings.log_level)

# Setup OpenTelemetry (NEW)
if settings.OTEL_ENABLED:
    setup_telemetry(app)

# Add middleware (existing)
app.add_middleware(CorrelationIdMiddleware)
```

### Phase 5: Update .env.example

**Add OTEL variables**:
```bash
# =============================================================================
# OpenTelemetry Configuration (Observability)
# =============================================================================
# OTLP exporter endpoint (user's existing LGTM stack)
# gRPC: http://localhost:4317
# HTTP: http://localhost:4318
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318

# Service name for trace identification
OTEL_SERVICE_NAME=demeterai-api

# Enable/disable OTEL (set to false to disable tracing)
OTEL_ENABLED=true

# Application environment (for resource attributes)
APP_ENV=development
```

### Phase 6: Integration Testing

**Create tests/integration/test_telemetry.py**:
```python
"""Test OpenTelemetry integration."""
import pytest
from opentelemetry import trace

@pytest.mark.asyncio
async def test_tracer_initialized():
    """Verify OpenTelemetry tracer is initialized."""
    tracer = trace.get_tracer(__name__)
    assert tracer is not None

@pytest.mark.asyncio
async def test_span_creation(client):
    """Verify spans are created for API requests."""
    with trace.get_tracer(__name__).start_as_current_span("test_span"):
        response = await client.get("/health")
        assert response.status_code == 200
```

---

## Acceptance Criteria

- [ ] `opentelemetry-*` dependencies added to requirements.txt
- [ ] `app/core/telemetry.py` created with OTLP exporter setup
- [ ] `app/core/config.py` updated with OTEL settings
- [ ] `app/main.py` integrated with OTEL instrumentation
- [ ] FastAPI automatically instrumented (HTTP requests traced)
- [ ] SQLAlchemy instrumented (database queries traced)
- [ ] OTLP exporter connects to user's existing stack
- [ ] Traces visible in user's Grafana/Jaeger
- [ ] Resource attributes set (service.name, service.version, environment)
- [ ] Integration tests pass
- [ ] Documentation updated in .env.example

---

## Testing Procedure

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure OTLP endpoint (user's stack)
# Edit .env:
# OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
# OTEL_ENABLED=true

# 3. Start application
uvicorn app.main:app --reload

# 4. Generate test traffic
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/stock/batches

# 5. Verify traces in user's OTLP stack
# Check Grafana/Jaeger for traces with service.name="demeterai-api"

# 6. Run integration tests
pytest tests/integration/test_telemetry.py -v

# 7. Verify no errors in logs
# Should see: "OpenTelemetry initialized successfully"
```

---

## Performance Expectations

- Overhead: <5% latency increase (traces are batched)
- OTLP export interval: 5 seconds (default)
- No blocking on export (async batch processing)
- Graceful degradation if OTLP endpoint unavailable

---

## Dependencies

**Blocked By**: Mini-Plan A (need API running in Docker)
**Blocks**: None (parallel with other tasks)

**External Dependency**: User's OTLP LGTM stack must be running

---

## Notes

- User mentioned they have OTLP LGTM stack already running
- Need to verify OTLP endpoint (likely localhost:4317 or localhost:4318)
- Default to HTTP endpoint (4318) for simplicity
- Celery instrumentation can be added later if Celery app exists
- Consider adding custom spans for ML inference tasks (future)
- OTEL SDK automatically propagates context (correlation IDs preserved)

---

## Verification Checklist

**In Application Logs**:
- [ ] "OpenTelemetry initialized successfully" message
- [ ] No OTLP exporter errors
- [ ] Trace IDs logged with correlation IDs

**In User's Grafana/Jaeger**:
- [ ] Service "demeterai-api" visible
- [ ] HTTP requests traced (GET /health, API endpoints)
- [ ] Database queries traced (SQLAlchemy spans)
- [ ] Resource attributes present (service.version, environment)
- [ ] Trace context propagated across spans
