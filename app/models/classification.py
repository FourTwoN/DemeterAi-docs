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
    - THREE confidence fields: product_conf, packaging_conf, product_size_conf (INTEGER)
    - model_version: VARCHAR for ML model tracking
    - name: VARCHAR for classification name
    - description: TEXT for detailed notes
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
        product_conf=95,
        packaging_conf=87,
        product_size_conf=92,
        model_version="yolov11n-seg-v1.2.0",
        name="Echeveria Adult Medium",
        description="High confidence detection in all categories"
    )

    # Query by confidence threshold
    high_confidence = session.query(Classification).filter(
        Classification.product_conf >= 85
    ).all()

    # Query by model version
    v1_classifications = session.query(Classification).filter(
        Classification.model_version.like("yolov11n-seg-v1%")
    ).all()
    ```
"""

from typing import TYPE_CHECKING, Any

from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, relationship
from sqlalchemy.sql import func

from app.db.base import Base

# Forward declarations for type hints (avoids circular imports)
if TYPE_CHECKING:
    from app.models.detection import Detection
    from app.models.estimation import Estimation
    from app.models.packaging_catalog import PackagingCatalog
    from app.models.product import Product
    from app.models.product_size import ProductSize


class Classification(Base):
    """Classification model representing ML prediction results.

    Stores YOLO v11 inference results linking detections/estimations to actual
    entities (products, packaging, sizes) with confidence scores. This is the
    "ML prediction cache" - stores model outputs to avoid re-running inference.

    Key Features:
        - THREE nullable FKs: product_id, packaging_catalog_id, product_size_id
        - At least ONE FK must be NOT NULL (CHECK constraint enforced)
        - ALL FKs use CASCADE delete (invalid if referenced entity deleted)
        - THREE confidence fields: product_conf, packaging_conf, product_size_conf (INTEGER 0-100)
        - ML model tracking: model_version field (VARCHAR)
        - Name and description fields for classification metadata
        - NO seed data: Created by ML pipeline during inference

    Attributes:
        classification_id: Primary key (auto-increment) - DB column is "id"
        product_id: Foreign key to products (CASCADE, NULLABLE)
        packaging_catalog_id: Foreign key to packaging_catalog (CASCADE, NULLABLE)
        product_size_id: Foreign key to product_sizes (CASCADE, NULLABLE)
        product_conf: Product classification confidence (INTEGER, NULLABLE)
        packaging_conf: Packaging classification confidence (INTEGER, NULLABLE)
        product_size_conf: Size classification confidence (INTEGER, NULLABLE)
        model_version: ML model version (VARCHAR, NULLABLE)
        name: Classification name (VARCHAR, NULLABLE)
        description: Detailed description (TEXT, NULLABLE)
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

    Constraints:
        - CHECK at least ONE of (product_id, packaging_catalog_id, product_size_id) NOT NULL

    Example:
        ```python
        # Create classification with product + packaging
        classification = Classification(
            product_id=42,
            packaging_catalog_id=7,
            product_conf=95,
            packaging_conf=87,
            model_version="yolov11n-seg-v1.2.0",
            name="Echeveria Adult",
            description="High confidence detection"
        )

        # Query by product confidence threshold
        high_conf = session.query(Classification).filter(
            Classification.product_conf >= 85
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

    # Confidence scores (INTEGER, NULLABLE)
    product_conf = Column(
        Integer,
        nullable=True,
        comment="Product classification confidence (0-100, NULLABLE)",
    )

    packaging_conf = Column(
        Integer,
        nullable=True,
        comment="Packaging classification confidence (0-100, NULLABLE)",
    )

    product_size_conf = Column(
        Integer,
        nullable=True,
        comment="Size classification confidence (0-100, NULLABLE)",
    )

    # ML model metadata
    model_version = Column(
        String(100),
        nullable=True,
        comment="ML model version (e.g., 'yolov11n-seg-v1.2.0')",
    )

    # Descriptive fields
    name = Column(
        String(255),
        nullable=True,
        comment="Classification name",
    )

    description = Column(
        Text,
        nullable=True,
        comment="Detailed description",
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
    packaging_catalog: Mapped["PackagingCatalog | None"] = relationship(
        "PackagingCatalog",
        back_populates="classifications",
        doc="Packaging this classification predicts (optional)",
    )

    # Many-to-one: Classification → ProductSize (optional)
    product_size: Mapped["ProductSize | None"] = relationship(
        "ProductSize",
        back_populates="classifications",
        doc="Product size this classification predicts (optional)",
    )

    # One-to-many: Classification → Detection
    detections: Mapped[list["Detection"]] = relationship(
        "Detection",
        back_populates="classification",
        foreign_keys="Detection.classification_id",
        doc="List of detections using this classification",
    )

    # One-to-many: Classification → Estimation
    estimations: Mapped[list["Estimation"]] = relationship(
        "Estimation",
        back_populates="classification",
        foreign_keys="Estimation.classification_id",
        doc="List of estimations using this classification",
    )

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "product_id IS NOT NULL OR packaging_catalog_id IS NOT NULL OR product_size_id IS NOT NULL",
            name="ck_classification_at_least_one_fk",
        ),
        {
            "comment": "Classifications - ML prediction cache (product + packaging + size inference). NO seed data."
        },
    )

    def __init__(self, **kwargs: Any) -> None:
        """Initialize Classification.

        Validates that at least ONE of (product_id, packaging_catalog_id, product_size_id)
        is provided (NOT NULL).
        """
        # Validate at least one FK is provided
        product_id = kwargs.get("product_id")
        packaging_catalog_id = kwargs.get("packaging_catalog_id")
        product_size_id = kwargs.get("product_size_id")

        if product_id is None and packaging_catalog_id is None and product_size_id is None:
            raise ValueError(
                "At least one of (product_id, packaging_catalog_id, product_size_id) must be NOT NULL"
            )

        super().__init__(**kwargs)

    def __repr__(self) -> str:
        """String representation for debugging.

        Returns:
            String with classification_id, product_id, product_conf

        Example:
            <Classification(classification_id=1, product_id=42, product_conf=95)>
        """
        return (
            f"<Classification("
            f"classification_id={self.classification_id}, "
            f"product_id={self.product_id}, "
            f"packaging_catalog_id={self.packaging_catalog_id}, "
            f"product_size_id={self.product_size_id}, "
            f"product_conf={self.product_conf}"
            f")>"
        )
