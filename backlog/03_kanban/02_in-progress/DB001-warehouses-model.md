# [DB001] Warehouses Model - PostGIS Geospatial Root

## Metadata
- **Epic**: epic-002-database-models.md
- **Sprint**: Sprint-01 (Week 3-4)
- **Status**: `backlog`
- **Priority**: `high` (foundation for location hierarchy)
- **Complexity**: M (2 story points)
- **Area**: `database/models`
- **Assignee**: TBD
- **Dependencies**:
  - Blocks: [DB002, DB006, R001]
  - Blocked by: [F007-alembic-setup, F006-database-connection]

## Related Documentation
- **Engineering Plan**: ../../engineering_plan/database/README.md
- **Database ERD**: ../../database/database.mmd
- **Architecture**: ../../engineering_plan/03_architecture_overview.md
- **PostGIS Guide**: https://postgis.net/documentation/

## Description

Create the `warehouses` SQLAlchemy model with **PostGIS geometry support** for the root level of the 4-tier location hierarchy. This is the top-level container representing physical cultivation facilities.

**What**: SQLAlchemy model for `warehouses` table (level 1 of hierarchy):
- Stores greenhouse, shadehouse, and open field facilities
- PostGIS geometry for precise boundary definitions
- Auto-calculated area from geometry
- Supports multiple warehouse types

**Why**:
- **Hierarchy root**: Foundation of warehouse → storage_area → storage_location → storage_bin
- **Geospatial precision**: GPS-based photo localization needs accurate boundaries
- **Multi-facility**: System manages multiple cultivation zones
- **Area calculations**: Auto-compute area_m2 for capacity planning

**Context**: This is the first level of the geospatial hierarchy. All photos, stock, and locations ultimately belong to a warehouse. PostGIS is essential for photo GPS → location mapping.

## Acceptance Criteria

- [ ] **AC1**: Model created in `app/models/warehouse.py`:
  ```python
  from sqlalchemy import Column, Integer, String, Boolean, DateTime, Numeric, Enum, CheckConstraint
  from sqlalchemy.orm import relationship
  from sqlalchemy.sql import func
  from geoalchemy2 import Geometry
  from app.models.base import Base

  class Warehouse(Base):
      __tablename__ = 'warehouses'

      # Primary key
      warehouse_id = Column(Integer, primary_key=True, autoincrement=True)

      # Identification
      code = Column(String(50), unique=True, nullable=False, index=True)
      name = Column(String(200), nullable=False)

      # Type classification
      warehouse_type = Column(
          Enum(
              'greenhouse', 'shadehouse', 'open_field', 'tunnel',
              name='warehouse_type_enum'
          ),
          nullable=False,
          index=True
      )

      # PostGIS geometry (polygon boundaries)
      geojson_coordinates = Column(
          Geometry('POLYGON', srid=4326),
          nullable=False
      )

      # Centroid (for quick distance calculations)
      centroid = Column(
          Geometry('POINT', srid=4326),
          nullable=True
      )

      # Auto-calculated area (GENERATED column in PostgreSQL 18)
      area_m2 = Column(
          Numeric(10, 2),
          nullable=True,
          comment="Auto-calculated from geojson_coordinates"
      )

      # Status
      active = Column(Boolean, default=True, nullable=False, index=True)

      # Timestamps
      created_at = Column(DateTime(timezone=True), server_default=func.now())
      updated_at = Column(DateTime(timezone=True), onupdate=func.now())

      # Relationships
      storage_areas = relationship(
          'StorageArea',
          back_populates='warehouse',
          cascade='all, delete-orphan',
          lazy='selectinload'
      )
  ```

- [ ] **AC2**: Warehouse type enum created in migration:
  ```sql
  CREATE TYPE warehouse_type_enum AS ENUM (
      'greenhouse',   -- Enclosed glass/plastic structure
      'shadehouse',   -- Covered with shade cloth
      'open_field',   -- Outdoor cultivation area
      'tunnel'        -- Low tunnel / hoop house
  );
  ```

- [ ] **AC3**: PostGIS GENERATED column for area calculation:
  ```sql
  -- In Alembic migration, add GENERATED column:
  ALTER TABLE warehouses
  ADD COLUMN area_m2 NUMERIC(10,2)
  GENERATED ALWAYS AS (
      ST_Area(geojson_coordinates::geography)
  ) STORED;
  ```

- [ ] **AC4**: Trigger for auto-calculating centroid:
  ```sql
  -- Trigger to auto-update centroid when geometry changes
  CREATE OR REPLACE FUNCTION update_warehouse_centroid()
  RETURNS TRIGGER AS $$
  BEGIN
      NEW.centroid = ST_Centroid(NEW.geojson_coordinates);
      RETURN NEW;
  END;
  $$ LANGUAGE plpgsql;

  CREATE TRIGGER trg_warehouse_centroid
  BEFORE INSERT OR UPDATE OF geojson_coordinates ON warehouses
  FOR EACH ROW
  EXECUTE FUNCTION update_warehouse_centroid();
  ```

- [ ] **AC5**: Indexes for geospatial and common queries:
  ```sql
  -- Spatial index (GIST for PostGIS)
  CREATE INDEX idx_warehouses_geom ON warehouses USING GIST(geojson_coordinates);
  CREATE INDEX idx_warehouses_centroid ON warehouses USING GIST(centroid);

  -- Standard indexes
  CREATE INDEX idx_warehouses_code ON warehouses(code);
  CREATE INDEX idx_warehouses_type ON warehouses(warehouse_type);
  CREATE INDEX idx_warehouses_active ON warehouses(active);
  ```

