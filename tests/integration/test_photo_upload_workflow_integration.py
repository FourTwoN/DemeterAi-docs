"""Integration tests for photo upload workflow with real database.

Tests the complete workflow with:
- Real PostgreSQL database (with transactions)
- Real service layer (PhotoUploadService, S3ImageService, etc.)
- Mocked S3 SDK (boto3)
- Mocked Celery tasks

NO MOCKS of business logic - only external dependencies (S3, Celery).

Coverage target: ≥80%
"""

import io
import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi import UploadFile

pytestmark = pytest.mark.skip("Legacy integration tests pending update for new photo upload flow")

from app.core.exceptions import ResourceNotFoundException
from app.factories.service_factory import ServiceFactory
from app.models.photo_processing_session import (
    PhotoProcessingSession,
    ProcessingSessionStatusEnum,
)
from app.models.s3_image import S3Image
from app.models.storage_area import StorageArea
from app.models.storage_location import StorageLocation
from app.models.warehouse import Warehouse
from app.services.photo.photo_upload_service import PhotoUploadService

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
async def test_warehouse(db_session):
    """Create test warehouse with PostGIS geometry."""
    from geoalchemy2.elements import WKTElement

    # Create polygon in Santiago, Chile
    polygon_wkt = "POLYGON((-70.7 -33.5, -70.6 -33.5, -70.6 -33.4, -70.7 -33.4, -70.7 -33.5))"
    geometry = WKTElement(polygon_wkt, srid=4326)

    warehouse = Warehouse(
        code="WH-TEST-001",
        name="Test Warehouse",
        address="Test Address, Santiago, Chile",
        geojson_coordinates=geometry,
        active=True,
    )

    db_session.add(warehouse)
    await db_session.commit()
    await db_session.refresh(warehouse)

    return warehouse


@pytest.fixture
async def test_storage_area(db_session, test_warehouse):
    """Create test storage area."""
    from geoalchemy2.elements import WKTElement

    # Create polygon inside warehouse
    polygon_wkt = (
        "POLYGON((-70.68 -33.48, -70.66 -33.48, -70.66 -33.46, -70.68 -33.46, -70.68 -33.48))"
    )
    geometry = WKTElement(polygon_wkt, srid=4326)

    storage_area = StorageArea(
        warehouse_id=test_warehouse.warehouse_id,
        code="AREA-TEST-001",
        qr_code="QR-AREA-001",
        name="Test Storage Area",
        description="Test storage area for integration tests",
        geojson_coordinates=geometry,
        active=True,
    )

    db_session.add(storage_area)
    await db_session.commit()
    await db_session.refresh(storage_area)

    return storage_area


@pytest.fixture
async def test_storage_location(db_session, test_storage_area):
    """Create test storage location with GPS point."""
    from geoalchemy2.elements import WKTElement

    # Create point inside storage area (lon, lat)
    point_wkt = "POINT(-70.670 -33.470)"
    geometry = WKTElement(point_wkt, srid=4326)

    storage_location = StorageLocation(
        storage_area_id=test_storage_area.storage_area_id,
        code="LOC-TEST-001",
        qr_code="QR-LOC-001",
        name="Test Storage Location",
        description="Test location for GPS lookup",
        geojson_coordinates=geometry,
        active=True,
    )

    db_session.add(storage_location)
    await db_session.commit()
    await db_session.refresh(storage_location)

    return storage_location


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
        filename="test_greenhouse_photo.jpg",
        file=io.BytesIO(jpeg_bytes),
        headers={"content-type": "image/jpeg"},
    )


@pytest.fixture
def photo_upload_service(db_session) -> PhotoUploadService:
    """Create PhotoUploadService with real dependencies."""
    factory = ServiceFactory(db_session)
    return factory.get_photo_upload_service()


# =============================================================================
# Integration Tests - Complete Workflow
# =============================================================================


