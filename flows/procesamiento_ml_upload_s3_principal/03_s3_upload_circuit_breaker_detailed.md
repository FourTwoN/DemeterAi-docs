# S3 Upload with Circuit Breaker - Detailed

## Purpose

This diagram shows the ultra-detailed implementation of the Celery S3 upload task with **circuit breaker pattern** to prevent API exhaustion during AWS outages, including EXIF extraction, thumbnail generation, and AVIF compression.

## Scope

- **Level**: Ultra-detail (implementation code with AWS SDK calls)
- **Audience**: Developers implementing reliability patterns, debugging S3 issues
- **Detail**: Circuit breaker state machine, retry logic, AWS boto3 calls, error handling
- **Mermaid Version**: v11.3.0+

## What It Represents

Complete S3 upload task including:

1. **Circuit Breaker Check**: Prevent task execution if S3 is failing
2. **Database Query**: Fetch s3_images record by UUID
3. **Temp File Read**: Load image from `/tmp/uploads/`
4. **EXIF Extraction**: GPS coordinates, camera model, timestamp, dimensions
5. **S3 Upload**: Original image with server-side encryption (AES256)
6. **Thumbnail Generation**: 400x400 max, LANCZOS resampling
7. **AVIF Compression**: 50% size reduction vs JPEG (quality=85)
8. **Fallback to WebP**: If AVIF encoding fails
9. **Database UPDATE**: Mark as 'ready', store thumbnail key
10. **Circuit Breaker Management**: Record success/failure, state transitions

## Circuit Breaker Pattern

### Why Circuit Breaker?

**Problem**: During AWS S3 outages, thousands of tasks retry S3 API calls, making the problem worse.

**Solution**: Circuit breaker stops all S3 calls after threshold failures, gives AWS time to recover.

### State Machine

```
CLOSED (Normal)
   ↓ (50% failures)
OPEN (Reject all)
   ↓ (60s timeout)
HALF_OPEN (Test)
   ↓ (success)
CLOSED (Recovered)
```

### States

**🟢 CLOSED** (Normal operation):
- All requests go through
- Record successes and failures
- If failure rate ≥ 50% → OPEN

**🔴 OPEN** (Circuit tripped):
- Reject ALL requests immediately
- Raise `CircuitBreakerOpenError`
- Schedule retry after 60s
- After timeout → HALF_OPEN

**🟡 HALF_OPEN** (Testing):
- Allow test requests through
- If success → CLOSED
- If failure → OPEN

### Configuration

```python
CircuitBreaker(
  failure_threshold=10,      # Min failures to trigger
  recovery_timeout=60,       # Seconds before test
  expected_exception=S3Error # What counts as failure
)
```

## EXIF Extraction

Uses **Pillow (PIL)** to extract metadata:

```python
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS

with Image.open(file_path) as img:
  exif_data = img.getexif()

  # GPS coordinates
  gps_info = exif_data.get_ifd(34853)  # GPSInfo tag
  lat = convert_gps_to_decimal(
    gps_info['GPSLatitude'],
    gps_info['GPSLatitudeRef']
  )
  lon = convert_gps_to_decimal(
    gps_info['GPSLongitude'],
    gps_info['GPSLongitudeRef']
  )

  # Other metadata
  camera_model = exif_data.get(272)  # Model tag
  timestamp = exif_data.get(306)     # DateTime tag
```

### GPS Conversion

```python
def convert_gps_to_decimal(coord, ref):
  degrees, minutes, seconds = coord
  decimal = degrees + minutes/60 + seconds/3600
  if ref in ['S', 'W']:
    decimal = -decimal
  return decimal
```

## Thumbnail Generation

### Size Strategy

**Target**: 400x400 max, preserving aspect ratio

**Example**:
- Original: 3000x2000 → Thumbnail: 400x267
- Original: 1000x2000 → Thumbnail: 200x400

### Resampling Algorithm

**LANCZOS**: High-quality downsampling filter

