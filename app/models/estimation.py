"""Estimation model - Dense vegetation count estimation results from YOLO model.

This module defines the Estimation SQLAlchemy model for storing dense vegetation
count estimation results. Each estimation represents ONE dense area where individual
plants cannot be separated, requiring band/density-based counting.

Architecture:
    Layer: Database / Models (Infrastructure Layer)
    Dependencies: SQLAlchemy 2.0, PostgreSQL 18
    Pattern: ML inference results (NO seed data, ML-generated)

Design Decisions:
    - PARTITIONED by session_id: Daily partitioning for millions of estimations
    - THREE FKs: session_id + stock_movement_id + classification_id (all CASCADE)
    - JSONB vegetation_polygon: Full polygon coordinates for dense area
    - Calculation method enum: band_estimation|density_estimation|grid_analysis
    - Estimation confidence: 0.0-1.0 (default 0.70 for estimations)
    - used_density_parameters flag: Tracks if density params were used
    - Timestamps: created_at only (immutable record)

See:
    - Database ERD: ../../database/database.mmd (lines 277-289)
    - Database docs: ../../engineering_plan/database/README.md

Example:
    ```python
    # Create estimation
    estimation = Estimation(
        session_id=1,
        stock_movement_id=1,
        classification_id=1,
        vegetation_polygon={"coordinates": [[x1, y1], [x2, y2], ...]},
        detected_area_cm2=250.5,
        estimated_count=15,
        calculation_method="band_estimation",
        estimation_confidence=0.75,
        used_density_parameters=True
    )

    # Query by session
    estimations = session.query(Estimation).filter_by(session_id=1).all()

    # Query by method
    band_estimations = session.query(Estimation).filter_by(
        calculation_method="band_estimation"
    ).all()
    ```
"""

import enum
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Enum,
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


class CalculationMethodEnum(str, enum.Enum):
    """Estimation calculation method enum.

    Calculation methods:
        - BAND_ESTIMATION: Band-based counting (colored bands on pot rims)
        - DENSITY_ESTIMATION: Density-based counting (avg plants per m²)
        - GRID_ANALYSIS: Grid-based counting (divide area into cells)

    Note: This is a Python enum for type hints. The actual database ENUM
    is created in the migration file.
    """

    BAND_ESTIMATION = "band_estimation"
    DENSITY_ESTIMATION = "density_estimation"
    GRID_ANALYSIS = "grid_analysis"


