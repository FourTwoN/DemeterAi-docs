# Product Catalog CRUD Operations - Detailed Flow

## Purpose

Shows the detailed flow for managing the product catalog hierarchy: Categories → Families →
Products, with complete CRUD operations for each level.

## Scope

- **Level**: Implementation detail
- **Audience**: Backend developers, API designers
- **Detail**: Complete flow for three-level product hierarchy
- **Mermaid Version**: v11.3.0+

## What It Represents

Complete CRUD flow for product catalog structure:

1. **Product Categories**: Top level (cactus, suculenta, injerto)
2. **Product Families**: Mid level (belongs to category)
3. **Products**: Bottom level (individual plants)

## Database Schema

### Three-Level Hierarchy

```sql
-- Level 1: Categories
CREATE TABLE product_categories (
    id SERIAL PRIMARY KEY,
    code VARCHAR(20) UNIQUE NOT NULL,  -- CACT, SUCC, INJT
    name VARCHAR(100) NOT NULL,        -- Cactus, Suculenta, Injerto
    description TEXT,
    display_order INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Level 2: Families (belongs to category)
CREATE TABLE product_families (
    id SERIAL PRIMARY KEY,
    category_id INT NOT NULL REFERENCES product_categories(id) ON DELETE RESTRICT,
    name VARCHAR(100) NOT NULL,
    scientific_name VARCHAR(200),
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(category_id, name)  -- Unique name within category
);

-- Level 3: Products (belongs to family)
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    family_id INT NOT NULL REFERENCES product_families(id) ON DELETE RESTRICT,
    sku VARCHAR(50) UNIQUE NOT NULL,
    common_name VARCHAR(100) NOT NULL,
    scientific_name VARCHAR(200),
    description TEXT,
    min_temperature_c INT,
    max_temperature_c INT,
    sunlight_requirement VARCHAR(50),  -- full_sun, partial_shade, shade
    watering_frequency VARCHAR(50),    -- high, medium, low
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_product_families_category ON product_families(category_id);
CREATE INDEX idx_products_family ON products(family_id);
CREATE INDEX idx_products_sku ON products(sku);
CREATE INDEX idx_products_common_name ON products(common_name);
```

## Product Categories CRUD

### CREATE Category

```sql
-- Insert new category
INSERT INTO product_categories (code, name, description, display_order)
VALUES ($1, $2, $3, $4)
RETURNING id, code, name, created_at;
```

**API Endpoint**:

```python
@router.post("/api/admin/product-categories")
async def create_category(
    request: CreateCategoryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
) -> CategoryResponse:
    """
    Create new product category

    Args:
        request: Category data (code, name, description)

    Returns:
        Created category

    Raises:
        400: Invalid data
        409: Code already exists
    """
    # Validate code format (uppercase, max 4 chars)
    if not request.code.isupper() or len(request.code) > 4:
        raise HTTPException(400, "Code must be uppercase, max 4 characters")

    # Check uniqueness
    existing = await db.execute(
        select(ProductCategory).where(ProductCategory.code == request.code)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(409, f"Category code {request.code} already exists")

    # Create category
    category = ProductCategory(
        code=request.code,
        name=request.name,
        description=request.description,
        display_order=request.display_order or 0
    )

    db.add(category)
    await db.commit()
    await db.refresh(category)

    await create_audit_log(
        user_id=current_user.id,
        action="create_category",
        entity_type="product_categories",
        entity_id=category.id,
        details={"code": category.code, "name": category.name}
    )

    return CategoryResponse.from_orm(category)
```

### READ Categories

```sql
-- List all categories with family counts
SELECT
    pc.id,
    pc.code,
    pc.name,
    pc.description,
    pc.display_order,
    COUNT(pf.id) as family_count,
    pc.created_at,
    pc.updated_at
FROM product_categories pc
LEFT JOIN product_families pf ON pc.id = pf.category_id
GROUP BY pc.id
ORDER BY pc.display_order, pc.name;
```

**API Endpoint**:

