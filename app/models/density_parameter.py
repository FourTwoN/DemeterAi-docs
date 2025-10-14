"""DensityParameter model - Density-based plant count estimation calibration.

This module defines the DensityParameter SQLAlchemy model for storing calibration
data for density-based plant count estimation. Used by ML pipeline to estimate
plant counts in dense vegetation areas.

Architecture:
    Layer: Database / Models (Infrastructure Layer)
    Dependencies: SQLAlchemy 2.0, PostgreSQL 18
    Pattern: Calibration catalog (NO seed data, user-created)

Design Decisions:
    - Composite key: storage_bin_type_id + product_id + packaging_catalog_id
    - avg_area_per_plant_cm2: Average plant footprint
    - plants_per_m2: Derived density metric
    - overlap_adjustment_factor: Overlap correction (default 0.85)
    - avg_diameter_cm: Average plant diameter
    - Timestamps: created_at + updated_at (auto-managed)

See:
    - Database ERD: ../../database/database.mmd (lines 315-327)
    - Database docs: ../../engineering_plan/database/README.md

Example:
    ```python
    # Create density parameters for Echeveria in plug trays
    density = DensityParameter(
        storage_bin_type_id=1,
        product_id=42,
        packaging_catalog_id=7,
        avg_area_per_plant_cm2=25.0,
        plants_per_m2=400.0,
        overlap_adjustment_factor=0.85,
        avg_diameter_cm=5.0,
        notes="Calibrated for 288-cell plug trays"
    )
    ```
"""

from typing import TYPE_CHECKING

from sqlalchemy import (
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
    from app.models.storage_bin_type import StorageBinType


class DensityParameter(Base):
    """DensityParameter model for density-based plant count estimation calibration.

    Stores calibration data for density-based estimation in dense vegetation areas.
    Used by ML pipeline when individual plants cannot be separated by object detection.

    Key Features:
        - Composite key: bin_type_id + product_id + packaging_catalog_id
        - avg_area_per_plant_cm2: Average plant footprint
        - plants_per_m2: Density metric
        - overlap_adjustment_factor: Overlap correction (default 0.85)
        - avg_diameter_cm: Average plant diameter

    Attributes:
        id: Primary key (auto-increment)
        storage_bin_type_id: FK to storage_bin_types (CASCADE, NOT NULL)
        product_id: FK to products (CASCADE, NOT NULL)
        packaging_catalog_id: FK to packaging_catalog (CASCADE, NOT NULL)
        avg_area_per_plant_cm2: Average plant footprint in cm² (NUMERIC, NOT NULL, CHECK > 0.0)
        plants_per_m2: Plants per square meter (NUMERIC, NOT NULL, CHECK > 0.0)
        overlap_adjustment_factor: Overlap correction factor (NUMERIC, default 0.85, CHECK 0.0-1.0)
        avg_diameter_cm: Average plant diameter in cm (NUMERIC, NOT NULL, CHECK > 0.0)
        notes: Optional text notes (NULLABLE)
        created_at: Param creation timestamp (auto)
        updated_at: Last update timestamp (auto)

    Relationships:
        storage_bin_type: StorageBinType instance (many-to-one)
        product: Product instance (many-to-one)
        packaging_catalog: PackagingCatalog instance (many-to-one)

    Indexes:
        - B-tree index on storage_bin_type_id (foreign key)
        - B-tree index on product_id (foreign key)
        - B-tree index on packaging_catalog_id (foreign key)

    Constraints:
        - CHECK avg_area_per_plant_cm2 > 0.0
        - CHECK plants_per_m2 > 0.0
        - CHECK overlap_adjustment_factor between 0.0 and 1.0
        - CHECK avg_diameter_cm > 0.0

    Example:
        ```python
        density = DensityParameter(
            storage_bin_type_id=1,
            product_id=42,
            packaging_catalog_id=7,
            avg_area_per_plant_cm2=25.0,
            plants_per_m2=400.0,
            overlap_adjustment_factor=0.85,
            avg_diameter_cm=5.0
        )
        ```
    """

    __tablename__ = "density_parameters"

    # Primary key
    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Primary key (auto-increment)",
    )

    # Foreign keys
    storage_bin_type_id = Column(
        Integer,
        ForeignKey("storage_bin_types.storage_bin_type_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to storage_bin_types (CASCADE delete)",
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
        nullable=False,
        index=True,
        comment="Foreign key to packaging_catalog (CASCADE delete)",
    )

    # Density metrics
    avg_area_per_plant_cm2 = Column(
        Numeric(10, 2),
        nullable=False,
        comment="Average plant footprint in cm² (CHECK > 0.0)",
    )

    plants_per_m2 = Column(
        Numeric(10, 2),
        nullable=False,
        comment="Plants per square meter (CHECK > 0.0)",
    )

    overlap_adjustment_factor = Column(
        Numeric(3, 2),
        nullable=False,
        default=0.85,
        comment="Overlap correction factor (default 0.85, CHECK 0.0-1.0)",
    )

    avg_diameter_cm = Column(
        Numeric(10, 2),
        nullable=False,
        comment="Average plant diameter in cm (CHECK > 0.0)",
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
        comment="Param creation timestamp",
    )

    updated_at = Column(
        DateTime(timezone=True),
        onupdate=func.now(),
        nullable=True,
        comment="Last update timestamp",
    )

    # Relationships
    storage_bin_type: Mapped["StorageBinType"] = relationship(
        "StorageBinType",
        back_populates="density_parameters",
        doc="Storage bin type",
    )

    product: Mapped["Product"] = relationship(
        "Product",
        back_populates="density_parameters",
        doc="Product",
    )

    packaging_catalog: Mapped["PackagingCatalog"] = relationship(
        "PackagingCatalog",
        back_populates="density_parameters",
        doc="Packaging catalog",
    )

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "avg_area_per_plant_cm2 > 0.0",
            name="ck_density_param_area_positive",
        ),
        CheckConstraint(
            "plants_per_m2 > 0.0",
            name="ck_density_param_density_positive",
        ),
        CheckConstraint(
            "overlap_adjustment_factor >= 0.0 AND overlap_adjustment_factor <= 1.0",
            name="ck_density_param_overlap_range",
        ),
        CheckConstraint(
            "avg_diameter_cm > 0.0",
            name="ck_density_param_diameter_positive",
        ),
        {
            "comment": "Density Parameters - Calibration data for density-based plant count estimation. NO seed data."
        },
    )

    @validates("avg_area_per_plant_cm2", "plants_per_m2", "avg_diameter_cm")
    def validate_positive(self, key: str, value: float | None) -> float | None:
        """Validate positive metrics."""
        if value is None:
            raise ValueError(f"{key} cannot be None")
        if value <= 0.0:
            raise ValueError(f"{key} must be positive (got: {value})")
        return value

    @validates("overlap_adjustment_factor")
    def validate_overlap(self, key: str, value: float | None) -> float | None:
        """Validate overlap_adjustment_factor."""
        if value is None:
            raise ValueError("overlap_adjustment_factor cannot be None")
        if not (0.0 <= value <= 1.0):
            raise ValueError(f"overlap_adjustment_factor must be 0.0-1.0 (got: {value})")
        return value

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"<DensityParameter("
            f"id={self.id}, "
            f"bin_type_id={self.storage_bin_type_id}, "
            f"product_id={self.product_id}, "
            f"plants_per_m2={self.plants_per_m2}"
            f")>"
        )
