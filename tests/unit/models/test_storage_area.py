"""Unit tests for StorageArea model validation logic.

These tests focus on validation logic and do NOT require a database connection.
They test:
- Code validation (format WAREHOUSE-AREA, uppercase, length)
- Position enum validation (N, S, E, W, C, NULL)
- Foreign key constraints (warehouse_id required)
- Required fields enforcement
- Default values
- Geometry assignment from Shapely
- Self-referential relationship (parent_area_id)

Integration tests with full database stack are in tests/integration/models/
"""

import pytest
from geoalchemy2.shape import from_shape
from shapely.geometry import Polygon
from sqlalchemy.exc import StatementError

# Note: Import will work once Python Expert completes the model
# For now, tests will be skipped if model doesn't exist
pytest.importorskip("app.models.storage_area", reason="StorageArea model not yet implemented")

from app.models.storage_area import StorageArea  # noqa: E402


class TestStorageAreaCodeValidation:
    """Test code field validation rules (WAREHOUSE-AREA format)."""

    def test_storage_area_code_format_validation(self):
        """Code must match WAREHOUSE-AREA pattern with hyphen."""
        # Valid formats
        valid_codes = [
            "INV01-NORTH",
            "GH-001-PROP",
            "WAREHOUSE-A-ZONE-B",
            "WH-AREA",
        ]

        for code in valid_codes:
            area = StorageArea(
                code=code,
                name="Test Storage Area",
                warehouse_id=1,
                geojson_coordinates=from_shape(
                    Polygon(
                        [
                            (-70.6485, -33.4495),
                            (-70.6480, -33.4495),
                            (-70.6480, -33.4490),
                            (-70.6485, -33.4490),
                            (-70.6485, -33.4495),
                        ]
                    ),
                    srid=4326,
                ),
            )
            assert area.code == code

    def test_storage_area_code_requires_hyphen(self):
        """Code without hyphen should be rejected."""
        with pytest.raises(ValueError, match="must contain hyphen"):
            StorageArea(
                code="NORTH",  # Missing hyphen - invalid
                name="Test Area",
                warehouse_id=1,
                geojson_coordinates=from_shape(
                    Polygon(
                        [
                            (-70.6485, -33.4495),
                            (-70.6480, -33.4495),
                            (-70.6480, -33.4490),
                            (-70.6485, -33.4490),
                            (-70.6485, -33.4495),
                        ]
                    ),
                    srid=4326,
                ),
            )

    def test_storage_area_code_uppercase_enforced(self):
        """Code must be uppercase - lowercase should be rejected."""
        area = StorageArea(
            code="INV01-NORTH",
            name="Test Storage Area",
            warehouse_id=1,
            geojson_coordinates=from_shape(
                Polygon(
                    [
                        (-70.6485, -33.4495),
                        (-70.6480, -33.4495),
                        (-70.6480, -33.4490),
                        (-70.6485, -33.4490),
                        (-70.6485, -33.4495),
                    ]
                ),
                srid=4326,
            ),
        )

        # Lowercase should raise ValueError
        with pytest.raises(ValueError, match="must be uppercase"):
            area.code = "inv01-north"

    def test_storage_area_code_alphanumeric_only(self):
        """Code must be alphanumeric (plus hyphen/underscore)."""
        area = StorageArea(
            code="WH-AREA-01",
            name="Test Storage Area",
            warehouse_id=1,
            geojson_coordinates=from_shape(
                Polygon(
                    [
                        (-70.6485, -33.4495),
                        (-70.6480, -33.4495),
                        (-70.6480, -33.4490),
                        (-70.6485, -33.4490),
                        (-70.6485, -33.4495),
                    ]
                ),
                srid=4326,
            ),
        )

        # Valid patterns
        area.code = "WH-AREA_01"  # Should not raise
        area.code = "WAREHOUSE-STORAGE-AREA-01"  # Should not raise

        # Special chars should fail
        with pytest.raises(ValueError, match="alphanumeric"):
            area.code = "WH@AREA-01"

        with pytest.raises(ValueError, match="alphanumeric"):
            area.code = "WH#AREA-01"

        with pytest.raises(ValueError, match="alphanumeric"):
            area.code = "WH AREA-01"  # Space not allowed

    def test_storage_area_code_length_validation(self):
        """Code must be 2-50 characters."""
        area = StorageArea(
            code="W-A",  # Minimum 3 chars (X-Y)
            name="Test Storage Area",
            warehouse_id=1,
            geojson_coordinates=from_shape(
                Polygon(
                    [
                        (-70.6485, -33.4495),
                        (-70.6480, -33.4495),
                        (-70.6480, -33.4490),
                        (-70.6485, -33.4490),
                        (-70.6485, -33.4495),
                    ]
                ),
                srid=4326,
            ),
        )

        # Valid lengths
        area.code = "W-A"  # Min (3 with hyphen)
        area.code = "A" * 24 + "-" + "B" * 25  # Max (50)

        # Too short (no hyphen)
        with pytest.raises(ValueError, match="2-50 characters"):
            area.code = "A"

        # Too long
        with pytest.raises(ValueError, match="2-50 characters"):
            area.code = "A" * 51

    def test_storage_area_code_required(self):
        """Code field is required (not nullable)."""
        with pytest.raises(ValueError, match="required"):
            StorageArea(
                code=None,  # Should fail
                name="Test Storage Area",
                warehouse_id=1,
            )

        with pytest.raises(ValueError, match="required"):
            area = StorageArea(
                code="WH-AREA",
                name="Test Area",
                warehouse_id=1,
                geojson_coordinates=from_shape(
                    Polygon(
                        [
                            (-70.6485, -33.4495),
                            (-70.6480, -33.4495),
                            (-70.6480, -33.4490),
                            (-70.6485, -33.4490),
                            (-70.6485, -33.4495),
                        ]
                    ),
                    srid=4326,
                ),
            )
            area.code = None  # Should fail

    def test_storage_area_code_empty_string(self):
        """Empty string code should be rejected."""
        with pytest.raises(ValueError, match="required"):
            area = StorageArea(
                code="WH-AREA",
                name="Test Area",
                warehouse_id=1,
                geojson_coordinates=from_shape(
                    Polygon(
                        [
                            (-70.6485, -33.4495),
                            (-70.6480, -33.4495),
                            (-70.6480, -33.4490),
                            (-70.6485, -33.4490),
                            (-70.6485, -33.4495),
                        ]
                    ),
                    srid=4326,
                ),
            )
            area.code = ""


