# Team Leader Mini-Plan: DB019 - ProductSizes Enum

**Date**: 2025-10-14
**Task Card**: DB019 - ProductSizes Enum
**Epic**: epic-002-database-models
**Priority**: HIGH (blocks DB017 Products - critical path for Product Catalog)
**Complexity**: 1 story point (S - Simple enum with seed data)
**Estimated Time**: 30-40 minutes

---

## Task Overview

Create the `product_sizes` SQLAlchemy model - a reference/catalog table defining plant size categories (XS, S, M, L, XL, XXL, CUSTOM) with height ranges.

**What**: Enum model for product size categories
**Why**:
- Inventory filtering (show all Large plants)
- Size-based pricing (different sizes → different prices)
- ML classification (Classifications.product_size_id FK)
- Stock tracking (StockBatches.product_size_id FK)
- Product sample images (ProductSampleImages.product_size_id FK for growth tracking)

**Pattern**: Same as DB005 (StorageBinTypes) and DB018 (ProductStates) - reference catalog with seed data

---

## Architecture

**Layer**: Database / Models (Infrastructure Layer)
**Pattern**: Reference/Catalog table with seed data
**Dependencies**:
- SQLAlchemy 2.0
- PostgreSQL numeric types
- Alembic migrations

**Relationships** (FK from):
- StockBatches.product_size_id → ProductSizes.product_size_id (nullable)
- Classifications.product_size_id → ProductSizes.product_size_id (nullable)
- ProductSampleImages.product_size_id → ProductSizes.product_size_id (nullable)

---

## Files to Create/Modify

- [ ] `app/models/product_size.py` (~160 lines)
  - Model class with code validation
  - Height range fields (min_height_cm, max_height_cm)
  - sort_order for UI dropdowns
  - Relationships (COMMENT OUT until referenced models exist)

- [ ] `alembic/versions/XXXX_create_product_sizes.py` (~120 lines)
  - CREATE TABLE migration
  - CREATE UNIQUE INDEX on code
  - CREATE INDEX on sort_order
  - INSERT 7 seed records (XS → CUSTOM)

- [ ] `tests/unit/models/test_product_size.py` (~350 lines, 12-15 tests)
  - Code validation tests (uppercase, alphanumeric, 3-50 chars)
  - Height range tests (min_height_cm, max_height_cm nullable)
  - sort_order default tests
  - Relationship tests (COMMENT OUT)
  - Basic CRUD tests

- [ ] `tests/integration/models/test_product_size.py` (~250 lines, 6-8 tests)
  - Seed data verification (7 sizes loaded)
  - RESTRICT delete tests (cannot delete if stock_batches reference)
  - Code uniqueness tests (DB-level UK constraint)
  - sort_order ordering tests

- [ ] `app/models/__init__.py` (update exports)

---

## Database Schema

**Table**: `product_sizes`

**Columns**:
```python
product_size_id: Integer PK (auto-increment)
code: String(50) UK, NOT NULL, indexed (XS, S, M, L, XL, XXL, CUSTOM)
name: String(200) NOT NULL (Human-readable: "Extra Small (0-5cm)")
description: Text NULL
min_height_cm: Numeric(6,2) NULL (minimum height in cm)
max_height_cm: Numeric(6,2) NULL (maximum height in cm)
sort_order: Integer DEFAULT 99 (UI dropdown order)
created_at: DateTime(TZ) server_default=now()
updated_at: DateTime(TZ) onupdate=now()
```

**Indexes**:
- B-tree index on code (unique lookups)
- B-tree index on sort_order (ORDER BY queries)

**Constraints**:
- UK on code
- CHECK LENGTH(code) >= 3 AND <= 50
- NOT NULL on code, name

---

## Seed Data (7 Sizes)

**Standard Sizes** (with height ranges):
1. XS (sort: 10) - "Extra Small (0-5cm)" - min: 0, max: 5
2. S (sort: 20) - "Small (5-10cm)" - min: 5, max: 10
3. M (sort: 30) - "Medium (10-20cm)" - min: 10, max: 20
4. L (sort: 40) - "Large (20-40cm)" - min: 20, max: 40
5. XL (sort: 50) - "Extra Large (40-80cm)" - min: 40, max: 80
6. XXL (sort: 60) - "Extra Extra Large (80+cm)" - min: 80, max: NULL

**Special Size**:
7. CUSTOM (sort: 99) - "Custom Size (no fixed range)" - min: NULL, max: NULL

**Business Rule**:
- CUSTOM size has no height range (NULL for both min and max)
- XXL has no max height (NULL for max)
- Height ranges are approximate guidelines, not strict constraints

