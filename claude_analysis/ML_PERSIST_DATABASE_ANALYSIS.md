# ML Pipeline Database Persistence Analysis

**Date**: 2025-10-24
**Author**: Database Expert
**Source**: database/database.mmd ERD + Model Analysis
**Purpose**: Document correct INSERT order and FK relationships for ML processing workflow

---

## Executive Summary

This document provides the **authoritative guide** for persisting ML pipeline results to the database. It addresses the critical question: **"What is the correct order of INSERT operations to avoid FK constraint violations?"**

**Key Finding**: The current `detections` and `estimations` tables do **NOT** have a `storage_bin_id` FK. Storage bins are linked **indirectly** via `stock_movements`.

---

## 1. Storage Hierarchy Relationships

### Schema Overview

```
warehouses (id: SERIAL)
    ↓ (warehouse_id FK)
storage_areas (id: SERIAL)
    ↓ (storage_area_id FK)
storage_locations (location_id: SERIAL)
    ↓ (storage_location_id FK)
storage_bins (bin_id: SERIAL)
```

### Table: `storage_bins`

**File**: `/home/lucasg/proyectos/DemeterDocs/app/models/storage_bin.py`

**Schema**:
```sql
CREATE TABLE storage_bins (
    bin_id SERIAL PRIMARY KEY,
    storage_location_id INT NOT NULL,  -- FK → storage_locations.location_id (CASCADE)
    storage_bin_type_id INT NULL,      -- FK → storage_bin_types.bin_type_id (RESTRICT)
    code VARCHAR(100) UNIQUE NOT NULL,
    label VARCHAR(100) NULL,
    description TEXT NULL,
    position_metadata JSONB NULL,     -- ML segmentation output
    status VARCHAR(20) NOT NULL DEFAULT 'active',  -- active|maintenance|retired
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NULL
);
```

**Foreign Keys**:
- `storage_location_id` → `storage_locations.location_id` (CASCADE DELETE)
- `storage_bin_type_id` → `storage_bin_types.bin_type_id` (RESTRICT DELETE)

**JSONB `position_metadata` Schema** (from ML segmentation):
```json
{
    "segmentation_mask": [[x1, y1], [x2, y2], ...],  // Polygon vertices (px)
    "bbox": {"x": 100, "y": 200, "width": 300, "height": 150},
    "confidence": 0.92,  // Segmentation quality (0.0-1.0)
    "ml_model_version": "yolov11-seg-v2.3",
    "detected_at": "2025-10-09T14:30:00Z",
    "container_type": "segmento"  // or "cajon", "box", "plug"
}
```

**Key Insight**: Storage bins are **created** from `storage_bin_types` catalog + ML segmentation results. The `position_metadata` stores the full ML output (mask, bbox, confidence).

---

## 2. Photo Processing Flow Relationships

### Table: `photo_processing_sessions`

**File**: `/home/lucasg/proyectos/DemeterDocs/app/models/photo_processing_session.py`

**Schema**:
```sql
CREATE TABLE photo_processing_sessions (
    id SERIAL PRIMARY KEY,
    session_id UUID UNIQUE NOT NULL,  -- Business identifier
    storage_location_id INT NULL,     -- FK → storage_locations.location_id (CASCADE)
    original_image_id UUID NULL,      -- FK → s3_images.image_id (CASCADE)
    processed_image_id UUID NULL,     -- FK → s3_images.image_id (CASCADE)
    total_detected INT NOT NULL DEFAULT 0,
    total_estimated INT NOT NULL DEFAULT 0,
    total_empty_containers INT NOT NULL DEFAULT 0,
    avg_confidence NUMERIC(5,4) NULL,
    category_counts JSONB NOT NULL DEFAULT '{}',
    status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending|processing|completed|failed
    error_message TEXT NULL,
    validated BOOLEAN NOT NULL DEFAULT FALSE,
    validated_by_user_id INT NULL,  -- FK → users.id (SET NULL)
    validation_date TIMESTAMP NULL,
    manual_adjustments JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NULL
);
```

**Foreign Keys**:
- `storage_location_id` → `storage_locations.location_id` (CASCADE DELETE)
- `original_image_id` → `s3_images.image_id` (CASCADE DELETE)
- `processed_image_id` → `s3_images.image_id` (CASCADE DELETE)
- `validated_by_user_id` → `users.id` (SET NULL)

**Workflow States**:
1. `pending`: Session created, waiting for ML processing
2. `processing`: ML pipeline is running
3. `completed`: ML processing complete, results available
4. `failed`: ML processing failed (see `error_message`)

**Relationships**:
- **One-to-many**: `photo_processing_sessions` → `detections` (via `session_id`)
- **One-to-many**: `photo_processing_sessions` → `estimations` (via `session_id`)
- **One-to-many**: `photo_processing_sessions` → `stock_movements` (via `processing_session_id`)

---

## 3. Detections & Stock Relationships

### Table: `detections`

**File**: `/home/lucasg/proyectos/DemeterDocs/app/models/detection.py`

