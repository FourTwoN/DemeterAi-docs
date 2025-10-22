# Price List Management - Detailed Flow

## Purpose

Shows the detailed flow for managing price list entries that combine packaging catalog items with
product categories, including pricing, SKU management, and logistics information.

## Scope

- **Level**: Implementation detail
- **Audience**: Backend developers, API designers
- **Detail**: Complete flow for price_list table management
- **Mermaid Version**: v11.3.0+

## What It Represents

Complete CRUD flow for `price_list` table:

1. **Create**: Combine packaging + category with pricing
2. **Read**: List and filter price entries
3. **Update**: Modify prices, SKUs, availability
4. **Delete**: Remove price entries (with constraints)

## Database Schema

### price_list Table

```sql
CREATE TABLE price_list (
    id SERIAL PRIMARY KEY,
    packaging_catalog_id INT NOT NULL REFERENCES packaging_catalog(id) ON DELETE RESTRICT,
    product_categories_id INT NOT NULL REFERENCES product_categories(id) ON DELETE RESTRICT,
    wholesale_unit_price INT NOT NULL,  -- Price in cents
    retail_unit_price INT NOT NULL,     -- Price in cents
    SKU VARCHAR(50) UNIQUE NOT NULL,
    unit_per_storage_box INT NOT NULL,
    wholesale_total_price_per_box INT NOT NULL,  -- Calculated field
    observations TEXT,
    availability VARCHAR(20) NOT NULL DEFAULT 'available',  -- available, out_of_stock, discontinued
    updated_at TIMESTAMP DEFAULT NOW(),
    discount_factor INT DEFAULT 0,  -- Percentage 0-100
    created_at TIMESTAMP DEFAULT NOW(),

    -- Constraints
    CONSTRAINT unique_packaging_category UNIQUE (packaging_catalog_id, product_categories_id),
    CONSTRAINT retail_gte_wholesale CHECK (retail_unit_price >= wholesale_unit_price),
    CONSTRAINT positive_prices CHECK (wholesale_unit_price > 0 AND retail_unit_price > 0),
    CONSTRAINT positive_units CHECK (unit_per_storage_box > 0),
    CONSTRAINT valid_discount CHECK (discount_factor >= 0 AND discount_factor <= 100),
    CONSTRAINT valid_availability CHECK (availability IN ('available', 'out_of_stock', 'discontinued'))
);

-- Indexes
CREATE INDEX idx_price_list_packaging ON price_list(packaging_catalog_id);
CREATE INDEX idx_price_list_category ON price_list(product_categories_id);
CREATE INDEX idx_price_list_sku ON price_list(SKU);
CREATE INDEX idx_price_list_availability ON price_list(availability);

-- Trigger to auto-calculate total price
CREATE OR REPLACE FUNCTION calculate_total_price_per_box()
RETURNS TRIGGER AS $$
BEGIN
    NEW.wholesale_total_price_per_box := NEW.wholesale_unit_price * NEW.unit_per_storage_box;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_calculate_total_price
BEFORE INSERT OR UPDATE OF wholesale_unit_price, unit_per_storage_box
ON price_list
FOR EACH ROW
EXECUTE FUNCTION calculate_total_price_per_box();
```

## CREATE Price List Entry

### Business Rules

1. **Unique Combination**: Each packaging + category combo can only exist once
2. **Price Validation**:
    - Both prices must be > 0
    - Retail price >= Wholesale price
    - Prices stored in cents (integer) to avoid floating-point errors
3. **SKU Generation**: Auto-generate if not provided
    - Pattern: `{CATEGORY_CODE}-{PACKAGING_SKU}`
    - Example: `CACT-R7-BLK`, `SUCC-R10-WHT`
4. **Auto-calculation**: `wholesale_total_price_per_box` = unit_price × units_per_box

### SQL - Create Price List Entry

