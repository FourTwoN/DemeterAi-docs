"""PackagingColor model - Packaging color catalog (NO seed data).

This module defines the PackagingColor SQLAlchemy model for the packaging catalog
foundation. Represents container colors with hex code values for UI rendering.

Architecture:
    Layer: Database / Models (Infrastructure Layer)
    Dependencies: SQLAlchemy 2.0, PostgreSQL 18
    Pattern: User-created catalog (NO seed data)

Design Decisions:
    - Simple catalog model with name/hex_code pattern
    - Name field: Unique, 3-50 chars (e.g., "Black", "Terracotta")
    - Hex code: Standard CSS hex format (#RRGGBB or #RGB)
    - NO seed data: Created by users/admins as needed
    - NO timestamps: Per ERD (lines 151-155)
    - INT PK: Simple auto-increment (id)

See:
    - Database ERD: ../../database/database.mmd (lines 151-155)
    - Database docs: ../../engineering_plan/database/README.md

Example:
    ```python
    # Create packaging colors
    black = PackagingColor(
        name="Black",
        hex_code="#000000"
    )

    terracotta = PackagingColor(
        name="Terracotta",
        hex_code="#E07855"
    )

    # Query by name
    color = session.query(PackagingColor).filter_by(name="Black").first()
    ```
"""

from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Column, Integer, String
from sqlalchemy.orm import Mapped, relationship, validates

from app.db.base import Base

# Forward declarations for type hints (avoids circular imports)
if TYPE_CHECKING:
    from app.models.packaging_catalog import PackagingCatalog


class PackagingColor(Base):
    """PackagingColor model representing container color categories.

    Simple catalog model for packaging color categories with hex code values
    for UI rendering. Part of the packaging catalog foundation along with
    PackagingType and PackagingMaterial.

    Key Features:
        - Simple catalog: name + hex_code pattern
        - NO seed data: User-created as needed
        - Name validation: Unique, 3-50 chars
        - Hex code validation: Standard CSS hex format (#RRGGBB or #RGB)
        - NO timestamps: Per ERD

    Attributes:
        id: Primary key (auto-increment)
        name: Unique color name (3-50 chars, unique)
        hex_code: CSS hex color code (7 chars, #RRGGBB format)

    Relationships:
        packaging_catalog_items: List of PackagingCatalog instances (one-to-many)

    Indexes:
        - B-tree index on name (unique constraint)

    Constraints:
        - CHECK name length between 3-50 characters
        - CHECK hex_code matches #RRGGBB pattern

    Example:
        ```python
        # Create black color
        black = PackagingColor(
            name="Black",
            hex_code="#000000"
        )

        # Create terracotta color
        terracotta = PackagingColor(
            name="Terracotta",
            hex_code="#E07855"
        )

        # Query
        color = session.query(PackagingColor).filter_by(name="Black").first()
        ```
    """

    __tablename__ = "packaging_colors"

    # Primary key
    id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Primary key (auto-increment)",
    )

    # Unique name field (3-50 chars)
    name = Column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique color name (3-50 chars, e.g., 'Black', 'Terracotta')",
    )

    # Hex code field (7 chars, #RRGGBB format)
    hex_code = Column(
        String(7),
        nullable=False,
        comment="CSS hex color code (#RRGGBB format, e.g., '#000000')",
    )

    # NO timestamps (per ERD lines 151-155)

    # Relationships

    # One-to-many: PackagingColor → PackagingCatalog
    packaging_catalog_items: Mapped[list["PackagingCatalog"]] = relationship(
        "PackagingCatalog",
        back_populates="packaging_color",
        foreign_keys="PackagingCatalog.packaging_color_id",
        doc="List of packaging catalog items of this color",
    )

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "LENGTH(name) >= 3 AND LENGTH(name) <= 50",
            name="ck_packaging_color_name_length",
        ),
        CheckConstraint(
            "hex_code ~ '^#[0-9A-Fa-f]{6}$'",
            name="ck_packaging_color_hex_format",
        ),
        {"comment": "Packaging Colors - Container color catalog with hex codes. NO seed data."},
    )

    @validates("name")
    def validate_name(self, key: str, value: str | None) -> str | None:
        """Validate name field.

        Rules:
            - Length: 3-50 characters
            - Cannot be None or empty

        Args:
            key: Field name ("name")
            value: Name value to validate

        Returns:
            Validated name

        Raises:
            ValueError: If name is invalid

        Examples:
            >>> color.name = "Black"
            >>> color.name
            "Black"

            >>> color.name = "AB"  # Too short
            ValueError: Name must be 3-50 characters (got: 2)

            >>> color.name = ""  # Empty
            ValueError: Name cannot be empty
        """
        if value is None or not value.strip():
            raise ValueError("Name cannot be empty")

        value = value.strip()

        # Validate length
        if len(value) < 3 or len(value) > 50:
            raise ValueError(f"Name must be 3-50 characters (got: {len(value)})")

        return value

    @validates("hex_code")
    def validate_hex_code(self, key: str, value: str | None) -> str | None:
        """Validate hex_code field.

        Rules:
            - Format: #RRGGBB (7 chars total)
            - Must start with #
            - Must have 6 hex digits (0-9, A-F, a-f)
            - Auto-convert to uppercase

        Args:
            key: Field name ("hex_code")
            value: Hex code value to validate

        Returns:
            Validated hex code (uppercase)

        Raises:
            ValueError: If hex code is invalid

        Examples:
            >>> color.hex_code = "#000000"
            >>> color.hex_code
            "#000000"

            >>> color.hex_code = "#e07855"
            >>> color.hex_code
            "#E07855"

            >>> color.hex_code = "000000"  # Missing #
            ValueError: Hex code must start with # (e.g., '#000000')

            >>> color.hex_code = "#GGGGGG"  # Invalid hex
            ValueError: Hex code must contain 6 hex digits (0-9, A-F)

            >>> color.hex_code = "#000"  # Too short
            ValueError: Hex code must be 7 characters (#RRGGBB format)
        """
        if value is None:
            raise ValueError("Hex code cannot be None")

        value = value.strip().upper()

        # Validate length
        if len(value) != 7:
            raise ValueError("Hex code must be 7 characters (#RRGGBB format)")

        # Validate starts with #
        if not value.startswith("#"):
            raise ValueError("Hex code must start with # (e.g., '#000000')")

        # Validate hex digits
        hex_part = value[1:]
        if not all(c in "0123456789ABCDEF" for c in hex_part):
            raise ValueError("Hex code must contain 6 hex digits (0-9, A-F)")

        return value

    def __repr__(self) -> str:
        """String representation for debugging.

        Returns:
            String with id, name, and hex_code

        Example:
            <PackagingColor(id=1, name='Black', hex_code='#000000')>
        """
        return f"<PackagingColor(id={self.id}, name='{self.name}', hex_code='{self.hex_code}')>"
