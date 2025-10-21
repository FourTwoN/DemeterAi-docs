"""Integration tests for S3ImageService with real database.

Tests service operations against real PostgreSQL database.
Uses mocked S3 client (boto3) but REAL database via S3ImageRepository.

TESTING STRATEGY:
- Real PostgreSQL database (via db_session fixture)
- Real S3ImageRepository
- Mocked boto3 S3 client (use moto or manual mocks)
- Test full workflows: upload → verify DB → download → delete
- Test cascade deletes and relationships

Coverage target: ≥85%

Test categories:
- upload_and_retrieve: Full workflow (upload → DB insert → verify)
- download_workflow: Upload → download → verify bytes
- delete_workflow: Upload → delete → verify cascade
- presigned_urls: Generate URLs for uploaded images
- concurrent_uploads: Multiple uploads to same session
- error_recovery: Transaction rollback on failures

See:
    - Service: app/services/photo/s3_image_service.py
    - Repository: app/repositories/s3_image_repository.py
    - Model: app/models/s3_image.py
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.s3_image import (
    ContentTypeEnum,
    ProcessingStatusEnum,
    S3Image,
    UploadSourceEnum,
)
from app.repositories.s3_image_repository import S3ImageRepository
from app.services.photo.s3_image_service import S3ImageService

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_s3_client():
    """Create mock boto3 S3 client for integration tests."""
    client = MagicMock()
    client.upload_fileobj = AsyncMock()
    client.download_fileobj = AsyncMock()
    client.generate_presigned_url = MagicMock()
    client.delete_object = AsyncMock()
    return client


@pytest.fixture
async def s3_service(db_session, mock_s3_client):
    """Create S3ImageService with REAL repository and mocked S3 client."""
    repo = S3ImageRepository(session=db_session)
    service = S3ImageService(repo=repo)

    # Mock S3 client (use moto in real implementation)
    service.s3_client = mock_s3_client
    service.bucket_original = "demeter-photos-original"
    service.bucket_viz = "demeter-photos-viz"

    # Mock circuit breaker to not interfere with tests
    service.circuit_breaker = MagicMock()
    service.circuit_breaker.call = lambda func, *args, **kwargs: func(*args, **kwargs)

    return service


# ============================================================================
# Test Upload and Retrieve Integration
# ============================================================================


@pytest.mark.asyncio
async def test_upload_original_full_workflow(s3_service, db_session):
    """Integration test: Upload photo and verify in database."""
    # Arrange
    session_id = uuid4()
    file_bytes = b"integration_test_image_data" * 500  # ~13.5KB
    filename = "integration_test.jpg"

    # Act - Upload to S3 (mocked) and insert to database (real)
    result = await s3_service.upload_original(
        file_bytes=file_bytes,
        session_id=session_id,
        filename=filename,
        content_type=ContentTypeEnum.JPEG,
        width_px=4000,
        height_px=3000,
    )

    # Assert - Verify response
    assert result.image_id is not None
    assert result.s3_bucket == "demeter-photos-original"
    assert str(session_id) in result.s3_key_original
    assert result.file_size_bytes == len(file_bytes)
    assert result.status == ProcessingStatusEnum.UPLOADED

    # Verify in database (real DB query)
    await db_session.commit()
    db_image = await db_session.get(S3Image, result.image_id)
    assert db_image is not None
    assert db_image.s3_key_original == result.s3_key_original
    assert db_image.file_size_bytes == len(file_bytes)
    assert db_image.content_type == ContentTypeEnum.JPEG
    assert db_image.width_px == 4000
    assert db_image.height_px == 3000


@pytest.mark.asyncio
async def test_upload_with_metadata_integration(s3_service, db_session):
    """Integration test: Upload with EXIF and GPS metadata."""
    # Arrange
    session_id = uuid4()
    file_bytes = b"photo_with_metadata" * 400
    filename = "metadata_test.jpg"
    exif_data = {
        "camera": "Canon EOS R5",
        "iso": 400,
        "shutter_speed": "1/500",
        "f_stop": "f/2.8",
    }
    gps_data = {
        "lat": -33.449150,
        "lng": -70.647500,
        "altitude": 570.5,
        "accuracy": 10.0,
    }

    # Act
    result = await s3_service.upload_original(
        file_bytes=file_bytes,
        session_id=session_id,
        filename=filename,
        exif_metadata=exif_data,
        gps_coordinates=gps_data,
    )

    # Assert - Verify metadata in database
    await db_session.commit()
    db_image = await db_session.get(S3Image, result.image_id)
    assert db_image is not None
    assert db_image.exif_metadata == exif_data
    assert db_image.gps_coordinates == gps_data
    assert db_image.gps_coordinates["lat"] == -33.449150
    assert db_image.gps_coordinates["lng"] == -70.647500


@pytest.mark.asyncio
async def test_upload_visualization_integration(s3_service, db_session):
    """Integration test: Upload visualization image to viz bucket."""
    # Arrange
    session_id = uuid4()
    file_bytes = b"visualization_image" * 300
    filename = "viz_001.jpg"

    # Act
    result = await s3_service.upload_visualization(
        file_bytes=file_bytes, session_id=session_id, filename=filename
    )

    # Assert
    assert result.s3_bucket == "demeter-photos-viz"
    assert "viz" in result.s3_key_original.lower()

    # Verify in database
    await db_session.commit()
    db_image = await db_session.get(S3Image, result.image_id)
    assert db_image is not None
    assert db_image.s3_bucket == "demeter-photos-viz"


# ============================================================================
# Test Download Workflow
# ============================================================================


@pytest.mark.asyncio
async def test_download_uploaded_image_workflow(s3_service, db_session, mock_s3_client):
    """Integration test: Upload → Download → Verify bytes."""
    # Arrange
    session_id = uuid4()
    original_bytes = b"original_photo_data" * 500
    filename = "download_test.jpg"

    # Upload image first
    upload_result = await s3_service.upload_original(
        file_bytes=original_bytes, session_id=session_id, filename=filename
    )

    # Mock S3 download to return original bytes
    async def mock_download(bucket, key, fileobj):
        fileobj.write(original_bytes)

    mock_s3_client.download_fileobj = AsyncMock(side_effect=mock_download)

    # Act - Download the uploaded image
    s3_key = upload_result.s3_key_original
    downloaded_bytes = await s3_service.download_image(s3_key)

    # Assert - Verify downloaded bytes match original
    assert downloaded_bytes == original_bytes
    assert len(downloaded_bytes) == len(original_bytes)


# ============================================================================
# Test Delete Workflow
# ============================================================================


@pytest.mark.asyncio
async def test_delete_image_integration(s3_service, db_session):
    """Integration test: Upload → Delete → Verify removed from DB."""
    # Arrange - Create image in database
    session_id = uuid4()
    file_bytes = b"delete_test_data" * 100
    filename = "delete_test.jpg"

    # Upload first
    upload_result = await s3_service.upload_original(
        file_bytes=file_bytes, session_id=session_id, filename=filename
    )
    image_id = upload_result.image_id

    # Verify exists in database
    await db_session.commit()
    db_image_before = await db_session.get(S3Image, image_id)
    assert db_image_before is not None

    # Act - Delete the image
    result = await s3_service.delete_image(image_id)

    # Assert - Verify deleted
    assert result is True

    # Verify removed from database
    await db_session.commit()
    db_image_after = await db_session.get(S3Image, image_id)
    assert db_image_after is None


@pytest.mark.asyncio
async def test_delete_image_with_thumbnail_integration(s3_service, db_session):
    """Integration test: Delete image with thumbnail (both removed)."""
    # Arrange - Create image with thumbnail
    repo = S3ImageRepository(session=db_session)
    image_id = uuid4()

    s3_image = S3Image(
        image_id=image_id,
        s3_bucket="demeter-photos-original",
        s3_key_original=f"session-{uuid4()}/original-photo.jpg",
        s3_key_thumbnail=f"session-{uuid4()}/thumbnail-photo.jpg",  # Has thumbnail
        content_type=ContentTypeEnum.JPEG,
        file_size_bytes=2048576,
        width_px=4000,
        height_px=3000,
        upload_source=UploadSourceEnum.WEB,
        status=ProcessingStatusEnum.UPLOADED,
    )

    db_session.add(s3_image)
    await db_session.commit()

    # Act - Delete image
    result = await s3_service.delete_image(image_id)

    # Assert
    assert result is True

    # Verify both original and thumbnail deleted from S3
    assert s3_service.s3_client.delete_object.call_count >= 2


# ============================================================================
# Test Presigned URLs
# ============================================================================


@pytest.mark.asyncio
async def test_generate_presigned_url_for_uploaded_image(s3_service, db_session, mock_s3_client):
    """Integration test: Upload → Generate presigned URL."""
    # Arrange - Upload image
    session_id = uuid4()
    file_bytes = b"url_test_data" * 200
    filename = "url_test.jpg"

    upload_result = await s3_service.upload_original(
        file_bytes=file_bytes, session_id=session_id, filename=filename
    )

    # Mock presigned URL generation
    expected_url = (
        f"https://s3.amazonaws.com/{upload_result.s3_bucket}/{upload_result.s3_key_original}?..."
    )
    mock_s3_client.generate_presigned_url.return_value = expected_url

    # Act - Generate presigned URL
    url = await s3_service.generate_presigned_url(
        s3_key=upload_result.s3_key_original, expiry_hours=24
    )

    # Assert
    assert url == expected_url
    assert url.startswith("https://")
    assert upload_result.s3_bucket in url or upload_result.s3_key_original in url


# ============================================================================
# Test Concurrent Operations
# ============================================================================


@pytest.mark.asyncio
async def test_concurrent_uploads_same_session(s3_service, db_session):
    """Integration test: Multiple uploads to same session."""
    # Arrange
    session_id = uuid4()
    file_bytes_1 = b"photo_1_data" * 200
    file_bytes_2 = b"photo_2_data" * 300
    file_bytes_3 = b"photo_3_data" * 400

    # Act - Upload 3 photos to same session
    result1 = await s3_service.upload_original(
        file_bytes=file_bytes_1, session_id=session_id, filename="photo_001.jpg"
    )
    result2 = await s3_service.upload_original(
        file_bytes=file_bytes_2, session_id=session_id, filename="photo_002.jpg"
    )
    result3 = await s3_service.upload_original(
        file_bytes=file_bytes_3, session_id=session_id, filename="photo_003.jpg"
    )

    # Assert - All 3 should have unique IDs and keys
    assert result1.image_id != result2.image_id != result3.image_id
    assert result1.s3_key_original != result2.s3_key_original != result3.s3_key_original

    # Verify all in database
    await db_session.commit()
    stmt = select(S3Image).where(S3Image.s3_key_original.like(f"%{session_id}%"))
    result = await db_session.execute(stmt)
    images = result.scalars().all()
    assert len(images) >= 3  # At least our 3 uploads


@pytest.mark.asyncio
async def test_upload_different_content_types(s3_service, db_session):
    """Integration test: Upload JPEG and PNG images."""
    # Arrange
    session_id = uuid4()
    jpeg_bytes = b"jpeg_image_data" * 200
    png_bytes = b"png_image_data" * 250

    # Act - Upload JPEG
    jpeg_result = await s3_service.upload_original(
        file_bytes=jpeg_bytes,
        session_id=session_id,
        filename="photo.jpg",
        content_type=ContentTypeEnum.JPEG,
    )

    # Upload PNG
    png_result = await s3_service.upload_original(
        file_bytes=png_bytes,
        session_id=session_id,
        filename="photo.png",
        content_type=ContentTypeEnum.PNG,
    )

    # Assert
    await db_session.commit()

    jpeg_db = await db_session.get(S3Image, jpeg_result.image_id)
    png_db = await db_session.get(S3Image, png_result.image_id)

    assert jpeg_db.content_type == ContentTypeEnum.JPEG
    assert png_db.content_type == ContentTypeEnum.PNG


# ============================================================================
# Test Error Recovery and Transactions
# ============================================================================


@pytest.mark.asyncio
async def test_upload_rollback_on_s3_failure(s3_service, db_session, mock_s3_client):
    """Integration test: Database rollback when S3 upload fails."""
    # Arrange
    session_id = uuid4()
    file_bytes = b"fail_test_data" * 100
    filename = "fail_test.jpg"

    # Mock S3 upload failure
    mock_s3_client.upload_fileobj.side_effect = Exception("S3 connection timeout")

    # Count images before
    stmt = select(S3Image)
    result_before = await db_session.execute(stmt)
    count_before = len(result_before.scalars().all())

    # Act & Assert - Upload should fail
    with pytest.raises(Exception):
        await s3_service.upload_original(file_bytes, session_id, filename)

    # Verify database NOT modified (rollback)
    await db_session.rollback()
    result_after = await db_session.execute(stmt)
    count_after = len(result_after.scalars().all())

    assert count_after == count_before  # No new records


@pytest.mark.asyncio
async def test_delete_nonexistent_image_integration(s3_service, db_session):
    """Integration test: Delete non-existent image raises exception."""
    # Arrange
    nonexistent_id = uuid4()

    # Act & Assert
    with pytest.raises(Exception):  # ResourceNotFoundException
        await s3_service.delete_image(nonexistent_id)


# ============================================================================
# Test GPS Validation Integration
# ============================================================================


@pytest.mark.asyncio
async def test_upload_with_invalid_gps_coordinates(s3_service, db_session):
    """Integration test: Upload with invalid GPS coordinates fails."""
    # Arrange
    session_id = uuid4()
    file_bytes = b"gps_test_data" * 100
    filename = "gps_invalid.jpg"

    invalid_gps = {
        "lat": 100.0,  # Invalid: lat must be -90 to +90
        "lng": -70.647500,
    }

    # Act & Assert - Should fail validation
    with pytest.raises(ValueError) as exc_info:
        await s3_service.upload_original(
            file_bytes=file_bytes,
            session_id=session_id,
            filename=filename,
            gps_coordinates=invalid_gps,
        )

    assert "latitude" in str(exc_info.value).lower() or "90" in str(exc_info.value)


@pytest.mark.asyncio
async def test_upload_with_valid_gps_coordinates(s3_service, db_session):
    """Integration test: Upload with valid GPS coordinates succeeds."""
    # Arrange
    session_id = uuid4()
    file_bytes = b"gps_valid_data" * 100
    filename = "gps_valid.jpg"

    valid_gps = {
        "lat": -33.449150,  # Valid: Santiago, Chile
        "lng": -70.647500,
        "altitude": 570.5,
        "accuracy": 10.0,
    }

    # Act
    result = await s3_service.upload_original(
        file_bytes=file_bytes,
        session_id=session_id,
        filename=filename,
        gps_coordinates=valid_gps,
    )

    # Assert
    await db_session.commit()
    db_image = await db_session.get(S3Image, result.image_id)
    assert db_image.gps_coordinates == valid_gps


# ============================================================================
# Test File Size Validation Integration
# ============================================================================


@pytest.mark.asyncio
async def test_upload_file_exceeds_limit_integration(s3_service, db_session):
    """Integration test: Upload file exceeding 500MB limit fails."""
    # Arrange
    session_id = uuid4()
    # Create 501MB file (exceeds 500MB limit)
    large_file_bytes = b"x" * (501 * 1024 * 1024)
    filename = "huge_file.jpg"

    # Act & Assert
    with pytest.raises(Exception):  # FileSizeException
        await s3_service.upload_original(large_file_bytes, session_id, filename)


@pytest.mark.asyncio
async def test_upload_maximum_allowed_file_size(s3_service, db_session):
    """Integration test: Upload 499MB file (within limit) succeeds."""
    # Arrange
    session_id = uuid4()
    # Create 499MB file (just under limit)
    max_file_bytes = b"x" * (499 * 1024 * 1024)
    filename = "max_size.jpg"

    # Act
    result = await s3_service.upload_original(
        file_bytes=max_file_bytes,
        session_id=session_id,
        filename=filename,
        width_px=8000,
        height_px=6000,
    )

    # Assert
    await db_session.commit()
    db_image = await db_session.get(S3Image, result.image_id)
    assert db_image is not None
    assert db_image.file_size_bytes == len(max_file_bytes)


# ============================================================================
# Test Status Transitions
# ============================================================================


@pytest.mark.asyncio
async def test_upload_sets_initial_status(s3_service, db_session):
    """Integration test: New upload has status 'uploaded'."""
    # Arrange
    session_id = uuid4()
    file_bytes = b"status_test_data" * 100
    filename = "status_test.jpg"

    # Act
    result = await s3_service.upload_original(file_bytes, session_id, filename)

    # Assert
    await db_session.commit()
    db_image = await db_session.get(S3Image, result.image_id)
    assert db_image.status == ProcessingStatusEnum.UPLOADED
    assert db_image.processing_status_updated_at is not None


@pytest.mark.asyncio
async def test_query_images_by_status(s3_service, db_session):
    """Integration test: Query images by processing status."""
    # Arrange - Create multiple images
    session_id = uuid4()

    # Upload 2 images
    await s3_service.upload_original(b"data1" * 100, session_id, "photo1.jpg")
    await s3_service.upload_original(b"data2" * 100, session_id, "photo2.jpg")

    # Act - Query by status
    await db_session.commit()
    stmt = select(S3Image).where(S3Image.status == ProcessingStatusEnum.UPLOADED)
    result = await db_session.execute(stmt)
    uploaded_images = result.scalars().all()

    # Assert
    assert len(uploaded_images) >= 2
    assert all(img.status == ProcessingStatusEnum.UPLOADED for img in uploaded_images)
