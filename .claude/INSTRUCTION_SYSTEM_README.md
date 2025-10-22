# Instruction System Overview - v3.0

**Created**: 2025-10-20
**Purpose**: Comprehensive guide to the new development-focused instruction system

---

## What Changed

### Before (v2.2)

- **Focus**: Documentation and Mermaid diagrams
- **Workflow**: Plan → Execute (for documentation)
- **Agent System**: Basic, not well-defined
- **Quality Control**: Manual, inconsistent
- **Problem**: Sprint 02 had 70/386 tests failing (marked as passing)

### After (v3.0)

- **Focus**: Full-stack development (Services, Controllers, Repositories)
- **Workflow**: Scrum Master → Team Leader → Parallel Specialists → Quality Gates
- **Agent System**: 6 specialized agents with clear workflows
- **Quality Control**: Mandatory gates, automated verification
- **Prevention**: Comprehensive rules to prevent Sprint 02 issues

---

## File Structure

```
DemeterDocs/
├── CLAUDE.md                           ← MAIN ENTRY POINT (read this first!)
├── CRITICAL_ISSUES.md                  ← Sprint 02 lessons learned
├── .claude/
│   ├── README.md                       ← Multi-agent system overview
│   ├── INSTRUCTION_SYSTEM_README.md   ← THIS FILE
│   ├── workflows/
│   │   ├── orchestration.md           ← How agents coordinate (read second!)
│   │   ├── scrum-master-workflow.md   ← Project state management
│   │   ├── team-leader-workflow.md    ← Task planning & quality gates
│   │   ├── python-expert-workflow.md  ← Clean Architecture implementation
│   │   └── testing-expert-workflow.md ← Real database testing
│   ├── agents/                        ← Agent definitions (existing)
│   ├── commands/                      ← Slash commands (existing)
│   └── templates/                     ← Task templates (existing)
```

---

## Quick Start Guide

### For New Users

**Step 1**: Read CLAUDE.md

- Main instructions
- Critical rules
- Quality gates checklist
- Technology stack

**Step 2**: Read orchestration.md

- How the 6 agents work together
- Complete workflow (start to finish)
- Communication patterns

**Step 3**: Read your role's workflow

- Scrum Master: Sprint planning, backlog management
- Team Leader: Task planning, quality gates
- Python Expert: Code implementation
- Testing Expert: Test writing

### For Existing Users

**If you're familiar with the old system**:

1. OLD: CLAUDE.md was for Mermaid documentation
    - NEW: CLAUDE.md is for full development workflow

2. OLD: Agents were vaguely defined
    - NEW: 5 detailed workflow files (one per role)

3. OLD: Tests were mocked, marked as passing
    - NEW: Tests must actually pass (pytest verification required)

4. OLD: Quality gates were optional
    - NEW: Quality gates are mandatory (all must pass)

---

## The 6 Agents

### 1. Scrum Master

**File**: `.claude/workflows/scrum-master-workflow.md`
**Role**: Project orchestration, backlog management
**Use when**: Planning sprints, tracking progress, unblocking tasks

**Key Actions**:

- Read current sprint and goals
- Identify ready tasks (no blockers)
- Move tasks through kanban states
- Report project status

### 2. Team Leader

**File**: `.claude/workflows/team-leader-workflow.md`
**Role**: Task planning, quality enforcement
**Use when**: Implementing a task, reviewing code

**Key Actions**:

- Create Mini-Plans (detailed architecture plans)
- Spawn Python Expert + Testing Expert in parallel
- Review code (enforce Service→Service pattern)
- Run quality gates (≥80% coverage, tests pass)
- Approve or reject completion

### 3. Python Expert

**File**: `.claude/workflows/python-expert-workflow.md`
**Role**: Backend code implementation
**Use when**: Writing services, controllers, repositories

**Key Actions**:

- Read existing code (never assume)
- Implement following Clean Architecture (Service→Service)
- Use async/await, type hints, Pydantic schemas
- Verify imports work before completion

### 4. Testing Expert

**File**: `.claude/workflows/testing-expert-workflow.md`
**Role**: Test writing (unit + integration)
**Use when**: Writing tests for services/controllers

