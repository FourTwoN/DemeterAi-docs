# Epic 001: Foundation & Infrastructure

**Status**: Ready
**Sprint**: Sprint-00 (Week 1-2)
**Priority**: high (blocks all development)
**Total Story Points**: 65
**Total Cards**: 12 (F001-F012)

---

## Goal

Establish production-ready development environment and foundational infrastructure enabling backend
development with zero blockers in Sprint 01.

---

## Success Criteria

- [ ] All 10 developers can run `docker-compose up` successfully
- [ ] Database migrations work (`alembic upgrade head`)
- [ ] Tests pass (`pytest`) with 0 errors
- [ ] Pre-commit hooks enforce quality standards
- [ ] FastAPI server starts and serves `/docs`
- [ ] All foundation patterns established (logging, exceptions, DB)

---

## Cards List (12 cards, 65 points)

### Project Setup (10 points)

- **F001**: Project directory structure + pyproject.toml (5pts)
- **F002**: Virtual environment + dependencies (3pts)
- **F003**: Git setup (pre-commit hooks, .gitignore) (2pts)

### Core Infrastructure (25 points)

- **F004**: Base logging configuration (structured JSON, correlation IDs) (5pts)
- **F005**: Base exception taxonomy (AppBaseException + 10 subclasses) (5pts)
- **F006**: Database connection manager (async session, pooling) (5pts)
- **F007**: Alembic setup + first migration (5pts)
- **F009**: pytest configuration (test fixtures, test DB) (5pts)

### Quality Tooling (7 points)

- **F008**: Ruff configuration (linting + formatting) (3pts)
- **F010**: mypy configuration (type checking) (2pts)
- **F003**: Pre-commit hooks (integrated) (2pts)

### Containerization (13 points)

- **F011**: Dockerfile (multi-stage build, Python 3.12-slim) (8pts)
- **F012**: docker-compose.yml (PostgreSQL 18, Redis 7, API, workers) (5pts)

---

## Dependencies

**Blocked By**: None (first epic)
**Blocks**: All other epics (foundation required for everything)

---

## Technical Approach

**Directory Structure**:

```
app/
├── core/          # F004, F005
├── models/        # Sprint 01
├── repositories/  # Sprint 01
├── services/      # Sprint 03
├── controllers/   # Sprint 04
├── schemas/       # Sprint 04
├── db/            # F006, F007
└── main.py        # F001
```

**Key Patterns**:

- Async-first (AsyncSession, async def)
- Modern Python packaging (pyproject.toml)
- Quality gates (Ruff, pytest, mypy, pre-commit)

---

**Epic Owner**: Tech Lead
**Created**: 2025-10-09
