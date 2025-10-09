# Sprint 00: Foundation & Setup - Sprint Backlog

**Sprint Duration**: Week 1-2
**Team Capacity**: 80 story points
**Committed**: 65 story points (81% capacity - healthy buffer)

---

## Selected Cards

| Card ID | Title | Points | Assignee | Status |
|---------|-------|--------|----------|--------|
| **F001** | Project setup (pyproject.toml, directory structure) | 5 | TBD | Backlog |
| **F002** | Virtual environment + dependencies | 3 | TBD | Backlog |
| **F003** | Git setup (pre-commit hooks, .gitignore) | 2 | TBD | Backlog |
| **F004** | Base logging configuration | 5 | TBD | Backlog |
| **F005** | Base exception taxonomy | 5 | TBD | Backlog |
| **F006** | Database connection manager | 5 | TBD | Backlog |
| **F007** | Alembic setup + first migration | 5 | TBD | Backlog |
| **F008** | Ruff configuration | 3 | TBD | Backlog |
| **F009** | pytest configuration | 5 | TBD | Backlog |
| **F010** | mypy configuration | 2 | TBD | Backlog |
| **F011** | Dockerfile (multi-stage) | 8 | TBD | Backlog |
| **F012** | docker-compose.yml | 5 | TBD | Backlog |
| | **TOTAL** | **65** | | |

---

## Sprint Goal

> "Establish production-ready development environment and foundational infrastructure"

---

## Daily Breakdown (Planned)

### Week 1

**Day 1-2: Initial Setup** (18 points)
- F001: Project setup (5 pts)
- F002: Virtual environment (3 pts)
- F003: Git setup (2 pts)
- F004: Logging (5 pts)
- F008: Ruff (3 pts)

**Day 3-4: Core Infrastructure** (17 points)
- F005: Exceptions (5 pts)
- F006: Database connection (5 pts)
- F007: Alembic (5 pts)
- F010: mypy (2 pts)

**Day 5: Testing Setup** (5 points)
- F009: pytest configuration (5 pts)

### Week 2

**Day 6-8: Containerization** (13 points)
- F011: Dockerfile (8 pts)
- F012: docker-compose.yml (5 pts)

**Day 9-10: Testing & Documentation** (buffer)
- Integration testing
- Documentation review
- Troubleshooting guide updates
- Sprint review preparation

---

## Parallel Work Tracks

### Track 1: Infrastructure (3 devs)
- F004, F005, F006, F007, F009
- Focus: Core app infrastructure

### Track 2: Quality Tooling (2 devs)
- F008, F010, F003
- Focus: Linting, typing, git hooks

### Track 3: Containerization (2 devs)
- F011, F012
- Focus: Docker setup

### Track 4: Project Foundation (3 devs)
- F001, F002
- Focus: Initial project structure

---

## Dependencies Graph

```
F001 (Project setup)
  ↓
F002 (Dependencies) → F003 (Git hooks)
  ↓
F004 (Logging) ────┐
F005 (Exceptions) ─┤
F006 (DB connection) → F007 (Alembic)
  ↓               ↓
F009 (pytest) ←────┘
  ↓
F011 (Dockerfile) → F012 (docker-compose)
```

**Critical Path**: F001 → F002 → F006 → F007 → F011 → F012

---

## Sprint Risks

| Risk | Mitigation | Owner |
|------|-----------|-------|
| Docker issues on Windows | Test early, provide WSL2 guide | DevOps Lead |
| Dependency conflicts | Lock versions, use pip-tools | Tech Lead |
| Team onboarding delays | Pair programming first 2 days | Scrum Master |

---

## Definition of Done Reminder

Each card must meet:
- [ ] Code passes Ruff linting
- [ ] Type hints added (mypy passes)
- [ ] Tests written (if applicable)
- [ ] Documentation updated
- [ ] PR approved by 2+ reviewers
- [ ] Merged to main branch

---

**Last Updated**: 2025-10-09
**Sprint Planning Date**: TBD
**Sprint Review Date**: TBD
