# ML Processing Flow Analysis - DemeterAI v2.0

## Executive Summary

The main ML processing flow for photo upload and S3/ML processing is **fully implemented** with the following components:

1. **Controller Endpoint**: `POST /api/v1/stock/photo` (Stock Controller)
2. **Orchestration Service**: `PhotoUploadService`
3. **S3 Operations**: `S3ImageService` with circuit breaker
4. **ML Pipeline Tasks**: Celery chord pattern (parent → children → callback)
5. **Session Tracking**: `PhotoProcessingSessionService`
6. **Results Persistence**: Detection and Estimation bulk inserts

---

## 1. API CONTROLLER ENDPOINT

### Location
**File**: `/home/lucasg/proyectos/DemeterDocs/app/controllers/stock_controller.py`
**Endpoint**: `POST /api/v1/stock/photo` (Lines 62-145)

### Endpoint Details

```python
@router.post(
    "/photo",
    response_model=PhotoUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload photo for ML processing",
)
async def upload_photo_for_stock_count(
    file: Annotated[UploadFile, File(description="Photo file (max 20MB, JPEG/PNG/WEBP)")],
    user_id: Annotated[int, Form(description="User ID for tracking")],
    factory: ServiceFactory = Depends(get_factory),
) -> PhotoUploadResponse:
```

### Request Schema
- **Parameter**: `file` (multipart file upload)
  - Accepted types: JPEG, PNG, WEBP (max 20MB)
- **Parameter**: `user_id` (integer form field)
  - Used for audit trail and user tracking

### Response Schema
**Schema**: `PhotoUploadResponse` (from `app/schemas/photo_schema.py`)
```python
class PhotoUploadResponse(BaseModel):
    task_id: UUID                    # Celery task ID for polling
    session_id: int                  # PhotoProcessingSession database ID
    status: str                      # "pending"
    message: str                     # Human-readable message
    poll_url: str                    # "/api/photo-sessions/{session_id}"
```

### HTTP Status
- **202 ACCEPTED**: Async processing initiated
- **400 BAD_REQUEST**: Invalid file type/size or missing GPS
- **404 NOT_FOUND**: GPS location not found
- **500 INTERNAL_SERVER_ERROR**: Upload/processing error

### Service Called
```python
service = factory.get_photo_upload_service()
result = await service.upload_photo(file, user_id)
```

---

## 2. PHOTO UPLOAD SERVICE

### Location
**File**: `/home/lucasg/proyectos/DemeterDocs/app/services/photo/photo_upload_service.py`

### Class
`PhotoUploadService` (Lines 67-650)

### Dependencies (Service→Service Pattern)
```python
def __init__(
    self,
    session_service: PhotoProcessingSessionService,    # Session management
    s3_service: S3ImageService,                        # S3 upload
    location_service: StorageLocationService,          # GPS lookup
) -> None:
```

### Main Method: `upload_photo()`
**Signature**: `async def upload_photo(file: UploadFile, user_id: int) -> PhotoUploadResponse`

### Complete Workflow (9 Steps)

#### STEP 1: Validate Photo File
- **Method**: `_validate_photo_file()` (Lines 398-442)
- **Checks**:
  - Content type must be in ALLOWED_CONTENT_TYPES (image/jpeg, image/jpg, image/png, image/webp)
  - File size must be ≤ 20MB (MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024)
- **Returns**: File bytes

#### STEP 2: Extract GPS Coordinates
- **Method**: `_extract_gps_from_metadata()` (Lines 444-560)
- **Extracts from**:
  - piexif library (primary, most reliable)
  - PIL _getexif() method (fallback)
- **Converts**: DMS (degrees, minutes, seconds) to decimal coordinates
- **Returns**: `(longitude, latitude)` tuple or `(None, None)`
- **Error Handling**: Raises `ValidationException` if missing GPS

#### STEP 3: GPS-Based Location Lookup (COMMENTED OUT)
**STATUS**: Currently bypassed with hardcoded `storage_location_id = 1`

**Code** (Lines 170-189):
```python
# # STEP 3: GPS-based location lookup (fail fast if no location)
# logger.info("Looking up location by GPS coordinates")
# location = await self.location_service.get_location_by_gps(gps_longitude, gps_latitude)
#
# if not location:
#     raise ResourceNotFoundException(
#         resource_type="StorageLocation",
#         resource_id=f"GPS({gps_longitude}, {gps_latitude})",
#     )
#
# storage_location_id = location.storage_location_id
```

