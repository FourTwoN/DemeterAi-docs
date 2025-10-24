# ML Pipeline Persistence Fix - Testing Guide

**Date**: 2025-10-24
**Related**: ML_PERSIST_FIX_SUMMARY.md

---

## Quick Verification Steps

### 1. Import Test (Already Passed ✅)

```bash
python -c "from app.tasks.ml_tasks import _persist_ml_results; print('✅ Import successful')"
```

**Status**: ✅ PASSED

---

## Expected Behavior

### Scenario 1: No StorageLocationConfig (Current State)

**Database State**:
- storage_location_config table: EMPTY
- packaging_catalog table: EMPTY
- products table: 4 entries (IDs 1-4)
- product_states table: 11 entries (IDs 1-11)

**Expected Behavior**:
1. Code detects no StorageLocationConfig for storage_location_id
2. Falls back to defaults:
   - product_id = 1 (Mammillaria)
   - product_state_id = 3 (SEEDLING)
   - packaging_catalog_id = None
3. Logs warning: "No StorageLocationConfig found, using fallback values"
4. Creates StockBatch with has_packaging=False, packaging_catalog_id=None
5. Creates Classification with product_id=1, packaging_catalog_id=None
6. Successfully persists all detections and estimations
7. **No foreign key violations**

**Database Records Created**:
```sql
-- StockBatch
INSERT INTO stock_batches (
    batch_code,
    current_storage_bin_id,
    product_id,
    product_state_id,
    quantity_initial,
    quantity_current,
    quantity_empty_containers,
    has_packaging,
    packaging_catalog_id
) VALUES (
    'ML-SESSION-1-20251024123456',
    1,
    1,  -- Mammillaria
    3,  -- SEEDLING
    150,
    150,
    0,
    FALSE,  -- ✅ No packaging
    NULL    -- ✅ NULL allowed when has_packaging=FALSE
);

-- Classification
INSERT INTO classifications (
    product_id,
    packaging_catalog_id,
    product_conf,
    packaging_conf,
    model_version,
    name,
    description
) VALUES (
    1,     -- Mammillaria
    NULL,  -- ✅ NULL allowed (CHECK constraint satisfied by product_id)
    70,
    NULL,  -- ✅ NULL when no packaging
    'yolov11n-seg-v1.0.0',
    'ML Classification - Product 1',
    'Auto-generated classification for ML pipeline (product_id=1, packaging_catalog_id=None)'
);
```

**Constraints Satisfied**:
- ✅ StockBatch CHECK: `has_packaging=FALSE OR (has_packaging=TRUE AND packaging_catalog_id IS NOT NULL)`
  - has_packaging=FALSE, so packaging_catalog_id can be NULL
- ✅ Classification CHECK: At least ONE of (product_id, packaging_catalog_id, product_size_id) NOT NULL
  - product_id=1 (NOT NULL), so constraint satisfied

---

### Scenario 2: With StorageLocationConfig (Future State)

**Database State**:
```sql
INSERT INTO storage_location_config (
    storage_location_id,
    product_id,
    expected_product_state_id,
    packaging_catalog_id,
    active
) VALUES (
    1,   -- Storage location ID
    2,   -- Echeveria
    4,   -- YOUNG_PLANT
    5,   -- Some packaging type
    TRUE
);
```

**Expected Behavior**:
1. Code finds StorageLocationConfig for storage_location_id=1
2. Uses config values:
   - product_id = 2 (Echeveria)
   - product_state_id = 4 (YOUNG_PLANT)
   - packaging_catalog_id = 5
3. Logs info: "Using StorageLocationConfig: product_id=2, product_state_id=4, packaging_catalog_id=5"
4. Creates StockBatch with has_packaging=True, packaging_catalog_id=5
5. Creates Classification with product_id=2, packaging_catalog_id=5
6. Successfully persists all records

---

## Manual Testing Steps

### Step 1: Verify Current Database State

```bash
# Connect to test database
docker exec -it demeterai-db-test psql -U demeter_test -d demeterai_test

# Check tables
SELECT COUNT(*) FROM storage_location_config;  -- Should be 0
SELECT COUNT(*) FROM packaging_catalog;        -- Should be 0
SELECT COUNT(*) FROM products;                 -- Should be 4
SELECT COUNT(*) FROM product_states;           -- Should be 11

# Verify product IDs exist
SELECT id, name FROM products;
-- Expected:
-- 1 | Mammillaria
-- 2 | Echeveria
-- 3 | Haworthia
-- 4 | Crassula

# Verify product_state_id=3 exists
SELECT id, state_name FROM product_states WHERE id = 3;
-- Expected: 3 | SEEDLING
```

### Step 2: Run ML Pipeline

```bash
# Run the ML task (replace with actual test command)
# Example:
python -c "
from app.tasks.ml_tasks import process_ml_photo_task
# Trigger ML processing with a test image
"
```

### Step 3: Verify Logs

Look for these log messages:

**Expected WARNING** (no config found):
```
[Session X] No StorageLocationConfig found for storage_location_id=Y, using fallback values:
product_id=1, product_state_id=3, packaging_catalog_id=None
```

**Expected INFO** (StockBatch created):
```
[Session X] Created StockBatch: batch_id=Z, batch_code=ML-SESSION-X-...,
current_storage_bin_id=1, product_id=1, product_state_id=3, has_packaging=False
```

