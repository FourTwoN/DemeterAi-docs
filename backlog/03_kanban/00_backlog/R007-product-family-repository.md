# R007: Product Family Repository

## Metadata
- **Epic**: [epic-003-repositories.md](../../02_epics/epic-003-repositories.md)
- **Sprint**: Sprint-01
- **Status**: `backlog`
- **Priority**: `medium`
- **Complexity**: S (2 story points)
- **Area**: `repositories`
- **Assignee**: TBD
- **Dependencies**:
  - Blocks: [R008, S006]
  - Blocked by: [F006, F007, DB016, R006]

## Related Documentation
- **Engineering Plan**: [../../engineering_plan/backend/repository_layer.md](../../engineering_plan/backend/repository_layer.md)
- **Database ERD**: [../../database/database.mmd](../../database/database.mmd#L81-L87)
- **Architecture**: [../../engineering_plan/03_architecture_overview.md](../../engineering_plan/03_architecture_overview.md)

## Description

**What**: Implement repository class for `product_families` table with CRUD operations, category filtering, and scientific name search.

**Why**: Product families group related species (e.g., Echeveria, Sedum within Crassulaceae). Repository provides lookup by scientific name, category filtering for catalog, and hierarchy navigation.

**Context**: Middle level of 3-tier product hierarchy (category → family → product). Botanical taxonomy level for species grouping.

## Acceptance Criteria

- [ ] **AC1**: `ProductFamilyRepository` class inherits from `AsyncRepository[ProductFamily]`
- [ ] **AC2**: Implements `get_by_scientific_name(scientific_name: str)` for taxonomy lookup
- [ ] **AC3**: Implements `get_by_category_id(category_id: int)` with eager loading of category and products
- [ ] **AC4**: Implements `search_by_name(search_term: str)` for fuzzy search (ILIKE)
- [ ] **AC5**: Includes eager loading for category (joinedload) and products (selectinload)
- [ ] **AC6**: Query performance: <15ms for category filtering, <30ms for search

## Technical Implementation Notes

### Architecture
- **Layer**: Infrastructure (Repository)
- **Dependencies**: F006 (Database connection), DB016 (ProductFamily model), R006 (ProductCategoryRepository)
- **Design Pattern**: Repository pattern, inherits AsyncRepository

### Code Hints
```python
from typing import Optional, List
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product_family import ProductFamily
from app.repositories.base_repository import AsyncRepository

class ProductFamilyRepository(AsyncRepository[ProductFamily]):
    """Repository for product family CRUD and taxonomy queries"""

    def __init__(self, session: AsyncSession):
        super().__init__(ProductFamily, session)

    async def get_by_scientific_name(
        self,
        scientific_name: str
    ) -> Optional[ProductFamily]:
        """Get product family by scientific name"""
        stmt = (
            select(ProductFamily)
            .where(ProductFamily.scientific_name == scientific_name)
            .options(joinedload(ProductFamily.category))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_category_id(
        self,
        category_id: int,
        with_products: bool = False
    ) -> List[ProductFamily]:
        """Get all families in a category"""
        stmt = (
            select(ProductFamily)
            .where(ProductFamily.category_id == category_id)
            .options(joinedload(ProductFamily.category))
            .order_by(ProductFamily.name)
        )

        if with_products:
            stmt = stmt.options(selectinload(ProductFamily.products))

        result = await self.session.execute(stmt)
        return list(result.scalars().unique().all())

    async def search_by_name(
        self,
        search_term: str
    ) -> List[ProductFamily]:
        """Fuzzy search by name or scientific name (ILIKE)"""
        search_pattern = f"%{search_term}%"
        stmt = (
            select(ProductFamily)
            .where(
                or_(
                    ProductFamily.name.ilike(search_pattern),
                    ProductFamily.scientific_name.ilike(search_pattern)
                )
            )
            .options(joinedload(ProductFamily.category))
            .order_by(ProductFamily.name)
            .limit(50)  # Prevent excessive results
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().unique().all())

    async def get_with_full_hierarchy(
        self,
        family_id: int
    ) -> Optional[ProductFamily]:
        """Get family with category and all products"""
        stmt = (
            select(ProductFamily)
            .where(ProductFamily.id == family_id)
            .options(
                joinedload(ProductFamily.category),
                selectinload(ProductFamily.products)
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_popular_families(
        self,
        limit: int = 10
    ) -> List[dict]:
        """Get families with most products (for analytics/reporting)"""
        from sqlalchemy import func
        from app.models.product import Product

        stmt = (
            select(
                ProductFamily,
                func.count(Product.id).label("product_count")
            )
            .join(Product, isouter=True)
            .group_by(ProductFamily.id)
            .order_by(func.count(Product.id).desc())
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        families_with_counts = result.all()

        return [
            {
                "family": row[0],
                "product_count": row[1]
            }
            for row in families_with_counts
        ]
```

### Testing Requirements

**Unit Tests**:
```python
@pytest.mark.asyncio
async def test_product_family_repo_by_scientific_name(db_session, sample_family):
    """Test family lookup by scientific name"""
    repo = ProductFamilyRepository(db_session)
    family = await repo.get_by_scientific_name("Echeveria")

    assert family is not None
    assert family.scientific_name == "Echeveria"
    assert family.category is not None  # Eager loaded

@pytest.mark.asyncio
async def test_product_family_repo_by_category(db_session, families_by_category):
    """Test filtering families by category"""
    repo = ProductFamilyRepository(db_session)
    families = await repo.get_by_category_id(1, with_products=True)

    assert len(families) > 0
    for family in families:
        assert family.category_id == 1
        assert family.category is not None
        # Check eager loading
        assert isinstance(family.products, list)

@pytest.mark.asyncio
async def test_product_family_repo_search(db_session, families):
    """Test fuzzy search by name"""
    repo = ProductFamilyRepository(db_session)
    # Search for "echev" should match "Echeveria"
    results = await repo.search_by_name("echev")

    assert len(results) > 0
    assert any("echev" in f.name.lower() or "echev" in f.scientific_name.lower() for f in results)

@pytest.mark.asyncio
async def test_product_family_repo_full_hierarchy(db_session, family_with_products):
    """Test loading full hierarchy (category + products)"""
    repo = ProductFamilyRepository(db_session)
    family = await repo.get_with_full_hierarchy(1)

    assert family is not None
    assert family.category is not None
    assert len(family.products) > 0

@pytest.mark.asyncio
async def test_product_family_repo_popular(db_session, families_with_products):
    """Test popular families query (analytics)"""
    repo = ProductFamilyRepository(db_session)
    popular = await repo.get_popular_families(limit=5)

    assert len(popular) > 0
    # Should be sorted by product_count desc
    counts = [p["product_count"] for p in popular]
    assert counts == sorted(counts, reverse=True)
```

**Coverage Target**: ≥85%

### Performance Expectations
- get_by_scientific_name: <10ms (indexed column)
- get_by_category_id: <15ms for 30 families per category
- search_by_name: <30ms (ILIKE with LIMIT 50)
- get_popular_families: <50ms (GROUP BY with JOIN)

## Handover Briefing

**For the next developer:**
- **Context**: Middle level of product hierarchy. Botanical taxonomy for species grouping
- **Key decisions**:
  - Scientific name is unique (botanical standard)
  - Search supports both name and scientific_name (fuzzy ILIKE)
  - Limit search results to 50 to prevent performance issues
  - Popular families query useful for catalog homepage/analytics
- **Known limitations**:
  - Search is case-insensitive but not fuzzy matching (no Levenshtein)
  - No full-text search (consider adding if search becomes critical)
- **Next steps**: R008 (ProductRepository) completes product hierarchy
- **Questions to validate**:
  - Should scientific_name be indexed for search performance?
  - Do we need synonym support for common names?

## Definition of Done Checklist

- [ ] Code written following AsyncRepository pattern
- [ ] Unit tests pass (≥85% coverage)
- [ ] Fuzzy search tested with ILIKE
- [ ] Eager loading tested for category and products
- [ ] Popular families aggregation tested
- [ ] Linting passes (ruff check)
- [ ] Type hints validated (mypy)
- [ ] PR reviewed (2+ approvals)
- [ ] Integration test with DB016 model and R006
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
