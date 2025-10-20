"""PhotoProcessingSession model - ML photo processing pipeline tracking.

This module defines the PhotoProcessingSession SQLAlchemy model for tracking the
entire ML processing lifecycle from photo upload to ML inference results. Each
session represents ONE photo being processed through the YOLO pipeline.

Architecture:
    Layer: Database / Models (Infrastructure Layer)
    Dependencies: SQLAlchemy 2.0, PostgreSQL 18
    Pattern: ML pipeline tracking (NO seed data, ML-generated)

Design Decisions:
    - UUID session_id: Unique session identifier for idempotent processing
    - TWO S3 image FKs: original_image_id + processed_image_id (CASCADE delete)
    - storage_location_id FK: Optional (nullable, CASCADE delete)
    - validated_by_user_id FK: Optional (nullable, SET NULL on user delete)
    - Status enum: pending | processing | completed | failed
    - JSONB fields: category_counts (detection results) + manual_adjustments (user edits)
    - Aggregates: total_detected, total_estimated, total_empty_containers, avg_confidence
    - INT PK + UUID UK: id (PK) + session_id (UK) pattern
    - Timestamps: created_at + updated_at (auto-managed)

See:
    - Database ERD: ../../database/database.mmd (lines 207-226)
    - Database docs: ../../engineering_plan/database/README.md

Example:
    ```python
    from uuid import uuid4

    # Create photo processing session
    session_id = uuid4()

    session = PhotoProcessingSession(
        session_id=session_id,
        storage_location_id=1,
        original_image_id=original_image_uuid,
        processed_image_id=processed_image_uuid,
        total_detected=42,
        total_estimated=150,
        total_empty_containers=3,
        avg_confidence=0.92,
        category_counts={"echeveria": 25, "aloe": 17},
        status="completed",
        validated=False
    )

    # Query by status
    pending = session.query(PhotoProcessingSession).filter_by(
        status="pending"
    ).all()
    ```
"""

import enum
import uuid
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
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, relationship, validates
from sqlalchemy.sql import func

from app.db.base import Base

# Forward declarations for type hints (avoids circular imports)
if TYPE_CHECKING:
    from app.models.detection import Detection
    from app.models.estimation import Estimation
    from app.models.s3_image import S3Image
    from app.models.stock_movement import StockMovement
    from app.models.storage_location import StorageLocation
    from app.models.user import User


