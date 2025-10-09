# Epic 011: Deployment & Infrastructure

**Status**: Ready
**Sprint**: Sprint-05 (Week 11-12)
**Priority**: high (production readiness)
**Total Story Points**: 60
**Total Cards**: 12 (DEP001-DEP012)

---

## Goal

Implement production deployment infrastructure with CI/CD pipeline, container orchestration, database backups, and production docker-compose configuration.

---

## Success Criteria

- [ ] CI/CD pipeline builds and tests on every commit
- [ ] Docker images pushed to container registry (ECR or Docker Hub)
- [ ] Production docker-compose.yml with secrets management
- [ ] Database backup and restore scripts
- [ ] Health checks and readiness probes configured
- [ ] SSL/TLS certificates configured
- [ ] Deployment runbook documented

---

## Cards List (12 cards, 60 points)

### CI/CD (20 points)
- **DEP001**: GitHub Actions workflow (or GitLab CI) (8pts)
- **DEP002**: Automated testing in CI (5pts)
- **DEP003**: Docker image build and push (5pts)
- **DEP004**: Deployment to staging (2pts)

### Production Config (15 points)
- **DEP005**: docker-compose.prod.yml (5pts)
- **DEP006**: Secrets management (AWS Secrets Manager) (5pts)
- **DEP007**: SSL/TLS configuration (nginx reverse proxy) (3pts)
- **DEP008**: Environment-specific .env files (2pts)

### Database Operations (15 points)
- **DEP009**: Database backup scripts (automated) (5pts)
- **DEP010**: Database restore procedure (3pts)
- **DEP011**: Migration rollback plan (3pts)
- **DEP012**: Point-in-time recovery (PITR) setup (4pts)

### Health & Reliability (10 points)
- **DEP013**: Health check endpoints (2pts)
- **DEP014**: Readiness probes (2pts)
- **DEP015**: Graceful shutdown (3pts)
- **DEP016**: Zero-downtime deployment (3pts)

---

## Dependencies

**Blocked By**: F011 (Dockerfile), F012 (docker-compose), all feature cards
**Blocks**: Production launch

---

## Technical Approach

**CI/CD Pipeline** (.github/workflows/main.yml):
```yaml
name: CI/CD

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - run: pip install -r requirements.txt
      - run: pytest --cov=app --cov-fail-under=80

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: docker/build-push-action@v4
        with:
          push: true
          tags: myregistry/demeterai:${{ github.sha }}

  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - run: ssh user@server 'docker-compose pull && docker-compose up -d'
```

**Production docker-compose.yml**:
```yaml
version: '3.8'

services:
  api:
    image: myregistry/demeterai:latest
    secrets:
      - db_password
      - jwt_secret
    environment:
      - DATABASE_URL=postgresql+asyncpg://demeter:${DB_PASSWORD}@db:5432/demeterai
      - JWT_SECRET=${JWT_SECRET}
    deploy:
      replicas: 3
      restart_policy:
        condition: on-failure
        max_attempts: 3
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s

secrets:
  db_password:
    external: true
  jwt_secret:
    external: true
```

**Database Backup** (automated):
```bash
#!/bin/bash
# Daily backup at 2 AM
pg_dump -h localhost -U demeter demeterai | \
  gzip > backups/demeterai_$(date +%Y%m%d).sql.gz

# Upload to S3
aws s3 cp backups/demeterai_$(date +%Y%m%d).sql.gz \
  s3://backups/demeterai/

# Keep 30 days, then monthly
find backups/ -name "*.sql.gz" -mtime +30 -delete
```

---

**Epic Owner**: DevOps Lead
**Created**: 2025-10-09
