## Team Leader Mini-Plan (2025-10-13 16:40)

### Task Overview

- **Card**: DB004 - StorageBin Model
- **Epic**: epic-002 (Database Models)
- **Priority**: HIGH (Completes 100% geospatial hierarchy)
- **Complexity**: 2 points (S - SIMPLEST MODEL YET)
- **Location**: Level 4 (leaf level) - Final geospatial tier

### Architecture

**Layer**: Database / Models (Infrastructure Layer)
**Pattern**: SQLAlchemy 2.0 model with simplified structure (NO PostGIS)
**Hierarchy Position**: Warehouse → StorageArea → StorageLocation → **StorageBin** (LEAF)

**Dependencies**:

- DB003 (StorageLocation) - ✅ COMPLETE
- DB005 (StorageBinType) - NOT YET (FK will be NULLABLE)
- PostgreSQL 18 JSONB for position_metadata

**Key Simplifications** (Why this is FASTER than DB001-DB003):

- ❌ NO PostGIS POLYGON or POINT geometry
- ❌ NO GENERATED columns (no area_m2)
- ❌ NO spatial containment triggers
- ❌ NO centroid triggers
- ❌ NO GIST indexes (no spatial queries)
- ✅ ONLY B-tree indexes + GIN index on JSONB
- ✅ Simple CASCADE and RESTRICT FK relationships
- ✅ JSONB position_metadata (ML segmentation output)

### Files to Create/Modify

- [ ] `/home/lucasg/proyectos/DemeterDocs/app/models/storage_bin.py` (~200 lines)
- [ ] `/home/lucasg/proyectos/DemeterDocs/alembic/versions/XXXX_create_storage_bins.py` (~100 lines)
- [ ] `/home/lucasg/proyectos/DemeterDocs/tests/unit/models/test_storage_bin.py` (~300 lines)
- [ ]
  `/home/lucasg/proyectos/DemeterDocs/tests/integration/models/test_storage_bin_geospatial.py` (~200
  lines)

### Database Schema (From database.mmd lines 48-58)

```python
storage_bins {
    int bin_id PK (autoincrement)
    int storage_location_id FK (storage_locations.location_id, CASCADE, NOT NULL)
    int storage_bin_type_id FK (storage_bin_types.id, RESTRICT, NULLABLE)
    varchar code UK (WAREHOUSE-AREA-LOCATION-BIN, e.g., "INV01-NORTH-A1-SEG001")
    varchar label (human-readable name, NULLABLE)
    text description (NULLABLE)
    jsonb position_metadata (ML segmentation output: mask, bbox, confidence)
    varchar status (enum: active, maintenance, retired)
    timestamp created_at (auto)
}
```

**Status Enum**: `CREATE TYPE storage_bin_status_enum AS ENUM ('active', 'maintenance', 'retired')`

### Implementation Strategy

#### Python Expert Task: Model + Migration

**File 1**: `app/models/storage_bin.py`

**Key Features**:

1. **Primary Key**: `bin_id` (Integer, autoincrement)
2. **Foreign Keys**:
    - `storage_location_id` → storage_locations.location_id (CASCADE, NOT NULL)
    - `storage_bin_type_id` → storage_bin_types.id (RESTRICT, NULLABLE)
3. **Code Validation**: 4-part pattern: WAREHOUSE-AREA-LOCATION-BIN
    - Example: "INV01-NORTH-A1-SEG001"
    - Regex: `^[A-Z0-9_-]+-[A-Z0-9_-]+-[A-Z0-9_-]+-[A-Z0-9_-]+$`
    - Must be uppercase
    - 2-100 characters
4. **Status Enum**: active, maintenance, retired
    - Validation: retired is terminal state (cannot transition out)
5. **JSONB position_metadata Schema** (from ML segmentation):
   ```python
   {
       "segmentation_mask": [[x1, y1], [x2, y2], ...],  # Polygon vertices (px)
       "bbox": {"x": 100, "y": 200, "width": 300, "height": 150},
       "confidence": 0.92,
       "ml_model_version": "yolov11-seg-v2.3",
       "detected_at": "2025-10-09T14:30:00Z",
       "container_type": "segmento"  # or "cajon"
   }
   ```
6. **Relationships**:
    - `storage_location` (many-to-one, back_populates='storage_bins')
    - `storage_bin_type` (many-to-one, back_populates='storage_bins')
    - `stock_batches` (one-to-many, COMMENT OUT - DB007 not ready)

**File 2**: `alembic/versions/XXXX_create_storage_bins.py`

**Key Features**:

1. Create `storage_bin_status_enum` type FIRST
2. CREATE TABLE storage_bins with:
    - Primary key: bin_id (SERIAL)
    - FKs with proper CASCADE/RESTRICT
    - Unique constraint on code
    - Status enum column with default 'active'
    - JSONB position_metadata (nullable)
3. **Indexes** (NO GIST, only B-tree + GIN):
    - B-tree index on code (UK, fast lookups)
    - B-tree index on storage_location_id (FK queries)
    - B-tree index on storage_bin_type_id (FK queries)
    - B-tree index on status (filtering)
    - GIN index on position_metadata (JSONB queries: confidence, container_type)
4. **NO triggers** (no spatial validation needed)

**Reusable Patterns** (from DB001-DB003):

- Code validation: Similar to StorageLocation (3-part → 4-part)
- CASCADE FK: Same pattern as DB002 (parent → child)
- JSONB metadata: Similar to StorageLocation.position_metadata
- Enum validation: Similar to StorageArea.PositionEnum
- Standard timestamps: created_at (with server_default=func.now())

#### Testing Expert Task: Unit + Integration Tests

**File 1**: `tests/unit/models/test_storage_bin.py`

**Expected Test Cases** (20-25 tests):

