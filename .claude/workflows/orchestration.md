# Agent Orchestration Workflow

**Version**: 1.0
**Last Updated**: 2025-10-20

---

## Overview

This document explains how the 6 agents work together to implement tasks in the DemeterAI v2.0 project.

**The Agents**:
1. **Scrum Master** - Project state and backlog management
2. **Team Leader** - Task planning and quality gates
3. **Python Expert** - Code implementation
4. **Testing Expert** - Test writing (parallel with Python Expert)
5. **Database Expert** - Schema guidance (on-call)
6. **Git Commit Agent** - Commit creation after approval

---

## Complete Workflow (Start to Finish)

### Phase 1: Project State (Scrum Master)

**Trigger**: User wants to start working or plan an epic

**Scrum Master Actions**:
```bash
# 1. Read current sprint
cat backlog/01_sprints/sprint-03-services/sprint-goal.md

# 2. Check kanban board
ls backlog/03_kanban/*/

# 3. Identify blockers and dependencies
grep "Blocked by" backlog/03_kanban/00_backlog/*.md

# 4. Report state to user
echo "Sprint 03: 42 tasks, 5 ready, 3 in-progress, 2 blocked"
```

**Output**: State report showing:
- Current sprint and goals
- Tasks ready for implementation
- Tasks in progress
- Blockers
- Critical path items

**Next**: Scrum Master delegates ready tasks to Team Leader

---

### Phase 2: Task Planning (Team Leader)

**Trigger**: Scrum Master delegates a task from `01_ready/`

**Team Leader Actions**:
```bash
# 1. Read task file
cat backlog/03_kanban/01_ready/S001-stock-movement-service.md

# 2. Read existing code to understand current state
cat app/services/*.py
cat app/models/*.py
cat database/database.mmd

# 3. Create Mini-Plan (detailed architecture plan)
cat >> backlog/03_kanban/01_ready/S001-*.md <<EOF
## Team Leader Mini-Plan ($(date))

### Task Overview
- Card: S001 - StockMovementService
- Epic: epic-004 (Services Layer)
- Priority: HIGH
- Complexity: 8 points

### Architecture
Layer: Service (Application Layer)
Pattern: Service→Service communication

Dependencies:
- Own repository: StockMovementRepository (R003) ✅
- Other services: ConfigService (S028) ❌ blocked
- NEVER: Direct access to ConfigRepository

### Files to Create/Modify
- [ ] app/services/stock_movement_service.py (~150 lines)
- [ ] tests/unit/services/test_stock_movement_service.py (~200 lines)
- [ ] tests/integration/test_stock_movement_api.py (~150 lines)

### Database Access
Tables involved:
- stock_movements (primary)
- Via ConfigService: storage_location_config

See: database/database.mmd (lines 245-280)

### Implementation Strategy
1. Python Expert: Implement service (2-3 hours)
2. Testing Expert: Write tests in PARALLEL (2-3 hours)
3. Team Leader: Review code + tests
4. Team Leader: Run quality gates
5. Team Leader: Approve or request changes

### Acceptance Criteria
- [ ] Service implements create_manual_initialization()
- [ ] Calls ConfigService (NOT ConfigRepository)
- [ ] Unit tests ≥80% coverage
- [ ] Integration tests pass
EOF

# 4. Move to in-progress
mv backlog/03_kanban/01_ready/S001-*.md backlog/03_kanban/02_in-progress/
```

**Output**: Mini-Plan appended to task file

**Next**: Team Leader spawns specialists

---

### Phase 3: Parallel Implementation

**Trigger**: Team Leader spawns Python Expert + Testing Expert

#### Python Expert Thread

