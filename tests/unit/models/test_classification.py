"""Unit tests for Classification model.

Tests the Classification SQLAlchemy model in isolation without database dependencies.
Covers model instantiation, FK validation, confidence fields, model_version, name/description,
relationships, and business logic.

Test Coverage:
    - Model instantiation with valid data
    - FK validation (at least ONE FK required)
    - Confidence fields (product_conf, packaging_conf, product_size_conf as INTEGER 0-100)
    - Model version tracking (VARCHAR)
    - Name and description fields (VARCHAR/TEXT)
    - Nullable FKs (product_id, packaging_catalog_id, product_size_id)
    - Required fields (at least ONE FK)
    - __repr__ method
    - Model attributes and types

Architecture:
    - Layer: Unit Tests (isolated model testing)
    - Dependencies: pytest, Classification model
    - Pattern: AAA (Arrange-Act-Assert)

Usage:
    pytest tests/unit/models/test_classification.py -v
    pytest tests/unit/models/test_classification.py::TestClassificationModel -v
    pytest tests/unit/models/test_classification.py --cov=app.models.classification --cov-report=term-missing
"""

import pytest

from app.models.classification import Classification


class TestClassificationModel:
    """Test suite for Classification model instantiation and attributes."""

    def test_create_classification_with_all_fks(self):
        """Test creating Classification with all three FKs populated."""
        # Arrange & Act
        classification = Classification(
            classification_id=1,
            product_id=42,
            packaging_catalog_id=7,
            product_size_id=3,
            product_conf=95,
            packaging_conf=87,
            product_size_conf=92,
            model_version="yolov11n-seg-v1.2.0",
            name="Echeveria Adult Medium",
            description="High confidence detection in all categories",
        )

        # Assert
        assert classification.classification_id == 1
        assert classification.product_id == 42
        assert classification.packaging_catalog_id == 7
        assert classification.product_size_id == 3
        assert classification.product_conf == 95
        assert classification.packaging_conf == 87
        assert classification.product_size_conf == 92
        assert classification.model_version == "yolov11n-seg-v1.2.0"
        assert classification.name == "Echeveria Adult Medium"
        assert classification.description == "High confidence detection in all categories"

    def test_create_classification_with_product_only(self):
        """Test creating Classification with only product_id (no packaging/size)."""
        # Arrange & Act
        classification = Classification(
            product_id=10,
            product_conf=87,
            model_version="yolov11n-seg-v1.2.0",
            name="Echeveria",
        )

        # Assert
        assert classification.product_id == 10
        assert classification.packaging_catalog_id is None
        assert classification.product_size_id is None
        assert classification.product_conf == 87
        assert classification.packaging_conf is None
        assert classification.product_size_conf is None
        assert classification.model_version == "yolov11n-seg-v1.2.0"
        assert classification.name == "Echeveria"

    def test_create_classification_with_packaging_only(self):
        """Test creating Classification with only packaging_catalog_id."""
        # Arrange & Act
        classification = Classification(
            packaging_catalog_id=5,
            packaging_conf=72,
            model_version="yolov11n-seg-v1.2.0",
        )

        # Assert
        assert classification.product_id is None
        assert classification.packaging_catalog_id == 5
        assert classification.product_size_id is None
        assert classification.product_conf is None
        assert classification.packaging_conf == 72
        assert classification.product_size_conf is None

    def test_create_classification_with_size_only(self):
        """Test creating Classification with only product_size_id."""
        # Arrange & Act
        classification = Classification(
            product_size_id=2,
            product_size_conf=65,
            model_version="yolov11n-seg-v1.2.0",
        )

        # Assert
        assert classification.product_id is None
        assert classification.packaging_catalog_id is None
        assert classification.product_size_id == 2
        assert classification.product_conf is None
        assert classification.packaging_conf is None
        assert classification.product_size_conf == 65

    def test_create_classification_minimal_required_fields(self):
        """Test creating Classification with minimal required fields."""
        # Arrange & Act
        classification = Classification(product_id=1)

        # Assert
        assert classification.product_id == 1
        assert classification.product_conf is None  # All conf fields nullable
        assert classification.packaging_conf is None
        assert classification.product_size_conf is None
        assert classification.model_version is None  # Nullable
        assert classification.name is None  # Nullable
        assert classification.description is None  # Nullable
        assert classification.created_at is None  # Not set until DB insert


