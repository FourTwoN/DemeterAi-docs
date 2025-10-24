"""Map view controllers."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.factories.service_factory import ServiceFactory
from app.schemas.map_schema import (
    LocationDetailResponse,
    LocationHistoryResponse,
    MapBulkLoadResponse,
)

router = APIRouter(prefix="/api/v1", tags=["map"])


def get_factory(session: AsyncSession = Depends(get_db_session)) -> ServiceFactory:
    return ServiceFactory(session)


@router.get("/map/bulk-load", response_model=MapBulkLoadResponse)
async def bulk_load_map(factory: ServiceFactory = Depends(get_factory)) -> MapBulkLoadResponse:
    service = factory.get_map_view_service()
    return await service.get_bulk_load()


@router.get("/storage-locations/{location_id}/detail", response_model=LocationDetailResponse)
async def get_location_detail(
    location_id: int,
    factory: ServiceFactory = Depends(get_factory),
) -> LocationDetailResponse:
    service = factory.get_map_view_service()
    detail = await service.get_location_detail(location_id)
    if not detail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Storage location not found"
        )
    return detail


@router.get("/storage-locations/{location_id}/history", response_model=LocationHistoryResponse)
async def get_location_history(
    location_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(12, ge=1, le=50),
    factory: ServiceFactory = Depends(get_factory),
) -> LocationHistoryResponse:
    service = factory.get_map_view_service()
    history = await service.get_location_history(location_id, page=page, per_page=per_page)
    if not history:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Storage location not found"
        )
    return history
