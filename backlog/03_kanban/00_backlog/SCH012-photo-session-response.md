# [SCH012] PhotoSessionResponse Schema

## Metadata
- **Epic**: epic-003-backend-implementation.md
- **Sprint**: Sprint-03
- **Status**: `backlog`
- **Priority**: `medium`
- **Complexity**: M (2 story points)
- **Area**: `backend/schemas`

## Description

Response schema for photo processing sessions.

## Acceptance Criteria

- [ ] **AC1**: Schema defined:
  ```python
  class PhotoSessionResponse(BaseModel):
      """Response schema for photo processing session."""

      session_id: int
      user_id: int
      storage_location_id: Optional[int]
      warehouse_id: Optional[int]

      # Status
      status: str  # pending, processing, completed, failed, warning
      celery_task_id: Optional[UUID]

      # Photo info
      original_photo_s3_key: str
      processed_photo_s3_key: Optional[str]
      photo_timestamp: Optional[datetime]

      # GPS
      latitude: Optional[float]
      longitude: Optional[float]

      # Results
      total_detections: Optional[int]
      total_estimations: Optional[int]

      # Metadata
      created_at: datetime
      completed_at: Optional[datetime]
      error_message: Optional[str]

      class Config:
          from_attributes = True

      @classmethod
      def from_model(cls, session):
          return cls(
              session_id=session.session_id,
              user_id=session.user_id,
              storage_location_id=session.storage_location_id,
              warehouse_id=session.warehouse_id,
              status=session.status,
              celery_task_id=session.celery_task_id,
              original_photo_s3_key=session.original_photo_s3_key,
              processed_photo_s3_key=session.processed_photo_s3_key,
              photo_timestamp=session.photo_timestamp,
              latitude=session.latitude,
              longitude=session.longitude,
              total_detections=session.total_detections,
              total_estimations=session.total_estimations,
              created_at=session.created_at,
              completed_at=session.completed_at,
              error_message=session.error_message
          )
  ```

**Coverage Target**: ≥80%

---

**Card Created**: 2025-10-09
