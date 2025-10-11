# DemeterAI Multi-Agent System

**Version:** 1.0
**Last Updated:** 2025-10-11
**Project:** DemeterAI v2.0 Backend Implementation

---

## Overview

This folder contains a **stateless multi-agent system** designed to implement the DemeterAI v2.0 backend using a **local file-based Kanban workflow**. The system coordinates 6 specialized Claude Code agents that work together to transform 229 tasks across 17 epics into production-ready code.

### Key Features

- **Stateless**: All state stored in markdown files and progress trackers
- **Local**: No external dependencies (Notion, JIRA, etc.) - pure file-based system
- **Parallel**: Python Expert + Testing Expert work simultaneously
- **Quality-gated**: Team Leader enforces ≥80% coverage, tests pass, code review
- **Automated**: Slash commands for common workflows
- **Traceable**: Complete audit trail in task files and git commits

---

## Quick Start

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

| Agent | Responsibility | When to Use |
|-------|---------------|-------------|
| **Scrum Master** | Project orchestration, backlog management | Planning, status tracking, epic decomposition |
| **Team Leader** | Task planning, quality gates, coordination | Starting tasks, reviewing code, enforcing standards |
| **Python Expert** | Code implementation (controllers/services/repositories) | Writing backend Python code |
| **Database Expert** | Schema guidance, migration proposals | DB questions, PostGIS queries, indexing advice |
| **Testing Expert** | Unit & integration tests, coverage verification | Writing tests (parallel with implementation) |
| **Git Commit Agent** | Commit creation, conventional commits | After Team Leader approves completion |

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

| Epic | Name | Cards | Points | Status |
|------|------|-------|--------|--------|
| epic-001 | Foundation | 12 | 45 | Planning |
| epic-002 | Database Models | 32 | 150 | In Progress |
| epic-003 | Repositories | 28 | 120 | Planning |
| epic-004 | Services | 42 | 210 | Planning |
| epic-005 | Controllers | 26 | 110 | Planning |
| ... | ... | ... | ... | ... |

### Agent Statistics (Example)

After implementing S001:
- **Python Expert**: 165 lines written
- **Testing Expert**: 365 lines written (210 unit + 155 integration)
- **Code Review**: 1 pass
- **Coverage**: 84%
- **Time**: 2.5 hours
- **Quality Gates**: 5/5 passed

---

## Further Reading

### Documentation References
- **CLAUDE.md**: System prompt and validation rules
- **engineering_plan/**: Complete architecture documentation
- **database/database.mmd**: ERD source of truth
- **flows/**: Detailed workflow diagrams
- **backlog/02_epics/**: Epic definitions
- **backlog/04_templates/**: Code templates

### Agent Definitions
- **agents/scrum-master.md**: Project orchestration
- **agents/team-leader.md**: Planning & quality gates
- **agents/python-expert.md**: Code implementation
- **agents/database-expert.md**: Schema guidance
- **agents/testing-expert.md**: Test writing
- **agents/git-commit-writer.md**: Commit creation

### Commands
- **commands/plan-epic.md**: Epic decomposition
- **commands/start-task.md**: Task initiation
- **commands/review-task.md**: Quality verification
- **commands/complete-task.md**: Task finalization

### Templates
- **templates/task-progress-update.md**: Progress notes
- **templates/mini-plan-template.md**: Planning format
- **templates/handoff-note.md**: Agent communication

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
  - 6 agents (Scrum Master, Team Leader, Python Expert, Database Expert, Testing Expert, Git Commit Agent)
  - 4 slash commands (plan-epic, start-task, review-task, complete-task)
  - 3 templates (progress update, mini-plan, handoff note)
  - File-based Kanban workflow
  - Quality gates (≥80% coverage)

---

**Maintained By**: DemeterAI Engineering Team
**Repository**: DemeterDocs
**Last Updated**: 2025-10-11
