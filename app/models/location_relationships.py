"""LocationRelationship model - Hierarchical and adjacency relationships.

Represents parent-child (contains) and sibling (adjacent_to) relationships
between storage locations in the 4-level geospatial hierarchy.
"""

import enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, relationship
from sqlalchemy.sql import func

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.storage_location import StorageLocation


class RelationshipTypeEnum(str, enum.Enum):
    CONTAINS = "contains"
    ADJACENT_TO = "adjacent_to"


class LocationRelationship(Base):
    __tablename__ = "location_relationships"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="Primary key")

    parent_location_id = Column(
        Integer,
        ForeignKey("storage_locations.location_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Parent location ID",
    )

    child_location_id = Column(
        Integer,
        ForeignKey("storage_locations.location_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Child location ID",
    )

    relationship_type = Column(
        Enum(RelationshipTypeEnum),
        nullable=False,
        comment="Relationship type: contains or adjacent_to",
    )

    created_at = Column(
        DateTime, server_default=func.now(), nullable=False, comment="Creation timestamp"
    )
    updated_at = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Last update timestamp",
    )

    parent_location: Mapped["StorageLocation"] = relationship(
        "StorageLocation",
        foreign_keys=[parent_location_id],
        primaryjoin="LocationRelationship.parent_location_id == StorageLocation.location_id",
    )

    child_location: Mapped["StorageLocation"] = relationship(
        "StorageLocation",
        foreign_keys=[child_location_id],
        primaryjoin="LocationRelationship.child_location_id == StorageLocation.location_id",
    )

    __table_args__ = (
        UniqueConstraint("parent_location_id", "child_location_id", name="uq_location_pair"),
        CheckConstraint("parent_location_id != child_location_id", name="ck_no_self_reference"),
        {"comment": "Hierarchical and adjacency relationships between storage locations"},
    )