class Estimation(Base):
    """Estimation model representing dense vegetation count estimation results.

    Stores count estimation results for dense vegetation areas where individual
    plants cannot be separated by object detection. Uses band detection, density
    parameters, or grid analysis to estimate plant counts.

    CRITICAL: This table is PARTITIONED by session_id (daily) to handle millions
    of estimations efficiently.

    Key Features:
        - PARTITIONED table: By session_id for scalability
        - THREE FKs: session_id + stock_movement_id + classification_id (all CASCADE)
        - JSONB vegetation_polygon: Full polygon coordinates
        - Calculation method enum: band_estimation|density_estimation|grid_analysis
        - Estimation confidence: 0.0-1.0 (default 0.70)
        - used_density_parameters flag: Tracks density param usage
        - Immutable: created_at only (NO updated_at)

    Attributes:
        id: Primary key (auto-increment)
        session_id: FK to photo_processing_sessions (CASCADE, NOT NULL)
        stock_movement_id: FK to stock_movements (CASCADE, NOT NULL)
        classification_id: FK to classifications (CASCADE, NOT NULL)
        vegetation_polygon: JSONB full polygon coordinates for dense area
        detected_area_cm2: Detected vegetation area in cm² (NUMERIC)
        estimated_count: Estimated plant count (INTEGER, NOT NULL)
        calculation_method: Calculation method enum (NOT NULL)
        estimation_confidence: ML confidence score (0.0-1.0, default 0.70)
        used_density_parameters: Density parameters usage flag (NOT NULL)
        created_at: Estimation timestamp (auto, immutable)

    Relationships:
        session: PhotoProcessingSession instance (many-to-one)
        stock_movement: StockMovement instance (many-to-one)
        classification: Classification instance (many-to-one)

    Indexes:
        - B-tree index on session_id (foreign key, partition key)
        - B-tree index on stock_movement_id (foreign key)
        - B-tree index on classification_id (foreign key)
        - B-tree index on calculation_method (filter by method)
        - B-tree index on created_at DESC (time-series queries)

    Constraints:
        - CHECK estimation_confidence between 0.0 and 1.0
        - CHECK detected_area_cm2 >= 0.0
        - CHECK estimated_count >= 0

    Example:
        ```python
        # Create estimation
        estimation = Estimation(
            session_id=1,
            stock_movement_id=1,
            classification_id=1,
            vegetation_polygon={"coordinates": [[x1, y1], [x2, y2], ...]},
            detected_area_cm2=250.5,
            estimated_count=15,
            calculation_method="band_estimation",
            estimation_confidence=0.75,
            used_density_parameters=True
        )

        # Query by session
        estimations = session.query(Estimation).filter_by(
            session_id=1
        ).all()

        # Query high-confidence estimations
        high_conf = session.query(Estimation).filter(
            Estimation.estimation_confidence >= 0.80
        ).all()
        ```
    """

    __tablename__ = "estimations"

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

    # JSONB vegetation polygon
    vegetation_polygon = Column(
        JSONB,
        nullable=False,
        comment="Full polygon coordinates for dense vegetation area",
    )

    # Detected area in cm²
    detected_area_cm2 = Column(
        Numeric(15, 2),
        nullable=False,
        comment="Detected vegetation area in cm² (CHECK >= 0.0)",
    )

    # Estimated count
    estimated_count = Column(
        Integer,
        nullable=False,
        comment="Estimated plant count (CHECK >= 0)",
    )

    # Calculation method enum
    calculation_method = Column(
        Enum(
            CalculationMethodEnum,
            name="calculation_method_enum",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        index=True,
        comment="Calculation method (band_estimation|density_estimation|grid_analysis)",
    )

    # Estimation confidence (default 0.70)
    estimation_confidence = Column(
        Numeric(5, 4),
        nullable=False,
        default=0.70,
        comment="ML confidence score (0.0000-1.0000, default 0.70)",
    )

    # Density parameters usage flag
    used_density_parameters = Column(
        Boolean,
        nullable=False,
        comment="Density parameters usage flag (NOT NULL)",
    )

    # Timestamp (immutable record)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=datetime.utcnow,
        nullable=False,
        comment="Estimation timestamp (immutable)",
    )

    # Relationships

    # Many-to-one: Estimation → PhotoProcessingSession
    session: Mapped["PhotoProcessingSession"] = relationship(
        "PhotoProcessingSession",
        back_populates="estimations",
        doc="Photo processing session for this estimation",
    )

    # Many-to-one: Estimation → StockMovement
    stock_movement: Mapped["StockMovement"] = relationship(
        "StockMovement",
        back_populates="estimations",
        doc="Stock movement for this estimation",
    )

    # Many-to-one: Estimation → Classification
    classification: Mapped["Classification"] = relationship(
        "Classification",
        back_populates="estimations",
        doc="ML classification for this estimation",
    )

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "estimation_confidence >= 0.0 AND estimation_confidence <= 1.0",
            name="ck_estimation_confidence_range",
        ),
        CheckConstraint(
            "detected_area_cm2 >= 0.0",
            name="ck_estimation_area_positive",
        ),
        CheckConstraint(
            "estimated_count >= 0",
            name="ck_estimation_count_positive",
        ),
        {
            "comment": "Estimations - Dense vegetation count estimation results from YOLO model. PARTITIONED by session_id."
        },
    )

    @validates("estimation_confidence")
    def validate_confidence(self, key: str, value: float | None) -> float | None:
        """Validate estimation_confidence field.

        Rules:
            - Must be between 0.0 and 1.0 (inclusive)
            - Cannot be None

        Args:
            key: Field name ("estimation_confidence")
            value: Confidence value to validate

        Returns:
            Validated confidence value

        Raises:
            ValueError: If confidence is invalid
        """
        if value is None:
            raise ValueError("estimation_confidence cannot be None")

        if not (0.0 <= value <= 1.0):
            raise ValueError(f"estimation_confidence must be between 0.0 and 1.0 (got: {value})")

        return value

    @validates("detected_area_cm2")
    def validate_area(self, key: str, value: float | None) -> float | None:
        """Validate detected_area_cm2 field.

        Rules:
            - Must be non-negative (>= 0.0)
            - Cannot be None

        Args:
            key: Field name ("detected_area_cm2")
            value: Area value to validate

        Returns:
            Validated area value

        Raises:
            ValueError: If area is invalid
        """
        if value is None:
            raise ValueError("detected_area_cm2 cannot be None")

        if value < 0.0:
            raise ValueError(f"detected_area_cm2 must be non-negative (got: {value})")

        return value

    @validates("estimated_count")
    def validate_count(self, key: str, value: int | None) -> int | None:
        """Validate estimated_count field.

        Rules:
            - Must be non-negative (>= 0)
            - Cannot be None

        Args:
            key: Field name ("estimated_count")
            value: Count value to validate

        Returns:
            Validated count value

        Raises:
            ValueError: If count is invalid
        """
        if value is None:
            raise ValueError("estimated_count cannot be None")

        if value < 0:
            raise ValueError(f"estimated_count must be non-negative (got: {value})")

        return value

    @validates("vegetation_polygon")
    def validate_polygon(self, key: str, value: dict[str, Any] | None) -> dict[str, Any]:
        """Validate vegetation_polygon JSONB field.

        Rules:
            - Must be a dict
            - Cannot be None

        Args:
            key: Field name ("vegetation_polygon")
            value: Polygon dict to validate

        Returns:
            Validated polygon dict

        Raises:
            ValueError: If polygon is invalid
        """
        if value is None:
            raise ValueError("vegetation_polygon cannot be None")

        if not isinstance(value, dict):
            raise ValueError("vegetation_polygon must be a dict")

        return value

    def __repr__(self) -> str:
        """String representation for debugging.

        Returns:
            String with id, session_id, estimated_count, and method

        Example:
            <Estimation(id=1, session_id=1, estimated_count=15, method='band_estimation')>
        """
        method_value = (
            self.calculation_method.value
            if isinstance(self.calculation_method, CalculationMethodEnum)
            else self.calculation_method
        )
        return (
            f"<Estimation("
            f"id={self.id}, "
            f"session_id={self.session_id}, "
            f"estimated_count={self.estimated_count}, "
            f"method='{method_value}'"
            f")>"
        )
