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

## Project Structure & Useful Paths

### Core Application (`app/`)
```
app/
├── main.py                 # FastAPI app entry point
├── core/
│   ├── config.py          # Configuration + environment
│   ├── exceptions.py       # Custom exceptions (CRITICAL: all exceptions here)
│   └── logging.py         # Logging configuration
├── db/
│   ├── base.py            # SQLAlchemy Base (all models inherit from this)
│   └── session.py         # Database session factory
├── models/                # 28 SQLAlchemy models (database/database.mmd is source of truth)
│   ├── warehouse.py       # (DB001) 4-level geospatial hierarchy
│   ├── storage_area.py    # (DB002)
│   ├── storage_location.py # (DB003)
│   ├── storage_bin.py     # (DB004)
│   ├── product*.py        # (DB015-DB019) 3-level product taxonomy
│   ├── stock_*.py         # (DB007-DB008) Stock management
│   ├── photo_processing_session.py # (DB012) ML pipeline
│   ├── detection.py       # (DB013) Partitioned by date
│   ├── estimation.py      # (DB014) Partitioned by date
│   └── [14 more models]
├── repositories/          # 27 async repositories (BaseRepository + 26 specialized)
│   ├── base.py            # Generic CRUD: get, get_multi, create, update, delete
│   ├── warehouse_repository.py
│   ├── product_repository.py
│   └── [24 more repositories]
├── services/              # Services layer (SPRINT 03 - TO BE IMPLEMENTED)
│   └── ml_processing/     # ML orchestration services
├── controllers/           # FastAPI route handlers (SPRINT 04+)
├── schemas/               # Pydantic schemas (SPRINT 03+)
└── celery/                # Celery tasks for async processing
```

### Database & Migrations
```
alembic/                   # Database migration system
├── versions/              # 14 migration files (consolidate as new ones added)
├── env.py                 # Alembic configuration
└── script.py.mako         # Migration template

database/
├── database.mmd           # ⭐️ SOURCE OF TRUTH - Complete ERD with all 28 models
└── database.md            # Schema documentation
```

### Documentation & Planning
```
backlog/                   # Project management
├── 00_epics/              # 17 epics defining all work
├── 01_sprints/            # Sprint goals and plans
│   ├── sprint-00/         # ✅ COMPLETE: Foundation
│   ├── sprint-01/         # ✅ COMPLETE: Database
│   ├── sprint-02/         # ✅ COMPLETE: ML Pipeline
│   └── sprint-03/         # → ACTIVE: Services Layer (42 tasks)
├── 03_kanban/             # Kanban board (DO NOT DELETE)
│   ├── 00_backlog/        # Raw backlog
│   ├── 01_ready/          # Tasks ready to start
│   ├── 02_in-progress/    # Currently working
│   ├── 03_code-review/    # Waiting review
│   ├── 04_testing/        # Testing phase
│   ├── 05_done/           # Completed tasks
│   └── 06_blocked/        # Blocked tasks

engineering_plan/          # Architecture & design documentation
├── 01_project_overview.md
├── 02_technology_stack.md
├── 03_architecture_overview.md
└── database/
    └── README.md          # Database design guide

flows/                     # Business process flows (Mermaid diagrams)
├── procesamiento_ml_upload_s3_principal/
├── photo_upload_gallery/
├── analiticas/
└── [other workflows]

.claude/                   # System instructions (READ FIRST!)
├── CLAUDE.md              # This file
├── CRITICAL_ISSUES.md     # ⚠️ Problems from Sprint 02 & prevention
├── README.md              # Quick navigation
├── workflows/
│   ├── orchestration.md        # How agents work together
│   ├── scrum-master-workflow.md
│   ├── team-leader-workflow.md
│   ├── python-expert-workflow.md
│   └── testing-expert-workflow.md
└── templates/
    ├── mini-plan-template.md
    ├── handoff-note.md
    └── task-progress-update.md
```

### Tests
```
tests/                     # 386/509 passing (75.8%)
├── unit/
│   └── models/            # Model tests (DB001-DB028)
├── integration/           # PostgreSQL integration tests
└── conftest.py            # Shared fixtures (db_session, factories, etc.)
```

### Key Documentation Files
```
SPRINT_02_COMPLETE_SUMMARY.md      # Current status (you are here)
FINAL_AUDIT_REPORT_*.md            # Detailed audit results
context/past_chats_summary.md       # Historical decisions
guides/flowchart_mermaid_docs.md    # Mermaid syntax reference
```

### Useful Commands

```bash
# PROJECT STATE
cd /home/lucasg/proyectos/DemeterDocs
ls backlog/03_kanban/01_ready/          # Tasks ready to start
ls backlog/03_kanban/02_in-progress/    # Currently working

# MODELS & DATABASE
cat database/database.mmd               # Source of truth for schema
python -c "from app.models import *; print('✅ Imports OK')"
pytest tests/unit/models/ -v            # Run model tests

# SERVICES (SPRINT 03)
ls app/services/                        # Services to implement
find app/services -name "*.py" | wc -l  # Service count

# REPOSITORIES (ALL 27 READY)
ls app/repositories/*.py | wc -l        # Verify 27 repos
python -c "from app.repositories import *"  # Verify imports

# TESTS
pytest tests/ -v --cov=app --cov-report=term-missing  # Full coverage
pytest tests/unit/models/ -v                          # Model tests only

# MIGRATIONS
ls alembic/versions/*.py                # See all migrations
alembic current                         # Current schema version
```

