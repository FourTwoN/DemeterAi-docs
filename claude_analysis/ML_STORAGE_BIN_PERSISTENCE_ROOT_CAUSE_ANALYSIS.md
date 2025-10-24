# ML Pipeline Storage Bin Persistence - Comprehensive Root Cause Analysis

**Date**: 2025-10-24  
**Severity**: CRITICAL - Production Bug in ML Processing  
**Status**: Active Investigation  
**Discoverer**: Claude Code (Thorough Codebase Analysis)  

---

## Executive Summary

The ML pipeline in DemeterAI v2.0 is **failing to create StorageBin records** when processing photos, leading to a cascade of FK constraint violations. The error manifests as **"StorageBin ID=1 not found"** when the system tries to default to a non-existent bin.

**Root Cause Chain**:
1. ML segments are generated ✅
2. StorageBin creation FAILS silently ❌ → Segments not persisted
3. StockBatch tries to use fallback `bin_id=1` ❌ → FK violation
4. StockMovement creation FAILS ❌ → Detections/Estimations can't be linked
5. Photography session marked FAILED ❌

**Critical Issue**: `_create_storage_bins()` function exists but is **NEVER SUCCESSFULLY CREATING BINS**. The `created_bin_ids` list is empty, forcing fallback to hardcoded `bin_id=1` which doesn't exist.

---

## 1. Where Exactly the Error Occurs

### 1.1 Primary Failure Point: Hardcoded Fallback (Line 2148)

**File**: `/home/lucasg/proyectos/DemeterDocs/app/tasks/ml_tasks.py`  
**Function**: `_persist_ml_results()`  
**Line**: 2148

```python
# Use first created bin_id, or default to 1 if no bins created
current_storage_bin_id = created_bin_ids[0] if created_bin_ids else 1
```

**Problem**: 
- If `created_bin_ids` is empty (which it is), defaults to `bin_id=1`
- No StorageBin with ID=1 exists in production database
- StockBatch is created with FK to non-existent bin
- PostgreSQL FK constraint violation occurs

### 1.2 Why `created_bin_ids` is Empty

**Function**: `_create_storage_bins()` (lines 1800-1968)

```python
created_bin_ids: list[int] = []
# ... loops through segments ...
created_bin_ids.append(storage_bin.bin_id)
return created_bin_ids
```

**Possible Failure Points**:

1. **Storage location not found** (Line 1861-1865):
```python
storage_location = (
    db_session.query(StorageLocation).filter_by(location_id=storage_location_id).first()
)
if not storage_location:
    raise ValueError(f"StorageLocation {storage_location_id} not found")
```

2. **StorageBinType creation fails** (Lines 1885-1908):
```python
bin_type = db_session.query(StorageBinType).filter_by(category=bin_category).first()
if not bin_type:
    # Create default StorageBinType if not exists
    bin_type = StorageBinType(
        code=bin_type_code,
        name=f"ML-Detected {bin_category.capitalize()}",
        category=bin_category,
        is_grid=False,
        description=f"Auto-generated bin type for ML-detected {bin_category} containers",
    )
    db_session.add(bin_type)
    db_session.flush()
    db_session.refresh(bin_type)
```

3. **StorageBin creation fails** (Lines 1932-1943):
```python
storage_bin = StorageBin(
    storage_location_id=storage_location_id,
    storage_bin_type_id=bin_type.bin_type_id,
    code=bin_code,
    label=f"ML {container_type.capitalize()} #{idx}",
    description=f"ML-detected {container_type} from session {session_id} (confidence: {confidence:.3f})",
    position_metadata=position_metadata,
    status="active",
)
db_session.add(storage_bin)
db_session.flush()
db_session.refresh(storage_bin)
```

**Exception Handling**: If ANY of these operations raise an Exception, it's **not caught** in `_persist_ml_results()`. The error propagates up, marking the session as FAILED.

### 1.3 Call Chain Flow

