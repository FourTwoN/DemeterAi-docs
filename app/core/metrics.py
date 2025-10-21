"""Prometheus metrics collection for DemeterAI v2.0.

This module provides comprehensive business and infrastructure metrics using
prometheus_client. Metrics are organized by domain and properly labeled for
multi-dimensional analysis in Grafana/Prometheus.

Architecture:
- Module-level singleton registry for thread-safety
- Context managers and decorators for timing operations
- Conditional initialization based on ENABLE_METRICS config
- Async-safe metric collection

Usage:
    # In app/main.py
    from app.core.metrics import get_metrics_collector, setup_metrics
    setup_metrics()

    # In controllers/services
    from app.core.metrics import (
        track_api_request,
        track_stock_operation,
        track_ml_inference,
    )

    @track_api_request(endpoint="/api/stock", method="POST")
    async def create_stock():
        ...
"""

from collections.abc import Callable
from contextlib import asynccontextmanager, contextmanager
from functools import wraps
from typing import Any

from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

from app.core.config import settings

# =============================================================================
# Module-Level Registry (Thread-Safe Singleton Pattern)
# =============================================================================

_registry: CollectorRegistry | None = None
_metrics_enabled: bool = False


def get_metrics_collector() -> CollectorRegistry | None:
    """Get the global metrics collector registry.

    Returns:
        CollectorRegistry if metrics are enabled, None otherwise.
    """
    return _registry if _metrics_enabled else None


# =============================================================================
# Metric Definitions
# =============================================================================

# API Request Metrics
api_request_duration_seconds = None  # Histogram
api_request_errors_total = None  # Counter

# Stock Operations Metrics
stock_operations_total = None  # Counter
stock_batch_size = None  # Histogram

# ML Pipeline Metrics
ml_inference_duration_seconds = None  # Histogram
ml_detections_total = None  # Counter

# S3 Operations Metrics
s3_operation_duration_seconds = None  # Histogram
s3_operation_errors_total = None  # Counter

# Warehouse/Location Metrics
warehouse_location_queries_total = None  # Counter
warehouse_query_duration_seconds = None  # Histogram

# Product Metrics
product_searches_total = None  # Counter
product_search_duration_seconds = None  # Histogram

# Celery Task Metrics
celery_task_duration_seconds = None  # Histogram
celery_task_status_total = None  # Counter

# Database Metrics
db_connection_pool_size = None  # Gauge
db_connection_pool_used = None  # Gauge
db_query_duration_seconds = None  # Histogram


