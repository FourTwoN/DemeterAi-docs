# [DEP010] Monitoring Stack Setup (Prometheus + Grafana)

## Metadata

- **Epic**: epic-011-deployment
- **Sprint**: Sprint-06
- **Priority**: `high`
- **Complexity**: M (5 points)
- **Dependencies**: Blocked by [OBS006, DEP002]

## Description

Deploy complete monitoring stack: Prometheus (metrics), Grafana (dashboards), Loki (logs), Tempo (
traces).

## Acceptance Criteria

- [ ] Prometheus scraping API /metrics every 15s
- [ ] Grafana dashboards accessible at :3000
- [ ] Loki collecting logs from all containers
- [ ] Tempo collecting traces via OTLP
- [ ] Persistent storage for metrics (30 days retention)
- [ ] Alertmanager configured for critical alerts

## Implementation

**docker-compose.yml additions:**

```yaml
services:
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.retention.time=30d'
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana:latest
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/dashboards:/etc/grafana/provisioning/dashboards
      - ./grafana/datasources:/etc/grafana/provisioning/datasources
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
    ports:
      - "3000:3000"

  loki:
    image: grafana/loki:latest
    volumes:
      - loki_data:/loki
    ports:
      - "3100:3100"

  tempo:
    image: grafana/tempo:latest
    volumes:
      - tempo_data:/tmp/tempo
    ports:
      - "4317:4317"  # OTLP gRPC
      - "3200:3200"  # Tempo HTTP

volumes:
  prometheus_data:
  grafana_data:
  loki_data:
  tempo_data:
```

**prometheus.yml:**

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'demeterai-api'
    static_configs:
      - targets: ['api:8000']

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres_exporter:9187']
```

**Grafana datasources:**

```yaml
apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    url: http://prometheus:9090
    isDefault: true

  - name: Loki
    type: loki
    url: http://loki:3100

  - name: Tempo
    type: tempo
    url: http://tempo:3200
```

## Testing

- Access Prometheus UI: http://localhost:9090
- Access Grafana UI: http://localhost:3000
- Query metrics: `rate(http_requests_total[5m])`
- View logs in Loki
- View traces in Tempo

---
**Card Created**: 2025-10-09
