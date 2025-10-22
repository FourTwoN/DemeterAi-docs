# Packaging Catalog CRUD Operations - Detailed Flow

## Purpose

Shows the detailed flow for managing the packaging catalog (macetas, bandejas, plugs) with full CRUD
operations including validation, constraints, and business rules.

## Scope

- **Level**: Implementation detail
- **Audience**: Backend developers, API designers
- **Detail**: Complete flow from form submission to database persistence
- **Mermaid Version**: v11.3.0+

## What It Represents

Complete CRUD flow for packaging_catalog table:

1. **Create**: Add new packaging items (R7, R10, R12, etc.)
2. **Read**: List and filter packaging catalog
3. **Update**: Modify existing packaging attributes
4. **Delete**: Remove packaging (with constraints)

## Database Schema

### packaging_catalog Table

```sql
CREATE TABLE packaging_catalog (
    id SERIAL PRIMARY KEY,
    packaging_type_id INT NOT NULL REFERENCES packaging_types(id),
    packaging_material_id INT NOT NULL REFERENCES packaging_materials(id),
    packaging_color_id INT NOT NULL REFERENCES packaging_colors(id),
    sku VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    volume_liters NUMERIC(8,2),
    diameter_cm NUMERIC(6,2),
    height_cm NUMERIC(6,2),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_packaging_catalog_type ON packaging_catalog(packaging_type_id);
CREATE INDEX idx_packaging_catalog_sku ON packaging_catalog(sku);
CREATE UNIQUE INDEX idx_packaging_catalog_combination
    ON packaging_catalog(packaging_type_id, packaging_material_id,
                         packaging_color_id, diameter_cm, height_cm);
```

### Reference Tables

```sql
CREATE TABLE packaging_types (
    id SERIAL PRIMARY KEY,
    code VARCHAR(20) UNIQUE NOT NULL,  -- MACETA, BANDEJA, PLUG
    name VARCHAR(100) NOT NULL,
    description TEXT
);

CREATE TABLE packaging_materials (
    id SERIAL PRIMARY KEY,
    code VARCHAR(20) UNIQUE NOT NULL,  -- PLASTIC, CERAMIC, BIODEGRADABLE
    name VARCHAR(100) NOT NULL
);

CREATE TABLE packaging_colors (
    id SERIAL PRIMARY KEY,
    code VARCHAR(20) UNIQUE NOT NULL,  -- BLK, WHT, TERRA, GRN
    name VARCHAR(100) NOT NULL,
    hex_color VARCHAR(7)  -- #000000
);
```

## CREATE Operation

### Business Rules

1. **SKU Generation**: Auto-generate if not provided
    - Pattern: `{TYPE}-{SIZE}-{COLOR}`
    - Example: `MAC-R7-BLK`, `MAC-R10-WHT`

2. **Validation Rules**:
    - All dimensions must be positive numbers
    - Volume should match approximate calculation: V ≈ π × (d/2)² × h / 1000
    - Type, material, color must exist in reference tables
    - Unique combination of type+material+color+dimensions

3. **Default Values**:
    - Auto-generate SKU if not provided
    - Auto-calculate volume if only dimensions provided
    - Default material: PLASTIC if not specified

### SQL - Create Packaging

```sql
-- Validation: Check references exist
SELECT id FROM packaging_types WHERE id = $1;
SELECT id FROM packaging_materials WHERE id = $2;
SELECT id FROM packaging_colors WHERE id = $3;

-- Validation: Check unique combination
SELECT id FROM packaging_catalog
WHERE packaging_type_id = $1
  AND packaging_material_id = $2
  AND packaging_color_id = $3
  AND diameter_cm = $4
  AND height_cm = $5;
-- Must return empty

-- Insert new packaging
INSERT INTO packaging_catalog (
    packaging_type_id,
    packaging_material_id,
    packaging_color_id,
    sku,
    name,
    volume_liters,
    diameter_cm,
    height_cm
) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
RETURNING id, sku, name, created_at;
```

### API Endpoint - Create

