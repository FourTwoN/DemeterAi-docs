"""Pydantic schemas for photo gallery and session endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class PhotoGalleryProcessingSummary(BaseModel):
    """Summary information about the processing session for gallery listings."""

    session_id: UUID | None = Field(None, description="Processing session UUID")
    total_detected: int | None = Field(None, ge=0)
    total_estimated: int | None = Field(None, ge=0)
    storage_location_id: int | None = None
    storage_location_name: str | None = None
    status: str | None = None


class PhotoGalleryItem(BaseModel):
    """Single photo representation in gallery response."""

    image_id: UUID
    thumbnail_url: str | None = None
    original_url: str | None = None
    status: str
    error_details: str | None = None
    uploaded_at: datetime
    warehouse_name: str | None = None
    processing_session: PhotoGalleryProcessingSummary | None = None


class GalleryPagination(BaseModel):
    """Pagination metadata for gallery responses."""

    page: int = Field(1, ge=1)
    per_page: int = Field(50, ge=1)
    total_items: int = Field(0, ge=0)
    total_pages: int = Field(0, ge=0)


class PhotoGalleryResponse(BaseModel):
    """Gallery response payload."""

    photos: list[PhotoGalleryItem] = Field(default_factory=list)
    pagination: GalleryPagination


class PhotoMetadata(BaseModel):
    """Detailed metadata for a photo."""

    file_size_bytes: int
    width_px: int
    height_px: int
    content_type: str
    exif: dict[str, Any] | None = None


class PhotoProcessingSessionDetail(BaseModel):
    """Extended session information for photo detail view."""

    session_id: UUID
    status: str
    storage_location_id: int | None = None
    storage_location_name: str | None = None
    total_detected: int = 0
    total_estimated: int = 0
    total_empty_containers: int = 0
    avg_confidence: float | None = None
    category_counts: dict[str, int] = Field(default_factory=dict)
    validated: bool = False
    validated_by: str | None = None
    validation_date: datetime | None = None


class StorageLocationHistoryItem(BaseModel):
    """Entry in storage location history timeline."""

    timestamp: datetime
    event: str
    total_plants: int | None = None
    session_id: UUID | None = None
    validated: bool | None = None


class PhotoDetailResponse(BaseModel):
    """Detailed photo response."""

    image_id: UUID
    original_url: str | None = None
    thumbnail_url: str | None = None
    annotated_url: str | None = None
    status: str
    metadata: PhotoMetadata
    processing_session: PhotoProcessingSessionDetail | None = None
    storage_location_history: list[StorageLocationHistoryItem] = Field(default_factory=list)


class PhotoJobStatusItem(BaseModel):
    """Individual job status entry."""

    job_id: str
    image_id: UUID | None = None
    filename: str | None = None
    status: str
    progress_percent: float = Field(0.0, ge=0.0, le=100.0)
    updated_at: datetime | None = None
    result: dict[str, Any] | None = None


class PhotoJobSummary(BaseModel):
    """Aggregated summary for upload session jobs."""

    total_jobs: int = 0
    completed: int = 0
    processing: int = 0
    pending: int = 0
    failed: int = 0
    overall_progress_percent: float = 0.0


class PhotoJobStatusResponse(BaseModel):
    """Response for job status polling endpoint."""

    upload_session_id: UUID
    jobs: list[PhotoJobStatusItem]
    summary: PhotoJobSummary
    last_updated: datetime


class PhotoReprocessRequest(BaseModel):
    """Request body for photo reprocess endpoint."""

    reason: str | None = None
    storage_location_id: int | None = None


class PhotoReprocessResponse(BaseModel):
    """Response returned when reprocess is accepted."""

    upload_session_id: UUID
    image_id: UUID
    new_job_id: str
    message: str
    poll_url: str


class PhotoBatchDeleteRequest(BaseModel):
    """Request body for batch delete endpoint."""

    image_ids: list[UUID] = Field(..., min_length=1)
    reason: str | None = None


class PhotoBatchDeleteResult(BaseModel):
    """Result of batch delete operation."""

    deleted: int = 0
    not_found: list[UUID] = Field(default_factory=list)


class PhotoSessionProgressResponse(BaseModel):
    """Progress response while session is processing."""

    status: str
    progress_percent: float = Field(0.0, ge=0.0, le=100.0)
    images_completed: int = 0
    images_total: int = 0
    images_failed: int = 0
    avg_time_per_image_s: float | None = None
    estimated_remaining_s: float | None = None


class PhotoSessionDownloadLinks(BaseModel):
    """Download links for completed session."""

    pdf_report: str | None = None
    csv_export: str | None = None
    detections_geojson: str | None = None


class PhotoSessionSummaryResponse(BaseModel):
    """Detailed summary returned when session is completed."""

    status: str
    session_id: UUID
    completed_at: datetime | None = None
    plant_detection: dict[str, Any] | None = None
    field_metrics: dict[str, Any] | None = None
    quality: dict[str, Any] | None = None
    download_links: PhotoSessionDownloadLinks | None = None


class PhotoSessionValidationRequest(BaseModel):
    """Request for validating a photo processing session."""

    validated: bool = True
    notes: str | None = None
