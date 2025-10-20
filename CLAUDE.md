# DemeterAI v2.0 - Development Instructions

**Version**: 3.0
**Last Updated**: 2025-10-20
**Project**: DemeterAI v2.0 Backend Implementation
**Phase**: Sprint 03 - Services Layer

---

## Overview

You are working on **DemeterAI v2.0**, a production ML-powered inventory management system for **600,000+ plants**. This document is your primary instruction set for the entire development workflow.

**Project Context**:
- **Tech Stack**: FastAPI + PostgreSQL/PostGIS + Celery + YOLO v11
- **Architecture**: Clean Architecture (Controller → Service → Repository)
- **Current Phase**: Sprint 03 (Services Layer) - 42 tasks, 210 story points
- **Previous Sprints**: Sprint 00 (Setup) ✅, Sprint 01 (Database) ✅, Sprint 02 (ML Pipeline) ✅

---

## Quick Start

### I'm starting work - what should I do?

**Step 1: Understand your role**
```bash
# Are you orchestrating the project?
→ Use Scrum Master workflow

# Are you planning a specific task?
→ Use Team Leader workflow

# Are you writing Python code?
→ Use Python Expert workflow

# Are you writing tests?
→ Use Testing Expert workflow
```

**Step 2: Check current state**
```bash
# See what sprint we're in
cat /home/lucasg/proyectos/DemeterDocs/backlog/01_sprints/sprint-03-services/sprint-goal.md

# See what tasks are ready
ls /home/lucasg/proyectos/DemeterDocs/backlog/03_kanban/01_ready/

# See what's in progress
ls /home/lucasg/proyectos/DemeterDocs/backlog/03_kanban/02_in-progress/
```

**Step 3: Use the right workflow**
- See `.claude/workflows/orchestration.md` for how agents work together
- See role-specific workflow files for detailed instructions

---

## Multi-Agent System

### Chain of Command

```
User Request
    ↓
Scrum Master (State & Planning)
    ↓
Team Leader (Execution Planning)
    ↓
Python Expert + Testing Expert (Parallel Implementation)
    ↓
Team Leader (Quality Gates)
    ↓
Git Commit Agent (Finalization)
```

### When to Use Each Agent

| Situation | Use This Agent |
|-----------|---------------|
| Starting a sprint | Scrum Master |
| Breaking down an epic | Scrum Master |
| Implementing a task | Team Leader |
| Writing service/controller/repository code | Python Expert |
| Writing tests | Testing Expert |
| Database schema questions | Database Expert |
| Creating a commit | Git Commit Agent |

### Critical Workflows

**Location**: `.claude/workflows/`

1. **orchestration.md** - How all agents work together
2. **scrum-master-workflow.md** - Project state and task management
3. **team-leader-workflow.md** - Task planning and quality gates
4. **python-expert-workflow.md** - Clean Architecture implementation
5. **testing-expert-workflow.md** - Real database testing (NO MOCKS)

---

## Critical Rules (NEVER VIOLATE)

### Rule 1: Database as Source of Truth
- PostgreSQL schema in `database/database.mmd` is authoritative
- All models must match the schema EXACTLY
- Verify table names, column names, data types before implementing

### Rule 2: Tests Must ACTUALLY Pass
**Sprint 02 Critical Issue**: Tests were marked as passing when 70/386 were failing

**Prevention**:
```bash
# ALWAYS run pytest and verify output
pytest tests/ -v

# Check exit code (0 = pass, non-zero = fail)
echo $?

# Verify no mocked failures
grep -r "mock.*fail\|skip\|xfail" tests/

# Verify imports work
python -c "from app.models import *"
```

### Rule 3: Clean Architecture Patterns
**Service → Service** communication ONLY (NEVER Service → OtherRepository)

```python
# ❌ WRONG
class StockMovementService:
    def __init__(self, repo, config_repo):  # VIOLATION
        self.config_repo = config_repo

    async def method(self):
        config = await self.config_repo.get(...)  # WRONG

# ✅ CORRECT
class StockMovementService:
    def __init__(self, repo, config_service):
        self.config_service = config_service

    async def method(self):
        config = await self.config_service.get_by_location(...)  # CORRECT
```

### Rule 4: Quality Gates Are Mandatory
**Before marking any task complete**:
- ✅ All tests pass (verified by running pytest)
- ✅ Coverage ≥80% (verified by coverage report)
- ✅ Code review completed
- ✅ No hallucinated code (all imports verified)
- ✅ Models match database schema

