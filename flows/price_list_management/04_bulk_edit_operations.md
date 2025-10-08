# Bulk Edit Operations - Detailed Flow

## Purpose

Shows the detailed flow for bulk operations on price list entries, including price adjustments, availability changes, and discount factor updates with preview and confirmation.

## Scope

- **Level**: Implementation detail
- **Audience**: Backend developers, API designers
- **Detail**: Complete flow for batch updates with filters and preview
- **Mermaid Version**: v11.3.0+

## What It Represents

Complete bulk operations flow:
1. **Bulk Price Update**: Increase/decrease prices by percentage
2. **Bulk Availability Change**: Change status for filtered items
3. **Bulk Discount Update**: Apply discount factors
4. **Preview & Confirm**: Show impact before applying

## Business Rules

### Critical Principles

1. **Historical Data Preservation**:
   - Bulk changes only affect current price list
   - Historical sales, quotes, and orders remain unchanged
   - Price changes apply to new transactions only

2. **Filter-Based Operations**:
   - Apply changes to filtered subsets
   - Preview shows exact items affected
   - Confirmation required for operations affecting > 100 items

3. **Transaction Integrity**:
   - All changes in single transaction
   - Rollback on any error
   - Audit trail for all operations

4. **Rate Limiting**:
   - Max 1000 items per operation
   - Max 10 bulk operations per user per hour
   - Admin override available

## Database Operations

### Bulk Price Update

```sql
-- Preview: Show items that will be affected
SELECT
    pl.id,
    pl.SKU,
    pl.wholesale_unit_price as current_wholesale,
    pl.retail_unit_price as current_retail,
    FLOOR(pl.wholesale_unit_price * (1 + $percentage / 100.0)) as new_wholesale,
    FLOOR(pl.retail_unit_price * (1 + $percentage / 100.0)) as new_retail,
    pc.name as packaging,
    pcat.name as category
FROM price_list pl
JOIN packaging_catalog pc ON pl.packaging_catalog_id = pc.id
JOIN product_categories pcat ON pl.product_categories_id = pcat.id
WHERE
    ($1::int IS NULL OR pl.product_categories_id = $1)
    AND ($2::int IS NULL OR pl.packaging_catalog_id = $2)
    AND ($3::varchar IS NULL OR pl.availability = $3)
    AND ($4::int IS NULL OR pl.wholesale_unit_price >= $4)
    AND ($5::int IS NULL OR pl.wholesale_unit_price <= $5);

-- Execute: Update prices
UPDATE price_list
SET
    wholesale_unit_price = FLOOR(wholesale_unit_price * (1 + $percentage / 100.0)),
    retail_unit_price = FLOOR(retail_unit_price * (1 + $percentage / 100.0)),
    wholesale_total_price_per_box = FLOOR(wholesale_unit_price * (1 + $percentage / 100.0)) * unit_per_storage_box,
    updated_at = NOW()
WHERE id IN (
    SELECT id FROM price_list
    WHERE
        ($1::int IS NULL OR product_categories_id = $1)
        AND ($2::int IS NULL OR packaging_catalog_id = $2)
        AND ($3::varchar IS NULL OR availability = $3)
        AND ($4::int IS NULL OR wholesale_unit_price >= $4)
        AND ($5::int IS NULL OR wholesale_unit_price <= $5)
)
RETURNING id, SKU, wholesale_unit_price, retail_unit_price;
```

### Bulk Availability Update

```sql
-- Preview: Show items that will be affected
SELECT
    pl.id,
    pl.SKU,
    pl.availability as current_availability,
    $new_availability as new_availability,
    pc.name as packaging,
    pcat.name as category
FROM price_list pl
JOIN packaging_catalog pc ON pl.packaging_catalog_id = pc.id
JOIN product_categories pcat ON pl.product_categories_id = pcat.id
WHERE
    ($1::int IS NULL OR pl.product_categories_id = $1)
    AND ($2::int IS NULL OR pl.packaging_catalog_id = $2)
    AND ($3::varchar IS NULL OR pl.availability = $3);

-- Execute: Update availability
UPDATE price_list
SET
    availability = $new_availability,
    updated_at = NOW()
WHERE id IN (
    SELECT id FROM price_list
    WHERE
        ($1::int IS NULL OR product_categories_id = $1)
        AND ($2::int IS NULL OR packaging_catalog_id = $2)
        AND ($3::varchar IS NULL OR availability = $3)
)
RETURNING id, SKU, availability;
```

