# [C001] Photo Upload Endpoint - POST /api/stock/photo

## Metadata

- **Epic**: epic-003-backend-implementation.md
- **Sprint**: Sprint-02 (Week 5-6)
- **Status**: `backlog`
- **Priority**: `critical` (primary stock initialization method)
- **Complexity**: L (3 story points)
- **Area**: `backend/controllers`
- **Assignee**: TBD
- **Dependencies**:
    - Blocks: [SCH002, CEL005]
    - Blocked by: [SVC001-photo-service, SVC002-s3-service, DB007-stock-movements-model]

## Related Documentation

- **Engineering Plan**: ../../engineering_plan/api/README.md
- **Controller Layer**: ../../engineering_plan/03_architecture_overview.md
- **Flow Diagram**: ../../flows/procesamiento_ml_upload_s3_principal/README.md
- **FastAPI Docs**: https://fastapi.tiangolo.com/tutorial/request-files/

## Description

Create the **primary stock initialization endpoint** that accepts photo uploads and dispatches ML
processing pipeline via Celery.

**What**: FastAPI endpoint for multipart photo upload:

- Accepts JPEG/PNG/AVIF images up to 20MB
- Extracts EXIF metadata (GPS, timestamp, camera)
- Validates user authentication
- Dispatches async ML pipeline task
- Returns HTTP 202 (Accepted) with task_id for polling

**Why**:

- **Primary initialization**: Photo-based stock counting is the main workflow
- **Async processing**: ML inference takes 5-10 mins (CPU), needs background task
- **User experience**: Immediate response, poll for status later
- **Traceability**: task_id allows tracking pipeline progress

**Context**: This endpoint triggers the 8-step ML pipeline (localization → segmentation →
detection → estimation → aggregation → batch creation → visualization → finalization). It's the
entry point for 95%+ stock initializations.

## Acceptance Criteria

- [ ] **AC1**: FastAPI route defined in `app/controllers/stock_controller.py`:
  ```python
  from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
  from fastapi.responses import JSONResponse
  from app.services.photo_service import PhotoService
  from app.services.s3_service import S3Service
  from app.schemas.stock_schema import PhotoUploadRequest, PhotoUploadResponse
  from app.dependencies.auth import get_current_user
  from app.models.user import User
  import logging

  router = APIRouter(prefix="/api/stock", tags=["Stock Management"])
  logger = logging.getLogger(__name__)

  @router.post(
      "/photo",
      response_model=PhotoUploadResponse,
      status_code=status.HTTP_202_ACCEPTED,
      summary="Upload photo for ML-based stock initialization",
      description="""
      Upload a photo to initialize stock counts using ML pipeline.

      **Flow**:
      1. Upload photo (multipart/form-data)
      2. Extract EXIF metadata (GPS, timestamp)
      3. Upload to S3 (original bucket)
      4. Create photo_processing_session record
      5. Dispatch Celery task (ml_parent_task)
      6. Return task_id for polling

      **Processing time**: 5-10 minutes (CPU) or 1-3 minutes (GPU)

      **Poll status**: GET /api/stock/tasks/status?task_id={task_id}
      """,
      responses={
          202: {"description": "Photo accepted, processing started"},
          400: {"description": "Invalid file format or size"},
          401: {"description": "Authentication required"},
          413: {"description": "File too large (>20MB)"},
          500: {"description": "S3 upload failed"}
      }
  )
  async def upload_photo(
      file: UploadFile = File(..., description="Photo file (JPEG/PNG/AVIF, max 20MB)"),
      current_user: User = Depends(get_current_user),
      photo_service: PhotoService = Depends(),
      s3_service: S3Service = Depends()
  ) -> PhotoUploadResponse:
      """
      Upload photo for ML-based stock initialization.

      **HTTP Concerns Only** - Business logic in PhotoService.
      """
      # Validate file type
      allowed_types = ['image/jpeg', 'image/png', 'image/avif']
      if file.content_type not in allowed_types:
          raise HTTPException(
              status_code=status.HTTP_400_BAD_REQUEST,
              detail=f"Invalid file type. Allowed: {allowed_types}"
          )

      # Validate file size (max 20MB)
      MAX_SIZE = 20 * 1024 * 1024  # 20MB
      file.file.seek(0, 2)  # Seek to end
      file_size = file.file.tell()
      file.file.seek(0)  # Reset to start

      if file_size > MAX_SIZE:
          raise HTTPException(
              status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
              detail=f"File too large. Max size: 20MB"
          )

      logger.info(
          f"Photo upload started by user {current_user.id}: "
          f"{file.filename} ({file_size / 1024:.2f} KB)"
      )

      # Call service layer (business logic)
      try:
          result = await photo_service.create_photo_session(
              file=file,
              user_id=current_user.id
          )

          return PhotoUploadResponse(
              task_id=result.task_id,
              session_id=result.session_id,
              status="processing",
              message="Photo uploaded successfully. Check status with task_id.",
              poll_url=f"/api/stock/tasks/status?task_id={result.task_id}"
          )

      except Exception as e:
          logger.error(f"Photo upload failed: {str(e)}", exc_info=True)
          raise HTTPException(
              status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
              detail="Photo upload failed. Please try again."
          )
  ```

