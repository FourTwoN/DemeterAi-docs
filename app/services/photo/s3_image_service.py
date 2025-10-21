"""S3 Image Service - Business logic for S3 image upload/download operations.

This service handles all S3 operations including:
- Uploading original photos to S3
- Uploading visualization images to S3
- Downloading images from S3
- Generating presigned URLs for browser access
- Circuit breaker pattern for S3 resilience
- Image lifecycle management

Architecture:
    Layer: Service Layer (Business Logic)
    Dependencies: S3ImageRepository (own repo), Settings (config)
    Pattern: Circuit breaker for S3 failures (pybreaker)

Critical Rules:
    - Service→Service pattern enforced (NO direct repository access except own)
    - All S3 operations are async (using asyncio.to_thread with boto3)
    - Circuit breaker prevents cascading failures (fail_max=5, timeout=60s)
    - Presigned URLs default to 24-hour expiry
    - S3 key format: {session_id}/{filename} for original images
    - S3 key format: {session_id}/viz_{filename} for visualizations

Note:
    Uses boto3 (sync) with asyncio.to_thread() for async operations.
    This avoids adding aioboto3 dependency while maintaining async interface.
"""

import asyncio
import uuid

import boto3
from pybreaker import CircuitBreaker, CircuitBreakerError

from app.core.config import settings
from app.core.exceptions import S3UploadException, ValidationException
from app.core.logging import get_logger
from app.models.s3_image import ProcessingStatusEnum
from app.repositories.s3_image_repository import S3ImageRepository
from app.schemas.s3_image_schema import S3ImageResponse, S3ImageUploadRequest

logger = get_logger(__name__)

# Circuit breaker for S3 operations (fail_max=5, reset_timeout=60s)
# After 5 consecutive failures, circuit opens for 60 seconds
s3_circuit_breaker = CircuitBreaker(fail_max=5, reset_timeout=60, name="S3CircuitBreaker")


