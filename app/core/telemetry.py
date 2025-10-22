"""OpenTelemetry instrumentation and tracing configuration.

This module provides complete OpenTelemetry integration for DemeterAI v2.0,
including distributed tracing, metrics collection, and automatic instrumentation
for FastAPI, SQLAlchemy, and Celery.

Architecture:
- OTLP exporter to user's existing LGTM stack (Grafana/Loki/Tempo/Mimir)
- Trace context propagation across services (API → Celery → Database)
- Batch span processor for performance
- Automatic correlation with structured logging (trace_id, span_id)

Key features:
- Auto-instrumentation for FastAPI, SQLAlchemy, Celery, requests, redis
- OTLP HTTP/gRPC exporter to localhost:4318
- Trace context propagation (W3C Trace Context standard)
- Resource attributes (service.name, service.version, deployment.environment)
- Batch span processor (performance optimization)
- Metric collection with OTLP exporter
- Thread-safe initialization

Usage:
    from app.core.telemetry import setup_telemetry

    # In app/main.py startup
    tracer_provider, metric_reader, meter_provider = setup_telemetry()

    # Tracer and meter are automatically registered globally
    # All instrumented libraries will use them automatically

Integration with LGTM stack:
    - Traces → Grafana Tempo (via OTLP)
    - Metrics → Prometheus/Mimir (via OTLP)
    - Logs → Loki (structured JSON with trace_id correlation)

Environment Variables:
    OTEL_ENABLED: Enable/disable OpenTelemetry (default: True)
    OTEL_EXPORTER_OTLP_ENDPOINT: OTLP endpoint (default: http://localhost:4318)
    OTEL_SERVICE_NAME: Service name (default: demeterai-api)
    APP_ENV: Environment name (default: development)
"""

from opentelemetry import metrics, trace  # type: ignore[import-not-found]
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (  # type: ignore[import-not-found]
    OTLPMetricExporter,
)
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (  # type: ignore[import-not-found]
    OTLPSpanExporter,
)
from opentelemetry.instrumentation.celery import (  # type: ignore[import-not-found]
    CeleryInstrumentor,
)
from opentelemetry.instrumentation.fastapi import (  # type: ignore[import-not-found]
    FastAPIInstrumentor,
)
from opentelemetry.instrumentation.redis import RedisInstrumentor  # type: ignore[import-not-found]
from opentelemetry.instrumentation.requests import (  # type: ignore[import-not-found]
    RequestsInstrumentor,
)
from opentelemetry.instrumentation.sqlalchemy import (  # type: ignore[import-not-found]
    SQLAlchemyInstrumentor,
)
from opentelemetry.sdk.metrics import MeterProvider  # type: ignore[import-not-found]
from opentelemetry.sdk.metrics.export import (  # type: ignore[import-not-found]
    PeriodicExportingMetricReader,
)
from opentelemetry.sdk.resources import Resource  # type: ignore[import-not-found]
from opentelemetry.sdk.trace import TracerProvider  # type: ignore[import-not-found]
from opentelemetry.sdk.trace.export import BatchSpanProcessor  # type: ignore[import-not-found]

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def _create_resource() -> Resource:
    """Create OpenTelemetry resource with service attributes.

    Resource attributes provide metadata about the service for all telemetry
    data (traces, metrics, logs). This enables filtering and grouping in
    observability backends.

    Returns:
        Resource: OpenTelemetry resource with service identification

    Example attributes:
        - service.name: "demeterai-api"
        - service.version: "2.0.0"
        - deployment.environment: "production"
        - service.namespace: "demeterai"
    """
    from collections.abc import Mapping

    resource_attributes: Mapping[str, str] = {
        "service.name": settings.OTEL_SERVICE_NAME,
        "service.version": "2.0.0",
        "deployment.environment": settings.APP_ENV,
        "service.namespace": "demeterai",
    }

    return Resource.create(resource_attributes)


def _setup_trace_provider(resource: Resource) -> TracerProvider:
    """Configure OpenTelemetry trace provider with OTLP exporter.

    Sets up distributed tracing with:
    - OTLP exporter to user's LGTM stack (Grafana Tempo)
    - Batch span processor for performance (batches spans before export)
    - W3C Trace Context propagation (standard for trace context across services)

    Args:
        resource: OpenTelemetry resource with service metadata

    Returns:
        TracerProvider: Configured tracer provider registered globally

    Architecture:
        API Request → FastAPI middleware → Service → Repository → Database
             ↓              ↓                  ↓           ↓           ↓
        root span     http.route span    service span  db span   query span
             └─────────────── trace_id (propagated) ──────────────┘
    """
    # Create OTLP exporter (gRPC to Grafana Tempo)
    otlp_exporter = OTLPSpanExporter(
        endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
        insecure=True,  # Use HTTP (not HTTPS) for local LGTM stack
    )

    # Batch span processor (performance: batch spans before export)
    span_processor = BatchSpanProcessor(
        otlp_exporter,
        max_queue_size=2048,  # Max spans in queue before dropping
        schedule_delay_millis=5000,  # Export every 5 seconds
        max_export_batch_size=512,  # Max spans per export batch
    )

    # Create tracer provider
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(span_processor)

    # Register globally (all instrumentations will use this)
    trace.set_tracer_provider(tracer_provider)

    logger.info(
        "Trace provider configured",
        endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
        service_name=settings.OTEL_SERVICE_NAME,
        environment=settings.APP_ENV,
    )

    return tracer_provider