### Rule 5: No Hallucinations
**Sprint 02 Issue**: Code referenced non-existent relationships

**Prevention**:
```bash
# Before implementing, READ existing code
cat app/models/warehouse.py

# Verify relationships exist
grep "relationship" app/models/*.py

# Check what's actually in the database
psql -d demeter -c "\d+ warehouses"
```

---

## File Structure

```
DemeterDocs/
├── CLAUDE.md                        ← THIS FILE (main instructions)
├── .claude/
│   ├── README.md                    ← Multi-agent system overview
│   ├── workflows/
│   │   ├── orchestration.md         ← How agents coordinate
│   │   ├── scrum-master-workflow.md
│   │   ├── team-leader-workflow.md
│   │   ├── python-expert-workflow.md
│   │   └── testing-expert-workflow.md
│   ├── agents/                      ← Agent definitions
│   ├── commands/                    ← Slash commands (/start-task, etc.)
│   └── templates/                   ← Task templates
├── CRITICAL_ISSUES.md               ← Lessons learned from Sprint 02
├── database/
│   └── database.mmd                 ← ERD (source of truth)
├── engineering_plan/                ← Architecture documentation
├── backlog/
│   ├── 01_sprints/                  ← Sprint goals
│   ├── 02_epics/                    ← Epic definitions
│   ├── 03_kanban/                   ← Task board (00_backlog → 05_done)
│   └── 04_templates/                ← Code templates
└── flows/                           ← Business process diagrams
```

---

## Kanban Workflow

### Task Lifecycle
```
00_backlog → 01_ready → 02_in-progress → 03_code-review → 04_testing → 05_done
                                   ↓
                             06_blocked (if issues)
```

### State Transitions (via `mv` command)
```bash
# Scrum Master: Unblock task
mv backlog/03_kanban/00_backlog/S001-*.md backlog/03_kanban/01_ready/

# Team Leader: Start task
mv backlog/03_kanban/01_ready/S001-*.md backlog/03_kanban/02_in-progress/

# Team Leader: Progress through review stages
mv backlog/03_kanban/02_in-progress/S001-*.md backlog/03_kanban/03_code-review/
mv backlog/03_kanban/03_code-review/S001-*.md backlog/03_kanban/04_testing/

# Team Leader: Complete (only after ALL quality gates pass)
mv backlog/03_kanban/04_testing/S001-*.md backlog/03_kanban/05_done/
```

---

## Quality Gates Checklist

### Before ANY task moves to `05_done/`:

**Gate 1: Code Review**
- [ ] Service→Service pattern enforced (no cross-repository access)
- [ ] All methods have type hints
- [ ] Async/await used correctly
- [ ] Docstrings present
- [ ] No TODO/FIXME in production code

**Gate 2: Tests Actually Pass**
```bash
# Run tests and verify
pytest tests/unit/services/test_example.py -v
pytest tests/integration/test_example.py -v

# Check exit code
echo $?  # Must be 0
```

**Gate 3: Coverage ≥80%**
```bash
pytest tests/ --cov=app/services/example --cov-report=term-missing

# Verify TOTAL line shows ≥80%
```

**Gate 4: No Hallucinations**
```bash
# Verify all imports work
python -c "from app.services.example import ExampleService"

# Verify models match schema
grep "class Example" app/models/example.py
# Compare with database/database.mmd
```

**Gate 5: Database Schema Match**
```bash
# Compare model with ERD
diff <(grep "class Example" app/models/example.py) \
     <(grep "Example" database/database.mmd)
```

---

## Sprint 02 Critical Issues

**See**: `CRITICAL_ISSUES.md` for complete details

### Issue 1: Tests Marked Passing When Actually Failing
- **What happened**: 70/386 tests were failing but marked as complete
- **Root cause**: Tests were mocked incorrectly, hiding real failures
- **Prevention**: Always run `pytest` and verify exit code

### Issue 2: Hallucinated Code
- **What happened**: Code referenced non-existent relationships
- **Root cause**: Didn't read existing models before implementing
- **Prevention**: Always READ code before modifying

### Issue 3: Schema Drift
- **What happened**: Models didn't match database schema
- **Root cause**: Implemented from memory instead of ERD
- **Prevention**: Always consult `database/database.mmd` first

---

## Technology Stack

### Core Technologies
- **Python**: 3.12
- **Framework**: FastAPI 0.109.0+
- **Database**: PostgreSQL 15+ with PostGIS 3.3+
- **ORM**: SQLAlchemy 2.0+ (async)
- **Validation**: Pydantic 2.5+
- **Task Queue**: Celery 5.3+ with Redis 7+
- **ML**: YOLO v11 (CPU-first, GPU optional)