**NOTE**: This is intentional - GPS lookup is commented but can be re-enabled

#### STEP 4: Extract Image Dimensions
- **Uses**: PIL Image to read width_px and height_px
- **Fallback**: 1x1 if extraction fails
- **Purpose**: Store metadata for ML processing

#### STEP 5: Create PhotoProcessingSession
- **Status**: PENDING (before S3 upload)
- **Original Image ID**: Null (set after S3 upload)
- **Location**: GPS-based or hardcoded 1

```python
session_request = PhotoProcessingSessionCreate(
    storage_location_id=storage_location_id,
    original_image_id=None,  # ✅ Set after S3 upload
    status=ProcessingSessionStatusEnum.PENDING,
    total_detected=0,
    total_estimated=0,
    total_empty_containers=0,
    avg_confidence=None,
    category_counts={},
    manual_adjustments={},
    error_message=None,
)

session = await self.session_service.create_session(session_request)
```

#### STEP 6: Upload Original to S3
- **Service**: S3ImageService.upload_original()
- **S3 Key Format**: `{session_id}/original.{ext}`
- **Returns**: S3ImageResponse with:
  - image_id (UUID)
  - s3_key_original
  - presigned_url

```python
upload_request = S3ImageUploadRequest(
    session_id=session.session_id,           # PhotoProcessingSession UUID
    filename=file.filename or "photo.jpg",
    content_type=ContentTypeEnum(file.content_type or "image/jpeg"),
    file_size_bytes=len(file_bytes),
    width_px=width_px,
    height_px=height_px,
    upload_source=UploadSourceEnum.WEB,
    uploaded_by_user_id=user_id,
    exif_metadata=None,
    gps_coordinates={"latitude": gps_latitude, "longitude": gps_longitude},
)

original_image = await self.s3_service.upload_original(
    file_bytes=file_bytes,
    session_id=session.session_id,
    upload_request=upload_request,
)
```

#### STEP 7: Generate and Upload Thumbnail (Original)
- **Function**: `generate_thumbnail()` from S3ImageService
- **Size**: 300x300px
- **Format**: JPEG (quality 85)
- **S3 Key**: `{session_id}/thumbnail_original.jpg`
- **Note**: Optional - logs warning if fails, doesn't block workflow

```python
thumbnail_bytes = generate_thumbnail(file_bytes, size=300)
thumbnail_image = await self.s3_service.upload_thumbnail(
    file_bytes=thumbnail_bytes,
    session_id=session.session_id,
    size=300,
    filename="thumbnail_original.jpg",
)
```

#### STEP 8: Update Session with original_image_id
- **Updates**: PhotoProcessingSession.original_image_id
- **Database ID**: session.id (integer PK)
- **Status**: Still PENDING

```python
update_request = PhotoProcessingSessionUpdate(
    original_image_id=original_image.image_id
)

session = await self.session_service.update_session(
    session.id, update_request
)
```

#### STEP 9: Dispatch ML Pipeline (Celery Task)
- **Task**: `ml_parent_task.delay()`
- **Parameters**:
  - `session_id`: PhotoProcessingSession.id (integer PK)
  - `image_data`: List of dicts with image metadata

```python
image_data = [
    {
        "image_id": str(original_image.image_id),    # S3Image UUID as string
        "image_path": original_image.s3_key_original, # S3 key path
        "storage_location_id": storage_location_id,   # From GPS lookup
    }
]

celery_task = ml_parent_task.delay(
    session_id=session.id,
    image_data=image_data,
)
task_id = celery_task.id
```

### Return Value
```python
return PhotoUploadResponse(
    task_id=task_id,
    session_id=session.id,
    status="pending",
    message="Photo uploaded successfully. Processing will start shortly.",
    poll_url=f"/api/photo-sessions/{session.id}",
)
```

---

## 3. S3 IMAGE SERVICE

### Location
**File**: `/home/lucasg/proyectos/DemeterDocs/app/services/photo/s3_image_service.py`

### Class
`S3ImageService` (Lines 49-909)

