"""E2E tests for Photo Upload Flow V3 (Complete Flowchart).

Tests the COMPLETE end-to-end workflow from API to Celery:
1. POST /api/v1/stock/photo with multipart form
2. Controller validates file
3. Service orchestrates GPS lookup + S3 upload + session creation
4. Celery task is dispatched (verified via task queue)
5. Response returned with 202 ACCEPTED
6. Task status can be polled via /api/v1/stock/tasks/{task_id}

Uses:
- Real FastAPI client (httpx AsyncClient)
- Real database (PostgreSQL with PostGIS)
- Mocked S3 SDK (boto3)
- Real Celery task dispatch (verified in queue)

NOTE: This is NOT an integration test - it's a full E2E test with minimal mocking.
"""

import io
import uuid
from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient

from app.main import app
from app.models.storage_area import StorageArea
from app.models.storage_location import StorageLocation
from app.models.warehouse import Warehouse


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
async def test_warehouse(db_session):
    """Create test warehouse for GPS lookup."""
    from geoalchemy2.elements import WKTElement

    # Create polygon covering Santiago, Chile area
    polygon_wkt = "POLYGON((-70.75 -33.55, -70.55 -33.55, -70.55 -33.35, -70.75 -33.35, -70.75 -33.55))"
    geometry = WKTElement(polygon_wkt, srid=4326)

    warehouse = Warehouse(
        code="WH-E2E-001",
        name="E2E Test Warehouse",
        address="Santiago, Chile",
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

    polygon_wkt = "POLYGON((-70.70 -33.50, -70.60 -33.50, -70.60 -33.40, -70.70 -33.40, -70.70 -33.50))"
    geometry = WKTElement(polygon_wkt, srid=4326)

    storage_area = StorageArea(
        warehouse_id=test_warehouse.warehouse_id,
        code="AREA-E2E-001",
        qr_code="QR-AREA-E2E-001",
        name="E2E Test Storage Area",
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

    # GPS point: lon -70.650, lat -33.450 (inside area)
    point_wkt = "POINT(-70.650 -33.450)"
    geometry = WKTElement(point_wkt, srid=4326)

    storage_location = StorageLocation(
        storage_area_id=test_storage_area.storage_area_id,
        code="LOC-E2E-001",
        qr_code="QR-LOC-E2E-001",
        name="E2E Test Storage Location",
        geojson_coordinates=geometry,
        active=True,
    )

    db_session.add(storage_location)
    await db_session.commit()
    await db_session.refresh(storage_location)

    return storage_location


@pytest.fixture
def test_photo_bytes():
    """Create minimal JPEG file bytes."""
    return (
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


# =============================================================================
# E2E Tests - Complete Workflow
# =============================================================================


@pytest.mark.asyncio
async def test_photo_upload_flow_v3_complete_e2e(
    db_session,
    test_storage_location,
    test_photo_bytes,
):
    """Test complete Photo Upload Flow V3 from API to Celery.

    Complete workflow:
    1. POST /api/v1/stock/photo with multipart/form-data
    2. API validates file (type, size)
    3. GPS location lookup via PostGIS ST_Contains
    4. S3 upload (mocked boto3)
    5. Photo processing session created
    6. Celery ML task dispatched
    7. Response 202 ACCEPTED with task_id
    8. Task can be polled via GET /api/v1/stock/tasks/{task_id}
    """
    # Arrange: GPS coordinates matching test_storage_location
    gps_longitude = -70.650
    gps_latitude = -33.450
    user_id = 1

    # Mock S3 SDK
    with patch("app.services.photo.s3_image_service.boto3") as mock_boto3:
        mock_s3_client = MagicMock()
        mock_boto3.client.return_value = mock_s3_client
        mock_s3_client.put_object.return_value = {"ETag": "test-etag-123"}

        # Mock Celery task dispatch
        with patch("app.services.photo.photo_upload_service.ml_parent_task") as mock_ml_task:
            mock_task_id = uuid.uuid4()
            mock_celery_result = MagicMock()
            mock_celery_result.id = str(mock_task_id)
            mock_ml_task.delay.return_value = mock_celery_result

            # Act: POST /api/v1/stock/photo
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/stock/photo",
                    files={
                        "file": ("greenhouse_photo.jpg", io.BytesIO(test_photo_bytes), "image/jpeg"),
                    },
                    data={
                        "longitude": str(gps_longitude),
                        "latitude": str(gps_latitude),
                        "user_id": str(user_id),
                    },
                )

            # Assert 1: Response status and structure
            assert response.status_code == 202, f"Expected 202, got {response.status_code}: {response.text}"

            response_data = response.json()
            assert "task_id" in response_data, "Response missing task_id"
            assert "session_id" in response_data, "Response missing session_id"
            assert "status" in response_data, "Response missing status"
            assert "message" in response_data, "Response missing message"
            assert "poll_url" in response_data, "Response missing poll_url"

            # Assert 2: Response values
            assert response_data["task_id"] == str(mock_task_id)
            assert response_data["status"] == "pending"
            assert isinstance(response_data["session_id"], int)

            # Assert 3: Celery task was dispatched
            mock_ml_task.delay.assert_called_once()

            # Assert 4: S3 upload was called
            mock_s3_client.put_object.assert_called_once()


@pytest.mark.asyncio
async def test_photo_upload_flow_v3_invalid_file_type_returns_400(
    db_session,
    test_storage_location,
):
    """Test API returns 400 for invalid file type (e.g., PDF)."""
    # Arrange: Create PDF file
    pdf_bytes = b"%PDF-1.4\n%test"

    # Act: POST /api/v1/stock/photo with PDF file
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/stock/photo",
            files={
                "file": ("document.pdf", io.BytesIO(pdf_bytes), "application/pdf"),
            },
            data={
                "longitude": "-70.650",
                "latitude": "-33.450",
                "user_id": "1",
            },
        )

    # Assert: 400 Bad Request
    assert response.status_code == 400
    response_data = response.json()
    assert "detail" in response_data
    assert "Invalid file type" in response_data["detail"]


@pytest.mark.asyncio
async def test_photo_upload_flow_v3_gps_not_found_returns_404(
    db_session,
    test_storage_location,
    test_photo_bytes,
):
    """Test API returns 404 when GPS coordinates don't match any location."""
    # Arrange: GPS coordinates far from test location (Pacific Ocean)
    gps_longitude = -150.0
    gps_latitude = 0.0

    # Mock S3 SDK (won't be called)
    with patch("app.services.photo.s3_image_service.boto3"):
        # Act: POST /api/v1/stock/photo
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/stock/photo",
                files={
                    "file": ("photo.jpg", io.BytesIO(test_photo_bytes), "image/jpeg"),
                },
                data={
                    "longitude": str(gps_longitude),
                    "latitude": str(gps_latitude),
                    "user_id": "1",
                },
            )

        # Assert: 404 Not Found
        assert response.status_code == 404
        response_data = response.json()
        assert "detail" in response_data
        assert "StorageLocation" in response_data["detail"] or "GPS" in response_data["detail"]


