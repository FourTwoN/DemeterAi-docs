"""Unit tests for Classification model.

Tests the Classification SQLAlchemy model in isolation without database dependencies.
Covers model instantiation, confidence validation, FK validation, JSONB ml_metadata,
relationships, and business logic.

Test Coverage:
    - Model instantiation with valid data
    - Confidence validation (0.0-1.0 range, 4 decimal precision)
    - FK validation (at least ONE FK required)
    - JSONB ml_metadata (default value, ML model info)
    - Nullable FKs (product_id, packaging_catalog_id, product_size_id)
    - Required fields (confidence, at least ONE FK)
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
            confidence=0.9523,
            ml_metadata={
                "model_name": "yolov11n-seg",
                "model_version": "1.2.0",
                "inference_time_ms": 145,
                "gpu_used": False,
            },
        )

        # Assert
        assert classification.classification_id == 1
        assert classification.product_id == 42
        assert classification.packaging_catalog_id == 7
        assert classification.product_size_id == 3
        assert float(classification.confidence) == 0.9523
        assert classification.ml_metadata["model_name"] == "yolov11n-seg"
        assert classification.ml_metadata["inference_time_ms"] == 145

    def test_create_classification_with_product_only(self):
        """Test creating Classification with only product_id (no packaging/size)."""
        # Arrange & Act
        classification = Classification(
            product_id=10, confidence=0.8750, ml_metadata={"model_name": "yolov11n"}
        )

        # Assert
        assert classification.product_id == 10
        assert classification.packaging_catalog_id is None
        assert classification.product_size_id is None
        assert float(classification.confidence) == 0.8750
        assert classification.ml_metadata == {"model_name": "yolov11n"}

    def test_create_classification_with_packaging_only(self):
        """Test creating Classification with only packaging_catalog_id."""
        # Arrange & Act
        classification = Classification(
            packaging_catalog_id=5,
            confidence=0.7200,
        )

        # Assert
        assert classification.product_id is None
        assert classification.packaging_catalog_id == 5
        assert classification.product_size_id is None
        assert float(classification.confidence) == 0.7200

    def test_create_classification_with_size_only(self):
        """Test creating Classification with only product_size_id."""
        # Arrange & Act
        classification = Classification(
            product_size_id=2,
            confidence=0.6500,
        )

        # Assert
        assert classification.product_id is None
        assert classification.packaging_catalog_id is None
        assert classification.product_size_id == 2
        assert float(classification.confidence) == 0.6500

    def test_create_classification_minimal_required_fields(self):
        """Test creating Classification with minimal required fields."""
        # Arrange & Act
        classification = Classification(product_id=1, confidence=0.9000)

        # Assert
        assert classification.product_id == 1
        assert float(classification.confidence) == 0.9000
        assert classification.ml_metadata == {}  # Default empty dict
        assert classification.created_at is None  # Not set until DB insert


class TestClassificationConfidenceValidation:
    """Test suite for Classification confidence validation logic."""

    def test_valid_confidence_min_value(self):
        """Test confidence with minimum valid value (0.0)."""
        # Arrange & Act
        classification = Classification(product_id=1, confidence=0.0)

        # Assert
        assert float(classification.confidence) == 0.0

    def test_valid_confidence_max_value(self):
        """Test confidence with maximum valid value (1.0)."""
        # Arrange & Act
        classification = Classification(product_id=1, confidence=1.0)

        # Assert
        assert float(classification.confidence) == 1.0

    def test_valid_confidence_mid_range(self):
        """Test confidence with mid-range value."""
        # Arrange & Act
        classification = Classification(product_id=1, confidence=0.5000)

        # Assert
        assert float(classification.confidence) == 0.5000

    def test_valid_confidence_high_precision(self):
        """Test confidence with 4 decimal precision (0.9523)."""
        # Arrange & Act
        classification = Classification(product_id=1, confidence=0.9523)

        # Assert
        assert float(classification.confidence) == 0.9523

    def test_confidence_above_max_raises_error(self):
        """Test that confidence > 1.0 raises ValueError."""
        # Arrange & Act & Assert
        with pytest.raises(ValueError, match="Confidence must be between 0.0 and 1.0"):
            Classification(product_id=1, confidence=1.5)

    def test_confidence_negative_raises_error(self):
        """Test that negative confidence raises ValueError."""
        # Arrange & Act & Assert
        with pytest.raises(ValueError, match="Confidence must be between 0.0 and 1.0"):
            Classification(product_id=1, confidence=-0.1)

    def test_confidence_none_raises_error(self):
        """Test that None confidence raises ValueError."""
        # Arrange & Act & Assert
        with pytest.raises(ValueError, match="Confidence cannot be None"):
            Classification(product_id=1, confidence=None)

    def test_confidence_decimal_precision(self):
        """Test that confidence supports 4 decimal places."""
        # Arrange & Act
        classification = Classification(product_id=1, confidence=0.9876)

        # Assert
        assert float(classification.confidence) == 0.9876

    def test_confidence_edge_case_0_0001(self):
        """Test confidence with smallest non-zero value (0.0001)."""
        # Arrange & Act
        classification = Classification(product_id=1, confidence=0.0001)

        # Assert
        assert float(classification.confidence) == 0.0001

    def test_confidence_edge_case_0_9999(self):
        """Test confidence with near-maximum value (0.9999)."""
        # Arrange & Act
        classification = Classification(product_id=1, confidence=0.9999)

        # Assert
        assert float(classification.confidence) == 0.9999


class TestClassificationFKValidation:
    """Test suite for Classification FK validation (at least ONE required)."""

    def test_all_fks_null_raises_error(self):
        """Test that no FKs raises ValueError."""
        # Arrange & Act & Assert
        with pytest.raises(ValueError, match="At least one of .* must be NOT NULL"):
            Classification(confidence=0.9)

    def test_product_and_packaging_both_present(self):
        """Test that product_id + packaging_catalog_id is valid."""
        # Arrange & Act
        classification = Classification(product_id=10, packaging_catalog_id=5, confidence=0.8)

        # Assert
        assert classification.product_id == 10
        assert classification.packaging_catalog_id == 5
        assert classification.product_size_id is None

    def test_product_and_size_both_present(self):
        """Test that product_id + product_size_id is valid."""
        # Arrange & Act
        classification = Classification(product_id=10, product_size_id=3, confidence=0.85)

        # Assert
        assert classification.product_id == 10
        assert classification.packaging_catalog_id is None
        assert classification.product_size_id == 3

    def test_packaging_and_size_both_present(self):
        """Test that packaging_catalog_id + product_size_id is valid."""
        # Arrange & Act
        classification = Classification(packaging_catalog_id=5, product_size_id=2, confidence=0.75)

        # Assert
        assert classification.product_id is None
        assert classification.packaging_catalog_id == 5
        assert classification.product_size_id == 2


class TestClassificationMLMetadata:
    """Test suite for Classification JSONB ml_metadata field."""

    def test_ml_metadata_default_empty_dict(self):
        """Test that ml_metadata defaults to empty dict."""
        # Arrange & Act
        classification = Classification(product_id=1, confidence=0.9)

        # Assert
        assert classification.ml_metadata == {}

    def test_ml_metadata_none_converts_to_empty_dict(self):
        """Test that None ml_metadata is converted to empty dict."""
        # Arrange & Act
        classification = Classification(product_id=1, confidence=0.9, ml_metadata=None)

        # Assert
        assert classification.ml_metadata == {}

    def test_ml_metadata_simple_dict(self):
        """Test ml_metadata with simple key-value pairs."""
        # Arrange
        metadata = {
            "model_name": "yolov11n-seg",
            "model_version": "1.2.0",
            "inference_time_ms": 145,
        }

        # Act
        classification = Classification(product_id=1, confidence=0.95, ml_metadata=metadata)

        # Assert
        assert classification.ml_metadata["model_name"] == "yolov11n-seg"
        assert classification.ml_metadata["model_version"] == "1.2.0"
        assert classification.ml_metadata["inference_time_ms"] == 145

    def test_ml_metadata_nested_dict(self):
        """Test ml_metadata with nested structure."""
        # Arrange
        metadata = {
            "model": {"name": "yolov11n", "version": "1.2.0", "type": "segmentation"},
            "inference": {"time_ms": 145, "gpu_used": False, "batch_size": 1},
        }

        # Act
        classification = Classification(product_id=2, confidence=0.88, ml_metadata=metadata)

        # Assert
        assert classification.ml_metadata["model"]["name"] == "yolov11n"
        assert classification.ml_metadata["inference"]["gpu_used"] is False
        assert classification.ml_metadata["inference"]["batch_size"] == 1

    def test_ml_metadata_complex_ml_info(self):
        """Test ml_metadata with realistic ML model information."""
        # Arrange
        metadata = {
            "model_name": "yolov11n-seg",
            "model_version": "1.2.0",
            "inference_time_ms": 145,
            "gpu_used": False,
            "temperature": 0.7,
            "top_k": 5,
            "confidence_threshold": 0.25,
            "nms_threshold": 0.45,
            "image_size": [640, 640],
            "device": "cpu",
        }

        # Act
        classification = Classification(product_id=1, confidence=0.9523, ml_metadata=metadata)

        # Assert
        assert classification.ml_metadata["temperature"] == 0.7
        assert classification.ml_metadata["device"] == "cpu"
        assert classification.ml_metadata["image_size"] == [640, 640]

    def test_ml_metadata_boolean_values(self):
        """Test ml_metadata with boolean flags."""
        # Arrange
        metadata = {"gpu_used": True, "augmentation_applied": False, "ensemble_mode": True}

        # Act
        classification = Classification(product_id=3, confidence=0.92, ml_metadata=metadata)

        # Assert
        assert classification.ml_metadata["gpu_used"] is True
        assert classification.ml_metadata["augmentation_applied"] is False
        assert classification.ml_metadata["ensemble_mode"] is True


class TestClassificationFieldValidation:
    """Test suite for Classification field validation and constraints."""

    def test_nullable_packaging_catalog_id(self):
        """Test that packaging_catalog_id can be NULL."""
        # Arrange & Act
        classification = Classification(product_id=1, packaging_catalog_id=None, confidence=0.8)

        # Assert
        assert classification.packaging_catalog_id is None

    def test_nullable_product_size_id(self):
        """Test that product_size_id can be NULL."""
        # Arrange & Act
        classification = Classification(product_id=1, product_size_id=None, confidence=0.8)

        # Assert
        assert classification.product_size_id is None

    def test_nullable_product_id(self):
        """Test that product_id can be NULL (if other FKs present)."""
        # Arrange & Act
        classification = Classification(product_id=None, packaging_catalog_id=5, confidence=0.7)

        # Assert
        assert classification.product_id is None

    def test_confidence_required(self):
        """Test that confidence field is required."""
        # Arrange & Act & Assert
        with pytest.raises(ValueError, match="Confidence cannot be None"):
            Classification(product_id=1, confidence=None)


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
            confidence=0.9523,
        )

        # Act
        repr_str = repr(classification)

        # Assert
        assert "Classification" in repr_str
        assert "classification_id=5" in repr_str
        assert "product_id=42" in repr_str
        assert "packaging_catalog_id=7" in repr_str
        assert "product_size_id=3" in repr_str
        assert "0.9523" in repr_str

    def test_repr_with_product_only(self):
        """Test __repr__ with only product_id."""
        # Arrange
        classification = Classification(product_id=10, confidence=0.85)

        # Act
        repr_str = repr(classification)

        # Assert
        assert "Classification" in repr_str
        assert "product_id=10" in repr_str
        assert "packaging_catalog_id=None" in repr_str
        assert "product_size_id=None" in repr_str

    def test_repr_without_classification_id(self):
        """Test __repr__ before classification_id is assigned (pre-insert)."""
        # Arrange
        classification = Classification(product_id=1, confidence=0.9)

        # Act
        repr_str = repr(classification)

        # Assert
        assert "Classification" in repr_str
        assert "classification_id=None" in repr_str
        assert "product_id=1" in repr_str


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

        # Check confidence comment
        assert "0.0000-1.0000" in table.c.confidence.comment
        assert "4 decimals" in table.c.confidence.comment

        # Check metadata comment (mapped to ml_metadata)
        assert "ML model metadata" in table.c.metadata.comment

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

        # Should have confidence range constraint
        assert any("confidence_range" in name for name in constraint_names)

        # Should have at least one FK constraint
        assert any("at_least_one_fk" in name for name in constraint_names)

    def test_confidence_numeric_type(self):
        """Test that confidence is Numeric(5,4)."""
        table = Classification.__table__
        confidence_col = table.c.confidence

        # Check type
        assert str(confidence_col.type) == "NUMERIC(5, 4)"

    def test_ml_metadata_jsonb_type(self):
        """Test that metadata column is JSONB."""
        table = Classification.__table__
        metadata_col = table.c.metadata

        # Check type name
        assert "JSONB" in str(metadata_col.type)


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
        """Test classification with very low confidence (0.0001)."""
        # Arrange & Act
        classification = Classification(product_id=1, confidence=0.0001)

        # Assert
        assert float(classification.confidence) == 0.0001

    def test_zero_confidence(self):
        """Test classification with zero confidence (valid but suspicious)."""
        # Arrange & Act
        classification = Classification(product_id=1, confidence=0.0)

        # Assert
        assert float(classification.confidence) == 0.0

    def test_perfect_confidence(self):
        """Test classification with perfect confidence (1.0)."""
        # Arrange & Act
        classification = Classification(product_id=1, confidence=1.0)

        # Assert
        assert float(classification.confidence) == 1.0

    def test_complex_ml_metadata_with_arrays(self):
        """Test ml_metadata with complex nested arrays."""
        # Arrange
        metadata = {
            "model_name": "yolov11n",
            "predictions": [
                {"class": "echeveria", "confidence": 0.95},
                {"class": "aloe", "confidence": 0.03},
                {"class": "haworthia", "confidence": 0.02},
            ],
            "bounding_boxes": [[10, 20, 100, 150], [200, 300, 50, 75]],
        }

        # Act
        classification = Classification(product_id=1, confidence=0.95, ml_metadata=metadata)

        # Assert
        assert len(classification.ml_metadata["predictions"]) == 3
        assert classification.ml_metadata["predictions"][0]["class"] == "echeveria"
        assert len(classification.ml_metadata["bounding_boxes"]) == 2

    def test_ml_metadata_with_timestamps(self):
        """Test ml_metadata with timestamp strings."""
        # Arrange
        metadata = {
            "model_version": "1.2.0",
            "inference_timestamp": "2025-10-14T14:30:00Z",
            "model_trained_at": "2025-09-01T00:00:00Z",
        }

        # Act
        classification = Classification(product_id=1, confidence=0.90, ml_metadata=metadata)

        # Assert
        assert "2025-10-14" in classification.ml_metadata["inference_timestamp"]
        assert "2025-09-01" in classification.ml_metadata["model_trained_at"]
