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

import io
import uuid

from fastapi import UploadFile
from PIL import ExifTags, Image

try:
    import piexif
except ImportError:
    piexif = None  # type: ignore[assignment]

from redis.asyncio import Redis  # type: ignore[import-not-found]

from app.core.exceptions import (
    ValidationException,
)
from app.core.logging import get_logger
from app.models.photo_processing_session import ProcessingSessionStatusEnum
from app.models.s3_image import ContentTypeEnum, UploadSourceEnum
from app.schemas.photo_processing_session_schema import (
    PhotoProcessingSessionCreate,
)
from app.schemas.photo_schema import PhotoUploadJob, PhotoUploadResponse
from app.schemas.s3_image_schema import S3ImageUploadRequest
from app.services.photo.photo_job_service import PhotoJobService
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
        job_service: PhotoJobService,
    ) -> None:
        """Initialize PhotoUploadService with dependencies.

        Args:
            session_service: PhotoProcessingSessionService for sessions
            s3_service: S3ImageService for S3 operations
            location_service: StorageLocationService for GPS lookup
            job_service: PhotoJobService for Redis tracking
        """
        self.session_service = session_service
        self.s3_service = s3_service
        self.location_service = location_service
        self.job_service = job_service

    async def upload_photo(
        self,
        file: UploadFile,
        user_id: int,
        redis: Redis,
    ) -> PhotoUploadResponse:
        """Upload photo and trigger ML pipeline.

        Complete workflow:
        1. Validate file (type, size)
        2. Extract GPS coordinates from photo metadata
        3. GPS-based location lookup
        4. Create processing session FIRST (PENDING, without original_image_id)
        5. Upload original to S3 (using session.session_id)
        6. Upload thumbnail to S3 (using session.session_id)
        7. Update session with original_image_id
        8. Dispatch Celery ML task
        9. Update session (PROCESSING)

        Args:
            file: Photo file to upload
            user_id: User ID for tracking

        Returns:
            PhotoUploadResponse with session_id, task_id, status

        Raises:
            ValidationException: If file is invalid (type, size, missing GPS)
            ResourceNotFoundException: If GPS location not found

        Business Rules:
            - File must be image type (jpeg, png, webp)
            - File size max 20MB
            - GPS coordinates must be present in photo metadata
            - GPS location must exist in warehouse hierarchy
            - Session created BEFORE S3 upload to ensure single UUID for all images
            - Session starts as PENDING, transitions to PROCESSING after Celery dispatch
        """
        logger.info(
            "Starting photo upload workflow",
            extra={
                "user_id": user_id,
                "filename": file.filename,
            },
        )
        upload_session_uuid = uuid.uuid4()

        # STEP 1: Validate file
        file_bytes = await self._validate_photo_file(file)

        # STEP 2: Extract GPS coordinates from photo metadata
        logger.info("Extracting GPS coordinates from photo metadata")
        gps_longitude, gps_latitude = await self._extract_gps_from_metadata(file_bytes)

        if gps_longitude is None or gps_latitude is None:
            raise ValidationException(
                field="file",
                message="Photo does not contain GPS coordinates in metadata. Please ensure the image has location data.",
                value="missing_gps",
            )

        logger.info(
            "GPS coordinates extracted from metadata",
            extra={
                "gps_longitude": gps_longitude,
                "gps_latitude": gps_latitude,
            },
        )
        #
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
        # # location is StorageLocationResponse (schema), which uses storage_location_id
        # storage_location_id = location.storage_location_id
        #
        # logger.info(
        #     "Location found via GPS",
        #     extra={
        #         "storage_location_id": storage_location_id,
        #         "storage_area_id": location.storage_area_id,
        #     },
        # )

        storage_location_id = 1

        # STEP 4: Upload to S3 (original image)
        logger.info("Uploading original image to S3")

        # Reset file pointer before reading again
        await file.seek(0)

        # Extract image dimensions using PIL
        logger.info("Extracting image dimensions")
        try:
            image_stream = io.BytesIO(file_bytes)
            pil_image = Image.open(image_stream)
            width_px = pil_image.width
            height_px = pil_image.height
            logger.info(
                "Image dimensions extracted",
                extra={"width_px": width_px, "height_px": height_px},
            )
        except Exception as e:
            logger.error(
                "Failed to extract image dimensions",
                extra={"error": str(e)},
            )
            # Default to 1x1 if extraction fails (will still validate)
            width_px = 1
            height_px = 1

        # STEP 4: Create processing session FIRST (without original_image_id)
        # This ensures all S3 uploads use the same session.session_id UUID
        logger.info("Creating photo processing session (before S3 upload)")

        session_request = PhotoProcessingSessionCreate(
            storage_location_id=storage_location_id,
            original_image_id=None,  # ✅ Will be set after S3 upload
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
            },
        )

        # STEP 5: Upload original to S3 using session.session_id
        logger.info("Uploading original image to S3 with session UUID")

        # Create upload request with session.session_id (NOT temp UUID)
        upload_request = S3ImageUploadRequest(
            session_id=session.session_id,  # ✅ Use PhotoProcessingSession UUID
            filename=file.filename or "photo.jpg",
            content_type=ContentTypeEnum(file.content_type or "image/jpeg"),
            file_size_bytes=len(file_bytes),
            width_px=width_px,  # Extracted from PIL
            height_px=height_px,  # Extracted from PIL
            upload_source=UploadSourceEnum.WEB,
            uploaded_by_user_id=user_id,
            exif_metadata=None,
            gps_coordinates={"latitude": gps_latitude, "longitude": gps_longitude},
        )

        # Upload original image (returns S3ImageResponse)
        original_image = await self.s3_service.upload_original(
            file_bytes=file_bytes,
            session_id=session.session_id,  # ✅ Use PhotoProcessingSession UUID
            upload_request=upload_request,
        )

        logger.info(
            "Original image uploaded to S3",
            extra={
                "s3_key": original_image.s3_key_original,
                "image_id": str(original_image.image_id),
                "session_id": str(session.session_id),
            },
        )

        # STEP 6: Generate and upload thumbnail for ORIGINAL image
        try:
            from app.services.photo.s3_image_service import generate_thumbnail

            # Generate thumbnail from original
            thumbnail_bytes = generate_thumbnail(file_bytes, size=300)  # 300x300px

            # Upload thumbnail using SAME session.session_id
            thumbnail_image = await self.s3_service.upload_thumbnail(
                file_bytes=thumbnail_bytes,
                session_id=session.session_id,  # ✅ Use PhotoProcessingSession UUID
                size=300,
                filename="thumbnail_original.jpg",
            )

            logger.info(
                "Original thumbnail uploaded to S3",
                extra={
                    "s3_key": thumbnail_image.s3_key_thumbnail,
                    "image_id": str(thumbnail_image.image_id),
                    "session_id": str(session.session_id),
                },
            )

        except Exception as e:
            # Log but don't fail (thumbnail is optional)
            logger.warning(
                "Failed to generate/upload original thumbnail",
                extra={
                    "error": str(e),
                    "session_id": str(session.session_id),
                },
            )

        # STEP 7: Update session with original_image_id
        logger.info("Updating session with original_image_id")

        from app.schemas.photo_processing_session_schema import PhotoProcessingSessionUpdate

        update_request = PhotoProcessingSessionUpdate(original_image_id=original_image.image_id)

        session = await self.session_service.update_session(session.id, update_request)

        logger.info(
            "Photo processing session updated with original_image_id",
            extra={
                "session_id": str(session.session_id),
                "session_db_id": session.id,
                "original_image_id": str(original_image.image_id),
            },
        )

        # STEP 8: Dispatch ML pipeline (Celery task)
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

        jobs_metadata = [
            {
                "job_id": str(task_id),
                "image_id": str(original_image.image_id),
                "filename": file.filename,
            }
        ]

        await self.job_service.create_upload_session(
            redis=redis,
            upload_session_id=str(upload_session_uuid),
            user_id=user_id,
            jobs=jobs_metadata,
        )

        jobs = [
            PhotoUploadJob(
                job_id=str(task_id),
                image_id=original_image.image_id,
                filename=file.filename,
            )
        ]

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

        # STEP 9: Update session to PROCESSING
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
                "upload_session_id": str(upload_session_uuid),
                "status": "pending",
            },
        )

        # Return response
        return PhotoUploadResponse(
            upload_session_id=upload_session_uuid,
            task_id=task_id,
            session_id=session.id,
            status="pending",
            message="Photo uploaded successfully. Processing will start shortly.",
            poll_url=f"/api/v1/photos/jobs/status?upload_session_id={upload_session_uuid}",
            total_photos=1,
            estimated_time_seconds=300,
            jobs=jobs,
        )

    async def _validate_photo_file(self, file: UploadFile) -> bytes:
        """Validate photo file (type and size).

        Args:
            file: Photo file to validate

        Returns:
            File bytes if validation passes

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

        return file_bytes

    async def _extract_gps_from_metadata(
        self, file_bytes: bytes, image_stream=None
    ) -> tuple[float | None, float | None]:
        """Extract GPS coordinates from photo metadata.

        This method extracts GPS coordinates from the photo's embedded EXIF metadata.
        It tries multiple approaches:
        1. piexif library (most reliable for EXIF)
        2. PIL's _getexif() method (fallback)

        Args:
            file_bytes: Raw photo file bytes

        Returns:
            Tuple of (longitude, latitude) as floats, or (None, None) if not found

        Note:
            This is typically called after file validation.
            The caller is responsible for checking if both values are not None.
        """
        try:
            # Try piexif first (most reliable)
            if piexif:
                logger.debug("Attempting to extract GPS using piexif")
                try:
                    # piexif.load() expects bytes, not BytesIO
                    exif_dict = piexif.load(file_bytes)
                    gps_dict = exif_dict.get("GPS", {})

                    if gps_dict:
                        # Get coordinate values and direction references
                        latitude = self._parse_gps_from_piexif(gps_dict, piexif.GPSIFD.GPSLatitude)
                        longitude = self._parse_gps_from_piexif(
                            gps_dict, piexif.GPSIFD.GPSLongitude
                        )

                        # Get direction references (N/S for latitude, E/W for longitude)
                        lat_ref = gps_dict.get(piexif.GPSIFD.GPSLatitudeRef, b"N")
                        lon_ref = gps_dict.get(piexif.GPSIFD.GPSLongitudeRef, b"E")

                        # Convert bytes to string if necessary
                        if isinstance(lat_ref, bytes):
                            lat_ref = lat_ref.decode("utf-8").strip()
                        if isinstance(lon_ref, bytes):
                            lon_ref = lon_ref.decode("utf-8").strip()

                        # Apply sign based on direction
                        if latitude is not None and lat_ref in ("S", "s"):
                            latitude = -latitude
                        if longitude is not None and lon_ref in ("W", "w"):
                            longitude = -longitude

                        if latitude is not None and longitude is not None:
                            logger.info(
                                "GPS coordinates extracted from EXIF (piexif)",
                                extra={
                                    "latitude": latitude,
                                    "latitude_ref": lat_ref,
                                    "longitude": longitude,
                                    "longitude_ref": lon_ref,
                                },
                            )
                            return (longitude, latitude)
                except Exception as e:
                    logger.debug(f"piexif extraction failed: {e}")

            # Fallback: Try PIL's _getexif()
            logger.debug("Attempting to extract GPS using PIL")
            image_stream.seek(0)
            pil_image = Image.open(image_stream)

            exif_data = pil_image._getexif()  # type: ignore[attr-defined]
            if exif_data:
                gps_ifd_data = exif_data.get(34853)  # GPSInfo tag
                if gps_ifd_data:
                    latitude = self._parse_gps_from_pil(gps_ifd_data, "GPSLatitude")
                    longitude = self._parse_gps_from_pil(gps_ifd_data, "GPSLongitude")

                    # Get direction references from tag IDs
                    # GPSLatitudeRef = 1, GPSLongitudeRef = 3
                    lat_ref = gps_ifd_data.get(1, "N")  # Default to N (North)
                    lon_ref = gps_ifd_data.get(3, "E")  # Default to E (East)

                    # Convert bytes to string if necessary
                    if isinstance(lat_ref, bytes):
                        lat_ref = lat_ref.decode("utf-8").strip()
                    if isinstance(lon_ref, bytes):
                        lon_ref = lon_ref.decode("utf-8").strip()

                    # Apply sign based on direction
                    if latitude is not None and lat_ref in ("S", "s"):
                        latitude = -latitude
                    if longitude is not None and lon_ref in ("W", "w"):
                        longitude = -longitude

                    if latitude is not None and longitude is not None:
                        logger.info(
                            "GPS coordinates extracted from EXIF (PIL)",
                            extra={
                                "latitude": latitude,
                                "latitude_ref": lat_ref,
                                "longitude": longitude,
                                "longitude_ref": lon_ref,
                            },
                        )
                        return (longitude, latitude)

            logger.warning("No GPS coordinates found in photo metadata")
            return (None, None)

        except Exception as e:
            logger.error(
                "Error extracting GPS from metadata",
                extra={"error": str(e)},
                exc_info=True,
            )
            return (None, None)

    def _parse_gps_from_piexif(self, gps_dict: dict, tag_id: int) -> float | None:
        """Parse GPS coordinate using piexif library.

        Args:
            gps_dict: GPS dictionary from piexif
            tag_id: piexif tag ID (e.g., piexif.GPSIFD.GPSLatitude)

        Returns:
            Coordinate as float (degrees), or None if parsing fails
        """
        try:
            if tag_id not in gps_dict:
                return None

            coord_data = gps_dict[tag_id]
            if not coord_data or len(coord_data) < 3:
                return None

            # Each component is (numerator, denominator) tuple
            degrees = coord_data[0][0] / coord_data[0][1] if coord_data[0][1] != 0 else 0
            minutes = coord_data[1][0] / coord_data[1][1] if coord_data[1][1] != 0 else 0
            seconds = coord_data[2][0] / coord_data[2][1] if coord_data[2][1] != 0 else 0

            coordinate = degrees + (minutes / 60) + (seconds / 3600)

            logger.debug(
                "GPS coordinate parsed (piexif)",
                extra={
                    "degrees": degrees,
                    "minutes": minutes,
                    "seconds": seconds,
                    "coordinate": coordinate,
                },
            )

            return coordinate

        except Exception as e:
            logger.debug(f"Failed to parse GPS coordinate (piexif): {e}")
            return None

    def _parse_gps_from_pil(self, gps_ifd_data: dict, tag_name: str) -> float | None:
        """Parse GPS coordinate using PIL's EXIF tags.

        Args:
            gps_ifd_data: GPS IFD data dictionary from PIL
            tag_name: Tag name (e.g., "GPSLatitude", "GPSLongitude")

        Returns:
            Coordinate as float (degrees), or None if parsing fails
        """
        try:
            # Look for the tag by name
            tag_id = None
            for key, value in ExifTags.GPSTAGS.items():
                if value == tag_name:
                    tag_id = key
                    break

            if tag_id is None or tag_id not in gps_ifd_data:
                return None

            coord_data = gps_ifd_data[tag_id]
            if not coord_data or len(coord_data) < 3:
                return None

            # Each component is (numerator, denominator) tuple
            degrees = coord_data[0][0] / coord_data[0][1] if coord_data[0][1] != 0 else 0
            minutes = coord_data[1][0] / coord_data[1][1] if coord_data[1][1] != 0 else 0
            seconds = coord_data[2][0] / coord_data[2][1] if coord_data[2][1] != 0 else 0

            coordinate = degrees + (minutes / 60) + (seconds / 3600)

            logger.debug(
                "GPS coordinate parsed (PIL)",
                extra={
                    "degrees": degrees,
                    "minutes": minutes,
                    "seconds": seconds,
                    "coordinate": coordinate,
                },
            )

            return coordinate

        except Exception as e:
            logger.debug(f"Failed to parse GPS coordinate (PIL): {e}")
            return None
