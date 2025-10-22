# [DEP002] Docker Compose Production

## Metadata

- **Epic**: epic-011-deployment
- **Sprint**: Sprint-02
- **Priority**: `critical` ⚡
- **Complexity**: L (8 points)
- **Dependencies**: Blocked by [DEP001, F012]

## Description

Complete docker-compose.yml for production with all services: API, Celery workers (GPU/CPU/IO),
PostgreSQL, Redis, Prometheus, Grafana.

## Acceptance Criteria

- [ ] All 9 services defined (api, celery_gpu_0, celery_gpu_1, celery_cpu, celery_io, db, redis,
  prometheus, grafana)
- [ ] GPU workers use nvidia-runtime
- [ ] Volume mounts for persistence
- [ ] Health checks for all services
- [ ] Networks configured (backend, monitoring)
- [ ] Environment variable files (.env)

## Implementation

```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    env_file: .env
    depends_on:
      - db
      - redis
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  celery_gpu_0:
    build: .
    command: celery -A app worker --pool=solo --concurrency=1 --queues=gpu_queue_0
    env_file: .env
    environment:
      - CUDA_VISIBLE_DEVICES=0
    runtime: nvidia
    depends_on:
      - redis

  celery_cpu:
    build: .
    command: celery -A app worker --pool=prefork --concurrency=16 --queues=cpu_queue
    env_file: .env

  db:
    image: postgis/postgis:18-3.3
    environment:
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"

volumes:
  postgres_data:
  redis_data:
```

## Testing

- Start stack: `docker-compose up -d`
- Verify all services healthy: `docker-compose ps`
- Test API at http://localhost:8000
- Test Grafana at http://localhost:3000

---
**Card Created**: 2025-10-09
