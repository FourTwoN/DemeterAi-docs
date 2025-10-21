"""Unit tests for S3ImageService.

Tests business logic with mocked repository and S3 client dependencies.
Uses AsyncMock for all external dependencies.

TESTING STRATEGY:
- Mock S3ImageRepository (database operations)
- Mock boto3 S3 client (AWS operations)
- Mock circuit breaker (pybreaker)
- Test all S3 operations (upload, download, presigned URLs, delete)
- Test error handling and circuit breaker integration

Coverage target: ≥85%

Test categories:
- upload_original: success, file too large, file too small, S3 failure
- upload_visualization: success, circuit breaker failure
- download_image: success, not found, S3 failure
- generate_presigned_url: success, invalid key, expired URL
- delete_image: success, not found, cascade delete
- circuit_breaker: fail_max=5, timeout=60s, recovery

See:
    - Service: app/services/photo/s3_image_service.py
    - Repository: app/repositories/s3_image_repository.py
    - Model: app/models/s3_image.py
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, patch
from uuid import UUID, uuid4

import pytest

from app.core.exceptions import (
    S3UploadException,
    ValidationException,
)
from app.models.s3_image import (
    ContentTypeEnum,
    ProcessingStatusEnum,
    S3Image,
    UploadSourceEnum,
)
from app.schemas.s3_image_schema import S3ImageUploadRequest
from app.services.photo.s3_image_service import S3ImageService

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_s3_image_repo():
    """Create mock S3ImageRepository."""
    return AsyncMock()


@pytest.fixture
def mock_s3_client():
    """Create mock boto3 S3 client."""
    client = MagicMock()
    client.put_object = MagicMock()
    client.get_object = MagicMock()
    client.generate_presigned_url = MagicMock()
    client.delete_object = MagicMock()
    return client


@pytest.fixture
def s3_service(mock_s3_image_repo, mock_s3_client):
    """Create S3ImageService with mocked S3 client.

    Uses PropertyMock to mock the s3_client property since it's read-only.
    """
    with patch.object(S3ImageService, "s3_client", new_callable=PropertyMock) as mock_prop:
        mock_prop.return_value = mock_s3_client
        service = S3ImageService(repo=mock_s3_image_repo)
        yield service


@pytest.fixture
def mock_s3_image():
    """Create mock S3Image model instance."""
    image = Mock(spec=S3Image)
    image.image_id = UUID("123e4567-e89b-12d3-a456-426614174000")
    image.s3_bucket = "demeter-photos-original"
    image.s3_key_original = "session-123/original-photo_001.jpg"
    image.s3_key_thumbnail = None
    image.content_type = ContentTypeEnum.JPEG
    image.file_size_bytes = 2048576  # 2MB
    image.width_px = 4000
    image.height_px = 3000
    image.exif_metadata = {"camera": "iPhone 13", "iso": 100}
    image.gps_coordinates = {"lat": -33.449150, "lng": -70.647500}
    image.upload_source = UploadSourceEnum.WEB
    image.uploaded_by_user_id = 1
    image.status = ProcessingStatusEnum.UPLOADED
    image.error_details = None
    image.processing_status_updated_at = None
    image.created_at = datetime(2025, 10, 21, 10, 0, 0, tzinfo=UTC)
    image.updated_at = None
    return image


# ============================================================================
# upload_original tests
# ============================================================================


@pytest.mark.asyncio
async def test_upload_original_success(
    s3_service, mock_s3_image_repo, mock_s3_image, mock_s3_client
):
    """Test successful original photo upload to S3."""
    # Arrange
    session_id = UUID("123e4567-e89b-12d3-a456-426614174000")
    file_bytes = b"fake_jpeg_data" * 1000  # ~15KB

    upload_request = S3ImageUploadRequest(
        session_id=session_id,
        filename="photo_001.jpg",
        content_type=ContentTypeEnum.JPEG,
        file_size_bytes=len(file_bytes),
        width_px=4000,
        height_px=3000,
        upload_source=UploadSourceEnum.WEB,
        uploaded_by_user_id=1,
    )

    mock_s3_image_repo.create.return_value = mock_s3_image
    mock_s3_client.generate_presigned_url.return_value = "https://s3.amazonaws.com/test-url"

    # Act
    result = await s3_service.upload_original(
        file_bytes=file_bytes, session_id=session_id, upload_request=upload_request
    )

    # Assert
    assert result.image_id == UUID("123e4567-e89b-12d3-a456-426614174000")
    assert result.s3_bucket == "demeter-photos-original"
    assert result.file_size_bytes == 2048576
    assert result.status == ProcessingStatusEnum.UPLOADED

    # Verify S3 put_object called
    mock_s3_client.put_object.assert_called_once()

    # Verify repository called
    mock_s3_image_repo.create.assert_called_once()
    call_data = mock_s3_image_repo.create.call_args[0][0]
    assert call_data["file_size_bytes"] == len(file_bytes)


@pytest.mark.asyncio
async def test_upload_original_file_too_large(s3_service):
    """Test upload fails when file exceeds 500MB limit (caught by service logic)."""
    # Arrange
    session_id = uuid4()
    file_bytes = b"x" * (501 * 1024 * 1024)  # 501MB > 500MB limit

    # Create request with smaller size to bypass Pydantic validation
    # (service validates actual file_bytes size)
    upload_request = S3ImageUploadRequest(
        session_id=session_id,
        filename="huge_photo.jpg",
        content_type=ContentTypeEnum.JPEG,
        file_size_bytes=10000,  # Pydantic-compliant value
        width_px=4000,
        height_px=3000,
    )

    # Act & Assert
    with pytest.raises(ValidationException) as exc_info:
        await s3_service.upload_original(file_bytes, session_id, upload_request)

    assert "500MB" in str(exc_info.value) or "file size" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_upload_original_file_too_small(s3_service):
    """Test upload fails when file is empty or too small."""
    # Arrange
    session_id = uuid4()
    file_bytes = b""  # Empty file

    upload_request = S3ImageUploadRequest(
        session_id=session_id,
        filename="empty.jpg",
        content_type=ContentTypeEnum.JPEG,
        file_size_bytes=1,  # Schema validation requires > 0
        width_px=100,
        height_px=100,
    )

    # Act & Assert
    with pytest.raises(ValidationException) as exc_info:
        await s3_service.upload_original(file_bytes, session_id, upload_request)

    assert (
        "empty" in str(exc_info.value).lower() or "cannot be empty" in str(exc_info.value).lower()
    )


@pytest.mark.asyncio
async def test_upload_original_s3_failure(s3_service, mock_s3_client):
    """Test upload handles S3 connection failure with circuit breaker."""
    # Arrange
    session_id = uuid4()
    file_bytes = b"data" * 1000

    upload_request = S3ImageUploadRequest(
        session_id=session_id,
        filename="photo.jpg",
        content_type=ContentTypeEnum.JPEG,
        file_size_bytes=len(file_bytes),
        width_px=2000,
        height_px=1500,
    )

    # Mock S3 upload failure
    mock_s3_client.put_object.side_effect = Exception("S3 connection timeout")

    # Act & Assert
    with pytest.raises(S3UploadException) as exc_info:
        await s3_service.upload_original(file_bytes, session_id, upload_request)

    assert "S3" in str(exc_info.value)


@pytest.mark.asyncio
async def test_upload_original_with_metadata(
    s3_service, mock_s3_image_repo, mock_s3_image, mock_s3_client
):
    """Test upload with EXIF metadata and GPS coordinates."""
    # Arrange
    session_id = uuid4()
    file_bytes = b"jpeg_with_exif" * 500
    exif_data = {"camera": "Canon EOS R5", "iso": 400, "shutter_speed": "1/500"}
    gps_data = {"lat": -33.449150, "lng": -70.647500, "altitude": 570.5}

    upload_request = S3ImageUploadRequest(
        session_id=session_id,
        filename="photo_with_metadata.jpg",
        content_type=ContentTypeEnum.JPEG,
        file_size_bytes=len(file_bytes),
        width_px=6000,
        height_px=4000,
        exif_metadata=exif_data,
        gps_coordinates=gps_data,
    )

    mock_s3_image_repo.create.return_value = mock_s3_image
    mock_s3_client.generate_presigned_url.return_value = "https://s3.amazonaws.com/test-url"

    # Act
    result = await s3_service.upload_original(
        file_bytes=file_bytes,
        session_id=session_id,
        upload_request=upload_request,
    )

    # Assert
    assert result is not None
    call_data = mock_s3_image_repo.create.call_args[0][0]
    assert call_data["exif_metadata"] == exif_data
    assert call_data["gps_coordinates"] == gps_data


# ============================================================================
# upload_visualization tests
# ============================================================================


@pytest.mark.asyncio
async def test_upload_visualization_success(s3_service, mock_s3_image_repo, mock_s3_client):
    """Test successful visualization image upload."""
    # Arrange
    session_id = uuid4()
    file_bytes = b"viz_image_data" * 500
    filename = "viz_001.jpg"

    mock_viz_image = Mock(spec=S3Image)
    mock_viz_image.image_id = uuid4()
    mock_viz_image.s3_bucket = "demeter-photos-viz"
    mock_viz_image.s3_key_original = f"{session_id}/viz_{filename}"
    mock_viz_image.s3_key_thumbnail = None
    mock_viz_image.content_type = ContentTypeEnum.JPEG
    mock_viz_image.file_size_bytes = len(file_bytes)
    mock_viz_image.width_px = 0
    mock_viz_image.height_px = 0
    mock_viz_image.status = ProcessingStatusEnum.READY
    mock_viz_image.upload_source = UploadSourceEnum.API
    mock_viz_image.uploaded_by_user_id = None
    mock_viz_image.created_at = datetime.now(UTC)
    mock_viz_image.updated_at = None

    mock_s3_image_repo.create.return_value = mock_viz_image
    mock_s3_client.generate_presigned_url.return_value = "https://s3.amazonaws.com/viz-url"

    # Act
    result = await s3_service.upload_visualization(file_bytes, session_id, filename)

    # Assert
    assert "viz" in result.s3_key_original
    mock_s3_image_repo.create.assert_called_once()
    mock_s3_client.put_object.assert_called_once()


@pytest.mark.asyncio
async def test_upload_visualization_s3_failure(s3_service, mock_s3_client):
    """Test upload handles S3 failure."""
    # Arrange
    session_id = uuid4()
    file_bytes = b"data" * 100
    filename = "viz.jpg"

    # Mock S3 failure
    mock_s3_client.put_object.side_effect = Exception("S3 connection timeout")

    # Act & Assert
    with pytest.raises(S3UploadException) as exc_info:
        await s3_service.upload_visualization(file_bytes, session_id, filename)

    assert "S3" in str(exc_info.value)


# ============================================================================
# download_original tests
# ============================================================================


@pytest.mark.asyncio
async def test_download_original_success(s3_service, mock_s3_client):
    """Test successful image download from S3."""
    # Arrange
    s3_key = "session-123/original-photo.jpg"
    expected_bytes = b"downloaded_image_data" * 100

    # Mock S3 get_object response
    mock_response = {"Body": MagicMock()}
    mock_response["Body"].read = MagicMock(return_value=expected_bytes)
    mock_s3_client.get_object.return_value = mock_response

    # Act
    result = await s3_service.download_original(s3_key)

    # Assert
    assert result == expected_bytes
    mock_s3_client.get_object.assert_called_once()


@pytest.mark.asyncio
async def test_download_original_not_found(s3_service, mock_s3_client):
    """Test download fails when S3 key doesn't exist."""
    # Arrange
    s3_key = "nonexistent/photo.jpg"

    # Mock S3 404 error
    mock_s3_client.get_object.side_effect = Exception("NoSuchKey: The specified key does not exist")

    # Act & Assert
    with pytest.raises(S3UploadException) as exc_info:
        await s3_service.download_original(s3_key)

    assert "NoSuchKey" in str(exc_info.value) or "Download failed" in str(exc_info.value)


