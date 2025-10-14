"""S3Image model - S3 uploaded image metadata with UUID primary key.

This module defines the S3Image SQLAlchemy model for storing metadata about
images uploaded to S3. Uses UUID primary key (generated in API layer) to enable
S3 key pre-generation before database insertion. This is the foundation of the
photo processing ML pipeline.

Architecture:
    Layer: Database / Models (Infrastructure Layer)
    Dependencies: SQLAlchemy 2.0, PostgreSQL 18
    Pattern: UUID primary key for S3 key generation

Design Decisions:
    - UUID primary key: Generated in API layer BEFORE S3 upload (NOT database default)
    - S3 key pattern: original/{image_id}.jpg, thumbnail/{image_id}_thumb.jpg
    - JSONB for EXIF metadata: Flexible schema for camera settings
    - JSONB for GPS coordinates: {lat, lng, altitude, accuracy}
    - GPS validation: lat [-90, +90], lng [-180, +180]
    - File size validation: Max 500MB (BigInteger for large files > 4GB)
    - Content type enum: image/jpeg, image/png
    - Upload source enum: web, mobile, api
    - Processing status enum: uploaded, processing, ready, failed
    - Unique constraint on s3_key_original: Prevent duplicate uploads
    - CASCADE delete: Delete image → delete photo sessions and product samples
    - SET NULL on user delete: Preserve image if user is deleted

See:
    - Database ERD: ../../database/database.mmd (lines 227-245)
    - Database docs: ../../engineering_plan/database/README.md
    - Mini-plan: ../../backlog/03_kanban/01_ready/DB011-MINI-PLAN.md

UUID Generation Pattern:
    ```python
    # API layer generates UUID BEFORE S3 upload
    from uuid import uuid4

    image_id = uuid4()  # Generate UUID first
    s3_key = f"original/{image_id}.jpg"  # Use in S3 key

    # Upload to S3 with UUID-based key
    await S3Service.upload(file, key=s3_key)

    # Insert to database with pre-generated UUID
    s3_image = S3Image(
        image_id=image_id,  # EXPLICIT UUID (not database default)
        s3_bucket="demeter-photos",
        s3_key_original=s3_key,
        content_type="image/jpeg",
        file_size_bytes=file.size,
        width_px=4000,
        height_px=3000,
        uploaded_by_user_id=user_id,
        status="uploaded"
    )
    await session.add(s3_image)
    ```

Example:
    ```python
    from uuid import uuid4
    from geoalchemy2.functions import ST_SetSRID, ST_MakePoint

    # Create S3 image with GPS coordinates
    image_id = uuid4()

    image = S3Image(
        image_id=image_id,
        s3_bucket="demeter-photos",
        s3_key_original=f"original/{image_id}.jpg",
        s3_key_thumbnail=f"thumbnail/{image_id}_thumb.jpg",
        content_type="image/jpeg",
        file_size_bytes=2048576,  # 2MB
        width_px=4000,
        height_px=3000,
        exif_metadata={
            "camera": "iPhone 13 Pro",
            "iso": 100,
            "shutter_speed": "1/120",
            "f_stop": "f/1.8"
        },
        gps_coordinates={
            "lat": -33.449150,
            "lng": -70.647500,
            "altitude": 570.5,
            "accuracy": 10.0
        },
        upload_source="mobile",
        uploaded_by_user_id=1,
        status="uploaded"
    )
    ```
"""

import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, relationship, validates
from sqlalchemy.sql import func

from app.db.base import Base

# Forward declarations for type hints (avoids circular imports)
if TYPE_CHECKING:
    from app.models.user import User
    # NOTE: Uncomment after DB012 (PhotoProcessingSession) is complete
    # from app.models.photo_processing_session import PhotoProcessingSession
    # NOTE: Uncomment after DB020 (ProductSampleImage) is complete
    # from app.models.product_sample_image import ProductSampleImage


# Enum definitions (will be created in migration as PostgreSQL ENUMs)