### Bulk Discount Update

```sql
-- Execute: Update discount factor
UPDATE price_list
SET
    discount_factor = $new_discount_factor,
    updated_at = NOW()
WHERE id IN (
    SELECT id FROM price_list
    WHERE
        ($1::int IS NULL OR product_categories_id = $1)
        AND ($2::int IS NULL OR packaging_catalog_id = $2)
)
RETURNING id, SKU, discount_factor;
```

## API Endpoints

### Bulk Price Update - Preview

```python
@router.post("/api/admin/price-list/bulk-update-prices/preview")
async def preview_bulk_price_update(
    request: BulkPriceUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
) -> BulkUpdatePreviewResponse:
    """
    Preview bulk price update without applying changes

    Args:
        request: Filters and percentage change

    Returns:
        List of items that would be affected with before/after values

    Raises:
        400: Invalid percentage or filters
    """
    # Validate percentage
    if request.percentage_change == 0:
        raise HTTPException(400, "Percentage change cannot be zero")
    if abs(request.percentage_change) > 100:
        raise HTTPException(400, "Percentage change cannot exceed ±100%")

    # Build query
    query = (
        select(
            PriceList.id,
            PriceList.SKU,
            PriceList.wholesale_unit_price,
            PriceList.retail_unit_price,
            PriceList.wholesale_total_price_per_box,
            PackagingCatalog.name.label('packaging_name'),
            ProductCategory.name.label('category_name')
        )
        .join(PackagingCatalog)
        .join(ProductCategory)
    )

    # Apply filters
    if request.category_id:
        query = query.where(PriceList.product_categories_id == request.category_id)
    if request.packaging_id:
        query = query.where(PriceList.packaging_catalog_id == request.packaging_id)
    if request.availability:
        query = query.where(PriceList.availability == request.availability)
    if request.min_price:
        query = query.where(PriceList.wholesale_unit_price >= request.min_price)
    if request.max_price:
        query = query.where(PriceList.wholesale_unit_price <= request.max_price)

    result = await db.execute(query)
    items = result.all()

    if len(items) == 0:
        raise HTTPException(400, "No items match the specified filters")

    if len(items) > 1000:
        raise HTTPException(
            400,
            f"Operation would affect {len(items)} items. Maximum is 1000. "
            f"Please use more specific filters."
        )

    # Calculate new prices
    factor = 1 + (request.percentage_change / 100.0)
    preview_items = []

    for item in items:
        new_wholesale = int(item.wholesale_unit_price * factor)
        new_retail = int(item.retail_unit_price * factor)
        new_total = new_wholesale * (item.wholesale_total_price_per_box // item.wholesale_unit_price)

        preview_items.append({
            "id": item.id,
            "SKU": item.SKU,
            "packaging": item.packaging_name,
            "category": item.category_name,
            "current_wholesale": item.wholesale_unit_price,
            "new_wholesale": new_wholesale,
            "current_retail": item.retail_unit_price,
            "new_retail": new_retail,
            "current_total_per_box": item.wholesale_total_price_per_box,
            "new_total_per_box": new_total,
            "price_change_amount": new_wholesale - item.wholesale_unit_price
        })

    return BulkUpdatePreviewResponse(
        operation="price_update",
        affected_count=len(items),
        items=preview_items,
        summary={
            "percentage_change": request.percentage_change,
            "total_items": len(items),
            "avg_price_increase": sum(i["price_change_amount"] for i in preview_items) / len(items)
        }
    )
```

### Bulk Price Update - Execute

