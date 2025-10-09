# [DB012] PhotoProcessingSession Model

## Metadata
- **Epic**: epic-002-database-models.md
- **Sprint**: Sprint-01 (Week 3-4)
- **Status**: `backlog`
- **Priority**: `critical` ⚡ (blocks ML pipeline)
- **Complexity**: M (2 story points)
- **Area**: `database/models`
- **Assignee**: TBD
- **Dependencies**:
  - Blocks: [DB013, DB014, ML002, ML009, CEL005]
  - Blocked by: [DB011-s3-images-model, DB003-storage-locations-model]

## Related Documentation
- **Engineering Plan**: ../../engineering_plan/workflows/README.md
- **Database ERD**: ../../database/database.mmd
- **ML Pipeline Flow**: ../../flows/procesamiento_ml_upload_s3_principal/PIPELINE_OVERVIEW.md
- **Context**: ../../context/past_chats_summary.md (Warning states, not failures)

## Description

Create the `photo_processing_sessions` SQLAlchemy model that tracks each ML processing run from photo upload through detection/estimation to final stock movements. This is the central coordination table for the entire ML pipeline.

**What**: SQLAlchemy model for `photo_processing_sessions` table that stores:
- Link to source photo (S3Image)
- Processing status and progress tracking
- Computed results (total plants, confidence, processing time)
- Link to storage location where photo was taken
- Warning states (NOT failures - see context/past_chats)

**Why**:
- **Pipeline coordination**: One session = one photo processing job
- **Progress tracking**: Frontend polls this table for real-time updates
- **Results aggregation**: After ML processing, aggregates all detections/estimations
- **Audit trail**: Historical record of all ML runs with timestamps

**Context**: This table is queried heavily by the frontend for job status polling. Must be optimized for read performance. Uses **warning states** instead of hard failures (see ADR-008).

## Acceptance Criteria

- [ ] **AC1**: Model created in `app/models/photo_processing_session.py`:
  ```python
  from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Enum
  from sqlalchemy.orm import relationship
  from sqlalchemy.dialects.postgresql import UUID
  from app.models.base import Base

  class PhotoProcessingSession(Base):
      __tablename__ = 'photo_processing_sessions'

      # Primary key
      session_id = Column(Integer, primary_key=True, autoincrement=True)

      # Foreign keys
      source_image_id = Column(
          UUID(as_uuid=True),
          ForeignKey('s3_images.image_id', ondelete='CASCADE'),
          nullable=False
      )
      storage_location_id = Column(
          Integer,
          ForeignKey('storage_locations.location_id', ondelete='SET NULL'),
          nullable=True  # May not have GPS or failed localization
      )

      # Session identification
      session_code = Column(String(100), unique=True, nullable=False)  # e.g., "job-a1b2c3d4"

      # Processing status
      status = Column(
          Enum(
              'pending', 'processing', 'completed', 'failed', 'warning',
              name='session_status_enum'
          ),
          default='pending',
          nullable=False,
          index=True
      )

      # Progress tracking (0.0 to 1.0)
      progress_percent = Column(Float, default=0.0)

      # Results - aggregated after processing
      total_plants_detected = Column(Integer, default=0)
      total_plants_estimated = Column(Integer, default=0)  # Detected + undetected estimation
      average_confidence = Column(Float, nullable=True)

      # Segmentation results
      segmentos_count = Column(Integer, default=0)
      cajones_count = Column(Integer, default=0)

      # Processing metadata
      processing_time_seconds = Column(Float, nullable=True)
      device_type = Column(String(20), default='cpu')  # 'cpu' or 'gpu'
      worker_id = Column(String(50), nullable=True)  # Celery worker ID

      # Warning/error messages (warning state, not failure)
      warning_message = Column(Text, nullable=True)
      error_details = Column(Text, nullable=True)

      # Timestamps
      created_at = Column(DateTime(timezone=True), server_default=func.now())
      started_at = Column(DateTime(timezone=True), nullable=True)
      completed_at = Column(DateTime(timezone=True), nullable=True)

      # Relationships
      source_image = relationship('S3Image', back_populates='processing_sessions')
      storage_location = relationship('StorageLocation', back_populates='processing_sessions')
      detections = relationship('Detection', back_populates='session', cascade='all, delete-orphan')
      estimations = relationship('Estimation', back_populates='session', cascade='all, delete-orphan')
      stock_movements = relationship('StockMovement', back_populates='processing_session')
  ```

