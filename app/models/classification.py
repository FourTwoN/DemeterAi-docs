"""Classification model - ML prediction cache for product/packaging/size inference.

This module defines the Classification SQLAlchemy model for storing ML model predictions
(YOLO v11 inference results) that link detections/estimations to actual entities
(products, packaging, sizes) with confidence scores.

Architecture:
    Layer: Database / Models (Infrastructure Layer)
    Dependencies: SQLAlchemy 2.0, PostgreSQL 18
    Pattern: ML prediction cache (NO seed data, ML-generated)

Design Decisions:
    - THREE nullable FKs: product_id, packaging_catalog_id, product_size_id (all CASCADE)
    - At least ONE FK must be NOT NULL (enforced by CHECK constraint)
    - JSONB metadata: ML model info (model_name, version, inference_time, etc.)
    - Numeric(5,4) confidence: 0.0000-1.0000 range (4 decimal precision)
    - NO name/description fields (per user requirements - simplified schema)
    - INT PK: Simple auto-increment (classification_id mapped to "id" in DB)
    - created_at timestamp: Auto-generated

Business Context:
    This is the "ML prediction cache" - stores YOLO v11 model outputs so we don't
    re-run expensive inference. Each classification represents ONE inference result
    that may predict product type, packaging type, and/or product size.

    Flow: Photo → YOLO Segmentation → YOLO Detection → Classifications → Detections/Estimations

See:
    - Database ERD: ../../database/database.mmd (lines 290-302)
    - Task specification: ../../backlog/03_kanban/02_in-progress/DB026-classifications-model.md

Example:
    ```python
    # Create classification with all fields
    classification = Classification(
        product_id=42,
        packaging_catalog_id=7,
        product_size_id=3,
        confidence=0.9523,
        ml_metadata={
            "model_name": "yolov11n-seg",
            "model_version": "1.2.0",
            "inference_time_ms": 145,
            "gpu_used": False,
            "temperature": 0.7
        }
    )

    # Query by confidence threshold
    high_confidence = session.query(Classification).filter(
        Classification.confidence >= 0.85
    ).all()

    # Query by metadata (JSONB)
    gpu_classifications = session.query(Classification).filter(
        Classification.ml_metadata["gpu_used"].astext == "true"
    ).all()
    ```
"""

from typing import TYPE_CHECKING, Any

from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Integer, Numeric
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, relationship, validates
from sqlalchemy.sql import func

from app.db.base import Base

# Forward declarations for type hints (avoids circular imports)
if TYPE_CHECKING:
    from app.models.product import Product
    from app.models.product_size import ProductSize

    # NOTE: Uncomment after dependent models are complete
    # from app.models.packaging_catalog import PackagingCatalog
    # from app.models.detection import Detection
    # from app.models.estimation import Estimation