```python
@router.post("/api/admin/packaging-catalog")
async def create_packaging(
    request: CreatePackagingRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
) -> PackagingResponse:
    """
    Create new packaging catalog entry

    Args:
        request: Packaging data
        db: Database session
        current_user: Must be admin

    Returns:
        Created packaging with generated SKU

    Raises:
        400: Validation error
        409: Duplicate SKU or combination
    """
    # Validate references
    pkg_type = await db.get(PackagingType, request.packaging_type_id)
    if not pkg_type:
        raise HTTPException(400, "Packaging type not found")

    material = await db.get(PackagingMaterial, request.packaging_material_id)
    if not material:
        raise HTTPException(400, "Packaging material not found")

    color = await db.get(PackagingColor, request.packaging_color_id)
    if not color:
        raise HTTPException(400, "Packaging color not found")

    # Validate dimensions
    if request.diameter_cm <= 0 or request.height_cm <= 0:
        raise HTTPException(400, "Dimensions must be positive")

    # Auto-generate SKU if not provided
    if not request.sku:
        request.sku = generate_packaging_sku(
            type_code=pkg_type.code,
            diameter=request.diameter_cm,
            color_code=color.code
        )

    # Check SKU uniqueness
    existing_sku = await db.execute(
        select(PackagingCatalog).where(PackagingCatalog.sku == request.sku)
    )
    if existing_sku.scalar_one_or_none():
        raise HTTPException(409, f"SKU {request.sku} already exists")

    # Check combination uniqueness
    existing_combo = await db.execute(
        select(PackagingCatalog).where(
            and_(
                PackagingCatalog.packaging_type_id == request.packaging_type_id,
                PackagingCatalog.packaging_material_id == request.packaging_material_id,
                PackagingCatalog.packaging_color_id == request.packaging_color_id,
                PackagingCatalog.diameter_cm == request.diameter_cm,
                PackagingCatalog.height_cm == request.height_cm
            )
        )
    )
    if existing_combo.scalar_one_or_none():
        raise HTTPException(409, "This packaging combination already exists")

    # Auto-calculate volume if not provided
    if not request.volume_liters:
        request.volume_liters = calculate_pot_volume(
            diameter_cm=request.diameter_cm,
            height_cm=request.height_cm
        )

    # Create packaging
    packaging = PackagingCatalog(
        packaging_type_id=request.packaging_type_id,
        packaging_material_id=request.packaging_material_id,
        packaging_color_id=request.packaging_color_id,
        sku=request.sku,
        name=request.name or f"R{int(request.diameter_cm)} {color.name}",
        volume_liters=request.volume_liters,
        diameter_cm=request.diameter_cm,
        height_cm=request.height_cm
    )

    db.add(packaging)
    await db.commit()
    await db.refresh(packaging)

    # Audit log
    await create_audit_log(
        user_id=current_user.id,
        action="create_packaging",
        entity_type="packaging_catalog",
        entity_id=packaging.id,
        details={"sku": packaging.sku, "name": packaging.name}
    )

    return PackagingResponse.from_orm(packaging)


def generate_packaging_sku(type_code: str, diameter: float, color_code: str) -> str:
    """
    Generate SKU following pattern: {TYPE}-R{SIZE}-{COLOR}

    Examples:
        MAC-R7-BLK (Maceta R7 Black)
        MAC-R10-WHT (Maceta R10 White)
    """
    size = int(diameter)
    return f"{type_code}-R{size}-{color_code}"


def calculate_pot_volume(diameter_cm: float, height_cm: float) -> float:
    """
    Calculate approximate pot volume in liters

    Formula: V = π × r² × h / 1000 (convert cm³ to liters)
    Using 0.75 factor for typical pot taper
    """
    import math
    radius_cm = diameter_cm / 2
    volume_cm3 = math.pi * (radius_cm ** 2) * height_cm * 0.75
    volume_liters = volume_cm3 / 1000
    return round(volume_liters, 2)
```

## READ Operation

### SQL - List Packaging