- [ ] **AC2**: Status enum includes **warning state** (not just success/failure):
  ```sql
  CREATE TYPE session_status_enum AS ENUM (
      'pending',      -- Queued, not started
      'processing',   -- Currently running
      'completed',    -- Successfully finished
      'failed',       -- Critical failure (e.g., image corrupt)
      'warning'       -- Completed with warnings (e.g., low confidence, missing GPS)
  );
  ```

- [ ] **AC3**: Indexes for common queries:
  ```sql
  CREATE INDEX idx_sessions_status ON photo_processing_sessions(status);
  CREATE INDEX idx_sessions_created_at ON photo_processing_sessions(created_at DESC);
  CREATE INDEX idx_sessions_location ON photo_processing_sessions(storage_location_id);
  CREATE INDEX idx_sessions_code ON photo_processing_sessions(session_code);
  ```

- [ ] **AC4**: `session_code` format validation:
  - Pattern: `job-{uuid}`
  - Example: `job-a1b2c3d4-e5f6-7890-abcd-ef1234567890`
  - Generated in service layer when creating session

- [ ] **AC5**: Progress tracking logic:
  ```python
  # Enum for progress stages
  # 0.0 = pending
  # 0.2 = segmentation complete
  # 0.5 = detection complete
  # 0.8 = estimation complete
  # 1.0 = aggregation complete
  ```

- [ ] **AC6**: Cascade deletes configured:
  - If S3Image deleted → session deleted (CASCADE)
  - If Session deleted → detections/estimations deleted (CASCADE)
  - If StorageLocation deleted → session.storage_location_id = NULL (SET NULL)

- [ ] **AC7**: Alembic migration created and tested

## Technical Implementation Notes

### Architecture
- Layer: Database / Models
- Dependencies: DB011 (S3Image), DB003 (StorageLocation), SQLAlchemy 2.0.43
- Design pattern: Aggregate root for ML pipeline results

### Code Hints

**Status transitions:**
```python
# Valid transitions:
# pending → processing → completed
# pending → processing → warning (completed with issues)
# pending → processing → failed

@validates('status')
def validate_status_transition(self, key, new_status):
    """Validate status state machine transitions"""
    if self.status == 'completed' and new_status != 'completed':
        raise ValueError("Cannot change status from completed")
    return new_status
```

**Progress calculation example (in service layer):**
```python
async def update_progress(session_id: int, stage: str):
    progress_map = {
        'segmentation_done': 0.2,
        'detection_done': 0.5,
        'estimation_done': 0.8,
        'aggregation_done': 1.0
    }
    await session_repo.update(
        session_id,
        {
            'progress_percent': progress_map[stage],
            'status': 'processing'
        }
    )
```

**Warning state usage:**
```python
# Scenario: Low confidence but processing succeeded
session.status = 'warning'
session.warning_message = (
    "Processing completed but average confidence is below 60%. "
    "Manual review recommended."
)
session.average_confidence = 0.52
```

### Testing Requirements

**Unit Tests** (`tests/models/test_photo_processing_session.py`):
```python
def test_session_code_format():
    """Session code follows job-{uuid} pattern"""
    session = PhotoProcessingSession(
        session_code="job-a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        source_image_id=uuid4()
    )
    assert session.session_code.startswith("job-")
    assert len(session.session_code) == 40  # "job-" + 36 char UUID

def test_status_enum_values():
    """Status accepts all valid enum values"""
    session = PhotoProcessingSession(...)
    for status in ['pending', 'processing', 'completed', 'failed', 'warning']:
        session.status = status  # Should not raise

def test_progress_bounds():
    """Progress is between 0.0 and 1.0"""
    session = PhotoProcessingSession(...)
    session.progress_percent = 0.5
    assert 0.0 <= session.progress_percent <= 1.0
```