- [ ] **AC6**: Validation for code format:
  ```python
  from sqlalchemy.orm import validates

  @validates('code')
  def validate_code(self, key, value):
      """Warehouse code must be uppercase alphanumeric, 2-20 chars"""
      if not value:
          raise ValueError("Warehouse code is required")
      if not value.isupper():
          raise ValueError("Warehouse code must be uppercase")
      if not value.replace('_', '').replace('-', '').isalnum():
          raise ValueError("Warehouse code must be alphanumeric (with - or _)")
      if not (2 <= len(value) <= 20):
          raise ValueError("Warehouse code must be 2-20 characters")
      return value
  ```

- [ ] **AC7**: Alembic migration created and tested (upgrade + downgrade)

## Technical Implementation Notes

### Architecture
- Layer: Database / Models
- Dependencies: PostGIS 3.3+, SQLAlchemy 2.0.43, GeoAlchemy2 0.14+
- Design pattern: Geospatial hierarchy root with GENERATED columns

### Code Hints

**GeoAlchemy2 usage for PostGIS:**
```python
from geoalchemy2 import Geometry
from geoalchemy2.shape import to_shape, from_shape
from shapely.geometry import Polygon, Point

# Model field definition
geojson_coordinates = Column(Geometry('POLYGON', srid=4326), nullable=False)

# Inserting geometry from GeoJSON
from shapely.geometry import shape
geojson = {"type": "Polygon", "coordinates": [[...]]}
polygon = shape(geojson)
warehouse.geojson_coordinates = from_shape(polygon, srid=4326)

# Reading geometry to GeoJSON
from geoalchemy2.shape import to_shape
polygon = to_shape(warehouse.geojson_coordinates)
geojson = polygon.__geo_interface__
```

**Spatial query example (find nearest warehouse to GPS point):**
```python
from geoalchemy2.functions import ST_Distance

def find_nearest_warehouse(latitude: float, longitude: float):
    """Find closest warehouse to GPS coordinates"""
    point = func.ST_SetSRID(func.ST_MakePoint(longitude, latitude), 4326)

    return session.query(Warehouse).order_by(
        ST_Distance(Warehouse.centroid, point)
    ).first()
```

**Area calculation verification:**
```python
def verify_area(warehouse_id: int):
    """Verify GENERATED area matches manual calculation"""
    warehouse = session.query(Warehouse).get(warehouse_id)

    # Manual calculation
    manual_area = session.scalar(
        select(func.ST_Area(warehouse.geojson_coordinates.cast(Geography)))
    )

    assert abs(warehouse.area_m2 - manual_area) < 0.01  # Within 1cm²
```

### Testing Requirements

**Unit Tests** (`tests/models/test_warehouse.py`):
```python
import pytest
from shapely.geometry import Polygon
from geoalchemy2.shape import from_shape
from app.models.warehouse import Warehouse

def test_warehouse_code_validation():
    """Code must be uppercase alphanumeric"""
    warehouse = Warehouse(
        code="INV01",  # Valid
        name="Main Greenhouse",
        warehouse_type="greenhouse"
    )

    # Lowercase should fail
    with pytest.raises(ValueError):
        warehouse.code = "inv01"

    # Special chars should fail
    with pytest.raises(ValueError):
        warehouse.code = "INV@01"

def test_warehouse_type_enum():
    """Type accepts only valid enum values"""
    warehouse = Warehouse()
    for wtype in ['greenhouse', 'shadehouse', 'open_field', 'tunnel']:
        warehouse.warehouse_type = wtype  # Should not raise

    with pytest.raises(StatementError):
        warehouse.warehouse_type = 'invalid_type'

def test_geometry_assignment():
    """Can assign PostGIS geometry from shapely"""
    coords = [
        (-70.648300, -33.448900),  # SW corner
        (-70.647300, -33.448900),  # SE corner
        (-70.647300, -33.449900),  # NE corner
        (-70.648300, -33.449900),  # NW corner
        (-70.648300, -33.448900)   # Close polygon
    ]
    polygon = Polygon(coords)

    warehouse = Warehouse(
        code="TEST01",
        name="Test Warehouse",
        warehouse_type="greenhouse",
        geojson_coordinates=from_shape(polygon, srid=4326)
    )

    assert warehouse.geojson_coordinates is not None
```