**Key Actions**:

- Write unit tests (mock dependencies)
- Write integration tests (real PostgreSQL)
- Achieve ≥80% coverage
- Verify tests ACTUALLY pass (run pytest)

### 5. Database Expert

**File**: `.claude/agents/database-expert.md` (existing)
**Role**: Schema guidance, on-call support
**Use when**: Questions about database schema, PostGIS

### 6. Git Commit Agent

**File**: `.claude/agents/git-commit-writer.md` (existing)
**Role**: Create commits after Team Leader approval
**Use when**: Task complete, all quality gates passed

---

## Critical Rules (NEVER VIOLATE)

### Rule 1: Database as Source of Truth

- `database/database.mmd` is authoritative
- All models must match schema EXACTLY
- Verify table names, column names, data types

**Prevention**:

```bash
cat database/database.mmd | grep -A 30 "table_name"
# Compare with model implementation
```

### Rule 2: Tests Must ACTUALLY Pass

- Sprint 02 issue: 70/386 tests were failing (marked as passing)
- Always run pytest and verify exit code

**Prevention**:

```bash
pytest tests/ -v
EXIT_CODE=$?
if [ $EXIT_CODE -ne 0 ]; then
    echo "❌ Tests failing"
    exit 1
fi
```

### Rule 3: Clean Architecture Patterns

- Service → Service communication ONLY
- NEVER Service → OtherRepository

**Prevention**:

```bash
grep -n "Repository" app/services/example.py | grep -v "self.repo"
# Output should be EMPTY (no violations)
```

### Rule 4: Quality Gates Are Mandatory

**Before ANY task moves to `05_done/`**:

- ✅ All tests pass (verified)
- ✅ Coverage ≥80% (verified)
- ✅ Code review passed
- ✅ No hallucinations (imports work)
- ✅ Schema matches ERD

### Rule 5: No Hallucinations

- Read existing code before implementing
- Don't assume methods exist
- Don't assume relationships exist

**Prevention**:

```bash
# Before implementing
cat app/services/other_service.py
cat app/models/example.py
grep "relationship" app/models/*.py
```

---

## Sprint 02 Critical Issues (Documented in CRITICAL_ISSUES.md)

### Issue 1: Tests Marked Passing When Failing

- **What**: 70/386 tests were failing
- **Why**: Tests were mocked incorrectly
- **Fix**: Always run pytest, verify exit code

### Issue 2: Hallucinated Code

- **What**: Code referenced non-existent relationships
- **Why**: Assumed instead of reading
- **Fix**: Always read existing code first

### Issue 3: Schema Drift

- **What**: Models didn't match database
- **Why**: Implemented from memory
- **Fix**: Always consult database/database.mmd

### Issue 4: Incomplete Coverage

- **What**: Only happy path tested
- **Why**: Didn't test exceptions
- **Fix**: Test all code paths (success, exceptions, edge cases)

### Issue 5: Service→Repository Anti-Pattern

- **What**: Services calling other repositories directly
- **Why**: Didn't understand Clean Architecture
- **Fix**: Enforce Service→Service pattern in code review

---

## Workflow Example (Complete)

**Scenario**: Implement S001 - StockMovementService

### Phase 1: Scrum Master (State)

```bash
# Check current state
cat backlog/03_kanban/DATABASE_CARDS_STATUS.md

# Move S001 to ready (no blockers)
mv backlog/03_kanban/00_backlog/S001-*.md backlog/03_kanban/01_ready/

# Report: "S001 ready for Team Leader"
```

### Phase 2: Team Leader (Planning)

```bash
# Create Mini-Plan
cat >> backlog/03_kanban/01_ready/S001-*.md <<EOF
## Team Leader Mini-Plan
- Architecture: Service layer
- Dependencies: ConfigService, BatchService
- Files: app/services/stock_movement_service.py
- Pattern: Service→Service (NEVER Service→Repo)
EOF

# Move to in-progress
mv backlog/03_kanban/01_ready/S001-*.md backlog/03_kanban/02_in-progress/

# Spawn specialists (parallel)
# → Python Expert: Implement service
# → Testing Expert: Write tests
```