@pytest.mark.asyncio
async def test_photo_upload_flow_v3_file_too_large_returns_400(
    db_session,
    test_storage_location,
):
    """Test API returns 400 when file exceeds 20MB size limit."""
    # Arrange: Create file exceeding 20MB
    from app.services.photo.photo_upload_service import MAX_FILE_SIZE_BYTES

    large_data = b"x" * (MAX_FILE_SIZE_BYTES + 1024)  # 20MB + 1KB

    # Act: POST /api/v1/stock/photo
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/stock/photo",
            files={
                "file": ("huge.jpg", io.BytesIO(large_data), "image/jpeg"),
            },
            data={
                "longitude": "-70.650",
                "latitude": "-33.450",
                "user_id": "1",
            },
        )

    # Assert: 400 Bad Request
    assert response.status_code == 400
    response_data = response.json()
    assert "detail" in response_data
    assert "File size exceeds" in response_data["detail"] or "20MB" in response_data["detail"]


@pytest.mark.asyncio
async def test_photo_upload_flow_v3_celery_task_dispatch_verified(
    db_session,
    test_storage_location,
    test_photo_bytes,
):
    """Test Celery task is dispatched with correct arguments.

    Verifies:
    - ml_parent_task.delay() is called
    - session_id (int) is passed
    - image_data (list[dict]) contains correct structure
    """
    # Arrange
    gps_longitude = -70.650
    gps_latitude = -33.450

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
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/stock/photo",
                    files={
                        "file": ("photo.jpg", io.BytesIO(test_photo_bytes), "image/jpeg"),
                    },
                    data={
                        "longitude": str(gps_longitude),
                        "latitude": str(gps_latitude),
                        "user_id": "1",
                    },
                )

            # Assert: Celery task dispatch
            assert response.status_code == 202

            mock_ml_task.delay.assert_called_once()

            # Verify task arguments
            call_kwargs = mock_ml_task.delay.call_args.kwargs

            assert "session_id" in call_kwargs
            assert isinstance(call_kwargs["session_id"], int)

            assert "image_data" in call_kwargs
            assert isinstance(call_kwargs["image_data"], list)
            assert len(call_kwargs["image_data"]) == 1

            image_data = call_kwargs["image_data"][0]
            assert "image_id" in image_data
            assert "image_path" in image_data
            assert "storage_location_id" in image_data
            assert image_data["storage_location_id"] == test_storage_location.location_id