**Integration Tests** (`tests/integration/test_warehouse_geospatial.py`):
```python
@pytest.mark.asyncio
async def test_warehouse_area_auto_calculation(db_session):
    """Area is auto-calculated from geometry"""
    # Create 100m x 50m rectangle
    coords = [
        (-70.648300, -33.448900),
        (-70.647300, -33.448900),
        (-70.647300, -33.449400),
        (-70.648300, -33.449400),
        (-70.648300, -33.448900)
    ]
    polygon = Polygon(coords)

    warehouse = Warehouse(
        code="AREA01",
        name="Area Test Warehouse",
        warehouse_type="greenhouse",
        geojson_coordinates=from_shape(polygon, srid=4326)
    )

    db_session.add(warehouse)
    await db_session.commit()
    await db_session.refresh(warehouse)

    # Verify area was auto-calculated (approximate)
    assert warehouse.area_m2 is not None
    assert warehouse.area_m2 > 0

@pytest.mark.asyncio
async def test_centroid_auto_calculation(db_session):
    """Centroid is auto-calculated via trigger"""
    coords = [
        (-70.648300, -33.448900),
        (-70.647300, -33.448900),
        (-70.647300, -33.449900),
        (-70.648300, -33.449900),
        (-70.648300, -33.448900)
    ]
    polygon = Polygon(coords)

    warehouse = Warehouse(
        code="CENT01",
        name="Centroid Test",
        warehouse_type="greenhouse",
        geojson_coordinates=from_shape(polygon, srid=4326)
    )

    db_session.add(warehouse)
    await db_session.commit()
    await db_session.refresh(warehouse)

    # Centroid should be auto-populated
    assert warehouse.centroid is not None

    # Verify centroid is inside polygon
    from geoalchemy2.shape import to_shape
    polygon_shape = to_shape(warehouse.geojson_coordinates)
    centroid_shape = to_shape(warehouse.centroid)
    assert polygon_shape.contains(centroid_shape)

@pytest.mark.asyncio
async def test_find_warehouses_within_radius(db_session):
    """Spatial query: find warehouses near GPS point"""
    # Create warehouse
    coords = [(-70.648, -33.449), (-70.647, -33.449),
              (-70.647, -33.450), (-70.648, -33.450), (-70.648, -33.449)]
    warehouse = Warehouse(
        code="NEAR01",
        name="Nearby Warehouse",
        warehouse_type="greenhouse",
        geojson_coordinates=from_shape(Polygon(coords), srid=4326)
    )
    db_session.add(warehouse)
    await db_session.commit()

    # Query warehouses within 1km of point
    target_point = func.ST_SetSRID(func.ST_MakePoint(-70.6475, -33.4495), 4326)

    result = await db_session.execute(
        select(Warehouse).where(
            func.ST_DWithin(
                Warehouse.centroid.cast(Geography),
                target_point.cast(Geography),
                1000  # 1km radius
            )
        )
    )

    nearby = result.scalars().all()
    assert len(nearby) >= 1
    assert warehouse in nearby
```

**Coverage Target**: ≥80%

### Performance Expectations
- Insert: <15ms (includes trigger execution for centroid)
- Retrieve by code: <5ms (unique index)
- Spatial query (ST_DWithin): <50ms for 100 warehouses
- Area calculation: Automatic via GENERATED column (no query overhead)

## Handover Briefing

**For the next developer:**

**Context**: This is the **root of the geospatial hierarchy**. Every location in the system rolls up to a warehouse. PostGIS is critical for GPS-based photo localization.

**Key decisions made**:
1. **PostGIS POLYGON**: Full boundary definition (not just centroid) for accurate containment checks
2. **GENERATED column for area**: PostgreSQL 18 calculates area automatically from geometry
3. **Trigger for centroid**: Auto-update centroid when geometry changes (for fast distance queries)
4. **4 warehouse types**: Covers all cultivation facility types in agriculture
5. **Code validation**: Uppercase alphanumeric enforced for consistency in UI/reports
6. **SRID 4326**: Standard WGS84 (GPS coordinates) for global compatibility

**Known limitations**:
- Geometry cannot be NULL (must have defined boundaries)
- Area calculation uses geography cast (accurate but ~10× slower than geometry - acceptable tradeoff)
- Centroid trigger adds ~5ms to insert/update (acceptable for low-frequency operations)

**Next steps after this card**:
- DB002: StorageArea model (child of Warehouse, similar PostGIS structure)
- DB006: Location relationships (hierarchy validation triggers)
- R001: WarehouseRepository (spatial query methods)

**Questions to validate**:
- Are GIST indexes created on geometry columns? (Should be YES - critical for performance)
- Is PostGIS extension enabled? (`CREATE EXTENSION postgis;`)
- Does centroid trigger fire on INSERT and UPDATE? (Test with geometry change)

## Definition of Done Checklist

- [ ] Model code written in `app/models/warehouse.py`
- [ ] Enum type `warehouse_type_enum` created
- [ ] GENERATED column for area_m2 added via migration
- [ ] Trigger for centroid auto-calculation created
- [ ] GIST indexes on geometry columns verified
- [ ] Code validation working (uppercase, alphanumeric)
- [ ] Unit tests pass (≥80% coverage)
- [ ] Integration tests for geospatial queries pass
- [ ] Alembic migration tested (upgrade + downgrade)
- [ ] PostGIS extension enabled in database
- [ ] Relationships to StorageArea configured (once DB002 complete)
- [ ] PR reviewed and approved (2+ reviewers)
- [ ] No linting errors (`ruff check`)

## Time Tracking
- **Estimated**: 3 story points
- **Actual**: TBD
- **Started**: TBD
- **Completed**: TBD

---

## Scrum Master Delegation (2025-10-13 15:40)

**Assigned to**: Team Leader
**Priority**: HIGH (Critical path - foundation for location hierarchy)
**Epic**: epic-002 (Database Models)
**Sprint**: Sprint-01 (Database Models & Repositories)

**Context**:
This is the FIRST database model in Sprint 01 and the root of the 4-level geospatial hierarchy (warehouse → storage_area → storage_location → storage_bin). All spatial queries and photo localization depend on this foundation. The card is already fully expanded with 443 lines of comprehensive documentation including PostGIS patterns, validation logic, and geospatial query examples.

**Why This Task Next**:
1. BLOCKS DB002-DB006 (all other location hierarchy models)
2. BLOCKS R001 (WarehouseRepository)
3. BLOCKS DB007-DB008 (stock movements need location hierarchy)
4. Foundation for ALL geospatial features (600,000+ plants across multiple cultivation zones)

**Dependencies Satisfied**:
- F006: Database connection manager (COMPLETE)
- F007: Alembic setup (COMPLETE)
- PostGIS 3.3+ extension available

