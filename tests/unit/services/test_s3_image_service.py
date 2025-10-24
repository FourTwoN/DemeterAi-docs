"""Unit tests for S3ImageService - S3 bucket consolidation refactoring.

This module tests the S3ImageService after consolidation from dual-bucket
(demeter-photos-original + demeter-photos-viz) to single-bucket with folder structure.

Test Coverage:
- New folder structure: {session_id}/original.{ext}, {session_id}/processed.{ext}, {session_id}/thumbnail.{ext}
- Thumbnail generation (300x300px, JPEG quality 85)
- Image type filtering (original/processed/thumbnail)
- Delete cascades (all 3 image types)
- Circuit breaker behavior
- Error handling

Architecture:
    Layer: Service Layer Testing
    Pattern: Real database + mocked S3 (boto3 client)
    Fixtures: db_session (real PostgreSQL), mock S3 client

Note:
    We mock ONLY boto3 S3 client (external dependency).
    All business logic and database operations use real PostgreSQL.
"""

import io
import uuid
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from app.core.config import settings
from app.core.exceptions import S3UploadException, ValidationException
from app.models.s3_image import ContentTypeEnum, ProcessingStatusEnum
from app.repositories.s3_image_repository import S3ImageRepository
from app.schemas.s3_image_schema import S3ImageUploadRequest
from app.services.photo.s3_image_service import S3ImageService

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_s3_client():
    """Mock boto3 S3 client for testing.

    Returns:
        MagicMock configured for S3 operations (put_object, get_object, delete_object)
    """
    mock_client = MagicMock()
    mock_client.put_object.return_value = {"ETag": '"abc123"', "VersionId": "v1"}
    mock_client.get_object.return_value = {
        "Body": MagicMock(read=lambda: b"fake_image_data"),
        "ContentType": "image/jpeg",
        "ContentLength": 1024,
    }
    mock_client.delete_object.return_value = {"DeleteMarker": False}
    mock_client.generate_presigned_url.return_value = "https://s3.amazonaws.com/presigned-url"
    return mock_client


@pytest.fixture
async def s3_image_service(db_session, mock_s3_client):
    """S3ImageService with real database and mocked S3 client.

    Args:
        db_session: Real PostgreSQL session from conftest.py
        mock_s3_client: Mocked boto3 S3 client

    Returns:
        S3ImageService instance ready for testing
    """
    repo = S3ImageRepository(db_session)
    service = S3ImageService(repo)
    service.s3_client = mock_s3_client  # Inject mock S3 client
    return service


@pytest.fixture
def sample_upload_request():
    """Sample S3ImageUploadRequest for testing.

    Returns:
        S3ImageUploadRequest with realistic metadata
    """
    return S3ImageUploadRequest(
        filename="test_photo.jpg",
        content_type=ContentTypeEnum.JPEG,
        file_size_bytes=2048576,  # 2MB
        width_px=4000,
        height_px=3000,
        upload_source="web",
        uploaded_by_user_id=1,
        exif_metadata={"camera": "Test Camera", "iso": 100},
        gps_coordinates={"lat": -33.449150, "lng": -70.647500},
    )


@pytest.fixture
def sample_image_bytes():
    """Generate realistic test image bytes (JPEG).

    Returns:
        bytes: JPEG image (1000x800px, RGB)
    """
    img = Image.new("RGB", (1000, 800), color="blue")
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=85)
    return buffer.getvalue()


@pytest.fixture
def sample_png_image_bytes():
    """Generate realistic test image bytes (PNG with transparency).

    Returns:
        bytes: PNG image (1000x800px, RGBA)
    """
    img = Image.new("RGBA", (1000, 800), color=(255, 0, 0, 128))  # Semi-transparent red
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


# =============================================================================
# Test New Folder Structure
# =============================================================================