**Schema**:
```sql
CREATE TABLE detections (
    id SERIAL PRIMARY KEY,
    session_id INT NOT NULL,           -- FK → photo_processing_sessions.id (CASCADE)
    stock_movement_id INT NOT NULL,    -- FK → stock_movements.id (CASCADE)
    classification_id INT NOT NULL,    -- FK → classifications.id (CASCADE)
    center_x_px NUMERIC(10,2) NOT NULL,
    center_y_px NUMERIC(10,2) NOT NULL,
    width_px INT NOT NULL,
    height_px INT NOT NULL,
    area_px NUMERIC(15,2) NULL,        -- GENERATED = width_px * height_px
    bbox_coordinates JSONB NOT NULL,   -- {x1, y1, x2, y2}
    detection_confidence NUMERIC(5,4) NOT NULL,
    is_empty_container BOOLEAN NOT NULL DEFAULT FALSE,
    is_alive BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

**Foreign Keys**:
- `session_id` → `photo_processing_sessions.id` (CASCADE DELETE)
- `stock_movement_id` → `stock_movements.id` (CASCADE DELETE)
- `classification_id` → `classifications.id` (CASCADE DELETE)

**CRITICAL FINDING**: There is **NO** `storage_bin_id` FK in the `detections` table!

**How to link detections to storage_bins?**

**Answer**: Via `stock_movements` table:
```
detections.stock_movement_id → stock_movements.id
stock_movements.destination_bin_id → storage_bins.bin_id
```

### Table: `estimations`

**File**: `/home/lucasg/proyectos/DemeterDocs/app/models/estimation.py`

**Schema**:
```sql
CREATE TABLE estimations (
    id SERIAL PRIMARY KEY,
    session_id INT NOT NULL,           -- FK → photo_processing_sessions.id (CASCADE)
    stock_movement_id INT NOT NULL,    -- FK → stock_movements.id (CASCADE)
    classification_id INT NOT NULL,    -- FK → classifications.id (CASCADE)
    vegetation_polygon JSONB NOT NULL,
    detected_area_cm2 NUMERIC(15,2) NOT NULL,
    estimated_count INT NOT NULL,
    calculation_method VARCHAR(20) NOT NULL,  -- band_estimation|density_estimation|grid_analysis
    estimation_confidence NUMERIC(5,4) NOT NULL DEFAULT 0.70,
    used_density_parameters BOOLEAN NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

**Foreign Keys**:
- `session_id` → `photo_processing_sessions.id` (CASCADE DELETE)
- `stock_movement_id` → `stock_movements.id` (CASCADE DELETE)
- `classification_id` → `classifications.id` (CASCADE DELETE)

**CRITICAL FINDING**: There is **NO** `storage_bin_id` FK in the `estimations` table either!

**Same linking approach as detections**:
```
estimations.stock_movement_id → stock_movements.id
stock_movements.destination_bin_id → storage_bins.bin_id
```

---

## 4. Stock Movements Linking Everything

### Table: `stock_movements`

**File**: `/home/lucasg/proyectos/DemeterDocs/app/models/stock_movement.py`

**Schema**:
```sql
CREATE TABLE stock_movements (
    id SERIAL PRIMARY KEY,
    movement_id UUID UNIQUE NOT NULL,  -- Business identifier
    batch_id INT NOT NULL,             -- FK → stock_batches.id (CASCADE)
    movement_type VARCHAR(20) NOT NULL,  -- plantar|sembrar|transplante|muerte|ventas|foto|ajuste|manual_init
    source_bin_id INT NULL,            -- FK → storage_bins.bin_id (CASCADE)
    destination_bin_id INT NULL,       -- FK → storage_bins.bin_id (CASCADE)
    quantity INT NOT NULL,             -- CHECK != 0 (can be negative)
    user_id INT NOT NULL,              -- FK → users.id (CASCADE)
    unit_price NUMERIC(10,2) NULL,
    total_price NUMERIC(10,2) NULL,
    reason_description TEXT NULL,
    processing_session_id INT NULL,    -- FK → photo_processing_sessions.id (CASCADE)
    source_type VARCHAR(20) NOT NULL,  -- manual|ia
    is_inbound BOOLEAN NOT NULL,       -- True = addition, False = subtraction
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

**Foreign Keys**:
- `batch_id` → `stock_batches.id` (CASCADE DELETE)
- `source_bin_id` → `storage_bins.bin_id` (CASCADE DELETE)
- `destination_bin_id` → `storage_bins.bin_id` (CASCADE DELETE)
- `user_id` → `users.id` (CASCADE DELETE)
- `processing_session_id` → `photo_processing_sessions.id` (CASCADE DELETE)

**Key Points**:
1. `movement_id` is UUID (for distributed systems), `id` is SERIAL (PK)
2. `quantity` can be negative (deaths, sales are negative movements)
3. `batch_id` links to stock_batches (which links to storage_bins)
4. `destination_bin_id` is where the stock physically exists after the movement
5. `processing_session_id` links to photo processing session (for ML-generated movements)

**Relationships**:
- **Many-to-one**: `stock_movements` → `stock_batches` (via `batch_id`)
- **Many-to-one**: `stock_movements` → `storage_bins` (via `source_bin_id` or `destination_bin_id`)
- **Many-to-one**: `stock_movements` → `photo_processing_sessions` (via `processing_session_id`)
- **One-to-many**: `stock_movements` → `detections` (via `stock_movement_id`)
- **One-to-many**: `stock_movements` → `estimations` (via `stock_movement_id`)

---

## 5. Stock Batches Linking Products to Bins

### Table: `stock_batches`

**File**: `/home/lucasg/proyectos/DemeterDocs/app/models/stock_batch.py`

**Schema**:
```sql
CREATE TABLE stock_batches (
    id SERIAL PRIMARY KEY,
    batch_code VARCHAR(50) UNIQUE NOT NULL,  -- 6-50 chars, alphanumeric+hyphen, uppercase
    current_storage_bin_id INT NOT NULL,     -- FK → storage_bins.bin_id (CASCADE)
    product_id INT NOT NULL,                 -- FK → products.id (CASCADE)
    product_state_id INT NOT NULL,           -- FK → product_states.product_state_id (CASCADE)
    product_size_id INT NULL,                -- FK → product_sizes.product_size_id (CASCADE)
    has_packaging BOOLEAN NOT NULL DEFAULT FALSE,
    packaging_catalog_id INT NULL,           -- FK → packaging_catalog.id (CASCADE)
    quantity_initial INT NOT NULL,           -- CHECK >= 0
    quantity_current INT NOT NULL,           -- CHECK >= 0
    quantity_empty_containers INT NOT NULL DEFAULT 0,  -- CHECK >= 0
    quality_score NUMERIC(3,2) NULL,         -- 0.00-5.00 range
    planting_date DATE NULL,
    germination_date DATE NULL,
    transplant_date DATE NULL,
    expected_ready_date DATE NULL,
    notes TEXT NULL,
    custom_attributes JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NULL
);
```

**Foreign Keys**:
- `current_storage_bin_id` → `storage_bins.bin_id` (CASCADE DELETE)
- `product_id` → `products.id` (CASCADE DELETE)
- `product_state_id` → `product_states.product_state_id` (CASCADE DELETE)
- `product_size_id` → `product_sizes.product_size_id` (CASCADE DELETE)
- `packaging_catalog_id` → `packaging_catalog.id` (CASCADE DELETE)

**Key Points**:
1. Each batch represents a group of plants of the same product, state, size, and packaging
2. `current_storage_bin_id` tracks the physical location of the batch
3. `quantity_current` is updated by stock movements
4. `batch_code` must be unique (6-50 chars, uppercase, alphanumeric+hyphen)

**Relationships**:
- **Many-to-one**: `stock_batches` → `storage_bins` (via `current_storage_bin_id`)
- **Many-to-one**: `stock_batches` → `products` (via `product_id`)
- **Many-to-one**: `stock_batches` → `product_states` (via `product_state_id`)
- **Many-to-one**: `stock_batches` → `product_sizes` (via `product_size_id`)
- **Many-to-one**: `stock_batches` → `packaging_catalog` (via `packaging_catalog_id`)
- **One-to-many**: `stock_batches` → `stock_movements` (via `batch_id`)

---

## 6. Configuration Tables

### Table: `storage_location_config`

**File**: `/home/lucasg/proyectos/DemeterDocs/app/models/storage_location_config.py`

**Schema**:
```sql
CREATE TABLE storage_location_config (
    id SERIAL PRIMARY KEY,
    storage_location_id INT NOT NULL,         -- FK → storage_locations.location_id (CASCADE)
    product_id INT NOT NULL,                  -- FK → products.id (CASCADE)
    packaging_catalog_id INT NULL,            -- FK → packaging_catalog.id (CASCADE)
    expected_product_state_id INT NOT NULL,   -- FK → product_states.product_state_id (CASCADE)
    area_cm2 NUMERIC(15,2) NOT NULL,          -- CHECK >= 0.0
    active BOOLEAN NOT NULL DEFAULT TRUE,
    notes TEXT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NULL
);
```

**Foreign Keys**:
- `storage_location_id` → `storage_locations.location_id` (CASCADE DELETE)
- `product_id` → `products.id` (CASCADE DELETE)
- `packaging_catalog_id` → `packaging_catalog.id` (CASCADE DELETE)
- `expected_product_state_id` → `product_states.product_state_id` (CASCADE DELETE)

**Usage in ML Processing**:
1. Query config by `storage_location_id` to get expected product/packaging
2. Use `product_id` and `packaging_catalog_id` to create `stock_batches`
3. Use `expected_product_state_id` to set batch state
4. Use `area_cm2` for density calculations

**Query Example**:
```python
config = await db.execute(
    select(StorageLocationConfig)
    .where(StorageLocationConfig.storage_location_id == location_id)
    .where(StorageLocationConfig.active == True)
)
```

---

## 7. Correct INSERT Order for ML Pipeline

Based on the FK constraints, here is the **correct order** of INSERT operations:

### **Phase 1: Pre-Processing (Before ML)**

```sql
-- 1. Create photo processing session (FIRST)
INSERT INTO photo_processing_sessions (
    session_id,
    storage_location_id,
    original_image_id,
    status
) VALUES (
    'uuid-here',
    123,  -- storage_location_id
    'uuid-here',  -- original_image_id
    'processing'
) RETURNING id;  -- Save as session_pk
```

**Why first?**: `detections`, `estimations`, and `stock_movements` all have FKs to `photo_processing_sessions.id`.

### **Phase 2: ML Processing**

**YOLO runs and produces**:
- Segmentation masks → storage_bins
- Detections → individual plants
- Estimations → dense areas

### **Phase 3: Persist ML Results**

**Step 3.1: Create Storage Bins** (if they don't exist)

```sql
-- 2. Create storage bins from segmentation results
INSERT INTO storage_bins (
    storage_location_id,
    storage_bin_type_id,  -- Get from storage_location_config or default
    code,  -- Generate: WAREHOUSE-AREA-LOCATION-BIN
    label,
    position_metadata,  -- Store full ML output here
    status
) VALUES (
    123,  -- storage_location_id
    5,    -- storage_bin_type_id (e.g., "segmento")
    'INV01-NORTH-A1-SEG001',
    'Segment 1',
    '{
        "segmentation_mask": [[100, 200], [300, 200], ...],
        "bbox": {"x": 100, "y": 200, "width": 200, "height": 200},
        "confidence": 0.92,
        "ml_model_version": "yolov11-seg-v2.3",
        "detected_at": "2025-10-09T14:30:00Z",
        "container_type": "segmento"
    }',
    'active'
) RETURNING bin_id;  -- Save as bin_pk
```

**Why now?**: `stock_batches` and `stock_movements` need `bin_id` to exist.

**Step 3.2: Create Stock Batches** (for each detected product/packaging combination)

```sql
-- 3. Create stock batches (one per product/packaging/bin combination)
INSERT INTO stock_batches (
    batch_code,  -- Generate: BATCH-PRODUCT-YYYYMMDD-NNNN
    current_storage_bin_id,
    product_id,         -- From storage_location_config or ML classification
    product_state_id,   -- From storage_location_config.expected_product_state_id
    product_size_id,    -- From ML classification
    has_packaging,
    packaging_catalog_id,  -- From storage_location_config or ML classification
    quantity_initial,   -- From detection/estimation count
    quantity_current,   -- Same as quantity_initial
    quantity_empty_containers,  -- From detection.is_empty_container count
    quality_score,      -- From ML confidence (optional)
    planting_date       -- From storage_location_config or user input
) VALUES (
    'BATCH-ECHEV-20251024-0001',
    42,   -- bin_pk (from step 3.1)
    10,   -- product_id (from config or classification)
    3,    -- product_state_id (e.g., "Adult")
    2,    -- product_size_id (e.g., "Medium")
    TRUE,
    7,    -- packaging_catalog_id (e.g., "10cm pot")
    25,   -- quantity_initial (sum of detections in this bin)
    25,   -- quantity_current
    2,    -- quantity_empty_containers
    4.5,  -- quality_score
    '2025-01-15'
) RETURNING id;  -- Save as batch_pk
```

**Why now?**: `stock_movements` need `batch_id` to exist.

**Step 3.3: Create Stock Movements** (one per detection/estimation group)

```sql
-- 4. Create stock movements (one per bin, linking to processing session)
INSERT INTO stock_movements (
    movement_id,  -- Generate UUID
    batch_id,
    movement_type,
    destination_bin_id,  -- Where the stock is after ML processing
    quantity,
    user_id,
    processing_session_id,  -- Link to session created in step 1
    source_type,
    is_inbound,
    reason_description
) VALUES (
    'uuid-here',
    5,      -- batch_pk (from step 3.2)
    'foto',
    42,     -- bin_pk (from step 3.1)
    25,     -- Total count in this bin (positive for inbound)
    1,      -- user_id (system user or current user)
    7,      -- session_pk (from step 1)
    'ia',
    TRUE,
    'ML photo detection'
) RETURNING id;  -- Save as movement_pk
```

**Why now?**: `detections` and `estimations` need `stock_movement_id` to exist.

**Step 3.4: Create Detections** (one per detected plant)

```sql
-- 5. Create detections (one per detected plant)
INSERT INTO detections (
    session_id,
    stock_movement_id,
    classification_id,
    center_x_px,
    center_y_px,
    width_px,
    height_px,
    bbox_coordinates,
    detection_confidence,
    is_empty_container,
    is_alive
) VALUES (
    7,      -- session_pk (from step 1)
    12,     -- movement_pk (from step 3.3)
    3,      -- classification_id (ML product/packaging/size classification)
    512.5,
    768.3,
    120,
    135,
    '{"x1": 452, "y1": 700, "x2": 572, "y2": 835}',
    0.95,
    FALSE,
    TRUE
);
```

**Step 3.5: Create Estimations** (one per dense area)

```sql
-- 6. Create estimations (one per dense vegetation area)
INSERT INTO estimations (
    session_id,
    stock_movement_id,
    classification_id,
    vegetation_polygon,
    detected_area_cm2,
    estimated_count,
    calculation_method,
    estimation_confidence,
    used_density_parameters
) VALUES (
    7,      -- session_pk (from step 1)
    12,     -- movement_pk (from step 3.3)
    3,      -- classification_id
    '{"coordinates": [[100, 200], [300, 200], [300, 400], [100, 400]]}',
    250.5,
    15,
    'band_estimation',
    0.75,
    TRUE
);
```

### **Phase 4: Update Session**

```sql
-- 7. Update session with aggregated results
UPDATE photo_processing_sessions
SET
    processed_image_id = 'uuid-here',  -- After visualization image created
    total_detected = 25,
    total_estimated = 15,
    total_empty_containers = 2,
    avg_confidence = 0.92,
    category_counts = '{"echeveria": 25, "aloe": 0}',
    status = 'completed',
    updated_at = CURRENT_TIMESTAMP