```
ml_aggregation_callback() [line 605]
    ↓
_persist_ml_results() [line 1971]
    ↓
_create_storage_bins() [line 1800]
    ↓ (IF SUCCEEDS) → returns [bin_id_1, bin_id_2, ...]
    ✅ created_bin_ids = [1, 2, 3]
    ↓ (IF FAILS) → Exception raised
    ❌ created_bin_ids = [] (empty)
        ↓
        caught somewhere?
        NO! No try/except wrapping _create_storage_bins() call
        ↓
    Exception propagates to ml_aggregation_callback()
    ↓
    Session marked as "failed"
```

---

## 2. Missing Data in Database

### 2.1 StorageLocation Required

**Model**: `/home/lucasg/proyectos/DemeterDocs/app/models/storage_location.py`

**Requirements for StorageBin creation**:
- Must have a parent StorageLocation
- Must have valid `location_id` (PK)
- Inherited from Warehouse → StorageArea hierarchy

**Test data requirement**:
```python
# Must exist in database
SELECT * FROM storage_locations WHERE location_id = <storage_location_id>;
```

### 2.2 StorageBinType Enum Categories

**Model**: `/home/lucasg/proyectos/DemeterDocs/app/models/storage_bin_type.py`

**BinCategoryEnum values**:
- `segment` (default from ML)
- `box` (cajon in Spanish)
- `plug` (pequeños plantones)
- `seedling_tray` (almacigo)
- `pot` (maceta)

**Mapping function** (lines 176-212 in ml_tasks.py):
```python
def _map_container_type_to_bin_category(container_type: str) -> str:
    mapping = {
        "segment": "segment",
        "box": "box",
        "cajon": "box",
        "plug": "plug",
        "almacigo": "seedling_tray",
    }
    normalized = container_type.lower().strip()
    return mapping.get(normalized, "segment")
```

**Auto-creation mechanism** (lines 1885-1908):
- If StorageBinType with given category doesn't exist
- Creates it automatically with generated code
- Example: `ML_SEGMENT_DEFAULT` for "segment" category

### 2.3 What Data IS Required to Exist

**MUST EXIST**:
1. PhotoProcessingSession with valid `storage_location_id`
2. StorageLocation that exists in database
3. Warehouse → StorageArea → StorageLocation hierarchy chain

**AUTO-CREATED IF MISSING**:
1. StorageBinType (auto-created with sensible defaults)
2. StorageBin (created from ML segments)
3. StockBatch (created for batch tracking)
4. StockMovement (created for movement tracking)

---

## 3. Code Architecture for StorageBin Creation

### 3.1 ML Pipeline Data Flow

```
Photo Upload
    ↓
ml_parent_task()
    - Updates PhotoProcessingSession.status = "processing"
    - Spawns child tasks (one per image)
    - Creates chord: [child_task_1, child_task_2, ...] → callback
    ↓
ml_child_task() [GPU Queue] ✅ WORKS
    - Loads image (PostgreSQL → /tmp → S3 cache)
    - Runs YOLO segmentation
    - Outputs: {"container_type": "segment", "bbox": [...], "confidence": 0.92, ...}
    - Returns: {"detections": [...], "estimations": [...], "segments": [...]}
    ↓
ml_aggregation_callback() [CPU Queue]
    - Aggregates results from all children
    - Extracts: all_detections, all_estimations, all_segments
    - Retrieves: storage_location_id from PhotoProcessingSession
    ↓
_persist_ml_results()
    - Step 0: Validate storage_location_id
    - Step 0b: Create StorageBins from ML segments ❌ FAILS HERE
    - Step 1: Create StockBatch (needs valid bin_id)
    - Step 2: Create StockMovement
    - Step 3: Get/create Classification
    - Step 4-7: Bulk insert Detections/Estimations
```

### 3.2 StorageBin Creation Process

**Input**: 
```python
segments = [
    {
        "container_type": "segment",
        "bbox": [0.1, 0.2, 0.3, 0.4],  # Normalized coords
        "polygon": [[100, 200], [300, 200], [300, 400], [100, 400]],
        "area_pixels": 40000,
        "confidence": 0.92
    },
    ...
]
```

