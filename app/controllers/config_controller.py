"""Configuration API Controllers.

This module provides HTTP endpoints for system configuration:
- Storage location defaults (product, packaging, density)
- Density parameters for ML estimation
- Configuration management

Architecture:
    Layer: Controller Layer (HTTP only)
    Dependencies: Service layer only (NO business logic here)
    Pattern: Thin controllers - delegate to services

Endpoints:
    GET /api/v1/config/location-defaults - Get location defaults (C021)
    POST /api/v1/config/location-defaults - Set location defaults (C022)
    GET /api/v1/config/density-params - Get density parameters (C023)
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ResourceNotFoundException, ValidationException
from app.core.logging import get_logger
from app.db.session import get_db_session
from app.factories.service_factory import ServiceFactory
from app.schemas.density_parameter_schema import DensityParameterResponse
from app.schemas.storage_location_config_schema import (
    StorageLocationConfigCreateRequest,
    StorageLocationConfigResponse,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/config", tags=["configuration"])


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
    "/location-defaults",
    response_model=StorageLocationConfigResponse | None,
    summary="Get location default configuration",
)
async def get_location_defaults(
    location_id: int = Query(..., description="Storage location ID"),
    factory: ServiceFactory = Depends(get_factory),
) -> StorageLocationConfigResponse | None:
    """Get default product/packaging configuration for a storage location (C021).

    This configuration determines:
    - Default product for the location
    - Default packaging type and size
    - Default density parameters for ML estimation

    Args:
        location_id: Storage location ID

    Returns:
        StorageLocationConfigResponse or None if not configured

    Example:
        ```bash
        curl "http://localhost:8000/api/v1/config/location-defaults?location_id=10"
        ```

    Response:
        ```json
        {
          "config_id": 5,
          "storage_location_id": 10,
          "product_id": 15,
          "packaging_catalog_id": 20,
          "default_density_param_id": 3
        }
        ```
    """
    try:
        logger.info("Getting location defaults", extra={"location_id": location_id})

        service = factory.get_storage_location_config_service()
        config = await service.get_by_location(location_id)

        if config:
            logger.info(
                "Location defaults found",
                extra={
                    "location_id": location_id,
                    "config_id": config.config_id,
                    "product_id": config.product_id,
                },
            )
        else:
            logger.info(
                "No location defaults found",
                extra={"location_id": location_id},
            )

        return config

    except Exception as e:
        logger.error("Failed to get location defaults", extra={"error": str(e)}, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get location defaults.",
        )


@router.post(
    "/location-defaults",
    response_model=StorageLocationConfigResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Set location default configuration",
)
async def set_location_defaults(
    request: StorageLocationConfigCreateRequest,
    factory: ServiceFactory = Depends(get_factory),
) -> StorageLocationConfigResponse:
    """Set or update default configuration for a storage location (C022).

    Business rules:
    1. Location must exist
    2. Product must exist
    3. Packaging must exist
    4. Density parameter must exist (if specified)
    5. Only one config per location (upsert behavior)

    Args:
        request: Location configuration data

    Returns:
        StorageLocationConfigResponse with created/updated config

    Raises:
        HTTPException 400: Validation error
        HTTPException 404: Location/product/packaging not found
        HTTPException 500: Database error

    Example:
        ```json
        {
          "storage_location_id": 10,
          "product_id": 15,
          "packaging_catalog_id": 20,
          "default_density_param_id": 3
        }
        ```

    Response:
        ```json
        {
          "config_id": 5,
          "storage_location_id": 10,
          "product_id": 15,
          "packaging_catalog_id": 20,
          "default_density_param_id": 3
        }
        ```
    """
    try:
        logger.info(
            "Setting location defaults",
            extra={
                "location_id": request.storage_location_id,
                "product_id": request.product_id,
                "packaging_catalog_id": request.packaging_catalog_id,
            },
        )

        service = factory.get_storage_location_config_service()
        config = await service.create_or_update(request)

        logger.info(
            "Location defaults set",
            extra={
                "config_id": config.config_id,
                "location_id": config.storage_location_id,
                "product_id": config.product_id,
            },
        )

        return config

    except ValidationException as e:
        logger.warning("Config validation failed", extra={"error": str(e)})
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    except ResourceNotFoundException as e:
        logger.warning("Resource not found", extra={"error": str(e)})
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    except Exception as e:
        logger.error("Failed to set location defaults", extra={"error": str(e)}, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to set location defaults.",
        )


@router.get(
    "/density-params",
    response_model=list[DensityParameterResponse],
    summary="Get density parameters",
)
async def get_density_parameters(
    product_id: int | None = Query(None, description="Filter by product ID"),
    packaging_catalog_id: int | None = Query(None, description="Filter by packaging catalog ID"),
    skip: int = Query(0, ge=0, description="Offset for pagination"),
    limit: int = Query(100, ge=1, le=1000, description="Max results"),
    factory: ServiceFactory = Depends(get_factory),
) -> list[DensityParameterResponse]:
    """Get density parameters for ML plant counting estimation (C023).

    Density parameters define:
    - Plants per area (m²) for a product/packaging combination
    - Used by ML pipeline to estimate total plants from image detections

    Args:
        product_id: Optional product ID filter
        packaging_catalog_id: Optional packaging catalog ID filter
        skip: Offset (default 0)
        limit: Max results (default 100, max 1000)

    Returns:
        List of DensityParameterResponse

    Example:
        ```bash
        # All density parameters
        curl "http://localhost:8000/api/v1/config/density-params?skip=0&limit=50"

        # Filter by product
        curl "http://localhost:8000/api/v1/config/density-params?product_id=15"

        # Filter by product + packaging
        curl "http://localhost:8000/api/v1/config/density-params?product_id=15&packaging_catalog_id=20"
        ```

    Response:
        ```json
        [
          {
            "param_id": 3,
            "product_id": 15,
            "packaging_catalog_id": 20,
            "plants_per_sqm": 25.5,
            "is_active": true
          }
        ]
        ```
    """
    try:
        logger.info(
            "Getting density parameters",
            extra={
                "product_id": product_id,
                "packaging_catalog_id": packaging_catalog_id,
                "skip": skip,
                "limit": limit,
            },
        )

        service = factory.get_density_parameter_service()
        if product_id and packaging_catalog_id:
            params = await service.get_by_product_and_packaging(product_id, packaging_catalog_id)
        elif product_id:
            params = await service.get_by_product(product_id)
        else:
            params = await service.get_all(skip=skip, limit=limit)

        logger.info("Density parameters retrieved", extra={"count": len(params)})

        return params

    except ResourceNotFoundException as e:
        logger.warning("Resource not found", extra={"error": str(e)})
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    except Exception as e:
        logger.error("Failed to get density parameters", extra={"error": str(e)}, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get density parameters.",
        )