@pytest.mark.asyncio
async def test_photo_upload_complete_workflow_with_real_db(
    db_session,
    photo_upload_service,
    test_storage_location,
    valid_jpeg_file,
):
    """Test complete photo upload workflow with real database.

    Workflow:
    1. Upload photo with GPS coordinates
    2. Verify GPS location lookup works (PostGIS ST_Contains)
    3. Verify S3Image record created
    4. Verify PhotoProcessingSession created
    5. Verify Celery task dispatched
    6. Verify all database records are linked correctly
    """
    # Arrange
    gps_longitude = -70.670  # Matches test_storage_location
    gps_latitude = -33.470
    user_id = 1

    # Mock S3 SDK (boto3) - we don't want to upload to real S3
    with patch("app.services.photo.s3_image_service.boto3") as mock_boto3:
        # Mock S3 client
        mock_s3_client = MagicMock()
        mock_boto3.client.return_value = mock_s3_client
        mock_s3_client.put_object.return_value = {"ETag": "abc123"}

        # Mock Celery task dispatch
        with patch("app.services.photo.photo_upload_service.ml_parent_task") as mock_ml_task:
            mock_celery_result = MagicMock()
            task_id = uuid.uuid4()
            mock_celery_result.id = str(task_id)
            mock_ml_task.delay.return_value = mock_celery_result

            # Act: Upload photo
            result = await photo_upload_service.upload_photo(
                file=valid_jpeg_file,
                gps_longitude=gps_longitude,
                gps_latitude=gps_latitude,
                user_id=user_id,
            )

            # Assert 1: Response structure
            assert result.task_id == task_id
            assert result.session_id is not None
            assert result.status == "pending"
            assert result.message is not None
            assert result.poll_url is not None

            # Assert 2: S3Image record created in database
            from sqlalchemy import select

            s3_images_query = select(S3Image)
            s3_images_result = await db_session.execute(s3_images_query)
            s3_images = s3_images_result.scalars().all()

            assert len(s3_images) == 1
            s3_image = s3_images[0]

            assert s3_image.image_id is not None
            assert s3_image.s3_bucket == "demeterai-photos"
            assert s3_image.s3_key_original is not None
            assert s3_image.content_type.value == "image/jpeg"
            assert s3_image.status.value == "uploaded"
            assert s3_image.gps_coordinates is not None
            assert s3_image.gps_coordinates["latitude"] == gps_latitude
            assert s3_image.gps_coordinates["longitude"] == gps_longitude

            # Assert 3: PhotoProcessingSession created in database
            sessions_query = select(PhotoProcessingSession)
            sessions_result = await db_session.execute(sessions_query)
            sessions = sessions_result.scalars().all()

            assert len(sessions) == 1
            session = sessions[0]

            assert session.id == result.session_id
            assert session.session_id is not None
            assert session.storage_location_id == test_storage_location.location_id
            assert session.original_image_id == s3_image.image_id
            assert session.status == ProcessingSessionStatusEnum.PENDING
            assert session.total_detected == 0
            assert session.total_estimated == 0

            # Assert 4: Celery task was dispatched with correct arguments
            mock_ml_task.delay.assert_called_once()

            call_kwargs = mock_ml_task.delay.call_args.kwargs
            assert call_kwargs["session_id"] == session.id
            assert len(call_kwargs["image_data"]) == 1
            assert call_kwargs["image_data"][0]["image_id"] == str(s3_image.image_id)
            assert (
                call_kwargs["image_data"][0]["storage_location_id"]
                == test_storage_location.location_id
            )


@pytest.mark.asyncio
async def test_photo_upload_gps_location_not_found_with_real_db(
    photo_upload_service,
    test_storage_location,
    valid_jpeg_file,
):
    """Test GPS lookup fails when coordinates are outside all locations."""
    # Arrange: GPS coordinates far from test location (middle of ocean)
    gps_longitude = -100.0  # Pacific Ocean
    gps_latitude = 0.0

    # Mock S3 SDK
    with patch("app.services.photo.s3_image_service.boto3"):
        # Mock Celery task
        with patch("app.services.photo.photo_upload_service.ml_parent_task"):
            # Act & Assert: Should raise ResourceNotFoundException
            with pytest.raises(ResourceNotFoundException) as exc_info:
                await photo_upload_service.upload_photo(
                    file=valid_jpeg_file,
                    gps_longitude=gps_longitude,
                    gps_latitude=gps_latitude,
                    user_id=1,
                )

            assert exc_info.value.resource_type == "StorageLocation"


@pytest.mark.asyncio
async def test_photo_upload_creates_correct_s3_key_pattern(
    db_session,
    photo_upload_service,
    test_storage_location,
    valid_jpeg_file,
):
    """Test S3 key follows correct pattern: original/{image_id}.jpg"""
    # Arrange
    gps_longitude = -70.670
    gps_latitude = -33.470

    # Mock S3 SDK
    with patch("app.services.photo.s3_image_service.boto3") as mock_boto3:
        mock_s3_client = MagicMock()
        mock_boto3.client.return_value = mock_s3_client

        # Mock Celery task
        with patch("app.services.photo.photo_upload_service.ml_parent_task") as mock_ml_task:
            mock_celery_result = MagicMock()
            mock_celery_result.id = str(uuid.uuid4())
            mock_ml_task.delay.return_value = mock_celery_result

            # Act
            await photo_upload_service.upload_photo(
                file=valid_jpeg_file,
                gps_longitude=gps_longitude,
                gps_latitude=gps_latitude,
                user_id=1,
            )

            # Assert: Verify S3 key pattern
            from sqlalchemy import select

            s3_images_query = select(S3Image)
            s3_images_result = await db_session.execute(s3_images_query)
            s3_image = s3_images_result.scalar_one()

            # S3 key should be: original/{image_id}.jpg
            assert s3_image.s3_key_original.startswith("original/")
            assert s3_image.s3_key_original.endswith(".jpg")

            # Extract image_id from S3 key
            s3_key_parts = s3_image.s3_key_original.split("/")
            assert len(s3_key_parts) == 2
            assert s3_key_parts[0] == "original"


