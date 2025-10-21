"""Detection Pydantic schemas for ML detection results."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class DetectionCreate(BaseModel):
    """Schema for creating a detection."""

    session_id: int = Field(..., description="Photo processing session ID")
    stock_movement_id: int = Field(..., description="Stock movement ID")
    classification_id: int = Field(..., description="Classification ID")
    center_x_px: Decimal = Field(..., description="Bounding box center X coordinate")
    center_y_px: Decimal = Field(..., description="Bounding box center Y coordinate")
    width_px: int = Field(..., gt=0, description="Bounding box width in pixels")
    height_px: int = Field(..., gt=0, description="Bounding box height in pixels")
    bbox_coordinates: dict = Field(..., description="Full bbox {x1, y1, x2, y2}")
    detection_confidence: Decimal = Field(..., ge=0.0, le=1.0, description="ML confidence score")
    is_empty_container: bool = Field(False, description="Empty container flag")
    is_alive: bool = Field(True, description="Plant alive flag")

    model_config = {"from_attributes": True}


class DetectionBulkCreateRequest(BaseModel):
    """Schema for bulk creating detections."""

    session_id: int = Field(..., description="Photo processing session ID")
    detections: list[DetectionCreate] = Field(..., description="List of detections")

    model_config = {"from_attributes": True}


class DetectionResponse(BaseModel):
    """Schema for detection responses."""

    id: int = Field(..., description="Detection ID")
    session_id: int = Field(...)
    stock_movement_id: int = Field(...)
    classification_id: int = Field(...)
    center_x_px: Decimal = Field(...)
    center_y_px: Decimal = Field(...)
    width_px: int = Field(...)
    height_px: int = Field(...)
    area_px: Decimal | None = Field(None, description="Computed area")
    bbox_coordinates: dict = Field(...)
    detection_confidence: Decimal = Field(...)
    is_empty_container: bool = Field(...)
    is_alive: bool = Field(...)
    created_at: datetime = Field(...)

    model_config = {"from_attributes": True}


class DetectionStatistics(BaseModel):
    """Schema for detection statistics."""

    total_count: int = Field(..., description="Total detections")
    live_count: int = Field(..., description="Live plants count")
    empty_container_count: int = Field(..., description="Empty containers count")
    dead_count: int = Field(..., description="Dead plants count")
    avg_confidence: float = Field(..., description="Average confidence score")
    min_confidence: float = Field(..., description="Minimum confidence score")
    max_confidence: float = Field(..., description="Maximum confidence score")

    model_config = {"from_attributes": True}
