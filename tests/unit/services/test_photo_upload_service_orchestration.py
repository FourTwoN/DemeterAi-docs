"""Unit tests for PhotoUploadService orchestration logic.

Tests the complete orchestration workflow:
1. GPS location lookup
2. S3 upload coordination
3. Session creation
4. Celery task dispatch

Uses mocked dependencies (Service→Service pattern).

Coverage target: ≥80%
"""

import io
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import UploadFile

from app.core.exceptions import ResourceNotFoundException, ValidationException
from app.models.photo_processing_session import ProcessingSessionStatusEnum
from app.models.s3_image import ContentTypeEnum, UploadSourceEnum
from app.schemas.photo_processing_session_schema import PhotoProcessingSessionResponse
from app.schemas.s3_image_schema import S3ImageResponse
from app.schemas.storage_location_schema import StorageLocationResponse
from app.services.photo.photo_upload_service import PhotoUploadService


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_session_service():
    """Mock PhotoProcessingSessionService."""
    service = AsyncMock()

    # Mock create_session response
    mock_session = MagicMock()
    mock_session.id = 123  # Database ID
    mock_session.session_id = uuid.uuid4()  # UUID
    mock_session.storage_location_id = 1
    mock_session.original_image_id = uuid.uuid4()
    mock_session.status = ProcessingSessionStatusEnum.PENDING
    mock_session.total_detected = 0
    mock_session.total_estimated = 0

    service.create_session = AsyncMock(return_value=mock_session)
    service.mark_session_processing = AsyncMock()

    return service


@pytest.fixture
def mock_s3_service():
    """Mock S3ImageService."""
    service = AsyncMock()

    # Mock upload_original response
    mock_image_id = uuid.uuid4()
    mock_s3_response = S3ImageResponse(
        image_id=mock_image_id,
        s3_bucket="demeterai-photos",
        s3_key_original=f"original/{mock_image_id}.jpg",
        s3_key_thumbnail=None,
        content_type=ContentTypeEnum.JPEG,
        file_size_bytes=1024,
        width_px=1920,
        height_px=1080,
        upload_source=UploadSourceEnum.WEB,
        uploaded_by_user_id=1,
        status="uploaded",
        gps_coordinates={"latitude": -33.043, "longitude": -68.701},
    )

    service.upload_original = AsyncMock(return_value=mock_s3_response)

    return service


@pytest.fixture
def mock_location_service():
    """Mock StorageLocationService."""
    service = AsyncMock()

    # Mock get_location_by_gps response
    mock_location = StorageLocationResponse(
        storage_location_id=1,
        storage_area_id=10,
        warehouse_id=100,
        code="LOC-001",
        qr_code="QR-LOC-001",
        name="Test Location",
        description="Test storage location",
        active=True,
    )

    service.get_location_by_gps = AsyncMock(return_value=mock_location)

    return service


@pytest.fixture
def photo_upload_service(mock_session_service, mock_s3_service, mock_location_service):
    """Create PhotoUploadService with mocked dependencies."""
    return PhotoUploadService(
        session_service=mock_session_service,
        s3_service=mock_s3_service,
        location_service=mock_location_service,
    )


@pytest.fixture
def valid_jpeg_file():
    """Create a minimal valid JPEG file."""
    jpeg_bytes = (
        b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
        b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c"
        b"\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c"
        b"\x1c $.' ,\x1c\x1c(7),01444\x1f'9=82<.342\xff\xc0\x00\x0b\x08\x00"
        b"\x01\x00\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01"
        b"\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06"
        b"\x07\x08\t\n\x0b\xff\xc4\x00\xb5\x10\x00\x02\x01\x03\x03\x02\x04\x03"
        b"\x05\x05\x04\x04\x00\x00\x01}\x01\x02\x03\x00\x04\x11\x05\x12!1A\x06"
        b'\x13Qa\x07"q\x142\x81\x91\xa1\x08#B\xb1\xc1\x15R\xd1\xf0$3br\x82'
        b"\t\n\x16\x17\x18\x19\x1a%&'()*456789:CDEFGHIJSTUVWXYZcdefghijstuvwxyz"
        b"\x83\x84\x85\x86\x87\x88\x89\x8a\x92\x93\x94\x95\x96\x97\x98\x99\x9a"
        b"\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9"
        b"\xba\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xd2\xd3\xd4\xd5\xd6\xd7\xd8"
        b"\xd9\xda\xe1\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xf1\xf2\xf3\xf4\xf5"
        b"\xf6\xf7\xf8\xf9\xfa\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xfb\xd3"
        b"\xff\xd9"
    )

    return UploadFile(
        filename="test_photo.jpg",
        file=io.BytesIO(jpeg_bytes),
        headers={"content-type": "image/jpeg"},
    )


