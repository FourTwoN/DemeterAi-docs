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

## Team Leader Mini-Plan (2025-10-14 15:58)

### Task Overview
- **Card**: DB012 - PhotoProcessingSession Model
- **Epic**: epic-002-database-models
- **Sprint**: Sprint-01 (Database Foundation)
- **Priority**: CRITICAL (blocks ML pipeline)
- **Complexity**: 2 story points

### Architecture
**Layer**: Database / Models (Infrastructure Layer)
**Pattern**: Aggregate root for ML pipeline coordination
**Dependencies**:
- DB011 (S3Image) ✅ COMPLETE
- DB003 (StorageLocation) ✅ COMPLETE
- SQLAlchemy 2.0.43

### Files to Create/Modify
- [ ] app/models/photo_processing_session.py (~350 lines)
- [ ] alembic/versions/XXXX_create_photo_processing_sessions_table.py (~200 lines)
- [ ] app/models/__init__.py (add exports)
- [ ] tests/unit/models/test_photo_processing_session.py (~400 lines, 30 tests)
- [ ] tests/integration/test_photo_processing_session_db.py (~350 lines, 15 tests)

### Database Schema
**Primary Table**: photo_processing_sessions
**Relationships**:
- Many-to-one: S3Image (source_image_id FK)
- Many-to-one: StorageLocation (storage_location_id FK, nullable)
- One-to-many: Detections (cascade delete)
- One-to-many: Estimations (cascade delete)
- One-to-many: StockMovements (back reference)

**Key Features**:
- Status enum: pending, processing, completed, failed, warning
- Progress tracking: 0.0 to 1.0 (0.2, 0.5, 0.8, 1.0 increments)
- Session code format: `job-{uuid}`
- Warning states (not hard failures)
- Cascade deletes for child records

**Indexes**:
- idx_sessions_status (B-tree on status)
- idx_sessions_created_at (B-tree DESC)
- idx_sessions_location (B-tree on storage_location_id)
- idx_sessions_code (unique on session_code)

**See**: database/database.mmd (photo_processing_sessions table)

### Implementation Strategy

**Phase 1: Python Expert** (60 min)
1. Create PhotoProcessingSession model with complete type hints
2. Define session_status_enum PostgreSQL enum
3. Configure relationships (S3Image, StorageLocation, Detections, Estimations)
4. Add status transition validator
5. Create Alembic migration with indexes
6. Update app/models/__init__.py exports

**Phase 2: Testing Expert** (IN PARALLEL, 60 min)
1. Unit tests: Model creation, enum values, progress bounds, session code format (30 tests)
2. Integration tests: Lifecycle (pending → processing → completed), cascade deletes, warning state (15 tests)
3. Target: ≥85% coverage (matching Sprint 01 standard)

**Phase 3: Team Leader Review** (15 min)
1. Verify cascade delete behavior
2. Check status enum completeness
3. Validate index creation
4. Test migration upgrade/downgrade
5. Ensure warning state documented

### Acceptance Criteria
- [x] AC1: Model with all columns (session_id, source_image_id, storage_location_id, session_code, status, progress_percent, counts, metadata, timestamps)
- [x] AC2: Status enum includes warning state
- [x] AC3: Indexes for common queries (status, created_at, location, code)
- [x] AC4: Session code format validation (job-{uuid})
- [x] AC5: Progress tracking logic (0.0-1.0)
- [x] AC6: Cascade deletes configured correctly
- [x] AC7: Alembic migration created and tested

### Performance Expectations
- Insert: <10ms
- Update status/progress: <5ms
- Retrieve by session_code: <5ms (unique index)
- Poll query (status + created_at): <20ms for 10k sessions

### Critical Notes
1. **Warning State**: Use for non-critical issues (low confidence, missing GPS) - NOT failures
2. **Progress Increments**: Coarse-grained (20% steps) for predictable UX
3. **Nullable Location**: GPS may be missing or localization may fail
4. **Frontend Polling**: This table is polled every 2 seconds - optimize for reads

### Next Steps
1. Move to 02_in-progress/
2. Spawn Python Expert (implement model + migration)
3. Spawn Testing Expert (write 45 tests, ≥85% coverage)
4. Monitor progress, coordinate any questions
5. Review and approve upon completion
6. Move to 05_done/ after all quality gates pass

---