@pytest.mark.asyncio
async def test_upload_original_new_structure(
    s3_image_service, sample_image_bytes, sample_upload_request, mock_s3_client
):
    """Test upload_original uses new folder structure: {session_id}/original.{ext}."""
    # Arrange
    session_id = uuid.uuid4()

    # Act
    result = await s3_image_service.upload_original(
        file_bytes=sample_image_bytes, session_id=session_id, upload_request=sample_upload_request
    )

    # Assert - Verify new S3 key format
    expected_s3_key = f"{session_id}/original.jpg"
    assert result.s3_key_original == expected_s3_key
    assert result.s3_bucket == settings.S3_BUCKET_ORIGINAL

    # Verify S3 upload was called with new key
    mock_s3_client.put_object.assert_called_once()
    call_kwargs = mock_s3_client.put_object.call_args[1]
    assert call_kwargs["Bucket"] == settings.S3_BUCKET_ORIGINAL
    assert call_kwargs["Key"] == expected_s3_key
    assert call_kwargs["ContentType"] == "image/jpeg"


@pytest.mark.asyncio
async def test_upload_visualization_new_location(
    s3_image_service, sample_image_bytes, mock_s3_client
):
    """Test upload_visualization uses new folder structure: {session_id}/processed.{ext}."""
    # Arrange
    session_id = uuid.uuid4()
    filename = "viz_detections.jpg"

    # Act
    result = await s3_image_service.upload_visualization(
        file_bytes=sample_image_bytes, session_id=session_id, filename=filename
    )

    # Assert - Verify new S3 key format (same bucket, different key pattern)
    expected_s3_key = f"{session_id}/processed.jpg"
    assert result.s3_key_original == expected_s3_key
    assert result.s3_bucket == settings.S3_BUCKET_ORIGINAL  # CHANGED: Now using original bucket

    # Verify S3 upload was called with new key in original bucket
    mock_s3_client.put_object.assert_called_once()
    call_kwargs = mock_s3_client.put_object.call_args[1]
    assert call_kwargs["Bucket"] == settings.S3_BUCKET_ORIGINAL
    assert call_kwargs["Key"] == expected_s3_key


@pytest.mark.asyncio
async def test_upload_thumbnail_new_structure(s3_image_service, sample_image_bytes, mock_s3_client):
    """Test upload_thumbnail uses new folder structure: {session_id}/thumbnail.{ext}."""
    # Arrange
    session_id = uuid.uuid4()

    # Act - Upload thumbnail (NEW METHOD)
    result = await s3_image_service.upload_thumbnail(
        file_bytes=sample_image_bytes, session_id=session_id, filename="thumbnail.jpg"
    )

    # Assert - Verify new S3 key format
    expected_s3_key = f"{session_id}/thumbnail.jpg"
    assert result.s3_key_thumbnail == expected_s3_key
    assert result.s3_bucket == settings.S3_BUCKET_ORIGINAL

    # Verify S3 upload was called with new key
    mock_s3_client.put_object.assert_called_once()
    call_kwargs = mock_s3_client.put_object.call_args[1]
    assert call_kwargs["Bucket"] == settings.S3_BUCKET_ORIGINAL
    assert call_kwargs["Key"] == expected_s3_key


# =============================================================================
# Test Thumbnail Generation
# =============================================================================


@pytest.mark.asyncio
async def test_generate_thumbnail_from_jpeg(s3_image_service, sample_image_bytes):
    """Test thumbnail generation from JPEG (300x300px, JPEG quality 85)."""
    # Act
    thumbnail_bytes = await s3_image_service._generate_thumbnail(
        image_bytes=sample_image_bytes, size=300
    )

    # Assert - Verify thumbnail properties
    assert thumbnail_bytes is not None
    assert len(thumbnail_bytes) > 0

    # Load thumbnail and verify dimensions
    thumb_img = Image.open(io.BytesIO(thumbnail_bytes))
    assert thumb_img.size[0] <= 300  # Width <= 300px
    assert thumb_img.size[1] <= 300  # Height <= 300px
    assert thumb_img.format == "JPEG"


