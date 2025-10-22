"""LocationRelationship repository for hierarchical and adjacency relationships.

Provides CRUD operations for location relationships (contains/adjacent_to).
Includes domain-specific queries for parent-child and adjacency lookups.

Architecture:
    Layer: Infrastructure (Repository Pattern)
    Dependencies: SQLAlchemy 2.0
    Used by: LocationRelationshipService

Example:
    ```python
    # Get all children of a location
    children = await repo.get_children_by_parent(location_id=123)

    # Find adjacent locations
    adjacent = await repo.get_adjacent_locations(location_id=456)
    ```

See:
    - Model: app/models/location_relationships.py
    - Task: backlog/03_kanban/01_ready/S0XX-location-relationship-service.md
"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.location_relationships import LocationRelationship, RelationshipTypeEnum
from app.repositories.base import AsyncRepository


class LocationRelationshipRepository(AsyncRepository[LocationRelationship]):
    """Repository for location relationship database operations.

    Inherits base CRUD operations from AsyncRepository and adds:
    - Parent-child relationship queries (contains)
    - Adjacency relationship queries (adjacent_to)
    - Eager loading of parent/child locations
    - Relationship type filtering
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with database session.

        Args:
            session: Async database session (injected via FastAPI Depends)
        """
        super().__init__(LocationRelationship, session)

    async def get_children_by_parent(
        self, parent_location_id: int, relationship_type: RelationshipTypeEnum | None = None
    ) -> list[LocationRelationship]:
        """Get all child relationships for a parent location.

        Args:
            parent_location_id: Parent location ID
            relationship_type: Optional filter by relationship type
                             (defaults to all types)

        Returns:
            List of LocationRelationship instances (empty list if none)

        Example:
            ```python
            # Get all children (contains relationships)
            children = await repo.get_children_by_parent(
                parent_location_id=123,
                relationship_type=RelationshipTypeEnum.CONTAINS
            )
            ```
        """
        stmt = select(LocationRelationship).where(
            LocationRelationship.parent_location_id == parent_location_id
        )

        if relationship_type:
            stmt = stmt.where(LocationRelationship.relationship_type == relationship_type)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_parents_by_child(
        self, child_location_id: int, relationship_type: RelationshipTypeEnum | None = None
    ) -> list[LocationRelationship]:
        """Get all parent relationships for a child location.

        Args:
            child_location_id: Child location ID
            relationship_type: Optional filter by relationship type
                             (defaults to all types)

        Returns:
            List of LocationRelationship instances (empty list if none)

        Example:
            ```python
            # Find what contains this location
            parents = await repo.get_parents_by_child(
                child_location_id=456,
                relationship_type=RelationshipTypeEnum.CONTAINS
            )
            ```
        """
        stmt = select(LocationRelationship).where(
            LocationRelationship.child_location_id == child_location_id
        )

        if relationship_type:
            stmt = stmt.where(LocationRelationship.relationship_type == relationship_type)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_adjacent_locations(self, location_id: int) -> list[LocationRelationship]:
        """Get all adjacent locations (bidirectional adjacency query).

        Returns relationships where the location is either parent or child
        with relationship_type = 'adjacent_to'.

        Args:
            location_id: Location ID to find adjacent neighbors

        Returns:
            List of LocationRelationship instances with adjacent_to type

        Example:
            ```python
            # Find all adjacent storage bins
            adjacent = await repo.get_adjacent_locations(location_id=789)
            for rel in adjacent:
                if rel.parent_location_id == location_id:
                    neighbor = rel.child_location  # Adjacent neighbor
                else:
                    neighbor = rel.parent_location  # Adjacent neighbor
            ```

        Note:
            Adjacency is typically bidirectional, so query includes
            both parent and child positions.
        """
        stmt = select(LocationRelationship).where(
            (
                (LocationRelationship.parent_location_id == location_id)
                | (LocationRelationship.child_location_id == location_id)
            )
            & (LocationRelationship.relationship_type == RelationshipTypeEnum.ADJACENT_TO)
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_with_locations(self, relationship_id: int) -> LocationRelationship | None:
        """Get relationship with eager-loaded parent and child locations.

        Uses selectinload to avoid N+1 queries when accessing location details.

        Args:
            relationship_id: Primary key

        Returns:
            LocationRelationship with parent_location and child_location loaded,
            None if not found

        Example:
            ```python
            rel = await repo.get_with_locations(123)
            if rel:
                logger.debug(rel.parent_location.location_code)  # No additional query
                logger.debug(rel.child_location.location_code)   # No additional query
            ```
        """
        stmt = (
            select(LocationRelationship)
            .where(LocationRelationship.id == relationship_id)
            .options(
                selectinload(LocationRelationship.parent_location),
                selectinload(LocationRelationship.child_location),
            )
        )

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_relationship_by_pair(
        self,
        parent_location_id: int,
        child_location_id: int,
        relationship_type: RelationshipTypeEnum | None = None,
    ) -> LocationRelationship | None:
        """Get relationship by parent-child pair (unique constraint lookup).

        Uses unique constraint (parent_location_id, child_location_id) for
        indexed lookup.

        Args:
            parent_location_id: Parent location ID
            child_location_id: Child location ID
            relationship_type: Optional filter by relationship type

        Returns:
            LocationRelationship if found, None otherwise

        Example:
            ```python
            # Check if relationship already exists
            existing = await repo.get_relationship_by_pair(
                parent_location_id=123,
                child_location_id=456,
                relationship_type=RelationshipTypeEnum.CONTAINS
            )
            if existing:
                # Relationship already exists
            ```
        """
        stmt = select(LocationRelationship).where(
            (LocationRelationship.parent_location_id == parent_location_id)
            & (LocationRelationship.child_location_id == child_location_id)
        )

        if relationship_type:
            stmt = stmt.where(LocationRelationship.relationship_type == relationship_type)

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update(
        self, relationship_id: int, data: dict[str, Any]
    ) -> LocationRelationship | None:
        """Update location relationship (overrides base to use id column).

        Args:
            relationship_id: Primary key
            data: Dictionary of fields to update

        Returns:
            Updated LocationRelationship instance if found, None otherwise
        """
        relationship = await self.get(relationship_id)
        if not relationship:
            return None

        for field, value in data.items():
            setattr(relationship, field, value)

        await self.session.flush()
        await self.session.refresh(relationship)
        return relationship

    async def delete(self, relationship_id: int) -> bool:
        """Delete location relationship (overrides base to use id column).

        Args:
            relationship_id: Primary key

        Returns:
            True if deleted, False if not found
        """
        relationship = await self.get(relationship_id)
        if not relationship:
            return False

        await self.session.delete(relationship)
        await self.session.flush()
        return True
