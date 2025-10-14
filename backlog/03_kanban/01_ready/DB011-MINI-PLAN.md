# DB011 Mini-Plan: S3Images Model (UUID Primary Key)

**Task**: Implement S3Images model with UUID primary key (NOT SERIAL)
**Complexity**: 2 story points (MEDIUM - UUID + GPS validation + enums)
**Estimated Time**: 60-90 minutes
**Priority**: CRITICAL (blocks DB012 PhotoProcessingSessions, entire ML pipeline)

---

## Strategic Context

**What**: S3Images table stores metadata for all uploaded photos with S3 URLs
**Why**: Foundation of photo processing pipeline; UUID enables S3 key pre-generation
**Where in Pipeline**:
```
Upload → Generate UUID → S3 Upload (using UUID) → DB Insert → ML Processing
```

**Key Insight**: UUID is generated in API layer BEFORE S3 upload, not in database
- **Problem**: S3 key must be known before DB row exists
- **Solution**: API generates UUID first, uses it for S3 key, then inserts to DB
- **Benefit**: Idempotent uploads (retry-safe), no race conditions

---

## Technical Approach

### 1. Model Structure (20 min)

**File**: `app/models/s3_image.py`

```python
from sqlalchemy import Column, String, Integer, BigInteger, DateTime, Text, Enum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, validates
from app.models.base import Base
import uuid

class S3Image(Base):
    __tablename__ = 's3_images'

    # UUID primary key (API-generated, not DB default)
    image_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4  # Fallback only (should be set explicitly)
    )

    # S3 storage paths
    s3_bucket = Column(String(255), nullable=False)
    s3_key_original = Column(String(512), nullable=False, unique=True)
    s3_key_thumbnail = Column(String(512), nullable=True)

    # File metadata
    content_type = Column(
        Enum('image/jpeg', 'image/png', name='image_content_type_enum'),
        nullable=False
    )
    file_size_bytes = Column(BigInteger, nullable=False)  # Large files > 4GB
    width_px = Column(Integer, nullable=False)
    height_px = Column(Integer, nullable=False)

    # EXIF metadata (JSON)
    exif_metadata = Column(JSONB, nullable=True)

    # GPS coordinates (for storage location matching)
    gps_coordinates = Column(JSONB, nullable=True)  # {lat, lng, altitude, accuracy}

    # Upload tracking
    upload_source = Column(
        Enum('web', 'mobile', 'api', name='upload_source_enum'),
        nullable=False,
        default='web'
    )
    uploaded_by_user_id = Column(
        Integer,
        ForeignKey('users.id', ondelete='SET NULL'),
        nullable=True  # Anonymous uploads allowed
    )

    # Processing status
    status = Column(
        Enum('uploaded', 'processing', 'ready', 'failed', name='image_status_enum'),
        nullable=False,
        default='uploaded',
        index=True
    )
    error_details = Column(Text, nullable=True)
    processing_status_updated_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    uploaded_by = relationship('User', back_populates='uploaded_images')
    processing_sessions = relationship(
        'PhotoProcessingSession',
        back_populates='source_image',
        cascade='all, delete-orphan'
    )
    product_samples = relationship(
        'ProductSampleImage',
        back_populates='image',
        cascade='all, delete-orphan'
    )

    @validates('gps_coordinates')
    def validate_gps(self, key, value):
        """Validate GPS coordinates format and bounds"""
        if value is not None:
            if not isinstance(value, dict):
                raise ValueError("gps_coordinates must be a dict")
            lat = value.get('lat')
            lng = value.get('lng')
            if lat is not None and not (-90 <= lat <= 90):
                raise ValueError(f"Latitude must be -90 to +90, got {lat}")
            if lng is not None and not (-180 <= lng <= 180):
                raise ValueError(f"Longitude must be -180 to +180, got {lng}")
        return value

    @validates('file_size_bytes')
    def validate_file_size(self, key, value):
        """Validate file size (max 500MB)"""
        MAX_SIZE = 500 * 1024 * 1024  # 500 MB
        if value > MAX_SIZE:
            raise ValueError(f"File size {value} exceeds max {MAX_SIZE}")
        return value

    def __repr__(self):
        return f"<S3Image {self.image_id} - {self.s3_key_original}>"
```

**Key Decisions**:
- `UUID(as_uuid=True)`: Python UUID objects, not strings
- `BigInteger` for file_size: Supports files > 4GB
- `JSONB` for EXIF/GPS: Flexible schema, searchable
- `unique=True` on s3_key_original: Prevent duplicate uploads
- Enum types: Content type, upload source, status
- CASCADE delete on relationships: Delete image → delete sessions/samples

---

### 2. Migration (15 min)

**File**: `alembic/versions/XXXXX_create_s3_images_table.py`

