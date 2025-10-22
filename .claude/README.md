# DemeterAI Multi-Agent System & Instruction Index

**Version:** 3.0
**Last Updated:** 2025-10-20
**Project:** DemeterAI v2.0 Backend Implementation
**Phase**: Sprint 03 - Services Layer (42 tasks, 210 story points)
**Status**: Sprint 00-02 ✅ COMPLETE (Sprints 01-02 at critical path)

---

## 📍 WHERE AM I? (Navigation Guide)

**QUICK REFERENCE**: Pick your role, then find your starting file:

| Role                        | Go Here                                        | Then                            | Purpose                        |
|-----------------------------|------------------------------------------------|---------------------------------|--------------------------------|
| **🎯 I'm planning**         | `.claude/workflows/orchestration.md`           | Read top to bottom              | Understand system flow         |
| **📋 I'm managing**         | `.claude/workflows/scrum-master-workflow.md`   | Step 1: Check backlog           | Manage tasks & sprints         |
| **🛠️ I'm implementing**    | `.claude/workflows/python-expert-workflow.md`  | Read mini-plan first            | Write clean architecture code  |
| **✅ I'm testing**           | `.claude/workflows/testing-expert-workflow.md` | Read quality gates              | Write real DB tests (NO MOCKS) |
| **📊 I'm reviewing**        | `.claude/workflows/team-leader-workflow.md`    | Check quality gates             | Review code before merge       |
| **🗄️ I have DB questions** | `../CLAUDE.md` > Search "Rule 1"               | Consult `database/database.mmd` | Get schema authority           |
| **🔴 Something broke**      | `../CRITICAL_ISSUES.md`                        | Read prevention section         | Learn from Sprint 02 mistakes  |

**MAIN ENTRY POINT**: Start by reading `../CLAUDE.md` (15 minute read) - it has everything you need
to know.

---

## Overview

This folder (`/.claude/`) contains all **system instructions and multi-agent coordination** files
for DemeterAI v2.0 development. It's a **stateless, file-based system** that coordinates 6
specialized agents working through a local Kanban board.

### ✨ Key Features

- **🎯 Stateless**: All state in markdown files (no external tools)
- **⚡ Parallel**: Python Expert + Testing Expert work simultaneously
- **✅ Quality-gated**: Team Leader enforces ≥80% coverage + tests pass + code review
- **🔄 Automated**: Slash commands (`/start-task`, `/review-task`, `/complete-task`)
- **📝 Traceable**: Complete audit trail (task files + git commits)
- **🏗️ Clean Architecture**: Service → Service pattern (never violate)
- **🚫 Prevention-Focused**: Critical issues from Sprint 02 documented and prevented

### 📊 Project Status

```
✅ Sprint 00: Foundation (Setup, Docker, Pre-commit hooks)
✅ Sprint 01: Database (27 models, 27 repositories)
✅ Sprint 02: ML Pipeline (5 critical ML services)
→ Sprint 03: Services Layer (42 tasks - ACTIVE NOW)
  → 28 services to implement
  → Service → Service pattern enforcement
  → ≥80% coverage requirement
```

---

## 🚀 Quick Start

### 1. Plan an Epic

```bash
# Break epic into tasks and move unblocked ones to ready queue
/plan-epic epic-004
```

### 2. Start a Task

```bash
# Create Mini-Plan and spawn specialists
/start-task S001
```

### 3. Review Progress

```bash
# Run quality gates and move through stages
/review-task S001
```

### 4. Complete Task

```bash
# Create git commit and unblock dependencies
/complete-task S001
```

---

## Architecture

### Chain of Command

