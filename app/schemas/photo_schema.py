"""Photo Processing Pydantic schemas (ML pipeline)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class PhotoUploadRequest(BaseModel):
    """Request body for photo upload endpoint."""

    file: bytes = Field(..., description="Photo file bytes")


class PhotoUploadResponse(BaseModel):
    """Response for photo upload endpoint."""

    upload_session_id: UUID = Field(..., description="Upload session UUID used for polling")
    task_id: UUID = Field(..., description="Celery task ID for tracking")
    session_id: int = Field(..., description="Photo processing session ID")
    status: str = Field(..., description="Processing status")
    message: str = Field(..., description="Human-readable message")
    poll_url: str = Field(..., description="URL to poll for results")
    total_photos: int = Field(1, description="Number of photos included in upload", ge=1)
    estimated_time_seconds: int | None = Field(
        None, description="Estimated time to completion (seconds)"
    )
    jobs: list["PhotoUploadJob"] = Field(
        default_factory=list,
        description="Individual job descriptors for polling",
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when upload was accepted",
    )


class PhotoUploadJob(BaseModel):
    """Metadata for individual jobs created during upload."""

    job_id: str = Field(..., description="Celery job identifier")
    image_id: UUID = Field(..., description="Image UUID associated with job")
    filename: str | None = Field(None, description="Original filename (if available)")
    status: str = Field("pending", description="Job status")
    progress_percent: float = Field(0.0, ge=0.0, le=100.0, description="Progress percentage")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Job creation timestamp"
    )


PhotoUploadResponse.model_rebuild()
PhotoUploadJob.model_rebuild()