- [ ] **AC2**: File validation includes:
    - Content type check (JPEG/PNG/AVIF only)
    - Size limit (20MB max)
    - Filename sanitization (prevent path traversal)

- [ ] **AC3**: EXIF metadata extraction delegated to service layer

- [ ] **AC4**: Error handling for:
    - Invalid file type → HTTP 400
    - File too large → HTTP 413
    - S3 upload failure → HTTP 500 (with retry logic in service)
    - Missing authentication → HTTP 401

- [ ] **AC5**: OpenAPI documentation complete with:
    - Request example (multipart form)
    - Response schema
    - Error responses (400, 401, 413, 500)
    - Processing time estimates

- [ ] **AC6**: Logging includes:
    - User ID
    - Filename and size
    - Task ID dispatched
    - Any errors with stack traces

## Technical Implementation Notes

### Architecture

- Layer: Controller (Presentation)
- Dependencies: PhotoService, S3Service, Auth dependency
- Design pattern: Thin controller, business logic in service

### Code Hints

**File upload handling (FastAPI):**

```python
from fastapi import UploadFile, File

@router.post("/photo")
async def upload_photo(
    file: UploadFile = File(..., description="Photo file")
):
    # Read file content
    contents = await file.read()

    # Get file info
    filename = file.filename
    content_type = file.content_type

    # Reset file pointer for service layer
    await file.seek(0)

    # Pass to service
    result = await photo_service.process(file)
```

**File size validation:**

```python
# Method 1: Read entire file (small files)
contents = await file.read()
if len(contents) > MAX_SIZE:
    raise HTTPException(413, "File too large")

# Method 2: Seek to end (efficient for large files)
file.file.seek(0, 2)
file_size = file.file.tell()
file.file.seek(0)
```

**Multipart form example (OpenAPI):**

```python
from fastapi.openapi.models import Example

@router.post(
    "/photo",
    responses={
        202: {
            "description": "Accepted",
            "content": {
                "application/json": {
                    "example": {
                        "task_id": "550e8400-e29b-41d4-a716-446655440000",
                        "status": "processing",
                        "poll_url": "/api/stock/tasks/status?task_id=..."
                    }
                }
            }
        }
    }
)
```

### Testing Requirements

**Unit Tests** (`tests/controllers/test_stock_controller.py`):

```python
import pytest
from fastapi.testclient import TestClient
from io import BytesIO
from app.main import app

client = TestClient(app)

def test_upload_photo_success(mock_photo_service, auth_headers):
    """Valid photo upload returns 202 with task_id"""
    # Create test image
    image_data = b"fake_jpeg_data"
    files = {"file": ("test.jpg", BytesIO(image_data), "image/jpeg")}

    mock_photo_service.create_photo_session.return_value = {
        "task_id": "550e8400-e29b-41d4-a716-446655440000",
        "session_id": 123
    }

    response = client.post(
        "/api/stock/photo",
        files=files,
        headers=auth_headers
    )

    assert response.status_code == 202
    assert "task_id" in response.json()
    assert response.json()["status"] == "processing"

def test_upload_invalid_file_type(auth_headers):
    """Non-image file returns 400"""
    files = {"file": ("test.txt", BytesIO(b"text"), "text/plain")}

    response = client.post("/api/stock/photo", files=files, headers=auth_headers)

    assert response.status_code == 400
    assert "Invalid file type" in response.json()["detail"]

def test_upload_file_too_large(auth_headers):
    """File >20MB returns 413"""
    large_file = BytesIO(b"x" * (21 * 1024 * 1024))  # 21MB
    files = {"file": ("large.jpg", large_file, "image/jpeg")}

    response = client.post("/api/stock/photo", files=files, headers=auth_headers)

    assert response.status_code == 413

def test_upload_unauthenticated():
    """Missing auth token returns 401"""
    files = {"file": ("test.jpg", BytesIO(b"data"), "image/jpeg")}

    response = client.post("/api/stock/photo", files=files)

    assert response.status_code == 401
```

