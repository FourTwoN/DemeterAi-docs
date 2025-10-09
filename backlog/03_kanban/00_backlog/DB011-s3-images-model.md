# [DB011] S3Images Model - UUID Primary Key

## Metadata
- **Epic**: epic-002-database-models.md
- **Sprint**: Sprint-01 (Week 3-4)
- **Status**: `backlog`
- **Priority**: `critical` ⚡ (blocks ML pipeline)
- **Complexity**: M (2 story points)
- **Area**: `database/models`
- **Assignee**: TBD
- **Dependencies**:
  - Blocks: [DB012, ML001, ML002, CEL001]
  - Blocked by: [F007-alembic-setup]

## Related Documentation
- **Engineering Plan**: ../../engineering_plan/database/README.md
- **Database ERD**: ../../database/database.mmd
- **ADR**: ../../backlog/09_decisions/ADR-002-uuid-s3-images.md
- **Context**: ../../context/past_chats_summary.md (UUID vs SERIAL decision)

## Description

Create the `s3_images` SQLAlchemy model with **UUID primary key** (NOT database SERIAL). This is a critical architectural decision that enables S3 key pre-generation and prevents race conditions in distributed systems.

**What**: SQLAlchemy model for the `s3_images` table that stores original and processed photo metadata with S3 URLs. Uses UUID as primary key, generated in the API layer before database insert.

**Why**:
- **Pre-generation**: S3 keys need to be known before DB row exists (`s3://bucket/original/{uuid}.jpg`)
- **Idempotency**: Retry-safe uploads (same UUID = same S3 key)
- **Distributed systems**: Multiple API servers can generate UUIDs independently without coordination
- **Race condition prevention**: No "insert then get ID" pattern needed

**Context**: This table is the foundation of the entire photo processing pipeline. Every photo uploaded goes through this table, which then triggers ML processing via `photo_processing_sessions`.

## Acceptance Criteria

- [ ] **AC1**: Model created in `app/models/s3_images.py`:
  ```python
  from sqlalchemy import Column, String, Integer, DateTime, Text, Enum
  from sqlalchemy.dialects.postgresql import UUID
  import uuid
  from app.models.base import Base

  class S3Image(Base):
      __tablename__ = 's3_images'

      # UUID primary key (generated in API, not DB)
      image_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

      # S3 paths
      original_s3_url = Column(String(512), nullable=False)
      processed_s3_url = Column(String(512), nullable=True)
      thumbnail_s3_url = Column(String(512), nullable=True)

      # Image metadata
      filename = Column(String(255), nullable=False)
      file_size_bytes = Column(Integer, nullable=False)
      image_format = Column(String(10), nullable=False)  # jpg, png, avif

      # Dimensions
      width_px = Column(Integer, nullable=False)
      height_px = Column(Integer, nullable=False)

      # EXIF data
      gps_latitude = Column(Numeric(10, 7), nullable=True)
      gps_longitude = Column(Numeric(10, 7), nullable=True)
      capture_datetime = Column(DateTime(timezone=True), nullable=True)
      camera_model = Column(String(100), nullable=True)

      # Lifecycle
      upload_status = Column(
          Enum('pending', 'uploaded', 'failed', name='upload_status_enum'),
          default='pending',
          nullable=False
      )

      # Timestamps
      created_at = Column(DateTime(timezone=True), server_default=func.now())
      updated_at = Column(DateTime(timezone=True), onupdate=func.now())
  ```

- [ ] **AC2**: UUID generation happens in API layer (NOT database default):
  - When creating new image: `image_id = uuid.uuid4()` in service/controller
  - S3 key uses this UUID: `f"original/{year}/{month}/{day}/{image_id}.jpg"`
  - Then insert into database with pre-generated UUID

- [ ] **AC3**: Enum type `upload_status_enum` created in migration:
  ```sql
  CREATE TYPE upload_status_enum AS ENUM ('pending', 'uploaded', 'failed');
  ```

- [ ] **AC4**: Indexes created for common queries:
  ```sql
  CREATE INDEX idx_s3_images_status ON s3_images(upload_status);
  CREATE INDEX idx_s3_images_created_at ON s3_images(created_at DESC);
  CREATE INDEX idx_s3_images_gps ON s3_images(gps_latitude, gps_longitude) WHERE gps_latitude IS NOT NULL;
  ```

- [ ] **AC5**: Relationship to `photo_processing_sessions`:
  ```python
  # In S3Image model:
  processing_sessions = relationship(
      'PhotoProcessingSession',
      back_populates='source_image',
      lazy='selectinload'
  )
  ```

- [ ] **AC6**: Alembic migration created and tested (upgrade + downgrade)

- [ ] **AC7**: Model validates GPS coordinates:
  - Latitude: -90 to +90
  - Longitude: -180 to +180
  - Use SQLAlchemy CheckConstraint or @validates

## Technical Implementation Notes

### Architecture
- Layer: Database / Models
- Dependencies: F007 (Alembic), SQLAlchemy 2.0.43, PostgreSQL 18
- Design pattern: UUID primary key (ADR-002)

### Code Hints

**UUID import and usage:**
```python
from sqlalchemy.dialects.postgresql import UUID
import uuid

# Model field
image_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
```

