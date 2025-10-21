"""ProductSize model - Reference/Catalog table defining product size categories.

This module defines the ProductSize SQLAlchemy model for product size catalog.
Product sizes define plant size categories (XS, S, M, L, XL, XXL, CUSTOM) with
height ranges for inventory filtering and size-based pricing.

Architecture:
    Layer: Database / Models (Infrastructure Layer)
    Dependencies: SQLAlchemy 2.0, PostgreSQL numeric types
    Pattern: Reference/Catalog table with seed data

Design Decisions:
    - 7 size categories: XS, S, M, L, XL, XXL, CUSTOM
    - Height ranges (nullable): min_height_cm, max_height_cm
    - CUSTOM size: No height range (NULL for both min/max)
    - XXL size: No max height (NULL for max)
    - sort_order field: For UI dropdowns (size progression order)
    - Code validation: uppercase, alphanumeric + underscores, 3-50 chars
    - Seed data: All 7 sizes preloaded in migration

See:
    - Database ERD: ../../database/database.mmd (lines 105-113)
    - Database docs: ../../engineering_plan/database/README.md
    - Task specification: ../../backlog/03_kanban/02_in-progress/DB019-product-sizes-enum.md

Example:
    ```python
    # Query by size
    medium_plants = session.query(Product).join(ProductSize).filter_by(code='M').all()

    # Create stock batch with size
    batch = StockBatch(
        product_size=session.query(ProductSize).filter_by(code='L').first(),
        quantity=50
    )
    ```
"""

import re
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Column, DateTime, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, relationship, validates
from sqlalchemy.sql import func

from app.db.base import Base

# Forward declarations for type hints (avoids circular imports)
if TYPE_CHECKING:
    from app.models.classification import Classification
    from app.models.product_sample_image import ProductSampleImage

    # NOTE: Uncomment after respective models are complete
    from app.models.stock_batch import StockBatch


