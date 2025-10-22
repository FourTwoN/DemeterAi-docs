# Critical Issues - Lessons Learned from Sprint 02

**Version**: 1.0
**Last Updated**: 2025-10-20
**Sprint**: Sprint 02 (ML Pipeline)

---

## Overview

This document captures **critical issues** discovered during Sprint 02 that must NEVER happen again. These issues caused 70/386 tests to fail silently and nearly derailed the project.

**Purpose**: Ensure every agent understands what went wrong and how to prevent it.

---

## Issue 1: Tests Marked as Passing When They Were Failing

### What Happened

**Claim**: All 386 tests passing
**Reality**: 70/386 tests (18%) were failing

### Root Cause

1. **Tests were mocked incorrectly**: Mocks returned success even when logic was broken
2. **Tests never actually ran**: Pytest command wasn't executed, results were assumed
3. **Exit codes weren't checked**: No verification that pytest returned 0

### Impact

- HIGH: Nearly 20% of code was broken
- Project marked "complete" when it was not
- Would have failed in production
- Lost trust in test suite

### Example

```python
# ❌ WRONG: Mock hides real failure
@pytest.mark.asyncio
async def test_create_movement():
    mock_service = AsyncMock()
    mock_service.create.return_value = MockSuccess()  # Always returns success

    result = await service.create(...)
    assert result is not None  # Test passes even if real logic is broken
```

```python
# ✅ CORRECT: Real database test
@pytest.mark.asyncio
async def test_create_movement(db_session):
    # Real service with real database
    service = StockMovementService(
        repo=StockMovementRepository(db_session),
        config_service=ConfigService(...)  # Real service
    )

    result = await service.create(valid_request)

    # Verify in actual database
    db_record = await db_session.get(StockMovement, result.id)
    assert db_record is not None
    assert db_record.movement_type == "manual_init"
```

### Prevention Rules

**Rule 1: Always Run Pytest**
```bash
# MANDATORY: Actually run tests
pytest tests/ -v

# Check exit code
if [ $? -ne 0 ]; then
    echo "❌ TESTS FAILED"
    exit 1
fi
```

**Rule 2: Use Real Database for Integration Tests**
```python
# ✅ Integration tests use real PostgreSQL
@pytest.mark.asyncio
async def test_workflow(db_session):  # Real database session
    service = RealService(RealRepository(db_session))
    result = await service.method(...)
    # Verify in database
```

**Rule 3: Verify Test Results in Task Files**
```markdown
## Testing Expert Report
Status: COMPLETE

Test Results (VERIFIED):
```bash
$ pytest tests/unit/ -v
========================= 12 passed in 2.34s =========================
$ echo $?
0
```

- Unit tests: ✅ 12/12 passed (exit code 0)
- Integration tests: ✅ 5/5 passed (exit code 0)
```

**Rule 4: Quality Gate Must Verify**
```bash
# Team Leader MUST run tests before approving
pytest tests/ -v
PYTEST_EXIT=$?

if [ $PYTEST_EXIT -ne 0 ]; then
    echo "❌ Quality Gate FAILED: Tests failing"
    # Keep in 04_testing/, don't move to 05_done/
    exit 1
fi
```

---

## Issue 2: Hallucinated Code (Non-Existent Relationships)

### What Happened

**Code written**: `warehouse.storage_areas` relationship
**Reality**: Relationship didn't exist in models

### Root Cause

1. **Assumed relationships existed** without reading actual code
2. **Implemented from memory** instead of schema
3. **Didn't verify imports** before claiming completion

### Impact

- MEDIUM: Code couldn't import
- ImportError at runtime
- Had to rewrite entire model layer

### Example

```python
# ❌ WRONG: Assumed relationship exists
class WarehouseService:
    async def get_storage_areas(self, warehouse_id: UUID):
        warehouse = await self.repo.get(warehouse_id)
        return warehouse.storage_areas  # ❌ Relationship doesn't exist!
```

**Error**:
```
AttributeError: 'Warehouse' object has no attribute 'storage_areas'
```

```python
# ✅ CORRECT: Read model first, verify relationship exists
# Step 1: Read existing model
$ cat app/models/warehouse.py
class Warehouse(Base):
    __tablename__ = "warehouses"
    id: Mapped[UUID]
    name: Mapped[str]
    # NO storage_areas relationship!

# Step 2: Check database schema
$ cat database/database.mmd | grep -A 10 "Warehouse"
# Confirms: No relationship defined

# Step 3: Add relationship if needed (via migration)
# OR use repository join
class WarehouseService:
    async def get_storage_areas(self, warehouse_id: UUID):
        # Use repository to query, don't assume relationship
        return await self.area_repo.get_by_warehouse(warehouse_id)
```

### Prevention Rules

