# Sprint 5 Implementation Coordination Plan

**Created**: 2025-10-21
**Orchestrator**: Team Leader Agent
**Sprint**: Sprint 05 - Deployment + Observability
**Status**: READY FOR IMPLEMENTATION

---

## Overview

This document coordinates parallel implementation of Sprint 5 tasks between Python Expert and
Testing Expert. All mini-plans are complete and ready for execution.

---

## Mini-Plans Created

All mini-plans are located in `/home/lucasg/proyectos/DemeterDocs/backlog/03_kanban/01_ready/`:

1. **DEP001-docker-optimization-mini-plan.md** - Docker & Docker Compose optimization
2. **OBS001-opentelemetry-setup-mini-plan.md** - OpenTelemetry integration
3. **AUTH001-auth0-integration-mini-plan.md** - Auth0 JWT authentication
4. **OBS002-prometheus-metrics-mini-plan.md** - Prometheus metrics
5. **DEP002-github-actions-cicd-mini-plan.md** - GitHub Actions CI/CD
6. **DEP003-deployment-runbook-mini-plan.md** - Deployment documentation

---

## Parallel Execution Plan

### Phase 1: Foundational Tasks (Can Run in Parallel)

**Task Group A - Python Expert**:

- [ ] **OBS001**: OpenTelemetry Setup (10 points)
    - Create `app/core/telemetry.py`
    - Update `app/core/config.py` with OTEL settings
    - Update `app/main.py` to integrate OTEL
    - Add dependencies to `requirements.txt`
    - Update `.env.example`

- [ ] **OBS002**: Prometheus Metrics (6 points)
    - Create `app/core/metrics.py`
    - Update `app/main.py` to expose `/metrics`
    - Add dependencies to `requirements.txt`
    - Instrument business logic (stock service, ML service)

- [ ] **AUTH001**: Auth0 Integration (8 points)
    - Create `app/core/auth.py` (JWT verification)
    - Create `app/core/security.py` (password hashing)
    - Create `app/core/dependencies.py` (auth dependencies)
    - Create `app/controllers/auth_controller.py` (login/logout endpoints)
    - Create `app/schemas/auth.py` (Token, UserLogin schemas)
    - Update `app/core/config.py` with Auth0 settings
    - Update `.env.example`

**Task Group B - Testing Expert** (parallel):

- [ ] Create integration tests for OTEL (`tests/integration/test_telemetry.py`)
- [ ] Create integration tests for metrics (`tests/integration/test_metrics.py`)
- [ ] Create integration tests for auth (`tests/integration/test_auth.py`)
- [ ] Verify all existing tests still pass with new dependencies

**Estimated Time**: 6-8 hours (parallel)

---

### Phase 2: Infrastructure Tasks (Sequential, Python Expert)

**DEP001**: Docker Optimization (5 points)

- [ ] Check if Celery app exists (`app/celery_app.py`)
- [ ] Create `docker-compose.prod.yml`
- [ ] Update `.dockerignore`
- [ ] Verify image size (<500MB)
- [ ] Test production Docker Compose

**DEP002**: GitHub Actions CI/CD (7 points)

- [ ] Create `requirements-dev.txt`
- [ ] Create/update `pyproject.toml` (ruff, black, mypy config)
- [ ] Create `.github/workflows/ci.yml`
- [ ] Create `.github/workflows/docker-build.yml`
- [ ] Create `.pre-commit-config.yaml` (optional)

**Estimated Time**: 3-4 hours

---

### Phase 3: Documentation (Python Expert or Technical Writer)

**DEP003**: Deployment Runbook (5 points)

- [ ] Create `DEPLOYMENT_GUIDE.md`
- [ ] Create `OPERATIONS_RUNBOOK.md`
- [ ] Create `TROUBLESHOOTING.md`
- [ ] Update `README.md`

**Estimated Time**: 3-4 hours

---

## Dependency Graph

```
Phase 1 (Parallel):
  Python Expert                Testing Expert
  ├─ OBS001 (OTEL)       ───→  test_telemetry.py
  ├─ OBS002 (Metrics)    ───→  test_metrics.py
  └─ AUTH001 (Auth0)     ───→  test_auth.py

Phase 2 (Sequential):
  ├─ DEP001 (Docker)
  └─ DEP002 (CI/CD)
     └─ Depends on: All tests passing

Phase 3 (Sequential):
  └─ DEP003 (Documentation)
     └─ Depends on: All implementations complete
```

