# ML Storage Bin Persistence - Quick Reference Guide

**For**: Developers debugging "StorageBin not found" errors in ML processing  
**Time to read**: 5 minutes  
**Actionable**: YES - includes exact fixes

---

## The Bug in 30 Seconds

```python
# Line 2148 in app/tasks/ml_tasks.py
current_storage_bin_id = created_bin_ids[0] if created_bin_ids else 1  # ❌ BUG HERE
```

**Problem**: When `_create_storage_bins()` fails, `created_bin_ids` is empty, so it defaults to `bin_id=1`. But no StorageBin with ID=1 exists in the database, causing a FK constraint violation.

**Why it fails**: `_create_storage_bins()` exceptions are NOT caught, so errors are silently lost.

---

## Critical Code Locations

| What | File | Line | Status |
|------|------|------|--------|
| **Hardcoded fallback** | `app/tasks/ml_tasks.py` | 2148 | ❌ BUG |
| **No try/except** | `app/tasks/ml_tasks.py` | 2065-2073 | ❌ BUG |
| **Create bins func** | `app/tasks/ml_tasks.py` | 1800-1968 | ✅ CODE OK, DATA MISSING |
| **StorageBin model** | `app/models/storage_bin.py` | Full | ✅ OK |

---

## Required Test Data (Minimum)

```sql
-- 1. Warehouse
INSERT INTO warehouses (code, name, warehouse_type, geojson_coordinates)
VALUES ('WH1', 'Warehouse 1', 'greenhouse', 
        ST_GeomFromText('POLYGON((0 0, 100 0, 100 100, 0 100, 0 0))', 4326));

-- 2. Storage Area
INSERT INTO storage_areas (warehouse_id, code, name, area_type, geojson_coordinates)
VALUES (1, 'AREA1', 'Area 1', 'greenhouse',
        ST_GeomFromText('POLYGON((0 0, 50 0, 50 100, 0 100, 0 0))', 4326));

-- 3. Storage Location (CRITICAL - must exist with same ID as PhotoProcessingSession.storage_location_id)
INSERT INTO storage_locations (storage_area_id, code, name, location_type, geojson_coordinates)
VALUES (1, 'LOC1', 'Location 1', 'growing_bed',
        ST_GeomFromText('POINT(25 50)', 4326));

-- 4. Product
INSERT INTO products (product_category_id, product_family_id, code, name, current_height_mm)
VALUES (1, 1, 'PROD1', 'Product 1', 50)
ON CONFLICT DO NOTHING;

-- 5. User (for StockMovement.user_id)
INSERT INTO users (username, email, hashed_password, is_active)
VALUES ('ml_user', 'ml@example.com', 'pwd', TRUE)
ON CONFLICT DO NOTHING;
```

---

## The Fix (Priority Order)

### 1. IMMEDIATE: Add Error Handling (Line ~2065)

**Before**:
```python
created_bin_ids = _create_storage_bins(
    db_session=db_session,
    session_id=session_id,
    storage_location_id=storage_location_id,
    segments=segments,
)
```

**After**:
```python
try:
    created_bin_ids = _create_storage_bins(
        db_session=db_session,
        session_id=session_id,
        storage_location_id=storage_location_id,
        segments=segments,
    )
except Exception as e:
    logger.error(
        f"[Session {session_id}] Failed to create StorageBins: {e}",
        extra={"session_id": session_id, "error": str(e)},
        exc_info=True,
    )
    raise ValueError(f"Cannot create StorageBins: {str(e)}") from e
```

### 2. IMMEDIATE: Remove Hardcoded Fallback (Line ~2148)

**Before**:
```python
current_storage_bin_id = created_bin_ids[0] if created_bin_ids else 1
```

**After**:
```python
if not created_bin_ids:
    raise ValueError(
        f"No StorageBins created for session {session_id}. "
        f"Cannot proceed without valid bin IDs. "
        f"Check that storage_location_id={storage_location_id} exists."
    )
current_storage_bin_id = created_bin_ids[0]
```

### 3. TESTING: Verify Data Setup

```bash
# Run this in psql
SELECT location_id, code FROM storage_locations;
SELECT * FROM products WHERE id = 1;
SELECT * FROM product_states WHERE product_state_id = 3;
```

---

## Debug Flow

1. **ML segments generated?** Check ML child task output ✅
2. **_create_storage_bins() called?** Add logging to confirm ⚠️
3. **StorageLocation exists?** `SELECT * FROM storage_locations WHERE location_id = X` ⚠️
4. **StorageBinType created?** `SELECT * FROM storage_bin_types WHERE category IN ('segment', 'box', ...)` ⚠️
5. **StorageBins created?** `SELECT * FROM storage_bins ORDER BY created_at DESC LIMIT 5` ⚠️
6. **StockBatch linked correctly?** `SELECT * FROM stock_batches WHERE current_storage_bin_id = 1` ⚠️

---

## Error Messages & Meanings

| Error | Means | Fix |
|-------|-------|-----|
| `foreign key violation... storage_bins.bin_id (1)` | Hardcoded fallback hit | Add error handling #1 |
| `StorageLocation X not found` | Storage data missing | Run test data setup |
| `StorageBinType with category Y not found` | Enum issue | Auto-creates, check logs |
| `Cannot parse bin code format` | Code generation failed | Check `_map_container_type_to_bin_category()` |

---

## Files Modified in This Investigation

```
Created: /home/lucasg/proyectos/DemeterDocs/claude_analysis/
  - ML_STORAGE_BIN_PERSISTENCE_ROOT_CAUSE_ANALYSIS.md (full 10-section report)
  - ML_STORAGE_BIN_QUICK_REFERENCE.md (this file)
```

---

## Key Insights

1. **Problem is NOT in the model** - StorageBin model is correct
2. **Problem is NOT in the logic** - `_create_storage_bins()` logic is correct
3. **Problem IS in error handling** - No try/except around critical section
4. **Problem IS in test data** - StorageLocation must exist before ML processing
5. **Problem IS in fallback** - Hardcoded `bin_id=1` doesn't exist

---

## Next Steps

1. [ ] Apply fix #1 (add error handling)
2. [ ] Apply fix #2 (remove hardcoded fallback)
3. [ ] Run test data setup SQL
4. [ ] Trigger ML pipeline with test image
5. [ ] Verify StorageBins created: `SELECT * FROM storage_bins ORDER BY created_at DESC LIMIT 5`
6. [ ] Verify StockBatch created with valid FK
7. [ ] Check PhotoProcessingSession status = "completed"

---

**Generated**: 2025-10-24 Claude Code Analysis  
**Confidence**: HIGH - Detailed codebase investigation with line references
