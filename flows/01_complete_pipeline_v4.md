# Complete ML Pipeline V4 - Full Detail

## Purpose

This diagram provides a **comprehensive, implementation-level** view of the entire DemeterAI ML processing pipeline, from photo upload through stock batch creation, with all error paths, retries, and optimizations documented.

## Version History

- **v4.0** (2025-10-07): Complete refactor to Mermaid v11.3.0+ syntax, added performance annotations, edge IDs, retry logic
- **v3.0** (2025-10-07): Added circuit breaker, band-based estimation, warning states
- **v2.0**: Previous iteration (legacy)

## Scope

- **Level**: Full implementation detail (~1000 lines, ~300 nodes)
- **Audience**: Senior developers, system architects, DevOps engineers
- **Detail**: Every database query, API call, algorithm step, error path
- **Mermaid Version**: v11.3.0+ (modern syntax throughout)

## What It Represents

This diagram documents the complete journey of a plant cultivation photo through the system with full technical detail:

### 1. API Entry (Section 1)
- FastAPI controller receives MultipartForm upload
- Validation: Content-Type, file extensions, size limits
- UUID v4 generation (PK strategy, NOT database SERIAL)
- Temporary file storage (`/tmp/uploads/`)
- Database INSERT into `s3_images` table
- Celery task chunking and dispatch

**Performance**: ~200-300ms total API response time

### 2. S3 Upload with Circuit Breaker (Section 2)
- **Pattern**: Circuit Breaker to prevent S3 API exhaustion
- EXIF metadata extraction (GPS, timestamp, resolution, camera)
- S3 upload with AES256 server-side encryption
- Thumbnail generation (400x400 LANCZOS, AVIF compression 50% reduction)
- Retry logic: Exponential backoff with full jitter (AWS best practice)
- Circuit states: CLOSED → OPEN → HALF_OPEN
- **Threshold**: 50% failure rate triggers circuit open
- **Recovery**: 60-second timeout before retry allowed

**Performance**: ~4-10 seconds per 20-image chunk

### 3. ML Parent Task - Segmentation (Section 3)
- **GPU Worker**: pool=solo (1 worker per GPU, MANDATORY)
- Model singleton pattern: Cached per worker, loaded once
- GPS-based geolocation: PostGIS `ST_Contains` with SP-GiST index
- **Graceful Degradation**: Warning states (not failures):
  - `needs_location`: GPS missing or coordinates outside cultivation
  - `needs_config`: Storage location not configured (product/packaging unknown)
  - `needs_calibration`: Density parameters missing
- YOLO v11 segmentation: conf=0.30, iou=0.50, imgsz=1024, half=True (FP16)
- Mask processing: Morphological smoothing, hole filling
- Mask classification: segment | cajon | almacigo | plug
- **Celery Chord Pattern**: Parent spawns children, waits for all to complete

**Performance**: ~2-3 minutes total (mostly GPU segmentation)

### 4. SAHI Detection Child Task (Section 4)
- **SAHI**: Slicing Aided Hyper Inference for high-resolution images
- 640×640 slices with 20% overlap
- YOLO detection per slice (conf=0.25, max_det=1500)
- Automatic NMS (Non-Maximum Suppression, threshold=0.5)
- **Band-Based Estimation** (CRITICAL INNOVATION):
  1. Create detection mask from bounding boxes
  2. Subtract from segment mask
  3. Divide remaining area into 5 horizontal bands
  4. Check detections within each band
  5. **Auto-Calibration**: If bands have detections → `avg_area = mean(band_areas)`
  6. Fallback: Use `density_parameters` if no band detections
  7. HSV vegetation filter (green hue: 35-85)
  8. Calculate area in cm² (pixel-to-cm conversion)
  9. Estimate count: `area_cm2 / avg_area × overlap_factor`
  10. UPDATE `density_parameters` (self-learning system)
- Bulk INSERT with asyncpg (future upgrade for 350x performance)

**Performance**: ~1-2 minutes per segment