```bash
# 1. Read Mini-Plan
cat backlog/03_kanban/02_in-progress/S001-*.md

# 2. Read existing code (NEVER assume!)
cat app/services/config_service.py  # What methods exist?
cat app/models/stock_movement.py     # What fields exist?

# 3. Read database schema
cat database/database.mmd | grep -A 20 "stock_movements"

# 4. Implement service
cat > app/services/stock_movement_service.py <<EOF
from typing import Optional
from app.repositories.stock_movement_repository import StockMovementRepository
from app.services.config_service import ConfigService
from app.schemas.stock_movement import CreateRequest, StockMovementResponse

class StockMovementService:
    def __init__(
        self,
        repo: StockMovementRepository,
        config_service: ConfigService  # ✅ Service, NOT Repository
    ):
        self.repo = repo
        self.config_service = config_service

    async def create_manual_initialization(
        self, request: CreateRequest
    ) -> StockMovementResponse:
        """Create manual stock initialization movement."""
        # Get config via service (NOT repository)
        config = await self.config_service.get_by_location(
            request.storage_location_id
        )

        # Validate product match
        if config.product_id != request.product_id:
            raise ProductMismatchException(...)

        # Create via own repository
        movement = await self.repo.create(request)

        return StockMovementResponse.model_validate(movement)
EOF

# 5. Verify imports work
python -c "from app.services.stock_movement_service import StockMovementService"

# 6. Update task file
cat >> backlog/03_kanban/02_in-progress/S001-*.md <<EOF
## Python Expert Progress ($(date))
Status: COMPLETE

Files created:
- app/services/stock_movement_service.py (165 lines)

Verification:
- ✅ Imports work
- ✅ Service→Service pattern used
- ✅ Type hints on all methods
EOF
```

#### Testing Expert Thread (PARALLEL)

```bash
# 1. Read Mini-Plan (same time as Python Expert)
cat backlog/03_kanban/02_in-progress/S001-*.md

# 2. Coordinate with Python Expert for method signatures
# (Can start writing test structure while Python Expert codes)

# 3. Write unit tests (mock dependencies)
cat > tests/unit/services/test_stock_movement_service.py <<EOF
import pytest
from unittest.mock import AsyncMock
from app.services.stock_movement_service import StockMovementService

@pytest.mark.asyncio
async def test_create_manual_initialization():
    # Mock dependencies
    mock_repo = AsyncMock()
    mock_config_service = AsyncMock()

    # Setup mock responses
    mock_config_service.get_by_location.return_value = ConfigMock(
        product_id="PROD-001"
    )

    service = StockMovementService(mock_repo, mock_config_service)

    # Test
    result = await service.create_manual_initialization(request)

    # Verify
    assert result.id is not None
    mock_config_service.get_by_location.assert_called_once()
EOF

# 4. Write integration tests (real database)
cat > tests/integration/test_stock_movement_api.py <<EOF
@pytest.mark.asyncio
async def test_manual_init_workflow(db_session):
    # Setup: Real database records
    config = await create_test_config(db_session)

    # Real services
    service = StockMovementService(
        repo=StockMovementRepository(db_session),
        config_service=ConfigService(...)
    )

    # Test
    result = await service.create_manual_initialization(request)

    # Verify in database
    db_record = await db_session.get(StockMovement, result.id)
    assert db_record is not None
EOF

# 5. Run tests
pytest tests/unit/services/test_stock_movement_service.py -v
pytest tests/integration/test_stock_movement_api.py -v

# 6. Check coverage
pytest --cov=app.services.stock_movement_service --cov-report=term-missing

# 7. Update task file
cat >> backlog/03_kanban/02_in-progress/S001-*.md <<EOF
## Testing Expert Progress ($(date))
Status: COMPLETE

Files created:
- tests/unit/services/test_stock_movement_service.py (210 lines, 12 tests)
- tests/integration/test_stock_movement_api.py (155 lines, 5 tests)

Test Results:
- Unit tests: ✅ 12/12 passed
- Integration tests: ✅ 5/5 passed
- Coverage: 85% (target ≥80%)
EOF
```

**Both experts work in parallel** (2-3 hours)

---

### Phase 4: Code Review (Team Leader)

**Trigger**: Both Python Expert and Testing Expert report completion

**Team Leader Actions**:
```bash
# 1. Review Python Expert's code
cat app/services/stock_movement_service.py

# 2. Verify Service→Service pattern
grep -n "Repository" app/services/stock_movement_service.py | grep -v "self.repo"
# Output should be EMPTY (no violations)

# 3. Check type hints
grep "async def" app/services/stock_movement_service.py
# All methods should have return type annotations

# 4. Review Testing Expert's tests
cat tests/unit/services/test_stock_movement_service.py
cat tests/integration/test_stock_movement_api.py

# 5. Run tests manually
pytest tests/unit/services/test_stock_movement_service.py -v
pytest tests/integration/test_stock_movement_api.py -v

# 6. Check coverage
pytest --cov=app.services.stock_movement_service --cov-report=term-missing

# 7. Append review to task
cat >> backlog/03_kanban/02_in-progress/S001-*.md <<EOF
## Team Leader Code Review ($(date))
Status: ✅ APPROVED

Checklist:
- [✅] Service→Service pattern enforced
- [✅] No direct repository access (except self.repo)
- [✅] Type hints on all methods
- [✅] Async/await used correctly
- [✅] Docstrings present

Test Review:
- [✅] Unit tests: 12/12 passed
- [✅] Integration tests: 5/5 passed
- [✅] Coverage: 85% (≥80%)
- [✅] No mocked business logic

Approved for quality gates.
EOF

# 8. Move to code-review stage
mv backlog/03_kanban/02_in-progress/S001-*.md backlog/03_kanban/03_code-review/
```

