"""Location Hierarchy API Controllers.

This module provides HTTP endpoints for warehouse hierarchy operations:
- 4-level geospatial hierarchy (Warehouse → Area → Location → Bin)
- GPS-based location lookup
- Hierarchy navigation and validation

Architecture:
    Layer: Controller Layer (HTTP only)
    Dependencies: Service layer only (NO business logic here)
    Pattern: Thin controllers - delegate to services

Endpoints:
    GET /api/v1/locations/warehouses - List all warehouses (C008)
    GET /api/v1/locations/warehouses/{id}/areas - Get warehouse areas (C009)
    GET /api/v1/locations/areas/{id}/locations - Get storage locations (C010)
    GET /api/v1/locations/locations/{id}/bins - Get storage bins (C011)
    GET /api/v1/locations/search - Search by GPS coordinates (C012)
    POST /api/v1/locations/validate - Validate location hierarchy (C013)
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ResourceNotFoundException
from app.core.logging import get_logger
from app.db.session import get_db_session
from app.factories.service_factory import ServiceFactory
from app.schemas.storage_area_schema import StorageAreaResponse
from app.schemas.storage_bin_schema import StorageBinResponse
from app.schemas.storage_location_schema import StorageLocationResponse
from app.schemas.warehouse_schema import WarehouseResponse

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/locations", tags=["locations"])


# =============================================================================
# Dependency Injection Helpers
# =============================================================================


def get_factory(session: AsyncSession = Depends(get_db_session)) -> ServiceFactory:
    """Dependency injection for ServiceFactory."""
    return ServiceFactory(session)


# =============================================================================
# API Endpoints
# =============================================================================


@router.get(
    "/warehouses",
    response_model=list[WarehouseResponse],
    summary="List all warehouses",
)
async def list_warehouses(
    skip: int = Query(0, ge=0, description="Offset for pagination"),
    limit: int = Query(100, ge=1, le=1000, description="Max results"),
    factory: ServiceFactory = Depends(get_factory),
) -> list[WarehouseResponse]:
    """List all warehouses with pagination (C008).

    Args:
        skip: Offset (default 0)
        limit: Max results (default 100, max 1000)

    Returns:
        List of WarehouseResponse

    Example:
        ```bash
        curl "http://localhost:8000/api/v1/locations/warehouses?skip=0&limit=50"
        ```
    """
    try:
        logger.info("Listing warehouses", extra={"skip": skip, "limit": limit})

        service = factory.get_warehouse_service()
        warehouses = await service.get_all(skip=skip, limit=limit)

        logger.info("Warehouses retrieved", extra={"count": len(warehouses)})

        return warehouses

    except Exception as e:
        logger.error("Failed to list warehouses", extra={"error": str(e)}, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list warehouses.",
        )


@router.get(
    "/warehouses/{warehouse_id}/areas",
    response_model=list[StorageAreaResponse],
    summary="Get warehouse areas",
)
async def get_warehouse_areas(
    warehouse_id: int,
    factory: ServiceFactory = Depends(get_factory),
) -> list[StorageAreaResponse]:
    """Get all storage areas for a warehouse (C009).

    Args:
        warehouse_id: Warehouse ID

    Returns:
        List of StorageAreaResponse

    Raises:
        HTTPException 404: Warehouse not found

    Example:
        ```bash
        curl "http://localhost:8000/api/v1/locations/warehouses/1/areas"
        ```
    """
    try:
        logger.info("Getting warehouse areas", extra={"warehouse_id": warehouse_id})

        service = factory.get_storage_area_service()
        areas = await service.get_by_warehouse(warehouse_id)

        logger.info(
            "Warehouse areas retrieved",
            extra={"warehouse_id": warehouse_id, "count": len(areas)},
        )

        return areas

    except ResourceNotFoundException as e:
        logger.warning("Warehouse not found", extra={"error": str(e)})
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    except Exception as e:
        logger.error("Failed to get warehouse areas", extra={"error": str(e)}, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get warehouse areas.",
        )


@router.get(
    "/areas/{area_id}/locations",
    response_model=list[StorageLocationResponse],
    summary="Get storage locations",
)
async def get_area_locations(
    area_id: int,
    factory: ServiceFactory = Depends(get_factory),
) -> list[StorageLocationResponse]:
    """Get all storage locations for an area (C010).

    Args:
        area_id: Storage area ID

    Returns:
        List of StorageLocationResponse

    Raises:
        HTTPException 404: Area not found

    Example:
        ```bash
        curl "http://localhost:8000/api/v1/locations/areas/1/locations"
        ```
    """
    try:
        logger.info("Getting area locations", extra={"area_id": area_id})

        service = factory.get_storage_location_service()
        locations = await service.get_by_area(area_id)

        logger.info(
            "Area locations retrieved",
            extra={"area_id": area_id, "count": len(locations)},
        )

        return locations

    except ResourceNotFoundException as e:
        logger.warning("Area not found", extra={"error": str(e)})
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    except Exception as e:
        logger.error("Failed to get area locations", extra={"error": str(e)}, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get area locations.",
        )


@router.get(
    "/locations/{location_id}/bins",
    response_model=list[StorageBinResponse],
    summary="Get storage bins",
)
async def get_location_bins(
    location_id: int,
    factory: ServiceFactory = Depends(get_factory),
) -> list[StorageBinResponse]:
    """Get all storage bins for a location (C011).

    Args:
        location_id: Storage location ID

    Returns:
        List of StorageBinResponse

    Raises:
        HTTPException 404: Location not found

    Example:
        ```bash
        curl "http://localhost:8000/api/v1/locations/locations/1/bins"
        ```
    """
    try:
        logger.info("Getting location bins", extra={"location_id": location_id})

        service = factory.get_storage_bin_service()
        bins = await service.get_by_location(location_id)

        logger.info(
            "Location bins retrieved",
            extra={"location_id": location_id, "count": len(bins)},
        )

        return bins

    except ResourceNotFoundException as e:
        logger.warning("Location not found", extra={"error": str(e)})
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    except Exception as e:
        logger.error("Failed to get location bins", extra={"error": str(e)}, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get location bins.",
        )


@router.get(
    "/search",
    response_model=dict,
    summary="Search by GPS coordinates",
)
async def search_by_gps(
    longitude: float = Query(..., description="GPS longitude coordinate"),
    latitude: float = Query(..., description="GPS latitude coordinate"),
    factory: ServiceFactory = Depends(get_factory),
) -> dict:
    """Search warehouse hierarchy by GPS coordinates (C012).

    Uses PostGIS ST_Contains to find location containing the GPS point.

    Args:
        longitude: GPS longitude
        latitude: GPS latitude

    Returns:
        Complete hierarchy (warehouse, area, location, bin)

    Raises:
        HTTPException 404: No location found at coordinates

    Example:
        ```bash
        curl "http://localhost:8000/api/v1/locations/search?longitude=10.5&latitude=20.5"
        ```

    Response:
        ```json
        {
          "warehouse": {"warehouse_id": 1, "name": "Main Warehouse"},
          "area": {"area_id": 5, "name": "Zone A"},
          "location": {"location_id": 10, "name": "A-1"},
          "bin": {"bin_id": 15, "name": "A-1-01"}
        }
        ```
    """
    try:
        logger.info(
            "GPS-based location search",
            extra={"longitude": longitude, "latitude": latitude},
        )

        # Use lookup_gps_full_chain which returns {"location": location, "bins": bins}
        service = factory.get_location_hierarchy_service()
        result = await service.lookup_gps_full_chain(longitude, latitude)

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No location found at GPS coordinates ({longitude}, {latitude})",
            )

        location = result["location"]
        bins = result["bins"]

        # Get area and warehouse by traversing the hierarchy
        # StorageLocationResponse has storage_area_id
        area = await service.area_service.get_storage_area_by_id(location.storage_area_id)
        warehouse = None
        if area:
            warehouse = await service.warehouse_service.get_warehouse_by_id(area.warehouse_id)

        logger.info(
            "GPS search successful",
            extra={
                "warehouse_id": warehouse.warehouse_id if warehouse else None,
                "location_id": location.storage_location_id,
            },
        )

        # Convert hierarchy to dict response
        return {
            "warehouse": warehouse.model_dump() if warehouse else None,
            "area": area.model_dump() if area else None,
            "location": location.model_dump(),
            "bins": [bin_item.model_dump() for bin_item in bins] if bins else [],
        }

    except HTTPException:
        raise

    except Exception as e:
        logger.error("GPS search failed", extra={"error": str(e)}, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="GPS search failed.",
        )


@router.post(
    "/validate",
    response_model=dict,
    summary="Validate location hierarchy",
)
async def validate_location_hierarchy(
    warehouse_id: int | None = None,
    area_id: int | None = None,
    location_id: int | None = None,
    bin_id: int | None = None,
    factory: ServiceFactory = Depends(get_factory),
) -> dict:
    """Validate location hierarchy integrity (C013).

    Checks that child entities belong to specified parents.

    Args:
        warehouse_id: Warehouse ID (optional)
        area_id: Storage area ID (optional)
        location_id: Storage location ID (optional)
        bin_id: Storage bin ID (optional)

    Returns:
        Validation result with any errors

    Example:
        ```json
        {
          "warehouse_id": 1,
          "area_id": 5,
          "location_id": 10
        }
        ```

    Response:
        ```json
        {
          "valid": true,
          "errors": [],
          "hierarchy": {
            "warehouse": "Main Warehouse",
            "area": "Zone A",
            "location": "A-1"
          }
        }
        ```
    """
    try:
        logger.info(
            "Validating location hierarchy",
            extra={
                "warehouse_id": warehouse_id,
                "area_id": area_id,
                "location_id": location_id,
                "bin_id": bin_id,
            },
        )

        # TODO: Implement validate_hierarchy method in LocationHierarchyService
        # For now, return placeholder
        logger.warning("Hierarchy validation not yet implemented")

        return {
            "valid": True,
            "errors": [],
            "message": "Validation not yet implemented",
            "hierarchy": {
                "warehouse_id": warehouse_id,
                "area_id": area_id,
                "location_id": location_id,
                "bin_id": bin_id,
            },
        }

    except Exception as e:
        logger.error("Hierarchy validation failed", extra={"error": str(e)}, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Hierarchy validation failed.",
        )