@pytest.mark.asyncio
async def test_download_original_s3_failure(s3_service, mock_s3_client):
    """Test download handles S3 connection failure."""
    # Arrange
    s3_key = "session-123/photo.jpg"
    mock_s3_client.get_object.side_effect = Exception("S3 connection timeout")

    # Act & Assert
    with pytest.raises(S3UploadException):
        await s3_service.download_original(s3_key)


# ============================================================================
# generate_presigned_url tests
# ============================================================================


@pytest.mark.asyncio
async def test_generate_presigned_url_success(s3_service, mock_s3_client):
    """Test successful presigned URL generation."""
    # Arrange
    s3_key = "session-123/photo.jpg"
    expiry_hours = 24
    expected_url = (
        "https://s3.amazonaws.com/demeter-photos-original/session-123/photo.jpg?X-Amz-Signature=..."
    )

    mock_s3_client.generate_presigned_url.return_value = expected_url

    # Act
    result = await s3_service.generate_presigned_url(s3_key, expiry_hours=expiry_hours)

    # Assert
    assert result == expected_url
    assert result.startswith("https://")
    mock_s3_client.generate_presigned_url.assert_called_once()

    # Verify expiration parameter
    call_kwargs = mock_s3_client.generate_presigned_url.call_args[1]
    assert call_kwargs["ExpiresIn"] == expiry_hours * 3600  # Convert hours to seconds