WHERE id = 7;  -- session_pk
```

---

## 8. Complete INSERT Order Summary

### **Correct Order** (with dependencies)

```
1. photo_processing_sessions (FIRST - no dependencies)
   ↓
2. storage_bins (depends on: storage_location_id)
   ↓
3. stock_batches (depends on: storage_bins.bin_id)
   ↓
4. stock_movements (depends on: stock_batches.id, storage_bins.bin_id, photo_processing_sessions.id)
   ↓
5. detections (depends on: photo_processing_sessions.id, stock_movements.id)
   ↓
6. estimations (depends on: photo_processing_sessions.id, stock_movements.id)
   ↓
7. UPDATE photo_processing_sessions (final aggregation)
```

### **Performance Notes**

- **Batch inserts**: Use `INSERT INTO ... VALUES (...), (...), ...` for detections/estimations
- **RETURNING clause**: Always use `RETURNING id` to get PK values for FK references
- **Transactions**: Wrap entire workflow in a single transaction for atomicity
- **Partitioning**: `detections` and `estimations` are partitioned by `session_id` (daily)

---

## 9. Missing Links Analysis

### Question: Does `detections` have a `storage_bin_id` FK?

**Answer**: ❌ **NO**

**From ERD** (lines 261-276):
```
detections {
    int id PK
    int session_id FK → photo_processing_sessions
    int stock_movement_id FK → stock_movements
    int classification_id FK → classifications
    -- NO storage_bin_id FK!
}
```

**From Model** (`app/models/detection.py`, lines 99-112):
```python
# Foreign key to photo processing session (CASCADE delete, PARTITION KEY)
session_id = Column(...)

