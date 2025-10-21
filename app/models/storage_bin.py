"""StorageBin model - Level 4 (leaf level) of the 4-tier geospatial location hierarchy.

This module defines the StorageBin SQLAlchemy model for physical plant containers.
Storage bins are the FINAL LEVEL (leaf) of the hierarchy - where stock physically exists.
This is the SIMPLEST MODEL YET with NO PostGIS complexity!

Architecture:
    Layer: Database / Models (Infrastructure Layer)
    Dependencies: SQLAlchemy 2.0, PostgreSQL 18 JSONB
    Hierarchy: Warehouse (1) → StorageArea (N) → StorageLocation (N) → StorageBin (N) [LEAF]

Design Decisions:
    - NO PostGIS geometry (bins inherit location from parent StorageLocation)
    - JSONB position_metadata stores ML segmentation output (mask, bbox, confidence)
    - Status enum: active, maintenance, retired (retired is terminal state)
    - Code validation: WAREHOUSE-AREA-LOCATION-BIN pattern (4 parts)
    - CASCADE delete from storage_location (intentional - bins deleted with parent)
    - RESTRICT delete from storage_bin_type (safety - cannot delete type if bins exist)
    - NO GIST indexes (no spatial queries)
    - ONLY B-tree indexes + GIN index on JSONB

See:
    - Database ERD: ../../database/database.mmd (lines 48-58)
    - Database docs: ../../engineering_plan/database/README.md
    - Task specification: ../../backlog/03_kanban/02_in-progress/DB004-storage-bins-model.md

Example:
    ```python
    # Create storage bin within location
    bin = StorageBin(
        storage_location_id=1,
        storage_bin_type_id=2,
        code="INV01-NORTH-A1-SEG001",
        label="Segment 1",
        status="active",
        position_metadata={
            "segmentation_mask": [[100, 200], [300, 200], [300, 400], [100, 400]],
            "bbox": {"x": 100, "y": 200, "width": 200, "height": 200},
            "confidence": 0.92,
            "ml_model_version": "yolov11-seg-v2.3",
            "detected_at": "2025-10-09T14:30:00Z",
            "container_type": "segmento"
        }
    )
    ```
"""

import enum
import re
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, relationship, validates
from sqlalchemy.sql import func

from app.db.base import Base

# Forward declarations for type hints (avoids circular imports)
if TYPE_CHECKING:
    from app.models.stock_batch import StockBatch
    from app.models.stock_movement import StockMovement
    from app.models.storage_bin_type import StorageBinType
    from app.models.storage_location import StorageLocation


class StorageBinStatusEnum(str, enum.Enum):
    """Status classification for storage bins.

    Attributes:
        ACTIVE: Bin is operational and accepting stock
        MAINTENANCE: Bin is temporarily unavailable (cleaning, repair)
        RETIRED: Bin is permanently removed (TERMINAL STATE - no transitions out)
    """

    ACTIVE = "active"
    MAINTENANCE = "maintenance"
    RETIRED = "retired"


