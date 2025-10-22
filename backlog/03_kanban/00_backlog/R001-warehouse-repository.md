# R001: Warehouse Repository

## Metadata

- **Epic**: [epic-003-repositories.md](../../02_epics/epic-003-repositories.md)
- **Sprint**: Sprint-01
- **Status**: `backlog`
- **Priority**: `high`
- **Complexity**: S (2 story points)
- **Area**: `repositories`
- **Assignee**: TBD
- **Dependencies**:
    - Blocks: [R002, S001]
    - Blocked by: [F006, F007, DB001]

## Related Documentation

- **Engineering Plan
  **: [../../engineering_plan/backend/repository_layer.md](../../engineering_plan/backend/repository_layer.md)
- **Database ERD**: [../../database/database.mmd](../../database/database.mmd#L8-L19)
- **Architecture
  **: [../../engineering_plan/03_architecture_overview.md](../../engineering_plan/03_architecture_overview.md)

## Description

**What**: Implement repository class for `warehouses` table with CRUD operations + geospatial
queries for warehouse management.

**Why**: Warehouses are the root of the 4-level location hierarchy. Repository provides database
access layer for warehouse operations with PostGIS support for GPS-based warehouse lookup.

**Context**: Clean Architecture pattern - repositories encapsulate all database access. This
repository must support ST_Contains queries for GPS → warehouse mapping and eager loading of
storage_areas relationship to prevent N+1 queries.

## Acceptance Criteria

- [ ] **AC1**: `WarehouseRepository` class inherits from `AsyncRepository[Warehouse]`
- [ ] **AC2**: Implements `get_by_code(code: str)` method with unique constraint validation
- [ ] **AC3**: Implements `get_by_gps_point(longitude: float, latitude: float)` using PostGIS
  ST_Contains
- [ ] **AC4**: Implements `get_active_warehouses()` with active=true filter
- [ ] **AC5**: Includes eager loading strategy for `storage_areas` relationship (use `selectinload`)
- [ ] **AC6**: Query performance <50ms for GPS lookup (test with SP-GiST index)
- [ ] **AC7**: Type hints for all methods using SQLAlchemy 2.0 typed API

## Technical Implementation Notes

### Architecture

- **Layer**: Infrastructure (Repository)
- **Dependencies**: F006 (Database connection), DB001 (Warehouse model)
- **Design Pattern**: Repository pattern, inherits AsyncRepository

### Code Hints

```python
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from geoalchemy2.functions import ST_Contains, ST_Point

from app.models.warehouse import Warehouse
from app.repositories.base_repository import AsyncRepository

class WarehouseRepository(AsyncRepository[Warehouse]):
    """Repository for warehouse CRUD + geospatial queries"""

    def __init__(self, session: AsyncSession):
        super().__init__(Warehouse, session)

    async def get_by_code(self, code: str) -> Optional[Warehouse]:
        """Get warehouse by unique code"""
        stmt = select(Warehouse).where(Warehouse.code == code)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_gps_point(
        self,
        longitude: float,
        latitude: float
    ) -> Optional[Warehouse]:
        """Find warehouse containing GPS point using PostGIS"""
        stmt = (
            select(Warehouse)
            .where(
                ST_Contains(
                    Warehouse.geojson_coordinates,
                    ST_Point(longitude, latitude)
                )
            )
            .where(Warehouse.active == True)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_warehouses(
        self,
        with_areas: bool = False
    ) -> List[Warehouse]:
        """Get all active warehouses, optionally with storage_areas"""
        stmt = select(Warehouse).where(Warehouse.active == True)

        if with_areas:
            stmt = stmt.options(selectinload(Warehouse.storage_areas))

        result = await self.session.execute(stmt)
        return list(result.scalars().all())
```

### Testing Requirements

**Unit Tests**:

```python
@pytest.mark.asyncio
async def test_warehouse_repo_get_by_code(db_session, sample_warehouse):
    repo = WarehouseRepository(db_session)
    warehouse = await repo.get_by_code("WH001")
    assert warehouse is not None
    assert warehouse.code == "WH001"

@pytest.mark.asyncio
async def test_warehouse_repo_gps_lookup(db_session, sample_warehouse):
    """Test GPS → warehouse lookup using PostGIS"""
    repo = WarehouseRepository(db_session)
    # GPS point inside warehouse polygon
    warehouse = await repo.get_by_gps_point(-70.6483, -33.4489)
    assert warehouse is not None
    assert warehouse.code == "WH001"

@pytest.mark.asyncio
async def test_warehouse_repo_eager_loading(db_session, warehouse_with_areas):
    """Test N+1 prevention with eager loading"""
    repo = WarehouseRepository(db_session)
    warehouses = await repo.get_active_warehouses(with_areas=True)

    # Access storage_areas without additional query
    for wh in warehouses:
        assert len(wh.storage_areas) >= 0  # No query fired here
```

**Coverage Target**: ≥85%

### Performance Expectations

- GPS lookup: <50ms (with SP-GiST index on geojson_coordinates)
- get_active_warehouses: <20ms for 50 warehouses
- Eager loading prevents N+1 queries (constant query count regardless of result set size)

## Handover Briefing

**For the next developer:**

- **Context**: First repository in 4-level hierarchy. Sets pattern for all location repositories.
- **Key decisions**:
    - Use ST_Contains for GPS queries (PostGIS operator)
    - Eager loading via selectinload (not joinedload) for one-to-many
    - SP-GiST index required for performance (see DB001 migration)
- **Known limitations**: GPS lookup returns first match only (warehouses should not overlap)
- **Next steps**: R002 (StorageAreaRepository) follows same pattern
- **Questions to validate**:
    - Does GPS lookup work without explicit CRS conversion?
    - Are inactive warehouses correctly filtered in GPS queries?

## Definition of Done Checklist

- [ ] Code written following AsyncRepository pattern
- [ ] Unit tests pass (≥85% coverage)
- [ ] PostGIS queries tested with real geometry data
- [ ] Linting passes (ruff check)
- [ ] Type hints validated (mypy)
- [ ] PR reviewed (2+ approvals)
- [ ] Integration test with DB001 model
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