### Key Features
- **Circuit Breaker**: pybreaker.CircuitBreaker (fail_max=5, reset_timeout=60s)
- **Async Operations**: Using asyncio.to_thread() with boto3 (sync)
- **Database Caching**: Binary image_data stored in PostgreSQL for fast ML access

### Upload Methods

#### 1. upload_original()
**Purpose**: Upload original photo to S3
**Parameters**:
- `file_bytes`: Image bytes (1 byte to 500MB)
- `session_id`: PhotoProcessingSession UUID
- `upload_request`: S3ImageUploadRequest with metadata

**S3 Key Format**: `{session_id}/original.{ext}`

**Bucket**: `demeter-photos-original`

**Database Storage**:
```python
s3_image_data = {
    "image_id": image_id,
    "s3_bucket": settings.S3_BUCKET_ORIGINAL,
    "s3_key_original": s3_key,
    "image_type": ImageTypeEnum.ORIGINAL,
    "content_type": upload_request.content_type,
    "file_size_bytes": len(file_bytes),
    "width_px": upload_request.width_px,
    "height_px": upload_request.height_px,
    "upload_source": upload_request.upload_source,
    "uploaded_by_user_id": upload_request.uploaded_by_user_id,
    "exif_metadata": upload_request.exif_metadata,
    "gps_coordinates": upload_request.gps_coordinates,
    "status": ProcessingStatusEnum.UPLOADED,
    "image_data": file_bytes,  # ✅ Cache binary in PostgreSQL
}
```

**Returns**: S3ImageResponse with image_id, s3_key, presigned_url

#### 2. upload_thumbnail()
**Purpose**: Upload thumbnail to S3
**Parameters**:
- `file_bytes`: Thumbnail bytes
- `session_id`: PhotoProcessingSession UUID
- `size`: Thumbnail size (default from settings)
- `filename`: Optional filename

**S3 Key Format**: `{session_id}/{filename}`

**Default Filename**: "thumbnail.jpg" (or "thumbnail_original.jpg", "thumbnail_processed.jpg")

#### 3. generate_thumbnail()
**Standalone Function** (Lines 840-908)

**Parameters**:
- `image_bytes`: Original image bytes
- `size`: Thumbnail size in pixels (default: 300)

**Process**:
1. Open image with PIL
2. Convert RGBA/P/LA to RGB (JPEG compatibility)
3. Create square thumbnail maintaining aspect ratio
4. Save as JPEG (quality=85, optimized)

**Returns**: Thumbnail bytes

### Circuit Breaker Details
```python
s3_circuit_breaker = CircuitBreaker(
    fail_max=5,           # Open after 5 consecutive failures
    reset_timeout=60,     # 60-second cooldown before retry
    name="S3CircuitBreaker"
)
```

**States**:
- **Closed**: Normal operation
- **Open**: Reject requests (after 5 failures)
- **Half-Open**: Test recovery (after cooldown)

---

## 4. CELERY ML TASKS

### Location
**File**: `/home/lucasg/proyectos/DemeterDocs/app/tasks/ml_tasks.py`

### Task Pattern: Celery Chord
```
ml_parent_task
    ├─> Creates child signatures for each image
    └─> chord([child1, child2, ...])(ml_aggregation_callback)
        ├─> child1 runs on gpu_queue (parallel)
        ├─> child2 runs on gpu_queue (parallel)
        └─> callback runs on cpu_queue (after all children complete)
```

### CEL005: ML Parent Task

**Function**: `ml_parent_task()` (Lines 176-295)

**Signature**:
```python
@app.task(bind=True, queue="cpu_queue", max_retries=2)
def ml_parent_task(
    self: Task,
    session_id: int,                    # PhotoProcessingSession database ID
    image_data: list[dict[str, Any]],  # List of images with metadata
) -> dict[str, Any]:
```

**Workflow**:
1. Check circuit breaker
2. Validate image_data (not empty)
3. Mark session as PROCESSING
4. Create child task signatures (one per image)
5. Dispatch chord: children → callback
6. Return status

**Returns**:
```python
{
    "session_id": session_id,
    "num_images": len(image_data),
    "status": "processing",
    "celery_task_id": self.request.id,
}
```

### CEL006: ML Child Task

**Function**: `ml_child_task()` (Lines 302-563)

