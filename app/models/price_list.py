"""PriceList model - Product pricing catalog for wholesale and retail.

This module defines the PriceList SQLAlchemy model for managing product prices
by packaging and category. Supports wholesale and retail pricing with discounts.

Architecture:
    Layer: Database / Models (Infrastructure Layer)
    Dependencies: SQLAlchemy 2.0, PostgreSQL 18
    Pattern: Pricing catalog (NO seed data, user-created)

See:
    - Database ERD: ../../database/database.mmd (lines 131-144)
    - Database docs: ../../engineering_plan/database/README.md
"""

from typing import TYPE_CHECKING

from sqlalchemy import Column, Date, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, relationship

from app.db.base import Base

# Forward declarations for type hints (avoids circular imports)
if TYPE_CHECKING:
    from app.models.packaging_catalog import PackagingCatalog
    from app.models.product_category import ProductCategory


class PriceList(Base):
    """PriceList model for product pricing by packaging and category."""

    __tablename__ = "price_list"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True, comment="Primary key")

    # Foreign keys
    packaging_catalog_id = Column(
        Integer,
        ForeignKey("packaging_catalog.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to packaging_catalog",
    )

    product_categories_id = Column(
        Integer,
        ForeignKey("product_categories.product_category_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to product_categories (product_category_id)",
    )

    # Pricing
    wholesale_unit_price = Column(Integer, nullable=False, comment="Wholesale unit price")
    retail_unit_price = Column(Integer, nullable=False, comment="Retail unit price")
    SKU = Column(String(50), nullable=True, comment="SKU")
    unit_per_storage_box = Column(Integer, nullable=True, comment="Units per box")
    wholesale_total_price_per_box = Column(Integer, nullable=True, comment="Wholesale box price")
    observations = Column(String(255), nullable=True, comment="Observations")
    availability = Column(String(50), nullable=True, comment="Availability")
    discount_factor = Column(Integer, nullable=True, comment="Discount factor")
    updated_at = Column(Date, nullable=True, comment="Last update date")

    # Relationships
    packaging_catalog: Mapped["PackagingCatalog"] = relationship(
        "PackagingCatalog",
        back_populates="price_list_items",
        doc="Packaging catalog",
    )

    product_category: Mapped["ProductCategory"] = relationship(
        "ProductCategory",
        back_populates="price_list_items",
        doc="Product category",
    )

    # Table constraints
    __table_args__ = (
        {"comment": "Price List - Product pricing by packaging and category. NO seed data."},
    )

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"<PriceList("
            f"id={self.id}, "
            f"packaging_id={self.packaging_catalog_id}, "
            f"category_id={self.product_categories_id}, "
            f"retail_price={self.retail_unit_price}"
            f")>"
        )
