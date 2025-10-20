"""PackagingCatalog model - Complete packaging specification catalog (NO seed data).

This module defines the PackagingCatalog SQLAlchemy model combining packaging type,
material, color, and physical dimensions. Each catalog entry represents a distinct
packaging SKU available for stock tracking.

Architecture:
    Layer: Database / Models (Infrastructure Layer)
    Dependencies: SQLAlchemy 2.0, PostgreSQL 18
    Pattern: User-created catalog (NO seed data)

Design Decisions:
    - Composite FK model: type_id + material_id + color_id + dimensions
    - SKU field: Unique, alphanumeric+hyphen, 6-50 chars, uppercase
    - Physical dimensions: volume_liters, diameter_cm, height_cm (all NUMERIC)
    - NO seed data: Created by users/admins as needed
    - NO timestamps: Per ERD (lines 120-130)
    - INT PK: Simple auto-increment (id)

See:
    - Database ERD: ../../database/database.mmd (lines 120-130)
    - Database docs: ../../engineering_plan/database/README.md

Example:
    ```python
    # Create packaging catalog entry
    pot_10cm = PackagingCatalog(
        packaging_type_id=1,      # POT
        packaging_material_id=1,  # PLASTIC
        packaging_color_id=1,     # BLACK
        sku="POT-PLAST-BLK-10CM",
        name="10cm Black Plastic Pot",
        volume_liters=0.5,
        diameter_cm=10.0,
        height_cm=9.0
    )

    # Query by SKU
    packaging = session.query(PackagingCatalog).filter_by(sku="POT-PLAST-BLK-10CM").first()
    ```
"""

from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Column, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, relationship, validates

from app.db.base import Base

# Forward declarations for type hints (avoids circular imports)
if TYPE_CHECKING:
    from app.models.classification import Classification
    from app.models.density_parameter import DensityParameter
    from app.models.packaging_color import PackagingColor
    from app.models.packaging_material import PackagingMaterial
    from app.models.packaging_type import PackagingType
    from app.models.price_list import PriceList
    from app.models.stock_batch import StockBatch
    from app.models.storage_location_config import StorageLocationConfig


