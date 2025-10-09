# [DB013] Detections Model - Partitioned Table

## Metadata
- **Epic**: epic-002-database-models.md
- **Sprint**: Sprint-01 (Week 3-4)
- **Status**: `backlog`
- **Priority**: `critical` ⚡ (blocks ML pipeline)
- **Complexity**: M (2 story points)
- **Area**: `database/models`
- **Assignee**: TBD
- **Dependencies**:
  - Blocks: [ML003, ML005, R011, S013]
  - Blocked by: [DB012-photo-processing-sessions, DB007-stock-movements, DB026-classifications]

## Related Documentation
- **Engineering Plan**: ../../engineering_plan/database/README.md (Partitioning section)
- **Database ERD**: ../../database/database.mmd
- **ADR**: ../../backlog/09_decisions/ADR-007-daily-partitioning.md
- **ML Pipeline**: ../../flows/procesamiento_ml_upload_s3_principal/05_sahi_detection_child_detailed.md

## Description

Create the `detections` SQLAlchemy model with **daily partitioning** for high-volume plant detection data. Each row represents one individual plant detected by YOLO in a photo, with bounding box coordinates and confidence score.

**What**: Partitioned SQLAlchemy model for individual plant detections from ML pipeline:
- Each detection = one plant's bounding box + confidence + classification
- 500-1000 detections per photo average
- Daily partitions to handle millions of rows efficiently

**Why**:
- **High volume**: 600k plants → 600k+ detections expected
- **Query performance**: 99% of queries filter by date → partition pruning 10-100× faster
- **Maintenance**: VACUUM on daily partitions 100× faster than monolithic table
- **Storage management**: Auto-drop old partitions after retention period

**Context**: This table grows rapidly (1000+ rows per ML job). Without partitioning, queries slow to crawl after 1M+ rows. Partitioning is non-negotiable for performance (see ADR-007).

## Acceptance Criteria

- [ ] **AC1**: Model created in `app/models/detection.py`:
  ```python
  from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, String
  from sqlalchemy.orm import relationship
  from geoalchemy2 import Geometry
  from app.models.base import Base

  class Detection(Base):
      __tablename__ = 'detections'
      __table_args__ = {
          'postgresql_partition_by': 'RANGE (created_at)',
      }

      # Primary key (serial per partition)
      detection_id = Column(Integer, primary_key=True, autoincrement=True)

      # Foreign keys
      session_id = Column(
          Integer,
          ForeignKey('photo_processing_sessions.session_id', ondelete='CASCADE'),
          nullable=False,
          index=True
      )
      stock_movement_id = Column(
          Integer,
          ForeignKey('stock_movements.movement_id', ondelete='SET NULL'),
          nullable=True  # NULL until aggregation creates movement
      )
      classification_id = Column(
          Integer,
          ForeignKey('classifications.classification_id', ondelete='SET NULL'),
          nullable=True  # May be NULL if unclassified
      )

      # Bounding box (in pixels, original image coordinates)
      center_x_px = Column(Float, nullable=False)
      center_y_px = Column(Float, nullable=False)
      width_px = Column(Float, nullable=False)
      height_px = Column(Float, nullable=False)

      # ML model outputs
      confidence = Column(Float, nullable=False)  # 0.0 to 1.0
      model_class = Column(String(50), default='item')  # YOLO class name

      # Container type (from segmentation)
      container_type = Column(String(20), nullable=True)  # 'segmento' or 'cajon'

      # PostGIS point (for spatial queries if needed)
      point_geom = Column(
          Geometry('POINT', srid=4326),
          nullable=True  # Populated if photo has GPS
      )

      # Partition key (MANDATORY for partitioned table)
      created_at = Column(
          DateTime(timezone=True),
          server_default=func.now(),
          nullable=False,
          primary_key=True  # Part of composite PK with detection_id
      )

      # Relationships
      session = relationship('PhotoProcessingSession', back_populates='detections')
      stock_movement = relationship('StockMovement', back_populates='detections')
      classification = relationship('Classification')
  ```

- [ ] **AC2**: Daily partitions configured using pg_partman:
  ```sql
  -- In Alembic migration:
  SELECT partman.create_parent(
      p_parent_table := 'public.detections',
      p_partition_key := 'created_at',
      p_partition_type := 'native',  -- PostgreSQL 18 native partitioning
      p_interval := 'daily',
      p_premake := 7,  -- Create 7 days ahead
      p_start_partition := CURRENT_DATE::text
  );
  ```

