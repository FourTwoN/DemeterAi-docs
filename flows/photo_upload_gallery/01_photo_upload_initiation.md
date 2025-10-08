# Diagram 01: Photo Upload Initiation

**Version:** 1.0.0
**Date:** 2025-10-08
**Parent Diagram:** 00_comprehensive_view.mmd
**Related Diagrams:** 02_job_monitoring_progress.mmd

## Purpose

This diagram documents the **photo upload initiation flow** from the moment a user selects photos to the creation of asynchronous Celery jobs. This is the entry point for the entire photo processing pipeline.

## Scope

**Input:**
- Multiple image files (1-100 photos)
- User authentication token
- Optional metadata (warehouse_id, notes)

**Output:**
- Files saved to temporary storage (/tmp/uploads/)
- S3 originals uploaded
- UUIDs generated for each photo
- Celery jobs created and queued
- 202 Accepted response with job IDs

**Performance Target:**
- File upload: 10-30s for 100 photos (network-dependent)
- Backend processing: < 500ms after upload completes
- Total response time: < 1 second (excluding file transfer)

## Upload Strategy

### Why Multipart/Form-Data?

**Problem:** Need to upload multiple large binary files (5-20MB each) efficiently.

**Solution:** Multipart/form-data with streaming upload

**Alternatives considered:**
1. **Base64 encoded JSON** - 33% larger payload, slow encoding/decoding ❌
2. **Multiple single-file requests** - Too many HTTP handshakes, slow ❌
3. **Multipart/form-data** - Native browser support, efficient, chosen ✓

### Upload Configuration

**Frontend (JavaScript/TypeScript):**
```javascript
const uploadConfig = {
    maxFiles: 100,              // Limit batch size
    maxFileSize: 20 * 1024 * 1024,  // 20MB per file
    acceptedTypes: ['image/jpeg', 'image/png'],
    parallelUploads: 6,         // Browser connection limit
    chunkSize: null,            // No chunking for now (future: 5MB chunks)
    timeout: 120000             // 2 minutes timeout
}
```

**Backend (FastAPI):**
```python
@router.post('/photos/upload')
async def upload_photos(
    files: List[UploadFile] = File(...),
    warehouse_id: Optional[int] = Form(None),
    notes: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user)
):
    # Limit batch size
    if len(files) > 100:
        raise HTTPException(400, 'Maximum 100 files per upload')

    # Validate file types
    for file in files:
        if file.content_type not in ['image/jpeg', 'image/png']:
            raise HTTPException(400, f'Invalid file type: {file.content_type}')
```

## Key Components

### 1. Client-Side File Selection (lines 84-120)

**HTML5 File Input:**
```html
<input
    type="file"
    id="photo-upload"
    name="files"
    accept="image/jpeg,image/png"
    multiple
    max="100"
/>
```

**Or drag-and-drop:**
```javascript
function handleDrop(event) {
    event.preventDefault()
    const files = Array.from(event.dataTransfer.files)

    // Validate files
    const validFiles = files.filter(file => {
        if (!file.type.match(/image\/(jpeg|png)/)) {
            showError(`Invalid file type: ${file.name}`)
            return false
        }
        if (file.size > 20 * 1024 * 1024) {
            showError(`File too large: ${file.name} (${formatBytes(file.size)})`)
            return false
        }
        return true
    })

    if (validFiles.length > 100) {
        showError(`Too many files. Maximum 100, got ${validFiles.length}`)
        return
    }

    uploadFiles(validFiles)
}
```

### 2. Client-Side Validation (lines 140-180)

**Validation checks:**
1. **File count**: 1-100 files
2. **File type**: JPEG or PNG only
3. **File size**: < 20MB per file
4. **Total size**: < 500MB total (optional)

**Why validate on client?**
- **Instant feedback**: No need to wait for server response
- **Reduce server load**: Invalid requests never sent
- **Better UX**: User sees errors before upload starts

