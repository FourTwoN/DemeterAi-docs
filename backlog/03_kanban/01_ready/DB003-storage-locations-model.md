# [DB003] StorageLocations Model - PostGIS Level 3 (Photo Unit)

## Metadata
- **Epic**: epic-002-database-models.md
- **Sprint**: Sprint-01 (Week 3-4)
- **Status**: `backlog`
- **Priority**: `critical` ⚡ (ML pipeline depends on this)
- **Complexity**: M (2 story points)
- **Area**: `database/models`
- **Assignee**: TBD
- **Dependencies**:
  - Blocks: [DB004, DB012, DB024, ML007, R003]
  - Blocked by: [DB002-storage-areas-model]

## Related Documentation
- **Engineering Plan**: ../../engineering_plan/database/README.md
- **Database ERD**: ../../database/database.mmd
- **ML Pipeline**: ../../flows/procesamiento_ml_upload_s3_principal/PIPELINE_OVERVIEW.md

## Description

Create the `storage_locations` SQLAlchemy model for level 3 of the hierarchy. This is the **photo unit level** - one photo = one storage location. Critical for ML pipeline.

**What**: SQLAlchemy model for `storage_locations` table:
- The "photo unit" where ML processing happens
- Each location has QR code for physical identification
- Links to latest photo processing session
- Contains multiple storage bins (segmentos/cajones)

**Why**:
- **Photo granularity**: One photo captures one storage location
- **ML foundation**: ML pipeline processes per-location
- **QR tracking**: Physical identifier for mobile app scanning
- **Stock rollup**: Aggregate all bins in a location for inventory

**Context**: This is THE critical level for ML. One photo → one location → ML detects bins within location → counts plants per bin.

## Acceptance Criteria

- [ ] **AC1**: Model created in `app/models/storage_location.py` with PostGIS geometry, QR code UK, photo_session_id FK nullable, relationships
- [ ] **AC2**: QR code unique constraint and validation (alphanumeric, 8-20 chars)
- [ ] **AC3**: GENERATED area_m2 column and centroid trigger (same as warehouse/area)
- [ ] **AC4**: Spatial constraint: location geometry must be within storage_area
- [ ] **AC5**: Self-referencing FK to photo_processing_sessions.session_id (nullable, latest photo for this location)
- [ ] **AC6**: Indexes: GIST on geometry/centroid, B-tree on storage_area_id, code, qr_code, active, photo_session_id
- [ ] **AC7**: Alembic migration with CASCADE delete from storage_area

## Technical Implementation Notes

### Architecture
- Layer: Database / Models
- Dependencies: DB002 (StorageArea), PostGIS 3.3+, SQLAlchemy 2.0.43
- Design pattern: Photo unit with QR tracking and latest session reference

### Model Signature

```python
class StorageLocation(Base):
    __tablename__ = 'storage_locations'

    location_id = Column(Integer, PK, autoincrement=True)
    storage_area_id = Column(Integer, FK → storage_areas, CASCADE, index=True)
    photo_session_id = Column(Integer, FK → photo_processing_sessions, SET NULL, nullable=True)  # Latest photo

    code = Column(String(50), UK, index=True)
    qr_code = Column(String(50), UK, index=True)
    name = Column(String(200))
    description = Column(Text, nullable=True)

    geojson_coordinates = Column(Geometry('POLYGON', srid=4326), nullable=False)
    centroid = Column(Geometry('POINT', srid=4326), nullable=True)
    area_m2 = Column(Numeric(10,2), GENERATED)

    active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    storage_area = relationship('StorageArea', back_populates='storage_locations')
    latest_photo_session = relationship('PhotoProcessingSession', foreign_keys=[photo_session_id])
    storage_bins = relationship('StorageBin', back_populates='storage_location', cascade='all, delete-orphan')
    photo_processing_sessions = relationship('PhotoProcessingSession', back_populates='storage_location', foreign_keys='PhotoProcessingSession.storage_location_id')
    storage_location_configs = relationship('StorageLocationConfig', back_populates='storage_location')
```

### Key Features

**QR Code validation:**
```python
@validates('qr_code')
def validate_qr_code(self, key, value):
    """QR code must be alphanumeric, 8-20 chars"""
    if not value:
        raise ValueError("QR code is required")
    if not value.isalnum():
        raise ValueError("QR code must be alphanumeric")
    if not (8 <= len(value) <= 20):
        raise ValueError("QR code must be 8-20 characters")
    return value.upper()
```

**Spatial containment trigger:**
```sql
CREATE FUNCTION check_storage_location_within_area() RETURNS TRIGGER AS $$
DECLARE area_geom GEOMETRY;
BEGIN
    SELECT geojson_coordinates INTO area_geom
    FROM storage_areas WHERE storage_area_id = NEW.storage_area_id;

    IF NOT ST_Within(NEW.geojson_coordinates, area_geom) THEN
        RAISE EXCEPTION 'Storage location must be within storage area';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

**Latest photo session update:**
```python
async def update_latest_photo_session(location_id: int, session_id: int):
    """Update location's latest photo session after successful ML processing"""
    await session.execute(
        update(StorageLocation)
        .where(StorageLocation.location_id == location_id)
        .values(photo_session_id=session_id)
    )
    await session.commit()
```

### Testing Requirements

**Unit Tests** (`tests/models/test_storage_location.py`):
- QR code validation (alphanumeric, 8-20 chars, uppercase)
- Code format validation
- Relationship configuration

**Integration Tests** (`tests/integration/test_storage_location.py`):
- Containment constraint (location within area)
- Latest photo session FK (nullable, SET NULL on delete)
- QR code uniqueness enforcement
- GPS → StorageLocation lookup (ST_Contains)
- Cascade delete from storage_area

**Coverage Target**: ≥80%

### Performance Expectations
- Insert: <20ms
- QR code lookup: <5ms (unique index)
- GPS → Location: <30ms (GIST index)
- Update latest_photo_session: <10ms

## Handover Briefing

**Context**: This is the **photo unit level** - the most important level for ML. One photo = one location. All ML processing happens at this granularity.

**Key decisions**:
1. **photo_session_id FK**: Nullable, references latest successful photo for this location
2. **QR code UK**: Physical identifier for mobile app (scan QR → jump to location)
3. **Code format**: AREA-LOCATION (e.g., "INV01-NORTH-A1")
4. **Containment validation**: Location MUST be within parent storage_area
5. **SET NULL on photo session delete**: Don't cascade delete location if session deleted

**Next steps**: DB004 (StorageBin), DB012 (PhotoProcessingSession circular reference), DB024 (StorageLocationConfig), ML007 (GPS localization), R003 (StorageLocationRepository)

## Definition of Done Checklist

- [ ] Model code written
- [ ] QR code validation + UK constraint
- [ ] GENERATED area_m2 + centroid trigger
- [ ] Containment validation trigger
- [ ] photo_session_id FK with SET NULL
- [ ] GIST + B-tree indexes
- [ ] Unit tests ≥80% coverage
- [ ] Integration tests pass
- [ ] Alembic migration tested
- [ ] PR reviewed and approved

## Time Tracking
- **Estimated**: 2 story points
- **Actual**: TBD
- **Started**: TBD
- **Completed**: TBD

---

**Card Created**: 2025-10-09
**Last Updated**: 2025-10-09
**Card Owner**: TBD