```sql
-- Validation: Check packaging exists
SELECT id, sku FROM packaging_catalog WHERE id = $1;

-- Validation: Check category exists
SELECT id, code FROM product_categories WHERE id = $2;

-- Validation: Check unique combination
SELECT id FROM price_list
WHERE packaging_catalog_id = $1 AND product_categories_id = $2;
-- Must return empty

-- Insert price list entry
INSERT INTO price_list (
    packaging_catalog_id,
    product_categories_id,
    wholesale_unit_price,
    retail_unit_price,
    SKU,
    unit_per_storage_box,
    wholesale_total_price_per_box,
    observations,
    availability,
    discount_factor
) VALUES (
    $1,  -- packaging_catalog_id
    $2,  -- product_categories_id
    $3,  -- wholesale_unit_price (cents)
    $4,  -- retail_unit_price (cents)
    $5,  -- SKU
    $6,  -- unit_per_storage_box
    $3 * $6,  -- wholesale_total_price_per_box (auto-calculated)
    $7,  -- observations
    $8,  -- availability
    $9   -- discount_factor
)
RETURNING id, SKU, wholesale_unit_price, retail_unit_price, created_at;
```

### API Endpoint - Create

```python
@router.post("/api/admin/price-list")
async def create_price_list_entry(
    request: CreatePriceListRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
) -> PriceListResponse:
    """
    Create new price list entry

    Args:
        request: Price list data

    Returns:
        Created price list entry

    Raises:
        400: Validation error, references not found
        409: Duplicate combination or SKU
    """
    # Validate packaging exists
    packaging = await db.get(PackagingCatalog, request.packaging_catalog_id)
    if not packaging:
        raise HTTPException(400, "Packaging not found")

    # Validate category exists
    category = await db.get(ProductCategory, request.product_categories_id)
    if not category:
        raise HTTPException(400, "Product category not found")

    # Check unique combination
    existing_combo = await db.execute(
        select(PriceList).where(
            and_(
                PriceList.packaging_catalog_id == request.packaging_catalog_id,
                PriceList.product_categories_id == request.product_categories_id
            )
        )
    )
    if existing_combo.scalar_one_or_none():
        raise HTTPException(
            409,
            f"Price entry already exists for {category.name} + {packaging.name}"
        )

    # Validate prices
    if request.wholesale_unit_price <= 0 or request.retail_unit_price <= 0:
        raise HTTPException(400, "Prices must be positive")

    if request.retail_unit_price < request.wholesale_unit_price:
        raise HTTPException(400, "Retail price cannot be less than wholesale price")

    # Validate units per box
    if request.unit_per_storage_box <= 0:
        raise HTTPException(400, "Units per box must be positive")

    # Validate discount factor
    if request.discount_factor < 0 or request.discount_factor > 100:
        raise HTTPException(400, "Discount factor must be between 0 and 100")

    # Auto-generate SKU if not provided
    if not request.SKU:
        request.SKU = generate_price_list_sku(
            category_code=category.code,
            packaging_sku=packaging.sku
        )

    # Check SKU uniqueness
    existing_sku = await db.execute(
        select(PriceList).where(PriceList.SKU == request.SKU)
    )
    if existing_sku.scalar_one_or_none():
        raise HTTPException(409, f"SKU {request.SKU} already exists")

    # Calculate total price per box
    wholesale_total_price_per_box = request.wholesale_unit_price * request.unit_per_storage_box

    # Create price list entry
    price_entry = PriceList(
        packaging_catalog_id=request.packaging_catalog_id,
        product_categories_id=request.product_categories_id,
        wholesale_unit_price=request.wholesale_unit_price,
        retail_unit_price=request.retail_unit_price,
        SKU=request.SKU,
        unit_per_storage_box=request.unit_per_storage_box,
        wholesale_total_price_per_box=wholesale_total_price_per_box,
        observations=request.observations,
        availability=request.availability or 'available',
        discount_factor=request.discount_factor or 0
    )

    db.add(price_entry)
    await db.commit()
    await db.refresh(price_entry)

    # Load relationships for response
    await db.refresh(price_entry, ['packaging', 'category'])

    # Audit log
    await create_audit_log(
        user_id=current_user.id,
        action="create_price_list",
        entity_type="price_list",
        entity_id=price_entry.id,
        details={
            "SKU": price_entry.SKU,
            "packaging": packaging.name,
            "category": category.name,
            "wholesale_price": request.wholesale_unit_price / 100,  # Display in dollars
            "retail_price": request.retail_unit_price / 100
        }
    )

    return PriceListResponse.from_orm(price_entry)


def generate_price_list_sku(category_code: str, packaging_sku: str) -> str:
    """
    Generate price list SKU

    Pattern: {CATEGORY_CODE}-{PACKAGING_SKU}

    Examples:
        CACT-MAC-R7-BLK (Cactus + Maceta R7 Black)
        SUCC-MAC-R10-WHT (Suculenta + Maceta R10 White)
    """
    return f"{category_code}-{packaging_sku}"
```

