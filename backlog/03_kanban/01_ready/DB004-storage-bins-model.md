# [DB004] StorageBins Model - Level 4 (Container/Segment)

## Metadata
- **Epic**: epic-002-database-models.md
- **Sprint**: Sprint-01 (Week 3-4)
- **Status**: `ready` (delegated to Team Leader)
- **Priority**: `HIGH` ⚡⚡ (completes geospatial hierarchy to 100%)
- **Complexity**: S (2 story points) - SIMPLEST MODEL YET
- **Area**: `database/models`
- **Assignee**: Team Leader
- **Dependencies**:
  - Blocks: [DB005-DB011 (stock models), DB012-DB014 (photo models), R004 (repository)]
  - Blocked by: [DB003 ✅ COMPLETE]

## Related Documentation
- **Engineering Plan**: ../../engineering_plan/database/README.md
- **Database ERD**: ../../database/database.mmd
- **ML Pipeline**: ../../flows/procesamiento_ml_upload_s3_principal/05_sahi_detection_child_detailed.md

## Description

Create the `storage_bins` SQLAlchemy model for level 4 (leaf level) of hierarchy. Storage bins are the physical containers where plants live (segmentos, cajones, boxes, plugs).

**What**: SQLAlchemy model for `storage_bins` table:
- Lowest level of hierarchy (warehouse → area → location → **bin**)
- Physical container: segmento, cajon, box, plug tray
- Stores position_metadata JSON from ML segmentation (mask, bbox, confidence)
- Links to storage_bin_type (defines capacity, dimensions)

**Why**:
- **Physical storage**: Where stock_batches actually live
- **ML detection target**: ML detects bins in photo, creates rows here
- **Capacity planning**: Bin type defines max capacity per bin
- **Stock movements**: Movements reference source/destination bins

**Context**: This is where stock physically exists. Stock_batches reference current_storage_bin_id. ML pipeline creates bins from segmentation results.

## Acceptance Criteria

- [ ] **AC1**: Model created in `app/models/storage_bin.py` with FKs to storage_location and storage_bin_type, position_metadata JSONB, status enum
- [ ] **AC2**: Status enum created (`CREATE TYPE storage_bin_status_enum AS ENUM ('active', 'maintenance', 'retired')`)
- [ ] **AC3**: position_metadata JSONB schema documented (segmentation_mask, bbox, confidence, ml_model_version)
- [ ] **AC4**: Code format validation: LOCATION-BIN (e.g., "INV01-NORTH-A1-SEG001")
- [ ] **AC5**: Indexes on storage_location_id, storage_bin_type_id, code, status
- [ ] **AC6**: Relationship to stock_batches (one-to-many, CASCADE delete propagates)
- [ ] **AC7**: Alembic migration with CASCADE delete from storage_location

## Technical Implementation Notes

### Architecture
- Layer: Database / Models
- Dependencies: DB003 (StorageLocation), DB005 (StorageBinType), PostgreSQL 18 JSONB
- Design pattern: Container with ML metadata

### Model Signature

```python
class StorageBin(Base):
    __tablename__ = 'storage_bins'

    bin_id = Column(Integer, PK, autoincrement=True)
    storage_location_id = Column(Integer, FK → storage_locations, CASCADE, index=True)
    storage_bin_type_id = Column(Integer, FK → storage_bin_types, RESTRICT, index=True)

    code = Column(String(100), UK, index=True)
    label = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)

    position_metadata = Column(JSONB, nullable=True)  # ML segmentation results
    status = Column(Enum('active', 'maintenance', 'retired'), default='active', index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    storage_location = relationship('StorageLocation', back_populates='storage_bins')
    storage_bin_type = relationship('StorageBinType', back_populates='storage_bins')
    stock_batches = relationship('StockBatch', back_populates='current_storage_bin')
```

### JSONB Schema for position_metadata

```python
# position_metadata structure (from ML segmentation):
{
    "segmentation_mask": [[x1, y1], [x2, y2], ...],  # Polygon vertices (px coords)
    "bbox": {"x": 100, "y": 200, "width": 300, "height": 150},  # Bounding box
    "confidence": 0.92,  # Segmentation confidence
    "ml_model_version": "yolov11-seg-v2.3",
    "detected_at": "2025-10-09T14:30:00Z",
    "container_type": "segmento"  # or "cajon"
}
```