class PackagingCatalog(Base):
    """PackagingCatalog model representing complete packaging specifications.

    Combines packaging type, material, color, and physical dimensions into a
    single catalog entry. Each entry represents a distinct packaging SKU that
    can be used in stock tracking, ML classification, and pricing.

    Key Features:
        - Composite FK model: type + material + color + dimensions
        - SKU validation: Unique, uppercase, alphanumeric+hyphen, 6-50 chars
        - Physical dimensions: volume_liters, diameter_cm, height_cm
        - NO seed data: User-created as needed
        - NO timestamps: Per ERD

    Attributes:
        id: Primary key (auto-increment)
        packaging_type_id: Foreign key to packaging_types (CASCADE, NOT NULL)
        packaging_material_id: Foreign key to packaging_materials (CASCADE, NOT NULL)
        packaging_color_id: Foreign key to packaging_colors (CASCADE, NOT NULL)
        sku: Unique packaging SKU (6-50 chars, alphanumeric+hyphen, uppercase)
        name: Human-readable packaging name (200 chars max, NOT NULL)
        volume_liters: Container volume in liters (NUMERIC, NULLABLE)
        diameter_cm: Container diameter in cm (NUMERIC, NULLABLE)
        height_cm: Container height in cm (NUMERIC, NULLABLE)

    Relationships:
        packaging_type: PackagingType instance (many-to-one)
        packaging_material: PackagingMaterial instance (many-to-one)
        packaging_color: PackagingColor instance (many-to-one)
        stock_batches: List of StockBatch instances (one-to-many)
        classifications: List of Classification instances (one-to-many)
        storage_location_configs: List of StorageLocationConfig instances (one-to-many)
        density_parameters: List of DensityParameter instances (one-to-many)
        price_list_items: List of PriceList instances (one-to-many)

    Indexes:
        - B-tree index on sku (unique constraint)
        - B-tree index on packaging_type_id (foreign key)
        - B-tree index on packaging_material_id (foreign key)
        - B-tree index on packaging_color_id (foreign key)

    Constraints:
        - CHECK sku length between 6-50 characters
        - CHECK sku matches alphanumeric+hyphen pattern
        - CHECK volume_liters >= 0 (if not null)
        - CHECK diameter_cm >= 0 (if not null)
        - CHECK height_cm >= 0 (if not null)

    Example:
        ```python
        # Create 10cm black plastic pot
        pot = PackagingCatalog(
            packaging_type_id=1,
            packaging_material_id=1,
            packaging_color_id=1,
            sku="POT-PLAST-BLK-10CM",
            name="10cm Black Plastic Pot",
            volume_liters=0.5,
            diameter_cm=10.0,
            height_cm=9.0
        )

        # Query by dimensions
        small_pots = session.query(PackagingCatalog).filter(
            PackagingCatalog.diameter_cm <= 12.0
        ).all()
        ```
    """

    __tablename__ = "packaging_catalog"

    # Primary key
    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Primary key (auto-increment)",
    )

    # Foreign keys to packaging foundation tables
    packaging_type_id = Column(
        Integer,
        ForeignKey("packaging_types.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to packaging_types (CASCADE delete)",
    )

    packaging_material_id = Column(
        Integer,
        ForeignKey("packaging_materials.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to packaging_materials (CASCADE delete)",
    )

    packaging_color_id = Column(
        Integer,
        ForeignKey("packaging_colors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to packaging_colors (CASCADE delete)",
    )

    # Unique SKU field (6-50 chars, alphanumeric+hyphen, uppercase)
    sku = Column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique packaging SKU (6-50 chars, alphanumeric+hyphen, uppercase)",
    )

    # Packaging identification
    name = Column(
        String(200),
        nullable=False,
        comment="Human-readable packaging name (e.g., '10cm Black Plastic Pot')",
    )

    # Physical dimensions (all nullable)
    volume_liters = Column(
        Numeric(10, 2),
        nullable=True,
        comment="Container volume in liters (NULLABLE)",
    )

    diameter_cm = Column(
        Numeric(10, 2),
        nullable=True,
        comment="Container diameter in cm (NULLABLE)",
    )

    height_cm = Column(
        Numeric(10, 2),
        nullable=True,
        comment="Container height in cm (NULLABLE)",
    )

    # NO timestamps (per ERD lines 120-130)

    # Relationships

    # Many-to-one: PackagingCatalog → PackagingType
    packaging_type: Mapped["PackagingType"] = relationship(
        "PackagingType",
        back_populates="packaging_catalog_items",
        doc="Packaging type (e.g., POT, PLUG_TRAY)",
    )

    # Many-to-one: PackagingCatalog → PackagingMaterial
    packaging_material: Mapped["PackagingMaterial"] = relationship(
        "PackagingMaterial",
        back_populates="packaging_catalog_items",
        doc="Packaging material (e.g., PLASTIC, TERRACOTTA)",
    )

    # Many-to-one: PackagingCatalog → PackagingColor
    packaging_color: Mapped["PackagingColor"] = relationship(
        "PackagingColor",
        back_populates="packaging_catalog_items",
        doc="Packaging color (e.g., Black, Terracotta)",
    )

    # One-to-many: PackagingCatalog → StockBatch (COMMENT OUT - not ready)
    # NOTE: Uncomment after StockBatch model is complete
    stock_batches: Mapped[list["StockBatch"]] = relationship(
        "StockBatch",
        back_populates="packaging_catalog",
        foreign_keys="StockBatch.packaging_catalog_id",
        doc="List of stock batches using this packaging",
    )

    # One-to-many: PackagingCatalog → Classification
    classifications: Mapped[list["Classification"]] = relationship(
        "Classification",
        back_populates="packaging_catalog",
        foreign_keys="Classification.packaging_catalog_id",
        doc="List of ML classifications for this packaging",
    )

    # One-to-many: PackagingCatalog → StorageLocationConfig (COMMENT OUT - not ready)
    # NOTE: Uncomment after StorageLocationConfig model is complete
    storage_location_configs: Mapped[list["StorageLocationConfig"]] = relationship(
        "StorageLocationConfig",
        back_populates="packaging_catalog",
        foreign_keys="StorageLocationConfig.packaging_catalog_id",
        doc="List of storage location configs using this packaging",
    )

    # One-to-many: PackagingCatalog → DensityParameter
    density_parameters: Mapped[list["DensityParameter"]] = relationship(
        "DensityParameter",
        back_populates="packaging_catalog",
        foreign_keys="DensityParameter.packaging_catalog_id",
        doc="List of density parameters for this packaging",
    )

    # One-to-many: PackagingCatalog → PriceList
    price_list_items: Mapped[list["PriceList"]] = relationship(
        "PriceList",
        back_populates="packaging_catalog",
        foreign_keys="PriceList.packaging_catalog_id",
        doc="List of price list items for this packaging",
    )

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "LENGTH(sku) >= 6 AND LENGTH(sku) <= 50",
            name="ck_packaging_catalog_sku_length",
        ),
        CheckConstraint(
            "sku ~ '^[A-Z0-9-]+$'",
            name="ck_packaging_catalog_sku_format",
        ),
        CheckConstraint(
            "volume_liters IS NULL OR volume_liters >= 0",
            name="ck_packaging_catalog_volume_positive",
        ),
        CheckConstraint(
            "diameter_cm IS NULL OR diameter_cm >= 0",
            name="ck_packaging_catalog_diameter_positive",
        ),
        CheckConstraint(
            "height_cm IS NULL OR height_cm >= 0",
            name="ck_packaging_catalog_height_positive",
        ),
        {
            "comment": "Packaging Catalog - Complete packaging specifications (type + material + color + dimensions). NO seed data."
        },
    )

    @validates("sku")
    def validate_sku(self, key: str, value: str | None) -> str | None:
        """Validate and normalize SKU field.

        Rules:
            - Length: 6-50 characters
            - Characters: Alphanumeric + hyphen only
            - Auto-convert to uppercase

        Args:
            key: Field name ("sku")
            value: SKU value to validate

        Returns:
            Normalized SKU (uppercase)

        Raises:
            ValueError: If SKU is invalid

        Examples:
            >>> packaging.sku = "pot-plast-blk-10cm"
            >>> packaging.sku
            "POT-PLAST-BLK-10CM"

            >>> packaging.sku = "POT10"  # Too short
            ValueError: SKU must be 6-50 characters (got: 5)

            >>> packaging.sku = "POT_10CM"  # Invalid character
            ValueError: SKU must contain only alphanumeric characters and hyphens
        """
        if value is None:
            raise ValueError("SKU cannot be None")

        # Auto-convert to uppercase
        value = value.upper()

        # Validate length
        if len(value) < 6 or len(value) > 50:
            raise ValueError(f"SKU must be 6-50 characters (got: {len(value)})")

        # Validate characters (alphanumeric + hyphen only)
        if not all(c.isalnum() or c == "-" for c in value):
            raise ValueError("SKU must contain only alphanumeric characters and hyphens")

        return value

    @validates("volume_liters", "diameter_cm", "height_cm")
    def validate_dimensions(self, key: str, value: float | None) -> float | None:
        """Validate dimension fields are non-negative.

        Args:
            key: Field name (volume_liters, diameter_cm, or height_cm)
            value: Dimension value to validate

        Returns:
            Validated dimension value

        Raises:
            ValueError: If dimension is negative

        Examples:
            >>> packaging.volume_liters = 0.5
            >>> packaging.volume_liters
            0.5

            >>> packaging.diameter_cm = -10.0
            ValueError: diameter_cm must be non-negative (got: -10.0)
        """
        if value is not None and value < 0:
            raise ValueError(f"{key} must be non-negative (got: {value})")

        return value

    def __repr__(self) -> str:
        """String representation for debugging.

        Returns:
            String with id, sku, and name

        Example:
            <PackagingCatalog(id=1, sku='POT-PLAST-BLK-10CM', name='10cm Black Plastic Pot')>
        """
        return (
            f"<PackagingCatalog("
            f"id={self.id}, "
            f"sku='{self.sku}', "
            f"name='{self.name}'"
            f")>"
        )