## READ Price List

### SQL - List Price List Entries

```sql
-- List all price list entries with full details
SELECT
    pl.id,
    pl.SKU,
    pl.wholesale_unit_price,
    pl.retail_unit_price,
    pl.unit_per_storage_box,
    pl.wholesale_total_price_per_box,
    pl.availability,
    pl.discount_factor,
    pl.observations,
    pl.updated_at,
    pl.created_at,
    -- Packaging details
    pc.id as packaging_id,
    pc.sku as packaging_sku,
    pc.name as packaging_name,
    pc.volume_liters,
    pc.diameter_cm,
    pc.height_cm,
    pt.name as packaging_type,
    pcol.name as packaging_color,
    pcol.hex_color,
    -- Category details
    pcat.id as category_id,
    pcat.code as category_code,
    pcat.name as category_name
FROM price_list pl
JOIN packaging_catalog pc ON pl.packaging_catalog_id = pc.id
JOIN packaging_types pt ON pc.packaging_type_id = pt.id
JOIN packaging_colors pcol ON pc.packaging_color_id = pcol.id
JOIN product_categories pcat ON pl.product_categories_id = pcat.id
WHERE
    ($1::int IS NULL OR pl.product_categories_id = $1)  -- Filter by category
    AND ($2::int IS NULL OR pl.packaging_catalog_id = $2)  -- Filter by packaging
    AND ($3::varchar IS NULL OR pl.availability = $3)  -- Filter by availability
    AND ($4::varchar IS NULL OR pl.SKU ILIKE '%' || $4 || '%')  -- Search SKU
    AND ($5::int IS NULL OR pl.wholesale_unit_price >= $5)  -- Min wholesale price
    AND ($6::int IS NULL OR pl.wholesale_unit_price <= $6)  -- Max wholesale price
ORDER BY
    pcat.code,
    pc.diameter_cm,
    pcol.code
LIMIT $7 OFFSET $8;

-- Count total for pagination
SELECT COUNT(*) FROM price_list pl
WHERE ... (same filters);
```

### API Endpoint - List

```python
@router.get("/api/admin/price-list")
async def list_price_list(
    category_id: Optional[int] = None,
    packaging_id: Optional[int] = None,
    availability: Optional[str] = None,
    search_sku: Optional[str] = None,
    min_wholesale_price: Optional[int] = None,  # In cents
    max_wholesale_price: Optional[int] = None,  # In cents
    page: int = 1,
    page_size: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_authenticated)
) -> PriceListListResponse:
    """
    List price list entries with filters

    Query params:
        category_id: Filter by product category
        packaging_id: Filter by packaging
        availability: Filter by availability status
        search_sku: Search in SKU
        min_wholesale_price: Min wholesale price (cents)
        max_wholesale_price: Max wholesale price (cents)
        page: Page number (1-indexed)
        page_size: Items per page (max 100)

    Returns:
        Paginated list of price entries with full details
    """
    # Build query
    query = (
        select(PriceList)
        .join(PackagingCatalog)
        .join(ProductCategory)
        .options(
            selectinload(PriceList.packaging).selectinload(PackagingCatalog.type),
            selectinload(PriceList.packaging).selectinload(PackagingCatalog.color),
            selectinload(PriceList.category)
        )
    )

    # Apply filters
    if category_id:
        query = query.where(PriceList.product_categories_id == category_id)
    if packaging_id:
        query = query.where(PriceList.packaging_catalog_id == packaging_id)
    if availability:
        query = query.where(PriceList.availability == availability)
    if search_sku:
        query = query.where(PriceList.SKU.ilike(f'%{search_sku}%'))
    if min_wholesale_price:
        query = query.where(PriceList.wholesale_unit_price >= min_wholesale_price)
    if max_wholesale_price:
        query = query.where(PriceList.wholesale_unit_price <= max_wholesale_price)

    # Count total
    count_query = select(func.count()).select_from(PriceList)
    # ... apply same filters
    total = await db.scalar(count_query)

    # Pagination
    offset = (page - 1) * page_size
    query = query.order_by(
        ProductCategory.code,
        PackagingCatalog.diameter_cm
    ).limit(page_size).offset(offset)

    result = await db.execute(query)
    items = result.scalars().all()

    return PriceListListResponse(
        items=[PriceListDetailResponse.from_orm(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size
    )
```

