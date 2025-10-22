"""Unit tests for Warehouse model validation logic.

These tests focus on validation logic and do NOT require a database connection.
They test:
- Code validation (uppercase, alphanumeric, length)
- Enum validation (warehouse types)
- Required fields enforcement
- Default values
- Geometry assignment from Shapely

Integration tests with full database stack are in tests/integration/models/
"""

import pytest
from geoalchemy2.shape import from_shape
from shapely.geometry import Polygon
from sqlalchemy.exc import StatementError

# Note: Import will work once Python Expert completes the model
# For now, tests will be skipped if model doesn't exist
pytest.importorskip("app.models.warehouse", reason="Warehouse model not yet implemented")

from app.models.warehouse import Warehouse  # noqa: E402


class TestWarehouseCodeValidation:
    """Test code field validation rules."""

    def test_warehouse_code_uppercase_enforced(self):
        """Code must be uppercase - lowercase should be rejected."""
        warehouse = Warehouse(
            code="TEST01",  # Valid uppercase
            name="Test Warehouse",
            warehouse_type="greenhouse",
            geojson_geojson_coordinates=from_shape(
                Polygon(
                    [
                        (-70.648, -33.449),
                        (-70.647, -33.449),
                        (-70.647, -33.450),
                        (-70.648, -33.450),
                        (-70.648, -33.449),
                    ]
                ),
                srid=4326,
            ),
        )

        # Lowercase should raise ValueError
        with pytest.raises(ValueError, match="must be uppercase"):
            warehouse.code = "test01"

    def test_warehouse_code_alphanumeric_only(self):
        """Code must be alphanumeric (plus hyphen/underscore)."""
        warehouse = Warehouse(
            code="TEST-01",
            name="Test Warehouse",
            warehouse_type="greenhouse",
            geojson_geojson_coordinates=from_shape(
                Polygon(
                    [
                        (-70.648, -33.449),
                        (-70.647, -33.449),
                        (-70.647, -33.450),
                        (-70.648, -33.450),
                        (-70.648, -33.449),
                    ]
                ),
                srid=4326,
            ),
        )

        # Valid patterns
        warehouse.code = "TEST_01"  # Should not raise
        warehouse.code = "TEST-WAREHOUSE-01"  # Should not raise

        # Special chars should fail
        with pytest.raises(ValueError, match="alphanumeric"):
            warehouse.code = "TEST@01"

        with pytest.raises(ValueError, match="alphanumeric"):
            warehouse.code = "TEST#01"

        with pytest.raises(ValueError, match="alphanumeric"):
            warehouse.code = "TEST 01"  # Space not allowed

    def test_warehouse_code_length_validation(self):
        """Code must be 2-20 characters."""
        warehouse = Warehouse(
            code="AB",  # Minimum 2 chars
            name="Test Warehouse",
            warehouse_type="greenhouse",
            geojson_geojson_coordinates=from_shape(
                Polygon(
                    [
                        (-70.648, -33.449),
                        (-70.647, -33.449),
                        (-70.647, -33.450),
                        (-70.648, -33.450),
                        (-70.648, -33.449),
                    ]
                ),
                srid=4326,
            ),
        )

        # Valid lengths
        warehouse.code = "AB"  # Min (2)
        warehouse.code = "ABCDEFGHIJ1234567890"  # Max (20)

        # Too short
        with pytest.raises(ValueError, match="2-20 characters"):
            warehouse.code = "A"

        # Too long
        with pytest.raises(ValueError, match="2-20 characters"):
            warehouse.code = "A" * 21

    def test_warehouse_code_required(self):
        """Code field is required (not nullable)."""
        with pytest.raises(ValueError, match="required"):
            Warehouse(
                code=None,  # Should fail
                name="Test Warehouse",
                warehouse_type="greenhouse",
            )

        with pytest.raises(ValueError, match="required"):
            warehouse = Warehouse(code="TEST01", name="Test Warehouse", warehouse_type="greenhouse")
            warehouse.code = None  # Should fail

    def test_warehouse_code_empty_string(self):
        """Empty string code should be rejected."""
        with pytest.raises(ValueError, match="required"):
            warehouse = Warehouse(code="TEST01", name="Test Warehouse", warehouse_type="greenhouse")
            warehouse.code = ""