class Classification(Base):
    """Classification model representing ML prediction results.

    Stores YOLO v11 inference results linking detections/estimations to actual
    entities (products, packaging, sizes) with confidence scores. This is the
    "ML prediction cache" - stores model outputs to avoid re-running inference.

    Key Features:
        - THREE nullable FKs: product_id, packaging_catalog_id, product_size_id
        - At least ONE FK must be NOT NULL (CHECK constraint enforced)
        - ALL FKs use CASCADE delete (invalid if referenced entity deleted)
        - Confidence: Numeric(5,4) for 0.0000-1.0000 range (4 decimals)
        - JSONB metadata: ML model info (model_name, version, inference_time, etc.)
        - NO seed data: Created by ML pipeline during inference

    Attributes:
        classification_id: Primary key (auto-increment) - DB column is "id"
        product_id: Foreign key to products (CASCADE, NULLABLE)
        packaging_catalog_id: Foreign key to packaging_catalog (CASCADE, NULLABLE)
        product_size_id: Foreign key to product_sizes (CASCADE, NULLABLE)
        confidence: Overall classification confidence (0.0000-1.0000, NOT NULL)
        ml_metadata: JSONB flexible ML model metadata (model_name, version, etc.)
        created_at: Timestamp (auto-generated, NOT NULL)

    Relationships:
        product: Product instance (many-to-one, optional)
        packaging_catalog: PackagingCatalog instance (many-to-one, optional)
        product_size: ProductSize instance (many-to-one, optional)
        detections: List of Detection instances (one-to-many, COMMENTED OUT)
        estimations: List of Estimation instances (one-to-many, COMMENTED OUT)

    Indexes:
        - B-tree index on product_id (foreign key, common queries)
        - B-tree index on created_at DESC (time-series queries)
        - GIN index on metadata (JSONB queries)

    Constraints:
        - CHECK confidence between 0.0 and 1.0
        - CHECK at least ONE of (product_id, packaging_catalog_id, product_size_id) NOT NULL

    Example:
        ```python
        # Create classification with product + packaging
        classification = Classification(
            product_id=42,
            packaging_catalog_id=7,
            confidence=0.9523,
            ml_metadata={
                "model_name": "yolov11n-seg",
                "model_version": "1.2.0",
                "inference_time_ms": 145
            }
        )

        # Query by confidence threshold
        high_conf = session.query(Classification).filter(
            Classification.confidence >= 0.85
        ).all()

        # JSONB query
        gpu_results = session.query(Classification).filter(
            Classification.ml_metadata["gpu_used"].astext == "true"
        ).all()
        ```
    """

    __tablename__ = "classifications"

    # Primary key
    classification_id = Column(
        "id",  # Database column name is "id" (per ERD)
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Primary key (auto-increment)",
    )

    # Foreign keys (ALL nullable, ALL CASCADE)
    product_id = Column(
        Integer,
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Foreign key to products (CASCADE delete, NULLABLE)",
    )

    packaging_catalog_id = Column(
        Integer,
        ForeignKey("packaging_catalog.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Foreign key to packaging_catalog (CASCADE delete, NULLABLE)",
    )

    product_size_id = Column(
        Integer,
        ForeignKey("product_sizes.product_size_id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Foreign key to product_sizes (CASCADE delete, NULLABLE)",
    )

    # Confidence score (0.0000-1.0000)
    confidence = Column(
        Numeric(5, 4),
        nullable=False,
        comment="Overall classification confidence (0.0000-1.0000, 4 decimals)",
    )

    # JSONB metadata for ML model info
    ml_metadata = Column(
        "metadata",  # Database column name is "metadata" (per ERD)
        JSONB,
        nullable=True,
        default=lambda: {},
        server_default="{}",
        comment="ML model metadata (model_name, version, inference_time_ms, gpu_used, etc.)",
    )

    # Timestamp
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Creation timestamp (auto-generated)",
    )

    # Relationships

    # Many-to-one: Classification → Product (optional)
    product: Mapped["Product | None"] = relationship(
        "Product",
        back_populates="classifications",
        doc="Product this classification predicts (optional)",
    )

    # Many-to-one: Classification → PackagingCatalog (optional)
    # NOTE: Uncomment after PackagingCatalog model is complete
    # packaging_catalog: Mapped["PackagingCatalog | None"] = relationship(
    #     "PackagingCatalog",
    #     back_populates="classifications",
    #     doc="Packaging this classification predicts (optional)",
    # )

    # Many-to-one: Classification → ProductSize (optional)
    product_size: Mapped["ProductSize | None"] = relationship(
        "ProductSize",
        back_populates="classifications",
        doc="Product size this classification predicts (optional)",
    )

    # One-to-many: Classification → Detection (COMMENT OUT - DB013 not ready)
    # NOTE: Uncomment after DB013 (Detection) is complete
    # detections: Mapped[list["Detection"]] = relationship(
    #     "Detection",
    #     back_populates="classification",
    #     foreign_keys="Detection.classification_id",
    #     doc="List of detections using this classification"
    # )

    # One-to-many: Classification → Estimation (COMMENT OUT - DB014 not ready)
    # NOTE: Uncomment after DB014 (Estimation) is complete
    # estimations: Mapped[list["Estimation"]] = relationship(
    #     "Estimation",
    #     back_populates="classification",
    #     foreign_keys="Estimation.classification_id",
    #     doc="List of estimations using this classification"
    # )

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "confidence >= 0.0 AND confidence <= 1.0",
            name="ck_classification_confidence_range",
        ),
        CheckConstraint(
            "product_id IS NOT NULL OR packaging_catalog_id IS NOT NULL OR product_size_id IS NOT NULL",
            name="ck_classification_at_least_one_fk",
        ),
        {
            "comment": "Classifications - ML prediction cache (product + packaging + size inference). NO seed data."
        },
    )

    @validates("confidence")
    def validate_confidence(self, key: str, value: float | None) -> float | None:
        """Validate confidence field.

        Rules:
            - Must be between 0.0 and 1.0 (inclusive)
            - Cannot be None

        Args:
            key: Field name ("confidence")
            value: Confidence value to validate

        Returns:
            Validated confidence value

        Raises:
            ValueError: If confidence is invalid

        Examples:
            >>> classification.confidence = 0.9523
            >>> classification.confidence
            0.9523

            >>> classification.confidence = 1.5  # Too high
            ValueError: Confidence must be between 0.0 and 1.0 (got: 1.5)

            >>> classification.confidence = None
            ValueError: Confidence cannot be None
        """
        if value is None:
            raise ValueError("Confidence cannot be None")

        # Validate range
        if not (0.0 <= value <= 1.0):
            raise ValueError(f"Confidence must be between 0.0 and 1.0 (got: {value})")

        return value

    def __init__(self, **kwargs: Any) -> None:
        """Initialize Classification with default ml_metadata.

        Validates that at least ONE of (product_id, packaging_catalog_id, product_size_id)
        is provided (NOT NULL).
        """
        # Ensure ml_metadata is always a dict
        if "ml_metadata" not in kwargs or kwargs.get("ml_metadata") is None:
            kwargs["ml_metadata"] = {}

        # Validate at least one FK is provided
        product_id = kwargs.get("product_id")
        packaging_catalog_id = kwargs.get("packaging_catalog_id")
        product_size_id = kwargs.get("product_size_id")

        if product_id is None and packaging_catalog_id is None and product_size_id is None:
            raise ValueError(
                "At least one of (product_id, packaging_catalog_id, product_size_id) must be NOT NULL"
            )

        super().__init__(**kwargs)

    @validates("ml_metadata")
    def validate_ml_metadata(self, key: str, value: dict[str, Any] | None) -> dict[str, Any]:
        """Validate ml_metadata JSONB field.

        Ensures ml_metadata is always a dict (never None).

        Args:
            key: Field name ("ml_metadata")
            value: ML metadata dict

        Returns:
            Validated ml_metadata dict (empty dict if None)

        Examples:
            >>> classification.ml_metadata = None
            >>> classification.ml_metadata
            {}

            >>> classification.ml_metadata = {"model_name": "yolov11n"}
            >>> classification.ml_metadata
            {"model_name": "yolov11n"}
        """
        if value is None:
            return {}
        return value

    def __repr__(self) -> str:
        """String representation for debugging.

        Returns:
            String with classification_id, product_id, confidence

        Example:
            <Classification(classification_id=1, product_id=42, confidence=0.9523)>
        """
        return (
            f"<Classification("
            f"classification_id={self.classification_id}, "
            f"product_id={self.product_id}, "
            f"packaging_catalog_id={self.packaging_catalog_id}, "
            f"product_size_id={self.product_size_id}, "
            f"confidence={self.confidence}"
            f")>"
        )