**Processing**:
1. Validate StorageLocation exists
2. For each segment:
   a. Map `container_type` → `bin_category` (segment → segment)
   b. Get or create StorageBinType
   c. Generate unique bin code: `{location_code}-ML-{container_type}{idx}-{timestamp}`
   d. Create position_metadata JSONB (full ML output)
   e. Create StorageBin record
   f. Collect bin_id
3. Return list of created bin_ids

**Output**:
```python
[1, 2, 3]  # List of created StorageBin IDs
```

---

## 4. Models and Schema Details

### 4.1 StorageBin Model

**File**: `/home/lucasg/proyectos/DemeterDocs/app/models/storage_bin.py`

**Key Columns**:
```python
bin_id: SERIAL PRIMARY KEY                          # Auto-increment
storage_location_id: INT FK (CASCADE)               # Parent location (REQUIRED)
storage_bin_type_id: INT FK (RESTRICT, NULLABLE)    # Bin type catalog
code: VARCHAR(100) UNIQUE NOT NULL                  # 4-part: WAREHOUSE-AREA-LOCATION-BIN
label: VARCHAR(100) NULLABLE                         # Human readable name
description: TEXT NULLABLE                           # Optional description
position_metadata: JSONB NULLABLE                    # ML segmentation output
status: ENUM (active|maintenance|retired)           # Status (default: active)
created_at: TIMESTAMP (auto)
updated_at: TIMESTAMP (nullable)
```

**Validation Rules**:
- `code` must match pattern: `^[A-Z0-9_-]+-[A-Z0-9_-]+-[A-Z0-9_-]+-[A-Z0-9_-]+$`
- `code` length: 2-100 characters
- Unique constraint on `code`
- Status transitions: active ↔ maintenance → retired (terminal)

**JSONB position_metadata Schema**:
```json
{
    "segmentation_mask": [[x1, y1], [x2, y2], ...],
    "bbox": {"x1": 100, "y1": 200, "x2": 300, "y2": 400},
    "confidence": 0.92,
    "ml_model_version": "yolov11n-seg-v1.0.0",
    "detected_at": "2025-10-24T14:30:00Z",
    "container_type": "segment",
    "area_pixels": 40000,
    "session_id": 123
}
```

### 4.2 StorageBinType Model

**File**: `/home/lucasg/proyectos/DemeterDocs/app/models/storage_bin_type.py`

**Key Columns**:
```python
bin_type_id: SERIAL PRIMARY KEY
code: VARCHAR(50) UNIQUE NOT NULL               # e.g., ML_SEGMENT_DEFAULT
name: VARCHAR(100) NOT NULL                     # e.g., ML-Detected Segment
category: ENUM (segment|box|plug|seedling_tray|pot)
is_grid: BOOLEAN                                # Grid layout indicator
description: TEXT NULLABLE
created_at: TIMESTAMP (auto)
```

### 4.3 StockBatch Model

**File**: `/home/lucasg/proyectos/DemeterDocs/app/models/stock_batch.py`

**Critical FK**:
```python
current_storage_bin_id: INT FK → storage_bins.bin_id (CASCADE)  # REQUIRED, NOT NULL
```

**When FK Violation Occurs**:
```python
stock_batch = StockBatch(
    batch_code=batch_code,
    current_storage_bin_id=1,  # ❌ If bin_id=1 doesn't exist → FK violation
    product_id=...,
    product_state_id=...,
    ...
)
db_session.add(stock_batch)
db_session.flush()  # ❌ FK constraint check fails here
```

---

## 5. Test Data Requirements

### 5.1 Minimal Test Data Setup

To successfully test ML persistence:

```sql
-- 1. Create warehouse
INSERT INTO warehouses (code, name, warehouse_type, geojson_coordinates)
VALUES ('NAVE1', 'Greenhouse 1', 'greenhouse', 
        ST_GeomFromText('POLYGON((0 0, 100 0, 100 100, 0 100, 0 0))', 4326));

-- 2. Create storage area
INSERT INTO storage_areas (warehouse_id, code, name, area_type, geojson_coordinates)
VALUES (1, 'NORTH', 'North Section', 'greenhouse',
        ST_GeomFromText('POLYGON((0 0, 50 0, 50 100, 0 100, 0 0))', 4326));

-- 3. Create storage location
INSERT INTO storage_locations (storage_area_id, code, name, location_type, geojson_coordinates)
VALUES (1, 'A1', 'Location A1', 'growing_bed',
        ST_GeomFromText('POINT(25 50)', 4326));

-- 4. Create product (if not exists)
INSERT INTO products (product_category_id, product_family_id, code, name, current_height_mm)
VALUES (1, 1, 'MAMM001', 'Mammillaria', 50)
ON CONFLICT (code) DO NOTHING;

-- 5. Create product state (if not exists)
INSERT INTO product_states (product_state_id, name, description)
VALUES (3, 'SEEDLING', 'Young plant')
ON CONFLICT (product_state_id) DO NOTHING;

-- 6. Create storage location config (enables ML processing)
INSERT INTO storage_location_config (
    storage_location_id, product_id, expected_product_state_id,
    packaging_catalog_id, active
)
VALUES (1, 1, 3, NULL, TRUE);

-- 7. Create user (for StockMovement)
INSERT INTO users (username, email, hashed_password, is_active)
VALUES ('ml_user', 'ml@example.com', '$2b$12$...', TRUE)
ON CONFLICT (username) DO NOTHING;
```

### 5.2 Verification Queries

```sql
-- Verify storage location exists
SELECT * FROM storage_locations WHERE location_id = 1;

-- Verify config exists
SELECT * FROM storage_location_config WHERE storage_location_id = 1;

-- Verify no hardcoded bin_id=1 exists (should be empty initially)
SELECT * FROM storage_bins WHERE bin_id = 1;

-- After ML processing, verify StorageBins created
SELECT * FROM storage_bins 
WHERE storage_location_id = 1 
ORDER BY created_at DESC;

-- Verify StockBatch links to valid bin
SELECT sb.id, sb.batch_code, sb.current_storage_bin_id, 
       sbin.bin_id, sbin.code
FROM stock_batches sb
LEFT JOIN storage_bins sbin ON sb.current_storage_bin_id = sbin.bin_id
WHERE sb.id IN (SELECT id FROM stock_batches ORDER BY created_at DESC LIMIT 5);
```

---

## 6. Key Files and Line References

| File | Location | Purpose | Status |
|------|----------|---------|--------|
| `/home/lucasg/proyectos/DemeterDocs/app/tasks/ml_tasks.py` | Lines 176-212 | Container type mapping | ✅ Implemented |
| | Lines 1800-1968 | `_create_storage_bins()` function | ❌ **FAILING** |
| | Lines 1971-2280+ | `_persist_ml_results()` function | ❌ **FAILING** |
| | Lines 2065-2073 | StorageBin creation call | ❌ **NO TRY/EXCEPT** |
| | Lines 2147-2148 | **HARDCODED BIN_ID=1 FALLBACK** | ❌ **CRITICAL BUG** |
| `/home/lucasg/proyectos/DemeterDocs/app/models/storage_bin.py` | Full | StorageBin model | ✅ OK |
| `/home/lucasg/proyectos/DemeterDocs/app/models/storage_bin_type.py` | Full | StorageBinType model | ✅ OK |
| `/home/lucasg/proyectos/DemeterDocs/app/models/stock_batch.py` | Lines 193-199 | **FK to storage_bins** | ✅ Validated |
| `/home/lucasg/proyectos/DemeterDocs/app/models/storage_location_config.py` | Full | Config lookup | ✅ OK |
| `/home/lucasg/proyectos/DemeterDocs/tests/fixtures/test_fixtures.sql` | All | Test data | ⚠️ Check if storage_location exists |

