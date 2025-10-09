# [OBS001] OpenTelemetry Setup

## Metadata
- **Epic**: epic-010-observability
- **Sprint**: Sprint-06
- **Status**: `backlog`
- **Priority**: `high`
- **Complexity**: M (5 story points)
- **Area**: `observability`
- **Assignee**: TBD
- **Dependencies**:
  - Blocks: [OBS002, OBS003, OBS004, OBS005]
  - Blocked by: [F002]

## Related Documentation
- **Engineering Plan**: ../../engineering_plan/02_technology_stack.md (Monitoring section)
- **Deployment**: ../../engineering_plan/deployment/README.md

## Description

Initialize OpenTelemetry SDK for distributed tracing, metrics, and logging correlation. OpenTelemetry provides vendor-neutral observability (export to Prometheus, Grafana, Jaeger, or commercial APMs).

**What**: Install and configure OpenTelemetry SDK with automatic FastAPI and Celery instrumentation.

**Why**: Gain visibility into request flows across API → Celery → Database. Essential for debugging production issues and performance optimization.

**Context**: Foundation for all observability features (traces, metrics, logs).

## Acceptance Criteria

- [ ] **AC1**: OpenTelemetry dependencies installed:
  ```txt
  opentelemetry-api==1.22.0
  opentelemetry-sdk==1.22.0
  opentelemetry-instrumentation-fastapi==0.43b0
  opentelemetry-instrumentation-celery==0.43b0
  opentelemetry-instrumentation-sqlalchemy==0.43b0
  opentelemetry-exporter-otlp==1.22.0
  ```

- [ ] **AC2**: OpenTelemetry initialization in `app/core/observability.py`:
  ```python
  from opentelemetry import trace, metrics
  from opentelemetry.sdk.trace import TracerProvider
  from opentelemetry.sdk.metrics import MeterProvider

  def init_observability():
      # Initialize tracer
      # Initialize meter
      # Configure resource (service name, version)
  ```

- [ ] **AC3**: Service identification:
  ```python
  Resource(attributes={
      "service.name": "demeterai-api",
      "service.version": "2.0.0",
      "deployment.environment": "production"
  })
  ```

- [ ] **AC4**: Automatic instrumentation:
  - FastAPI: HTTP request traces
  - Celery: Task execution traces
  - SQLAlchemy: Database query traces

- [ ] **AC5**: Call `init_observability()` on app startup:
  ```python
  @app.on_event("startup")
  async def startup():
      init_observability()
  ```

## Technical Implementation Notes

### Architecture
- Layer: Core (Infrastructure)
- Pattern: Initialization hook
- Dependencies: opentelemetry-* packages

### Code Hints

**app/core/observability.py:**
```python
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.celery import CeleryInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

def init_observability():
    """
    Initialize OpenTelemetry SDK for tracing and metrics.

    Automatic instrumentation for:
    - FastAPI (HTTP requests)
    - Celery (async tasks)
    - SQLAlchemy (database queries)
    """
    # Define service resource
    resource = Resource(attributes={
        "service.name": settings.SERVICE_NAME,
        "service.version": settings.SERVICE_VERSION,
        "deployment.environment": settings.ENVIRONMENT,
    })

    # Initialize tracer provider
    tracer_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(tracer_provider)

    # Initialize meter provider
    meter_provider = MeterProvider(resource=resource)
    metrics.set_meter_provider(meter_provider)

    logger.info(f"OpenTelemetry initialized for service: {settings.SERVICE_NAME}")

def instrument_app(app):
    """
    Apply automatic instrumentation to FastAPI app.

    Call after app creation: instrument_app(app)
    """
    FastAPIInstrumentor.instrument_app(app)
    logger.info("FastAPI instrumented for tracing")

def instrument_celery(celery_app):
    """
    Apply automatic instrumentation to Celery app.

    Call in celery_app.py after Celery initialization.
    """
    CeleryInstrumentor().instrument()
    logger.info("Celery instrumented for tracing")

def instrument_database(engine):
    """
    Apply automatic instrumentation to SQLAlchemy engine.

    Call after engine creation.
    """
    SQLAlchemyInstrumentor().instrument(engine=engine)
    logger.info("SQLAlchemy instrumented for tracing")
```

**app/main.py integration:**
```python
from fastapi import FastAPI
from app.core.observability import init_observability, instrument_app

app = FastAPI(title="DemeterAI v2.0")

@app.on_event("startup")
async def startup():
    # Initialize OpenTelemetry
    init_observability()

    # Instrument FastAPI
    instrument_app(app)

@app.get("/health")
async def health():
    return {"status": "healthy"}
```

**app/core/config.py additions:**
```python
class Settings(BaseSettings):
    # Observability
    SERVICE_NAME: str = "demeterai-api"
    SERVICE_VERSION: str = "2.0.0"
    ENVIRONMENT: str = "production"  # dev, staging, production
```

### Testing Requirements

**Unit Tests** (`tests/core/test_observability.py`):
- [ ] Test init_observability sets up providers
- [ ] Test tracer provider configured with correct resource
- [ ] Test meter provider configured with correct resource

**Integration Tests** (`tests/test_tracing.py`):
- [ ] Test FastAPI request creates trace span
- [ ] Test span includes service.name attribute
- [ ] Test nested spans (API → service → repo)

**Test Example**:
```python
from opentelemetry import trace
from app.core.observability import init_observability

def test_observability_init():
    init_observability()

    tracer = trace.get_tracer(__name__)
    assert tracer is not None

def test_fastapi_creates_trace(client):
    response = client.get("/health")
    assert response.status_code == 200

    # Verify trace was created (check exporter or in-memory spans)
```

### Performance Expectations
- Overhead per request: <5ms (tracing)
- Memory overhead: ~50MB (trace buffers)
- CPU overhead: <2%

## Handover Briefing

**For the next developer:**
- **Context**: OpenTelemetry is the CNCF standard for observability
- **Key decisions**:
  - Using OTLP exporter (next card OBS002)
  - Automatic instrumentation (zero code changes in business logic)
  - Export to Prometheus (metrics) + Tempo (traces) + Loki (logs)
- **Next steps after this card**:
  - OBS002: Configure OTLP exporter (send data to Grafana stack)
  - OBS003: Add custom trace spans for ML pipeline
  - OBS004: Add business metrics (counters, histograms)

## Definition of Done Checklist

- [ ] Code passes all tests
- [ ] OpenTelemetry SDK initialized on startup
- [ ] FastAPI, Celery, SQLAlchemy auto-instrumented
- [ ] Service resource configured (name, version, environment)
- [ ] Test coverage >70%
- [ ] PR approved by 2+ reviewers
- [ ] Documentation updated

## Time Tracking
- **Estimated**: 5 story points
- **Actual**: TBD
- **Started**: TBD
- **Completed**: TBD

---

**Card Created**: 2025-10-09
**Last Updated**: 2025-10-09
**Card Owner**: TBD