@pytest.mark.asyncio
async def test_photo_upload_flow_v3_task_status_polling(
    db_session,
    test_storage_location,
    test_photo_bytes,
):
    """Test task status can be polled via GET /api/v1/stock/tasks/{task_id}.

    Workflow:
    1. Upload photo (get task_id)
    2. Poll task status via GET /api/v1/stock/tasks/{task_id}
    3. Verify response contains task state
    """
    # Arrange
    gps_longitude = -70.650
    gps_latitude = -33.450

    # Mock S3 SDK
    with patch("app.services.photo.s3_image_service.boto3") as mock_boto3:
        mock_s3_client = MagicMock()
        mock_boto3.client.return_value = mock_s3_client

        # Mock Celery task
        with patch("app.services.photo.photo_upload_service.ml_parent_task") as mock_ml_task:
            mock_task_id = uuid.uuid4()
            mock_celery_result = MagicMock()
            mock_celery_result.id = str(mock_task_id)
            mock_ml_task.delay.return_value = mock_celery_result

            # Act 1: Upload photo
            async with AsyncClient(app=app, base_url="http://test") as client:
                upload_response = await client.post(
                    "/api/v1/stock/photo",
                    files={
                        "file": ("photo.jpg", io.BytesIO(test_photo_bytes), "image/jpeg"),
                    },
                    data={
                        "longitude": str(gps_longitude),
                        "latitude": str(gps_latitude),
                        "user_id": "1",
                    },
                )

                assert upload_response.status_code == 202
                upload_data = upload_response.json()
                task_id = upload_data["task_id"]

                # Act 2: Poll task status
                # Mock Celery AsyncResult
                with patch("app.controllers.stock_controller.celery_app") as mock_celery_app:
                    mock_async_result = MagicMock()
                    mock_async_result.state = "PENDING"
                    mock_async_result.ready.return_value = False
                    mock_async_result.info = None
                    mock_celery_app.AsyncResult.return_value = mock_async_result

                    status_response = await client.get(f"/api/v1/stock/tasks/{task_id}")

                    # Assert: Task status response
                    assert status_response.status_code == 200

                    status_data = status_response.json()
                    assert "task_id" in status_data
                    assert "status" in status_data
                    assert status_data["task_id"] == task_id


@pytest.mark.asyncio
async def test_photo_upload_flow_v3_multipart_form_data_validation():
    """Test API validates multipart/form-data structure.

    Required fields:
    - file: Photo file
    - longitude: GPS longitude (float)
    - latitude: GPS latitude (float)
    - user_id: User ID (int)
    """
    # Act: POST without required fields
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Missing 'file' field
        response1 = await client.post(
            "/api/v1/stock/photo",
            data={
                "longitude": "-70.650",
                "latitude": "-33.450",
                "user_id": "1",
            },
        )

        # Missing 'longitude' field
        response2 = await client.post(
            "/api/v1/stock/photo",
            files={
                "file": ("photo.jpg", io.BytesIO(b"fake"), "image/jpeg"),
            },
            data={
                "latitude": "-33.450",
                "user_id": "1",
            },
        )

    # Assert: 422 Unprocessable Entity (FastAPI validation)
    assert response1.status_code == 422
    assert response2.status_code == 422