**If issues found**:
```bash
# Append changes requested
cat >> backlog/03_kanban/02_in-progress/S001-*.md <<EOF
## Team Leader Code Review ($(date))
Status: ❌ NEEDS CHANGES

Issues:
- [ ] Service is calling ConfigRepository directly (line 45)
- [ ] Missing type hint on create() method
- [ ] Coverage only 72% (need ≥80%)

Action: Python Expert + Testing Expert - make changes, then resubmit
EOF

# Keep in 02_in-progress/ until fixed
```

---

### Phase 5: Quality Gates (Team Leader)

**Trigger**: Code review approved, moving to `04_testing/`

**Team Leader Actions**:
```bash
# Move to testing stage
mv backlog/03_kanban/03_code-review/S001-*.md backlog/03_kanban/04_testing/

# Run quality gate script
#!/bin/bash
TASK_FILE="backlog/03_kanban/04_testing/S001-*.md"

echo "Quality Gate Verification"
echo "=========================="

# Gate 1: All acceptance criteria checked
UNCHECKED=$(grep -c "\[ \]" "$TASK_FILE")
if [ $UNCHECKED -eq 0 ]; then
    echo "✅ Gate 1: All criteria checked"
else
    echo "❌ Gate 1: $UNCHECKED unchecked criteria"
    exit 1
fi

# Gate 2: Tests pass
pytest tests/unit/services/test_stock_movement_service.py -q
if [ $? -eq 0 ]; then
    echo "✅ Gate 2: Unit tests pass"
else
    echo "❌ Gate 2: Unit tests failing"
    exit 1
fi

# Gate 3: Integration tests pass
pytest tests/integration/test_stock_movement_api.py -q
if [ $? -eq 0 ]; then
    echo "✅ Gate 3: Integration tests pass"
else
    echo "❌ Gate 3: Integration tests failing"
    exit 1
fi

# Gate 4: Coverage ≥80%
COVERAGE=$(pytest --cov=app.services.stock_movement_service --cov-report=term | grep TOTAL | awk '{print $4}' | sed 's/%//')
if [ $COVERAGE -ge 80 ]; then
    echo "✅ Gate 4: Coverage $COVERAGE%"
else
    echo "❌ Gate 4: Coverage $COVERAGE% (<80%)"
    exit 1
fi

# Gate 5: No hallucinations
python -c "from app.services.stock_movement_service import StockMovementService"
if [ $? -eq 0 ]; then
    echo "✅ Gate 5: Imports work"
else
    echo "❌ Gate 5: Import errors (hallucinated code)"
    exit 1
fi

echo "✅ ALL QUALITY GATES PASSED"

# Append approval to task
cat >> "$TASK_FILE" <<EOF
## Team Leader Final Approval ($(date))
Status: ✅ READY FOR COMPLETION

Quality Gates Summary:
- [✅] All acceptance criteria checked
- [✅] Unit tests pass (12/12)
- [✅] Integration tests pass (5/5)
- [✅] Coverage: 85% (≥80%)
- [✅] Code review approved
- [✅] No hallucinations

Files Modified:
- app/services/stock_movement_service.py (created, 165 lines)
- tests/unit/services/test_stock_movement_service.py (created, 210 lines)
- tests/integration/test_stock_movement_api.py (created, 155 lines)

Next: Invoke Git Commit Agent
EOF
```

**If gates fail**: Keep in `04_testing/`, send back to specialists

---

### Phase 6: Git Commit (Git Commit Agent)

**Trigger**: Team Leader approves completion