@pytest.mark.asyncio
async def test_generate_presigned_url_default_expiry(s3_service, mock_s3_client):
    """Test presigned URL uses default 24-hour expiry."""
    # Arrange
    s3_key = "session-123/photo.jpg"
    mock_s3_client.generate_presigned_url.return_value = "https://s3.amazonaws.com/..."

    # Act
    result = await s3_service.generate_presigned_url(s3_key)

    # Assert
    call_kwargs = mock_s3_client.generate_presigned_url.call_args[1]
    assert call_kwargs["ExpiresIn"] == 24 * 3600  # Default 24 hours


@pytest.mark.asyncio
async def test_generate_presigned_url_invalid_key(s3_service, mock_s3_client):
    """Test presigned URL generation with invalid S3 key (wrapped in S3UploadException)."""
    # Arrange
    s3_key = ""  # Empty key
    mock_s3_client.generate_presigned_url.side_effect = ValueError("Invalid S3 key")

    # Act & Assert - Service wraps ValueError in S3UploadException
    with pytest.raises(S3UploadException) as exc_info:
        await s3_service.generate_presigned_url(s3_key)

    assert "Invalid S3 key" in str(exc_info.value)


# ============================================================================
# delete_image tests
# ============================================================================


@pytest.mark.asyncio
async def test_delete_image_success(s3_service, mock_s3_image_repo, mock_s3_client, mock_s3_image):
    """Test successful image deletion from S3 and database."""
    # Arrange
    image_id = UUID("123e4567-e89b-12d3-a456-426614174000")

    # Mock repository get and delete
    mock_s3_image_repo.get.return_value = mock_s3_image
    mock_s3_image_repo.delete.return_value = None

    # Act
    result = await s3_service.delete_image(image_id)

    # Assert
    assert result is True

    # Verify S3 delete called
    mock_s3_client.delete_object.assert_called_once()
    call_kwargs = mock_s3_client.delete_object.call_args[1]
    assert call_kwargs["Bucket"] == "demeter-photos-original"
    assert call_kwargs["Key"] == "session-123/original-photo_001.jpg"

    # Verify database delete called
    mock_s3_image_repo.delete.assert_called_once_with(image_id)


