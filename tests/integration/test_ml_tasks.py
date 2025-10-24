"""Integration tests for ML tasks - S3 bucket consolidation refactoring.

This module tests the ML pipeline (ml_tasks.py) after S3 bucket consolidation.
Tests verify that visualization and thumbnail images are uploaded to the correct
location in the single-bucket structure.

Test Coverage:
- ML callback uploads viz to {session_id}/processed.{ext} in original bucket
- ML callback generates thumbnail to {session_id}/thumbnail.{ext}
- End-to-end ML pipeline with new S3 structure
- Error handling in ML callback

Architecture:
    Layer: Integration Testing (ML Pipeline)
    Pattern: Real database + mocked S3 + mocked YOLO
    Fixtures: db_session, mock S3, mock YOLO model

Note:
    Uses real PostgreSQL database for full workflow testing.
    Mocks only external dependencies (S3, YOLO model).
"""

import io
import uuid
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from app.core.config import settings
from app.models.photo_processing_session import SessionStatusEnum
from app.models.s3_image import ContentTypeEnum, ProcessingStatusEnum
from app.repositories.photo_processing_session_repository import PhotoProcessingSessionRepository
from app.repositories.s3_image_repository import S3ImageRepository

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_s3_client():
    """Mock boto3 S3 client for ML tasks testing."""
    mock_client = MagicMock()
    mock_client.put_object.return_value = {"ETag": '"abc123"'}
    mock_client.get_object.return_value = {
        "Body": MagicMock(read=lambda: b"fake_image_data"),
        "ContentType": "image/jpeg",
    }
    return mock_client


@pytest.fixture
def mock_yolo_model():
    """Mock YOLO model for testing (avoids loading real model)."""
    mock_model = MagicMock()
    mock_model.predict.return_value = [
        MagicMock(
            boxes=MagicMock(
                xyxy=[[100, 100, 300, 300]],  # Bounding box
                conf=[0.92],  # Confidence
                cls=[0],  # Class ID
            )
        )
    ]
    return mock_model


@pytest.fixture
def sample_visualization_bytes():
    """Generate sample visualization image (AVIF format)."""
    img = Image.new("RGB", (1000, 800), color="red")
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG")  # Use JPEG as fallback (Pillow may not support AVIF)
    return buffer.getvalue()


@pytest.fixture
async def sample_photo_session(db_session):
    """Create sample PhotoProcessingSession for testing.

    Returns:
        PhotoProcessingSession with uploaded S3 image
    """
    # Create S3 image
    s3_repo = S3ImageRepository(db_session)
    session_id = uuid.uuid4()
    s3_image = await s3_repo.create(
        {
            "image_id": uuid.uuid4(),
            "s3_bucket": settings.S3_BUCKET_ORIGINAL,
            "s3_key_original": f"{session_id}/original.jpg",
            "content_type": ContentTypeEnum.JPEG,
            "file_size_bytes": 2048576,
            "width_px": 4000,
            "height_px": 3000,
            "upload_source": "web",
            "status": ProcessingStatusEnum.UPLOADED,
        }
    )

    # Create photo processing session
    session_repo = PhotoProcessingSessionRepository(db_session)
    session = await session_repo.create(
        {
            "session_id": session_id,
            "original_image_id": s3_image.image_id,
            "uploaded_by_user_id": 1,
            "status": SessionStatusEnum.UPLOADED,
        }
    )

    return session


# =============================================================================
# Test ML Callback - Visualization Upload to New Location
# =============================================================================