---

## Handoff to Python Expert

**Start with Phase 1, Task Group A**

Read mini-plans in this order:

1.

`/home/lucasg/proyectos/DemeterDocs/backlog/03_kanban/01_ready/OBS001-opentelemetry-setup-mini-plan.md`

2.

`/home/lucasg/proyectos/DemeterDocs/backlog/03_kanban/01_ready/OBS002-prometheus-metrics-mini-plan.md`

3.

`/home/lucasg/proyectos/DemeterDocs/backlog/03_kanban/01_ready/AUTH001-auth0-integration-mini-plan.md`

**Implementation Order** (within Phase 1):

1. Start with **OBS002 (Prometheus)** - simplest, no external dependencies
2. Then **OBS001 (OpenTelemetry)** - depends on Prometheus client
3. Finally **AUTH001 (Auth0)** - requires Auth0 account setup

**Key Rules**:

- Follow Clean Architecture patterns
- Add type hints to all functions
- Use async/await correctly
- Update imports in `app/core/__init__.py`
- Test each component as you build it

**Expected Deliverables**:

- [ ] `app/core/telemetry.py` (~150 lines)
- [ ] `app/core/metrics.py` (~200 lines)
- [ ] `app/core/auth.py` (~180 lines)
- [ ] `app/core/security.py` (~50 lines)
- [ ] `app/core/dependencies.py` (~80 lines)
- [ ] `app/controllers/auth_controller.py` (~100 lines)
- [ ] `app/schemas/auth.py` (~60 lines)
- [ ] Updated `requirements.txt` (add ~15 packages)
- [ ] Updated `.env.example` (add ~15 variables)

---

## Handoff to Testing Expert

**Start simultaneously with Python Expert's Phase 1**

Read mini-plans in this order:

1.

`/home/lucasg/proyectos/DemeterDocs/backlog/03_kanban/01_ready/OBS002-prometheus-metrics-mini-plan.md` (
Testing Procedure section)

2.

`/home/lucasg/proyectos/DemeterDocs/backlog/03_kanban/01_ready/OBS001-opentelemetry-setup-mini-plan.md` (
Testing Procedure section)

3.

`/home/lucasg/proyectos/DemeterDocs/backlog/03_kanban/01_ready/AUTH001-auth0-integration-mini-plan.md` (
Testing Procedure section)

**Testing Strategy**:

- Create integration tests (use real database, NOT mocks)
- Test against Python Expert's implementations
- Coordinate to get method signatures early
- Run tests locally before CI

**Expected Deliverables**:

- [ ] `tests/integration/test_metrics.py` (~100 lines)
- [ ] `tests/integration/test_telemetry.py` (~120 lines)
- [ ] `tests/integration/test_auth.py` (~150 lines)
- [ ] Verify all existing tests still pass
- [ ] Coverage report for new modules (≥80%)

---

## Quality Gates (Before Completion)

**Gate 1: Code Compiles and Imports Work**

```bash
python -c "from app.core.telemetry import setup_telemetry; print('✅ Telemetry OK')"
python -c "from app.core.metrics import setup_metrics; print('✅ Metrics OK')"
python -c "from app.core.auth import get_current_user; print('✅ Auth OK')"
```

**Gate 2: All Tests Pass**

```bash
pytest tests/unit/ -v
pytest tests/integration/ -v
echo $?  # Must be 0
```

**Gate 3: Coverage ≥80%**

```bash
pytest tests/ --cov=app.core.telemetry --cov=app.core.metrics --cov=app.core.auth --cov-report=term-missing
```

**Gate 4: Docker Build Succeeds**

```bash
docker build -t demeterai:latest .
docker images demeterai:latest | grep -E "(SIZE|demeterai)"
# Must be <500MB
```

**Gate 5: docker-compose up Works**

```bash
docker-compose -f docker-compose.prod.yml up -d
sleep 10
curl http://localhost:8000/health
curl http://localhost:8000/metrics
docker-compose -f docker-compose.prod.yml down
```

**Gate 6: OpenTelemetry Connects**

```bash
# Start application with OTEL enabled
OTEL_ENABLED=true uvicorn app.main:app --reload &
sleep 5

# Generate traffic
curl http://localhost:8000/health

# Check logs for "OpenTelemetry initialized successfully"
# Verify no OTLP exporter errors

kill %1
```

