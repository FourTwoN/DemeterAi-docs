# [OBS003] Custom Trace Instrumentation

## Metadata

- **Epic**: epic-010-observability
- **Sprint**: Sprint-06
- **Priority**: `medium`
- **Complexity**: M (5 points)
- **Dependencies**: Blocked by [OBS001, OBS002]

## Description

Add custom trace spans for ML pipeline, service layer, and critical business logic paths.

## Acceptance Criteria

- [ ] ML pipeline instrumented (segmentation, detection, estimation)
- [ ] Service layer methods traced
- [ ] Span attributes include business context (photo_id, location_id)
- [ ] Parent-child relationships correct (API → Celery → Services)

## Implementation

```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

async def segment_image(photo_id: int, image_path: str):
    with tracer.start_as_current_span("ml.segmentation") as span:
        span.set_attribute("photo_id", photo_id)
        span.set_attribute("model", "yolov11m-seg")

        # ML logic here
        result = model.predict(image_path)

        span.set_attribute("segments_found", len(result))
        return result
```

## Testing

- Verify nested spans in Grafana Tempo
- Verify span attributes visible
- Test distributed tracing (API → Celery)

---
**Card Created**: 2025-10-09