## UPDATE Price List Entry

### Business Rules

1. **Immutable Fields**:
    - `id`, `packaging_catalog_id`, `product_categories_id` cannot be changed
    - If combination needs change, delete and recreate

2. **Price Updates**:
    - Must maintain retail >= wholesale
    - Auto-recalculate total price per box

3. **SKU Updates**:
    - Can be changed (unlike packaging/product catalogs)
    - Must remain unique

### SQL - Update Price List Entry

```sql
-- Check impact: Is this used in any orders/quotes?
-- (Depends on system design - may want to track price history)

-- Update price list entry
UPDATE price_list
SET
    wholesale_unit_price = COALESCE($1, wholesale_unit_price),
    retail_unit_price = COALESCE($2, retail_unit_price),
    SKU = COALESCE($3, SKU),
    unit_per_storage_box = COALESCE($4, unit_per_storage_box),
    wholesale_total_price_per_box =
        COALESCE($1, wholesale_unit_price) * COALESCE($4, unit_per_storage_box),
    observations = COALESCE($5, observations),
    availability = COALESCE($6, availability),
    discount_factor = COALESCE($7, discount_factor),
    updated_at = NOW()
WHERE id = $8
RETURNING id, SKU, wholesale_unit_price, retail_unit_price, updated_at;
```

### API Endpoint - Update

```python
@router.put("/api/admin/price-list/{price_id}")
async def update_price_list_entry(
    price_id: int,
    request: UpdatePriceListRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
) -> PriceListUpdateResponse:
    """
    Update price list entry

    Args:
        price_id: Price list entry ID
        request: Updated data

    Returns:
        Updated price list entry

    Raises:
        404: Entry not found
        400: Validation error
        409: SKU already exists (if changed)
    """
    # Get existing entry
    price_entry = await db.get(PriceList, price_id)
    if not price_entry:
        raise HTTPException(404, "Price list entry not found")

    # Store old values for audit
    old_values = {
        "wholesale_unit_price": price_entry.wholesale_unit_price,
        "retail_unit_price": price_entry.retail_unit_price,
        "SKU": price_entry.SKU,
        "availability": price_entry.availability,
        "discount_factor": price_entry.discount_factor
    }

    # Validate prices if provided
    new_wholesale = request.wholesale_unit_price or price_entry.wholesale_unit_price
    new_retail = request.retail_unit_price or price_entry.retail_unit_price

    if new_wholesale <= 0 or new_retail <= 0:
        raise HTTPException(400, "Prices must be positive")

    if new_retail < new_wholesale:
        raise HTTPException(400, "Retail price cannot be less than wholesale price")

    # Validate SKU uniqueness if changed
    if request.SKU and request.SKU != price_entry.SKU:
        existing_sku = await db.execute(
            select(PriceList).where(PriceList.SKU == request.SKU)
        )
        if existing_sku.scalar_one_or_none():
            raise HTTPException(409, f"SKU {request.SKU} already exists")
        price_entry.SKU = request.SKU

    # Validate units per box
    if request.unit_per_storage_box:
        if request.unit_per_storage_box <= 0:
            raise HTTPException(400, "Units per box must be positive")
        price_entry.unit_per_storage_box = request.unit_per_storage_box

    # Validate discount factor
    if request.discount_factor is not None:
        if request.discount_factor < 0 or request.discount_factor > 100:
            raise HTTPException(400, "Discount factor must be between 0 and 100")
        price_entry.discount_factor = request.discount_factor

    # Update fields
    if request.wholesale_unit_price:
        price_entry.wholesale_unit_price = request.wholesale_unit_price
    if request.retail_unit_price:
        price_entry.retail_unit_price = request.retail_unit_price
    if request.observations is not None:
        price_entry.observations = request.observations
    if request.availability:
        price_entry.availability = request.availability

    # Recalculate total price per box
    price_entry.wholesale_total_price_per_box = (
        price_entry.wholesale_unit_price * price_entry.unit_per_storage_box
    )
    price_entry.updated_at = datetime.now()

    await db.commit()
    await db.refresh(price_entry)

    # Audit log
    await create_audit_log(
        user_id=current_user.id,
        action="update_price_list",
        entity_type="price_list",
        entity_id=price_entry.id,
        changes={
            "old": old_values,
            "new": {
                "wholesale_unit_price": price_entry.wholesale_unit_price,
                "retail_unit_price": price_entry.retail_unit_price,
                "SKU": price_entry.SKU,
                "availability": price_entry.availability,
                "discount_factor": price_entry.discount_factor
            }
        }
    )

    return PriceListUpdateResponse(
        price_entry=PriceListResponse.from_orm(price_entry),
        changes_applied=len([k for k, v in request.dict(exclude_unset=True).items() if v is not None])
    )
```