### Working with PostgreSQL

```bash
# Test database connection
docker compose up db_test -d
docker exec demeterai-db-test psql -U demeter_test -d demeterai_test -c "SELECT version();"

# Apply migrations
cd /home/lucasg/proyectos/DemeterDocs
alembic upgrade head

# Check tables
alembic current  # Get current revision
```

---

---

## Practical Programming Patterns

### Real Repository Example

```python
# ✅ app/repositories/product_repository.py
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.base import Base
from app.models.product import Product
from app.repositories.base import BaseRepository

class ProductRepository(BaseRepository[Product]):
    """Repository for Product entities - implements CRUD + domain-specific queries."""

    def __init__(self, session: AsyncSession):
        super().__init__(Product, session)

    async def get_by_code(self, code: str) -> Optional[Product]:
        """Get product by unique code (domain-specific query)."""
        stmt = select(self.model).where(self.model.code == code)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_category_and_family(
        self, category_id: int, family_id: int
    ) -> list[Product]:
        """Get products filtered by category and family."""
        stmt = select(self.model).where(
            (self.model.product_category_id == category_id) &
            (self.model.product_family_id == family_id)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
```

### Real Service Example (Sprint 03)

```python
# ✅ app/services/product_service.py
from app.repositories.product_repository import ProductRepository
from app.repositories.product_category_repository import ProductCategoryRepository
from app.repositories.product_family_repository import ProductFamilyRepository

class ProductService:
    """Service layer - business logic for products.

    Key Pattern: Service → Service (never Service → OtherRepository)
    """

    def __init__(
        self,
        repo: ProductRepository,
        category_service: ProductCategoryService,  # ✅ Service (not repo!)
        family_service: ProductFamilyService        # ✅ Service (not repo!)
    ):
        self.repo = repo
        self.category_service = category_service
        self.family_service = family_service

    async def create_product(self, request: CreateProductRequest) -> ProductResponse:
        """Create product with category/family validation.

        Flow:
        1. Validate category via CategoryService
        2. Validate family via FamilyService
        3. Create via ProductRepository
        4. Return response
        """
        # ✅ Call other services (NOT other repos)
        category = await self.category_service.get_by_id(request.category_id)
        family = await self.family_service.get_by_id(request.family_id)

        # ✅ Use own repository for database operations
        product = await self.repo.create(request)

        return ProductResponse.model_validate(product)
```

### Real Model With All 28 in Project

```
Database Models (DB001-DB028):
├─ Geospatial Layer (4-level hierarchy):
│  ├── DB001: Warehouse
│  ├── DB002: StorageArea
│  ├── DB003: StorageLocation
│  ├── DB004: StorageBin
│  └── DB006: LocationRelationships (NEW)
├─ Product Layer (3-level taxonomy):
│  ├── DB015: ProductCategory
│  ├── DB016: ProductFamily
│  ├── DB017: Product
│  ├── DB018: ProductSize
│  └── DB019: ProductState
├─ Stock Management:
│  ├── DB007: StockBatch
│  ├── DB008: StockMovement
│  └── DB005: StorageBinType
├─ ML Pipeline:
│  ├── DB012: PhotoProcessingSession
│  ├── DB013: Detection
│  ├── DB014: Estimation
│  └── DB011: Classification
├─ Packaging & Pricing:
│  ├── DB009: PackagingType
│  ├── DB010: PackagingColor
│  ├── DB021: PackagingMaterial
│  ├── DB022: PackagingCatalog
│  └── DB023: PriceList
├─ User Management:
│  ├── DB028: User
│  └── DB020: ProductSampleImage
└─ Configuration:
   ├── DB024: StorageLocationConfig
   ├── DB025: DensityParameter
   └── DB027: S3Image
```

---

## Directory Reference for Development

### When Working on Services (Sprint 03)

```bash
# STEP 1: Check if repository exists
ls app/repositories/ | grep -i product

# STEP 2: Read the repository to understand available methods
cat app/repositories/product_repository.py

# STEP 3: Read existing model to understand structure
cat app/models/product.py

# STEP 4: Create service in correct location
vim app/services/product_service.py

# STEP 5: Import repository in service
# Do NOT import other repositories directly!
from app.repositories.product_repository import ProductRepository
from app.services.category_service import ProductCategoryService  # ✅ Service!
```

### When Debugging Tests

```bash
# Run specific model tests
pytest tests/unit/models/test_product.py -v

# Run specific service tests (Sprint 03+)
pytest tests/unit/services/test_product_service.py -v

# Run integration tests
pytest tests/integration/ -v

# Full coverage with missing lines
pytest tests/ --cov=app --cov-report=term-missing | grep "TOTAL"
```