# Foreign key to stock movement (CASCADE delete)
stock_movement_id = Column(...)

# Foreign key to classification (CASCADE delete)
classification_id = Column(...)

# NO storage_bin_id column defined!
```

### Question: Does `estimations` have a `storage_bin_id` FK?

**Answer**: ❌ **NO**

**From ERD** (lines 277-289):
```
estimations {
    int id PK
    int session_id FK → photo_processing_sessions
    int stock_movement_id FK → stock_movements
    int classification_id FK → classifications
    -- NO storage_bin_id FK!
}
```

**From Model** (`app/models/estimation.py`, lines 114-124):
```python
# Foreign key to photo processing session (CASCADE delete, PARTITION KEY)
session_id = Column(...)

# Foreign key to stock movement (CASCADE delete)
stock_movement_id = Column(...)

# Foreign key to classification (CASCADE delete)
classification_id = Column(...)

# NO storage_bin_id column defined!
```

### How to Link Detections/Estimations to Storage Bins?

**Answer**: Via `stock_movements` table:

```python
# Get storage bin for a detection
detection = await db.get(Detection, detection_id)
stock_movement = await db.get(StockMovement, detection.stock_movement_id)
storage_bin_id = stock_movement.destination_bin_id
storage_bin = await db.get(StorageBin, storage_bin_id)

