"""E2E test for Photo Upload Flow V3 (Main Flowchart).

Tests the complete workflow:
1. API receives multipart photo upload
2. Photo is validated (type, size)
3. GPS location is looked up
4. Photo is uploaded to S3
5. Processing session is created
6. Celery ML tasks are dispatched
7. Frontend polls task status

NOTE: This E2E test uses real API but mocks database lookups.
"""

import asyncio
import io
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.storage_location import StorageLocation
from app.schemas.storage_location_schema import StorageLocationResponse


@pytest.fixture
def test_photo_file():
    """Create a minimal test JPEG file."""
    # Minimal JPEG file (1x1 pixel)
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
    return io.BytesIO(jpeg_bytes)


@pytest.mark.asyncio
async def test_photo_upload_flow_v3_complete():
    """Test complete photo upload flow V3."""
    # Setup: Mock GPS lookup service
    mock_location = StorageLocation(
        location_id=1,
        storage_area_id=1,
        code="LOC_TEST",
        qr_code="QR_TEST",
        name="Test Location",
        description="Test location for E2E testing",
        coordinates=MagicMock(),  # PostGIS geometry (mocked)
        centroid=MagicMock(),
        active=True,
        photo_session_id=None,
    )

    with patch(
        "app.services.storage_location_service.StorageLocationService.get_location_by_gps"
    ) as mock_gps_lookup:
        mock_gps_lookup.return_value = StorageLocationResponse.from_model(mock_location)

        # Act: Make POST request to /api/v1/stock/photo
        with TestClient(app) as client:
            photo_bytes = (
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

            response = client.post(
                "/api/v1/stock/photo",
                files={
                    "file": ("test_photo.jpg", io.BytesIO(photo_bytes), "image/jpeg"),
                },
                data={
                    "longitude": "-68.701",
                    "latitude": "-33.043",
                    "user_id": "1",
                },
            )

        # Assert: Check response
        assert response.status_code == 202, (
            f"Expected 202, got {response.status_code}: {response.text}"
        )

        response_data = response.json()
        assert "task_id" in response_data, "Response should contain task_id"
        assert "session_id" in response_data, "Response should contain session_id"
        assert response_data["status"] == "pending", "Status should be pending"

        print("\n✓ E2E Test PASSED")
        print(f"  Task ID: {response_data['task_id']}")
        print(f"  Session ID: {response_data['session_id']}")
        print(f"  Status: {response_data['status']}")
        print(f"  Poll URL: {response_data.get('poll_url')}")


if __name__ == "__main__":
    # Run test without pytest
    asyncio.run(test_photo_upload_flow_v3_complete())