```
┌─────────────────────────────────────────────────────────────┐
│                     SCRUM MASTER                             │
│  - Manages 229 tasks across 17 epics                        │
│  - Breaks epics into atomic tasks                           │
│  - Updates DATABASE_CARDS_STATUS.md                         │
│  - Delegates to Team Leader                                 │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────┐
│                     TEAM LEADER                              │
│  - Creates detailed Mini-Plans                              │
│  - Spawns Python Expert + Testing Expert (parallel)         │
│  - Reviews code and tests                                   │
│  - Enforces quality gates (≥80% coverage)                   │
│  - Gates completion                                         │
└──────┬────────────────────────┬──────────────────────────────┘
       │                        │
       ▼                        ▼
┌──────────────────┐   ┌──────────────────┐
│  PYTHON EXPERT   │   │  TESTING EXPERT  │
│  - Implements    │   │  - Writes tests  │
│  - Controllers   │   │  - Unit tests    │
│  - Services      │   │  - Integration   │
│  - Repositories  │   │  - ≥80% coverage │
└────────┬─────────┘   └────────┬─────────┘
         │                      │
         └──────────┬───────────┘
                    │
                    ▼
         ┌─────────────────────┐
         │   DATABASE EXPERT   │
         │   - Schema advice   │
         │   - On-call for     │
         │     questions       │
         └──────────┬──────────┘
                    │
                    ▼
           ┌────────────────────┐
           │  GIT COMMIT AGENT  │
           │  - Creates commits │
           │  - Links tasks     │
           └────────────────────┘
```

### Agent Roles

| Agent                | Responsibility                                          | When to Use                                         |
|----------------------|---------------------------------------------------------|-----------------------------------------------------|
| **Scrum Master**     | Project orchestration, backlog management               | Planning, status tracking, epic decomposition       |
| **Team Leader**      | Task planning, quality gates, coordination              | Starting tasks, reviewing code, enforcing standards |
| **Python Expert**    | Code implementation (controllers/services/repositories) | Writing backend Python code                         |
| **Database Expert**  | Schema guidance, migration proposals                    | DB questions, PostGIS queries, indexing advice      |
| **Testing Expert**   | Unit & integration tests, coverage verification         | Writing tests (parallel with implementation)        |
| **Git Commit Agent** | Commit creation, conventional commits                   | After Team Leader approves completion               |

---

## File-Based Kanban System

### Folder Structure

```
backlog/03_kanban/
├── 00_backlog/        ← 229 tasks (not started)
├── 01_ready/          ← Ready for Team Leader
├── 02_in-progress/    ← Currently being coded
├── 03_code-review/    ← Under code review
├── 04_testing/        ← Testing & quality gates
├── 05_done/           ← Completed ✅
├── 06_blocked/        ← Blocked tasks
└── DATABASE_CARDS_STATUS.md  ← Progress tracker
```

### Task Lifecycle

```
00_backlog → 01_ready → 02_in-progress → 03_code-review → 04_testing → 05_done
                                  ↓
                            06_blocked (if issues arise)
```

**State changes** are implemented via `mv` command:

```bash
# Scrum Master: Move to ready
mv backlog/03_kanban/00_backlog/S001-*.md backlog/03_kanban/01_ready/

# Team Leader: Start task
mv backlog/03_kanban/01_ready/S001-*.md backlog/03_kanban/02_in-progress/

# Team Leader: Complete reviews
mv backlog/03_kanban/02_in-progress/S001-*.md backlog/03_kanban/03_code-review/
mv backlog/03_kanban/03_code-review/S001-*.md backlog/03_kanban/04_testing/
mv backlog/03_kanban/04_testing/S001-*.md backlog/03_kanban/05_done/
```

---

## Slash Commands

### `/plan-epic <epic-id>`

**Purpose**: Break epic into atomic tasks and prioritize

**Example**:

```bash
/plan-epic epic-004
```

**What it does**:

1. Reads `backlog/02_epics/epic-004-services.md`
2. Identifies 42 cards (S001-S042)
3. Analyzes dependencies
4. Moves unblocked tasks to `01_ready/`
5. Updates `DATABASE_CARDS_STATUS.md`

**Output**:

- 5 tasks moved to ready queue
- 37 tasks remain blocked
- Critical path items identified

---

### `/start-task <task-id>`

**Purpose**: Begin implementation with Mini-Plan

**Example**:

```bash
/start-task S001
```

**What it does**:

1. Locates task in `01_ready/`
2. Creates detailed Mini-Plan (architecture, files, DB access)
3. Moves to `02_in-progress/`
4. Spawns Python Expert + Testing Expert (parallel)
5. Updates status

**Output**:

- Mini-Plan appended to task file
- Two specialists working in parallel
- ETA provided

---

### `/review-task <task-id>`

**Purpose**: Review code, run tests, enforce quality gates

**Example**:

```bash
/review-task S001
```

**What it does**:

