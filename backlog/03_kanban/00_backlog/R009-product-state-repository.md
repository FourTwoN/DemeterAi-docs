# R009: Product State Repository

## Metadata
- **Epic**: [epic-003-repositories.md](../../02_epics/epic-003-repositories.md)
- **Sprint**: Sprint-01
- **Status**: `backlog`
- **Priority**: `medium`
- **Complexity**: XS (1 story point)
- **Area**: `repositories`
- **Assignee**: TBD
- **Dependencies**:
  - Blocks: [R016, S008]
  - Blocked by: [F006, F007, DB018]

## Related Documentation
- **Engineering Plan**: [../../engineering_plan/backend/repository_layer.md](../../engineering_plan/backend/repository_layer.md)
- **Database ERD**: [../../database/database.mmd](../../database/database.mmd#L97-L104)
- **Architecture**: [../../engineering_plan/03_architecture_overview.md](../../engineering_plan/03_architecture_overview.md)

## Description

**What**: Implement repository class for `product_states` table with CRUD operations and sellable filtering.

**Why**: Product states define lifecycle stages (semilla, germinado, trasplantado, listo_para_venta). Repository provides lookup by code and filtering for sales workflows (only sellable states).

**Context**: Master data table for product lifecycle. Critical for sales filtering and monthly reconciliation (only "listo_para_venta" generates revenue).

## Acceptance Criteria

- [ ] **AC1**: `ProductStateRepository` class inherits from `AsyncRepository[ProductState]`
- [ ] **AC2**: Implements `get_by_code(code: str)` method with unique constraint validation
- [ ] **AC3**: Implements `get_sellable_states()` for sales workflows (is_sellable=true)
- [ ] **AC4**: Implements `get_all_ordered()` returning states in sort_order
- [ ] **AC5**: Query performance: <10ms for all queries (small lookup table)

## Technical Implementation Notes

### Architecture
- **Layer**: Infrastructure (Repository)
- **Dependencies**: F006 (Database connection), DB018 (ProductState model)
- **Design Pattern**: Repository pattern, inherits AsyncRepository

### Code Hints
```python
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product_state import ProductState
from app.repositories.base_repository import AsyncRepository

class ProductStateRepository(AsyncRepository[ProductState]):
    """Repository for product state CRUD"""

    def __init__(self, session: AsyncSession):
        super().__init__(ProductState, session)

    async def get_by_code(self, code: str) -> Optional[ProductState]:
        """Get product state by unique code"""
        stmt = select(ProductState).where(ProductState.code == code)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_sellable_states(self) -> List[ProductState]:
        """Get states that are sellable (is_sellable=true)"""
        stmt = (
            select(ProductState)
            .where(ProductState.is_sellable == True)
            .order_by(ProductState.sort_order)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_all_ordered(self) -> List[ProductState]:
        """Get all states ordered by sort_order"""
        stmt = select(ProductState).order_by(ProductState.sort_order)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_ready_for_sale_state(self) -> Optional[ProductState]:
        """Get the 'listo_para_venta' state (convenience method)"""
        return await self.get_by_code("listo_para_venta")
```

### Testing Requirements

**Unit Tests**:
```python
@pytest.mark.asyncio
async def test_product_state_repo_get_by_code(db_session, sample_states):
    """Test state lookup by code"""
    repo = ProductStateRepository(db_session)
    state = await repo.get_by_code("listo_para_venta")

    assert state is not None
    assert state.code == "listo_para_venta"
    assert state.is_sellable == True

@pytest.mark.asyncio
async def test_product_state_repo_sellable(db_session, sample_states):
    """Test filtering sellable states only"""
    repo = ProductStateRepository(db_session)
    sellable = await repo.get_sellable_states()

    assert len(sellable) > 0
    assert all(s.is_sellable == True for s in sellable)
    # Should be ordered by sort_order
    orders = [s.sort_order for s in sellable]
    assert orders == sorted(orders)

@pytest.mark.asyncio
async def test_product_state_repo_all_ordered(db_session, sample_states):
    """Test retrieving all states in order"""
    repo = ProductStateRepository(db_session)
    states = await repo.get_all_ordered()

    # Should be ordered by sort_order
    orders = [s.sort_order for s in states]
    assert orders == sorted(orders)

@pytest.mark.asyncio
async def test_product_state_repo_ready_for_sale(db_session, sample_states):
    """Test convenience method for ready-for-sale state"""
    repo = ProductStateRepository(db_session)
    ready_state = await repo.get_ready_for_sale_state()

    assert ready_state is not None
    assert ready_state.code == "listo_para_venta"
    assert ready_state.is_sellable == True
```

**Coverage Target**: ≥85%

### Performance Expectations
- All queries: <10ms (small lookup table, ~10 rows)
- Sorted queries: <5ms (indexed sort_order column)

## Handover Briefing

**For the next developer:**
- **Context**: Master data defining product lifecycle stages. Critical for sales filtering
- **Key decisions**:
  - is_sellable flag separates growing vs. ready-for-sale inventory
  - sort_order defines UI display order (semilla → germinado → trasplantado → listo_para_venta)
  - Code is unique identifier (e.g., "listo_para_venta", "germinado")
  - Only "listo_para_venta" generates revenue in monthly reconciliation
- **Known limitations**:
  - No active/inactive flag (assumes all states always active)
  - States are hard-coded in migration (not user-configurable)
- **Next steps**: R016 (StockBatchRepository) uses states for inventory filtering
- **Questions to validate**:
  - Should states be cached in Redis?
  - Do we need custom state transitions (workflow engine)?

## Definition of Done Checklist

- [ ] Code written following AsyncRepository pattern
- [ ] Unit tests pass (≥85% coverage)
- [ ] Sellable filtering tested
- [ ] Sort order tested
- [ ] Linting passes (ruff check)
- [ ] Type hints validated (mypy)
- [ ] PR reviewed (2+ approvals)
- [ ] Integration test with DB018 model
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
