"""Photo Upload Service - Orchestration service for photo upload workflow.

This service orchestrates the complete photo upload workflow:
1. GPS-based location lookup
2. Create photo processing session
3. Upload to S3
4. Dispatch ML pipeline (Celery task)

Architecture:
    Layer: Service Layer (Orchestration)
    Dependencies:
        - PhotoProcessingSessionService (session management)
        - S3ImageService (S3 upload)
        - LocationHierarchyService (GPS lookup)
    Pattern: Orchestration service - coordinates multiple services

Critical Rules:
    - Service→Service pattern enforced (NO direct repository access)
    - GPS lookup before S3 upload (fail fast if no location)
    - Session created with PENDING status
    - Celery task dispatch is async (non-blocking)
    - File size validation (max 20MB)
"""

import uuid

from fastapi import UploadFile

from app.core.exceptions import (
    ResourceNotFoundException,
    ValidationException,
)
from app.core.logging import get_logger
from app.models.photo_processing_session import ProcessingSessionStatusEnum
from app.models.s3_image import ContentTypeEnum, UploadSourceEnum
from app.schemas.photo_processing_session_schema import (
    PhotoProcessingSessionCreate,
)
from app.schemas.photo_schema import PhotoUploadResponse
from app.schemas.s3_image_schema import S3ImageUploadRequest
from app.services.photo.photo_processing_session_service import (
    PhotoProcessingSessionService,
)
from app.services.photo.s3_image_service import S3ImageService
from app.services.storage_location_service import StorageLocationService

logger = get_logger(__name__)

# File size limit: 20MB
MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024

# Allowed image content types
ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
}