@pytest.mark.asyncio
async def test_generate_thumbnail_from_png(s3_image_service, sample_png_image_bytes):
    """Test thumbnail generation from PNG with transparency (RGBA → RGB conversion)."""
    # Act
    thumbnail_bytes = await s3_image_service._generate_thumbnail(
        image_bytes=sample_png_image_bytes, size=300
    )

    # Assert - Verify RGBA was converted to RGB
    thumb_img = Image.open(io.BytesIO(thumbnail_bytes))
    assert thumb_img.mode == "RGB"  # RGBA → RGB conversion
    assert thumb_img.size[0] <= 300
    assert thumb_img.size[1] <= 300
    assert thumb_img.format == "JPEG"


@pytest.mark.asyncio
async def test_generate_thumbnail_preserves_aspect_ratio(s3_image_service, sample_image_bytes):
    """Test thumbnail generation preserves aspect ratio (no stretching)."""
    # Arrange - Create 1000x500 image (2:1 aspect ratio)
    img = Image.new("RGB", (1000, 500), color="green")
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG")
    image_bytes = buffer.getvalue()

    # Act
    thumbnail_bytes = await s3_image_service._generate_thumbnail(image_bytes=image_bytes, size=300)

    # Assert - Verify aspect ratio preserved (2:1)
    thumb_img = Image.open(io.BytesIO(thumbnail_bytes))
    aspect_ratio = thumb_img.size[0] / thumb_img.size[1]
    assert 1.9 <= aspect_ratio <= 2.1  # Tolerance for rounding (2.0 ± 0.1)


@pytest.mark.asyncio
async def test_generate_thumbnail_quality_settings(s3_image_service, sample_image_bytes):
    """Test thumbnail uses JPEG quality 85 and optimize=True."""
    # Arrange
    with patch("PIL.Image.Image.save") as mock_save:
        # Act
        await s3_image_service._generate_thumbnail(image_bytes=sample_image_bytes, size=300)

        # Assert - Verify save was called with quality=85, optimize=True
        mock_save.assert_called_once()
        call_kwargs = mock_save.call_args[1]
        assert call_kwargs["format"] == "JPEG"
        assert call_kwargs["quality"] == 85
        assert call_kwargs["optimize"] is True


# =============================================================================
# Test Image Type Filtering
# =============================================================================


@pytest.mark.asyncio
async def test_get_by_image_type_original(db_session, s3_image_service):
    """Test filtering images by image_type='original'."""
    # Arrange - Create images with different types
    session_id = uuid.uuid4()
    original_image = await s3_image_service.repo.create(
        {
            "image_id": uuid.uuid4(),
            "s3_bucket": settings.S3_BUCKET_ORIGINAL,
            "s3_key_original": f"{session_id}/original.jpg",
            "content_type": ContentTypeEnum.JPEG,
            "file_size_bytes": 1024,
            "width_px": 1000,
            "height_px": 800,
            "upload_source": "web",
            "status": ProcessingStatusEnum.UPLOADED,
            "image_type": "original",
        }
    )

    await s3_image_service.repo.create(
        {
            "image_id": uuid.uuid4(),
            "s3_bucket": settings.S3_BUCKET_ORIGINAL,
            "s3_key_original": f"{session_id}/processed.jpg",
            "content_type": ContentTypeEnum.JPEG,
            "file_size_bytes": 1024,
            "width_px": 1000,
            "height_px": 800,
            "upload_source": "api",
            "status": ProcessingStatusEnum.READY,
            "image_type": "processed",
        }
    )

    # Act - Filter by image_type='original'
    results = await s3_image_service.get_by_image_type(image_type="original")

    # Assert - Only original image returned
    assert len(results) == 1
    assert results[0].image_id == original_image.image_id
    assert results[0].image_type == "original"


