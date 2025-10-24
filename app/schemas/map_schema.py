"""Schemas for warehouse map endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class LocationPreviewMetrics(BaseModel):
    current_quantity: int | None = None
    previous_quantity: int | None = None
    quantity_change: int | None = None
    last_photo_date: datetime | None = None
    last_photo_thumbnail_url: str | None = None
    status: str | None = None
    quality_score: float | None = None


class StorageLocationNode(BaseModel):
    location_id: int = Field(..., description="Storage location identifier")
    code: str
    name: str
    preview: LocationPreviewMetrics | None = None


class StorageAreaNode(BaseModel):
    storage_area_id: int
    code: str
    name: str
    position: str | None = None
    locations: list[StorageLocationNode] = Field(default_factory=list)


class WarehouseNode(BaseModel):
    warehouse_id: int
    code: str
    name: str
    storage_areas: list[StorageAreaNode] = Field(default_factory=list)


class MapBulkLoadResponse(BaseModel):
    warehouses: list[WarehouseNode] = Field(default_factory=list)


class LocationDetailResponse(BaseModel):
    storage_location: dict[str, Any]
    latest_session: dict[str, Any] | None = None
    detections: list[dict[str, Any]] = Field(default_factory=list)
    stock_summary: dict[str, Any] | None = None
    financial: dict[str, Any] | None = None
    quality_metrics: dict[str, Any] | None = None


class LocationHistoryItem(BaseModel):
    fecha: datetime
    period_end: datetime | None = None
    session_id: str | None = None
    cantidad_inicial: int | None = None
    muertes: int | None = None
    transplantes: int | None = None
    plantados: int | None = None
    cantidad_vendida: int | None = None
    cantidad_final: int | None = None
    net_change: int | None = None
    photo_thumbnail_url: str | None = None


class LocationHistoryResponse(BaseModel):
    storage_location: dict[str, Any]
    periods: list[LocationHistoryItem]
    summary: dict[str, Any]
    pagination: dict[str, Any]
