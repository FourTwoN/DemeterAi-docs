# Team Leader Mini-Plan: DB018 - ProductStates Enum

**Date**: 2025-10-14
**Task Card**: DB018 - ProductStates Enum
**Epic**: epic-002-database-models
**Priority**: HIGH (blocks DB017 Products - critical path for Product Catalog)
**Complexity**: 1 story point (S - Simple enum with seed data)
**Estimated Time**: 30-40 minutes

---

## Task Overview

Create the `product_states` SQLAlchemy model - a reference/catalog table defining plant lifecycle
states (SEED → DEAD) with `is_sellable` business logic flag.

**What**: Enum model for product lifecycle states
**Why**:

- Inventory filtering (show all flowering plants)
- Sales logic enforcement (only sellable states can be sold)
- Manual stock validation (expected_product_state_id in StorageLocationConfig)
- ML validation (verify ML-detected state matches expected state)

**Pattern**: Same as DB005 (StorageBinTypes) - reference catalog with seed data

---

## Architecture

**Layer**: Database / Models (Infrastructure Layer)
**Pattern**: Reference/Catalog table with seed data
**Dependencies**:

- SQLAlchemy 2.0
- PostgreSQL enums
- Alembic migrations

**Relationships** (FK from):

- StockBatches.product_state_id → ProductStates.product_state_id
- Classifications.product_state_id → ProductStates.product_state_id (nullable)
- ProductSampleImages.product_state_id → ProductStates.product_state_id (nullable)
- StorageLocationConfig.expected_product_state_id → ProductStates.product_state_id

---

## Files to Create/Modify

- [ ] `app/models/product_state.py` (~180 lines)
    - Model class with code validation
    - is_sellable business logic flag
    - sort_order for UI dropdowns
    - Relationships (COMMENT OUT until referenced models exist)

- [ ] `alembic/versions/XXXX_create_product_states.py` (~140 lines)
    - CREATE TABLE migration
    - CREATE UNIQUE INDEX on code
    - CREATE INDEX on is_sellable
    - CREATE INDEX on sort_order
    - INSERT 11 seed records (SEED → DEAD lifecycle)

- [ ] `tests/unit/models/test_product_state.py` (~400 lines, 15-20 tests)
    - Code validation tests (uppercase, alphanumeric, 3-50 chars)
    - is_sellable flag tests
    - sort_order default tests
    - Relationship tests (COMMENT OUT)
    - Basic CRUD tests

- [ ] `tests/integration/models/test_product_state.py` (~300 lines, 8-10 tests)
    - Seed data verification (11 states loaded)
    - RESTRICT delete tests (cannot delete if stock_batches reference)
    - Code uniqueness tests (DB-level UK constraint)
    - is_sellable filter queries
    - sort_order ordering tests

- [ ] `app/models/__init__.py` (update exports)

---

## Database Schema

**Table**: `product_states`

**Columns**:

```python
product_state_id: Integer PK (auto-increment)
code: String(50) UK, NOT NULL, indexed (SEED, SEEDLING, ADULT, etc.)
name: String(200) NOT NULL (Human-readable: "Flowering Adult")
description: Text NULL
is_sellable: Boolean DEFAULT FALSE, indexed (business logic flag)
sort_order: Integer DEFAULT 99 (UI dropdown order)
created_at: DateTime(TZ) server_default=now()
updated_at: DateTime(TZ) onupdate=now()
```

**Indexes**:

- B-tree index on code (unique lookups)
- B-tree index on is_sellable (WHERE queries)
- B-tree index on sort_order (ORDER BY queries)

**Constraints**:

- UK on code
- CHECK LENGTH(code) >= 3 AND <= 50
- NOT NULL on code, name, is_sellable

---

## Seed Data (11 States)

**Early Lifecycle (NOT sellable)**:

1. SEED (sort: 10) - is_sellable: FALSE
2. GERMINATING (sort: 20) - is_sellable: FALSE
3. SEEDLING (sort: 30) - is_sellable: FALSE
4. JUVENILE (sort: 40) - is_sellable: FALSE

**Mature Stages (SELLABLE)**:

5. ADULT (sort: 50) - is_sellable: TRUE
6. FLOWERING (sort: 60) - is_sellable: TRUE
7. FRUITING (sort: 70) - is_sellable: TRUE

**Special States**:

8. DORMANT (sort: 80) - is_sellable: TRUE (winter dormancy, still sellable)
9. PROPAGATING (sort: 90) - is_sellable: FALSE (cutting/division rooting)

**End-of-Life (NOT sellable)**:

10. DYING (sort: 100) - is_sellable: FALSE
11. DEAD (sort: 110) - is_sellable: FALSE

**Business Rule**: Only 4 states are sellable (ADULT, FLOWERING, FRUITING, DORMANT)

---

## Implementation Strategy

### Step 1: Python Expert Implementation

**Template**: Follow DB005 (StorageBinTypes) pattern exactly

**Tasks**:

1. Create `app/models/product_state.py`
    - Class definition with `__tablename__ = 'product_states'`
    - All columns with correct types
    - `@validates('code')` decorator for code validation
    - Relationships (COMMENT OUT until models exist)
    - `__repr__()` method
    - `__table_args__` with CHECK constraint and comment

2. Create Alembic migration
    - `alembic revision -m "create_product_states"`
    - upgrade(): CREATE TABLE + 3 indexes + 11 INSERT statements
    - downgrade(): DROP TABLE

3. Update `app/models/__init__.py`
    - Add `from app.models.product_state import ProductState`

**Code Validation Rules**:

- Required (not empty)
- Must be uppercase
- Alphanumeric + underscores only (NO hyphens)
- Length between 3 and 50 characters

**Estimated Time**: 25-30 minutes

---

### Step 2: Testing Expert (PARALLEL)

**Template**: Follow DB005 test patterns

**Tasks**:

**Unit Tests** (`tests/unit/models/test_product_state.py`):

1. Code validation tests (6 tests):
    - test_code_valid_uppercase
    - test_code_auto_uppercase
    - test_code_empty_raises_error
    - test_code_invalid_characters_raises_error (hyphens, spaces, lowercase)
    - test_code_too_short_raises_error
    - test_code_too_long_raises_error

2. is_sellable flag tests (2 tests):
    - test_is_sellable_default_false
    - test_is_sellable_explicit_true

3. sort_order tests (2 tests):
    - test_sort_order_default_99
    - test_sort_order_custom_value

4. Relationship tests (2 tests, COMMENT OUT):
    - test_stock_batches_relationship
    - test_classifications_relationship

5. Basic CRUD tests (3 tests):
    - test_create_product_state
    - test_update_product_state
    - test_delete_product_state

**Integration Tests** (`tests/integration/models/test_product_state.py`):

1. Seed data tests (2 tests):
    - test_seed_data_loaded (verify 11 states exist)
    - test_seed_data_is_sellable_logic (verify 4 sellable, 7 not sellable)

2. RESTRICT delete tests (2 tests):
    - test_cannot_delete_referenced_product_state (if stock_batches reference)
    - test_can_delete_unreferenced_product_state

3. Uniqueness tests (2 tests):
    - test_code_unique_constraint_db_level
    - test_duplicate_code_raises_integrity_error

4. Query tests (2 tests):
    - test_filter_by_is_sellable_true
    - test_order_by_sort_order

**Coverage Target**: ≥75% for model, ≥70% for integration

**Estimated Time**: 30-35 minutes (can start BEFORE implementation complete)

---

### Step 3: Team Leader Review

**Code Review Checklist**:

- [ ] Model file follows DB005 pattern exactly
- [ ] Code validation uses `@validates` decorator
- [ ] is_sellable boolean with default FALSE
- [ ] sort_order integer with default 99
- [ ] 11 seed records in migration
- [ ] 3 indexes created (code UK, is_sellable, sort_order)
- [ ] Relationships COMMENTED OUT (stock_batches, classifications not ready)
- [ ] Type hints on all methods
- [ ] Docstrings present
- [ ] `__repr__()` method implemented

**Testing Review Checklist**:

- [ ] 15-20 unit tests written
- [ ] 8-10 integration tests written
- [ ] All tests pass
- [ ] Coverage ≥75% (unit), ≥70% (integration)
- [ ] Seed data test verifies all 11 states
- [ ] is_sellable logic test verifies 4 sellable states

**Estimated Time**: 10 minutes

---

### Step 4: Quality Gates (MANDATORY)

**Gate 1: All Acceptance Criteria Checked**

```bash
grep -c "\[x\]" /home/lucasg/proyectos/DemeterDocs/backlog/03_kanban/02_in-progress/DB018-product-states-enum.md
# Should be 7 (all ACs checked)
```

**Gate 2: Unit Tests Pass**

```bash
pytest tests/unit/models/test_product_state.py -v
# All tests must pass
```

**Gate 3: Integration Tests Pass**

```bash
pytest tests/integration/models/test_product_state.py -v
# All tests must pass
```