```python
def upgrade():
    # Create enum types
    op.execute("""
        CREATE TYPE image_content_type_enum AS ENUM ('image/jpeg', 'image/png');
        CREATE TYPE upload_source_enum AS ENUM ('web', 'mobile', 'api');
        CREATE TYPE image_status_enum AS ENUM ('uploaded', 'processing', 'ready', 'failed');
    """)

    op.create_table(
        's3_images',
        sa.Column('image_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('s3_bucket', sa.String(255), nullable=False),
        sa.Column('s3_key_original', sa.String(512), nullable=False, unique=True),
        sa.Column('s3_key_thumbnail', sa.String(512), nullable=True),
        sa.Column('content_type', sa.Enum(name='image_content_type_enum'), nullable=False),
        sa.Column('file_size_bytes', sa.BigInteger(), nullable=False),
        sa.Column('width_px', sa.Integer(), nullable=False),
        sa.Column('height_px', sa.Integer(), nullable=False),
        sa.Column('exif_metadata', postgresql.JSONB(), nullable=True),
        sa.Column('gps_coordinates', postgresql.JSONB(), nullable=True),
        sa.Column('upload_source', sa.Enum(name='upload_source_enum'), nullable=False),
        sa.Column('uploaded_by_user_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.Enum(name='image_status_enum'), nullable=False),
        sa.Column('error_details', sa.Text(), nullable=True),
        sa.Column('processing_status_updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['uploaded_by_user_id'], ['users.id'], ondelete='SET NULL'),
    )

    # Indexes
    op.create_index('idx_s3_images_status', 's3_images', ['status'])
    op.create_index('idx_s3_images_created_at', 's3_images', ['created_at'], desc=True)
    op.create_index('idx_s3_images_uploaded_by', 's3_images', ['uploaded_by_user_id'])

    # GIN index for JSONB GPS queries (spatial searches)
    op.execute("CREATE INDEX idx_s3_images_gps_gin ON s3_images USING GIN (gps_coordinates)")

def downgrade():
    op.drop_index('idx_s3_images_gps_gin')
    op.drop_index('idx_s3_images_uploaded_by')
    op.drop_index('idx_s3_images_created_at')
    op.drop_index('idx_s3_images_status')
    op.drop_table('s3_images')
    op.execute("DROP TYPE image_status_enum")
    op.execute("DROP TYPE upload_source_enum")
    op.execute("DROP TYPE image_content_type_enum")
```

**Indexes Rationale**:
- `status`: Filter by processing status (uploaded, ready, failed)
- `created_at DESC`: Recent images first (time-series queries)
- `uploaded_by_user_id`: User's upload history
- `gps_coordinates GIN`: Spatial queries ("find images near lat/lng")

---

### 3. Testing Strategy (30 min)

#### Unit Tests (`tests/unit/models/test_s3_image.py`)

**Test Cases** (18 tests):
1. `test_s3_image_creation` - Basic instantiation
2. `test_uuid_primary_key_type` - UUID4 format validation
3. `test_gps_validation_valid` - Valid GPS coordinates
4. `test_gps_validation_invalid_latitude` - lat > 90
5. `test_gps_validation_invalid_longitude` - lng > 180
6. `test_file_size_validation_valid` - Under 500MB
7. `test_file_size_validation_exceeds_max` - Over 500MB
8. `test_content_type_enum_jpeg` - JPEG accepted
9. `test_content_type_enum_png` - PNG accepted
10. `test_upload_source_enum_values` - web, mobile, api
11. `test_status_enum_values` - uploaded, processing, ready, failed
12. `test_nullable_fields` - thumbnail, EXIF, GPS, user_id
13. `test_exif_metadata_jsonb` - Store arbitrary JSON
14. `test_gps_coordinates_jsonb_structure` - {lat, lng, altitude}
15. `test_s3_key_uniqueness` - Duplicate s3_key_original fails
16. `test_uploaded_by_relationship` - FK to User
17. `test_cascade_delete_sessions` - Delete image → delete sessions
18. `test_repr_method` - Human-readable string

#### Integration Tests (`tests/integration/test_s3_image_db.py`)

**Test Cases** (12 tests):
1. `test_insert_s3_image_with_uuid`
2. `test_insert_with_gps_coordinates`
3. `test_insert_without_gps_coordinates`
4. `test_query_by_uuid`
5. `test_query_by_status`
6. `test_query_by_created_at_desc`
7. `test_unique_s3_key_constraint` - Duplicate insert fails
8. `test_cascade_delete_processing_sessions`
9. `test_set_null_on_user_delete` - Delete user → SET NULL
10. `test_gps_jsonb_query` - WHERE gps_coordinates->>'lat' = '...'
11. `test_exif_jsonb_query` - WHERE exif_metadata->>'camera' = '...'
12. `test_update_status_with_timestamp` - Update status + processing_status_updated_at

**Coverage Target**: ≥85%

---

### 4. API-Level UUID Generation Pattern (IMPORTANT)

**Service Layer Example** (for documentation):