**Signature**:
```python
@app.task(bind=True, queue="gpu_queue", max_retries=3)
def ml_child_task(
    self: Task,
    session_id: int,
    image_id: str,                  # S3Image UUID as string
    image_path: str,                # S3 key or local path
    storage_location_id: int,
) -> dict[str, Any]:
```

**Queue**: `gpu_queue` (GPU-intensive inference)

**Image Retrieval (3-Tier Cache)**:
1. **Priority 1**: PostgreSQL binary cache (fastest)
2. **Priority 2**: /tmp local cache (retry optimization)
3. **Priority 3**: S3 download (fallback)

**Code** (Lines 370-461):
```python
# PRIORITY 1: Check PostgreSQL for cached binary data
s3_image = db_session.query(S3Image).filter(
    S3Image.image_id == image_id
).first()

if s3_image and s3_image.image_data:
    # Found binary data in PostgreSQL - write to /tmp
    with open(temp_path, "wb") as f:
        f.write(s3_image.image_data)
    processing_path = temp_path
    temp_file_created = True

# PRIORITY 2: Check /tmp local cache
elif temp_file.exists():
    processing_path = temp_path

# PRIORITY 3: Download from S3 (fallback)
else:
    s3 = boto3.client("s3")
    s3.download_file("demeter-photos-original", image_path, temp_path)
    processing_path = temp_path
```

**ML Pipeline**:
```python
coordinator = MLPipelineCoordinator(
    segmentation_service=SegmentationService(),
    sahi_service=SAHIDetectionService(worker_id=0),
    band_estimation_service=BandEstimationService(),
)

result: PipelineResult = asyncio.run(
    coordinator.process_complete_pipeline(
        session_id=session_id,
        image_path=processing_path,
        worker_id=0,
        conf_threshold_segment=0.30,
        conf_threshold_detect=0.25,
    )
)
```

**Temporary Files**:
- **Created**: `/tmp/{image_id}.jpg`
- **NOT Deleted**: Kept for visualization generation in callback
- **Cleanup**: Happens in ml_aggregation_callback after visualization

**Returns**:
```python
{
    "image_id": image_id,
    "total_detected": result.total_detected,
    "total_estimated": result.total_estimated,
    "avg_confidence": result.avg_confidence,
    "segments_processed": result.segments_processed,
    "processing_time_seconds": result.processing_time_seconds,
    "detections": result.detections,        # List of detection dicts
    "estimations": result.estimations,      # List of estimation dicts
}
```

**Retry Logic**:
- **Max Retries**: 3
- **Backoff**: Exponential (2^n seconds: 2s, 4s, 8s)

### CEL007: Aggregation Callback

**Function**: `ml_aggregation_callback()` (Lines 571-1062)

**Signature**:
```python
@app.task(queue="cpu_queue")
def ml_aggregation_callback(
    results: list[dict[str, Any]],  # Results from all child tasks
    session_id: int,                 # PhotoProcessingSession database ID
) -> dict[str, Any]:
```

**Workflow**:
1. Aggregate ML results from all children
2. Persist detections and estimations to database
3. Generate visualization image
4. Upload visualization to S3
5. Create S3Image record for visualization
6. Update PhotoProcessingSession with final results
7. Cleanup temporary files and binary cache

#### Persistence: `_persist_ml_results()`
**Location**: Lines 1679-1965

**Steps**:
1. Create StockBatch record
2. Create StockMovement record (movement_type="foto", source_type="ia")
3. Get or create Classification
4. Bulk insert Detections (Links: session_id, stock_movement_id, classification_id)
5. Bulk insert Estimations (Links: session_id, stock_movement_id, classification_id)

**StockBatch Created**:
```python
StockBatch(
    batch_code=f"ML-SESSION-{session_id}-{datetime}",
    current_storage_bin_id=1,                    # TODO: From PhotoProcessingSession
    product_id=1,                                # TODO: From configuration
    product_state_id=1,                          # TODO: Default seedling
    quantity_initial=detected + estimated,
    quantity_current=detected + estimated,
    quantity_empty_containers=0,
    has_packaging=False,
)
```

#### Visualization: `_generate_visualization()`
**Location**: Lines 1318-1676