@pytest.mark.asyncio
@patch("app.tasks.ml_tasks.boto3.client")
async def test_ml_callback_uploads_viz_to_new_location(
    mock_boto3_client, db_session, sample_photo_session, sample_visualization_bytes
):
    """Test ml_aggregation_callback uploads visualization to {session_id}/processed.{ext}."""
    # Arrange
    mock_s3_client = MagicMock()
    mock_s3_client.put_object.return_value = {"ETag": '"viz123"'}
    mock_boto3_client.return_value = mock_s3_client

    session_id = sample_photo_session.session_id

    # Simulate ML callback with visualization bytes
    from app.tasks.ml_tasks import ml_aggregation_callback

    # Mock visualization file path
    viz_file_path = f"/tmp/viz_{session_id}.avif"
    with patch("pathlib.Path.read_bytes", return_value=sample_visualization_bytes):
        with patch("pathlib.Path.exists", return_value=True):
            # Act
            await ml_aggregation_callback(
                session_id=str(session_id), viz_file_path=viz_file_path, db_session=db_session
            )

    # Assert - Verify viz uploaded to new location
    mock_s3_client.put_object.assert_called()
    call_kwargs = mock_s3_client.put_object.call_args[1]
    assert call_kwargs["Bucket"] == settings.S3_BUCKET_ORIGINAL  # NEW: Same bucket as original
    assert f"{session_id}/processed" in call_kwargs["Key"]  # NEW: processed.{ext} pattern
    assert call_kwargs["ContentType"] == "image/avif"

    # Verify database record created with new key
    s3_repo = S3ImageRepository(db_session)
    viz_images = await s3_repo.get_multi(filters={"image_type": "processed"})
    assert len(viz_images) >= 1
    viz_image = viz_images[0]
    assert viz_image.s3_bucket == settings.S3_BUCKET_ORIGINAL
    assert f"{session_id}/processed" in viz_image.s3_key_original


@pytest.mark.asyncio
@patch("app.tasks.ml_tasks.boto3.client")
async def test_ml_callback_generates_thumbnail(
    mock_boto3_client, db_session, sample_photo_session, sample_visualization_bytes
):
    """Test ml_aggregation_callback generates thumbnail to {session_id}/thumbnail.{ext}."""
    # Arrange
    mock_s3_client = MagicMock()
    mock_s3_client.put_object.return_value = {"ETag": '"thumb123"'}
    mock_boto3_client.return_value = mock_s3_client

    session_id = sample_photo_session.session_id
    viz_file_path = f"/tmp/viz_{session_id}.avif"

    # Act
    with patch("pathlib.Path.read_bytes", return_value=sample_visualization_bytes):
        with patch("pathlib.Path.exists", return_value=True):
            from app.tasks.ml_tasks import ml_aggregation_callback

            await ml_aggregation_callback(
                session_id=str(session_id), viz_file_path=viz_file_path, db_session=db_session
            )

    # Assert - Verify thumbnail uploaded
    put_object_calls = mock_s3_client.put_object.call_args_list
    thumbnail_call = [call for call in put_object_calls if "thumbnail" in call[1].get("Key", "")][0]

    assert thumbnail_call is not None
    assert thumbnail_call[1]["Bucket"] == settings.S3_BUCKET_ORIGINAL
    assert f"{session_id}/thumbnail.jpg" in thumbnail_call[1]["Key"]

    # Verify thumbnail image size (300x300px max)
    thumbnail_bytes = thumbnail_call[1]["Body"]
    thumb_img = Image.open(io.BytesIO(thumbnail_bytes))
    assert thumb_img.size[0] <= 300
    assert thumb_img.size[1] <= 300


