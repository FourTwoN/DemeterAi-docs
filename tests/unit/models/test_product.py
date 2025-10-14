"""Unit tests for Product model.

Tests the Product SQLAlchemy model in isolation without database dependencies.
Covers model instantiation, SKU validation, JSONB custom_attributes, relationships, and business logic.

Test Coverage:
    - Model instantiation with valid data
    - SKU validation (length, format, uppercase conversion)
    - JSONB custom_attributes (default value, nested structures)
    - Family relationship (many-to-one)
    - Nullable fields (scientific_name, description)
    - Required fields (product_id, family_id, sku, common_name)
    - __repr__ method
    - Model attributes and types

Architecture:
    - Layer: Unit Tests (isolated model testing)
    - Dependencies: pytest, Product model
    - Pattern: AAA (Arrange-Act-Assert)

Usage:
    pytest tests/unit/models/test_product.py -v
    pytest tests/unit/models/test_product.py::TestProductModel::test_create_product_with_all_fields -v
    pytest tests/unit/models/test_product.py --cov=app.models.product --cov-report=term-missing
"""

import pytest

from app.models.product import Product


class TestProductModel:
    """Test suite for Product model instantiation and attributes."""

    def test_create_product_with_all_fields(self):
        """Test creating Product with all fields populated."""
        # Arrange & Act
        product = Product(
            product_id=1,
            family_id=1,
            sku="ECHEV-LOLA-001",
            common_name="Echeveria 'Lola'",
            scientific_name="Echeveria lilacina × Echeveria derenbergii",
            description="Compact rosette succulent with powdery blue-gray leaves",
            custom_attributes={
                "color": "blue-gray",
                "variegation": False,
                "growth_rate": "slow",
            },
        )

        # Assert
        assert product.product_id == 1
        assert product.family_id == 1
        assert product.sku == "ECHEV-LOLA-001"
        assert product.common_name == "Echeveria 'Lola'"
        assert product.scientific_name == "Echeveria lilacina × Echeveria derenbergii"
        assert product.description == "Compact rosette succulent with powdery blue-gray leaves"
        assert product.custom_attributes["color"] == "blue-gray"
        assert product.custom_attributes["variegation"] is False

    def test_create_product_minimal_required_fields(self):
        """Test creating Product with only required fields."""
        # Arrange & Act
        product = Product(family_id=2, sku="ALOE-VERA-001", common_name="Aloe Vera")

        # Assert
        assert product.family_id == 2
        assert product.sku == "ALOE-VERA-001"
        assert product.common_name == "Aloe Vera"
        assert product.scientific_name is None
        assert product.description is None
        assert product.custom_attributes == {}  # Default empty dict

    def test_common_name_required(self):
        """Test that common_name field is required."""
        # Arrange & Act
        product = Product(family_id=1, sku="TEST-001")

        # Assert - common_name is None (database will enforce NOT NULL)
        assert product.common_name is None
        assert product.family_id == 1

    def test_family_id_required(self):
        """Test that family_id field is required."""
        # Arrange & Act
        product = Product(sku="TEST-002", common_name="Test Product")

        # Assert - family_id is None (database will enforce NOT NULL)
        assert product.family_id is None
        assert product.common_name == "Test Product"

    def test_sku_required(self):
        """Test that SKU field is required."""
        # Arrange & Act
        product = Product(family_id=1, common_name="Test Product")

        # Assert - SKU is None (database will enforce NOT NULL)
        assert product.sku is None
        assert product.common_name == "Test Product"

    def test_scientific_name_nullable(self):
        """Test that scientific_name can be NULL."""
        # Arrange & Act
        product = Product(
            family_id=3, sku="GENERIC-001", common_name="Generic Product", scientific_name=None
        )

        # Assert
        assert product.scientific_name is None

    def test_description_nullable(self):
        """Test that description can be NULL."""
        # Arrange & Act
        product = Product(family_id=4, sku="TEST-003", common_name="Test Product", description=None)

        # Assert
        assert product.description is None