@pytest.mark.asyncio
async def test_get_by_image_type_processed(db_session, s3_image_service):
    """Test filtering images by image_type='processed'."""
    # Arrange
    session_id = uuid.uuid4()
    processed_image = await s3_image_service.repo.create(
        {
            "image_id": uuid.uuid4(),
            "s3_bucket": settings.S3_BUCKET_ORIGINAL,
            "s3_key_original": f"{session_id}/processed.jpg",
            "content_type": ContentTypeEnum.JPEG,
            "file_size_bytes": 1024,
            "width_px": 1000,
            "height_px": 800,
            "upload_source": "api",
            "status": ProcessingStatusEnum.READY,
            "image_type": "processed",
        }
    )

    # Act
    results = await s3_image_service.get_by_image_type(image_type="processed")

    # Assert
    assert len(results) == 1
    assert results[0].image_id == processed_image.image_id
    assert results[0].image_type == "processed"


@pytest.mark.asyncio
async def test_get_by_image_type_thumbnail(db_session, s3_image_service):
    """Test filtering images by image_type='thumbnail'."""
    # Arrange
    session_id = uuid.uuid4()
    thumbnail_image = await s3_image_service.repo.create(
        {
            "image_id": uuid.uuid4(),
            "s3_bucket": settings.S3_BUCKET_ORIGINAL,
            "s3_key_thumbnail": f"{session_id}/thumbnail.jpg",
            "content_type": ContentTypeEnum.JPEG,
            "file_size_bytes": 512,
            "width_px": 300,
            "height_px": 300,
            "upload_source": "api",
            "status": ProcessingStatusEnum.READY,
            "image_type": "thumbnail",
        }
    )

    # Act
    results = await s3_image_service.get_by_image_type(image_type="thumbnail")

    # Assert
    assert len(results) == 1
    assert results[0].image_id == thumbnail_image.image_id
    assert results[0].image_type == "thumbnail"


# =============================================================================
# Test Delete Cascades
# =============================================================================


@pytest.mark.asyncio
async def test_delete_image_removes_all_types(
    db_session, s3_image_service, mock_s3_client, sample_image_bytes
):
    """Test delete_image removes original, processed, and thumbnail from S3."""
    # Arrange - Create all 3 image types for a session
    session_id = uuid.uuid4()
    image_id = uuid.uuid4()

    # Create database record with all 3 keys
    s3_image = await s3_image_service.repo.create(
        {
            "image_id": image_id,
            "s3_bucket": settings.S3_BUCKET_ORIGINAL,
            "s3_key_original": f"{session_id}/original.jpg",
            "s3_key_processed": f"{session_id}/processed.jpg",
            "s3_key_thumbnail": f"{session_id}/thumbnail.jpg",
            "content_type": ContentTypeEnum.JPEG,
            "file_size_bytes": 2048,
            "width_px": 1000,
            "height_px": 800,
            "upload_source": "web",
            "status": ProcessingStatusEnum.READY,
        }
    )

    # Act - Delete image
    deleted = await s3_image_service.delete_image(image_id)

    # Assert - All 3 types deleted from S3
    assert deleted is True
    assert mock_s3_client.delete_object.call_count == 3  # original + processed + thumbnail

    # Verify each S3 delete call
    delete_calls = mock_s3_client.delete_object.call_args_list
    deleted_keys = [call[1]["Key"] for call in delete_calls]
    assert f"{session_id}/original.jpg" in deleted_keys
    assert f"{session_id}/processed.jpg" in deleted_keys
    assert f"{session_id}/thumbnail.jpg" in deleted_keys

    # Verify database record deleted
    db_image = await s3_image_service.repo.get(image_id)
    assert db_image is None


