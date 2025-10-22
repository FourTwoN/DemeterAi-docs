"""Photo Processing Session Pydantic schemas.

This module defines request/response schemas for photo processing sessions.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.models.photo_processing_session import ProcessingSessionStatusEnum


class PhotoProcessingSessionCreate(BaseModel):
    """Schema for creating a photo processing session."""

    storage_location_id: int | None = Field(None, description="Storage location ID (optional)")
    original_image_id: UUID = Field(..., description="Original S3 image UUID")
    processed_image_id: UUID | None = Field(None, description="Processed S3 image UUID (optional)")
    status: ProcessingSessionStatusEnum | None = Field(
        ProcessingSessionStatusEnum.PENDING, description="Processing status"
    )
    total_detected: int = Field(0, ge=0, description="Total detections count")
    total_estimated: int = Field(0, ge=0, description="Total estimations count")
    total_empty_containers: int = Field(0, ge=0, description="Empty container count")
    avg_confidence: float | None = Field(None, ge=0.0, le=1.0, description="Average ML confidence")
    category_counts: dict[str, int] | None = Field(
        default_factory=dict, description="Detection counts by category"
    )
    manual_adjustments: dict[str, Any] | None = Field(
        default_factory=dict, description="User adjustments to ML results"
    )
    error_message: str | None = Field(None, description="Error message if failed")

    model_config = {"from_attributes": True}


class PhotoProcessingSessionUpdate(BaseModel):
    """Schema for updating a photo processing session."""

    storage_location_id: int | None = Field(None)
    processed_image_id: UUID | None = Field(None)
    status: ProcessingSessionStatusEnum | None = Field(None)
    total_detected: int | None = Field(None, ge=0)
    total_estimated: int | None = Field(None, ge=0)
    total_empty_containers: int | None = Field(None, ge=0)
    avg_confidence: float | None = Field(None, ge=0.0, le=1.0)
    category_counts: dict[str, int] | None = Field(None)
    manual_adjustments: dict[str, Any] | None = Field(None)
    error_message: str | None = Field(None)
    validated: bool | None = Field(None)
    validated_by_user_id: int | None = Field(None)
    validation_date: datetime | None = Field(None)

    model_config = {"from_attributes": True}


class PhotoProcessingSessionResponse(BaseModel):
    """Schema for photo processing session responses."""

    id: int = Field(..., description="Database ID")
    session_id: UUID = Field(..., description="Session UUID")
    storage_location_id: int | None = Field(None)
    original_image_id: UUID = Field(...)
    processed_image_id: UUID | None = Field(None)
    total_detected: int = Field(...)
    total_estimated: int = Field(...)
    total_empty_containers: int = Field(...)
    avg_confidence: float | None = Field(None)
    category_counts: dict[str, int] = Field(default_factory=dict)
    status: ProcessingSessionStatusEnum = Field(...)
    error_message: str | None = Field(None)
    validated: bool = Field(...)
    validated_by_user_id: int | None = Field(None)
    validation_date: datetime | None = Field(None)
    manual_adjustments: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(...)
    updated_at: datetime | None = Field(None)

    model_config = {"from_attributes": True}

    @field_validator("category_counts", "manual_adjustments", mode="before")
    @classmethod
    def ensure_dict(cls, v: Any) -> dict[str, Any]:
        """Ensure JSONB fields are dicts, not None."""
        return v if v is not None else {}
