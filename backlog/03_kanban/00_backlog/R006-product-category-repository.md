# R006: Product Category Repository

## Metadata
- **Epic**: [epic-003-repositories.md](../../02_epics/epic-003-repositories.md)
- **Sprint**: Sprint-01
- **Status**: `backlog`
- **Priority**: `medium`
- **Complexity**: XS (1 story point)
- **Area**: `repositories`
- **Assignee**: TBD
- **Dependencies**:
  - Blocks: [R007, S005]
  - Blocked by: [F006, F007, DB015]

## Related Documentation
- **Engineering Plan**: [../../engineering_plan/backend/repository_layer.md](../../engineering_plan/backend/repository_layer.md)
- **Database ERD**: [../../database/database.mmd](../../database/database.mmd#L75-L80)
- **Architecture**: [../../engineering_plan/03_architecture_overview.md](../../engineering_plan/03_architecture_overview.md)

## Description

**What**: Implement repository class for `product_categories` table with CRUD operations and hierarchy navigation.

**Why**: Product categories group plant families (e.g., Cactaceae, Crassulaceae). Repository provides lookup by code and navigation to child families for catalog browsing and analytics.

**Context**: Top level of 3-tier product hierarchy (category → family → product). Master data table for plant taxonomy organization.

## Acceptance Criteria

- [ ] **AC1**: `ProductCategoryRepository` class inherits from `AsyncRepository[ProductCategory]`
- [ ] **AC2**: Implements `get_by_code(code: str)` method with unique constraint validation
- [ ] **AC3**: Implements `get_with_families(category_id: int)` with eager loading of product_families
- [ ] **AC4**: Implements `get_all_active()` for catalog/analytics dropdown lists
- [ ] **AC5**: Query performance: <10ms for all queries (small master data table)

## Technical Implementation Notes

### Architecture
- **Layer**: Infrastructure (Repository)
- **Dependencies**: F006 (Database connection), DB015 (ProductCategory model)
- **Design Pattern**: Repository pattern, inherits AsyncRepository

### Code Hints
```python
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product_category import ProductCategory
from app.repositories.base_repository import AsyncRepository

class ProductCategoryRepository(AsyncRepository[ProductCategory]):
    """Repository for product category CRUD"""

    def __init__(self, session: AsyncSession):
        super().__init__(ProductCategory, session)

    async def get_by_code(self, code: str) -> Optional[ProductCategory]:
        """Get product category by unique code"""
        stmt = select(ProductCategory).where(ProductCategory.code == code)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_with_families(
        self,
        category_id: int
    ) -> Optional[ProductCategory]:
        """Get category with all product families eagerly loaded"""
        stmt = (
            select(ProductCategory)
            .where(ProductCategory.id == category_id)
            .options(selectinload(ProductCategory.product_families))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_active(self) -> List[ProductCategory]:
        """Get all categories (for dropdown lists)"""
        stmt = select(ProductCategory).order_by(ProductCategory.name)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_category_statistics(
        self,
        category_id: int
    ) -> dict:
        """Get statistics for a category (family count, product count)"""
        from sqlalchemy import func
        from app.models.product_family import ProductFamily
        from app.models.product import Product

        # Count families
        family_count_stmt = (
            select(func.count(ProductFamily.id))
            .where(ProductFamily.category_id == category_id)
        )
        family_count = await self.session.scalar(family_count_stmt)

        # Count products
        product_count_stmt = (
            select(func.count(Product.id))
            .join(ProductFamily)
            .where(ProductFamily.category_id == category_id)
        )
        product_count = await self.session.scalar(product_count_stmt)

        return {
            "category_id": category_id,
            "family_count": family_count or 0,
            "product_count": product_count or 0
        }
```

### Testing Requirements

**Unit Tests**:
```python
@pytest.mark.asyncio
async def test_product_category_repo_get_by_code(db_session, sample_category):
    """Test category lookup by code"""
    repo = ProductCategoryRepository(db_session)
    category = await repo.get_by_code("CACT")

    assert category is not None
    assert category.code == "CACT"
    assert category.name == "Cactaceae"

@pytest.mark.asyncio
async def test_product_category_repo_with_families(db_session, category_with_families):
    """Test eager loading of product families"""
    repo = ProductCategoryRepository(db_session)
    category = await repo.get_with_families(1)

    assert category is not None
    assert len(category.product_families) > 0
    # No N+1 query when accessing families
    for family in category.product_families:
        assert family.name is not None

@pytest.mark.asyncio
async def test_product_category_repo_get_all(db_session, categories):
    """Test retrieving all categories"""
    repo = ProductCategoryRepository(db_session)
    all_categories = await repo.get_all_active()

    assert len(all_categories) > 0
    # Should be ordered by name
    names = [cat.name for cat in all_categories]
    assert names == sorted(names)

@pytest.mark.asyncio
async def test_product_category_repo_statistics(db_session, category_with_products):
    """Test category statistics aggregation"""
    repo = ProductCategoryRepository(db_session)
    stats = await repo.get_category_statistics(1)

    assert stats["category_id"] == 1
    assert stats["family_count"] > 0
    assert stats["product_count"] > 0
```

**Coverage Target**: ≥85%

### Performance Expectations
- All queries: <10ms (small master data table)
- get_with_families: <20ms with eager loading
- get_category_statistics: <30ms (aggregation queries)

## Handover Briefing

**For the next developer:**
- **Context**: Top level of product hierarchy. Used for catalog organization and analytics grouping
- **Key decisions**:
  - Code is uppercase alphanumeric (e.g., CACT, CRAS, SUCC)
  - Name is human-readable (e.g., "Cactaceae", "Crassulaceae")
  - Description provides botanical context
  - Master data (rarely changes, good candidate for caching)
- **Known limitations**:
  - No active/inactive flag (assumes all categories always active)
  - No sorting order field (uses alphabetical by name)
- **Next steps**: R007 (ProductFamilyRepository) links to this
- **Questions to validate**:
  - Should categories be cached in Redis for performance?
  - Do we need audit timestamps (created_at, updated_at)?

## Definition of Done Checklist

- [ ] Code written following AsyncRepository pattern
- [ ] Unit tests pass (≥85% coverage)
- [ ] Eager loading tested for product_families
- [ ] Statistics aggregation tested
- [ ] Linting passes (ruff check)
- [ ] Type hints validated (mypy)
- [ ] PR reviewed (2+ approvals)
- [ ] Integration test with DB015 model
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