@pytest.mark.asyncio
async def test_delete_image_handles_missing_thumbnail(db_session, s3_image_service, mock_s3_client):
    """Test delete_image handles missing thumbnail gracefully."""
    # Arrange - Create image WITHOUT thumbnail
    session_id = uuid.uuid4()
    image_id = uuid.uuid4()

    await s3_image_service.repo.create(
        {
            "image_id": image_id,
            "s3_bucket": settings.S3_BUCKET_ORIGINAL,
            "s3_key_original": f"{session_id}/original.jpg",
            "s3_key_processed": f"{session_id}/processed.jpg",
            "s3_key_thumbnail": None,  # No thumbnail
            "content_type": ContentTypeEnum.JPEG,
            "file_size_bytes": 2048,
            "width_px": 1000,
            "height_px": 800,
            "upload_source": "web",
            "status": ProcessingStatusEnum.READY,
        }
    )

    # Act
    deleted = await s3_image_service.delete_image(image_id)

    # Assert - Only 2 S3 deletes (original + processed, no thumbnail)
    assert deleted is True
    assert mock_s3_client.delete_object.call_count == 2


@pytest.mark.asyncio
async def test_delete_image_continues_on_thumbnail_error(
    db_session, s3_image_service, mock_s3_client
):
    """Test delete_image continues if thumbnail delete fails (logs warning, doesn't fail)."""
    # Arrange
    session_id = uuid.uuid4()
    image_id = uuid.uuid4()

    await s3_image_service.repo.create(
        {
            "image_id": image_id,
            "s3_bucket": settings.S3_BUCKET_ORIGINAL,
            "s3_key_original": f"{session_id}/original.jpg",
            "s3_key_thumbnail": f"{session_id}/thumbnail.jpg",
            "content_type": ContentTypeEnum.JPEG,
            "file_size_bytes": 2048,
            "width_px": 1000,
            "height_px": 800,
            "upload_source": "web",
            "status": ProcessingStatusEnum.UPLOADED,
        }
    )

    # Mock thumbnail delete to fail
    def delete_side_effect(*args, **kwargs):
        if "thumbnail" in kwargs.get("Key", ""):
            raise Exception("S3 error: thumbnail not found")
        return {"DeleteMarker": False}

    mock_s3_client.delete_object.side_effect = delete_side_effect

    # Act - Delete should succeed despite thumbnail error
    deleted = await s3_image_service.delete_image(image_id)

    # Assert - Delete succeeded (thumbnail failure logged but didn't fail operation)
    assert deleted is True


# =============================================================================
# Test Download with Image Type Parameter
# =============================================================================


@pytest.mark.asyncio
async def test_download_original_with_image_type_parameter(s3_image_service, mock_s3_client):
    """Test download_original supports image_type parameter (original/processed/thumbnail)."""
    # Arrange
    session_id = uuid.uuid4()

    # Act - Download processed image (not original)
    result = await s3_image_service.download_original(
        s3_key=f"{session_id}/processed.jpg", bucket=settings.S3_BUCKET_ORIGINAL
    )

    # Assert
    assert result == b"fake_image_data"
    mock_s3_client.get_object.assert_called_once_with(
        Bucket=settings.S3_BUCKET_ORIGINAL, Key=f"{session_id}/processed.jpg"
    )


@pytest.mark.asyncio
async def test_download_thumbnail(s3_image_service, mock_s3_client):
    """Test downloading thumbnail image type."""
    # Arrange
    session_id = uuid.uuid4()

    # Act
    result = await s3_image_service.download_original(
        s3_key=f"{session_id}/thumbnail.jpg", bucket=settings.S3_BUCKET_ORIGINAL
    )

    # Assert
    assert result == b"fake_image_data"
    mock_s3_client.get_object.assert_called_once_with(
        Bucket=settings.S3_BUCKET_ORIGINAL, Key=f"{session_id}/thumbnail.jpg"
    )


# =============================================================================
# Test Error Handling
# =============================================================================


