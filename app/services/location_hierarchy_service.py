"""Location Hierarchy Service (aggregator for S001-S005).

Orchestrates warehouse → area → location → bin hierarchy queries.
Critical for reporting and analytics dashboards.
"""

import logging
from typing import Any

from app.services.storage_area_service import StorageAreaService
from app.services.storage_bin_service import StorageBinService
from app.services.storage_location_service import StorageLocationService
from app.services.warehouse_service import WarehouseService

logger = logging.getLogger(__name__)


class LocationHierarchyService:
    """Aggregate service for full location hierarchy operations."""

    def __init__(
        self,
        warehouse_service: WarehouseService,
        area_service: StorageAreaService,
        location_service: StorageLocationService,
        bin_service: StorageBinService,
    ) -> None:
        self.warehouse_service = warehouse_service
        self.area_service = area_service
        self.location_service = location_service
        self.bin_service = bin_service

    async def get_full_hierarchy(self, warehouse_id: int) -> dict[str, Any]:
        """Get complete hierarchy: warehouse → areas → locations → bins."""
        logger.debug(f"Fetching full hierarchy for warehouse {warehouse_id}")
        warehouse = await self.warehouse_service.get_warehouse_by_id(warehouse_id)
        areas = await self.area_service.get_areas_by_warehouse(warehouse_id)
        logger.debug(f"Found {len(areas)} areas for warehouse {warehouse_id}")

        hierarchy: dict[str, Any] = {"warehouse": warehouse, "areas": []}

        for area in areas:
            locations = await self.location_service.get_locations_by_area(area.storage_area_id)
            area_data: dict[str, Any] = {"area": area, "locations": []}

            for loc in locations:
                bins = await self.bin_service.get_bins_by_location(loc.location_id)
                area_data["locations"].append({"location": loc, "bins": bins})

            hierarchy["areas"].append(area_data)

        return hierarchy

    async def lookup_gps_full_chain(
        self, longitude: float, latitude: float
    ) -> dict[str, Any] | None:
        """GPS → full chain (warehouse → area → location) for photo localization.

        Returns complete hierarchy including warehouse and storage area.

        Returns:
            dict with keys: warehouse, area, location, bins
            or None if location not found at GPS coordinates
        """
        logger.debug(f"GPS lookup: longitude={longitude}, latitude={latitude}")
        # Use StorageLocationService's GPS lookup (already does full chain)
        location = await self.location_service.get_location_by_gps(longitude, latitude)

        if not location:
            logger.debug(f"No location found at GPS coordinates ({longitude}, {latitude})")
            return None

        logger.debug(
            f"Found location {location.location_id} at GPS ({longitude}, {latitude})"
        )

        # Get parent storage area
        area = await self.area_service.get_storage_area_by_id(location.storage_area_id)

        # Get parent warehouse
        warehouse = None
        if area:
            warehouse = await self.warehouse_service.get_warehouse_by_id(area.warehouse_id)
            logger.debug(
                f"Full hierarchy: warehouse={warehouse.warehouse_id if warehouse else None}, area={area.storage_area_id}, location={location.location_id}"
            )

        # Get bins for this location
        bins = await self.bin_service.get_bins_by_location(location.location_id)

        return {"warehouse": warehouse, "area": area, "location": location, "bins": bins}

    async def validate_hierarchy(
        self,
        warehouse_id: int | None = None,
        area_id: int | None = None,
        location_id: int | None = None,
        bin_id: int | None = None,
    ) -> dict[str, Any]:
        """Validate that a location hierarchy is valid and consistent.

        Checks that:
        1. Each entity exists
        2. Parent-child relationships are correct
        3. IDs match across the hierarchy

        Args:
            warehouse_id: Optional warehouse ID
            area_id: Optional area ID
            location_id: Optional location ID
            bin_id: Optional bin ID

        Returns:
            dict with 'valid' (bool), 'errors' (list), and validated entities
        """
        errors: list[str] = []
        validated: dict[str, Any] = {}

        # Validate warehouse
        if warehouse_id:
            try:
                warehouse = await self.warehouse_service.get_warehouse_by_id(warehouse_id)
                validated["warehouse"] = warehouse
            except Exception as e:
                errors.append(f"Invalid warehouse_id {warehouse_id}: {str(e)}")

        # Validate area
        if area_id:
            try:
                area = await self.area_service.get_storage_area_by_id(area_id)
                validated["area"] = area

                # Check area belongs to warehouse if both provided
                if warehouse_id and area.warehouse_id != warehouse_id:
                    errors.append(
                        f"Area {area_id} belongs to warehouse {area.warehouse_id}, "
                        f"not warehouse {warehouse_id}"
                    )
            except Exception as e:
                errors.append(f"Invalid area_id {area_id}: {str(e)}")

        # Validate location
        if location_id:
            try:
                location = await self.location_service.get_storage_location_by_id(location_id)
                validated["location"] = location

                # Check location belongs to area if both provided
                if area_id and location.storage_area_id != area_id:
                    errors.append(
                        f"Location {location_id} belongs to area {location.storage_area_id}, "
                        f"not area {area_id}"
                    )
            except Exception as e:
                errors.append(f"Invalid location_id {location_id}: {str(e)}")

        # Validate bin
        if bin_id:
            try:
                bin_entity = await self.bin_service.get_storage_bin_by_id(bin_id)
                validated["bin"] = bin_entity

                # Check bin belongs to location if both provided
                if location_id and bin_entity.storage_location_id != location_id:
                    errors.append(
                        f"Bin {bin_id} belongs to location {bin_entity.storage_location_id}, "
                        f"not location {location_id}"
                    )
            except Exception as e:
                errors.append(f"Invalid bin_id {bin_id}: {str(e)}")

        return {"valid": len(errors) == 0, "errors": errors, "validated": validated}