# =============================================================================
# Happy Path Tests - Complete Workflow
# =============================================================================


@pytest.mark.asyncio
async def test_upload_photo_complete_workflow_success(
    photo_upload_service,
    valid_jpeg_file,
    mock_location_service,
    mock_s3_service,
    mock_session_service,
):
    """Test successful photo upload with complete workflow.

    Workflow:
    1. Validate file
    2. GPS location lookup
    3. S3 upload
    4. Session creation
    5. Celery task dispatch
    """
    # Arrange
    gps_longitude = -68.701
    gps_latitude = -33.043
    user_id = 1

    # Mock Celery task
    with patch("app.services.photo.photo_upload_service.ml_parent_task") as mock_ml_task:
        mock_celery_result = MagicMock()
        mock_celery_result.id = "550e8400-e29b-41d4-a716-446655440000"
        mock_ml_task.delay.return_value = mock_celery_result

        # Act
        result = await photo_upload_service.upload_photo(
            file=valid_jpeg_file,
            gps_longitude=gps_longitude,
            gps_latitude=gps_latitude,
            user_id=user_id,
        )

        # Assert: Verify service calls
        # 1. GPS lookup was called
        mock_location_service.get_location_by_gps.assert_called_once_with(
            gps_longitude, gps_latitude
        )

        # 2. S3 upload was called
        mock_s3_service.upload_original.assert_called_once()

        # 3. Session creation was called
        mock_session_service.create_session.assert_called_once()

        # 4. Celery task was dispatched
        mock_ml_task.delay.assert_called_once()

        # Verify response structure
        assert result.task_id == mock_celery_result.id
        assert result.session_id == mock_session_service.create_session.return_value.id
        assert result.status == "pending"
        assert result.message is not None
        assert result.poll_url is not None


@pytest.mark.asyncio
async def test_upload_photo_celery_task_dispatched_with_correct_args(
    photo_upload_service,
    valid_jpeg_file,
    mock_session_service,
    mock_s3_service,
    mock_location_service,
):
    """Test Celery ML task is dispatched with correct arguments.

    Verifies:
    - session_id (int): PhotoProcessingSession.id
    - image_data (list[dict]): Contains image_id, image_path, storage_location_id
    """
    # Arrange
    gps_longitude = -68.701
    gps_latitude = -33.043
    user_id = 1

    # Mock Celery task
    with patch("app.services.photo.photo_upload_service.ml_parent_task") as mock_ml_task:
        mock_celery_result = MagicMock()
        mock_celery_result.id = uuid.uuid4()
        mock_ml_task.delay.return_value = mock_celery_result

        # Act
        await photo_upload_service.upload_photo(
            file=valid_jpeg_file,
            gps_longitude=gps_longitude,
            gps_latitude=gps_latitude,
            user_id=user_id,
        )

        # Assert: Verify Celery task arguments
        mock_ml_task.delay.assert_called_once()

        call_args = mock_ml_task.delay.call_args
        kwargs = call_args.kwargs

        # Verify session_id (int)
        assert "session_id" in kwargs
        assert isinstance(kwargs["session_id"], int)
        assert kwargs["session_id"] == mock_session_service.create_session.return_value.id

        # Verify image_data (list[dict])
        assert "image_data" in kwargs
        assert isinstance(kwargs["image_data"], list)
        assert len(kwargs["image_data"]) == 1

        image_data = kwargs["image_data"][0]
        assert "image_id" in image_data
        assert "image_path" in image_data
        assert "storage_location_id" in image_data


