# Epic 010: Observability & Monitoring

**Status**: Ready
**Sprint**: Sprint-05 (Week 11-12)
**Priority**: medium (production readiness)
**Total Story Points**: 50
**Total Cards**: 10 (OBS001-OBS010)

---

## Goal

Implement comprehensive observability stack with Prometheus metrics, Grafana dashboards, OpenTelemetry traces, and structured logging for production monitoring and debugging.

---

## Success Criteria

- [ ] Prometheus metrics exported from FastAPI and Celery
- [ ] Grafana dashboards for API, ML pipeline, database health
- [ ] OpenTelemetry traces show end-to-end request flow
- [ ] Structured JSON logs sent to Loki (or ELK)
- [ ] Alerting rules configured (high error rate, slow responses)
- [ ] All observability stack runs in docker-compose

---

## Cards List (10 cards, 50 points)

### Metrics (20 points)
- **OBS001**: Prometheus integration (5pts)
- **OBS002**: FastAPI metrics middleware (5pts)
- **OBS003**: Celery metrics exporter (5pts)
- **OBS004**: Custom business metrics (5pts)

### Dashboards (15 points)
- **OBS005**: Grafana setup (3pts)
- **OBS006**: API performance dashboard (5pts)
- **OBS007**: ML pipeline dashboard (5pts)
- **OBS008**: Database health dashboard (2pts)

### Tracing (10 points)
- **OBS009**: OpenTelemetry setup (OTLP export) (5pts)
- **OBS010**: Trace correlation (API → Celery → DB) (5pts)

### Alerting (5 points)
- **OBS011**: Prometheus alerting rules (3pts)
- **OBS012**: Grafana alert notifications (2pts)

---

## Dependencies

**Blocked By**: F012 (docker-compose), C001-C026 (API endpoints)
**Blocks**: Production deployment

---

## Technical Approach

**Prometheus Metrics**:
```python
from prometheus_client import Counter, Histogram, Gauge

api_requests_total = Counter(
    'api_requests_total',
    'Total API requests',
    ['method', 'endpoint', 'status']
)

ml_inference_duration = Histogram(
    'ml_inference_duration_seconds',
    'ML inference time',
    ['model_type']
)

celery_queue_length = Gauge(
    'celery_queue_length',
    'Celery queue depth',
    ['queue_name']
)
```

**OpenTelemetry Traces**:
```python
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

tracer = trace.get_tracer(__name__)

@tracer.start_as_current_span("process_photo")
async def process_photo(photo_id: int):
    with tracer.start_as_current_span("segmentation"):
        segments = await segment_image(photo_id)

    with tracer.start_as_current_span("detection"):
        detections = await detect_plants(segments)

    return detections
```

**Grafana Dashboards**:
- API latency (p50, p95, p99)
- Request rate (requests/second)
- Error rate (4xx, 5xx)
- ML inference time
- GPU utilization
- Database connections
- Celery queue depth

---

**Epic Owner**: DevOps Lead
**Created**: 2025-10-09