class ProcessingSessionStatusEnum(str, enum.Enum):
    """Photo processing session status enum.

    Processing workflow:
        - PENDING: Session created, waiting for ML processing
        - PROCESSING: ML pipeline is processing the photo
        - COMPLETED: ML processing complete, results available
        - FAILED: ML processing failed (see error_message)

    Note: This is a Python enum for type hints. The actual database ENUM
    is created in the migration file.
    """

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class PhotoProcessingSession(Base):
    """PhotoProcessingSession model representing ML photo processing lifecycle.

    Tracks the entire ML processing pipeline from photo upload to inference
    results. Each session represents ONE photo being processed through YOLO
    segmentation + detection models with validation workflow.

    Key Features:
        - UUID session_id: Unique identifier for idempotent processing
        - TWO S3 image FKs: original_image_id (input) + processed_image_id (output)
        - storage_location_id FK: Optional location context (CASCADE delete)
        - Status enum: pending → processing → completed/failed
        - JSONB category_counts: Detection results by product category
        - JSONB manual_adjustments: User edits to ML results
        - Validation tracking: validated flag + validated_by_user_id + validation_date
        - Aggregates: total_detected, total_estimated, total_empty_containers, avg_confidence

    Attributes:
        id: Primary key (auto-increment)
        session_id: UUID unique identifier (indexed, NOT NULL)
        storage_location_id: Foreign key to storage_locations (CASCADE, NULLABLE)
        original_image_id: Foreign key to s3_images for input photo (CASCADE, NOT NULL)
        processed_image_id: Foreign key to s3_images for output photo (CASCADE, NULLABLE)
        total_detected: Total detections count (default 0)
        total_estimated: Total estimations count (default 0)
        total_empty_containers: Empty container count (default 0)
        avg_confidence: Average ML confidence score (0.0-1.0, NULLABLE)
        category_counts: JSONB detection counts by category (default {})
        status: Processing status enum (pending/processing/completed/failed)
        error_message: Error details if status = failed (NULLABLE)
        validated: Validation flag (default False)
        validated_by_user_id: FK to users who validated (SET NULL, NULLABLE)
        validation_date: Timestamp of validation (NULLABLE)
        manual_adjustments: JSONB user edits to ML results (default {})
        created_at: Session creation timestamp (auto)
        updated_at: Last update timestamp (auto)

    Relationships:
        storage_location: StorageLocation instance (many-to-one, optional)
        original_image: S3Image instance for input photo (many-to-one)
        processed_image: S3Image instance for output photo (many-to-one, optional)
        validated_by_user: User who validated session (many-to-one, optional)
        detections: List of Detection instances (one-to-many)
        estimations: List of Estimation instances (one-to-many)
        stock_movements: List of StockMovement instances (one-to-many)
        storage_locations_latest: StorageLocation instances using this as latest (one-to-many)

    Indexes:
        - B-tree index on session_id (unique constraint)
        - B-tree index on status (filter by status)
        - B-tree index on storage_location_id (foreign key)
        - B-tree index on created_at DESC (time-series queries)
        - GIN index on category_counts (JSONB queries)

    Constraints:
        - CHECK avg_confidence between 0.0 and 1.0 (if not null)
        - CHECK total_detected >= 0
        - CHECK total_estimated >= 0
        - CHECK total_empty_containers >= 0

    Example:
        ```python
        from uuid import uuid4

        # Create session
        session = PhotoProcessingSession(
            session_id=uuid4(),
            storage_location_id=1,
            original_image_id=original_uuid,
            processed_image_id=processed_uuid,
            total_detected=42,
            total_estimated=150,
            avg_confidence=0.92,
            category_counts={"echeveria": 25, "aloe": 17},
            status="completed"
        )

        # Query pending sessions
        pending = session.query(PhotoProcessingSession).filter_by(
            status="pending"
        ).all()
        ```
    """

    __tablename__ = "photo_processing_sessions"

    # Primary key
    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Primary key (auto-increment)",
    )

    # UUID unique identifier
    session_id = Column(
        UUID(as_uuid=True),
        unique=True,
        nullable=False,
        default=uuid.uuid4,
        index=True,
        comment="UUID unique identifier for idempotent processing",
    )

    # Foreign key to storage_locations (optional, CASCADE delete)
    storage_location_id = Column(
        Integer,
        ForeignKey("storage_locations.location_id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Foreign key to storage_locations (CASCADE delete, NULLABLE)",
    )

    # Foreign key to s3_images for original photo (CASCADE delete)
    original_image_id = Column(
        UUID(as_uuid=True),
        ForeignKey("s3_images.image_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to s3_images for original photo (CASCADE delete)",
    )

    # Foreign key to s3_images for processed photo (CASCADE delete, nullable)
    processed_image_id = Column(
        UUID(as_uuid=True),
        ForeignKey("s3_images.image_id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Foreign key to s3_images for processed photo (CASCADE delete, NULLABLE)",
    )

    # Aggregated ML results
    total_detected = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Total detections count (default 0)",
    )

    total_estimated = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Total estimations count (default 0)",
    )

    total_empty_containers = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Empty container count (default 0)",
    )

    avg_confidence = Column(
        Numeric(5, 4),
        nullable=True,
        comment="Average ML confidence score (0.0000-1.0000, NULLABLE)",
    )

    # JSONB detection counts by category
    category_counts = Column(
        JSONB,
        nullable=True,
        default=lambda: {},
        server_default="{}",
        comment="Detection counts by product category (JSONB)",
    )

    # Processing status
    status = Column(
        Enum(
            ProcessingSessionStatusEnum,
            name="processing_session_status_enum",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=ProcessingSessionStatusEnum.PENDING,
        index=True,
        comment="Processing status (pending/processing/completed/failed)",
    )

    error_message = Column(
        Text,
        nullable=True,
        comment="Error details if status = failed (NULLABLE)",
    )

    # Validation tracking
    validated = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Validation flag (default False)",
    )

    validated_by_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="FK to users who validated (SET NULL on user delete, NULLABLE)",
    )

    validation_date = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp of validation (NULLABLE)",
    )

    # JSONB manual adjustments
    manual_adjustments = Column(
        JSONB,
        nullable=True,
        default=lambda: {},
        server_default="{}",
        comment="User edits to ML results (JSONB)",
    )

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Session creation timestamp",
    )

    updated_at = Column(
        DateTime(timezone=True),
        onupdate=func.now(),
        nullable=True,
        comment="Last update timestamp",
    )

    # Relationships

    # Many-to-one: PhotoProcessingSession → StorageLocation (optional)
    storage_location: Mapped["StorageLocation | None"] = relationship(
        "StorageLocation",
        back_populates="photo_processing_sessions",
        foreign_keys=[storage_location_id],
        doc="Storage location where photo was taken (optional)",
    )

    # Many-to-one: PhotoProcessingSession → S3Image (original)
    original_image: Mapped["S3Image"] = relationship(
        "S3Image",
        foreign_keys=[original_image_id],
        doc="Original input photo",
    )

    # Many-to-one: PhotoProcessingSession → S3Image (processed)
    processed_image: Mapped["S3Image | None"] = relationship(
        "S3Image",
        foreign_keys=[processed_image_id],
        doc="Processed output photo (optional)",
    )

    # Many-to-one: PhotoProcessingSession → User (validator)
    validated_by_user: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[validated_by_user_id],
        doc="User who validated session (optional)",
    )

    # One-to-many: PhotoProcessingSession → Detection
    detections: Mapped[list["Detection"]] = relationship(
        "Detection",
        back_populates="session",
        foreign_keys="Detection.session_id",
        cascade="all, delete-orphan",
        doc="List of detections from this session",
    )

    # One-to-many: PhotoProcessingSession → Estimation
    estimations: Mapped[list["Estimation"]] = relationship(
        "Estimation",
        back_populates="session",
        foreign_keys="Estimation.session_id",
        cascade="all, delete-orphan",
        doc="List of estimations from this session",
    )

    # One-to-many: PhotoProcessingSession → StockMovement (COMMENT OUT - not ready)
    # NOTE: Uncomment after StockMovement model is complete
    stock_movements: Mapped[list["StockMovement"]] = relationship(
        "StockMovement",
        back_populates="processing_session",
        foreign_keys="StockMovement.processing_session_id",
        doc="List of stock movements generated from this session",
    )

    # One-to-many: PhotoProcessingSession → StorageLocation (latest photo reference)
    storage_locations_latest: Mapped[list["StorageLocation"]] = relationship(
        "StorageLocation",
        back_populates="latest_photo_session",
        foreign_keys="StorageLocation.photo_session_id",
        doc="Storage locations using this as latest photo",
    )

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "avg_confidence IS NULL OR (avg_confidence >= 0.0 AND avg_confidence <= 1.0)",
            name="ck_photo_session_confidence_range",
        ),
        CheckConstraint(
            "total_detected >= 0",
            name="ck_photo_session_detected_positive",
        ),
        CheckConstraint(
            "total_estimated >= 0",
            name="ck_photo_session_estimated_positive",
        ),
        CheckConstraint(
            "total_empty_containers >= 0",
            name="ck_photo_session_empty_positive",
        ),
        {
            "comment": "Photo Processing Sessions - ML photo processing pipeline tracking. NO seed data."
        },
    )

    @validates("avg_confidence")
    def validate_avg_confidence(self, key: str, value: float | None) -> float | None:
        """Validate avg_confidence field.

        Rules:
            - Must be between 0.0 and 1.0 (inclusive) if not null

        Args:
            key: Field name ("avg_confidence")
            value: Confidence value to validate

        Returns:
            Validated confidence value

        Raises:
            ValueError: If confidence is invalid

        Examples:
            >>> session.avg_confidence = 0.92
            >>> session.avg_confidence
            0.92

            >>> session.avg_confidence = 1.5  # Too high
            ValueError: avg_confidence must be between 0.0 and 1.0 (got: 1.5)

            >>> session.avg_confidence = None  # Allowed
            >>> session.avg_confidence
            None
        """
        if value is not None and not (0.0 <= value <= 1.0):
            raise ValueError(f"avg_confidence must be between 0.0 and 1.0 (got: {value})")

        return value

    def __init__(self, **kwargs: Any) -> None:
        """Initialize PhotoProcessingSession with default JSONB fields."""
        # Ensure category_counts is always a dict
        if "category_counts" not in kwargs or kwargs.get("category_counts") is None:
            kwargs["category_counts"] = {}

        # Ensure manual_adjustments is always a dict
        if "manual_adjustments" not in kwargs or kwargs.get("manual_adjustments") is None:
            kwargs["manual_adjustments"] = {}

        super().__init__(**kwargs)

    @validates("category_counts", "manual_adjustments")
    def validate_jsonb_fields(self, key: str, value: dict[str, Any] | None) -> dict[str, Any]:
        """Validate JSONB fields are always dicts.

        Args:
            key: Field name (category_counts or manual_adjustments)
            value: JSONB value to validate

        Returns:
            Validated JSONB dict (empty dict if None)

        Examples:
            >>> session.category_counts = None
            >>> session.category_counts
            {}

            >>> session.manual_adjustments = {"adjustment": "value"}
            >>> session.manual_adjustments
            {"adjustment": "value"}
        """
        if value is None:
            return {}
        return value

    def __repr__(self) -> str:
        """String representation for debugging.

        Returns:
            String with id, session_id, and status

        Example:
            <PhotoProcessingSession(id=1, session_id=UUID('...'), status='completed')>
        """
        status_value = (
            self.status.value
            if isinstance(self.status, ProcessingSessionStatusEnum)
            else self.status
        )
        return (
            f"<PhotoProcessingSession("
            f"id={self.id}, "
            f"session_id={self.session_id}, "
            f"status='{status_value}'"
            f")>"
        )
