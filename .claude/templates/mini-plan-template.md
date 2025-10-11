# Team Leader Mini-Plan Template

**Use this template when starting a new task (via `/start-task`).**

---

## Team Leader Mini-Plan (YYYY-MM-DD HH:MM)

### Task Overview
- **Card**: [CARD-ID] - [Title]
- **Epic**: [epic-XXX] ([Epic Name])
- **Priority**: [CRITICAL ⚡⚡ | HIGH | MEDIUM | LOW]
- **Complexity**: [X] points ([S/M/L/XL])

### Architecture
**Layer**: [Controller | Service | Repository | Model | Test]
**Pattern**: [Clean Architecture principle - describe]
**Dependencies**:
- Own repository: [RepositoryName] ([REPO-CARD-ID])
- Other services: [Service1Name] ([SERVICE1-ID]), [Service2Name] ([SERVICE2-ID])
- **NEVER**: Direct access to other repositories ❌

### Files to Create/Modify
- [ ] `app/[layer]/[filename].py` (~[X] lines)
- [ ] `tests/unit/[layer]/test_[filename].py` (~[Y] lines)
- [ ] `tests/integration/test_[name]_api.py` (~[Z] lines)
- [ ] `[other files if needed]`

### Database Access
**Tables involved**:
- `[table1]` (primary - [brief description])
- `[table2]` (via [ServiceName], NOT direct repo)
- `[table3]` (via [ServiceName], NOT direct repo)

**See**: database/database.mmd (lines XXX-YYY)

### Implementation Strategy

1. **Python Expert**: Implement [ClassName]
   - Use template: backlog/04_templates/starter-code/[template].py
   - Follow Service→Service pattern (NEVER Service→OtherRepo)
   - Key methods:
     - `[method1_name]([params])`: [description]
     - `[method2_name]([params])`: [description]
   - Business logic:
     - Validation: [validation1, validation2]
     - Exceptions: [Exception1Name, Exception2Name]
   - Async methods with type hints

2. **Testing Expert**: Write tests **IN PARALLEL**
   - Unit tests: Mock dependencies ([Service1, Service2, etc.])
   - Integration tests: Real testing DB
   - Target: ≥80% coverage
   - Test scenarios:
     - [Scenario 1: description]
     - [Scenario 2: description]
     - [Scenario 3: edge case]

3. **Database Expert**: On-call for schema questions
   - Clarify [table1] relationships
   - Explain [specific_column] usage
   - Advise on [query_pattern] optimization

### Acceptance Criteria (from task card)
- [ ] [Criterion 1: specific testable requirement]
- [ ] [Criterion 2: specific testable requirement]
- [ ] [Criterion 3: specific testable requirement]
- [ ] [Criterion 4: specific testable requirement]
- [ ] [Criterion 5: specific testable requirement]
- [ ] Unit tests ≥80% coverage
- [ ] Integration tests pass
- [ ] No direct repository access (except self.repo)

### Performance Expectations
- [Operation 1]: <[X]ms
- [Operation 2]: <[Y]ms
- Full workflow (with DB): <[Z]ms
- Tests: All passing, no warnings

### Next Steps
1. Move task to `02_in-progress/`
2. Spawn Python Expert + Testing Expert (parallel)
3. Monitor progress (agents update task file every 30 min)
4. Review code when both agents report completion
5. Run quality gates
6. Approve completion

---

## Example

```markdown
## Team Leader Mini-Plan (2025-10-11 14:30)

### Task Overview
- **Card**: S001 - StockMovementService
- **Epic**: epic-004 (Service Layer)
- **Priority**: HIGH (critical for manual init workflow)
- **Complexity**: 8 points (Medium)

### Architecture
**Layer**: Service (Application Layer)
**Pattern**: Clean Architecture - Service→Service communication
**Dependencies**:
- Own repository: StockMovementRepository (R003)
- Other services:
  - StorageLocationConfigService (S028) - for config validation
  - StockBatchService (S002) - for batch creation
- **NEVER**: Direct access to ConfigRepository or BatchRepository ❌

### Files to Create/Modify
- [ ] `app/services/stock_movement_service.py` (~150 lines)
- [ ] `tests/unit/services/test_stock_movement_service.py` (~200 lines)
- [ ] `tests/integration/test_stock_movement_api.py` (~150 lines)

### Database Access
**Tables involved**:
- `stock_movements` (primary - event sourcing table for all movements)
- `stock_batches` (via BatchService, NOT direct repo)
- `storage_location_config` (via ConfigService, NOT direct repo)

**See**: database/database.mmd (lines 245-280 for stock_movements)

### Implementation Strategy

1. **Python Expert**: Implement StockMovementService
   - Use template: backlog/04_templates/starter-code/base_service.py
   - Follow Service→Service pattern
   - Key methods:
     - `create_manual_initialization(request)`: Create manual stock entry
     - `get_by_id(movement_id)`: Retrieve single movement
     - `get_by_location(location_id)`: Get all movements for location
   - Business logic:
     - Validation: Product must match config, Quantity > 0
     - Exceptions: ProductMismatchException, ConfigNotFoundException, InvalidQuantityException
   - Async methods with full type hints

2. **Testing Expert**: Write tests **IN PARALLEL**
   - Unit tests: Mock ConfigService, BatchService
   - Integration tests: Real testing DB with seed data
   - Target: ≥80% coverage
   - Test scenarios:
     - Success: Valid manual initialization
     - Failure: Product mismatch (should raise exception)
     - Failure: Missing configuration (should raise exception)
     - Edge case: Zero/negative quantity

3. **Database Expert**: On-call for questions
   - Clarify stock_movements UUID vs SERIAL structure
   - Explain movement_type enum values
   - Advise on batch_id NULL handling

### Acceptance Criteria
- [ ] Service implements `create_manual_initialization(request)` method
- [ ] Calls ConfigService.get_by_location() (NOT config repo)
- [ ] Validates product_id matches config.product_id
- [ ] Raises ProductMismatchException on mismatch
- [ ] Calls BatchService.create_from_movement() (NOT batch repo)
- [ ] Returns StockMovementResponse (Pydantic schema)
- [ ] Unit tests ≥80% coverage
- [ ] Integration tests pass (full workflow)
- [ ] No direct repository access (verified in code review)

### Performance Expectations
- Service method: <50ms (excluding repo calls)
- Full workflow (API → Service → Repo → DB): <200ms
- Tests: All passing, execution time <5s

### Next Steps
1. Move to `02_in-progress/`
2. Spawn Python Expert + Testing Expert (parallel work)
3. Check progress in 30 minutes
4. Review when both report completion
5. Run quality gates
6. Approve for completion
```