**Resources**:
- **Database ERD**: /home/lucasg/proyectos/DemeterDocs/database/database.mmd (warehouses table definition)
- **Engineering Plan**: /home/lucasg/proyectos/DemeterDocs/engineering_plan/database/README.md
- **PostGIS Documentation**: https://postgis.net/documentation/
- **GeoAlchemy2 Guide**: https://geoalchemy-2.readthedocs.io/

**Implementation Strategy**:
1. Create `app/models/warehouse.py` with Warehouse class
2. Use GeoAlchemy2 for PostGIS geometry columns
3. Add warehouse_type_enum (greenhouse, shadehouse, open_field, tunnel)
4. Implement code validation (@validates decorator)
5. Create Alembic migration with:
   - CREATE TYPE warehouse_type_enum
   - CREATE TABLE warehouses
   - GENERATED column for area_m2 (ST_Area calculation)
   - Trigger for centroid auto-update
   - GIST indexes for geometry columns
6. Write unit tests (code validation, enum, geometry assignment)
7. Write integration tests (area calculation, centroid trigger, spatial queries)
8. Verify coverage ≥80%

**Key Technical Details**:
- SRID 4326 (WGS84 for GPS coordinates)
- GENERATED column uses ST_Area(geojson_coordinates::geography) for accurate area_m2
- Trigger updates centroid on INSERT/UPDATE of geojson_coordinates
- GIST indexes REQUIRED for spatial query performance (<50ms for 100 warehouses)

**Expected Deliverables**:
- app/models/warehouse.py (SQLAlchemy model)
- alembic/versions/XXXX_create_warehouses.py (migration)
- tests/models/test_warehouse.py (unit tests)
- tests/integration/test_warehouse_geospatial.py (integration tests)
- All tests passing with ≥80% coverage
- Git commit following project conventions

**Command to Start**:
```bash
# Team Leader should use:
/start-task DB001
```

This will create a Mini-Plan and spawn Python Expert + Testing Expert in parallel.

---

**Card Created**: 2025-10-09
**Last Updated**: 2025-10-13
**Card Owner**: Team Leader (delegated 2025-10-13 15:40)

---

## Team Leader Mini-Plan (2025-10-13 15:40)

### Task Overview
- **Card**: DB001 - Warehouses Model (PostGIS Geospatial Root)
- **Epic**: epic-002-database-models.md
- **Priority**: HIGH - Critical Path (blocks DB002-DB006, R001)
- **Complexity**: 3 story points (Medium)
- **Sprint**: Sprint-01 (Database Models & Repositories)

### Architecture
**Layer**: Database / Models (Infrastructure Layer)
**Pattern**: SQLAlchemy 2.0 + GeoAlchemy2 for PostGIS geometry
**Dependencies**:
- F006: Database connection manager (COMPLETE)
- F007: Alembic setup (COMPLETE)
- PostGIS 3.3+ extension enabled
- GeoAlchemy2 0.14+ library

**Key Principle**: This is the ROOT of the 4-level geospatial hierarchy:
```
Warehouse (DB001) ← YOU ARE HERE
    ↓
StorageArea (DB002) ← BLOCKED
    ↓
StorageLocation (DB003) ← BLOCKED
    ↓
StorageBin (DB004) ← BLOCKED
```

### Files to Create/Modify

#### 1. Model File (~180 lines)
- **Path**: `/home/lucasg/proyectos/DemeterDocs/app/models/warehouse.py`
- **Content**:
  - SQLAlchemy model class `Warehouse(Base)`
  - PostGIS geometry columns (POLYGON, POINT)
  - Enum: warehouse_type_enum (greenhouse, shadehouse, open_field, tunnel)
  - Columns: warehouse_id (PK), code (UK), name, warehouse_type, geojson_coordinates, centroid, area_m2, active, timestamps
  - Code validation with @validates decorator
  - Relationship to StorageArea (one-to-many, will be used by DB002)

#### 2. Alembic Migration (~120 lines)
- **Path**: `/home/lucasg/proyectos/DemeterDocs/alembic/versions/XXXX_create_warehouses.py`
- **Content**:
  - CREATE TYPE warehouse_type_enum
  - CREATE TABLE warehouses with PostGIS columns
  - GENERATED column: area_m2 = ST_Area(geojson_coordinates::geography)
  - Trigger function: update_warehouse_centroid()
  - Trigger: trg_warehouse_centroid BEFORE INSERT OR UPDATE
  - GIST indexes: idx_warehouses_geom, idx_warehouses_centroid
  - Standard indexes: idx_warehouses_code, idx_warehouses_type, idx_warehouses_active
  - CHECK constraint: code uppercase alphanumeric validation

#### 3. Unit Tests (~250 lines)
- **Path**: `/home/lucasg/proyectos/DemeterDocs/tests/models/test_warehouse.py`
- **Test Cases**:
  - test_warehouse_code_validation (uppercase, alphanumeric, length)
  - test_warehouse_type_enum (valid values, invalid rejection)
  - test_geometry_assignment (shapely → GeoAlchemy2)
  - test_required_fields_validation
  - test_default_values (active=True, timestamps)
  - test_code_uniqueness

#### 4. Integration Tests (~200 lines)
- **Path**: `/home/lucasg/proyectos/DemeterDocs/tests/integration/test_warehouse_geospatial.py`
- **Test Cases**:
  - test_warehouse_area_auto_calculation (GENERATED column)
  - test_centroid_auto_calculation (trigger validation)
  - test_centroid_updates_on_geometry_change (trigger on UPDATE)
  - test_find_warehouses_within_radius (ST_DWithin spatial query)
  - test_find_nearest_warehouse (ST_Distance ordering)
  - test_point_in_polygon (ST_Contains for GPS localization)
  - test_gist_index_performance (verify index usage with EXPLAIN)