**JSONB query examples:**
```python
# Find bins with low confidence segmentation
low_confidence_bins = session.query(StorageBin).filter(
    StorageBin.position_metadata['confidence'].as_float() < 0.7
).all()

# Find all segmentos (vs cajones)
segmentos = session.query(StorageBin).filter(
    StorageBin.position_metadata['container_type'].as_string() == 'segmento'
).all()
```

### Status Transitions

```python
# Status state machine
# active → maintenance (for cleaning/repair)
# active → retired (permanently removed)
# maintenance → active (back in service)
# retired → (terminal state, no transitions out)

@validates('status')
def validate_status_transition(self, key, new_status):
    """Validate status transitions"""
    if self.status == 'retired' and new_status != 'retired':
        raise ValueError("Cannot reactivate retired bin")
    return new_status
```

### Testing Requirements

**Unit Tests** (`tests/models/test_storage_bin.py`):
- Status enum validation
- Code format validation (LOCATION-BIN)
- position_metadata JSON structure validation
- Status transition validation (retired is terminal)

**Integration Tests** (`tests/integration/test_storage_bin.py`):
- Cascade delete from storage_location
- RESTRICT delete from storage_bin_type (cannot delete type if bins exist)
- JSONB queries (filter by confidence, container_type)
- Relationship to stock_batches

**Coverage Target**: ≥75%

### Performance Expectations
- Insert: <10ms
- Retrieve by code: <5ms (UK index)
- JSONB query (confidence filter): <50ms with GIN index
- Cascade delete: <20ms per bin

## Handover Briefing

**Context**: Leaf level of hierarchy. This is where stock physically lives. ML creates bins from segmentation, stock_batches reference bins.

**Key decisions**:
1. **position_metadata JSONB**: Stores ML segmentation output (mask, bbox, confidence)
2. **Status enum**: active/maintenance/retired (retired is terminal state)
3. **Code format**: LOCATION-BIN (e.g., "INV01-NORTH-A1-SEG001")
4. **CASCADE delete from location**: If location deleted, bins deleted (intentional)
5. **RESTRICT delete from bin_type**: Cannot delete bin type if bins exist (safety)

**Next steps**: DB007 (StockMovements - source/destination bins), DB008 (StockBatches - current_storage_bin_id), R004 (StorageBinRepository)

---

## Scrum Master Delegation (2025-10-13 16:35)

**Delegated to**: Team Leader
**Task**: DB004 - StorageBin Model (Level 4 - FINAL LEVEL of Geospatial Hierarchy)
**Priority**: HIGH - Completes geospatial hierarchy to 100%
**Complexity**: S (2 story points) - SIMPLEST MODEL YET
**Estimated Time**: 1-1.5 hours (faster than DB001-DB003)

### Why This Task NOW

**Critical Achievement**: Completes 4-level geospatial hierarchy
- Level 1: Warehouse ✅ (DB001 - 2.5 hours)
- Level 2: StorageArea ✅ (DB002 - 1.5 hours)
- Level 3: StorageLocation ✅ (DB003 - 1.5 hours)
- Level 4: StorageBin ← THIS TASK (projected: 1-1.5 hours)

**Impact**: UNBLOCKS 50% of remaining database models
- Stock Management: DB005-DB011 (7 models)
- Photo Processing: DB012-DB014 (3 models)
- Repository: R004 (StorageBinRepository)

**Sprint Velocity**: Averaging 1 hour per story point (EXCELLENT)

### Key Simplifications (Why This is EASIER than DB001-DB003)

**NO PostGIS requirements**:
- No POLYGON geometry (bins inherit location from parent)
- No POINT centroid
- No ST_Area calculations
- No GIST indexes
- No spatial containment triggers

**Simple model structure**:
- Just integer FK to storage_location_id (CASCADE)
- Optional FK to storage_bin_type_id (RESTRICT)
- Simple validation (code format, capacity range)
- JSONB position_metadata (reuse pattern from DB003)
- Status enum (active/maintenance/retired)

