# CRITICAL FIXES - Photo Upload Workflow

**Generated**: 2025-10-22
**Priority**: HIGH - MUST FIX BEFORE PRODUCTION
**Scope**: Photo upload workflow (FASE 3 - Flowchart V3)

---

## Critical Fix #1: Database Schema Type Mismatch

### Issue

**File**: `/home/lucasg/proyectos/DemeterDocs/database/database.mmd`
**Tables**: `photo_processing_sessions`, `s3_images`

**Problem**: Foreign key type mismatch between `photo_processing_sessions` and `s3_images`:

```mermaid
photo_processing_sessions {
    int id PK
    uuid session_id UK
    int original_image_id FK "s3_images"     ← ❌ WRONG TYPE (int)
    int processed_image_id FK "s3_images"    ← ❌ WRONG TYPE (int)
}

s3_images {
    uuid image_id PK ""  ← ❌ PRIMARY KEY IS UUID, NOT INT
}
```

**Impact**:
- Foreign key constraint will FAIL on insert
- PhotoUploadService will crash when creating sessions
- ML pipeline cannot link sessions to images

### Solution

#### Step 1: Update Schema Documentation

**File**: `/home/lucasg/proyectos/DemeterDocs/database/database.mmd`

```diff
 photo_processing_sessions {
     int id PK ""
     uuid session_id UK ""
     int storage_location_id FK "nullable"
-    int original_image_id FK "s3_images"
-    int processed_image_id FK "s3_images"
+    uuid original_image_id FK "s3_images"
+    uuid processed_image_id FK "s3_images"
     int total_detected  ""
     int total_estimated  ""
     ...
 }
```

#### Step 2: Create Alembic Migration

```bash
cd /home/lucasg/proyectos/DemeterDocs
alembic revision -m "fix_photo_session_image_fk_uuid_types"
```

**Migration file**: `alembic/versions/XXXX_fix_photo_session_image_fk_uuid_types.py`

```python
"""fix photo_session image FK UUID types

Revision ID: XXXX
Revises: YYYY
Create Date: 2025-10-22

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'XXXX'
down_revision = 'YYYY'  # Replace with current head
branch_labels = None
depends_on = None


def upgrade():
    """Change original_image_id and processed_image_id from INTEGER to UUID."""

    # Drop existing foreign key constraints (if any)
    op.drop_constraint(
        'photo_processing_sessions_original_image_id_fkey',
        'photo_processing_sessions',
        type_='foreignkey'
    )
    op.drop_constraint(
        'photo_processing_sessions_processed_image_id_fkey',
        'photo_processing_sessions',
        type_='foreignkey'
    )

    # Alter column types to UUID
    op.alter_column(
        'photo_processing_sessions',
        'original_image_id',
        type_=postgresql.UUID(as_uuid=True),
        existing_nullable=False,
        postgresql_using='original_image_id::uuid'
    )

    op.alter_column(
        'photo_processing_sessions',
        'processed_image_id',
        type_=postgresql.UUID(as_uuid=True),
        existing_nullable=True,
        postgresql_using='processed_image_id::uuid'
    )

    # Recreate foreign key constraints
    op.create_foreign_key(
        'photo_processing_sessions_original_image_id_fkey',
        'photo_processing_sessions',
        's3_images',
        ['original_image_id'],
        ['image_id'],
        ondelete='RESTRICT'
    )

    op.create_foreign_key(
        'photo_processing_sessions_processed_image_id_fkey',
        'photo_processing_sessions',
        's3_images',
        ['processed_image_id'],
        ['image_id'],
        ondelete='SET NULL'
    )


def downgrade():
    """Revert UUID columns back to INTEGER (NOT RECOMMENDED)."""

    # Drop FK constraints
    op.drop_constraint(
        'photo_processing_sessions_original_image_id_fkey',
        'photo_processing_sessions',
        type_='foreignkey'
    )
    op.drop_constraint(
        'photo_processing_sessions_processed_image_id_fkey',
        'photo_processing_sessions',
        type_='foreignkey'
    )

    # Alter columns back to INTEGER
    op.alter_column(
        'photo_processing_sessions',
        'original_image_id',
        type_=sa.INTEGER(),
        existing_nullable=False
    )

    op.alter_column(
        'photo_processing_sessions',
        'processed_image_id',
        type_=sa.INTEGER(),
        existing_nullable=True
    )

    # Recreate FK constraints (will fail if UUIDs exist)
    op.create_foreign_key(
        'photo_processing_sessions_original_image_id_fkey',
        'photo_processing_sessions',
        's3_images',
        ['original_image_id'],
        ['image_id']
    )

    op.create_foreign_key(
        'photo_processing_sessions_processed_image_id_fkey',
        'photo_processing_sessions',
        's3_images',
        ['processed_image_id'],
        ['image_id']
    )
```