# SQL equivalent
SELECT sb.*
FROM detections d
JOIN stock_movements sm ON d.stock_movement_id = sm.id
JOIN storage_bins sb ON sm.destination_bin_id = sb.bin_id
WHERE d.id = 123;
```

---

## 10. Storage Bin Creation from ML Segmentation

### How are `storage_bins` created during ML processing?

**Answer**: From segmentation results + `storage_bin_types` catalog

**Process**:

1. **YOLO segmentation** produces:
   - Segmentation mask (polygon vertices)
   - Bounding box (x, y, width, height)
   - Confidence score
   - Container type (segmento, cajon, box, plug)

2. **Service looks up** `storage_bin_type_id`:
   ```python
   # Get bin type by category (e.g., "segmento")
   bin_type = await db.execute(
       select(StorageBinType)
       .where(StorageBinType.category == container_type)
   )
   ```

3. **Service creates** `storage_bin`:
   ```python
   storage_bin = StorageBin(
       storage_location_id=location_id,
       storage_bin_type_id=bin_type.bin_type_id,
       code=generate_code(),  # WAREHOUSE-AREA-LOCATION-BIN
       label=f"Segment {index}",
       position_metadata={
           "segmentation_mask": mask_vertices,
           "bbox": {"x": x, "y": y, "width": w, "height": h},
           "confidence": confidence,
           "ml_model_version": "yolov11-seg-v2.3",
           "detected_at": datetime.utcnow().isoformat(),
           "container_type": container_type
       },
       status="active"
   )
   ```

4. **Insert** and return `bin_id`

### What fields in `storage_bins` are populated from segmentation?

**Answer**: `position_metadata` JSONB field stores **ALL** ML output:

| Field | Source | Example |
|-------|--------|---------|
| `segmentation_mask` | YOLO mask vertices | `[[100, 200], [300, 200], ...]` |
| `bbox` | YOLO bounding box | `{"x": 100, "y": 200, "width": 200, "height": 200}` |
| `confidence` | YOLO confidence | `0.92` |
| `ml_model_version` | System constant | `"yolov11-seg-v2.3"` |
| `detected_at` | Current timestamp | `"2025-10-09T14:30:00Z"` |
| `container_type` | YOLO classification | `"segmento"` |

**Note**: Other fields (`code`, `label`, `status`) are generated/set by the service, not ML.

---

## 11. Configuration Usage in ML Processing

### How is `storage_location_config` used to create `stock_batches`?

**Answer**: It provides expected product/packaging/state for validation and batch creation.

**Query Pattern**:
```python
# Get active config for location
config = await db.execute(
    select(StorageLocationConfig)
    .where(StorageLocationConfig.storage_location_id == location_id)
    .where(StorageLocationConfig.active == True)
)

