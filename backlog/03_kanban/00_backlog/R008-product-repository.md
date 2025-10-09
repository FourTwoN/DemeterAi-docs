# R008: Product Repository

## Metadata
- **Epic**: [epic-003-repositories.md](../../02_epics/epic-003-repositories.md)
- **Sprint**: Sprint-01
- **Status**: `backlog`
- **Priority**: `high`
- **Complexity**: M (3 story points)
- **Area**: `repositories`
- **Assignee**: TBD
- **Dependencies**:
  - Blocks: [R016, R024, S007]
  - Blocked by: [F006, F007, DB017, R007]

## Related Documentation
- **Engineering Plan**: [../../engineering_plan/backend/repository_layer.md](../../engineering_plan/backend/repository_layer.md)
- **Database ERD**: [../../database/database.mmd](../../database/database.mmd#L88-L96)
- **Architecture**: [../../engineering_plan/03_architecture_overview.md](../../engineering_plan/03_architecture_overview.md)

## Description

**What**: Implement repository class for `products` table (Level 3 of product hierarchy) with CRUD operations, SKU lookup, and search.

**Why**: Products are the core inventory items (individual species/varieties). Repository provides fast SKU lookup for barcode scanning, search for catalog browsing, and hierarchy navigation for taxonomy.

**Context**: Leaf level of product hierarchy. Each product links to stock batches, ML classifications, and pricing. SKU must be unique for inventory tracking.

## Acceptance Criteria

- [ ] **AC1**: `ProductRepository` class inherits from `AsyncRepository[Product]`
- [ ] **AC2**: Implements `get_by_sku(sku: str)` method with unique index (critical for barcode scanning)
- [ ] **AC3**: Implements `search_products(search_term: str)` for catalog browsing (name + scientific name)
- [ ] **AC4**: Implements `get_by_family_id(family_id: int)` with eager loading of family → category
- [ ] **AC5**: Implements `get_with_sample_images(product_id: int)` loading product images
- [ ] **AC6**: Includes eager loading for family, category, and sample_images
- [ ] **AC7**: Query performance: SKU lookup <10ms, search <30ms

## Technical Implementation Notes

### Architecture
- **Layer**: Infrastructure (Repository)
- **Dependencies**: F006 (Database connection), DB017 (Product model), R007 (ProductFamilyRepository)
- **Design Pattern**: Repository pattern, inherits AsyncRepository

### Code Hints
```python
from typing import Optional, List
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product
from app.repositories.base_repository import AsyncRepository

class ProductRepository(AsyncRepository[Product]):
    """Repository for product CRUD with SKU lookup and search"""

    def __init__(self, session: AsyncSession):
        super().__init__(Product, session)

    async def get_by_sku(self, sku: str) -> Optional[Product]:
        """Get product by SKU (barcode scanning workflow)"""
        stmt = (
            select(Product)
            .where(Product.sku == sku)
            .options(
                joinedload(Product.family)
                .joinedload(ProductFamily.category)
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def search_products(
        self,
        search_term: str,
        family_id: Optional[int] = None
    ) -> List[Product]:
        """Fuzzy search by common or scientific name"""
        search_pattern = f"%{search_term}%"
        stmt = (
            select(Product)
            .where(
                or_(
                    Product.common_name.ilike(search_pattern),
                    Product.scientific_name.ilike(search_pattern),
                    Product.sku.ilike(search_pattern)
                )
            )
            .options(
                joinedload(Product.family)
                .joinedload(ProductFamily.category)
            )
            .order_by(Product.common_name)
            .limit(100)
        )

        if family_id:
            stmt = stmt.where(Product.family_id == family_id)

        result = await self.session.execute(stmt)
        return list(result.scalars().unique().all())

    async def get_by_family_id(
        self,
        family_id: int,
        with_sample_images: bool = False
    ) -> List[Product]:
        """Get all products in a family"""
        stmt = (
            select(Product)
            .where(Product.family_id == family_id)
            .options(
                joinedload(Product.family)
                .joinedload(ProductFamily.category)
            )
            .order_by(Product.common_name)
        )

        if with_sample_images:
            stmt = stmt.options(selectinload(Product.sample_images))

        result = await self.session.execute(stmt)
        return list(result.scalars().unique().all())

    async def get_with_sample_images(
        self,
        product_id: int
    ) -> Optional[Product]:
        """Get product with all sample images loaded"""
        stmt = (
            select(Product)
            .where(Product.id == product_id)
            .options(
                joinedload(Product.family)
                .joinedload(ProductFamily.category),
                selectinload(Product.sample_images)
                .joinedload(ProductSampleImage.s3_image)
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_products_needing_images(
        self,
        limit: int = 50
    ) -> List[Product]:
        """Get products without sample images (for photography workflow)"""
        stmt = (
            select(Product)
            .outerjoin(ProductSampleImage)
            .where(ProductSampleImage.id == None)
            .options(
                joinedload(Product.family)
                .joinedload(ProductFamily.category)
            )
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().unique().all())

    async def get_catalog_products(
        self,
        category_id: Optional[int] = None,
        family_id: Optional[int] = None
    ) -> List[Product]:
        """Get products for catalog display (with images, active only)"""
        stmt = (
            select(Product)
            .options(
                joinedload(Product.family)
                .joinedload(ProductFamily.category),
                selectinload(Product.sample_images)
                .where(ProductSampleImage.is_primary == True)
            )
            .order_by(Product.common_name)
        )

        if category_id:
            stmt = stmt.join(ProductFamily).where(ProductFamily.category_id == category_id)
        if family_id:
            stmt = stmt.where(Product.family_id == family_id)

        result = await self.session.execute(stmt)
        return list(result.scalars().unique().all())
```

### Testing Requirements

**Unit Tests**:
```python
@pytest.mark.asyncio
async def test_product_repo_get_by_sku(db_session, sample_product):
    """Test SKU lookup (barcode scanning)"""
    repo = ProductRepository(db_session)
    product = await repo.get_by_sku("ECHEV-001")

    assert product is not None
    assert product.sku == "ECHEV-001"
    assert product.family is not None
    assert product.family.category is not None

@pytest.mark.asyncio
async def test_product_repo_search(db_session, products):
    """Test fuzzy search by name/SKU"""
    repo = ProductRepository(db_session)
    results = await repo.search_products("echev")

    assert len(results) > 0
    # All results should match search term
    assert all(
        "echev" in p.common_name.lower() or
        "echev" in p.scientific_name.lower() or
        "echev" in p.sku.lower()
        for p in results
    )

@pytest.mark.asyncio
async def test_product_repo_by_family(db_session, family_with_products):
    """Test filtering products by family"""
    repo = ProductRepository(db_session)
    products = await repo.get_by_family_id(1, with_sample_images=True)

    assert len(products) > 0
    for p in products:
        assert p.family_id == 1
        assert isinstance(p.sample_images, list)

@pytest.mark.asyncio
async def test_product_repo_with_images(db_session, product_with_images):
    """Test loading product with sample images"""
    repo = ProductRepository(db_session)
    product = await repo.get_with_sample_images(1)

    assert product is not None
    assert len(product.sample_images) > 0
    for img in product.sample_images:
        assert img.s3_image is not None

@pytest.mark.asyncio
async def test_product_repo_needing_images(db_session, products_no_images):
    """Test finding products without images"""
    repo = ProductRepository(db_session)
    products = await repo.get_products_needing_images(limit=10)

    assert len(products) > 0
    # Verify no images attached
    for p in products:
        assert len(p.sample_images) == 0
```

**Coverage Target**: ≥85%

### Performance Expectations
- SKU lookup: <10ms (unique index on sku)
- search_products: <30ms (ILIKE with LIMIT 100)
- get_by_family_id: <20ms for 50 products per family
- get_with_sample_images: <40ms (multiple eager loads)

## Handover Briefing

**For the next developer:**
- **Context**: Leaf level of product hierarchy. Core inventory entity linked to stock, ML, pricing
- **Key decisions**:
  - SKU unique globally (barcode scanning requirement)
  - Search includes common_name, scientific_name, AND sku
  - Sample images loaded separately (avoid N+1 in catalog)
  - custom_attributes is JSONB for flexible metadata
- **Known limitations**:
  - Search is ILIKE (not full-text search)
  - No product variants (size/color handled via product_sizes/packaging)
- **Next steps**: R016 (StockBatchRepository) links products to inventory
- **Questions to validate**:
  - Should SKU be auto-generated or manual input?
  - Do we need product versioning/history?

## Definition of Done Checklist

- [ ] Code written following AsyncRepository pattern
- [ ] Unit tests pass (≥85% coverage)
- [ ] SKU lookup tested with unique constraint
- [ ] Fuzzy search tested with ILIKE
- [ ] Sample images eager loading tested
- [ ] Linting passes (ruff check)
- [ ] Type hints validated (mypy)
- [ ] PR reviewed (2+ approvals)
- [ ] Integration test with DB017, R007
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
