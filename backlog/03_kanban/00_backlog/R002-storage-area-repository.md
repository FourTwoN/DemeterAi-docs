# R002: Storage Area Repository

## Metadata
- **Epic**: [epic-003-repositories.md](../../02_epics/epic-003-repositories.md)
- **Sprint**: Sprint-01
- **Status**: `backlog`
- **Priority**: `high`
- **Complexity**: S (2 story points)
- **Area**: `repositories`
- **Assignee**: TBD
- **Dependencies**:
  - Blocks: [R003, S002]
  - Blocked by: [F006, F007, DB002, R001]

## Related Documentation
- **Engineering Plan**: [../../engineering_plan/backend/repository_layer.md](../../engineering_plan/backend/repository_layer.md)
- **Database ERD**: [../../database/database.mmd](../../database/database.mmd#L20-L32)
- **Architecture**: [../../engineering_plan/03_architecture_overview.md](../../engineering_plan/03_architecture_overview.md)

## Description

**What**: Implement repository class for `storage_areas` table (Level 2 of hierarchy) with CRUD operations + geospatial queries.

**Why**: Storage areas partition warehouses into manageable zones (N/S/E/W/C positions). Repository provides database access with PostGIS support for GPS-based area lookup and hierarchy navigation.

**Context**: Level 2 of 4-level hierarchy. Must support ST_Contains for GPS queries and eager loading of parent (warehouse) and children (storage_locations) to prevent N+1 queries.

## Acceptance Criteria

- [ ] **AC1**: `StorageAreaRepository` class inherits from `AsyncRepository[StorageArea]`
- [ ] **AC2**: Implements `get_by_code(code: str)` method with unique constraint validation
- [ ] **AC3**: Implements `get_by_gps_point(longitude: float, latitude: float)` using PostGIS ST_Contains
- [ ] **AC4**: Implements `get_by_warehouse_id(warehouse_id: int)` with optional eager loading
- [ ] **AC5**: Implements `get_by_position(warehouse_id: int, position: str)` for zone filtering
- [ ] **AC6**: Includes eager loading for warehouse (joinedload) and storage_locations (selectinload)
- [ ] **AC7**: Query performance <50ms for GPS lookup, <20ms for warehouse_id filtering

## Technical Implementation Notes

### Architecture
- **Layer**: Infrastructure (Repository)
- **Dependencies**: F006 (Database connection), DB002 (StorageArea model), R001 (WarehouseRepository)
- **Design Pattern**: Repository pattern, inherits AsyncRepository

### Code Hints
```python
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from geoalchemy2.functions import ST_Contains, ST_Point

from app.models.storage_area import StorageArea
from app.repositories.base_repository import AsyncRepository

class StorageAreaRepository(AsyncRepository[StorageArea]):
    """Repository for storage area CRUD + geospatial queries"""

    def __init__(self, session: AsyncSession):
        super().__init__(StorageArea, session)

    async def get_by_code(self, code: str) -> Optional[StorageArea]:
        """Get storage area by unique code"""
        stmt = select(StorageArea).where(StorageArea.code == code)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_gps_point(
        self,
        longitude: float,
        latitude: float
    ) -> Optional[StorageArea]:
        """Find storage area containing GPS point using PostGIS"""
        stmt = (
            select(StorageArea)
            .where(
                ST_Contains(
                    StorageArea.geojson_coordinates,
                    ST_Point(longitude, latitude)
                )
            )
            .where(StorageArea.active == True)
            .options(joinedload(StorageArea.warehouse))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_warehouse_id(
        self,
        warehouse_id: int,
        with_locations: bool = False
    ) -> List[StorageArea]:
        """Get all storage areas for a warehouse"""
        stmt = (
            select(StorageArea)
            .where(StorageArea.warehouse_id == warehouse_id)
            .where(StorageArea.active == True)
            .options(joinedload(StorageArea.warehouse))
        )

        if with_locations:
            stmt = stmt.options(selectinload(StorageArea.storage_locations))

        result = await self.session.execute(stmt)
        return list(result.scalars().unique().all())

    async def get_by_position(
        self,
        warehouse_id: int,
        position: str
    ) -> List[StorageArea]:
        """Get storage areas by position (N/S/E/W/C)"""
        stmt = (
            select(StorageArea)
            .where(StorageArea.warehouse_id == warehouse_id)
            .where(StorageArea.position == position)
            .where(StorageArea.active == True)
            .options(joinedload(StorageArea.warehouse))
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().unique().all())
```

### Testing Requirements

**Unit Tests**:
```python
@pytest.mark.asyncio
async def test_storage_area_repo_get_by_code(db_session, sample_storage_area):
    repo = StorageAreaRepository(db_session)
    area = await repo.get_by_code("SA001")
    assert area is not None
    assert area.code == "SA001"

@pytest.mark.asyncio
async def test_storage_area_repo_gps_lookup(db_session, sample_storage_area):
    """Test GPS → storage area lookup using PostGIS"""
    repo = StorageAreaRepository(db_session)
    # GPS point inside storage area polygon
    area = await repo.get_by_gps_point(-70.6483, -33.4489)
    assert area is not None
    assert area.warehouse is not None  # Eager loaded

@pytest.mark.asyncio
async def test_storage_area_repo_by_warehouse(db_session, warehouse_with_areas):
    """Test filtering by warehouse with eager loading"""
    repo = StorageAreaRepository(db_session)
    areas = await repo.get_by_warehouse_id(1, with_locations=True)

    assert len(areas) > 0
    for area in areas:
        assert area.warehouse_id == 1
        # Check eager loading (no N+1)
        assert len(area.storage_locations) >= 0

@pytest.mark.asyncio
async def test_storage_area_repo_by_position(db_session, sample_warehouse):
    """Test position filtering (N/S/E/W/C)"""
    repo = StorageAreaRepository(db_session)
    north_areas = await repo.get_by_position(1, "N")

    assert all(area.position == "N" for area in north_areas)
```

**Coverage Target**: ≥85%

### Performance Expectations
- GPS lookup: <50ms (with GIST index on geojson_coordinates)
- get_by_warehouse_id: <20ms for 20 areas per warehouse
- Eager loading prevents N+1 queries (constant query count)

## Handover Briefing

**For the next developer:**
- **Context**: Level 2 of 4-level hierarchy (warehouse → storage_area → storage_location → storage_bin)
- **Key decisions**:
  - Use joinedload for many-to-one (warehouse) - single JOIN query
  - Use selectinload for one-to-many (storage_locations) - separate query
  - Position enum validated at model level (N/S/E/W/C)
  - GPS queries include active=true filter
- **Known limitations**: GPS lookup returns first match only (areas within warehouse should not overlap)
- **Next steps**: R003 (StorageLocationRepository) adds QR code lookup
- **Questions to validate**:
  - Are GIST indexes created for geojson_coordinates?
  - Does position enum enforce valid values?

## Definition of Done Checklist

- [ ] Code written following AsyncRepository pattern
- [ ] Unit tests pass (≥85% coverage)
- [ ] PostGIS queries tested with real geometry data
- [ ] Linting passes (ruff check)
- [ ] Type hints validated (mypy)
- [ ] PR reviewed (2+ approvals)
- [ ] Integration test with DB002 model and R001
- [ ] Performance benchmarks documented

## Time Tracking
- **Estimated**: 2 story points (~4 hours)
- **Actual**: TBD
- **Started**: TBD
- **Completed**: TBD

---

**Card Created**: 2025-10-09
**Last Updated**: 2025-10-09
**Card Owner**: TBD
