# Team Leader Mini-Plan: DB005 - StorageBinTypes Model

**Date**: 2025-10-14 10:30
**Team Leader**: Claude
**Task**: DB005 - StorageBinTypes Model (Container Type Catalog)
**Sprint**: Sprint-01 (Week 3-4)
**Epic**: epic-002-database-models

---

## Task Overview

- **Card**: DB005 - StorageBinTypes Model
- **Epic**: epic-002 (Database Models)
- **Priority**: HIGH (reference data for DB004)
- **Complexity**: 1 point (S - SIMPLE catalog + seed data)
- **Category**: Reference/Catalog Table

---

## Architecture

**Layer**: Database / Models (Infrastructure Layer)
**Pattern**: SQLAlchemy 2.0 model - Reference/Catalog table with seed data
**Dependencies**:
- Referenced by: DB004 (storage_bin_type_id FK) - ALREADY COMPLETE
- Blocks: DB025 (DensityParameters - uses bin_type_id FK)
- PostgreSQL 18 enums + standard types

**Key Features**:
1. **Category enum**: 5 types (plug, seedling_tray, box, segment, pot)
2. **Nullable dimensions**: Not all types have fixed size (ML-detected segments)
3. **Grid flag**: True for plug trays (rows × columns grid capacity)
4. **CHECK constraint**: If is_grid=true, then rows/columns must NOT be NULL
5. **SEED DATA**: 6-10 common bin types preloaded in migration

---

## Files to Create/Modify

- [ ] `/home/lucasg/proyectos/DemeterDocs/app/models/storage_bin_type.py` (~150 lines)
- [ ] `/home/lucasg/proyectos/DemeterDocs/alembic/versions/XXXX_create_storage_bin_types.py` (~120 lines + seed data)
- [ ] `/home/lucasg/proyectos/DemeterDocs/tests/unit/models/test_storage_bin_type.py` (~400 lines)
- [ ] `/home/lucasg/proyectos/DemeterDocs/tests/integration/models/test_storage_bin_type.py` (~300 lines)

---

## Database Schema (From database.mmd lines 59-74)

```python
storage_bin_types {
    int bin_type_id PK (autoincrement, or just "id")
    varchar code UK (uppercase, alphanumeric, 3-50 chars, e.g., "PLUG_TRAY_288")
    varchar name (human-readable, e.g., "288-Cell Plug Tray")
    varchar category (enum: plug, seedling_tray, box, segment, pot)
    text description (optional details)

    # Dimensions (NULLABLE - not all types have fixed dimensions)
    int rows (nullable - for grid types only)
    int columns (nullable - for grid types only)
    int capacity (nullable - total capacity, may differ from rows×columns)
    numeric length_cm (nullable - container length)
    numeric width_cm (nullable - container width)
    numeric height_cm (nullable - container height)

    boolean is_grid (default FALSE - TRUE for plug trays with rows×columns)

    timestamp created_at (auto)
    timestamp updated_at (auto)
}
```

**Category Enum**: `CREATE TYPE bin_category_enum AS ENUM ('plug', 'seedling_tray', 'box', 'segment', 'pot')`

**CHECK Constraint**:
```sql
ALTER TABLE storage_bin_types
ADD CONSTRAINT check_grid_has_rows_columns
CHECK (
    (is_grid = false) OR
    (is_grid = true AND rows IS NOT NULL AND columns IS NOT NULL)
);
```

---

## Implementation Strategy

### Phase 1: Python Expert (Model + Migration + Seed Data)

**File 1**: `app/models/storage_bin_type.py` (~150 lines)

**Key Features**:
1. **Primary Key**: `bin_type_id` (Integer, autoincrement) OR just `id` (follow DB001-DB004 pattern)
2. **Code validation**:
   - Uppercase
   - Alphanumeric (+ underscores allowed)
   - 3-50 characters
   - Unique constraint
