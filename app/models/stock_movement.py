"""StockMovement model - Stock transaction audit trail with UUID tracking.

This module defines the StockMovement SQLAlchemy model for tracking all stock
transactions (plantings, deaths, transplants, sales, photos, adjustments, manual init).
Each movement is a permanent audit record with UUID for idempotent processing.

Architecture:
    Layer: Database / Models (Infrastructure Layer)
    Dependencies: SQLAlchemy 2.0, PostgreSQL 18
    Pattern: Immutable audit trail (NO updates, INSERT only)

Design Decisions:
    - UUID movement_id: Unique identifier for idempotent processing (indexed)
    - INT PK + UUID UK: id (PK) + movement_id (UK) pattern
    - Movement type enum: plantar|sembrar|transplante|muerte|ventas|foto|ajuste|manual_init
    - Source type enum: manual|ia (user vs ML-generated)
    - Signed quantity: Positive for inbound, negative for outbound (CHECK != 0)
    - is_inbound flag: True for additions, False for subtractions
    - Optional bin references: source_bin_id + destination_bin_id (nullable)
    - COGS tracking: unit_price + total_price (for sales calculation)
    - Reason tracking: reason_description text field
    - Photo session link: processing_session_id FK (nullable)
    - User tracking: user_id FK (NOT NULL, identifies who made the movement)
    - Timestamps: created_at only (immutable record)

See:
    - Database ERD: ../../database/database.mmd (lines 178-194)
    - Database docs: ../../engineering_plan/database/README.md

Example:
    ```python
    from uuid import uuid4
    from decimal import Decimal

    # Manual stock initialization
    movement = StockMovement(
        movement_id=uuid4(),
        batch_id=1,
        movement_type="manual_init",
        quantity=100,
        user_id=1,
        source_type="manual",
        is_inbound=True,
        reason_description="Initial stock count"
    )

    # Photo-based detection
    photo_movement = StockMovement(
        movement_id=uuid4(),
        batch_id=1,
        movement_type="foto",
        quantity=95,
        user_id=1,
        processing_session_id=session.id,
        source_type="ia",
        is_inbound=True,
        reason_description="ML photo detection"
    )

    # Sale transaction
    sale = StockMovement(
        movement_id=uuid4(),
        batch_id=1,
        movement_type="ventas",
        destination_bin_id=shipping_bin.id,
        quantity=-10,
        user_id=1,
        unit_price=Decimal("5.50"),
        total_price=Decimal("55.00"),
        source_type="manual",
        is_inbound=False,
        reason_description="Customer order #12345"
    )
    ```
"""

import enum
import uuid
from typing import TYPE_CHECKING

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
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, relationship, validates
from sqlalchemy.sql import func

from app.db.base import Base

# Forward declarations for type hints (avoids circular imports)
if TYPE_CHECKING:
    from app.models.detection import Detection
    from app.models.estimation import Estimation
    from app.models.photo_processing_session import PhotoProcessingSession
    from app.models.stock_batch import StockBatch
    from app.models.storage_bin import StorageBin
    from app.models.user import User


class MovementTypeEnum(str, enum.Enum):
    """Stock movement type enum.

    Movement types:
        - PLANTAR: Planting operation (outbound from seedling area)
        - SEMBRAR: Seeding operation (inbound to seedling area)
        - TRANSPLANTE: Transplant between bins/locations
        - MUERTE: Plant death (outbound/loss)
        - VENTAS: Sales (outbound to customer)
        - FOTO: Photo-based ML detection (inbound/correction)
        - AJUSTE: Manual adjustment/correction
        - MANUAL_INIT: Manual stock initialization (baseline)

    Note: This is a Python enum for type hints. The actual database ENUM
    is created in the migration file.
    """

    PLANTAR = "plantar"
    SEMBRAR = "sembrar"
    TRANSPLANTE = "transplante"
    MUERTE = "muerte"
    VENTAS = "ventas"
    FOTO = "foto"
    AJUSTE = "ajuste"
    MANUAL_INIT = "manual_init"


class SourceTypeEnum(str, enum.Enum):
    """Stock movement source type enum.

    Source types:
        - MANUAL: User-initiated movement (web/mobile UI)
        - IA: ML-generated movement (photo processing pipeline)

    Note: This is a Python enum for type hints. The actual database ENUM
    is created in the migration file.
    """

    MANUAL = "manual"
    IA = "ia"


