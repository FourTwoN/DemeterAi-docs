"""ProductSampleImage model - Product reference images for ML training and catalogs.

This module defines the ProductSampleImage SQLAlchemy model for managing product
reference images used for ML training, quality checks, and product catalogs.

Architecture:
    Layer: Database / Models (Infrastructure Layer)
    Dependencies: SQLAlchemy 2.0, PostgreSQL 18
    Pattern: Reference image catalog (NO seed data, user-created)

See:
    - Database ERD: ../../database/database.mmd (lines 246-260)
    - Database docs: ../../engineering_plan/database/README.md
"""

import enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, relationship
from sqlalchemy.sql import func

from app.db.base import Base

# Forward declarations for type hints (avoids circular imports)
if TYPE_CHECKING:
    from app.models.product import Product
    from app.models.product_size import ProductSize
    from app.models.product_state import ProductState
    from app.models.s3_image import S3Image
    from app.models.storage_location import StorageLocation
    from app.models.user import User


class SampleTypeEnum(str, enum.Enum):
    """Sample type enum."""

    REFERENCE = "reference"
    GROWTH_STAGE = "growth_stage"
    QUALITY_CHECK = "quality_check"
    MONTHLY_SAMPLE = "monthly_sample"


class ProductSampleImage(Base):
    """ProductSampleImage model for product reference images."""

    __tablename__ = "product_sample_images"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True, comment="Primary key")

    # Foreign keys
    product_id = Column(
        Integer,
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to products",
    )

    image_id = Column(
        UUID(as_uuid=True),
        ForeignKey("s3_images.image_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to s3_images",
    )

    product_state_id = Column(
        Integer,
        ForeignKey("product_states.product_state_id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="FK to product_states (nullable)",
    )

    product_size_id = Column(
        Integer,
        ForeignKey("product_sizes.product_size_id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="FK to product_sizes (nullable)",
    )

    storage_location_id = Column(
        Integer,
        ForeignKey("storage_locations.location_id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="FK to storage_locations (nullable)",
    )

    captured_by_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to users",
    )

    # Metadata
    sample_type = Column(
        Enum(
            SampleTypeEnum,
            name="sample_type_enum",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        comment="Sample type enum",
    )

    capture_date = Column(Date, nullable=False, comment="Capture date")
    notes = Column(Text, nullable=True, comment="Notes")
    display_order = Column(Integer, nullable=False, default=0, comment="Display order")
    is_primary = Column(Boolean, nullable=False, default=False, comment="Primary flag")
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, comment="Created at"
    )

    # Relationships
    product: Mapped["Product"] = relationship(
        "Product", back_populates="product_sample_images", doc="Product"
    )

    image: Mapped["S3Image"] = relationship("S3Image", doc="S3 image")

    product_state: Mapped["ProductState | None"] = relationship(
        "ProductState", back_populates="product_sample_images", doc="Product state (optional)"
    )

    product_size: Mapped["ProductSize | None"] = relationship(
        "ProductSize", back_populates="product_sample_images", doc="Product size (optional)"
    )

    storage_location: Mapped["StorageLocation | None"] = relationship(
        "StorageLocation", back_populates="product_sample_images", doc="Storage location (optional)"
    )

    captured_by_user: Mapped["User"] = relationship("User", doc="User who captured")

    # Table constraints
    __table_args__ = (
        {
            "comment": "Product Sample Images - Reference images for ML training and catalogs. NO seed data."
        },
    )

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"<ProductSampleImage("
            f"id={self.id}, "
            f"product_id={self.product_id}, "
            f"sample_type='{self.sample_type}', "
            f"is_primary={self.is_primary}"
            f")>"
        )
