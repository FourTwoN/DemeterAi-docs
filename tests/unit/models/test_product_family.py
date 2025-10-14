"""Unit tests for ProductFamily model.

Tests the ProductFamily SQLAlchemy model in isolation without database dependencies.
Covers model instantiation, validation, relationships, and business logic.

Test Coverage:
    - Model instantiation with valid data
    - Category relationship (many-to-one)
    - Nullable fields (scientific_name, description)
    - Required fields (family_id, category_id, name)
    - __repr__ method
    - Model attributes and types

Architecture:
    - Layer: Unit Tests (isolated model testing)
    - Dependencies: pytest, ProductFamily model
    - Pattern: AAA (Arrange-Act-Assert)

Usage:
    pytest tests/unit/models/test_product_family.py -v
    pytest tests/unit/models/test_product_family.py::test_create_family_minimal -v
"""

from app.models.product_family import ProductFamily


class TestProductFamilyModel:
    """Test suite for ProductFamily model instantiation and attributes."""

    def test_create_family_with_all_fields(self):
        """Test creating ProductFamily with all fields populated."""
        # Arrange & Act
        family = ProductFamily(
            family_id=1,
            category_id=1,
            name="Echeveria",
            scientific_name="Echeveria",
            description="Small rosette-forming succulents native to Mexico",
        )

        # Assert
        assert family.family_id == 1
        assert family.category_id == 1
        assert family.name == "Echeveria"
        assert family.scientific_name == "Echeveria"
        assert family.description == "Small rosette-forming succulents native to Mexico"

    def test_create_family_minimal_required_fields(self):
        """Test creating ProductFamily with only required fields."""
        # Arrange & Act
        family = ProductFamily(category_id=2, name="Aloe")

        # Assert
        assert family.category_id == 2
        assert family.name == "Aloe"
        assert family.scientific_name is None
        assert family.description is None

    def test_family_name_required(self):
        """Test that name field is required."""
        # Arrange & Act
        family = ProductFamily(category_id=1)

        # Assert - name is None (database will enforce NOT NULL)
        assert family.name is None
        assert family.category_id == 1

    def test_category_id_required(self):
        """Test that category_id field is required."""
        # Arrange & Act
        family = ProductFamily(name="Haworthia")

        # Assert - category_id is None (database will enforce NOT NULL)
        assert family.category_id is None
        assert family.name == "Haworthia"

    def test_scientific_name_nullable(self):
        """Test that scientific_name can be NULL."""
        # Arrange & Act
        family = ProductFamily(category_id=3, name="Generic Family", scientific_name=None)

        # Assert
        assert family.scientific_name is None

    def test_description_nullable(self):
        """Test that description can be NULL."""
        # Arrange & Act
        family = ProductFamily(category_id=4, name="Test Family", description=None)

        # Assert
        assert family.description is None

    def test_long_name(self):
        """Test family with maximum length name (200 chars)."""
        # Arrange
        long_name = "A" * 200

        # Act
        family = ProductFamily(category_id=1, name=long_name)

        # Assert
        assert len(family.name) == 200
        assert family.name == long_name

    def test_long_scientific_name(self):
        """Test family with maximum length scientific_name (200 chars)."""
        # Arrange
        long_scientific_name = "B" * 200

        # Act
        family = ProductFamily(category_id=2, name="Test", scientific_name=long_scientific_name)

        # Assert
        assert len(family.scientific_name) == 200
        assert family.scientific_name == long_scientific_name

    def test_long_description(self):
        """Test family with very long description (text field)."""
        # Arrange
        long_description = "This is a very long description. " * 100  # ~3400 chars

        # Act
        family = ProductFamily(
            category_id=3, name="Long Description Family", description=long_description
        )

        # Assert
        assert len(family.description) > 1000
        assert family.description == long_description


class TestProductFamilyRepr:
    """Test suite for ProductFamily __repr__ method."""

    def test_repr_with_all_fields(self):
        """Test __repr__ with all fields populated."""
        # Arrange
        family = ProductFamily(
            family_id=5,
            category_id=2,
            name="Crassula",
            scientific_name="Crassula",
            description="Diverse genus of succulents",
        )

        # Act
        repr_str = repr(family)

        # Assert
        assert "ProductFamily" in repr_str
        assert "family_id=5" in repr_str
        assert "category_id=2" in repr_str
        assert "name='Crassula'" in repr_str

    def test_repr_with_minimal_fields(self):
        """Test __repr__ with minimal required fields."""
        # Arrange
        family = ProductFamily(category_id=1, name="Sedum")

        # Act
        repr_str = repr(family)

        # Assert
        assert "ProductFamily" in repr_str
        assert "category_id=1" in repr_str
        assert "name='Sedum'" in repr_str

    def test_repr_without_family_id(self):
        """Test __repr__ before family_id is assigned (pre-insert)."""
        # Arrange
        family = ProductFamily(category_id=3, name="Tillandsia")

        # Act
        repr_str = repr(family)

        # Assert
        assert "ProductFamily" in repr_str
        assert "family_id=None" in repr_str
        assert "category_id=3" in repr_str
        assert "name='Tillandsia'" in repr_str


class TestProductFamilyTableMetadata:
    """Test suite for ProductFamily table metadata and constraints."""

    def test_table_name(self):
        """Test that table name is correct."""
        assert ProductFamily.__tablename__ == "product_families"

    def test_table_comment(self):
        """Test that table has descriptive comment."""
        table_args = ProductFamily.__table_args__
        assert isinstance(table_args, tuple)
        comment_dict = table_args[-1] if table_args else {}
        assert "comment" in comment_dict
        assert "LEVEL 2" in comment_dict["comment"]
        assert "Category → Family → Product" in comment_dict["comment"]

    def test_column_comments(self):
        """Test that columns have descriptive comments."""
        # Get table columns
        table = ProductFamily.__table__

        # Check family_id comment
        assert table.c.family_id.comment == "Primary key (auto-increment)"

        # Check category_id comment
        assert "CASCADE" in table.c.category_id.comment

        # Check name comment
        assert "family name" in table.c.name.comment.lower()

    def test_primary_key(self):
        """Test that family_id is the primary key."""
        table = ProductFamily.__table__
        pk_columns = [col.name for col in table.primary_key.columns]
        assert pk_columns == ["family_id"]

    def test_foreign_key_cascade(self):
        """Test that category_id FK has CASCADE delete."""
        table = ProductFamily.__table__
        category_fk = None

        for fk in table.foreign_keys:
            if fk.parent.name == "category_id":
                category_fk = fk
                break

        assert category_fk is not None
        assert category_fk.ondelete == "CASCADE"


class TestProductFamilyRelationships:
    """Test suite for ProductFamily relationships (type hints only, no DB)."""

    def test_category_relationship_exists(self):
        """Test that category relationship is defined."""
        assert hasattr(ProductFamily, "category")

    def test_category_relationship_type_hint(self):
        """Test that category relationship has correct type hint."""
        # Check that relationship is defined (will be tested in integration)
        assert "category" in ProductFamily.__mapper__.relationships

    def test_products_relationship_commented_out(self):
        """Test that products relationship is NOT defined yet (DB017 not ready)."""
        # Products relationship should NOT exist until DB017 is complete
        assert "products" not in ProductFamily.__mapper__.relationships
