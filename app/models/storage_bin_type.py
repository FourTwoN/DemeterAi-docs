"""StorageBinType model - Reference/Catalog table defining container types.

This module defines the StorageBinType SQLAlchemy model for container type catalog.
Storage bin types define the physical characteristics of containers (plug trays, boxes,
segments, pots) used throughout the system.

Architecture:
    Layer: Database / Models (Infrastructure Layer)
    Dependencies: SQLAlchemy 2.0, PostgreSQL 18 enums
    Pattern: Reference/Catalog table with seed data

Design Decisions:
    - Category enum: 5 types (plug, seedling_tray, box, segment, pot)
    - Nullable dimensions: Not all types have fixed size (ML-detected segments)
    - Grid flag: True for plug trays (rows × columns capacity)
    - CHECK constraint: Grid types must have rows AND columns NOT NULL
    - Seed data: 6-10 common types preloaded in migration
    - Code validation: uppercase, alphanumeric + underscores, 3-50 chars

See:
    - Database ERD: ../../database/database.mmd (lines 59-74)
    - Database docs: ../../engineering_plan/database/README.md
    - Task specification: ../../backlog/03_kanban/02_in-progress/DB005-storage-bin-types-model.md

Example:
    ```python
    # Create plug tray type
    plug_tray = StorageBinType(
        code="PLUG_TRAY_288",
        name="288-Cell Plug Tray",
        category=BinCategoryEnum.PLUG,
        rows=18,
        columns=16,
        capacity=288,
        is_grid=True,
        length_cm=54.0,
        width_cm=27.5,
        height_cm=5.5,
        description="Standard 288-cell plug tray (18 rows × 16 columns)"
    )

    # Create segment type (no fixed dimensions)
    segment = StorageBinType(
        code="SEGMENT_STANDARD",
        name="Individual Segment",
        category=BinCategoryEnum.SEGMENT,
        is_grid=False,
        description="Individual segment detected by ML (no fixed dimensions)"
    )
    ```
"""

import enum
import re
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, relationship, validates
from sqlalchemy.sql import func

from app.db.base import Base

# Forward declarations for type hints (avoids circular imports)
if TYPE_CHECKING:
    from app.models.density_parameter import DensityParameter
    from app.models.storage_bin import StorageBin


class BinCategoryEnum(str, enum.Enum):
    """Category classification for storage bin types.

    Attributes:
        PLUG: High-density plug trays (100-288 cells)
        SEEDLING_TRAY: Seedling trays (20-72 cells)
        BOX: Transport/storage boxes (no fixed grid)
        SEGMENT: Individual segments (no grid)
        POT: Individual pots (no grid)
    """

    PLUG = "plug"
    SEEDLING_TRAY = "seedling_tray"
    BOX = "box"
    SEGMENT = "segment"
    POT = "pot"


