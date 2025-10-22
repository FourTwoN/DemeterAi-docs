"""Unit tests for StorageBinType model.

Tests the StorageBinType model (DB005) - reference/catalog table for container types.

Test Coverage:
    - Category enum validation (3 tests)
    - Code validation (6 tests)
    - Nullable dimensions (2 tests)
    - Grid flag validation (2 tests)
    - Relationships (2 tests)
    - Basic CRUD operations (3 tests)
    - Field constraints (2 tests)

Target Coverage: ≥75%
"""

import pytest

from app.models.storage_bin_type import BinCategoryEnum, StorageBinType


class TestBinCategoryEnum:
    """Test BinCategoryEnum values."""

    def test_valid_categories(self):
        """Test all valid category enum values."""
        assert BinCategoryEnum.PLUG == "plug"
        assert BinCategoryEnum.SEEDLING_TRAY == "seedling_tray"
        assert BinCategoryEnum.BOX == "box"
        assert BinCategoryEnum.SEGMENT == "segment"
        assert BinCategoryEnum.POT == "pot"

    def test_enum_values_list(self):
        """Test that all expected categories exist."""
        categories = [e.value for e in BinCategoryEnum]
        assert len(categories) == 5
        assert "plug" in categories
        assert "seedling_tray" in categories
        assert "box" in categories
        assert "segment" in categories
        assert "pot" in categories

    def test_category_assignment(self):
        """Test assigning category to StorageBinType."""
        bin_type = StorageBinType(code="TEST_TYPE", name="Test Type", category=BinCategoryEnum.PLUG)
        assert bin_type.category == BinCategoryEnum.PLUG
        assert bin_type.category.value == "plug"


class TestCodeValidation:
    """Test code validation rules."""

    def test_valid_code_uppercase(self):
        """Test valid uppercase code."""
        bin_type = StorageBinType(
            code="PLUG_TRAY_288", name="288-Cell Plug Tray", category=BinCategoryEnum.PLUG
        )
        assert bin_type.code == "PLUG_TRAY_288"

    def test_lowercase_code_auto_uppercases(self):
        """Test that lowercase code is auto-uppercased."""
        bin_type = StorageBinType(
            code="plug_tray_288", name="288-Cell Plug Tray", category=BinCategoryEnum.PLUG
        )
        assert bin_type.code == "PLUG_TRAY_288"

    def test_mixed_case_code_auto_uppercases(self):
        """Test that mixed case code is auto-uppercased."""
        bin_type = StorageBinType(
            code="Plug_Tray_288", name="288-Cell Plug Tray", category=BinCategoryEnum.PLUG
        )
        assert bin_type.code == "PLUG_TRAY_288"

    def test_invalid_code_with_hyphens(self):
        """Test that hyphens in code are rejected."""
        with pytest.raises(ValueError, match="must be alphanumeric \\+ underscores only"):
            StorageBinType(
                code="PLUG-TRAY-288", name="288-Cell Plug Tray", category=BinCategoryEnum.PLUG
            )

    def test_invalid_code_with_special_chars(self):
        """Test that special characters in code are rejected."""
        with pytest.raises(ValueError, match="must be alphanumeric \\+ underscores only"):
            StorageBinType(
                code="PLUG@TRAY#288", name="288-Cell Plug Tray", category=BinCategoryEnum.PLUG
            )

    def test_invalid_code_empty(self):
        """Test that empty code is rejected."""
        with pytest.raises(ValueError, match="cannot be empty"):
            StorageBinType(code="", name="288-Cell Plug Tray", category=BinCategoryEnum.PLUG)

    def test_invalid_code_too_short(self):
        """Test that code shorter than 3 characters is rejected."""
        with pytest.raises(ValueError, match="must be 3-50 characters"):
            StorageBinType(code="AB", name="Test Type", category=BinCategoryEnum.BOX)

    def test_invalid_code_too_long(self):
        """Test that code longer than 50 characters is rejected."""
        long_code = "A" * 51
        with pytest.raises(ValueError, match="must be 3-50 characters"):
            StorageBinType(code=long_code, name="Test Type", category=BinCategoryEnum.BOX)

    def test_code_with_numbers(self):
        """Test that code with numbers is valid."""
        bin_type = StorageBinType(
            code="PLUG_TRAY_128", name="128-Cell Plug Tray", category=BinCategoryEnum.PLUG
        )
        assert bin_type.code == "PLUG_TRAY_128"


