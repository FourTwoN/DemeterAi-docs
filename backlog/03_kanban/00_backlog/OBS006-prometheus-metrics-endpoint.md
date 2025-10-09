# [OBS006] Prometheus Metrics Endpoint

## Metadata
- **Epic**: epic-010-observability
- **Sprint**: Sprint-06
- **Priority**: `high`
- **Complexity**: S (2 points)
- **Dependencies**: Blocked by [OBS002, OBS004]

## Description
Expose `/metrics` endpoint for Prometheus scraping. Includes default metrics (CPU, memory) + custom business metrics.

## Acceptance Criteria
- [ ] GET /metrics endpoint returns Prometheus format
- [ ] Includes default metrics (process_cpu_seconds, http_requests_total)
- [ ] Includes custom metrics from OBS004
- [ ] Prometheus scrapes endpoint every 15 seconds

## Implementation
```python
from prometheus_client import generate_latest, REGISTRY
from starlette.responses import Response

@app.get("/metrics")
async def metrics():
    return Response(
        content=generate_latest(REGISTRY),
        media_type="text/plain"
    )
```

**prometheus.yml config:**
```yaml
scrape_configs:
  - job_name: 'demeterai-api'
    scrape_interval: 15s
    static_configs:
      - targets: ['api:8000']
```

## Testing
- Verify GET /metrics returns data
- Verify Prometheus scrapes successfully
- Query metrics in Prometheus UI

---
**Card Created**: 2025-10-09
