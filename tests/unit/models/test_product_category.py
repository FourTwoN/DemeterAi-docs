"""Unit tests for ProductCategory model.

Tests code validation and model instantiation without database persistence.
"""

import pytest

from app.models import ProductCategory


class TestProductCategoryCodeValidation:
    """Test code validation rules."""

    def test_code_valid_uppercase(self):
        """Test valid uppercase code is accepted."""
        category = ProductCategory(
            code="CACTUS",
            name="Cactus",
            description="Cacti family (Cactaceae) - succulent plants with spines",
        )
        assert category.code == "CACTUS"
        assert category.name == "Cactus"

    def test_code_auto_uppercase(self):
        """Test lowercase code is auto-uppercased."""
        category = ProductCategory(
            code="succulent", name="Succulent", description="Non-cactus succulents"
        )
        assert category.code == "SUCCULENT"

    def test_code_empty_raises_error(self):
        """Test empty code raises ValueError."""
        with pytest.raises(ValueError, match="code cannot be empty"):
            ProductCategory(code="", name="Test", description="Test category")

    def test_code_with_hyphens_raises_error(self):
        """Test code with hyphens raises ValueError."""
        with pytest.raises(ValueError, match="alphanumeric \\+ underscores only"):
            ProductCategory(code="CACTUS-SUCCULENT", name="Cactus Succulent", description="Test")

    def test_code_with_spaces_raises_error(self):
        """Test code with spaces raises ValueError."""
        with pytest.raises(ValueError, match="alphanumeric \\+ underscores only"):
            ProductCategory(code="CACTUS TEST", name="Cactus Test", description="Test")

    def test_code_too_short_raises_error(self):
        """Test code <3 chars raises ValueError."""
        with pytest.raises(ValueError, match="3-50 characters"):
            ProductCategory(code="CA", name="Cactus", description="Test")

    def test_code_too_long_raises_error(self):
        """Test code >50 chars raises ValueError."""
        long_code = "A" * 51
        with pytest.raises(ValueError, match="3-50 characters"):
            ProductCategory(code=long_code, name="Test", description="Test category")

    def test_code_with_underscores_valid(self):
        """Test code with underscores is valid."""
        category = ProductCategory(
            code="ORCHID_RARE", name="Rare Orchid", description="Rare orchid species"
        )
        assert category.code == "ORCHID_RARE"

    def test_code_with_numbers_valid(self):
        """Test code with numbers is valid."""
        category = ProductCategory(
            code="CACTUS123", name="Cactus Type 123", description="Test category"
        )
        assert category.code == "CACTUS123"

    def test_code_mixed_case_uppercased(self):
        """Test mixed case code is uppercased."""
        category = ProductCategory(code="CaCTuS", name="Cactus", description="Test")
        assert category.code == "CACTUS"


class TestProductCategoryFields:
    """Test field constraints and model instantiation."""

    def test_create_category_with_all_fields(self):
        """Test creating a product category with all fields."""
        category = ProductCategory(
            code="BROMELIAD",
            name="Bromeliad",
            description="Bromeliaceae family - epiphytic tropical plants",
        )
        assert category.code == "BROMELIAD"
        assert category.name == "Bromeliad"
        assert category.description == "Bromeliaceae family - epiphytic tropical plants"

    def test_description_nullable(self):
        """Test description is nullable."""
        category = ProductCategory(
            code="TROPICAL",
            name="Tropical Plant",
            description=None,  # Nullable
        )
        assert category.description is None

    def test_all_fields_assignable(self):
        """Test all model fields are assignable."""
        category = ProductCategory(
            code="FERN",
            name="Fern",
            description="Ferns and fern allies",
        )
        assert category.code == "FERN"
        assert category.name == "Fern"
        assert category.description == "Ferns and fern allies"


class TestProductCategoryRepr:
    """Test __repr__ method."""

    def test_repr_format(self):
        """Test __repr__ returns expected format."""
        category = ProductCategory(
            code="CARNIVOROUS",
            name="Carnivorous Plant",
            description="Insectivorous plants",
        )
        repr_str = repr(category)
        assert "ProductCategory" in repr_str
        assert "CARNIVOROUS" in repr_str
        assert "Carnivorous Plant" in repr_str

    def test_repr_without_id(self):
        """Test __repr__ works before persistence (id is None)."""
        category = ProductCategory(code="ORCHID", name="Orchid", description="Test")
        repr_str = repr(category)
        assert "ProductCategory" in repr_str
        assert "ORCHID" in repr_str
        # ID should be None before persistence (repr uses 'id', not 'product_category_id')
        assert "id=None" in repr_str