**Integration Tests** (`tests/integration/test_photo_upload_flow.py`):

```python
@pytest.mark.asyncio
async def test_photo_upload_end_to_end(db_session, test_user, real_photo_file):
    """Complete photo upload flow (no mocks)"""
    with open(real_photo_file, "rb") as f:
        files = {"file": ("photo.jpg", f, "image/jpeg")}

        response = client.post(
            "/api/stock/photo",
            files=files,
            headers={"Authorization": f"Bearer {test_user.token}"}
        )

    assert response.status_code == 202
    task_id = response.json()["task_id"]

    # Verify photo_processing_session created in DB
    session_result = await db_session.execute(
        select(PhotoProcessingSession).where(
            PhotoProcessingSession.celery_task_id == task_id
        )
    )
    session = session_result.scalar_one()
    assert session is not None
    assert session.user_id == test_user.id
```

**Coverage Target**: ≥85%

### Performance Expectations

- File upload (20MB): <3s (network + S3 upload)
- Response time: <500ms (async dispatch, no waiting for ML)
- Celery task dispatch: <50ms
- Concurrent uploads: Support 10+ simultaneous uploads

## Handover Briefing

**For the next developer:**

**Context**: This is the **main entry point** for stock initialization. 95%+ of users will use this
photo-based method instead of manual entry.

**Key decisions made**:

1. **HTTP 202 (Accepted)**: Immediate response, poll for status (async pattern)
2. **20MB limit**: Balances high-res photos vs server memory
3. **Multipart form-data**: Standard for file uploads, works with all HTTP clients
4. **Task ID polling**: User polls GET /api/stock/tasks/status?task_id=... (separate endpoint)
5. **EXIF extraction in service**: Controller only validates file, service extracts metadata
6. **Auth required**: Only authenticated users can upload (prevents abuse)

**Known limitations**:

- No streaming upload (file loaded into memory) - acceptable for 20MB limit
- No progress updates during upload (browser handles this)
- Task polling required (no WebSocket push notifications yet)

**Next steps after this card**:

- C007: GET /api/stock/tasks/status (task polling endpoint)
- SCH002: PhotoUploadRequest/Response schemas
- SVC001: PhotoService.create_photo_session implementation
- CEL005: ml_parent_task Celery task

**Questions to validate**:

- Is multipart/form-data correctly handled? (Test with Postman/curl)
- Does file size validation work? (Upload 21MB file, expect HTTP 413)
- Is task_id returned immediately? (Response <500ms)

## Definition of Done Checklist

- [ ] Controller route defined in `app/controllers/stock_controller.py`
- [ ] File validation (type, size) implemented
- [ ] Error handling for all edge cases (400, 401, 413, 500)
- [ ] OpenAPI documentation complete (request/response examples)
- [ ] Logging for uploads and errors
- [ ] Unit tests pass (≥85% coverage)
- [ ] Integration test with real file upload
- [ ] Manual test with Postman/Swagger UI
- [ ] PhotoService dependency injected correctly
- [ ] Auth dependency working (401 for unauthenticated)
- [ ] PR reviewed and approved (2+ reviewers)
- [ ] No linting errors (`ruff check`)

## Time Tracking

- **Estimated**: 3 story points
- **Actual**: TBD
- **Started**: TBD
- **Completed**: TBD

---

**Card Created**: 2025-10-09
**Last Updated**: 2025-10-09
**Card Owner**: TBD