class TestProductSKUValidation:
    """Test suite for Product SKU validation logic."""

    def test_valid_sku_with_hyphens(self):
        """Test SKU with valid format (alphanumeric + hyphens)."""
        # Arrange & Act
        product = Product(family_id=1, sku="ECHEV-001", common_name="Echeveria")

        # Assert
        assert product.sku == "ECHEV-001"

    def test_valid_sku_multiple_hyphens(self):
        """Test SKU with multiple hyphens."""
        # Arrange & Act
        product = Product(family_id=1, sku="CACT-MAMM-123", common_name="Mammillaria")

        # Assert
        assert product.sku == "CACT-MAMM-123"

    def test_valid_sku_no_hyphen(self):
        """Test SKU with only alphanumeric characters (no hyphen)."""
        # Arrange & Act
        product = Product(family_id=2, sku="ALOE001", common_name="Aloe")

        # Assert
        assert product.sku == "ALOE001"

    def test_sku_uppercase_conversion(self):
        """Test that lowercase SKU is automatically converted to uppercase."""
        # Arrange & Act
        product = Product(family_id=1, sku="echev-lola-001", common_name="Echeveria Lola")

        # Assert
        assert product.sku == "ECHEV-LOLA-001"

    def test_sku_mixed_case_conversion(self):
        """Test that mixed case SKU is converted to uppercase."""
        # Arrange & Act
        product = Product(family_id=2, sku="Aloe-Vera-123", common_name="Aloe Vera")

        # Assert
        assert product.sku == "ALOE-VERA-123"

    def test_sku_minimum_length(self):
        """Test SKU with minimum valid length (6 chars)."""
        # Arrange & Act
        product = Product(family_id=1, sku="CACT01", common_name="Cactus")

        # Assert
        assert product.sku == "CACT01"
        assert len(product.sku) == 6

    def test_sku_maximum_length(self):
        """Test SKU with maximum valid length (20 chars)."""
        # Arrange & Act
        product = Product(family_id=1, sku="ECHEV-LOLA-XL-123456", common_name="Echeveria")

        # Assert
        assert product.sku == "ECHEV-LOLA-XL-123456"
        assert len(product.sku) == 20

    def test_sku_too_short_raises_error(self):
        """Test that SKU shorter than 6 chars raises ValueError."""
        # Arrange & Act & Assert
        with pytest.raises(ValueError, match="SKU must be 6-20 characters"):
            Product(family_id=1, sku="CACT", common_name="Cactus")

    def test_sku_too_long_raises_error(self):
        """Test that SKU longer than 20 chars raises ValueError."""
        # Arrange & Act & Assert
        with pytest.raises(ValueError, match="SKU must be 6-20 characters"):
            Product(family_id=1, sku="VERY-LONG-SKU-123456789", common_name="Test")

    def test_sku_invalid_characters_underscore(self):
        """Test that SKU with underscore raises ValueError."""
        # Arrange & Act & Assert
        with pytest.raises(ValueError, match="alphanumeric characters and hyphens"):
            Product(family_id=1, sku="ECHEV_001", common_name="Echeveria")

    def test_sku_invalid_characters_space(self):
        """Test that SKU with space raises ValueError."""
        # Arrange & Act & Assert
        with pytest.raises(ValueError, match="alphanumeric characters and hyphens"):
            Product(family_id=1, sku="ECHEV 001", common_name="Echeveria")

    def test_sku_invalid_characters_special(self):
        """Test that SKU with special characters raises ValueError."""
        # Arrange & Act & Assert
        with pytest.raises(ValueError, match="alphanumeric characters and hyphens"):
            Product(family_id=1, sku="ECHEV@001", common_name="Echeveria")

    def test_sku_none_raises_error(self):
        """Test that None SKU raises ValueError."""
        # Arrange & Act & Assert
        with pytest.raises(ValueError, match="SKU cannot be None"):
            Product(family_id=1, sku=None, common_name="Test")