class TestWarehouseTypeEnum:
    """Test warehouse_type enum validation."""

    def test_warehouse_type_enum_valid_values(self):
        """Valid warehouse types should be accepted."""
        valid_types = ["greenhouse", "shadehouse", "open_field", "tunnel"]

        for wtype in valid_types:
            warehouse = Warehouse(
                code="TEST01",
                name="Test Warehouse",
                warehouse_type=wtype,
                geojson_geojson_coordinates=from_shape(
                    Polygon(
                        [
                            (-70.648, -33.449),
                            (-70.647, -33.449),
                            (-70.647, -33.450),
                            (-70.648, -33.450),
                            (-70.648, -33.449),
                        ]
                    ),
                    srid=4326,
                ),
            )
            assert warehouse.warehouse_type == wtype

    def test_warehouse_type_enum_invalid_values(self):
        """Invalid warehouse types should be rejected."""
        invalid_types = ["factory", "storage", "warehouse", "building", ""]

        for invalid_type in invalid_types:
            with pytest.raises((ValueError, StatementError)):
                Warehouse(
                    code="TEST01",
                    name="Test Warehouse",
                    warehouse_type=invalid_type,
                    geojson_geojson_coordinates=from_shape(
                        Polygon(
                            [
                                (-70.648, -33.449),
                                (-70.647, -33.449),
                                (-70.647, -33.450),
                                (-70.648, -33.450),
                                (-70.648, -33.449),
                            ]
                        ),
                        srid=4326,
                    ),
                )

    def test_warehouse_type_required(self):
        """Warehouse type is required (not nullable)."""
        with pytest.raises((ValueError, TypeError)):
            Warehouse(code="TEST01", name="Test Warehouse", warehouse_type=None)


class TestWarehouseRequiredFields:
    """Test required field enforcement."""

    def test_name_field_required(self):
        """Name field must not be null or empty."""
        with pytest.raises((ValueError, TypeError)):
            Warehouse(code="TEST01", name=None, warehouse_type="greenhouse")

    def test_geometry_field_required(self):
        """geojson_coordinates field must not be null."""
        with pytest.raises((ValueError, TypeError)):
            Warehouse(
                code="TEST01",
                name="Test Warehouse",
                warehouse_type="greenhouse",
                geojson_geojson_coordinates=None,
            )


class TestWarehouseDefaultValues:
    """Test default field values."""

    def test_active_defaults_to_true(self):
        """active field should default to True."""
        warehouse = Warehouse(
            code="TEST01",
            name="Test Warehouse",
            warehouse_type="greenhouse",
            geojson_geojson_coordinates=from_shape(
                Polygon(
                    [
                        (-70.648, -33.449),
                        (-70.647, -33.449),
                        (-70.647, -33.450),
                        (-70.648, -33.450),
                        (-70.648, -33.449),
                    ]
                ),
                srid=4326,
            ),
        )

        # active should default to True (before DB insert)
        assert warehouse.active is True

    def test_timestamps_auto_set(self):
        """created_at and updated_at should be auto-set (server-side)."""
        # Note: Timestamps are set by database server_default
        # This test verifies the column definition exists
        warehouse = Warehouse(
            code="TEST01",
            name="Test Warehouse",
            warehouse_type="greenhouse",
            geojson_geojson_coordinates=from_shape(
                Polygon(
                    [
                        (-70.648, -33.449),
                        (-70.647, -33.449),
                        (-70.647, -33.450),
                        (-70.648, -33.450),
                        (-70.648, -33.449),
                    ]
                ),
                srid=4326,
            ),
        )

        # Timestamps start as None (set by DB on insert)
        assert warehouse.created_at is None
        assert warehouse.updated_at is None


