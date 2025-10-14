"""StorageLocationConfig model - Configuration for storage location product/packaging.

This module defines the StorageLocationConfig SQLAlchemy model for configuring
expected products and packaging at storage locations. Enables validation during
manual stock initialization and ML processing.

Architecture:
    Layer: Database / Models (Infrastructure Layer)
    Dependencies: SQLAlchemy 2.0, PostgreSQL 18
    Pattern: Configuration catalog (NO seed data, user-created)

Design Decisions:
    - storage_location_id FK: One config per location (NOT unique, many configs allowed)
    - product_id + packaging_catalog_id FKs: Expected product/packaging
    - expected_product_state_id FK: Expected lifecycle state
    - area_cm2: Location area in cm² for density calculations
    - active flag: Soft delete (default True)
    - Timestamps: created_at + updated_at (auto-managed)

See:
    - Database ERD: ../../database/database.mmd (lines 303-314)
    - Database docs: ../../engineering_plan/database/README.md

Example:
    ```python
    # Create config for Echeveria in 10cm pots
    config = StorageLocationConfig(
        storage_location_id=1,
        product_id=42,
        packaging_catalog_id=7,
        expected_product_state_id=3,  # Adult
        area_cm2=5000.0,
        active=True,
        notes="North wing - premium quality"
    )
    ```
"""

from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    Text,
)
from sqlalchemy.orm import Mapped, relationship, validates
from sqlalchemy.sql import func

from app.db.base import Base

# Forward declarations for type hints (avoids circular imports)
if TYPE_CHECKING:
    from app.models.packaging_catalog import PackagingCatalog
    from app.models.product import Product
    from app.models.product_state import ProductState
    from app.models.storage_location import StorageLocation


class StorageLocationConfig(Base):
    """StorageLocationConfig model for storage location product/packaging configuration.

    Configures expected products, packaging, and state at storage locations.
    Enables validation during manual stock initialization and ML processing.

    Key Features:
        - storage_location_id FK: Configuration for specific location
        - product_id FK: Expected product
        - packaging_catalog_id FK: Expected packaging (nullable)
        - expected_product_state_id FK: Expected lifecycle state
        - area_cm2: Location area for density calculations
        - active flag: Soft delete (default True)

    Attributes:
        id: Primary key (auto-increment)
        storage_location_id: FK to storage_locations (CASCADE, NOT NULL)
        product_id: FK to products (CASCADE, NOT NULL)
        packaging_catalog_id: FK to packaging_catalog (CASCADE, NULLABLE)
        expected_product_state_id: FK to product_states (CASCADE, NOT NULL)
        area_cm2: Location area in cm² (NUMERIC, NOT NULL, CHECK >= 0.0)
        active: Active flag (default True)
        notes: Optional text notes (NULLABLE)
        created_at: Config creation timestamp (auto)
        updated_at: Last update timestamp (auto)

    Relationships:
        storage_location: StorageLocation instance (many-to-one)
        product: Product instance (many-to-one)
        packaging_catalog: PackagingCatalog instance (many-to-one, optional)
        expected_product_state: ProductState instance (many-to-one)

    Indexes:
        - B-tree index on storage_location_id (foreign key)
        - B-tree index on product_id (foreign key)
        - B-tree index on active (soft delete queries)

    Constraints:
        - CHECK area_cm2 >= 0.0

    Example:
        ```python
        config = StorageLocationConfig(
            storage_location_id=1,
            product_id=42,
            packaging_catalog_id=7,
            expected_product_state_id=3,
            area_cm2=5000.0,
            active=True
        )
        ```
    """

    __tablename__ = "storage_location_config"

    # Primary key
    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Primary key (auto-increment)",
    )

    # Foreign keys
    storage_location_id = Column(
        Integer,
        ForeignKey("storage_locations.location_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to storage_locations (CASCADE delete)",
    )

    product_id = Column(
        Integer,
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to products (CASCADE delete)",
    )

    packaging_catalog_id = Column(
        Integer,
        ForeignKey("packaging_catalog.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Foreign key to packaging_catalog (CASCADE delete, NULLABLE)",
    )

    expected_product_state_id = Column(
        Integer,
        ForeignKey("product_states.product_state_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to product_states (CASCADE delete)",
    )

    # Area
    area_cm2 = Column(
        Numeric(15, 2),
        nullable=False,
        comment="Location area in cm² (CHECK >= 0.0)",
    )

    # Active flag
    active = Column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
        comment="Active flag (default True)",
    )

    # Notes
    notes = Column(
        Text,
        nullable=True,
        comment="Optional text notes (NULLABLE)",
    )

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Config creation timestamp",
    )

    updated_at = Column(
        DateTime(timezone=True),
        onupdate=func.now(),
        nullable=True,
        comment="Last update timestamp",
    )

    # Relationships
    storage_location: Mapped["StorageLocation"] = relationship(
        "StorageLocation",
        back_populates="storage_location_configs",
        doc="Storage location for this config",
    )

    product: Mapped["Product"] = relationship(
        "Product",
        back_populates="storage_location_configs",
        doc="Expected product",
    )

    packaging_catalog: Mapped["PackagingCatalog | None"] = relationship(
        "PackagingCatalog",
        back_populates="storage_location_configs",
        doc="Expected packaging (optional)",
    )

    expected_product_state: Mapped["ProductState"] = relationship(
        "ProductState",
        back_populates="storage_location_configs",
        doc="Expected product state",
    )

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "area_cm2 >= 0.0",
            name="ck_storage_location_config_area_positive",
        ),
        {
            "comment": "Storage Location Config - Product/packaging configuration for storage locations. NO seed data."
        },
    )

    @validates("area_cm2")
    def validate_area(self, key: str, value: float | None) -> float | None:
        """Validate area_cm2 field."""
        if value is None:
            raise ValueError("area_cm2 cannot be None")
        if value < 0.0:
            raise ValueError(f"area_cm2 must be non-negative (got: {value})")
        return value

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"<StorageLocationConfig("
            f"id={self.id}, "
            f"location_id={self.storage_location_id}, "
            f"product_id={self.product_id}, "
            f"active={self.active}"
            f")>"
        )