#### 5. Update Base Imports
- **Path**: `/home/lucasg/proyectos/DemeterDocs/app/db/base.py`
- **Action**: Add `from app.models.warehouse import Warehouse` (for Alembic autogenerate)

### Database Access

**Tables involved**:
- `warehouses` (PRIMARY - being created by this task)
  - warehouse_id: INT PRIMARY KEY AUTOINCREMENT
  - code: VARCHAR(50) UNIQUE NOT NULL
  - name: VARCHAR(200) NOT NULL
  - warehouse_type: warehouse_type_enum NOT NULL
  - geojson_coordinates: GEOMETRY(POLYGON, 4326) NOT NULL
  - centroid: GEOMETRY(POINT, 4326) (auto-generated by trigger)
  - area_m2: NUMERIC(10,2) GENERATED ALWAYS AS (ST_Area(geojson_coordinates::geography)) STORED
  - active: BOOLEAN DEFAULT TRUE NOT NULL
  - created_at: TIMESTAMPTZ DEFAULT now()
  - updated_at: TIMESTAMPTZ (on update)

**See**:
- Database ERD: `/home/lucasg/proyectos/DemeterDocs/database/database.mmd` (lines 8-19)
- Database engineering: `/home/lucasg/proyectos/DemeterDocs/engineering_plan/database/README.md`

### PostGIS Patterns to Implement

#### 1. POLYGON Geometry Column
```python
from geoalchemy2 import Geometry

geojson_coordinates = Column(
    Geometry('POLYGON', srid=4326),
    nullable=False,
    comment="Warehouse boundary polygon (WGS84)"
)
```

#### 2. POINT Geometry Column (Centroid)
```python
centroid = Column(
    Geometry('POINT', srid=4326),
    nullable=True,
    comment="Auto-calculated centroid for distance queries"
)
```

#### 3. GENERATED Column (PostgreSQL 12+)
```sql
-- In migration upgrade():
op.execute("""
    ALTER TABLE warehouses
    ADD COLUMN area_m2 NUMERIC(10,2)
    GENERATED ALWAYS AS (
        ST_Area(geojson_coordinates::geography)
    ) STORED;
""")
```

#### 4. Trigger for Centroid Auto-Update
```sql
-- In migration upgrade():
op.execute("""
    CREATE OR REPLACE FUNCTION update_warehouse_centroid()
    RETURNS TRIGGER AS $$
    BEGIN
        NEW.centroid = ST_Centroid(NEW.geojson_coordinates);
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;

    CREATE TRIGGER trg_warehouse_centroid
    BEFORE INSERT OR UPDATE OF geojson_coordinates ON warehouses
    FOR EACH ROW
    EXECUTE FUNCTION update_warehouse_centroid();
""")
```

#### 5. GIST Spatial Indexes
```sql
-- In migration upgrade():
op.execute("CREATE INDEX idx_warehouses_geom ON warehouses USING GIST(geojson_coordinates);")
op.execute("CREATE INDEX idx_warehouses_centroid ON warehouses USING GIST(centroid);")
```

### Implementation Strategy

#### Phase 1: Python Expert (Model + Migration)
**Estimated Time**: 2.5 hours

**Tasks**:
1. Create `app/models/warehouse.py`:
   - Import: SQLAlchemy, GeoAlchemy2, Base
   - Define Warehouse class with all columns
   - Add warehouse_type_enum using SQLAlchemy Enum
   - Implement @validates('code') decorator for validation
   - Add relationship to StorageArea (forward declaration, will be used by DB002)
   - Type hints for all methods

2. Create Alembic migration:
   - Use `alembic revision --autogenerate -m "create warehouses table"`
   - Manually add:
     - CREATE TYPE warehouse_type_enum (autogenerate may miss this)
     - GENERATED column for area_m2
     - Trigger function + trigger for centroid
     - GIST indexes (autogenerate creates B-tree by default)
     - CHECK constraint for code validation
   - Test upgrade() and downgrade() thoroughly

3. Update `app/db/base.py`:
   - Import Warehouse model for Alembic autogenerate

**Dependencies**: None (foundation task)

**Output**:
- Model file ready for testing
- Migration file validated with `alembic check`

#### Phase 2: Testing Expert (Unit + Integration Tests) - PARALLEL
**Estimated Time**: 2.5 hours

**Tasks**:
1. Create `tests/models/test_warehouse.py`:
   - Test code validation (uppercase, alphanumeric, length 2-20)
   - Test enum validation (valid types, invalid rejection)
   - Test geometry assignment from shapely
   - Test required fields
   - Test default values
   - Test code uniqueness constraint

2. Create `tests/integration/test_warehouse_geospatial.py`:
   - Setup: Real testing database with PostGIS
   - Test area_m2 GENERATED column (create warehouse, verify area calculated)
   - Test centroid trigger (INSERT + UPDATE scenarios)
   - Test spatial queries:
     - ST_DWithin (find warehouses within radius)
     - ST_Distance (find nearest warehouse)
     - ST_Contains (point-in-polygon for GPS localization)
   - Test GIST index performance (EXPLAIN ANALYZE validation)
   - Teardown: Clean test data

3. Achieve ≥80% coverage:
   - Focus on validation logic
   - PostGIS trigger behavior
   - Spatial query correctness

