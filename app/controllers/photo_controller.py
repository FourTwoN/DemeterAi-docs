"""Photo gallery and detail API controllers."""

from __future__ import annotations

import io
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse, StreamingResponse
from redis.asyncio import Redis  # type: ignore[import-not-found]
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_redis
from app.core.exceptions import ResourceNotFoundException
from app.core.logging import get_logger
from app.db.session import get_db_session
from app.factories.service_factory import ServiceFactory
from app.schemas.photo_output_schema import (
    PhotoDetailResponse,
    PhotoGalleryResponse,
    PhotoJobStatusResponse,
    PhotoSessionProgressResponse,
    PhotoSessionSummaryResponse,
    PhotoSessionValidationRequest,
    PhotoReprocessRequest,
    PhotoReprocessResponse,
    PhotoBatchDeleteRequest,
    PhotoBatchDeleteResult,
)
from app.schemas.photo_processing_session_schema import PhotoProcessingSessionResponse

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/photos", tags=["photos"])


def get_factory(session: AsyncSession = Depends(get_db_session)) -> ServiceFactory:
    return ServiceFactory(session)


@router.get("/gallery", response_model=PhotoGalleryResponse)
async def list_photos_gallery(
    status: str | None = Query(None, description="Filter by processing status"),
    warehouse_id: int | None = Query(None, description="Filter by warehouse"),
    storage_location_id: int | None = Query(None, description="Filter by storage location"),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    factory: ServiceFactory = Depends(get_factory),
) -> PhotoGalleryResponse:
    """List photos for gallery view with filters."""

    service = factory.get_photo_query_service()
    logger.info("Listing photo gallery", extra={"page": page, "per_page": per_page})
    response = await service.get_gallery(
        status=status,
        warehouse_id=warehouse_id,
        storage_location_id=storage_location_id,
        date_from=date_from,
        date_to=date_to,
        page=page,
        per_page=per_page,
    )
    return response


@router.get("/{image_id}", response_model=PhotoDetailResponse)
async def get_photo_detail(
    image_id: UUID,
    factory: ServiceFactory = Depends(get_factory),
) -> PhotoDetailResponse:
    """Get detailed information for a single photo."""

    service = factory.get_photo_query_service()
    detail = await service.get_photo_detail(image_id)
    if not detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo not found")
    return detail


@router.get("/sessions/{session_id}/progress")
async def get_session_progress(
    session_id: UUID,
    factory: ServiceFactory = Depends(get_factory),
):
    """Get session progress (returns 202 while processing, 200 when completed)."""

    service = factory.get_photo_processing_session_service()
    progress = await service.get_session_progress_response(session_id)
    if progress is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    if isinstance(progress, PhotoSessionSummaryResponse):
        return JSONResponse(status_code=status.HTTP_200_OK, content=progress.model_dump(mode="json"))

    return JSONResponse(status_code=status.HTTP_202_ACCEPTED, content=progress.model_dump(mode="json"))


@router.post(
    "/sessions/{session_id}/validate",
    response_model=PhotoProcessingSessionResponse,
)
async def validate_session(
    session_id: UUID,
    request: PhotoSessionValidationRequest,
    factory: ServiceFactory = Depends(get_factory),
) -> PhotoProcessingSessionResponse:
    service = factory.get_photo_processing_session_service()
    updated = await service.validate_session_by_uuid(session_id, request.validated)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return updated


@router.get("/sessions/{session_id}/report.pdf")
async def download_session_pdf(
    session_id: UUID,
    factory: ServiceFactory = Depends(get_factory),
) -> StreamingResponse:
    service = factory.get_photo_processing_session_service()
    data = await service.generate_pdf_report_bytes(session_id)
    if data is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="session_{session_id}.pdf"'},
    )


@router.get("/sessions/{session_id}/export.csv")
async def download_session_csv(
    session_id: UUID,
    factory: ServiceFactory = Depends(get_factory),
) -> StreamingResponse:
    service = factory.get_photo_processing_session_service()
    data = await service.generate_csv_export(session_id)
    if data is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return StreamingResponse(
        io.BytesIO(data),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="session_{session_id}.csv"'},
    )


@router.get("/sessions/{session_id}/detections.geojson")
async def download_session_geojson(
    session_id: UUID,
    factory: ServiceFactory = Depends(get_factory),
) -> StreamingResponse:
    service = factory.get_photo_processing_session_service()
    data = await service.generate_geojson_export(session_id)
    if data is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/geo+json",
        headers={"Content-Disposition": f'attachment; filename="session_{session_id}.geojson"'},
    )


@router.get("/jobs/status", response_model=PhotoJobStatusResponse)
async def get_photo_jobs_status(
    upload_session_id: UUID = Query(..., description="Upload session identifier"),
    redis: Redis = Depends(get_redis),
    factory: ServiceFactory = Depends(get_factory),
) -> PhotoJobStatusResponse:
    """Get status for all jobs within an upload session."""

    service = factory.get_photo_query_service()
    try:
        return await service.get_job_status(redis, upload_session_id)
    except ResourceNotFoundException as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.post(
    "/{image_id}/reprocess",
    response_model=PhotoReprocessResponse,
    summary="Reprocess a photo using existing S3 image",
)
async def reprocess_photo_endpoint(
    image_id: UUID,
    request: PhotoReprocessRequest,
    redis: Redis = Depends(get_redis),
    factory: ServiceFactory = Depends(get_factory),
) -> PhotoReprocessResponse:
    service = factory.get_photo_query_service()
    result = await service.reprocess_photo(redis, image_id, request)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo not found")
    return result


@router.post(
    "/batch-delete",
    response_model=PhotoBatchDeleteResult,
    summary="Batch delete photos",
)
async def batch_delete_photos(
    request: PhotoBatchDeleteRequest,
    factory: ServiceFactory = Depends(get_factory),
) -> PhotoBatchDeleteResult:
    service = factory.get_photo_query_service()
    return await service.batch_delete_photos(request)