---

## 7. What's Working vs. What's Broken

### ✅ Working Components

1. **ML Child Tasks** - Image processing, segmentation, detection work correctly
   - Segments generated: `{"container_type": "segment", "bbox": [...], ...}`
   - Detections generated: Individual plant bounding boxes
   - Estimations generated: Vegetation area estimates

2. **PhotoProcessingSession Creation** - Session tracking works
   - Status updates: pending → processing → completed/failed
   - Image upload/download from S3 works

3. **Model Definitions** - All 28 models properly defined
   - StorageBin model structure is correct
   - FK relationships properly defined

4. **Repository Layer** - CRUD operations implemented
   - StorageBinRepository exists
   - StorageLocationRepository exists

### ❌ Broken Components

1. **StorageBin Creation** - `_create_storage_bins()` failing silently
   - No exception caught in `_persist_ml_results()`
   - Returns empty list `[]` on failure
   - Fallback to hardcoded `bin_id=1`

2. **Hardcoded Fallback** - Line 2148 uses non-existent bin
   - `current_storage_bin_id = created_bin_ids[0] if created_bin_ids else 1`
   - DB has no bin with ID=1
   - FK constraint violation when StockBatch created

3. **Error Handling** - No try/except around critical section
   - Exception from `_create_storage_bins()` propagates uncaught
   - No graceful degradation
   - No logging of actual error

4. **Test Data** - Missing required database entries
   - No test StorageLocation with ID matching PhotoProcessingSession
   - Or StorageLocation exists but StorageBin creation fails for other reasons

---

## 8. Recommended Fixes

### Priority 1: Add Exception Handling (IMMEDIATE)

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
    # Graceful fallback or re-raise with context
    raise ValueError(f"Cannot create StorageBins: {str(e)}") from e
```

### Priority 2: Remove Hardcoded Fallback (IMMEDIATE)

**Don't do**:
```python
current_storage_bin_id = created_bin_ids[0] if created_bin_ids else 1  # ❌
```

**Do**:
```python
if not created_bin_ids:
    raise ValueError(
        f"No StorageBins created for session {session_id}. "
        f"Cannot proceed without valid bin IDs."
    )
current_storage_bin_id = created_bin_ids[0]  # ✅
```

### Priority 3: Verify Test Data

Ensure test database has:
- StorageLocation records matching PhotoProcessingSession.storage_location_id
- At least one Product (ID=1 used as fallback)
- At least one ProductState (ID=3 = SEEDLING)
- User ID=1 for StockMovement

### Priority 4: Add Logging

Log actual exception messages from `_create_storage_bins()` to identify:
- Why StorageLocation lookup fails
- Why StorageBinType creation fails
- Why StorageBin insertion fails

---

## 9. Error Message Interpretation

When you see: **"StorageBin ID=X not found"**

It means:
1. ML segments WERE created ✅
2. `_create_storage_bins()` was called
3. One of these happened:
   - a) StorageLocation with given ID doesn't exist
   - b) StorageBinType creation failed (bad category)
   - c) StorageBin.code validation failed (doesn't match pattern)
   - d) FK constraint failed on insert
4. Exception was NOT caught
5. `created_bin_ids` remains empty `[]`
6. Fallback to `bin_id=1`
7. StockBatch tries to link to non-existent bin_id=1
8. FK constraint violation: "Key (current_storage_bin_id)=(1) is not present in table storage_bins"

---

## 10. Summary Checklist

- [ ] Verify StorageLocation exists in database
- [ ] Verify product_id=1 exists
- [ ] Verify product_state_id=3 exists
- [ ] Add try/except around `_create_storage_bins()` call
- [ ] Remove hardcoded `bin_id=1` fallback
- [ ] Add detailed error logging
- [ ] Test with minimal dataset
- [ ] Verify all 28 models have test data
- [ ] Run ML pipeline end-to-end
- [ ] Check database for created StorageBins