### 5. Boxes/Plugs Direct Detection (Section 5)
- **WITHOUT SAHI**: Direct YOLO detection (no slicing)
- Classes: cajon (boxes), plug (plug trays), almacigo (seedling trays)
- Same estimation algorithm as SAHI (band-based with auto-calibration)
- Faster than SAHI due to no slicing overhead

**Performance**: ~30-60 seconds per class

### 6. Callback Aggregation (Section 6)
- **Triggered**: When ALL child tasks complete (Chord callback)
- Aggregate totals: detected + estimated counts
- Weighted average confidence
- **Visualization Generation**:
  - Load original image
  - Draw detections: Transparent circles (80% opacity)
  - Draw estimations: Smooth polygon masks (different color)
  - Add legend: Totals, confidence percentage
  - AVIF compression (quality=85, 50% smaller than JPEG)
  - Upload to S3: `processed/YYYY/MM/DD/uuid_viz.avif`
- **Stock Batch Creation**:
  - Group movements by classification
  - Find/create storage bins
  - Generate `batch_code`: `LOC{id}-PROD{id}-{YYYYMMDD}-{seq}`
  - INSERT `stock_batches` with quantities, quality score
  - Link movements to batches
- **Comprehensive Verification**:
  - Validate all foreign keys
  - Check batch data integrity
  - Verify movement consistency
  - Ensure totals match: `batch quantities = sum(movements)`
  - On error: **Partial rollback** (DELETE batches, keep detections for debug)
- GPU cache clear (every 100 tasks to prevent OOM)

**Performance**: ~1-2 minutes callback

## Key Technical Improvements (v3 → v4)

### 1. **Modern Mermaid v11.3.0+ Syntax**
All nodes now use standardized syntax:
```mermaid
NODE@{ shape: cyl, label: "Database query..." }
NODE@{ shape: diamond, label: "Decision..." }
NODE@{ shape: subproc, label: "Complex process..." }
NODE@{ shape: stadium, label: "Start/End..." }
```

**Before (v3)**:
```mermaid
NODE["Description"]
NODE{"Decision"}
NODE[("Database")]
```

**After (v4)**:
```mermaid
NODE@{ shape: rect, label: "Description" }
NODE@{ shape: diamond, label: "Decision" }
NODE@{ shape: cyl, label: "Database" }
```

### 2. **Performance Annotations**
Every major step includes:
- ⏱️ **Timing**: Approximate duration (`~500ms`, `~2min`)
- ⚡ **Parallelism**: Parallel vs. sequential execution
- ♻️ **Retry Logic**: Max retries, backoff strategy
- ⏰ **Timeouts**: Circuit breaker recovery times

### 3. **Edge IDs for Critical Path**
```mermaid
START e1@--> VALIDATE
e1@{ class: critical-path }  ← Styled separately
```

### 4. **Semantic Shapes**
- `cyl`: Database operations (SELECT, INSERT, UPDATE)
- `diamond`: Decision points (if/else logic)
- `subproc`: Complex sub-processes (multi-step algorithms)
- `stadium`: Start/end points
- `circle`: Events (callbacks, triggers)
- `rect`: Simple processes

### 5. **Comprehensive Comments**
- `%%` comments explain complex sections
- Section headers with detail level references
- Pattern explanations (Circuit Breaker, Chord, etc.)

### 6. **Frontend Polling Removed**
Separated into `flows/08_frontend_polling_detailed.mmd` for clarity.

## Related Detailed Diagrams

For even more granular implementation details, see:

- **Master Overview**: `flows/00_master_overview.mmd` (high-level, ~50 nodes)
- **API Entry**: `flows/02_api_entry_detailed.mmd` (line-by-line code)
- **S3 Circuit Breaker**: `flows/03_s3_upload_circuit_breaker_detailed.mmd`
- **ML Parent**: `flows/04_ml_parent_segmentation_detailed.mmd`
- **SAHI Detection**: `flows/05_sahi_detection_child_detailed.mmd`
- **Boxes Detection**: `flows/06_boxes_plugs_detection_detailed.mmd`
- **Callback Aggregation**: `flows/07_callback_aggregate_batches_detailed.mmd`
- **Frontend Polling**: `flows/08_frontend_polling_detailed.mmd`

