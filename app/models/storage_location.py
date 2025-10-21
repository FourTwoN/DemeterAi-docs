"""StorageLocation model - Level 3 of the 4-tier geospatial location hierarchy.

This module defines the StorageLocation SQLAlchemy model with PostGIS POINT geometry.
Storage locations are the "photo unit" where ML processing happens - one photo = one location.
This is the CRITICAL LEVEL for ML pipeline processing.

Architecture:
    Layer: Database / Models (Infrastructure Layer)
    Dependencies: SQLAlchemy 2.0, GeoAlchemy2, PostGIS 3.3+
    Hierarchy: Warehouse (1) → StorageArea (N) → StorageLocation (N) → StorageBin (N)

Design Decisions:
    - PostGIS POINT for single GPS coordinate (photo capture location)
    - QR code for physical identification via mobile app
    - position_metadata JSONB for flexible camera/lighting data
    - photo_session_id FK for circular reference to latest photo (nullable, SET NULL)
    - GENERATED column for area_m2 (always 0 for POINT geometry)
    - Database trigger for centroid auto-update (centroid = coordinates for POINT)
    - Database trigger for spatial containment (POINT must be within StorageArea POLYGON)
    - SRID 4326 (WGS84) for GPS compatibility
    - Code validation: WAREHOUSE-AREA-LOCATION pattern (e.g., "INV01-NORTH-LOC-001")

See:
    - Database ERD: ../../database/database.mmd (lines 33-47)
    - Database docs: ../../engineering_plan/database/README.md
    - Task specification: ../../backlog/03_kanban/02_in-progress/DB003-storage-locations-model.md

Example:
    ```python
    from geoalchemy2.functions import ST_SetSRID, ST_MakePoint

    # Create storage location within storage area
    point = ST_SetSRID(ST_MakePoint(-70.647500, -33.449150), 4326)

    location = StorageLocation(
        storage_area_id=1,
        code="INV01-NORTH-LOC-001",
        name="North Wing Location 1",
        qr_code="LOC12345-A",
        coordinates=point,
        position_metadata={
            "camera_angle": "45deg",
            "camera_height_m": 2.5,
            "lighting": "natural"
        }
    )
    ```
"""

import re
from datetime import datetime
from typing import TYPE_CHECKING

from geoalchemy2 import Geometry
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from sqlalchemy.sql import func, text

from app.db.base import Base

# Forward declarations for type hints (avoids circular imports)
if TYPE_CHECKING:
    from app.models.photo_processing_session import PhotoProcessingSession
    from app.models.product_sample_image import ProductSampleImage
    from app.models.storage_area import StorageArea
    from app.models.storage_bin import StorageBin
    from app.models.storage_location_config import StorageLocationConfig


