# R010: Product Size Repository

## Metadata

- **Epic**: [epic-003-repositories.md](../../02_epics/epic-003-repositories.md)
- **Sprint**: Sprint-01
- **Status**: `backlog`
- **Priority**: `medium`
- **Complexity**: XS (1 story point)
- **Area**: `repositories`
- **Assignee**: TBD
- **Dependencies**:
    - Blocks: [R016, R024, S009]
    - Blocked by: [F006, F007, DB019]

## Related Documentation

- **Engineering Plan
  **: [../../engineering_plan/backend/repository_layer.md](../../engineering_plan/backend/repository_layer.md)
- **Database ERD**: [../../database/database.mmd](../../database/database.mmd#L105-L113)
- **Architecture
  **: [../../engineering_plan/03_architecture_overview.md](../../engineering_plan/03_architecture_overview.md)

## Description

**What**: Implement repository class for `product_sizes` table with CRUD operations and height-based
classification.

**Why**: Product sizes define plant size categories (XS/S/M/L/XL) with height ranges for ML
classification and pricing tiers. Repository provides lookup by code and height-based classification
for ML pipeline.

**Context**: Master data table for size classification. ML pipeline uses height ranges to classify
detected plants. Pricing varies by size (larger plants = higher price).

## Acceptance Criteria

- [ ] **AC1**: `ProductSizeRepository` class inherits from `AsyncRepository[ProductSize]`
- [ ] **AC2**: Implements `get_by_code(code: str)` method with unique constraint validation
- [ ] **AC3**: Implements `get_by_height_range(min_height: float, max_height: float)` for ML
  classification
- [ ] **AC4**: Implements `classify_by_height(height_cm: float)` returning matching size category
- [ ] **AC5**: Implements `get_all_ordered()` returning sizes in sort_order (XS → XL)
- [ ] **AC6**: Query performance: <10ms for all queries (small lookup table)

## Technical Implementation Notes

### Architecture

- **Layer**: Infrastructure (Repository)
- **Dependencies**: F006 (Database connection), DB019 (ProductSize model)
- **Design Pattern**: Repository pattern, inherits AsyncRepository

### Code Hints

```python
from typing import Optional, List
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product_size import ProductSize
from app.repositories.base_repository import AsyncRepository

class ProductSizeRepository(AsyncRepository[ProductSize]):
    """Repository for product size CRUD and height-based classification"""

    def __init__(self, session: AsyncSession):
        super().__init__(ProductSize, session)

    async def get_by_code(self, code: str) -> Optional[ProductSize]:
        """Get product size by unique code"""
        stmt = select(ProductSize).where(ProductSize.code == code)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_height_range(
        self,
        min_height: float,
        max_height: float
    ) -> List[ProductSize]:
        """Get sizes matching height range (for ML classification)"""
        stmt = (
            select(ProductSize)
            .where(
                and_(
                    ProductSize.min_height_cm <= max_height,
                    ProductSize.max_height_cm >= min_height
                )
            )
            .order_by(ProductSize.sort_order)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def classify_by_height(
        self,
        height_cm: float
    ) -> Optional[ProductSize]:
        """Classify plant by height (returns matching size category)"""
        stmt = (
            select(ProductSize)
            .where(
                and_(
                    ProductSize.min_height_cm <= height_cm,
                    ProductSize.max_height_cm >= height_cm
                )
            )
            .order_by(ProductSize.sort_order)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_ordered(self) -> List[ProductSize]:
        """Get all sizes ordered by sort_order (XS → XL)"""
        stmt = select(ProductSize).order_by(ProductSize.sort_order)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_size_distribution(
        self,
        product_id: Optional[int] = None
    ) -> List[dict]:
        """Get size distribution for analytics (count per size)"""
        from sqlalchemy import func
        from app.models.stock_batch import StockBatch

        stmt = (
            select(
                ProductSize,
                func.count(StockBatch.id).label("batch_count"),
                func.sum(StockBatch.quantity_current).label("total_quantity")
            )
            .join(StockBatch, isouter=True)
            .group_by(ProductSize.id)
            .order_by(ProductSize.sort_order)
        )

        if product_id:
            stmt = stmt.where(StockBatch.product_id == product_id)

        result = await self.session.execute(stmt)
        rows = result.all()

        return [
            {
                "size": row[0],
                "batch_count": row[1] or 0,
                "total_quantity": row[2] or 0
            }
            for row in rows
        ]
```

### Testing Requirements

**Unit Tests**:

```python
@pytest.mark.asyncio
async def test_product_size_repo_get_by_code(db_session, sample_sizes):
    """Test size lookup by code"""
    repo = ProductSizeRepository(db_session)
    size = await repo.get_by_code("M")

    assert size is not None
    assert size.code == "M"
    assert size.min_height_cm < size.max_height_cm

@pytest.mark.asyncio
async def test_product_size_repo_by_height_range(db_session, sample_sizes):
    """Test height range matching (for ML)"""
    repo = ProductSizeRepository(db_session)
    # Search for sizes covering 10-20cm range
    sizes = await repo.get_by_height_range(10.0, 20.0)

    assert len(sizes) > 0
    for size in sizes:
        # Range should overlap with search range
        assert not (size.max_height_cm < 10.0 or size.min_height_cm > 20.0)

@pytest.mark.asyncio
async def test_product_size_repo_classify_by_height(db_session, sample_sizes):
    """Test height-based classification (ML pipeline)"""
    repo = ProductSizeRepository(db_session)
    # 15cm should classify as S or M
    size = await repo.classify_by_height(15.0)

    assert size is not None
    assert size.min_height_cm <= 15.0 <= size.max_height_cm

@pytest.mark.asyncio
async def test_product_size_repo_all_ordered(db_session, sample_sizes):
    """Test retrieving all sizes in order (XS → XL)"""
    repo = ProductSizeRepository(db_session)
    sizes = await repo.get_all_ordered()

    # Should be ordered by sort_order
    orders = [s.sort_order for s in sizes]
    assert orders == sorted(orders)

    # Should be ordered by min_height_cm
    heights = [s.min_height_cm for s in sizes]
    assert heights == sorted(heights)

@pytest.mark.asyncio
async def test_product_size_repo_distribution(db_session, batches_by_size):
    """Test size distribution analytics"""
    repo = ProductSizeRepository(db_session)
    distribution = await repo.get_size_distribution()

    assert len(distribution) > 0
    for item in distribution:
        assert "size" in item
        assert "batch_count" in item
        assert "total_quantity" in item
```

**Coverage Target**: ≥85%

### Performance Expectations

- All queries: <10ms (small lookup table, ~5-8 rows)
- classify_by_height: <5ms (indexed height columns)
- get_size_distribution: <30ms (GROUP BY aggregation)

## Handover Briefing

**For the next developer:**

- **Context**: Master data for size classification. Used by ML pipeline and pricing
- **Key decisions**:
    - Height ranges non-overlapping for clean classification
    - sort_order ensures XS → XL ordering in UI
    - Code is standard size naming (XS/S/M/L/XL)
    - ML uses classify_by_height for automatic size detection
- **Known limitations**:
    - Height ranges are static (not per-product customizable)
    - No diameter/width classification (only height)
    - Assumes linear size progression (no special sizes)
- **Next steps**: R016 uses sizes for stock batches, R024 for ML classification
- **Questions to validate**:
    - Should height ranges be per-product or global?
    - Do we need custom size categories per species?

## Definition of Done Checklist

- [ ] Code written following AsyncRepository pattern
- [ ] Unit tests pass (≥85% coverage)
- [ ] Height-based classification tested
- [ ] Range overlap queries tested
- [ ] Size distribution analytics tested
- [ ] Linting passes (ruff check)
- [ ] Type hints validated (mypy)
- [ ] PR reviewed (2+ approvals)
- [ ] Integration test with DB019 model
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
