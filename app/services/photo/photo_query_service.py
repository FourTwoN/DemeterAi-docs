"""Service providing read operations for photo gallery and details."""

from __future__ import annotations

import uuid
from datetime import datetime
from uuid import UUID

from redis.asyncio import Redis  # type: ignore[import-not-found]

from app.core.logging import get_logger
from app.models.photo_processing_session import ProcessingSessionStatusEnum
from app.models.s3_image import ProcessingStatusEnum
from app.repositories.photo_read_repository import PhotoReadRepository
from app.schemas.photo_output_schema import (
    GalleryPagination,
    PhotoBatchDeleteRequest,
    PhotoBatchDeleteResult,
    PhotoDetailResponse,
    PhotoGalleryItem,
    PhotoGalleryProcessingSummary,
    PhotoGalleryResponse,
    PhotoJobStatusItem,
    PhotoJobStatusResponse,
    PhotoMetadata,
    PhotoProcessingSessionDetail,
    PhotoReprocessRequest,
    PhotoReprocessResponse,
    StorageLocationHistoryItem,
)
from app.schemas.photo_processing_session_schema import PhotoProcessingSessionCreate
from app.services.photo.photo_job_service import PhotoJobService
from app.services.photo.photo_processing_session_service import PhotoProcessingSessionService
from app.services.photo.s3_image_service import S3ImageService
from app.tasks.ml_tasks import ml_parent_task

logger = get_logger(__name__)


