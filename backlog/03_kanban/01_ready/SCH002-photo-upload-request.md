# [SCH002] PhotoUploadRequest/Response Schemas

## Metadata

- **Epic**: epic-003-backend-implementation.md
- **Sprint**: Sprint-02
- **Status**: `backlog`
- **Priority**: `critical`
- **Complexity**: S (1 story point)
- **Area**: `backend/schemas`
- **Assignee**: TBD

## Description

Pydantic schemas for photo upload endpoint (request and response).

## Acceptance Criteria

- [ ] **AC1**: PhotoUploadResponse schema:
  ```python
  from pydantic import BaseModel, Field
  from uuid import UUID

  class PhotoUploadResponse(BaseModel):
      """Response schema for photo upload."""

      task_id: UUID = Field(
          ...,
          description="Celery task ID for polling status",
          example="550e8400-e29b-41d4-a716-446655440000"
      )

      session_id: int = Field(
          ...,
          description="Photo processing session ID",
          example=123
      )

      status: str = Field(
          ...,
          description="Processing status",
          example="processing"
      )

      message: str = Field(
          ...,
          description="User-friendly message",
          example="Photo uploaded successfully. Check status with task_id."
      )

      poll_url: str = Field(
          ...,
          description="URL to poll task status",
          example="/api/stock/tasks/status?task_id=550e8400-..."
      )

      class Config:
          json_schema_extra = {
              "example": {
                  "task_id": "550e8400-e29b-41d4-a716-446655440000",
                  "session_id": 123,
                  "status": "processing",
                  "message": "Photo uploaded successfully",
                  "poll_url": "/api/stock/tasks/status?task_id=..."
              }
          }
  ```

- [ ] **AC2**: OpenAPI examples

**Coverage Target**: ≥80%

## Time Tracking

- **Estimated**: 1 story point

---

**Card Created**: 2025-10-09