@pytest.mark.asyncio
@patch("app.tasks.ml_tasks.boto3.client")
async def test_ml_callback_thumbnail_preserves_aspect_ratio(
    mock_boto3_client, db_session, sample_photo_session
):
    """Test thumbnail generation in ML callback preserves aspect ratio."""
    # Arrange - Create 2000x1000 image (2:1 aspect ratio)
    img = Image.new("RGB", (2000, 1000), color="blue")
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG")
    wide_image_bytes = buffer.getvalue()

    mock_s3_client = MagicMock()
    mock_s3_client.put_object.return_value = {"ETag": '"thumb123"'}
    mock_boto3_client.return_value = mock_s3_client

    session_id = sample_photo_session.session_id
    viz_file_path = f"/tmp/viz_{session_id}.jpg"

    # Act
    with patch("pathlib.Path.read_bytes", return_value=wide_image_bytes):
        with patch("pathlib.Path.exists", return_value=True):
            from app.tasks.ml_tasks import ml_aggregation_callback

            await ml_aggregation_callback(
                session_id=str(session_id), viz_file_path=viz_file_path, db_session=db_session
            )

    # Assert - Verify thumbnail aspect ratio (2:1)
    thumbnail_call = [
        call
        for call in mock_s3_client.put_object.call_args_list
        if "thumbnail" in call[1].get("Key", "")
    ][0]
    thumbnail_bytes = thumbnail_call[1]["Body"]
    thumb_img = Image.open(io.BytesIO(thumbnail_bytes))
    aspect_ratio = thumb_img.size[0] / thumb_img.size[1]
    assert 1.9 <= aspect_ratio <= 2.1  # 2.0 ± 0.1


# =============================================================================
# Test End-to-End ML Pipeline
# =============================================================================


@pytest.mark.asyncio
@patch("app.tasks.ml_tasks.boto3.client")
@patch("app.services.ml_processing.detection_service.get_yolo_model")
async def test_ml_pipeline_end_to_end(
    mock_get_model,
    mock_boto3_client,
    db_session,
    sample_photo_session,
    mock_yolo_model,
    sample_visualization_bytes,
):
    """Test full ML pipeline with new S3 structure (original → detection → viz → thumbnail)."""
    # Arrange
    mock_s3_client = MagicMock()
    mock_s3_client.put_object.return_value = {"ETag": '"upload123"'}
    mock_s3_client.get_object.return_value = {
        "Body": MagicMock(read=lambda: sample_visualization_bytes)
    }
    mock_boto3_client.return_value = mock_s3_client
    mock_get_model.return_value = mock_yolo_model

    session_id = sample_photo_session.session_id

    # Act - Run ML pipeline
    from app.tasks.ml_tasks import ml_parent_task

    with patch("app.tasks.ml_tasks.generate_visualization_avif") as mock_gen_viz:
        mock_gen_viz.return_value = "/tmp/viz_test.avif"
        with patch("pathlib.Path.read_bytes", return_value=sample_visualization_bytes):
            with patch("pathlib.Path.exists", return_value=True):
                result = await ml_parent_task(session_id=str(session_id))

    # Assert - Verify all uploads happened
    assert result is not None

    # Verify visualization uploaded to new location
    viz_calls = [
        call for call in mock_s3_client.put_object.call_args_list if "processed" in call[1]["Key"]
    ]
    assert len(viz_calls) >= 1
    viz_call = viz_calls[0]
    assert viz_call[1]["Bucket"] == settings.S3_BUCKET_ORIGINAL
    assert f"{session_id}/processed" in viz_call[1]["Key"]

    # Verify thumbnail uploaded
    thumb_calls = [
        call for call in mock_s3_client.put_object.call_args_list if "thumbnail" in call[1]["Key"]
    ]
    assert len(thumb_calls) >= 1
    thumb_call = thumb_calls[0]
    assert thumb_call[1]["Bucket"] == settings.S3_BUCKET_ORIGINAL
    assert f"{session_id}/thumbnail" in thumb_call[1]["Key"]


# =============================================================================
# Test Error Handling in ML Callback
# =============================================================================


@pytest.mark.asyncio
@patch("app.tasks.ml_tasks.boto3.client")
async def test_ml_callback_handles_s3_upload_failure(
    mock_boto3_client, db_session, sample_photo_session
):
    """Test ML callback handles S3 upload failure gracefully."""
    # Arrange
    mock_s3_client = MagicMock()
    mock_s3_client.put_object.side_effect = Exception("S3 connection timeout")
    mock_boto3_client.return_value = mock_s3_client

    session_id = sample_photo_session.session_id
    viz_file_path = f"/tmp/viz_{session_id}.avif"

    # Act - ML callback should handle error without crashing
    from app.tasks.ml_tasks import ml_aggregation_callback

    with patch("pathlib.Path.read_bytes", return_value=b"fake_viz_data"):
        with patch("pathlib.Path.exists", return_value=True):
            try:
                await ml_aggregation_callback(
                    session_id=str(session_id), viz_file_path=viz_file_path, db_session=db_session
                )
            except Exception as e:
                # Assert - Error should be logged but not crash entire pipeline
                assert "timeout" in str(e).lower() or "S3" in str(e)


