# [DB006] Location Hierarchy Validation Triggers

## Metadata

- **Epic**: epic-002-database-models.md
- **Sprint**: Sprint-01 (Week 3-4)
- **Status**: `backlog`
- **Priority**: `medium` (data integrity enforcement)
- **Complexity**: M (2 story points)
- **Area**: `database/migrations`
- **Assignee**: TBD
- **Dependencies**:
    - Blocks: [R001-R004]
    - Blocked by: [DB001, DB002, DB003, DB004]

## Related Documentation

- **Engineering Plan**: ../../engineering_plan/database/README.md
- **Database ERD**: ../../database/database.mmd

## Description

Create database triggers and constraints to enforce geospatial hierarchy integrity across all 4
levels (warehouse → storage_area → storage_location → storage_bin).

**What**: PostgreSQL triggers for hierarchy validation:

- Verify storage_area geometry is within warehouse
- Verify storage_location geometry is within storage_area
- Prevent circular references
- Enforce active status propagation (inactive warehouse → all children inactive)

**Why**:

- **Data integrity**: Prevent invalid hierarchy (e.g., location outside its parent area)
- **Geospatial consistency**: All geometries must nest correctly
- **Status cascade**: Inactive parent should cascade to children
- **Prevent orphans**: Cannot delete parent if active children exist

**Context**: These are NOT in individual model files - they're cross-table validation triggers
created in a dedicated migration.

## Acceptance Criteria

- [ ] **AC1**: Containment validation triggers for storage_areas, storage_locations (ST_Within
  checks)
- [ ] **AC2**: Active status cascade trigger: if warehouse/area/location set to inactive, cascade to
  children
- [ ] **AC3**: Prevent delete trigger: cannot delete warehouse if active storage_areas exist (must
  deactivate first)
- [ ] **AC4**: Circular reference prevention for photo_session_id in storage_locations
- [ ] **AC5**: Hierarchy depth validation (max 4 levels: warehouse → area → location → bin)
- [ ] **AC6**: All triggers documented in migration with clear comments
- [ ] **AC7**: Alembic migration tested with violation scenarios

## Technical Implementation Notes

### Architecture

- Layer: Database / Triggers & Constraints
- Dependencies: DB001-DB004 (all location models must exist first)
- Design pattern: Database-level integrity enforcement

### Trigger Implementations

**1. Storage Area Containment**

```sql
CREATE OR REPLACE FUNCTION validate_storage_area_within_warehouse()
RETURNS TRIGGER AS $$
DECLARE
    wh_geom GEOMETRY;
BEGIN
    SELECT geojson_coordinates INTO wh_geom
    FROM warehouses
    WHERE warehouse_id = NEW.warehouse_id;

    IF NOT ST_Within(NEW.geojson_coordinates, wh_geom) THEN
        RAISE EXCEPTION 'Storage area % must be within warehouse boundaries', NEW.code;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_validate_storage_area_containment
BEFORE INSERT OR UPDATE OF geojson_coordinates, warehouse_id
ON storage_areas
FOR EACH ROW
EXECUTE FUNCTION validate_storage_area_within_warehouse();
```

**2. Storage Location Containment**

```sql
CREATE OR REPLACE FUNCTION validate_storage_location_within_area()
RETURNS TRIGGER AS $$
DECLARE
    area_geom GEOMETRY;
BEGIN
    SELECT geojson_coordinates INTO area_geom
    FROM storage_areas
    WHERE storage_area_id = NEW.storage_area_id;

    IF NOT ST_Within(NEW.geojson_coordinates, area_geom) THEN
        RAISE EXCEPTION 'Storage location % must be within storage area boundaries', NEW.code;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_validate_storage_location_containment
BEFORE INSERT OR UPDATE OF geojson_coordinates, storage_area_id
ON storage_locations
FOR EACH ROW
EXECUTE FUNCTION validate_storage_location_within_area();
```

**3. Active Status Cascade**

```sql
CREATE OR REPLACE FUNCTION cascade_inactive_status()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.active = false AND OLD.active = true THEN
        -- Cascade to children (example for warehouse → storage_areas)
        UPDATE storage_areas
        SET active = false
        WHERE warehouse_id = NEW.warehouse_id;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_cascade_warehouse_inactive
AFTER UPDATE OF active
ON warehouses
FOR EACH ROW
WHEN (NEW.active = false AND OLD.active = true)
EXECUTE FUNCTION cascade_inactive_status();
```