def _setup_metrics_provider(
    resource: Resource,
) -> tuple[PeriodicExportingMetricReader, MeterProvider]:
    """Configure OpenTelemetry metrics provider with OTLP exporter.

    Sets up metrics collection with:
    - OTLP metric exporter to user's LGTM stack (Prometheus/Mimir)
    - Periodic exporter (exports metrics every 60 seconds)
    - Delta temporality (only send metric deltas, not cumulative)

    Args:
        resource: OpenTelemetry resource with service metadata

    Returns:
        Tuple of (PeriodicExportingMetricReader, MeterProvider)

    Metrics collected:
        - FastAPI: request count, duration, status codes
        - SQLAlchemy: query count, duration, connection pool stats
        - Celery: task count, duration, success/failure rates
        - Custom business metrics (via app.core.metrics)
    """
    # Create OTLP metric exporter (gRPC to Prometheus/Mimir)
    otlp_metric_exporter = OTLPMetricExporter(
        endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
        insecure=True,  # Use HTTP (not HTTPS) for local LGTM stack
    )

    # Periodic exporter (export metrics every 60 seconds)
    metric_reader = PeriodicExportingMetricReader(
        otlp_metric_exporter,
        export_interval_millis=60000,  # 60 seconds
    )

    # Create meter provider
    meter_provider = MeterProvider(
        resource=resource,
        metric_readers=[metric_reader],
    )

    # Register globally (all instrumentations will use this)
    metrics.set_meter_provider(meter_provider)

    logger.info(
        "Metrics provider configured",
        endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
        export_interval_seconds=60,
    )

    return metric_reader, meter_provider


def _instrument_libraries() -> None:
    """Enable automatic instrumentation for all supported libraries.

    Auto-instrumentation wraps library calls with OpenTelemetry spans,
    automatically capturing:
    - FastAPI: HTTP requests, routes, middleware
    - SQLAlchemy: Database queries, connection pool
    - Celery: Task execution, retries, failures
    - Redis: Cache operations
    - Requests: HTTP client calls

    This requires NO code changes - instrumentation is automatic.

    Thread Safety:
        All instrumentors are thread-safe and can be called once at startup.
        They use global state internally but are designed for this pattern.
    """
    # FastAPI instrumentation (HTTP server traces)
    FastAPIInstrumentor().instrument()
    logger.debug("FastAPI instrumentation enabled")

    # SQLAlchemy instrumentation (database query traces)
    SQLAlchemyInstrumentor().instrument()
    logger.debug("SQLAlchemy instrumentation enabled")

    # Celery instrumentation (async task traces)
    CeleryInstrumentor().instrument()
    logger.debug("Celery instrumentation enabled")

    # Redis instrumentation (cache operation traces)
    RedisInstrumentor().instrument()
    logger.debug("Redis instrumentation enabled")

    # Requests instrumentation (HTTP client traces)
    RequestsInstrumentor().instrument()
    logger.debug("Requests instrumentation enabled")

    logger.info("All library instrumentations enabled")