## How It Fits in the System

This diagram is the **authoritative reference** for the complete ML pipeline implementation. Use it to:

- Understand the full system architecture (API → ML → Database)
- Debug production issues (trace photo through entire pipeline)
- Optimize performance (identify bottlenecks with timing annotations)
- Add new features (understand where to integrate)
- Review error handling (all error paths documented)
- Plan scaling (see parallel execution points)

## Critical Patterns Documented

### 1. Circuit Breaker Pattern (S3 Upload)
Prevents S3 API exhaustion when AWS has issues:
- **CLOSED**: Normal operation, all requests go through
- **OPEN**: Too many failures (50%), reject all requests for 60s
- **HALF_OPEN**: After timeout, allow test requests

### 2. Celery Chord Pattern (ML Parent → Children)
Parallel execution with callback:
```python
chord(
  group(*child_tasks),  # All run in parallel
  callback_task.s()     # Runs when ALL complete
)
```

### 3. Model Singleton Pattern (GPU Workers)
One model per GPU worker, cached in memory:
```python
model_key = f'yolo_v11_seg_{worker_id}'
if model_key not in cache:
  model = YOLO('yolo11m-seg.pt')
  model.to(f'cuda:{worker_id}')
  cache[model_key] = model
```

### 4. Band-Based Auto-Calibration (SAHI/Boxes)
System learns from real detections, updates `density_parameters`:
- Divide undetected area into 5 horizontal bands
- Check detections in each band
- Calculate average plant area from band detections
- **Priority**: Band average > density_parameters (fallback)
- UPDATE database with new calibrated values

### 5. Graceful Degradation (Warning States)
Missing data creates warnings, NOT failures:
- User can complete manually (assign location, configure, calibrate)
- Photo and processing session preserved
- Frontend shows specific actions needed

## Database Tables Referenced

- `s3_images`: Photo metadata, S3 keys, EXIF, GPS, status
- `photo_processing_sessions`: Processing state, totals, confidence
- `storage_locations`: Geospatial hierarchy (PostGIS)
- `storage_location_config`: Product + packaging expected
- `density_parameters`: Area per plant, overlap factor (auto-calibrated)
- `detections`: Bounding boxes, confidence (partitioned daily)
- `estimations`: Vegetation masks, estimated counts (partitioned daily)
- `stock_movements`: Event sourcing (foto, plantar, muerte, etc.)
- `stock_batches`: Aggregated inventory state
- `classifications`: Product + packaging + model version

## Performance Summary

| Phase | Duration | Bottleneck | Optimization |
|-------|----------|------------|--------------|
| API Entry | ~200-300ms | Database INSERT | Connection pooling |
| S3 Upload | ~4-10s/20 images | Network I/O | Chunking, circuit breaker |
| ML Segmentation | ~500ms | GPU compute | FP16 inference, model caching |
| SAHI Detection | ~1-2 min | GPU + slicing | High-res images, 640×640 slices |
| Boxes Detection | ~30-60s | GPU compute | Direct detection (no SAHI) |
| Callback | ~1-2 min | Visualization rendering | AVIF compression |
| **Total** | **~3-5 min** | GPU availability | Scale GPU workers |

## Error Handling

All error paths documented:
- **400 Bad Request**: Invalid file format/size (API entry)
- **File Not Found**: Race condition temp files (S3 upload)
- **Circuit Breaker Open**: S3 API issues (automatic recovery)
- **Image Not Available**: S3 task failed, file missing (ML parent)
- **Location Not Found**: GPS outside cultivation (warning state)
- **Config Missing**: Storage location not configured (warning state)
- **Density Missing**: No calibration data (warning state)
- **No Detections**: Valid photo but empty (warning, user review)
- **Verification Failed**: Batch creation integrity check (partial rollback)

---

**Version**: 4.0
**Last Updated**: 2025-10-07
**Diagram Size**: ~1000 lines, ~300 nodes
**Mermaid**: v11.3.0+ syntax
**Author**: DemeterAI Engineering Team