1. **Code Validation Tests** (8 tests):
    - Valid 4-part code: "INV01-NORTH-A1-SEG001"
    - Invalid: 3-part code (missing BIN)
    - Invalid: 5-part code (too many parts)
    - Invalid: Lowercase code (must uppercase)
    - Invalid: Empty code
    - Invalid: Special characters (only alphanumeric + _ -)
    - Invalid: Too short (<2 chars)
    - Invalid: Too long (>100 chars)

2. **Status Enum Tests** (5 tests):
    - Valid: active, maintenance, retired
    - Transition: active → maintenance (valid)
    - Transition: maintenance → active (valid)
    - Transition: active → retired (valid)
    - Transition: retired → active (INVALID - terminal state)

3. **JSONB position_metadata Tests** (4 tests):
    - Valid full schema (all fields)
    - Valid partial schema (optional fields)
    - Query by confidence (filter low confidence bins)
    - Query by container_type (segmento vs cajon)

4. **Relationship Tests** (3 tests):
    - storage_location relationship exists
    - storage_bin_type relationship exists
    - stock_batches relationship commented out (not ready)

5. **Basic CRUD Tests** (5 tests):
    - Create bin with all fields
    - Create bin with minimal fields
    - Update bin status
    - Soft delete (no active flag for bins)
    - Check timestamps (created_at)

**Coverage Target**: ≥75% (MANDATORY)

**File 2**: `tests/integration/models/test_storage_bin_geospatial.py`

**Expected Test Cases** (10-15 tests):

1. **CASCADE Delete Tests** (3 tests):
    - Delete storage_location → bins deleted (CASCADE)
    - Delete storage_area → locations + bins deleted (CASCADE chain)
    - Delete warehouse → areas + locations + bins deleted (CASCADE chain)

2. **RESTRICT Delete Tests** (2 tests):
    - Delete storage_bin_type with bins → FAILS (RESTRICT)
    - Delete storage_bin_type without bins → SUCCESS

3. **JSONB Query Tests** (4 tests):
    - Filter bins by confidence > 0.9
    - Filter bins by confidence < 0.7 (low confidence)
    - Filter bins by container_type = 'segmento'
    - Filter bins by ml_model_version

4. **Code Uniqueness Tests** (2 tests):
    - Create two bins with same code → FAILS (UK constraint)
    - Create bins with different codes → SUCCESS

5. **FK Integrity Tests** (3 tests):
    - Create bin with non-existent storage_location_id → FAILS
    - Create bin with NULL storage_location_id → FAILS (NOT NULL)
    - Create bin with NULL storage_bin_type_id → SUCCESS (NULLABLE)

**Coverage Target**: ≥70% (integration tests)

### Performance Expectations

- Insert: <10ms
- Retrieve by code: <5ms (UK index)
- JSONB query (confidence filter): <50ms (with GIN index)
- CASCADE delete: <20ms per bin

### Acceptance Criteria (From Task Card)

- [ ] AC1: Model created in `app/models/storage_bin.py` with FKs to storage_location and
  storage_bin_type, position_metadata JSONB, status enum
- [ ] AC2: Status enum created (
  `CREATE TYPE storage_bin_status_enum AS ENUM ('active', 'maintenance', 'retired')`)
- [ ] AC3: position_metadata JSONB schema documented (segmentation_mask, bbox, confidence,
  ml_model_version)
- [ ] AC4: Code format validation: LOCATION-BIN (e.g., "INV01-NORTH-A1-SEG001")
- [ ] AC5: Indexes on storage_location_id, storage_bin_type_id, code, status
- [ ] AC6: Relationship to stock_batches (one-to-many, CASCADE delete propagates) - COMMENTED OUT
- [ ] AC7: Alembic migration with CASCADE delete from storage_location

### Critical TODO After DB004 Completion

**Re-enable relationships** in parent models:

1. **MANDATORY**: Uncomment in `/home/lucasg/proyectos/DemeterDocs/app/models/storage_location.py` (
   lines 273-279):
   ```python
   storage_bins: Mapped[list["StorageBin"]] = relationship(
       "StorageBin",
       back_populates="storage_location",
       cascade="all, delete-orphan",
       lazy="selectin",
       doc="List of storage bins within this location"
   )
   ```

2. **Future**: Create StorageBinType model (DB005 - next task after this)

### Next Steps

1. Move task to `02_in-progress/`
2. Spawn Python Expert + Testing Expert (PARALLEL - ONE message with TWO Task calls)
3. Monitor progress (both experts update task file)
4. Review code (Python Expert completes first)
5. Run quality gates (Testing Expert completes)
6. Re-enable StorageLocation.storage_bins relationship
7. Approve completion
8. Invoke git-commit-writer agent
9. Move to `05_done/`

### Timeline Estimate

- **Python Expert**: 30-45 minutes (model + migration, NO PostGIS complexity)
- **Testing Expert**: 30-45 minutes (unit + integration tests, simpler than DB003)
- **Team Leader Review**: 15-20 minutes (validation + commit)
- **Total**: 1-1.5 hours (FASTEST MODEL YET)

### Success Criteria

- ✅ StorageBin model (NO PostGIS)
- ✅ Migration (simple, no triggers)
- ✅ Unit + integration tests (≥75% coverage)
- ✅ All quality gates passed (mypy, ruff, pytest)
- ✅ StorageLocation relationship re-enabled
- ✅ **100% GEOSPATIAL HIERARCHY COMPLETE**
- ✅ **UNBLOCKS 11 MODELS** (DB005-DB014)

---

## Mini-Plan Complete - Ready to Execute

**Status**: APPROVED by Team Leader
**Next Action**: Spawn Python Expert + Testing Expert in parallel
**Estimated Completion**: 2025-10-13 18:10 (1-1.5 hours)