class ContentTypeEnum(str, enum.Enum):
    """Image content type enum.

    Supported formats:
        - JPEG: image/jpeg (most common, high compression)
        - PNG: image/png (lossless, transparency support)

    Note: This is a Python enum for type hints. The actual database ENUM
    is created in the migration file.
    """

    JPEG = "image/jpeg"
    PNG = "image/png"


class UploadSourceEnum(str, enum.Enum):
    """Image upload source enum.

    Upload sources:
        - WEB: Desktop web application
        - MOBILE: Mobile app (iOS/Android)
        - API: Direct API upload

    Note: This is a Python enum for type hints. The actual database ENUM
    is created in the migration file.
    """

    WEB = "web"
    MOBILE = "mobile"
    API = "api"


class ProcessingStatusEnum(str, enum.Enum):
    """Image processing status enum.

    Processing workflow:
        - UPLOADED: Image uploaded to S3, ready for ML processing
        - PROCESSING: ML pipeline is processing the image
        - READY: ML processing complete, results available
        - FAILED: ML processing failed (see error_details)

    Note: This is a Python enum for type hints. The actual database ENUM
    is created in the migration file.
    """

    UPLOADED = "uploaded"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class S3Image(Base):
    """S3Image model representing uploaded images with S3 metadata.

    Foundation of the photo processing ML pipeline. Uses UUID primary key
    generated in API layer BEFORE S3 upload to enable idempotent uploads
    and S3 key pre-generation.

    UUID Generation Pattern:
        1. API generates UUID first (NOT database)
        2. API uploads to S3 using UUID in key (e.g., "original/{uuid}.jpg")
        3. API inserts to database with pre-generated UUID
        4. If upload fails, retry with same UUID (idempotent)

    Key Features:
        - UUID primary key: API-generated for S3 key generation
        - S3 storage tracking: bucket, original key, thumbnail key
        - EXIF metadata: JSONB with camera settings (ISO, shutter, etc.)
        - GPS coordinates: JSONB with lat/lng/altitude/accuracy
        - GPS validation: lat [-90, +90], lng [-180, +180]
        - File size validation: Max 500MB (BigInteger for large files)
        - Content type enum: image/jpeg, image/png
        - Upload source enum: web, mobile, api
        - Processing status enum: uploaded, processing, ready, failed

    Attributes:
        image_id: UUID primary key (API-generated, NOT database default)
        s3_bucket: S3 bucket name (e.g., "demeter-photos")
        s3_key_original: S3 key for original image (unique, indexed)
        s3_key_thumbnail: S3 key for thumbnail (nullable)
        content_type: Image MIME type (image/jpeg, image/png)
        file_size_bytes: File size in bytes (BigInteger for large files > 4GB)
        width_px: Image width in pixels
        height_px: Image height in pixels
        exif_metadata: JSONB with camera settings (camera, ISO, shutter, f-stop)
        gps_coordinates: JSONB with {lat, lng, altitude, accuracy}
        upload_source: Upload source (web, mobile, api)
        uploaded_by_user_id: FK to User (nullable, SET NULL on delete)
        status: Processing status (uploaded, processing, ready, failed)
        error_details: Error message if status = failed (nullable)
        processing_status_updated_at: Timestamp of last status change (nullable)
        created_at: Record creation timestamp (auto)
        updated_at: Last update timestamp (auto)

    Relationships:
        uploaded_by_user: User who uploaded the image (many-to-one, nullable)
        photo_processing_sessions: Photo sessions using this image (one-to-many)
        product_sample_images: Product samples using this image (one-to-many)

    Indexes:
        - B-tree index on status (filter by processing status)
        - B-tree index on created_at DESC (recent images first)
        - B-tree index on uploaded_by_user_id (user's uploads)
        - GIN index on gps_coordinates (spatial JSONB queries)

    Constraints:
        - image_id primary key (UUID)
        - s3_key_original unique constraint
        - GPS coordinates validation (lat/lng bounds)
        - File size validation (max 500MB)

    Example:
        ```python
        from uuid import uuid4

        # API layer generates UUID
        image_id = uuid4()

        # Create image with GPS
        image = S3Image(
            image_id=image_id,  # EXPLICIT UUID
            s3_bucket="demeter-photos",
            s3_key_original=f"original/{image_id}.jpg",
            content_type="image/jpeg",
            file_size_bytes=2048576,
            width_px=4000,
            height_px=3000,
            gps_coordinates={
                "lat": -33.449150,
                "lng": -70.647500,
                "altitude": 570.5,
                "accuracy": 10.0
            },
            upload_source="mobile",
            uploaded_by_user_id=1,
            status="uploaded"
        )
        ```
    """

    __tablename__ = "s3_images"

    # UUID primary key (API-generated, NOT database default)
    # NOTE: default=uuid.uuid4 is a FALLBACK ONLY - API should set explicitly
    image_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,  # Fallback only (should be set explicitly)
        comment="UUID primary key (API-generated, not database default)",
    )

    # S3 storage paths
    s3_bucket = Column(
        String(255),
        nullable=False,
        comment='S3 bucket name (e.g., "demeter-photos")',
    )

    s3_key_original = Column(
        String(512),
        unique=True,
        nullable=False,
        comment="S3 key for original image (unique, indexed)",
    )

    s3_key_thumbnail = Column(
        String(512),
        nullable=True,
        comment="S3 key for thumbnail image (nullable)",
    )

    # File metadata
    content_type = Column(
        Enum(ContentTypeEnum, name="content_type_enum"),
        nullable=False,
        comment="Image MIME type (image/jpeg, image/png)",
    )

    file_size_bytes = Column(
        BigInteger,
        nullable=False,
        comment="File size in bytes (BigInteger for large files > 4GB)",
    )

    width_px = Column(
        Integer,
        nullable=False,
        comment="Image width in pixels",
    )

    height_px = Column(
        Integer,
        nullable=False,
        comment="Image height in pixels",
    )

    # EXIF metadata (JSON)
    exif_metadata = Column(
        JSONB,
        nullable=True,
        comment="EXIF metadata (camera, ISO, shutter speed, f-stop, etc.)",
    )

    # GPS coordinates (for storage location matching)
    gps_coordinates = Column(
        JSONB,
        nullable=True,
        comment="GPS coordinates {lat, lng, altitude, accuracy} for location matching",
    )

    # Upload tracking
    upload_source = Column(
        Enum(UploadSourceEnum, name="upload_source_enum"),
        nullable=False,
        default=UploadSourceEnum.WEB,
        comment="Upload source (web, mobile, api)",
    )

    uploaded_by_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,  # Anonymous uploads allowed
        index=True,
        comment="User who uploaded the image (nullable, SET NULL on delete)",
    )

    # Processing status
    status = Column(
        Enum(ProcessingStatusEnum, name="processing_status_enum"),
        nullable=False,
        default=ProcessingStatusEnum.UPLOADED,
        index=True,
        comment="Processing status (uploaded, processing, ready, failed)",
    )

    error_details = Column(
        Text,
        nullable=True,
        comment="Error message if status = failed (nullable)",
    )

    processing_status_updated_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp of last status change (nullable)",
    )

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Record creation timestamp",
    )

    updated_at = Column(
        DateTime(timezone=True),
        onupdate=func.now(),
        nullable=True,
        comment="Last update timestamp",
    )

    # Relationships

    # Many-to-one: S3Image → User (uploaded_by)
    uploaded_by_user: Mapped["User | None"] = relationship(
        "User",
        # NOTE: Uncomment after User model is updated with back_populates
        # back_populates="uploaded_images",
        foreign_keys=[uploaded_by_user_id],
        doc="User who uploaded the image (nullable, SET NULL on delete)",
    )

    # One-to-many: S3Image → PhotoProcessingSession (COMMENT OUT - DB012 not ready)
    # NOTE: Uncomment after DB012 (PhotoProcessingSession) is complete
    # photo_processing_sessions: Mapped[list["PhotoProcessingSession"]] = relationship(
    #     "PhotoProcessingSession",
    #     back_populates="source_image",
    #     foreign_keys="PhotoProcessingSession.original_image_id",
    #     cascade="all, delete-orphan",
    #     doc="Photo processing sessions using this image as source"
    # )

    # One-to-many: S3Image → ProductSampleImage (COMMENT OUT - DB020 not ready)
    # NOTE: Uncomment after DB020 (ProductSampleImage) is complete
    # product_sample_images: Mapped[list["ProductSampleImage"]] = relationship(
    #     "ProductSampleImage",
    #     back_populates="image",
    #     foreign_keys="ProductSampleImage.image_id",
    #     cascade="all, delete-orphan",
    #     doc="Product sample images using this S3 image"
    # )

    # Table constraints
    __table_args__ = ({"comment": "S3 Images - Uploaded image metadata with UUID primary key"},)

    @validates("gps_coordinates")
    def validate_gps(self, key: str, value: dict[str, float] | None) -> dict[str, float] | None:
        """Validate GPS coordinates format and bounds.

        Rules:
            - Format: dict with {lat, lng, altitude?, accuracy?}
            - Latitude: -90 to +90 degrees
            - Longitude: -180 to +180 degrees
            - Altitude and accuracy: optional

        Args:
            key: Column name (always 'gps_coordinates')
            value: GPS coordinates dict to validate (nullable)

        Returns:
            Validated GPS coordinates dict

        Raises:
            ValueError: If validation fails with specific error message

        Examples:
            >>> image.gps_coordinates = {"lat": -33.449150, "lng": -70.647500}
            >>> image.gps_coordinates
            {"lat": -33.449150, "lng": -70.647500}

            >>> image.gps_coordinates = {"lat": 100, "lng": 0}
            ValueError: Latitude must be -90 to +90, got 100

            >>> image.gps_coordinates = {"lat": 0, "lng": 200}
            ValueError: Longitude must be -180 to +180, got 200

            >>> image.gps_coordinates = None
            >>> image.gps_coordinates
            None
        """
        if value is None:
            return None

        if not isinstance(value, dict):
            raise ValueError("gps_coordinates must be a dict")

        lat = value.get("lat")
        lng = value.get("lng")

        # Validate latitude bounds
        if lat is not None:
            if not isinstance(lat, int | float):
                raise ValueError(f"Latitude must be a number, got {type(lat).__name__}")
            if not (-90 <= lat <= 90):
                raise ValueError(f"Latitude must be -90 to +90, got {lat}")

        # Validate longitude bounds
        if lng is not None:
            if not isinstance(lng, int | float):
                raise ValueError(f"Longitude must be a number, got {type(lng).__name__}")
            if not (-180 <= lng <= 180):
                raise ValueError(f"Longitude must be -180 to +180, got {lng}")

        return value

    @validates("file_size_bytes")
    def validate_file_size(self, key: str, value: int) -> int:
        """Validate file size (max 500MB).

        Rules:
            - Max size: 500MB (500 * 1024 * 1024 bytes)
            - Must be positive integer

        Args:
            key: Column name (always 'file_size_bytes')
            value: File size in bytes to validate

        Returns:
            Validated file size in bytes

        Raises:
            ValueError: If validation fails with specific error message

        Examples:
            >>> image.file_size_bytes = 2048576  # 2MB
            >>> image.file_size_bytes
            2048576

            >>> image.file_size_bytes = 600 * 1024 * 1024  # 600MB
            ValueError: File size 629145600 exceeds max 524288000 (500MB)

            >>> image.file_size_bytes = -100
            ValueError: File size must be positive, got -100
        """
        max_size = 500 * 1024 * 1024  # 500MB

        if value <= 0:
            raise ValueError(f"File size must be positive, got {value}")

        if value > max_size:
            raise ValueError(f"File size {value} exceeds max {max_size} (500MB)")

        return value

    def __repr__(self) -> str:
        """String representation for debugging.

        Returns:
            String with image_id, s3_key_original, and status

        Example:
            <S3Image(image_id=UUID('123e4567-e89b-12d3-a456-426614174000'),
             s3_key='original/123e4567-e89b-12d3-a456-426614174000.jpg',
             status='uploaded')>
        """
        status_value = (
            self.status.value if isinstance(self.status, ProcessingStatusEnum) else self.status
        )
        return (
            f"<S3Image("
            f"image_id={self.image_id}, "
            f"s3_key='{self.s3_key_original}', "
            f"status='{status_value}'"
            f")>"
        )