**Expected INFO** (Classification created):
```
[Session X] Created new Classification: classification_id=A, product_id=1, packaging_catalog_id=None
```

**Expected SUCCESS**:
```
[Session X] Successfully committed all ML results to database
```

### Step 4: Verify Database Records

```sql
-- Check StockBatch
SELECT
    id,
    batch_code,
    product_id,
    product_state_id,
    has_packaging,
    packaging_catalog_id,
    quantity_initial,
    quantity_current
FROM stock_batches
ORDER BY id DESC
LIMIT 1;

-- Expected:
-- product_id = 1
-- product_state_id = 3
-- has_packaging = FALSE
-- packaging_catalog_id = NULL
-- quantity > 0

-- Check Classification
SELECT
    classification_id,
    product_id,
    packaging_catalog_id,
    product_conf,
    packaging_conf,
    model_version,
    name
FROM classifications
ORDER BY classification_id DESC
LIMIT 1;

-- Expected:
-- product_id = 1
-- packaging_catalog_id = NULL
-- product_conf = 70
-- packaging_conf = NULL
-- model_version = 'yolov11n-seg-v1.0.0'
-- name = 'ML Classification - Product 1'

-- Check Detections
SELECT COUNT(*) FROM detections WHERE session_id = X;
-- Should match number of detected plants

-- Check Estimations
SELECT COUNT(*) FROM estimations WHERE session_id = X;
-- Should match number of estimated bands

-- Verify foreign keys
SELECT
    d.id,
    d.session_id,
    d.stock_movement_id,
    d.classification_id,
    c.product_id,
    c.packaging_catalog_id
FROM detections d
JOIN classifications c ON d.classification_id = c.classification_id
WHERE d.session_id = X
LIMIT 5;

-- All should have classification_id pointing to valid classification
```

---

## Error Scenarios (Should NOT Occur)

### ❌ Foreign Key Violation (FIXED)

**Before Fix**:
```
psycopg2.errors.ForeignKeyViolation: insert or update on table "classifications"
violates foreign key constraint "classifications_packaging_catalog_id_fkey"
DETAIL: Key (packaging_catalog_id)=(1) is not present in table "packaging_catalog".
```

**After Fix**: This error should NEVER occur because we now use `packaging_catalog_id=None`

### ❌ CHECK Constraint Violation (Prevented)

**Scenario**: has_packaging=TRUE but packaging_catalog_id=NULL
```sql
-- This would fail:
INSERT INTO stock_batches (...) VALUES (..., TRUE, NULL);
-- Error: ck_stock_batch_packaging_required
```

**Our Code Prevents This**:
```python
has_packaging=bool(packaging_catalog_id)  # False when None, True when not None
```

---

## Success Criteria

After running the ML pipeline, ALL of these must be TRUE:

- [ ] ✅ No foreign key violations in logs/errors
- [ ] ✅ StockBatch created with valid product_id and product_state_id
- [ ] ✅ StockBatch has `has_packaging=False` and `packaging_catalog_id=NULL`
- [ ] ✅ Classification created with `product_id=1` and `packaging_catalog_id=NULL`
- [ ] ✅ All detections persisted with valid classification_id
- [ ] ✅ All estimations persisted with valid classification_id
- [ ] ✅ PhotoProcessingSession updated with totals
- [ ] ✅ Logs show warning about fallback values
- [ ] ✅ Logs show successful commit message

---

## Rollback Plan

If the fix causes issues:

1. **Revert the changes**:
   ```bash
   git checkout HEAD -- app/tasks/ml_tasks.py
   ```

2. **Temporary workaround** (not recommended):
   ```sql
   -- Populate packaging_catalog with dummy data
   INSERT INTO packaging_catalog (name, description) VALUES ('Default', 'Temporary');
   ```

3. **Report the issue** with:
   - Full error logs
   - Database state (counts from all tables)
   - Specific ML pipeline input that caused the failure

---

## Future Testing

### With Configuration Data

Once you populate storage_location_config:

```sql
INSERT INTO storage_location_config (
    storage_location_id,
    product_id,
    expected_product_state_id,
    packaging_catalog_id,
    active
) VALUES (
    1,    -- Your test storage location
    2,    -- Echeveria
    4,    -- YOUNG_PLANT
    NULL, -- Still no packaging
    TRUE
);
```

**Expected Behavior**:
- Code should use config values
- product_id = 2 (from config)
- product_state_id = 4 (from config)
- packaging_catalog_id = NULL (from config)
- Log shows "Using StorageLocationConfig" (not warning)

---

## Monitoring in Production

Watch for these log patterns:

**Good** (using configuration):
```
grep "Using StorageLocationConfig" logs/celery.log | wc -l
# High count = good
```

**Warning** (using fallback):
```
grep "No StorageLocationConfig found" logs/celery.log | wc -l
# Should decrease as you populate configuration
```

**Error** (foreign key violation):
```
grep "ForeignKeyViolation.*packaging_catalog_id" logs/celery.log | wc -l
# Should be 0 after fix
```

---

## Contact

If you encounter issues:
1. Check this guide's troubleshooting section
2. Review ML_PERSIST_FIX_SUMMARY.md for implementation details
3. Check database constraints in database/database.mmd
4. Review model definitions in app/models/

**Status**: ✅ Ready for Testing
