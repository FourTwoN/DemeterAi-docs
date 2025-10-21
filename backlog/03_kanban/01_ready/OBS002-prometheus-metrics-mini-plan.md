# Mini-Plan D: Prometheus Metrics Exporting

**Created**: 2025-10-21
**Team Leader**: Orchestration Agent
**Epic**: sprint-05-deployment
**Priority**: HIGH (observability critical)
**Complexity**: 6 points (Low-Medium)

---

## Task Overview

Expose Prometheus-compatible metrics at `/metrics` endpoint, tracking API latency, request counts, ML inference time, database query performance, and system health.

---

## Current State Analysis

**Existing Monitoring**:
- Health check endpoint (/health)
- Structured JSON logging
- Correlation ID tracking

**Missing**:
- Prometheus metrics exporter
- Custom metrics (API latency, request counts)
- ML inference metrics
- Database query metrics
- System resource metrics (CPU, memory)

---

## Architecture

**Layer**: Infrastructure (Observability Layer)
**Pattern**: Prometheus Client → /metrics Endpoint → Prometheus Scraper

**Dependencies**:
- New package: `prometheus-client` (official Python client)
- Optional: `prometheus-fastapi-instrumentator` (auto-instrumentation)
- User's existing OTLP LGTM stack likely includes Prometheus

**Files to Create/Modify**:
- [ ] `app/core/metrics.py` (create - Prometheus metrics setup)
- [ ] `app/main.py` (modify - add /metrics endpoint)
- [ ] `requirements.txt` (modify - add prometheus-client)
- [ ] `.env.example` (modify - add metrics configuration)
- [ ] `tests/integration/test_metrics.py` (create - verify metrics endpoint)
- [ ] `prometheus.yml` (create - Prometheus scrape config for reference)

---

## Implementation Strategy

### Phase 1: Add Dependencies

**Add to requirements.txt**:
```
prometheus-client==0.20.0
prometheus-fastapi-instrumentator==7.0.0
```

**Why prometheus-fastapi-instrumentator**:
- Auto-instruments FastAPI (request duration, request count, response size)
- Less boilerplate code
- Includes default metrics (http_request_duration_seconds, etc.)

### Phase 2: Create app/core/metrics.py

**Custom metrics for DemeterAI**:
```python
"""Prometheus metrics for DemeterAI v2.0."""

from prometheus_client import Counter, Histogram, Gauge, Info
from prometheus_fastapi_instrumentator import Instrumentator

# ===========================================================================
# Custom Business Metrics
# ===========================================================================

# Stock operations
stock_operations_total = Counter(
    "demeter_stock_operations_total",
    "Total number of stock operations",
    ["operation_type"]  # create, update, delete, move
)

# ML inference metrics
ml_inference_duration_seconds = Histogram(
    "demeter_ml_inference_duration_seconds",
    "Duration of ML inference in seconds",
    ["model_type"],  # detection, segmentation
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
)

ml_inference_total = Counter(
    "demeter_ml_inference_total",
    "Total number of ML inferences",
    ["model_type", "status"]  # success, failure
)

# Database query metrics
db_query_duration_seconds = Histogram(
    "demeter_db_query_duration_seconds",
    "Duration of database queries in seconds",
    ["query_type"],  # select, insert, update, delete
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0]
)

# Active processing sessions
active_photo_sessions = Gauge(
    "demeter_active_photo_sessions",
    "Number of active photo processing sessions"
)

# S3 operations
s3_operations_total = Counter(
    "demeter_s3_operations_total",
    "Total number of S3 operations",
    ["operation_type", "status"]  # upload/download, success/failure
)

s3_operation_duration_seconds = Histogram(
    "demeter_s3_operation_duration_seconds",
    "Duration of S3 operations in seconds",
    ["operation_type"],
    buckets=[0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0]
)

# Application info
app_info = Info(
    "demeter_application",
    "Application version and environment information"
)

# ===========================================================================
# Setup Function
# ===========================================================================

def setup_metrics(app) -> Instrumentator:
    """Setup Prometheus metrics instrumentation for FastAPI.

    Args:
        app: FastAPI application instance

    Returns:
        Instrumentator instance (for testing/monitoring)
    """
    # Set application info
    app_info.info({
        "version": "2.0.0",
        "environment": "production",  # From settings
        "python_version": "3.12"
    })

    # Initialize instrumentator (auto-instruments FastAPI)
    instrumentator = Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=True,
        should_respect_env_var=True,
        should_instrument_requests_inprogress=True,
        excluded_handlers=["/metrics"],  # Don't track metrics endpoint
        env_var_name="ENABLE_METRICS",
        inprogress_name="demeter_requests_inprogress",
        inprogress_labels=True,
    )

    # Add default metrics
    instrumentator.instrument(app)

    # Expose /metrics endpoint
    instrumentator.expose(app, endpoint="/metrics")

    return instrumentator
```