class TestClassificationConfidenceFields:
    """Test suite for Classification confidence fields (INTEGER 0-100, nullable)."""

    def test_product_conf_min_value(self):
        """Test product_conf with minimum value (0)."""
        # Arrange & Act
        classification = Classification(product_id=1, product_conf=0)

        # Assert
        assert classification.product_conf == 0

    def test_product_conf_max_value(self):
        """Test product_conf with maximum value (100)."""
        # Arrange & Act
        classification = Classification(product_id=1, product_conf=100)

        # Assert
        assert classification.product_conf == 100

    def test_product_conf_mid_range(self):
        """Test product_conf with mid-range value (50)."""
        # Arrange & Act
        classification = Classification(product_id=1, product_conf=50)

        # Assert
        assert classification.product_conf == 50

    def test_product_conf_nullable(self):
        """Test that product_conf can be NULL."""
        # Arrange & Act
        classification = Classification(product_id=1, product_conf=None)

        # Assert
        assert classification.product_conf is None

    def test_packaging_conf_valid(self):
        """Test packaging_conf with valid value."""
        # Arrange & Act
        classification = Classification(packaging_catalog_id=5, packaging_conf=87)

        # Assert
        assert classification.packaging_conf == 87

    def test_packaging_conf_nullable(self):
        """Test that packaging_conf can be NULL."""
        # Arrange & Act
        classification = Classification(packaging_catalog_id=5, packaging_conf=None)

        # Assert
        assert classification.packaging_conf is None

    def test_product_size_conf_valid(self):
        """Test product_size_conf with valid value."""
        # Arrange & Act
        classification = Classification(product_size_id=3, product_size_conf=92)

        # Assert
        assert classification.product_size_conf == 92

    def test_product_size_conf_nullable(self):
        """Test that product_size_conf can be NULL."""
        # Arrange & Act
        classification = Classification(product_size_id=3, product_size_conf=None)

        # Assert
        assert classification.product_size_conf is None

    def test_all_conf_fields_together(self):
        """Test all three confidence fields populated."""
        # Arrange & Act
        classification = Classification(
            product_id=1,
            packaging_catalog_id=5,
            product_size_id=3,
            product_conf=95,
            packaging_conf=87,
            product_size_conf=92,
        )

        # Assert
        assert classification.product_conf == 95
        assert classification.packaging_conf == 87
        assert classification.product_size_conf == 92

    def test_conf_fields_independent(self):
        """Test that confidence fields are independent (can be set separately)."""
        # Arrange & Act
        classification = Classification(
            product_id=1,
            packaging_catalog_id=5,
            product_conf=85,  # Only product_conf set
        )

        # Assert
        assert classification.product_conf == 85
        assert classification.packaging_conf is None  # Not set
        assert classification.product_size_conf is None  # Not set


class TestClassificationFKValidation:
    """Test suite for Classification FK validation (at least ONE required)."""

    def test_all_fks_null_raises_error(self):
        """Test that no FKs raises ValueError."""
        # Arrange & Act & Assert
        with pytest.raises(ValueError, match="At least one of .* must be NOT NULL"):
            Classification()

    def test_product_and_packaging_both_present(self):
        """Test that product_id + packaging_catalog_id is valid."""
        # Arrange & Act
        classification = Classification(product_id=10, packaging_catalog_id=5, product_conf=80)

        # Assert
        assert classification.product_id == 10
        assert classification.packaging_catalog_id == 5
        assert classification.product_size_id is None

    def test_product_and_size_both_present(self):
        """Test that product_id + product_size_id is valid."""
        # Arrange & Act
        classification = Classification(product_id=10, product_size_id=3, product_conf=85)

        # Assert
        assert classification.product_id == 10
        assert classification.packaging_catalog_id is None
        assert classification.product_size_id == 3

    def test_packaging_and_size_both_present(self):
        """Test that packaging_catalog_id + product_size_id is valid."""
        # Arrange & Act
        classification = Classification(
            packaging_catalog_id=5, product_size_id=2, packaging_conf=75
        )

        # Assert
        assert classification.product_id is None
        assert classification.packaging_catalog_id == 5
        assert classification.product_size_id == 2


