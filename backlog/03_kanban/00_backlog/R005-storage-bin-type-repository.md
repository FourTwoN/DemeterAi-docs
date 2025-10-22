# R005: Storage Bin Type Repository

## Metadata

- **Epic**: [epic-003-repositories.md](../../02_epics/epic-003-repositories.md)
- **Sprint**: Sprint-01
- **Status**: `backlog`
- **Priority**: `medium`
- **Complexity**: XS (1 story point)
- **Area**: `repositories`
- **Assignee**: TBD
- **Dependencies**:
    - Blocks: [R004, R026]
    - Blocked by: [F006, F007, DB005]

## Related Documentation

- **Engineering Plan
  **: [../../engineering_plan/backend/repository_layer.md](../../engineering_plan/backend/repository_layer.md)
- **Database ERD**: [../../database/database.mmd](../../database/database.mmd#L59-L74)
- **Architecture
  **: [../../engineering_plan/03_architecture_overview.md](../../engineering_plan/03_architecture_overview.md)

## Description

**What**: Implement repository class for `storage_bin_types` table with CRUD operations and category
filtering.

**Why**: Storage bin types define container categories (plug trays, seedling trays, boxes, segments,
pots) with capacity metadata. Repository provides lookup by code and category filtering for ML
classification and capacity planning.

**Context**: Master data table defining container types. Used by ML pipeline to classify detected
bins and calculate plant density. Each type has dimensions and capacity metadata.

## Acceptance Criteria

- [ ] **AC1**: `StorageBinTypeRepository` class inherits from `AsyncRepository[StorageBinType]`
- [ ] **AC2**: Implements `get_by_code(code: str)` method with unique constraint validation
- [ ] **AC3**: Implements `get_by_category(category: str)` for filtering (
  plug/seedling_tray/box/segment/pot)
- [ ] **AC4**: Implements `get_grid_types()` for grid-based containers (rows × columns)
- [ ] **AC5**: Implements `calculate_capacity(type_id: int)` for capacity calculations
- [ ] **AC6**: Query performance: <10ms for all queries (small lookup table)

## Technical Implementation Notes

### Architecture

- **Layer**: Infrastructure (Repository)
- **Dependencies**: F006 (Database connection), DB005 (StorageBinType model)
- **Design Pattern**: Repository pattern, inherits AsyncRepository

### Code Hints

```python
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.storage_bin_type import StorageBinType
from app.repositories.base_repository import AsyncRepository

class StorageBinTypeRepository(AsyncRepository[StorageBinType]):
    """Repository for storage bin type CRUD and category queries"""

    def __init__(self, session: AsyncSession):
        super().__init__(StorageBinType, session)

    async def get_by_code(self, code: str) -> Optional[StorageBinType]:
        """Get storage bin type by unique code"""
        stmt = select(StorageBinType).where(StorageBinType.code == code)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_category(
        self,
        category: str
    ) -> List[StorageBinType]:
        """Get bin types by category (plug/seedling_tray/box/segment/pot)"""
        stmt = (
            select(StorageBinType)
            .where(StorageBinType.category == category)
            .order_by(StorageBinType.capacity.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_grid_types(self) -> List[StorageBinType]:
        """Get bin types with grid layout (rows × columns)"""
        stmt = (
            select(StorageBinType)
            .where(StorageBinType.is_grid == True)
            .where(StorageBinType.rows.isnot(None))
            .where(StorageBinType.columns.isnot(None))
            .order_by(StorageBinType.capacity.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_dimensions(
        self,
        min_length: float,
        max_length: float,
        min_width: float,
        max_width: float
    ) -> List[StorageBinType]:
        """Find bin types matching dimension range (for ML classification)"""
        stmt = (
            select(StorageBinType)
            .where(StorageBinType.length_cm.between(min_length, max_length))
            .where(StorageBinType.width_cm.between(min_width, max_width))
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def calculate_capacity(self, type_id: int) -> Optional[int]:
        """Calculate capacity for a bin type"""
        bin_type = await self.get(type_id)
        if not bin_type:
            return None

        # If capacity is explicitly set, use it
        if bin_type.capacity:
            return bin_type.capacity

        # Calculate from grid dimensions
        if bin_type.is_grid and bin_type.rows and bin_type.columns:
            return bin_type.rows * bin_type.columns

        # Cannot calculate
        return None

    async def get_all_active(self) -> List[StorageBinType]:
        """Get all active bin types (for ML classification dropdown)"""
        stmt = select(StorageBinType).order_by(StorageBinType.category, StorageBinType.capacity.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
```

### Testing Requirements

**Unit Tests**:

```python
@pytest.mark.asyncio
async def test_storage_bin_type_repo_get_by_code(db_session, sample_bin_type):
    """Test bin type lookup by code"""
    repo = StorageBinTypeRepository(db_session)
    bin_type = await repo.get_by_code("PLUG-72")

    assert bin_type is not None
    assert bin_type.code == "PLUG-72"
    assert bin_type.category == "plug"

@pytest.mark.asyncio
async def test_storage_bin_type_repo_by_category(db_session, bin_types):
    """Test filtering by category"""
    repo = StorageBinTypeRepository(db_session)
    plug_types = await repo.get_by_category("plug")

    assert len(plug_types) > 0
    assert all(bt.category == "plug" for bt in plug_types)
    # Should be sorted by capacity desc
    capacities = [bt.capacity for bt in plug_types]
    assert capacities == sorted(capacities, reverse=True)

@pytest.mark.asyncio
async def test_storage_bin_type_repo_grid_types(db_session, grid_bin_types):
    """Test filtering grid-based containers"""
    repo = StorageBinTypeRepository(db_session)
    grid_types = await repo.get_grid_types()

    assert len(grid_types) > 0
    for bt in grid_types:
        assert bt.is_grid == True
        assert bt.rows is not None
        assert bt.columns is not None

@pytest.mark.asyncio
async def test_storage_bin_type_repo_by_dimensions(db_session, bin_types):
    """Test dimension-based lookup (for ML classification)"""
    repo = StorageBinTypeRepository(db_session)
    # Search for bins ~50cm × ~30cm
    matches = await repo.get_by_dimensions(45, 55, 25, 35)

    assert len(matches) > 0
    for bt in matches:
        assert 45 <= bt.length_cm <= 55
        assert 25 <= bt.width_cm <= 35

@pytest.mark.asyncio
async def test_storage_bin_type_repo_calculate_capacity(db_session, grid_bin_type):
    """Test capacity calculation from grid dimensions"""
    repo = StorageBinTypeRepository(db_session)

    # Grid type: 8 rows × 9 columns = 72 capacity
    capacity = await repo.calculate_capacity(1)
    assert capacity == 72

    # Type with explicit capacity
    capacity = await repo.calculate_capacity(2)
    assert capacity == 100
```

**Coverage Target**: ≥85%

### Performance Expectations

- All queries: <10ms (small lookup table, ~20-50 rows)
- Category filtering: <5ms (indexed category column)
- Dimension search: <15ms (indexed length_cm, width_cm)

## Handover Briefing

**For the next developer:**

- **Context**: Master data defining container types. Critical for ML classification and capacity
  planning
- **Key decisions**:
    - Category enum: plug/seedling_tray/box/segment/pot (validated at model level)
    - Grid containers have rows × columns → auto-calculate capacity
    - Non-grid containers have explicit capacity field
    - Dimensions used by ML to match detected bins to types
- **Known limitations**:
    - Capacity calculation assumes all grid cells usable (no adjustments for edge cells)
    - Dimension matching is simple range query (no tolerance/fuzzy matching)
- **Next steps**: R004 uses this for bin type lookups, R026 for density parameters
- **Questions to validate**:
    - Should category be an enum type or varchar?
    - Are dimension columns indexed for ML queries?

## Definition of Done Checklist

- [ ] Code written following AsyncRepository pattern
- [ ] Unit tests pass (≥85% coverage)
- [ ] Category filtering tested with all enum values
- [ ] Grid capacity calculation tested
- [ ] Dimension-based search tested
- [ ] Linting passes (ruff check)
- [ ] Type hints validated (mypy)
- [ ] PR reviewed (2+ approvals)
- [ ] Integration test with DB005 model
- [ ] Performance benchmarks documented

## Time Tracking

- **Estimated**: 1 story point (~2 hours)
- **Actual**: TBD
- **Started**: TBD
- **Completed**: TBD

---

**Card Created**: 2025-10-09
**Last Updated**: 2025-10-09
**Card Owner**: TBD
