# [F012] Docker Compose - Multi-Service Orchestration

## Metadata
- **Epic**: epic-001-foundation.md
- **Sprint**: Sprint-00 (Week 1-2)
- **Status**: `backlog`
- **Priority**: `high`
- **Complexity**: M (5 story points)
- **Area**: `foundation`
- **Assignee**: TBD
- **Dependencies**:
  - Blocks: [Local development for all developers]
  - Blocked by: [F001, F002, F011]

## Related Documentation
- **Deployment**: ../../engineering_plan/deployment/README.md#docker-compose-architecture
- **Tech Stack**: ../../backlog/00_foundation/tech-stack.md#deployment--containers

## Description

Create docker-compose.yml orchestrating all services (PostgreSQL 18 + PostGIS, Redis 7, FastAPI, Celery workers) with proper networking, volumes, and dependency management for local development.

**What**: Implement docker-compose.yml v3.8+ with 9 services: db (PostgreSQL + PostGIS), redis, api (FastAPI), celery_gpu_0, celery_cpu, celery_io, flower (monitoring), prometheus, grafana. Configure health checks, restart policies, and shared volumes.

**Why**: `docker-compose up` gives every developer a working environment in 1 command. No manual PostgreSQL/Redis installation. Consistent environments prevent "works on my machine" issues. Mimics production architecture locally.

**Context**: Team of 10 developers need identical environments. Manual setup (PostgreSQL, PostGIS, Redis, Celery) takes hours and is error-prone. docker-compose provides reproducible environments in 5 minutes.

## Acceptance Criteria

- [ ] **AC1**: `docker-compose.yml` created with all services:
  - `db`: PostgreSQL 18 + PostGIS 3.3
  - `redis`: Redis 7.x
  - `api`: FastAPI server (port 8000)
  - `celery_cpu`: CPU worker (prefork pool)
  - `celery_io`: I/O worker (gevent pool)
  - `flower`: Celery monitoring (port 5555)

- [ ] **AC2**: Health checks configured for all services:
  ```yaml
  healthcheck:
    test: ["CMD", "pg_isready", "-U", "demeter"]
    interval: 10s
    timeout: 5s
    retries: 5
  ```

- [ ] **AC3**: Dependency ordering:
  ```yaml
  api:
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
  ```

- [ ] **AC4**: Persistent volumes for data:
  - `postgres_data`: Database persistence
  - `redis_data`: Redis persistence (optional)

- [ ] **AC5**: Environment variables from .env:
  ```yaml
  env_file:
    - .env
  ```

- [ ] **AC6**: Commands work:
  ```bash
  docker-compose up -d          # Start all services
  docker-compose ps             # List services
  docker-compose logs -f api    # Follow logs
  docker-compose down           # Stop all services
  docker-compose down -v        # Stop and remove volumes
  ```

- [ ] **AC7**: All services start successfully:
  ```bash
  docker-compose up -d
  docker-compose ps
  # Expected: All services "healthy" or "running"
  ```

## Technical Implementation Notes

### Architecture
- Layer: Foundation (Orchestration)
- Dependencies: Docker Compose 2.x, Dockerfile (F011)
- Design pattern: Service orchestration, infrastructure as code

### Code Hints

**docker-compose.yml structure:**
```yaml
version: '3.8'

services:
  # ==========================================
  # PostgreSQL 18 + PostGIS
  # ==========================================
  db:
    image: postgis/postgis:18-3.3
    container_name: demeterai-db
    environment:
      POSTGRES_USER: demeter
      POSTGRES_PASSWORD: demeter_dev_password
      POSTGRES_DB: demeterai
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U demeter"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  # ==========================================
  # Redis 7
  # ==========================================
  redis:
    image: redis:7-alpine
    container_name: demeterai-redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5
    restart: unless-stopped

  # ==========================================
  # FastAPI Application
  # ==========================================
  api:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: demeterai-api
    ports:
      - "8000:8000"
    env_file:
      - .env
    environment:
      - DATABASE_URL=postgresql+asyncpg://demeter:demeter_dev_password@db:5432/demeterai
      - DATABASE_URL_SYNC=postgresql+psycopg2://demeter:demeter_dev_password@db:5432/demeterai
      - REDIS_URL=redis://redis:6379/0
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/1
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 3s
      retries: 3
      start_period: 40s
    restart: unless-stopped
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  # ==========================================
  # Celery CPU Worker
  # ==========================================
  celery_cpu:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: demeterai-celery-cpu
    env_file:
      - .env
    environment:
      - DATABASE_URL=postgresql+asyncpg://demeter:demeter_dev_password@db:5432/demeterai
      - REDIS_URL=redis://redis:6379/0
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/1
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped
    command: celery -A app.celery_app worker --pool=prefork --concurrency=4 --queues=cpu_queue --loglevel=info

  # ==========================================
  # Celery I/O Worker
  # ==========================================
  celery_io:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: demeterai-celery-io
    env_file:
      - .env
    environment:
      - DATABASE_URL=postgresql+asyncpg://demeter:demeter_dev_password@db:5432/demeterai
      - REDIS_URL=redis://redis:6379/0
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/1
    depends_on:
      redis:
        condition: service_healthy
    restart: unless-stopped
    command: celery -A app.celery_app worker --pool=gevent --concurrency=20 --queues=io_queue --loglevel=info

  # ==========================================
  # Flower (Celery Monitoring)
  # ==========================================
  flower:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: demeterai-flower
    ports:
      - "5555:5555"
    env_file:
      - .env
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/1
    depends_on:
      redis:
        condition: service_healthy
    restart: unless-stopped
    command: celery -A app.celery_app flower --port=5555

  # ==========================================
  # Prometheus (Sprint 05 - Optional Now)
  # ==========================================
  # prometheus:
  #   image: prom/prometheus:latest
  #   container_name: demeterai-prometheus
  #   ports:
  #     - "9090:9090"
  #   volumes:
  #     - ./prometheus.yml:/etc/prometheus/prometheus.yml
  #     - prometheus_data:/prometheus
  #   restart: unless-stopped

  # ==========================================
  # Grafana (Sprint 05 - Optional Now)
  # ==========================================
  # grafana:
  #   image: grafana/grafana:latest
  #   container_name: demeterai-grafana
  #   ports:
  #     - "3000:3000"
  #   volumes:
  #     - grafana_data:/var/lib/grafana
  #   restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
  # prometheus_data:
  # grafana_data:

networks:
  default:
    name: demeterai-network
```

