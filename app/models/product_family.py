"""ProductFamily model - Reference/Catalog table for product taxonomy LEVEL 2.

This module defines the ProductFamily SQLAlchemy model for LEVEL 2 of the
3-level Product Catalog hierarchy (Category → Family → Product). Represents
plant genera/families within product categories (e.g., Echeveria, Aloe, Monstera).

Architecture:
    Layer: Database / Models (Infrastructure Layer)
    Dependencies: SQLAlchemy 2.0, PostgreSQL 18
    Pattern: Reference/Catalog table with seed data

Design Decisions:
    - LEVEL 2 taxonomy: Middle level of Category → Family → Product hierarchy
    - 15-20 seed families: Preloaded via migration across 8 categories
    - Simpler than ProductCategory: NO code field, NO timestamps (per ERD)
    - FK to ProductCategory: category_id (CASCADE delete)
    - INT PK: Simple auto-increment (reference/catalog pattern)
    - Scientific names: NULLABLE (some families may not have scientific classification)
    - Relationships: COMMENTED OUT (Product not ready)

See:
    - Database ERD: ../../database/database.mmd (lines 81-87)
    - Database docs: ../../engineering_plan/database/README.md
    - Task specification: ../../backlog/03_kanban/02_in-progress/DB016-product-families-model.md

Example:
    ```python
    # Create family
    echeveria = ProductFamily(
        category_id=1,  # CACTUS category
        name="Echeveria",
        scientific_name="Echeveria",
        description="Small rosette-forming succulents native to Mexico"
    )

    # Query by category
    cactus_families = session.query(ProductFamily).filter_by(category_id=1).all()

    # Access category relationship
    family = session.query(ProductFamily).filter_by(name="Aloe").first()
    # family.category.name returns "Succulent"
    ```
"""

from typing import TYPE_CHECKING

from sqlalchemy import Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, relationship

from app.db.base import Base

# Forward declarations for type hints (avoids circular imports)
if TYPE_CHECKING:
    # NOTE: Uncommented after DB017 (Products) complete
    from app.models.product import Product
    from app.models.product_category import ProductCategory


class ProductFamily(Base):
    """ProductFamily model representing product taxonomy LEVEL 2.

    Reference/catalog table defining plant families/genera within product categories.
    This is LEVEL 2 of the 3-level Product Catalog hierarchy:
    - Level 1: ProductCategory (ROOT)
    - Level 2: ProductFamily (LEVEL 2) ← THIS MODEL
    - Level 3: Product (LEAF - category_id FK)

    Key Features:
        - LEVEL 2 taxonomy: Defines families within categories (Echeveria, Aloe, etc.)
        - 15-20 seed families: Preloaded via migration
        - Simpler than ProductCategory: NO code field, NO timestamps (per ERD)
        - FK to ProductCategory: category_id (CASCADE delete)
        - Scientific names: NULLABLE (optional botanical classification)
        - INT PK: Simple auto-increment (reference/catalog pattern)

    Attributes:
        family_id: Primary key (auto-increment)
        category_id: Foreign key to product_categories (CASCADE, NOT NULL)
        name: Human-readable family name (200 chars max, NOT NULL)
        scientific_name: Optional botanical/scientific name (200 chars max, NULLABLE)
        description: Optional detailed description (text, NULLABLE)

    Relationships:
        category: ProductCategory instance (many-to-one)
        products: List of Product instances in this family (one-to-many, COMMENTED OUT)

    Indexes:
        - B-tree index on category_id (foreign key)

    Example:
        ```python
        # Create family with category FK
        aloe = ProductFamily(
            category_id=2,  # SUCCULENT category
            name="Aloe",
            scientific_name="Aloe",
            description="Succulent plants with thick fleshy leaves"
        )

        # Query by category
        succulent_families = session.query(ProductFamily).filter_by(category_id=2).all()

        # Access category relationship
        # aloe.category.name returns "Succulent"
        ```
    """

    __tablename__ = "product_families"

    # Primary key
    family_id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Primary key (auto-increment)",
    )

    # Foreign key to product_categories (CASCADE delete)
    category_id = Column(
        Integer,
        ForeignKey("product_categories.product_category_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to product_categories (CASCADE delete)",
    )

    # Family identification (NO code field per ERD)
    name = Column(
        String(200),
        nullable=False,
        comment="Human-readable family name (e.g., Echeveria, Aloe)",
    )

    scientific_name = Column(
        String(200),
        nullable=True,
        comment="Optional botanical/scientific name",
    )

    description = Column(
        Text,
        nullable=True,
        comment="Optional detailed description",
    )

    # NO timestamps (per ERD lines 81-87)

    # Relationships

    # Many-to-one: ProductFamily → ProductCategory
    category: Mapped["ProductCategory"] = relationship(
        "ProductCategory",
        back_populates="product_families",
        doc="Category this family belongs to",
    )

    # One-to-many: ProductFamily → Product (UNCOMMENTED - DB017 complete)
    products: Mapped[list["Product"]] = relationship(
        "Product",
        back_populates="family",
        foreign_keys="[Product.family_id]",
        doc="List of products in this family",
    )

    # Table constraints
    __table_args__ = (
        {"comment": "Product Families - LEVEL 2 taxonomy (Category → Family → Product)"},
    )

    def __repr__(self) -> str:
        """String representation for debugging.

        Returns:
            String with family_id, category_id, and name

        Example:
            <ProductFamily(family_id=1, category_id=1, name='Echeveria')>
        """
        return (
            f"<ProductFamily("
            f"family_id={self.family_id}, "
            f"category_id={self.category_id}, "
            f"name='{self.name}'"
            f")>"
        )