## DELETE Price List Entry

### Business Rules

1. **Check References**: Verify entry not used in:
    - Active quotes
    - Pending orders
    - Historical invoices (may allow delete depending on business rules)

2. **Soft Delete Option**: Consider soft delete for entries with history

### SQL - Delete Price List Entry

```sql
-- Check if used in quotes/orders
SELECT COUNT(*) FROM quotes WHERE price_list_id = $1;
SELECT COUNT(*) FROM order_items WHERE price_list_id = $1;

-- If no references: Hard delete
DELETE FROM price_list
WHERE id = $1
  AND NOT EXISTS (SELECT 1 FROM quotes WHERE price_list_id = $1)
  AND NOT EXISTS (SELECT 1 FROM order_items WHERE price_list_id = $1)
RETURNING id, SKU;

-- Alternative: Soft delete (if column exists)
UPDATE price_list
SET availability = 'discontinued',
    updated_at = NOW()
WHERE id = $1
RETURNING id, SKU;
```

### API Endpoint - Delete

```python
@router.delete("/api/admin/price-list/{price_id}")
async def delete_price_list_entry(
    price_id: int,
    force: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
) -> DeleteResponse:
    """
    Delete price list entry

    Args:
        price_id: Price list entry ID
        force: If true, mark as discontinued instead of deleting

    Returns:
        Deletion result

    Raises:
        404: Entry not found
        409: Entry has references (cannot delete)
    """
    # Get entry
    price_entry = await db.get(PriceList, price_id)
    if not price_entry:
        raise HTTPException(404, "Price list entry not found")

    # Check references (if quote/order system exists)
    # quote_refs = await db.scalar(
    #     select(func.count()).select_from(Quote).where(Quote.price_list_id == price_id)
    # )
    # order_refs = await db.scalar(
    #     select(func.count()).select_from(OrderItem).where(OrderItem.price_list_id == price_id)
    # )
    # total_refs = quote_refs + order_refs

    total_refs = 0  # Placeholder if no quote/order system yet

    if total_refs > 0 and not force:
        raise HTTPException(
            409,
            f"Cannot delete: referenced by {total_refs} quotes/orders. "
            f"Use force=true to mark as discontinued instead."
        )

    if force or total_refs > 0:
        # Soft delete: mark as discontinued
        price_entry.availability = 'discontinued'
        price_entry.updated_at = datetime.now()
        await db.commit()

        action = "discontinue_price_list"
        message = f"Price list entry {price_entry.SKU} marked as discontinued"
    else:
        # Hard delete
        sku = price_entry.SKU
        await db.delete(price_entry)
        await db.commit()

        action = "delete_price_list"
        message = f"Price list entry {sku} deleted successfully"

    # Audit log
    await create_audit_log(
        user_id=current_user.id,
        action=action,
        entity_type="price_list",
        entity_id=price_id,
        details={"SKU": price_entry.SKU if force else sku}
    )

    return DeleteResponse(
        success=True,
        message=message,
        deleted_id=price_id
    )
```