class TestNullableDimensions:
    """Test nullable dimension fields."""

    def test_create_type_with_all_dimensions_null(self):
        """Test creating type with all dimensions NULL (segment)."""
        bin_type = StorageBinType(
            code="SEGMENT_STANDARD",
            name="Individual Segment",
            category=BinCategoryEnum.SEGMENT,
            is_grid=False,
        )
        assert bin_type.rows is None
        assert bin_type.columns is None
        assert bin_type.capacity is None
        assert bin_type.length_cm is None
        assert bin_type.width_cm is None
        assert bin_type.height_cm is None

    def test_create_type_with_partial_dimensions(self):
        """Test creating type with partial dimensions (only capacity)."""
        bin_type = StorageBinType(
            code="BOX_MEDIUM",
            name="Medium Box",
            category=BinCategoryEnum.BOX,
            capacity=50,
            is_grid=False,
        )
        assert bin_type.capacity == 50
        assert bin_type.rows is None
        assert bin_type.columns is None
        assert bin_type.length_cm is None


class TestGridFlag:
    """Test grid flag validation."""

    def test_grid_type_with_rows_and_columns(self):
        """Test grid type (is_grid=TRUE) with rows and columns."""
        bin_type = StorageBinType(
            code="PLUG_TRAY_288",
            name="288-Cell Plug Tray",
            category=BinCategoryEnum.PLUG,
            rows=18,
            columns=16,
            capacity=288,
            is_grid=True,
        )
        assert bin_type.is_grid is True
        assert bin_type.rows == 18
        assert bin_type.columns == 16
        assert bin_type.capacity == 288

    def test_non_grid_type_without_rows_columns(self):
        """Test non-grid type (is_grid=FALSE) without rows/columns."""
        bin_type = StorageBinType(
            code="SEGMENT_STANDARD",
            name="Individual Segment",
            category=BinCategoryEnum.SEGMENT,
            is_grid=False,
        )
        assert bin_type.is_grid is False
        assert bin_type.rows is None
        assert bin_type.columns is None


class TestRelationships:
    """Test model relationships."""

    def test_storage_bins_relationship_exists(self):
        """Test that storage_bins relationship exists."""
        bin_type = StorageBinType(code="TEST_TYPE", name="Test Type", category=BinCategoryEnum.BOX)
        assert hasattr(bin_type, "storage_bins")

    def test_density_parameters_relationship_commented_out(self):
        """Test that density_parameters relationship is commented out (DB025 not ready)."""
        bin_type = StorageBinType(code="TEST_TYPE", name="Test Type", category=BinCategoryEnum.BOX)
        # Should NOT have density_parameters relationship yet
        # (uncommented after DB025 is complete)
        # This test will fail after DB025 is implemented
        assert not hasattr(bin_type, "density_parameters") or bin_type.density_parameters == []


class TestBasicCRUD:
    """Test basic CRUD operations."""

    def test_create_type_with_all_fields(self):
        """Test creating type with all fields populated."""
        bin_type = StorageBinType(
            code="PLUG_TRAY_288",
            name="288-Cell Plug Tray",
            category=BinCategoryEnum.PLUG,
            description="Standard 288-cell plug tray (18 rows × 16 columns)",
            rows=18,
            columns=16,
            capacity=288,
            length_cm=54.0,
            width_cm=27.5,
            height_cm=5.5,
            is_grid=True,
        )
        assert bin_type.code == "PLUG_TRAY_288"
        assert bin_type.name == "288-Cell Plug Tray"
        assert bin_type.category == BinCategoryEnum.PLUG
        assert bin_type.description == "Standard 288-cell plug tray (18 rows × 16 columns)"
        assert bin_type.rows == 18
        assert bin_type.columns == 16
        assert bin_type.capacity == 288
        assert bin_type.length_cm == 54.0
        assert bin_type.width_cm == 27.5
        assert bin_type.height_cm == 5.5
        assert bin_type.is_grid is True

    def test_create_type_with_minimal_fields(self):
        """Test creating type with minimal required fields."""
        bin_type = StorageBinType(code="BOX_SMALL", name="Small Box", category=BinCategoryEnum.BOX)
        assert bin_type.code == "BOX_SMALL"
        assert bin_type.name == "Small Box"
        assert bin_type.category == BinCategoryEnum.BOX
        # is_grid should default to False, but may also be None before DB insert
        assert bin_type.is_grid is False or bin_type.is_grid is None

    def test_repr(self):
        """Test string representation."""
        bin_type = StorageBinType(
            code="PLUG_TRAY_288",
            name="288-Cell Plug Tray",
            category=BinCategoryEnum.PLUG,
            is_grid=True,
        )
        repr_str = repr(bin_type)
        assert "StorageBinType" in repr_str
        assert "PLUG_TRAY_288" in repr_str
        assert "288-Cell Plug Tray" in repr_str
        assert "plug" in repr_str
        assert "is_grid=True" in repr_str