**4. Prevent Delete with Active Children**

```sql
CREATE OR REPLACE FUNCTION prevent_delete_with_active_children()
RETURNS TRIGGER AS $$
DECLARE
    active_count INT;
BEGIN
    SELECT COUNT(*) INTO active_count
    FROM storage_areas
    WHERE warehouse_id = OLD.warehouse_id AND active = true;

    IF active_count > 0 THEN
        RAISE EXCEPTION 'Cannot delete warehouse % - has % active storage areas. Deactivate them first.',
            OLD.code, active_count;
    END IF;

    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_prevent_warehouse_delete
BEFORE DELETE
ON warehouses
FOR EACH ROW
EXECUTE FUNCTION prevent_delete_with_active_children();
```

### Testing Requirements

**Integration Tests** (`tests/integration/test_location_hierarchy_triggers.py`):

```python
@pytest.mark.asyncio
async def test_storage_area_must_be_within_warehouse(db_session):
    """Storage area outside warehouse should fail"""
    warehouse = Warehouse(...)  # Create warehouse with specific bounds
    db_session.add(warehouse)
    await db_session.commit()

    # Create area OUTSIDE warehouse bounds
    outside_area = StorageArea(
        warehouse_id=warehouse.warehouse_id,
        code="TEST-OUTSIDE",
        geojson_coordinates=<polygon outside warehouse>
    )
    db_session.add(outside_area)

    with pytest.raises(IntegrityError, match="must be within warehouse boundaries"):
        await db_session.commit()

@pytest.mark.asyncio
async def test_inactive_warehouse_cascades_to_areas(db_session):
    """Setting warehouse to inactive should cascade to storage areas"""
    warehouse = Warehouse(..., active=True)
    area1 = StorageArea(..., warehouse_id=warehouse.id, active=True)
    area2 = StorageArea(..., warehouse_id=warehouse.id, active=True)

    db_session.add_all([warehouse, area1, area2])
    await db_session.commit()

    # Deactivate warehouse
    warehouse.active = False
    await db_session.commit()

    # Verify areas are now inactive
    await db_session.refresh(area1)
    await db_session.refresh(area2)

    assert area1.active == False
    assert area2.active == False

@pytest.mark.asyncio
async def test_cannot_delete_warehouse_with_active_areas(db_session):
    """Cannot delete warehouse if it has active storage areas"""
    warehouse = Warehouse(..., active=True)
    area = StorageArea(..., warehouse_id=warehouse.id, active=True)

    db_session.add_all([warehouse, area])
    await db_session.commit()

    # Attempt to delete warehouse
    await db_session.delete(warehouse)

    with pytest.raises(IntegrityError, match="has .* active storage areas"):
        await db_session.commit()

    # Deactivate area first, then delete should succeed
    await db_session.rollback()
    area.active = False
    await db_session.commit()

    await db_session.delete(warehouse)
    await db_session.commit()  # Should succeed now
```

**Coverage Target**: ≥80%

### Performance Expectations

- Containment validation: +5-10ms per insert/update (acceptable for data integrity)
- Status cascade: +10-20ms per warehouse deactivation (batch update to children)
- Delete validation: +5ms per delete (single COUNT query)

## Handover Briefing

**Context**: Cross-table validation triggers. These enforce geospatial hierarchy integrity that
cannot be done at the model level.

**Key decisions**:

1. **Separate migration**: Not in model files, dedicated migration for all hierarchy triggers
2. **ST_Within validation**: Enforces geometric containment (child within parent)
3. **Status cascade**: Inactive parent → inactive children (automatic)
4. **Safe delete**: Must deactivate children before deleting parent
5. **PostgreSQL 18 triggers**: Use modern trigger syntax

**Next steps**: R001-R004 (Repository classes can rely on these triggers for data integrity)

## Definition of Done Checklist

- [ ] All containment validation triggers created
- [ ] Active status cascade triggers created
- [ ] Delete prevention triggers created
- [ ] Circular reference prevention documented
- [ ] Integration tests for all triggers pass
- [ ] Migration tested with violation scenarios
- [ ] Performance impact measured (<20ms overhead)
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
