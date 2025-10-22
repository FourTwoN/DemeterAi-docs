# R015: Price List Repository

## Metadata

- **Epic**: [epic-003-repositories.md](../../02_epics/epic-003-repositories.md)
- **Sprint**: Sprint-01
- **Status**: `backlog`
- **Priority**: `high`
- **Complexity**: M (3 story points)
- **Area**: `repositories`
- **Assignee**: TBD
- **Dependencies**:
    - Blocks: [S012]
    - Blocked by: [F006, F007, DB027, R014, R006]

## Related Documentation

- **Engineering Plan
  **: [../../engineering_plan/backend/repository_layer.md](../../engineering_plan/backend/repository_layer.md)
- **Database ERD**: [../../database/database.mmd](../../database/database.mmd#L131-L144)

## Description

**What**: Implement repository class for `price_list` table with CRUD operations, SKU lookup, and
pricing queries.

**Why**: Price list defines wholesale/retail prices for product/packaging combinations. Repository
provides fast price lookup for sales calculations and catalog display.

**Context**: Pricing data for monthly reconciliation and sales. Links product categories and
packaging catalog. Updated periodically by admin.

## Acceptance Criteria

- [ ] **AC1**: `PriceListRepository` class inherits from `AsyncRepository[PriceList]`
- [ ] **AC2**: Implements `get_by_sku(sku: str)` method for fast price lookup
- [ ] **AC3**: Implements `get_by_category_and_packaging(category_id: int, packaging_id: int)` for
  pricing matrix
- [ ] **AC4**: Implements `get_available_products()` filtering by availability
- [ ] **AC5**: Includes eager loading for packaging_catalog and product_category
- [ ] **AC6**: Query performance: SKU lookup <10ms, pricing matrix <30ms

## Technical Implementation Notes

```python
from typing import Optional, List
from sqlalchemy import select, and_
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.price_list import PriceList
from app.repositories.base_repository import AsyncRepository

class PriceListRepository(AsyncRepository[PriceList]):
    """Repository for price list CRUD and pricing queries"""

    def __init__(self, session: AsyncSession):
        super().__init__(PriceList, session)

    async def get_by_sku(self, sku: str) -> Optional[PriceList]:
        """Get price list entry by SKU (fast price lookup)"""
        stmt = (
            select(PriceList)
            .where(PriceList.sku == sku)
            .options(
                joinedload(PriceList.packaging_catalog),
                joinedload(PriceList.product_category)
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_category_and_packaging(
        self,
        product_category_id: int,
        packaging_catalog_id: int
    ) -> Optional[PriceList]:
        """Get pricing for specific category + packaging combination"""
        stmt = (
            select(PriceList)
            .where(
                and_(
                    PriceList.product_categories_id == product_category_id,
                    PriceList.packaging_catalog_id == packaging_catalog_id
                )
            )
            .options(
                joinedload(PriceList.packaging_catalog),
                joinedload(PriceList.product_category)
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_available_products(
        self,
        product_category_id: Optional[int] = None
    ) -> List[PriceList]:
        """Get available products for sales (availability filter)"""
        stmt = (
            select(PriceList)
            .where(PriceList.availability.isnot(None))
            .where(PriceList.availability != "")
            .options(
                joinedload(PriceList.packaging_catalog)
                .joinedload(PackagingCatalog.packaging_type),
                joinedload(PriceList.product_category)
            )
            .order_by(PriceList.product_category_id, PriceList.retail_unit_price)
        )

        if product_category_id:
            stmt = stmt.where(PriceList.product_categories_id == product_category_id)

        result = await self.session.execute(stmt)
        return list(result.scalars().unique().all())

    async def get_pricing_matrix(
        self,
        product_category_id: Optional[int] = None
    ) -> List[PriceList]:
        """Get full pricing matrix (all category + packaging combinations)"""
        stmt = (
            select(PriceList)
            .options(
                joinedload(PriceList.packaging_catalog)
                .joinedload(PackagingCatalog.packaging_type),
                joinedload(PriceList.product_category)
            )
            .order_by(
                PriceList.product_categories_id,
                PriceList.packaging_catalog_id
            )
        )

        if product_category_id:
            stmt = stmt.where(PriceList.product_categories_id == product_category_id)

        result = await self.session.execute(stmt)
        return list(result.scalars().unique().all())

    async def get_recently_updated(
        self,
        days: int = 30
    ) -> List[PriceList]:
        """Get price list entries updated in last N days"""
        from datetime import datetime, timedelta
        cutoff_date = datetime.now().date() - timedelta(days=days)

        stmt = (
            select(PriceList)
            .where(PriceList.updated_at >= cutoff_date)
            .options(
                joinedload(PriceList.packaging_catalog),
                joinedload(PriceList.product_category)
            )
            .order_by(PriceList.updated_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().unique().all())
```

## Testing Requirements

**Unit Tests**:

```python
@pytest.mark.asyncio
async def test_price_list_repo_by_sku(db_session, sample_price_list):
    """Test SKU-based price lookup"""
    repo = PriceListRepository(db_session)
    price = await repo.get_by_sku("CACT-10CM")

    assert price is not None
    assert price.sku == "CACT-10CM"
    assert price.retail_unit_price > 0

@pytest.mark.asyncio
async def test_price_list_repo_by_category_packaging(db_session, price_entries):
    """Test pricing matrix lookup"""
    repo = PriceListRepository(db_session)
    price = await repo.get_by_category_and_packaging(
        product_category_id=1,
        packaging_catalog_id=1
    )

    assert price is not None
    assert price.product_categories_id == 1
    assert price.packaging_catalog_id == 1

@pytest.mark.asyncio
async def test_price_list_repo_available_products(db_session, price_list_with_availability):
    """Test filtering available products"""
    repo = PriceListRepository(db_session)
    available = await repo.get_available_products()

    assert len(available) > 0
    for price in available:
        assert price.availability is not None
        assert price.availability != ""

@pytest.mark.asyncio
async def test_price_list_repo_pricing_matrix(db_session, full_price_list):
    """Test full pricing matrix retrieval"""
    repo = PriceListRepository(db_session)
    matrix = await repo.get_pricing_matrix(product_category_id=1)

    assert len(matrix) > 0
    # Should be ordered by category, then packaging
    assert all(p.product_categories_id == 1 for p in matrix)
```

**Coverage Target**: ≥85%

### Performance Expectations

- SKU lookup: <10ms (indexed sku column)
- Category+packaging lookup: <15ms (composite index)
- Pricing matrix: <30ms for full catalog
- Available products: <20ms with availability filter

## Handover Briefing

**For the next developer:**

- **Context**: Pricing data for sales and monthly reconciliation. Updated periodically by admin
- **Key decisions**:
    - SKU format: "{CATEGORY}-{PACKAGING}" (e.g., "CACT-10CM")
    - Wholesale vs retail pricing tracked separately
    - Availability field indicates stock status (nullable)
    - discount_factor for promotions/seasonal pricing
- **Next steps**: Service layer uses this for sales calculations

## Definition of Done Checklist

- [ ] Code written following AsyncRepository pattern
- [ ] Unit tests pass (≥85% coverage)
- [ ] SKU lookup tested
- [ ] Pricing matrix tested
- [ ] Availability filtering tested
- [ ] Linting passes (ruff check)
- [ ] PR reviewed (2+ approvals)

## Time Tracking

- **Estimated**: 3 story points (~6 hours)
- **Actual**: TBD

---

**Card Created**: 2025-10-09
**Last Updated**: 2025-10-09
**Card Owner**: TBD
