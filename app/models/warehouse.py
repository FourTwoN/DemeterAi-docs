"""Warehouse model - Root level of the 4-tier geospatial location hierarchy.

This module defines the Warehouse SQLAlchemy model with PostGIS geometry support.
Warehouses represent physical cultivation facilities (greenhouses, shadehouses,
tunnels, open fields) and are the top-level container in the location hierarchy.

Architecture:
    Layer: Database / Models (Infrastructure Layer)
    Dependencies: SQLAlchemy 2.0, GeoAlchemy2, PostGIS 3.3+
    Hierarchy: Warehouse (1) → StorageArea (N) → StorageLocation (N) → StorageBin (N)

Design Decisions:
    - PostGIS POLYGON for precise boundary definition (not just centroid)
    - GENERATED column for area_m2 (auto-calculated from geometry)
    - Database trigger for centroid auto-update (not Python property)
    - SRID 4326 (WGS84) for GPS compatibility
    - Code validation: uppercase alphanumeric, 2-20 characters

See:
    - Database ERD: ../../database/database.mmd (lines 8-19)
    - Database docs: ../../engineering_plan/database/README.md
    - Task specification: ../../backlog/03_kanban/02_in-progress/DB001-warehouses-model.md

Example:
    ```python
    from shapely.geometry import Polygon
    from geoalchemy2.shape import from_shape

    # Create warehouse with geometry
    coords = [
        (-70.648300, -33.448900),  # SW
        (-70.647300, -33.448900),  # SE
        (-70.647300, -33.449900),  # NE
        (-70.648300, -33.449900),  # NW
        (-70.648300, -33.448900)   # Close polygon
    ]
    polygon = Polygon(coords)

    warehouse = Warehouse(
        code="GH-001",
        name="Main Greenhouse",
        warehouse_type="greenhouse",
        geojson_coordinates=from_shape(polygon, srid=4326)
    )
    ```
"""

import enum
import re
from datetime import datetime

# Forward declaration for type hints (avoids circular imports)
from typing import TYPE_CHECKING

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, Enum, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from sqlalchemy.sql import func

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.storage_area import StorageArea


class WarehouseTypeEnum(str, enum.Enum):
    """Warehouse facility types for agricultural cultivation.

    Attributes:
        GREENHOUSE: Enclosed glass/plastic structure with climate control
        SHADEHOUSE: Covered with shade cloth, open sides
        OPEN_FIELD: Outdoor cultivation area without cover
        TUNNEL: Low tunnel / hoop house structure
    """

    GREENHOUSE = "greenhouse"
    SHADEHOUSE = "shadehouse"
    OPEN_FIELD = "open_field"
    TUNNEL = "tunnel"


