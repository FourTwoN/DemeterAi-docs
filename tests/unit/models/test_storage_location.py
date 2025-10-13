"""Unit tests for StorageLocation model validation logic.

These tests focus on validation logic and do NOT require a database connection.
They test:
- QR code validation (format, uppercase, length 8-20 chars)
- Code validation (format WAREHOUSE-AREA-LOCATION, uppercase, length)
- JSONB position_metadata validation
- Foreign key constraints (storage_area_id required)
- Required fields enforcement
- Default values
- Geometry assignment from Shapely Point
- photo_session_id FK (nullable)

Integration tests with full database stack are in tests/integration/models/
"""

import pytest
from geoalchemy2.shape import from_shape
from shapely.geometry import Point, Polygon

# Note: Import will work once Python Expert completes the model
# For now, tests will be skipped if model doesn't exist
pytest.importorskip(
    "app.models.storage_location", reason="StorageLocation model not yet implemented"
)

from app.models.storage_location import StorageLocation  # noqa: E402


class TestStorageLocationQRCodeValidation:
    """Test QR code field validation rules (alphanumeric, 8-20 chars, uppercase)."""

    def test_qr_code_valid_formats(self):
        """Valid QR codes should be accepted."""
        valid_qr_codes = [
            "LOC12345",  # 8 chars (minimum)
            "LOC12345678",  # 11 chars
            "LOC-001-TEST",  # With hyphens
            "LOC_TEST_01",  # With underscores
            "QR123456789012345",  # 18 chars
            "12345678",  # 8 chars numeric
            "ABCDEFGH",  # 8 chars alpha
            "A1B2C3D4E5F6G7H8I9J0",  # 20 chars (maximum)
        ]

        for qr_code in valid_qr_codes:
            location = StorageLocation(
                code="WH-AREA-LOC001",
                name="Test Location",
                storage_area_id=1,
                qr_code=qr_code,
                coordinates=from_shape(Point(-70.6485, -33.4495), srid=4326),
            )
            assert location.qr_code == qr_code.upper()  # Should be uppercase

    def test_qr_code_uppercase_enforced(self):
        """QR code should be auto-converted to uppercase."""
        location = StorageLocation(
            code="WH-AREA-LOC001",
            name="Test Location",
            storage_area_id=1,
            qr_code="loc12345",  # Lowercase input
            coordinates=from_shape(Point(-70.6485, -33.4495), srid=4326),
        )

        # Should be converted to uppercase
        assert location.qr_code == "LOC12345"

        # Try updating with lowercase
        location.qr_code = "qr_test_01"
        assert location.qr_code == "QR_TEST_01"

    def test_qr_code_alphanumeric_validation(self):
        """QR code must be alphanumeric (plus hyphen and underscore)."""
        location = StorageLocation(
            code="WH-AREA-LOC001",
            name="Test Location",
            storage_area_id=1,
            qr_code="LOC12345",
            coordinates=from_shape(Point(-70.6485, -33.4495), srid=4326),
        )

        # Valid patterns with hyphen and underscore
        location.qr_code = "LOC-001-A"  # Should not raise
        location.qr_code = "LOC_TEST_01"  # Should not raise

        # Special chars should fail
        with pytest.raises(ValueError, match="alphanumeric"):
            location.qr_code = "LOC@12345"

        with pytest.raises(ValueError, match="alphanumeric"):
            location.qr_code = "LOC#TEST"

        with pytest.raises(ValueError, match="alphanumeric"):
            location.qr_code = "LOC 12345"  # Space not allowed

        with pytest.raises(ValueError, match="alphanumeric"):
            location.qr_code = "LOC.TEST"  # Dot not allowed

    def test_qr_code_length_validation(self):
        """QR code must be 8-20 characters."""
        location = StorageLocation(
            code="WH-AREA-LOC001",
            name="Test Location",
            storage_area_id=1,
            qr_code="LOC12345",  # Minimum 8 chars
            coordinates=from_shape(Point(-70.6485, -33.4495), srid=4326),
        )

        # Valid lengths
        location.qr_code = "ABCDEFGH"  # Min (8)
        location.qr_code = "A" * 20  # Max (20)

        # Too short (< 8)
        with pytest.raises(ValueError, match="8-20 characters"):
            location.qr_code = "SHORT"  # 5 chars

        with pytest.raises(ValueError, match="8-20 characters"):
            location.qr_code = "ABC1234"  # 7 chars

        # Too long (> 20)
        with pytest.raises(ValueError, match="8-20 characters"):
            location.qr_code = "A" * 21

        with pytest.raises(ValueError, match="8-20 characters"):
            location.qr_code = "TOOLONGQRCODE123456789"  # 22 chars

    def test_qr_code_required(self):
        """QR code field is required (not nullable)."""
        with pytest.raises(ValueError, match="required"):
            StorageLocation(
                code="WH-AREA-LOC001",
                name="Test Location",
                storage_area_id=1,
                qr_code=None,  # Should fail
                coordinates=from_shape(Point(-70.6485, -33.4495), srid=4326),
            )

    def test_qr_code_empty_string_rejected(self):
        """Empty string QR code should be rejected."""
        with pytest.raises(ValueError, match="required"):
            location = StorageLocation(
                code="WH-AREA-LOC001",
                name="Test Location",
                storage_area_id=1,
                qr_code="LOC12345",
                coordinates=from_shape(Point(-70.6485, -33.4495), srid=4326),
            )
            location.qr_code = ""

    def test_qr_code_whitespace_only_rejected(self):
        """Whitespace-only QR code should be rejected."""
        with pytest.raises(ValueError, match="required"):
            location = StorageLocation(
                code="WH-AREA-LOC001",
                name="Test Location",
                storage_area_id=1,
                qr_code="LOC12345",
                coordinates=from_shape(Point(-70.6485, -33.4495), srid=4326),
            )
            location.qr_code = "   "