**Rule 1: Read Before Writing**
```bash
# BEFORE implementing service
cat app/models/warehouse.py
cat app/models/storage_area.py
grep "relationship" app/models/*.py
```

**Rule 2: Verify Imports**
```bash
# BEFORE claiming completion
python -c "from app.services.warehouse_service import WarehouseService"
python -c "from app.models import Warehouse"

# Must succeed with exit code 0
if [ $? -ne 0 ]; then
    echo "❌ Import error - code is hallucinated"
    exit 1
fi
```

**Rule 3: Consult ERD First**
```bash
# ALWAYS check database/database.mmd before implementing
cat database/database.mmd | grep -A 20 "warehouses"

# Verify:
# - Table name
# - Column names
# - Foreign keys
# - Relationships
```

---

## Issue 3: Schema Drift (Models vs Database Mismatch)

### What Happened

**Model defined**: `storage_location_id INT`
**Database schema**: `storage_location_id UUID`

### Root Cause

1. **Implemented from memory** instead of ERD
2. **Didn't verify data types** against schema
3. **Assumed conventions** instead of checking

### Impact

- HIGH: Migrations failed
- Database queries broke
- Had to rewrite migrations

### Example

```python
# ❌ WRONG: Guessed data type
class StockMovement(Base):
    __tablename__ = "stock_movements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # ❌ Should be UUID
    storage_location_id: Mapped[int] = mapped_column(Integer)  # ❌ Should be UUID
```

**Error**:
```sql
psql: ERROR: column "id" is of type uuid but expression is of type integer
```

```python
# ✅ CORRECT: Read ERD first
# Step 1: Check database/database.mmd
$ cat database/database.mmd | grep -A 30 "stock_movements"
# Output shows:
# id UUID PRIMARY KEY
# storage_location_id UUID REFERENCES storage_locations(id)

# Step 2: Implement correctly
class StockMovement(Base):
    __tablename__ = "stock_movements"

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    storage_location_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("storage_locations.id")
    )
```

### Prevention Rules

**Rule 1: ERD is Source of Truth**
```bash
# BEFORE implementing model
cat database/database.mmd | grep -A 50 "table_name"

# Verify:
# - Primary key type (UUID vs SERIAL)
# - Foreign key types and references
# - Column types (UUID, VARCHAR, INTEGER, etc.)
# - NOT NULL constraints
```

**Rule 2: Compare Model with ERD**
```bash
# AFTER implementing model
diff <(grep "class StockMovement" app/models/stock_movement.py) \
     <(grep "stock_movements" database/database.mmd)

# Verify types match
```

**Rule 3: Test Migrations**
```bash
# BEFORE claiming completion
alembic upgrade head

# Verify migration applies cleanly
if [ $? -ne 0 ]; then
    echo "❌ Migration failed - schema mismatch"
    exit 1
fi
```

---

## Issue 4: Incomplete Coverage Reporting

### What Happened

**Claim**: 80% coverage
**Reality**: Only happy path tested, error handling at 0%

### Root Cause

1. **Only tested success cases**
2. **Didn't test exceptions**
3. **Didn't verify coverage report details**

### Impact

- MEDIUM: Error handling broken in production
- Missing ProductMismatchException tests
- Missing network failure tests

### Example

```python
# ❌ WRONG: Only tests happy path
@pytest.mark.asyncio
async def test_create_movement():
    result = await service.create(valid_request)
    assert result.id is not None  # Only tests success

# Coverage: 50% (missing exception handling)
```

```python
# ✅ CORRECT: Tests both success and failure
@pytest.mark.asyncio
async def test_create_movement_success():
    result = await service.create(valid_request)
    assert result.id is not None

@pytest.mark.asyncio
async def test_create_movement_product_mismatch():
    with pytest.raises(ProductMismatchException):
        await service.create(invalid_request)  # Tests exception

@pytest.mark.asyncio
async def test_create_movement_config_not_found():
    with pytest.raises(ConfigNotFoundException):
        await service.create(request_with_invalid_location)

# Coverage: 85% (includes error handling)
```

### Prevention Rules

**Rule 1: Test All Code Paths**
```python
# For every method, test:
# 1. Happy path (success)
# 2. Business exceptions (validation failures)
# 3. Technical exceptions (network failures, database errors)
# 4. Edge cases (null values, empty lists, etc.)
```

**Rule 2: Verify Coverage Details**
```bash
# Run with --cov-report=term-missing
pytest --cov=app.services.example --cov-report=term-missing

# Output shows which lines are NOT covered:
# Name                                    Stmts   Miss  Cover   Missing
# ---------------------------------------------------------------------
# app/services/example.py                    42      6    85%   78-82
#
# Lines 78-82 are missing coverage - add tests!
```