1. Code review (Service→Service pattern, type hints, docstrings)
2. Run tests (unit + integration)
3. Check coverage (≥80%)
4. Move through stages (02 → 03 → 04)
5. Verify all quality gates

**Output**:

- Code review results (✅ APPROVED / ❌ NEEDS CHANGES)
- Test results (X/X passed)
- Coverage percentage
- Task moved to next stage

---

### `/complete-task <task-id>`

**Purpose**: Finalize task after quality gates pass

**Example**:

```bash
/complete-task S001
```

**What it does**:

1. Verify task in `04_testing/` (all gates passed)
2. Invoke Git Commit Agent (create commit)
3. Move to `05_done/`
4. Update `DATABASE_CARDS_STATUS.md`
5. Unblock dependent tasks

**Output**:

- Git commit SHA
- Task moved to done
- Dependent tasks moved to ready
- Epic progress percentage

---

## Task File Format

Each task is a markdown file with standard structure:

```markdown
# [CARD-ID] Title

## Metadata
- **Epic**: epic-XXX
- **Sprint**: Sprint-XX
- **Priority**: critical/high/medium/low
- **Complexity**: X points
- **Dependencies**: Blocked by [other cards]

## Description
[What needs to be done]

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Coverage ≥80%
- [ ] Tests pass

## Implementation
[Code snippets, examples]

---

## Team Leader Mini-Plan (appended by Team Leader)
[Architecture, files, strategy]

## Python Expert Progress (appended by Python Expert)
[Status updates]

## Testing Expert Progress (appended by Testing Expert)
[Coverage reports]

## Team Leader Code Review (appended by Team Leader)
[Review results]

## Git Commit (appended by Git Commit Agent)
[Commit SHA]
```

---

## Templates

### 1. Task Progress Update

**File**: `.claude/templates/task-progress-update.md`

**Use**: Append to task files every 30-60 minutes

**Example**:

```markdown
## Python Expert Progress Update (2025-10-11 15:30)
**Status**: in-progress

### Work Completed
- [✅] Created app/services/stock_movement_service.py
- [✅] Implemented create_manual_initialization method

### ETA
1 hour
```

---

### 2. Mini-Plan Template

**File**: `.claude/templates/mini-plan-template.md`

**Use**: Team Leader creates before starting task

**Example**:

```markdown
## Team Leader Mini-Plan (2025-10-11 14:30)

### Task Overview
- **Card**: S001 - StockMovementService
- **Priority**: HIGH

### Architecture
- Layer: Service
- Dependencies: ConfigService, BatchService

### Files to Create
- app/services/stock_movement_service.py
- tests/unit/services/test_stock_movement_service.py
```

---

### 3. Handoff Note

**File**: `.claude/templates/handoff-note.md`

**Use**: Agent-to-agent communication

**Example**:

```markdown
## Team Leader → Python Expert (2025-10-11 14:45)

**Task**: S001
**Need**: Implement StockMovementService

### Context
- Critical path item
- See Mini-Plan above

**Start now** (parallel with Testing Expert)
```

---

## Quality Gates

**Before task can move to `05_done/`**, all gates must pass:

### Gate 1: Code Review ✅

- [ ] Service→Service pattern enforced
- [ ] No direct repository access (except `self.repo`)
- [ ] Type hints on all methods
- [ ] Async/await used correctly
- [ ] Business exceptions used
- [ ] Docstrings present

### Gate 2: Unit Tests ✅

- [ ] All unit tests pass
- [ ] Dependencies mocked correctly

### Gate 3: Integration Tests ✅

- [ ] All integration tests pass
- [ ] Real database used

### Gate 4: Coverage ✅

- [ ] Coverage ≥80% for changed code
- [ ] Critical paths covered

### Gate 5: Acceptance Criteria ✅

- [ ] All task criteria checked
- [ ] No TODO/FIXME in production code

---

## Best Practices

### For Scrum Master

- Update `DATABASE_CARDS_STATUS.md` after every task movement
- Check dependencies before moving tasks to ready
- Prioritize critical path items (⚡⚡)
- Verify Team Leader provides "OK" acknowledgment

### For Team Leader