# =============================================================================
# Error Handling Tests
# =============================================================================


@pytest.mark.asyncio
async def test_upload_photo_gps_location_not_found_fails(
    photo_upload_service,
    valid_jpeg_file,
    mock_location_service,
):
    """Test failure when GPS coordinates do not match any location."""
    # Arrange: Mock location service returns None (no location found)
    mock_location_service.get_location_by_gps.return_value = None

    gps_longitude = -68.701
    gps_latitude = -33.043
    user_id = 1

    # Act & Assert: Should raise ResourceNotFoundException
    with pytest.raises(ResourceNotFoundException) as exc_info:
        await photo_upload_service.upload_photo(
            file=valid_jpeg_file,
            gps_longitude=gps_longitude,
            gps_latitude=gps_latitude,
            user_id=user_id,
        )

    assert exc_info.value.resource_type == "StorageLocation"
    assert "GPS" in str(exc_info.value.resource_id)


@pytest.mark.asyncio
async def test_upload_photo_invalid_file_type_fails(
    photo_upload_service,
    mock_location_service,
):
    """Test failure when file type is invalid (not JPEG/PNG/WEBP)."""
    # Arrange: Create invalid file (PDF)
    invalid_file = UploadFile(
        filename="document.pdf",
        file=io.BytesIO(b"%PDF-1.4"),
        headers={"content-type": "application/pdf"},
    )

    # Act & Assert: Should raise ValidationException
    with pytest.raises(ValidationException) as exc_info:
        await photo_upload_service.upload_photo(
            file=invalid_file,
            gps_longitude=-68.701,
            gps_latitude=-33.043,
            user_id=1,
        )

    assert exc_info.value.field == "file"
    assert "Invalid file type" in exc_info.value.message


@pytest.mark.asyncio
async def test_upload_photo_file_too_large_fails(
    photo_upload_service,
    mock_location_service,
):
    """Test failure when file exceeds 20MB size limit."""
    # Arrange: Create file exceeding 20MB
    from app.services.photo.photo_upload_service import MAX_FILE_SIZE_BYTES

    large_data = b"x" * (MAX_FILE_SIZE_BYTES + 1024)

    large_file = UploadFile(
        filename="huge.jpg",
        file=io.BytesIO(large_data),
        headers={"content-type": "image/jpeg"},
    )

    # Act & Assert: Should raise ValidationException
    with pytest.raises(ValidationException) as exc_info:
        await photo_upload_service.upload_photo(
            file=large_file,
            gps_longitude=-68.701,
            gps_latitude=-33.043,
            user_id=1,
        )

    assert exc_info.value.field == "file"
    assert "File size exceeds" in exc_info.value.message


@pytest.mark.asyncio
async def test_upload_photo_s3_upload_failure_propagates(
    photo_upload_service,
    valid_jpeg_file,
    mock_s3_service,
):
    """Test that S3 upload failures propagate to caller."""
    # Arrange: Mock S3 upload failure
    mock_s3_service.upload_original.side_effect = Exception("S3 connection failed")

    # Act & Assert: Exception should propagate
    with pytest.raises(Exception) as exc_info:
        await photo_upload_service.upload_photo(
            file=valid_jpeg_file,
            gps_longitude=-68.701,
            gps_latitude=-33.043,
            user_id=1,
        )

    assert "S3 connection failed" in str(exc_info.value)


@pytest.mark.asyncio
async def test_upload_photo_session_creation_failure_propagates(
    photo_upload_service,
    valid_jpeg_file,
    mock_session_service,
):
    """Test that session creation failures propagate to caller."""
    # Arrange: Mock session creation failure
    mock_session_service.create_session.side_effect = Exception("Database connection failed")

    # Act & Assert: Exception should propagate
    with pytest.raises(Exception) as exc_info:
        await photo_upload_service.upload_photo(
            file=valid_jpeg_file,
            gps_longitude=-68.701,
            gps_latitude=-33.043,
            user_id=1,
        )

    assert "Database connection failed" in str(exc_info.value)


