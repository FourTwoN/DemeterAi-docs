# [OBS009] Grafana Dashboard JSON

## Metadata
- **Epic**: epic-010-observability
- **Sprint**: Sprint-07
- **Priority**: `medium`
- **Complexity**: M (5 points)
- **Dependencies**: Blocked by [OBS004, OBS006, DEP010]

## Description
Create pre-built Grafana dashboards (JSON) for API performance, ML pipeline metrics, database health, and Celery workers.

## Acceptance Criteria
- [ ] **Dashboard 1: API Performance**
  - Request rate (req/sec)
  - Latency (p50, p95, p99)
  - Error rate (4xx, 5xx)
  - Top endpoints by latency

- [ ] **Dashboard 2: ML Pipeline**
  - Inference time (segmentation, detection)
  - Photos processed per hour
  - GPU utilization (if available)
  - Task queue depth

- [ ] **Dashboard 3: Database Health**
  - Connection pool usage
  - Query duration (p95, p99)
  - Slow queries (>1s)
  - Active connections

- [ ] **Dashboard 4: Celery Workers**
  - Active tasks
  - Task duration by type
  - Failed tasks
  - Worker status

- [ ] Dashboards versioned in `grafana/dashboards/`

## Implementation
Create JSON files:
```
grafana/dashboards/
├── api_performance.json
├── ml_pipeline.json
├── database_health.json
└── celery_workers.json
```

**Example panel (request rate):**
```json
{
  "title": "Request Rate",
  "targets": [
    {
      "expr": "rate(http_requests_total[5m])",
      "legendFormat": "{{endpoint}}"
    }
  ],
  "type": "graph"
}
```

## Testing
- Import dashboards into Grafana
- Verify all panels render data
- Test drill-down links

---
**Card Created**: 2025-10-09