def setup_metrics(enable_metrics: bool | None = None) -> None:
    """Initialize Prometheus metrics if enabled.

    This function is called once during application startup. It creates
    all metric collectors and registers them with the global registry.

    Args:
        enable_metrics: Override for ENABLE_METRICS config (default: None uses config)
    """
    global _registry, _metrics_enabled
    global api_request_duration_seconds, api_request_errors_total
    global stock_operations_total, stock_batch_size
    global ml_inference_duration_seconds, ml_detections_total
    global s3_operation_duration_seconds, s3_operation_errors_total
    global warehouse_location_queries_total, warehouse_query_duration_seconds
    global product_searches_total, product_search_duration_seconds
    global celery_task_duration_seconds, celery_task_status_total
    global db_connection_pool_size, db_connection_pool_used, db_query_duration_seconds

    # Check if metrics should be enabled
    _metrics_enabled = (
        enable_metrics if enable_metrics is not None else getattr(settings, "ENABLE_METRICS", True)
    )

    if not _metrics_enabled:
        return

    # Create registry
    _registry = CollectorRegistry()

    # =============================================================================
    # API Request Metrics
    # =============================================================================

    api_request_duration_seconds = Histogram(
        name="demeter_api_request_duration_seconds",
        documentation="API request latency in seconds",
        labelnames=["method", "endpoint", "status"],
        buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
        registry=_registry,
    )

    api_request_errors_total = Counter(
        name="demeter_api_request_errors_total",
        documentation="Total API request errors by endpoint and error type",
        labelnames=["method", "endpoint", "error_type", "status"],
        registry=_registry,
    )

    # =============================================================================
    # Stock Operations Metrics
    # =============================================================================

    stock_operations_total = Counter(
        name="demeter_stock_operations_total",
        documentation="Total stock operations by type (create, update, delete)",
        labelnames=["operation", "product_type", "status"],
        registry=_registry,
    )

    stock_batch_size = Histogram(
        name="demeter_stock_batch_size",
        documentation="Size of stock batches in operations",
        labelnames=["operation", "product_type"],
        buckets=(1, 5, 10, 25, 50, 100, 250, 500, 1000, 5000),
        registry=_registry,
    )

    # =============================================================================
    # ML Pipeline Metrics
    # =============================================================================

    ml_inference_duration_seconds = Histogram(
        name="demeter_ml_inference_duration_seconds",
        documentation="ML inference time in seconds",
        labelnames=["model_type", "batch_size_bucket"],
        buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0),
        registry=_registry,
    )

    ml_detections_total = Counter(
        name="demeter_ml_detections_total",
        documentation="Total ML detections by confidence level",
        labelnames=["model_type", "confidence_bucket"],
        registry=_registry,
    )

    # =============================================================================
    # S3 Operations Metrics
    # =============================================================================

    s3_operation_duration_seconds = Histogram(
        name="demeter_s3_operation_duration_seconds",
        documentation="S3 operation latency in seconds (upload/download)",
        labelnames=["operation", "bucket"],
        buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0),
        registry=_registry,
    )

    s3_operation_errors_total = Counter(
        name="demeter_s3_operation_errors_total",
        documentation="Total S3 operation errors",
        labelnames=["operation", "bucket", "error_type"],
        registry=_registry,
    )

    # =============================================================================
    # Warehouse/Location Metrics
    # =============================================================================

    warehouse_location_queries_total = Counter(
        name="demeter_warehouse_location_queries_total",
        documentation="Total warehouse location queries by hierarchy level",
        labelnames=["level", "operation"],
        registry=_registry,
    )

    warehouse_query_duration_seconds = Histogram(
        name="demeter_warehouse_query_duration_seconds",
        documentation="Warehouse query duration in seconds",
        labelnames=["level", "operation"],
        buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
        registry=_registry,
    )

    # =============================================================================
    # Product Search Metrics
    # =============================================================================

    product_searches_total = Counter(
        name="demeter_product_searches_total",
        documentation="Total product searches by type",
        labelnames=["search_type", "result_count_bucket"],
        registry=_registry,
    )

    product_search_duration_seconds = Histogram(
        name="demeter_product_search_duration_seconds",
        documentation="Product search duration in seconds",
        labelnames=["search_type"],
        buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
        registry=_registry,
    )

    # =============================================================================
    # Celery Task Metrics
    # =============================================================================

    celery_task_duration_seconds = Histogram(
        name="demeter_celery_task_duration_seconds",
        documentation="Celery task execution duration in seconds",
        labelnames=["task_name", "queue"],
        buckets=(1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0, 1800.0, 3600.0),
        registry=_registry,
    )

    celery_task_status_total = Counter(
        name="demeter_celery_task_status_total",
        documentation="Total Celery task executions by status",
        labelnames=["task_name", "status", "queue"],
        registry=_registry,
    )

    # =============================================================================
    # Database Metrics
    # =============================================================================

    db_connection_pool_size = Gauge(
        name="demeter_db_connection_pool_size",
        documentation="Current database connection pool size",
        registry=_registry,
    )

    db_connection_pool_used = Gauge(
        name="demeter_db_connection_pool_used",
        documentation="Number of database connections currently in use",
        registry=_registry,
    )

    db_query_duration_seconds = Histogram(
        name="demeter_db_query_duration_seconds",
        documentation="Database query duration in seconds",
        labelnames=["operation", "table"],
        buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5),
        registry=_registry,
    )


# =============================================================================
# Context Managers and Decorators
# =============================================================================


@contextmanager
def time_operation(metric: Histogram | None, **labels: str):
    """Context manager for timing synchronous operations.

    Usage:
        with time_operation(api_request_duration_seconds, method="GET", endpoint="/health"):
            # ... operation ...

    Args:
        metric: Histogram metric to record to (None = no-op)
        **labels: Label values for the metric
    """
    if metric is None or not _metrics_enabled:
        yield
        return

    with metric.labels(**labels).time():
        yield


@asynccontextmanager
async def time_operation_async(metric: Histogram | None, **labels: str):
    """Async context manager for timing async operations.

    Usage:
        async with time_operation_async(ml_inference_duration_seconds, model_type="yolo"):
            # ... async operation ...

    Args:
        metric: Histogram metric to record to (None = no-op)
        **labels: Label values for the metric
    """
    if metric is None or not _metrics_enabled:
        yield
        return

    # Manual timing for async operations
    import time

    start_time = time.perf_counter()
    try:
        yield
    finally:
        duration = time.perf_counter() - start_time
        metric.labels(**labels).observe(duration)


def track_api_request(endpoint: str, method: str = "GET"):
    """Decorator to track API request metrics.

    Usage:
        @track_api_request(endpoint="/api/stock", method="POST")
        async def create_stock():
            ...

    Args:
        endpoint: API endpoint path
        method: HTTP method
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            if not _metrics_enabled or api_request_duration_seconds is None:
                return await func(*args, **kwargs)

            import time

            start_time = time.perf_counter()
            status = "success"

            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status = "error"
                if api_request_errors_total is not None:
                    api_request_errors_total.labels(
                        method=method,
                        endpoint=endpoint,
                        error_type=type(e).__name__,
                        status="500",
                    ).inc()
                raise
            finally:
                duration = time.perf_counter() - start_time
                api_request_duration_seconds.labels(
                    method=method, endpoint=endpoint, status=status
                ).observe(duration)

        return wrapper

    return decorator


def track_stock_operation(operation: str, product_type: str = "unknown"):
    """Decorator to track stock operation metrics.

    Usage:
        @track_stock_operation(operation="create", product_type="plant")
        async def create_stock_batch():
            ...

    Args:
        operation: Operation type (create, update, delete)
        product_type: Type of product
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            if not _metrics_enabled or stock_operations_total is None:
                return await func(*args, **kwargs)

            status = "success"
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception:
                status = "error"
                raise
            finally:
                stock_operations_total.labels(
                    operation=operation, product_type=product_type, status=status
                ).inc()

        return wrapper

    return decorator