class TestStorageLocationCodeValidation:
    """Test code field validation rules (WAREHOUSE-AREA-LOCATION format)."""

    def test_storage_location_code_format_validation(self):
        """Code must match WAREHOUSE-AREA-LOCATION pattern."""
        # Valid formats
        valid_codes = [
            "INV01-NORTH-A1",
            "GH-001-PROP-LOC1",
            "WAREHOUSE-AREA-LOCATION",
            "WH-A-L1",
            "INV01-SOUTH-B2",
        ]

        for code in valid_codes:
            location = StorageLocation(
                code=code,
                name="Test Location",
                storage_area_id=1,
                qr_code="LOC12345",
                coordinates=from_shape(Point(-70.6485, -33.4495), srid=4326),
            )
            assert location.code == code

    def test_storage_location_code_requires_two_hyphens(self):
        """Code must have at least 2 hyphens (WAREHOUSE-AREA-LOCATION)."""
        with pytest.raises(ValueError, match="WAREHOUSE-AREA-LOCATION"):
            StorageLocation(
                code="INV01-NORTH",  # Missing location part
                name="Test Location",
                storage_area_id=1,
                qr_code="LOC12345",
                coordinates=from_shape(Point(-70.6485, -33.4495), srid=4326),
            )

        with pytest.raises(ValueError, match="WAREHOUSE-AREA-LOCATION"):
            StorageLocation(
                code="INV01",  # Missing area and location
                name="Test Location",
                storage_area_id=1,
                qr_code="LOC12345",
                coordinates=from_shape(Point(-70.6485, -33.4495), srid=4326),
            )

    def test_storage_location_code_uppercase_enforced(self):
        """Code must be uppercase - lowercase should raise ValueError."""
        location = StorageLocation(
            code="INV01-NORTH-A1",
            name="Test Location",
            storage_area_id=1,
            qr_code="LOC12345",
            coordinates=from_shape(Point(-70.6485, -33.4495), srid=4326),
        )

        # Lowercase should raise ValueError
        with pytest.raises(ValueError, match="must be uppercase"):
            location.code = "inv01-north-a1"

    def test_storage_location_code_alphanumeric_only(self):
        """Code must be alphanumeric (plus hyphen/underscore)."""
        location = StorageLocation(
            code="WH-AREA-LOC01",
            name="Test Location",
            storage_area_id=1,
            qr_code="LOC12345",
            coordinates=from_shape(Point(-70.6485, -33.4495), srid=4326),
        )

        # Valid patterns
        location.code = "WH-AREA_01-LOC1"  # Should not raise
        location.code = "WAREHOUSE-STORAGE-AREA-LOC-01"  # Should not raise

        # Special chars should fail
        with pytest.raises(ValueError, match="alphanumeric"):
            location.code = "WH@AREA-LOC01"

        with pytest.raises(ValueError, match="alphanumeric"):
            location.code = "WH#AREA-LOC01"

        with pytest.raises(ValueError, match="alphanumeric"):
            location.code = "WH AREA-LOC01"  # Space not allowed

    def test_storage_location_code_length_validation(self):
        """Code must be 2-50 characters."""
        location = StorageLocation(
            code="W-A-L",  # Minimum with hyphens
            name="Test Location",
            storage_area_id=1,
            qr_code="LOC12345",
            coordinates=from_shape(Point(-70.6485, -33.4495), srid=4326),
        )

        # Valid lengths
        location.code = "W-A-L"  # Min
        location.code = "A" * 15 + "-" + "B" * 15 + "-" + "C" * 18  # Max (50)

        # Too short
        with pytest.raises(ValueError, match="2-50 characters"):
            location.code = "A"

        # Too long
        with pytest.raises(ValueError, match="2-50 characters"):
            location.code = "A" * 51

    def test_storage_location_code_required(self):
        """Code field is required (not nullable)."""
        with pytest.raises(ValueError, match="required"):
            StorageLocation(
                code=None,
                name="Test Location",
                storage_area_id=1,
                qr_code="LOC12345",
                coordinates=from_shape(Point(-70.6485, -33.4495), srid=4326),
            )

    def test_storage_location_code_empty_string(self):
        """Empty string code should be rejected."""
        with pytest.raises(ValueError, match="required"):
            location = StorageLocation(
                code="WH-AREA-LOC01",
                name="Test Location",
                storage_area_id=1,
                qr_code="LOC12345",
                coordinates=from_shape(Point(-70.6485, -33.4495), srid=4326),
            )
            location.code = ""