class TestClassificationModelVersion:
    """Test suite for Classification model_version field."""

    def test_model_version_nullable(self):
        """Test that model_version can be NULL."""
        # Arrange & Act
        classification = Classification(product_id=1, model_version=None)

        # Assert
        assert classification.model_version is None

    def test_model_version_valid(self):
        """Test model_version with valid value."""
        # Arrange & Act
        classification = Classification(
            product_id=1,
            model_version="yolov11n-seg-v1.2.0",
        )

        # Assert
        assert classification.model_version == "yolov11n-seg-v1.2.0"

    def test_model_version_formats(self):
        """Test various model_version formats."""
        # Different version formats
        versions = [
            "yolov11n-seg-v1.0.0",
            "yolov11s-det-v2.3.1",
            "custom-model-v1",
            "prod-2024-10-14",
        ]

        for version in versions:
            classification = Classification(product_id=1, model_version=version)
            assert classification.model_version == version


class TestClassificationNameDescription:
    """Test suite for Classification name and description fields."""

    def test_name_nullable(self):
        """Test that name can be NULL."""
        # Arrange & Act
        classification = Classification(product_id=1, name=None)

        # Assert
        assert classification.name is None

    def test_name_valid(self):
        """Test name with valid value."""
        # Arrange & Act
        classification = Classification(
            product_id=1,
            name="Echeveria Adult",
        )

        # Assert
        assert classification.name == "Echeveria Adult"

    def test_description_nullable(self):
        """Test that description can be NULL."""
        # Arrange & Act
        classification = Classification(product_id=1, description=None)

        # Assert
        assert classification.description is None

    def test_description_valid(self):
        """Test description with valid text."""
        # Arrange & Act
        classification = Classification(
            product_id=1,
            description="High confidence detection with good lighting conditions",
        )

        # Assert
        assert (
            classification.description == "High confidence detection with good lighting conditions"
        )

    def test_name_and_description_together(self):
        """Test name and description fields together."""
        # Arrange & Act
        classification = Classification(
            product_id=1,
            name="Echeveria Adult Medium",
            description="Detected with high confidence in optimal lighting",
        )

        # Assert
        assert classification.name == "Echeveria Adult Medium"
        assert classification.description == "Detected with high confidence in optimal lighting"


class TestClassificationFieldValidation:
    """Test suite for Classification field validation and constraints."""

    def test_nullable_packaging_catalog_id(self):
        """Test that packaging_catalog_id can be NULL."""
        # Arrange & Act
        classification = Classification(product_id=1, packaging_catalog_id=None)

        # Assert
        assert classification.packaging_catalog_id is None

    def test_nullable_product_size_id(self):
        """Test that product_size_id can be NULL."""
        # Arrange & Act
        classification = Classification(product_id=1, product_size_id=None)

        # Assert
        assert classification.product_size_id is None

    def test_nullable_product_id(self):
        """Test that product_id can be NULL (if other FKs present)."""
        # Arrange & Act
        classification = Classification(product_id=None, packaging_catalog_id=5)

        # Assert
        assert classification.product_id is None

    def test_all_fields_nullable_except_one_fk(self):
        """Test that all fields except ONE FK are nullable."""
        # Arrange & Act - minimal valid classification
        classification = Classification(product_id=1)

        # Assert - all other fields should be None
        assert classification.product_id == 1  # Required (at least ONE FK)
        assert classification.packaging_catalog_id is None
        assert classification.product_size_id is None
        assert classification.product_conf is None
        assert classification.packaging_conf is None
        assert classification.product_size_conf is None
        assert classification.model_version is None
        assert classification.name is None
        assert classification.description is None