```python
@router.get("/api/admin/product-categories")
async def list_categories(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_authenticated)
) -> List[CategoryWithCountsResponse]:
    """
    List all product categories with counts
    """
    query = """
        SELECT
            pc.*,
            COUNT(DISTINCT pf.id) as family_count,
            COUNT(DISTINCT p.id) as product_count
        FROM product_categories pc
        LEFT JOIN product_families pf ON pc.id = pf.category_id
        LEFT JOIN products p ON pf.id = p.family_id
        GROUP BY pc.id
        ORDER BY pc.display_order, pc.name
    """

    result = await db.execute(text(query))
    rows = result.fetchall()

    return [CategoryWithCountsResponse(**row._mapping) for row in rows]
```

### UPDATE Category

```sql
UPDATE product_categories
SET
    name = COALESCE($1, name),
    description = COALESCE($2, description),
    display_order = COALESCE($3, display_order),
    updated_at = NOW()
WHERE id = $4
RETURNING *;
```

### DELETE Category

**Business Rule**: Cannot delete if has families.

```sql
-- Check if has families
SELECT COUNT(*) FROM product_families WHERE category_id = $1;

-- If count = 0, allow delete
DELETE FROM product_categories WHERE id = $1 AND NOT EXISTS (
    SELECT 1 FROM product_families WHERE category_id = $1
)
RETURNING id;
```

## Product Families CRUD

### CREATE Family

```sql
-- Insert new family
INSERT INTO product_families (category_id, name, scientific_name, description)
VALUES ($1, $2, $3, $4)
RETURNING id, category_id, name, created_at;
```

**API Endpoint**:

```python
@router.post("/api/admin/product-families")
async def create_family(
    request: CreateFamilyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
) -> FamilyResponse:
    """
    Create new product family

    Args:
        request: Family data (category_id, name, scientific_name)

    Returns:
        Created family

    Raises:
        400: Category not found
        409: Name already exists in category
    """
    # Validate category exists
    category = await db.get(ProductCategory, request.category_id)
    if not category:
        raise HTTPException(400, "Product category not found")

    # Check unique name within category
    existing = await db.execute(
        select(ProductFamily).where(
            and_(
                ProductFamily.category_id == request.category_id,
                ProductFamily.name == request.name
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            409,
            f"Family '{request.name}' already exists in category '{category.name}'"
        )

    # Create family
    family = ProductFamily(
        category_id=request.category_id,
        name=request.name,
        scientific_name=request.scientific_name,
        description=request.description
    )

    db.add(family)
    await db.commit()
    await db.refresh(family)

    await create_audit_log(
        user_id=current_user.id,
        action="create_family",
        entity_type="product_families",
        entity_id=family.id,
        details={"category_id": family.category_id, "name": family.name}
    )

    return FamilyResponse.from_orm(family)
```

### READ Families

```sql
-- List families by category with product counts
SELECT
    pf.id,
    pf.category_id,
    pf.name,
    pf.scientific_name,
    pf.description,
    pc.name as category_name,
    pc.code as category_code,
    COUNT(p.id) as product_count,
    pf.created_at,
    pf.updated_at
FROM product_families pf
JOIN product_categories pc ON pf.category_id = pc.id
LEFT JOIN products p ON pf.id = p.family_id
WHERE ($1::int IS NULL OR pf.category_id = $1)
GROUP BY pf.id, pc.id
ORDER BY pc.display_order, pc.name, pf.name;
```

**API Endpoint**:

```python
@router.get("/api/admin/product-families")
async def list_families(
    category_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_authenticated)
) -> List[FamilyWithCountsResponse]:
    """
    List product families, optionally filtered by category

    Query params:
        category_id: Filter by category
    """
    query = (
        select(
            ProductFamily,
            ProductCategory.name.label('category_name'),
            ProductCategory.code.label('category_code'),
            func.count(Product.id).label('product_count')
        )
        .join(ProductCategory)
        .outerjoin(Product)
        .group_by(ProductFamily.id, ProductCategory.id)
        .order_by(ProductCategory.display_order, ProductCategory.name, ProductFamily.name)
    )

    if category_id:
        query = query.where(ProductFamily.category_id == category_id)

    result = await db.execute(query)
    rows = result.all()

    return [
        FamilyWithCountsResponse(
            **row.ProductFamily.__dict__,
            category_name=row.category_name,
            category_code=row.category_code,
            product_count=row.product_count
        )
        for row in rows
    ]
```

