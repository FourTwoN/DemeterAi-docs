"""PackagingMaterial model - Packaging material catalog (NO seed data).

This module defines the PackagingMaterial SQLAlchemy model for the packaging catalog
foundation. Represents container materials (plastic, terracotta, biodegradable, etc.).

Architecture:
    Layer: Database / Models (Infrastructure Layer)
    Dependencies: SQLAlchemy 2.0, PostgreSQL 18
    Pattern: User-created catalog (NO seed data)

Design Decisions:
    - Simple catalog model with code/name/description pattern
    - Code field: Unique, alphanumeric+hyphen, 3-50 chars, uppercase
    - NO seed data: Created by users/admins as needed
    - NO timestamps: Per ERD (lines 145-150)
    - INT PK: Simple auto-increment (id)

See:
    - Database ERD: ../../database/database.mmd (lines 145-150)
    - Database docs: ../../engineering_plan/database/README.md

Example:
    ```python
    # Create packaging material
    plastic = PackagingMaterial(
        code="PLASTIC",
        name="Plastic",
        description="Standard black plastic container"
    )

    terracotta = PackagingMaterial(
        code="TERRACOTTA",
        name="Terracotta",
        description="Clay pot for premium products"
    )

    # Query by code
    material = session.query(PackagingMaterial).filter_by(code="PLASTIC").first()
    ```
"""

from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Column, Integer, String, Text
from sqlalchemy.orm import Mapped, relationship, validates

from app.db.base import Base

# Forward declarations for type hints (avoids circular imports)
if TYPE_CHECKING:
    from app.models.packaging_catalog import PackagingCatalog


class PackagingMaterial(Base):
    """PackagingMaterial model representing container material categories.

    Simple catalog model for packaging material categories (plastic, terracotta, etc.).
    Part of the packaging catalog foundation along with PackagingType and
    PackagingColor.

    Key Features:
        - Simple catalog: code + name + description pattern
        - NO seed data: User-created as needed
        - Code validation: Uppercase, alphanumeric+hyphen, 3-50 chars
        - NO timestamps: Per ERD

    Attributes:
        id: Primary key (auto-increment)
        code: Unique material code (3-50 chars, alphanumeric+hyphen, uppercase)
        name: Human-readable material name (100 chars max, NOT NULL)
        description: Optional detailed description (text, NULLABLE)

    Relationships:
        packaging_catalog_items: List of PackagingCatalog instances (one-to-many)

    Indexes:
        - B-tree index on code (unique constraint)

    Constraints:
        - CHECK code length between 3-50 characters
        - CHECK code matches alphanumeric+hyphen pattern

    Example:
        ```python
        # Create plastic material
        plastic = PackagingMaterial(
            code="PLASTIC",
            name="Plastic",
            description="Standard black plastic container"
        )

        # Create terracotta material
        terracotta = PackagingMaterial(
            code="TERRACOTTA",
            name="Terracotta",
            description="Clay pot for premium products"
        )

        # Query
        material = session.query(PackagingMaterial).filter_by(code="PLASTIC").first()
        ```
    """

    __tablename__ = "packaging_materials"

    # Primary key
    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Primary key (auto-increment)",
    )

    # Unique code field (3-50 chars, alphanumeric+hyphen, uppercase)
    code = Column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique material code (3-50 chars, alphanumeric+hyphen, uppercase)",
    )

    # Material identification fields
    name = Column(
        String(100),
        nullable=False,
        comment="Human-readable material name (e.g., 'Plastic', 'Terracotta')",
    )

    description = Column(
        Text,
        nullable=True,
        comment="Optional detailed description",
    )

    # NO timestamps (per ERD lines 145-150)

    # Relationships

    # One-to-many: PackagingMaterial → PackagingCatalog
    packaging_catalog_items: Mapped[list["PackagingCatalog"]] = relationship(
        "PackagingCatalog",
        back_populates="packaging_material",
        foreign_keys="PackagingCatalog.packaging_material_id",
        doc="List of packaging catalog items of this material",
    )

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "LENGTH(code) >= 3 AND LENGTH(code) <= 50",
            name="ck_packaging_material_code_length",
        ),
        CheckConstraint(
            "code ~ '^[A-Z0-9_-]+$'",
            name="ck_packaging_material_code_format",
        ),
        {
            "comment": "Packaging Materials - Container material catalog (plastic, terracotta, biodegradable, etc.). NO seed data."
        },
    )

    @validates("code")
    def validate_code(self, key: str, value: str | None) -> str | None:
        """Validate and normalize code field.

        Rules:
            - Length: 3-50 characters
            - Characters: Alphanumeric + hyphen + underscore only
            - Auto-convert to uppercase

        Args:
            key: Field name ("code")
            value: Code value to validate

        Returns:
            Normalized code (uppercase)

        Raises:
            ValueError: If code is invalid

        Examples:
            >>> material.code = "plastic"
            >>> material.code
            "PLASTIC"

            >>> material.code = "bio_degradable"
            >>> material.code
            "BIO_DEGRADABLE"

            >>> material.code = "AB"  # Too short
            ValueError: Code must be 3-50 characters (got: 2)

            >>> material.code = "INVALID@CODE"  # Invalid character
            ValueError: Code must contain only alphanumeric characters, hyphens, and underscores
        """
        if value is None:
            raise ValueError("Code cannot be None")

        # Auto-convert to uppercase
        value = value.upper()

        # Validate length
        if len(value) < 3 or len(value) > 50:
            raise ValueError(f"Code must be 3-50 characters (got: {len(value)})")

        # Validate characters (alphanumeric + hyphen + underscore only)
        if not all(c.isalnum() or c in ("-", "_") for c in value):
            raise ValueError(
                "Code must contain only alphanumeric characters, hyphens, and underscores"
            )

        return value

    def __repr__(self) -> str:
        """String representation for debugging.

        Returns:
            String with id, code, and name

        Example:
            <PackagingMaterial(id=1, code='PLASTIC', name='Plastic')>
        """
        return f"<PackagingMaterial(id={self.id}, code='{self.code}', name='{self.name}')>"