def setup_telemetry() -> tuple[TracerProvider, PeriodicExportingMetricReader, MeterProvider] | None:
    """Initialize OpenTelemetry SDK with OTLP exporters and auto-instrumentation.

    This is the main entry point called from app/main.py at startup.
    Sets up complete observability stack:
    - Distributed tracing (Grafana Tempo)
    - Metrics collection (Prometheus/Mimir)
    - Automatic instrumentation (FastAPI, SQLAlchemy, Celery, etc.)

    Returns:
        Tuple of (TracerProvider, MetricReader, MeterProvider) if enabled,
        None if OTEL_ENABLED=False

    Environment Configuration:
        OTEL_ENABLED: Enable/disable OpenTelemetry (default: True)
        OTEL_EXPORTER_OTLP_ENDPOINT: OTLP endpoint (default: http://localhost:4318)
        OTEL_SERVICE_NAME: Service name (default: demeterai-api)
        APP_ENV: Environment (default: development)

    Example:
        >>> # In app/main.py
        >>> from app.core.telemetry import setup_telemetry
        >>>
        >>> # Setup before creating FastAPI app
        >>> setup_telemetry()
        >>>
        >>> # FastAPI app creation (will be auto-instrumented)
        >>> app = FastAPI(title="DemeterAI v2.0")

    Integration with Structured Logging:
        The logging.py module automatically extracts trace_id and span_id
        from OpenTelemetry context and adds them to structured logs.
        This enables correlation between traces and logs in Grafana.

    Architecture:
        ┌─────────────────────────────────────────────────────┐
        │ FastAPI App                                         │
        │  ├─ HTTP Request (trace context extracted)          │
        │  ├─ Service Layer (spans created automatically)     │
        │  ├─ Repository Layer (DB queries traced)            │
        │  └─ Celery Task (trace context propagated)          │
        └─────────────────────────────────────────────────────┘
                               ↓
        ┌─────────────────────────────────────────────────────┐
        │ OpenTelemetry SDK                                   │
        │  ├─ TracerProvider (manages trace exporters)        │
        │  ├─ MeterProvider (manages metric exporters)        │
        │  └─ BatchSpanProcessor (batches for performance)    │
        └─────────────────────────────────────────────────────┘
                               ↓
        ┌─────────────────────────────────────────────────────┐
        │ OTLP Exporters (gRPC to localhost:4318)             │
        │  ├─ Trace Exporter → Grafana Tempo                  │
        │  └─ Metric Exporter → Prometheus/Mimir              │
        └─────────────────────────────────────────────────────┘
                               ↓
        ┌─────────────────────────────────────────────────────┐
        │ LGTM Stack (User's existing observability)          │
        │  ├─ Tempo: Distributed traces                       │
        │  ├─ Prometheus/Mimir: Metrics                       │
        │  ├─ Loki: Structured logs (with trace_id)           │
        │  └─ Grafana: Unified visualization                  │
        └─────────────────────────────────────────────────────┘
    """
    # Check if OpenTelemetry is enabled
    if not settings.OTEL_ENABLED:
        logger.info("OpenTelemetry disabled (OTEL_ENABLED=False)")
        return None

    try:
        logger.info(
            "Initializing OpenTelemetry",
            service_name=settings.OTEL_SERVICE_NAME,
            endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
            environment=settings.APP_ENV,
        )

        # Create resource (service identification)
        resource = _create_resource()

        # Setup trace provider (distributed tracing)
        tracer_provider = _setup_trace_provider(resource)

        # Setup metrics provider (metrics collection)
        metric_reader, meter_provider = _setup_metrics_provider(resource)

        # Enable automatic instrumentation
        _instrument_libraries()

        logger.info(
            "OpenTelemetry initialized successfully",
            service_name=settings.OTEL_SERVICE_NAME,
            instrumentations=["FastAPI", "SQLAlchemy", "Celery", "Redis", "Requests"],
        )

        return tracer_provider, metric_reader, meter_provider

    except Exception as e:
        logger.error(
            "Failed to initialize OpenTelemetry",
            error=str(e),
            exc_info=True,
        )
        # Don't crash the application if telemetry setup fails
        return None


def get_tracer(name: str) -> trace.Tracer:
    """Get a tracer instance for manual instrumentation.

    Use this when you need to create custom spans beyond auto-instrumentation.
    Most of the time, auto-instrumentation is sufficient.

    Args:
        name: Tracer name (typically __name__ of the calling module)

    Returns:
        Tracer: OpenTelemetry tracer instance

    Example:
        >>> from app.core.telemetry import get_tracer
        >>>
        >>> tracer = get_tracer(__name__)
        >>>
        >>> async def complex_business_logic():
        >>>     with tracer.start_as_current_span("business_logic"):
        >>>         # Your code here
        >>>         result = await some_operation()
        >>>         return result
    """
    return trace.get_tracer(name)


def get_meter(name: str) -> metrics.Meter:
    """Get a meter instance for custom metrics.

    Use this when you need to record custom business metrics beyond
    auto-instrumentation metrics.

    Args:
        name: Meter name (typically __name__ of the calling module)

    Returns:
        Meter: OpenTelemetry meter instance

    Example:
        >>> from app.core.telemetry import get_meter
        >>>
        >>> meter = get_meter(__name__)
        >>> photo_counter = meter.create_counter(
        ...     "demeter.photos.processed",
        ...     description="Number of photos processed by ML pipeline"
        ... )
        >>>
        >>> # In your service
        >>> photo_counter.add(1, {"product": "strawberry", "location": "warehouse_1"})
    """
    return metrics.get_meter(name)