**Example validation:**
```javascript
function validateFiles(files) {
    const errors = []

    if (files.length === 0) {
        errors.push('Please select at least one photo')
    }

    if (files.length > 100) {
        errors.push(`Maximum 100 photos. You selected ${files.length}`)
    }

    let totalSize = 0
    for (const file of files) {
        if (!['image/jpeg', 'image/png'].includes(file.type)) {
            errors.push(`Invalid file type: ${file.name}`)
        }

        if (file.size > 20 * 1024 * 1024) {
            errors.push(`File too large: ${file.name} (${formatBytes(file.size)})`)
        }

        totalSize += file.size
    }

    if (totalSize > 500 * 1024 * 1024) {
        errors.push(`Total size too large: ${formatBytes(totalSize)} (max 500MB)`)
    }

    return { valid: errors.length === 0, errors }
}
```

### 3. Multipart Upload Request (lines 220-280)

**JavaScript fetch API:**
```javascript
async function uploadFiles(files, options = {}) {
    // Create FormData
    const formData = new FormData()

    // Add files
    for (const file of files) {
        formData.append('files', file, file.name)
    }

    // Add optional metadata
    if (options.warehouse_id) {
        formData.append('warehouse_id', options.warehouse_id)
    }
    if (options.notes) {
        formData.append('notes', options.notes)
    }

    // Show progress bar
    const progressBar = createProgressBar()

    try {
        const response = await fetch('/api/v1/photos/upload', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${getToken()}`
            },
            body: formData,

            // Track upload progress (if supported by browser)
            onUploadProgress: (progressEvent) => {
                const percentComplete = Math.round(
                    (progressEvent.loaded * 100) / progressEvent.total
                )
                updateProgressBar(progressBar, percentComplete)
            }
        })

        if (!response.ok) {
            const error = await response.json()
            throw new Error(error.detail)
        }

        const result = await response.json()
        return result

    } catch (error) {
        showError(`Upload failed: ${error.message}`)
        throw error
    } finally {
        hideProgressBar(progressBar)
    }
}
```

**Raw HTTP request:**
```http
POST /api/v1/photos/upload HTTP/1.1
Host: api.demeterai.com
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: multipart/form-data; boundary=----WebKitFormBoundary7MA4YWxkTrZu0gW
Content-Length: 52428800

------WebKitFormBoundary7MA4YWxkTrZu0gW
Content-Disposition: form-data; name="files"; filename="photo1.jpg"
Content-Type: image/jpeg

<binary data for photo1.jpg>
------WebKitFormBoundary7MA4YWxkTrZu0gW
Content-Disposition: form-data; name="files"; filename="photo2.jpg"
Content-Type: image/jpeg

<binary data for photo2.jpg>
------WebKitFormBoundary7MA4YWxkTrZu0gW
Content-Disposition: form-data; name="warehouse_id"

3
------WebKitFormBoundary7MA4YWxkTrZu0gW
Content-Disposition: form-data; name="notes"

Weekly inventory check - Greenhouse A
------WebKitFormBoundary7MA4YWxkTrZu0gW--
```

### 4. Backend: Save to Temporary Storage (lines 320-380)

**FastAPI endpoint handler:**
```python
import uuid
import shutil
from pathlib import Path
from typing import List
from fastapi import UploadFile, File, Form, Depends, HTTPException
from datetime import datetime

