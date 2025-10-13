"""StorageArea model - Level 2 of the 4-tier geospatial location hierarchy.

This module defines the StorageArea SQLAlchemy model with PostGIS geometry support.
Storage areas subdivide warehouses into logical zones (North, South, East, West, Center)
and are the second level in the location hierarchy.

Architecture:
    Layer: Database / Models (Infrastructure Layer)
    Dependencies: SQLAlchemy 2.0, GeoAlchemy2, PostGIS 3.3+
    Hierarchy: Warehouse (1) → StorageArea (N) → StorageLocation (N) → StorageBin (N)

Design Decisions:
    - PostGIS POLYGON for precise area boundary definition
    - GENERATED column for area_m2 (auto-calculated from geometry)
    - Database trigger for centroid auto-update (not Python property)
    - Database trigger for spatial containment validation (area MUST be within warehouse)
    - SRID 4326 (WGS84) for GPS compatibility
    - Code validation: WAREHOUSE-AREA pattern (e.g., "INV01-NORTH")
    - Self-referential FK: parent_area_id allows hierarchical subdivision

See:
    - Database ERD: ../../database/database.mmd
    - Database docs: ../../engineering_plan/database/README.md
    - Task specification: ../../backlog/03_kanban/01_ready/DB002-storage-areas-model.md

Example:
    ```python
    from shapely.geometry import Polygon
    from geoalchemy2.shape import from_shape

    # Create storage area within warehouse
    coords = [
        (-70.648000, -33.448900),  # SW corner
        (-70.647500, -33.448900),  # SE corner
        (-70.647500, -33.449400),  # NE corner
        (-70.648000, -33.449400),  # NW corner
        (-70.648000, -33.448900)   # Close polygon
    ]
    polygon = Polygon(coords)

    area = StorageArea(
        warehouse_id=1,
        code="INV01-NORTH",
        name="North Wing",
        position="N",
        geojson_coordinates=from_shape(polygon, srid=4326)
    )
    ```
"""

import enum
import re
from typing import TYPE_CHECKING

from geoalchemy2 import Geometry
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from sqlalchemy.sql import func

from app.db.base import Base

# Forward declarations for type hints (avoids circular imports)
if TYPE_CHECKING:
    from app.models.storage_location import StorageLocation
    from app.models.warehouse import Warehouse


class PositionEnum(str, enum.Enum):
    """Cardinal position classification for storage areas within warehouses.

    Attributes:
        NORTH: North zone of warehouse
        SOUTH: South zone of warehouse
        EAST: East zone of warehouse
        WEST: West zone of warehouse
        CENTER: Central zone of warehouse
    """

    NORTH = "N"
    SOUTH = "S"
    EAST = "E"
    WEST = "W"
    CENTER = "C"


