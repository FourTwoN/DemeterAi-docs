"""Shared fixtures for photo upload tests.

Provides reusable test data:
- JPEG test images (minimal, realistic)
- GPS coordinates
- Test warehouse/area/location setup
- S3 mock configurations
"""

import io

import pytest
from geoalchemy2.elements import WKTElement

from app.models.storage_area import StorageArea
from app.models.storage_location import StorageLocation
from app.models.warehouse import Warehouse

# =============================================================================
# Test Image Data
# =============================================================================


@pytest.fixture
def minimal_jpeg_bytes():
    """Minimal valid JPEG file (1x1 pixel, ~200 bytes).

    Use for: Quick validation tests where image content doesn't matter.
    """
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


@pytest.fixture
def minimal_png_bytes():
    """Minimal valid PNG file (1x1 pixel, transparent).

    Use for: Testing PNG file type support.
    """
    return (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\x00\x01\x00\x00"
        b"\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )


@pytest.fixture
def minimal_webp_bytes():
    """Minimal valid WEBP file.

    Use for: Testing WEBP file type support.
    """
    return b"RIFF\x00\x00\x00\x00WEBPVP8 "


# =============================================================================
# GPS Test Data
# =============================================================================


@pytest.fixture
def gps_santiago_chile():
    """GPS coordinates in Santiago, Chile region.

    Returns:
        dict with longitude, latitude
    """
    return {
        "longitude": -70.650,
        "latitude": -33.450,
    }


@pytest.fixture
def gps_pacific_ocean():
    """GPS coordinates in Pacific Ocean (no location match).

    Use for: Testing location not found scenarios.
    """
    return {
        "longitude": -150.0,
        "latitude": 0.0,
    }


# =============================================================================
# Database Fixtures - Warehouse Hierarchy
# =============================================================================


@pytest.fixture
async def santiago_warehouse(db_session):
    """Create test warehouse covering Santiago, Chile area.

    Use for: Integration/E2E tests requiring real GPS lookup.
    """
    polygon_wkt = (
        "POLYGON((-70.75 -33.55, -70.55 -33.55, -70.55 -33.35, -70.75 -33.35, -70.75 -33.55))"
    )
    geometry = WKTElement(polygon_wkt, srid=4326)

    warehouse = Warehouse(
        code="WH-SANTIAGO-001",
        name="Santiago Test Warehouse",
        address="Santiago, Chile",
        geojson_coordinates=geometry,
        active=True,
    )

    db_session.add(warehouse)
    await db_session.commit()
    await db_session.refresh(warehouse)

    return warehouse


@pytest.fixture
async def santiago_storage_area(db_session, santiago_warehouse):
    """Create test storage area within Santiago warehouse.

    Use for: Integration/E2E tests requiring area context.
    """
    polygon_wkt = (
        "POLYGON((-70.70 -33.50, -70.60 -33.50, -70.60 -33.40, -70.70 -33.40, -70.70 -33.50))"
    )
    geometry = WKTElement(polygon_wkt, srid=4326)

    storage_area = StorageArea(
        warehouse_id=santiago_warehouse.warehouse_id,
        code="AREA-SANTIAGO-001",
        qr_code="QR-AREA-SANTIAGO-001",
        name="Santiago Test Storage Area",
        geojson_coordinates=geometry,
        active=True,
    )

    db_session.add(storage_area)
    await db_session.commit()
    await db_session.refresh(storage_area)

    return storage_area


@pytest.fixture
async def santiago_storage_location(db_session, santiago_storage_area):
    """Create test storage location at specific GPS point in Santiago.

    GPS coordinates: lon=-70.650, lat=-33.450

    Use for: Integration/E2E tests with GPS lookup.
    """
    # GPS point matching gps_santiago_chile fixture
    point_wkt = "POINT(-70.650 -33.450)"
    geometry = WKTElement(point_wkt, srid=4326)

    storage_location = StorageLocation(
        storage_area_id=santiago_storage_area.storage_area_id,
        code="LOC-SANTIAGO-001",
        qr_code="QR-LOC-SANTIAGO-001",
        name="Santiago Test Storage Location",
        description="Test location with GPS (-70.650, -33.450)",
        geojson_coordinates=geometry,
        active=True,
    )

    db_session.add(storage_location)
    await db_session.commit()
    await db_session.refresh(storage_location)

    return storage_location


# =============================================================================
# Utility Functions
# =============================================================================


def create_large_jpeg(size_mb: int) -> bytes:
    """Create large JPEG file for size limit testing.

    Args:
        size_mb: Approximate size in megabytes

    Returns:
        JPEG file bytes of approximately size_mb MB
    """
    # Minimal JPEG header + footer
    header = (
        b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
        b"\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x11\x00"
    )
    footer = b"\xff\xd9"

    # Fill with junk data to reach desired size
    target_size = size_mb * 1024 * 1024
    junk_size = target_size - len(header) - len(footer)
    junk_data = b"\x00" * junk_size

    return header + junk_data + footer


def create_multipart_file(file_bytes: bytes, filename: str, content_type: str):
    """Create multipart file for FastAPI testing.

    Args:
        file_bytes: File content bytes
        filename: Filename to use
        content_type: MIME type (e.g., "image/jpeg")

    Returns:
        Tuple of (filename, BytesIO, content_type) for FastAPI client
    """
    return (filename, io.BytesIO(file_bytes), content_type)