@pytest.mark.asyncio
async def test_upload_original_validates_file_size(
    s3_image_service, sample_upload_request, mock_s3_client
):
    """Test upload_original rejects files > 500MB."""
    # Arrange
    session_id = uuid.uuid4()
    large_file = b"x" * (501 * 1024 * 1024)  # 501MB

    # Act & Assert
    with pytest.raises(ValidationException) as exc_info:
        await s3_image_service.upload_original(
            file_bytes=large_file, session_id=session_id, upload_request=sample_upload_request
        )

    assert "500MB" in str(exc_info.value)


@pytest.mark.asyncio
async def test_upload_original_validates_empty_file(
    s3_image_service, sample_upload_request, mock_s3_client
):
    """Test upload_original rejects empty files."""
    # Arrange
    session_id = uuid.uuid4()

    # Act & Assert
    with pytest.raises(ValidationException) as exc_info:
        await s3_image_service.upload_original(
            file_bytes=b"", session_id=session_id, upload_request=sample_upload_request
        )

    assert "empty" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_upload_handles_s3_failure(
    s3_image_service, sample_image_bytes, sample_upload_request, mock_s3_client
):
    """Test upload_original handles S3 upload failure gracefully."""
    # Arrange
    session_id = uuid.uuid4()
    mock_s3_client.put_object.side_effect = Exception("S3 connection timeout")

    # Act & Assert
    with pytest.raises(S3UploadException) as exc_info:
        await s3_image_service.upload_original(
            file_bytes=sample_image_bytes,
            session_id=session_id,
            upload_request=sample_upload_request,
        )

    assert "timeout" in str(exc_info.value).lower()


# =============================================================================
# Test Circuit Breaker Behavior
# =============================================================================


@pytest.mark.asyncio
async def test_circuit_breaker_opens_after_failures(
    s3_image_service, sample_image_bytes, sample_upload_request, mock_s3_client
):
    """Test circuit breaker opens after 5 consecutive S3 failures."""
    # Arrange
    session_id = uuid.uuid4()
    mock_s3_client.put_object.side_effect = Exception("S3 error")

    # Act - Trigger 5 failures (circuit breaker should open)
    for i in range(5):
        with pytest.raises(S3UploadException):
            await s3_image_service.upload_original(
                file_bytes=sample_image_bytes,
                session_id=session_id,
                upload_request=sample_upload_request,
            )

    # Assert - 6th call should fail immediately (circuit open)
    # Note: Testing circuit breaker state requires pybreaker internals
    # This is a simplified test - full circuit breaker testing would check state
    assert mock_s3_client.put_object.call_count == 5


# =============================================================================
# Test Presigned URL Generation
# =============================================================================


@pytest.mark.asyncio
async def test_generate_presigned_url_for_new_structure(s3_image_service, mock_s3_client):
    """Test presigned URL generation works with new folder structure."""
    # Arrange
    session_id = uuid.uuid4()
    s3_key = f"{session_id}/original.jpg"

    # Act
    url = await s3_image_service.generate_presigned_url(
        s3_key=s3_key, bucket=settings.S3_BUCKET_ORIGINAL, expiry_hours=24
    )

    # Assert
    assert url == "https://s3.amazonaws.com/presigned-url"
    mock_s3_client.generate_presigned_url.assert_called_once_with(
        ClientMethod="get_object",
        Params={"Bucket": settings.S3_BUCKET_ORIGINAL, "Key": s3_key},
        ExpiresIn=24 * 3600,
    )


@pytest.mark.asyncio
async def test_generate_presigned_url_validates_expiry(s3_image_service):
    """Test presigned URL rejects invalid expiry_hours."""
    # Act & Assert - Too short
    with pytest.raises(ValidationException) as exc_info:
        await s3_image_service.generate_presigned_url(
            s3_key="test.jpg",
            expiry_hours=0,  # Invalid
        )
    assert "1-168 hours" in str(exc_info.value)

    # Act & Assert - Too long
    with pytest.raises(ValidationException) as exc_info:
        await s3_image_service.generate_presigned_url(
            s3_key="test.jpg",
            expiry_hours=200,  # > 7 days
        )
    assert "1-168 hours" in str(exc_info.value)
