# [OBS010] Prometheus Alert Rules

## Metadata

- **Epic**: epic-010-observability
- **Sprint**: Sprint-07
- **Priority**: `medium`
- **Complexity**: M (5 points)
- **Dependencies**: Blocked by [OBS006, DEP010]

## Description

Define Prometheus alerting rules for critical issues: high error rate, slow responses, database
down, GPU OOM.

## Acceptance Criteria

- [ ] **Alert: High Error Rate**
    - Trigger: >5% of requests return 5xx
    - Duration: 5 minutes
    - Severity: critical

- [ ] **Alert: Slow API Response**
    - Trigger: p95 latency >2s
    - Duration: 10 minutes
    - Severity: warning

- [ ] **Alert: Database Down**
    - Trigger: All database connections fail
    - Duration: 1 minute
    - Severity: critical

- [ ] **Alert: Celery Queue Backed Up**
    - Trigger: >100 pending tasks
    - Duration: 15 minutes
    - Severity: warning

- [ ] **Alert: GPU OOM**
    - Trigger: GPU memory >90%
    - Duration: 5 minutes
    - Severity: critical

- [ ] Alerts sent to Slack/email (Alertmanager)

## Implementation

**prometheus/alerts.yml:**

```yaml
groups:
  - name: api_alerts
    interval: 30s
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status_code=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High 5xx error rate"
          description: "{{ $value | humanizePercentage }} of requests failing"

      - alert: SlowAPIResponse
        expr: histogram_quantile(0.95, rate(http_request_duration_bucket[5m])) > 2000
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "API responses slow (p95 > 2s)"

      - alert: DatabaseDown
        expr: up{job="postgres"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Database is down"
```

## Testing

- Trigger alerts manually (simulate failures)
- Verify alerts fire in Prometheus
- Verify notifications sent via Alertmanager

---
**Card Created**: 2025-10-09
