# [OBS002] OTLP Exporter Configuration

## Metadata

- **Epic**: epic-010-observability
- **Sprint**: Sprint-06
- **Priority**: `high`
- **Complexity**: S (3 points)
- **Dependencies**: Blocks [OBS006], Blocked by [OBS001]

## Description

Configure OTLP (OpenTelemetry Protocol) exporter to send traces and metrics to Grafana stack (
Prometheus, Tempo, Loki).

## Acceptance Criteria

- [ ] OTLP exporter configured with endpoint URL
- [ ] Traces exported to Tempo (port 4317)
- [ ] Metrics exported to Prometheus (port 9090)
- [ ] Batch export (reduce network overhead)
- [ ] Configurable via environment variables

## Implementation

```python
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.trace.export import BatchSpanProcessor

def configure_otlp_exporter():
    # Trace exporter (Tempo)
    trace_exporter = OTLPSpanExporter(
        endpoint=settings.OTLP_TRACE_ENDPOINT,
        insecure=True  # Use TLS in production
    )
    span_processor = BatchSpanProcessor(trace_exporter)
    trace.get_tracer_provider().add_span_processor(span_processor)

    # Metric exporter (Prometheus)
    metric_exporter = OTLPMetricExporter(
        endpoint=settings.OTLP_METRIC_ENDPOINT
    )
    meter_provider.add_metric_reader(PeriodicExportingMetricReader(metric_exporter))
```

## Testing

- Verify traces appear in Grafana Tempo
- Verify metrics appear in Prometheus

---
**Card Created**: 2025-10-09
