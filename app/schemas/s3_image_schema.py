"""S3 Image Pydantic schemas for photo upload and management.

This module provides request/response schemas for S3 image operations including
upload, download, and presigned URL generation.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.s3_image import ContentTypeEnum, ProcessingStatusEnum, UploadSourceEnum


class S3ImageUploadRequest(BaseModel):
    """Request schema for uploading images to S3.

    Attributes:
        session_id: UUID of photo processing session
        filename: Original filename (e.g., "photo_123.jpg")
        content_type: MIME type (image/jpeg or image/png)
        file_size_bytes: File size in bytes (max 500MB)
        width_px: Image width in pixels
        height_px: Image height in pixels
        upload_source: Upload source (web, mobile, api)
        uploaded_by_user_id: User ID who uploaded the image (optional)
        exif_metadata: EXIF data from camera (optional)
        gps_coordinates: GPS coordinates {lat, lng, altitude, accuracy} (optional)
    """

    session_id: UUID = Field(..., description="Photo processing session UUID")
    filename: str = Field(..., min_length=1, max_length=255, description="Original filename")
    content_type: ContentTypeEnum = Field(..., description="Image MIME type")
    file_size_bytes: int = Field(..., gt=0, le=500_000_000, description="File size (max 500MB)")
    width_px: int = Field(..., gt=0, description="Image width in pixels")
    height_px: int = Field(..., gt=0, description="Image height in pixels")
    upload_source: UploadSourceEnum = Field(
        default=UploadSourceEnum.WEB, description="Upload source"
    )
    uploaded_by_user_id: int | None = Field(default=None, description="User ID (optional)")
    exif_metadata: dict[str, Any] | None = Field(default=None, description="EXIF camera metadata")
    gps_coordinates: dict[str, Any] | None = Field(
        default=None, description="GPS coordinates {lat, lng, altitude, accuracy}"
    )


class S3ImageResponse(BaseModel):
    """Response schema for S3 image operations.

    Attributes:
        image_id: UUID primary key
        s3_bucket: S3 bucket name
        s3_key_original: S3 key for original image
        s3_key_thumbnail: S3 key for thumbnail (optional)
        content_type: Image MIME type
        file_size_bytes: File size in bytes
        width_px: Image width in pixels
        height_px: Image height in pixels
        status: Processing status (uploaded, processing, ready, failed)
        upload_source: Upload source (web, mobile, api)
        uploaded_by_user_id: User ID who uploaded (optional)
        presigned_url: Presigned URL for browser access (optional, generated on demand)
        created_at: Record creation timestamp
        updated_at: Last update timestamp
    """

    image_id: UUID
    s3_bucket: str
    s3_key_original: str
    s3_key_thumbnail: str | None = None
    content_type: ContentTypeEnum
    file_size_bytes: int
    width_px: int
    height_px: int
    status: ProcessingStatusEnum
    upload_source: UploadSourceEnum
    uploaded_by_user_id: int | None = None
    presigned_url: str | None = Field(
        default=None, description="Presigned URL (generated on demand)"
    )
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_model(cls, model: Any, presigned_url: str | None = None) -> "S3ImageResponse":
        """Create response from SQLAlchemy model with optional presigned URL.

        Args:
            model: S3Image SQLAlchemy model
            presigned_url: Optional presigned URL for browser access

        Returns:
            S3ImageResponse with data from model
        """
        data = {
            "image_id": model.image_id,
            "s3_bucket": model.s3_bucket,
            "s3_key_original": model.s3_key_original,
            "s3_key_thumbnail": model.s3_key_thumbnail,
            "content_type": model.content_type,
            "file_size_bytes": model.file_size_bytes,
            "width_px": model.width_px,
            "height_px": model.height_px,
            "status": model.status,
            "upload_source": model.upload_source,
            "uploaded_by_user_id": model.uploaded_by_user_id,
            "created_at": model.created_at,
            "updated_at": model.updated_at,
            "presigned_url": presigned_url,
        }
        return cls(**data)


class PresignedUrlRequest(BaseModel):
    """Request schema for generating presigned URLs.

    Attributes:
        s3_key: S3 key for the image
        expiry_hours: Expiry time in hours (default: 24, max: 168 = 7 days)
    """

    s3_key: str = Field(..., min_length=1, max_length=512, description="S3 key")
    expiry_hours: int = Field(default=24, ge=1, le=168, description="Expiry in hours (max 7 days)")


class PresignedUrlResponse(BaseModel):
    """Response schema for presigned URL generation.

    Attributes:
        s3_key: S3 key for the image
        presigned_url: Generated presigned URL
        expires_in_hours: Expiry time in hours
    """

    s3_key: str
    presigned_url: str
    expires_in_hours: int