class StockMovement(Base):
    """StockMovement model representing stock transaction audit trail.

    Immutable audit record for all stock transactions. Each movement tracks
    quantity changes, bin transfers, pricing (COGS), and origin (manual vs ML).
    UUID movement_id enables idempotent processing for ML pipeline.

    Key Features:
        - UUID movement_id: Unique identifier for idempotent processing
        - INT PK + UUID UK: id (PK) + movement_id (UK) pattern
        - Movement type enum: 8 types (plantar, sembrar, transplante, muerte, ventas, foto, ajuste, manual_init)
        - Source type enum: manual vs ia (user vs ML)
        - Signed quantity: CHECK != 0 (no zero movements)
        - is_inbound flag: True for additions, False for subtractions
        - Optional bins: source_bin_id + destination_bin_id (nullable)
        - COGS tracking: unit_price + total_price
        - Photo session link: processing_session_id FK (nullable)
        - User tracking: user_id FK (NOT NULL)
        - Immutable: created_at only (NO updated_at)

    Attributes:
        id: Primary key (auto-increment)
        movement_id: UUID unique identifier (indexed, NOT NULL)
        batch_id: FK to stock_batches (CASCADE, NOT NULL)
        movement_type: Movement type enum (NOT NULL)
        source_bin_id: FK to storage_bins for source (CASCADE, NULLABLE)
        destination_bin_id: FK to storage_bins for destination (CASCADE, NULLABLE)
        quantity: Signed quantity (CHECK != 0, NOT NULL)
        user_id: FK to users who made movement (CASCADE, NOT NULL)
        unit_price: Unit price for COGS (NULLABLE)
        total_price: Total price for COGS (NULLABLE)
        reason_description: Text reason for movement (NULLABLE)
        processing_session_id: FK to photo_processing_sessions (CASCADE, NULLABLE)
        source_type: Source type enum (manual|ia, NOT NULL)
        is_inbound: Inbound flag (True = addition, False = subtraction, NOT NULL)
        created_at: Movement timestamp (auto, immutable)

    Relationships:
        batch: StockBatch instance (many-to-one)
        source_bin: StorageBin instance for source (many-to-one, optional)
        destination_bin: StorageBin instance for destination (many-to-one, optional)
        user: User who made movement (many-to-one)
        processing_session: PhotoProcessingSession for ML movements (many-to-one, optional)
        detections: List of Detection instances (one-to-many)
        estimations: List of Estimation instances (one-to-many)

    Indexes:
        - B-tree index on movement_id (unique constraint)
        - B-tree index on batch_id (foreign key)
        - B-tree index on user_id (foreign key)
        - B-tree index on processing_session_id (foreign key)
        - B-tree index on created_at DESC (time-series queries)
        - B-tree index on movement_type (filter by type)

    Constraints:
        - CHECK quantity != 0 (no zero movements)

    Example:
        ```python
        from uuid import uuid4
        from decimal import Decimal

        # Manual initialization
        movement = StockMovement(
            movement_id=uuid4(),
            batch_id=1,
            movement_type="manual_init",
            quantity=100,
            user_id=1,
            source_type="manual",
            is_inbound=True,
            reason_description="Initial count"
        )

        # Photo detection
        photo_mv = StockMovement(
            movement_id=uuid4(),
            batch_id=1,
            movement_type="foto",
            quantity=95,
            user_id=1,
            processing_session_id=1,
            source_type="ia",
            is_inbound=True
        )

        # Sale
        sale = StockMovement(
            movement_id=uuid4(),
            batch_id=1,
            movement_type="ventas",
            quantity=-10,
            user_id=1,
            unit_price=Decimal("5.50"),
            total_price=Decimal("55.00"),
            source_type="manual",
            is_inbound=False
        )
        ```
    """

    __tablename__ = "stock_movements"

    # Primary key
    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Primary key (auto-increment)",
    )

    # UUID unique identifier
    movement_id = Column(
        UUID(as_uuid=True),
        unique=True,
        nullable=False,
        default=uuid.uuid4,
        index=True,
        comment="UUID unique identifier for idempotent processing",
    )

    # Foreign key to stock batch (CASCADE delete)
    batch_id = Column(
        Integer,
        ForeignKey("stock_batches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to stock_batches (CASCADE delete)",
    )

    # Movement type enum
    movement_type = Column(
        Enum(
            MovementTypeEnum,
            name="movement_type_enum",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        index=True,
        comment="Movement type (plantar|sembrar|transplante|muerte|ventas|foto|ajuste|manual_init)",
    )

    # Optional bin references (CASCADE delete)
    source_bin_id = Column(
        Integer,
        ForeignKey("storage_bins.storage_bin_id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Foreign key to storage_bins for source (CASCADE delete, NULLABLE)",
    )

    destination_bin_id = Column(
        Integer,
        ForeignKey("storage_bins.storage_bin_id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Foreign key to storage_bins for destination (CASCADE delete, NULLABLE)",
    )

    # Signed quantity (CHECK != 0)
    quantity = Column(
        Integer,
        nullable=False,
        comment="Signed quantity (CHECK != 0, positive = inbound, negative = outbound)",
    )

    # User who made movement (CASCADE delete)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to users who made movement (CASCADE delete)",
    )

    # COGS tracking
    unit_price = Column(
        Numeric(10, 2),
        nullable=True,
        comment="Unit price for COGS (NULLABLE)",
    )

    total_price = Column(
        Numeric(10, 2),
        nullable=True,
        comment="Total price for COGS (NULLABLE)",
    )

    # Reason description
    reason_description = Column(
        Text,
        nullable=True,
        comment="Text reason for movement (NULLABLE)",
    )

    # Photo session link (CASCADE delete, nullable)
    processing_session_id = Column(
        Integer,
        ForeignKey("photo_processing_sessions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Foreign key to photo_processing_sessions (CASCADE delete, NULLABLE)",
    )

    # Source type enum
    source_type = Column(
        Enum(
            SourceTypeEnum,
            name="source_type_enum",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        comment="Source type (manual|ia, user vs ML)",
    )

    # Inbound/outbound flag
    is_inbound = Column(
        Boolean,
        nullable=False,
        comment="Inbound flag (True = addition, False = subtraction)",
    )

    # Timestamp (immutable record)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Movement timestamp (immutable)",
    )

    # Relationships

    # Many-to-one: StockMovement → StockBatch
    batch: Mapped["StockBatch"] = relationship(
        "StockBatch",
        back_populates="stock_movements",
        doc="Stock batch for this movement",
    )

    # Many-to-one: StockMovement → StorageBin (source)
    source_bin: Mapped["StorageBin | None"] = relationship(
        "StorageBin",
        foreign_keys=[source_bin_id],
        back_populates="stock_movements_source",
        doc="Source storage bin (optional)",
    )

    # Many-to-one: StockMovement → StorageBin (destination)
    destination_bin: Mapped["StorageBin | None"] = relationship(
        "StorageBin",
        foreign_keys=[destination_bin_id],
        back_populates="stock_movements_destination",
        doc="Destination storage bin (optional)",
    )

    # Many-to-one: StockMovement → User
    user: Mapped["User"] = relationship(
        "User",
        back_populates="stock_movements",
        doc="User who made movement",
    )

    # Many-to-one: StockMovement → PhotoProcessingSession (optional)
    processing_session: Mapped["PhotoProcessingSession | None"] = relationship(
        "PhotoProcessingSession",
        back_populates="stock_movements",
        doc="Photo processing session for ML movements (optional)",
    )

    # One-to-many: StockMovement → Detection
    detections: Mapped[list["Detection"]] = relationship(
        "Detection",
        back_populates="stock_movement",
        foreign_keys="Detection.stock_movement_id",
        cascade="all, delete-orphan",
        doc="List of detections from this movement",
    )

    # One-to-many: StockMovement → Estimation
    estimations: Mapped[list["Estimation"]] = relationship(
        "Estimation",
        back_populates="stock_movement",
        foreign_keys="Estimation.stock_movement_id",
        cascade="all, delete-orphan",
        doc="List of estimations from this movement",
    )

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "quantity != 0",
            name="ck_stock_movement_quantity_nonzero",
        ),
        {
            "comment": "Stock Movements - Immutable audit trail for all stock transactions. NO seed data."
        },
    )

    @validates("quantity")
    def validate_quantity(self, key: str, value: int | None) -> int | None:
        """Validate quantity field.

        Rules:
            - Must not be zero (CHECK != 0)
            - Cannot be None

        Args:
            key: Field name ("quantity")
            value: Quantity value to validate

        Returns:
            Validated quantity

        Raises:
            ValueError: If quantity is invalid

        Examples:
            >>> movement.quantity = 100  # Valid (inbound)
            >>> movement.quantity = -10  # Valid (outbound)
            >>> movement.quantity = 0    # Invalid
            ValueError: Quantity must not be zero

            >>> movement.quantity = None
            ValueError: Quantity cannot be None
        """
        if value is None:
            raise ValueError("Quantity cannot be None")

        if value == 0:
            raise ValueError("Quantity must not be zero")

        return value

    def __repr__(self) -> str:
        """String representation for debugging.

        Returns:
            String with id, movement_id, movement_type, and quantity

        Example:
            <StockMovement(id=1, movement_id=UUID('...'), movement_type='manual_init', quantity=100)>
        """
        movement_type_value = (
            self.movement_type.value
            if isinstance(self.movement_type, MovementTypeEnum)
            else self.movement_type
        )
        return (
            f"<StockMovement("
            f"id={self.id}, "
            f"movement_id={self.movement_id}, "
            f"movement_type='{movement_type_value}', "
            f"quantity={self.quantity}"
            f")>"
        )