### Phase 3: Parallel Implementation (2-3 hours)

**Python Expert**:

```python
# Read existing code first
cat app/services/config_service.py

# Implement service
class StockMovementService:
    def __init__(self, repo, config_service):  # ✅ Service, NOT repository
        self.config_service = config_service

    async def create(self, request):
        config = await self.config_service.get_by_location(...)  # ✅
```

**Testing Expert** (at same time):

```python
# Write unit tests
@pytest.mark.asyncio
async def test_create_success():
    mock_config = AsyncMock()
    service = StockMovementService(mock_repo, mock_config)
    result = await service.create(request)
    assert result.id is not None

# Write integration tests (real DB)
@pytest.mark.asyncio
async def test_workflow(db_session):
    service = StockMovementService(RealRepo(db_session), RealConfigService(...))
    result = await service.create(request)
    # Verify in database
```

### Phase 4: Team Leader (Review)

```bash
# Review code
grep -n "Repository" app/services/stock_movement_service.py | grep -v "self.repo"
# Empty output ✅

# Run tests
pytest tests/unit/services/test_stock_movement_service.py -v
pytest tests/integration/test_stock_movement_api.py -v
# All pass ✅

# Check coverage
pytest --cov=app.services.stock_movement_service --cov-report=term-missing
# 85% ✅

# Move to testing stage
mv backlog/03_kanban/02_in-progress/S001-*.md backlog/03_kanban/04_testing/
```

### Phase 5: Quality Gates

```bash
# Run quality gate script
./quality_gate_check.sh

# Output:
# ✅ Gate 1: All acceptance criteria checked
# ✅ Gate 2: Unit tests pass (12/12)
# ✅ Gate 3: Integration tests pass (5/5)
# ✅ Gate 4: Coverage 85% (≥80%)
# ✅ Gate 5: Imports work
# ✅ ALL QUALITY GATES PASSED
```

### Phase 6: Git Commit

```bash
git commit -m "feat(services): implement StockMovementService (S001)

- Add StockMovementService with manual initialization
- Implement Service→Service pattern
- Add unit tests (85% coverage)
- Add integration tests (real DB)

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>"
```

### Phase 7: Completion

```bash
# Move to done
mv backlog/03_kanban/04_testing/S001-*.md backlog/03_kanban/05_done/

# Update status
echo "✅ S001: COMPLETE" >> backlog/03_kanban/DATABASE_CARDS_STATUS.md

# Scrum Master: Unblock dependent tasks
mv backlog/03_kanban/00_backlog/S002-*.md backlog/03_kanban/01_ready/
```

---

## Key Improvements

### Before v3.0

- Tests marked passing (were actually failing)
- Code hallucinated relationships
- Models didn't match schema
- Service→Repository violations

### After v3.0

- Tests verified (pytest exit code checked)
- Code reads existing files first
- Models compared with ERD
- Service→Service enforced in review

---

## Next Steps

1. **Read CLAUDE.md** - Main entry point
2. **Read orchestration.md** - How agents work together
3. **Read your role's workflow** - Specific instructions
4. **Review CRITICAL_ISSUES.md** - Learn from Sprint 02 mistakes
5. **Start Sprint 03** - Implement services with new workflow

---

## Questions?

**Q: Which file do I read first?**
A: CLAUDE.md (main instructions)

**Q: I'm implementing a service - which workflow?**
A: Python Expert workflow (python-expert-workflow.md)

**Q: I'm writing tests - which workflow?**
A: Testing Expert workflow (testing-expert-workflow.md)

**Q: I'm planning a sprint - which workflow?**
A: Scrum Master workflow (scrum-master-workflow.md)

**Q: What if tests are failing?**
A: See CRITICAL_ISSUES.md Issue 1, then Testing Expert workflow

**Q: How do I prevent hallucinations?**
A: See Python Expert workflow Rule 1 (Read Before Writing)

---

**Version**: 3.0
**Last Updated**: 2025-10-20
**Maintained By**: DemeterAI Engineering Team

---

**Remember**: Quality over speed. The new instruction system prevents Sprint 02 issues from
recurring.