**Reusable Patterns from DB001-DB003**:
1. Code validation: WAREHOUSE-AREA-LOCATION-BIN pattern (e.g., "INV01-NORTH-A1-SEG001")
2. CASCADE FK relationships (from parent location)
3. Standard timestamps (created_at, updated_at)
4. Active boolean flag
5. JSONB metadata (position_metadata from ML segmentation)

### Model Implementation Guide

**File**: `app/models/storage_bin.py`

**Key Fields**:
```python
class StorageBin(Base):
    __tablename__ = 'storage_bins'

    bin_id = Column(Integer, PK, autoincrement=True)
    storage_location_id = Column(Integer, FK → storage_locations.id, CASCADE, index=True, NOT NULL)
    storage_bin_type_id = Column(Integer, FK → storage_bin_types.id, RESTRICT, index=True, NULLABLE)

    code = Column(String(100), UK, index=True)  # "INV01-NORTH-A1-SEG001"
    label = Column(String(100), nullable=True)  # Human-readable name
    description = Column(Text, nullable=True)

    capacity = Column(Integer, nullable=True)  # Max number of plants
    position_in_location = Column(String(50), nullable=True)  # Grid position: "A1", "B3"

    position_metadata = Column(JSONB, nullable=True)  # ML segmentation output
    status = Column(Enum(StorageBinStatusEnum), default='active', index=True)

    active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships (CRITICAL - re-enable in parent models after creation)
    storage_location = relationship('StorageLocation', back_populates='storage_bins')
    storage_bin_type = relationship('StorageBinType', back_populates='storage_bins')
    # NOTE: Comment out initially, uncomment after DB007
    # stock_batches = relationship('StockBatch', back_populates='current_storage_bin')
```

**Status Enum**: `CREATE TYPE storage_bin_status_enum AS ENUM ('active', 'maintenance', 'retired')`

**Code Validation**:
```python
@validates('code')
def validate_code(self, key, value):
    """Validate code format: WAREHOUSE-AREA-LOCATION-BIN (4 parts)"""
    if not value:
        raise ValueError("Code cannot be empty")

    parts = value.split('-')
    if len(parts) != 4:
        raise ValueError("Code must have 4 parts: WAREHOUSE-AREA-LOCATION-BIN")

    # Uppercase check
    if value != value.upper():
        raise ValueError("Code must be uppercase")

    # Alphanumeric check
    if not all(part.replace('_', '').isalnum() for part in parts):
        raise ValueError("Code parts must be alphanumeric")

    return value
```

**JSONB position_metadata Schema** (from ML segmentation):
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

### Migration (Alembic)

**File**: `alembic/versions/XXXX_create_storage_bins.py`

**Key Features**:
- Create `storage_bin_status_enum` type first
- CREATE TABLE with FKs (CASCADE from location, RESTRICT to bin_type)
- B-tree indexes: code (UK), storage_location_id, storage_bin_type_id, status
- GIN index on position_metadata (for JSONB queries)
- NO GIST indexes (no geometry)
- NO triggers (no spatial validation needed)

### Testing Strategy

**Unit Tests** (`tests/unit/models/test_storage_bin.py`):
Expected: 20-25 test cases
- Code validation (4-part format, uppercase, alphanumeric)
- Capacity validation (positive integer)
- Status enum (active/maintenance/retired)
- Status transition validation (retired is terminal)
- JSONB position_metadata structure
- Relationship definitions

**Integration Tests** (`tests/integration/models/test_storage_bin_geospatial.py`):
Expected: 10-15 test cases
- CASCADE delete from storage_location (bin deleted when location deleted)
- RESTRICT delete from storage_bin_type (cannot delete type if bins exist)
- JSONB queries (filter by confidence, container_type)
- Code uniqueness constraint
- FK integrity (parent location must exist)

**Coverage Target**: ≥75% (MANDATORY)

### Performance Expectations

- Insert: <10ms
- Retrieve by code: <5ms (UK index)
- JSONB query (confidence filter): <50ms with GIN index
- CASCADE delete: <20ms per bin

### Critical TODO After DB004 Completion

**Re-enable relationships** in parent models:

1. **app/models/storage_location.py** - UNCOMMENT:
   ```python
   storage_bins = relationship('StorageBin', back_populates='storage_location', cascade='all, delete-orphan')
   ```

