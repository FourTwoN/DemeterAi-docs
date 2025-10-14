"""Detection model - Individual plant detection results from YOLO model.

This module defines the Detection SQLAlchemy model for storing individual plant
detection results from YOLO object detection model. Each detection represents
ONE detected plant with bounding box coordinates and classification.

Architecture:
    Layer: Database / Models (Infrastructure Layer)
    Dependencies: SQLAlchemy 2.0, PostgreSQL 18
    Pattern: ML inference results (NO seed data, ML-generated)

Design Decisions:
    - PARTITIONED by session_id: Daily partitioning for millions of detections
    - THREE FKs: session_id + stock_movement_id + classification_id (all CASCADE)
    - Bounding box: center_x_px, center_y_px, width_px, height_px
    - GENERATED area_px: width_px * height_px (auto-calculated)
    - JSONB bbox_coordinates: Full bbox data {x1, y1, x2, y2}
    - Boolean flags: is_empty_container, is_alive
    - Confidence: detection_confidence (0.0-1.0)
    - Timestamps: created_at only (immutable record)

See:
    - Database ERD: ../../database/database.mmd (lines 261-276)
    - Database docs: ../../engineering_plan/database/README.md

Example:
    ```python
    # Create detection
    detection = Detection(
        session_id=1,
        stock_movement_id=1,
        classification_id=1,
        center_x_px=512.5,
        center_y_px=768.3,
        width_px=120,
        height_px=135,
        bbox_coordinates={"x1": 452, "y1": 700, "x2": 572, "y2": 835},
        detection_confidence=0.95,
        is_empty_container=False,
        is_alive=True
    )

    # Query by session
    detections = session.query(Detection).filter_by(session_id=1).all()

    # Query high-confidence detections
    high_conf = session.query(Detection).filter(
        Detection.detection_confidence >= 0.90
    ).all()
    ```
"""

from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, relationship, validates
from sqlalchemy.sql import func

from app.db.base import Base

# Forward declarations for type hints (avoids circular imports)
if TYPE_CHECKING:
    from app.models.classification import Classification
    from app.models.photo_processing_session import PhotoProcessingSession
    from app.models.stock_movement import StockMovement