### When Working with Database Schema

```bash
# View complete ERD (source of truth)
cat database/database.mmd | grep -A 5 "ProductModel"

# Check what migration version we're at
alembic current

# View all migrations
ls -la alembic/versions/ | wc -l  # Should be 14

# See migration history
alembic history
```

### When Adding New Features (Proper Workflow)

```bash
# 1. Check kanban board
ls backlog/03_kanban/01_ready/ | head -5

# 2. Move task to in-progress
mv backlog/03_kanban/01_ready/S001-*.md backlog/03_kanban/02_in-progress/

# 3. Read the task spec
cat backlog/03_kanban/02_in-progress/S001-*.md

# 4. Check if model exists
cat app/models/product.py

# 5. Check if repository exists
cat app/repositories/product_repository.py

# 6. Implement service
vim app/services/product_service.py

# 7. Run tests
pytest tests/unit/services/test_product_service.py -v

# 8. Check quality gates
pytest tests/unit/services/test_product_service.py --cov --cov-report=term-missing

# 9. If all pass, move to code-review
mv backlog/03_kanban/02_in-progress/S001-*.md backlog/03_kanban/03_code-review/

# 10. After code review passes, move to testing
mv backlog/03_kanban/03_code-review/S001-*.md backlog/03_kanban/04_testing/

# 11. After all gates pass, move to done
mv backlog/03_kanban/04_testing/S001-*.md backlog/03_kanban/05_done/

# 12. Commit work
git add app/services/product_service.py tests/unit/services/test_product_service.py
git commit -m "feat(services): implement ProductService with category/family validation"
```

---

## System Architecture At A Glance

```
Request → FastAPI Controller (SPRINT 04+)
           ↓
           Service Layer (SPRINT 03)
           ├─ ProductService
           ├─ StockService
           ├─ WarehouseService
           └─ [25+ more services]
           ↓
           Service Dependencies (Service → Service)
           ├─ ProductService uses CategoryService
           ├─ StockService uses ProductService
           └─ WarehouseService uses LocationService
           ↓
           Repository Layer (SPRINT 02 COMPLETE ✅)
           ├─ ProductRepository
           ├─ StockRepository
           ├─ WarehouseRepository
           └─ [24+ more repositories]
           ↓
           Database Layer (SPRINT 01 COMPLETE ✅)
           ├─ 28 SQLAlchemy Models
           ├─ PostgreSQL + PostGIS
           └─ 14 Alembic Migrations
```

---

## .claude/ System Navigation

The `.claude/` folder contains all system instructions organized by purpose:

```
.claude/
├── README.md                          # START HERE (system overview)
├── INSTRUCTION_SYSTEM_README.md       # Detailed system guide
│
├── workflows/                         # Core agent workflows
│   ├── orchestration.md              # How agents coordinate (read first!)
│   ├── scrum-master-workflow.md       # Sprint/project management
│   ├── team-leader-workflow.md        # Task planning & quality gates
│   ├── python-expert-workflow.md      # Code implementation patterns
│   └── testing-expert-workflow.md     # Test creation & verification
│
├── commands/                          # Slash commands for manual triggers
│   ├── plan-epic.md                  # /plan-epic epic-004
│   ├── start-task.md                 # /start-task S001
│   ├── review-task.md                # /review-task S001
│   ├── complete-task.md              # /complete-task S001
│   └── sprint-review.md              # /sprint-review
│
├── templates/                         # Reusable templates for tasks
│   ├── mini-plan-template.md         # Use when creating implementation plans
│   ├── task-progress-update.md       # Track task progress during work
│   └── handoff-note.md               # Document handoffs between agents
│
└── agents/                           # Agent role definitions
    ├── scrum-master.md               # How Scrum Master thinks/decides
    ├── team-leader.md                # How Team Leader reviews code
    ├── python-expert.md              # How Python Expert implements
    ├── testing-expert.md             # How Testing Expert verifies
    ├── database-expert.md            # Database schema authority
    └── git-commit-writer.md          # Commit message standards
```

**Key Entry Points by Role**:
- **Starting Sprint**: Read `.claude/workflows/orchestration.md` + `.claude/workflows/scrum-master-workflow.md`
- **Planning Task**: Read `.claude/workflows/team-leader-workflow.md`
- **Implementing Feature**: Read `.claude/workflows/python-expert-workflow.md`
- **Writing Tests**: Read `.claude/workflows/testing-expert-workflow.md`
- **Need Database Help**: Check `.claude/agents/database-expert.md`

---

## Next Steps

1. **Read the workflow files**: Start with `.claude/README.md` for navigation
2. **Understand your role**: Read the specific workflow for your agent type
3. **Check current state**: Look at kanban board (`backlog/03_kanban/`)
4. **Review critical issues**: Read `CRITICAL_ISSUES.md` to avoid past mistakes
5. **Start working**: Follow your workflow's step-by-step process

---

**Remember**: Quality over speed. It's better to implement one task correctly than five tasks incorrectly.

**Last Updated**: 2025-10-20
**Maintained By**: DemeterAI Engineering Team