3. **Category Enum**: BinCategoryEnum (plug, seedling_tray, box, segment, pot)
4. **Nullable dimensions**: All dimension fields (rows, columns, capacity, length_cm, width_cm, height_cm) are NULLABLE
5. **Grid flag**: Boolean `is_grid` (default FALSE)
6. **CHECK constraint**: Applied in model via `__table_args__`
7. **Relationships**:
   - `storage_bins` (one-to-many, back_populates='storage_bin_type')
   - `density_parameters` (one-to-many, COMMENT OUT - DB025 not ready yet)

**Code Validation Pattern** (from DB001-DB004):
```python
@validates('code')
def validate_code(self, key: str, value: str) -> str:
    """Validate storage bin type code format.

    Rules:
        1. Required (not empty)
        2. Must be uppercase
        3. Alphanumeric + underscores only
        4. Length between 3 and 50 characters
    """
    if not value or not value.strip():
        raise ValueError("Storage bin type code cannot be empty")

    code = value.strip().upper()

    if not re.match(r'^[A-Z0-9_]+$', code):
        raise ValueError(
            f"Storage bin type code must be alphanumeric + underscores only (got: {code})"
        )

    if len(code) < 3 or len(code) > 50:
        raise ValueError(f"Storage bin type code must be 3-50 characters (got {len(code)} chars)")

    return code
```

**File 2**: `alembic/versions/XXXX_create_storage_bin_types.py` (~120 lines + seed data)

**Key Features**:
1. Create `bin_category_enum` type FIRST
2. CREATE TABLE storage_bin_types with:
   - Primary key: bin_type_id (SERIAL) OR id (follow convention)
   - Unique constraint on code
   - Category enum column (NOT NULL)
   - All dimension fields NULLABLE
   - is_grid boolean (default FALSE)
   - Timestamps (created_at with server_default, updated_at with onupdate)
3. **CHECK constraint**: Grid types must have rows AND columns NOT NULL
4. **Indexes**:
   - B-tree index on code (UK, fast lookups)
   - B-tree index on category (filtering)
5. **SEED DATA** (6-10 common types):

```sql
-- PLUG TRAYS (is_grid = TRUE, rows/columns NOT NULL)
INSERT INTO storage_bin_types (code, name, category, rows, columns, capacity, is_grid, length_cm, width_cm, height_cm, description) VALUES
('PLUG_TRAY_288', '288-Cell Plug Tray', 'plug', 18, 16, 288, TRUE, 54.0, 27.5, 5.5, 'Standard 288-cell plug tray (18 rows × 16 columns)'),
('PLUG_TRAY_128', '128-Cell Plug Tray', 'plug', 8, 16, 128, TRUE, 54.0, 27.5, 6.0, 'Standard 128-cell plug tray (8 rows × 16 columns)'),
('PLUG_TRAY_72', '72-Cell Plug Tray', 'plug', 6, 12, 72, TRUE, 54.0, 27.5, 6.5, 'Standard 72-cell plug tray (6 rows × 12 columns)'),

-- SEEDLING TRAYS (is_grid = TRUE, rows/columns NOT NULL)
('SEEDLING_TRAY_50', '50-Cell Seedling Tray', 'seedling_tray', 5, 10, 50, TRUE, 54.0, 27.5, 6.0, 'Standard 50-cell seedling tray (5 rows × 10 columns)'),

-- BOXES (is_grid = FALSE, rows/columns NULL)
('BOX_STANDARD', 'Standard Transport Box', 'box', NULL, NULL, 100, FALSE, 60.0, 40.0, 30.0, 'Standard transport box for plant storage'),

-- SEGMENTS (is_grid = FALSE, rows/columns NULL, NO dimensions)
('SEGMENT_STANDARD', 'Individual Segment', 'segment', NULL, NULL, NULL, FALSE, NULL, NULL, NULL, 'Individual segment detected by ML (no fixed dimensions)'),

-- POTS (is_grid = FALSE, rows/columns NULL)
('POT_10CM', '10cm Diameter Pot', 'pot', NULL, NULL, 1, FALSE, 10.0, 10.0, 10.0, 'Standard 10cm diameter pot for individual plants');
```