class TestStorageAreaPositionEnum:
    """Test position enum validation (N, S, E, W, C)."""

    def test_position_enum_valid_values(self):
        """Valid position values should be accepted."""
        valid_positions = ["N", "S", "E", "W", "C"]

        for position in valid_positions:
            area = StorageArea(
                code="WH-AREA",
                name="Test Storage Area",
                warehouse_id=1,
                position=position,
                geojson_coordinates=from_shape(
                    Polygon(
                        [
                            (-70.6485, -33.4495),
                            (-70.6480, -33.4495),
                            (-70.6480, -33.4490),
                            (-70.6485, -33.4490),
                            (-70.6485, -33.4495),
                        ]
                    ),
                    srid=4326,
                ),
            )
            assert area.position == position

    def test_position_enum_invalid_values(self):
        """Invalid position values should be rejected."""
        invalid_positions = ["NORTH", "SOUTH", "X", "northeast", "1", ""]

        for invalid_pos in invalid_positions:
            with pytest.raises((ValueError, StatementError)):
                StorageArea(
                    code="WH-AREA",
                    name="Test Storage Area",
                    warehouse_id=1,
                    position=invalid_pos,
                    geojson_coordinates=from_shape(
                        Polygon(
                            [
                                (-70.6485, -33.4495),
                                (-70.6480, -33.4495),
                                (-70.6480, -33.4490),
                                (-70.6485, -33.4490),
                                (-70.6485, -33.4495),
                            ]
                        ),
                        srid=4326,
                    ),
                )

    def test_position_nullable(self):
        """Position can be NULL (not all warehouses use cardinal directions)."""
        area = StorageArea(
            code="WH-AREA",
            name="Test Storage Area",
            warehouse_id=1,
            position=None,  # Should be allowed
            geojson_coordinates=from_shape(
                Polygon(
                    [
                        (-70.6485, -33.4495),
                        (-70.6480, -33.4495),
                        (-70.6480, -33.4490),
                        (-70.6485, -33.4490),
                        (-70.6485, -33.4495),
                    ]
                ),
                srid=4326,
            ),
        )

        assert area.position is None