---

## Implementation Strategy

### Step 1: Python Expert Implementation

**Template**: Follow DB005 (StorageBinTypes) and DB018 (ProductStates) patterns

**Tasks**:
1. Create `app/models/product_size.py`
   - Class definition with `__tablename__ = 'product_sizes'`
   - All columns with correct types
   - `@validates('code')` decorator for code validation
   - Relationships (COMMENT OUT until models exist)
   - `__repr__()` method
   - `__table_args__` with CHECK constraint and comment

2. Create Alembic migration
   - `alembic revision -m "create_product_sizes"`
   - upgrade(): CREATE TABLE + 2 indexes + 7 INSERT statements
   - downgrade(): DROP TABLE

3. Update `app/models/__init__.py`
   - Add `from app.models.product_size import ProductSize`

**Code Validation Rules**:
- Required (not empty)
- Must be uppercase
- Alphanumeric + underscores only (NO hyphens)
- Length between 3 and 50 characters

**Estimated Time**: 20-25 minutes

---

### Step 2: Testing Expert (PARALLEL)

**Template**: Follow DB005 and DB018 test patterns

**Tasks**:

**Unit Tests** (`tests/unit/models/test_product_size.py`):
1. Code validation tests (6 tests):
   - test_code_valid_uppercase
   - test_code_auto_uppercase
   - test_code_empty_raises_error
   - test_code_invalid_characters_raises_error (hyphens, spaces)
   - test_code_too_short_raises_error
   - test_code_too_long_raises_error

2. Height range tests (3 tests):
   - test_height_ranges_nullable
   - test_height_ranges_valid_values
   - test_custom_size_no_height_ranges

3. sort_order tests (2 tests):
   - test_sort_order_default_99
   - test_sort_order_custom_value

4. Relationship tests (2 tests, COMMENT OUT):
   - test_stock_batches_relationship
   - test_classifications_relationship

5. Basic CRUD tests (3 tests):
   - test_create_product_size
   - test_update_product_size
   - test_delete_product_size

**Integration Tests** (`tests/integration/models/test_product_size.py`):
1. Seed data tests (2 tests):
   - test_seed_data_loaded (verify 7 sizes exist)
   - test_seed_data_height_ranges (verify XS: 0-5, S: 5-10, etc.)

2. RESTRICT delete tests (2 tests):
   - test_cannot_delete_referenced_product_size
   - test_can_delete_unreferenced_product_size

3. Uniqueness tests (2 tests):
   - test_code_unique_constraint_db_level
   - test_duplicate_code_raises_integrity_error

4. Query tests (1 test):
   - test_order_by_sort_order

**Coverage Target**: ≥75% for model, ≥70% for integration

**Estimated Time**: 25-30 minutes (can start BEFORE implementation complete)

---

### Step 3: Team Leader Review

**Code Review Checklist**:
- [ ] Model file follows DB005/DB018 pattern exactly
- [ ] Code validation uses `@validates` decorator
- [ ] Height range fields (min_height_cm, max_height_cm) are Numeric(6,2) nullable
- [ ] sort_order integer with default 99
- [ ] 7 seed records in migration
- [ ] 2 indexes created (code UK, sort_order)
- [ ] Relationships COMMENTED OUT (stock_batches, classifications not ready)
- [ ] Type hints on all methods
- [ ] Docstrings present
- [ ] `__repr__()` method implemented

**Testing Review Checklist**:
- [ ] 12-15 unit tests written
- [ ] 6-8 integration tests written
- [ ] All tests pass
- [ ] Coverage ≥75% (unit), ≥70% (integration)
- [ ] Seed data test verifies all 7 sizes
- [ ] Height range test verifies XS: 0-5, S: 5-10, etc.

**Estimated Time**: 8 minutes

---

### Step 4: Quality Gates (MANDATORY)

**Gate 1: All Acceptance Criteria Checked**
```bash
grep -c "\[x\]" /home/lucasg/proyectos/DemeterDocs/backlog/03_kanban/02_in-progress/DB019-product-sizes-enum.md
# Should be 6 (all ACs checked)
```

**Gate 2: Unit Tests Pass**
```bash
pytest tests/unit/models/test_product_size.py -v
# All tests must pass
```

**Gate 3: Integration Tests Pass**
```bash
pytest tests/integration/models/test_product_size.py -v
# All tests must pass
```

**Gate 4: Coverage ≥75%**
```bash
pytest tests/unit/models/test_product_size.py --cov=app.models.product_size --cov-report=term-missing
# TOTAL coverage ≥75%
```

