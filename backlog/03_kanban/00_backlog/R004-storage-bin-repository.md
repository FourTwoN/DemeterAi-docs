# R004: Storage Bin Repository

## Metadata
- **Epic**: [epic-003-repositories.md](../../02_epics/epic-003-repositories.md)
- **Sprint**: Sprint-01
- **Status**: `backlog`
- **Priority**: `high`
- **Complexity**: S (2 story points)
- **Area**: `repositories`
- **Assignee**: TBD
- **Dependencies**:
  - Blocks: [R016, S004]
  - Blocked by: [F006, F007, DB004, R003]

## Related Documentation
- **Engineering Plan**: [../../engineering_plan/backend/repository_layer.md](../../engineering_plan/backend/repository_layer.md)
- **Database ERD**: [../../database/database.mmd](../../database/database.mmd#L48-L58)
- **Architecture**: [../../engineering_plan/03_architecture_overview.md](../../engineering_plan/03_architecture_overview.md)

## Description

**What**: Implement repository class for `storage_bins` table (Level 4 of hierarchy) with CRUD operations and ML metadata queries.

**Why**: Storage bins are the leaf nodes of the location hierarchy - actual physical containers detected by ML (boxes, trays, pots). Repository provides database access for bin management and ML-generated metadata.

**Context**: Level 4 (leaf) of 4-level hierarchy. Created by ML segmentation pipeline with position_metadata from YOLO masks. Each bin stores stock batches.

## Acceptance Criteria

- [ ] **AC1**: `StorageBinRepository` class inherits from `AsyncRepository[StorageBin]`
- [ ] **AC2**: Implements `get_by_code(code: str)` method with unique constraint validation
- [ ] **AC3**: Implements `get_by_storage_location_id(location_id: int)` with eager loading
- [ ] **AC4**: Implements `get_by_status(status: str)` for filtering active/maintenance/retired bins
- [ ] **AC5**: Implements `get_with_current_stock(bin_id: int)` loading bin + stock_batches
- [ ] **AC6**: Includes eager loading for storage_bin_type and storage_location
- [ ] **AC7**: Query performance: <20ms for location filtering, <10ms for code lookup

## Technical Implementation Notes

### Architecture
- **Layer**: Infrastructure (Repository)
- **Dependencies**: F006 (Database connection), DB004 (StorageBin model), R003 (StorageLocationRepository)
- **Design Pattern**: Repository pattern, inherits AsyncRepository

### Code Hints
```python
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.storage_bin import StorageBin
from app.repositories.base_repository import AsyncRepository

class StorageBinRepository(AsyncRepository[StorageBin]):
    """Repository for storage bin CRUD and stock queries"""

    def __init__(self, session: AsyncSession):
        super().__init__(StorageBin, session)

    async def get_by_code(self, code: str) -> Optional[StorageBin]:
        """Get storage bin by unique code"""
        stmt = select(StorageBin).where(StorageBin.code == code)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_storage_location_id(
        self,
        storage_location_id: int,
        status: Optional[str] = "active"
    ) -> List[StorageBin]:
        """Get all bins for a storage location"""
        stmt = (
            select(StorageBin)
            .where(StorageBin.storage_location_id == storage_location_id)
            .options(
                joinedload(StorageBin.storage_bin_type),
                joinedload(StorageBin.storage_location)
            )
        )

        if status:
            stmt = stmt.where(StorageBin.status == status)

        result = await self.session.execute(stmt)
        return list(result.scalars().unique().all())

    async def get_by_status(
        self,
        status: str,
        storage_location_id: Optional[int] = None
    ) -> List[StorageBin]:
        """Get bins by status (active/maintenance/retired)"""
        stmt = (
            select(StorageBin)
            .where(StorageBin.status == status)
            .options(
                joinedload(StorageBin.storage_bin_type),
                joinedload(StorageBin.storage_location)
            )
        )

        if storage_location_id:
            stmt = stmt.where(StorageBin.storage_location_id == storage_location_id)

        result = await self.session.execute(stmt)
        return list(result.scalars().unique().all())

    async def get_with_current_stock(
        self,
        bin_id: int
    ) -> Optional[StorageBin]:
        """Get bin with all current stock batches"""
        stmt = (
            select(StorageBin)
            .where(StorageBin.id == bin_id)
            .options(
                joinedload(StorageBin.storage_bin_type),
                joinedload(StorageBin.storage_location),
                selectinload(StorageBin.stock_batches)
                .joinedload(StockBatch.product)
                .joinedload(Product.family)
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_bins_by_type(
        self,
        storage_bin_type_id: int,
        storage_location_id: Optional[int] = None
    ) -> List[StorageBin]:
        """Get bins by type (e.g., all plug trays)"""
        stmt = (
            select(StorageBin)
            .where(StorageBin.storage_bin_type_id == storage_bin_type_id)
            .where(StorageBin.status == "active")
            .options(joinedload(StorageBin.storage_bin_type))
        )

        if storage_location_id:
            stmt = stmt.where(StorageBin.storage_location_id == storage_location_id)

        result = await self.session.execute(stmt)
        return list(result.scalars().unique().all())

    async def get_empty_bins(
        self,
        storage_location_id: Optional[int] = None
    ) -> List[StorageBin]:
        """Get bins with no current stock (available for planting)"""
        from sqlalchemy import func, not_

        stmt = (
            select(StorageBin)
            .outerjoin(StockBatch)
            .where(StorageBin.status == "active")
            .where(
                not_(
                    StorageBin.stock_batches.any()
                )
            )
            .options(
                joinedload(StorageBin.storage_bin_type),
                joinedload(StorageBin.storage_location)
            )
        )

        if storage_location_id:
            stmt = stmt.where(StorageBin.storage_location_id == storage_location_id)

        result = await self.session.execute(stmt)
        return list(result.scalars().unique().all())
```

### Testing Requirements

**Unit Tests**:
```python
@pytest.mark.asyncio
async def test_storage_bin_repo_get_by_code(db_session, sample_bin):
    """Test bin lookup by code"""
    repo = StorageBinRepository(db_session)
    bin = await repo.get_by_code("BIN-001")

    assert bin is not None
    assert bin.code == "BIN-001"

@pytest.mark.asyncio
async def test_storage_bin_repo_by_location(db_session, location_with_bins):
    """Test filtering bins by storage location"""
    repo = StorageBinRepository(db_session)
    bins = await repo.get_by_storage_location_id(1, status="active")

    assert len(bins) > 0
    for bin in bins:
        assert bin.storage_location_id == 1
        assert bin.status == "active"
        # Check eager loading
        assert bin.storage_bin_type is not None

@pytest.mark.asyncio
async def test_storage_bin_repo_with_stock(db_session, bin_with_stock):
    """Test loading bin with stock batches"""
    repo = StorageBinRepository(db_session)
    bin = await repo.get_with_current_stock(1)

    assert bin is not None
    assert len(bin.stock_batches) > 0
    # Check deep eager loading
    for batch in bin.stock_batches:
        assert batch.product is not None
        assert batch.product.family is not None

@pytest.mark.asyncio
async def test_storage_bin_repo_empty_bins(db_session, empty_bins):
    """Test finding bins available for planting"""
    repo = StorageBinRepository(db_session)
    empty = await repo.get_empty_bins(storage_location_id=1)

    assert len(empty) > 0
    for bin in empty:
        assert len(bin.stock_batches) == 0

@pytest.mark.asyncio
async def test_storage_bin_repo_by_type(db_session, bins_by_type):
    """Test filtering bins by type (plug trays, boxes, etc)"""
    repo = StorageBinRepository(db_session)
    plug_trays = await repo.get_bins_by_type(storage_bin_type_id=1)

    assert all(bin.storage_bin_type_id == 1 for bin in plug_trays)
```

**Coverage Target**: ≥85%

### Performance Expectations
- Code lookup: <10ms (unique index on code)
- get_by_storage_location_id: <20ms for 50 bins per location
- get_with_current_stock: <30ms (with stock batch eager loading)
- get_empty_bins: <50ms (LEFT JOIN query)

## Handover Briefing

**For the next developer:**
- **Context**: Leaf node of 4-level hierarchy. Created by ML segmentation with position_metadata (bbox, mask, confidence)
- **Key decisions**:
  - Bins have status enum (active/maintenance/retired) for lifecycle management
  - position_metadata is JSONB storing ML detection results (bbox, segmentation_mask, confidence)
  - Empty bins query uses LEFT JOIN to find bins without stock (available for planting)
  - Eager load storage_bin_type for capacity calculations
- **Known limitations**:
  - Bin code must be unique globally (not per location)
  - position_metadata structure not enforced by DB (validated in Pydantic schemas)
- **Next steps**: R016 (StockBatchRepository) links batches to bins
- **Questions to validate**:
  - Should maintenance bins be excluded from stock queries?
  - Is position_metadata indexed for spatial queries?

## Definition of Done Checklist

- [ ] Code written following AsyncRepository pattern
- [ ] Unit tests pass (≥85% coverage)
- [ ] Status filtering tested (active/maintenance/retired)
- [ ] Empty bins query tested with LEFT JOIN
- [ ] Linting passes (ruff check)
- [ ] Type hints validated (mypy)
- [ ] PR reviewed (2+ approvals)
- [ ] Integration test with DB004 model and R003
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
