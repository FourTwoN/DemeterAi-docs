# [OBS005] Logging Correlation with Trace IDs

## Metadata

- **Epic**: epic-010-observability
- **Sprint**: Sprint-06
- **Priority**: `medium`
- **Complexity**: S (3 points)
- **Dependencies**: Blocked by [OBS001, F004]

## Description

Correlate logs with traces by injecting trace_id and span_id into log records. Enables jumping from
logs to traces in Grafana.

## Acceptance Criteria

- [ ] Every log record includes trace_id and span_id
- [ ] Logs formatted as JSON (structured logging)
- [ ] Trace context propagated across Celery tasks
- [ ] Click trace_id in Grafana Loki → jumps to Tempo trace

## Implementation

```python
import logging
from opentelemetry import trace

class TraceContextFilter(logging.Filter):
    def filter(self, record):
        span = trace.get_current_span()
        span_context = span.get_span_context()

        record.trace_id = format(span_context.trace_id, '032x')
        record.span_id = format(span_context.span_id, '016x')
        return True

# Add filter to logger
handler = logging.StreamHandler()
handler.addFilter(TraceContextFilter())
logger.addHandler(handler)

# Log format
formatter = logging.Formatter(
    '{"time":"%(asctime)s","level":"%(levelname)s","trace_id":"%(trace_id)s","span_id":"%(span_id)s","message":"%(message)s"}'
)
```

## Testing

- Verify logs include trace_id
- Verify clicking trace_id in Loki opens Tempo
- Test across API and Celery workers

---
**Card Created**: 2025-10-09