# Use config to create batch
batch = StockBatch(
    batch_code=generate_batch_code(),
    current_storage_bin_id=bin_id,
    product_id=config.product_id,  # ← From config
    product_state_id=config.expected_product_state_id,  # ← From config
    product_size_id=ml_classification.product_size_id,  # ← From ML (nullable)
    has_packaging=True if config.packaging_catalog_id else False,
    packaging_catalog_id=config.packaging_catalog_id,  # ← From config
    quantity_initial=detection_count,
    quantity_current=detection_count,
    quantity_empty_containers=empty_count,
    planting_date=None  # Optional
)
```

**Validation Example**:
```python
# Validate ML classification against config
if ml_classification.product_id != config.product_id:
    logger.warning(
        f"ML detected product {ml_classification.product_id} "
        f"but config expects {config.product_id} at location {location_id}"
    )
    # Option 1: Use config (trust manual setup)
    # Option 2: Flag for manual review
    # Option 3: Create separate batch for unexpected product
```

---

## 12. Query Performance Considerations

### Indexes Critical for ML Pipeline

**From ERD**:

1. **photo_processing_sessions**:
   - B-tree on `session_id` (unique lookups)
   - B-tree on `status` (filter pending/processing)
   - B-tree on `storage_location_id` (location queries)
   - B-tree on `created_at DESC` (time-series)
   - GIN on `category_counts` (JSONB queries)

2. **detections**:
   - B-tree on `session_id` (partition key, FK)
   - B-tree on `stock_movement_id` (FK)
   - B-tree on `classification_id` (FK)
   - B-tree on `detection_confidence DESC` (high-confidence queries)
   - B-tree on `created_at DESC` (time-series)

3. **estimations**:
   - B-tree on `session_id` (partition key, FK)
   - B-tree on `stock_movement_id` (FK)
   - B-tree on `classification_id` (FK)
   - B-tree on `calculation_method` (filter by method)
   - B-tree on `created_at DESC` (time-series)

4. **stock_movements**:
   - B-tree on `movement_id` (UUID unique lookups)
   - B-tree on `batch_id` (FK)
   - B-tree on `processing_session_id` (FK)
   - B-tree on `user_id` (FK)
   - B-tree on `created_at DESC` (time-series)
   - B-tree on `movement_type` (filter by type)

5. **storage_bins**:
   - B-tree on `code` (unique lookups)
   - B-tree on `storage_location_id` (FK)
   - B-tree on `storage_bin_type_id` (FK)
   - B-tree on `status` (filter active bins)
   - GIN on `position_metadata` (JSONB queries)

6. **stock_batches**:
   - B-tree on `batch_code` (unique lookups)
   - B-tree on `current_storage_bin_id` (FK)
   - B-tree on `product_id` (FK)
   - B-tree on `product_state_id` (FK)
   - B-tree on `created_at DESC` (time-series)
   - GIN on `custom_attributes` (JSONB queries)

### Query Patterns

**Get all detections for a session**:
```sql
-- Fast (uses session_id partition key + index)
SELECT * FROM detections
WHERE session_id = 123
ORDER BY created_at DESC;
```

**Get all detections for a storage bin**:
```sql
-- Requires JOIN (no direct FK)
SELECT d.*
FROM detections d
JOIN stock_movements sm ON d.stock_movement_id = sm.id
WHERE sm.destination_bin_id = 42
ORDER BY d.created_at DESC;
```

**Get current stock in a bin**:
```sql
-- Fast (uses batch.current_storage_bin_id index)
SELECT b.*
FROM stock_batches b
WHERE b.current_storage_bin_id = 42
  AND b.quantity_current > 0;
