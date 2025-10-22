# Create New Configuration - Detailed Flow

## Purpose

Shows the detailed flow for creating a new storage location configuration with historical
preservation, used when starting a new cultivation cycle.

## Scope

- **Level**: Implementation detail
- **Audience**: Backend developers
- **Detail**: Complete flow with atomic transaction
- **Mermaid Version**: v11.3.0+

## What It Represents

Complete CREATE flow including:

1. Form validation
2. Deactivate existing config (active=false)
3. Insert new config (active=true)
4. Atomic transaction (all or nothing)
5. Historical data preservation

## When to Use CREATE

**Use CREATE when**:

- Sold all previous stock, replanting different species
- Major crop change (cactus → suculenta)
- Starting new cultivation cycle
- Want to preserve historical configuration for reporting

**Impact**: Old config archived (active=false), new config active, historical queries still use old
config for their time period.

## Database Operations

### Atomic Transaction

```sql
BEGIN;

-- Step 1: Deactivate current config
UPDATE storage_location_config
SET
    active = false,
    updated_at = NOW()
WHERE
    storage_location_id = $1
    AND active = true;

-- Step 2: Insert new config
INSERT INTO storage_location_config (
    storage_location_id,
    product_id,
    packaging_catalog_id,
    expected_product_state_id,
    area_cm2,
    active,
    notes,
    created_at
) VALUES (
    $1, $2, $3, $4, $5, true, $6, NOW()
)
RETURNING id;

COMMIT;
```

### Rollback on Error

If either step fails, entire transaction rolls back - ensures data consistency.

## API Endpoint

```python
@router.post("/api/admin/storage-location-config")
async def create_storage_location_config(
    request: CreateConfigRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
) -> ConfigResponse:
    """
    Create new storage location configuration (preserves history)

    Args:
        request: New configuration data
        db: Database session
        current_user: Must be admin

    Returns:
        New active configuration
    """
    # Validation (same as UPDATE)
    ...

    # Start transaction
    async with db.begin():
        # Deactivate existing config
        await db.execute(
            update(StorageLocationConfig)
            .where(
                StorageLocationConfig.storage_location_id == request.storage_location_id,
                StorageLocationConfig.active == true
            )
            .values(active=false, updated_at=datetime.now())
        )

        # Create new config
        new_config = StorageLocationConfig(
            storage_location_id=request.storage_location_id,
            product_id=request.product_id,
            packaging_catalog_id=request.packaging_catalog_id,
            expected_product_state_id=request.expected_product_state_id,
            area_cm2=request.area_cm2,
            active=true,
            notes=request.notes,
            created_at=datetime.now()
        )
        db.add(new_config)
        await db.flush()  # Get ID without committing

        # Audit log
        await create_audit_log(...)

    # Transaction committed here (async with exit)
    await db.refresh(new_config)
    return ConfigResponse.from_orm(new_config)
```

## Historical Queries

### How to Query Historical Config

```sql
-- Get config active at specific date
SELECT *
FROM storage_location_config
WHERE storage_location_id = $1
  AND created_at <= $2  -- Config existed at that time
  AND (
    active = true  -- Still active
    OR updated_at >= $2  -- Or was active until after that date
  )
ORDER BY created_at DESC
LIMIT 1;

-- Get all historical configs for location
SELECT
    id,
    product_id,
    packaging_catalog_id,
    active,
    created_at,
    updated_at
FROM storage_location_config
WHERE storage_location_id = $1
ORDER BY created_at DESC;
```

## Performance

| Operation            | Time      | Notes             |
|----------------------|-----------|-------------------|
| Deactivate old       | ~20ms     | Single row UPDATE |
| Insert new           | ~20ms     | Single row INSERT |
| Transaction overhead | ~10ms     | BEGIN/COMMIT      |
| Total                | **~50ms** | Atomic operation  |

---

**Version**: 1.0
**Last Updated**: 2025-10-08
**Author**: DemeterAI Engineering Team