**Git Commit Agent Actions**:
```bash
# 1. Review changes
git status
git diff

# 2. Stage files
git add app/services/stock_movement_service.py
git add tests/unit/services/test_stock_movement_service.py
git add tests/integration/test_stock_movement_api.py

# 3. Create commit
git commit -m "feat(services): implement StockMovementService (S001)

- Add StockMovementService with manual initialization
- Implement Service→Service pattern (calls ConfigService)
- Add unit tests with 85% coverage (12 tests)
- Add integration tests with real DB (5 tests)
- Validate product_id matches location config

Closes S001

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>"

# 4. Get commit SHA
COMMIT_SHA=$(git rev-parse HEAD)

# 5. Update task file
cat >> backlog/03_kanban/04_testing/S001-*.md <<EOF
## Git Commit Agent ($(date))
Commit: $COMMIT_SHA

feat(services): implement StockMovementService (S001)
EOF
```

---

### Phase 7: Task Completion (Team Leader)

**Trigger**: Git commit created

**Team Leader Actions**:
```bash
# 1. Move to done
mv backlog/03_kanban/04_testing/S001-*.md backlog/03_kanban/05_done/

# 2. Update status file
echo "✅ S001: StockMovementService - COMPLETED ($(date +%Y-%m-%d))" >> backlog/03_kanban/DATABASE_CARDS_STATUS.md

# 3. Report to Scrum Master
cat >> backlog/03_kanban/05_done/S001-*.md <<EOF
## Team Leader → Scrum Master ($(date))
Task: S001 - StockMovementService
Status: ✅ COMPLETED

Summary:
Implemented StockMovementService with manual initialization workflow.
All quality gates passed. Tests achieve 85% coverage.

Deliverables:
- Service class: app/services/stock_movement_service.py
- Unit tests: tests/unit/services/test_stock_movement_service.py
- Integration tests: tests/integration/test_stock_movement_api.py
- Git commit: $COMMIT_SHA

Dependencies Unblocked:
- S002: StockBatchService (was blocked by S001)

Action for Scrum Master: Move S002 to ready queue
EOF
```

---

### Phase 8: Dependency Management (Scrum Master)

**Trigger**: Team Leader reports completion

**Scrum Master Actions**:
```bash
# 1. Read completion note
cat backlog/03_kanban/05_done/S001-*.md | grep "Dependencies Unblocked"

# 2. Check if S002 dependencies are now satisfied
grep "Blocked by" backlog/03_kanban/00_backlog/S002-*.md
# Output: "Blocked by: S001 ✅"

# 3. Move unblocked tasks to ready
mv backlog/03_kanban/00_backlog/S002-*.md backlog/03_kanban/01_ready/

# 4. Update status
sed -i 's/⛔ S002: Blocked/✅ S002: Ready/' backlog/03_kanban/DATABASE_CARDS_STATUS.md

# 5. Report to user
echo "Sprint 03 Progress: 1 task complete, S002 now ready"
```

---

## Communication Patterns

### Team Leader → Python Expert

**Format**:
```markdown
## Team Leader → Python Expert (YYYY-MM-DD)
Task file: backlog/03_kanban/02_in-progress/S001-*.md

Implement: StockMovementService

Requirements:
- Template: backlog/04_templates/starter-code/base_service.py
- Architecture: Service→Service (NO Service→OtherRepo)
- Type hints required
- Async methods
- Business exceptions

Read existing code FIRST:
- app/services/config_service.py (to understand interface)
- app/models/stock_movement.py (to understand fields)
- database/database.mmd (to verify schema)

Start now (parallel with Testing Expert)
```

### Team Leader → Testing Expert

**Format**:
```markdown
## Team Leader → Testing Expert (YYYY-MM-DD)
Task file: backlog/03_kanban/02_in-progress/S001-*.md

Test: StockMovementService

Requirements:
- Unit tests: Mock dependencies (ConfigService)
- Integration tests: Real testing DB
- Target: ≥80% coverage
- Test manual_init workflow completely

Coordinate with Python Expert for method signatures.

Start now (parallel with Python Expert)
```

### Python Expert → Team Leader

**Format**:
```markdown
## Python Expert → Team Leader (YYYY-MM-DD)
Status: COMPLETE

Files created:
- app/services/stock_movement_service.py (165 lines)

Verification:
- ✅ Imports work: python -c "from app.services.stock_movement_service import *"
- ✅ Service→Service pattern used
- ✅ Type hints on all methods
- ✅ Follows Clean Architecture

Ready for review.
```