**Dependencies**:
- Can start immediately (test-driven development)
- Coordinate with Python Expert for method signatures

**Output**:
- All tests passing
- Coverage ≥80%
- No warnings or deprecations

#### Phase 3: Team Leader Review (Sequential)
**Estimated Time**: 30 minutes

**Review Checklist**:
1. **Model Code**:
   - [ ] GeoAlchemy2 Geometry columns defined correctly
   - [ ] SRID 4326 (WGS84) used consistently
   - [ ] Enum values match database.mmd specification
   - [ ] Code validation logic correct (uppercase, alphanumeric, 2-20 chars)
   - [ ] Type hints on all methods
   - [ ] No business logic in model (validation only)

2. **Migration Code**:
   - [ ] CREATE TYPE warehouse_type_enum present
   - [ ] GENERATED column syntax correct (PostgreSQL 12+)
   - [ ] Trigger function + trigger created
   - [ ] GIST indexes on geometry columns (NOT B-tree)
   - [ ] Standard indexes on code, type, active
   - [ ] downgrade() properly reverses all changes

3. **Test Code**:
   - [ ] Unit tests cover validation logic
   - [ ] Integration tests use real PostGIS database
   - [ ] Spatial queries tested (ST_DWithin, ST_Contains, ST_Distance)
   - [ ] GIST index performance verified
   - [ ] Coverage ≥80%

### Acceptance Criteria Checklist

From task card (lines 40-172):

- [ ] **AC1**: Model created in `app/models/warehouse.py` with all fields
- [ ] **AC2**: Warehouse type enum created (greenhouse, shadehouse, open_field, tunnel)
- [ ] **AC3**: GENERATED column for area_m2 (ST_Area calculation)
- [ ] **AC4**: Trigger for auto-calculating centroid (INSERT + UPDATE)
- [ ] **AC5**: Indexes created (GIST for geometries, standard for code/type/active)
- [ ] **AC6**: Code validation (uppercase alphanumeric, 2-20 chars)
- [ ] **AC7**: Alembic migration tested (upgrade + downgrade)

### Performance Expectations

From task card (lines 382-386):

- Insert: <15ms (includes trigger execution for centroid)
- Retrieve by code: <5ms (unique index)
- Spatial query (ST_DWithin): <50ms for 100 warehouses
- Area calculation: Automatic via GENERATED column (no query overhead)

### Quality Gates

Before moving to `05_done/`, ALL gates must pass:

#### Gate 1: Code Quality
```bash
# Ruff linting
ruff check app/models/warehouse.py

# Mypy type checking
mypy app/models/warehouse.py --strict

# No TODO/FIXME in production code
grep -r "TODO\|FIXME" app/models/warehouse.py
```

#### Gate 2: Tests Pass
```bash
# Unit tests
pytest tests/models/test_warehouse.py -v

# Integration tests
pytest tests/integration/test_warehouse_geospatial.py -v

# All passing
```

#### Gate 3: Coverage ≥80%
```bash
pytest tests/models/test_warehouse.py tests/integration/test_warehouse_geospatial.py \
    --cov=app.models.warehouse \
    --cov-report=term-missing

# Coverage must be ≥80%
```

#### Gate 4: Migration Validation
```bash
# Check migration syntax
alembic check

# Upgrade to head (test database)
alembic upgrade head

# Verify table created
psql -c "\d warehouses"

# Verify GIST indexes exist
psql -c "\di idx_warehouses_geom"
psql -c "\di idx_warehouses_centroid"

# Downgrade (test rollback)
alembic downgrade -1

# Verify table dropped
psql -c "\d warehouses"
```

#### Gate 5: PostGIS Features Working
```bash
# Test GENERATED column
psql -c "SELECT area_m2 FROM warehouses WHERE code='TEST01';"  # Should return value

# Test centroid trigger
psql -c "SELECT ST_AsText(centroid) FROM warehouses WHERE code='TEST01';"  # Should return POINT

# Test GIST index usage
psql -c "EXPLAIN SELECT * FROM warehouses WHERE ST_DWithin(centroid, ST_MakePoint(-70.6475, -33.4495)::geography, 1000);"
# Should show "Index Scan using idx_warehouses_centroid"
```

### Known Risks & Mitigations

#### Risk 1: PostGIS Extension Not Enabled
**Symptom**: Migration fails with "type geometry does not exist"
**Mitigation**: Alembic migration 6f1b94ebef45 (F007) already enabled PostGIS
**Verification**: `psql -c "SELECT PostGIS_Version();"`

#### Risk 2: GENERATED Column Syntax Error
**Symptom**: Migration fails on PostgreSQL <12
**Mitigation**: Requires PostgreSQL 12+ (specified in requirements)
**Fallback**: Use computed property in model + trigger for persistence

#### Risk 3: Trigger Not Firing
**Symptom**: Centroid NULL after INSERT
**Mitigation**: BEFORE INSERT trigger syntax validated
**Verification**: Integration test test_centroid_auto_calculation

#### Risk 4: GIST Index Not Used
**Symptom**: Spatial queries slow (sequential scan)
**Mitigation**: EXPLAIN ANALYZE in integration test
**Fix**: Rebuild index if needed: `REINDEX INDEX idx_warehouses_geom;`

### Next Steps After Completion

1. **Move task to `05_done/`**: After all quality gates pass
2. **Unblock dependent tasks**:
   - DB002: StorageArea model (inherits PostGIS patterns)
   - DB003: StorageLocation model (inherits PostGIS patterns)
   - DB004: StorageBin model (no geometry, references locations)
   - R001: WarehouseRepository (spatial query methods)