**Reusable Patterns** (from DB001-DB004):
- Code validation: Similar to Warehouse/StorageArea (uppercase, alphanumeric)
- Enum creation: Same pattern as StorageArea.PositionEnum
- Seed data in migration: INSERT INTO ... VALUES (...), (...) pattern
- CHECK constraints: Applied in migration via ALTER TABLE ADD CONSTRAINT
- Standard timestamps: created_at (server_default=func.now()), updated_at (onupdate=func.now())

---

### Phase 2: Testing Expert (Unit + Integration Tests)

**File 1**: `tests/unit/models/test_storage_bin_type.py` (~400 lines, 15-20 tests)

**Expected Test Cases**:
1. **Category Enum Tests** (3 tests):
   - Valid categories: plug, seedling_tray, box, segment, pot
   - Invalid category: raises error
   - Category assignment and retrieval

2. **Code Validation Tests** (6 tests):
   - Valid code: "PLUG_TRAY_288" (uppercase, alphanumeric + underscore)
   - Invalid: Lowercase code (should auto-uppercase)
   - Invalid: Special characters (e.g., "PLUG-TRAY-288" with hyphens)
   - Invalid: Empty code
   - Invalid: Too short (<3 chars)
   - Invalid: Too long (>50 chars)

3. **Grid CHECK Constraint Tests** (4 tests):
   - Valid: is_grid=TRUE with rows AND columns NOT NULL
   - Valid: is_grid=FALSE with rows/columns NULL
   - Invalid: is_grid=TRUE with rows NULL (should fail CHECK)
   - Invalid: is_grid=TRUE with columns NULL (should fail CHECK)

4. **Nullable Dimensions Tests** (2 tests):
   - Valid: Create type with all dimensions NULL (segment)
   - Valid: Create type with partial dimensions (only capacity)

5. **Relationship Tests** (2 tests):
   - storage_bins relationship exists
   - density_parameters relationship commented out (not ready)

6. **Basic CRUD Tests** (3 tests):
   - Create type with all fields
   - Create type with minimal fields
   - Check timestamps (created_at, updated_at)

**Coverage Target**: ≥75%

**File 2**: `tests/integration/models/test_storage_bin_type.py` (~300 lines, 5-10 tests)

**Expected Test Cases**:
1. **Seed Data Tests** (2 tests):
   - Verify all 6-10 seed types exist after migration
   - Verify seed data integrity (correct categories, dimensions, grid flags)

2. **RESTRICT Delete Tests** (2 tests):
   - Delete bin_type with storage_bins → FAILS (RESTRICT)
   - Delete bin_type without storage_bins → SUCCESS

3. **Relationship Tests** (2 tests):
   - Query storage_bins from bin_type
   - Verify FK integrity (storage_bins.storage_bin_type_id → storage_bin_types.id)

4. **Code Uniqueness Tests** (2 tests):
   - Create two types with same code → FAILS (UK constraint)
   - Create types with different codes → SUCCESS

5. **CHECK Constraint Integration Tests** (2 tests):
   - Insert is_grid=TRUE with NULL rows → FAILS at DB level
   - Insert is_grid=FALSE with NULL rows → SUCCESS

**Coverage Target**: ≥70%

---

## Performance Expectations

- Insert: <10ms (small reference table)
- Retrieve by code: <5ms (UK index)
- Retrieve all: <10ms (≤100 rows expected)
- Seed data loading: <50ms (6-10 rows)

---

## Acceptance Criteria (From Task Card)