### Phase 3: Update app/main.py

**Add metrics initialization**:
```python
from app.core.metrics import setup_metrics

# ... existing imports and app creation ...

# Setup logging (existing)
setup_logging(log_level=settings.log_level)

# Setup OpenTelemetry (from Mini-Plan B)
if settings.OTEL_ENABLED:
    setup_telemetry(app)

# Setup Prometheus metrics (NEW)
setup_metrics(app)

# Add middleware (existing)
app.add_middleware(CorrelationIdMiddleware)
```

### Phase 4: Instrument Business Logic

**Example - instrument stock service**:
```python
# In app/services/stock_service.py
from app.core.metrics import stock_operations_total

class StockService:
    async def create_batch(self, request: CreateBatchRequest) -> BatchResponse:
        """Create stock batch with metrics tracking."""
        # Track operation
        stock_operations_total.labels(operation_type="create").inc()

        # Business logic
        batch = await self.repo.create(request)

        return BatchResponse.model_validate(batch)
```

**Example - instrument ML inference**:
```python
# In app/services/ml_processing/detection_service.py
import time
from app.core.metrics import ml_inference_duration_seconds, ml_inference_total

class DetectionService:
    async def run_detection(self, image_path: str) -> list[Detection]:
        """Run YOLO detection with metrics tracking."""
        start_time = time.time()

        try:
            # Run detection
            results = self.model(image_path)

            # Track success
            duration = time.time() - start_time
            ml_inference_duration_seconds.labels(model_type="detection").observe(duration)
            ml_inference_total.labels(model_type="detection", status="success").inc()

            return results

        except Exception as e:
            # Track failure
            ml_inference_total.labels(model_type="detection", status="failure").inc()
            raise
```

### Phase 5: Create prometheus.yml (Reference)

**Sample Prometheus configuration for scraping**:
```yaml
# prometheus.yml - Sample configuration for user's Prometheus instance
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  # DemeterAI API metrics
  - job_name: 'demeterai-api'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
    scrape_interval: 10s

  # Additional targets (if Celery workers expose metrics)
  - job_name: 'demeterai-celery'
    static_configs:
      - targets: ['localhost:9091']
    scrape_interval: 15s
```

### Phase 6: Update .env.example

```bash
# =============================================================================
# Metrics Configuration
# =============================================================================
# Enable Prometheus metrics (set to false to disable)
ENABLE_METRICS=true
```

---

## Acceptance Criteria

- [ ] `prometheus-client` and `prometheus-fastapi-instrumentator` added to requirements.txt
- [ ] `app/core/metrics.py` created with custom business metrics
- [ ] `/metrics` endpoint exposed and accessible
- [ ] Default HTTP metrics instrumented (request duration, count, status codes)
- [ ] Custom metrics defined:
  - [ ] stock_operations_total (Counter)
  - [ ] ml_inference_duration_seconds (Histogram)
  - [ ] ml_inference_total (Counter)
  - [ ] db_query_duration_seconds (Histogram)
  - [ ] active_photo_sessions (Gauge)
  - [ ] s3_operations_total (Counter)
  - [ ] app_info (Info)