def track_ml_inference(model_type: str = "yolo"):
    """Decorator to track ML inference metrics.

    Usage:
        @track_ml_inference(model_type="yolo")
        async def run_detection():
            ...

    Args:
        model_type: Type of ML model
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            if not _metrics_enabled or ml_inference_duration_seconds is None:
                return await func(*args, **kwargs)

            import time

            start_time = time.perf_counter()
            batch_size_bucket = "unknown"

            try:
                result = await func(*args, **kwargs)

                # Try to determine batch size from result
                if hasattr(result, "__len__"):
                    size = len(result)
                    if size <= 10:
                        batch_size_bucket = "1-10"
                    elif size <= 50:
                        batch_size_bucket = "11-50"
                    elif size <= 100:
                        batch_size_bucket = "51-100"
                    else:
                        batch_size_bucket = "100+"

                return result
            finally:
                duration = time.perf_counter() - start_time
                ml_inference_duration_seconds.labels(
                    model_type=model_type, batch_size_bucket=batch_size_bucket
                ).observe(duration)

        return wrapper

    return decorator


# =============================================================================
# Metric Recording Functions
# =============================================================================


def record_s3_operation(operation: str, bucket: str, duration: float, success: bool = True) -> None:
    """Record S3 operation metrics.

    Args:
        operation: Operation type (upload, download)
        bucket: S3 bucket name
        duration: Operation duration in seconds
        success: Whether operation succeeded
    """
    if not _metrics_enabled or s3_operation_duration_seconds is None:
        return

    s3_operation_duration_seconds.labels(operation=operation, bucket=bucket).observe(duration)

    if not success and s3_operation_errors_total is not None:
        s3_operation_errors_total.labels(
            operation=operation, bucket=bucket, error_type="unknown"
        ).inc()


def record_warehouse_query(level: str, operation: str, duration: float) -> None:
    """Record warehouse location query metrics.

    Args:
        level: Hierarchy level (warehouse, area, location, bin)
        operation: Query operation (get, list, search)
        duration: Query duration in seconds
    """
    if not _metrics_enabled:
        return

    if warehouse_location_queries_total is not None:
        warehouse_location_queries_total.labels(level=level, operation=operation).inc()

    if warehouse_query_duration_seconds is not None:
        warehouse_query_duration_seconds.labels(level=level, operation=operation).observe(duration)


def record_product_search(search_type: str, result_count: int, duration: float) -> None:
    """Record product search metrics.

    Args:
        search_type: Type of search (code, name, category)
        result_count: Number of results returned
        duration: Search duration in seconds
    """
    if not _metrics_enabled:
        return

    # Bucket result count
    if result_count == 0:
        bucket = "0"
    elif result_count <= 10:
        bucket = "1-10"
    elif result_count <= 50:
        bucket = "11-50"
    else:
        bucket = "50+"

    if product_searches_total is not None:
        product_searches_total.labels(search_type=search_type, result_count_bucket=bucket).inc()

    if product_search_duration_seconds is not None:
        product_search_duration_seconds.labels(search_type=search_type).observe(duration)


def record_celery_task(
    task_name: str, queue: str, duration: float, status: str = "success"
) -> None:
    """Record Celery task execution metrics.

    Args:
        task_name: Name of the Celery task
        queue: Queue name
        duration: Task execution duration in seconds
        status: Task status (success, failure, retry)
    """
    if not _metrics_enabled:
        return

    if celery_task_duration_seconds is not None:
        celery_task_duration_seconds.labels(task_name=task_name, queue=queue).observe(duration)

    if celery_task_status_total is not None:
        celery_task_status_total.labels(task_name=task_name, status=status, queue=queue).inc()


def update_db_pool_metrics(pool_size: int, used_connections: int) -> None:
    """Update database connection pool metrics.

    Args:
        pool_size: Total connection pool size
        used_connections: Number of connections currently in use
    """
    if not _metrics_enabled:
        return

    if db_connection_pool_size is not None:
        db_connection_pool_size.set(pool_size)

    if db_connection_pool_used is not None:
        db_connection_pool_used.set(used_connections)


def record_db_query(operation: str, table: str, duration: float) -> None:
    """Record database query metrics.

    Args:
        operation: Query operation (select, insert, update, delete)
        table: Database table name
        duration: Query duration in seconds
    """
    if not _metrics_enabled or db_query_duration_seconds is None:
        return

    db_query_duration_seconds.labels(operation=operation, table=table).observe(duration)


# =============================================================================
# Metrics Export
# =============================================================================


def get_metrics_text() -> bytes:
    """Get metrics in Prometheus text format.

    Returns:
        Prometheus-formatted metrics as bytes
    """
    if not _metrics_enabled or _registry is None:
        return b""

    return generate_latest(_registry)
