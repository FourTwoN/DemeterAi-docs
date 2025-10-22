# Manual Stock Initialization Workflow

**Version:** 1.0
**Last Updated:** 2025-10-08
**Status:** NEW - Alternative to photo-based initialization

---

## Overview

This workflow documents the **manual stock initialization process**, an alternative method to
initialize inventory for a storage location without using photos or ML processing.

### Purpose

- Allow users to enter pre-counted stock directly
- Support legacy data migration from Excel/paper systems
- Provide fallback when photo system unavailable
- Enable quick entry for small locations (<100 plants)

### Scope

- **Input:** User enters count via UI form
- **Validation:** CRITICAL configuration checks (product + packaging match)
- **Output:** `stock_movements` (type: `"manual_init"`) + `stock_batches`
- **No ML:** No detections, estimations, or photo processing

---

## Workflow Components

### Diagrams

1. **[00_comprehensive_view.mmd](./00_comprehensive_view.md)** - Complete end-to-end flow (
   high-level)
2. **[01_api_validation.mmd](./01_api_validation.md)** - API endpoint validation logic
3. **[02_config_check.mmd](./02_config_check.md)** - Configuration validation (CRITICAL)
4. **[03_batch_creation.mmd](./03_batch_creation.md)** - Stock batch creation process

---

## Key Features

### 1. Configuration Validation (CRITICAL)

**If `storage_location_config` exists:**

- ✅ Validate `product_id` matches expected product
- ✅ Validate `packaging_catalog_id` matches expected packaging
- ❌ **Hard error** if mismatch (HTTP 400)

**Why:** Prevents user errors (wrong plant species in wrong location).

**Example:**

```
Config: Echeveria Golden in R7 pot
User Input: Sedum Blue in R7 pot
Result: HTTP 400 - "Product mismatch"
```

### 2. No ML Processing

**Unlike photo initialization:**

- ❌ No YOLO segmentation/detection
- ❌ No SAHI slicing
- ❌ No area estimation
- ❌ No detections/estimations tables
- ❌ No S3 uploads
- ❌ No photo_processing_sessions

**Result:** Faster (seconds vs. 5-10 minutes), but less detailed.

### 3. Single Batch Creation

**User provides one total count:**

- Creates single `stock_batch` record
- No breakdown by size (unless user explicitly specifies size)
- `quality_score` is NULL (no ML confidence)

### 4. Audit Trail

**Full traceability:**

- `stock_movements.source_type = "manual"`
- `stock_movements.movement_type = "manual_init"`
- `stock_movements.reason_description` includes username
- `created_at` timestamp

---

## When to Use

### Valid Use Cases

✅ **Legacy data migration:** Import existing counts from Excel
✅ **System bootstrap:** Initial setup before camera ready
✅ **Small locations:** <100 plants, manual faster
✅ **Missing metadata:** Photo lacks GPS or config not set

### Invalid Use Cases

❌ **Regular workflow:** Should not replace photo-based method
❌ **Large locations:** 1000+ plants, high error risk
❌ **Audit requirements:** Photo provides better proof
❌ **Size estimation:** Cannot break down by size without ML

---

## Data Flow

```
POST /api/stock/manual
  ↓
Controller (validation)
  ↓
Service (config check) ← CRITICAL VALIDATION
  ↓
Repository (INSERT stock_movements + stock_batches)
  ↓
PostgreSQL (COMMIT)
  ↓
HTTP 201 Created
```

---

## Database Operations

### INSERT Operations

1. **stock_movements**
    - `movement_type`: `"manual_init"`
    - `source_type`: `"manual"`
    - `processing_session_id`: NULL
    - `is_inbound`: true

2. **stock_batches**
    - `quantity_initial`: user input
    - `quantity_current`: user input
    - `quality_score`: NULL (no ML)
    - `quantity_empty_containers`: 0

3. **OPTIONAL: storage_location_config** (if missing)
    - Auto-create with user-provided product/packaging

### NO INSERT Operations

- ❌ `photo_processing_sessions`
- ❌ `detections`
- ❌ `estimations`
- ❌ `s3_images`
- ❌ `classifications`

---

## Error Handling

### Critical Errors

| Error                                | HTTP | Message                                |
|--------------------------------------|------|----------------------------------------|
| **ProductMismatchException**         | 400  | Product does not match configuration   |
| **PackagingMismatchException**       | 400  | Packaging does not match configuration |
| **StorageLocationNotFoundException** | 404  | Location not found                     |
| **ValidationError**                  | 422  | Invalid request format                 |

### Recovery

**Product Mismatch:**

1. Update `storage_location_config` to new product, OR
2. Re-enter manual count with correct product

**Missing Location:**

1. Create `storage_location` first
2. Retry manual initialization

---

## Integration with Monthly Reconciliation

Manual initialization **starts the baseline** for monthly reconciliation, just like photo
initialization:

```
Manual Init (baseline) → Movements (plantado, muerte) → Month-end Photo → Sales Calculation
```

**Example:**

```
Oct 1:  Manual init = 5,000 plants (manual_init)
Oct:    +200 plantado, -100 muerte
Oct 31: Photo = 4,800 plants
        Sales = (5,000 + 200 - 100) - 4,800 = 300 plants
```

---

## Performance

| Aspect              | Photo Init        | Manual Init            |
|---------------------|-------------------|------------------------|
| **Processing Time** | 5-10 minutes      | <5 seconds             |
| **Accuracy**        | 95%+ (ML)         | Depends on user        |
| **Synchronous**     | ❌ Async (Celery)  | ✅ Immediate            |
| **Traceability**    | High (detections) | Medium (movement only) |

---

## Security & Authorization

**Required Permissions:**

- User must be authenticated (JWT token)
- Role: Admin, Supervisor, or Worker
- Viewer role: **cannot** create manual initializations

**Audit Log:**

- All manual initializations logged with username
- Timestamp recorded
- Cannot be deleted (only corrected via `ajuste` movements)

---

## Next Steps

- **Implementation:**
  See [../../engineering_plan/workflows/manual_initialization.md](../../engineering_plan/workflows/manual_initialization.md)
- **API Spec:**
  See [../../engineering_plan/api/endpoints_stock.md](../../engineering_plan/api/endpoints_stock.md)
- **Backend Services:**
  See [../../engineering_plan/backend/service_layer.md](../../engineering_plan/backend/service_layer.md)

---

**Document Owner:** DemeterAI Engineering Team
**Status:** NEW - Approved for implementation
**Mermaid Version:** v11.3.0+
**Last Reviewed:** 2025-10-08