#### Step 3: Verify Model Matches

**File**: `/home/lucasg/proyectos/DemeterDocs/app/models/photo_processing_session.py`

Verify model already uses UUID (if not, fix it):

```python
class PhotoProcessingSession(Base):
    __tablename__ = "photo_processing_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid4)
    storage_location_id = Column(Integer, ForeignKey("storage_locations.storage_location_id"), nullable=True)

    # ✅ VERIFY THESE ARE UUID, NOT Integer
    original_image_id = Column(UUID(as_uuid=True), ForeignKey("s3_images.image_id"), nullable=False)
    processed_image_id = Column(UUID(as_uuid=True), ForeignKey("s3_images.image_id"), nullable=True)
```

#### Step 4: Apply Migration

```bash
# Test migration (dry-run)
alembic upgrade head --sql > migration_preview.sql
cat migration_preview.sql  # Review SQL

# Apply migration to test database
docker compose up db_test -d
alembic upgrade head

# Verify
docker exec demeterai-db-test psql -U demeter_test -d demeterai_test -c "\d photo_processing_sessions"
# Expected output should show:
#   original_image_id | uuid | not null
#   processed_image_id | uuid |
```

#### Step 5: Test

```bash
# Run integration tests
pytest tests/integration/test_photo_processing_session.py -v

# Manual verification
python3 -c "
from app.models.photo_processing_session import PhotoProcessingSession
from app.models.s3_image import S3Image
import inspect

# Verify FK types
orig_col = PhotoProcessingSession.__table__.columns['original_image_id']
proc_col = PhotoProcessingSession.__table__.columns['processed_image_id']
s3_pk = S3Image.__table__.columns['image_id']

print(f'original_image_id type: {orig_col.type}')
print(f'processed_image_id type: {proc_col.type}')
print(f's3_images.image_id type: {s3_pk.type}')
print('Match:', orig_col.type == s3_pk.type)
"
```

---

## Verification Checklist

- [ ] Schema documentation updated (`database/database.mmd`)
- [ ] Alembic migration created
- [ ] Migration SQL reviewed
- [ ] Migration applied to test database
- [ ] Schema verified: `\d photo_processing_sessions` shows UUID types
- [ ] Model verified: `PhotoProcessingSession` uses `UUID(as_uuid=True)`
- [ ] Integration tests pass
- [ ] FK constraints work (insert test session with S3 image)

---

## Additional Fixes (Lower Priority)

### Fix #2: Update Schema to Include webp Content Type

**File**: `/home/lucasg/proyectos/DemeterDocs/database/database.mmd`

```diff
 s3_images {
     uuid image_id PK ""
     varchar s3_bucket  ""
     varchar s3_key_original UK ""
     varchar s3_key_thumbnail  ""
-    varchar content_type "image/jpeg|image/png"
+    varchar content_type "image/jpeg|image/png|image/webp"
     ...
 }
```

**Impact**: Documentation only - code already allows `webp` in `ALLOWED_CONTENT_TYPES`.

### Fix #3: Remove Commented Code

**File**: `/home/lucasg/proyectos/DemeterDocs/app/services/photo/photo_upload_service.py`
**Lines**: 269-275

**Action**: Either:
1. Remove commented code entirely, OR
2. Add clear TODO with ticket reference:

```python
# TODO(TICKET-XXX): Enable session status update to PROCESSING after Celery dispatch
# Currently disabled pending ML pipeline stabilization (awaiting GPU workers)
# Expected completion: Sprint 04
```

---

## Risk Assessment

### Before Fix

| Risk | Level | Impact |
|------|-------|--------|
| FK constraint failure | 🔴 CRITICAL | Photo upload will crash on session creation |
| Data corruption | 🔴 CRITICAL | Cannot link sessions to images |
| ML pipeline failure | 🔴 CRITICAL | Cannot retrieve images for processing |

### After Fix

| Risk | Level | Impact |
|------|-------|--------|
| FK constraint failure | 🟢 NONE | Types match correctly |
| Data corruption | 🟢 NONE | FK enforced by database |
| ML pipeline failure | 🟢 NONE | Session→Image relationship valid |

---

## Timeline

1. **Now**: Create migration (15 min)
2. **Test**: Apply to test database (10 min)
3. **Verify**: Run integration tests (15 min)
4. **Deploy**: Apply to staging database (5 min)
5. **Production**: Apply during maintenance window (5 min)

**Total estimated time**: 50 minutes

---

## Contact

**Issue Reporter**: Team Leader (Code Audit)
**Date**: 2025-10-22
**Priority**: HIGH - BLOCKING PRODUCTION DEPLOYMENT