**Gate 5: Type Checking**
```bash
mypy app/models/product_size.py --strict
# No errors
```

**Gate 6: Linting**
```bash
ruff check app/models/product_size.py
# No errors
```

**Gate 7: Migration Runs Successfully**
```bash
alembic upgrade head
alembic downgrade -1
alembic upgrade head
# All commands succeed, 7 seed records inserted
```

**Estimated Time**: 8 minutes

---

### Step 5: Completion

**After all gates pass**:

1. Append completion approval to task card
2. Invoke Git Commit Agent (create commit with DB018)
3. Move to `05_done/`
4. Update `DATABASE_CARDS_STATUS.md`
5. Report to Scrum Master

**Git Commit Message** (Combined with DB018):
```
feat(models): implement ProductState + ProductSize enums with seed data (DB018+DB019)

ProductState (DB018):
- 11 lifecycle states: SEED → GERMINATING → ... → DEAD
- is_sellable business logic flag (4 sellable states)
- sort_order for UI dropdowns
- Unit tests: 15-20 tests (≥75% coverage)
- Integration tests: 8-10 tests

ProductSize (DB019):
- 7 size categories: XS, S, M, L, XL, XXL, CUSTOM
- Height ranges (min_height_cm, max_height_cm)
- sort_order for UI dropdowns
- Unit tests: 12-15 tests (≥75% coverage)
- Integration tests: 6-8 tests

Total: 18 seed records, ~45-50 tests, 2 enums complete
Blocks: DB017 (Products - critical path)
```

**Estimated Time**: 5 minutes

---

## Performance Expectations

- Insert: <10ms
- Retrieve by code: <5ms (UK index)
- Retrieve all ordered by sort_order: <10ms (small reference table, <10 rows expected)

---

## Dependencies Unblocked After Completion

- **DB017**: Products model (uses product_size_id FK - nullable)
- **DB026**: Classifications (uses product_size_id FK for ML results)
- **StockBatches**: Uses product_size_id FK for size tracking

---

## Key Resources

- **Template**:
  - `/home/lucasg/proyectos/DemeterDocs/app/models/storage_bin_type.py` (DB005 pattern)
  - `/home/lucasg/proyectos/DemeterDocs/backlog/03_kanban/02_in-progress/DB018-MINI-PLAN.md` (DB018 pattern)
- **Task Card**: `/home/lucasg/proyectos/DemeterDocs/backlog/03_kanban/01_ready/DB019-product-sizes-enum.md`
- **Database ERD**: `/home/lucasg/proyectos/DemeterDocs/database/database.mmd` (lines 105-113)
- **Engineering Docs**: `/home/lucasg/proyectos/DemeterDocs/engineering_plan/database/README.md`

---

## Critical Rules

1. **NO Service→Repository violations**: This is a model, no service layer
2. **Coverage MUST be ≥75%**: Gate 4 will fail otherwise
3. **COMMENT OUT relationships**: StockBatch, Classification models not ready
4. **7 seed records REQUIRED**: XS, S, M, L, XL, XXL, CUSTOM
5. **Height ranges are NULLABLE**: CUSTOM size has NULL for both min/max

---

## Acceptance Criteria (6 ACs)

- [ ] Model created in `app/models/product_size.py`
- [ ] All columns defined with correct types (code, name, description, min_height_cm, max_height_cm, sort_order)
- [ ] Relationships configured with lazy loading strategy (COMMENT OUT until models ready)
- [ ] Alembic migration created (7 seed records)
- [ ] Indexes added for code (UK) and sort_order
- [ ] Unit tests ≥75% coverage

---

## Timeline Estimate

| Phase | Duration | Description |
|-------|----------|-------------|
| Python Expert Implementation | 20-25 min | Model + migration + seed data |
| Testing Expert (Parallel) | 25-30 min | Unit + integration tests |
| Team Leader Review | 8 min | Code + test review |
| Quality Gates | 8 min | Run all gates |
| Completion | 5 min | Commit + move to done |
| **TOTAL** | **35-40 min** | **Single task** |

**Note**: MUST be done in parallel with DB018 (ProductStates) for maximum efficiency.

---

## Parallel Execution with DB018

**Same Python Expert session**:
- Implement BOTH models in ~45-60 minutes
- Same pattern (code validation, seed data, indexes)
- Same migration approach
- Single __init__.py update

**Same Testing Expert session**:
- Write tests for BOTH models in ~45-60 minutes
- Same test patterns
- ~45-50 total tests
- Combined coverage report

**Total Time for BOTH**: 1-1.5 hours (vs 2-2.5 hours sequential)

---

**END OF MINI-PLAN DB019**
