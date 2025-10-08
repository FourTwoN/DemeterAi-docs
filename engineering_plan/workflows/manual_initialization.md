# Manual Stock Initialization Workflow

**Document Version:** 1.0
**Last Updated:** 2025-10-08
**Status:** NEW - Alternative to photo-based initialization

---

## Table of Contents

1. [Overview](#overview)
2. [Business Context](#business-context)
3. [When to Use Manual Initialization](#when-to-use-manual-initialization)
4. [Workflow Steps](#workflow-steps)
5. [Critical Validation Rules](#critical-validation-rules)
6. [Database Operations](#database-operations)
7. [API Endpoint](#api-endpoint)
8. [Differences from Photo Initialization](#differences-from-photo-initialization)
9. [Error Handling](#error-handling)
10. [Implementation Notes](#implementation-notes)

---

## Overview

**Manual Stock Initialization** is an alternative method to start the inventory tracking for a storage location **without using photos or ML processing**.

### What It Does

- User enters complete plant count via UI
- System validates against `storage_location_config`
- Creates `stock_movements` (type: `"manual_init"`)
- Creates `stock_batches` (grouped by product + size + packaging)
- **NO photo, detections, estimations, or ML processing**

### Key Principle

**Trust user input** - System assumes the manual count is accurate and complete. Configuration validation ensures data integrity.

---

## Business Context

### Problem Solved

1. **Pre-existing inventory:** User already has manually counted stock from previous system
2. **Photo system unavailable:** Temporary inability to take/process photos
3. **Fallback option:** When GPS/config/calibration missing for photo-based approach
4. **Quick entry:** Small locations where photo might be overkill

### NOT a Replacement for Photo Initialization

Manual initialization is **secondary** to photo-based initialization:

| Aspect | Photo Init | Manual Init |
|--------|-----------|-------------|
| **Accuracy** | 95%+ (ML verified) | Depends on user |
| **Speed** | 5-10 min (automatic) | Varies (manual counting) |
| **Traceability** | Full (detections + estimations) | Basic (movement record only) |
| **Preferred** | ✅ YES | ❌ Fallback |

---

## When to Use Manual Initialization

### Valid Use Cases

✅ **Migrating legacy data:** User has existing counts from Excel/paper
✅ **System bootstrap:** Initial setup before camera equipment ready
✅ **Small locations:** <100 plants, manual count faster than photo
✅ **Missing metadata:** Photo lacks GPS or config not set up yet

### Invalid Use Cases

❌ **Regular workflow:** Should not replace photo-based initialization
❌ **Large locations:** 1000+ plants, high error risk with manual counting
❌ **Audit trail:** Photo provides better proof of count accuracy
❌ **Estimation needed:** Cannot break down by size without ML

---

## Workflow Steps

### High-Level Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. USER ACTION: Navigate to storage location                   │
│    → Click "Manual Count" button                                │
│    → Fill form: Product, Packaging, Size (optional), Quantity  │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. FRONTEND: Validate form                                     │
│    → Quantity > 0                                               │
│    → Product and Packaging selected                             │
│    → POST /api/stock/manual                                     │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│ 3. API: Validate request (Pydantic schema)                     │
│    → ManualStockInitRequest schema                              │
│    → Required fields present                                    │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│ 4. SERVICE: CRITICAL VALIDATION                                │
│    → Get storage_location_config                                │
│    → IF config EXISTS:                                          │
│         IF config.product_id != request.product_id:             │
│            RAISE ProductMismatchException (HTTP 400)            │
│         IF config.packaging_id != request.packaging_id:         │
│            RAISE PackagingMismatchException (HTTP 400)          │
│    → ELSE (config missing):                                     │
│         ALLOW (creates initial config implicitly)               │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│ 5. SERVICE: Create stock_movement                              │
│    → movement_type: "manual_init"                               │
│    → quantity: request.quantity                                 │
│    → source_type: "manual"                                      │
│    → user_id: current authenticated user                        │
│    → is_inbound: true                                           │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│ 6. SERVICE: Create stock_batch                                 │
│    → batch_code: "LOC{location_id}-PROD{product_id}-{YYYYMMDD}-{seq}" │
│    → current_storage_bin_id: (from storage_location)            │
│    → product_id: request.product_id                             │
│    → product_size_id: request.product_size_id (optional)        │
│    → packaging_catalog_id: request.packaging_catalog_id         │
│    → quantity_initial: request.quantity                         │
│    → quantity_current: request.quantity                         │
│    → quality_score: NULL (no ML confidence)                     │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│ 7. REPOSITORY: Persist to PostgreSQL                           │
│    → INSERT stock_movements                                     │
│    → INSERT stock_batches                                       │
│    → COMMIT transaction                                         │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│ 8. RESPONSE: Return success                                    │
│    → HTTP 201 Created                                           │
│    → Include: stock_movement_id, stock_batch_id                 │
│    → Display success message to user                            │
└─────────────────────────────────────────────────────────────────┘
```

---

## Critical Validation Rules

### Rule 1: Product Match Validation

**CRITICAL:** If `storage_location_config` exists, the manually entered product MUST match the configured expected product.

**Why:** Prevents user errors (entering wrong plant species in wrong location).

**Example:**
```
Configuration:
  storage_location_id: 123
  product_id: 45 (Echeveria Golden)
  packaging_id: 12 (R7 pot)

User Input:
  storage_location_id: 123
  product_id: 50 (Sedum Blue) ← MISMATCH!
  packaging_id: 12

Result: HTTP 400 - ProductMismatchException
Message: "The product you entered (Sedum Blue) does not match the configured product for this location (Echeveria Golden). Please verify the location or update the configuration."
```

### Rule 2: Packaging Match Validation

**CRITICAL:** If `storage_location_config` exists, the manually entered packaging MUST match the configured expected packaging.

**Why:** Ensures inventory accuracy (can't mix different pot sizes in same location).

**Example:**
```
Configuration:
  packaging_id: 12 (R7 pot)

User Input:
  packaging_id: 15 (R10 pot) ← MISMATCH!

Result: HTTP 400 - PackagingMismatchException
Message: "The packaging you entered (R10 pot) does not match the configured packaging for this location (R7 pot)."
```

### Rule 3: Missing Configuration Handling

**Behavior:** If no `storage_location_config` exists, allow manual initialization and implicitly create configuration.

**Why:** Bootstrap scenario - user setting up system for first time.

**Example:**
```
No configuration exists for storage_location_id: 200

User Input:
  product_id: 30
  packaging_id: 8
  quantity: 500

Result:
  ✅ Create stock_movement
  ✅ Create stock_batch
  ✅ (Optional) Create storage_location_config with these values
```

### Rule 4: Quantity Validation

**CRITICAL:** Quantity must be > 0

**Why:** Manual initialization is for **initial counts**, not adjustments.

**Example:**
```
User Input:
  quantity: 0 ← INVALID!

Result: HTTP 422 - ValidationError
Message: "Quantity must be greater than 0"
```

---

## Database Operations

### Tables Affected

#### 1. stock_movements

**INSERT:**
```sql
INSERT INTO stock_movements (
    movement_id,              -- UUID
    batch_id,                 -- FK to stock_batches (created after batch insert)
    movement_type,            -- "manual_init"
    source_bin_id,            -- NULL (no source for initialization)
    destination_bin_id,       -- FK to storage_bin (derived from storage_location)
    quantity,                 -- User input
    user_id,                  -- Current authenticated user
    unit_price,               -- NULL or from price_list
    total_price,              -- quantity * unit_price
    reason_description,       -- "Initial manual count by user {name}"
    processing_session_id,    -- NULL (no photo processing)
    source_type,              -- "manual"
    is_inbound,               -- true
    created_at                -- NOW()
) VALUES (...);
```

**Key Differences from Photo Init:**
- ❌ No `processing_session_id` (NULL)
- ✅ `movement_type`: `"manual_init"` (not `"foto"`)
- ✅ `source_type`: `"manual"` (not `"ia"`)
- ✅ `reason_description`: Includes username for audit trail

#### 2. stock_batches

**INSERT:**
```sql
INSERT INTO stock_batches (
    batch_code,               -- "LOC123-PROD45-20251008-001"
    current_storage_bin_id,   -- FK to storage_bin
    product_id,               -- User input
    product_state_id,         -- From config or default
    product_size_id,          -- User input (optional)
    has_packaging,            -- true
    packaging_catalog_id,     -- User input
    quantity_initial,         -- User input
    quantity_current,         -- User input (same as initial)
    quantity_empty_containers,-- 0 (no ML detection)
    quality_score,            -- NULL (no ML confidence)
    planting_date,            -- User input (optional)
    germination_date,         -- NULL
    transplant_date,          -- NULL
    expected_ready_date,      -- NULL or calculated
    notes,                    -- User input (optional)
    custom_attributes,        -- {}
    created_at,               -- NOW()
    updated_at                -- NOW()
) VALUES (...);
```

**Key Differences from Photo Init:**
- ❌ No `quality_score` (NULL, no ML confidence)
- ❌ No `quantity_empty_containers` (0, no ML detection)
- ❌ Single batch (no grouping by size, user provides one count)

#### 3. NO INSERTS for:

- ❌ `photo_processing_sessions` (no photo)
- ❌ `detections` (no ML detections)
- ❌ `estimations` (no ML estimations)
- ❌ `s3_images` (no photo upload)
- ❌ `classifications` (no ML classification)

#### 4. OPTIONAL INSERT: storage_location_config

**IF missing configuration:**
```sql
INSERT INTO storage_location_config (
    storage_location_id,      -- From request
    product_id,               -- User input
    packaging_catalog_id,     -- User input
    expected_product_state_id,-- Default or user input
    area_cm2,                 -- From storage_location geometry
    active,                   -- true
    notes,                    -- "Auto-created from manual init"
    created_at,               -- NOW()
    updated_at                -- NOW()
) VALUES (...);
```

---

## API Endpoint

### POST /api/stock/manual

**Request:**
```json
{
  "storage_location_id": 123,
  "product_id": 45,
  "packaging_catalog_id": 12,
  "product_size_id": 3,        // Optional
  "quantity": 1500,
  "planting_date": "2025-09-15", // Optional
  "notes": "Initial count from legacy Excel file" // Optional
}
```

**Success Response (HTTP 201):**
```json
{
  "stock_movement_id": "550e8400-e29b-41d4-a716-446655440000",
  "stock_batch_id": 5432,
  "batch_code": "LOC123-PROD45-20251008-001",
  "quantity": 1500,
  "created_at": "2025-10-08T14:30:00Z",
  "message": "Manual stock initialization completed successfully"
}
```

**Error Response (HTTP 400 - Product Mismatch):**
```json
{
  "error": "Product mismatch",
  "detail": "The product you entered (Sedum Blue) does not match the configured product for this location (Echeveria Golden). Please verify the location or update the configuration.",
  "expected_product_id": 45,
  "entered_product_id": 50
}
```

**Error Response (HTTP 404 - Location Not Found):**
```json
{
  "error": "Storage location not found",
  "detail": "The storage location with ID 999 does not exist",
  "storage_location_id": 999
}
```

---

## Differences from Photo Initialization

| Aspect | Photo Initialization | Manual Initialization |
|--------|---------------------|----------------------|
| **Input** | Photo file (multipart) | JSON request body |
| **Processing** | Async (Celery) | Synchronous (immediate) |
| **ML Pipeline** | ✅ YOLO + SAHI | ❌ None |
| **Detections** | ✅ Individual plants | ❌ None |
| **Estimations** | ✅ Area-based counts | ❌ None |
| **Visualization** | ✅ Generated image | ❌ None |
| **S3 Upload** | ✅ Original + processed | ❌ None |
| **GPS Lookup** | ✅ From EXIF | ❌ N/A (user specifies location) |
| **Validation** | ⚠️ Warning if config mismatch | ❌ Hard error if config mismatch |
| **Accuracy** | 95%+ (ML) | Depends on user |
| **Speed** | 5-10 minutes | Seconds |
| **Batch Creation** | Multiple (by size) | Single (user count) |
| **Quality Score** | ✅ ML confidence | ❌ NULL |
| **Stock Movement Type** | `"foto"` | `"manual_init"` |
| **Source Type** | `"ia"` | `"manual"` |

---

## Error Handling

### Error Types

| Error | HTTP Code | Cause | Solution |
|-------|-----------|-------|----------|
| **ProductMismatchException** | 400 | User entered wrong product | Update config OR re-enter correct product |
| **PackagingMismatchException** | 400 | User entered wrong packaging | Update config OR re-enter correct packaging |
| **StorageLocationNotFoundException** | 404 | Invalid location_id | Verify location exists |
| **ProductNotFoundException** | 404 | Invalid product_id | Verify product exists |
| **PackagingNotFoundException** | 404 | Invalid packaging_id | Verify packaging exists |
| **ValidationError** | 422 | Invalid request format | Check required fields |
| **UnauthorizedException** | 401 | Not logged in | Login required |
| **ForbiddenException** | 403 | Insufficient permissions | Admin/supervisor role needed |

### Recovery Strategies

**Product Mismatch:**
```
Option 1: Update storage_location_config to match new product
  POST /api/configurations/storage-location
  { "storage_location_ids": [123], "product_id": 50 }

Option 2: Re-enter manual count with correct product
  Verify which product should be in this location
  Re-submit POST /api/stock/manual with correct product_id
```

**Missing Location:**
```
Create the storage_location first:
  POST /api/locations/storage-location
  { "storage_area_id": 5, "code": "LOC-123", ... }
Then retry manual initialization
```

---

## Implementation Notes

### Service Layer

**File:** `app/services/stock_movement_service.py`

**Method:** `async def create_manual_initialization(request: ManualStockInitRequest)`

**Pseudocode:**
```python
async def create_manual_initialization(self, request: ManualStockInitRequest):
    # 1. Get storage location (verify exists)
    location = await self.location_service.get(request.storage_location_id)
    if not location:
        raise StorageLocationNotFoundException(request.storage_location_id)

    # 2. Get configuration (CRITICAL validation)
    config = await self.config_service.get_by_location(request.storage_location_id)

    if config:
        # Config exists - validate match
        if config.product_id != request.product_id:
            raise ProductMismatchException(
                expected=config.product_id,
                actual=request.product_id
            )

        if config.packaging_catalog_id != request.packaging_catalog_id:
            raise PackagingMismatchException(
                expected=config.packaging_catalog_id,
                actual=request.packaging_catalog_id
            )
    else:
        # No config - optionally create one
        await self.config_service.create({
            "storage_location_id": request.storage_location_id,
            "product_id": request.product_id,
            "packaging_catalog_id": request.packaging_catalog_id,
            "expected_product_state_id": request.product_state_id or DEFAULT_STATE,
            "notes": "Auto-created from manual initialization"
        })

    # 3. Create stock movement
    movement = await self.repo.create({
        "movement_id": uuid4(),
        "movement_type": "manual_init",
        "quantity": request.quantity,
        "source_type": "manual",
        "is_inbound": True,
        "user_id": current_user.id,
        "reason_description": f"Initial manual count by {current_user.name}",
        # ... other fields
    })

    # 4. Create stock batch (via batch_service)
    batch = await self.batch_service.create_from_movement(movement)

    # 5. Return response
    return ManualStockInitResponse.from_models(movement, batch)
```

### Controller Layer

**File:** `app/controllers/stock_controller.py`

**Route:** `POST /api/stock/manual`

**Pseudocode:**
```python
@router.post("/stock/manual", status_code=status.HTTP_201_CREATED)
async def initialize_stock_manually(
    request: ManualStockInitRequest,
    service: StockMovementService = Depends(get_stock_service),
    current_user: User = Depends(get_current_user)
):
    """
    Initialize stock manually (no photo/ML).

    CRITICAL: Validates product/packaging against storage_location_config.
    """
    try:
        result = await service.create_manual_initialization(request)
        return result
    except ProductMismatchException as e:
        raise HTTPException(status_code=400, detail=e.user_message)
    except PackagingMismatchException as e:
        raise HTTPException(status_code=400, detail=e.user_message)
    except StorageLocationNotFoundException as e:
        raise HTTPException(status_code=404, detail=e.user_message)
```

---

## Next Steps

- **Detailed Diagrams:** See [../../flows/manual_stock_initialization/](../../flows/manual_stock_initialization/README.md)
- **API Implementation:** See [../../api/endpoints_stock.md](../../api/endpoints_stock.md)
- **Backend Services:** See [../../backend/service_layer.md](../../backend/service_layer.md)

---

**Document Owner:** DemeterAI Engineering Team
**Status:** NEW - Approved for implementation
**Last Reviewed:** 2025-10-08