class StorageBinType(Base):
    """StorageBinType model representing container type catalog.

    Reference/catalog table defining physical container types used throughout
    the system. Defines capacity, dimensions, and grid structure for different
    container types (plug trays, boxes, segments, pots).

    Key Features:
        - Category enum (5 types): plug, seedling_tray, box, segment, pot
        - Nullable dimensions: Not all types have fixed size
        - Grid flag: True for plug trays with rows × columns grid
        - CHECK constraint: Grid types must have rows AND columns NOT NULL
        - Seed data: 6-10 common types preloaded in migration

    Attributes:
        id: Primary key (auto-increment)
        code: Unique bin type code (uppercase, alphanumeric + underscores, 3-50 chars)
        name: Human-readable type name
        category: Category enum (plug, seedling_tray, box, segment, pot)
        description: Optional detailed description
        rows: Number of rows (nullable, required for grid types)
        columns: Number of columns (nullable, required for grid types)
        capacity: Total capacity (nullable, may differ from rows×columns)
        length_cm: Container length in cm (nullable)
        width_cm: Container width in cm (nullable)
        height_cm: Container height in cm (nullable)
        is_grid: True for plug trays with grid structure (default FALSE)
        created_at: Record creation timestamp (auto)
        updated_at: Last update timestamp (auto)

    Relationships:
        storage_bins: List of StorageBin instances using this type (one-to-many)
        density_parameters: List of DensityParameter instances for this type (one-to-many)

    Indexes:
        - B-tree index on code (unique lookups)
        - B-tree index on category (filtering)

    CHECK Constraint:
        - If is_grid=TRUE, then rows AND columns must be NOT NULL

    Example:
        ```python
        # Grid type (plug tray)
        plug = StorageBinType(
            code="PLUG_TRAY_288",
            name="288-Cell Plug Tray",
            category=BinCategoryEnum.PLUG,
            rows=18,
            columns=16,
            capacity=288,
            is_grid=True
        )

        # Non-grid type (segment)
        segment = StorageBinType(
            code="SEGMENT_STANDARD",
            name="Individual Segment",
            category=BinCategoryEnum.SEGMENT,
            is_grid=False
        )
        ```
    """

    __tablename__ = "storage_bin_types"

    # Primary key
    bin_type_id = Column(
        "bin_type_id",
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
        comment="Unique bin type code (uppercase, alphanumeric + underscores, 3-50 chars)",
    )

    name = Column(
        String(200),
        nullable=False,
        comment="Human-readable type name",
    )

    # Category enum
    category = Column(
        Enum(
            BinCategoryEnum,
            name="bin_category_enum",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        index=True,
        comment="Category: plug, seedling_tray, box, segment, pot",
    )

    description = Column(
        Text,
        nullable=True,
        comment="Optional detailed description",
    )

    # Grid structure (for plug trays and seedling trays)
    rows = Column(
        Integer,
        nullable=True,
        comment="Number of rows (nullable, required for grid types)",
    )

    columns = Column(
        Integer,
        nullable=True,
        comment="Number of columns (nullable, required for grid types)",
    )

    capacity = Column(
        Integer,
        nullable=True,
        comment="Total capacity (nullable, may differ from rows×columns)",
    )

    # Dimensions (nullable - not all types have fixed dimensions)
    length_cm = Column(
        Numeric(6, 2),
        nullable=True,
        comment="Container length in cm (nullable)",
    )

    width_cm = Column(
        Numeric(6, 2),
        nullable=True,
        comment="Container width in cm (nullable)",
    )

    height_cm = Column(
        Numeric(6, 2),
        nullable=True,
        comment="Container height in cm (nullable)",
    )

    # Grid flag (TRUE for plug trays with rows×columns structure)
    is_grid = Column(
        Boolean,
        nullable=False,
        server_default="false",
        comment="True for plug trays with grid structure (default FALSE)",
    )

    # Timestamps (automatic tracking)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=datetime.utcnow,
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

    # One-to-many: StorageBinType → StorageBin
    storage_bins: Mapped[list["StorageBin"]] = relationship(
        "StorageBin",
        back_populates="storage_bin_type",
        foreign_keys="StorageBin.storage_bin_type_id",
        doc="List of storage bins using this type",
    )

    # One-to-many: StorageBinType → DensityParameter
    density_parameters: Mapped[list["DensityParameter"]] = relationship(
        "DensityParameter",
        back_populates="storage_bin_type",
        foreign_keys="DensityParameter.storage_bin_type_id",
        cascade="all, delete-orphan",
        doc="List of density parameters for this bin type",
    )

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "LENGTH(code) >= 3 AND LENGTH(code) <= 50",
            name="ck_storage_bin_type_code_length",
        ),
        CheckConstraint(
            "(is_grid = false) OR (is_grid = true AND rows IS NOT NULL AND columns IS NOT NULL)",
            name="ck_storage_bin_type_grid_requires_rows_columns",
        ),
        {"comment": "Storage Bin Types - Reference/catalog table defining container types"},
    )

    @validates("code")
    def validate_code(self, key: str, value: str) -> str:
        """Validate storage bin type code format.

        Rules:
            1. Required (not empty)
            2. Must be uppercase
            3. Alphanumeric + underscores only (NO hyphens)
            4. Length between 3 and 50 characters

        Args:
            key: Column name (always 'code')
            value: Storage bin type code to validate

        Returns:
            Validated storage bin type code (uppercase)

        Raises:
            ValueError: If validation fails with specific error message

        Example:
            ```python
            bin_type.code = "PLUG_TRAY_288"     # Valid
            bin_type.code = "plug_tray_288"     # Auto-uppercases to "PLUG_TRAY_288"
            bin_type.code = "PLUG-TRAY-288"     # Raises ValueError (hyphens not allowed)
            bin_type.code = "PT"                # Raises ValueError (too short)
            bin_type.code = ""                  # Raises ValueError (empty)
            ```
        """
        if not value or not value.strip():
            raise ValueError("Storage bin type code cannot be empty")

        code = value.strip().upper()

        # Check alphanumeric + underscores only (NO hyphens)
        if not re.match(r"^[A-Z0-9_]+$", code):
            raise ValueError(
                f"Storage bin type code must be alphanumeric + underscores only "
                f"(NO hyphens, got: {code})"
            )

        if len(code) < 3 or len(code) > 50:
            raise ValueError(
                f"Storage bin type code must be 3-50 characters (got {len(code)} chars)"
            )

        return code

    def __repr__(self) -> str:
        """String representation for debugging.

        Returns:
            String with id, code, name, category, and is_grid

        Example:
            <StorageBinType(bin_type_id=1, code='PLUG_TRAY_288', name='288-Cell Plug Tray',
             category='plug', is_grid=True)>
        """
        return (
            f"<StorageBinType("
            f"bin_type_id={self.bin_type_id}, "
            f"code='{self.code}', "
            f"name='{self.name}', "
            f"category='{self.category.value if self.category else None}', "
            f"is_grid={self.is_grid}"
            f")>"
        )