**Rule 3: Coverage Must Be ≥80%**
```bash
COVERAGE=$(pytest --cov=app.services.example --cov-report=term | grep TOTAL | awk '{print $4}' | sed 's/%//')

if [ $COVERAGE -lt 80 ]; then
    echo "❌ Coverage too low: $COVERAGE% (need ≥80%)"
    exit 1
fi
```

---

## Issue 5: Service→Repository Anti-Pattern

### What Happened

**Code written**: `StockMovementService` calling `ConfigRepository` directly
**Expected**: `StockMovementService` calling `ConfigService`

### Root Cause

1. **Didn't understand Clean Architecture**
2. **Took shortcut** (direct repository access faster)
3. **Violated Service→Service pattern**

### Impact

- HIGH: Breaks architecture
- Creates tight coupling
- Violates separation of concerns

### Example

```python
# ❌ WRONG: Service calling other service's repository
class StockMovementService:
    def __init__(
        self,
        repo: StockMovementRepository,
        config_repo: ConfigRepository  # ❌ VIOLATION
    ):
        self.repo = repo
        self.config_repo = config_repo  # ❌

    async def create(self, request):
        config = await self.config_repo.get(...)  # ❌ Direct repo access
```

```python
# ✅ CORRECT: Service calling other service
class StockMovementService:
    def __init__(
        self,
        repo: StockMovementRepository,
        config_service: ConfigService  # ✅ Service
    ):
        self.repo = repo
        self.config_service = config_service  # ✅

    async def create(self, request):
        config = await self.config_service.get_by_location(...)  # ✅ Service method
```

### Prevention Rules

**Rule 1: Service→Service Communication ONLY**
```python
# ✅ Allowed:
# - Service → Own Repository
# - Service → Other Service

# ❌ Forbidden:
# - Service → Other Service's Repository
```

**Rule 2: Code Review Must Verify**
```bash
# Check for repository violations
grep -n "Repository" app/services/stock_movement_service.py | grep -v "self.repo"

# Output should be EMPTY (no other repository references)
```

**Rule 3: Team Leader Rejects Violations**
```markdown
## Team Leader Code Review
Status: ❌ REJECTED

Issue: Service→Repository violation (line 15)
- Found: self.config_repo.get(...)
- Expected: self.config_service.get_by_location(...)

Action: Python Expert - refactor to use ConfigService
```

---

## Quality Gate Enforcement Checklist

**Before ANY task moves to `05_done/`, verify ALL gates**:

### Gate 1: Code Review
- [ ] Service→Service pattern enforced
- [ ] No direct repository access (except self.repo)
- [ ] All methods have type hints
- [ ] Async/await used correctly
- [ ] Docstrings present

### Gate 2: Tests Actually Run
```bash
pytest tests/ -v
EXIT_CODE=$?
[ $EXIT_CODE -eq 0 ] || exit 1
```

### Gate 3: Coverage ≥80%
```bash
COVERAGE=$(pytest --cov=app.services.example --cov-report=term | grep TOTAL | awk '{print $4}' | sed 's/%//')
[ $COVERAGE -ge 80 ] || exit 1
```

### Gate 4: No Hallucinations
```bash
python -c "from app.services.example import ExampleService"
[ $? -eq 0 ] || exit 1
```

### Gate 5: Schema Match
```bash
# Compare model with ERD
grep "class Example" app/models/example.py
grep "example_table" database/database.mmd
# Types must match
```

---

## Summary: How to Prevent These Issues

### For Python Expert

1. **Read before writing**: Check existing code, ERD, related services
2. **Verify imports**: Test all imports before claiming completion
3. **Follow patterns**: Service→Service, never Service→OtherRepository

### For Testing Expert

1. **Run tests**: Actually execute pytest, don't assume
2. **Use real database**: Integration tests need real PostgreSQL
3. **Test all paths**: Happy path, exceptions, edge cases
4. **Verify coverage**: Check --cov-report=term-missing output

### For Team Leader

1. **Enforce quality gates**: Don't approve until ALL gates pass
2. **Verify claims**: Run pytest yourself, don't trust reports
3. **Check patterns**: Grep for repository violations
4. **Verify schema**: Compare models with ERD

### For Scrum Master

1. **Don't rush**: Quality over speed
2. **Verify completion**: Check that gates actually passed
3. **Track issues**: Document problems to prevent recurrence

---

## Action Items for Sprint 03

- [ ] Create quality_gate_check.sh script (automated validation)
- [ ] Add pre-commit hook (enforces linting, type checking)
- [ ] Document Service→Service pattern (with examples)
- [ ] Create ERD verification script (compares models with schema)
- [ ] Add coverage reporting to CI/CD

---

**Last Updated**: 2025-10-20
**Never Forget**: Sprint 02 taught us that tests must ACTUALLY pass, code must ACTUALLY work, and quality gates exist for a reason.