**⚠️ CRITICAL**: The `default=uuid.uuid4` is a fallback. In practice, always generate UUID in the service layer:
```python
# In service layer (CORRECT):
from uuid import uuid4

def create_image_record(file):
    image_id = uuid4()  # Generate in Python
    s3_key = f"original/{image_id}.jpg"
    # Upload to S3 first
    s3_client.upload(file, s3_key)
    # Then insert to DB
    db_image = S3Image(
        image_id=image_id,  # Pre-generated
        original_s3_url=f"s3://bucket/{s3_key}",
        ...
    )
    session.add(db_image)
    return image_id
```

**GPS validation:**
```python
from sqlalchemy.orm import validates

@validates('gps_latitude')
def validate_latitude(self, key, value):
    if value is not None and not (-90 <= value <= 90):
        raise ValueError("Latitude must be between -90 and +90")
    return value

@validates('gps_longitude')
def validate_longitude(self, key, value):
    if value is not None and not (-180 <= value <= 180):
        raise ValueError("Longitude must be between -180 and +180")
    return value
```

### Testing Requirements

**Unit Tests** (`tests/models/test_s3_image.py`):
```python
import pytest
from uuid import UUID
from app.models.s3_images import S3Image

def test_s3_image_uuid_primary_key():
    """UUID is valid UUID4 format"""
    image = S3Image(
        image_id=uuid4(),
        original_s3_url="s3://bucket/test.jpg",
        filename="test.jpg",
        file_size_bytes=1024,
        image_format="jpg",
        width_px=4000,
        height_px=3000
    )
    assert isinstance(image.image_id, UUID)

def test_gps_validation():
    """GPS coordinates validated correctly"""
    image = S3Image(...)

    # Valid
    image.gps_latitude = 45.5
    image.gps_longitude = -122.6

    # Invalid latitude
    with pytest.raises(ValueError):
        image.gps_latitude = 91.0

    # Invalid longitude
    with pytest.raises(ValueError):
        image.gps_longitude = 181.0

def test_upload_status_enum():
    """Upload status accepts only valid enum values"""
    image = S3Image(...)
    image.upload_status = 'uploaded'  # Valid

    with pytest.raises(StatementError):
        image.upload_status = 'invalid'  # Should fail
```

**Integration Tests** (`tests/integration/test_s3_image_db.py`):
```python
@pytest.mark.asyncio
async def test_s3_image_insert_with_uuid(db_session):
    """Test UUID-based insert into database"""
    image_id = uuid4()

    image = S3Image(
        image_id=image_id,
        original_s3_url=f"s3://bucket/{image_id}.jpg",
        filename="greenhouse.jpg",
        file_size_bytes=2048000,
        image_format="jpg",
        width_px=4000,
        height_px=3000,
        gps_latitude=-33.4489,
        gps_longitude=-70.6483
    )

    db_session.add(image)
    await db_session.commit()

    # Verify retrieval
    result = await db_session.get(S3Image, image_id)
    assert result.image_id == image_id
    assert result.original_s3_url.endswith(f"{image_id}.jpg")
```

**Coverage Target**: ≥85% (critical model)

### Performance Expectations
- Insert time: <10ms (UUID index is B-tree, same as SERIAL)
- Retrieval by UUID: <5ms (primary key lookup)
- GPS index query: <50ms for 10k rows

## Handover Briefing

**For the next developer:**

**Context**: This is the FIRST model in the ML pipeline chain. Everything flows from here:
```
S3Image → PhotoProcessingSession → Detections → Estimations → StockMovements
```

**Key decisions made**:
1. **UUID vs SERIAL**: UUID chosen for S3 key pre-generation and distributed system safety (see ADR-002)
2. **API-generated UUID**: NOT database default. Service layer generates UUID before S3 upload.
3. **Enum for upload_status**: Three states (pending, uploaded, failed) - simple state machine
4. **Optional GPS**: Not all photos have GPS (manual uploads from desktop)
5. **AVIF support**: Future-proofing for compressed format (50% smaller than JPEG)

**Known limitations**:
- UUID takes 16 bytes vs SERIAL 8 bytes (acceptable tradeoff for benefits)
- No automatic UUID generation in DB (intentional - must be API-generated)

**Next steps after this card**:
- DB012: PhotoProcessingSession model (references this via `source_image_id`)
- DB013: Detections model (partitioned table, references sessions)
- ML001: Model Singleton (needs S3Image to store results)

**Questions to validate**:
- Does the service layer generate UUID before S3 upload? (Should be YES)
- Is there a fallback mechanism if S3 upload succeeds but DB insert fails? (Should be: delete S3 file and retry)

## Definition of Done Checklist

- [ ] Model code written in `app/models/s3_images.py`
- [ ] Alembic migration created (`alembic revision --autogenerate -m "add s3_images table"`)
- [ ] Migration tested (upgrade + downgrade)
- [ ] Unit tests pass (≥85% coverage)
- [ ] Integration tests with real DB pass
- [ ] GPS validation working (latitude/longitude bounds)
- [ ] Enum type created and working
- [ ] Indexes created and verified with EXPLAIN ANALYZE
- [ ] PR reviewed and approved (2+ reviewers)
- [ ] No linting errors (`ruff check`)
- [ ] Documentation added (model docstring, field comments)

## Time Tracking
- **Estimated**: 2 story points
- **Actual**: TBD (fill after completion)
- **Started**: TBD
- **Completed**: TBD

---

**Card Created**: 2025-10-09
**Last Updated**: 2025-10-09
**Card Owner**: TBD (assign during sprint planning)