### Architecture Patterns
- **Clean Architecture**: Controller → Service → Repository
- **Service Communication**: Service → Service (NEVER Service → OtherRepository)
- **Async First**: All database operations async
- **Type Hints**: Required on all functions
- **Testing**: Real database (NO MOCKS of business logic)

---

## Key Documentation

### Primary References
1. **database/database.mmd** - Complete ERD (source of truth)
2. **engineering_plan/03_architecture_overview.md** - Architecture patterns
3. **engineering_plan/database/README.md** - Database design
4. **.claude/CRITICAL_ISSUES.md** - Lessons learned

### Workflow References
1. **.claude/workflows/orchestration.md** - Agent coordination
2. **.claude/workflows/scrum-master-workflow.md** - Project management
3. **.claude/workflows/team-leader-workflow.md** - Task planning
4. **.claude/workflows/python-expert-workflow.md** - Implementation
5. **.claude/workflows/testing-expert-workflow.md** - Testing

---

## Common Commands

### Slash Commands
```bash
/plan-epic epic-004        # Break epic into tasks
/start-task S001           # Create Mini-Plan and start implementation
/review-task S001          # Run quality gates
/complete-task S001        # Finalize after gates pass
```

### Git Workflow
```bash
# After Team Leader approves completion
git add app/services/example.py tests/
git commit -m "feat(services): implement ExampleService

- Add ExampleService with create/update/delete methods
- Implement Service→Service pattern (calls ConfigService)
- Add unit tests (85% coverage)
- Add integration tests (real DB)

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Best Practices

### For All Agents

1. **Read Before Writing**
   - Check existing code
   - Consult database schema
   - Review related services

2. **Verify Everything**
   - Run tests manually
   - Check imports
   - Validate against schema

3. **Document as You Go**
   - Update task files
   - Add comments to code
   - Explain architectural decisions

4. **Never Assume**
   - Don't guess schema details
   - Don't assume relationships exist
   - Don't hallucinate method signatures

### For Code Implementation

```python
# ✅ GOOD: Type hints, async, Service→Service
class ExampleService:
    def __init__(
        self,
        repo: ExampleRepository,
        config_service: ConfigService  # ✅ Service
    ):
        self.repo = repo
        self.config_service = config_service

    async def create(self, request: CreateRequest) -> ExampleResponse:
        """Create a new example."""
        # Validate via other service
        config = await self.config_service.validate(request)  # ✅

        # Use own repository
        entity = await self.repo.create(request)  # ✅

        return ExampleResponse.model_validate(entity)
```

### For Testing

```python
# ✅ GOOD: Real database, no mocks of business logic
@pytest.mark.asyncio
async def test_create_example(db_session):
    # Setup: Real database records
    config = await create_test_config(db_session)

    # Act: Call service with real dependencies
    service = ExampleService(
        repo=ExampleRepository(db_session),
        config_service=ConfigService(...)  # Real service
    )
    result = await service.create(request)

    # Assert: Verify database state
    assert result.id is not None
    db_record = await db_session.get(Example, result.id)
    assert db_record is not None
```

---

## Troubleshooting

### Tests are failing
1. Run `pytest tests/ -v` to see failures
2. Check imports: `python -c "from app.models import *"`
3. Verify database schema matches models
4. Check for mocked failures: `grep -r "mock.*fail" tests/`

### Code won't import
1. Check for circular imports
2. Verify `__init__.py` files exist
3. Check Python path
4. Verify dependencies installed

### Service pattern violation
1. Search for repository usage: `grep -r "Repository" app/services/`
2. Verify only `self.repo` is accessed directly
3. Other repositories must be accessed via services

### Schema mismatch
1. Compare model with ERD: `database/database.mmd`
2. Check migration files
3. Verify column names match exactly

---

## Next Steps

1. **Read the workflow files**: Start with `.claude/workflows/orchestration.md`
2. **Understand your role**: Read the specific workflow for your agent
3. **Check current state**: Look at kanban board (`backlog/03_kanban/`)
4. **Review critical issues**: Read `CRITICAL_ISSUES.md` to avoid past mistakes
5. **Start working**: Follow your workflow's step-by-step process

---

**Remember**: Quality over speed. It's better to implement one task correctly than five tasks incorrectly.

**Last Updated**: 2025-10-20
**Maintained By**: DemeterAI Engineering Team