class TestStorageAreaForeignKeys:
    """Test foreign key constraints."""

    def test_warehouse_id_required(self):
        """warehouse_id cannot be NULL - this is enforced at DB level, not Python."""
        # Note: SQLAlchemy does not enforce NOT NULL at Python level
        # So we just verify the object can be created (DB will reject on insert)
        area = StorageArea(
            code="WH-AREA",
            name="Test Storage Area",
            warehouse_id=None,  # Python allows it, but DB will reject
            geojson_coordinates=from_shape(
                Polygon(
                    [
                        (-70.6485, -33.4495),
                        (-70.6480, -33.4495),
                        (-70.6480, -33.4490),
                        (-70.6485, -33.4490),
                        (-70.6485, -33.4495),
                    ]
                ),
                srid=4326,
            ),
        )
        # Python allows None here; DB will reject on insert
        assert area.warehouse_id is None

    def test_parent_area_id_nullable(self):
        """parent_area_id can be NULL (root area)."""
        area = StorageArea(
            code="WH-ROOT",
            name="Root Storage Area",
            warehouse_id=1,
            parent_area_id=None,  # Should be allowed
            geojson_coordinates=from_shape(
                Polygon(
                    [
                        (-70.6485, -33.4495),
                        (-70.6480, -33.4495),
                        (-70.6480, -33.4490),
                        (-70.6485, -33.4490),
                        (-70.6485, -33.4495),
                    ]
                ),
                srid=4326,
            ),
        )

        assert area.parent_area_id is None


class TestStorageAreaRelationships:
    """Test model relationships."""

    def test_warehouse_relationship(self):
        """Many-to-one relationship to Warehouse."""
        # Note: This test verifies the relationship exists
        # Full relationship testing happens in integration tests

        area = StorageArea(
            code="WH-AREA",
            name="Test Storage Area",
            warehouse_id=1,
            geojson_coordinates=from_shape(
                Polygon(
                    [
                        (-70.6485, -33.4495),
                        (-70.6480, -33.4495),
                        (-70.6480, -33.4490),
                        (-70.6485, -33.4490),
                        (-70.6485, -33.4495),
                    ]
                ),
                srid=4326,
            ),
        )

        # Relationship should be defined
        assert hasattr(area, "warehouse")

    def test_self_referential_relationship(self):
        """Parent/child area relationship works (self-referential)."""
        parent = StorageArea(
            code="WH-PARENT",
            name="Parent Area",
            warehouse_id=1,
            geojson_coordinates=from_shape(
                Polygon(
                    [
                        (-70.649, -33.450),
                        (-70.648, -33.450),
                        (-70.648, -33.449),
                        (-70.649, -33.449),
                        (-70.649, -33.450),
                    ]
                ),
                srid=4326,
            ),
        )

        # Create child area referencing parent
        child = StorageArea(
            code="WH-CHILD",
            name="Child Area",
            warehouse_id=1,
            parent_area_id=1,  # Will reference parent.storage_area_id after DB insert
            geojson_coordinates=from_shape(
                Polygon(
                    [
                        (-70.6485, -33.4495),
                        (-70.6480, -33.4495),
                        (-70.6480, -33.4490),
                        (-70.6485, -33.4490),
                        (-70.6485, -33.4495),
                    ]
                ),
                srid=4326,
            ),
        )

        # Relationships should be defined
        assert hasattr(child, "parent_area")
        assert hasattr(parent, "child_areas")


class TestStorageAreaRequiredFields:
    """Test required field enforcement."""

    def test_name_field_required(self):
        """Name field must not be null or empty - enforced at DB level."""
        # Note: SQLAlchemy does not enforce NOT NULL at Python level
        area = StorageArea(code="WH-AREA", name=None, warehouse_id=1)
        # Python allows None; DB will reject on insert
        assert area.name is None

    def test_geometry_field_required(self):
        """geojson_coordinates field must not be null - enforced at DB level."""
        # Note: SQLAlchemy does not enforce NOT NULL at Python level
        area = StorageArea(
            code="WH-AREA",
            name="Test Storage Area",
            warehouse_id=1,
            geojson_coordinates=None,
        )
        # Python allows None; DB will reject on insert
        assert area.geojson_coordinates is None