```sql
-- List all packaging with filters
SELECT
    pc.id,
    pc.sku,
    pc.name,
    pc.volume_liters,
    pc.diameter_cm,
    pc.height_cm,
    pt.name as type_name,
    pt.code as type_code,
    pm.name as material_name,
    pcol.name as color_name,
    pcol.hex_color,
    pc.created_at,
    pc.updated_at
FROM packaging_catalog pc
JOIN packaging_types pt ON pc.packaging_type_id = pt.id
JOIN packaging_materials pm ON pc.packaging_material_id = pm.id
JOIN packaging_colors pcol ON pc.packaging_color_id = pcol.id
WHERE
    ($1::int IS NULL OR pc.packaging_type_id = $1)
    AND ($2::int IS NULL OR pc.packaging_color_id = $2)
    AND ($3::numeric IS NULL OR pc.diameter_cm >= $3)
    AND ($4::numeric IS NULL OR pc.diameter_cm <= $4)
ORDER BY
    pt.code,
    pc.diameter_cm,
    pcol.code
LIMIT $5 OFFSET $6;

-- Count total (for pagination)
SELECT COUNT(*) FROM packaging_catalog
WHERE ... (same filters);
```

### API Endpoint - List

```python
@router.get("/api/admin/packaging-catalog")
async def list_packaging(
    type_id: Optional[int] = None,
    color_id: Optional[int] = None,
    min_diameter: Optional[float] = None,
    max_diameter: Optional[float] = None,
    page: int = 1,
    page_size: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
) -> PackagingListResponse:
    """
    List packaging catalog with filters

    Query params:
        type_id: Filter by packaging type
        color_id: Filter by color
        min_diameter: Minimum diameter in cm
        max_diameter: Maximum diameter in cm
        page: Page number (1-indexed)
        page_size: Items per page (max 100)
    """
    # Build query
    query = (
        select(PackagingCatalog)
        .join(PackagingType)
        .join(PackagingMaterial)
        .join(PackagingColor)
        .options(
            selectinload(PackagingCatalog.type),
            selectinload(PackagingCatalog.material),
            selectinload(PackagingCatalog.color)
        )
    )

    # Apply filters
    if type_id:
        query = query.where(PackagingCatalog.packaging_type_id == type_id)
    if color_id:
        query = query.where(PackagingCatalog.packaging_color_id == color_id)
    if min_diameter:
        query = query.where(PackagingCatalog.diameter_cm >= min_diameter)
    if max_diameter:
        query = query.where(PackagingCatalog.diameter_cm <= max_diameter)

    # Count total
    count_query = select(func.count()).select_from(PackagingCatalog)
    # ... apply same filters
    total = await db.scalar(count_query)

    # Pagination
    offset = (page - 1) * page_size
    query = query.order_by(
        PackagingType.code,
        PackagingCatalog.diameter_cm,
        PackagingColor.code
    ).limit(page_size).offset(offset)

    result = await db.execute(query)
    items = result.scalars().all()

    return PackagingListResponse(
        items=[PackagingResponse.from_orm(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size
    )
```

## UPDATE Operation

### Business Rules

1. **Immutable Fields**:
    - `id`, `sku`, `created_at` cannot be changed
    - If SKU needs change, delete and recreate

2. **Impact Analysis**:
    - Check if packaging is used in active price_list entries
    - If yes, warn user that price list will be affected

3. **Validation**:
    - Same validations as CREATE
    - Must maintain uniqueness constraints

### SQL - Update Packaging

```sql
-- Check if used in price list
SELECT COUNT(*) FROM price_list
WHERE packaging_catalog_id = $1;

-- Update packaging
UPDATE packaging_catalog
SET
    packaging_type_id = COALESCE($1, packaging_type_id),
    packaging_material_id = COALESCE($2, packaging_material_id),
    packaging_color_id = COALESCE($3, packaging_color_id),
    name = COALESCE($4, name),
    volume_liters = COALESCE($5, volume_liters),
    diameter_cm = COALESCE($6, diameter_cm),
    height_cm = COALESCE($7, height_cm),
    updated_at = NOW()
WHERE id = $8
RETURNING id, sku, name, updated_at;
```

### API Endpoint - Update

