"""ProductState model - Reference/Catalog table defining product lifecycle states.

This module defines the ProductState SQLAlchemy model for product lifecycle state catalog.
Product states define the lifecycle stages of plants (seed, seedling, adult, flowering, etc.)
with business logic for sellable states.

Architecture:
    Layer: Database / Models (Infrastructure Layer)
    Dependencies: SQLAlchemy 2.0, PostgreSQL enums
    Pattern: Reference/Catalog table with seed data

Design Decisions:
    - 11 lifecycle states: SEED → GERMINATING → SEEDLING → JUVENILE → ADULT →
      FLOWERING → FRUITING → DORMANT → PROPAGATING → DYING → DEAD
    - is_sellable flag: Only ADULT, FLOWERING, FRUITING, DORMANT are sellable
    - sort_order field: For UI dropdowns (lifecycle progression order)
    - Code validation: uppercase, alphanumeric + underscores, 3-50 chars
    - Seed data: All 11 states preloaded in migration

See:
    - Database ERD: ../../database/database.mmd (lines 97-104)
    - Database docs: ../../engineering_plan/database/README.md
    - Task specification: ../../backlog/03_kanban/02_in-progress/DB018-product-states-enum.md

Example:
    ```python
    # Query sellable states
    sellable_states = session.query(ProductState).filter_by(is_sellable=True).all()
    # Returns: ADULT, FLOWERING, FRUITING, DORMANT

    # Create stock batch with adult state
    batch = StockBatch(
        product_state=session.query(ProductState).filter_by(code='ADULT').first(),
        quantity=100
    )
    ```
"""

import re
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, relationship, validates
from sqlalchemy.sql import func

from app.db.base import Base

# Forward declarations for type hints (avoids circular imports)
if TYPE_CHECKING:
    # NOTE: Uncomment after respective models are complete
    from app.models.product_sample_image import ProductSampleImage
    from app.models.stock_batch import StockBatch
    from app.models.storage_location_config import StorageLocationConfig