- [ ] **AC3**: Partition management configured:
  ```sql
  -- Retention: keep 90 days, auto-drop older partitions
  UPDATE partman.part_config
  SET
      retention = '90 days',
      retention_keep_table = false,  -- Drop, don't detach
      infinite_time_partitions = false
  WHERE parent_table = 'public.detections';
  ```

- [ ] **AC4**: Cron job for partition maintenance:
  ```sql
  SELECT cron.schedule(
      'detections-partition-maintenance',
      '0 */4 * * *',  -- Every 4 hours
      $$SELECT partman.run_maintenance('public.detections')$$
  );
  ```

- [ ] **AC5**: Indexes on each partition (auto-created):
  ```sql
  -- These apply to ALL partitions
  CREATE INDEX idx_detections_session ON detections(session_id);
  CREATE INDEX idx_detections_movement ON detections(stock_movement_id);
  CREATE INDEX idx_detections_confidence ON detections(confidence);
  CREATE INDEX idx_detections_container ON detections(container_type);

  -- Spatial index (if point_geom populated)
  CREATE INDEX idx_detections_geom ON detections USING GIST(point_geom);
  ```

- [ ] **AC6**: Confidence bounds validation:
  ```python
  from sqlalchemy import CheckConstraint

  __table_args__ = (
      CheckConstraint('confidence >= 0.0 AND confidence <= 1.0', name='check_confidence_bounds'),
      {'postgresql_partition_by': 'RANGE (created_at)'}
  )
  ```

- [ ] **AC7**: Bulk insert optimization documented:
  ```python
  # In repository, use asyncpg COPY for bulk inserts:
  # 714k rows/sec vs 2k rows/sec with ORM
  ```

## Technical Implementation Notes

### Architecture
- Layer: Database / Models
- Dependencies: DB012 (PhotoProcessingSession), pg_partman extension
- Design pattern: Partitioned table (RANGE on created_at)

### Code Hints

**Partitioning declaration (SQLAlchemy 2.0):**
```python
class Detection(Base):
    __tablename__ = 'detections'

    # CRITICAL: Must include partition key in primary key
    detection_id = Column(Integer, primary_key=True)
    created_at = Column(DateTime(timezone=True), primary_key=True, server_default=func.now())

    __table_args__ = {
        'postgresql_partition_by': 'RANGE (created_at)'
    }
```

**Bulk insert with asyncpg COPY (performance critical):**
```python
# In DetectionRepository:
async def bulk_insert_detections(self, detections: list[dict]) -> None:
    """Use asyncpg COPY for 350× faster inserts"""
    import asyncpg

    pool = await asyncpg.create_pool(DATABASE_URL)
    async with pool.acquire() as conn:
        records = [
            (
                d['session_id'],
                d['center_x_px'],
                d['center_y_px'],
                d['width_px'],
                d['height_px'],
                d['confidence'],
                d['model_class'],
                d['container_type'],
                datetime.utcnow()  # created_at
            )
            for d in detections
        ]

        await conn.copy_records_to_table(
            'detections',
            records=records,
            columns=[
                'session_id', 'center_x_px', 'center_y_px',
                'width_px', 'height_px', 'confidence',
                'model_class', 'container_type', 'created_at'
            ]
        )
```

**Query with partition pruning:**
```sql
-- Fast: Only scans today's partition
SELECT * FROM detections
WHERE created_at >= CURRENT_DATE
  AND confidence > 0.7;

-- Slow: Scans ALL partitions
SELECT * FROM detections
WHERE confidence > 0.7;  -- Missing created_at filter!
```

### Testing Requirements

**Unit Tests** (`tests/models/test_detection.py`):
```python
def test_confidence_bounds():
    """Confidence must be between 0.0 and 1.0"""
    detection = Detection(
        session_id=1,
        center_x_px=100.0,
        center_y_px=200.0,
        width_px=50.0,
        height_px=50.0,
        confidence=0.85,
        created_at=datetime.utcnow()
    )
    assert 0.0 <= detection.confidence <= 1.0

    # Invalid confidence should fail
    with pytest.raises(IntegrityError):
        invalid = Detection(..., confidence=1.5)
        session.add(invalid)
        session.commit()

def test_container_type_values():
    """Container type is segmento or cajon"""
    detection = Detection(...)
    for container in ['segmento', 'cajon', None]:
        detection.container_type = container  # Should not raise
```