2. **Create app/models/storage_bin_type.py** (DB005 - next task):
   - Implement StorageBinType model
   - Reference from StorageBin.storage_bin_type_id FK

### Resources

**Engineering Documentation**:
- Database ERD: `/home/lucasg/proyectos/DemeterDocs/database/database.mmd`
- Architecture: `/home/lucasg/proyectos/DemeterDocs/engineering_plan/03_architecture_overview.md`
- Workflows: `/home/lucasg/proyectos/DemeterDocs/engineering_plan/workflows/README.md`

**Reference Models** (patterns to reuse):
- DB001: Code validation, CASCADE relationships
- DB002: Simple model structure (no PostGIS)
- DB003: JSONB metadata, QR code tracking

**Test Infrastructure**:
- Pytest config: `/home/lucasg/proyectos/DemeterDocs/pyproject.toml`
- Mypy config: `/home/lucasg/proyectos/DemeterDocs/.mypy.ini`
- Pre-commit hooks: `/home/lucasg/proyectos/DemeterDocs/.pre-commit-config.yaml`

### Expected Timeline

**Total Time**: 1-1.5 hours (FASTEST MODEL YET)
- Python Expert: 0.5-1 hour (model + migration)
- Testing Expert: 0.5-1 hour (unit + integration tests)
- Team Leader Review: 15-30 minutes (validation + commit)

**Git Commit Message**:
```
feat(models): implement StorageBin model - complete geospatial hierarchy (DB004)

BREAKING CHANGE: Completes 4-level geospatial hierarchy (100%)
- Level 4 (leaf): StorageBin model with JSONB position_metadata
- Status enum: active/maintenance/retired
- Code validation: WAREHOUSE-AREA-LOCATION-BIN format
- CASCADE delete from storage_location
- RESTRICT delete from storage_bin_type
- NO PostGIS (simplest model yet)

UNBLOCKS:
- DB005-DB011: Stock management models (7 models)
- DB012-DB014: Photo processing models (3 models)
- R004: StorageBinRepository

Tests: 35+ tests (20 unit + 15 integration)
Coverage: ≥75%
Story Points: 2

Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>
```

### Success Criteria

**Ready to move to 05_done/ when**:
- [ ] Model file created with all fields
- [ ] Status enum defined
- [ ] Code validation working (4-part format)
- [ ] position_metadata JSONB schema documented
- [ ] Alembic migration created
- [ ] B-tree indexes on code, FKs, status
- [ ] GIN index on position_metadata
- [ ] Unit tests: 20-25 tests, ≥75% coverage
- [ ] Integration tests: 10-15 tests (CASCADE, RESTRICT, JSONB queries)
- [ ] Mypy strict mode: 0 errors
- [ ] Ruff linting: 0 violations
- [ ] Pre-commit hooks: All passed
- [ ] Git commit created with proper message
- [ ] StorageLocation.storage_bins relationship re-enabled

### Questions to Validate During Implementation

1. Should `capacity` be required or optional? (Nullable for now, required later)
2. Should `position_in_location` follow specific format? (Free text for now, grid validation optional)
3. Should retired bins block stock movements? (Yes - add validation in DB007)
4. Should position_metadata have schema validation? (No - JSONB is flexible, document schema only)

---

**DELEGATION COMPLETE**
**Next Action**: Team Leader uses /start-task DB004 to begin implementation
**Estimated Completion**: 2025-10-13 18:00 (1-1.5 hours from now)
**Impact**: Geospatial hierarchy 100% complete, 50% of database models unblocked

## Definition of Done Checklist

- [ ] Model code written
- [ ] Status enum created
- [ ] position_metadata JSONB schema documented
- [ ] Code validation working
- [ ] Indexes created (including GIN on JSONB)
- [ ] Unit tests ≥75% coverage
- [ ] Integration tests pass
- [ ] Alembic migration tested
- [ ] PR reviewed and approved

## Time Tracking
- **Estimated**: 2 story points
- **Actual**: TBD
- **Started**: TBD
- **Completed**: TBD

---

**Card Created**: 2025-10-09
**Last Updated**: 2025-10-09
**Card Owner**: TBD