**Integration Tests** (`tests/integration/test_session_lifecycle.py`):
```python
@pytest.mark.asyncio
async def test_session_creation_and_completion(db_session):
    """Test full session lifecycle"""
    # Create session
    image = S3Image(...)
    await db_session.add(image)
    await db_session.commit()

    session = PhotoProcessingSession(
        session_code="job-test-123",
        source_image_id=image.image_id,
        status='pending'
    )
    db_session.add(session)
    await db_session.commit()

    # Update to processing
    session.status = 'processing'
    session.started_at = datetime.utcnow()
    await db_session.commit()

    # Complete
    session.status = 'completed'
    session.completed_at = datetime.utcnow()
    session.progress_percent = 1.0
    session.total_plants_detected = 575
    await db_session.commit()

    assert session.status == 'completed'
    assert session.progress_percent == 1.0

@pytest.mark.asyncio
async def test_cascade_delete_detections(db_session):
    """When session deleted, detections are also deleted"""
    session = PhotoProcessingSession(...)
    detection1 = Detection(session_id=session.session_id, ...)
    detection2 = Detection(session_id=session.session_id, ...)

    db_session.add_all([session, detection1, detection2])
    await db_session.commit()

    await db_session.delete(session)
    await db_session.commit()

    # Detections should be gone (cascade)
    result = await db_session.execute(
        select(Detection).where(Detection.session_id == session.session_id)
    )
    assert len(result.all()) == 0
```

**Coverage Target**: ≥80%

### Performance Expectations
- Insert: <10ms
- Update status/progress: <5ms (indexed column)
- Retrieve by session_code: <5ms (unique index)
- Poll query (status + created_at): <20ms for 10k sessions

## Handover Briefing

**For the next developer:**

**Context**: This model is the **control center** for ML processing. Frontend polls this table every 2 seconds to show progress bars. Backend Celery tasks update this table at each pipeline stage.

**Key decisions made**:
1. **Warning state introduced**: Not all issues are failures. Warning = "completed but review recommended" (e.g., low confidence, missing GPS)
2. **Progress percent**: Enum-based stages (0.2, 0.5, 0.8, 1.0) for predictable progress bars
3. **Session code format**: `job-{uuid}` for URL-friendly IDs (frontend uses this in routes)
4. **Cascade deletes**: Session owns detections/estimations (delete session → delete children)
5. **NULL storage_location**: Allowed because GPS may be missing or localization may fail

**Known limitations**:
- Progress is coarse-grained (20% increments) - fine for user experience but not exact
- No retry mechanism in model (handled by Celery layer)

**Next steps after this card**:
- DB013: Detections model (partitioned, child of session)
- DB014: Estimations model (partitioned, child of session)
- ML002: YOLO Segmentation service (writes to this table)
- CEL005: ML Parent Task (creates session, spawns children)

**Questions to validate**:
- Does frontend poll `status` and `progress_percent`? (Should be YES)
- Is there a timeout mechanism for stuck `processing` status? (Should be: Celery task timeout + cleanup job)
- How are warning states displayed to users? (Should be: yellow badge, not red error)

## Definition of Done Checklist

- [ ] Model code written in `app/models/photo_processing_session.py`
- [ ] Enum type `session_status_enum` created
- [ ] Alembic migration created and tested (upgrade + downgrade)
- [ ] Relationships to S3Image, StorageLocation, Detections, Estimations configured
- [ ] Cascade delete behavior tested
- [ ] Indexes created and verified
- [ ] Unit tests pass (≥80% coverage)
- [ ] Integration tests with lifecycle simulation pass
- [ ] Warning state documented in model docstring
- [ ] PR reviewed and approved (2+ reviewers)
- [ ] No linting errors (`ruff check`)

## Time Tracking
- **Estimated**: 2 story points
- **Actual**: TBD
- **Started**: TBD
- **Completed**: TBD

---

**Card Created**: 2025-10-09
**Last Updated**: 2025-10-09
**Card Owner**: TBD
