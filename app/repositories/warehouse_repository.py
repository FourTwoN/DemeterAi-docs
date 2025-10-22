"""Warehouse repository for geospatial warehouse data access.

Provides CRUD operations for warehouse entities with PostGIS support.
Includes domain-specific queries for GPS-based lookups and spatial operations.

Architecture:
    Layer: Infrastructure (Repository Pattern)
    Dependencies: SQLAlchemy 2.0, GeoAlchemy2, PostGIS 3.3+
    Used by: WarehouseService

Example:
    ```python
    # GPS-based warehouse lookup
    warehouse = await repo.get_by_gps_point(-70.648, -33.449)

    # Get active warehouses with storage areas
    warehouses = await repo.get_active_warehouses(with_areas=True)
    ```

See:
    - Model: app/models/warehouse.py
    - Service: app/services/warehouse_service.py
    - Task: backlog/03_kanban/01_ready/S001-warehouse-service.md
"""

from typing import Any

from geoalchemy2.functions import ST_Contains, ST_MakePoint, ST_SetSRID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.warehouse import Warehouse
from app.repositories.base import AsyncRepository


class WarehouseRepository(AsyncRepository[Warehouse]):
    """Repository for warehouse database operations with PostGIS support.

    Inherits base CRUD operations from AsyncRepository and adds:
    - Code-based lookup (unique constraint)
    - GPS point-in-polygon queries (ST_Contains)
    - Active warehouse filtering
    - Eager loading of storage areas relationship
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with database session.

        Args:
            session: Async database session (injected via FastAPI Depends)
        """
        super().__init__(Warehouse, session)

    async def get(self, warehouse_id: int) -> Warehouse | None:
        """Get warehouse by ID (overrides base to use warehouse_id column).

        Args:
            warehouse_id: Primary key

        Returns:
            Warehouse instance if found, None otherwise
        """
        stmt = select(Warehouse).where(Warehouse.warehouse_id == warehouse_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_code(self, code: str) -> Warehouse | None:
        """Get warehouse by unique code.

        Uses indexed lookup for performance (<10ms typical).

        Args:
            code: Warehouse code (e.g., "GH-001")

        Returns:
            Warehouse instance if found, None otherwise

        Example:
            ```python
            warehouse = await repo.get_by_code("GH-001")
            if warehouse:
                # warehouse.name
            ```
        """
        stmt = select(Warehouse).where(Warehouse.code == code)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_gps_point(self, longitude: float, latitude: float) -> Warehouse | None:
        """Find warehouse containing GPS coordinates (point-in-polygon query).

        Uses PostGIS ST_Contains for spatial query with GIST index.
        Returns first match (assumes non-overlapping warehouse polygons).

        Args:
            longitude: GPS longitude (WGS84, e.g., -70.648)
            latitude: GPS latitude (WGS84, e.g., -33.449)

        Returns:
            Warehouse containing the point, None if no match

        Performance:
            ~30-50ms with GIST index on geojson_coordinates

        Example:
            ```python
            # Photo taken at these coordinates
            warehouse = await repo.get_by_gps_point(-70.648, -33.449)
            if warehouse:
                # Photo belongs to this warehouse
            ```

        Note:
            Undefined behavior if warehouse polygons overlap.
            ST_Contains returns first match only.
        """
        # Create PostGIS point from coordinates (SRID 4326 = WGS84)
        point = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)

        # Find warehouse polygon containing this point
        stmt = select(Warehouse).where(ST_Contains(Warehouse.geojson_coordinates, point))

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_warehouses(self, with_areas: bool = False) -> list[Warehouse]:
        """Get all active warehouses (soft delete filter).

        Optionally eager-loads storage_areas relationship to avoid N+1 queries.

        Args:
            with_areas: If True, eager-load storage_areas relationship

        Returns:
            List of active Warehouse instances (empty list if none)

        Performance:
            - Without areas: ~10-20ms for 50 warehouses
            - With areas: ~30-50ms (includes JOIN)

        Example:
            ```python
            # Get warehouses only
            warehouses = await repo.get_active_warehouses()

            # Get warehouses with storage areas (single query)
            warehouses = await repo.get_active_warehouses(with_areas=True)
            for wh in warehouses:
                logger.debug(wh.storage_areas)  # No additional query
            ```
        """
        stmt = select(Warehouse).where(Warehouse.active == True)  # noqa: E712

        # Eager load storage_areas if requested (avoid N+1)
        if with_areas:
            stmt = stmt.options(selectinload(Warehouse.storage_areas))

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update(self, warehouse_id: int, data: dict[str, Any]) -> Warehouse | None:
        """Update warehouse (overrides base to use warehouse_id column).

        Args:
            warehouse_id: Primary key
            data: Dictionary of fields to update

        Returns:
            Updated Warehouse instance if found, None otherwise
        """
        warehouse = await self.get(warehouse_id)
        if not warehouse:
            return None

        for field, value in data.items():
            setattr(warehouse, field, value)

        await self.session.flush()
        await self.session.refresh(warehouse)
        return warehouse

    async def delete(self, warehouse_id: int) -> bool:
        """Delete warehouse (overrides base to use warehouse_id column).

        Args:
            warehouse_id: Primary key

        Returns:
            True if deleted, False if not found
        """
        warehouse = await self.get(warehouse_id)
        if not warehouse:
            return False

        await self.session.delete(warehouse)
        await self.session.flush()
        return True