class ProductState(Base):
    """ProductState model representing product lifecycle state catalog.

    Reference/catalog table defining plant lifecycle states with is_sellable
    business logic flag. Used for inventory filtering, sales logic, and ML validation.

    Key Features:
        - 11 lifecycle states: SEED → DEAD (complete lifecycle)
        - is_sellable flag: Only 4 states are sellable (ADULT, FLOWERING, FRUITING, DORMANT)
        - sort_order field: UI dropdown order (lifecycle progression)
        - Code validation: uppercase, alphanumeric + underscores, 3-50 chars
        - Seed data: 11 states preloaded in migration

    Attributes:
        product_state_id: Primary key (auto-increment)
        code: Unique state code (uppercase, alphanumeric + underscores, 3-50 chars)
        name: Human-readable state name
        description: Optional detailed description
        is_sellable: Business logic flag (default FALSE) - can this state be sold?
        sort_order: UI dropdown order (default 99)
        created_at: Record creation timestamp (auto)
        updated_at: Last update timestamp (auto)

    Relationships:
        stock_batches: List of StockBatch instances in this state (one-to-many, COMMENTED OUT)
        classifications: List of Classification instances for this state (one-to-many, COMMENTED OUT)
        product_sample_images: List of ProductSampleImage instances (one-to-many, COMMENTED OUT)
        storage_location_configs: List of StorageLocationConfig instances (one-to-many, COMMENTED OUT)

    Indexes:
        - B-tree index on code (unique lookups)
        - B-tree index on is_sellable (filtering)
        - B-tree index on sort_order (ordering)

    CHECK Constraint:
        - Code length between 3 and 50 characters

    Example:
        ```python
        # Create state (usually done via seed migration)
        adult_state = ProductState(
            code="ADULT",
            name="Adult Plant",
            description="Mature plant, ready for sale",
            is_sellable=True,
            sort_order=50
        )

        # Query sellable states
        sellable = session.query(ProductState).filter_by(is_sellable=True).all()
        # Returns: [ADULT, FLOWERING, FRUITING, DORMANT]
        ```
    """

    __tablename__ = "product_states"

    # Primary key
    product_state_id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Primary key (auto-increment)",
    )

    # Identification (unique code required)
    code = Column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique state code (uppercase, alphanumeric + underscores, 3-50 chars)",
    )

    name = Column(
        String(200),
        nullable=False,
        comment="Human-readable state name",
    )

    description = Column(
        Text,
        nullable=True,
        comment="Optional detailed description",
    )

    # Business logic flags
    is_sellable = Column(
        Boolean,
        nullable=False,
        server_default="false",
        index=True,
        comment="Business logic flag - can this state be sold? (default FALSE)",
    )

    sort_order = Column(
        Integer,
        nullable=False,
        server_default="99",
        index=True,
        comment="UI dropdown order (lifecycle progression)",
    )

    # Timestamps (automatic tracking)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Record creation timestamp",
    )

    updated_at = Column(
        DateTime(timezone=True),
        onupdate=func.now(),
        nullable=True,
        comment="Last update timestamp",
    )

    # Relationships (COMMENTED OUT until models are complete)

    # One-to-many: ProductState → StockBatch
    # NOTE: Uncomment after StockBatch model is complete
    stock_batches: Mapped[list["StockBatch"]] = relationship(
        "StockBatch",
        back_populates="product_state",
        foreign_keys="StockBatch.product_state_id",
        doc="List of stock batches in this state",
    )

    # One-to-many: ProductState → Classification
    # NOTE: Uncomment after Classification model is complete
    # classifications: Mapped[list["Classification"]] = relationship(
    #     "Classification",
    #     back_populates="product_state",
    #     foreign_keys="Classification.product_state_id",
    #     doc="List of classifications for this state"
    # )

    # One-to-many: ProductState → ProductSampleImage
    # NOTE: Uncomment after ProductSampleImage model is complete
    product_sample_images: Mapped[list["ProductSampleImage"]] = relationship(
        "ProductSampleImage",
        back_populates="product_state",
        foreign_keys="ProductSampleImage.product_state_id",
        doc="List of sample images for this state",
    )

    # One-to-many: ProductState → StorageLocationConfig
    # NOTE: Uncomment after StorageLocationConfig model is complete
    storage_location_configs: Mapped[list["StorageLocationConfig"]] = relationship(
        "StorageLocationConfig",
        back_populates="expected_product_state",
        foreign_keys="StorageLocationConfig.expected_product_state_id",
        doc="List of location configs expecting this state",
    )

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "LENGTH(code) >= 3 AND LENGTH(code) <= 50",
            name="ck_product_state_code_length",
        ),
        {"comment": "Product States - Reference/catalog table defining product lifecycle states"},
    )

    @validates("code")
    def validate_code(self, key: str, value: str) -> str:
        """Validate product state code format.

        Rules:
            1. Required (not empty)
            2. Must be uppercase
            3. Alphanumeric + underscores only (NO hyphens)
            4. Length between 3 and 50 characters

        Args:
            key: Column name (always 'code')
            value: Product state code to validate

        Returns:
            Validated product state code (uppercase)

        Raises:
            ValueError: If validation fails with specific error message

        Example:
            ```python
            state.code = "ADULT"           # Valid
            state.code = "adult"           # Auto-uppercases to "ADULT"
            state.code = "ADULT-PLANT"     # Raises ValueError (hyphens not allowed)
            state.code = "SE"              # Raises ValueError (too short)
            state.code = ""                # Raises ValueError (empty)
            ```
        """
        if not value or not value.strip():
            raise ValueError("Product state code cannot be empty")

        code = value.strip().upper()

        # Check alphanumeric + underscores only (NO hyphens)
        if not re.match(r"^[A-Z0-9_]+$", code):
            raise ValueError(
                f"Product state code must be alphanumeric + underscores only "
                f"(NO hyphens, got: {code})"
            )

        if len(code) < 3 or len(code) > 50:
            raise ValueError(f"Product state code must be 3-50 characters (got {len(code)} chars)")

        return code

    @validates("is_sellable")
    def validate_is_sellable(self, key: str, value: object) -> object:
        """Validate is_sellable is boolean.

        Rules:
            1. Must be boolean (True or False)
            2. Defaults to False if not provided

        Args:
            key: Column name (always 'is_sellable')
            value: Boolean value to validate

        Returns:
            Validated boolean

        Raises:
            ValueError: If not a boolean
        """
        if value is None:
            return False
        if not isinstance(value, bool):
            raise ValueError(f"is_sellable must be boolean (got: {type(value).__name__})")
        return value

    @validates("sort_order")
    def validate_sort_order(self, key: str, value: object) -> object:
        """Validate sort_order is non-negative integer.

        Rules:
            1. Must be integer ≥0
            2. Defaults to 99 if not provided

        Args:
            key: Column name (always 'sort_order')
            value: Sort order to validate

        Returns:
            Validated sort_order

        Raises:
            ValueError: If not valid integer
        """
        if value is None:
            return 99
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError(f"sort_order must be integer (got: {type(value).__name__})")
        if value < 0:
            raise ValueError(f"sort_order must be ≥0 (got: {value})")
        return value

    def __repr__(self) -> str:
        """String representation for debugging.

        Returns:
            String with product_state_id, code, name, is_sellable, and sort_order

        Example:
            <ProductState(product_state_id=1, code='ADULT', name='Adult Plant',
             is_sellable=True, sort_order=50)>
        """
        return (
            f"<ProductState("
            f"product_state_id={self.product_state_id}, "
            f"code='{self.code}', "
            f"name='{self.name}', "
            f"is_sellable={self.is_sellable}, "
            f"sort_order={self.sort_order}"
            f")>"
        )
