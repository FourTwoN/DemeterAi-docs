# S015: S3ImageService

## Metadata

- **Epic**: [epic-004-services.md](../../02_epics/epic-004-services.md)
- **Sprint**: Sprint-04
- **Status**: `backlog`
- **Priority**: `high`
- **Complexity**: M (3 story points)
- **Area**: `services/photo`
- **Assignee**: TBD
- **Dependencies**:
    - Blocks: [S013, ML001, C014]
    - Blocked by: [F008-s3-connection]

## Description

**What**: S3 operations service (upload original, upload visualizations, download, generate
presigned URLs, lifecycle management).

**Why**: Centralizes S3 interactions. Implements circuit breaker pattern for resilience.

**Context**: Application Layer. Wraps boto3 S3 client with error handling and circuit breaker.

## Acceptance Criteria

- [ ] **AC1**: Upload original photo to S3 (bucket: demeter-photos-original)
- [ ] **AC2**: Upload visualization images (bucket: demeter-photos-viz)
- [ ] **AC3**: Generate presigned URLs (24-hour expiry)
- [ ] **AC4**: Download image from S3
- [ ] **AC5**: Circuit breaker for S3 failures (pybreaker, fail_max=5, timeout=60s)
- [ ] **AC6**: Unit tests ≥85% coverage

## Technical Notes

- Circuit breaker prevents cascading S3 failures
- Presigned URLs for secure browser access
- S3 key format: `{session_id}/{filename}`

## Time Tracking

- **Estimated**: 3 story points (~6 hours)

---
**Card Created**: 2025-10-09
**Last Updated**: 2025-10-09

---

## Python Expert Implementation (2025-10-21)

**Status**: ✅ IMPLEMENTATION COMPLETE - READY FOR REVIEW

### Files Created

1. **`app/services/photo/s3_image_service.py`** (675 lines)
    - S3ImageService with all required methods
    - Circuit breaker pattern (pybreaker: fail_max=5, reset_timeout=60s)
    - Async operations using boto3 + asyncio.to_thread()

2. **`app/schemas/s3_image_schema.py`** (145 lines)
    - S3ImageUploadRequest (request schema)
    - S3ImageResponse (response schema)
    - PresignedUrlRequest (request schema)
    - PresignedUrlResponse (response schema)

3. **`app/core/config.py`** (updated)
    - Added S3 configuration settings:
        - AWS_REGION
        - AWS_ACCESS_KEY_ID
        - AWS_SECRET_ACCESS_KEY
        - S3_BUCKET_ORIGINAL
        - S3_BUCKET_VISUALIZATION
        - S3_PRESIGNED_URL_EXPIRY_HOURS

4. **`app/services/photo/__init__.py`** (created directory structure)

### Methods Implemented

**Public Methods (5)**:

1. ✅ `upload_original(file_bytes, session_id, upload_request)` → S3ImageResponse
    - Upload to demeter-photos-original bucket
    - S3 key format: {session_id}/{filename}
    - File size validation (1 byte - 500MB)
    - Returns S3ImageResponse with presigned URL

2. ✅ `upload_visualization(file_bytes, session_id, filename)` → S3ImageResponse
    - Upload to demeter-photos-viz bucket
    - S3 key format: {session_id}/viz_{filename}
    - For ML pipeline outputs (annotated images, heatmaps, etc.)

3. ✅ `download_original(s3_key, bucket)` → bytes
    - Download image from S3
    - Returns file bytes

4. ✅ `generate_presigned_url(s3_key, bucket, expiry_hours)` → str
    - Generate presigned URL for browser access
    - Default 24-hour expiry (max 7 days)
    - Validation: 1-168 hours

5. ✅ `delete_image(image_id)` → bool
    - Delete from S3 (original + thumbnail)
    - Delete from database
    - Returns True if deleted, False if not found

**Private Methods (3)**:

- ✅ `_upload_to_s3()` - S3 upload with circuit breaker
- ✅ `_download_from_s3()` - S3 download with circuit breaker
- ✅ `_delete_from_s3()` - S3 delete with circuit breaker

