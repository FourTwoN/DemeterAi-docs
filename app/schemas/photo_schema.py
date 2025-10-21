"""Photo Processing Pydantic schemas (ML pipeline)."""

from uuid import UUID

from pydantic import BaseModel, Field


class PhotoUploadRequest(BaseModel):
    """Request body for photo upload endpoint."""

    file: bytes = Field(..., description="Photo file bytes")


class PhotoUploadResponse(BaseModel):
    """Response for photo upload endpoint."""

    task_id: UUID = Field(..., description="Celery task ID for tracking")
    session_id: int = Field(..., description="Photo processing session ID")
    status: str = Field(..., description="Processing status")
    message: str = Field(..., description="Human-readable message")
    poll_url: str = Field(..., description="URL to poll for results")
