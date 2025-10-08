# Diagram 06: Boxes & Electrical Plugs Detection Task

**Version:** 1.0.0
**Date:** 2025-10-08
**Parent Diagram:** 01_complete_pipeline_v4.mmd
**Related Diagrams:** 04_ml_parent_segmentation_detailed.mmd, 05_sahi_detection_child_detailed.mmd

## Purpose

This diagram documents the **electrical infrastructure detection task** for agricultural field auditing. Unlike plant counting (diagram 05), this task identifies and locates electrical boxes, plugs, meters, and junction boxes for maintenance planning and safety audits.

## Scope

**Input:**
- `image_id_pk` (UUID): Primary key of the image
- `detection_type` (str): 'boxes' | 'plugs' | 'meters' | 'all'

**Output:**
- `total_count` (int): Total infrastructure elements detected
- `by_class` (dict): Counts and locations per class (electrical_box, plug, etc.)
- `gps_locations` (list): GPS coordinates for each detection
- `confidence_band` (str): HIGH | MEDIUM | LOW

**Performance Target:** 5-10 seconds per image (fewer objects than plants)

## Key Differences from Plant Detection (Diagram 05)

| Aspect | Plant Detection (05) | Infrastructure Detection (06) |
|--------|---------------------|------------------------------|
| **Model** | yolo11m (medium) | yolo11x (extra-large) |
| **Confidence** | 0.45 (lower) | 0.6 (higher) |
| **Algorithm** | Band-based estimation | Direct count (no correction) |
| **SAHI slices** | 640×640, 20% overlap | 800×800, 30% overlap |
| **Objects/image** | 50-200 plants | 1-5 infrastructure |
| **GPS per object** | No (field-level only) | Yes (individual GPS) |
| **Processing time** | 15-30s | 5-10s |

## Key Components

### 1. Infrastructure-Specific Model (lines 45-91)

**Model:** `yolo11x-infrastructure.pt` (extra-large variant)

**Classes trained on:**
- `electrical_box` (class 0)
- `junction_box` (class 1)
- `control_panel` (class 2)
- `wall_plug` (class 3)
- `industrial_plug` (class 4)
- `outlet` (class 5)
- `electric_meter` (class 6)
- `smart_meter` (class 7)

**Why X-large model:**
- Infrastructure objects are fewer → can afford slower, more accurate model
- False positives are costly (maintenance crews dispatched unnecessarily)
- Precision > speed for safety-critical infrastructure

**Singleton pattern** (same as plant detection):
```python
worker_id = os.getpid() % num_gpus
model_key = f'yolo_v11_infrastructure_{worker_id}'

if model_key not in model_cache:
    model = YOLO('yolo11x-infrastructure.pt')
    model.to(f'cuda:{worker_id}')
    model.fuse()
    model_cache[model_key] = model
```

### 2. SAHI Configuration (lines 150-177)

**Different parameters than plant detection:**
```python
# Infrastructure SAHI config
slice_height = 800  # Larger (infrastructure bigger than plants)
slice_width = 800
overlap_ratio = 0.3  # More overlap (30% vs 20%)
postprocess_match_threshold = 0.4  # Stricter NMS
```

**Why larger slices:**
- Electrical boxes are typically 50-200px in size (vs plants 10-50px)
- Larger slices reduce total slice count → faster processing
- Example: 4000×3000 image → ~20 slices (vs ~42 for plants)

**Why more overlap:**
- Fewer objects → can afford more overlap for edge accuracy
- Infrastructure at tile boundary must not be missed

### 3. GPS Geolocation Per Detection (lines 256-303) 🔥

**CRITICAL DIFFERENCE:** Each infrastructure detection gets individual GPS coordinates!

```python
# Get field boundaries from PostGIS
field_polygon = db.execute(
    'SELECT ST_AsGeoJSON(geom) FROM fields WHERE id = :field_id'
).scalar()

# Calculate GPS for each detection
for detection in filtered_detections:
    # Get pixel coordinates (center of bbox)
    center_x = (bbox[0] + bbox[2]) / 2
    center_y = (bbox[1] + bbox[3]) / 2

    # Convert pixel → GPS using image metadata
    lat_offset = (center_y / img_height) * field_lat_span
    lon_offset = (center_x / img_width) * field_lon_span

    gps_lat = field_min_lat + lat_offset
    gps_lon = field_min_lon + lon_offset
```