- [ ] Business logic instrumented (stock service, ML service)
- [ ] prometheus.yml reference created
- [ ] Integration tests pass
- [ ] Metrics visible at http://localhost:8000/metrics

---

## Testing Procedure

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start application
uvicorn app.main:app --reload

# 3. Generate test traffic
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/stock/batches

# 4. Check /metrics endpoint
curl http://localhost:8000/metrics

# Expected output (sample):
# # HELP demeter_stock_operations_total Total number of stock operations
# # TYPE demeter_stock_operations_total counter
# demeter_stock_operations_total{operation_type="create"} 5.0
# demeter_stock_operations_total{operation_type="update"} 2.0
#
# # HELP http_request_duration_seconds HTTP request duration
# # TYPE http_request_duration_seconds histogram
# http_request_duration_seconds_bucket{handler="/health",le="0.005"} 10.0
# ...

# 5. Verify metrics format (Prometheus compatible)
curl http://localhost:8000/metrics | grep "# HELP"

# 6. Run integration tests
pytest tests/integration/test_metrics.py -v

# 7. If user has Prometheus, configure scraping:
# Add job to prometheus.yml
# Restart Prometheus
# Query metrics: demeter_stock_operations_total
```

---

## Metrics Reference

**Default Metrics (from prometheus-fastapi-instrumentator)**:
- `http_request_duration_seconds` - Request duration histogram
- `http_requests_total` - Total request count
- `http_request_size_bytes` - Request size histogram
- `http_response_size_bytes` - Response size histogram
- `demeter_requests_inprogress` - Active requests gauge

**Custom Business Metrics**:
- `demeter_stock_operations_total` - Stock operation counter
- `demeter_ml_inference_duration_seconds` - ML inference latency
- `demeter_ml_inference_total` - ML inference count
- `demeter_db_query_duration_seconds` - Database query latency
- `demeter_active_photo_sessions` - Active sessions gauge
- `demeter_s3_operations_total` - S3 operation counter
- `demeter_s3_operation_duration_seconds` - S3 operation latency
- `demeter_application_info` - App version/environment

**Example Queries (PromQL)**:
```promql
# Average API request duration (last 5 minutes)
rate(http_request_duration_seconds_sum[5m]) / rate(http_request_duration_seconds_count[5m])

# Stock operations per second
rate(demeter_stock_operations_total[1m])

# 95th percentile ML inference time
histogram_quantile(0.95, rate(demeter_ml_inference_duration_seconds_bucket[5m]))

# Failed ML inferences
demeter_ml_inference_total{status="failure"}

# Requests per second by status code
sum(rate(http_requests_total[1m])) by (status)
```

---

## Performance Expectations

- Metrics collection overhead: <1ms per request
- /metrics endpoint response time: <100ms
- Memory overhead: ~50MB (Prometheus client)
- Metrics endpoint should be excluded from logging

---

## Dependencies

**Blocked By**: None (can run in parallel)
**Blocks**: Production monitoring setup

**External Dependency**: User's Prometheus instance for scraping (optional)

---

## Notes

- `/metrics` endpoint is publicly accessible (no authentication)
- For production, consider protecting /metrics with network-level security
- Prometheus scrapes /metrics every 10-15 seconds
- Metrics are stored in-memory (reset on restart)
- Consider adding Celery worker metrics if Celery app exists
- GPU utilization metrics (if GPU enabled) - use `pynvml` library
- Database connection pool metrics can be added via SQLAlchemy instrumentation

---

## Integration with User's OTLP Stack

If user's OTLP LGTM stack includes Prometheus:
1. User adds scrape config to prometheus.yml
2. Prometheus scrapes http://localhost:8000/metrics
3. Metrics visible in Grafana dashboards
4. Alerts can be configured in Prometheus

**No additional deployment needed** - user's existing stack can scrape our /metrics endpoint.