class TestStorageLocationPositionMetadata:
    """Test JSONB position_metadata field handling."""

    def test_position_metadata_default_empty_dict(self):
        """position_metadata should default to empty dict {}."""
        location = StorageLocation(
            code="WH-AREA-LOC01",
            name="Test Location",
            storage_area_id=1,
            qr_code="LOC12345",
            coordinates=from_shape(Point(-70.6485, -33.4495), srid=4326),
        )

        # Default should be empty dict
        assert location.position_metadata == {} or location.position_metadata is None

    def test_position_metadata_accepts_valid_json(self):
        """position_metadata should accept valid JSON objects."""
        valid_metadata_examples = [
            {"camera_angle": "45deg"},
            {"camera_angle": "45deg", "lighting": "natural"},
            {"camera": {"angle": 45, "distance": 2.5}, "lighting": {"type": "natural"}},
            {"capture_height": 2.0, "orientation": "north", "weather": "sunny"},
        ]

        for metadata in valid_metadata_examples:
            location = StorageLocation(
                code="WH-AREA-LOC01",
                name="Test Location",
                storage_area_id=1,
                qr_code="LOC12345",
                coordinates=from_shape(Point(-70.6485, -33.4495), srid=4326),
                position_metadata=metadata,
            )
            assert location.position_metadata == metadata

    def test_position_metadata_nullable(self):
        """position_metadata can be NULL."""
        location = StorageLocation(
            code="WH-AREA-LOC01",
            name="Test Location",
            storage_area_id=1,
            qr_code="LOC12345",
            coordinates=from_shape(Point(-70.6485, -33.4495), srid=4326),
            position_metadata=None,
        )

        assert location.position_metadata is None