**Gate 4: Coverage ≥75%**

```bash
pytest tests/unit/models/test_product_state.py --cov=app.models.product_state --cov-report=term-missing
# TOTAL coverage ≥75%
```

**Gate 5: Type Checking**

```bash
mypy app/models/product_state.py --strict
# No errors
```

**Gate 6: Linting**

```bash
ruff check app/models/product_state.py
# No errors
```

**Gate 7: Migration Runs Successfully**

```bash
alembic upgrade head
alembic downgrade -1
alembic upgrade head
# All commands succeed, 11 seed records inserted
```

**Estimated Time**: 10 minutes

---

### Step 5: Completion

**After all gates pass**:

1. Append completion approval to task card
2. Invoke Git Commit Agent (create commit)
3. Move to `05_done/`
4. Update `DATABASE_CARDS_STATUS.md`
5. Report to Scrum Master

**Git Commit Message**:

```
feat(models): implement ProductState enum with 11 lifecycle seed records (DB018)

- Add ProductState model with is_sellable business logic flag
- 11 lifecycle states: SEED → GERMINATING → ... → DEAD
- 4 sellable states: ADULT, FLOWERING, FRUITING, DORMANT
- sort_order for UI dropdowns (lifecycle progression)
- Seed data migration with 11 INSERT statements
- Unit tests: 15-20 tests (≥75% coverage)
- Integration tests: 8-10 tests (verify seed data, RESTRICT delete)
- Follows DB005 StorageBinTypes pattern

Blocks: DB017 (Products), DB024 (StorageLocationConfig), DB026 (Classifications)
```

**Estimated Time**: 5 minutes

---

## Performance Expectations

- Insert: <10ms
- Retrieve by code: <5ms (UK index)
- Filter by is_sellable: <10ms (B-tree index)
- Retrieve all ordered by sort_order: <10ms (small reference table, <20 rows expected)

---

## Dependencies Unblocked After Completion

- **DB017**: Products model (uses product_state_id FK)
- **DB024**: StorageLocationConfig (uses expected_product_state_id FK)
- **DB026**: Classifications (uses product_state_id FK for ML results)

---

## Key Resources

- **Template**: `/home/lucasg/proyectos/DemeterDocs/app/models/storage_bin_type.py` (DB005 pattern)
- **Task Card**:
  `/home/lucasg/proyectos/DemeterDocs/backlog/03_kanban/02_in-progress/DB018-product-states-enum.md`
- **Database ERD**: `/home/lucasg/proyectos/DemeterDocs/database/database.mmd` (lines 97-104)
- **Engineering Docs**: `/home/lucasg/proyectos/DemeterDocs/engineering_plan/database/README.md`

---

## Critical Rules

1. **NO Service→Repository violations**: This is a model, no service layer
2. **Coverage MUST be ≥75%**: Gate 4 will fail otherwise
3. **COMMENT OUT relationships**: StockBatch, Classification models not ready
4. **11 seed records REQUIRED**: Business logic depends on these states
5. **is_sellable logic CRITICAL**: Only ADULT, FLOWERING, FRUITING, DORMANT are sellable

---

## Acceptance Criteria (7 ACs)

- [ ] **AC1**: Model created in `app/models/product_state.py` with code, name, description,
  is_sellable, sort_order fields
- [ ] **AC2**: Code validation (uppercase, alphanumeric + underscores, 3-50 chars, unique)
- [ ] **AC3**: is_sellable boolean (default FALSE) - only certain states are sellable
- [ ] **AC4**: sort_order integer (for UI dropdowns, default 99)
- [ ] **AC5**: Seed data migration with common states (SEED, SEEDLING, JUVENILE, ADULT, FLOWERING,
  DORMANT, DYING, DEAD)
- [ ] **AC6**: Indexes on code (UK), is_sellable (for WHERE queries), sort_order
- [ ] **AC7**: Alembic migration with seed data

---

## Timeline Estimate

| Phase                        | Duration      | Description                   |
|------------------------------|---------------|-------------------------------|
| Python Expert Implementation | 25-30 min     | Model + migration + seed data |
| Testing Expert (Parallel)    | 30-35 min     | Unit + integration tests      |
| Team Leader Review           | 10 min        | Code + test review            |
| Quality Gates                | 10 min        | Run all gates                 |
| Completion                   | 5 min         | Commit + move to done         |
| **TOTAL**                    | **40-45 min** | **Single task**               |

**Note**: Can be done in parallel with DB019 (ProductSizes) for maximum efficiency.

---

**END OF MINI-PLAN DB018**