class S3ImageService:
    """Service for S3 image upload/download with circuit breaker resilience.

    This service provides centralized S3 operations with error handling,
    circuit breaker pattern for resilience, and database metadata management.

    Key Features:
        - Async S3 operations using aioboto3
        - Circuit breaker prevents cascading failures
        - Presigned URLs for secure browser access
        - Database metadata tracking
        - File size validation (max 500MB)
        - Support for multiple buckets (original, visualization)

    Attributes:
        repo: S3ImageRepository for database operations
        s3_session: aioboto3 session for S3 operations
    """

    def __init__(self, repo: S3ImageRepository) -> None:
        """Initialize S3ImageService with repository.

        Args:
            repo: S3ImageRepository for database operations

        Note:
            S3 client is created lazily on first use to avoid
            blocking during service initialization.
        """
        self.repo = repo
        self._s3_client = None

    @property
    def s3_client(self) -> "boto3.client":
        """Get or create boto3 S3 client (lazy initialization).

        Returns:
            Configured boto3 S3 client for S3 operations

        Note:
            Client is created once and reused for all S3 operations.
            Uses boto3 (sync) which is wrapped with asyncio.to_thread() for async.
        """
        if self._s3_client is None:
            self._s3_client = boto3.client(
                "s3",
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION,
            )
        return self._s3_client

    async def upload_original(
        self,
        file_bytes: bytes,
        session_id: uuid.UUID,
        upload_request: S3ImageUploadRequest,
    ) -> S3ImageResponse:
        """Upload original photo to S3 (bucket: demeter-photos-original).

        Business rules:
        1. File size must be 1 byte to 500MB
        2. S3 key format: {session_id}/{filename}
        3. Image metadata stored in database
        4. Circuit breaker protects against S3 failures
        5. Presigned URL generated with 24-hour expiry

        Args:
            file_bytes: Image file bytes (max 500MB)
            session_id: Photo processing session UUID
            upload_request: Upload metadata (filename, dimensions, etc.)

        Returns:
            S3ImageResponse with S3 key and presigned URL

        Raises:
            ValidationException: If file size is invalid
            S3UploadException: If S3 upload fails
            CircuitBreakerError: If circuit breaker is open (too many failures)

        Example:
            ```python
            service = S3ImageService(repo)
            request = S3ImageUploadRequest(
                session_id=session_id,
                filename="photo_123.jpg",
                content_type=ContentTypeEnum.JPEG,
                file_size_bytes=2048576,
                width_px=4000,
                height_px=3000,
            )
            result = await service.upload_original(file_bytes, session_id, request)
            print(f"Uploaded to: {result.s3_key_original}")
            print(f"Presigned URL: {result.presigned_url}")
            ```
        """
        # Validate file size (1 byte to 500MB)
        if not file_bytes or len(file_bytes) == 0:
            raise ValidationException(field="file_bytes", message="File cannot be empty", value=0)

        if len(file_bytes) > 500_000_000:  # 500MB
            raise ValidationException(
                field="file_bytes",
                message="File size exceeds 500MB limit",
                value=len(file_bytes),
            )

        # Build S3 key: {session_id}/{filename}
        s3_key = f"{session_id}/{upload_request.filename}"

        logger.info(
            "Uploading original image to S3",
            s3_key=s3_key,
            bucket=settings.S3_BUCKET_ORIGINAL,
            file_size=len(file_bytes),
            session_id=str(session_id),
        )

        # Upload to S3 with circuit breaker
        try:
            await self._upload_to_s3(
                s3_key=s3_key,
                file_bytes=file_bytes,
                bucket=settings.S3_BUCKET_ORIGINAL,
                content_type=upload_request.content_type.value,
            )
        except CircuitBreakerError as e:
            logger.error(
                "S3 circuit breaker open - too many failures",
                s3_key=s3_key,
                bucket=settings.S3_BUCKET_ORIGINAL,
            )
            raise S3UploadException(
                file_name=upload_request.filename,
                bucket=settings.S3_BUCKET_ORIGINAL,
                error="S3 service temporarily unavailable (circuit breaker open)",
            ) from e

        # Generate image_id (UUID primary key)
        image_id = uuid.uuid4()

        # Store metadata in database
        s3_image_data = {
            "image_id": image_id,
            "s3_bucket": settings.S3_BUCKET_ORIGINAL,
            "s3_key_original": s3_key,
            "content_type": upload_request.content_type,
            "file_size_bytes": len(file_bytes),
            "width_px": upload_request.width_px,
            "height_px": upload_request.height_px,
            "upload_source": upload_request.upload_source,
            "uploaded_by_user_id": upload_request.uploaded_by_user_id,
            "exif_metadata": upload_request.exif_metadata,
            "gps_coordinates": upload_request.gps_coordinates,
            "status": ProcessingStatusEnum.UPLOADED,
        }

        s3_image = await self.repo.create(s3_image_data)

        # Generate presigned URL for browser access (24-hour expiry)
        presigned_url = await self.generate_presigned_url(
            s3_key=s3_key, bucket=settings.S3_BUCKET_ORIGINAL, expiry_hours=24
        )

        logger.info(
            "Original image uploaded successfully",
            image_id=str(image_id),
            s3_key=s3_key,
            bucket=settings.S3_BUCKET_ORIGINAL,
        )

        return S3ImageResponse.from_model(s3_image, presigned_url=presigned_url)

    async def upload_visualization(
        self,
        file_bytes: bytes,
        session_id: uuid.UUID,
        filename: str,
        content_type: str = "image/jpeg",
    ) -> S3ImageResponse:
        """Upload visualization image to S3 (bucket: demeter-photos-viz).

        Visualization images are processed results from ML pipeline (YOLO annotations,
        heatmaps, segmentation masks, etc.). Stored in separate bucket for organization.

        Business rules:
        1. File size must be 1 byte to 500MB
        2. S3 key format: {session_id}/viz_{filename}
        3. Image metadata stored in database
        4. Circuit breaker protects against S3 failures

        Args:
            file_bytes: Image file bytes (max 500MB)
            session_id: Photo processing session UUID
            filename: Filename for visualization (e.g., "detections_annotated.jpg")
            content_type: MIME type (default: image/jpeg)

        Returns:
            S3ImageResponse with S3 key and presigned URL

        Raises:
            ValidationException: If file size is invalid
            S3UploadException: If S3 upload fails
            CircuitBreakerError: If circuit breaker is open

        Example:
            ```python
            service = S3ImageService(repo)
            result = await service.upload_visualization(
                file_bytes=viz_bytes,
                session_id=session_id,
                filename="detections_annotated.jpg"
            )
            print(f"Visualization uploaded: {result.s3_key_original}")
            ```
        """
        # Validate file size
        if not file_bytes or len(file_bytes) == 0:
            raise ValidationException(field="file_bytes", message="File cannot be empty", value=0)

        if len(file_bytes) > 500_000_000:  # 500MB
            raise ValidationException(
                field="file_bytes",
                message="File size exceeds 500MB limit",
                value=len(file_bytes),
            )

        # Build S3 key: {session_id}/viz_{filename}
        s3_key = f"{session_id}/viz_{filename}"

        logger.info(
            "Uploading visualization image to S3",
            s3_key=s3_key,
            bucket=settings.S3_BUCKET_VISUALIZATION,
            file_size=len(file_bytes),
            session_id=str(session_id),
        )

        # Upload to S3 with circuit breaker
        try:
            await self._upload_to_s3(
                s3_key=s3_key,
                file_bytes=file_bytes,
                bucket=settings.S3_BUCKET_VISUALIZATION,
                content_type=content_type,
            )
        except CircuitBreakerError as e:
            logger.error(
                "S3 circuit breaker open - too many failures",
                s3_key=s3_key,
                bucket=settings.S3_BUCKET_VISUALIZATION,
            )
            raise S3UploadException(
                file_name=filename,
                bucket=settings.S3_BUCKET_VISUALIZATION,
                error="S3 service temporarily unavailable (circuit breaker open)",
            ) from e

        # Generate image_id (UUID primary key)
        image_id = uuid.uuid4()

        # Store metadata in database (minimal metadata for visualizations)
        s3_image_data = {
            "image_id": image_id,
            "s3_bucket": settings.S3_BUCKET_VISUALIZATION,
            "s3_key_original": s3_key,
            "content_type": content_type,
            "file_size_bytes": len(file_bytes),
            "width_px": 0,  # Unknown for visualizations (set by ML pipeline)
            "height_px": 0,
            "upload_source": "api",  # Visualizations always uploaded via API
            "status": ProcessingStatusEnum.READY,  # Visualizations are ready immediately
        }

        s3_image = await self.repo.create(s3_image_data)

        # Generate presigned URL
        presigned_url = await self.generate_presigned_url(
            s3_key=s3_key, bucket=settings.S3_BUCKET_VISUALIZATION, expiry_hours=24
        )

        logger.info(
            "Visualization image uploaded successfully",
            image_id=str(image_id),
            s3_key=s3_key,
            bucket=settings.S3_BUCKET_VISUALIZATION,
        )

        return S3ImageResponse.from_model(s3_image, presigned_url=presigned_url)

    async def download_original(self, s3_key: str, bucket: str | None = None) -> bytes:
        """Download image from S3 by key.

        Args:
            s3_key: S3 key for the image
            bucket: S3 bucket name (defaults to demeter-photos-original)

        Returns:
            Image file bytes

        Raises:
            S3UploadException: If S3 download fails (reusing exception for consistency)
            CircuitBreakerError: If circuit breaker is open

        Example:
            ```python
            service = S3ImageService(repo)
            file_bytes = await service.download_original(
                s3_key="session-123/photo.jpg"
            )
            with open("photo.jpg", "wb") as f:
                f.write(file_bytes)
            ```
        """
        bucket = bucket or settings.S3_BUCKET_ORIGINAL

        logger.info("Downloading image from S3", s3_key=s3_key, bucket=bucket)

        try:
            return await self._download_from_s3(s3_key=s3_key, bucket=bucket)
        except CircuitBreakerError as e:
            logger.error(
                "S3 circuit breaker open - too many failures",
                s3_key=s3_key,
                bucket=bucket,
            )
            raise S3UploadException(
                file_name=s3_key,
                bucket=bucket,
                error="S3 service temporarily unavailable (circuit breaker open)",
            ) from e

    async def generate_presigned_url(
        self, s3_key: str, bucket: str | None = None, expiry_hours: int = 24
    ) -> str:
        """Generate presigned URL for browser access to S3 image.

        Presigned URLs allow temporary browser access to private S3 objects without
        exposing AWS credentials. URLs expire after specified hours (default: 24).

        Args:
            s3_key: S3 key for the image
            bucket: S3 bucket name (defaults to demeter-photos-original)
            expiry_hours: Expiry time in hours (default: 24, max: 168 = 7 days)

        Returns:
            Presigned URL string (valid for expiry_hours)

        Raises:
            ValidationException: If expiry_hours is invalid
            S3UploadException: If presigned URL generation fails

        Example:
            ```python
            service = S3ImageService(repo)
            url = await service.generate_presigned_url(
                s3_key="session-123/photo.jpg",
                expiry_hours=24
            )
            print(f"Share this URL: {url}")
            # URL valid for 24 hours
            ```
        """
        bucket = bucket or settings.S3_BUCKET_ORIGINAL

        # Validate expiry_hours (1-168 hours = 7 days max)
        if expiry_hours < 1 or expiry_hours > 168:
            raise ValidationException(
                field="expiry_hours",
                message="Expiry must be 1-168 hours (7 days max)",
                value=expiry_hours,
            )

        logger.info(
            "Generating presigned URL",
            s3_key=s3_key,
            bucket=bucket,
            expiry_hours=expiry_hours,
        )

        try:
            # Run boto3 sync operation in thread pool
            presigned_url = await asyncio.to_thread(
                self.s3_client.generate_presigned_url,
                ClientMethod="get_object",
                Params={"Bucket": bucket, "Key": s3_key},
                ExpiresIn=expiry_hours * 3600,  # Convert hours to seconds
            )

            logger.info(
                "Presigned URL generated",
                s3_key=s3_key,
                bucket=bucket,
                expiry_hours=expiry_hours,
            )

            return presigned_url

        except Exception as e:
            logger.error(
                "Failed to generate presigned URL",
                s3_key=s3_key,
                bucket=bucket,
                error=str(e),
            )
            raise S3UploadException(
                file_name=s3_key,
                bucket=bucket,
                error=f"Failed to generate presigned URL: {str(e)}",
            ) from e

    async def delete_image(self, image_id: uuid.UUID) -> bool:
        """Delete image from S3 and database.

        Business rules:
        1. Delete from S3 first (prevents orphaned database records)
        2. Delete from database second
        3. If S3 delete fails, database record remains (manual cleanup)

        Args:
            image_id: UUID of S3 image to delete

        Returns:
            True if deleted successfully, False if image not found

        Raises:
            S3UploadException: If S3 delete fails

        Example:
            ```python
            service = S3ImageService(repo)
            deleted = await service.delete_image(image_id)
            if deleted:
                print("Image deleted successfully")
            else:
                print("Image not found")
            ```
        """
        # Get image from database
        s3_image = await self.repo.get(image_id)
        if not s3_image:
            logger.warning("S3 image not found for deletion", image_id=str(image_id))
            return False

        logger.info(
            "Deleting S3 image",
            image_id=str(image_id),
            s3_key=s3_image.s3_key_original,
            bucket=s3_image.s3_bucket,
        )

        # Delete from S3 first (prevents orphaned database records)
        try:
            await self._delete_from_s3(s3_key=s3_image.s3_key_original, bucket=s3_image.s3_bucket)
        except CircuitBreakerError as e:
            logger.error(
                "S3 circuit breaker open - cannot delete",
                image_id=str(image_id),
                s3_key=s3_image.s3_key_original,
            )
            raise S3UploadException(
                file_name=s3_image.s3_key_original,
                bucket=s3_image.s3_bucket,
                error="S3 service temporarily unavailable (circuit breaker open)",
            ) from e

        # Delete thumbnail if exists
        if s3_image.s3_key_thumbnail:
            try:
                await self._delete_from_s3(
                    s3_key=s3_image.s3_key_thumbnail, bucket=s3_image.s3_bucket
                )
            except Exception as e:
                # Log but don't fail (thumbnail is optional)
                logger.warning(
                    "Failed to delete thumbnail",
                    image_id=str(image_id),
                    s3_key=s3_image.s3_key_thumbnail,
                    error=str(e),
                )

        # Delete from database
        await self.repo.delete(image_id)

        logger.info("S3 image deleted successfully", image_id=str(image_id))

        return True

    # =========================================================================
    # Private helper methods (S3 operations with circuit breaker)
    # =========================================================================

    @s3_circuit_breaker
    async def _upload_to_s3(
        self, s3_key: str, file_bytes: bytes, bucket: str, content_type: str
    ) -> None:
        """Upload file to S3 with circuit breaker protection.

        This private method is wrapped by pybreaker circuit breaker.
        After 5 consecutive failures, circuit opens for 60 seconds.

        Uses boto3 (sync) with asyncio.to_thread() for async interface.

        Args:
            s3_key: S3 key for the file
            file_bytes: File bytes to upload
            bucket: S3 bucket name
            content_type: MIME type

        Raises:
            S3UploadException: If upload fails
        """
        try:
            # Run boto3 sync operation in thread pool
            await asyncio.to_thread(
                self.s3_client.put_object,
                Bucket=bucket,
                Key=s3_key,
                Body=file_bytes,
                ContentType=content_type,
            )

            logger.debug(
                "S3 upload successful",
                s3_key=s3_key,
                bucket=bucket,
                file_size=len(file_bytes),
            )

        except Exception as e:
            logger.error(
                "S3 upload failed",
                s3_key=s3_key,
                bucket=bucket,
                error=str(e),
                exc_info=True,
            )
            raise S3UploadException(file_name=s3_key, bucket=bucket, error=str(e)) from e

    @s3_circuit_breaker
    async def _download_from_s3(self, s3_key: str, bucket: str) -> bytes:
        """Download file from S3 with circuit breaker protection.

        Uses boto3 (sync) with asyncio.to_thread() for async interface.

        Args:
            s3_key: S3 key for the file
            bucket: S3 bucket name

        Returns:
            File bytes

        Raises:
            S3UploadException: If download fails
        """
        try:
            # Run boto3 sync operation in thread pool
            response = await asyncio.to_thread(self.s3_client.get_object, Bucket=bucket, Key=s3_key)

            # Read body as bytes (sync operation)
            file_bytes = response["Body"].read()

            logger.debug(
                "S3 download successful",
                s3_key=s3_key,
                bucket=bucket,
                file_size=len(file_bytes),
            )

            return file_bytes

        except Exception as e:
            logger.error(
                "S3 download failed",
                s3_key=s3_key,
                bucket=bucket,
                error=str(e),
                exc_info=True,
            )
            raise S3UploadException(
                file_name=s3_key, bucket=bucket, error=f"Download failed: {str(e)}"
            ) from e

    @s3_circuit_breaker
    async def _delete_from_s3(self, s3_key: str, bucket: str) -> None:
        """Delete file from S3 with circuit breaker protection.

        Uses boto3 (sync) with asyncio.to_thread() for async interface.

        Args:
            s3_key: S3 key for the file
            bucket: S3 bucket name

        Raises:
            S3UploadException: If delete fails
        """
        try:
            # Run boto3 sync operation in thread pool
            await asyncio.to_thread(self.s3_client.delete_object, Bucket=bucket, Key=s3_key)

            logger.debug("S3 delete successful", s3_key=s3_key, bucket=bucket)

        except Exception as e:
            logger.error(
                "S3 delete failed",
                s3_key=s3_key,
                bucket=bucket,
                error=str(e),
                exc_info=True,
            )
            raise S3UploadException(
                file_name=s3_key, bucket=bucket, error=f"Delete failed: {str(e)}"
            ) from e
