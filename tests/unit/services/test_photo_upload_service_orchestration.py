"""Updated tests for PhotoUploadService orchestration."""

import io
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import UploadFile

from app.models.photo_processing_session import ProcessingSessionStatusEnum
from app.models.s3_image import ContentTypeEnum, UploadSourceEnum
from app.schemas.s3_image_schema import S3ImageResponse
from app.services.photo.photo_job_service import PhotoJobService
from app.services.photo.photo_upload_service import PhotoUploadService


@pytest.fixture
def mock_session_service():
    service = AsyncMock()
    session = MagicMock()
    session.id = 1
    session.session_id = uuid.uuid4()
    session.storage_location_id = 1
    session.status = ProcessingSessionStatusEnum.PENDING
    session.total_detected = 0
    session.total_estimated = 0
    service.create_session.return_value = session
    return service


@pytest.fixture
def mock_s3_service():
    service = AsyncMock()
    response = S3ImageResponse(
        image_id=uuid.uuid4(),
        s3_bucket="bucket",
        s3_key_original="original/key.jpg",
        s3_key_thumbnail=None,
        content_type=ContentTypeEnum.JPEG,
        file_size_bytes=1024,
        width_px=100,
        height_px=100,
        upload_source=UploadSourceEnum.WEB,
        uploaded_by_user_id=1,
        status="uploaded",
        gps_coordinates=None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    service.upload_original.return_value = response
    service.upload_thumbnail.return_value = response
    return service


@pytest.fixture
def mock_location_service():
    service = AsyncMock()
    service.get_location_by_gps.return_value = None
    return service


@pytest.fixture
def mock_job_service():
    service = AsyncMock(spec=PhotoJobService)
    service.create_upload_session = AsyncMock()
    return service


@pytest.fixture
def photo_upload_service(
    mock_session_service,
    mock_s3_service,
    mock_location_service,
    mock_job_service,
):
    return PhotoUploadService(
        session_service=mock_session_service,
        s3_service=mock_s3_service,
        location_service=mock_location_service,
        job_service=mock_job_service,
    )


@pytest.fixture
def jpeg_file():
    data = b"\xff\xd8\xff\xd9"
    return UploadFile(filename="test.jpg", file=io.BytesIO(data))


@pytest.fixture
def mock_redis():
    redis = AsyncMock()
    redis.setex = AsyncMock()
    return redis


@pytest.mark.asyncio
async def test_upload_photo_returns_session_and_job(
    photo_upload_service,
    jpeg_file,
    mock_session_service,
    mock_job_service,
    mock_redis,
):
    with patch("app.services.photo.photo_upload_service.ml_parent_task") as mock_task:
        mock_celery_result = MagicMock()
        mock_celery_result.id = "job-123"
        mock_task.delay.return_value = mock_celery_result

        result = await photo_upload_service.upload_photo(jpeg_file, user_id=1, redis=mock_redis)

    assert result.session_id == mock_session_service.create_session.return_value.id
    assert result.task_id == mock_celery_result.id
    assert result.upload_session_id is not None
    mock_job_service.create_upload_session.assert_called_once()


@pytest.mark.asyncio
async def test_upload_photo_stores_job_in_redis(
    photo_upload_service,
    jpeg_file,
    mock_job_service,
    mock_redis,
):
    with patch("app.services.photo.photo_upload_service.ml_parent_task") as mock_task:
        mock_celery_result = MagicMock()
        mock_celery_result.id = "job-456"
        mock_task.delay.return_value = mock_celery_result

        await photo_upload_service.upload_photo(jpeg_file, user_id=42, redis=mock_redis)

    mock_job_service.create_upload_session.assert_called_once()