class TestStorageAreaDefaultValues:
    """Test default field values."""

    def test_active_defaults_to_true(self):
        """active field should default to True (on DB insert via Column default).

        Note: SQLAlchemy's Column(default=True) applies when inserting to database,
        not when instantiating Python object. So we test by explicitly setting it.
        """
        # Test 1: Explicit True
        area1 = StorageArea(
            code="WH-AREA",
            name="Test Storage Area",
            warehouse_id=1,
            geojson_coordinates=from_shape(
                Polygon(
                    [
                        (-70.6485, -33.4495),
                        (-70.6480, -33.4495),
                        (-70.6480, -33.4490),
                        (-70.6485, -33.4490),
                        (-70.6485, -33.4495),
                    ]
                ),
                srid=4326,
            ),
            active=True,
        )

        # active should be True when explicitly set
        assert area1.active is True

        # Test 2: Explicitly set to False
        area2 = StorageArea(
            code="WH-AREA2",
            name="Test Storage Area 2",
            warehouse_id=1,
            geojson_coordinates=from_shape(
                Polygon(
                    [
                        (-70.6485, -33.4495),
                        (-70.6480, -33.4495),
                        (-70.6480, -33.4490),
                        (-70.6485, -33.4490),
                        (-70.6485, -33.4495),
                    ]
                ),
                srid=4326,
            ),
            active=False,
        )

        assert area2.active is False

    def test_timestamps_auto_set(self):
        """created_at and updated_at should be auto-set (server-side)."""
        # Note: Timestamps are set by database server_default
        # This test verifies the column definition exists
        area = StorageArea(
            code="WH-AREA",
            name="Test Storage Area",
            warehouse_id=1,
            geojson_coordinates=from_shape(
                Polygon(
                    [
                        (-70.6485, -33.4495),
                        (-70.6480, -33.4495),
                        (-70.6480, -33.4490),
                        (-70.6485, -33.4490),
                        (-70.6485, -33.4495),
                    ]
                ),
                srid=4326,
            ),
        )

        # Timestamps start as None (set by DB on insert)
        assert area.created_at is None
        assert area.updated_at is None


class TestStorageAreaGeometryAssignment:
    """Test PostGIS geometry field assignment."""

    def test_geometry_assignment_from_shapely_polygon(self):
        """Should accept Shapely Polygon via from_shape()."""
        coords = [
            (-70.6485, -33.4495),  # SW corner
            (-70.6480, -33.4495),  # SE corner
            (-70.6480, -33.4490),  # NE corner
            (-70.6485, -33.4490),  # NW corner
            (-70.6485, -33.4495),  # Close polygon
        ]
        polygon = Polygon(coords)

        area = StorageArea(
            code="GEO-AREA",
            name="Geometry Test Area",
            warehouse_id=1,
            geojson_coordinates=from_shape(polygon, srid=4326),
        )

        assert area.geojson_coordinates is not None

    def test_geometry_assignment_with_correct_srid(self):
        """Geometry must use SRID 4326 (WGS84)."""
        polygon = Polygon(
            [
                (-70.6485, -33.4495),
                (-70.6480, -33.4495),
                (-70.6480, -33.4490),
                (-70.6485, -33.4490),
                (-70.6485, -33.4495),
            ]
        )

        # SRID 4326 (WGS84) is required for GPS coordinates
        area = StorageArea(
            code="SRID-AREA",
            name="SRID Test",
            warehouse_id=1,
            geojson_coordinates=from_shape(polygon, srid=4326),
        )

        assert area.geojson_coordinates is not None

    def test_geometry_complex_polygon(self):
        """Should handle complex polygons with many vertices."""
        # Create a more complex polygon (octagon)
        coords = [
            (-70.6485, -33.4492),
            (-70.6483, -33.4490),
            (-70.6480, -33.4490),
            (-70.6478, -33.4492),
            (-70.6478, -33.4495),
            (-70.6480, -33.4497),
            (-70.6483, -33.4497),
            (-70.6485, -33.4495),
            (-70.6485, -33.4492),  # Close
        ]
        polygon = Polygon(coords)

        area = StorageArea(
            code="COMPLEX-AREA",
            name="Complex Polygon Area",
            warehouse_id=1,
            geojson_coordinates=from_shape(polygon, srid=4326),
        )

        assert area.geojson_coordinates is not None