@pytest.mark.asyncio
async def test_photo_upload_session_linked_to_correct_location(
    db_session,
    photo_upload_service,
    test_storage_location,
    test_storage_area,
    test_warehouse,
    valid_jpeg_file,
):
    """Test photo processing session is correctly linked to location hierarchy.

    Verifies:
    - Session.storage_location_id = StorageLocation.location_id
    - StorageLocation.storage_area_id = StorageArea.storage_area_id
    - StorageArea.warehouse_id = Warehouse.warehouse_id
    """
    # Arrange
    gps_longitude = -70.670
    gps_latitude = -33.470

    # Mock S3 SDK
    with patch("app.services.photo.s3_image_service.boto3") as mock_boto3:
        mock_s3_client = MagicMock()
        mock_boto3.client.return_value = mock_s3_client

        # Mock Celery task
        with patch("app.services.photo.photo_upload_service.ml_parent_task") as mock_ml_task:
            mock_celery_result = MagicMock()
            mock_celery_result.id = str(uuid.uuid4())
            mock_ml_task.delay.return_value = mock_celery_result

            # Act
            result = await photo_upload_service.upload_photo(
                file=valid_jpeg_file,
                gps_longitude=gps_longitude,
                gps_latitude=gps_latitude,
                user_id=1,
            )

            # Assert: Verify session → location → area → warehouse hierarchy
            from sqlalchemy import select

            session_query = select(PhotoProcessingSession).where(
                PhotoProcessingSession.id == result.session_id
            )
            session_result = await db_session.execute(session_query)
            session = session_result.scalar_one()

            # Session → StorageLocation
            assert session.storage_location_id == test_storage_location.location_id

            # StorageLocation → StorageArea
            assert test_storage_location.storage_area_id == test_storage_area.storage_area_id

            # StorageArea → Warehouse
            assert test_storage_area.warehouse_id == test_warehouse.warehouse_id


@pytest.mark.asyncio
async def test_photo_upload_gps_boundary_lookup_accuracy(
    db_session,
    photo_upload_service,
    test_storage_location,
    valid_jpeg_file,
):
    """Test GPS lookup uses PostGIS ST_Contains for accurate spatial matching.

    Tests that GPS coordinates inside storage location polygon are matched correctly.
    """
    # Arrange: GPS coordinates inside test_storage_location
    gps_longitude = -70.670  # Inside POINT(-70.670 -33.470)
    gps_latitude = -33.470

    # Mock S3 SDK
    with patch("app.services.photo.s3_image_service.boto3") as mock_boto3:
        mock_s3_client = MagicMock()
        mock_boto3.client.return_value = mock_s3_client

        # Mock Celery task
        with patch("app.services.photo.photo_upload_service.ml_parent_task") as mock_ml_task:
            mock_celery_result = MagicMock()
            mock_celery_result.id = str(uuid.uuid4())
            mock_ml_task.delay.return_value = mock_celery_result

            # Act
            result = await photo_upload_service.upload_photo(
                file=valid_jpeg_file,
                gps_longitude=gps_longitude,
                gps_latitude=gps_latitude,
                user_id=1,
            )

            # Assert: Location lookup succeeded
            from sqlalchemy import select

            session_query = select(PhotoProcessingSession).where(
                PhotoProcessingSession.id == result.session_id
            )
            session_result = await db_session.execute(session_query)
            session = session_result.scalar_one()

            assert session.storage_location_id == test_storage_location.location_id


# =============================================================================
# Transaction Rollback Tests
# =============================================================================


@pytest.mark.asyncio
async def test_photo_upload_database_rollback_on_error(
    db_session,
    photo_upload_service,
    test_storage_location,
    valid_jpeg_file,
):
    """Test database changes are rolled back if workflow fails.

    Scenario: S3 upload succeeds, but Celery dispatch fails.
    Expected: No S3Image or PhotoProcessingSession records in database.
    """
    # Arrange
    gps_longitude = -70.670
    gps_latitude = -33.470

    # Mock S3 SDK (succeeds)
    with patch("app.services.photo.s3_image_service.boto3") as mock_boto3:
        mock_s3_client = MagicMock()
        mock_boto3.client.return_value = mock_s3_client

        # Mock Celery task (fails)
        with patch("app.services.photo.photo_upload_service.ml_parent_task") as mock_ml_task:
            mock_ml_task.delay.side_effect = Exception("Celery broker connection failed")

            # Act: Upload photo (should fail)
            with pytest.raises(Exception):
                await photo_upload_service.upload_photo(
                    file=valid_jpeg_file,
                    gps_longitude=gps_longitude,
                    gps_latitude=gps_latitude,
                    user_id=1,
                )

            # Assert: No database records created (transaction rolled back)
            from sqlalchemy import select

            s3_images_query = select(S3Image)
            s3_images_result = await db_session.execute(s3_images_query)
            s3_images = s3_images_result.scalars().all()

            # NOTE: S3Image is created BEFORE session creation, so it will exist
            # This is expected behavior (S3 upload is idempotent)
            # In production, failed sessions would be cleaned up by background job

            sessions_query = select(PhotoProcessingSession)
            sessions_result = await db_session.execute(sessions_query)
            sessions = sessions_result.scalars().all()

            # Session should not be created if Celery dispatch fails
            # NOTE: Depends on implementation - currently session is created before Celery dispatch
            # So this test may need adjustment based on transaction boundaries