**Integration Tests** (`tests/integration/test_detections_partitioning.py`):
```python
@pytest.mark.asyncio
async def test_partition_creation(db_session):
    """Verify daily partitions are created"""
    # Insert detection for today
    detection_today = Detection(
        session_id=1,
        center_x_px=100.0,
        center_y_px=200.0,
        width_px=50.0,
        height_px=50.0,
        confidence=0.85,
        created_at=datetime.utcnow()
    )
    db_session.add(detection_today)
    await db_session.commit()

    # Verify partition exists for today
    result = await db_session.execute(text("""
        SELECT tablename
        FROM pg_tables
        WHERE schemaname = 'public'
          AND tablename LIKE 'detections_%'
    """))
    partitions = [row[0] for row in result]

    today_str = datetime.utcnow().strftime('%Y%m%d')
    expected_partition = f"detections_{today_str}"
    assert expected_partition in partitions

@pytest.mark.asyncio
async def test_bulk_insert_performance(db_session):
    """Bulk insert 1000 detections in <2 seconds"""
    detections = [
        {
            'session_id': 1,
            'center_x_px': i * 10.0,
            'center_y_px': i * 20.0,
            'width_px': 50.0,
            'height_px': 50.0,
            'confidence': 0.85,
            'model_class': 'item',
            'container_type': 'segmento'
        }
        for i in range(1000)
    ]

    start = time.time()
    await detection_repo.bulk_insert_detections(detections)
    elapsed = time.time() - start

    assert elapsed < 2.0  # Should be <1s with COPY
```

**Coverage Target**: ≥75% (complex partitioning setup)

### Performance Expectations
- Single insert: <5ms (partition-local)
- Bulk insert (1000 rows): <1s with asyncpg COPY
- Query with date filter: <50ms (partition pruning)
- Query without date filter: >5s (scans all partitions - AVOID)

## Handover Briefing

**For the next developer:**

**Context**: This is a **high-volume table** (millions of rows expected). Partitioning is MANDATORY for performance. Without it, queries grind to a halt after 1M rows.

**Key decisions made**:
1. **Daily partitions**: Balance between too many partitions (overhead) and too few (large partition size)
2. **90-day retention**: Configurable, auto-cleanup with pg_partman
3. **asyncpg COPY for bulk inserts**: ORM too slow (2k rows/sec vs 714k rows/sec)
4. **Composite PK**: `(detection_id, created_at)` - partition key MUST be in PK
5. **Optional classification**: Many detections don't get classified until aggregation step

**Known limitations**:
- Queries without `created_at` filter scan ALL partitions (slow) - must educate team
- Partition maintenance requires cron extension (pg_cron)
- Cannot use ON CONFLICT with partitioned tables (PostgreSQL limitation)

**Next steps after this card**:
- DB014: Estimations model (similar partitioning strategy)
- R011: DetectionRepository (must use asyncpg COPY)
- ML003: SAHI Detection service (writes to this table)

**Questions to validate**:
- Are partitions being created 7 days ahead? (Check pg_partman config)
- Is cron job running every 4 hours? (Check `SELECT * FROM cron.job`)
- Are old partitions being dropped after 90 days? (Check partman logs)

## Definition of Done Checklist

- [ ] Model code written with partitioning declaration
- [ ] pg_partman configured in Alembic migration
- [ ] Daily partitions tested (create detection → verify partition exists)
- [ ] Cron job created for partition maintenance
- [ ] Retention policy configured (90 days)
- [ ] Indexes created and applied to all partitions
- [ ] Bulk insert with asyncpg COPY tested (<1s for 1000 rows)
- [ ] Confidence bounds CHECK constraint working
- [ ] Unit tests pass (≥75% coverage)
- [ ] Integration tests verify partitioning behavior
- [ ] Documentation: How to query efficiently (MUST include created_at filter)
- [ ] PR reviewed and approved (2+ reviewers)
- [ ] No linting errors

## Time Tracking
- **Estimated**: 2 story points
- **Actual**: TBD
- **Started**: TBD
- **Completed**: TBD

---

**Card Created**: 2025-10-09
**Last Updated**: 2025-10-09
**Card Owner**: TBD