class Warehouse(Base):
    """Warehouse model representing physical cultivation facilities.

    The root level of the 4-tier geospatial hierarchy. Warehouses contain
    storage areas, which contain storage locations, which contain storage bins.

    PostGIS Features:
        - geojson_coordinates: Full boundary polygon (SRID 4326)
        - centroid: Auto-calculated center point (trigger-based)
        - area_m2: Auto-calculated area in square meters (GENERATED column)

    Attributes:
        warehouse_id: Primary key (auto-increment)
        code: Unique warehouse code (uppercase alphanumeric, 2-20 chars)
        name: Human-readable warehouse name
        warehouse_type: Facility type (greenhouse, shadehouse, open_field, tunnel)
        geojson_coordinates: PostGIS POLYGON boundary (SRID 4326)
        centroid: Auto-calculated center point (SRID 4326)
        area_m2: Auto-calculated area in square meters (GENERATED column)
        active: Soft delete flag (default True)
        created_at: Record creation timestamp (auto)
        updated_at: Last update timestamp (auto)

    Relationships:
        storage_areas: List of StorageArea instances within this warehouse

    Indexes:
        - GIST index on geojson_coordinates (spatial queries)
        - GIST index on centroid (distance calculations)
        - B-tree index on code (unique lookups)
        - B-tree index on warehouse_type (filtering)
        - B-tree index on active (soft delete queries)

    Example:
        ```python
        # Find warehouses within 1km of GPS point
        from geoalchemy2.functions import ST_DWithin
        from sqlalchemy import cast, func
        from geoalchemy2.types import Geography

        point = func.ST_SetSRID(func.ST_MakePoint(-70.6475, -33.4495), 4326)
        result = await session.execute(
            select(Warehouse).where(
                ST_DWithin(
                    Warehouse.centroid.cast(Geography),
                    point.cast(Geography),
                    1000  # 1km radius in meters
                )
            )
        )
        warehouses = result.scalars().all()
        ```
    """

    __tablename__ = "warehouses"

    # Primary key
    warehouse_id = Column(
        Integer, primary_key=True, autoincrement=True, comment="Primary key (auto-increment)"
    )

    # Identification (unique code required for consistency across systems)
    code = Column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique warehouse code (uppercase alphanumeric, 2-20 chars)",
    )

    name = Column(String(200), nullable=False, comment="Human-readable warehouse name")

    # Type classification (enum for data integrity)
    warehouse_type = Column(
        Enum(
            WarehouseTypeEnum,
            name="warehouse_type_enum",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        index=True,
        comment="Facility type: greenhouse, shadehouse, open_field, tunnel",
    )

    # PostGIS geometry columns (SRID 4326 = WGS84 for GPS compatibility)
    geojson_coordinates: Mapped[str] = mapped_column(
        Geometry("POLYGON", srid=4326),
        nullable=False,
        comment="Warehouse boundary polygon (WGS84 coordinates)",
    )

    centroid: Mapped[str | None] = mapped_column(
        Geometry("POINT", srid=4326),
        nullable=True,
        insert_default=None,
        comment="Auto-calculated center point (database trigger)",
    )

    # Area calculation (GENERATED column - auto-calculated by PostgreSQL)
    # NOTE: This column is added via Alembic migration, not here
    # PostgreSQL syntax: GENERATED ALWAYS AS (ST_Area(geojson_coordinates::geography)) STORED
    area_m2: Mapped[float | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        insert_default=None,
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
    storage_areas: Mapped[list["StorageArea"]] = relationship(
        "StorageArea",
        back_populates="warehouse",
        cascade="all, delete-orphan",
        lazy="selectin",
        doc="List of storage areas within this warehouse",
    )

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "LENGTH(code) >= 2 AND LENGTH(code) <= 20",
            name="ck_warehouse_code_length",
        ),
        {"comment": "Warehouses - Root level of 4-tier geospatial location hierarchy"},
    )

    @validates("code")
    def validate_code(self, key: str, value: str) -> str:
        """Validate warehouse code format.

        Rules:
            1. Required (not empty)
            2. Must be uppercase
            3. Alphanumeric with optional - and _ characters
            4. Length between 2 and 20 characters

        Args:
            key: Column name (always 'code')
            value: Warehouse code to validate

        Returns:
            Validated warehouse code (uppercase)

        Raises:
            ValueError: If validation fails with specific error message

        Example:
            ```python
            warehouse.code = "GH-001"  # Valid
            warehouse.code = "gh-001"  # Raises ValueError (must be uppercase)
            warehouse.code = "GH@001"  # Raises ValueError (invalid character)
            warehouse.code = "A"       # Raises ValueError (too short)
            ```
        """
        if not value:
            raise ValueError("Warehouse code is required")

        if not value.isupper():
            raise ValueError(f"Warehouse code must be uppercase (got: {value})")

        # Check alphanumeric with optional - and _
        if not re.match(r"^[A-Z0-9_-]+$", value):
            raise ValueError(
                f"Warehouse code must be alphanumeric with optional - or _ (got: {value})"
            )

        if not (2 <= len(value) <= 20):
            raise ValueError(f"Warehouse code must be 2-20 characters (got {len(value)} chars)")

        return value

    @validates("warehouse_type")
    def validate_warehouse_type(self, key: str, value: str) -> str:
        """Validate warehouse_type is a valid enum value.

        Rules:
            1. Must be one of: greenhouse, shadehouse, open_field, tunnel

        Args:
            key: Column name (always 'warehouse_type')
            value: Warehouse type to validate

        Returns:
            Validated warehouse type

        Raises:
            ValueError: If validation fails

        Example:
            ```python
            warehouse.warehouse_type = "greenhouse"  # Valid
            warehouse.warehouse_type = "factory"     # Raises ValueError
            ```
        """
        if not value:
            raise ValueError("Warehouse type is required")

        valid_types = {e.value for e in WarehouseTypeEnum}
        if value not in valid_types:
            raise ValueError(f"Warehouse type must be one of {valid_types} (got: {value})")

        return value

    @validates("name")
    def validate_name(self, key: str, value: str) -> str:
        """Validate name field is not null or empty.

        Rules:
            1. Cannot be None
            2. Cannot be empty string

        Args:
            key: Column name (always 'name')
            value: Name to validate

        Returns:
            Validated name

        Raises:
            ValueError: If validation fails
        """
        if value is None:
            raise ValueError("Warehouse name is required (cannot be None)")
        if not value or not value.strip():
            raise ValueError("Warehouse name cannot be empty")
        return value

    @validates("geojson_coordinates")
    def validate_geojson_coordinates(self, key: str, value: object) -> object:
        """Validate geojson_coordinates field is not null.

        Rules:
            1. Cannot be None

        Args:
            key: Column name (always 'geojson_coordinates')
            value: Geometry to validate

        Returns:
            Validated geometry

        Raises:
            ValueError: If validation fails
        """
        if value is None:
            raise ValueError("Warehouse geojson_coordinates is required (cannot be None)")
        return value

    def __repr__(self) -> str:
        """String representation for debugging.

        Returns:
            String with warehouse_id, code, and name

        Example:
            <Warehouse(warehouse_id=1, code='GH-001', name='Main Greenhouse')>
        """
        return (
            f"<Warehouse(warehouse_id={self.warehouse_id}, code='{self.code}', name='{self.name}')>"
        )