class PhotoUploadService:
    """Orchestration service for photo upload workflow.

    This service coordinates the complete photo upload workflow including
    GPS lookup, S3 upload, session creation, and ML pipeline dispatch.

    Key Features:
        - GPS-based location lookup
        - File validation (type, size)
        - S3 upload orchestration
        - Photo processing session creation
        - ML pipeline dispatch (via Celery)

    Attributes:
        session_service: PhotoProcessingSessionService for session management
        s3_service: S3ImageService for S3 uploads
        location_service: StorageLocationService for GPS lookup
    """

    def __init__(
        self,
        session_service: PhotoProcessingSessionService,
        s3_service: S3ImageService,
        location_service: StorageLocationService,
    ) -> None:
        """Initialize PhotoUploadService with dependencies.

        Args:
            session_service: PhotoProcessingSessionService for sessions
            s3_service: S3ImageService for S3 operations
            location_service: StorageLocationService for GPS lookup
        """
        self.session_service = session_service
        self.s3_service = s3_service
        self.location_service = location_service

    async def upload_photo(
        self,
        file: UploadFile,
        gps_longitude: float,
        gps_latitude: float,
        user_id: int,
    ) -> PhotoUploadResponse:
        """Upload photo and trigger ML pipeline.

        Complete workflow:
        1. Validate file (type, size)
        2. GPS-based location lookup
        3. Upload to S3 (original image)
        4. Create processing session (PENDING)
        5. Dispatch Celery ML task
        6. Update session (PROCESSING)

        Args:
            file: Photo file to upload
            gps_longitude: GPS longitude coordinate
            gps_latitude: GPS latitude coordinate
            user_id: User ID for tracking

        Returns:
            PhotoUploadResponse with session_id, task_id, status

        Raises:
            ValidationException: If file is invalid (type, size)
            ResourceNotFoundException: If GPS location not found

        Business Rules:
            - File must be image type (jpeg, png, webp)
            - File size max 20MB
            - GPS location must exist in warehouse hierarchy
            - Session starts as PENDING, transitions to PROCESSING after Celery dispatch
        """
        logger.info(
            "Starting photo upload workflow",
            extra={
                "gps_longitude": gps_longitude,
                "gps_latitude": gps_latitude,
                "user_id": user_id,
                "filename": file.filename,
            },
        )

        # STEP 1: Validate file
        await self._validate_photo_file(file)

        # STEP 2: GPS-based location lookup (fail fast if no location)
        logger.info("Looking up location by GPS coordinates")
        location = await self.location_service.get_location_by_gps(gps_longitude, gps_latitude)

        if not location:
            raise ResourceNotFoundException(
                resource_type="StorageLocation",
                resource_id=f"GPS({gps_longitude}, {gps_latitude})",
            )

        storage_location_id = location.storage_location_id

        logger.info(
            "Location found via GPS",
            extra={
                "storage_location_id": storage_location_id,
                "storage_area_id": location.storage_area_id,
            },
        )

        # STEP 3: Upload to S3 (original image)
        logger.info("Uploading original image to S3")

        # Read file bytes
        file_bytes = await file.read()
        await file.seek(0)  # Reset file pointer

        # Generate temporary session_id for S3 upload (will be replaced by actual session)
        temp_session_id = uuid.uuid4()

        # Create upload request with required metadata
        upload_request = S3ImageUploadRequest(
            session_id=temp_session_id,
            filename=file.filename or "photo.jpg",
            content_type=ContentTypeEnum(file.content_type or "image/jpeg"),
            file_size_bytes=len(file_bytes),
            width_px=0,  # Will be set by ML pipeline
            height_px=0,  # Will be set by ML pipeline
            upload_source=UploadSourceEnum.WEB,
            uploaded_by_user_id=user_id,
            exif_metadata=None,
            gps_coordinates={"latitude": gps_latitude, "longitude": gps_longitude},
        )

        # Upload original image (returns S3ImageResponse)
        original_image = await self.s3_service.upload_original(
            file_bytes=file_bytes,
            session_id=temp_session_id,
            upload_request=upload_request,
        )

        logger.info(
            "Original image uploaded to S3",
            extra={
                "s3_key": original_image.s3_key_original,
                "image_id": str(original_image.image_id),
            },
        )

        # STEP 4: Create processing session (PENDING)
        logger.info("Creating photo processing session")

        session_request = PhotoProcessingSessionCreate(
            storage_location_id=storage_location_id,
            original_image_id=original_image.image_id,
            processed_image_id=None,
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

        logger.info(
            "Photo processing session created",
            extra={
                "session_id": str(session.session_id),
                "session_db_id": session.id,
                "status": session.status.value,
            },
        )

        # STEP 5: Dispatch ML pipeline (Celery task)
        from app.tasks.ml_tasks import ml_parent_task

        # Build image_data for ML task
        # NOTE: ml_parent_task expects list[dict] with keys:
        #   - image_id: S3Image UUID (used for tracking)
        #   - image_path (str): Path to image file (local or S3)
        #   - storage_location_id (int): Where photo was taken
        image_data = [
            {
                "image_id": str(original_image.image_id),  # S3Image UUID as string
                "image_path": original_image.s3_key_original,  # S3 key path
                "storage_location_id": storage_location_id,  # From GPS lookup (line 156)
            }
        ]

        # Call ML task with correct signature
        # ml_parent_task(session_id: int, image_data: list[dict])
        celery_task = ml_parent_task.delay(
            session_id=session.id,  # PhotoProcessingSession.id (integer PK)
            image_data=image_data,
        )
        task_id = celery_task.id

        logger.info(
            "ML pipeline task dispatched",
            extra={
                "task_id": str(task_id),
                "session_db_id": session.id,  # Database ID (int)
                "session_uuid": str(session.session_id),  # UUID for external reference
                "image_uuid": str(original_image.image_id),  # S3Image UUID
                "storage_location_id": storage_location_id,
                "num_images": len(image_data),
            },
        )

        # STEP 6: Update session to PROCESSING
        # NOTE: In production, this would be done by the ML pipeline
        # For now, we keep it as PENDING until ML pipeline is ready

        # await self.session_service.mark_session_processing(
        #     session.id, str(task_id)
        # )

        logger.info(
            "Photo upload workflow completed",
            extra={
                "session_id": str(session.session_id),
                "task_id": str(task_id),
                "status": "pending",
            },
        )

        # Return response
        return PhotoUploadResponse(
            task_id=task_id,
            session_id=session.id,
            status="pending",
            message="Photo uploaded successfully. Processing will start shortly.",
            poll_url=f"/api/photo-sessions/{session.id}",
        )

    async def _validate_photo_file(self, file: UploadFile) -> None:
        """Validate photo file (type and size).

        Args:
            file: Photo file to validate

        Raises:
            ValidationException: If file is invalid

        Business Rules:
            - Content type must be in ALLOWED_CONTENT_TYPES
            - File size must be ≤ MAX_FILE_SIZE_BYTES (20MB)
        """
        # Validate content type
        if file.content_type not in ALLOWED_CONTENT_TYPES:
            raise ValidationException(
                field="file",
                message=f"Invalid file type. Must be one of {ALLOWED_CONTENT_TYPES}, got {file.content_type}",
                value=file.content_type,
            )

        # Validate file size
        file_bytes = await file.read()
        await file.seek(0)  # Reset file pointer

        if len(file_bytes) > MAX_FILE_SIZE_BYTES:
            raise ValidationException(
                field="file",
                message=f"File size exceeds {MAX_FILE_SIZE_BYTES / (1024 * 1024):.0f}MB limit (got {len(file_bytes) / (1024 * 1024):.2f}MB)",
                value=len(file_bytes),
            )

        logger.info(
            "File validation passed",
            extra={
                "content_type": file.content_type,
                "size_bytes": len(file_bytes),
                "filename": file.filename,
            },
        )
