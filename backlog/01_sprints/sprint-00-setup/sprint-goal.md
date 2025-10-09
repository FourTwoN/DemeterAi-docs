# Sprint 00: Foundation & Setup
## Sprint Goal

**Duration**: Week 1-2 (Days 1-10)
**Team Size**: 10 developers
**Capacity**: 80 story points (10 devs × 8 points)

---

## Goal Statement

> **"Establish production-ready development environment and foundational infrastructure so the team can start backend development with zero blockers in Sprint 01."**

---

## Success Criteria

At the end of this sprint, every developer should be able to:
- [ ] Clone repository and run `docker-compose up` successfully
- [ ] Run database migrations (`alembic upgrade head`) without errors
- [ ] Start FastAPI server and see Swagger docs at `/docs`
- [ ] Run tests (`pytest`) and get green results
- [ ] Commit code that passes pre-commit hooks (linting, formatting, typing)
- [ ] Understand Clean Architecture principles and conventions

---

## Sprint Scope

### In Scope (12 cards, ~65 story points)

**Project Setup (F001-F003)**: 15 points
- F001: Project directory structure + pyproject.toml
- F002: Virtual environment + dependencies (requirements.txt)
- F003: Git setup (pre-commit hooks, .gitignore)

**Base Infrastructure (F004-F007)**: 20 points
- F004: Base logging configuration (structured JSON, correlation IDs)
- F005: Base exception taxonomy (AppBaseException + 10 subclasses)
- F006: Database connection manager (async session factory, pooling)
- F007: Alembic setup (migrations infrastructure, first migration)

**Quality & Tooling (F008-F010)**: 15 points
- F008: Ruff configuration (linting + formatting rules)
- F009: pytest configuration (fixtures, test DB setup)
- F010: mypy configuration (type checking rules)

**Containerization (F011-F012)**: 15 points
- F011: Dockerfile (multi-stage build, Python 3.12-slim base)
- F012: docker-compose.yml (PostgreSQL 18, Redis 7, API, workers)

### Out of Scope
- ❌ Any database models (Sprint 01)
- ❌ Any services or repositories (Sprint 01+)
- ❌ ML pipeline components (Sprint 02)
- ❌ API controllers (Sprint 04)

---

## Key Deliverables

**Code Artifacts**:
1. Working `pyproject.toml` with all dependencies
2. Base exception classes in `app/core/exceptions.py`
3. Logger configuration in `app/core/logging.py`
4. Database session manager in `app/db/session.py`
5. Alembic migrations in `alembic/versions/`
6. Working `Dockerfile` and `docker-compose.yml`

**Documentation**:
1. `README.md` with setup instructions
2. `CONTRIBUTING.md` with development workflow
3. `.env.example` with all required environment variables

**Quality Gates**:
1. All pre-commit hooks pass
2. pytest runs successfully (even with 0 tests initially)
3. Docker Compose brings up all services without errors
4. Database migrations run successfully

---

## Sprint Risks & Mitigation

### Risk 1: Docker Issues on Different OS
**Probability**: Medium
**Impact**: High (blocks entire team)
**Mitigation**:
- Test on Linux, Mac, Windows before sprint end
- Document OS-specific issues in troubleshooting guide
- Provide VM/cloud alternative if local Docker fails

### Risk 2: Dependency Conflicts
**Probability**: Low
**Impact**: Medium
**Mitigation**:
- Lock all dependencies with exact versions in requirements.txt
- Use `pip-tools` for dependency resolution
- Test clean install on fresh machine

### Risk 3: Team Onboarding Delays
**Probability**: Medium
**Impact**: Medium (reduces velocity)
**Mitigation**:
- Pair new team members with experienced devs
- Allocate first 2 days for setup (don't assign cards yet)
- Create detailed QUICK_START.md guide

---

## Dependencies

### External Dependencies
- **Docker**: v24+ required (check with `docker --version`)
- **PostgreSQL 18**: Docker image `postgis/postgis:18-3.5`
- **Python 3.12**: Required on host for development

### Blocking Issues
- None (first sprint, no dependencies)

---

## Definition of Done (Sprint Level)

- [ ] All 12 cards completed and merged to main
- [ ] Every team member completed local setup successfully
- [ ] docker-compose.yml tested on Linux, Mac, Windows
- [ ] Documentation reviewed and approved
- [ ] Sprint review demo shows working environment
- [ ] Sprint retrospective completed with action items

---

## Next Sprint Preview

**Sprint 01 (Week 3-4)**: Database Models & Repositories
- Create all 28 SQLAlchemy models
- Implement AsyncRepository pattern
- Write Alembic migrations for complete schema
- 63 cards: DB001-DB035 (models) + R001-R028 (repositories)

**Why Sprint 00 is Critical**:
Without a solid foundation, Sprint 01 will be blocked. Every hour spent on setup in Sprint 00 saves 10 hours of debugging in later sprints.

---

**Sprint Owner**: Tech Lead
**Last Updated**: 2025-10-09