class StorageArea(Base):
    """StorageArea model representing logical zones within warehouses.

    Level 2 of the 4-tier geospatial hierarchy. Storage areas subdivide
    warehouses into manageable zones, which contain storage locations,
    which contain storage bins.

    PostGIS Features:
        - geojson_coordinates: Full boundary polygon (SRID 4326)
        - centroid: Auto-calculated center point (trigger-based)
        - area_m2: Auto-calculated area in square meters (GENERATED column)
        - Spatial containment: Area MUST be within parent warehouse (trigger-enforced)

    Attributes:
        storage_area_id: Primary key (auto-increment)
        warehouse_id: Foreign key to parent warehouse (CASCADE delete)
        parent_area_id: Self-referential FK for hierarchical areas (NULLABLE)
        code: Unique area code (format: WAREHOUSE-AREA, uppercase)
        name: Human-readable area name
        position: Cardinal direction (N/S/E/W/C, optional)
        geojson_coordinates: PostGIS POLYGON boundary (SRID 4326)
        centroid: Auto-calculated center point (SRID 4326)
        area_m2: Auto-calculated area in square meters (GENERATED column)
        active: Soft delete flag (default True)
        created_at: Record creation timestamp (auto)
        updated_at: Last update timestamp (auto)

    Relationships:
        warehouse: Parent warehouse (many-to-one)
        parent_area: Parent storage area (many-to-one, self-referential)
        child_areas: Child storage areas (one-to-many, self-referential)
        storage_locations: List of StorageLocation instances within this area

    Indexes:
        - GIST index on geojson_coordinates (spatial queries)
        - GIST index on centroid (distance calculations)
        - B-tree index on code (unique lookups)
        - B-tree index on warehouse_id (foreign key queries)
        - B-tree index on parent_area_id (hierarchical queries)
        - B-tree index on position (filtering)
        - B-tree index on active (soft delete queries)

    Example:
        ```python
        # Find storage area by GPS point
        from geoalchemy2.functions import ST_Contains
        from sqlalchemy import func

        point = func.ST_SetSRID(func.ST_MakePoint(-70.6475, -33.4495), 4326)
        result = await session.execute(
            select(StorageArea).where(
                ST_Contains(StorageArea.geojson_coordinates, point)
            )
        )
        area = result.scalar_one_or_none()
        ```
    """

    __tablename__ = "storage_areas"

    # Primary key
    storage_area_id = Column(
        Integer, primary_key=True, autoincrement=True, comment="Primary key (auto-increment)"
    )

    # Foreign key to parent warehouse (CASCADE delete)
    warehouse_id = Column(
        Integer,
        ForeignKey("warehouses.warehouse_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Parent warehouse (CASCADE delete)",
    )

    # Self-referential FK for hierarchical areas (NULLABLE)
    parent_area_id = Column(
        Integer,
        ForeignKey("storage_areas.storage_area_id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Parent storage area for hierarchical subdivision (NULLABLE)",
    )

    # Identification (unique code required for consistency)
    code = Column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique area code (format: WAREHOUSE-AREA, uppercase, 2-50 chars)",
    )

    name = Column(String(200), nullable=False, comment="Human-readable area name")

    # Cardinal position classification (optional)
    position = Column(
        Enum(PositionEnum, name="position_enum"),
        nullable=True,
        index=True,
        comment="Cardinal direction: N, S, E, W, C (optional)",
    )

    # PostGIS geometry columns (SRID 4326 = WGS84 for GPS compatibility)
    geojson_coordinates: Mapped[str] = mapped_column(
        Geometry("POLYGON", srid=4326),
        nullable=False,
        comment="Storage area boundary polygon (WGS84 coordinates)",
    )

    centroid: Mapped[str | None] = mapped_column(
        Geometry("POINT", srid=4326),
        nullable=True,
        comment="Auto-calculated center point (database trigger)",
    )

    # Area calculation (GENERATED column - auto-calculated by PostgreSQL)
    # NOTE: This column is added via Alembic migration, not here
    # PostgreSQL syntax: GENERATED ALWAYS AS (ST_Area(geojson_coordinates::geography)) STORED
    area_m2 = Column(
        Numeric(10, 2),
        nullable=True,
        comment="Auto-calculated area in m² (GENERATED column)",
    )

    # Status (soft delete pattern)
    active = Column(
        Boolean, default=True, nullable=False, index=True, comment="Active status (soft delete)"
    )

    # Timestamps (automatic tracking)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
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

    # Many-to-one: StorageArea → Warehouse
    warehouse: Mapped["Warehouse"] = relationship(
        "Warehouse",
        back_populates="storage_areas",
        doc="Parent warehouse containing this storage area",
    )

    # Self-referential: Parent/Child areas
    parent_area: Mapped["StorageArea | None"] = relationship(
        "StorageArea",
        remote_side=[storage_area_id],
        back_populates="child_areas",
        foreign_keys=[parent_area_id],
        doc="Parent storage area (for hierarchical subdivision)",
    )

    child_areas: Mapped[list["StorageArea"]] = relationship(
        "StorageArea",
        back_populates="parent_area",
        cascade="all, delete-orphan",
        doc="Child storage areas (hierarchical subdivision)",
    )

    # One-to-many: StorageArea → StorageLocation (DB003 complete)
    storage_locations: Mapped[list["StorageLocation"]] = relationship(
        "StorageLocation",
        back_populates="storage_area",
        cascade="all, delete-orphan",
        lazy="selectin",
        doc="List of storage locations within this area",
    )

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "LENGTH(code) >= 2 AND LENGTH(code) <= 50",
            name="ck_storage_area_code_length",
        ),
        {"comment": "Storage Areas - Level 2 of 4-tier geospatial location hierarchy"},
    )

    @validates("code")
    def validate_code(self, key: str, value: str) -> str:
        """Validate storage area code format.

        Rules:
            1. Required (not empty)
            2. Must be uppercase
            3. Format: WAREHOUSE-AREA (e.g., "INV01-NORTH")
            4. Pattern: ^[A-Z0-9_-]+-[A-Z0-9_-]+$
            5. Length between 2 and 50 characters

        Args:
            key: Column name (always 'code')
            value: Storage area code to validate

        Returns:
            Validated storage area code (uppercase)

        Raises:
            ValueError: If validation fails with specific error message

        Example:
            ```python
            area.code = "INV01-NORTH"  # Valid
            area.code = "inv01-north"  # Raises ValueError (must be uppercase)
            area.code = "INV01"        # Raises ValueError (must have WAREHOUSE-AREA pattern)
            area.code = "A"            # Raises ValueError (too short)
            ```
        """
        if not value or not value.strip():
            raise ValueError("Storage area code cannot be empty")

        code = value.strip().upper()

        # Check WAREHOUSE-AREA pattern
        if not re.match(r"^[A-Z0-9_-]+-[A-Z0-9_-]+$", code):
            raise ValueError(
                f"Storage area code must match pattern WAREHOUSE-AREA (e.g., 'INV01-NORTH', got: {code})"
            )

        if len(code) < 2 or len(code) > 50:
            raise ValueError(f"Storage area code must be 2-50 characters (got {len(code)} chars)")

        return code

    def __repr__(self) -> str:
        """String representation for debugging.

        Returns:
            String with storage_area_id, code, name, and warehouse_id

        Example:
            <StorageArea(storage_area_id=1, code='INV01-NORTH', name='North Wing', warehouse_id=1)>
        """
        return (
            f"<StorageArea("
            f"storage_area_id={self.storage_area_id}, "
            f"code='{self.code}', "
            f"name='{self.name}', "
            f"warehouse_id={self.warehouse_id}"
            f")>"
        )