class Detection(Base):
    """Detection model representing individual plant detection results.

    Stores YOLO object detection results for individual plants detected in
    photos. Each detection represents ONE plant with bounding box coordinates,
    classification, and confidence score.

    CRITICAL: This table is PARTITIONED by session_id (daily) to handle millions
    of detections efficiently.

    Key Features:
        - PARTITIONED table: By session_id for scalability
        - THREE FKs: session_id + stock_movement_id + classification_id (all CASCADE)
        - Bounding box: center_x_px, center_y_px, width_px, height_px
        - GENERATED area_px: width_px * height_px (auto-calculated)
        - JSONB bbox_coordinates: Full bbox data {x1, y1, x2, y2}
        - Boolean flags: is_empty_container, is_alive
        - Confidence: detection_confidence (0.0-1.0)
        - Immutable: created_at only (NO updated_at)

    Attributes:
        id: Primary key (auto-increment)
        session_id: FK to photo_processing_sessions (CASCADE, NOT NULL)
        stock_movement_id: FK to stock_movements (CASCADE, NOT NULL)
        classification_id: FK to classifications (CASCADE, NOT NULL)
        center_x_px: Bounding box center X coordinate in pixels (NUMERIC)
        center_y_px: Bounding box center Y coordinate in pixels (NUMERIC)
        width_px: Bounding box width in pixels (INTEGER)
        height_px: Bounding box height in pixels (INTEGER)
        area_px: Bounding box area (GENERATED = width_px * height_px)
        bbox_coordinates: JSONB full bbox data {x1, y1, x2, y2}
        detection_confidence: ML confidence score (0.0-1.0, NOT NULL)
        is_empty_container: Empty container flag (default False)
        is_alive: Plant alive flag (default True)
        created_at: Detection timestamp (auto, immutable)

    Relationships:
        session: PhotoProcessingSession instance (many-to-one)
        stock_movement: StockMovement instance (many-to-one)
        classification: Classification instance (many-to-one)

    Indexes:
        - B-tree index on session_id (foreign key, partition key)
        - B-tree index on stock_movement_id (foreign key)
        - B-tree index on classification_id (foreign key)
        - B-tree index on detection_confidence DESC (high confidence queries)
        - B-tree index on created_at DESC (time-series queries)

    Constraints:
        - CHECK detection_confidence between 0.0 and 1.0
        - CHECK width_px > 0
        - CHECK height_px > 0

    Example:
        ```python
        # Create detection
        detection = Detection(
            session_id=1,
            stock_movement_id=1,
            classification_id=1,
            center_x_px=512.5,
            center_y_px=768.3,
            width_px=120,
            height_px=135,
            bbox_coordinates={"x1": 452, "y1": 700, "x2": 572, "y2": 835},
            detection_confidence=0.95
        )

        # Query by session
        detections = session.query(Detection).filter_by(
            session_id=1
        ).all()

        # Query live plants only
        live = session.query(Detection).filter_by(
            is_alive=True,
            is_empty_container=False
        ).all()
        ```
    """

    __tablename__ = "detections"

    # Primary key
    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Primary key (auto-increment)",
    )

    # Foreign key to photo processing session (CASCADE delete, PARTITION KEY)
    session_id = Column(
        Integer,
        ForeignKey("photo_processing_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to photo_processing_sessions (CASCADE delete, PARTITION KEY)",
    )

    # Foreign key to stock movement (CASCADE delete)
    stock_movement_id = Column(
        Integer,
        ForeignKey("stock_movements.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to stock_movements (CASCADE delete)",
    )

    # Foreign key to classification (CASCADE delete)
    classification_id = Column(
        Integer,
        ForeignKey("classifications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to classifications (CASCADE delete)",
    )

    # Bounding box coordinates
    center_x_px = Column(
        Numeric(10, 2),
        nullable=False,
        comment="Bounding box center X coordinate in pixels",
    )

    center_y_px = Column(
        Numeric(10, 2),
        nullable=False,
        comment="Bounding box center Y coordinate in pixels",
    )

    width_px = Column(
        Integer,
        nullable=False,
        comment="Bounding box width in pixels (CHECK > 0)",
    )

    height_px = Column(
        Integer,
        nullable=False,
        comment="Bounding box height in pixels (CHECK > 0)",
    )

    # GENERATED area_px column
    # NOTE: This column is added via Alembic migration, not here
    # PostgreSQL syntax: GENERATED ALWAYS AS (width_px * height_px) STORED
    area_px = Column(
        Numeric(15, 2),
        nullable=True,
        comment="Bounding box area in pixels (GENERATED = width_px * height_px)",
    )

    # JSONB full bbox coordinates
    bbox_coordinates = Column(
        JSONB,
        nullable=False,
        comment="Full bounding box coordinates {x1, y1, x2, y2}",
    )

    # Confidence score
    detection_confidence = Column(
        Numeric(5, 4),
        nullable=False,
        comment="ML confidence score (0.0000-1.0000)",
    )

    # Boolean flags
    is_empty_container = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Empty container flag (default False)",
    )

    is_alive = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="Plant alive flag (default True)",
    )

    # Timestamp (immutable record)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Detection timestamp (immutable)",
    )

    # Relationships

    # Many-to-one: Detection → PhotoProcessingSession
    session: Mapped["PhotoProcessingSession"] = relationship(
        "PhotoProcessingSession",
        back_populates="detections",
        doc="Photo processing session for this detection",
    )

    # Many-to-one: Detection → StockMovement
    stock_movement: Mapped["StockMovement"] = relationship(
        "StockMovement",
        back_populates="detections",
        doc="Stock movement for this detection",
    )

    # Many-to-one: Detection → Classification
    classification: Mapped["Classification"] = relationship(
        "Classification",
        back_populates="detections",
        doc="ML classification for this detection",
    )

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "detection_confidence >= 0.0 AND detection_confidence <= 1.0",
            name="ck_detection_confidence_range",
        ),
        CheckConstraint(
            "width_px > 0",
            name="ck_detection_width_positive",
        ),
        CheckConstraint(
            "height_px > 0",
            name="ck_detection_height_positive",
        ),
        {
            "comment": "Detections - Individual plant detection results from YOLO model. PARTITIONED by session_id."
        },
    )

    @validates("detection_confidence")
    def validate_confidence(self, key: str, value: float | None) -> float | None:
        """Validate detection_confidence field.

        Rules:
            - Must be between 0.0 and 1.0 (inclusive)
            - Cannot be None

        Args:
            key: Field name ("detection_confidence")
            value: Confidence value to validate

        Returns:
            Validated confidence value

        Raises:
            ValueError: If confidence is invalid
        """
        if value is None:
            raise ValueError("detection_confidence cannot be None")

        if not (0.0 <= value <= 1.0):
            raise ValueError(f"detection_confidence must be between 0.0 and 1.0 (got: {value})")

        return value

    @validates("width_px", "height_px")
    def validate_dimensions(self, key: str, value: int | None) -> int | None:
        """Validate width_px and height_px fields.

        Rules:
            - Must be positive integers (> 0)
            - Cannot be None

        Args:
            key: Field name (width_px or height_px)
            value: Dimension value to validate

        Returns:
            Validated dimension value

        Raises:
            ValueError: If dimension is invalid
        """
        if value is None:
            raise ValueError(f"{key} cannot be None")

        if value <= 0:
            raise ValueError(f"{key} must be positive (got: {value})")

        return value

    @validates("bbox_coordinates")
    def validate_bbox_coordinates(self, key: str, value: dict[str, Any] | None) -> dict[str, Any]:
        """Validate bbox_coordinates JSONB field.

        Rules:
            - Must be a dict with keys: x1, y1, x2, y2
            - Cannot be None

        Args:
            key: Field name ("bbox_coordinates")
            value: Bbox coordinates dict to validate

        Returns:
            Validated bbox coordinates dict

        Raises:
            ValueError: If bbox_coordinates is invalid
        """
        if value is None:
            raise ValueError("bbox_coordinates cannot be None")

        if not isinstance(value, dict):
            raise ValueError("bbox_coordinates must be a dict")

        required_keys = {"x1", "y1", "x2", "y2"}
        if not required_keys.issubset(value.keys()):
            raise ValueError(f"bbox_coordinates must contain keys: {required_keys}")

        return value

    def __repr__(self) -> str:
        """String representation for debugging.

        Returns:
            String with id, session_id, classification_id, and confidence

        Example:
            <Detection(id=1, session_id=1, classification_id=1, confidence=0.95)>
        """
        return (
            f"<Detection("
            f"id={self.id}, "
            f"session_id={self.session_id}, "
            f"classification_id={self.classification_id}, "
            f"confidence={self.detection_confidence}"
            f")>"
        )
