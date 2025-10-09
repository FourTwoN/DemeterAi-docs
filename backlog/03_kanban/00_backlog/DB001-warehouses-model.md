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
- **Estimated**: 2 story points
- **Actual**: TBD
- **Started**: TBD
- **Completed**: TBD

---

**Card Created**: 2025-10-09
**Last Updated**: 2025-10-09
**Card Owner**: TBD