class PhotoQueryService:
    """Service orchestrating photo read operations for gallery and detail endpoints."""

    def __init__(
        self,
        repo: PhotoReadRepository,
        s3_service: S3ImageService,
        session_service: PhotoProcessingSessionService,
        job_service: PhotoJobService,
    ) -> None:
        self.repo = repo
        self.s3_service = s3_service
        self.session_service = session_service
        self.job_service = job_service

    async def get_gallery(
        self,
        *,
        status: str | None = None,
        warehouse_id: int | None = None,
        storage_location_id: int | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        page: int = 1,
        per_page: int = 50,
    ) -> PhotoGalleryResponse:
        offset = (page - 1) * per_page

        rows = await self.repo.list_gallery_photos(
            status=status,
            warehouse_id=warehouse_id,
            storage_location_id=storage_location_id,
            date_from=date_from,
            date_to=date_to,
            offset=offset,
            limit=per_page,
        )

        photos: list[PhotoGalleryItem] = []
        for row in rows:
            image_id: UUID = row.image_id
            thumbnail_url = await self._build_presigned_url(row.s3_key_thumbnail)
            original_url = await self._build_presigned_url(row.s3_key_original)

            processing_summary = None
            if row.processing_session_uuid:
                processing_summary = PhotoGalleryProcessingSummary(
                    session_id=row.processing_session_uuid,
                    total_detected=row.total_detected,
                    total_estimated=row.total_estimated,
                    storage_location_id=row.storage_location_id,
                    storage_location_name=row.storage_location_name,
                    status=row.processing_status,
                )

            photos.append(
                PhotoGalleryItem(
                    image_id=image_id,
                    thumbnail_url=thumbnail_url,
                    original_url=original_url,
                    status=row.status,
                    error_details=row.error_details,
                    uploaded_at=row.created_at,
                    warehouse_name=row.warehouse_name,
                    processing_session=processing_summary,
                )
            )

        total_items = await self.repo.count_gallery_photos(
            status=status,
            warehouse_id=warehouse_id,
            storage_location_id=storage_location_id,
            date_from=date_from,
            date_to=date_to,
        )

        total_pages = (total_items + per_page - 1) // per_page if per_page else 0

        pagination = GalleryPagination(
            page=page,
            per_page=per_page,
            total_items=total_items,
            total_pages=total_pages,
        )

        return PhotoGalleryResponse(photos=photos, pagination=pagination)

    async def get_photo_detail(self, image_id: UUID) -> PhotoDetailResponse | None:
        row = await self.repo.get_photo_detail(image_id)
        if not row:
            return None

        s3_image = await self.s3_service.repo.get(image_id)
        if not s3_image:
            return None

        original_url = await self._build_presigned_url(row.s3_key_original)
        thumbnail_url = await self._build_presigned_url(row.s3_key_thumbnail)
        annotated_url = await self._build_presigned_url(row.processed_key)

        metadata = PhotoMetadata(
            file_size_bytes=s3_image.file_size_bytes,
            width_px=s3_image.width_px,
            height_px=s3_image.height_px,
            content_type=s3_image.content_type.value if s3_image.content_type else "",
            exif=s3_image.exif_metadata,
        )

        session_detail = None
        if row.processing_session_uuid:
            session = await self.session_service.get_session_by_uuid(row.processing_session_uuid)
            if session:
                session_detail = PhotoProcessingSessionDetail(
                    session_id=session.session_id,
                    status=session.status.value if session.status else "",
                    storage_location_id=session.storage_location_id,
                    storage_location_name=row.storage_location_name,
                    total_detected=session.total_detected,
                    total_estimated=session.total_estimated,
                    total_empty_containers=session.total_empty_containers,
                    avg_confidence=session.avg_confidence,
                    category_counts=session.category_counts,
                    validated=session.validated,
                    validated_by=str(session.validated_by_user_id)
                    if session.validated_by_user_id
                    else None,
                    validation_date=session.validation_date,
                )

        history_items: list[StorageLocationHistoryItem] = []
        if row.storage_location_id:
            recent_sessions = await self.repo.get_recent_sessions_for_location(
                row.storage_location_id,
                limit=10,
            )
            for session in recent_sessions:
                history_items.append(
                    StorageLocationHistoryItem(
                        timestamp=session.created_at,
                        event="photo_processed",
                        total_plants=session.total_detected,
                        session_id=session.session_id,
                        validated=session.validated,
                    )
                )

        return PhotoDetailResponse(
            image_id=image_id,
            original_url=original_url,
            thumbnail_url=thumbnail_url,
            annotated_url=annotated_url,
            status=row.status,
            metadata=metadata,
            processing_session=session_detail,
            storage_location_history=history_items,
        )

    async def get_job_status(
        self,
        redis: Redis,
        upload_session_id: UUID,
    ) -> PhotoJobStatusResponse:
        status_payload = await self.job_service.get_session_status(redis, str(upload_session_id))

        jobs: list[PhotoJobStatusItem] = []
        for job in status_payload["jobs"]:
            jobs.append(
                PhotoJobStatusItem(
                    job_id=job.get("job_id"),
                    image_id=UUID(job["image_id"]) if job.get("image_id") else None,
                    filename=job.get("filename"),
                    status=job.get("status", "pending"),
                    progress_percent=job.get("progress_percent", 0.0) or 0.0,
                    updated_at=datetime.fromisoformat(job["updated_at"])
                    if job.get("updated_at")
                    else None,
                    result=job.get("result"),
                )
            )

        summary = status_payload.get("summary", {})
        response_summary = {
            "total_jobs": summary.get("total_jobs", 0),
            "completed": summary.get("completed", 0),
            "processing": summary.get("processing", 0),
            "pending": summary.get("pending", 0),
            "failed": summary.get("failed", 0),
            "overall_progress_percent": summary.get("overall_progress_percent", 0.0),
        }

        return PhotoJobStatusResponse(
            upload_session_id=upload_session_id,
            jobs=jobs,
            summary=response_summary,
            last_updated=datetime.fromisoformat(status_payload["last_updated"])
            if status_payload.get("last_updated")
            else datetime.utcnow(),
        )

    async def _build_presigned_url(self, s3_key: str | None) -> str | None:
        if not s3_key:
            return None
        try:
            return await self.s3_service.generate_presigned_url(s3_key)
        except Exception as exc:  # pragma: no cover - fallback logging
            logger.warning("Failed to generate presigned URL", extra={"error": str(exc)})
            return None

    async def reprocess_photo(
        self,
        redis: Redis,
        image_id: UUID,
        request: PhotoReprocessRequest | None = None,
    ) -> PhotoReprocessResponse | None:
        original_image = await self.s3_service.repo.get(image_id)
        if not original_image:
            return None

        if request and request.storage_location_id:
            storage_location_id = request.storage_location_id
        else:
            existing_session = await self.session_service.get_session_by_original_image(image_id)
            storage_location_id = existing_session.storage_location_id if existing_session else None

        session_request = PhotoProcessingSessionCreate(
            storage_location_id=storage_location_id,
            original_image_id=image_id,
            processed_image_id=None,
            status=ProcessingSessionStatusEnum.PENDING,
            total_detected=0,
            total_estimated=0,
            total_empty_containers=0,
            avg_confidence=None,
            category_counts={},
            manual_adjustments={},
            error_message=None,
        )

        session = await self.session_service.create_session(session_request)

        image_data = [
            {
                "image_id": str(image_id),
                "image_path": original_image.s3_key_original,
                "storage_location_id": storage_location_id,
            }
        ]

        celery_task = ml_parent_task.delay(session_id=session.id, image_data=image_data)
        upload_session_id = uuid.uuid4()

        await self.job_service.create_upload_session(
            redis=redis,
            upload_session_id=str(upload_session_id),
            user_id=None,
            jobs=[
                {
                    "job_id": celery_task.id,
                    "image_id": str(image_id),
                    "filename": None,
                }
            ],
        )

        return PhotoReprocessResponse(
            upload_session_id=upload_session_id,
            image_id=image_id,
            new_job_id=celery_task.id,
            message="Reprocessing started",
            poll_url=f"/api/v1/photos/jobs/status?upload_session_id={upload_session_id}",
        )

    async def batch_delete_photos(
        self,
        request: PhotoBatchDeleteRequest,
    ) -> PhotoBatchDeleteResult:
        deleted = 0
        not_found: list[UUID] = []

        for image_id in request.image_ids:
            image = await self.s3_service.repo.get(image_id)
            if not image:
                not_found.append(image_id)
                continue

            image.status = ProcessingStatusEnum.FAILED
            image.error_details = request.reason or "deleted_by_user"
            await self.s3_service.repo.session.flush()
            deleted += 1

        return PhotoBatchDeleteResult(deleted=deleted, not_found=not_found)
