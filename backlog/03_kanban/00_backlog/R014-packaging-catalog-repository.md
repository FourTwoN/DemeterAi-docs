# R014: Packaging Catalog Repository

## Metadata
- **Epic**: [epic-003-repositories.md](../../02_epics/epic-003-repositories.md)
- **Sprint**: Sprint-01
- **Status**: `backlog`
- **Priority**: `high`
- **Complexity**: M (3 story points)
- **Area**: `repositories`
- **Assignee**: TBD
- **Dependencies**:
  - Blocks: [R015, R016, S011]
  - Blocked by: [F006, F007, DB023, R011, R012, R013]

## Related Documentation
- **Engineering Plan**: [../../engineering_plan/backend/repository_layer.md](../../engineering_plan/backend/repository_layer.md)
- **Database ERD**: [../../database/database.mmd](../../database/database.mmd#L120-L130)

## Description

**What**: Implement repository class for `packaging_catalog` table with CRUD operations, SKU lookup, and dimension filtering.

**Why**: Packaging catalog defines available container products (combinations of type/material/color with dimensions). Repository provides SKU lookup for inventory and dimension-based search for ML classification.

**Context**: Master data combining packaging attributes. Used by stock batches, ML classification, and pricing. SKU uniquely identifies each packaging combination.

## Acceptance Criteria

- [ ] **AC1**: `PackagingCatalogRepository` class inherits from `AsyncRepository[PackagingCatalog]`
- [ ] **AC2**: Implements `get_by_sku(sku: str)` method (unique constraint)
- [ ] **AC3**: Implements `get_by_dimensions(diameter_cm: float, tolerance: float)` for ML classification
- [ ] **AC4**: Implements `get_by_type_and_volume(type_id: int, volume_liters: float)` for filtering
- [ ] **AC5**: Includes eager loading for packaging_type, packaging_material, packaging_color
- [ ] **AC6**: Query performance: SKU lookup <10ms, dimension search <20ms

## Technical Implementation Notes

```python
from typing import Optional, List
from sqlalchemy import select, and_
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.packaging_catalog import PackagingCatalog
from app.repositories.base_repository import AsyncRepository

class PackagingCatalogRepository(AsyncRepository[PackagingCatalog]):
    """Repository for packaging catalog CRUD and dimension queries"""

    def __init__(self, session: AsyncSession):
        super().__init__(PackagingCatalog, session)

    async def get_by_sku(self, sku: str) -> Optional[PackagingCatalog]:
        """Get packaging by SKU (barcode scanning)"""
        stmt = (
            select(PackagingCatalog)
            .where(PackagingCatalog.sku == sku)
            .options(
                joinedload(PackagingCatalog.packaging_type),
                joinedload(PackagingCatalog.packaging_material),
                joinedload(PackagingCatalog.packaging_color)
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_dimensions(
        self,
        diameter_cm: float,
        tolerance: float = 2.0
    ) -> List[PackagingCatalog]:
        """Find packaging by diameter (for ML classification)"""
        min_diameter = diameter_cm - tolerance
        max_diameter = diameter_cm + tolerance

        stmt = (
            select(PackagingCatalog)
            .where(PackagingCatalog.diameter_cm.between(min_diameter, max_diameter))
            .options(
                joinedload(PackagingCatalog.packaging_type),
                joinedload(PackagingCatalog.packaging_material),
                joinedload(PackagingCatalog.packaging_color)
            )
            .order_by(PackagingCatalog.volume_liters.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().unique().all())

    async def get_by_type_and_volume(
        self,
        packaging_type_id: int,
        min_volume: Optional[float] = None,
        max_volume: Optional[float] = None
    ) -> List[PackagingCatalog]:
        """Get packaging by type and volume range"""
        stmt = (
            select(PackagingCatalog)
            .where(PackagingCatalog.packaging_type_id == packaging_type_id)
            .options(
                joinedload(PackagingCatalog.packaging_type),
                joinedload(PackagingCatalog.packaging_material),
                joinedload(PackagingCatalog.packaging_color)
            )
        )

        if min_volume is not None:
            stmt = stmt.where(PackagingCatalog.volume_liters >= min_volume)
        if max_volume is not None:
            stmt = stmt.where(PackagingCatalog.volume_liters <= max_volume)

        stmt = stmt.order_by(PackagingCatalog.volume_liters)
        result = await self.session.execute(stmt)
        return list(result.scalars().unique().all())

    async def get_catalog_with_pricing(
        self,
        packaging_type_id: Optional[int] = None
    ) -> List[PackagingCatalog]:
        """Get catalog entries with pricing information"""
        from app.models.price_list import PriceList

        stmt = (
            select(PackagingCatalog)
            .outerjoin(PriceList)
            .options(
                joinedload(PackagingCatalog.packaging_type),
                joinedload(PackagingCatalog.packaging_material),
                joinedload(PackagingCatalog.packaging_color),
                selectinload(PackagingCatalog.price_list_entries)
            )
        )

        if packaging_type_id:
            stmt = stmt.where(PackagingCatalog.packaging_type_id == packaging_type_id)

        result = await self.session.execute(stmt)
        return list(result.scalars().unique().all())
```

## Testing Requirements

**Unit Tests**:
```python
@pytest.mark.asyncio
async def test_packaging_catalog_repo_by_sku(db_session, sample_packaging):
    """Test SKU lookup"""
    repo = PackagingCatalogRepository(db_session)
    packaging = await repo.get_by_sku("POT-10CM-BLK")

    assert packaging is not None
    assert packaging.sku == "POT-10CM-BLK"
    assert packaging.packaging_type is not None

@pytest.mark.asyncio
async def test_packaging_catalog_repo_by_dimensions(db_session, packaging_items):
    """Test dimension-based search (ML classification)"""
    repo = PackagingCatalogRepository(db_session)
    # Search for ~10cm diameter pots (±2cm tolerance)
    matches = await repo.get_by_dimensions(10.0, tolerance=2.0)

    assert len(matches) > 0
    for p in matches:
        assert 8.0 <= p.diameter_cm <= 12.0

@pytest.mark.asyncio
async def test_packaging_catalog_repo_by_type_and_volume(db_session, packaging_items):
    """Test filtering by type and volume range"""
    repo = PackagingCatalogRepository(db_session)
    # Get all macetas between 1-5 liters
    pots = await repo.get_by_type_and_volume(1, min_volume=1.0, max_volume=5.0)

    assert len(pots) > 0
    for p in pots:
        assert p.packaging_type_id == 1
        assert 1.0 <= p.volume_liters <= 5.0
```

**Coverage Target**: ≥85%

### Performance Expectations
- SKU lookup: <10ms (unique index on sku)
- Dimension search: <20ms (indexed diameter_cm)
- Type/volume filtering: <15ms

## Handover Briefing

**For the next developer:**
- **Context**: Master data combining packaging attributes. Critical for ML classification and inventory
- **Key decisions**:
  - SKU unique globally (e.g., "POT-10CM-BLK")
  - Dimension tolerance for ML classification (default ±2cm)
  - Eager load all FK relationships (type, material, color)
  - Volume used for capacity calculations
- **Next steps**: R015 (PriceListRepository) links pricing to catalog

## Definition of Done Checklist

- [ ] Code written following AsyncRepository pattern
- [ ] Unit tests pass (≥85% coverage)
- [ ] SKU lookup tested
- [ ] Dimension search tested
- [ ] Linting passes (ruff check)
- [ ] PR reviewed (2+ approvals)

## Time Tracking
- **Estimated**: 3 story points (~6 hours)
- **Actual**: TBD

---

**Card Created**: 2025-10-09
**Last Updated**: 2025-10-09
**Card Owner**: TBD