class TestWarehouseGeometryAssignment:
    """Test PostGIS geometry field assignment."""

    def test_geometry_assignment_from_shapely_polygon(self):
        """Should accept Shapely Polygon via from_shape()."""
        coords = [
            (-70.648300, -33.448900),  # SW corner
            (-70.647300, -33.448900),  # SE corner
            (-70.647300, -33.449900),  # NE corner
            (-70.648300, -33.449900),  # NW corner
            (-70.648300, -33.448900),  # Close polygon
        ]
        polygon = Polygon(coords)

        warehouse = Warehouse(
            code="GEO01",
            name="Geometry Test Warehouse",
            warehouse_type="greenhouse",
            geojson_geojson_coordinates=from_shape(polygon, srid=4326),
        )

        assert warehouse.geojson_coordinates is not None

    def test_geometry_assignment_with_correct_srid(self):
        """Geometry must use SRID 4326 (WGS84)."""
        polygon = Polygon(
            [
                (-70.648, -33.449),
                (-70.647, -33.449),
                (-70.647, -33.450),
                (-70.648, -33.450),
                (-70.648, -33.449),
            ]
        )

        # SRID 4326 (WGS84) is required for GPS coordinates
        warehouse = Warehouse(
            code="SRID01",
            name="SRID Test",
            warehouse_type="greenhouse",
            geojson_geojson_coordinates=from_shape(polygon, srid=4326),
        )

        assert warehouse.geojson_coordinates is not None

    def test_geometry_complex_polygon(self):
        """Should handle complex polygons with many vertices."""
        # Create a more complex polygon (octagon)
        coords = [
            (-70.6483, -33.4492),
            (-70.6480, -33.4490),
            (-70.6477, -33.4490),
            (-70.6474, -33.4492),
            (-70.6474, -33.4495),
            (-70.6477, -33.4497),
            (-70.6480, -33.4497),
            (-70.6483, -33.4495),
            (-70.6483, -33.4492),  # Close
        ]
        polygon = Polygon(coords)

        warehouse = Warehouse(
            code="COMPLEX01",
            name="Complex Polygon Warehouse",
            warehouse_type="open_field",
            geojson_geojson_coordinates=from_shape(polygon, srid=4326),
        )

        assert warehouse.geojson_coordinates is not None


class TestWarehouseFieldCombinations:
    """Test various field combinations and edge cases."""

    def test_create_greenhouse_type(self):
        """Create warehouse with greenhouse type."""
        warehouse = Warehouse(
            code="GREENHOUSE-01",
            name="Main Greenhouse",
            warehouse_type="greenhouse",
            geojson_geojson_coordinates=from_shape(
                Polygon(
                    [
                        (-70.648, -33.449),
                        (-70.647, -33.449),
                        (-70.647, -33.450),
                        (-70.648, -33.450),
                        (-70.648, -33.449),
                    ]
                ),
                srid=4326,
            ),
            active=True,
        )

        assert warehouse.code == "GREENHOUSE-01"
        assert warehouse.warehouse_type == "greenhouse"

    def test_create_shadehouse_type(self):
        """Create warehouse with shadehouse type."""
        warehouse = Warehouse(
            code="SHADE-01",
            name="Shadehouse Zone A",
            warehouse_type="shadehouse",
            geojson_geojson_coordinates=from_shape(
                Polygon(
                    [
                        (-70.648, -33.449),
                        (-70.647, -33.449),
                        (-70.647, -33.450),
                        (-70.648, -33.450),
                        (-70.648, -33.449),
                    ]
                ),
                srid=4326,
            ),
        )

        assert warehouse.warehouse_type == "shadehouse"

    def test_create_open_field_type(self):
        """Create warehouse with open_field type."""
        warehouse = Warehouse(
            code="FIELD-01",
            name="Open Field North",
            warehouse_type="open_field",
            geojson_geojson_coordinates=from_shape(
                Polygon(
                    [
                        (-70.648, -33.449),
                        (-70.647, -33.449),
                        (-70.647, -33.450),
                        (-70.648, -33.450),
                        (-70.648, -33.449),
                    ]
                ),
                srid=4326,
            ),
        )

        assert warehouse.warehouse_type == "open_field"

    def test_create_tunnel_type(self):
        """Create warehouse with tunnel type."""
        warehouse = Warehouse(
            code="TUNNEL-01",
            name="Low Tunnel Section B",
            warehouse_type="tunnel",
            geojson_geojson_coordinates=from_shape(
                Polygon(
                    [
                        (-70.648, -33.449),
                        (-70.647, -33.449),
                        (-70.647, -33.450),
                        (-70.648, -33.450),
                        (-70.648, -33.449),
                    ]
                ),
                srid=4326,
            ),
        )

        assert warehouse.warehouse_type == "tunnel"

    def test_inactive_warehouse(self):
        """Create inactive warehouse."""
        warehouse = Warehouse(
            code="INACTIVE-01",
            name="Closed Warehouse",
            warehouse_type="greenhouse",
            geojson_geojson_coordinates=from_shape(
                Polygon(
                    [
                        (-70.648, -33.449),
                        (-70.647, -33.449),
                        (-70.647, -33.450),
                        (-70.648, -33.450),
                        (-70.648, -33.449),
                    ]
                ),
                srid=4326,
            ),
            active=False,
        )

        assert warehouse.active is False
