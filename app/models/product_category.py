"""ProductCategory model - Reference/Catalog table for product taxonomy ROOT.

This module defines the ProductCategory SQLAlchemy model for the ROOT level of the
3-level Product Catalog hierarchy (Category → Family → Product). Defines high-level
plant categories (Cactus, Succulent, Bromeliad, etc.) used throughout the system.

Architecture:
    Layer: Database / Models (Infrastructure Layer)
    Dependencies: SQLAlchemy 2.0, PostgreSQL 18
    Pattern: Reference/Catalog table with seed data

Design Decisions:
    - ROOT taxonomy: Top level of Category → Family → Product hierarchy
    - 8 seed categories: CACTUS, SUCCULENT, BROMELIAD, CARNIVOROUS, ORCHID, FERN, TROPICAL, HERB
    - Flat taxonomy: NO parent_category_id (not hierarchical per ERD)
    - Code validation: uppercase, alphanumeric + underscores, 3-50 chars
    - INT PK: Simple auto-increment (reference/catalog pattern)
    - Relationships: COMMENTED OUT (ProductFamily, PriceList not ready)

See:
    - Database ERD: ../../database/database.mmd (lines 75-80)
    - Database docs: ../../engineering_plan/database/README.md
    - Task specification: ../../backlog/03_kanban/02_in-progress/DB015-product-categories-model.md

Example:
    ```python
    # Create category
    cactus = ProductCategory(
        code="CACTUS",
        name="Cactus",
        description="Cacti family (Cactaceae) - succulent plants with spines"
    )

    # Query by code (UK index)
    category = session.query(ProductCategory).filter_by(code="SUCCULENT").first()

    # Order by name
    categories = session.query(ProductCategory).order_by(ProductCategory.name).all()
    ```
"""

import re
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Column, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, relationship, validates
from sqlalchemy.sql import func

from app.db.base import Base

# Forward declarations for type hints (avoids circular imports)
if TYPE_CHECKING:
    from app.models.product_family import ProductFamily

    # NOTE: Uncomment after DB027 (PriceList) is complete
    # from app.models.price_list import PriceList


class ProductCategory(Base):
    """ProductCategory model representing product taxonomy ROOT.

    Reference/catalog table defining high-level product categories used for product
    classification, inventory grouping, pricing rules, and business analytics. This is
    the ROOT of the 3-level Product Catalog hierarchy:
    - Level 1: ProductCategory (ROOT) ← THIS MODEL
    - Level 2: ProductFamily (category_id FK)
    - Level 3: Product (family_id FK)

    Key Features:
        - ROOT taxonomy: Defines top-level categories (Cactus, Succulent, etc.)
        - 8 seed categories: Preloaded via migration
        - Flat taxonomy: NO parent_category_id (not hierarchical per ERD)
        - Code validation: uppercase, alphanumeric + underscores, 3-50 chars
        - UK constraint: Code must be unique
        - INT PK: Simple auto-increment (reference/catalog pattern)

    Attributes:
        product_category_id: Primary key (auto-increment)
        code: Unique category code (uppercase, alphanumeric + underscores, 3-50 chars)
        name: Human-readable category name (200 chars max)
        description: Optional detailed description (text)
        created_at: Record creation timestamp (auto)
        updated_at: Last update timestamp (auto)

    Relationships:
        product_families: List of ProductFamily instances in this category (one-to-many, COMMENTED OUT)
        price_lists: List of PriceList instances for this category (one-to-many, COMMENTED OUT)

    Indexes:
        - B-tree index on code (unique lookups)

    CHECK Constraint:
        - code length between 3 and 50 characters

    Example:
        ```python
        # Create category
        cactus = ProductCategory(
            code="CACTUS",
            name="Cactus",
            description="Cacti family (Cactaceae) - succulent plants with spines"
        )

        # Auto-uppercase
        orchid = ProductCategory(code="orchid", name="Orchid")
        assert orchid.code == "ORCHID"

        # Query by code (UK index used)
        category = session.query(ProductCategory).filter_by(code="BROMELIAD").first()
        ```
    """

    __tablename__ = "product_categories"

    # Primary key
    product_category_id = Column(
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
        comment="Unique category code (uppercase, alphanumeric + underscores, 3-50 chars)",
    )

    name = Column(
        String(200),
        nullable=False,
        comment="Human-readable category name",
    )

    description = Column(
        Text,
        nullable=True,
        comment="Optional detailed description",
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

    # Relationships

    # One-to-many: ProductCategory → ProductFamily
    product_families: Mapped[list["ProductFamily"]] = relationship(
        "ProductFamily",
        back_populates="category",
        foreign_keys="ProductFamily.category_id",
        doc="List of product families in this category",
    )

    # One-to-many: ProductCategory → PriceList (COMMENT OUT - DB027 not ready)
    # NOTE: Uncomment after DB027 (PriceList) is complete
    # price_lists: Mapped[list["PriceList"]] = relationship(
    #     "PriceList",
    #     back_populates="category",
    #     foreign_keys="PriceList.category_id",
    #     doc="List of price lists for this category"
    # )

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "LENGTH(code) >= 3 AND LENGTH(code) <= 50",
            name="ck_product_category_code_length",
        ),
        {"comment": "Product Categories - ROOT taxonomy table (Category → Family → Product)"},
    )

    @validates("code")
    def validate_code(self, key: str, value: str) -> str:
        """Validate product category code format.

        Rules:
            1. Required (not empty)
            2. Must be uppercase
            3. Alphanumeric + underscores only (NO hyphens, NO spaces)
            4. Length between 3 and 50 characters

        Args:
            key: Column name (always 'code')
            value: Product category code to validate

        Returns:
            Validated product category code (uppercase)

        Raises:
            ValueError: If validation fails with specific error message

        Example:
            ```python
            category.code = "CACTUS"           # Valid
            category.code = "cactus"           # Auto-uppercases to "CACTUS"
            category.code = "ORCHID_123"       # Valid (underscores OK)
            category.code = "CACTUS-123"       # Raises ValueError (hyphens not allowed)
            category.code = "CA"               # Raises ValueError (too short)
            category.code = ""                 # Raises ValueError (empty)
            ```
        """
        if not value or not value.strip():
            raise ValueError("Product category code cannot be empty")

        code = value.strip().upper()

        # Check alphanumeric + underscores only (NO hyphens, NO spaces)
        if not re.match(r"^[A-Z0-9_]+$", code):
            raise ValueError(
                f"Product category code must be alphanumeric + underscores only "
                f"(NO hyphens, NO spaces, got: {code})"
            )

        if len(code) < 3 or len(code) > 50:
            raise ValueError(
                f"Product category code must be 3-50 characters (got {len(code)} chars)"
            )

        return code

    def __repr__(self) -> str:
        """String representation for debugging.

        Returns:
            String with product_category_id, code, and name

        Example:
            <ProductCategory(product_category_id=1, code='CACTUS', name='Cactus')>
        """
        return (
            f"<ProductCategory("
            f"product_category_id={self.product_category_id}, "
            f"code='{self.code}', "
            f"name='{self.name}'"
            f")>"
        )