```python
@router.post("/api/admin/price-list/bulk-update-prices/execute")
async def execute_bulk_price_update(
    request: BulkPriceUpdateRequest,
    confirmation_token: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
) -> BulkUpdateResultResponse:
    """
    Execute bulk price update

    Args:
        request: Filters and percentage change
        confirmation_token: Token from preview response

    Returns:
        Result of bulk update operation

    Raises:
        400: Invalid request or token
        403: Rate limit exceeded
    """
    # Validate confirmation token (contains preview hash)
    # This ensures user saw the preview before executing
    if not validate_confirmation_token(confirmation_token, request):
        raise HTTPException(400, "Invalid confirmation token. Please preview changes again.")

    # Check rate limit
    rate_limit_key = f"bulk_ops:{current_user.id}"
    ops_count = await redis.get(rate_limit_key) or 0
    if int(ops_count) >= 10:
        raise HTTPException(403, "Rate limit exceeded. Maximum 10 bulk operations per hour.")

    # Begin transaction
    async with db.begin():
        # Build update query
        update_stmt = (
            update(PriceList)
            .values(
                wholesale_unit_price=func.floor(
                    PriceList.wholesale_unit_price * (1 + request.percentage_change / 100.0)
                ),
                retail_unit_price=func.floor(
                    PriceList.retail_unit_price * (1 + request.percentage_change / 100.0)
                ),
                wholesale_total_price_per_box=func.floor(
                    PriceList.wholesale_unit_price * (1 + request.percentage_change / 100.0)
                ) * PriceList.unit_per_storage_box,
                updated_at=func.now()
            )
        )

        # Apply same filters as preview
        if request.category_id:
            update_stmt = update_stmt.where(
                PriceList.product_categories_id == request.category_id
            )
        if request.packaging_id:
            update_stmt = update_stmt.where(
                PriceList.packaging_catalog_id == request.packaging_id
            )
        if request.availability:
            update_stmt = update_stmt.where(PriceList.availability == request.availability)
        if request.min_price:
            update_stmt = update_stmt.where(
                PriceList.wholesale_unit_price >= request.min_price
            )
        if request.max_price:
            update_stmt = update_stmt.where(
                PriceList.wholesale_unit_price <= request.max_price
            )

        # Execute update
        result = await db.execute(update_stmt)
        affected_count = result.rowcount

        # Create audit log
        await create_audit_log(
            user_id=current_user.id,
            action="bulk_update_prices",
            entity_type="price_list",
            entity_id=None,  # Multiple items
            details={
                "percentage_change": request.percentage_change,
                "affected_count": affected_count,
                "filters": request.dict(exclude={'percentage_change'})
            }
        )

        # Increment rate limit counter
        await redis.incr(rate_limit_key)
        await redis.expire(rate_limit_key, 3600)  # 1 hour

        # Invalidate cache
        await invalidate_price_list_cache()

    return BulkUpdateResultResponse(
        success=True,
        operation="price_update",
        affected_count=affected_count,
        message=f"Successfully updated prices for {affected_count} items"
    )
```

### Bulk Availability Update

```python
@router.post("/api/admin/price-list/bulk-update-availability")
async def bulk_update_availability(
    request: BulkAvailabilityUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
) -> BulkUpdateResultResponse:
    """
    Bulk update availability status

    Args:
        request: Filters and new availability status

    Returns:
        Result of bulk update

    Raises:
        400: Invalid availability status
    """
    # Validate availability value
    valid_statuses = ['available', 'out_of_stock', 'discontinued']
    if request.new_availability not in valid_statuses:
        raise HTTPException(
            400,
            f"Invalid availability. Must be one of: {valid_statuses}"
        )

    # Preview (optional, can be same endpoint with preview param)
    preview_query = (
        select(func.count())
        .select_from(PriceList)
    )

    if request.category_id:
        preview_query = preview_query.where(
            PriceList.product_categories_id == request.category_id
        )
    if request.packaging_id:
        preview_query = preview_query.where(
            PriceList.packaging_catalog_id == request.packaging_id
        )
    if request.current_availability:
        preview_query = preview_query.where(
            PriceList.availability == request.current_availability
        )

    affected_count_preview = await db.scalar(preview_query)

    if affected_count_preview == 0:
        raise HTTPException(400, "No items match the specified filters")

    if affected_count_preview > 1000:
        raise HTTPException(
            400,
            f"Operation would affect {affected_count_preview} items. Maximum is 1000."
        )

    # Execute update
    async with db.begin():
        update_stmt = (
            update(PriceList)
            .values(
                availability=request.new_availability,
                updated_at=func.now()
            )
        )

        # Apply filters
        if request.category_id:
            update_stmt = update_stmt.where(
                PriceList.product_categories_id == request.category_id
            )
        if request.packaging_id:
            update_stmt = update_stmt.where(
                PriceList.packaging_catalog_id == request.packaging_id
            )
        if request.current_availability:
            update_stmt = update_stmt.where(
                PriceList.availability == request.current_availability
            )

        result = await db.execute(update_stmt)
        affected_count = result.rowcount

        # Audit log
        await create_audit_log(
            user_id=current_user.id,
            action="bulk_update_availability",
            entity_type="price_list",
            entity_id=None,
            details={
                "new_availability": request.new_availability,
                "affected_count": affected_count,
                "filters": {
                    "category_id": request.category_id,
                    "packaging_id": request.packaging_id,
                    "current_availability": request.current_availability
                }
            }
        )

        await invalidate_price_list_cache()

    return BulkUpdateResultResponse(
        success=True,
        operation="availability_update",
        affected_count=affected_count,
        message=f"Successfully updated availability for {affected_count} items to '{request.new_availability}'"
    )
```