class TestProductCustomAttributes:
    """Test suite for Product JSONB custom_attributes field."""

    def test_custom_attributes_default_empty_dict(self):
        """Test that custom_attributes defaults to empty dict."""
        # Arrange & Act
        product = Product(family_id=1, sku="TEST-001", common_name="Test")

        # Assert
        assert product.custom_attributes == {}

    def test_custom_attributes_none_converts_to_empty_dict(self):
        """Test that None custom_attributes is converted to empty dict."""
        # Arrange & Act
        product = Product(family_id=1, sku="TEST-002", common_name="Test", custom_attributes=None)

        # Assert
        assert product.custom_attributes == {}

    def test_custom_attributes_simple_dict(self):
        """Test custom_attributes with simple key-value pairs."""
        # Arrange
        attrs = {"color": "green", "variegation": True, "growth_rate": "fast"}

        # Act
        product = Product(family_id=1, sku="TEST-003", common_name="Test", custom_attributes=attrs)

        # Assert
        assert product.custom_attributes["color"] == "green"
        assert product.custom_attributes["variegation"] is True
        assert product.custom_attributes["growth_rate"] == "fast"

    def test_custom_attributes_nested_dict(self):
        """Test custom_attributes with nested structure."""
        # Arrange
        attrs = {
            "appearance": {"color": "green", "variegation": "cream edges"},
            "care": {"water": "low", "light": "full sun"},
        }

        # Act
        product = Product(family_id=2, sku="TEST-004", common_name="Test", custom_attributes=attrs)

        # Assert
        assert product.custom_attributes["appearance"]["color"] == "green"
        assert product.custom_attributes["care"]["water"] == "low"

    def test_custom_attributes_complex_metadata(self):
        """Test custom_attributes with realistic plant metadata."""
        # Arrange
        attrs = {
            "color": "blue-gray",
            "variegation": False,
            "growth_rate": "slow",
            "bloom_season": "spring",
            "cold_hardy": False,
            "notes": "Rare cultivar from Mexico",
        }

        # Act
        product = Product(
            family_id=1,
            sku="ECHEV-RARE-001",
            common_name="Rare Echeveria",
            custom_attributes=attrs,
        )

        # Assert
        assert product.custom_attributes["bloom_season"] == "spring"
        assert product.custom_attributes["cold_hardy"] is False
        assert product.custom_attributes["notes"] == "Rare cultivar from Mexico"


class TestProductFieldValidation:
    """Test suite for Product field validation and constraints."""

    def test_long_common_name(self):
        """Test product with maximum length common_name (200 chars)."""
        # Arrange
        long_name = "A" * 200

        # Act
        product = Product(family_id=1, sku="TEST-001", common_name=long_name)

        # Assert
        assert len(product.common_name) == 200
        assert product.common_name == long_name

    def test_long_scientific_name(self):
        """Test product with maximum length scientific_name (200 chars)."""
        # Arrange
        long_scientific_name = "B" * 200

        # Act
        product = Product(
            family_id=2,
            sku="TEST-002",
            common_name="Test",
            scientific_name=long_scientific_name,
        )

        # Assert
        assert len(product.scientific_name) == 200
        assert product.scientific_name == long_scientific_name

    def test_long_description(self):
        """Test product with very long description (text field)."""
        # Arrange
        long_description = "This is a very long description. " * 100  # ~3400 chars

        # Act
        product = Product(
            family_id=3,
            sku="TEST-003",
            common_name="Long Description Product",
            description=long_description,
        )

        # Assert
        assert len(product.description) > 1000
        assert product.description == long_description

    def test_unicode_characters_in_names(self):
        """Test product with Unicode characters (Spanish/Latin plant names)."""
        # Arrange & Act
        product = Product(
            family_id=1,
            sku="ECHEV-001",
            common_name="Echeveria 'María'",
            scientific_name="Echeveria × 'María González'",
            description="Planta suculenta con hojas azuladas",
        )

        # Assert
        assert "María" in product.common_name
        assert "González" in product.scientific_name
        assert "suculenta" in product.description