**Gate 7: Prometheus Metrics Exposed**

```bash
curl http://localhost:8000/metrics | grep "demeter_"
# Should show custom metrics
```

**Gate 8: GitHub Actions CI Passes** (after push)

```bash
git push origin main
# Check GitHub Actions: all jobs must pass
```

---

## Risk Mitigation

**Risk 1: OTLP endpoint not available**

- **Mitigation**: Make OTEL_ENABLED configurable (default: false for development)
- **Fallback**: Disable OTEL if endpoint unavailable

**Risk 2: Auth0 account setup delays**

- **Mitigation**: Use mock JWT tokens for testing
- **Fallback**: Implement local JWT signing (already in plan)

**Risk 3: Docker image size >500MB**

- **Mitigation**: Multi-stage build already implemented
- **Optimization**: Remove unnecessary packages, use slim base image

**Risk 4: Celery app doesn't exist**

- **Mitigation**: Keep Celery workers commented out in docker-compose
- **Documentation**: Add TODO note in deployment guide

**Risk 5: Tests fail with new dependencies**

- **Mitigation**: Testing Expert verifies all existing tests still pass
- **Fix**: Update fixtures if needed

---

## Communication Protocol

**Python Expert Status Updates** (every 30 minutes):

```markdown
## Status Update (HH:MM)
- OBS001: 60% complete (telemetry.py created, testing OTLP export)
- OBS002: 100% complete (metrics.py working, /metrics endpoint live)
- AUTH001: 20% complete (created auth.py skeleton)
- Blockers: Need Auth0 test credentials
```

**Testing Expert Status Updates** (every 30 minutes):

```markdown
## Status Update (HH:MM)
- test_metrics.py: 100% complete (all tests passing)
- test_telemetry.py: 70% complete (waiting for OTLP mock)
- test_auth.py: 30% complete (waiting for auth endpoints)
- Blockers: None
```

**Team Leader Reviews** (hourly):

- Check status updates from both experts
- Unblock dependencies
- Run quality gate checks
- Approve completed tasks

---

## Completion Checklist

**Phase 1 Complete When**:

- [ ] All Phase 1 code committed
- [ ] All Phase 1 tests passing
- [ ] Coverage ≥80% for new modules
- [ ] No import errors
- [ ] Application starts without errors

**Phase 2 Complete When**:

- [ ] docker-compose.prod.yml works
- [ ] Docker image <500MB
- [ ] GitHub Actions workflows created
- [ ] CI pipeline passes

**Phase 3 Complete When**:

- [ ] All documentation files created
- [ ] README.md updated
- [ ] Deployment guide validated (someone follows it successfully)

**Sprint 5 Complete When**:

- [ ] All quality gates passed
- [ ] All tasks moved to `05_done/`
- [ ] Git commit created with all changes
- [ ] SPRINT_05_DEPLOYMENT_GUIDE.md created and reviewed

---

## Estimated Timeline

**Day 1** (8 hours):

- Morning: Phase 1 (Python Expert + Testing Expert in parallel)
- Afternoon: Complete Phase 1, start Phase 2

**Day 2** (8 hours):

- Morning: Complete Phase 2 (Docker + CI/CD)
- Afternoon: Phase 3 (Documentation) + Quality Gates

**Total Effort**: 16 hours (2 days, 2 developers working in parallel)

---

## Success Metrics

- ✅ All 6 mini-plans implemented
- ✅ All tests passing (100%)
- ✅ Coverage ≥80%
- ✅ Docker image <500MB
- ✅ docker-compose up works cleanly
- ✅ OpenTelemetry connects to OTLP
- ✅ Prometheus /metrics endpoint functional
- ✅ Auth0 authentication working
- ✅ GitHub Actions CI passes
- ✅ Deployment guide complete and validated

---

## Next Steps After Sprint 5

1. **Deploy to Staging Environment** - Use deployment guide to deploy to staging server
2. **Load Testing** - Test with 600,000+ plant records
3. **Frontend Integration** - Integrate with React/Vue frontend
4. **Production Handoff** - Train operations team using OPERATIONS_RUNBOOK.md
5. **Monitoring Setup** - Configure alerts in Prometheus/Grafana
6. **Security Audit** - Run security scans, penetration testing

---

**Ready to Begin**: YES ✅

**Blockers**: NONE

**Dependencies**: All satisfied

**Start Implementation**: NOW