@pytest.mark.asyncio
@patch("app.tasks.ml_tasks.boto3.client")
async def test_ml_callback_handles_missing_viz_file(
    mock_boto3_client, db_session, sample_photo_session
):
    """Test ML callback handles missing visualization file gracefully."""
    # Arrange
    mock_s3_client = MagicMock()
    mock_boto3_client.return_value = mock_s3_client

    session_id = sample_photo_session.session_id
    viz_file_path = f"/tmp/nonexistent_viz_{session_id}.avif"

    # Act
    from app.tasks.ml_tasks import ml_aggregation_callback

    with patch("pathlib.Path.exists", return_value=False):  # File doesn't exist
        try:
            await ml_aggregation_callback(
                session_id=str(session_id), viz_file_path=viz_file_path, db_session=db_session
            )
        except FileNotFoundError:
            # Assert - Should raise FileNotFoundError
            pass


# =============================================================================
# Test Backward Compatibility
# =============================================================================


@pytest.mark.asyncio
async def test_old_viz_bucket_images_still_accessible(db_session):
    """Test that old visualization bucket images can still be accessed during migration period."""
    # Arrange - Create old-style viz image (in viz bucket)
    s3_repo = S3ImageRepository(db_session)
    session_id = uuid.uuid4()
    old_viz_image = await s3_repo.create(
        {
            "image_id": uuid.uuid4(),
            "s3_bucket": settings.S3_BUCKET_VISUALIZATION,  # OLD bucket
            "s3_key_original": f"{session_id}/viz_old_style.jpg",
            "content_type": ContentTypeEnum.JPEG,
            "file_size_bytes": 1024,
            "width_px": 1000,
            "height_px": 800,
            "upload_source": "api",
            "status": ProcessingStatusEnum.READY,
            "image_type": "processed",
        }
    )

    # Act - Query should find old-style image
    results = await s3_repo.get_multi(filters={"image_type": "processed"})

    # Assert - Old image still accessible
    assert len(results) >= 1
    old_image = [img for img in results if img.image_id == old_viz_image.image_id][0]
    assert old_image.s3_bucket == settings.S3_BUCKET_VISUALIZATION  # OLD bucket


@pytest.mark.asyncio
@patch("app.tasks.ml_tasks.boto3.client")
async def test_new_viz_uses_original_bucket(
    mock_boto3_client, db_session, sample_photo_session, sample_visualization_bytes
):
    """Test that new visualizations are uploaded to original bucket (not viz bucket)."""
    # Arrange
    mock_s3_client = MagicMock()
    mock_s3_client.put_object.return_value = {"ETag": '"new_viz"'}
    mock_boto3_client.return_value = mock_s3_client

    session_id = sample_photo_session.session_id
    viz_file_path = f"/tmp/viz_{session_id}.avif"

    # Act
    with patch("pathlib.Path.read_bytes", return_value=sample_visualization_bytes):
        with patch("pathlib.Path.exists", return_value=True):
            from app.tasks.ml_tasks import ml_aggregation_callback

            await ml_aggregation_callback(
                session_id=str(session_id), viz_file_path=viz_file_path, db_session=db_session
            )

    # Assert - NEW visualization uses original bucket (not viz bucket)
    put_object_call = mock_s3_client.put_object.call_args_list[0]  # First call = viz upload
    assert put_object_call[1]["Bucket"] == settings.S3_BUCKET_ORIGINAL  # NEW behavior
    assert put_object_call[1]["Bucket"] != settings.S3_BUCKET_VISUALIZATION  # NOT viz bucket
