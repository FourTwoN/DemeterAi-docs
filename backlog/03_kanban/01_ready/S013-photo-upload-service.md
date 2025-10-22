# S013: PhotoUploadService

## Metadata

- **Epic**: [epic-004-services.md](../../02_epics/epic-004-services.md)
- **Sprint**: Sprint-04
- **Status**: `backlog`
- **Priority**: `CRITICAL`
- **Complexity**: L (5 story points)
- **Area**: `services/photo`
- **Assignee**: TBD
- **Dependencies**:
    - Blocks: [S014, C012]
    - Blocked by: [S006, S015, CEL005]

## Description

**What**: Implement `PhotoUploadService` for photo upload orchestration (S3 upload + session
creation + ML pipeline dispatch).

**Why**: Entry point for photo-based stock initialization. Orchestrates S3 upload, GPS extraction,
location lookup, and Celery task dispatch.

**Context**: Clean Architecture Application Layer. CRITICAL SERVICE - triggers ML pipeline via
Celery. Calls S006 (GPS lookup), S015 (S3 upload), and CEL005 (ML task dispatch).

## Acceptance Criteria

- [ ] **AC1**: Photo upload workflow:

```python
class PhotoUploadService:
    def __init__(
        self,
        session_service: PhotoProcessingSessionService,
        s3_service: S3ImageService,
        location_hierarchy_service: LocationHierarchyService,
        celery_app: Celery
    ):
        self.session_service = session_service
        self.s3_service = s3_service
        self.location_hierarchy_service = location_hierarchy_service
        self.celery_app = celery_app

    async def upload_photo(
        self,
        file: UploadFile,
        gps_longitude: float,
        gps_latitude: float,
        user_id: int
    ) -> PhotoUploadResponse:
        """
        Upload photo and trigger ML pipeline
        CRITICAL WORKFLOW: Upload → S3 → GPS lookup → Celery dispatch
        """
        # 1. GPS-based location lookup
        hierarchy = await self.location_hierarchy_service.get_full_hierarchy_by_gps(
            gps_longitude, gps_latitude
        )
        if not hierarchy:
            raise LocationNotFoundException(
                f"No location found at GPS ({gps_longitude}, {gps_latitude})"
            )

        # 2. Create processing session
        session = await self.session_service.create_session({
            "storage_location_id": hierarchy.storage_location.storage_location_id,
            "gps_longitude": gps_longitude,
            "gps_latitude": gps_latitude,
            "user_id": user_id,
            "status": "pending"
        })

        # 3. Upload to S3
        s3_key = await self.s3_service.upload_original(
            file, session.photo_processing_session_id
        )

        # 4. Dispatch ML pipeline (Celery task)
        task = self.celery_app.send_task(
            "ml.parent_task",
            args=[session.photo_processing_session_id, s3_key]
        )

        # 5. Update session with task ID
        await self.session_service.update_session(session.photo_processing_session_id, {
            "celery_task_id": task.id,
            "status": "processing"
        })

        return PhotoUploadResponse(
            session_id=session.photo_processing_session_id,
            s3_key=s3_key,
            task_id=task.id,
            location=hierarchy.storage_location
        )
```

- [ ] **AC2**: Validate file upload:

```python
async def validate_photo_upload(self, file: UploadFile) -> ValidationResult:
    """Validate photo file"""
    errors = []

    # Check file type
    if not file.content_type.startswith("image/"):
        errors.append("File must be an image")

    # Check file size (max 20MB)
    file_size = await file.read()
    await file.seek(0)
    if len(file_size) > 20 * 1024 * 1024:
        errors.append("File size exceeds 20MB limit")

    return ValidationResult(valid=len(errors) == 0, errors=errors)
```

- [ ] **AC3**: Unit tests achieve ≥85% coverage

## Technical Implementation Notes

### Architecture

- **Layer**: Application (Service)
- **Dependencies**: S006, S014, S015, CEL005
- **Design Pattern**: Orchestration service (coordinates photo workflow)

### Performance Expectations

- `upload_photo`: <2000ms (includes S3 upload)

## Handover Briefing

**Context**: CRITICAL entry point for photo-based initialization. Orchestrates GPS lookup, S3
upload, and ML dispatch.

**Key decisions**:

- GPS lookup before S3 upload (fail fast if no location)
- Session created with "pending" status, updated to "processing" after Celery dispatch
- Max file size: 20MB

**Next steps**: S014 (PhotoProcessingSessionService), CEL005 (ML parent task)

## Definition of Done Checklist

- [ ] Service code written
- [ ] S3 upload integration working
- [ ] Celery task dispatch tested
- [ ] Unit tests pass (≥85% coverage)
- [ ] PR reviewed (2+ approvals)

## Time Tracking

- **Estimated**: 5 story points (~10 hours)
- **Actual**: TBD

---

**Card Created**: 2025-10-09
**Last Updated**: 2025-10-09
**Card Owner**: TBD
