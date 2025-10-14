"""Product model - Main product catalog LEAF model (NO seed data).

This module defines the Product SQLAlchemy model for LEVEL 3 of the
3-level Product Catalog hierarchy (Category → Family → Product). Represents
individual cacti/succulent products with SKU, names, and flexible metadata.

Architecture:
    Layer: Database / Models (Infrastructure Layer)
    Dependencies: SQLAlchemy 2.0, PostgreSQL 18
    Pattern: User-created catalog (NO seed data, unlike DB015/DB016)

Design Decisions:
    - LEVEL 3 taxonomy: LEAF level of Category → Family → Product hierarchy
    - NO seed data: Products created by users/ML pipeline (unlike DB015/DB016)
    - ONLY 1 FK: family_id (per ERD lines 88-96) - NO product_state_id/size_id here
    - SKU field: Unique, alphanumeric+hyphen, 6-20 chars, barcode-compatible
    - common_name field: NOT "name" (per ERD) - actual field name
    - JSONB custom_attributes: Flexible metadata (color, variegation, growth_rate)
    - NO timestamps: Per ERD (created_at/updated_at not shown)
    - INT PK: Simple auto-increment (product_id)

See:
    - Database ERD: ../../database/database.mmd (lines 88-96)
    - Database docs: ../../engineering_plan/database/README.md
    - Task specification: ../../backlog/03_kanban/02_in-progress/DB017-products-model.md

Example:
    ```python
    # Create product with family FK
    echeveria_lola = Product(
        family_id=1,  # Echeveria family
        sku="ECHEV-LOLA-001",
        common_name="Echeveria 'Lola'",
        scientific_name="Echeveria lilacina × Echeveria derenbergii",
        description="Compact rosette succulent with powdery blue-gray leaves",
        custom_attributes={
            "color": "blue-gray",
            "variegation": False,
            "growth_rate": "slow",
            "bloom_season": "spring",
            "cold_hardy": False
        }
    )

    # Query by family
    echeverias = session.query(Product).filter_by(family_id=1).all()

    # Access family relationship
    product = session.query(Product).filter_by(sku="ECHEV-LOLA-001").first()
    # product.family.name returns "Echeveria"
    # product.family.category.name returns "Cactus"
    ```
"""

from typing import TYPE_CHECKING, Any

from sqlalchemy import CheckConstraint, Column, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, relationship, validates

from app.db.base import Base

# Forward declarations for type hints (avoids circular imports)
if TYPE_CHECKING:
    from app.models.classification import Classification
    from app.models.density_parameter import DensityParameter
    from app.models.product_family import ProductFamily

    # NOTE: Uncomment after dependent models are complete
    # from app.models.stock_batch import StockBatch
    # from app.models.product_sample_image import ProductSampleImage
    # from app.models.storage_location_config import StorageLocationConfig