### Pattern Compliance Checklist

- [✅] **Service→Service pattern**: Only accesses own repository (S3ImageRepository)
- [✅] **Type hints**: All 10 methods have explicit return type annotations
- [✅] **Async/await**: All I/O operations use async (boto3 + asyncio.to_thread)
- [✅] **Business exceptions**: Uses S3UploadException, ValidationException
- [✅] **Pydantic schemas**: Returns S3ImageResponse (not SQLAlchemy model)
- [✅] **Docstrings**: Google-style docstrings on all public methods
- [✅] **Circuit breaker**: pybreaker with fail_max=5, reset_timeout=60s
- [✅] **No hallucinations**: All imports verified working

### Import Verification

```bash
$ python -c "from app.services.photo.s3_image_service import S3ImageService; print('✅')"
✅ S3ImageService import successful

$ python -c "from app.schemas.s3_image_schema import S3ImageUploadRequest, S3ImageResponse; print('✅')"
✅ All schemas import successfully
```

### Code Quality Metrics

- **Lines of code**: 675 (service) + 145 (schemas) = 820 total
- **Methods**: 10 total (5 public, 3 private, 1 property, 1 constructor)
- **Type hints**: 10/10 methods (100%)
- **Docstrings**: Present on all public methods
- **Async operations**: 8/8 I/O operations use async pattern

### Architecture Decisions

1. **boto3 vs aioboto3**: Used boto3 (sync) with `asyncio.to_thread()` instead of aioboto3
    - Reason: Project already has boto3 dependency, avoids adding aioboto3
    - Pattern: `await asyncio.to_thread(self.s3_client.put_object, ...)`

2. **Circuit breaker placement**: Applied to all S3 operations (upload, download, delete)
    - Prevents cascading failures when S3 is unavailable
    - After 5 failures, circuit opens for 60 seconds

3. **Presigned URL generation**: Not circuit-breaker protected
    - Reason: Presigned URL generation is local operation (no network call)
    - Only wrapped in try/except for error handling

4. **S3 key format**:
    - Original: `{session_id}/{filename}`
    - Visualization: `{session_id}/viz_{filename}`
    - Enables session-based organization in S3

### Testing Notes (for Testing Expert)

**Unit tests should mock**:

- `S3ImageRepository` (database)
- `boto3.client` (S3 operations)

**Integration tests should test**:

- Real database (PostgreSQL)
- Mock S3 using moto or localstack

**Test coverage should include**:

- Upload success/failure paths
- Circuit breaker behavior (5 failures → open circuit)
- Presigned URL generation
- Delete cascade (S3 → database)
- File size validation (500MB limit)
- Expiry validation (1-168 hours)

### Acceptance Criteria Status

- [✅] **AC1**: Upload original photo to S3 (bucket: demeter-photos-original)
- [✅] **AC2**: Upload visualization images (bucket: demeter-photos-viz)
- [✅] **AC3**: Generate presigned URLs (24-hour expiry)
- [✅] **AC4**: Download image from S3
- [✅] **AC5**: Circuit breaker for S3 failures (pybreaker, fail_max=5, timeout=60s)
- [ ] **AC6**: Unit tests ≥85% coverage (pending Testing Expert)

### Next Steps

1. **Team Leader Review**: Code review for architecture compliance
2. **Testing Expert**: Write unit + integration tests (target ≥85% coverage)
3. **Integration**: Wire into FastAPI controllers (Sprint 04)

### Known Limitations

1. **AWS credentials**: Currently loaded from environment variables
    - Production: Should use IAM roles or AWS Secrets Manager

2. **S3 client lifecycle**: Singleton pattern (created once, reused)
    - If credentials rotate, service restart required

3. **Large file uploads**: No multipart upload support yet
    - Current limit: 500MB (single PUT operation)
    - Future: Add multipart for files >100MB

---

**Implementation Date**: 2025-10-21
**Implementer**: Python Expert (Claude Code)
**Review Status**: Pending Team Leader review
**Testing Status**: Pending Testing Expert