```

---

## 13. Cascade Rules Summary

| Table | Column | FK Target | Cascade Rule | Reason |
|-------|--------|-----------|--------------|--------|
| **storage_bins** | `storage_location_id` | `storage_locations.location_id` | CASCADE | Delete bins when location deleted |
| **storage_bins** | `storage_bin_type_id` | `storage_bin_types.bin_type_id` | RESTRICT | Prevent deleting type if bins exist |
| **photo_processing_sessions** | `storage_location_id` | `storage_locations.location_id` | CASCADE | Delete sessions when location deleted |
| **photo_processing_sessions** | `original_image_id` | `s3_images.image_id` | CASCADE | Delete sessions when image deleted |
| **photo_processing_sessions** | `processed_image_id` | `s3_images.image_id` | CASCADE | Delete sessions when image deleted |
| **photo_processing_sessions** | `validated_by_user_id` | `users.id` | SET NULL | Keep sessions when user deleted |
| **detections** | `session_id` | `photo_processing_sessions.id` | CASCADE | Delete detections when session deleted |
| **detections** | `stock_movement_id` | `stock_movements.id` | CASCADE | Delete detections when movement deleted |
| **detections** | `classification_id` | `classifications.id` | CASCADE | Delete detections when classification deleted |
| **estimations** | `session_id` | `photo_processing_sessions.id` | CASCADE | Delete estimations when session deleted |
| **estimations** | `stock_movement_id` | `stock_movements.id` | CASCADE | Delete estimations when movement deleted |
| **estimations** | `classification_id` | `classifications.id` | CASCADE | Delete estimations when classification deleted |
| **stock_movements** | `batch_id` | `stock_batches.id` | CASCADE | Delete movements when batch deleted |
| **stock_movements** | `source_bin_id` | `storage_bins.bin_id` | CASCADE | Delete movements when bin deleted |
| **stock_movements** | `destination_bin_id` | `storage_bins.bin_id` | CASCADE | Delete movements when bin deleted |
| **stock_movements** | `user_id` | `users.id` | CASCADE | Delete movements when user deleted |
| **stock_movements** | `processing_session_id` | `photo_processing_sessions.id` | CASCADE | Delete movements when session deleted |
| **stock_batches** | `current_storage_bin_id` | `storage_bins.bin_id` | CASCADE | Delete batches when bin deleted |
| **stock_batches** | `product_id` | `products.id` | CASCADE | Delete batches when product deleted |
| **stock_batches** | `product_state_id` | `product_states.product_state_id` | CASCADE | Delete batches when state deleted |
| **stock_batches** | `product_size_id` | `product_sizes.product_size_id` | CASCADE | Delete batches when size deleted |
| **stock_batches** | `packaging_catalog_id` | `packaging_catalog.id` | CASCADE | Delete batches when packaging deleted |

**Key Insight**: Almost all FKs use CASCADE delete. Only exception is `storage_bin_types` (RESTRICT) to prevent deleting types in use.

---

## 14. Practical Code Examples

### Complete ML Persistence Workflow (Python)

```python
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import (
    PhotoProcessingSession,
    StorageBin,
    StockBatch,
    StockMovement,
    Detection,
    Estimation,
)