class StorageLocation(Base):
    """StorageLocation model representing photo units within storage areas.

    Level 3 of the 4-tier geospatial hierarchy. Storage locations are the
    "photo unit" where ML processing happens. Each location has a QR code
    for physical tracking and contains multiple storage bins.

    PostGIS Features:
        - coordinates: Single GPS point where photo is captured (SRID 4326)
        - centroid: Auto-calculated (equals coordinates for POINT geometry)
        - area_m2: Auto-calculated (always 0 for POINT geometry, GENERATED column)
        - Spatial containment: POINT MUST be within parent StorageArea POLYGON

    QR Code Tracking:
        - Physical QR code label on location marker
        - Mobile app scans QR code to jump to location
        - Format: Uppercase alphanumeric + optional hyphen/underscore
        - Length: 8-20 characters
        - Example: "LOC12345-A", "QR-LOC-001"

    Attributes:
        location_id: Primary key (auto-increment)
        storage_area_id: Foreign key to parent storage area (CASCADE delete)
        photo_session_id: FK to latest photo processing session (nullable, SET NULL)
        code: Unique location code (format: WAREHOUSE-AREA-LOCATION, uppercase)
        qr_code: Physical QR code label (unique, 8-20 chars)
        name: Human-readable location name
        description: Optional detailed description
        coordinates: PostGIS POINT - single GPS coordinate (SRID 4326)
        centroid: Auto-calculated center point (equals coordinates for POINT)
        area_m2: Auto-calculated area (always 0 for POINT, GENERATED column)
        position_metadata: JSONB with camera angle, height, lighting conditions
        active: Soft delete flag (default True)
        created_at: Record creation timestamp (auto)
        updated_at: Last update timestamp (auto)

    Relationships:
        storage_area: Parent storage area (many-to-one)
        latest_photo_session: Latest photo processing session (many-to-one, nullable)
        storage_bins: List of StorageBin instances within this location (one-to-many)
        photo_processing_sessions: All photo sessions for this location (one-to-many)

    Indexes:
        - GIST index on coordinates (spatial queries)
        - GIST index on centroid (distance calculations)
        - B-tree index on code (unique lookups)
        - B-tree index on qr_code (unique lookups, mobile app scanning)
        - B-tree index on storage_area_id (foreign key queries)
        - B-tree index on photo_session_id (latest photo queries)
        - B-tree index on active (soft delete queries)

    Example:
        ```python
        # Find storage location by QR code scan
        result = await session.execute(
            select(StorageLocation).where(
                StorageLocation.qr_code == "LOC12345-A"
            )
        )
        location = result.scalar_one_or_none()

        # Find locations within storage area (ST_Contains)
        from geoalchemy2.functions import ST_Contains

        area_geom = area.geojson_coordinates
        result = await session.execute(
            select(StorageLocation).where(
                ST_Contains(area_geom, StorageLocation.coordinates)
            )
        )
        locations = result.scalars().all()
        ```
    """

    __tablename__ = "storage_locations"

    # Primary key
    location_id = Column(
        Integer, primary_key=True, autoincrement=True, comment="Primary key (auto-increment)"
    )

    # Foreign key to parent storage area (CASCADE delete)
    storage_area_id = Column(
        Integer,
        ForeignKey("storage_areas.storage_area_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Parent storage area (CASCADE delete)",
    )

    # Foreign key to latest photo processing session (nullable, SET NULL on delete)
    # NOTE: This creates a circular reference with photo_processing_sessions
    # photo_processing_sessions.storage_location_id → storage_locations.location_id
    # storage_locations.photo_session_id → photo_processing_sessions.id
    # TODO: Uncomment use_alter=True once migration is updated to include the circular FK
    photo_session_id = Column(
        Integer,
        # NOTE: FK commented out because migration doesn't include circular reference constraint
        # ForeignKey(
        #     "photo_processing_sessions.id",
        #     ondelete="SET NULL",
        #     use_alter=True,
        #     name="fk_storage_location_photo_session",
        # ),
        nullable=True,
        index=True,
        comment="Latest photo processing session for this location (nullable, SET NULL on delete)",
    )

    # Identification (unique code required for consistency)
    code = Column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique location code (format: WAREHOUSE-AREA-LOCATION, uppercase, 2-50 chars)",
    )

    # QR code for physical tracking (unique, indexed for fast mobile app lookups)
    qr_code = Column(
        String(20),
        unique=True,
        nullable=False,
        index=True,
        comment="Physical QR code label (alphanumeric + optional hyphen/underscore, 8-20 chars, uppercase)",
    )

    name = Column(String(200), nullable=False, comment="Human-readable location name")

    description = Column(Text, nullable=True, comment="Optional detailed description")

    # PostGIS geometry columns (SRID 4326 = WGS84 for GPS compatibility)
    # CRITICAL: Using POINT geometry (not POLYGON) for single GPS coordinate
    coordinates: Mapped[str] = mapped_column(
        Geometry("POINT", srid=4326, spatial_index=False),
        nullable=False,
        comment="GPS coordinate where photo is taken (POINT geometry, WGS84)",
    )

    centroid: Mapped[str | None] = mapped_column(
        Geometry("POINT", srid=4326, spatial_index=False),
        nullable=True,
        comment="Auto-calculated center point (equals coordinates for POINT geometry)",
    )

    # Area calculation (GENERATED column - always 0 for POINT geometry)
    # NOTE: This column is added via Alembic migration, not here
    # PostgreSQL syntax: GENERATED ALWAYS AS (0.0) STORED
    area_m2 = Column(
        Numeric(10, 2),
        nullable=True,
        comment="Auto-calculated area in m² (always 0 for POINT geometry, GENERATED column)",
    )

    # Position metadata (JSONB for flexible camera/lighting data)
    position_metadata = Column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
        comment="Camera angle, height, lighting conditions (flexible JSONB structure)",
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
        DateTime(timezone=True), onupdate=func.now(), nullable=True, comment="Last update timestamp"
    )

    # Relationships

    # Many-to-one: StorageLocation → StorageArea
    storage_area: Mapped["StorageArea"] = relationship(
        "StorageArea",
        back_populates="storage_locations",
        foreign_keys=[storage_area_id],
        doc="Parent storage area containing this location",
    )

    # Many-to-one: StorageLocation → PhotoProcessingSession (latest photo, nullable)
    # TODO: Uncomment once circular FK is added to migration
    # latest_photo_session: Mapped["PhotoProcessingSession | None"] = relationship(
    #     "PhotoProcessingSession",
    #     foreign_keys=[photo_session_id],
    #     back_populates="storage_locations_latest",
    #     doc="Latest photo processing session for this location (nullable)",
    # )

    # One-to-many: StorageLocation → StorageBin (DB004 complete)
    storage_bins: Mapped[list["StorageBin"]] = relationship(
        "StorageBin",
        back_populates="storage_location",
        cascade="all, delete-orphan",
        lazy="selectin",
        doc="List of storage bins within this location",
    )

    # One-to-many: StorageLocation → PhotoProcessingSession (all photos for this location)
    photo_processing_sessions: Mapped[list["PhotoProcessingSession"]] = relationship(
        "PhotoProcessingSession",
        back_populates="storage_location",
        foreign_keys="PhotoProcessingSession.storage_location_id",
        cascade="all, delete-orphan",
        doc="All photo processing sessions for this location",
    )

    # One-to-many: StorageLocation → ProductSampleImage
    product_sample_images: Mapped[list["ProductSampleImage"]] = relationship(
        "ProductSampleImage",
        back_populates="storage_location",
        foreign_keys="ProductSampleImage.storage_location_id",
        doc="Product sample images captured at this location",
    )

    # One-to-many: StorageLocation → StorageLocationConfig
    storage_location_configs: Mapped[list["StorageLocationConfig"]] = relationship(
        "StorageLocationConfig",
        back_populates="storage_location",
        foreign_keys="StorageLocationConfig.storage_location_id",
        cascade="all, delete-orphan",
        doc="Configuration entries for this location",
    )

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "LENGTH(code) >= 2 AND LENGTH(code) <= 50", name="ck_storage_location_code_length"
        ),
        CheckConstraint(
            "LENGTH(qr_code) >= 8 AND LENGTH(qr_code) <= 20",
            name="ck_storage_location_qr_code_length",
        ),
        {
            "comment": "Storage Locations - Level 3 of 4-tier geospatial location hierarchy (photo unit)"
        },
    )

    @validates("code")
    def validate_code(self, key: str, value: str) -> str:
        """Validate storage location code format.

        Rules:
            1. Required (not empty)
            2. Must be uppercase
            3. Format: WAREHOUSE-AREA-LOCATION (e.g., "INV01-NORTH-LOC-001")
            4. Pattern: ^[A-Z0-9_-]+-[A-Z0-9_-]+-[A-Z0-9_-]+$
            5. Length between 2 and 50 characters

        Args:
            key: Column name (always 'code')
            value: Storage location code to validate

        Returns:
            Validated storage location code (uppercase)

        Raises:
            ValueError: If validation fails with specific error message

        Example:
            ```python
            location.code = "INV01-NORTH-LOC-001"  # Valid
            location.code = "inv01-north-loc-001"  # Raises ValueError (must be uppercase)
            location.code = "INV01-NORTH"          # Raises ValueError (must have 3 parts)
            location.code = "A"                    # Raises ValueError (too short)
            ```
        """
        if not value or not value.strip():
            raise ValueError("Storage location code cannot be empty")

        code = value.strip().upper()

        # Check WAREHOUSE-AREA-LOCATION pattern (3 parts separated by hyphens)
        if not re.match(r"^[A-Z0-9_-]+-[A-Z0-9_-]+-[A-Z0-9_-]+$", code):
            raise ValueError(
                f"Storage location code must match pattern WAREHOUSE-AREA-LOCATION "
                f"(e.g., 'INV01-NORTH-LOC-001', got: {code})"
            )

        if len(code) < 2 or len(code) > 50:
            raise ValueError(
                f"Storage location code must be 2-50 characters (got {len(code)} chars)"
            )

        return code

    @validates("qr_code")
    def validate_qr_code(self, key: str, value: str) -> str:
        """Validate QR code format.

        Rules:
            1. Required (not empty)
            2. Alphanumeric with optional hyphen (-) and underscore (_)
            3. Length between 8 and 20 characters
            4. Auto-converted to uppercase

        Args:
            key: Column name (always 'qr_code')
            value: QR code to validate

        Returns:
            Validated QR code (uppercase)

        Raises:
            ValueError: If validation fails with specific error message

        Example:
            ```python
            location.qr_code = "LOC12345-A"   # Valid
            location.qr_code = "loc12345-a"   # Valid (auto-converted to uppercase)
            location.qr_code = "LOC_TEST_01"  # Valid
            location.qr_code = "SHORT"        # Raises ValueError (too short, <8 chars)
            location.qr_code = "LOC@TEST"     # Raises ValueError (invalid character @)
            location.qr_code = "TOOLONGQRCODE123456789"  # Raises ValueError (too long, >20 chars)
            ```
        """
        if not value or not value.strip():
            raise ValueError("QR code cannot be empty")

        code = value.strip().upper()

        # Check alphanumeric with optional - and _
        if not re.match(r"^[A-Z0-9_-]{8,20}$", code):
            raise ValueError(
                f"QR code must be 8-20 chars, uppercase alphanumeric with optional "
                f"hyphen (-) or underscore (_) (got: {value})"
            )

        return code

    def __repr__(self) -> str:
        """String representation for debugging.

        Returns:
            String with location_id, code, qr_code, name, and storage_area_id

        Example:
            <StorageLocation(location_id=1, code='INV01-NORTH-LOC-001', qr_code='LOC12345-A',
             name='North Wing Location 1', storage_area_id=1)>
        """
        return (
            f"<StorageLocation("
            f"location_id={self.location_id}, "
            f"code='{self.code}', "
            f"qr_code='{self.qr_code}', "
            f"name='{self.name}', "
            f"storage_area_id={self.storage_area_id}"
            f")>"
        )