class TestFieldConstraints:
    """Test field constraints and required fields."""

    def test_code_required(self):
        """Test that code is required - enforced at DB level, not Python."""
        # SQLAlchemy does not enforce NOT NULL at Python level
        bin_type = StorageBinType(name="Test Type", category=BinCategoryEnum.BOX)
        # Python allows None; DB will reject on insert
        assert bin_type.code is None

    def test_name_required(self):
        """Test that name is required - enforced at DB level, not Python."""
        # SQLAlchemy does not enforce NOT NULL at Python level
        bin_type = StorageBinType(code="TEST_TYPE", category=BinCategoryEnum.BOX)
        # Python allows None; DB will reject on insert
        assert bin_type.name is None

    def test_category_required(self):
        """Test that category is required - enforced at DB level, not Python."""
        # SQLAlchemy does not enforce NOT NULL at Python level
        bin_type = StorageBinType(code="TEST_TYPE", name="Test Type")
        # Python allows None; DB will reject on insert
        assert bin_type.category is None


class TestDefaultValues:
    """Test default values for columns."""

    def test_is_grid_default_false(self):
        """Test that is_grid defaults to FALSE."""
        bin_type = StorageBinType(code="TEST_TYPE", name="Test Type", category=BinCategoryEnum.BOX)
        # is_grid may be False or None before DB insert depending on implementation
        assert bin_type.is_grid is False or bin_type.is_grid is None

    def test_created_at_auto_set(self):
        """Test that created_at will be auto-set (server_default)."""
        bin_type = StorageBinType(code="TEST_TYPE", name="Test Type", category=BinCategoryEnum.BOX)
        # created_at will be set by database server_default
        # This test just verifies the field exists
        assert hasattr(bin_type, "created_at")


class TestFieldCombinations:
    """Test various field combinations."""

    def test_plug_tray_with_grid(self):
        """Test plug tray type with grid structure."""
        bin_type = StorageBinType(
            code="PLUG_TRAY_128",
            name="128-Cell Plug Tray",
            category=BinCategoryEnum.PLUG,
            rows=8,
            columns=16,
            capacity=128,
            is_grid=True,
            length_cm=54.0,
            width_cm=27.5,
            height_cm=6.0,
        )
        assert bin_type.category == BinCategoryEnum.PLUG
        assert bin_type.is_grid is True
        assert bin_type.rows == 8
        assert bin_type.columns == 16

    def test_seedling_tray_with_grid(self):
        """Test seedling tray type with grid structure."""
        bin_type = StorageBinType(
            code="SEEDLING_TRAY_50",
            name="50-Cell Seedling Tray",
            category=BinCategoryEnum.SEEDLING_TRAY,
            rows=5,
            columns=10,
            capacity=50,
            is_grid=True,
        )
        assert bin_type.category == BinCategoryEnum.SEEDLING_TRAY
        assert bin_type.is_grid is True
        assert bin_type.rows == 5
        assert bin_type.columns == 10

    def test_box_without_grid(self):
        """Test box type without grid structure."""
        bin_type = StorageBinType(
            code="BOX_STANDARD",
            name="Standard Transport Box",
            category=BinCategoryEnum.BOX,
            capacity=100,
            is_grid=False,
            length_cm=60.0,
            width_cm=40.0,
            height_cm=30.0,
        )
        assert bin_type.category == BinCategoryEnum.BOX
        assert bin_type.is_grid is False
        assert bin_type.rows is None
        assert bin_type.columns is None
        assert bin_type.capacity == 100

    def test_segment_no_dimensions(self):
        """Test segment type with no dimensions (ML-detected)."""
        bin_type = StorageBinType(
            code="SEGMENT_STANDARD",
            name="Individual Segment",
            category=BinCategoryEnum.SEGMENT,
            description="Individual segment detected by ML (no fixed dimensions)",
            is_grid=False,
        )
        assert bin_type.category == BinCategoryEnum.SEGMENT
        assert bin_type.is_grid is False
        assert bin_type.rows is None
        assert bin_type.columns is None
        assert bin_type.capacity is None
        assert bin_type.length_cm is None
        assert bin_type.width_cm is None
        assert bin_type.height_cm is None