3. **Update documentation**:
   - Add warehouse model to `app/db/base.py` imports
   - Document PostGIS patterns for future DB models
4. **Git commit**:
   - Format: `feat(models): implement Warehouse model with PostGIS support`
   - Include: Model + migration + tests

### Resources

- **Task Card**: `/home/lucasg/proyectos/DemeterDocs/backlog/03_kanban/01_ready/DB001-warehouses-model.md` (510 lines)
- **Database ERD**: `/home/lucasg/proyectos/DemeterDocs/database/database.mmd` (lines 8-19)
- **Database Engineering**: `/home/lucasg/proyectos/DemeterDocs/engineering_plan/database/README.md`
- **Architecture**: `/home/lucasg/proyectos/DemeterDocs/engineering_plan/03_architecture_overview.md`
- **Base Repository**: `/home/lucasg/proyectos/DemeterDocs/app/repositories/base.py`
- **PostGIS Docs**: https://postgis.net/docs/reference.html
- **GeoAlchemy2 Docs**: https://geoalchemy-2.readthedocs.io/en/latest/

---

**Mini-Plan Created**: 2025-10-13 15:40
**Status**: READY FOR EXECUTION
**Next Action**: Move to `02_in-progress/` and spawn Python Expert + Testing Expert in parallel


---

## Team Leader Status Update (2025-10-13 15:45)

**Status**: MOVED TO IN-PROGRESS
**Action**: Spawning Python Expert + Testing Expert in parallel

### Delegation to Python Expert

**Task**: Implement Warehouse model + Alembic migration
**File**: `/home/lucasg/proyectos/DemeterDocs/backlog/03_kanban/02_in-progress/DB001-warehouses-model.md`
**Priority**: HIGH - Foundation task (blocks DB002-DB006, R001)

**Key Requirements**:
1. Create `app/models/warehouse.py`:
   - SQLAlchemy model with GeoAlchemy2 Geometry columns
   - warehouse_type_enum (greenhouse, shadehouse, open_field, tunnel)
   - Code validation (@validates decorator: uppercase, alphanumeric, 2-20 chars)
   - Type hints on all methods
   - Relationship to StorageArea (forward declaration)

2. Create Alembic migration:
   - CREATE TYPE warehouse_type_enum
   - CREATE TABLE warehouses with PostGIS POLYGON and POINT
   - GENERATED column: area_m2 = ST_Area(geojson_coordinates::geography)
   - Trigger function + trigger for centroid auto-update
   - GIST indexes on geometry columns (NOT B-tree)
   - Standard indexes on code, type, active
   - CHECK constraint for code validation

3. Update `app/db/base.py`:
   - Import Warehouse model for Alembic autogenerate

**Critical Patterns**:
- SRID 4326 (WGS84) for all geometry columns
- GENERATED column requires PostgreSQL 12+
- GIST indexes for spatial queries (<50ms target)
- Trigger BEFORE INSERT OR UPDATE OF geojson_coordinates

**Resources**:
- Base Repository: `/home/lucasg/proyectos/DemeterDocs/app/repositories/base.py`
- PostGIS docs: https://postgis.net/docs/reference.html
- GeoAlchemy2 docs: https://geoalchemy-2.readthedocs.io/

**Start now** (can work in parallel with Testing Expert)

---

### Delegation to Testing Expert

**Task**: Write unit + integration tests for Warehouse model
**File**: `/home/lucasg/proyectos/DemeterDocs/backlog/03_kanban/02_in-progress/DB001-warehouses-model.md`
**Priority**: HIGH - Must achieve ≥80% coverage

**Key Requirements**:
1. Create `tests/models/test_warehouse.py` (unit tests):
   - test_warehouse_code_validation (uppercase, alphanumeric, length 2-20)
   - test_warehouse_type_enum (valid values, invalid rejection)
   - test_geometry_assignment (shapely → GeoAlchemy2)
   - test_required_fields_validation
   - test_default_values (active=True, timestamps)
   - test_code_uniqueness

2. Create `tests/integration/test_warehouse_geospatial.py` (integration tests):
   - test_warehouse_area_auto_calculation (GENERATED column)
   - test_centroid_auto_calculation (trigger validation)
   - test_centroid_updates_on_geometry_change (trigger on UPDATE)
   - test_find_warehouses_within_radius (ST_DWithin spatial query)
   - test_find_nearest_warehouse (ST_Distance ordering)
   - test_point_in_polygon (ST_Contains for GPS localization)
   - test_gist_index_performance (EXPLAIN ANALYZE validation)

3. Coverage target: ≥80%

**Critical Patterns**:
- Use real testing database with PostGIS for integration tests
- Mock nothing in integration tests (test full stack)
- Verify GIST index usage with EXPLAIN ANALYZE
- Test both INSERT and UPDATE scenarios for trigger

**Resources**:
- Existing test structure: `/home/lucasg/proyectos/DemeterDocs/tests/`
- pytest fixtures in conftest.py
- Database connection: use testing database

**Start now** (can work in parallel with Python Expert)

**Coordinate with Python Expert** for method signatures and model structure.

---

**Next Team Leader Action**: Monitor progress, review code when both experts complete, run quality gates, approve for completion


---

## Python Expert Progress (2025-10-13 15:40)

### Status: IMPLEMENTATION COMPLETE - Ready for Testing

### Completed Tasks

#### 1. Warehouse Model Created ✅
**File**: `/home/lucasg/proyectos/DemeterDocs/app/models/warehouse.py` (329 lines)