class TestClassificationRepr:
    """Test suite for Classification __repr__ method."""

    def test_repr_with_all_fks(self):
        """Test __repr__ with all FKs populated."""
        # Arrange
        classification = Classification(
            classification_id=5,
            product_id=42,
            packaging_catalog_id=7,
            product_size_id=3,
            product_conf=95,
        )

        # Act
        repr_str = repr(classification)

        # Assert
        assert "Classification" in repr_str
        assert "classification_id=5" in repr_str
        assert "product_id=42" in repr_str
        assert "packaging_catalog_id=7" in repr_str
        assert "product_size_id=3" in repr_str
        assert "product_conf=95" in repr_str

    def test_repr_with_product_only(self):
        """Test __repr__ with only product_id."""
        # Arrange
        classification = Classification(product_id=10, product_conf=85)

        # Act
        repr_str = repr(classification)

        # Assert
        assert "Classification" in repr_str
        assert "product_id=10" in repr_str
        assert "packaging_catalog_id=None" in repr_str
        assert "product_size_id=None" in repr_str
        assert "product_conf=85" in repr_str

    def test_repr_without_classification_id(self):
        """Test __repr__ before classification_id is assigned (pre-insert)."""
        # Arrange
        classification = Classification(product_id=1, product_conf=90)

        # Act
        repr_str = repr(classification)

        # Assert
        assert "Classification" in repr_str
        assert "classification_id=None" in repr_str
        assert "product_id=1" in repr_str
        assert "product_conf=90" in repr_str


class TestClassificationTableMetadata:
    """Test suite for Classification table metadata and constraints."""

    def test_table_name(self):
        """Test that table name is correct."""
        assert Classification.__tablename__ == "classifications"

    def test_table_comment(self):
        """Test that table has descriptive comment."""
        table_args = Classification.__table_args__
        assert isinstance(table_args, tuple)
        comment_dict = table_args[-1] if table_args else {}
        assert "comment" in comment_dict
        assert "ML prediction cache" in comment_dict["comment"]
        assert "NO seed data" in comment_dict["comment"]

    def test_column_comments(self):
        """Test that columns have descriptive comments."""
        # Get table columns
        table = Classification.__table__

        # Check id comment (mapped to classification_id)
        assert table.c.id.comment == "Primary key (auto-increment)"

        # Check product_id comment
        assert "CASCADE" in table.c.product_id.comment
        assert "NULLABLE" in table.c.product_id.comment

        # Check product_conf comment
        assert "0-100" in table.c.product_conf.comment
        assert "NULLABLE" in table.c.product_conf.comment

        # Check model_version comment
        assert "ML model version" in table.c.model_version.comment

    def test_primary_key(self):
        """Test that id is the primary key."""
        table = Classification.__table__
        pk_columns = [col.name for col in table.primary_key.columns]
        assert pk_columns == ["id"]

    def test_foreign_key_cascade(self):
        """Test that all FKs have CASCADE delete."""
        table = Classification.__table__

        # Check product_id FK
        product_fk = None
        for fk in table.foreign_keys:
            if fk.parent.name == "product_id":
                product_fk = fk
                break
        assert product_fk is not None
        assert product_fk.ondelete == "CASCADE"

        # Check packaging_catalog_id FK
        packaging_fk = None
        for fk in table.foreign_keys:
            if fk.parent.name == "packaging_catalog_id":
                packaging_fk = fk
                break
        assert packaging_fk is not None
        assert packaging_fk.ondelete == "CASCADE"

        # Check product_size_id FK
        size_fk = None
        for fk in table.foreign_keys:
            if fk.parent.name == "product_size_id":
                size_fk = fk
                break
        assert size_fk is not None
        assert size_fk.ondelete == "CASCADE"

    def test_check_constraints_exist(self):
        """Test that CHECK constraints are defined."""
        table = Classification.__table__
        constraint_names = [c.name for c in table.constraints if hasattr(c, "name") and c.name]

        # Should have at least one FK constraint
        assert any("at_least_one_fk" in name for name in constraint_names)

    def test_confidence_fields_integer_type(self):
        """Test that confidence fields are INTEGER."""
        table = Classification.__table__

        # Check product_conf type
        assert "INTEGER" in str(table.c.product_conf.type)

        # Check packaging_conf type
        assert "INTEGER" in str(table.c.packaging_conf.type)

        # Check product_size_conf type
        assert "INTEGER" in str(table.c.product_size_conf.type)

    def test_model_version_varchar_type(self):
        """Test that model_version is VARCHAR."""
        table = Classification.__table__
        model_version_col = table.c.model_version

        # Check type
        assert "VARCHAR" in str(model_version_col.type)

    def test_name_varchar_type(self):
        """Test that name is VARCHAR."""
        table = Classification.__table__
        name_col = table.c.name

        # Check type
        assert "VARCHAR" in str(name_col.type)

    def test_description_text_type(self):
        """Test that description is TEXT."""
        table = Classification.__table__
        description_col = table.c.description

        # Check type
        assert "TEXT" in str(description_col.type)