class ProductSize(Base):
    """ProductSize model representing product size category catalog.

    Reference/catalog table defining plant size categories with height ranges.
    Used for inventory filtering, size-based pricing, and ML classification.

    Key Features:
        - 7 size categories: XS, S, M, L, XL, XXL, CUSTOM
        - Height ranges (nullable): min_height_cm, max_height_cm
        - CUSTOM size: No height range (NULL for both)
        - XXL size: No max height (open-ended)
        - sort_order field: UI dropdown order (size progression)
        - Code validation: uppercase, alphanumeric + underscores, 3-50 chars
        - Seed data: 7 sizes preloaded in migration

    Attributes:
        product_size_id: Primary key (auto-increment)
        code: Unique size code (uppercase, alphanumeric + underscores, 3-50 chars)
        name: Human-readable size name
        description: Optional detailed description
        min_height_cm: Minimum height in cm (nullable)
        max_height_cm: Maximum height in cm (nullable)
        sort_order: UI dropdown order (default 99)
        created_at: Record creation timestamp (auto)
        updated_at: Last update timestamp (auto)

    Relationships:
        stock_batches: List of StockBatch instances of this size (one-to-many, COMMENTED OUT)
        classifications: List of Classification instances for this size (one-to-many, COMMENTED OUT)
        product_sample_images: List of ProductSampleImage instances (one-to-many, COMMENTED OUT)

    Indexes:
        - B-tree index on code (unique lookups)
        - B-tree index on sort_order (ordering)

    CHECK Constraint:
        - Code length between 3 and 50 characters

    Example:
        ```python
        # Create size (usually done via seed migration)
        medium = ProductSize(
            code="M",
            name="Medium (10-20cm)",
            min_height_cm=10.0,
            max_height_cm=20.0,
            sort_order=30
        )

        # Custom size (no height range)
        custom = ProductSize(
            code="CUSTOM",
            name="Custom Size (no fixed range)",
            min_height_cm=None,
            max_height_cm=None,
            sort_order=99
        )
        ```
    """

    __tablename__ = "product_sizes"

    # Primary key
    product_size_id = Column(
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
        comment="Unique size code (uppercase, alphanumeric + underscores, 3-50 chars)",
    )

    name = Column(
        String(200),
        nullable=False,
        comment="Human-readable size name",
    )

    description = Column(
        Text,
        nullable=True,
        comment="Optional detailed description",
    )

    # Height ranges (nullable - CUSTOM has no range, XXL has no max)
    min_height_cm = Column(
        Numeric(6, 2),
        nullable=True,
        comment="Minimum height in cm (nullable)",
    )

    max_height_cm = Column(
        Numeric(6, 2),
        nullable=True,
        comment="Maximum height in cm (nullable)",
    )

    # UI ordering
    sort_order = Column(
        Integer,
        nullable=False,
        server_default="99",
        index=True,
        comment="UI dropdown order (size progression)",
    )

    # Timestamps (automatic tracking)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=datetime.utcnow,
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

    # One-to-many: ProductSize → StockBatch
    # NOTE: Uncomment after StockBatch model is complete
    stock_batches: Mapped[list["StockBatch"]] = relationship(
        "StockBatch",
        back_populates="product_size",
        foreign_keys="StockBatch.product_size_id",
        doc="List of stock batches of this size",
    )

    # One-to-many: ProductSize → Classification
    # NOTE: Uncomment after Classification model is complete
    classifications: Mapped[list["Classification"]] = relationship(
        "Classification",
        back_populates="product_size",
        foreign_keys="Classification.product_size_id",
        doc="List of classifications for this size",
    )

    # One-to-many: ProductSize → ProductSampleImage
    # NOTE: Uncomment after ProductSampleImage model is complete
    product_sample_images: Mapped[list["ProductSampleImage"]] = relationship(
        "ProductSampleImage",
        back_populates="product_size",
        foreign_keys="ProductSampleImage.product_size_id",
        doc="List of sample images for this size",
    )

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "LENGTH(code) >= 3 AND LENGTH(code) <= 50",
            name="ck_product_size_code_length",
        ),
        {"comment": "Product Sizes - Reference/catalog table defining product size categories"},
    )

    @validates("code")
    def validate_code(self, key: str, value: str) -> str:
        """Validate product size code format.

        Rules:
            1. Required (not empty)
            2. Must be uppercase
            3. Alphanumeric + underscores only (NO hyphens)
            4. Length between 3 and 50 characters

        Args:
            key: Column name (always 'code')
            value: Product size code to validate

        Returns:
            Validated product size code (uppercase)

        Raises:
            ValueError: If validation fails with specific error message

        Example:
            ```python
            size.code = "XL"               # Valid
            size.code = "xl"               # Auto-uppercases to "XL"
            size.code = "EXTRA-LARGE"      # Raises ValueError (hyphens not allowed)
            size.code = "X"                # Raises ValueError (too short)
            size.code = ""                 # Raises ValueError (empty)
            ```
        """
        if not value or not value.strip():
            raise ValueError("Product size code cannot be empty")

        code = value.strip().upper()

        # Check alphanumeric + underscores only (NO hyphens)
        if not re.match(r"^[A-Z0-9_]+$", code):
            raise ValueError(
                f"Product size code must be alphanumeric + underscores only "
                f"(NO hyphens, got: {code})"
            )

        if len(code) < 3 or len(code) > 50:
            raise ValueError(f"Product size code must be 3-50 characters (got {len(code)} chars)")

        return code

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

    @validates("min_height_cm")
    def validate_min_height_cm(self, key: str, value: object) -> object:
        """Validate min_height_cm is non-negative numeric.

        Rules:
            1. If provided, must be ≥0
            2. Can be None

        Args:
            key: Column name (always 'min_height_cm')
            value: Min height in cm

        Returns:
            Validated value

        Raises:
            ValueError: If not valid
        """
        if value is None:
            return None
        try:
            float_val = float(value)  # type: ignore[arg-type]
            if float_val < 0:
                raise ValueError(f"min_height_cm must be ≥0 (got: {value})")
        except (TypeError, ValueError) as e:
            if "must be ≥0" in str(e):
                raise
            raise ValueError(f"min_height_cm must be numeric (got: {type(value).__name__})") from e
        return value

    @validates("max_height_cm")
    def validate_max_height_cm(self, key: str, value: object) -> object:
        """Validate max_height_cm is non-negative numeric and ≥ min_height_cm.

        Rules:
            1. If provided, must be ≥0
            2. Must be ≥ min_height_cm
            3. Can be None

        Args:
            key: Column name (always 'max_height_cm')
            value: Max height in cm

        Returns:
            Validated value

        Raises:
            ValueError: If not valid
        """
        if value is None:
            return None
        try:
            float_val = float(value)  # type: ignore[arg-type]
            if float_val < 0:
                raise ValueError(f"max_height_cm must be ≥0 (got: {value})")
            # Check against min_height_cm if it exists
            if self.min_height_cm is not None:
                min_val = float(self.min_height_cm)
                if float_val < min_val:
                    raise ValueError(
                        f"max_height_cm must be ≥ min_height_cm ({min_val}, got: {value})"
                    )
        except (TypeError, ValueError) as e:
            if "must be" in str(e):
                raise
            raise ValueError(f"max_height_cm must be numeric (got: {type(value).__name__})") from e
        return value

    def __repr__(self) -> str:
        """String representation for debugging.

        Returns:
            String with product_size_id, code, name, height range, and sort_order

        Example:
            <ProductSize(product_size_id=3, code='M', name='Medium (10-20cm)',
             height_range='10.0-20.0cm', sort_order=30)>
        """
        height_range = "N/A"
        if self.min_height_cm is not None and self.max_height_cm is not None:
            height_range = f"{self.min_height_cm}-{self.max_height_cm}cm"
        elif self.min_height_cm is not None:
            height_range = f"{self.min_height_cm}+cm"
        elif self.max_height_cm is not None:
            height_range = f"<{self.max_height_cm}cm"

        return (
            f"<ProductSize("
            f"product_size_id={self.product_size_id}, "
            f"code='{self.code}', "
            f"name='{self.name}', "
            f"height_range='{height_range}', "
            f"sort_order={self.sort_order}"
            f")>"
        )