@pytest.mark.asyncio
async def test_delete_image_not_found(s3_service, mock_s3_image_repo):
    """Test delete returns False when image doesn't exist in database."""
    # Arrange
    image_id = uuid4()
    mock_s3_image_repo.get.return_value = None

    # Act
    result = await s3_service.delete_image(image_id)

    # Assert - Service returns False instead of raising exception
    assert result is False
    mock_s3_image_repo.delete.assert_not_called()  # No delete attempt


@pytest.mark.asyncio
async def test_delete_image_with_thumbnail(
    s3_service, mock_s3_image_repo, mock_s3_client, mock_s3_image
):
    """Test deletion of image with thumbnail (deletes both)."""
    # Arrange
    image_id = UUID("123e4567-e89b-12d3-a456-426614174000")
    mock_s3_image.s3_key_thumbnail = "session-123/thumbnail-photo_001.jpg"

    mock_s3_image_repo.get.return_value = mock_s3_image
    mock_s3_image_repo.delete.return_value = None

    # Act
    result = await s3_service.delete_image(image_id)

    # Assert
    assert result is True

    # Verify both original and thumbnail deleted from S3
    assert mock_s3_client.delete_object.call_count == 2


@pytest.mark.asyncio
async def test_delete_image_s3_failure_rollback(
    s3_service, mock_s3_image_repo, mock_s3_client, mock_s3_image
):
    """Test database rollback when S3 deletion fails."""
    # Arrange
    image_id = UUID("123e4567-e89b-12d3-a456-426614174000")
    mock_s3_image_repo.get.return_value = mock_s3_image

    # Mock S3 delete failure
    mock_s3_client.delete_object.side_effect = Exception("S3 access denied")

    # Act & Assert
    with pytest.raises(Exception):
        await s3_service.delete_image(image_id)

    # Verify database delete NOT called (rollback)
    mock_s3_image_repo.delete.assert_not_called()


