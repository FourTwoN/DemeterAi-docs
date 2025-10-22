---
description: Complete a task after all quality gates pass - invoke Git Commit Agent, move to done, update status, and unblock dependent tasks. Usage: /complete-task <task-id> (e.g., /complete-task S001)
---

You are the **Team Leader** executing the `/complete-task` command.

## Task

Finalize task `{{task-id}}` and prepare for next tasks.

## Prerequisites

Before running this command, ensure:

- Task is in `04_testing/` folder
- All quality gates passed (via `/review-task`)
- All acceptance criteria checked
- Tests pass with ≥80% coverage

## Steps

### 1. Verify Task Location

```bash
TASK_FILE="backlog/03_kanban/04_testing/{{task-id}}-*.md"

if [ ! -f $TASK_FILE ]; then
    echo "Error: Task {{task-id}} not in 04_testing/ (run /review-task first)"
    exit 1
fi

echo "Found task: $TASK_FILE"
```

### 2. Extract Modified Files

```bash
# Read task file to find modified files
cat "$TASK_FILE" | grep -A 10 "Files Modified\|Files Created" | grep -E "app/|tests/" | awk '{print $2}'

# Example output:
# app/services/stock_movement_service.py
# tests/unit/services/test_stock_movement_service.py
# tests/integration/test_stock_movement_api.py
```

### 3. Invoke Git Commit Agent

```markdown
## Team Leader → Git Commit Agent ($(date +%Y-%m-%d\ %H:%M))
**Task**: {{task-id}} - [Title]
**Files**: [list of modified files]

**Create commit with**:
- Type: feat / fix / refactor (determine from task type)
- Scope: services / controllers / repositories
- Message: [descriptive message from acceptance criteria]

**Link to task**: {{task-id}}

**Git Commit Agent - Please create commit now**
```

### 4. Wait for Git Commit (Git Commit Agent execution)

```bash
# Git Commit Agent will:
# 1. Stage files: git add app/services/... tests/...
# 2. Create commit: git commit -m "feat(services): implement StockMovementService (S001)"
# 3. Return commit SHA

# Example commit:
# feat(services): implement StockMovementService (S001)
#
# - Add manual stock initialization workflow
# - Enforce product/packaging validation
# - Service→Service communication pattern
# - 84% test coverage
#
# 🤖 Generated with Claude Code
# Co-Authored-By: Claude <noreply@anthropic.com>
```

### 5. Record Commit SHA

```markdown
## Git Commit ($(date +%Y-%m-%d\ %H:%M))
**Commit SHA**: [sha from Git Commit Agent]
**Branch**: [branch name]
**Files**:
- app/services/stock_movement_service.py (165 lines)
- tests/unit/services/test_stock_movement_service.py (210 lines)
- tests/integration/test_stock_movement_api.py (155 lines)
```

### 6. Move to Done

```bash
mv "$TASK_FILE" "backlog/03_kanban/05_done/"

echo "✅ Moved {{task-id}} to 05_done/"
```

### 7. Update DATABASE_CARDS_STATUS.md

```bash
cat >> backlog/03_kanban/DATABASE_CARDS_STATUS.md <<EOF

## Task Completion: {{task-id}} ($(date +%Y-%m-%d\ %H:%M))
**Status**: ✅ COMPLETED

### Summary
- Card: {{task-id}} - [Title]
- Epic: [epic-XXX]
- Story Points: [X]
- Time Spent: [estimate based on task complexity]

### Deliverables
- Service: app/services/[name]_service.py
- Tests: tests/unit + tests/integration
- Coverage: [X]% (≥80%)
- Commit: [SHA]

### Quality Metrics
- All acceptance criteria: ✅
- Tests pass: ✅
- Coverage target: ✅
- Code review: ✅

**Dependencies Unblocked**: [list tasks that were blocked by this one]

EOF
```

### 8. Identify and Unblock Dependent Tasks