class TestClassificationRelationships:
    """Test suite for Classification relationships (type hints only, no DB)."""

    def test_product_relationship_exists(self):
        """Test that product relationship is defined."""
        assert hasattr(Classification, "product")

    def test_product_relationship_type_hint(self):
        """Test that product relationship has correct type hint."""
        # Check that relationship is defined (will be tested in integration)
        assert "product" in Classification.__mapper__.relationships

    def test_product_size_relationship_exists(self):
        """Test that product_size relationship is defined."""
        assert hasattr(Classification, "product_size")

    def test_product_size_relationship_type_hint(self):
        """Test that product_size relationship has correct type hint."""
        assert "product_size" in Classification.__mapper__.relationships

    def test_packaging_catalog_relationship_commented_out(self):
        """Test that packaging_catalog relationship is NOT defined yet."""
        # PackagingCatalog model not ready yet
        assert "packaging_catalog" not in Classification.__mapper__.relationships

    def test_detections_relationship_commented_out(self):
        """Test that detections relationship is NOT defined yet (DB013 not ready)."""
        # Detections relationship should NOT exist until DB013 is complete
        assert "detections" not in Classification.__mapper__.relationships

    def test_estimations_relationship_commented_out(self):
        """Test that estimations relationship is NOT defined yet (DB014 not ready)."""
        # Estimations relationship should NOT exist until DB014 is complete
        assert "estimations" not in Classification.__mapper__.relationships


class TestClassificationEdgeCases:
    """Test suite for Classification edge cases and corner scenarios."""

    def test_very_low_confidence(self):
        """Test classification with very low confidence (1)."""
        # Arrange & Act
        classification = Classification(product_id=1, product_conf=1)

        # Assert
        assert classification.product_conf == 1

    def test_zero_confidence(self):
        """Test classification with zero confidence (0)."""
        # Arrange & Act
        classification = Classification(product_id=1, product_conf=0)

        # Assert
        assert classification.product_conf == 0

    def test_perfect_confidence(self):
        """Test classification with perfect confidence (100)."""
        # Arrange & Act
        classification = Classification(product_id=1, product_conf=100)

        # Assert
        assert classification.product_conf == 100

    def test_all_confidence_fields_at_max(self):
        """Test all confidence fields at maximum value (100)."""
        # Arrange & Act
        classification = Classification(
            product_id=1,
            packaging_catalog_id=5,
            product_size_id=3,
            product_conf=100,
            packaging_conf=100,
            product_size_conf=100,
        )

        # Assert
        assert classification.product_conf == 100
        assert classification.packaging_conf == 100
        assert classification.product_size_conf == 100

    def test_mixed_confidence_values(self):
        """Test mixed confidence values across fields."""
        # Arrange & Act
        classification = Classification(
            product_id=1,
            packaging_catalog_id=5,
            product_size_id=3,
            product_conf=95,  # High
            packaging_conf=50,  # Medium
            product_size_conf=10,  # Low
        )

        # Assert
        assert classification.product_conf == 95
        assert classification.packaging_conf == 50
        assert classification.product_size_conf == 10

    def test_long_model_version_string(self):
        """Test with long model version string."""
        # Arrange
        long_version = "yolov11n-seg-custom-trained-2024-10-14-v1.2.3-production"

        # Act
        classification = Classification(product_id=1, model_version=long_version)

        # Assert
        assert classification.model_version == long_version

    def test_long_description_text(self):
        """Test with long description text."""
        # Arrange
        long_description = (
            "This is a high confidence classification detected in optimal lighting "
            "conditions with minimal occlusion. The model successfully identified "
            "the product type, packaging, and size with high accuracy scores across "
            "all three categories. Inference was performed on CPU using the production "
            "model version yolov11n-seg-v1.2.0."
        )

        # Act
        classification = Classification(product_id=1, description=long_description)

        # Assert
        assert classification.description == long_description
