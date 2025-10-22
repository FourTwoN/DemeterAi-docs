"""StockBatch model - Physical stock tracking at storage bin level.

This module defines the StockBatch SQLAlchemy model for tracking physical inventory
batches at the storage bin level. Each batch represents a group of plants of the
same product, state, size, and packaging in a single storage bin.

Architecture:
    Layer: Database / Models (Infrastructure Layer)
    Dependencies: SQLAlchemy 2.0, PostgreSQL 18
    Pattern: Stock inventory tracking (NO seed data, user/ML-generated)

Design Decisions:
    - Batch code: Unique, alphanumeric+hyphen, 6-50 chars, uppercase
    - Current location tracking: current_storage_bin_id FK (CASCADE delete)
    - Product tracking: product_id + product_state_id + product_size_id (nullable)
    - Packaging tracking: has_packaging flag + packaging_catalog_id (nullable)
    - Quantity tracking: quantity_initial + quantity_current + quantity_empty_containers
    - Quality score: Numeric(3,2) range 0.00-5.00 (nullable)
    - Date tracking: planting_date, germination_date, transplant_date, expected_ready_date
    - JSONB custom_attributes: Flexible metadata
    - Timestamps: created_at + updated_at (auto-managed)

See:
    - Database ERD: ../../database/database.mmd (lines 156-177)
    - Database docs: ../../engineering_plan/database/README.md

Example:
    ```python
    from datetime import date

    # Create stock batch
    batch = StockBatch(
        batch_code="BATCH-ECHEV-001",
        current_storage_bin_id=1,
        product_id=42,
        product_state_id=3,  # Adult
        product_size_id=2,   # Medium
        has_packaging=True,
        packaging_catalog_id=7,
        quantity_initial=100,
        quantity_current=95,
        quantity_empty_containers=2,
        quality_score=4.5,
        planting_date=date(2025, 1, 15),
        custom_attributes={"batch_notes": "Premium quality"}
    )

    # Query by product
    batches = session.query(StockBatch).filter_by(product_id=42).all()
    ```
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, relationship, validates
from sqlalchemy.sql import func

from app.db.base import Base

# Forward declarations for type hints (avoids circular imports)
if TYPE_CHECKING:
    from app.models.packaging_catalog import PackagingCatalog
    from app.models.product import Product
    from app.models.product_size import ProductSize
    from app.models.product_state import ProductState
    from app.models.stock_movement import StockMovement
    from app.models.storage_bin import StorageBin


class StockBatch(Base):
    """StockBatch model representing physical inventory batches.

    Tracks groups of plants of the same product, state, size, and packaging
    within a single storage bin. This is the core inventory tracking model
    linking products to physical locations.

    Key Features:
        - Unique batch_code: Alphanumeric+hyphen, 6-50 chars, uppercase
        - Current location: current_storage_bin_id FK (CASCADE delete)
        - Product identity: product_id + product_state_id + product_size_id
        - Packaging: has_packaging flag + optional packaging_catalog_id
        - Quantity tracking: initial, current, empty containers
        - Quality score: 0.00-5.00 range (nullable)
        - Growth dates: planting, germination, transplant, expected ready
        - JSONB metadata: Flexible custom_attributes

    Attributes:
        id: Primary key (auto-increment)
        batch_code: Unique batch identifier (6-50 chars, alphanumeric+hyphen, uppercase)
        current_storage_bin_id: FK to storage_bins for current location (CASCADE, NOT NULL)
        product_id: FK to products (CASCADE, NOT NULL)
        product_state_id: FK to product_states (CASCADE, NOT NULL)
        product_size_id: FK to product_sizes (CASCADE, NULLABLE)
        has_packaging: Packaging presence flag (default False)
        packaging_catalog_id: FK to packaging_catalog (CASCADE, NULLABLE)
        quantity_initial: Initial quantity when batch created (CHECK >= 0)
        quantity_current: Current quantity in batch (CHECK >= 0)
        quantity_empty_containers: Empty container count (default 0, CHECK >= 0)
        quality_score: Quality rating 0.00-5.00 (NULLABLE)
        planting_date: When planted (NULLABLE)
        germination_date: When germinated (NULLABLE)
        transplant_date: When transplanted (NULLABLE)
        expected_ready_date: Expected ready for sale date (NULLABLE)
        notes: Optional text notes (NULLABLE)
        custom_attributes: JSONB flexible metadata (default {})
        created_at: Batch creation timestamp (auto)
        updated_at: Last update timestamp (auto)

    Relationships:
        current_storage_bin: StorageBin instance for current location (many-to-one)
        product: Product instance (many-to-one)
        product_state: ProductState instance (many-to-one)
        product_size: ProductSize instance (many-to-one, optional)
        packaging_catalog: PackagingCatalog instance (many-to-one, optional)
        stock_movements: List of StockMovement instances (one-to-many)

    Indexes:
        - B-tree index on batch_code (unique constraint)
        - B-tree index on current_storage_bin_id (foreign key)
        - B-tree index on product_id (foreign key)
        - B-tree index on product_state_id (foreign key)
        - B-tree index on created_at DESC (time-series queries)
        - GIN index on custom_attributes (JSONB queries)

    Constraints:
        - CHECK batch_code length between 6-50 characters
        - CHECK quantity_initial >= 0
        - CHECK quantity_current >= 0
        - CHECK quantity_empty_containers >= 0
        - CHECK quality_score between 0.00 and 5.00 (if not null)
        - CHECK has_packaging logic: if TRUE then packaging_catalog_id NOT NULL

    Example:
        ```python
        from datetime import date

        # Create batch
        batch = StockBatch(
            batch_code="BATCH-ECHEV-001",
            current_storage_bin_id=1,
            product_id=42,
            product_state_id=3,
            product_size_id=2,
            has_packaging=True,
            packaging_catalog_id=7,
            quantity_initial=100,
            quantity_current=95,
            quality_score=4.5,
            planting_date=date(2025, 1, 15)
        )

        # Query by bin
        batches = session.query(StockBatch).filter_by(
            current_storage_bin_id=1
        ).all()
        ```
    """

    __tablename__ = "stock_batches"

    # Primary key
    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Primary key (auto-increment)",
    )

    # Unique batch code
    batch_code = Column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique batch identifier (6-50 chars, alphanumeric+hyphen, uppercase)",
    )

    # Foreign key to current storage bin (CASCADE delete)
    current_storage_bin_id = Column(
        Integer,
        ForeignKey("storage_bins.bin_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to storage_bins for current location (CASCADE delete)",
    )

    # Foreign key to product (CASCADE delete)
    product_id = Column(
        Integer,
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to products (CASCADE delete)",
    )

    # Foreign key to product state (CASCADE delete)
    product_state_id = Column(
        Integer,
        ForeignKey("product_states.product_state_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to product_states (CASCADE delete)",
    )

    # Foreign key to product size (CASCADE delete, nullable)
    product_size_id = Column(
        Integer,
        ForeignKey("product_sizes.product_size_id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Foreign key to product_sizes (CASCADE delete, NULLABLE)",
    )

    # Packaging tracking
    has_packaging = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Packaging presence flag (default False)",
    )

    packaging_catalog_id = Column(
        Integer,
        ForeignKey("packaging_catalog.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Foreign key to packaging_catalog (CASCADE delete, NULLABLE)",
    )

    # Quantity tracking
    quantity_initial = Column(
        Integer,
        nullable=False,
        comment="Initial quantity when batch created (CHECK >= 0)",
    )

    quantity_current = Column(
        Integer,
        nullable=False,
        comment="Current quantity in batch (CHECK >= 0)",
    )

    quantity_empty_containers = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Empty container count (default 0, CHECK >= 0)",
    )

    # Quality score (0.00-5.00 range)
    quality_score = Column(
        Numeric(3, 2),
        nullable=True,
        comment="Quality rating 0.00-5.00 (NULLABLE)",
    )

    # Growth dates
    planting_date = Column(
        Date,
        nullable=True,
        comment="When planted (NULLABLE)",
    )

    germination_date = Column(
        Date,
        nullable=True,
        comment="When germinated (NULLABLE)",
    )

    transplant_date = Column(
        Date,
        nullable=True,
        comment="When transplanted (NULLABLE)",
    )

    expected_ready_date = Column(
        Date,
        nullable=True,
        comment="Expected ready for sale date (NULLABLE)",
    )

    # Notes
    notes = Column(
        Text,
        nullable=True,
        comment="Optional text notes (NULLABLE)",
    )

    # JSONB custom attributes
    custom_attributes = Column(
        JSONB,
        nullable=True,
        default=lambda: {},
        server_default="{}",
        comment="Flexible metadata (JSONB)",
    )

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=datetime.utcnow,
        nullable=False,
        comment="Batch creation timestamp",
    )

    updated_at = Column(
        DateTime(timezone=True),
        onupdate=func.now(),
        nullable=True,
        comment="Last update timestamp",
    )

    # Relationships

    # Many-to-one: StockBatch → StorageBin
    current_storage_bin: Mapped["StorageBin"] = relationship(
        "StorageBin",
        back_populates="stock_batches",
        foreign_keys=[current_storage_bin_id],
        doc="Current storage bin location",
    )

    # Many-to-one: StockBatch → Product
    product: Mapped["Product"] = relationship(
        "Product",
        back_populates="stock_batches",
        doc="Product in this batch",
    )

    # Many-to-one: StockBatch → ProductState
    product_state: Mapped["ProductState"] = relationship(
        "ProductState",
        back_populates="stock_batches",
        doc="Product state in this batch",
    )

    # Many-to-one: StockBatch → ProductSize (optional)
    product_size: Mapped["ProductSize | None"] = relationship(
        "ProductSize",
        back_populates="stock_batches",
        doc="Product size in this batch (optional)",
    )

    # Many-to-one: StockBatch → PackagingCatalog (optional)
    packaging_catalog: Mapped["PackagingCatalog | None"] = relationship(
        "PackagingCatalog",
        back_populates="stock_batches",
        doc="Packaging used in this batch (optional)",
    )

    # One-to-many: StockBatch → StockMovement (COMMENT OUT - not ready)
    # NOTE: Uncomment after StockMovement model is complete
    stock_movements: Mapped[list["StockMovement"]] = relationship(
        "StockMovement",
        back_populates="batch",
        foreign_keys="StockMovement.batch_id",
        cascade="all, delete-orphan",
        doc="List of stock movements for this batch",
    )

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "LENGTH(batch_code) >= 6 AND LENGTH(batch_code) <= 50",
            name="ck_stock_batch_code_length",
        ),
        CheckConstraint(
            "batch_code ~ '^[A-Z0-9-]+$'",
            name="ck_stock_batch_code_format",
        ),
        CheckConstraint(
            "quantity_initial >= 0",
            name="ck_stock_batch_quantity_initial_positive",
        ),
        CheckConstraint(
            "quantity_current >= 0",
            name="ck_stock_batch_quantity_current_positive",
        ),
        CheckConstraint(
            "quantity_empty_containers >= 0",
            name="ck_stock_batch_empty_positive",
        ),
        CheckConstraint(
            "quality_score IS NULL OR (quality_score >= 0.00 AND quality_score <= 5.00)",
            name="ck_stock_batch_quality_range",
        ),
        CheckConstraint(
            "has_packaging = FALSE OR (has_packaging = TRUE AND packaging_catalog_id IS NOT NULL)",
            name="ck_stock_batch_packaging_required",
        ),
        {
            "comment": "Stock Batches - Physical inventory tracking at storage bin level. NO seed data."
        },
    )

    @validates("batch_code")
    def validate_batch_code(self, key: str, value: str | None) -> str | None:
        """Validate and normalize batch_code field.

        Rules:
            - Length: 6-50 characters
            - Characters: Alphanumeric + hyphen only
            - Auto-convert to uppercase

        Args:
            key: Field name ("batch_code")
            value: Batch code value to validate

        Returns:
            Normalized batch code (uppercase)

        Raises:
            ValueError: If batch code is invalid
        """
        if value is None:
            raise ValueError("Batch code cannot be None")

        # Auto-convert to uppercase
        value = value.upper()

        # Validate length
        if len(value) < 6 or len(value) > 50:
            raise ValueError(f"Batch code must be 6-50 characters (got: {len(value)})")

        # Validate characters (alphanumeric + hyphen only)
        if not all(c.isalnum() or c == "-" for c in value):
            raise ValueError("Batch code must contain only alphanumeric characters and hyphens")

        return value

    @validates("quality_score")
    def validate_quality_score(self, key: str, value: float | None) -> float | None:
        """Validate quality_score field.

        Rules:
            - Must be between 0.00 and 5.00 (inclusive) if not null

        Args:
            key: Field name ("quality_score")
            value: Quality score value to validate

        Returns:
            Validated quality score

        Raises:
            ValueError: If quality score is invalid
        """
        if value is not None and not (0.0 <= value <= 5.0):
            raise ValueError(f"Quality score must be between 0.00 and 5.00 (got: {value})")

        return value

    def __init__(self, **kwargs: Any) -> None:
        """Initialize StockBatch with default custom_attributes."""
        if "custom_attributes" not in kwargs or kwargs.get("custom_attributes") is None:
            kwargs["custom_attributes"] = {}
        super().__init__(**kwargs)

    @validates("custom_attributes")
    def validate_custom_attributes(self, key: str, value: dict[str, Any] | None) -> dict[str, Any]:
        """Validate custom_attributes JSONB field.

        Ensures custom_attributes is always a dict (never None).
        """
        if value is None:
            return {}
        return value

    def __repr__(self) -> str:
        """String representation for debugging.

        Returns:
            String with id, batch_code, product_id, and quantity_current

        Example:
            <StockBatch(id=1, batch_code='BATCH-ECHEV-001', product_id=42, quantity_current=95)>
        """
        return (
            f"<StockBatch("
            f"id={self.id}, "
            f"batch_code='{self.batch_code}', "
            f"product_id={self.product_id}, "
            f"quantity_current={self.quantity_current}"
            f")>"
        )
