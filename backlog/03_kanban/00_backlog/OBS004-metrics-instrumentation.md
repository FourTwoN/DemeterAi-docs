# [OBS004] Metrics Instrumentation

## Metadata

- **Epic**: epic-010-observability
- **Sprint**: Sprint-06
- **Priority**: `high`
- **Complexity**: M (5 points)
- **Dependencies**: Blocked by [OBS001, OBS002]

## Description

Add business metrics: request counters, latency histograms, ML inference time, GPU utilization.

## Acceptance Criteria

- [ ] HTTP request counter (by endpoint, status code)
- [ ] Request latency histogram (p50, p95, p99)
- [ ] ML inference time histogram
- [ ] Celery task duration histogram
- [ ] Database query duration histogram
- [ ] Active connections gauge

## Implementation

```python
from opentelemetry import metrics

meter = metrics.get_meter(__name__)

# Counters
http_requests = meter.create_counter(
    "http.requests",
    description="Total HTTP requests"
)

# Histograms
request_duration = meter.create_histogram(
    "http.request.duration",
    unit="ms",
    description="HTTP request duration"
)

# Usage
http_requests.add(1, {"endpoint": "/api/stock", "status_code": 200})
request_duration.record(150, {"endpoint": "/api/stock"})
```

## Testing

- Verify metrics exported to Prometheus
- Query metrics with PromQL
- Grafana dashboards display metrics

---
**Card Created**: 2025-10-09