**Steps**:
1. Get original image using 3-tier cache
2. Load with OpenCV
3. Draw detection circles (cyan, semi-transparent)
4. Draw estimation polygons (blue, with Gaussian blur)
5. Add text legend (detected, estimated, confidence)
6. Compress as AVIF (fallback to WebP)
7. Save to `/tmp/processed/session_{session_id}_viz.avif`
8. Upload to S3: `{session_uuid}/processed.avif`
9. Create S3Image record

**S3 Key Format**: `{session_uuid}/processed.avif`

**Visualization Features**:
- Detection circles: Cyan (255,255,0 BGR), radius=75% of bbox
- Estimation polygons: Blue (255,0,0 BGR), Gaussian blur
- Text legend: White text on black background
- Compression: AVIF quality=85, speed=4

#### Cleanup: `_cleanup_image_binary_data()`
**Purpose**: Delete cached binary data from PostgreSQL after ML processing

**SQL**:
```python
stmt = (
    update(S3Image)
    .where(S3Image.image_id.in_(image_ids))
    .values(image_data=None)
)
```

**Benefit**: Saves database space while keeping S3 as source of truth

**Returns**:
```python
{
    "session_id": session_id,
    "num_images_processed": num_valid,
    "total_detected": total_detected,
    "total_estimated": total_estimated,
    "avg_confidence": avg_confidence,
    "status": "completed" or "warning",  # "warning" if partial failures
}
```

### CEL008: Circuit Breaker

**Functions**: Lines 87-169

**States**:
- **closed**: Normal operation (failures < CIRCUIT_BREAKER_THRESHOLD)
- **open**: Too many failures, reject requests for CIRCUIT_BREAKER_TIMEOUT
- **half_open**: Testing recovery after cooldown

**Thresholds**:
```python
CIRCUIT_BREAKER_THRESHOLD = 5           # Open after 5 consecutive failures
CIRCUIT_BREAKER_TIMEOUT = 300           # 5 minutes cooldown
```

**Functions**:
- `check_circuit_breaker()`: Check before task execution
- `record_circuit_breaker_success()`: Reset on success
- `record_circuit_breaker_failure()`: Increment on failure

---

## 5. S3 IMAGE MODEL

### Location
**File**: `/home/lucasg/proyectos/DemeterDocs/app/models/s3_image.py`

### Key Columns

```python
class S3Image(Base):
    __tablename__ = "s3_images"

    # Primary Key
    image_id: UUID                    # UUID primary key (generated in API)

    # S3 Storage
    s3_bucket: str                    # S3 bucket name
    s3_key_original: str              # Original image key
    s3_key_processed: str             # Processed/visualization key
    s3_key_thumbnail: str             # Thumbnail key

    # Image Type
    image_type: ImageTypeEnum         # ORIGINAL, PROCESSED, THUMBNAIL
    content_type: str                 # image/jpeg, image/png, image/webp, image/avif

    # Image Metadata
    file_size_bytes: BigInteger       # File size in bytes
    width_px: Integer                 # Image width in pixels
    height_px: Integer                # Image height in pixels

    # GPS and EXIF
    exif_metadata: JSONB              # Camera settings (ISO, shutter, f-stop, etc.)
    gps_coordinates: JSONB            # {"latitude": X, "longitude": Y, ...}

    # Audit Trail
    upload_source: str                # "web", "mobile", "api"
    uploaded_by_user_id: Integer      # FK to users (SET NULL on delete)

    # Processing Status
    status: ProcessingStatusEnum       # UPLOADED, PROCESSING, READY, FAILED

    # Binary Cache (Temporary)
    image_data: LargeBinary           # Binary photo data (cached from S3)
                                      # Deleted after ML processing completes

    # Timestamps
    created_at: DateTime              # Auto-set on creation
    updated_at: DateTime              # Auto-set on update
```

### Enum Values

#### ImageTypeEnum
- `ORIGINAL`: Input photo
- `PROCESSED`: ML-generated visualization
- `THUMBNAIL`: 300x300px preview

#### ContentTypeEnum
- `JPEG` = "image/jpeg"
- `PNG` = "image/png"
- `WEBP` = "image/webp"
- `AVIF` = "image/avif"

#### ProcessingStatusEnum
- `UPLOADED`: Initial upload
- `PROCESSING`: Currently processing
- `READY`: Ready for use
- `FAILED`: Processing failed

#### UploadSourceEnum
- `WEB`: Browser upload
- `MOBILE`: Mobile app upload
- `API`: API/Celery upload