class TestProductRepr:
    """Test suite for Product __repr__ method."""

    def test_repr_with_all_fields(self):
        """Test __repr__ with all fields populated."""
        # Arrange
        product = Product(
            product_id=5,
            family_id=2,
            sku="ALOE-VERA-001",
            common_name="Aloe Vera",
            scientific_name="Aloe barbadensis",
            description="Medicinal succulent",
        )

        # Act
        repr_str = repr(product)

        # Assert
        assert "Product" in repr_str
        assert "product_id=5" in repr_str
        assert "family_id=2" in repr_str
        assert "sku='ALOE-VERA-001'" in repr_str
        assert "common_name='Aloe Vera'" in repr_str

    def test_repr_with_minimal_fields(self):
        """Test __repr__ with minimal required fields."""
        # Arrange
        product = Product(family_id=1, sku="TEST-001", common_name="Test Product")

        # Act
        repr_str = repr(product)

        # Assert
        assert "Product" in repr_str
        assert "family_id=1" in repr_str
        assert "sku='TEST-001'" in repr_str
        assert "common_name='Test Product'" in repr_str

    def test_repr_without_product_id(self):
        """Test __repr__ before product_id is assigned (pre-insert)."""
        # Arrange
        product = Product(family_id=3, sku="NEW-001", common_name="New Product")

        # Act
        repr_str = repr(product)

        # Assert
        assert "Product" in repr_str
        assert "product_id=None" in repr_str
        assert "family_id=3" in repr_str
        assert "sku='NEW-001'" in repr_str


class TestProductTableMetadata:
    """Test suite for Product table metadata and constraints."""

    def test_table_name(self):
        """Test that table name is correct."""
        assert Product.__tablename__ == "products"

    def test_table_comment(self):
        """Test that table has descriptive comment."""
        table_args = Product.__table_args__
        assert isinstance(table_args, tuple)
        comment_dict = table_args[-1] if table_args else {}
        assert "comment" in comment_dict
        assert "LEAF" in comment_dict["comment"]
        assert "NO seed data" in comment_dict["comment"]

    def test_column_comments(self):
        """Test that columns have descriptive comments."""
        # Get table columns
        table = Product.__table__

        # Check id comment (mapped to product_id)
        assert table.c.id.comment == "Primary key (auto-increment)"

        # Check family_id comment
        assert "CASCADE" in table.c.family_id.comment

        # Check sku comment
        assert "Stock Keeping Unit" in table.c.sku.comment

        # Check common_name comment
        assert "product name" in table.c.common_name.comment.lower()

    def test_primary_key(self):
        """Test that id is the primary key."""
        table = Product.__table__
        pk_columns = [col.name for col in table.primary_key.columns]
        assert pk_columns == ["id"]

    def test_foreign_key_cascade(self):
        """Test that family_id FK has CASCADE delete."""
        table = Product.__table__
        family_fk = None

        for fk in table.foreign_keys:
            if fk.parent.name == "family_id":
                family_fk = fk
                break

        assert family_fk is not None
        assert family_fk.ondelete == "CASCADE"

    def test_sku_unique_constraint(self):
        """Test that SKU has unique constraint."""
        table = Product.__table__
        sku_column = table.c.sku
        assert sku_column.unique is True

    def test_check_constraints_exist(self):
        """Test that CHECK constraints are defined."""
        table = Product.__table__
        constraint_names = [c.name for c in table.constraints if hasattr(c, "name") and c.name]

        # Should have SKU length and format constraints
        assert any("sku_length" in name for name in constraint_names)
        assert any("sku_format" in name for name in constraint_names)


class TestProductRelationships:
    """Test suite for Product relationships (type hints only, no DB)."""

    def test_family_relationship_exists(self):
        """Test that family relationship is defined."""
        assert hasattr(Product, "family")

    def test_family_relationship_type_hint(self):
        """Test that family relationship has correct type hint."""
        # Check that relationship is defined (will be tested in integration)
        assert "family" in Product.__mapper__.relationships

    def test_stock_batches_relationship_commented_out(self):
        """Test that stock_batches relationship is NOT defined yet (DB007 not ready)."""
        # Stock batches relationship should NOT exist until DB007 is complete
        assert "stock_batches" not in Product.__mapper__.relationships

    def test_classifications_relationship_exists(self):
        """Test that classifications relationship is defined (DB026 COMPLETE)."""
        # Classifications relationship NOW exists (DB026 complete)
        assert "classifications" in Product.__mapper__.relationships
