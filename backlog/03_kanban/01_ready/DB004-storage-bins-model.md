# [DB004] StorageBins Model - Level 4 (Container/Segment)

## Metadata
- **Epic**: epic-002-database-models.md
- **Sprint**: Sprint-01 (Week 3-4)
- **Status**: `backlog`
- **Priority**: `critical` ⚡ (stock storage foundation)
- **Complexity**: M (2 story points)
- **Area**: `database/models`
- **Assignee**: TBD
- **Dependencies**:
  - Blocks: [DB007, DB008, R004]
  - Blocked by: [DB003-storage-locations-model, DB005-storage-bin-types-model]

## Related Documentation
- **Engineering Plan**: ../../engineering_plan/database/README.md
- **Database ERD**: ../../database/database.mmd
- **ML Pipeline**: ../../flows/procesamiento_ml_upload_s3_principal/05_sahi_detection_child_detailed.md

## Description

Create the `storage_bins` SQLAlchemy model for level 4 (leaf level) of hierarchy. Storage bins are the physical containers where plants live (segmentos, cajones, boxes, plugs).

**What**: SQLAlchemy model for `storage_bins` table:
- Lowest level of hierarchy (warehouse → area → location → **bin**)
- Physical container: segmento, cajon, box, plug tray
- Stores position_metadata JSON from ML segmentation (mask, bbox, confidence)
- Links to storage_bin_type (defines capacity, dimensions)

**Why**:
- **Physical storage**: Where stock_batches actually live
- **ML detection target**: ML detects bins in photo, creates rows here
- **Capacity planning**: Bin type defines max capacity per bin
- **Stock movements**: Movements reference source/destination bins

**Context**: This is where stock physically exists. Stock_batches reference current_storage_bin_id. ML pipeline creates bins from segmentation results.

## Acceptance Criteria

- [ ] **AC1**: Model created in `app/models/storage_bin.py` with FKs to storage_location and storage_bin_type, position_metadata JSONB, status enum
- [ ] **AC2**: Status enum created (`CREATE TYPE storage_bin_status_enum AS ENUM ('active', 'maintenance', 'retired')`)
- [ ] **AC3**: position_metadata JSONB schema documented (segmentation_mask, bbox, confidence, ml_model_version)
- [ ] **AC4**: Code format validation: LOCATION-BIN (e.g., "INV01-NORTH-A1-SEG001")
- [ ] **AC5**: Indexes on storage_location_id, storage_bin_type_id, code, status
- [ ] **AC6**: Relationship to stock_batches (one-to-many, CASCADE delete propagates)
- [ ] **AC7**: Alembic migration with CASCADE delete from storage_location

## Technical Implementation Notes

### Architecture
- Layer: Database / Models
- Dependencies: DB003 (StorageLocation), DB005 (StorageBinType), PostgreSQL 18 JSONB
- Design pattern: Container with ML metadata

### Model Signature

```python
class StorageBin(Base):
    __tablename__ = 'storage_bins'

    bin_id = Column(Integer, PK, autoincrement=True)
    storage_location_id = Column(Integer, FK → storage_locations, CASCADE, index=True)
    storage_bin_type_id = Column(Integer, FK → storage_bin_types, RESTRICT, index=True)

    code = Column(String(100), UK, index=True)
    label = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)

    position_metadata = Column(JSONB, nullable=True)  # ML segmentation results
    status = Column(Enum('active', 'maintenance', 'retired'), default='active', index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    storage_location = relationship('StorageLocation', back_populates='storage_bins')
    storage_bin_type = relationship('StorageBinType', back_populates='storage_bins')
    stock_batches = relationship('StockBatch', back_populates='current_storage_bin')
```

### JSONB Schema for position_metadata

```python
# position_metadata structure (from ML segmentation):
{
    "segmentation_mask": [[x1, y1], [x2, y2], ...],  # Polygon vertices (px coords)
    "bbox": {"x": 100, "y": 200, "width": 300, "height": 150},  # Bounding box
    "confidence": 0.92,  # Segmentation confidence
    "ml_model_version": "yolov11-seg-v2.3",
    "detected_at": "2025-10-09T14:30:00Z",
    "container_type": "segmento"  # or "cajon"
}
```

**JSONB query examples:**
```python
# Find bins with low confidence segmentation
low_confidence_bins = session.query(StorageBin).filter(
    StorageBin.position_metadata['confidence'].as_float() < 0.7
).all()

# Find all segmentos (vs cajones)
segmentos = session.query(StorageBin).filter(
    StorageBin.position_metadata['container_type'].as_string() == 'segmento'
).all()
```

### Status Transitions

```python
# Status state machine
# active → maintenance (for cleaning/repair)
# active → retired (permanently removed)
# maintenance → active (back in service)
# retired → (terminal state, no transitions out)

@validates('status')
def validate_status_transition(self, key, new_status):
    """Validate status transitions"""
    if self.status == 'retired' and new_status != 'retired':
        raise ValueError("Cannot reactivate retired bin")
    return new_status
```

### Testing Requirements

**Unit Tests** (`tests/models/test_storage_bin.py`):
- Status enum validation
- Code format validation (LOCATION-BIN)
- position_metadata JSON structure validation
- Status transition validation (retired is terminal)

**Integration Tests** (`tests/integration/test_storage_bin.py`):
- Cascade delete from storage_location
- RESTRICT delete from storage_bin_type (cannot delete type if bins exist)
- JSONB queries (filter by confidence, container_type)
- Relationship to stock_batches

**Coverage Target**: ≥75%

### Performance Expectations
- Insert: <10ms
- Retrieve by code: <5ms (UK index)
- JSONB query (confidence filter): <50ms with GIN index
- Cascade delete: <20ms per bin

## Handover Briefing

**Context**: Leaf level of hierarchy. This is where stock physically lives. ML creates bins from segmentation, stock_batches reference bins.

**Key decisions**:
1. **position_metadata JSONB**: Stores ML segmentation output (mask, bbox, confidence)
2. **Status enum**: active/maintenance/retired (retired is terminal state)
3. **Code format**: LOCATION-BIN (e.g., "INV01-NORTH-A1-SEG001")
4. **CASCADE delete from location**: If location deleted, bins deleted (intentional)
5. **RESTRICT delete from bin_type**: Cannot delete bin type if bins exist (safety)

**Next steps**: DB007 (StockMovements - source/destination bins), DB008 (StockBatches - current_storage_bin_id), R004 (StorageBinRepository)

## Definition of Done Checklist

- [ ] Model code written
- [ ] Status enum created
- [ ] position_metadata JSONB schema documented
- [ ] Code validation working
- [ ] Indexes created (including GIN on JSONB)
- [ ] Unit tests ≥75% coverage
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
