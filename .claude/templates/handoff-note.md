# Agent Handoff Note Template

**Use this template when one agent needs to communicate with another.**

---

## [From Agent] → [To Agent] (YYYY-MM-DD HH:MM)

**From**: [Agent Name/Role]
**To**: [Target Agent Name/Role]
**Task**: [CARD-ID] – [Task Title]
**File**: backlog/03_kanban/[folder]/[task-file].md

### Need

[What the target agent needs to do - be specific]

### Context

- [Context point 1]
- [Context point 2]
- [Context point 3]

### Inputs Provided

- [Link to docs/files/data available]
- [Template or starter code]
- [Database schema references]

### Done So Far

- [✅] [Completed item 1]
- [✅] [Completed item 2]
- [In progress] [Current work item]

### Acceptance Criteria / Expected Output

- [ ] [Specific deliverable 1]
- [ ] [Specific deliverable 2]
- [ ] [Quality standard to meet]

### Blockers / Questions

[Any known issues or questions the target agent should address]

### Urgency

[IMMEDIATE | URGENT | NORMAL | LOW] - [Brief explanation why]

---

## Example Usage Scenarios

### 1. Team Leader → Python Expert

```markdown
## Team Leader → Python Expert (2025-10-11 14:45)

**From**: Team Leader
**To**: Python Expert
**Task**: S001 – StockMovementService
**File**: backlog/03_kanban/02_in-progress/S001-stock-movement-service.md

### Need
Implement StockMovementService following Clean Architecture pattern with Service→Service communication (CRITICAL: NO direct repo access to other services' repositories).

### Context
- This is core stock management functionality
- Part of manual initialization workflow
- Depends on ConfigService (S028) and BatchService (S002)
- See engineering_plan/workflows/manual_initialization.md for full workflow

### Inputs Provided
- Template: backlog/04_templates/starter-code/base_service.py
- Architecture: engineering_plan/03_architecture_overview.md (Service→Service pattern)
- Database: database/database.mmd (stock_movements table, lines 245-280)
- Mini-Plan: See task file (above)

### Done So Far
- [✅] Task moved to in-progress
- [✅] Mini-Plan created
- [✅] Dependencies verified (ConfigService, BatchService)
- [In progress] Spawning Testing Expert (parallel work)

### Acceptance Criteria
- [ ] Service class: `app/services/stock_movement_service.py`
- [ ] Method: `create_manual_initialization(request)` implemented
- [ ] Calls ConfigService.get_by_location() (NOT ConfigRepository)
- [ ] Calls BatchService.create_from_movement() (NOT BatchRepository)
- [ ] Returns Pydantic schema (StockMovementResponse)
- [ ] Type hints on all methods
- [ ] Async/await throughout
- [ ] Business exceptions (ProductMismatchException, etc.)

### Blockers / Questions
None identified. If you need schema clarifications, ask Database Expert.

### Urgency
HIGH - Critical path item, blocking S002 and S003

**Start now** (Testing Expert working in parallel)
```

### 2. Python Expert → Team Leader (Completion Report)

```markdown
## Python Expert → Team Leader (2025-10-11 17:15)

**From**: Python Expert
**To**: Team Leader
**Task**: S001 – StockMovementService
**File**: backlog/03_kanban/02_in-progress/S001-stock-movement-service.md

### Need
Code review and approval for StockMovementService implementation.

### Context
- Implementation complete (165 lines)
- All acceptance criteria met
- Service→Service pattern enforced
- Ready for quality gates

### Inputs Provided
- **Service file**: app/services/stock_movement_service.py (165 lines)
- **Test coordination**: Shared method signatures with Testing Expert
- **Documentation**: Docstrings for all public methods

### Done So Far
- [✅] Implemented StockMovementService class
- [✅] Method: create_manual_initialization(request)
- [✅] Service→Service communication (ConfigService, BatchService)
- [✅] Business validations (ProductMismatchException, ConfigNotFoundException)
- [✅] Type hints on all methods
- [✅] Async/await throughout
- [✅] Error handling for network failures
- [✅] Structured logging

### Acceptance Criteria Status
- [✅] Service class created
- [✅] create_manual_initialization method implemented
- [✅] Calls ConfigService (NOT repo)
- [✅] Calls BatchService (NOT repo)
- [✅] Returns Pydantic schema
- [✅] Type hints present
- [✅] Async methods
- [✅] Business exceptions

### Review Checklist
- [✅] Service→Service pattern enforced (no direct repo access)
- [✅] Type hints on all public methods
- [✅] Async/await used correctly
- [✅] Business exceptions (ProductMismatchException, etc.)
- [✅] Pydantic schemas returned (not SQLAlchemy models)
- [✅] Docstrings present (8 methods documented)
- [✅] No TODO/FIXME in production code

### Urgency
NORMAL - Ready for review when you're available

**Status**: ✅ READY FOR REVIEW
```