class StorageBin(Base):
    """StorageBin model representing physical plant containers.

    Level 4 (LEAF) of the 4-tier geospatial hierarchy. Storage bins are the
    physical containers where stock batches live (segmentos, cajones, boxes, plugs).
    This is WHERE PLANTS PHYSICALLY EXIST.

    ML Integration:
        - ML segmentation pipeline creates bins from photo analysis
        - position_metadata stores full ML output (mask, bbox, confidence)
        - container_type identifies segmento vs cajon vs box
        - confidence tracks segmentation quality (threshold: 0.7+)

    Attributes:
        storage_bin_id: Primary key (auto-increment)
        storage_location_id: Foreign key to parent storage location (CASCADE delete)
        storage_bin_type_id: Foreign key to bin type catalog (RESTRICT delete, NULLABLE)
        code: Unique bin code (format: WAREHOUSE-AREA-LOCATION-BIN, 4 parts, uppercase)
        label: Human-readable bin name (optional)
        description: Optional detailed description
        position_metadata: JSONB with ML segmentation output (mask, bbox, confidence)
        status: Status enum (active/maintenance/retired)
        created_at: Record creation timestamp (auto)
        updated_at: Last update timestamp (auto)

    Relationships:
        storage_location: Parent storage location (many-to-one)
        storage_bin_type: Bin type definition (many-to-one, optional)
        stock_batches: List of StockBatch instances in this bin (one-to-many)

    Indexes:
        - B-tree index on code (unique lookups)
        - B-tree index on storage_location_id (FK queries)
        - B-tree index on storage_bin_type_id (FK queries)
        - B-tree index on status (filtering)
        - GIN index on position_metadata (JSONB queries)

    JSONB position_metadata Schema:
        ```python
        {
            "segmentation_mask": [[x1, y1], [x2, y2], ...],  # Polygon vertices (px)
            "bbox": {"x": 100, "y": 200, "width": 300, "height": 150},
            "confidence": 0.92,  # Segmentation quality (0.0-1.0)
            "ml_model_version": "yolov11-seg-v2.3",
            "detected_at": "2025-10-09T14:30:00Z",
            "container_type": "segmento"  # or "cajon", "box", "plug"
        }
        ```

    Status Transitions:
        - active → maintenance (for cleaning/repair)
        - maintenance → active (back in service)
        - active → retired (permanently removed)
        - retired → (TERMINAL STATE - NO transitions out)

    Example:
        ```python
        # Find bins with low confidence segmentation
        low_confidence_bins = await session.execute(
            select(StorageBin).where(
                StorageBin.position_metadata['confidence'].as_float() < 0.7
            )
        )

        # Find all segmentos (vs cajones)
        segmentos = await session.execute(
            select(StorageBin).where(
                StorageBin.position_metadata['container_type'].as_string() == 'segmento'
            )
        )
        ```
    """

    __tablename__ = "storage_bins"

    # Primary key
    storage_bin_id = Column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="Primary key (auto-increment)",
    )

    # Foreign key to parent storage location (CASCADE delete)
    storage_location_id = Column(
        Integer,
        ForeignKey("storage_locations.location_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Parent storage location (CASCADE delete)",
    )

    # Foreign key to storage bin type (RESTRICT delete, NULLABLE)
    # NOTE: RESTRICT prevents deleting bin type if bins exist (safety)
    storage_bin_type_id = Column(
        Integer,
        ForeignKey("storage_bin_types.bin_type_id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
        comment="Bin type definition (RESTRICT delete, optional)",
    )

    # Identification (unique code required for consistency)
    code = Column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique bin code (format: WAREHOUSE-AREA-LOCATION-BIN, 4 parts, 2-100 chars)",
    )

    label = Column(
        String(100),
        nullable=True,
        comment="Human-readable bin name (optional)",
    )

    description = Column(
        Text,
        nullable=True,
        comment="Optional detailed description",
    )

    # Position metadata (JSONB for ML segmentation output)
    # NO schema validation - flexible structure for ML pipeline evolution
    position_metadata = Column(
        JSONB,
        nullable=True,
        comment="ML segmentation output: mask, bbox, confidence, ml_model_version, container_type",
    )

    # Status enum (active/maintenance/retired)
    status = Column(
        Enum(
            StorageBinStatusEnum,
            name="storage_bin_status_enum",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        server_default="active",
        index=True,
        comment="Status enum: active, maintenance, retired (terminal state)",
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

    # Many-to-one: StorageBin → StorageLocation
    storage_location: Mapped["StorageLocation"] = relationship(
        "StorageLocation",
        back_populates="storage_bins",
        foreign_keys=[storage_location_id],
        doc="Parent storage location containing this bin",
    )

    # Many-to-one: StorageBin → StorageBinType (optional)
    storage_bin_type: Mapped["StorageBinType | None"] = relationship(
        "StorageBinType",
        back_populates="storage_bins",
        foreign_keys=[storage_bin_type_id],
        doc="Bin type definition (capacity, dimensions)",
    )

    # One-to-many: StorageBin → StockBatch
    stock_batches: Mapped[list["StockBatch"]] = relationship(
        "StockBatch",
        back_populates="current_storage_bin",
        foreign_keys="StockBatch.current_storage_bin_id",
        cascade="all, delete-orphan",
        doc="List of stock batches in this bin",
    )

    # One-to-many: StorageBin → StockMovement (as source bin)
    stock_movements_source: Mapped[list["StockMovement"]] = relationship(
        "StockMovement",
        back_populates="source_bin",
        foreign_keys="StockMovement.source_bin_id",
        doc="Stock movements where this bin is the source",
    )

    # One-to-many: StorageBin → StockMovement (as destination bin)
    stock_movements_destination: Mapped[list["StockMovement"]] = relationship(
        "StockMovement",
        back_populates="destination_bin",
        foreign_keys="StockMovement.destination_bin_id",
        doc="Stock movements where this bin is the destination",
    )

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "LENGTH(code) >= 2 AND LENGTH(code) <= 100",
            name="ck_storage_bin_code_length",
        ),
        {
            "comment": "Storage Bins - Level 4 (LEAF) of 4-tier geospatial location hierarchy (physical container)"
        },
    )

    @validates("code")
    def validate_code(self, key: str, value: str) -> str:
        """Validate storage bin code format.

        Rules:
            1. Required (not empty)
            2. Must be uppercase
            3. Format: WAREHOUSE-AREA-LOCATION-BIN (4 parts, e.g., "INV01-NORTH-A1-SEG001")
            4. Pattern: ^[A-Z0-9_-]+-[A-Z0-9_-]+-[A-Z0-9_-]+-[A-Z0-9_-]+$
            5. Length between 2 and 100 characters

        Args:
            key: Column name (always 'code')
            value: Storage bin code to validate

        Returns:
            Validated storage bin code (uppercase)

        Raises:
            ValueError: If validation fails with specific error message

        Example:
            ```python
            bin.code = "INV01-NORTH-A1-SEG001"  # Valid (4 parts)
            bin.code = "inv01-north-a1-seg001"  # Raises ValueError (must be uppercase)
            bin.code = "INV01-NORTH-A1"         # Raises ValueError (must have 4 parts)
            bin.code = "A"                      # Raises ValueError (too short)
            ```
        """
        if not value or not value.strip():
            raise ValueError("Storage bin code cannot be empty")

        code = value.strip().upper()

        # Check WAREHOUSE-AREA-LOCATION-BIN pattern (4 parts separated by hyphens)
        if not re.match(r"^[A-Z0-9_-]+-[A-Z0-9_-]+-[A-Z0-9_-]+-[A-Z0-9_-]+$", code):
            raise ValueError(
                f"Storage bin code must match pattern WAREHOUSE-AREA-LOCATION-BIN "
                f"(4 parts, e.g., 'INV01-NORTH-A1-SEG001', got: {code})"
            )

        if len(code) < 2 or len(code) > 100:
            raise ValueError(f"Storage bin code must be 2-100 characters (got {len(code)} chars)")

        return code

    @validates("status")
    def validate_status_transition(self, key: str, new_status: str) -> str:
        """Validate status transitions.

        Rules:
            - active → maintenance (allowed)
            - maintenance → active (allowed)
            - active → retired (allowed)
            - retired → (TERMINAL STATE - NO transitions out)

        Args:
            key: Column name (always 'status')
            new_status: New status value

        Returns:
            Validated status value

        Raises:
            ValueError: If transition from retired to any other status

        Example:
            ```python
            bin.status = "active"
            bin.status = "maintenance"  # Valid
            bin.status = "active"       # Valid
            bin.status = "retired"      # Valid
            bin.status = "active"       # Raises ValueError (retired is terminal)
            ```
        """
        # Allow initial status setting (self.status not set yet)
        if not hasattr(self, "status") or self.status is None:
            return new_status

        # Retired is terminal state - no transitions out
        if (
            self.status == StorageBinStatusEnum.RETIRED
            and new_status != StorageBinStatusEnum.RETIRED
        ):
            raise ValueError(
                "Cannot transition from 'retired' status - retired bins cannot be reactivated"
            )

        return new_status

    def __repr__(self) -> str:
        """String representation for debugging.

        Returns:
            String with storage_bin_id, code, label, status, and storage_location_id

        Example:
            <StorageBin(storage_bin_id=1, code='INV01-NORTH-A1-SEG001', label='Segment 1',
             status='active', storage_location_id=1)>
        """
        return (
            f"<StorageBin("
            f"storage_bin_id={self.storage_bin_id}, "
            f"code='{self.code}', "
            f"label='{self.label}', "
            f"status='{self.status.value if self.status else None}', "
            f"storage_location_id={self.storage_location_id}"
            f")>"
        )
