"""Warehouse repository for geospatial warehouse data access.

Provides CRUD operations for warehouse entities with PostGIS support.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.warehouse import Warehouse
from app.repositories.base import AsyncRepository


class WarehouseRepository(AsyncRepository[Warehouse]):
    """Repository for warehouse database operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with database session."""
        super().__init__(Warehouse, session)