**Features Implemented**:
- SQLAlchemy 2.0 declarative model inheriting from Base
- GeoAlchemy2 Geometry columns (POLYGON + POINT with SRID 4326)
- WarehouseTypeEnum (greenhouse, shadehouse, open_field, tunnel)
- Code validation with @validates decorator:
  - Uppercase enforcement
  - Alphanumeric with optional - and _
  - Length 2-20 characters
  - Detailed error messages
- Type hints on all methods and attributes
- Comprehensive docstrings (module, class, methods)
- Relationship to StorageArea (forward declaration for DB002)

**Key Design Decisions**:
- Used Python enum.Enum for WarehouseTypeEnum (type safety)
- area_m2 column defined in model but marked as GENERATED (added in migration)
- CheckConstraint for code length validation (database-level enforcement)
- Server defaults for active=True and created_at=now()
- __repr__ method for debugging

#### 2. Alembic Migration Created ✅
**File**: `/home/lucasg/proyectos/DemeterDocs/alembic/versions/2f68e3f132f5_create_warehouses_table.py` (160 lines)

**Migration Steps (upgrade)**:
1. CREATE TYPE warehouse_type_enum ✅
2. CREATE TABLE warehouses with all columns ✅
3. ADD COLUMN area_m2 as GENERATED (ST_Area calculation) ✅
4. CREATE FUNCTION update_warehouse_centroid() ✅
5. CREATE TRIGGER trg_warehouse_centroid (BEFORE INSERT OR UPDATE) ✅
6. CREATE GIST indexes on geojson_coordinates and centroid ✅
7. CREATE B-tree indexes on code, type, active ✅

**Migration Features**:
- Comprehensive comments explaining each step
- Proper downgrade() that reverses all changes in correct order
- GIST indexes for spatial queries (NOT B-tree)
- GENERATED column uses geography cast for accurate area_m2
- Trigger ensures centroid always synchronized with polygon

#### 3. Base Configuration Updated ✅

**Files Updated**:
- `/home/lucasg/proyectos/DemeterDocs/app/db/base.py` - Import Warehouse for Alembic autogenerate
- `/home/lucasg/proyectos/DemeterDocs/app/models/__init__.py` - Export Warehouse and WarehouseTypeEnum

#### 4. Dependencies Updated ✅
- Added `geoalchemy2==0.14.7` to requirements.txt
- Installed GeoAlchemy2 in virtual environment

### Architecture Compliance

✅ **Clean Architecture**:
- Model has NO business logic (validation only)
- Uses @validates for data integrity
- Type hints on all methods

✅ **SQLAlchemy 2.0**:
- Declarative base pattern
- Async-compatible structure
- Proper column definitions with comments

✅ **PostGIS Best Practices**:
- SRID 4326 (WGS84) for GPS compatibility
- GIST indexes for spatial queries
- GENERATED column for area calculation
- Database trigger for centroid (not Python property)

✅ **Code Quality**:
- Type hints throughout
- Comprehensive docstrings
- Forward declaration for StorageArea relationship
- Proper enum usage (Python enum + SQLAlchemy Enum)

### Technical Highlights

1. **GENERATED Column**:
   - Uses `ST_Area(geojson_coordinates::geography)` for accurate square meter calculation
   - Geography cast ensures metric units (not degrees)
   - Automatically updated by PostgreSQL (no Python code needed)

2. **Centroid Trigger**:
   - BEFORE INSERT OR UPDATE OF geojson_coordinates
   - Uses ST_Centroid for geometric center
   - Enables fast distance queries via GIST index

3. **Code Validation**:
   - Regex: `^[A-Z0-9_-]+$`
   - Length: 2-20 characters
   - Uppercase enforcement
   - Detailed error messages

4. **Spatial Indexes**:
   - GIST on geojson_coordinates (boundary queries)
   - GIST on centroid (distance queries)
   - Target: <50ms for ST_DWithin on 100+ warehouses

### Files Created/Modified

1. **Created**:
   - `app/models/warehouse.py` (329 lines)
   - `alembic/versions/2f68e3f132f5_create_warehouses_table.py` (160 lines)

2. **Modified**:
   - `app/db/base.py` (added Warehouse import)
   - `app/models/__init__.py` (export Warehouse, WarehouseTypeEnum)
   - `requirements.txt` (added geoalchemy2==0.14.7)

### Next Steps

**For Testing Expert**:
1. Run migration: `alembic upgrade head`
2. Verify table created with correct schema
3. Test code validation (uppercase, alphanumeric, length)
4. Test enum values (valid + invalid)
5. Test geometry assignment (shapely → GeoAlchemy2)
6. Test GENERATED column (area_m2 auto-calculation)
7. Test trigger (centroid auto-update on INSERT/UPDATE)
8. Test spatial queries (ST_DWithin, ST_Distance, ST_Contains)
9. Test GIST index usage (EXPLAIN ANALYZE)

**Quality Gates**:
- [ ] Migration upgrade successful
- [ ] Migration downgrade successful
- [ ] Code validation tests pass
- [ ] Enum validation tests pass
- [ ] Geometry tests pass
- [ ] GENERATED column tests pass
- [ ] Trigger tests pass
- [ ] Spatial query tests pass
- [ ] GIST index performance tests pass
- [ ] Coverage ≥80%

**Estimated Testing Time**: 2-3 hours

---

**Implementation Time**: 1.5 hours
**Status**: READY FOR REVIEW AND TESTING
**Next Action**: Testing Expert to begin test suite creation