## Performance Considerations

### Indexing

```sql
-- Essential indexes (already defined in schema)
CREATE INDEX idx_price_list_packaging ON price_list(packaging_catalog_id);
CREATE INDEX idx_price_list_category ON price_list(product_categories_id);
CREATE INDEX idx_price_list_sku ON price_list(SKU);
CREATE INDEX idx_price_list_availability ON price_list(availability);

-- Composite index for common queries
CREATE INDEX idx_price_list_cat_avail ON price_list(product_categories_id, availability);
CREATE INDEX idx_price_list_price_range ON price_list(wholesale_unit_price, retail_unit_price);
```

### Caching

```python
# Cache price list entries (invalidate on changes)
@cache(expire=600)  # 10 minutes
async def get_price_list_cached(filters):
    return await list_price_list(**filters)

# Cache frequently accessed entries
@cache(expire=1800)  # 30 minutes
async def get_price_by_sku(sku: str):
    return await db.execute(
        select(PriceList).where(PriceList.SKU == sku)
    )
```

## Performance Targets

| Operation               | Target Time | Notes                |
|-------------------------|-------------|----------------------|
| List entries (50 items) | < 200ms     | With full joins      |
| Create entry            | < 100ms     | With validation      |
| Update entry            | < 100ms     | With recalculation   |
| Delete entry            | < 100ms     | With reference check |
| Search by SKU           | < 50ms      | Indexed lookup       |

## Request/Response Models

```python
class CreatePriceListRequest(BaseModel):
    packaging_catalog_id: int
    product_categories_id: int
    wholesale_unit_price: int  # In cents
    retail_unit_price: int  # In cents
    SKU: Optional[str] = None  # Auto-generated if not provided
    unit_per_storage_box: int
    observations: Optional[str] = None
    availability: Optional[str] = 'available'
    discount_factor: Optional[int] = 0

    @validator('wholesale_unit_price', 'retail_unit_price')
    def validate_positive(cls, v):
        if v <= 0:
            raise ValueError('Price must be positive')
        return v

    @validator('retail_unit_price')
    def validate_retail_gte_wholesale(cls, v, values):
        if 'wholesale_unit_price' in values and v < values['wholesale_unit_price']:
            raise ValueError('Retail price must be >= wholesale price')
        return v


class UpdatePriceListRequest(BaseModel):
    wholesale_unit_price: Optional[int] = None
    retail_unit_price: Optional[int] = None
    SKU: Optional[str] = None
    unit_per_storage_box: Optional[int] = None
    observations: Optional[str] = None
    availability: Optional[str] = None
    discount_factor: Optional[int] = None


class PriceListDetailResponse(BaseModel):
    id: int
    SKU: str
    wholesale_unit_price: int
    retail_unit_price: int
    unit_per_storage_box: int
    wholesale_total_price_per_box: int
    availability: str
    discount_factor: int
    observations: Optional[str]
    packaging_id: int
    packaging_name: str
    packaging_sku: str
    packaging_type: str
    packaging_volume: float
    packaging_dimensions: str  # "Ø7cm × 8cm"
    category_id: int
    category_name: str
    category_code: str
    updated_at: datetime
    created_at: datetime

    # Computed fields
    @property
    def wholesale_unit_price_display(self) -> float:
        return self.wholesale_unit_price / 100

    @property
    def retail_unit_price_display(self) -> float:
        return self.retail_unit_price / 100

    @property
    def wholesale_total_price_per_box_display(self) -> float:
        return self.wholesale_total_price_per_box / 100

    class Config:
        from_attributes = True
```

---

**Version**: 1.0
**Last Updated**: 2025-10-08
**Author**: DemeterAI Engineering Team