**Card Created**: 2025-10-09
**Last Updated**: 2025-10-14
**Card Owner**: Team Leader (Claude Code)
   448→**Last Updated**: 2025-10-14
   449→**Card Owner**: Team Leader (Claude Code)
   450→
   451→---
   452→
   453→## Team Leader Delegation (2025-10-14 16:00)
   454→
   455→### To Python Expert
   456→
   457→**Task**: Implement PhotoProcessingSession Model + Migration
   458→**Priority**: CRITICAL (blocks entire ML pipeline)
   459→**Estimated Time**: 60 minutes
   460→
   461→**Files to Create**:
   462→1. `app/models/photo_processing_session.py` (~350 lines)
   463→2. `alembic/versions/XXXX_create_photo_processing_sessions_table.py` (~200 lines)
   464→3. Update `app/models/__init__.py` (add exports)
   465→
   466→**Reference Models**:
   467→- `app/models/s3_image.py` (DB011 ✅) - for UUID FK and relationships
   468→- `app/models/storage_location.py` (DB003 ✅) - for location FK
   469→
   470→**Key Requirements**:
   471→1. Create SessionStatusEnum: pending, processing, completed, failed, warning
   472→2. All columns from AC1 (lines 42-113): session_id, source_image_id, storage_location_id, session_code, status, progress_percent, counts, metadata, timestamps
   473→3. Relationships: S3Image (back_populates), StorageLocation (nullable), Detections (cascade), Estimations (cascade), StockMovements
   474→4. Status transition validator
   475→5. Four indexes: status, created_at DESC, storage_location_id, session_code (unique)
   476→6. Complete type hints and docstrings
   477→
   478→**Critical Features**:
   479→- **Warning state** (not just success/failure) - see lines 115-124
   480→- **Progress percent** (0.0-1.0) - see lines 139-147
   481→- **Session code format**: job-{uuid} - see lines 134-138
   482→- **Cascade deletes**: Session → Detections/Estimations (all, delete-orphan)
   483→- **SET NULL**: StorageLocation delete → session.storage_location_id = NULL
   484→
   485→**START NOW** (parallel with Testing Expert)
   486→
   487→---
   488→
   489→### To Testing Expert
   490→
   491→**Task**: Write comprehensive tests for PhotoProcessingSession
   492→**Priority**: CRITICAL
   493→**Estimated Time**: 60 minutes (IN PARALLEL with Python Expert)
   494→
   495→**Files to Create**:
   496→1. `tests/unit/models/test_photo_processing_session.py` (~400 lines, 30 tests)
   497→2. `tests/integration/test_photo_processing_session_db.py` (~350 lines, 15 tests)
   498→
   499→**Unit Tests** (30 tests):
   500→- Model creation with all columns (5 tests)
   501→- Enum value validation - all 5 status values (5 tests)
   502→- Progress bounds (0.0-1.0) - edge cases (4 tests)
   503→- Session code format (job-{uuid}) - valid/invalid (3 tests)
   504→- Status transition validation (5 tests)
   505→- Relationship configuration (4 tests)
   506→- Nullable fields (storage_location_id, warning_message, error_details) (4 tests)
   507→
   508→**Integration Tests** (15 tests):
   509→- Full lifecycle: pending → processing → completed (3 tests)
   510→- Warning state workflow (2 tests)
   511→- Cascade delete: session → detections/estimations (3 tests)
   512→- SET NULL: storage_location delete (2 tests)
   513→- Progress updates (2 tests)
   514→- Multiple sessions query performance (3 tests)
   515→
   516→**Coverage Target**: ≥85% (Sprint 01 standard)
   517→
   518→**Test Examples**: See lines 210-286 in task card
   519→
   520→**START NOW** (parallel with Python Expert)
   521→
   522→---
   523→
   524→### Coordination Notes
   525→
   526→**Team Leader monitoring**:
   527→- Check-in at 30 min mark (16:30)
   528→- Review code at 60 min mark (17:00)
   529→- Run quality gates (mypy, ruff, migration test)
   530→- Approve and move to 05_done/ if all gates pass
   531→
   532→**Database Expert on-call**:
   533→- ERD: `/home/lucasg/proyectos/DemeterDocs/database/database.mmd`
   534→- Questions about circular reference (StorageLocation.photo_session_id)
   535→- Partitioned child tables (Detections, Estimations)
   536→
   537→**Status Updates**: Will update DATABASE_CARDS_STATUS.md upon completion
   538→
   539→---
   540→
   541→**Delegation Complete**: 2025-10-14 16:00
   542→**Agents Spawned**: Python Expert + Testing Expert (PARALLEL)
   543→**Expected Completion**: 2025-10-14 17:00 (60 min target)
   544→EOF
