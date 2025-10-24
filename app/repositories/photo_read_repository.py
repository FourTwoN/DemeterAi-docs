"""Repository with read-only queries for photo gallery and details."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Select, and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.models.photo_processing_session import PhotoProcessingSession
from app.models.s3_image import S3Image
from app.models.storage_area import StorageArea
from app.models.storage_location import StorageLocation
from app.models.warehouse import Warehouse


class PhotoReadRepository:
    """Repository providing complex read queries for photos."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_gallery_photos(
        self,
        *,
        status: str | None = None,
        warehouse_id: int | None = None,
        storage_location_id: int | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[Any]:
        stmt = self._base_gallery_select()

        if status:
            stmt = stmt.where(S3Image.status == status)

        if warehouse_id:
            stmt = stmt.where(Warehouse.warehouse_id == warehouse_id)

        if storage_location_id:
            stmt = stmt.where(StorageLocation.location_id == storage_location_id)

        if date_from:
            stmt = stmt.where(S3Image.created_at >= date_from)

        if date_to:
            stmt = stmt.where(S3Image.created_at <= date_to)

        stmt = stmt.order_by(S3Image.created_at.desc()).offset(offset).limit(limit)

        result = await self.session.execute(stmt)
        return list(result.all())

    async def count_gallery_photos(
        self,
        *,
        status: str | None = None,
        warehouse_id: int | None = None,
        storage_location_id: int | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> int:
        stmt = select(func.count(S3Image.image_id))
        stmt = stmt.select_from(S3Image)
        stmt = stmt.outerjoin(
            PhotoProcessingSession,
            PhotoProcessingSession.original_image_id == S3Image.image_id,
        )
        stmt = stmt.outerjoin(
            StorageLocation,
            PhotoProcessingSession.storage_location_id == StorageLocation.location_id,
        )
        stmt = stmt.outerjoin(
            StorageArea, StorageLocation.storage_area_id == StorageArea.storage_area_id
        )
        stmt = stmt.outerjoin(Warehouse, StorageArea.warehouse_id == Warehouse.warehouse_id)

        conditions = []
        if status:
            conditions.append(S3Image.status == status)
        if warehouse_id:
            conditions.append(Warehouse.warehouse_id == warehouse_id)
        if storage_location_id:
            conditions.append(StorageLocation.location_id == storage_location_id)
        if date_from:
            conditions.append(S3Image.created_at >= date_from)
        if date_to:
            conditions.append(S3Image.created_at <= date_to)

        if conditions:
            stmt = stmt.where(and_(*conditions))

        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def get_photo_detail(self, image_id: UUID) -> Any | None:
        stmt = self._base_gallery_select().where(S3Image.image_id == image_id)
        result = await self.session.execute(stmt)
        return result.first()

    async def get_recent_sessions_for_location(
        self,
        location_id: int,
        limit: int = 10,
    ) -> list[PhotoProcessingSession]:
        stmt = (
            select(PhotoProcessingSession)
            .where(PhotoProcessingSession.storage_location_id == location_id)
            .order_by(PhotoProcessingSession.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    def _base_gallery_select(self) -> Select[Any]:
        processed_alias = aliased(S3Image)

        stmt = (
            select(
                S3Image.image_id,
                S3Image.s3_key_thumbnail,
                S3Image.s3_key_original,
                S3Image.s3_key_processed,
                S3Image.status,
                S3Image.error_details,
                S3Image.created_at,
                PhotoProcessingSession.session_id.label("processing_session_uuid"),
                PhotoProcessingSession.id.label("processing_session_id"),
                PhotoProcessingSession.total_detected,
                PhotoProcessingSession.total_estimated,
                PhotoProcessingSession.total_empty_containers,
                PhotoProcessingSession.avg_confidence,
                PhotoProcessingSession.storage_location_id,
                PhotoProcessingSession.status.label("processing_status"),
                StorageLocation.name.label("storage_location_name"),
                Warehouse.name.label("warehouse_name"),
                processed_alias.s3_key_original.label("processed_key"),
            )
            .select_from(S3Image)
            .outerjoin(
                PhotoProcessingSession,
                PhotoProcessingSession.original_image_id == S3Image.image_id,
            )
            .outerjoin(
                processed_alias,
                PhotoProcessingSession.processed_image_id == processed_alias.image_id,
            )
            .outerjoin(
                StorageLocation,
                PhotoProcessingSession.storage_location_id == StorageLocation.location_id,
            )
            .outerjoin(
                StorageArea,
                StorageLocation.storage_area_id == StorageArea.storage_area_id,
            )
            .outerjoin(Warehouse, StorageArea.warehouse_id == Warehouse.warehouse_id)
        )
        return stmt