- Create detailed Mini-Plans (don't skip!)
- Spawn Python + Testing Experts in parallel
- Run quality gates BEFORE moving to done
- Never skip code review
- Enforce Service→Service pattern strictly

### For Python Expert

- Always use Service→Service communication
- NEVER call other services' repositories directly
- Use type hints on ALL methods
- Return Pydantic schemas (not SQLAlchemy models)
- Update task file every 30 minutes

### For Testing Expert

- Target ≥80% coverage
- Use real testing DB when possible
- Write tests in parallel with implementation
- Report coverage metrics to Team Leader
- Never modify pipeline code (only tests)

### For Database Expert

- Always consult `database/database.mmd` first
- Never guess schema details
- Propose migrations via new tasks (never direct changes)
- Provide query examples with performance expectations

---

## Example Workflow

### Scenario: Implement StockMovementService (S001)

#### Step 1: Plan Epic

```bash
/plan-epic epic-004
```

**Scrum Master**:

- Reads epic-004-services.md (42 cards)
- Identifies S001 has no blockers
- Moves S001 to `01_ready/`

#### Step 2: Start Task

```bash
/start-task S001
```

**Team Leader**:

- Creates Mini-Plan (architecture, files, DB tables)
- Moves S001 to `02_in-progress/`
- Spawns Python Expert + Testing Expert

#### Step 3: Parallel Work

**Python Expert**:

- Implements `app/services/stock_movement_service.py`
- Follows Service→Service pattern
- Updates task file every 30 min

**Testing Expert**:

- Writes `tests/unit/services/test_stock_movement_service.py`
- Writes `tests/integration/test_stock_movement_api.py`
- Achieves 84% coverage

Both work simultaneously for 2-3 hours.

#### Step 4: Review

```bash
/review-task S001
```

**Team Leader**:

- Code review: ✅ APPROVED (Service→Service enforced)
- Tests run: ✅ 17/17 passed
- Coverage: ✅ 84% (≥80%)
- Moves: 02 → 03 → 04

#### Step 5: Complete

```bash
/complete-task S001
```

**Team Leader**:

- All gates passed
- Invokes Git Commit Agent
- **Git Commit Agent** creates commit: `feat(services): implement StockMovementService (S001)`
- Moves to `05_done/`
- Unblocks S002

**Scrum Master**:

- Updates `DATABASE_CARDS_STATUS.md`
- Moves S002 to `01_ready/` (now unblocked)

---

## Monitoring Progress

### DATABASE_CARDS_STATUS.md

Track overall progress:

```markdown
## Epic-004 Progress (2025-10-11)

### Completed
- ✅ S001: StockMovementService (8pts)
- ✅ S007: WarehouseService (3pts)

### In Progress
- 🔄 S002: StockBatchService (5pts) - Testing stage

### Blocked
- ⛔ S003: ManualInitializationService - Blocked by: S028

### Statistics
- Total: 42 cards (210 points)
- Done: 2 cards (11 points) - 5%
- Remaining: 40 cards (199 points)
```

### Task-Level Progress

Each task file contains complete history:

- Mini-Plan (Team Leader)
- Implementation updates (Python Expert)
- Coverage reports (Testing Expert)
- Code review (Team Leader)
- Commit SHA (Git Commit Agent)

---

## Troubleshooting

### Problem: Task stuck in code review

**Solution**: Run `/review-task <id>` to see what's failing. Common issues:

- Direct repository access (violates Service→Service pattern)
- Missing type hints
- Coverage <80%

### Problem: Tests failing

**Solution**:

1. Check test output in `/review-task`
2. Testing Expert: Fix tests
3. Python Expert: Fix implementation (if bug found)
4. Re-run `/review-task`

### Problem: Task blocked

**Solution**:

1. Scrum Master: Move to `06_blocked/`
2. Add blocker note to task file
3. Create documentation task if needed
4. Unblock when dependency complete

### Problem: Can't find task file

**Solution**:

```bash
find backlog/03_kanban -name "S001-*.md"
```

---

## Statistics & Metrics

### Current Project Status

- **Total Tasks**: 229
- **Epics**: 17
- **Sprints**: 5
- **Story Points**: ~1100+

### Epic Breakdown

| Epic     | Name            | Cards | Points | Status      |
|----------|-----------------|-------|--------|-------------|
| epic-001 | Foundation      | 12    | 45     | Planning    |
| epic-002 | Database Models | 32    | 150    | In Progress |
| epic-003 | Repositories    | 28    | 120    | Planning    |
| epic-004 | Services        | 42    | 210    | Planning    |
| epic-005 | Controllers     | 26    | 110    | Planning    |
| ...      | ...             | ...   | ...    | ...         |

### Agent Statistics (Example)

After implementing S001:

- **Python Expert**: 165 lines written
- **Testing Expert**: 365 lines written (210 unit + 155 integration)
- **Code Review**: 1 pass
- **Coverage**: 84%
- **Time**: 2.5 hours
- **Quality Gates**: 5/5 passed

---

---

## 📚 Complete File Structure Reference

### `.claude/workflows/` - Core Agent Workflows (READ THESE FIRST)

```
workflows/
├── orchestration.md               ← START HERE: Complete system flow & agent coordination
├── scrum-master-workflow.md        ← How to manage sprints, kanban, task decomposition
├── team-leader-workflow.md         ← Mini-plans, quality gates, code review process
├── python-expert-workflow.md       ← Clean Architecture patterns, read-before-write, async
└── testing-expert-workflow.md      ← Real DB testing (NO MOCKS), ≥80% coverage target
```

**When to Read Each**:

- **orchestration.md**: First time? Read this. Always. (774 lines)
- **scrum-master-workflow.md**: Managing tasks? Read this. (343 lines)
- **team-leader-workflow.md**: Planning implementation? Read this. (475 lines)
- **python-expert-workflow.md**: Writing services/controllers? Read this. (461 lines)
- **testing-expert-workflow.md**: Writing tests? Read this. (546 lines)

### `.claude/commands/` - Slash Command Definitions

```
commands/
├── plan-epic.md        # /plan-epic epic-004
├── start-task.md       # /start-task S001
├── review-task.md      # /review-task S001
├── complete-task.md    # /complete-task S001
└── sprint-review.md    # /sprint-review
```

### `.claude/templates/` - Reusable Templates

```
templates/
├── mini-plan-template.md       # Team Leader uses to create implementation plans
├── task-progress-update.md     # Agents append every 30-60 minutes
└── handoff-note.md            # Agent-to-agent communication
```

### `.claude/agents/` - Agent Role Definitions

```
agents/
├── scrum-master.md      # Project orchestration, backlog management
├── team-leader.md       # Planning, review, quality gates
├── python-expert.md     # Code implementation, Clean Architecture
├── testing-expert.md    # Test writing, coverage verification
├── database-expert.md   # Schema guidance, migration proposals
└── git-commit-writer.md # Commit creation, conventional commits
```

---

## 🗂️ Project Structure (For Development Context)

### Source Code (`app/`)

```
app/
├── models/                    # 28 SQLAlchemy models (DB001-DB028)
│   ├── warehouse.py          # (DB001) Geospatial hierarchy root
│   ├── storage_area.py       # (DB002)
│   ├── storage_location.py   # (DB003)
│   ├── storage_bin.py        # (DB004)
│   ├── product_category.py   # (DB015) 3-level taxonomy
│   ├── product_family.py     # (DB016)
│   ├── product.py            # (DB017)
│   ├── stock_batch.py        # (DB007) Stock management
│   ├── stock_movement.py     # (DB008)
│   ├── photo_processing_session.py  # (DB012) ML pipeline
│   ├── detection.py          # (DB013) Partitioned by date
│   ├── estimation.py         # (DB014) Partitioned by date
│   └── [15 more models]
│
├── repositories/              # 27 async repositories (BaseRepository + 26 specialized)
│   ├── base.py              # Generic CRUD: get, get_multi, create, update, delete
│   ├── product_repository.py
│   ├── stock_batch_repository.py
│   └── [24 more repositories]
│
├── services/                 # Services layer (SPRINT 03 - IN PROGRESS)
│   ├── ml_processing/       # ML orchestration services
│   └── __init__.py
│
├── controllers/              # FastAPI route handlers (SPRINT 04+)
│   └── __init__.py
│
├── schemas/                  # Pydantic validation schemas (SPRINT 03+)
│   └── __init__.py
│
├── core/
│   ├── config.py            # Environment configuration
│   ├── exceptions.py        # ⚠️ ALL exceptions must be defined here
│   └── logging.py           # Centralized logging
│
├── db/
│   ├── base.py              # SQLAlchemy Base (all models inherit)
│   └── session.py           # AsyncSession factory
│
├── celery/                  # Async task queue
│   ├── base_tasks.py
│   └── __init__.py
│
├── main.py                  # FastAPI app entry point
└── __init__.py
```

### Database & Migrations

```
database/
├── database.mmd             # ⭐ SOURCE OF TRUTH - Complete ERD (28 models)
└── database.md              # Schema documentation

alembic/
├── versions/                # 14 migration files
│   ├── 6f1b94ebef45_initial_setup_enable_postgis.py
│   ├── 2f68e3f132f5_create_warehouses_table.py
│   ├── 742a3bebd3a8_create_storage_areas_table.py
│   ├── sof6kow8eu3r_create_storage_locations_table.py
│   ├── 1wgcfiexamud_create_storage_bins_table.py
│   ├── 3xy8k1m9n4pq_create_product_states_table.py
│   ├── 4ab9c2d8e5fg_create_product_sizes_table.py
│   ├── 1a2b3c4d5e6f_create_product_families_table.py
│   ├── 0fc9cac096f2_create_product_categories_table.py
│   ├── 5gh9j2n4k7lm_create_products_table.py
│   ├── 440n457t9cnp_create_s3_images_table.py
│   ├── 6kp8m3q9n5rt_create_users_table.py
│   ├── 8807863f7d8c_add_location_relationships_table.py
│   └── 2wh7p3r9bm6t_create_storage_bin_types_table.py
├── env.py                   # Alembic configuration
└── script.py.mako           # Migration template
```

### Backlog & Project Management

```
backlog/
├── 00_epics/               # 17 epic definitions (200+ tasks)
│   ├── epic-001-foundation/
│   ├── epic-002-database/
│   ├── epic-003-repositories/
│   └── [14 more epics]
│
├── 01_sprints/             # Sprint goals and plans
│   ├── sprint-00/          # ✅ Foundation
│   ├── sprint-01/          # ✅ Database Models
│   ├── sprint-02/          # ✅ ML Pipeline
│   └── sprint-03/          # → Services Layer (ACTIVE)
│
├── 03_kanban/              # File-based Kanban board
│   ├── 00_backlog/         # Not started (raw backlog)
│   ├── 01_ready/           # Ready for Team Leader
│   ├── 02_in-progress/     # Currently being implemented
│   ├── 03_code-review/     # Under code review
│   ├── 04_testing/         # Testing & quality gates
│   ├── 05_done/            # ✅ Completed
│   ├── 06_blocked/         # 🔴 Blocked tasks
│   └── DATABASE_CARDS_STATUS.md  # Progress tracker
│
└── 04_templates/           # Code templates for models, services, repos
```

### Tests

```
tests/
├── unit/
│   └── models/            # Model tests (DB001-DB028)
│       ├── test_product.py
│       ├── test_warehouse.py
│       ├── test_stock_batch.py
│       └── [25 more tests]
│
├── integration/           # PostgreSQL integration tests
│   ├── test_product_service.py
│   └── [other integration tests]
│
└── conftest.py            # Shared fixtures
    ├── db_session fixture
    ├── test factories
    └── PostgreSQL setup
```

### Documentation

```
engineering_plan/          # Architecture & design documentation
├── 01_project_overview.md
├── 02_technology_stack.md
├── 03_architecture_overview.md
└── database/
    └── README.md          # Database design philosophy

flows/                     # Business process Mermaid diagrams
├── procesamiento_ml_upload_s3_principal/
├── photo_upload_gallery/
└── [other workflows]

CLAUDE.md                  # ⭐ MAIN INSTRUCTIONS (632 lines)
CRITICAL_ISSUES.md         # Sprint 02 lessons learned & prevention
SPRINT_02_COMPLETE_SUMMARY.md  # Executive summary
```

---

## 📖 Reading Order (Recommended)

### First Time?

1. Read: `../CLAUDE.md` (15 min) - Gets you oriented
2. Read: `./workflows/orchestration.md` (20 min) - Understand system
3. Reference: `./README.md` (this file) - Find what you need

### Starting Work on a Task?

1. Read: `.claude/workflows/team-leader-workflow.md` - Understand planning
2. Read: Task file in `backlog/03_kanban/01_ready/` - Understand requirements
3. Read: Appropriate specialist workflow (Python/Testing) - Follow pattern

### Implementing a Feature?

1. Check: `app/models/` for relevant models
2. Check: `app/repositories/` for available repository methods
3. Read: `.claude/workflows/python-expert-workflow.md` - Follow Clean Architecture
4. Implement: Follow Service → Service pattern STRICTLY
5. Test: Read `.claude/workflows/testing-expert-workflow.md` - Real DB, ≥80% coverage

### Writing Tests?

1. Read: `.claude/workflows/testing-expert-workflow.md`
2. Rule 1: NO MOCKS of business logic
3. Rule 2: Use PostgreSQL real database
4. Rule 3: Target ≥80% coverage
5. Rule 4: Test integration points

---

## 🔧 Common Commands (Quick Reference)

```bash
# CHECK PROJECT STATE
cd /home/lucasg/proyectos/DemeterDocs
ls backlog/03_kanban/01_ready/                 # Tasks ready to start
ls backlog/03_kanban/02_in-progress/           # Currently working
cat backlog/03_kanban/DATABASE_CARDS_STATUS.md # Overall progress

# VERIFY CODE
python -c "from app.models import *; print('✅ Models OK')"
python -c "from app.repositories import *; print('✅ Repos OK')"
python -c "from app.services import *; print('✅ Services OK')"

# RUN TESTS
pytest tests/ -v                                          # All tests
pytest tests/unit/models/ -v                             # Models only
pytest tests/ --cov=app --cov-report=term-missing        # Full coverage

# DATABASE OPERATIONS
alembic current                                           # Current schema version
alembic history                                          # Migration history
docker compose up db_test -d                             # Start test DB

# GIT OPERATIONS
git status                                                # See changes
git log --oneline -10                                    # Recent commits
git diff CLAUDE.md                                       # See changes
```

---

## 🚨 Critical Rules (Never Break These)

### Rule 1: Database Schema is Source of Truth

- File: `database/database.mmd`
- Consult BEFORE implementing
- All models must match EXACTLY

### Rule 2: Service → Service Pattern (NO EXCEPTIONS)

```python
# ❌ WRONG: Service calling other Service's repository
class ProductService:
    def __init__(self, repo, category_repo):  # VIOLATION!
        self.category_repo = category_repo

# ✅ CORRECT: Service calling other Service
class ProductService:
    def __init__(self, repo, category_service):  # ✅ SERVICE
        self.category_service = category_service
```

### Rule 3: Tests MUST Use Real Database

- NO MOCKS of business logic
- Use PostgreSQL real test database
- Target ≥80% coverage

### Rule 4: Quality Gates Are Mandatory

- Tests must PASS (verified by running pytest)
- Coverage must be ≥80% (verified by running pytest --cov)
- Code review must PASS (Service→Service pattern enforced)
- NO hallucinated code (all imports verified)

### Rule 5: Read Before Writing

- Always read existing code first
- Consult database schema (database.mmd)
- Check for existing relationships
- Verify imports work

---

## 🔗 Further Reading

**Main Documentation**: `../CLAUDE.md` - Complete system guide
**Critical Issues**: `../CRITICAL_ISSUES.md` - What went wrong in Sprint 02
**Architecture**: `../engineering_plan/03_architecture_overview.md`
**Database**: `../database/database.mmd` - Entity relationships

---

## Contributing

When creating new agents, commands, or templates:

1. Follow existing format and structure
2. Include detailed examples
3. Document inputs, outputs, and edge cases
4. Test with real tasks before committing
5. Update this README if adding new workflows

---

## Version History

- **v1.0** (2025-10-11): Initial multi-agent system
    - 6 agents (Scrum Master, Team Leader, Python Expert, Database Expert, Testing Expert, Git
      Commit Agent)
    - 4 slash commands (plan-epic, start-task, review-task, complete-task)
    - 3 templates (progress update, mini-plan, handoff note)
    - File-based Kanban workflow
    - Quality gates (≥80% coverage)

---

**Maintained By**: DemeterAI Engineering Team
**Repository**: DemeterDocs
**Last Updated**: 2025-10-11
