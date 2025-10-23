"""Unit tests for photo upload validation logic.

Tests validation rules for:
- File type (JPEG, PNG, WEBP only)
- File size (max 20MB)
- Content type checking
- Edge cases (empty files, oversized files)

Coverage target: ≥80%
"""

import io

import pytest
from fastapi import UploadFile

from app.core.exceptions import ValidationException
from app.services.photo.photo_upload_service import (
    ALLOWED_CONTENT_TYPES,
    MAX_FILE_SIZE_BYTES,
    PhotoUploadService,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def photo_upload_service():
    """Create PhotoUploadService with mocked dependencies."""
    from unittest.mock import Mock

    mock_session_service = Mock()
    mock_s3_service = Mock()
    mock_location_service = Mock()

    return PhotoUploadService(
        session_service=mock_session_service,
        s3_service=mock_s3_service,
        location_service=mock_location_service,
    )


@pytest.fixture
def valid_jpeg_file():
    """Create a minimal valid JPEG file (1x1 pixel)."""
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
# File Type Validation Tests
# =============================================================================


@pytest.mark.asyncio
async def test_validate_jpeg_file_success(photo_upload_service, valid_jpeg_file):
    """Test validation succeeds for valid JPEG file."""
    # Act: Validate file (should not raise exception)
    await photo_upload_service._validate_photo_file(valid_jpeg_file)

    # Assert: No exception raised = validation passed
    assert True  # If we reach here, validation passed


@pytest.mark.asyncio
async def test_validate_png_file_success(photo_upload_service):
    """Test validation succeeds for valid PNG file."""
    # Arrange: Create minimal PNG file (1x1 pixel)
    png_bytes = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\x00\x01\x00\x00"
        b"\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )

    file = UploadFile(
        filename="test.png",
        file=io.BytesIO(png_bytes),
        headers={"content-type": "image/png"},
    )

    # Act & Assert: Should not raise exception
    await photo_upload_service._validate_photo_file(file)


@pytest.mark.asyncio
async def test_validate_webp_file_success(photo_upload_service):
    """Test validation succeeds for valid WEBP file."""
    # Arrange: Create minimal WEBP file
    webp_bytes = b"RIFF\x00\x00\x00\x00WEBPVP8 "

    file = UploadFile(
        filename="test.webp",
        file=io.BytesIO(webp_bytes),
        headers={"content-type": "image/webp"},
    )

    # Act & Assert: Should not raise exception
    await photo_upload_service._validate_photo_file(file)


@pytest.mark.asyncio
async def test_validate_invalid_content_type_fails(photo_upload_service):
    """Test validation fails for invalid content type (e.g., PDF)."""
    # Arrange: Create file with invalid content type
    file = UploadFile(
        filename="document.pdf",
        file=io.BytesIO(b"%PDF-1.4"),
        headers={"content-type": "application/pdf"},
    )

    # Act & Assert: Should raise ValidationException
    with pytest.raises(ValidationException) as exc_info:
        await photo_upload_service._validate_photo_file(file)

    assert exc_info.value.extra.get("field") == "file"
    assert "Invalid file type" in exc_info.value.user_message
    assert "application/pdf" in exc_info.value.user_message


@pytest.mark.asyncio
async def test_validate_unsupported_image_type_fails(photo_upload_service):
    """Test validation fails for unsupported image types (e.g., GIF, BMP)."""
    # Arrange: Create GIF file
    file = UploadFile(
        filename="animation.gif",
        file=io.BytesIO(b"GIF89a"),
        headers={"content-type": "image/gif"},
    )

    # Act & Assert: Should raise ValidationException
    with pytest.raises(ValidationException) as exc_info:
        await photo_upload_service._validate_photo_file(file)

    assert exc_info.value.extra.get("field") == "file"
    assert "image/gif" in exc_info.value.user_message


# =============================================================================
# File Size Validation Tests
# =============================================================================


@pytest.mark.asyncio
async def test_validate_file_within_size_limit(photo_upload_service):
    """Test validation succeeds for file within 20MB limit."""
    # Arrange: Create 1MB file (well within 20MB limit)
    file_size = 1 * 1024 * 1024  # 1MB
    large_data = b"x" * file_size

    file = UploadFile(
        filename="large.jpg",
        file=io.BytesIO(large_data),
        headers={"content-type": "image/jpeg"},
    )

    # Act & Assert: Should not raise exception
    await photo_upload_service._validate_photo_file(file)


@pytest.mark.asyncio
async def test_validate_file_at_size_limit_boundary(photo_upload_service):
    """Test validation succeeds for file exactly at 20MB limit."""
    # Arrange: Create file exactly at MAX_FILE_SIZE_BYTES
    file_size = MAX_FILE_SIZE_BYTES  # 20MB
    large_data = b"x" * file_size

    file = UploadFile(
        filename="exact_limit.jpg",
        file=io.BytesIO(large_data),
        headers={"content-type": "image/jpeg"},
    )

    # Act & Assert: Should not raise exception
    await photo_upload_service._validate_photo_file(file)


@pytest.mark.asyncio
async def test_validate_file_exceeds_size_limit_fails(photo_upload_service):
    """Test validation fails for file exceeding 20MB limit."""
    # Arrange: Create 21MB file (exceeds 20MB limit)
    file_size = MAX_FILE_SIZE_BYTES + 1024  # 20MB + 1KB
    large_data = b"x" * file_size

    file = UploadFile(
        filename="too_large.jpg",
        file=io.BytesIO(large_data),
        headers={"content-type": "image/jpeg"},
    )

    # Act & Assert: Should raise ValidationException
    with pytest.raises(ValidationException) as exc_info:
        await photo_upload_service._validate_photo_file(file)

    assert exc_info.value.extra.get("field") == "file"
    assert "File size exceeds" in exc_info.value.user_message
    assert "20MB" in exc_info.value.user_message


@pytest.mark.asyncio
async def test_validate_empty_file_succeeds(photo_upload_service):
    """Test validation succeeds for empty file (size 0 bytes).

    NOTE: Empty files are technically valid (size validation only checks max limit).
    The ML pipeline will handle empty files appropriately.
    """
    # Arrange: Create empty file
    file = UploadFile(
        filename="empty.jpg",
        file=io.BytesIO(b""),
        headers={"content-type": "image/jpeg"},
    )

    # Act & Assert: Should not raise exception
    # (size validation only checks max limit, not minimum)
    await photo_upload_service._validate_photo_file(file)


# =============================================================================
# Edge Cases
# =============================================================================


@pytest.mark.asyncio
async def test_validate_file_pointer_reset_after_validation(photo_upload_service, valid_jpeg_file):
    """Test file pointer is reset to beginning after validation.

    Important: Validation reads file bytes, so pointer must be reset
    for subsequent operations (S3 upload).
    """
    # Arrange: Get initial file size
    initial_position = valid_jpeg_file.file.tell()

    # Act: Validate file
    await photo_upload_service._validate_photo_file(valid_jpeg_file)

    # Assert: File pointer is reset to beginning
    final_position = valid_jpeg_file.file.tell()
    assert final_position == initial_position  # Should be 0


@pytest.mark.asyncio
async def test_allowed_content_types_configuration():
    """Test ALLOWED_CONTENT_TYPES constant is correctly configured."""
    assert "image/jpeg" in ALLOWED_CONTENT_TYPES
    assert "image/jpg" in ALLOWED_CONTENT_TYPES
    assert "image/png" in ALLOWED_CONTENT_TYPES
    assert "image/webp" in ALLOWED_CONTENT_TYPES

    # Verify unsupported types are excluded
    assert "image/gif" not in ALLOWED_CONTENT_TYPES
    assert "application/pdf" not in ALLOWED_CONTENT_TYPES


def test_max_file_size_configuration():
    """Test MAX_FILE_SIZE_BYTES constant is correctly configured."""
    expected_size = 20 * 1024 * 1024  # 20MB
    assert expected_size == MAX_FILE_SIZE_BYTES
