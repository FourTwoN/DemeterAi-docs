"""Admin configuration controllers."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.factories.service_factory import ServiceFactory
from app.schemas.storage_location_config_schema import (
    StorageLocationConfigBulkRequest,
    StorageLocationConfigResponse,
)

router = APIRouter(prefix="/api/admin", tags=["admin"])


def get_factory(session: AsyncSession = Depends(get_db_session)) -> ServiceFactory:
    return ServiceFactory(session)


@router.get("/warehouses/hierarchy")
async def get_warehouse_hierarchy(factory: ServiceFactory = Depends(get_factory)) -> dict:
    hierarchy_service = factory.get_location_hierarchy_service()
    warehouse_service = factory.get_warehouse_service()
    warehouses = await warehouse_service.get_active_warehouses(include_areas=False)

    result = []
    for warehouse in warehouses:
        result.append(await hierarchy_service.get_full_hierarchy(warehouse.warehouse_id))

    return {"warehouses": result}


@router.post(
    "/storage-location-config/bulk-update",
    response_model=list[StorageLocationConfigResponse],
)
async def bulk_update_location_config(
    request: StorageLocationConfigBulkRequest,
    factory: ServiceFactory = Depends(get_factory),
) -> list[StorageLocationConfigResponse]:
    service = factory.get_storage_location_config_service()
    return await service.bulk_apply(request, create_only=False)


@router.post(
    "/storage-location-config/bulk-create",
    response_model=list[StorageLocationConfigResponse],
)
async def bulk_create_location_config(
    request: StorageLocationConfigBulkRequest,
    factory: ServiceFactory = Depends(get_factory),
) -> list[StorageLocationConfigResponse]:
    service = factory.get_storage_location_config_service()
    try:
        return await service.bulk_apply(request, create_only=True)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