### Bulk Discount Update

```python
@router.post("/api/admin/price-list/bulk-update-discount")
async def bulk_update_discount(
    request: BulkDiscountUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
) -> BulkUpdateResultResponse:
    """
    Bulk update discount factor

    Args:
        request: Filters and new discount factor

    Returns:
        Result of bulk update

    Raises:
        400: Invalid discount factor
    """
    # Validate discount factor
    if request.discount_factor < 0 or request.discount_factor > 100:
        raise HTTPException(400, "Discount factor must be between 0 and 100")

    async with db.begin():
        update_stmt = (
            update(PriceList)
            .values(
                discount_factor=request.discount_factor,
                updated_at=func.now()
            )
        )

        # Apply filters
        if request.category_id:
            update_stmt = update_stmt.where(
                PriceList.product_categories_id == request.category_id
            )
        if request.packaging_id:
            update_stmt = update_stmt.where(
                PriceList.packaging_catalog_id == request.packaging_id
            )

        result = await db.execute(update_stmt)
        affected_count = result.rowcount

        if affected_count == 0:
            raise HTTPException(400, "No items match the specified filters")

        # Audit log
        await create_audit_log(
            user_id=current_user.id,
            action="bulk_update_discount",
            entity_type="price_list",
            entity_id=None,
            details={
                "discount_factor": request.discount_factor,
                "affected_count": affected_count,
                "filters": {
                    "category_id": request.category_id,
                    "packaging_id": request.packaging_id
                }
            }
        )

        await invalidate_price_list_cache()

    return BulkUpdateResultResponse(
        success=True,
        operation="discount_update",
        affected_count=affected_count,
        message=f"Successfully updated discount factor for {affected_count} items to {request.discount_factor}%"
    )
```

## Performance Considerations

### Batch Update Optimization

```sql
-- Use indexed columns in WHERE clause
CREATE INDEX idx_price_list_category ON price_list(product_categories_id);
CREATE INDEX idx_price_list_packaging ON price_list(packaging_catalog_id);
CREATE INDEX idx_price_list_availability ON price_list(availability);

-- For large updates, consider batching
-- Update in chunks of 100-500 items
DO $$
DECLARE
    batch_size INT := 500;
    offset_val INT := 0;
    affected_rows INT;
BEGIN
    LOOP
        UPDATE price_list
        SET wholesale_unit_price = FLOOR(wholesale_unit_price * 1.10)
        WHERE id IN (
            SELECT id FROM price_list
            WHERE product_categories_id = 1
            LIMIT batch_size OFFSET offset_val
        );

        GET DIAGNOSTICS affected_rows = ROW_COUNT;
        EXIT WHEN affected_rows = 0;

        offset_val := offset_val + batch_size;
        COMMIT;
    END LOOP;
END $$;
```

### Locking Strategy

```python
# Use row-level locking for updates
async with db.begin():
    # Lock rows to prevent concurrent modifications
    items = await db.execute(
        select(PriceList)
        .where(PriceList.product_categories_id == category_id)
        .with_for_update()  # Row-level lock
    )

    # Perform updates
    # ...
```

