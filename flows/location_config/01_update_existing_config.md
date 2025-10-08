# Update Existing Configuration - Detailed Flow

## Purpose

Shows the detailed flow for updating an existing storage location configuration, which modifies the current active config and impacts current stock metadata without affecting historical records.

## Scope

- **Level**: Implementation detail
- **Audience**: Backend developers
- **Detail**: Complete flow from form submission to database update
- **Mermaid Version**: v11.3.0+

## What It Represents

Complete UPDATE flow including:
1. Form validation
2. Business rule checks
3. Database update (single transaction)
4. Stock metadata refresh
5. Audit logging

## When to Use UPDATE

**Use UPDATE when**:
- Pot color changed
- Pot size adjusted (same plants)
- Product state changed (growth progression)
- Area recalculated
- Correcting data entry errors
- Any change that doesn't represent a new cultivation cycle

**Impact**: Current stock metadata updated, historical data unchanged.

## Database Operations

### Single UPDATE Statement

```sql
-- Update active configuration
UPDATE storage_location_config
SET
    product_id = $1,
    packaging_catalog_id = $2,
    expected_product_state_id = $3,
    area_cm2 = $4,
    notes = $5,
    updated_at = NOW()
WHERE
    storage_location_id = $6
    AND active = true
RETURNING id, storage_location_id;
```

### Validation Queries

```sql
-- Check product exists
SELECT id FROM products WHERE id = $1;

-- Check packaging exists (if provided)
SELECT id FROM packaging_catalog WHERE id = $1;

-- Check product state exists
SELECT id FROM product_states WHERE id = $1;

-- Check product-state compatibility
SELECT 1
FROM products p
JOIN product_families pf ON p.family_id = pf.id
JOIN product_categories pc ON pf.category_id = pc.id
WHERE p.id = $1
  AND EXISTS (
    SELECT 1 FROM product_states
    WHERE id = $2
    -- Add business rules for valid state transitions
  );
```

## API Endpoint

```python
@router.put("/api/admin/storage-location-config/{config_id}")
async def update_storage_location_config(
    config_id: int,
    request: UpdateConfigRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
) -> ConfigResponse:
    """
    Update existing storage location configuration

    Args:
        config_id: Configuration ID
        request: Updated configuration data
        db: Database session
        current_user: Must be admin

    Returns:
        Updated configuration
    """
    # Validate exists and is active
    config = await db.get(StorageLocationConfig, config_id)
    if not config or not config.active:
        raise HTTPException(404, "Active configuration not found")

    # Validate product exists
    product = await db.get(Product, request.product_id)
    if not product:
        raise HTTPException(400, "Product not found")

    # Validate packaging if provided
    if request.packaging_catalog_id:
        packaging = await db.get(PackagingCatalog, request.packaging_catalog_id)
        if not packaging:
            raise HTTPException(400, "Packaging not found")

    # Validate state
    state = await db.get(ProductState, request.expected_product_state_id)
    if not state:
        raise HTTPException(400, "Product state not found")

    # Update config
    config.product_id = request.product_id
    config.packaging_catalog_id = request.packaging_catalog_id
    config.expected_product_state_id = request.expected_product_state_id
    config.area_cm2 = request.area_cm2
    config.notes = request.notes
    config.updated_at = datetime.now()

    # Commit
    await db.commit()
    await db.refresh(config)

    # Create audit log
    await create_audit_log(
        user_id=current_user.id,
        action="update_config",
        entity_type="storage_location_config",
        entity_id=config.id,
        changes={
            "product_id": request.product_id,
            "packaging_catalog_id": request.packaging_catalog_id,
            ...
        }
    )

    return ConfigResponse.from_orm(config)
```

## Performance

| Operation | Time | Notes |
|-----------|------|-------|
| Validation queries | ~50ms | 3-4 SELECT queries |
| UPDATE execution | ~20ms | Single row update |
| Audit log insert | ~10ms | Async if possible |
| Total | **~80ms** | Very fast |

---

**Version**: 1.0
**Last Updated**: 2025-10-08
**Author**: DemeterAI Engineering Team
