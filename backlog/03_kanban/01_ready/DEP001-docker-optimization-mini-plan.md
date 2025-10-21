# Mini-Plan A: Docker & Docker Compose Optimization

**Created**: 2025-10-21
**Team Leader**: Orchestration Agent
**Epic**: sprint-05-deployment
**Priority**: HIGH (foundational for deployment)
**Complexity**: 5 points (Low)

---

## Task Overview

Optimize existing Dockerfile and docker-compose.yml for production readiness with health checks, proper restart policies, and environment variable management.

---

## Current State Analysis

**Existing Files**:
- `/home/lucasg/proyectos/DemeterDocs/Dockerfile` - Multi-stage build already implemented
- `/home/lucasg/proyectos/DemeterDocs/docker-compose.yml` - Services defined (db, db_test, redis, api)
- `/home/lucasg/proyectos/DemeterDocs/.env.example` - Environment template exists

**Already Implemented**:
- Multi-stage Dockerfile with Python 3.12
- Health checks for API (curl -f http://localhost:8000/health)
- Health checks for db, db_test, redis
- Non-root user (appuser)

**Missing**:
- Celery workers (currently commented out - need to verify Celery app exists)
- Production-specific docker-compose.prod.yml
- Optimized image size verification (<500MB target)
- Volume mounts for logs

---

## Architecture

**Layer**: Infrastructure (Deployment Layer)
**Pattern**: Docker multi-stage build + Docker Compose orchestration

**Dependencies**:
- Existing: Dockerfile, docker-compose.yml, .env.example
- New: docker-compose.prod.yml (production config)

**Files to Create/Modify**:
- [ ] `docker-compose.prod.yml` (create - production configuration)
- [ ] `.dockerignore` (verify/update - exclude test files, __pycache__)
- [ ] `Dockerfile` (minor updates - verify size optimization)
- [ ] `.env.example` (update with OTEL, Auth0 variables)

---

## Implementation Strategy

### Phase 1: Verify Celery App Exists (BLOCKER)

```bash
# Check if Celery app is implemented
ls /home/lucasg/proyectos/DemeterDocs/app/celery_app.py

# If exists, uncomment celery workers in docker-compose.yml
# If missing, keep commented and add TODO note
```

### Phase 2: Create docker-compose.prod.yml

**Production-specific changes**:
- Remove `--reload` from uvicorn command
- Add resource limits (memory, CPU)
- Add log rotation configuration
- Add volume mounts for persistent logs
- Add networks configuration
- Enable Celery workers if app exists

**Template**:
```yaml
services:
  api:
    build:
      context: .
      dockerfile: Dockerfile
      args:
        APP_ENV: production
    container_name: demeterai-api-prod
    restart: always
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
    # ... rest of config
```

### Phase 3: Verify Image Size

```bash
# Build image
docker build -t demeterai:latest .

# Check size
docker images demeterai:latest

# Target: <500MB
# If larger, optimize by:
# - Removing unnecessary packages
# - Using --no-cache-dir for pip
# - Cleaning apt cache
```

### Phase 4: Update .dockerignore

```
# Add/verify these entries
tests/
.pytest_cache/
__pycache__/
*.pyc
.git/
.env
.vscode/
*.md
docs/
backlog/
engineering_plan/
```

---

## Acceptance Criteria

- [ ] docker-compose.prod.yml created with production settings
- [ ] Image size ≤500MB verified
- [ ] Health checks working for all services
- [ ] Restart policies set to `always` or `unless-stopped`
- [ ] Resource limits defined
- [ ] Log rotation configured
- [ ] .dockerignore excludes test files
- [ ] Non-root user (appuser) used in production
- [ ] Celery workers enabled (if app exists) or documented as TODO

---

## Testing Procedure

```bash
# 1. Build production image
docker build -t demeterai:latest .

# 2. Check image size
docker images demeterai:latest | grep demeterai

# 3. Start production stack
docker-compose -f docker-compose.prod.yml up -d

# 4. Verify health checks
docker ps --format "table {{.Names}}\t{{.Status}}"

# 5. Test API health endpoint
curl http://localhost:8000/health

# 6. Check logs
docker-compose -f docker-compose.prod.yml logs api --tail=50

# 7. Verify resource limits
docker stats --no-stream demeterai-api-prod

# 8. Clean up
docker-compose -f docker-compose.prod.yml down
```

---

## Performance Expectations

- Image build time: <5 minutes
- Container startup time: <40 seconds (API)
- Health check response time: <3 seconds
- Image size: <500MB

---

## Dependencies

**Blocked By**: None (foundational task)
**Blocks**:
- Mini-Plan B (OpenTelemetry - needs container running)
- Mini-Plan C (Auth0 - needs API running)
- Mini-Plan D (Prometheus - needs metrics endpoint)

---

## Notes

- Celery workers (celery_cpu, celery_io, flower) are currently commented out in docker-compose.yml
- Need to verify if `/home/lucasg/proyectos/DemeterDocs/app/celery_app.py` exists
- If Celery app exists, enable workers in production compose file
- If missing, document as future work (out of scope for Sprint 5)