### 3. Testing Expert → Python Expert (Coordination)

```markdown
## Testing Expert → Python Expert (2025-10-11 15:00)

**From**: Testing Expert
**To**: Python Expert
**Task**: S001 – StockMovementService
**File**: backlog/03_kanban/02_in-progress/S001-stock-movement-service.md

### Need
Confirmation of method signatures for test scaffolds.

### Context
- Writing tests in parallel with your implementation
- Need stable interfaces to finalize mocks
- Can adjust tests later if signatures change

### Inputs Provided
- **Test scaffolds**: tests/unit/services/test_stock_movement_service.py (50% complete)
- **Mock fixtures**: ConfigService, BatchService mocks ready

### Done So Far
- [✅] Unit test structure (12 tests planned)
- [✅] Mock fixtures for dependencies
- [In progress] Finalizing test assertions

### Questions
1. **Method signature confirmed**:
   ```python
   async def create_manual_initialization(
       self,
       request: ManualStockInitRequest
   ) -> StockMovementResponse:
   ```

Is this still accurate?

2. **Exceptions**: Which exceptions does the method raise?
    - ProductMismatchException?
    - ConfigNotFoundException?
    - InvalidQuantityException?
    - Others?

3. **Return value**: Confirmed returning `StockMovementResponse` (Pydantic schema)?

### Urgency

NORMAL - Need answers within 15 minutes to stay on schedule

**Reply in task file** when you have a moment.

```

### 4. Team Leader → Database Expert (Schema Question)

```markdown
## Team Leader → Database Expert (2025-10-11 14:50)

**From**: Team Leader
**To**: Database Expert
**Task**: S001 – StockMovementService
**File**: backlog/03_kanban/02_in-progress/S001-stock-movement-service.md

### Need
Clarification on stock_movements table schema (blocking Python Expert).

### Context
- Python Expert needs to implement create_manual_initialization
- Unclear on UUID vs SERIAL usage
- Needs to know auto-generated columns

### Questions
1. Is `storage_location_id` UUID or INT?
2. Is `movement_id` the primary key or is `id` the PK?
3. Is `created_at` auto-generated or must we set it?
4. Is `batch_id` NULL initially (set later) or required on INSERT?

### Inputs Provided
- **Schema reference**: database/database.mmd (lines 245-280)
- **Task context**: Manual stock initialization workflow

### Urgency
HIGH - Blocking Python Expert implementation

**Please respond in task file within 10 minutes.**
```

---

## Usage Instructions

1. **Copy template** to your working document
2. **Fill all sections** (don't skip any)
3. **Be specific**: Provide exact file paths, line numbers, method signatures
4. **Append to task file**:
   ```bash
   cat >> backlog/03_kanban/[folder]/[task-file].md <<EOF
   [your handoff note]
   EOF
   ```
5. **Tag recipient** clearly in the header
6. **Set urgency** appropriately
7. **Follow up** if no response within expected timeframe

---

## Best Practices

- **Be concise but complete**: Include all necessary context
- **Link to resources**: Provide exact file paths and documentation links
- **State expectations clearly**: What exactly do you need?
- **Include context**: Why is this needed? What's the bigger picture?
- **Set realistic urgency**: Don't mark everything as URGENT
- **Update task file**: Always append handoffs to the task file for traceability
