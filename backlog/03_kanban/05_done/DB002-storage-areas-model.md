# [DB002] StorageAreas Model - PostGIS Level 2 Hierarchy

## Metadata
- **Epic**: epic-002-database-models.md
- **Sprint**: Sprint-01 (Week 3-4)
- **Status**: `backlog`
- **Priority**: `high` (location hierarchy)
- **Complexity**: M (2 story points)
- **Area**: `database/models`
- **Assignee**: TBD
- **Dependencies**:
  - Blocks: [DB003, DB006, R002]
  - Blocked by: [DB001-warehouses-model]

## Related Documentation
- **Engineering Plan**: ../../engineering_plan/database/README.md
- **Database ERD**: ../../database/database.mmd
- **Architecture**: ../../engineering_plan/03_architecture_overview.md

## Description

Create the `storage_areas` SQLAlchemy model for level 2 of the 4-tier location hierarchy. Storage areas subdivide warehouses into logical zones (North, South, East, West, Center).

**What**: SQLAlchemy model for `storage_areas` table:
- Child of warehouse (many-to-one relationship)
- PostGIS geometry for area boundaries
- Position classification (N/S/E/W/C)
- Auto-calculated area from geometry

**Why**:
- **Logical subdivision**: Large warehouses need zones (e.g., "North Wing", "Propagation Area")
- **GPS localization**: Photo GPS → Storage Area → drill down to location
- **Organization**: Group storage locations by physical zones
- **Reporting**: Aggregate inventory by warehouse area

**Context**: Level 2 of hierarchy (Warehouse → **StorageArea** → StorageLocation → StorageBin). Essential for organizing 600k+ plants across large facilities.

## Acceptance Criteria

- [ ] **AC1**: Model created in `app/models/storage_area.py` with PostGIS geometry, position enum, relationships to warehouse and storage_locations
- [ ] **AC2**: Position enum created (`CREATE TYPE position_enum AS ENUM ('N', 'S', 'E', 'W', 'C')`)
- [ ] **AC3**: GENERATED column for area_m2 and trigger for centroid auto-calculation
- [ ] **AC4**: Spatial constraint trigger: area geometry must be within warehouse geometry (`ST_Within` check)
- [ ] **AC5**: GIST indexes on geojson_coordinates and centroid, B-tree indexes on warehouse_id, code, position, active
- [ ] **AC6**: Code validation (format: `WAREHOUSE_CODE-AREA_CODE`, uppercase)
- [ ] **AC7**: Alembic migration created and tested (upgrade + downgrade)

## Technical Implementation Notes

### Architecture
- Layer: Database / Models
- Dependencies: DB001 (Warehouse), PostGIS 3.3+, SQLAlchemy 2.0.43
- Design pattern: Geospatial hierarchy with containment validation

### Key Implementation Points

**Model signature:**
```python
class StorageArea(Base):
    storage_area_id = Column(Integer, PK)
    warehouse_id = Column(Integer, FK → warehouses, CASCADE, index=True)
    code = Column(String(50), UK, index=True)
    name = Column(String(200))
    position = Column(Enum('N','S','E','W','C'), nullable=True)
    geojson_coordinates = Column(Geometry('POLYGON', srid=4326))
    centroid = Column(Geometry('POINT', srid=4326), nullable=True)
    area_m2 = Column(Numeric(10,2), GENERATED)
    active = Column(Boolean, default=True, index=True)
    # relationships: warehouse, storage_locations
```

**Containment validation trigger:**
```sql
CREATE FUNCTION check_storage_area_within_warehouse() RETURNS TRIGGER AS $$
  -- Verify ST_Within(NEW.geojson_coordinates, warehouse.geojson_coordinates)
  -- RAISE EXCEPTION if not within bounds
$$ LANGUAGE plpgsql;
```

**Spatial queries:**
```python
# Find area by GPS point
def get_storage_area_by_gps(lat, lon):
    point = func.ST_SetSRID(func.ST_MakePoint(lon, lat), 4326)
    return session.query(StorageArea).filter(
        ST_Contains(StorageArea.geojson_coordinates, point)
    ).first()
```

### Testing Requirements

**Unit Tests** (`tests/models/test_storage_area.py`):
- Position enum validation (N/S/E/W/C or NULL)
- Code format validation (WAREHOUSE-AREA, uppercase)
- Relationship configuration

**Integration Tests** (`tests/integration/test_storage_area_spatial.py`):
- Containment constraint (area inside warehouse succeeds, outside fails)
- GPS → StorageArea lookup (ST_Contains query)
- Centroid and area_m2 auto-calculation
- Cascade delete from warehouse

**Coverage Target**: ≥80%

### Performance Expectations
- Insert: <20ms (includes centroid trigger + containment check)
- Retrieve by code: <5ms
- GPS → Area lookup (ST_Contains): <30ms with GIST index

## Handover Briefing

**Context**: Level 2 of geospatial hierarchy. Subdivides warehouses into zones. Critical for GPS → Location mapping.

**Key decisions**:
1. Containment validation trigger (area MUST be within warehouse)
2. Position enum optional (not all warehouses use cardinal directions)
3. Code format: `WAREHOUSE-AREA` (e.g., "INV01-NORTH")
4. Cascade delete from warehouse (intentional)

**Next steps**: DB003 (StorageLocation), DB006 (hierarchy validation), R002 (StorageAreaRepository)

## Definition of Done Checklist

- [ ] Model code written
- [ ] Position enum created
- [ ] GENERATED area_m2 + centroid trigger
- [ ] Containment validation trigger tested
- [ ] GIST + B-tree indexes verified
- [ ] Unit tests ≥80% coverage
- [ ] Integration tests for spatial constraints pass
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