### UPDATE Family

```sql
UPDATE product_families
SET
    name = COALESCE($1, name),
    scientific_name = COALESCE($2, scientific_name),
    description = COALESCE($3, description),
    updated_at = NOW()
WHERE id = $4
RETURNING *;
```

**Note**: Cannot change `category_id` after creation (would break product relationships).

### DELETE Family

**Business Rule**: Cannot delete if has products.

```sql
-- Check if has products
SELECT COUNT(*) FROM products WHERE family_id = $1;

-- If count = 0, allow delete
DELETE FROM product_families WHERE id = $1 AND NOT EXISTS (
    SELECT 1 FROM products WHERE family_id = $1
)
RETURNING id;
```

## Products CRUD

### CREATE Product

```sql
-- Insert new product
INSERT INTO products (
    family_id,
    sku,
    common_name,
    scientific_name,
    description,
    min_temperature_c,
    max_temperature_c,
    sunlight_requirement,
    watering_frequency
) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
RETURNING id, family_id, sku, common_name, created_at;
```

**API Endpoint**:

```python
@router.post("/api/admin/products")
async def create_product(
    request: CreateProductRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
) -> ProductResponse:
    """
    Create new product

    Args:
        request: Product data

    Returns:
        Created product

    Raises:
        400: Family not found, invalid data
        409: SKU already exists
    """
    # Validate family exists
    family = await db.get(ProductFamily, request.family_id)
    if not family:
        raise HTTPException(400, "Product family not found")

    # Check SKU uniqueness
    existing_sku = await db.execute(
        select(Product).where(Product.sku == request.sku)
    )
    if existing_sku.scalar_one_or_none():
        raise HTTPException(409, f"SKU {request.sku} already exists")

    # Validate temperature range
    if request.min_temperature_c and request.max_temperature_c:
        if request.min_temperature_c > request.max_temperature_c:
            raise HTTPException(400, "Min temperature cannot exceed max temperature")

    # Validate enum values
    valid_sunlight = ['full_sun', 'partial_shade', 'shade']
    if request.sunlight_requirement and request.sunlight_requirement not in valid_sunlight:
        raise HTTPException(400, f"Invalid sunlight requirement. Must be one of: {valid_sunlight}")

    valid_watering = ['high', 'medium', 'low']
    if request.watering_frequency and request.watering_frequency not in valid_watering:
        raise HTTPException(400, f"Invalid watering frequency. Must be one of: {valid_watering}")

    # Create product
    product = Product(
        family_id=request.family_id,
        sku=request.sku,
        common_name=request.common_name,
        scientific_name=request.scientific_name,
        description=request.description,
        min_temperature_c=request.min_temperature_c,
        max_temperature_c=request.max_temperature_c,
        sunlight_requirement=request.sunlight_requirement,
        watering_frequency=request.watering_frequency
    )

    db.add(product)
    await db.commit()
    await db.refresh(product)

    # Load relationships for response
    await db.refresh(product, ['family'])

    await create_audit_log(
        user_id=current_user.id,
        action="create_product",
        entity_type="products",
        entity_id=product.id,
        details={"sku": product.sku, "name": product.common_name}
    )

    return ProductResponse.from_orm(product)
```

### READ Products

