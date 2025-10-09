# R016: Stock Batch Repository

## Metadata
- **Epic**: [epic-003-repositories.md](../../02_epics/epic-003-repositories.md)
- **Sprint**: Sprint-02
- **Status**: `backlog`
- **Priority**: `critical`
- **Complexity**: L (5 story points)
- **Area**: `repositories`
- **Assignee**: TBD
- **Dependencies**:
  - Blocks: [R017, S013]
  - Blocked by: [F006, F007, DB008, R004, R008]

## Related Documentation
- **Engineering Plan**: [../../engineering_plan/backend/repository_layer.md](../../engineering_plan/backend/repository_layer.md)
- **Database ERD**: [../../database/database.mmd](../../database/database.mmd#L156-L177)

## Description

**What**: Implement repository class for `stock_batches` table with CRUD operations, batch_code lookup, and complex inventory queries.

**Why**: Stock batches are the core inventory entities - groups of plants with shared attributes (product, state, size, location). Repository provides batch tracking, inventory queries, and lifecycle management.

**Context**: Central to inventory management. Created by ML pipeline (photo initialization) or manual input. Links to storage bins, products, and movements.

## Acceptance Criteria

- [ ] **AC1**: `StockBatchRepository` class inherits from `AsyncRepository[StockBatch]`
- [ ] **AC2**: Implements `get_by_batch_code(batch_code: str)` method (unique constraint)
- [ ] **AC3**: Implements `get_by_storage_bin_id(bin_id: int)` with full hierarchy loading
- [ ] **AC4**: Implements `get_by_product_and_state(product_id: int, state_id: int)` for inventory queries
- [ ] **AC5**: Implements `get_sellable_inventory(product_id: Optional[int])` for sales workflows
- [ ] **AC6**: Implements `get_batches_needing_attention()` for low quantity alerts
- [ ] **AC7**: Includes complex eager loading (product → family → category, packaging, state, size, bin → location)
- [ ] **AC8**: Query performance: batch_code <10ms, inventory queries <50ms

## Technical Implementation Notes

```python
from typing import Optional, List
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.stock_batch import StockBatch
from app.repositories.base_repository import AsyncRepository

class StockBatchRepository(AsyncRepository[StockBatch]):
    """Repository for stock batch CRUD and inventory queries"""

    def __init__(self, session: AsyncSession):
        super().__init__(StockBatch, session)

    async def get_by_batch_code(self, batch_code: str) -> Optional[StockBatch]:
        """Get batch by unique batch code"""
        stmt = (
            select(StockBatch)
            .where(StockBatch.batch_code == batch_code)
            .options(
                joinedload(StockBatch.product)
                .joinedload(Product.family)
                .joinedload(ProductFamily.category),
                joinedload(StockBatch.product_state),
                joinedload(StockBatch.product_size),
                joinedload(StockBatch.packaging_catalog),
                joinedload(StockBatch.current_storage_bin)
                .joinedload(StorageBin.storage_location)
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_storage_bin_id(
        self,
        storage_bin_id: int
    ) -> List[StockBatch]:
        """Get all batches in a storage bin"""
        stmt = (
            select(StockBatch)
            .where(StockBatch.current_storage_bin_id == storage_bin_id)
            .where(StockBatch.quantity_current > 0)
            .options(
                joinedload(StockBatch.product)
                .joinedload(Product.family),
                joinedload(StockBatch.product_state),
                joinedload(StockBatch.product_size),
                joinedload(StockBatch.packaging_catalog)
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().unique().all())

    async def get_by_product_and_state(
        self,
        product_id: int,
        product_state_id: int,
        min_quantity: int = 0
    ) -> List[StockBatch]:
        """Get batches by product and state (inventory lookup)"""
        stmt = (
            select(StockBatch)
            .where(StockBatch.product_id == product_id)
            .where(StockBatch.product_state_id == product_state_id)
            .where(StockBatch.quantity_current > min_quantity)
            .options(
                joinedload(StockBatch.product_size),
                joinedload(StockBatch.packaging_catalog),
                joinedload(StockBatch.current_storage_bin)
                .joinedload(StorageBin.storage_location)
            )
            .order_by(StockBatch.planting_date.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().unique().all())

    async def get_sellable_inventory(
        self,
        product_id: Optional[int] = None,
        product_size_id: Optional[int] = None
    ) -> List[StockBatch]:
        """Get sellable inventory (state=listo_para_venta, qty>0)"""
        from app.models.product_state import ProductState

        stmt = (
            select(StockBatch)
            .join(ProductState)
            .where(ProductState.is_sellable == True)
            .where(StockBatch.quantity_current > 0)
            .options(
                joinedload(StockBatch.product)
                .joinedload(Product.family)
                .joinedload(ProductFamily.category),
                joinedload(StockBatch.product_state),
                joinedload(StockBatch.product_size),
                joinedload(StockBatch.packaging_catalog)
                .joinedload(PackagingCatalog.packaging_type),
                joinedload(StockBatch.current_storage_bin)
                .joinedload(StorageBin.storage_location)
            )
        )

        if product_id:
            stmt = stmt.where(StockBatch.product_id == product_id)
        if product_size_id:
            stmt = stmt.where(StockBatch.product_size_id == product_size_id)

        stmt = stmt.order_by(
            StockBatch.product_id,
            StockBatch.product_size_id,
            StockBatch.planting_date.asc()
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().unique().all())

    async def get_batches_needing_attention(
        self,
        low_quantity_threshold: int = 10
    ) -> List[StockBatch]:
        """Get batches needing attention (low quantity alerts)"""
        stmt = (
            select(StockBatch)
            .where(
                and_(
                    StockBatch.quantity_current > 0,
                    StockBatch.quantity_current <= low_quantity_threshold
                )
            )
            .options(
                joinedload(StockBatch.product),
                joinedload(StockBatch.product_state),
                joinedload(StockBatch.current_storage_bin)
                .joinedload(StorageBin.storage_location)
            )
            .order_by(StockBatch.quantity_current.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().unique().all())

    async def get_inventory_summary(
        self,
        product_id: Optional[int] = None
    ) -> List[dict]:
        """Get inventory summary (qty by product/state/size)"""
        from sqlalchemy import func

        stmt = (
            select(
                StockBatch.product_id,
                StockBatch.product_state_id,
                StockBatch.product_size_id,
                func.count(StockBatch.id).label("batch_count"),
                func.sum(StockBatch.quantity_current).label("total_quantity")
            )
            .where(StockBatch.quantity_current > 0)
            .group_by(
                StockBatch.product_id,
                StockBatch.product_state_id,
                StockBatch.product_size_id
            )
        )

        if product_id:
            stmt = stmt.where(StockBatch.product_id == product_id)

        result = await self.session.execute(stmt)
        rows = result.all()

        return [
            {
                "product_id": row[0],
                "product_state_id": row[1],
                "product_size_id": row[2],
                "batch_count": row[3],
                "total_quantity": row[4]
            }
            for row in rows
        ]
```

## Testing Requirements

**Unit Tests**: Test batch_code lookup, storage bin filtering, sellable inventory, low quantity alerts, inventory summary aggregation.

**Coverage Target**: ≥85%

### Performance Expectations
- batch_code lookup: <10ms
- get_by_storage_bin_id: <20ms for 20 batches per bin
- get_sellable_inventory: <50ms for full catalog
- get_inventory_summary: <100ms with GROUP BY

## Handover Briefing

**For the next developer:**
- **Context**: Core inventory entity. Complex eager loading critical for performance
- **Key decisions**:
  - batch_code unique globally (format: "{LOCATION}-{DATE}-{SEQ}")
  - quantity_current tracks current stock (updated by movements)
  - Sellable inventory uses is_sellable flag from product_states
  - Low quantity alerts configurable threshold
- **Next steps**: R017 (StockMovementRepository) tracks batch movements

## Definition of Done Checklist

- [ ] Code written following AsyncRepository pattern
- [ ] Unit tests pass (≥85% coverage)
- [ ] Complex eager loading tested
- [ ] Inventory queries tested
- [ ] Linting passes (ruff check)
- [ ] PR reviewed (2+ approvals)

## Time Tracking
- **Estimated**: 5 story points (~10 hours)
- **Actual**: TBD

---

**Card Created**: 2025-10-09
**Last Updated**: 2025-10-09
**Card Owner**: TBD
