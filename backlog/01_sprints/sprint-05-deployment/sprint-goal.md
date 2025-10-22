# Sprint 05: Deployment + Observability

## Sprint Goal

**Duration**: Week 11-12 (Days 51-60)
**Team Capacity**: 80 story points
**Committed**: 70 story points (buffer for stabilization)

---

## Goal Statement

> **"Production-ready deployment with observability, enabling stakeholder demo and handoff to
operations team."**

---

## Success Criteria

- [ ] Docker multi-stage build optimized (<500MB final image)
- [ ] docker-compose.yml production-ready (health checks, restart policies)
- [ ] OpenTelemetry exporting traces/logs/metrics (OTLP)
- [ ] Prometheus metrics exposed at `/metrics`
- [ ] Structured JSON logging with correlation IDs
- [ ] CI/CD pipeline (GitHub Actions: lint, test, build, deploy)
- [ ] Authentication complete (JWT + RBAC)
- [ ] API documentation finalized
- [ ] Demo environment deployed and stable

---

## Sprint Scope

### In Scope (32 cards, 70 points)

**Deployment (DEP001-DEP012)**: 25 points

- Multi-stage Dockerfile optimization
- docker-compose production configuration
- Health checks (API, DB, Redis, Celery workers)
- CI/CD pipeline (GitHub Actions)
- Environment configuration management
- Secret management (AWS Secrets Manager integration)

**Observability (OBS001-OBS010)**: 25 points

- OpenTelemetry instrumentation (FastAPI, Celery, SQLAlchemy)
- Prometheus metrics (API latency, ML inference time, GPU util)
- Structured JSON logging (correlation IDs, trace IDs)
- Log aggregation setup (assume external Loki/Grafana)
- Error tracking integration (Sentry placeholder)

**Authentication (AUTH001-AUTH006)**: 10 points

- JWT token generation/validation
- Password hashing (passlib + bcrypt)
- User CRUD endpoints
- Role-Based Access Control (admin, supervisor, worker, viewer)
- Login/logout/refresh endpoints

**Final Polish (10 points buffer)**:

- Performance optimization
- Documentation finalization
- Demo preparation
- Bug fixes

### Out of Scope

- ❌ Production deployment (operations team responsibility)
- ❌ Frontend integration (separate project)

---

## Key Deliverables

1. `Dockerfile` - Multi-stage optimized
2. `docker-compose.prod.yml` - Production configuration
3. `.github/workflows/ci.yml` - CI/CD pipeline
4. `app/core/telemetry.py` - OpenTelemetry setup
5. `app/core/auth.py` - JWT authentication
6. Complete API documentation
7. Deployment runbook

---

## Dependencies

**Blocked By**: Sprint 04 (API + Celery)
**Blocks**: Production handoff

---

**Sprint Owner**: DevOps Lead
**Last Updated**: 2025-10-09