```sql
-- List products with hierarchy info
SELECT
    p.id,
    p.family_id,
    p.sku,
    p.common_name,
    p.scientific_name,
    p.description,
    p.min_temperature_c,
    p.max_temperature_c,
    p.sunlight_requirement,
    p.watering_frequency,
    pf.name as family_name,
    pf.scientific_name as family_scientific_name,
    pc.id as category_id,
    pc.name as category_name,
    pc.code as category_code,
    p.created_at,
    p.updated_at
FROM products p
JOIN product_families pf ON p.family_id = pf.id
JOIN product_categories pc ON pf.category_id = pc.id
WHERE
    ($1::int IS NULL OR pc.id = $1)  -- Filter by category
    AND ($2::int IS NULL OR pf.id = $2)  -- Filter by family
    AND ($3::text IS NULL OR p.common_name ILIKE '%' || $3 || '%')  -- Search name
    AND ($4::text IS NULL OR p.sku ILIKE '%' || $4 || '%')  -- Search SKU
ORDER BY pc.display_order, pc.name, pf.name, p.common_name
LIMIT $5 OFFSET $6;
```

**API Endpoint**:

```python
@router.get("/api/admin/products")
async def list_products(
    category_id: Optional[int] = None,
    family_id: Optional[int] = None,
    search_name: Optional[str] = None,
    search_sku: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_authenticated)
) -> ProductListResponse:
    """
    List products with filters and pagination

    Query params:
        category_id: Filter by category
        family_id: Filter by family
        search_name: Search in common name
        search_sku: Search in SKU
        page: Page number (1-indexed)
        page_size: Items per page (max 100)
    """
    # Build query
    query = (
        select(Product)
        .join(ProductFamily)
        .join(ProductCategory)
        .options(
            selectinload(Product.family).selectinload(ProductFamily.category)
        )
    )

    # Apply filters
    if category_id:
        query = query.where(ProductCategory.id == category_id)
    if family_id:
        query = query.where(ProductFamily.id == family_id)
    if search_name:
        query = query.where(Product.common_name.ilike(f'%{search_name}%'))
    if search_sku:
        query = query.where(Product.sku.ilike(f'%{search_sku}%'))

    # Count total
    count_query = select(func.count()).select_from(Product).join(ProductFamily).join(ProductCategory)
    # ... apply same filters
    total = await db.scalar(count_query)

    # Pagination
    offset = (page - 1) * page_size
    query = query.order_by(
        ProductCategory.display_order,
        ProductCategory.name,
        ProductFamily.name,
        Product.common_name
    ).limit(page_size).offset(offset)

    result = await db.execute(query)
    items = result.scalars().all()

    return ProductListResponse(
        items=[ProductDetailResponse.from_orm(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size
    )
```

### UPDATE Product

```sql
UPDATE products
SET
    common_name = COALESCE($1, common_name),
    scientific_name = COALESCE($2, scientific_name),
    description = COALESCE($3, description),
    min_temperature_c = COALESCE($4, min_temperature_c),
    max_temperature_c = COALESCE($5, max_temperature_c),
    sunlight_requirement = COALESCE($6, sunlight_requirement),
    watering_frequency = COALESCE($7, watering_frequency),
    updated_at = NOW()
WHERE id = $8
RETURNING *;
```

**Note**:

- Cannot change `family_id` or `sku` after creation
- If SKU needs change, delete and recreate

### DELETE Product

**Business Rule**: Check if used in configurations or price lists.

```sql
-- Check if used in storage location configs
SELECT COUNT(*) FROM storage_location_config WHERE product_id = $1;

-- Check if family is used in price list
SELECT COUNT(*) FROM price_list pl
JOIN product_categories pc ON pl.product_categories_id = pc.id
JOIN product_families pf ON pf.category_id = pc.id
WHERE pf.id = (SELECT family_id FROM products WHERE id = $1);

-- If no references, allow delete
DELETE FROM products WHERE id = $1 AND NOT EXISTS (
    SELECT 1 FROM storage_location_config WHERE product_id = $1
)
RETURNING id;
```

## Hierarchical Queries

### Get Complete Product Hierarchy