```bash
# Read epic file to find tasks blocked by {{task-id}}
cat backlog/02_epics/epic-*.md | grep "Blocked by.*{{task-id}}"

# For each blocked task, check if ALL blockers are now done
# If yes, move from 00_backlog/ to 01_ready/

echo "Checking for unblocked tasks..."

# Example: S002 was blocked by S001
# S001 is now done → S002 can move to ready
if [ -f "backlog/03_kanban/00_backlog/S002-*.md" ]; then
    # Check all blockers for S002
    BLOCKERS=$(cat backlog/03_kanban/00_backlog/S002-*.md | grep "Blocked by" | cut -d: -f2)
    ALL_DONE=true

    for BLOCKER in $BLOCKERS; do
        if [ ! -f "backlog/03_kanban/05_done/$BLOCKER-*.md" ]; then
            ALL_DONE=false
            break
        fi
    done

    if [ "$ALL_DONE" = true ]; then
        mv backlog/03_kanban/00_backlog/S002-*.md backlog/03_kanban/01_ready/
        echo "✅ Unblocked and moved to ready: S002"
    fi
fi
```

### 9. Report to Scrum Master

```markdown
## Team Leader → Scrum Master ($(date +%Y-%m-%d\ %H:%M))
**Task**: {{task-id}} - [Title]
**Status**: ✅ COMPLETED

### Summary
Implemented [ServiceName] with [key features].
All quality gates passed. Commit [SHA] created.

### Deliverables
- Service class: app/services/[name]_service.py (165 lines)
- Unit tests: tests/unit/services/test_[name]_service.py (210 lines)
- Integration tests: tests/integration/test_[name]_api.py (155 lines)
- Git commit: [SHA] (feat(services): [message])

### Quality Metrics
- Tests: 17/17 passed
- Coverage: 84% (≥80%) ✅
- Performance: Within targets ✅

### Dependencies Unblocked
- S002: StockBatchService (moved to 01_ready/)
- S003: ManualInitializationService (still blocked by S028)

**Recommendation**: Start S002 next (now unblocked)

**Epic Progress**:
- Completed: [Y] cards ([Y] points)
- In Progress: [Z] cards
- Remaining: [W] cards
- Epic completion: [X]%
```

### 10. Celebrate & Next Steps

```
✅ TASK COMPLETED: {{task-id}}

Summary:
- Moved to: 05_done/
- Commit: [SHA]
- Unblocked: [list]
- Epic progress: [X]%

Ready for next task!

Suggestions:
1. Start S002 (now unblocked, HIGH priority)
2. Continue with S007 (MEDIUM priority, no blockers)
3. Check critical path: S023, S031 (⚡⚡)
```

## Example

**Command**: `/complete-task S001`

**Output**:

```
Verifying task location...
✅ Found: backlog/03_kanban/04_testing/S001-stock-movement-service.md

Extracting modified files...
- app/services/stock_movement_service.py
- tests/unit/services/test_stock_movement_service.py
- tests/integration/test_stock_movement_api.py

Invoking Git Commit Agent...
Creating commit: feat(services): implement StockMovementService (S001)

✅ Commit created: abc123def

Recording commit in task file...

Moving to done...
✅ Moved to: backlog/03_kanban/05_done/S001-stock-movement-service.md

Updating DATABASE_CARDS_STATUS.md...
✅ Updated status tracker

Checking for unblocked tasks...
✅ Unblocked and moved to ready: S002-stock-batch-service.md

Reporting to Scrum Master...

✅ TASK COMPLETED: S001

Summary:
- Title: StockMovementService (8 points)
- Commit: abc123def
- Coverage: 84%
- Unblocked: S002 (StockBatchService)
- Epic progress: 2.4% (1/42 cards)

Next suggestions:
1. /start-task S002 (now unblocked, depends on S001)
2. /start-task S007 (WarehouseService, no blockers)
3. Critical path: S023, S031 (⚡⚡)

Ready for next task!
```