```python
@router.put("/api/admin/packaging-catalog/{packaging_id}")
async def update_packaging(
    packaging_id: int,
    request: UpdatePackagingRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
) -> PackagingUpdateResponse:
    """
    Update packaging catalog entry

    Returns:
        Updated packaging + impact analysis
    """
    # Get existing packaging
    packaging = await db.get(PackagingCatalog, packaging_id)
    if not packaging:
        raise HTTPException(404, "Packaging not found")

    # Check impact on price list
    price_list_count = await db.scalar(
        select(func.count()).select_from(PriceList)
        .where(PriceList.packaging_catalog_id == packaging_id)
    )

    # Validate references if changed
    if request.packaging_type_id:
        pkg_type = await db.get(PackagingType, request.packaging_type_id)
        if not pkg_type:
            raise HTTPException(400, "Packaging type not found")

    # ... similar validation for material, color

    # Validate dimensions
    if request.diameter_cm and request.diameter_cm <= 0:
        raise HTTPException(400, "Diameter must be positive")
    if request.height_cm and request.height_cm <= 0:
        raise HTTPException(400, "Height must be positive")

    # Store old values for audit
    old_values = {
        "name": packaging.name,
        "diameter_cm": packaging.diameter_cm,
        "height_cm": packaging.height_cm,
        # ...
    }

    # Update fields
    if request.packaging_type_id:
        packaging.packaging_type_id = request.packaging_type_id
    if request.packaging_material_id:
        packaging.packaging_material_id = request.packaging_material_id
    if request.packaging_color_id:
        packaging.packaging_color_id = request.packaging_color_id
    if request.name:
        packaging.name = request.name
    if request.volume_liters:
        packaging.volume_liters = request.volume_liters
    if request.diameter_cm:
        packaging.diameter_cm = request.diameter_cm
    if request.height_cm:
        packaging.height_cm = request.height_cm

    packaging.updated_at = datetime.now()

    await db.commit()
    await db.refresh(packaging)

    # Audit log
    await create_audit_log(
        user_id=current_user.id,
        action="update_packaging",
        entity_type="packaging_catalog",
        entity_id=packaging.id,
        changes={"old": old_values, "new": request.dict(exclude_unset=True)}
    )

    return PackagingUpdateResponse(
        packaging=PackagingResponse.from_orm(packaging),
        affected_price_list_entries=price_list_count,
        warning=f"This change affects {price_list_count} price list entries" if price_list_count > 0 else None
    )
```

## DELETE Operation

### Business Rules

1. **Constraint Checks**:
    - Cannot delete if referenced in active price_list
    - Cannot delete if used in historical stock
    - If has any references, must use soft delete

2. **Soft Delete**:
    - Add `deleted_at` timestamp
    - Keep record in database
    - Exclude from normal queries

3. **Hard Delete**:
    - Only if no references anywhere
    - Permanently remove from database

### SQL - Delete Packaging

```sql
-- Check if used in price list
SELECT COUNT(*) FROM price_list
WHERE packaging_catalog_id = $1;

-- Check if used in stock configuration
SELECT COUNT(*) FROM storage_location_config
WHERE packaging_catalog_id = $1;

-- If no references: Hard delete
DELETE FROM packaging_catalog
WHERE id = $1
  AND NOT EXISTS (
    SELECT 1 FROM price_list WHERE packaging_catalog_id = $1
  )
  AND NOT EXISTS (
    SELECT 1 FROM storage_location_config WHERE packaging_catalog_id = $1
  )
RETURNING id;

-- If has references: Soft delete (add column if needed)
-- UPDATE packaging_catalog
-- SET deleted_at = NOW()
-- WHERE id = $1
-- RETURNING id;
```

### API Endpoint - Delete

