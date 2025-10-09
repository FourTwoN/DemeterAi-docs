# R003: Storage Location Repository

## Metadata
- **Epic**: [epic-003-repositories.md](../../02_epics/epic-003-repositories.md)
- **Sprint**: Sprint-01
- **Status**: `backlog`
- **Priority**: `high`
- **Complexity**: M (3 story points)
- **Area**: `repositories`
- **Assignee**: TBD
- **Dependencies**:
  - Blocks: [R004, S003]
  - Blocked by: [F006, F007, DB003, R002]

## Related Documentation
- **Engineering Plan**: [../../engineering_plan/backend/repository_layer.md](../../engineering_plan/backend/repository_layer.md)
- **Database ERD**: [../../database/database.mmd](../../database/database.mmd#L33-L47)
- **Architecture**: [../../engineering_plan/03_architecture_overview.md](../../engineering_plan/03_architecture_overview.md)

## Description

**What**: Implement repository class for `storage_locations` table (Level 3 of hierarchy) with CRUD operations + geospatial queries + QR code lookup.

**Why**: Storage locations are the primary unit for photo-based counting. Each location has a QR code for mobile scanning. Repository provides database access with PostGIS support for GPS lookup and QR-based retrieval.

**Context**: Level 3 of 4-level hierarchy. Critical for mobile app workflows (scan QR → take photo → process). Must support complex eager loading of entire hierarchy chain and latest photo session.

## Acceptance Criteria

- [ ] **AC1**: `StorageLocationRepository` class inherits from `AsyncRepository[StorageLocation]`
- [ ] **AC2**: Implements `get_by_code(code: str)` method with unique constraint validation
- [ ] **AC3**: Implements `get_by_qr_code(qr_code: str)` for mobile scanning workflow
- [ ] **AC4**: Implements `get_by_gps_point(longitude: float, latitude: float)` using PostGIS ST_Contains
- [ ] **AC5**: Implements `get_by_storage_area_id(storage_area_id: int)` with eager loading options
- [ ] **AC6**: Implements `get_with_full_hierarchy(location_id: int)` loading warehouse → area → location → bins
- [ ] **AC7**: Includes eager loading for latest photo_processing_session (joinedload)
- [ ] **AC8**: Query performance: QR lookup <10ms, GPS lookup <50ms

## Technical Implementation Notes

### Architecture
- **Layer**: Infrastructure (Repository)
- **Dependencies**: F006 (Database connection), DB003 (StorageLocation model), R002 (StorageAreaRepository)
- **Design Pattern**: Repository pattern, inherits AsyncRepository

### Code Hints
```python
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.ext.asyncio import AsyncSession
from geoalchemy2.functions import ST_Contains, ST_Point

from app.models.storage_location import StorageLocation
from app.repositories.base_repository import AsyncRepository

class StorageLocationRepository(AsyncRepository[StorageLocation]):
    """Repository for storage location CRUD + geospatial + QR queries"""

    def __init__(self, session: AsyncSession):
        super().__init__(StorageLocation, session)

    async def get_by_code(self, code: str) -> Optional[StorageLocation]:
        """Get storage location by unique code"""
        stmt = select(StorageLocation).where(StorageLocation.code == code)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_qr_code(
        self,
        qr_code: str,
        with_latest_photo: bool = True
    ) -> Optional[StorageLocation]:
        """Get storage location by QR code (mobile scanning)"""
        stmt = (
            select(StorageLocation)
            .where(StorageLocation.qr_code == qr_code)
            .where(StorageLocation.active == True)
            .options(
                joinedload(StorageLocation.storage_area)
                .joinedload(StorageArea.warehouse)
            )
        )

        if with_latest_photo:
            stmt = stmt.options(
                joinedload(StorageLocation.latest_photo_session)
            )

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_gps_point(
        self,
        longitude: float,
        latitude: float
    ) -> Optional[StorageLocation]:
        """Find storage location containing GPS point using PostGIS"""
        stmt = (
            select(StorageLocation)
            .where(
                ST_Contains(
                    StorageLocation.geojson_coordinates,
                    ST_Point(longitude, latitude)
                )
            )
            .where(StorageLocation.active == True)
            .options(
                joinedload(StorageLocation.storage_area)
                .joinedload(StorageArea.warehouse)
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_storage_area_id(
        self,
        storage_area_id: int,
        with_bins: bool = False
    ) -> List[StorageLocation]:
        """Get all storage locations for a storage area"""
        stmt = (
            select(StorageLocation)
            .where(StorageLocation.storage_area_id == storage_area_id)
            .where(StorageLocation.active == True)
            .options(
                joinedload(StorageLocation.storage_area)
                .joinedload(StorageArea.warehouse)
            )
        )

        if with_bins:
            stmt = stmt.options(selectinload(StorageLocation.storage_bins))

        result = await self.session.execute(stmt)
        return list(result.scalars().unique().all())

    async def get_with_full_hierarchy(
        self,
        location_id: int
    ) -> Optional[StorageLocation]:
        """Get storage location with full hierarchy loaded"""
        stmt = (
            select(StorageLocation)
            .where(StorageLocation.id == location_id)
            .options(
                # Load parent chain
                joinedload(StorageLocation.storage_area)
                .joinedload(StorageArea.warehouse),
                # Load children
                selectinload(StorageLocation.storage_bins)
                .selectinload(StorageBin.storage_bin_type),
                # Load latest photo
                joinedload(StorageLocation.latest_photo_session)
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_locations_needing_photos(
        self,
        warehouse_id: Optional[int] = None
    ) -> List[StorageLocation]:
        """Get locations without recent photos (>30 days)"""
        from datetime import datetime, timedelta
        thirty_days_ago = datetime.now() - timedelta(days=30)

        stmt = (
            select(StorageLocation)
            .join(StorageArea)
            .outerjoin(PhotoProcessingSession)
            .where(StorageLocation.active == True)
            .where(
                (PhotoProcessingSession.created_at < thirty_days_ago) |
                (PhotoProcessingSession.id == None)
            )
        )

        if warehouse_id:
            stmt = stmt.where(StorageArea.warehouse_id == warehouse_id)

        result = await self.session.execute(stmt)
        return list(result.scalars().unique().all())
```

### Testing Requirements

**Unit Tests**:
```python
@pytest.mark.asyncio
async def test_storage_location_repo_get_by_qr_code(db_session, sample_location):
    """Test QR code lookup (mobile scanning workflow)"""
    repo = StorageLocationRepository(db_session)
    location = await repo.get_by_qr_code("QR-LOC-001")

    assert location is not None
    assert location.qr_code == "QR-LOC-001"
    # Check hierarchy loaded (no N+1)
    assert location.storage_area is not None
    assert location.storage_area.warehouse is not None

@pytest.mark.asyncio
async def test_storage_location_repo_gps_lookup(db_session, sample_location):
    """Test GPS → location lookup using PostGIS"""
    repo = StorageLocationRepository(db_session)
    location = await repo.get_by_gps_point(-70.6483, -33.4489)

    assert location is not None
    assert location.storage_area is not None

@pytest.mark.asyncio
async def test_storage_location_repo_full_hierarchy(db_session, location_with_bins):
    """Test loading full hierarchy in single query"""
    repo = StorageLocationRepository(db_session)
    location = await repo.get_with_full_hierarchy(1)

    # All relations loaded
    assert location.storage_area is not None
    assert location.storage_area.warehouse is not None
    assert len(location.storage_bins) >= 0
    for bin in location.storage_bins:
        assert bin.storage_bin_type is not None

@pytest.mark.asyncio
async def test_locations_needing_photos(db_session, old_location):
    """Test filtering locations without recent photos"""
    repo = StorageLocationRepository(db_session)
    locations = await repo.get_locations_needing_photos(warehouse_id=1)

    assert len(locations) > 0
    # Verify all are >30 days old or never photographed
```

**Coverage Target**: ≥85%

### Performance Expectations
- QR code lookup: <10ms (unique index on qr_code)
- GPS lookup: <50ms (with GIST index on geojson_coordinates)
- Full hierarchy load: <30ms (optimized eager loading)
- get_locations_needing_photos: <100ms for 500 locations

## Handover Briefing

**For the next developer:**
- **Context**: Level 3 of 4-level hierarchy. Critical for mobile workflows (scan QR → photo → ML processing)
- **Key decisions**:
  - QR code is unique across entire system (not just per area)
  - Use joinedload for parent chain (warehouse ← area ← location) - single query
  - Use selectinload for children (bins) - separate query to avoid cartesian product
  - Latest photo session loaded via FK relationship (photo_session_id)
- **Known limitations**:
  - GPS lookup returns first match only (locations should not overlap)
  - QR codes must be generated externally (not auto-generated by DB)
- **Next steps**: R004 (StorageBinRepository) completes the hierarchy
- **Questions to validate**:
  - Are QR codes validated for format/uniqueness?
  - Does get_locations_needing_photos handle null photo_session correctly?

## Definition of Done Checklist

- [ ] Code written following AsyncRepository pattern
- [ ] Unit tests pass (≥85% coverage)
- [ ] PostGIS queries tested with real geometry data
- [ ] QR code lookup tested with unique constraints
- [ ] Linting passes (ruff check)
- [ ] Type hints validated (mypy)
- [ ] PR reviewed (2+ approvals)
- [ ] Integration test with DB003 model and R002
- [ ] Performance benchmarks documented

## Time Tracking
- **Estimated**: 3 story points (~6 hours)
- **Actual**: TBD
- **Started**: TBD
- **Completed**: TBD

---

**Card Created**: 2025-10-09
**Last Updated**: 2025-10-09
**Card Owner**: TBD
