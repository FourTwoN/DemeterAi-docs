---
description: Start implementing a task - create Mini-Plan, move to in-progress, and spawn Python Expert + Testing Expert in parallel. Usage: /start-task <task-id> (e.g., /start-task S001)
---

You are the **Team Leader** executing the `/start-task` command.

## Task

Begin implementation of task `{{task-id}}` from the ready queue.

## Steps

1. **Locate Task File**:

```bash
# Find task in ready queue
TASK_FILE=$(find backlog/03_kanban/01_ready/ -name "{{task-id}}-*.md")

if [ -z "$TASK_FILE" ]; then
    echo "Error: Task {{task-id}} not found in 01_ready/"
    exit 1
fi
```

2. **Read Task Details**:

```bash
cat "$TASK_FILE"
```

Extract:

- Epic and sprint
- Priority and complexity
- Acceptance criteria
- Dependencies

3. **Create Mini-Plan** (append to task file):

```markdown
## Team Leader Mini-Plan ($(date +%Y-%m-%d\ %H:%M))

### Task Overview
- **Card**: {{task-id}} - [Title]
- **Epic**: [epic-XXX]
- **Priority**: [HIGH/MEDIUM/LOW]
- **Complexity**: [X] points

### Architecture
**Layer**: [Controller/Service/Repository]
**Pattern**: [Clean Architecture principle]
**Dependencies**:
- Own repository: [RepositoryName]
- Other services: [Service1, Service2] (NOT repos!)

### Files to Create/Modify
- [ ] app/[layer]/[name].py (~[X] lines)
- [ ] tests/unit/[layer]/test_[name].py (~[Y] lines)
- [ ] tests/integration/test_[name]_api.py (~[Z] lines)

### Database Access
**Tables involved**:
- [table1] (primary table)
- [table2] (via [Service], NOT direct repo)

**See**: database/database.mmd (lines XXX-YYY)

### Implementation Strategy
1. **Python Expert**: [what to implement]
2. **Testing Expert**: [what to test] (IN PARALLEL)
3. **Database Expert**: On-call for schema questions

### Acceptance Criteria
[Copy from task file, numbered with checkboxes]

### Performance Expectations
- [metric]: <Xms

### Next Steps
1. Move to 02_in-progress/
2. Spawn Python Expert + Testing Expert
3. Monitor progress
```

4. **Move Task to In-Progress**:

```bash
NEW_PATH="backlog/03_kanban/02_in-progress/$(basename "$TASK_FILE")"
mv "$TASK_FILE" "$NEW_PATH"

echo "Moved {{task-id}} to in-progress"
```

5. **Spawn Specialist Agents**:

```markdown
## Team Leader Delegation ($(date +%Y-%m-%d\ %H:%M))

### To Python Expert
**Task**: Implement [ServiceName]
**File**: backlog/03_kanban/02_in-progress/{{task-id}}-*.md
**Template**: backlog/04_templates/starter-code/base_service.py
**Key rules**:
- Service→Service communication ONLY
- Type hints required
- Async methods
- Business exceptions

**Start now** (parallel with Testing Expert)

---

### To Testing Expert
**Task**: Write tests for [ServiceName]
**File**: backlog/03_kanban/02_in-progress/{{task-id}}-*.md
**Template**: backlog/04_templates/test-templates/
**Key rules**:
- Unit tests: Mock dependencies
- Integration tests: Real DB
- Target: ≥80% coverage

**Start now** (parallel with Python Expert)

---

### To Database Expert
**On-call for questions**: database/database.mmd schema clarifications
```

6. **Update Status**:

```bash
echo "▶️ {{task-id}}: Started ($(date +%Y-%m-%d))" >> backlog/03_kanban/DATABASE_CARDS_STATUS.md
```

7. **Report Task Initiation**:
    - Confirm task moved to in-progress
    - Show Mini-Plan summary
    - List spawned agents
    - Provide ETA for completion

## Example

**Command**: `/start-task S001`

**Output**:

```
Located task: backlog/03_kanban/01_ready/S001-stock-movement-service.md

Reading task...
- Card: S001 - StockMovementService
- Epic: epic-004 (Service Layer)
- Priority: HIGH
- Complexity: 8 points

Creating Mini-Plan...

Architecture:
- Layer: Service (Application Layer)
- Pattern: Service→Service communication
- Dependencies: ConfigService (S028), BatchService (S002)

Files to create:
- app/services/stock_movement_service.py (~150 lines)
- tests/unit/services/test_stock_movement_service.py (~200 lines)
- tests/integration/test_stock_movement_api.py (~150 lines)

Moving to in-progress...
✅ Moved to: backlog/03_kanban/02_in-progress/S001-stock-movement-service.md

Spawning agents (PARALLEL):
- Python Expert: Implement StockMovementService
- Testing Expert: Write tests (≥80% coverage)
- Database Expert: On-call for schema questions

Updated DATABASE_CARDS_STATUS.md

Status:
- In Progress: S001
- ETA: 2-3 hours (with parallel development)

Monitoring progress... (agents will report back when complete)
```