**Use cases:**
1. **Maintenance navigation:** Navigate crew to exact plug location
2. **Work orders:** "Replace electrical box at GPS (-34.5678, -58.1234)"
3. **Geospatial analysis:** Distance between infrastructure elements
4. **Field maps:** Show infrastructure overlay on field boundary

**Accuracy:** ±2-5 meters (depends on image resolution and GPS accuracy of field boundaries)

### 4. Results Grouped by Class (lines 314-361)

```python
grouped = defaultdict(list)
for detection in filtered_detections:
    grouped[detection['class_name']].append(detection)

results_by_class = {}
for class_name, detections in grouped.items():
    results_by_class[class_name] = {
        'count': len(detections),
        'avg_confidence': np.mean([d['confidence'] for d in detections]),
        'locations': [
            {
                'gps': (d['gps_latitude'], d['gps_longitude']),
                'bbox': d['bbox'].tolist(),
                'confidence': d['confidence']
            }
            for d in detections
        ]
    }
```

**Example output:**
```json
{
  "electrical_box": {
    "count": 3,
    "avg_confidence": 0.82,
    "locations": [
      {
        "gps": [-34.5678, -58.1234],
        "bbox": [1200, 800, 1350, 1000],
        "confidence": 0.85
      },
      {
        "gps": [-34.5679, -58.1235],
        "bbox": [2100, 1500, 2280, 1720],
        "confidence": 0.78
      }
    ]
  },
  "industrial_plug": {
    "count": 1,
    "avg_confidence": 0.91,
    "locations": [...]
  }
}
```

### 5. Database Insert Pattern (lines 404-442)

**Different from plant detection:**
- Plant detection: Bulk insert (50-200 records)
- Infrastructure detection: Individual INSERTs (1-5 records)

```python
# Individual INSERTs acceptable (few objects)
for record in infrastructure_records:
    session.add(InfrastructureDetection(**record))

await session.commit()
```

**Why no bulk insert:**
- Typical infrastructure count: 1-5 per image
- Bulk insert overhead not justified
- Simpler code for low-volume data

**When to use bulk:**
```python
# Only if detection_type == 'all' and count > 20
if len(infrastructure_records) > 20:
    session.bulk_insert_mappings(InfrastructureDetection, infrastructure_records)
```

## Performance Breakdown

Total time: **5-10 seconds per image**

| Phase | Time | % of Total | Notes |
|-------|------|------------|-------|
| Model load (cached) | 0.1ms | ~0% | Singleton pattern |
| S3 download | 1s | ~15% | I/O-bound |
| SAHI slicing + inference | 2-4s | **~70%** | GPU-bound (CRITICAL) |
| GPS calculation | 15ms | ~0.3% | Simple math |
| Database save | 10ms | ~0.2% | Few INSERTs |
| Other | 100ms | ~1.5% | Python overhead |

**Why faster than plant detection:**
- Fewer SAHI slices: 20 vs 42 (larger slice size)
- Fewer objects: 1-5 vs 50-200 (less postprocessing)
- No band-based estimation algorithm
- Simpler database operations

**Bottleneck:** GPU inference (70% of time), same as plant detection

## Error Handling

### Warning States

**1. No infrastructure found** (line 244)
- **Cause:** YOLO found 0 infrastructure
- **Action:** Return success with count=0, no warning flag
- **Reason:** Many agricultural fields have no electrical infrastructure (this is NORMAL)

**Contrast with plant detection:**
- No plants found → warning (unusual, possible error)
- No infrastructure found → normal (expected in many fields)

### Graceful Degradation

**Low confidence detections:**
```python
if 0.5 <= confidence < 0.6:
    # Below threshold but might be valid
    # Save to 'uncertain_detections' table for manual review
    session.add(UncertainDetection(**record))
```

**GPS calculation failure:**
```python
try:
    gps_lat, gps_lon = calculate_gps(detection)
except GPSCalculationError:
    # Save detection without GPS (still valuable)
    gps_lat, gps_lon = None, None
    warning_state = 'gps_unavailable'
```

## Database Schema

### Tables Used

**`infrastructure_detections`** (INSERT):
```sql
CREATE TABLE infrastructure_detections (
    id UUID PRIMARY KEY,
    image_id UUID REFERENCES s3_images(id),
    class_name VARCHAR(50) NOT NULL,
    class_id INT NOT NULL,
    bbox JSONB NOT NULL,  -- [x1, y1, x2, y2]
    confidence FLOAT NOT NULL CHECK (confidence >= 0.6),
    gps_latitude FLOAT,  -- Individual GPS per detection
    gps_longitude FLOAT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_infra_image ON infrastructure_detections(image_id);
CREATE INDEX idx_infra_class ON infrastructure_detections(class_name);
CREATE INDEX idx_infra_gps ON infrastructure_detections USING GIST (
    ST_SetSRID(ST_MakePoint(gps_longitude, gps_latitude), 4326)
);  -- PostGIS spatial index for geospatial queries
```