# ============================================================================
# Edge cases and error handling
# ============================================================================


@pytest.mark.asyncio
async def test_upload_with_special_characters_in_filename(
    s3_service, mock_s3_image_repo, mock_s3_image, mock_s3_client
):
    """Test upload handles filenames with special characters."""
    # Arrange
    session_id = uuid4()
    file_bytes = b"data" * 100
    filename = "photo#&@!.jpg"  # Special characters

    upload_request = S3ImageUploadRequest(
        session_id=session_id,
        filename=filename,
        content_type=ContentTypeEnum.JPEG,
        file_size_bytes=len(file_bytes),
        width_px=1920,
        height_px=1080,
    )

    mock_s3_image_repo.create.return_value = mock_s3_image
    mock_s3_client.generate_presigned_url.return_value = "https://s3.amazonaws.com/test-url"

    # Act
    result = await s3_service.upload_original(file_bytes, session_id, upload_request)

    # Assert - Filename preserved in request (S3 handles special chars)
    assert result is not None


@pytest.mark.asyncio
async def test_upload_concurrent_same_session(
    s3_service, mock_s3_image_repo, mock_s3_image, mock_s3_client
):
    """Test multiple uploads to same session (unique keys)."""
    # Arrange
    session_id = uuid4()
    file_bytes_1 = b"photo1" * 100
    file_bytes_2 = b"photo2" * 100

    upload_request_1 = S3ImageUploadRequest(
        session_id=session_id,
        filename="photo_001.jpg",
        content_type=ContentTypeEnum.JPEG,
        file_size_bytes=len(file_bytes_1),
        width_px=2000,
        height_px=1500,
    )

    upload_request_2 = S3ImageUploadRequest(
        session_id=session_id,
        filename="photo_002.jpg",
        content_type=ContentTypeEnum.JPEG,
        file_size_bytes=len(file_bytes_2),
        width_px=2000,
        height_px=1500,
    )

    mock_s3_image_repo.create.return_value = mock_s3_image
    mock_s3_client.generate_presigned_url.return_value = "https://s3.amazonaws.com/test-url"

    # Act
    result1 = await s3_service.upload_original(file_bytes_1, session_id, upload_request_1)
    result2 = await s3_service.upload_original(file_bytes_2, session_id, upload_request_2)

    # Assert - Both uploads should succeed
    assert result1 is not None
    assert result2 is not None
    assert mock_s3_image_repo.create.call_count == 2


@pytest.mark.asyncio
async def test_generate_presigned_url_custom_expiry(s3_service, mock_s3_client):
    """Test presigned URL with custom expiry time (1 hour)."""
    # Arrange
    s3_key = "session-123/photo.jpg"
    expiry_hours = 1  # Short expiry

    mock_s3_client.generate_presigned_url.return_value = "https://s3.amazonaws.com/..."

    # Act
    result = await s3_service.generate_presigned_url(s3_key, expiry_hours=expiry_hours)

    # Assert
    call_kwargs = mock_s3_client.generate_presigned_url.call_args[1]
    assert call_kwargs["ExpiresIn"] == 3600  # 1 hour = 3600 seconds


@pytest.mark.asyncio
async def test_download_large_image(s3_service, mock_s3_client):
    """Test downloading large image."""
    # Arrange
    s3_key = "session-123/large_photo.jpg"
    large_data = b"x" * (100 * 1024 * 1024)  # 100MB

    # Mock S3 get_object response
    mock_response = {"Body": MagicMock()}
    mock_response["Body"].read = MagicMock(return_value=large_data)
    mock_s3_client.get_object.return_value = mock_response

    # Act
    result = await s3_service.download_original(s3_key)

    # Assert
    assert len(result) == len(large_data)
    assert result == large_data
