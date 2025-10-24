"""Service for warehouse map endpoints."""

from __future__ import annotations

from typing import Any

from app.core.logging import get_logger
from app.schemas.map_schema import (
    LocationDetailResponse,
    LocationHistoryItem,
    LocationHistoryResponse,
    LocationPreviewMetrics,
    MapBulkLoadResponse,
    StorageAreaNode,
    StorageLocationNode,
    WarehouseNode,
)
from app.services.photo.photo_processing_session_service import PhotoProcessingSessionService
from app.services.photo.s3_image_service import S3ImageService
from app.services.storage_area_service import StorageAreaService
from app.services.storage_location_service import StorageLocationService
from app.services.warehouse_service import WarehouseService

logger = get_logger(__name__)


class MapViewService:
    """Aggregates data for warehouse map visualizations."""

    def __init__(
        self,
        warehouse_service: WarehouseService,
        area_service: StorageAreaService,
        location_service: StorageLocationService,
        session_service: PhotoProcessingSessionService,
        s3_service: S3ImageService,
    ) -> None:
        self.warehouse_service = warehouse_service
        self.area_service = area_service
        self.location_service = location_service
        self.session_service = session_service
        self.s3_service = s3_service

    async def get_bulk_load(self) -> MapBulkLoadResponse:
        warehouses = await self.warehouse_service.get_active_warehouses(include_areas=True)
        warehouse_nodes: list[WarehouseNode] = []

        for warehouse in warehouses:
            areas = await self.area_service.get_areas_by_warehouse(warehouse.warehouse_id)
            area_nodes: list[StorageAreaNode] = []

            for area in areas:
                locations = await self.location_service.get_locations_by_area(area.storage_area_id)
                location_nodes: list[StorageLocationNode] = []

                for location in locations:
                    preview = await self._build_location_preview(location.storage_location_id)
                    location_nodes.append(
                        StorageLocationNode(
                            location_id=location.storage_location_id,
                            code=location.code,
                            name=location.name,
                            preview=preview,
                        )
                    )

                area_nodes.append(
                    StorageAreaNode(
                        storage_area_id=area.storage_area_id,
                        code=area.code,
                        name=area.name,
                        position=getattr(area, "position", None),
                        locations=location_nodes,
                    )
                )

            warehouse_nodes.append(
                WarehouseNode(
                    warehouse_id=warehouse.warehouse_id,
                    code=warehouse.code,
                    name=warehouse.name,
                    storage_areas=area_nodes,
                )
            )

        return MapBulkLoadResponse(warehouses=warehouse_nodes)

    async def get_location_detail(self, location_id: int) -> LocationDetailResponse | None:
        location = await self.location_service.get_storage_location_by_id(location_id)
        if not location:
            return None

        sessions = await self.session_service.get_by_storage_location(location_id, limit=1)
        latest_session = sessions[0] if sessions else None

        latest_summary: dict[str, Any] | None = None
        detections: list[dict[str, Any]] = []

        if latest_session:
            latest_summary = {
                "session_id": str(latest_session.session_id),
                "status": latest_session.status.value if latest_session.status else "",
                "total_detected": latest_session.total_detected,
                "total_estimated": latest_session.total_estimated,
                "total_empty_containers": latest_session.total_empty_containers,
                "avg_confidence": latest_session.avg_confidence,
                "category_counts": latest_session.category_counts,
                "created_at": latest_session.created_at,
            }

        return LocationDetailResponse(
            storage_location={
                "location_id": location.storage_location_id,
                "code": location.code,
                "name": location.name,
            },
            latest_session=latest_summary,
            detections=detections,
        )

    async def get_location_history(
        self,
        location_id: int,
        page: int = 1,
        per_page: int = 12,
    ) -> LocationHistoryResponse | None:
        location = await self.location_service.get_storage_location_by_id(location_id)
        if not location:
            return None

        sessions = await self.session_service.get_by_storage_location(location_id, limit=per_page)
        periods: list[LocationHistoryItem] = []

        for session in sessions:
            thumbnail_url = None
            if session.processed_image_id:
                s3_processed = await self.s3_service.repo.get(session.processed_image_id)
                if s3_processed and s3_processed.s3_key_thumbnail:
                    thumbnail_url = await self.s3_service.generate_presigned_url(
                        s3_processed.s3_key_thumbnail
                    )

            periods.append(
                LocationHistoryItem(
                    fecha=session.created_at,
                    period_end=None,
                    session_id=str(session.session_id),
                    cantidad_inicial=None,
                    muertes=None,
                    transplantes=None,
                    plantados=None,
                    cantidad_vendida=None,
                    cantidad_final=session.total_detected,
                    net_change=None,
                    photo_thumbnail_url=thumbnail_url,
                )
            )

        summary = {
            "total_periods": len(periods),
            "earliest_date": periods[-1].fecha if periods else None,
            "latest_date": periods[0].fecha if periods else None,
        }

        pagination = {
            "page": page,
            "per_page": per_page,
            "total_pages": 1,
            "total_items": len(periods),
        }

        return LocationHistoryResponse(
            storage_location={
                "location_id": location.storage_location_id,
                "code": location.code,
                "name": location.name,
            },
            periods=periods,
            summary=summary,
            pagination=pagination,
        )

    async def _build_location_preview(self, location_id: int) -> LocationPreviewMetrics:
        sessions = await self.session_service.get_by_storage_location(location_id, limit=2)

        if not sessions:
            return LocationPreviewMetrics(status="pending")

        latest = sessions[0]
        previous = sessions[1] if len(sessions) > 1 else None

        thumbnail_url = None
        if latest.processed_image_id:
            s3_processed = await self.s3_service.repo.get(latest.processed_image_id)
            if s3_processed and s3_processed.s3_key_thumbnail:
                thumbnail_url = await self.s3_service.generate_presigned_url(
                    s3_processed.s3_key_thumbnail
                )

        quantity_change = None
        if previous is not None:
            quantity_change = (latest.total_detected or 0) - (previous.total_detected or 0)

        return LocationPreviewMetrics(
            current_quantity=latest.total_detected,
            previous_quantity=previous.total_detected if previous else None,
            quantity_change=quantity_change,
            last_photo_date=latest.created_at,
            last_photo_thumbnail_url=thumbnail_url,
            status=latest.status.value if latest.status else "",
            quality_score=latest.avg_confidence,
        )