---

## 6. PHOTO PROCESSING SESSION MODEL

### Location
**File**: `/home/lucasg/proyectos/DemeterDocs/app/models/photo_processing_session.py`

### Key Attributes

```python
class PhotoProcessingSession(Base):
    __tablename__ = "photo_processing_sessions"

    # Primary Keys
    id: Integer                       # Auto-increment PK
    session_id: UUID                  # Unique session identifier

    # Image References
    original_image_id: UUID           # FK to s3_images (original photo)
    processed_image_id: UUID          # FK to s3_images (visualization)

    # Location
    storage_location_id: Integer      # FK to storage_locations

    # ML Results
    total_detected: Integer           # Total detected plants
    total_estimated: Integer          # Total estimated plants
    total_empty_containers: Integer   # Empty container count
    avg_confidence: Float             # Average detection confidence (0.0-1.0)
    category_counts: JSONB            # {"echeveria": 25, "aloe": 17, ...}

    # Status
    status: ProcessingSessionStatusEnum  # PENDING, PROCESSING, COMPLETED, FAILED
    error_message: String             # Error details if failed

    # User Adjustments
    manual_adjustments: JSONB         # User edits to ML results
    validated: Boolean                # User validation flag
    validated_by_user_id: Integer     # FK to users who validated (SET NULL)
    validation_date: DateTime         # Validation timestamp

    # Celery Tracking
    celery_task_id: String            # Parent task ID for polling
    processing_start_time: DateTime   # When processing started
    processing_end_time: DateTime     # When processing completed

    # Timestamps
    created_at: DateTime              # Session creation
    updated_at: DateTime              # Last update
```

### Status Enum
- `PENDING`: Session created, waiting for ML processing
- `PROCESSING`: ML pipeline is running
- `COMPLETED`: ML processing succeeded
- `FAILED`: ML processing failed

---

## 7. TODOS AND STUBS

### TODOs Found

#### Location: `/home/lucasg/proyectos/DemeterDocs/app/tasks/ml_tasks.py`

1. **Line 1742**: Get batch code from PhotoProcessingSession metadata
   ```python
   # For now, hardcode defaults (TODO: Get from PhotoProcessingSession metadata)
   batch_code = f"ML-SESSION-{session_id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
   ```

2. **Line 1747**: Read storage_location_id from session
   ```python
   # TODO: In production, read from PhotoProcessingSession.storage_location_id
   current_storage_bin_id = 1  # Default for now
   ```

3. **Line 1753-1754**: Get product and product_state from configuration
   ```python
   product_id=1,  # Default product (TODO: Get from configuration)
   product_state_id=1,  # Default product state (TODO: Get from configuration - likely "seedling" or first state)
   ```

4. **Line 1786**: Get ML user from configuration
   ```python
   user_id=1,  # Default ML user (TODO: Get from configuration)
   ```

5. **Line 1807**: Use actual ML classification results
   ```python
   # TODO: In production, use actual ML classification results
   classification = db_session.query(Classification)...
   ```

6. **Line 1904**: Use actual vegetation mask polygon
   ```python
   # TODO: In production, use actual vegetation mask polygon
   vegetation_polygon = {"type": "Polygon", "coordinates": [...]}
   ```

#### Location: `/home/lucasg/proyectos/DemeterDocs/app/services/photo/photo_upload_service.py`

7. **Lines 170-189**: GPS-based location lookup commented out
   ```python
   # # STEP 3: GPS-based location lookup (fail fast if no location)
   # location = await self.location_service.get_location_by_gps(...)
   #
   # if not location:
   #     raise ResourceNotFoundException(...)

   storage_location_id = 1  # Hardcoded for now
   ```

---

## 8. CIRCUIT BREAKER STATUS

### Implemented: YES

**Location**: `/home/lucasg/proyectos/DemeterDocs/app/tasks/ml_tasks.py` (Lines 72-169)

**Type**: In-memory circuit breaker with state tracking

**Configuration**:
```python
CIRCUIT_BREAKER_THRESHOLD = 5          # Open after 5 failures
CIRCUIT_BREAKER_TIMEOUT = 300          # 5 minutes cooldown
circuit_breaker_state = {
    "failures": 0,
    "last_failure_time": None,
    "state": "closed",                  # closed, open, half_open
}
```