```python
img.thumbnail(
  (400, 400),
  Image.Resampling.LANCZOS  # Best quality
)
```

## AVIF Compression

### Why AVIF?

- **50% smaller** than JPEG at same quality
- Better compression algorithm (AV1-based)
- Supported in modern browsers

### Implementation

```python
import pillow_avif  # pip install pillow-avif

img.save(
  'thumb.avif',
  'AVIF',
  quality=85,  # 0-100 (85 = good balance)
  speed=4      # 0-10 (4 = balanced speed/quality)
)
```

### Fallback Chain

1. Try **AVIF** (pillow-avif plugin)
2. If fails → Try **WebP** (built-in)
3. If fails → Keep **JPEG** (original)

## Retry Logic

### Exponential Backoff with Jitter

**AWS Recommended Pattern**:

```python
import random

retry_num = self.request.retries
base_delay = 60
max_delay = 600  # 10 min cap

delay = random.uniform(
  0,
  min(max_delay, base_delay * (2 ** retry_num))
)

self.retry(countdown=int(delay))
```

**Why Jitter?**
- Prevents "thundering herd" problem
- Spreads out retry attempts
- Reduces load spikes on recovery

**Example delays**:
- Retry 0: 0-60s (random)
- Retry 1: 0-120s (random)
- Retry 2: 0-240s (random)
- Retry 3: 0-480s (random)

## Performance

| Step | Duration | Notes |
|------|----------|-------|
| Circuit check | ~1ms | In-memory state |
| DB query | ~5-10ms | UUID PK lookup (fast) |
| Read temp file | ~10ms | Disk I/O |
| EXIF extraction | ~20-30ms | PIL parsing |
| S3 upload original | ~200-500ms | Network I/O (varies) |
| Thumbnail generation | ~50ms | CPU (Pillow) |
| AVIF compression | ~100ms | CPU-intensive |
| S3 upload thumbnail | ~100ms | Small file |
| DB UPDATE | ~30ms | PostgreSQL |
| **Total per image** | **~500-900ms** | Varies by network |
| **Total per chunk (20)** | **~10-18s** | Parallel processing possible |

## Error Handling

### Graceful Degradation

**Missing GPS**: Warning, not error
- Continue with upload
- Mark as 'ready'
- Set `error_details` for manual fix

**AVIF Fails**: Fallback to WebP
- Log warning
- Use WebP compression instead
- Still ~30% smaller than JPEG

**S3 Fails**: Retry with backoff
- Move file to `/tmp/failed_uploads/`
- Preserve for manual retry
- Exponential backoff

**Circuit Opens**: Reject immediately
- Don't waste time on doomed requests
- Schedule retry after recovery timeout
- Alert ops team

## Related Diagrams

- **Master Overview**: `flows/00_master_overview.mmd` (high-level)
- **Complete Pipeline v4**: `flows/01_complete_pipeline_v4.mmd` (full context)
- **API Entry**: `flows/02_api_entry_detailed.mmd` (previous step)
- **ML Parent**: `flows/04_ml_parent_segmentation_detailed.mmd` (parallel task)

## How It Fits in the System

This task runs **in parallel** with ML processing:
- Triggered by API after photo upload
- Runs on **gevent pool** (I/O workers, not GPU)
- Processes chunks of 20 images
- Stores originals + thumbnails in S3
- Updates database status to 'ready'
- ML tasks can proceed once status = 'ready'

## AWS S3 Best Practices Used

✅ **Server-Side Encryption**: AES256 (GDPR compliance)
✅ **No Built-In Retries**: Circuit breaker handles it
✅ **Exponential Backoff**: AWS recommended algorithm
✅ **Full Jitter**: Prevents thundering herd
✅ **Circuit Breaker**: Protects AWS API during outages
✅ **Metadata Tags**: Track image_id, user_id

---

**Version**: 1.0
**Last Updated**: 2025-10-07
**Complexity**: High (circuit breaker state machine)
**Author**: DemeterAI Engineering Team