@router.post('/photos/upload')
async def upload_photos(
    files: List[UploadFile] = File(...),
    warehouse_id: Optional[int] = Form(None),
    notes: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload photos and initiate processing jobs

    Performance target: < 500ms (excluding file transfer)
    """

    # Generate unique upload session ID
    upload_session_id = str(uuid.uuid4())

    # Create temp directory for this upload session
    temp_dir = Path(f'/tmp/uploads/{upload_session_id}')
    temp_dir.mkdir(parents=True, exist_ok=True)

    uploaded_files = []

    try:
        for file in files:
            # Generate unique image ID
            image_id = str(uuid.uuid4())

            # Determine file extension
            ext = file.filename.split('.')[-1].lower()
            if ext not in ['jpg', 'jpeg', 'png']:
                raise HTTPException(400, f'Invalid file type: {file.filename}')

            # Save to temp directory
            temp_path = temp_dir / f'{image_id}.{ext}'

            with temp_path.open('wb') as buffer:
                shutil.copyfileobj(file.file, buffer)

            uploaded_files.append({
                'image_id': image_id,
                'filename': file.filename,
                'temp_path': str(temp_path),
                'content_type': file.content_type,
                'size': temp_path.stat().st_size
            })

        # Files saved, now process asynchronously
        # (next steps: EXIF extraction, S3 upload, job creation)

    except Exception as e:
        # Cleanup temp files on error
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise HTTPException(500, f'Upload failed: {str(e)}')
```

**Temp directory structure:**
```
/tmp/uploads/
└── {upload_session_id}/
    ├── {image_id_1}.jpg
    ├── {image_id_2}.jpg
    └── {image_id_3}.png
```

**Cleanup policy:**
- Files deleted after 24 hours (cron job)
- Files deleted immediately after successful S3 upload
- Files deleted on server restart (in /tmp/)

### 5. EXIF Metadata Extraction (lines 420-500)

**Why extract EXIF?**
- **GPS coordinates**: Match photos to storage locations
- **Timestamp**: Photo capture time (may differ from upload time)
- **Camera info**: Useful for debugging image quality issues
- **Orientation**: Correct image rotation

**Python implementation:**
```python
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from typing import Optional, Dict, Any
from datetime import datetime

def extract_exif_metadata(image_path: str) -> Dict[str, Any]:
    """
    Extract EXIF metadata from image file

    Returns:
        {
            "camera_make": "Apple",
            "camera_model": "iPhone 13 Pro",
            "datetime_original": "2025-10-08T10:30:15Z",
            "gps_latitude": -34.603722,
            "gps_longitude": -58.381592,
            "gps_altitude": 25.0,
            "orientation": 1,
            "width": 4032,
            "height": 3024
        }
    """

    try:
        image = Image.open(image_path)
        exif_data = image._getexif()

        if not exif_data:
            return {}

        metadata = {}

        # Extract basic EXIF tags
        for tag_id, value in exif_data.items():
            tag_name = TAGS.get(tag_id, tag_id)

            if tag_name == 'Make':
                metadata['camera_make'] = str(value).strip()
            elif tag_name == 'Model':
                metadata['camera_model'] = str(value).strip()
            elif tag_name == 'DateTimeOriginal':
                metadata['datetime_original'] = parse_exif_datetime(value)
            elif tag_name == 'Orientation':
                metadata['orientation'] = int(value)
            elif tag_name == 'GPSInfo':
                gps_data = extract_gps_data(value)
                metadata.update(gps_data)

        # Extract image dimensions
        metadata['width'] = image.width
        metadata['height'] = image.height

        return metadata

    except Exception as e:
        logger.warning(f'Failed to extract EXIF from {image_path}: {e}')
        return {}


def extract_gps_data(gps_info: Dict) -> Dict[str, float]:
    """
    Extract GPS coordinates from EXIF GPSInfo

    Returns:
        {
            "gps_latitude": -34.603722,
            "gps_longitude": -58.381592,
            "gps_altitude": 25.0
        }
    """

    def convert_to_degrees(value):
        """Convert GPS coordinates to degrees in float format"""
        d, m, s = value
        return float(d) + (float(m) / 60.0) + (float(s) / 3600.0)

    gps_data = {}

    try:
        # Latitude
        lat = gps_info.get(2)  # GPSLatitude
        lat_ref = gps_info.get(1)  # GPSLatitudeRef (N or S)
        if lat and lat_ref:
            latitude = convert_to_degrees(lat)
            if lat_ref == 'S':
                latitude = -latitude
            gps_data['gps_latitude'] = latitude

        # Longitude
        lon = gps_info.get(4)  # GPSLongitude
        lon_ref = gps_info.get(3)  # GPSLongitudeRef (E or W)
        if lon and lon_ref:
            longitude = convert_to_degrees(lon)
            if lon_ref == 'W':
                longitude = -longitude
            gps_data['gps_longitude'] = longitude

        # Altitude
        alt = gps_info.get(6)  # GPSAltitude
        if alt:
            gps_data['gps_altitude'] = float(alt)

    except Exception as e:
        logger.warning(f'Failed to extract GPS data: {e}')

    return gps_data
```

**Performance:** ~50-100ms per image

### 6. S3 Upload (lines 540-640)

**Upload strategy:**
- Use boto3 with async wrapper (aioboto3)
- Upload original full-resolution image
- Generate presigned URL for frontend access
- Store S3 key in database

**Implementation:**
```python
import aioboto3
from botocore.exceptions import ClientError
from datetime import datetime
from typing import Dict

async def upload_to_s3(
    local_path: str,
    image_id: str,
    content_type: str,
    metadata: Dict[str, Any]
) -> Dict[str, str]:
    """
    Upload image to S3

    Returns:
        {
            "s3_bucket": "demeter-photos",
            "s3_key_original": "originals/2025/10/08/uuid-1.jpg",
            "s3_url": "https://s3.amazonaws.com/demeter-photos/..."
        }
    """

    # Generate S3 key with date-based folder structure
    upload_date = datetime.utcnow()
    s3_key = f'originals/{upload_date.year}/{upload_date.month:02d}/{upload_date.day:02d}/{image_id}.jpg'

    session = aioboto3.Session()

    async with session.client('s3') as s3_client:
        try:
            # Upload file
            await s3_client.upload_file(
                Filename=local_path,
                Bucket='demeter-photos',
                Key=s3_key,
                ExtraArgs={
                    'ContentType': content_type,
                    'Metadata': {
                        'image_id': image_id,
                        'uploaded_by': str(metadata.get('user_id', '')),
                        'upload_timestamp': upload_date.isoformat(),
                        'original_filename': metadata.get('filename', '')
                    },
                    # Set cache control
                    'CacheControl': 'max-age=31536000',  # 1 year
                    # Enable server-side encryption
                    'ServerSideEncryption': 'AES256'
                }
            )

            logger.info(f'Uploaded {image_id} to S3: {s3_key}')

            return {
                's3_bucket': 'demeter-photos',
                's3_key_original': s3_key,
                's3_url': f'https://s3.amazonaws.com/demeter-photos/{s3_key}'
            }

        except ClientError as e:
            logger.error(f'S3 upload failed for {image_id}: {e}')
            raise HTTPException(500, f'S3 upload failed: {str(e)}')
```

**Performance:** 2-5 seconds per image (network-dependent)

**Parallelization:**
```python
# Upload all images in parallel (up to 10 concurrent uploads)
import asyncio
from itertools import islice

async def upload_batch_to_s3(files: List[Dict], max_concurrent: int = 10):
    """Upload multiple files to S3 in parallel"""

    tasks = []
    for file_data in files:
        task = upload_to_s3(
            local_path=file_data['temp_path'],
            image_id=file_data['image_id'],
            content_type=file_data['content_type'],
            metadata=file_data
        )
        tasks.append(task)

    # Execute in batches of max_concurrent
    results = []
    for i in range(0, len(tasks), max_concurrent):
        batch = tasks[i:i+max_concurrent]
        batch_results = await asyncio.gather(*batch, return_exceptions=True)
        results.extend(batch_results)

    return results
```

### 7. Thumbnail Generation (lines 680-740)

**Why generate thumbnails?**
- **Gallery performance**: 300x300px loads 100x faster than 4000x3000px
- **Bandwidth savings**: Thumbnail ~30KB vs original ~5MB (167x smaller)
- **User experience**: Instant gallery loading

**Implementation:**
```python
from PIL import Image
from io import BytesIO

async def generate_and_upload_thumbnail(
    s3_key_original: str,
    image_id: str,
    size: tuple = (300, 300)
) -> str:
    """
    Download original from S3, generate thumbnail, upload back to S3

    Returns:
        s3_key_thumbnail: "thumbnails/2025/10/08/uuid-1.jpg"
    """

    session = aioboto3.Session()

    async with session.client('s3') as s3_client:
        try:
            # Download original from S3
            response = await s3_client.get_object(
                Bucket='demeter-photos',
                Key=s3_key_original
            )

            image_data = await response['Body'].read()

            # Generate thumbnail
            image = Image.open(BytesIO(image_data))

            # Use thumbnail() for aspect ratio preservation
            image.thumbnail(size, Image.Resampling.LANCZOS)

            # Convert to RGB if necessary (remove alpha channel)
            if image.mode in ('RGBA', 'LA', 'P'):
                image = image.convert('RGB')

            # Save to bytes buffer
            buffer = BytesIO()
            image.save(buffer, format='JPEG', quality=80, optimize=True)
            buffer.seek(0)

            # Generate S3 key for thumbnail
            s3_key_thumbnail = s3_key_original.replace('originals/', 'thumbnails/')

            # Upload thumbnail to S3
            await s3_client.put_object(
                Bucket='demeter-photos',
                Key=s3_key_thumbnail,
                Body=buffer,
                ContentType='image/jpeg',
                CacheControl='max-age=31536000',
                ServerSideEncryption='AES256'
            )

            logger.info(f'Generated thumbnail for {image_id}: {s3_key_thumbnail}')

            return s3_key_thumbnail

        except Exception as e:
            logger.error(f'Thumbnail generation failed for {image_id}: {e}')
            # Non-critical error, return empty string
            return ''
```

**Performance:** 1-2 seconds per image

**Optimization:** Run thumbnail generation as separate Celery task (non-blocking)

### 8. Database Record Creation (lines 780-860)

**Insert into s3_images table:**
```python
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

async def create_image_record(
    db: AsyncSession,
    image_id: str,
    s3_data: Dict[str, str],
    exif_metadata: Dict[str, Any],
    user_id: int,
    original_filename: str
) -> int:
    """
    Create s3_images record

    Returns:
        Database record ID
    """

    from models import S3Image  # SQLAlchemy model

    image = S3Image(
        image_id=image_id,
        s3_bucket=s3_data['s3_bucket'],
        s3_key_original=s3_data['s3_key_original'],
        s3_key_thumbnail=s3_data.get('s3_key_thumbnail', ''),
        content_type='image/jpeg',
        file_size_bytes=s3_data.get('file_size_bytes', 0),
        width_px=exif_metadata.get('width', 0),
        height_px=exif_metadata.get('height', 0),
        exif_metadata=exif_metadata,
        gps_coordinates={
            'lat': exif_metadata.get('gps_latitude'),
            'lon': exif_metadata.get('gps_longitude'),
            'altitude': exif_metadata.get('gps_altitude')
        } if exif_metadata.get('gps_latitude') else None,
        upload_source='web',
        uploaded_by_user_id=user_id,
        status='uploaded',
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    db.add(image)
    await db.commit()
    await db.refresh(image)

    logger.info(f'Created s3_images record for {image_id} (ID: {image.id})')

    return image.id
```

### 9. Celery Job Creation (lines 900-980)

**Create processing job for each uploaded photo:**
```python
from celery_app import celery_app

async def create_processing_jobs(
    uploaded_files: List[Dict],
    upload_session_id: str,
    db: AsyncSession
) -> List[Dict]:
    """
    Create Celery jobs for ML processing

    Returns:
        List of job metadata
    """

    jobs = []

    for file_data in uploaded_files:
        # Dispatch Celery task
        task = celery_app.send_task(
            'process_uploaded_photo',
            kwargs={
                'image_id': file_data['image_id'],
                's3_key_original': file_data['s3_key_original'],
                'upload_session_id': upload_session_id,
                'db_record_id': file_data['db_record_id']
            },
            queue='ml_processing',
            priority=5  # Normal priority (0-9, higher = more important)
        )

        jobs.append({
            'job_id': task.id,
            'image_id': file_data['image_id'],
            'filename': file_data['filename'],
            'status': 'pending',
            'created_at': datetime.utcnow().isoformat()
        })

        logger.info(f'Created Celery job {task.id} for image {file_data["image_id"]}')

    # Store job metadata in Redis for polling
    import redis.asyncio as redis
    redis_client = await redis.from_url('redis://localhost:6379')

    await redis_client.setex(
        f'upload_session:{upload_session_id}',
        86400,  # 24 hours TTL
        json.dumps({
            'upload_session_id': upload_session_id,
            'total_jobs': len(jobs),
            'jobs': jobs,
            'created_at': datetime.utcnow().isoformat()
        })
    )

    return jobs
```

### 10. HTTP 202 Response (lines 1020-1080)

**Return response to frontend:**
```python
from fastapi import Response
from fastapi.responses import JSONResponse

# Complete endpoint implementation
@router.post('/photos/upload')
async def upload_photos(
    files: List[UploadFile] = File(...),
    warehouse_id: Optional[int] = Form(None),
    notes: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> JSONResponse:
    """Upload photos and create processing jobs"""

    upload_session_id = str(uuid.uuid4())

    # ... (steps 4-9: save temp, extract EXIF, upload S3, create DB records, create jobs)

    jobs = await create_processing_jobs(uploaded_files, upload_session_id, db)

    # Calculate estimated completion time
    avg_processing_time_minutes = 7  # 5-10 min avg
    estimated_completion_minutes = len(jobs) * avg_processing_time_minutes / 4  # 4 GPU workers

    response_data = {
        'status': 'accepted',
        'upload_session_id': upload_session_id,
        'jobs': jobs,
        'total_files': len(files),
        'estimated_completion_time_minutes': int(estimated_completion_minutes),
        'poll_url': f'/api/v1/photos/jobs/status?upload_session_id={upload_session_id}',
        'message': f'Upload successful. Processing {len(jobs)} photos...'
    }

    # Return 202 Accepted (not 200 OK)
    return JSONResponse(
        content=response_data,
        status_code=202,
        headers={
            'Location': f'/api/v1/photos/jobs/status?upload_session_id={upload_session_id}'
        }
    )
```

**Response example:**
```json
{
  "status": "accepted",
  "upload_session_id": "550e8400-e29b-41d4-a716-446655440000",
  "jobs": [
    {
      "job_id": "celery-task-uuid-1",
      "image_id": "image-uuid-1",
      "filename": "greenhouse_a_rack3.jpg",
      "status": "pending",
      "created_at": "2025-10-08T10:30:00Z"
    },
    {
      "job_id": "celery-task-uuid-2",
      "image_id": "image-uuid-2",
      "filename": "greenhouse_a_rack4.jpg",
      "status": "pending",
      "created_at": "2025-10-08T10:30:01Z"
    }
  ],
  "total_files": 2,
  "estimated_completion_time_minutes": 3,
  "poll_url": "/api/v1/photos/jobs/status?upload_session_id=550e8400-e29b-41d4-a716-446655440000",
  "message": "Upload successful. Processing 2 photos..."
}
```

## Performance Breakdown

**Complete upload flow timing (for 50 photos):**

| Phase | Time | Details |
|-------|------|---------|
| **File selection** | < 1s | User clicks upload button |
| **Client validation** | < 100ms | Check file types, sizes |
| **Upload to server** | 15-30s | Multipart upload, network-dependent |
| **Save to /tmp/** | 2-5s | Write files to disk (50 × 50ms) |
| **Extract EXIF** | 4-5s | Parallel extraction (50 × 80ms / 10 workers) |
| **Upload to S3** | 15-20s | Parallel upload (50 × 3s / 10 concurrent) |
| **Generate thumbnails** | 8-10s | Parallel generation (50 × 1.5s / 10 workers) |
| **Create DB records** | 1-2s | Bulk insert (50 records) |
| **Create Celery jobs** | 500ms | Dispatch 50 tasks |
| **Build response** | 50ms | JSON serialization |
| **Total backend** | ~30-45s | From upload complete to 202 response |

**User perceives:**
- Upload progress: 15-30s (visible progress bar)
- Backend processing: ~30s (spinner or progress message)
- **Total: ~45-60s** from click to "processing started" message

**Bottlenecks:**
1. **Network upload**: Largest factor (user's internet speed)
2. **S3 upload**: Second largest (AWS network speed)
3. **Thumbnail generation**: CPU-bound, parallelized

**Optimizations:**
- Thumbnail generation moved to separate Celery task (non-blocking)
- EXIF extraction parallelized (10 workers)
- S3 uploads parallelized (10 concurrent)
- Database inserts batched

## Error Handling

### 1. Invalid File Type

**Scenario:** User uploads non-image file

**Client-side:**
```javascript
if (!file.type.match(/image\/(jpeg|png)/)) {
    showError(`Invalid file type: ${file.name}`)
    return
}
```

**Server-side:**
```python
if file.content_type not in ['image/jpeg', 'image/png']:
    raise HTTPException(400, f'Invalid file type: {file.content_type}')
```

### 2. File Too Large

**Scenario:** User uploads file > 20MB

**Client-side:**
```javascript
if (file.size > 20 * 1024 * 1024) {
    showError(`File too large: ${file.name} (${formatBytes(file.size)})`)
    return
}
```

**Server-side:**
```python
# FastAPI automatic request body size limit
app.add_middleware(
    RequestBodySizeLimitMiddleware,
    max_body_size=100 * 1024 * 1024  # 100MB total
)
```

### 3. S3 Upload Failure

**Scenario:** Network error, AWS down, credentials invalid

**Retry logic:**
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
async def upload_to_s3_with_retry(local_path, image_id, content_type, metadata):
    """Upload with automatic retries"""
    return await upload_to_s3(local_path, image_id, content_type, metadata)
```

**Fallback:**
```python
try:
    s3_data = await upload_to_s3_with_retry(...)
except Exception as e:
    # Log error, but don't fail entire upload
    logger.error(f'S3 upload failed after retries: {e}')

    # Save file path in database, retry later via background job
    image.status = 'upload_pending'
    image.error_details = f'S3 upload failed: {str(e)}'
```

### 4. Database Connection Lost

**Scenario:** PostgreSQL connection pool exhausted

**Retry with exponential backoff:**
```python
from asyncio import sleep

async def create_image_record_with_retry(db, image_id, s3_data, exif_metadata, user_id, filename):
    """Create record with retry logic"""

    max_retries = 3
    for attempt in range(max_retries):
        try:
            return await create_image_record(db, image_id, s3_data, exif_metadata, user_id, filename)
        except Exception as e:
            if attempt == max_retries - 1:
                raise

            wait_time = 2 ** attempt  # 1s, 2s, 4s
            logger.warning(f'Database error, retrying in {wait_time}s: {e}')
            await sleep(wait_time)
```

### 5. Disk Space Full

**Scenario:** /tmp/ partition full

**Check before writing:**
```python
import shutil

def check_disk_space(path: str, required_bytes: int) -> bool:
    """Check if enough disk space available"""
    stat = shutil.disk_usage(path)
    return stat.free > required_bytes

# Before saving files
total_size = sum(file.size for file in files)
if not check_disk_space('/tmp/uploads', total_size * 2):  # 2x buffer
    raise HTTPException(507, 'Insufficient disk space')
```

## Related Diagrams

- **00_comprehensive_view.mmd:** Complete upload and gallery system
- **02_job_monitoring_progress.mmd:** Polling for job status after upload

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-10-08 | Initial photo upload initiation subflow |

---

**Notes:**
- Files saved to /tmp/ are temporary (deleted after S3 upload)
- S3 is source of truth (originals never deleted)
- Thumbnail generation can be moved to background task for faster response
- EXIF extraction is optional but highly recommended (enables GPS matching)
- Celery jobs run asynchronously (user doesn't wait for ML processing)