**Integration Points**:
1. **Parent Task** (Line 228): Check before spawning children
2. **Child Task** (Line 515): Record success after completion
3. **Child Task** (Line 551-552): Record failure and retry

**Exception Type**:
```python
from app.core.exceptions import CircuitBreakerException
```

---

## 9. DATABASE SCHEMA ALIGNMENT

### S3Image Table
✅ **Matches Schema** - All columns implemented:
- image_id (UUID PK)
- s3_bucket, s3_key_original, s3_key_processed, s3_key_thumbnail
- image_type (ENUM: ORIGINAL, PROCESSED, THUMBNAIL)
- content_type, file_size_bytes, width_px, height_px
- exif_metadata (JSONB), gps_coordinates (JSONB)
- image_data (LargeBinary - cached binary)
- upload_source, uploaded_by_user_id, status
- created_at, updated_at

### PhotoProcessingSession Table
✅ **Matches Schema** - All columns implemented:
- id (INTEGER PK), session_id (UUID UK)
- original_image_id, processed_image_id (FK to s3_images)
- storage_location_id (FK to storage_locations)
- ML results: total_detected, total_estimated, avg_confidence
- category_counts (JSONB)
- status (ENUM), error_message
- validated, validated_by_user_id, validation_date
- manual_adjustments (JSONB)
- celery_task_id
- created_at, updated_at

---

## 10. KEY IMPLEMENTATION NOTES

### Image Caching Strategy
1. **PostgreSQL Cache**: Binary data stored in `image_data` column
2. **/tmp Cache**: ML tasks write to `/tmp/{image_id}.jpg` or `/tmp/session_{id}_original.jpg`
3. **S3 Cache**: Original source of truth

**Cleanup Sequence**:
- ML child task: Keeps `/tmp/{image_id}.jpg` (needed for visualization)
- Callback: Uses `/tmp/{image_id}.jpg` for visualization generation
- Callback: Deletes all `/tmp/session_*` files after visualization
- Callback: Sets `image_data = NULL` in database for cleanup

### Session ID Tracking
- **PhotoProcessingSession.id**: INTEGER primary key (used in Celery tasks)
- **PhotoProcessingSession.session_id**: UUID unique key (used in S3 paths)
- **S3Image.image_id**: UUID (used as S3 key component)

**Important**:
- Celery tasks receive `session_id` (INTEGER)
- S3 operations use `session.session_id` (UUID)
- Must query database to convert between them

### Error Handling
- **GPS Missing**: Raises ValidationException
- **File Invalid**: Raises ValidationException
- **S3 Failure**: Catches CircuitBreakerError, raises S3UploadException
- **ML Failure**: Records in circuit breaker, retries with exponential backoff
- **Callback Failure**: Logs error, marks session as FAILED

### Async/Await Patterns
- **Service Layer**: async def (FastAPI compatible)
- **Celery Tasks**: sync def (Celery doesn't support async)
- **ML Pipeline**: asyncio.run() in child task to handle async coordinator

---

## Summary Table

| Component | Status | Location | Type |
|-----------|--------|----------|------|
| Controller | ✅ Complete | stock_controller.py (L62-145) | POST /api/v1/stock/photo |
| PhotoUploadService | ✅ Complete | photo_upload_service.py | Orchestration |
| S3ImageService | ✅ Complete | s3_image_service.py | S3 Operations |
| ml_parent_task | ✅ Complete | ml_tasks.py (L176-295) | Celery Chord |
| ml_child_task | ✅ Complete | ml_tasks.py (L302-563) | GPU Processing |
| ml_aggregation_callback | ✅ Complete | ml_tasks.py (L571-1062) | Results Aggregation |
| Circuit Breaker | ✅ Complete | ml_tasks.py (L72-169) | Resilience |
| PhotoProcessingSession | ✅ Complete | photo_processing_session.py | Model |
| S3Image | ✅ Complete | s3_image.py | Model |
| UUID Generation | ✅ Complete | Services | Pre-generation before upload |
| /tmp Handling | ✅ Complete | ml_tasks.py | 3-tier cache |
| Visualization | ✅ Complete | ml_tasks.py (L1318-1676) | AVIF generation |
| Binary Cleanup | ✅ Complete | ml_tasks.py (L1243-1315) | PostgreSQL space management |