### Testing Expert → Team Leader

**Format**:
```markdown
## Testing Expert → Team Leader (YYYY-MM-DD)
Status: COMPLETE

Files created:
- tests/unit/services/test_stock_movement_service.py (210 lines, 12 tests)
- tests/integration/test_stock_movement_api.py (155 lines, 5 tests)

Test Results:
- Unit tests: ✅ 12/12 passed
- Integration tests: ✅ 5/5 passed
- Coverage: 85% (target ≥80%)

Command to verify:
pytest tests/unit/services/test_stock_movement_service.py -v

Ready for review.
```

---

## Escalation Patterns

### When Python Expert is Blocked

**Python Expert**:
```markdown
## Python Expert → Database Expert (YYYY-MM-DD)
BLOCKED: Need schema clarification

Question: Is storage_location_id UUID or INT?
Context: Implementing StockMovementService
File: database/database.mmd (line ~250)

Urgency: HIGH (blocking implementation)
```

**Database Expert**:
```markdown
## Database Expert → Python Expert (YYYY-MM-DD)
Answer: storage_location_id is UUID

See: database/database.mmd line 267
Type: UUID (references storage_locations.id)
Index: B-tree index on storage_location_id

Example usage:
location_id = UUID("123e4567-e89b-12d3-a456-426614174000")

Unblocked.
```

### When Quality Gates Fail

**Team Leader**:
```markdown
## Team Leader Quality Gate FAILURE (YYYY-MM-DD)

Gate 4: Coverage FAILED
- Current: 72%
- Required: ≥80%
- Missing coverage: Error handling (lines 45-52)

Action Required: Testing Expert
- Add test for ProductMismatchException
- Add test for ConfigService network failure

Task remains in 04_testing/ until fixed.
```

---

## Anti-Patterns (AVOID)

### Anti-Pattern 1: Skipping Mini-Plan

❌ **WRONG**:
```
User: "Implement S001"
Team Leader: [immediately spawns Python Expert]
```

✅ **CORRECT**:
```
User: "Implement S001"
Team Leader: [reads task, reads existing code, creates Mini-Plan]
Team Leader: [spawns Python Expert with detailed plan]
```

### Anti-Pattern 2: Sequential Instead of Parallel

❌ **WRONG**:
```
Team Leader: [spawns Python Expert]
[waits 3 hours]
Team Leader: [spawns Testing Expert]
[waits 2 more hours]
Total: 5 hours
```

✅ **CORRECT**:
```
Team Leader: [spawns Python Expert + Testing Expert simultaneously]
[both work in parallel for 3 hours]
Total: 3 hours
```

### Anti-Pattern 3: Assuming Code Exists

❌ **WRONG**:
```python
# Python Expert assumes ConfigService has get_by_location()
config = await self.config_service.get_by_location(...)  # May not exist!
```

✅ **CORRECT**:
```bash
# Python Expert reads existing code first
cat app/services/config_service.py | grep "def get"
# Output: "async def get_by_id()", "async def get_by_location()"
# ✅ Method exists, safe to use
```

### Anti-Pattern 4: Marking Tests as Passing Without Running

❌ **WRONG**:
```markdown
Test Results:
- Unit tests: ✅ 12/12 passed (assumed)
```

✅ **CORRECT**:
```bash
# Testing Expert ACTUALLY runs tests
pytest tests/unit/services/test_stock_movement_service.py -v
# ========================= 12 passed in 2.34s =========================

# Then updates task file with ACTUAL results
```

---

## Summary Checklist

Before moving a task to `05_done/`, verify:

- [ ] Scrum Master identified task as ready
- [ ] Team Leader created detailed Mini-Plan
- [ ] Python Expert implemented code (verified imports work)
- [ ] Testing Expert wrote tests (verified tests pass)
- [ ] Team Leader reviewed code (Service→Service pattern enforced)
- [ ] Team Leader reviewed tests (coverage ≥80%)
- [ ] All quality gates passed (actually ran pytest)
- [ ] Git Commit Agent created commit
- [ ] Team Leader moved to done
- [ ] Scrum Master unblocked dependent tasks

**Only then is the task truly complete.**

---

**Last Updated**: 2025-10-20
**Maintained By**: DemeterAI Engineering Team
