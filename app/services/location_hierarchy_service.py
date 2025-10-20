"""Location Hierarchy Service (aggregator for S001-S005).

Orchestrates warehouse → area → location → bin hierarchy queries.
Critical for reporting and analytics dashboards.
"""

from app.services.storage_area_service import StorageAreaService
from app.services.storage_bin_service import StorageBinService
from app.services.storage_location_service import StorageLocationService
from app.services.warehouse_service import WarehouseService


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

    async def get_full_hierarchy(self, warehouse_id: int) -> dict:
        """Get complete hierarchy: warehouse → areas → locations → bins."""
        warehouse = await self.warehouse_service.get_warehouse_by_id(warehouse_id)
        areas = await self.area_service.get_areas_by_warehouse(warehouse_id)

        hierarchy = {"warehouse": warehouse, "areas": []}

        for area in areas:
            locations = await self.location_service.get_locations_by_area(area.storage_area_id)
            area_data = {"area": area, "locations": []}

            for loc in locations:
                bins = await self.bin_service.get_bins_by_location(loc.storage_location_id)
                area_data["locations"].append({"location": loc, "bins": bins})

            hierarchy["areas"].append(area_data)

        return hierarchy

    async def lookup_gps_full_chain(self, longitude: float, latitude: float) -> dict | None:
        """GPS → full chain (warehouse → area → location) for photo localization."""
        # Use StorageLocationService's GPS lookup (already does full chain)
        location = await self.location_service.get_location_by_gps(longitude, latitude)

        if not location:
            return None

        # Get bins for this location
        bins = await self.bin_service.get_bins_by_location(location.storage_location_id)

        return {"location": location, "bins": bins}