## Performance Targets

| Operation | Items | Target Time | Notes |
|-----------|-------|-------------|-------|
| Preview | 100 items | < 200ms | Query + calculation |
| Preview | 1000 items | < 500ms | Max limit |
| Execute update | 100 items | < 300ms | Single transaction |
| Execute update | 500 items | < 1s | Acceptable |
| Execute update | 1000 items | < 2s | Max limit |

## Request/Response Models

```python
class BulkPriceUpdateRequest(BaseModel):
    percentage_change: float  # Can be positive or negative
    category_id: Optional[int] = None
    packaging_id: Optional[int] = None
    availability: Optional[str] = None
    min_price: Optional[int] = None  # In cents
    max_price: Optional[int] = None  # In cents

    @validator('percentage_change')
    def validate_percentage(cls, v):
        if v == 0:
            raise ValueError('Percentage change cannot be zero')
        if abs(v) > 100:
            raise ValueError('Percentage change cannot exceed ±100%')
        return v


class BulkAvailabilityUpdateRequest(BaseModel):
    new_availability: str  # available, out_of_stock, discontinued
    category_id: Optional[int] = None
    packaging_id: Optional[int] = None
    current_availability: Optional[str] = None  # Filter by current status


class BulkDiscountUpdateRequest(BaseModel):
    discount_factor: int  # 0-100
    category_id: Optional[int] = None
    packaging_id: Optional[int] = None

    @validator('discount_factor')
    def validate_discount(cls, v):
        if v < 0 or v > 100:
            raise ValueError('Discount factor must be between 0 and 100')
        return v


class BulkUpdatePreviewResponse(BaseModel):
    operation: str
    affected_count: int
    items: List[Dict[str, Any]]
    summary: Dict[str, Any]
    confirmation_token: str  # Hash of preview for verification


class BulkUpdateResultResponse(BaseModel):
    success: bool
    operation: str
    affected_count: int
    message: str
    errors: Optional[List[str]] = None
```

## Use Cases

### Scenario 1: Annual Price Increase

```python
# User: "Increase all prices by 8% for the new year"

request = BulkPriceUpdateRequest(
    percentage_change=8.0,
    # No filters = apply to all
)

# Preview shows 150 items affected
# User confirms
# Execute: 150 items updated in ~400ms
```

### Scenario 2: Mark Category Out of Stock

```python
# User: "Mark all Cactus products as out of stock temporarily"

request = BulkAvailabilityUpdateRequest(
    new_availability='out_of_stock',
    category_id=1,  # Cactus
    current_availability='available'
)

# Execute: 45 items updated in ~200ms
```

### Scenario 3: Apply Seasonal Discount

```python
# User: "Apply 15% discount to all succulentas in R10 pots"

request = BulkDiscountUpdateRequest(
    discount_factor=15,
    category_id=2,  # Suculenta
    packaging_id=5  # R10
)

# Execute: 12 items updated in ~150ms
```

## Security & Validation

### Rate Limiting

```python
# Redis-based rate limiting
RATE_LIMIT_KEY = "bulk_ops:{user_id}"
MAX_OPS_PER_HOUR = 10

async def check_rate_limit(user_id: int) -> bool:
    key = RATE_LIMIT_KEY.format(user_id=user_id)
    count = await redis.get(key)
    if count and int(count) >= MAX_OPS_PER_HOUR:
        return False
    return True

async def increment_rate_limit(user_id: int):
    key = RATE_LIMIT_KEY.format(user_id=user_id)
    await redis.incr(key)
    await redis.expire(key, 3600)  # 1 hour TTL
```

### Audit Trail

```python
# Every bulk operation logged
{
    "user_id": 123,
    "action": "bulk_update_prices",
    "timestamp": "2025-10-08T10:30:00Z",
    "details": {
        "operation": "price_update",
        "percentage_change": 8.0,
        "filters": {"category_id": 1},
        "affected_count": 45,
        "preview_hash": "abc123...",
        "execution_time_ms": 380
    }
}
```

---

**Version**: 1.0
**Last Updated**: 2025-10-08
**Author**: DemeterAI Engineering Team