```python
@router.delete("/api/admin/packaging-catalog/{packaging_id}")
async def delete_packaging(
    packaging_id: int,
    force_soft_delete: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
) -> DeleteResponse:
    """
    Delete packaging catalog entry

    Args:
        packaging_id: Packaging to delete
        force_soft_delete: If true, always soft delete

    Returns:
        Deletion result with constraint info
    """
    # Get packaging
    packaging = await db.get(PackagingCatalog, packaging_id)
    if not packaging:
        raise HTTPException(404, "Packaging not found")

    # Check references
    price_list_refs = await db.scalar(
        select(func.count()).select_from(PriceList)
        .where(PriceList.packaging_catalog_id == packaging_id)
    )

    config_refs = await db.scalar(
        select(func.count()).select_from(StorageLocationConfig)
        .where(StorageLocationConfig.packaging_catalog_id == packaging_id)
    )

    total_refs = price_list_refs + config_refs

    if total_refs > 0:
        # Cannot hard delete - has references
        raise HTTPException(
            409,
            f"Cannot delete: referenced by {price_list_refs} price list entries "
            f"and {config_refs} storage configurations. "
            f"Consider soft delete or removing references first."
        )

    # Hard delete (no references)
    await db.delete(packaging)
    await db.commit()

    # Audit log
    await create_audit_log(
        user_id=current_user.id,
        action="delete_packaging",
        entity_type="packaging_catalog",
        entity_id=packaging_id,
        details={"sku": packaging.sku, "name": packaging.name}
    )

    return DeleteResponse(
        success=True,
        message=f"Packaging {packaging.sku} deleted successfully",
        deleted_id=packaging_id
    )
```

## Performance Considerations

### Query Optimization

```sql
-- Index strategy
CREATE INDEX idx_packaging_catalog_type ON packaging_catalog(packaging_type_id);
CREATE INDEX idx_packaging_catalog_sku ON packaging_catalog(sku);
CREATE INDEX idx_packaging_catalog_diameter ON packaging_catalog(diameter_cm);

-- For filtered lists
CREATE INDEX idx_packaging_catalog_composite
    ON packaging_catalog(packaging_type_id, diameter_cm, packaging_color_id);
```

### Caching Strategy

```python
# Cache packaging types, materials, colors (rarely change)
@cache(expire=3600)  # 1 hour
async def get_packaging_types():
    return await db.execute(select(PackagingType))

@cache(expire=3600)
async def get_packaging_materials():
    return await db.execute(select(PackagingMaterial))

@cache(expire=3600)
async def get_packaging_colors():
    return await db.execute(select(PackagingColor))

# Invalidate cache on updates
async def invalidate_packaging_cache():
    await cache.delete("packaging_types")
    await cache.delete("packaging_materials")
    await cache.delete("packaging_colors")
```

## Performance Targets

| Operation                 | Target Time | Notes                     |
|---------------------------|-------------|---------------------------|
| List packaging (50 items) | < 150ms     | With joins and pagination |
| Create packaging          | < 100ms     | With validation           |
| Update packaging          | < 100ms     | With impact check         |
| Delete packaging          | < 100ms     | With constraint check     |
| Get by SKU                | < 50ms      | Indexed lookup            |

## Request/Response Models

```python
class CreatePackagingRequest(BaseModel):
    packaging_type_id: int
    packaging_material_id: int
    packaging_color_id: int
    sku: Optional[str] = None  # Auto-generated if not provided
    name: Optional[str] = None  # Auto-generated if not provided
    volume_liters: Optional[float] = None  # Auto-calculated if not provided
    diameter_cm: float
    height_cm: float

    @validator('diameter_cm', 'height_cm')
    def validate_positive(cls, v):
        if v <= 0:
            raise ValueError('Must be positive')
        return v


class UpdatePackagingRequest(BaseModel):
    packaging_type_id: Optional[int] = None
    packaging_material_id: Optional[int] = None
    packaging_color_id: Optional[int] = None
    name: Optional[str] = None
    volume_liters: Optional[float] = None
    diameter_cm: Optional[float] = None
    height_cm: Optional[float] = None


class PackagingResponse(BaseModel):
    id: int
    packaging_type_id: int
    packaging_material_id: int
    packaging_color_id: int
    sku: str
    name: str
    volume_liters: float
    diameter_cm: float
    height_cm: float
    type_name: Optional[str]
    material_name: Optional[str]
    color_name: Optional[str]
    hex_color: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PackagingListResponse(BaseModel):
    items: List[PackagingResponse]
    total: int
    page: int
    page_size: int
    pages: int
```

---

**Version**: 1.0
**Last Updated**: 2025-10-08
**Author**: DemeterAI Engineering Team