- [ ] **AC1**: Model created in `app/models/storage_bin_type.py` with category enum, dimensions (nullable), capacity fields, grid flag
- [ ] **AC2**: Category enum created (`CREATE TYPE bin_category_enum AS ENUM ('plug', 'seedling_tray', 'box', 'segment', 'pot')`)
- [ ] **AC3**: Code validation (uppercase, alphanumeric, 3-50 chars, unique)
- [ ] **AC4**: CHECK constraint: if is_grid=true, then rows/columns must be NOT NULL
- [ ] **AC5**: Seed data migration with common bin types (PLUG_TRAY_288, PLUG_TRAY_128, SEEDLING_BOX_STANDARD, etc.)
- [ ] **AC6**: Indexes on code, category
- [ ] **AC7**: Alembic migration with seed data

---

## Critical TODO After DB005 Completion

**Re-enable relationship** in parent model:

1. **MANDATORY**: Uncomment in `/home/lucasg/proyectos/DemeterDocs/app/models/storage_bin.py` (lines 256-263):
   ```python
   storage_bin_type: Mapped["StorageBinType | None"] = relationship(
       "StorageBinType",
       back_populates="storage_bins",
       foreign_keys=[storage_bin_type_id],
       doc="Bin type definition (capacity, dimensions)"
   )
   ```

2. **Update imports**: Add StorageBinType to `app/models/__init__.py` exports

---

## Timeline Estimate

- **Python Expert**: 20-30 minutes (simple model + seed data)
- **Testing Expert**: 20-30 minutes (unit + integration tests, seed verification)
- **Team Leader Review**: 10-15 minutes (validation + commit)
- **Total**: 30-45 minutes (FASTEST YET - simple catalog table)

---

## Success Criteria

- ✅ StorageBinType model with category enum
- ✅ Code validation (uppercase, 3-50 chars)
- ✅ CHECK constraint for grid types
- ✅ Migration with seed data (6-10 types)
- ✅ Unit + integration tests (≥75% coverage)
- ✅ All quality gates passed (mypy, ruff, pytest)
- ✅ StorageBin relationship re-enabled
- ✅ Seed data verified in integration tests
- ✅ **DB025 UNBLOCKED** (DensityParameters can now reference bin_type_id)

---

## Mini-Plan Complete - Ready to Execute

**Status**: APPROVED by Team Leader
**Next Action**: Spawn Python Expert + Testing Expert in parallel (ONE message with TWO delegations)
**Estimated Completion**: 2025-10-14 11:15 (30-45 minutes)

---

## Notes

**Why This is SIMPLE**:
- NO PostGIS (just reference table)
- NO complex triggers
- NO spatial queries
- ONLY code validation + CHECK constraint
- Seed data is straightforward INSERT statements

**Pattern from DB004**:
- Follow StorageBin model structure (simpler, no PostGIS)
- Reuse code validation pattern (uppercase, alphanumeric)
- Reuse enum creation pattern
- Reuse timestamp pattern

**Key Difference from DB001-DB004**:
- This is a CATALOG/REFERENCE table (rarely changes)
- Seed data is CRITICAL (preload 6-10 common types)
- CHECK constraint logic (grid types must have rows/columns)
- Nullable dimensions (ML-detected segments don't have fixed size)

---

**READY TO DELEGATE**


## Team Leader Final Approval (2025-10-20 - RETROACTIVE)

**Status**: ✅ COMPLETED (retroactive verification)

### Verification Results
- [✅] Implementation complete per task specification
- [✅] Code follows Clean Architecture patterns
- [✅] Type hints and validations present
- [✅] Unit tests implemented and passing
- [✅] Integration with PostgreSQL verified

### Quality Gates
- [✅] SQLAlchemy 2.0 async model
- [✅] Type hints complete
- [✅] SOLID principles followed
- [✅] No syntax errors
- [✅] Imports working correctly

### Completion Status
Retroactive approval based on audit of Sprint 00-02.
Code verified to exist and function correctly against PostgreSQL test database.

**Completion date**: 2025-10-20 (retroactive)
**Verified by**: Audit process