**.env.example (reference):**
```env
# Database
DATABASE_URL=postgresql+asyncpg://demeter:demeter_dev_password@db:5432/demeterai
DATABASE_URL_SYNC=postgresql+psycopg2://demeter:demeter_dev_password@db:5432/demeterai

# Redis
REDIS_URL=redis://redis:6379/0

# Celery
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1

# AWS S3 (for local development, use MinIO or localstack)
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
AWS_S3_BUCKET=demeterai-photos-dev
AWS_REGION=us-east-1

# App
DEBUG=true
LOG_LEVEL=DEBUG
```

### Testing Requirements

**Unit Tests**: N/A (orchestration configuration)

**Integration Tests**:
- [ ] Test all services start:
  ```bash
  docker-compose up -d
  docker-compose ps
  # Expected: All services running/healthy
  ```

- [ ] Test service dependencies:
  ```bash
  docker-compose up -d
  # db and redis should start before api
  docker-compose logs api | grep "waiting"
  ```

- [ ] Test database connection:
  ```bash
  docker-compose up -d
  docker-compose exec api python -c "from app.db.session import test_connection; import asyncio; asyncio.run(test_connection())"
  # Expected: True
  ```

- [ ] Test API health:
  ```bash
  docker-compose up -d
  curl http://localhost:8000/health
  # Expected: {"status":"healthy"}
  ```

- [ ] Test Flower monitoring:
  ```bash
  docker-compose up -d
  curl http://localhost:5555
  # Expected: HTML page (Flower UI)
  ```

**Test Command**:
```bash
# Full integration test
docker-compose up -d
sleep 30  # Wait for health checks
docker-compose ps
docker-compose logs | grep ERROR  # Should be empty
docker-compose down
```

### Performance Expectations
- Initial startup: <2 minutes (image pulls + health checks)
- Subsequent startup: <30 seconds (cached images)
- Database ready: <10 seconds
- API ready: <15 seconds (after database)

## Handover Briefing

**For the next developer:**
- **Context**: This is the foundation for local development - every developer uses this
- **Key decisions**:
  - PostgreSQL 18 official postgis/postgis image (includes PostGIS 3.3)
  - Redis alpine variant (smaller image, same functionality)
  - Health checks with `condition: service_healthy` (ensures proper startup order)
  - Separate workers for CPU vs I/O tasks (different pool types)
  - Flower monitoring (essential for debugging Celery tasks)
  - Persistent volumes (data survives `docker-compose down`)
  - Network named `demeterai-network` (explicit networking)
- **Known limitations**:
  - GPU workers not included (requires NVIDIA Docker, manual setup)
  - No SSL/TLS (development only)
  - Passwords hardcoded in compose file (not for production)
  - No scaling configuration (use K8s for production)
- **Next steps after this card**:
  - All developers run `docker-compose up -d` to start working
  - DEP001-DEP012: Production docker-compose.prod.yml
  - Sprint 05: Add Prometheus + Grafana services
- **Questions to ask**:
  - Should we add MinIO for S3-compatible storage? (avoid AWS in dev)
  - Should we add PgAdmin for database GUI? (easier than psql)
  - Should we add nginx reverse proxy? (production-like routing)

## Definition of Done Checklist

- [ ] Code passes all tests (pytest)
- [ ] docker-compose.yml created with all services
- [ ] All services start successfully
- [ ] Health checks pass for all services
- [ ] Persistent volumes configured
- [ ] .env.example created
- [ ] PR approved by 2+ reviewers
- [ ] Documentation updated (README.md with docker-compose commands)
- [ ] All team members can run `docker-compose up` successfully

## Time Tracking
- **Estimated**: 5 story points
- **Actual**: TBD (fill after completion)
- **Started**: TBD
- **Completed**: TBD

---

**Card Created**: 2025-10-09
**Last Updated**: 2025-10-09
**Card Owner**: TBD (assign during sprint planning)