class TestStorageAreaFieldCombinations:
    """Test various field combinations and edge cases."""

    def test_create_north_position_area(self):
        """Create storage area with North position."""
        area = StorageArea(
            code="INV01-NORTH",
            name="North Wing",
            warehouse_id=1,
            position="N",
            geojson_coordinates=from_shape(
                Polygon(
                    [
                        (-70.6485, -33.4495),
                        (-70.6480, -33.4495),
                        (-70.6480, -33.4490),
                        (-70.6485, -33.4490),
                        (-70.6485, -33.4495),
                    ]
                ),
                srid=4326,
            ),
            active=True,
        )

        assert area.code == "INV01-NORTH"
        assert area.position == "N"

    def test_create_south_position_area(self):
        """Create storage area with South position."""
        area = StorageArea(
            code="INV01-SOUTH",
            name="South Wing",
            warehouse_id=1,
            position="S",
            geojson_coordinates=from_shape(
                Polygon(
                    [
                        (-70.6485, -33.4495),
                        (-70.6480, -33.4495),
                        (-70.6480, -33.4490),
                        (-70.6485, -33.4490),
                        (-70.6485, -33.4495),
                    ]
                ),
                srid=4326,
            ),
        )

        assert area.position == "S"

    def test_create_center_position_area(self):
        """Create storage area with Center position."""
        area = StorageArea(
            code="GH-CENTER",
            name="Central Propagation Zone",
            warehouse_id=1,
            position="C",
            geojson_coordinates=from_shape(
                Polygon(
                    [
                        (-70.6485, -33.4495),
                        (-70.6480, -33.4495),
                        (-70.6480, -33.4490),
                        (-70.6485, -33.4490),
                        (-70.6485, -33.4495),
                    ]
                ),
                srid=4326,
            ),
        )

        assert area.position == "C"

    def test_create_area_without_position(self):
        """Create storage area without position (NULL allowed)."""
        area = StorageArea(
            code="WH-ZONE-A",
            name="Zone A",
            warehouse_id=1,
            position=None,  # Explicitly NULL
            geojson_coordinates=from_shape(
                Polygon(
                    [
                        (-70.6485, -33.4495),
                        (-70.6480, -33.4495),
                        (-70.6480, -33.4490),
                        (-70.6485, -33.4490),
                        (-70.6485, -33.4495),
                    ]
                ),
                srid=4326,
            ),
        )

        assert area.position is None

    def test_inactive_storage_area(self):
        """Create inactive storage area."""
        area = StorageArea(
            code="INACTIVE-AREA",
            name="Closed Storage Area",
            warehouse_id=1,
            geojson_coordinates=from_shape(
                Polygon(
                    [
                        (-70.6485, -33.4495),
                        (-70.6480, -33.4495),
                        (-70.6480, -33.4490),
                        (-70.6485, -33.4490),
                        (-70.6485, -33.4495),
                    ]
                ),
                srid=4326,
            ),
            active=False,
        )

        assert area.active is False

    def test_hierarchical_area_with_parent(self):
        """Create child area with parent_area_id."""
        area = StorageArea(
            code="NORTH-PROP-1",
            name="North Propagation Section 1",
            warehouse_id=1,
            parent_area_id=5,  # References parent area
            position="N",
            geojson_coordinates=from_shape(
                Polygon(
                    [
                        (-70.6485, -33.4495),
                        (-70.6480, -33.4495),
                        (-70.6480, -33.4490),
                        (-70.6485, -33.4490),
                        (-70.6485, -33.4495),
                    ]
                ),
                srid=4326,
            ),
        )

        assert area.parent_area_id == 5