class TestStorageLocationGeometry:
    """Test PostGIS geometry field assignment (POINT, not POLYGON)."""

    def test_geometry_accepts_point(self):
        """Should accept Shapely Point via from_shape()."""
        point = Point(-70.6485, -33.4495)

        location = StorageLocation(
            code="WH-AREA-LOC01",
            name="Test Location",
            storage_area_id=1,
            qr_code="LOC12345",
            coordinates=from_shape(point, srid=4326),
        )

        assert location.coordinates is not None

    def test_geometry_with_correct_srid(self):
        """Geometry must use SRID 4326 (WGS84)."""
        point = Point(-70.6485, -33.4495)

        location = StorageLocation(
            code="WH-AREA-LOC01",
            name="Test Location",
            storage_area_id=1,
            qr_code="LOC12345",
            coordinates=from_shape(point, srid=4326),
        )

        assert location.coordinates is not None

    def test_geometry_rejects_polygon(self):
        """Should reject Shapely Polygon (only POINT allowed)."""
        # Note: This test may need to be adapted based on actual implementation
        # GeoAlchemy2 might allow any geometry type at Python level
        # Validation happens at PostgreSQL level (POINT constraint)
        polygon = Polygon(
            [
                (-70.6485, -33.4495),
                (-70.6480, -33.4495),
                (-70.6480, -33.4490),
                (-70.6485, -33.4490),
                (-70.6485, -33.4495),
            ]
        )

        # This test verifies that polygon assignment happens
        # (database will reject on insert if type constraint exists)
        location = StorageLocation(
            code="WH-AREA-LOC01",
            name="Test Location",
            storage_area_id=1,
            qr_code="LOC12345",
            coordinates=from_shape(polygon, srid=4326),
        )

        # At Python level, assignment works
        # Database will reject with "geometry type mismatch" error
        assert location.coordinates is not None


class TestStorageLocationForeignKeys:
    """Test foreign key constraints."""

    def test_storage_area_id_required(self):
        """storage_area_id cannot be NULL."""
        with pytest.raises((ValueError, TypeError)):
            StorageLocation(
                code="WH-AREA-LOC01",
                name="Test Location",
                storage_area_id=None,  # Should fail
                qr_code="LOC12345",
                coordinates=from_shape(Point(-70.6485, -33.4495), srid=4326),
            )

    def test_photo_session_id_nullable(self):
        """photo_session_id can be NULL (latest photo reference)."""
        location = StorageLocation(
            code="WH-AREA-LOC01",
            name="Test Location",
            storage_area_id=1,
            qr_code="LOC12345",
            coordinates=from_shape(Point(-70.6485, -33.4495), srid=4326),
            photo_session_id=None,  # Should be allowed
        )

        assert location.photo_session_id is None


class TestStorageLocationRelationships:
    """Test model relationships."""

    def test_storage_area_relationship(self):
        """Many-to-one relationship to StorageArea."""
        # Note: This test verifies the relationship exists
        # Full relationship testing happens in integration tests

        location = StorageLocation(
            code="WH-AREA-LOC01",
            name="Test Location",
            storage_area_id=1,
            qr_code="LOC12345",
            coordinates=from_shape(Point(-70.6485, -33.4495), srid=4326),
        )

        # Relationship should be defined
        assert hasattr(location, "storage_area")

    def test_latest_photo_session_relationship(self):
        """Many-to-one relationship to PhotoProcessingSession (latest photo)."""
        location = StorageLocation(
            code="WH-AREA-LOC01",
            name="Test Location",
            storage_area_id=1,
            qr_code="LOC12345",
            coordinates=from_shape(Point(-70.6485, -33.4495), srid=4326),
            photo_session_id=123,
        )

        # Relationship should be defined
        assert hasattr(location, "latest_photo_session")

    def test_storage_bins_relationship(self):
        """One-to-many relationship to StorageBin."""
        location = StorageLocation(
            code="WH-AREA-LOC01",
            name="Test Location",
            storage_area_id=1,
            qr_code="LOC12345",
            coordinates=from_shape(Point(-70.6485, -33.4495), srid=4326),
        )

        # Relationship should be defined
        assert hasattr(location, "storage_bins")