async def persist_ml_results(
    db: AsyncSession,
    storage_location_id: int,
    original_image_id: uuid.UUID,
    ml_results: dict,
    user_id: int
) -> PhotoProcessingSession:
    """Persist ML processing results to database.

    Args:
        db: Database session
        storage_location_id: Storage location where photo was taken
        original_image_id: S3 image UUID for original photo
        ml_results: ML pipeline output (segmentation, detections, estimations)
        user_id: User who initiated processing

    Returns:
        Completed PhotoProcessingSession instance
    """

    # 1. Create photo processing session (FIRST)
    session_id = uuid4()
    session = PhotoProcessingSession(
        session_id=session_id,
        storage_location_id=storage_location_id,
        original_image_id=original_image_id,
        status="processing"
    )
    db.add(session)
    await db.flush()  # Get session.id

    # Get storage location config
    config = await get_location_config(db, storage_location_id)

    # 2. Create storage bins from segmentation results
    bins = []
    for idx, seg in enumerate(ml_results["segmentation"], start=1):
        bin = StorageBin(
            storage_location_id=storage_location_id,
            storage_bin_type_id=seg["bin_type_id"],
            code=generate_bin_code(storage_location_id, idx),
            label=f"Segment {idx}",
            position_metadata={
                "segmentation_mask": seg["mask"],
                "bbox": seg["bbox"],
                "confidence": seg["confidence"],
                "ml_model_version": "yolov11-seg-v2.3",
                "detected_at": datetime.utcnow().isoformat(),
                "container_type": seg["container_type"]
            },
            status="active"
        )
        db.add(bin)
        bins.append(bin)
    await db.flush()  # Get bin.bin_id

    # 3. Group detections/estimations by bin and classification
    grouped = group_results_by_bin_and_classification(ml_results, bins)

    # 4. Create stock batches and movements
    batches = []
    movements = []
    for group in grouped:
        # Create batch
        batch = StockBatch(
            batch_code=generate_batch_code(config.product_id),
            current_storage_bin_id=group["bin_id"],
            product_id=config.product_id,
            product_state_id=config.expected_product_state_id,
            product_size_id=group["classification"].product_size_id,
            has_packaging=bool(config.packaging_catalog_id),
            packaging_catalog_id=config.packaging_catalog_id,
            quantity_initial=group["total_count"],
            quantity_current=group["total_count"],
            quantity_empty_containers=group["empty_count"],
            quality_score=group["avg_confidence"] * 5.0  # Scale 0-1 to 0-5
        )
        db.add(batch)
        await db.flush()  # Get batch.id
        batches.append(batch)

        # Create movement
        movement = StockMovement(
            movement_id=uuid4(),
            batch_id=batch.id,
            movement_type="foto",
            destination_bin_id=group["bin_id"],
            quantity=group["total_count"],
            user_id=user_id,
            processing_session_id=session.id,
            source_type="ia",
            is_inbound=True,
            reason_description="ML photo detection"
        )
        db.add(movement)
        await db.flush()  # Get movement.id
        movements.append((movement, group))

    # 5. Create detections
    detections = []
    for movement, group in movements:
        for det in group["detections"]:
            detection = Detection(
                session_id=session.id,
                stock_movement_id=movement.id,
                classification_id=det["classification_id"],
                center_x_px=det["center_x"],
                center_y_px=det["center_y"],
                width_px=det["width"],
                height_px=det["height"],
                bbox_coordinates=det["bbox"],
                detection_confidence=det["confidence"],
                is_empty_container=det["is_empty"],
                is_alive=det["is_alive"]
            )
            db.add(detection)
            detections.append(detection)

    # 6. Create estimations
    estimations = []
    for movement, group in movements:
        for est in group["estimations"]:
            estimation = Estimation(
                session_id=session.id,
                stock_movement_id=movement.id,
                classification_id=est["classification_id"],
                vegetation_polygon=est["polygon"],
                detected_area_cm2=est["area_cm2"],
                estimated_count=est["count"],
                calculation_method=est["method"],
                estimation_confidence=est["confidence"],
                used_density_parameters=est["used_density"]
            )
            db.add(estimation)
            estimations.append(estimation)

    # 7. Update session with aggregated results
    session.processed_image_id = ml_results["processed_image_id"]
    session.total_detected = sum(len(g["detections"]) for _, g in movements)
    session.total_estimated = sum(sum(e["count"] for e in g["estimations"]) for _, g in movements)
    session.total_empty_containers = sum(g["empty_count"] for _, g in movements)
    session.avg_confidence = calculate_avg_confidence(detections, estimations)
    session.category_counts = calculate_category_counts(grouped)
    session.status = "completed"

    await db.commit()
    return session
```

---

## 15. Recommendations

### For Python Expert

1. **Always create `photo_processing_sessions` FIRST**
   - All other ML results depend on `session.id`
   - Use `RETURNING id` or `await db.flush()` to get PK

2. **Create `storage_bins` BEFORE `stock_batches`**
   - `stock_batches.current_storage_bin_id` requires `bin_id` to exist
   - Store full ML output in `position_metadata` JSONB

3. **Create `stock_batches` BEFORE `stock_movements`**
   - `stock_movements.batch_id` requires `batch.id` to exist
   - Use `storage_location_config` to get product/packaging/state

4. **Create `stock_movements` BEFORE `detections`/`estimations`**
   - Both depend on `stock_movements.id`
   - One movement per bin/classification group

5. **Use transactions**
   - Wrap entire workflow in a single transaction
   - Rollback on any failure to maintain consistency

6. **Batch insert detections/estimations**
   - Use `db.add_all()` for performance
   - Consider bulk_insert_mappings for large volumes

### For Testing Expert

1. **Test FK constraint violations**
   - Try creating detections before sessions → should fail
   - Try creating batches before bins → should fail

2. **Test cascade deletes**
   - Delete session → verify detections/estimations deleted
   - Delete bin → verify batches/movements deleted

3. **Test JSONB validation**
   - Invalid `position_metadata` → should fail
   - Invalid `bbox_coordinates` → should fail

4. **Test transaction rollback**
   - Simulate failure after step 3 → verify nothing committed

---

## Conclusion

This analysis provides the **complete picture** of ML pipeline database persistence:

1. ✅ **Storage bins** are created from segmentation results + `storage_bin_types`
2. ✅ **Detections/estimations** do NOT have direct `storage_bin_id` FK
3. ✅ **Link via** `stock_movements.destination_bin_id`
4. ✅ **Correct INSERT order** documented with dependencies
5. ✅ **Configuration usage** explained for batch creation
6. ✅ **All FK constraints** and cascade rules documented

**Next Steps**:
1. Python Expert: Use this as reference for service implementation
2. Testing Expert: Create integration tests for INSERT order
3. Team Leader: Review and approve for Sprint 03 tasks

---

**End of Analysis**