# =============================================================================
# Service Dependency Tests (Service→Service Pattern)
# =============================================================================


@pytest.mark.asyncio
async def test_upload_photo_calls_location_service_for_gps_lookup(
    photo_upload_service,
    valid_jpeg_file,
    mock_location_service,
):
    """Test PhotoUploadService calls LocationService for GPS lookup (Service→Service)."""
    # Arrange
    gps_longitude = -68.701
    gps_latitude = -33.043

    with patch("app.services.photo.photo_upload_service.ml_parent_task"):
        # Act
        await photo_upload_service.upload_photo(
            file=valid_jpeg_file,
            gps_longitude=gps_longitude,
            gps_latitude=gps_latitude,
            user_id=1,
        )

        # Assert: LocationService.get_location_by_gps was called
        mock_location_service.get_location_by_gps.assert_called_once_with(
            gps_longitude, gps_latitude
        )


@pytest.mark.asyncio
async def test_upload_photo_calls_s3_service_for_upload(
    photo_upload_service,
    valid_jpeg_file,
    mock_s3_service,
):
    """Test PhotoUploadService calls S3ImageService for upload (Service→Service)."""
    with patch("app.services.photo.photo_upload_service.ml_parent_task"):
        # Act
        await photo_upload_service.upload_photo(
            file=valid_jpeg_file,
            gps_longitude=-68.701,
            gps_latitude=-33.043,
            user_id=1,
        )

        # Assert: S3ImageService.upload_original was called
        mock_s3_service.upload_original.assert_called_once()


@pytest.mark.asyncio
async def test_upload_photo_calls_session_service_for_session_creation(
    photo_upload_service,
    valid_jpeg_file,
    mock_session_service,
):
    """Test PhotoUploadService calls SessionService for session creation (Service→Service)."""
    with patch("app.services.photo.photo_upload_service.ml_parent_task"):
        # Act
        await photo_upload_service.upload_photo(
            file=valid_jpeg_file,
            gps_longitude=-68.701,
            gps_latitude=-33.043,
            user_id=1,
        )

        # Assert: SessionService.create_session was called
        mock_session_service.create_session.assert_called_once()


# =============================================================================
# Session Creation Tests
# =============================================================================


@pytest.mark.asyncio
async def test_upload_photo_creates_session_with_correct_status(
    photo_upload_service,
    valid_jpeg_file,
    mock_session_service,
):
    """Test photo processing session is created with PENDING status."""
    with patch("app.services.photo.photo_upload_service.ml_parent_task"):
        # Act
        await photo_upload_service.upload_photo(
            file=valid_jpeg_file,
            gps_longitude=-68.701,
            gps_latitude=-33.043,
            user_id=1,
        )

        # Assert: Session created with PENDING status
        mock_session_service.create_session.assert_called_once()

        call_args = mock_session_service.create_session.call_args
        session_request = call_args.args[0]

        assert session_request.status == ProcessingSessionStatusEnum.PENDING
        assert session_request.total_detected == 0
        assert session_request.total_estimated == 0


@pytest.mark.asyncio
async def test_upload_photo_links_session_to_location_and_image(
    photo_upload_service,
    valid_jpeg_file,
    mock_session_service,
    mock_location_service,
    mock_s3_service,
):
    """Test photo processing session is linked to location and original image."""
    with patch("app.services.photo.photo_upload_service.ml_parent_task"):
        # Act
        await photo_upload_service.upload_photo(
            file=valid_jpeg_file,
            gps_longitude=-68.701,
            gps_latitude=-33.043,
            user_id=1,
        )

        # Assert: Session linked to location and image
        mock_session_service.create_session.assert_called_once()

        call_args = mock_session_service.create_session.call_args
        session_request = call_args.args[0]

        # Verify location link
        expected_location_id = mock_location_service.get_location_by_gps.return_value.storage_location_id
        assert session_request.storage_location_id == expected_location_id

        # Verify original image link
        expected_image_id = mock_s3_service.upload_original.return_value.image_id
        assert session_request.original_image_id == expected_image_id