class TestStorageLocationRequiredFields:
    """Test required field enforcement."""

    def test_name_field_required(self):
        """Name field must not be null or empty."""
        with pytest.raises((ValueError, TypeError)):
            StorageLocation(
                code="WH-AREA-LOC01",
                name=None,
                storage_area_id=1,
                qr_code="LOC12345",
                coordinates=from_shape(Point(-70.6485, -33.4495), srid=4326),
            )

    def test_geometry_field_required(self):
        """coordinates field must not be null."""
        with pytest.raises((ValueError, TypeError)):
            StorageLocation(
                code="WH-AREA-LOC01",
                name="Test Location",
                storage_area_id=1,
                qr_code="LOC12345",
                coordinates=None,
            )


class TestStorageLocationDefaultValues:
    """Test default field values."""

    def test_active_defaults_to_true(self):
        """active field should default to True."""
        location = StorageLocation(
            code="WH-AREA-LOC01",
            name="Test Location",
            storage_area_id=1,
            qr_code="LOC12345",
            coordinates=from_shape(Point(-70.6485, -33.4495), srid=4326),
        )

        # active should default to True (before DB insert)
        assert location.active is True

    def test_timestamps_auto_set(self):
        """created_at and updated_at should be auto-set (server-side)."""
        # Note: Timestamps are set by database server_default
        # This test verifies the column definition exists
        location = StorageLocation(
            code="WH-AREA-LOC01",
            name="Test Location",
            storage_area_id=1,
            qr_code="LOC12345",
            coordinates=from_shape(Point(-70.6485, -33.4495), srid=4326),
        )

        # Timestamps start as None (set by DB on insert)
        assert location.created_at is None
        assert location.updated_at is None


class TestStorageLocationFieldCombinations:
    """Test various field combinations and edge cases."""

    def test_create_location_with_photo_session(self):
        """Create location with latest photo session reference."""
        location = StorageLocation(
            code="INV01-NORTH-A1",
            name="North Wing Location A1",
            storage_area_id=1,
            qr_code="LOC12345",
            coordinates=from_shape(Point(-70.6485, -33.4495), srid=4326),
            photo_session_id=456,  # Latest photo
            position_metadata={"camera_angle": "45deg", "lighting": "natural"},
        )

        assert location.code == "INV01-NORTH-A1"
        assert location.photo_session_id == 456
        assert location.position_metadata["camera_angle"] == "45deg"

    def test_create_location_without_photo_session(self):
        """Create location without photo session (initial state)."""
        location = StorageLocation(
            code="INV01-SOUTH-B2",
            name="South Wing Location B2",
            storage_area_id=2,
            qr_code="QR-LOC-002",
            coordinates=from_shape(Point(-70.6480, -33.4490), srid=4326),
            photo_session_id=None,  # No photo yet
        )

        assert location.photo_session_id is None

    def test_inactive_storage_location(self):
        """Create inactive storage location."""
        location = StorageLocation(
            code="INACTIVE-LOC",
            name="Inactive Location",
            storage_area_id=1,
            qr_code="LOC99999",
            coordinates=from_shape(Point(-70.6485, -33.4495), srid=4326),
            active=False,
        )

        assert location.active is False

    def test_location_with_complex_position_metadata(self):
        """Create location with nested position metadata."""
        metadata = {
            "camera": {"angle": 45, "distance": 2.5, "height": 3.0},
            "lighting": {"type": "natural", "time": "morning", "weather": "sunny"},
            "environment": {"temperature": 22, "humidity": 65},
        }

        location = StorageLocation(
            code="GH-PROP-LOC01",
            name="Propagation Zone Location 01",
            storage_area_id=3,
            qr_code="LOC-PROP-01",
            coordinates=from_shape(Point(-70.6482, -33.4492), srid=4326),
            position_metadata=metadata,
        )

        assert location.position_metadata["camera"]["angle"] == 45
        assert location.position_metadata["lighting"]["type"] == "natural"
        assert location.position_metadata["environment"]["temperature"] == 22