**`infrastructure_summaries`** (INSERT):
```sql
CREATE TABLE infrastructure_summaries (
    image_id UUID PRIMARY KEY REFERENCES s3_images(id),
    total_count INT NOT NULL,
    overall_confidence FLOAT NOT NULL,
    by_class JSONB NOT NULL,  -- {'electrical_box': {'count': 3, ...}, ...}
    processing_time_s FLOAT,
    sahi_used BOOLEAN,
    confidence_band VARCHAR(20)
);
```

**`s3_images`** (UPDATE):
```sql
UPDATE s3_images
SET
    infrastructure_status = 'completed',
    infrastructure_completed_at = NOW(),
    infrastructure_count = :total_count
WHERE id = :image_id_pk;
```

## Code Patterns

### Pattern 1: Detection Type Filtering
```python
def get_target_classes(detection_type):
    """Map detection_type to YOLO class names"""
    mapping = {
        'boxes': ['electrical_box', 'junction_box', 'control_panel'],
        'plugs': ['wall_plug', 'industrial_plug', 'outlet'],
        'meters': ['electric_meter', 'smart_meter'],
        'all': [...]  # All classes
    }
    return mapping.get(detection_type, mapping['all'])
```

### Pattern 2: GPS Calculation
```python
def calculate_gps(detection, field_bounds, img_size):
    """Convert pixel coordinates to GPS"""
    bbox = detection['bbox']
    center_x = (bbox[0] + bbox[2]) / 2
    center_y = (bbox[1] + bbox[3]) / 2

    # Normalize to [0, 1]
    norm_x = center_x / img_size[0]
    norm_y = center_y / img_size[1]

    # Map to field bounds
    gps_lat = field_bounds['min_lat'] + (norm_y * field_bounds['lat_span'])
    gps_lon = field_bounds['min_lon'] + (norm_x * field_bounds['lon_span'])

    return gps_lat, gps_lon
```

### Pattern 3: Confidence Band Calculation
```python
def calculate_confidence_band(overall_confidence):
    """Simpler than plant detection (no band-based complexity)"""
    if overall_confidence >= 0.75:
        return 'HIGH'
    elif overall_confidence >= 0.6:
        return 'MEDIUM'
    else:
        return 'LOW'  # Unusual with 0.6 threshold
```

## Use Cases

### 1. Maintenance Planning
```python
# Query all infrastructure in field
infrastructure = db.query("""
    SELECT class_name, gps_latitude, gps_longitude, confidence
    FROM infrastructure_detections
    WHERE image_id IN (
        SELECT id FROM s3_images WHERE field_id = :field_id
    )
    ORDER BY class_name
""")

# Generate work order: "Inspect 3 electrical boxes at these GPS coordinates"
```

### 2. Safety Audits
```python
# Find fields with industrial plugs (requires certified electrician)
fields_with_industrial = db.query("""
    SELECT DISTINCT f.name, f.id
    FROM fields f
    JOIN s3_images i ON i.field_id = f.id
    JOIN infrastructure_detections d ON d.image_id = i.id
    WHERE d.class_name = 'industrial_plug'
""")
```

### 3. Geospatial Analysis (PostGIS)
```python
# Find infrastructure within 50m of field boundary (safety risk)
near_boundary = db.query("""
    SELECT d.*, ST_Distance(
        ST_SetSRID(ST_MakePoint(d.gps_longitude, d.gps_latitude), 4326)::geography,
        f.geom::geography
    ) as distance_m
    FROM infrastructure_detections d
    JOIN s3_images i ON i.image_id = d.image_id
    JOIN fields f ON f.id = i.field_id
    WHERE ST_Distance(...) < 50
""")
```

## Related Diagrams

- **04_ml_parent_segmentation_detailed.mmd:** Parent task that spawns this child
- **05_sahi_detection_child_detailed.mmd:** Plant detection (comparison)
- **07_callback_aggregation_detailed.mmd:** Receives results from all detection tasks

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-10-08 | Initial detailed subflow for infrastructure detection |

---

**Notes:**
- Infrastructure detection is a value-added feature for agricultural clients
- GPS per detection enables precise maintenance navigation
- Higher confidence threshold reduces false positives (costly for maintenance crews)