```python
from uuid import uuid4
from app.services.s3_service import S3Service
from app.repositories.s3_image_repository import S3ImageRepository

async def upload_photo(file, user_id: int):
    # 1. Generate UUID BEFORE S3 upload
    image_id = uuid4()

    # 2. Upload to S3 using UUID in key
    s3_key = f"original/{image_id}.jpg"
    await S3Service.upload(file, bucket="demeter-photos", key=s3_key)

    # 3. Insert to database with pre-generated UUID
    s3_image = S3Image(
        image_id=image_id,  # EXPLICIT, not default
        s3_bucket="demeter-photos",
        s3_key_original=s3_key,
        content_type="image/jpeg",
        file_size_bytes=file.size,
        width_px=4000,
        height_px=3000,
        uploaded_by_user_id=user_id,
        status="uploaded"
    )
    await S3ImageRepository.create(s3_image)

    return image_id
```

**Key Pattern**: UUID generated in Python, then used for BOTH S3 key AND database PK

---

## Execution Checklist

### Python Expert Tasks (35 min)
- [ ] Create `app/models/s3_image.py` with complete model
- [ ] Add UUID primary key with PostgreSQL UUID type
- [ ] Add GPS validation (lat/lng bounds)
- [ ] Add file size validation (max 500MB)
- [ ] Create 3 enum types (content_type, upload_source, status)
- [ ] Create Alembic migration with indexes
- [ ] Add relationships to User, PhotoProcessingSession, ProductSampleImage
- [ ] Test migration (upgrade + downgrade)
- [ ] Run pre-commit hooks (ruff, mypy)

### Testing Expert Tasks (30 min, PARALLEL)
- [ ] Write 18 unit tests in `test_s3_image.py`
- [ ] Write 12 integration tests in `test_s3_image_db.py`
- [ ] Test GPS validation edge cases (-90, +90, -180, +180)
- [ ] Test file size validation (0, 500MB, 501MB)
- [ ] Test enum type validation (invalid values)
- [ ] Test UUID type (not string, actual UUID object)
- [ ] Test JSONB queries (GPS, EXIF)
- [ ] Test CASCADE and SET NULL behaviors
- [ ] Verify coverage ≥85%
- [ ] All tests pass

### Team Leader Review (5 min)
- [ ] Verify ERD alignment (database.mmd line 227-245)
- [ ] Check UUID type (as_uuid=True)
- [ ] Validate GPS bounds (-90/+90, -180/+180)
- [ ] Verify enum types created
- [ ] Check indexes (status, created_at, GPS GIN)
- [ ] Approve and merge

---

## Known Edge Cases

1. **UUID collision (theoretically possible)**
   - Probability: ~1 in 10^36 (negligible)
   - Mitigation: Rely on UUID4 randomness
   - Recovery: Database will reject duplicate PK (unique constraint)

2. **S3 upload succeeds, DB insert fails**
   - Scenario: Network error after S3 upload
   - Solution: Service layer should catch exception and delete S3 file
   - Recovery: Retry with same UUID (idempotent)

3. **DB insert succeeds, S3 upload fails**
   - Scenario: Wrong order (should not happen)
   - Solution: ALWAYS upload to S3 first, then insert DB
   - Recovery: Mark status as 'failed' with error_details

4. **NULL GPS coordinates**
   - Scenario: Desktop upload (no GPS)
   - Solution: Allow NULL (nullable=True)
   - Query: `WHERE gps_coordinates IS NOT NULL`

5. **Invalid EXIF data**
   - Scenario: Corrupted EXIF, parsing fails
   - Solution: Store NULL, log warning
   - JSONB accepts NULL gracefully

---

## Performance Expectations

- Insert: <10ms (UUID PK, B-tree index same as SERIAL)
- Query by UUID: <5ms (primary key lookup)
- Query by status: <20ms (indexed)
- GPS JSONB query: <50ms for 10k rows (GIN index)
- Recent images: <15ms (created_at DESC index)

**UUID vs SERIAL Performance**: Negligible difference (<1ms) for DemeterAI scale

---

## Definition of Done

- [ ] Model created in `app/models/s3_image.py`
- [ ] UUID primary key configured (as_uuid=True)
- [ ] 3 enum types created (content_type, upload_source, status)
- [ ] Alembic migration created and tested
- [ ] GPS validation working (lat/lng bounds)
- [ ] File size validation working (max 500MB)
- [ ] Indexes added (status, created_at, uploaded_by, GPS GIN)
- [ ] 18 unit tests pass
- [ ] 12 integration tests pass
- [ ] Coverage ≥85%
- [ ] Pre-commit hooks pass (17/17)
- [ ] Relationships to User, PhotoProcessingSession, ProductSampleImage working
- [ ] CASCADE delete behavior tested
- [ ] Code review approved
- [ ] API-level UUID generation pattern documented

---

**Estimated Time**: 60-90 minutes
**Actual Time**: _____ (fill after completion)

**Ready to Execute**: YES - Independent model, no dependencies blocking
**Blocks**: DB012 (PhotoProcessingSessions) - CRITICAL ML pipeline dependency
