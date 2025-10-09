# [F001] Project Setup - Directory Structure + pyproject.toml

## Metadata
- **Epic**: epic-001-foundation.md
- **Sprint**: Sprint-00 (Week 1-2)
- **Status**: `backlog`
- **Priority**: `high`
- **Complexity**: S (5 story points)
- **Area**: `foundation`
- **Assignee**: TBD
- **Dependencies**:
  - Blocks: [F002, F003, F004, F005]
  - Blocked by: None (first card)

## Related Documentation
- **Engineering Plan**: ../../engineering_plan/development/README.md
- **Tech Stack**: ../../backlog/00_foundation/tech-stack.md
- **Template**: ../../backlog/04_templates/config-templates/pyproject.toml.template

## Description

Create the initial project structure and packaging configuration for DemeterAI v2.0 backend. This establishes the foundation for all future development work.

**What**: Set up Python project with modern packaging (pyproject.toml), create directory structure following Clean Architecture, and configure basic project metadata.

**Why**: A well-organized project structure from day 1 prevents technical debt and ensures team follows consistent patterns. Modern Python packaging (pyproject.toml) replaces legacy setup.py and enables better dependency management.

**Context**: This is the FIRST card in the project. Everything else depends on this foundation.

## Acceptance Criteria

- [ ] **AC1**: Directory structure created following Clean Architecture:
  ```
  app/
  ├── core/          (exceptions, logging, config)
  ├── models/        (SQLAlchemy models)
  ├── repositories/  (data access layer)
  ├── services/      (business logic)
  ├── controllers/   (FastAPI routes)
  ├── schemas/       (Pydantic validation)
  ├── db/            (database session, connection)
  └── main.py        (FastAPI app entry point)
  ```

- [ ] **AC2**: `pyproject.toml` created with:
  - Project metadata (name, version, description)
  - Python 3.12 requirement
  - All production dependencies with locked versions (see tech-stack.md)
  - Dev dependencies in separate section
  - Ruff, pytest, mypy configuration

- [ ] **AC3**: `requirements.txt` generated from pyproject.toml:
  ```bash
  pip install -e .
  pip freeze > requirements.txt
  ```

- [ ] **AC4**: Virtual environment working:
  ```bash
  python3.12 -m venv venv
  source venv/bin/activate
  pip install -e ".[dev]"
  ```

- [ ] **AC5**: Basic `app/main.py` created with FastAPI minimal app:
  ```python
  from fastapi import FastAPI
  app = FastAPI(title="DemeterAI v2.0", version="2.0.0")

  @app.get("/health")
  async def health():
      return {"status": "healthy"}
  ```
  Server starts with: `uvicorn app.main:app --reload`

## Technical Implementation Notes

### Architecture
- Layer: Foundation
- Dependencies: None
- Design pattern: Clean Architecture directory structure

### Code Hints

**pyproject.toml structure:**
```toml
[project]
name = "demeterai-backend"
version = "2.0.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi==0.118.2",
    # ... see tech-stack.md for complete list
]

[project.optional-dependencies]
dev = [
    "pytest==8.3.0",
    "ruff==0.7.0",
    # ... dev tools
]
```

**Directory creation:**
```bash
mkdir -p app/{core,models,repositories,services,controllers,schemas,db}
touch app/__init__.py app/main.py
touch app/core/{__init__.py,exceptions.py,logging.py,config.py}
# ... etc
```

### Testing Requirements

**Unit Tests**: N/A (structural card, no business logic)

**Integration Tests**:
- [ ] Test that FastAPI app starts: `uvicorn app.main:app`
- [ ] Test `/health` endpoint returns 200 OK
- [ ] Test all dependencies install without conflicts

**Test Command**:
```bash
# Verify installation
pip install -e ".[dev]"

# Verify FastAPI starts
uvicorn app.main:app --reload &
sleep 2
curl http://localhost:8000/health
# Expected: {"status":"healthy"}
killall uvicorn
```

### Performance Expectations
- Installation time: <2 minutes
- App startup time: <1 second
- `/health` response time: <10ms

## Handover Briefing

**For the next developer:**
- **Context**: This is the foundational card - sets up the entire project structure
- **Key decisions**:
  - Using pyproject.toml (modern Python packaging, not setup.py)
  - Clean Architecture directory structure (controllers → services → repositories → models)
  - Python 3.12 required (latest stable, async improvements)
- **Known limitations**: None
- **Next steps after this card**:
  - F002: Install dependencies and create requirements.txt
  - F003: Git setup (pre-commit hooks, .gitignore)
  - F004: Logging configuration
- **Questions to ask**: None - straightforward setup

## Definition of Done Checklist

- [ ] Code passes all tests (pytest)
- [ ] Directory structure matches specification
- [ ] pyproject.toml includes all dependencies from tech-stack.md
- [ ] Virtual environment activates successfully
- [ ] FastAPI server starts and `/health` endpoint works
- [ ] PR approved by 2+ reviewers
- [ ] Documentation updated (README.md with setup instructions)
- [ ] No console.log or print() statements

## Time Tracking
- **Estimated**: 5 story points
- **Actual**: TBD (fill after completion)
- **Started**: TBD
- **Completed**: TBD

---

**Card Created**: 2025-10-09
**Last Updated**: 2025-10-09
**Card Owner**: TBD (assign during sprint planning)