```python
@router.get("/api/admin/products/hierarchy")
async def get_product_hierarchy(
    db: AsyncSession = Depends(get_db)
) -> ProductHierarchyResponse:
    """
    Get complete product catalog hierarchy

    Returns nested structure:
    [
        {
            "category": {...},
            "families": [
                {
                    "family": {...},
                    "products": [...]
                }
            ]
        }
    ]
    """
    # Query all data
    categories = await db.execute(
        select(ProductCategory).order_by(ProductCategory.display_order, ProductCategory.name)
    )
    categories = categories.scalars().all()

    result = []

    for category in categories:
        # Get families for category
        families = await db.execute(
            select(ProductFamily)
            .where(ProductFamily.category_id == category.id)
            .order_by(ProductFamily.name)
        )
        families = families.scalars().all()

        category_data = {
            "category": CategoryResponse.from_orm(category),
            "families": []
        }

        for family in families:
            # Get products for family
            products = await db.execute(
                select(Product)
                .where(Product.family_id == family.id)
                .order_by(Product.common_name)
            )
            products = products.scalars().all()

            category_data["families"].append({
                "family": FamilyResponse.from_orm(family),
                "products": [ProductResponse.from_orm(p) for p in products]
            })

        result.append(category_data)

    return ProductHierarchyResponse(hierarchy=result)
```

## Performance Considerations

### Indexing Strategy

```sql
-- Essential indexes
CREATE INDEX idx_product_families_category ON product_families(category_id);
CREATE INDEX idx_products_family ON products(family_id);
CREATE INDEX idx_products_sku ON products(sku);

-- For search
CREATE INDEX idx_products_common_name_trgm ON products USING gin(common_name gin_trgm_ops);
CREATE INDEX idx_products_scientific_name_trgm ON products USING gin(scientific_name gin_trgm_ops);

-- For filters
CREATE INDEX idx_products_sunlight ON products(sunlight_requirement);
CREATE INDEX idx_products_watering ON products(watering_frequency);
```

### Caching Strategy

```python
# Cache categories (rarely change)
@cache(expire=3600)  # 1 hour
async def get_categories_cached():
    return await db.execute(select(ProductCategory))

# Cache hierarchy (refresh on changes)
@cache(expire=1800)  # 30 minutes
async def get_hierarchy_cached():
    return await get_product_hierarchy()

# Invalidate on any catalog change
async def invalidate_catalog_cache():
    await cache.delete("categories")
    await cache.delete("hierarchy")
    await cache.delete_pattern("families:*")
    await cache.delete_pattern("products:*")
```

## Performance Targets

| Operation                | Target Time | Notes               |
|--------------------------|-------------|---------------------|
| List categories          | < 50ms      | Small table, cached |
| List families (all)      | < 100ms     | Moderate size       |
| List products (50 items) | < 200ms     | With filters, joins |
| Create product           | < 100ms     | With validation     |
| Get hierarchy            | < 300ms     | Full tree, cached   |
| Search products          | < 250ms     | With trigram index  |

## Request/Response Models

```python
class CreateCategoryRequest(BaseModel):
    code: str = Field(..., max_length=4, regex="^[A-Z]+$")
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    display_order: Optional[int] = 0


class CreateFamilyRequest(BaseModel):
    category_id: int
    name: str = Field(..., min_length=1, max_length=100)
    scientific_name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None


class CreateProductRequest(BaseModel):
    family_id: int
    sku: str = Field(..., min_length=1, max_length=50)
    common_name: str = Field(..., min_length=1, max_length=100)
    scientific_name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    min_temperature_c: Optional[int] = None
    max_temperature_c: Optional[int] = None
    sunlight_requirement: Optional[str] = None  # full_sun, partial_shade, shade
    watering_frequency: Optional[str] = None    # high, medium, low


class ProductDetailResponse(BaseModel):
    id: int
    family_id: int
    sku: str
    common_name: str
    scientific_name: Optional[str]
    description: Optional[str]
    min_temperature_c: Optional[int]
    max_temperature_c: Optional[int]
    sunlight_requirement: Optional[str]
    watering_frequency: Optional[str]
    family_name: str
    family_scientific_name: Optional[str]
    category_id: int
    category_name: str
    category_code: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
```

---

**Version**: 1.0
**Last Updated**: 2025-10-08
**Author**: DemeterAI Engineering Team