class Product(Base):
    """Product model representing LEAF products in 3-level taxonomy.

    Main product catalog model for 600,000+ cacti and succulents. This is LEVEL 3
    (LEAF) of the Product Catalog hierarchy:
    - Level 1: ProductCategory (ROOT)
    - Level 2: ProductFamily (LEVEL 2)
    - Level 3: Product (LEAF) ← THIS MODEL

    Key Features:
        - NO seed data: Products created by users/ML pipeline (NOT preloaded)
        - ONLY 1 FK: family_id → product_families (per ERD)
        - SKU field: Unique, alphanumeric+hyphen, 6-20 chars, barcode-compatible
        - common_name: NOT "name" (per ERD lines 88-96)
        - JSONB custom_attributes: Flexible metadata (color, variegation, etc.)
        - NO timestamps: Per ERD (created_at/updated_at not shown)
        - INT PK: Simple auto-increment (product_id)

    Attributes:
        product_id: Primary key (auto-increment) - note: ERD shows "id" but renamed for clarity
        family_id: Foreign key to product_families (CASCADE, NOT NULL)
        sku: Unique Stock Keeping Unit (6-20 chars, alphanumeric+hyphen, uppercase)
        common_name: Human-readable product name (200 chars max, NOT NULL)
        scientific_name: Optional botanical name (200 chars max, NULLABLE)
        description: Optional detailed description (text, NULLABLE)
        custom_attributes: JSONB flexible metadata (color, variegation, etc., default {})

    Relationships:
        family: ProductFamily instance (many-to-one)
        stock_batches: List of StockBatch instances (one-to-many, COMMENTED OUT)
        classifications: List of Classification instances (one-to-many)
        density_parameters: List of DensityParameter instances (one-to-many)
        product_sample_images: List of ProductSampleImage instances (one-to-many, COMMENTED OUT)
        storage_location_configs: List of StorageLocationConfig instances (one-to-many, COMMENTED OUT)

    Indexes:
        - B-tree index on family_id (foreign key)
        - B-tree index on sku (unique constraint)
        - GIN index on custom_attributes (JSONB queries)

    Constraints:
        - CHECK sku length between 6-20 characters
        - CHECK sku matches alphanumeric+hyphen pattern

    Example:
        ```python
        # Create Echeveria product
        lola = Product(
            family_id=1,
            sku="ECHEV-LOLA-001",
            common_name="Echeveria 'Lola'",
            scientific_name="Echeveria lilacina × Echeveria derenbergii",
            description="Compact rosette succulent",
            custom_attributes={
                "color": "blue-gray",
                "growth_rate": "slow"
            }
        )

        # Query by family
        echeverias = session.query(Product).filter_by(family_id=1).all()

        # JSONB query
        green_products = session.query(Product).filter(
            Product.custom_attributes["color"].astext == "green"
        ).all()
        ```
    """

    __tablename__ = "products"

    # Primary key
    product_id = Column(
        "id",  # Database column name is "id" (per ERD)
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Primary key (auto-increment)",
    )

    # Foreign key to product_families (CASCADE delete)
    family_id = Column(
        Integer,
        ForeignKey("product_families.family_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Foreign key to product_families (CASCADE delete)",
    )

    # Unique SKU field (6-20 chars, alphanumeric+hyphen, uppercase)
    sku = Column(
        String(20),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique Stock Keeping Unit (6-20 chars, alphanumeric+hyphen, uppercase)",
    )

    # Product identification fields
    common_name = Column(
        String(200),
        nullable=False,
        comment="Human-readable product name (e.g., Echeveria 'Lola')",
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

    # JSONB flexible metadata
    custom_attributes = Column(
        JSONB,
        nullable=True,
        default=lambda: {},
        server_default="{}",
        comment="Flexible metadata (color, variegation, growth_rate, etc.)",
    )

    # NO timestamps (per ERD lines 88-96)

    # Relationships

    # Many-to-one: Product → ProductFamily
    family: Mapped["ProductFamily"] = relationship(
        "ProductFamily",
        back_populates="products",
        doc="Family this product belongs to",
    )

    # One-to-many: Product → StockBatch (COMMENT OUT - DB007 not ready)
    # NOTE: Uncomment after DB007 (StockBatch) is complete
    # stock_batches: Mapped[list["StockBatch"]] = relationship(
    #     "StockBatch",
    #     back_populates="product",
    #     foreign_keys="StockBatch.product_id",
    #     doc="List of stock batches for this product"
    # )

    # One-to-many: Product → Classification (DB026 COMPLETE)
    classifications: Mapped[list["Classification"]] = relationship(
        "Classification",
        back_populates="product",
        foreign_keys="Classification.product_id",
        doc="List of ML classifications for this product",
    )

    # One-to-many: Product → DensityParameter
    density_parameters: Mapped[list["DensityParameter"]] = relationship(
        "DensityParameter",
        back_populates="product",
        foreign_keys="DensityParameter.product_id",
        doc="List of density parameters for this product",
    )

    # One-to-many: Product → ProductSampleImage (COMMENT OUT - DB020 not ready)
    # NOTE: Uncomment after DB020 (ProductSampleImage) is complete
    # product_sample_images: Mapped[list["ProductSampleImage"]] = relationship(
    #     "ProductSampleImage",
    #     back_populates="product",
    #     foreign_keys="ProductSampleImage.product_id",
    #     doc="List of sample images for this product"
    # )

    # One-to-many: Product → StorageLocationConfig (COMMENT OUT - DB006 not ready)
    # NOTE: Uncomment after DB006 (StorageLocationConfig) is complete
    # storage_location_configs: Mapped[list["StorageLocationConfig"]] = relationship(
    #     "StorageLocationConfig",
    #     back_populates="product",
    #     foreign_keys="StorageLocationConfig.product_id",
    #     doc="List of storage location configurations for this product"
    # )

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "LENGTH(sku) >= 6 AND LENGTH(sku) <= 20",
            name="ck_product_sku_length",
        ),
        CheckConstraint(
            "sku ~ '^[A-Z0-9-]+$'",
            name="ck_product_sku_format",
        ),
        {"comment": "Products - LEAF taxonomy (Category → Family → Product). NO seed data."},
    )

    @validates("sku")
    def validate_sku(self, key: str, value: str | None) -> str | None:
        """Validate and normalize SKU field.

        Rules:
            - Length: 6-20 characters
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
            >>> product.sku = "echev-lola-001"
            >>> product.sku
            "ECHEV-LOLA-001"

            >>> product.sku = "ECHEV"  # Too short
            ValueError: SKU must be 6-20 characters (got: 5)

            >>> product.sku = "ECHEV_001"  # Invalid character
            ValueError: SKU must contain only alphanumeric characters and hyphens
        """
        if value is None:
            raise ValueError("SKU cannot be None")

        # Auto-convert to uppercase
        value = value.upper()

        # Validate length
        if len(value) < 6 or len(value) > 20:
            raise ValueError(f"SKU must be 6-20 characters (got: {len(value)})")

        # Validate characters (alphanumeric + hyphen only)
        if not all(c.isalnum() or c == "-" for c in value):
            raise ValueError("SKU must contain only alphanumeric characters and hyphens")

        return value

    def __init__(self, **kwargs: Any) -> None:
        """Initialize Product with default custom_attributes."""
        if "custom_attributes" not in kwargs or kwargs.get("custom_attributes") is None:
            kwargs["custom_attributes"] = {}
        super().__init__(**kwargs)

    @validates("custom_attributes")
    def validate_custom_attributes(self, key: str, value: dict[str, Any] | None) -> dict[str, Any]:
        """Validate custom_attributes JSONB field.

        Ensures custom_attributes is always a dict (never None).

        Args:
            key: Field name ("custom_attributes")
            value: Custom attributes dict

        Returns:
            Validated custom attributes dict (empty dict if None)

        Examples:
            >>> product.custom_attributes = None
            >>> product.custom_attributes
            {}

            >>> product.custom_attributes = {"color": "green"}
            >>> product.custom_attributes
            {"color": "green"}
        """
        if value is None:
            return {}
        return value

    def __repr__(self) -> str:
        """String representation for debugging.

        Returns:
            String with product_id, family_id, sku, and common_name

        Example:
            <Product(product_id=1, family_id=1, sku='ECHEV-LOLA-001', common_name='Echeveria Lola')>
        """
        return (
            f"<Product("
            f"product_id={self.product_id}, "
            f"family_id={self.family_id}, "
            f"sku='{self.sku}', "
            f"common_name='{self.common_name}'"
            f")>"
        )
