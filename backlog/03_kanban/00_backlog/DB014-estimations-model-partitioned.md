# [DB014] Estimations Model - Partitioned Table

## Metadata

- **Epic**: epic-002-database-models.md
- **Sprint**: Sprint-01 (Week 3-4)
- **Status**: `backlog`
- **Priority**: `critical` ⚡ (blocks ML pipeline)
- **Complexity**: M (2 story points)
- **Area**: `database/models`
- **Assignee**: TBD
- **Dependencies**:
    - Blocks: [ML005, ML006, R012, S014]
    - Blocked by: [DB012-photo-processing-sessions, DB013-detections]

## Related Documentation

- **Engineering Plan**: ../../engineering_plan/database/README.md
- **Database ERD**: ../../database/database.mmd
- **ML Pipeline**:
  ../../flows/procesamiento_ml_upload_s3_principal/05_sahi_detection_child_detailed.md
- **Context**: ../../context/past_chats_summary.md (Band-based estimation innovation)

## Description

Create the `estimations` SQLAlchemy model with **daily partitioning** for area-based plant
estimation data. Complements detections table by estimating plants in areas where individual
detection failed (dense plantings).

**What**: Partitioned SQLAlchemy model for undetected plant estimations:

- Area-based estimation (not individual plants)
- Band-based processing (handles perspective distortion)
- Density-based + band-based algorithms
- Daily partitions (same strategy as detections)

**Why**:

- **Completeness**: Detections miss 5-10% of plants in dense areas
- **Accuracy**: Band-based estimation accounts for perspective (far plants appear smaller)
- **Innovation**: Proprietary algorithm improves count accuracy (see past_chats)
- **Volume**: Similar scale to detections → needs partitioning

**Context**: This is the **secret sauce** of DemeterAI - the band-based estimation algorithm that
competitors don't have. Handles edge cases where YOLO struggles (overlapping plants, occlusion).

## Acceptance Criteria

- [ ] **AC1**: Model created in `app/models/estimation.py`:
  ```python
  from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, String, Text
  from sqlalchemy.orm import relationship
  from app.models.base import Base

  class Estimation(Base):
      __tablename__ = 'estimations'
      __table_args__ = {
          'postgresql_partition_by': 'RANGE (created_at)',
      }

      # Primary key (serial per partition)
      estimation_id = Column(Integer, primary_key=True, autoincrement=True)

      # Foreign keys
      session_id = Column(
          Integer,
          ForeignKey('photo_processing_sessions.session_id', ondelete='CASCADE'),
          nullable=False,
          index=True
      )

      # Estimation type
      estimation_type = Column(
          String(20),
          nullable=False  # 'band_based' or 'density_based'
      )

      # Band information (for band-based estimation)
      band_number = Column(Integer, nullable=True)  # 1-4 (NULL for density-based)
      band_y_start = Column(Integer, nullable=True)  # Pixel coordinates
      band_y_end = Column(Integer, nullable=True)

      # Area analyzed
      residual_area_px = Column(Float, nullable=False)  # Total residual area
      processed_area_px = Column(Float, nullable=False)  # After floor suppression
      floor_suppressed_px = Column(Float, nullable=False)  # Removed soil/floor

      # Estimation results
      estimated_count = Column(Integer, nullable=False)
      average_plant_area_px = Column(Float, nullable=True)  # Calibrated from detections

      # Calibration parameters
      density_factor = Column(Float, nullable=True)  # Plants per unit area
      alpha_overcount = Column(Float, default=0.9)  # Bias toward overestimation

      # Container context
      container_type = Column(String(20), nullable=True)  # 'segmento' or 'cajon'
      container_index = Column(Integer, nullable=True)  # Which segmento/cajon

      # Algorithm metadata
      algorithm_version = Column(String(20), default='v1.0')
      parameters_json = Column(Text, nullable=True)  # JSON of all algo params

      # Partition key
      created_at = Column(
          DateTime(timezone=True),
          server_default=func.now(),
          nullable=False,
          primary_key=True  # Composite PK with estimation_id
      )

      # Relationships
      session = relationship('PhotoProcessingSession', back_populates='estimations')
  ```

- [ ] **AC2**: Daily partitions configured (same as detections):
  ```sql
  SELECT partman.create_parent(
      p_parent_table := 'public.estimations',
      p_partition_key := 'created_at',
      p_partition_type := 'native',
      p_interval := 'daily',
      p_premake := 7,
      p_start_partition := CURRENT_DATE::text
  );

  UPDATE partman.part_config
  SET
      retention = '90 days',
      retention_keep_table = false
  WHERE parent_table = 'public.estimations';
  ```

- [ ] **AC3**: Estimation type validation:
  ```python
  @validates('estimation_type')
  def validate_estimation_type(self, key, value):
      if value not in ['band_based', 'density_based']:
          raise ValueError(f"Invalid estimation_type: {value}")
      return value
  ```

- [ ] **AC4**: Band-based constraints:
  ```sql
  -- If band_based, band_number must be 1-4
  ALTER TABLE estimations ADD CONSTRAINT check_band_number
  CHECK (
      (estimation_type = 'band_based' AND band_number BETWEEN 1 AND 4)
      OR estimation_type = 'density_based'
  );
  ```

- [ ] **AC5**: Indexes for analytics:
  ```sql
  CREATE INDEX idx_estimations_session ON estimations(session_id);
  CREATE INDEX idx_estimations_type ON estimations(estimation_type);
  CREATE INDEX idx_estimations_band ON estimations(band_number) WHERE band_number IS NOT NULL;
  CREATE INDEX idx_estimations_container ON estimations(container_type, container_index);
  ```

- [ ] **AC6**: Area calculations validated:
  ```sql
  ALTER TABLE estimations ADD CONSTRAINT check_area_balance
  CHECK (processed_area_px + floor_suppressed_px <= residual_area_px);
  ```

- [ ] **AC7**: Cron job for partition maintenance (shared with detections)

## Technical Implementation Notes

### Architecture

- Layer: Database / Models
- Dependencies: DB012 (PhotoProcessingSession), DB013 (Detections for calibration)
- Design pattern: Partitioned table, aggregate data model

### Code Hints

**Band-based vs Density-based differentiation:**

```python
# Band-based estimation (primary algorithm):
Estimation(
    session_id=1,
    estimation_type='band_based',
    band_number=1,  # Top band (far perspective)
    band_y_start=0,
    band_y_end=750,
    residual_area_px=50000,
    processed_area_px=38000,  # After floor removal
    floor_suppressed_px=12000,
    estimated_count=25,
    average_plant_area_px=1520,  # Calibrated from band 1 detections
    alpha_overcount=0.9
)

# Density-based estimation (fallback):
Estimation(
    session_id=1,
    estimation_type='density_based',
    band_number=None,  # Not band-specific
    residual_area_px=100000,
    processed_area_px=85000,
    floor_suppressed_px=15000,
    estimated_count=56,
    density_factor=0.000658,  # Plants per square pixel
    alpha_overcount=0.9
)
```

**Parameters JSON structure:**

```json
{
  "floor_suppression": {
    "otsu_threshold": 128,
    "hsv_filter": {"h_max": 30, "s_max": 40, "v_max": 40},
    "morph_kernel_size": 3
  },
  "calibration": {
    "sample_size": 120,
    "confidence_threshold": 0.7,
    "outlier_removal": "IQR"
  },
  "estimation": {
    "alpha": 0.9,
    "min_area_threshold_px": 500
  }
}
```

### Testing Requirements

**Unit Tests** (`tests/models/test_estimation.py`):

```python
def test_estimation_type_validation():
    """Only band_based or density_based allowed"""
    estimation = Estimation(
        session_id=1,
        estimation_type='band_based',
        band_number=2,
        residual_area_px=10000,
        processed_area_px=8000,
        floor_suppressed_px=2000,
        estimated_count=10,
        created_at=datetime.utcnow()
    )
    # Should not raise

    with pytest.raises(ValueError):
        invalid = Estimation(..., estimation_type='invalid_type')

def test_band_number_constraint():
    """Band number must be 1-4 for band_based"""
    # Valid
    est = Estimation(estimation_type='band_based', band_number=3, ...)

    # Invalid
    with pytest.raises(IntegrityError):
        invalid = Estimation(estimation_type='band_based', band_number=5, ...)

def test_area_balance():
    """processed + floor_suppressed <= residual"""
    # Valid
    est = Estimation(
        residual_area_px=10000,
        processed_area_px=7000,
        floor_suppressed_px=3000,
        ...
    )

    # Invalid (sum exceeds residual)
    with pytest.raises(IntegrityError):
        invalid = Estimation(
            residual_area_px=10000,
            processed_area_px=7000,
            floor_suppressed_px=4000,  # 7k + 4k > 10k
            ...
        )
```

**Integration Tests** (`tests/integration/test_estimations_lifecycle.py`):

```python
@pytest.mark.asyncio
async def test_band_based_estimation_4_bands(db_session):
    """Test creating all 4 band estimations for one session"""
    session = PhotoProcessingSession(...)
    await db_session.add(session)
    await db_session.commit()

    # Create 4 band estimations
    for band_num in range(1, 5):
        estimation = Estimation(
            session_id=session.session_id,
            estimation_type='band_based',
            band_number=band_num,
            band_y_start=(band_num - 1) * 750,
            band_y_end=band_num * 750,
            residual_area_px=50000,
            processed_area_px=38000,
            floor_suppressed_px=12000,
            estimated_count=10 + band_num,  # Far bands have smaller plants
            average_plant_area_px=1500 + (band_num * 100),
            created_at=datetime.utcnow()
        )
        db_session.add(estimation)

    await db_session.commit()

    # Verify all 4 created
    result = await db_session.execute(
        select(Estimation).where(Estimation.session_id == session.session_id)
    )
    estimations = result.scalars().all()
    assert len(estimations) == 4
    assert all(e.estimation_type == 'band_based' for e in estimations)

@pytest.mark.asyncio
async def test_partitioning_works(db_session):
    """Verify estimations go into correct daily partition"""
    estimation = Estimation(
        session_id=1,
        estimation_type='density_based',
        residual_area_px=100000,
        processed_area_px=85000,
        floor_suppressed_px=15000,
        estimated_count=56,
        created_at=datetime.utcnow()
    )
    db_session.add(estimation)
    await db_session.commit()

    # Check partition exists
    result = await db_session.execute(text("""
        SELECT tablename
        FROM pg_tables
        WHERE schemaname = 'public'
          AND tablename LIKE 'estimations_%'
    """))
    partitions = [row[0] for row in result]

    today_partition = f"estimations_{datetime.utcnow().strftime('%Y%m%d')}"
    assert today_partition in partitions
```

**Coverage Target**: ≥80%

### Performance Expectations

- Insert: <5ms (partition-local)
- Bulk insert (50 estimations): <200ms
- Query with date filter: <30ms
- Aggregation by band: <100ms

## Handover Briefing

**For the next developer:**

**Context**: This table stores the **innovative estimation algorithm** that makes DemeterAI more
accurate than competitors. Band-based estimation is proprietary intellectual property.

**Key decisions made**:

1. **Two estimation types**: Band-based (primary, handles perspective) + Density-based (fallback)
2. **4 bands**: Divides image into horizontal slices to handle perspective distortion
3. **Floor suppression metadata**: Track how much soil/floor was removed (important for algorithm
   validation)
4. **Alpha overcount factor**: Bias toward slight overestimation (better than undercount for sales)
5. **Parameters JSON**: Store full algorithm config for reproducibility and debugging

**Known limitations**:

- Band-based only works for ground-level photos (not aerial drone shots)
- Requires good calibration from detections (if detections fail, estimation fails)
- 4 bands is heuristic (may need tuning for different greenhouse layouts)

**Next steps after this card**:

- ML005: Band-based Estimation Service (implements the algorithm)
- ML006: Density-based Estimation Service (fallback)
- R012: EstimationRepository (includes aggregation queries)

**Questions to validate**:

- Is alpha_overcount consistently 0.9, or configurable per session? (Should be configurable)
- Are parameters_json being populated for debugging? (Should be YES)
- Is floor suppression aggressive enough? (Check residual vs processed area ratio)

## Definition of Done Checklist

- [ ] Model code written with partitioning
- [ ] Estimation type validation working
- [ ] Band number constraints enforced
- [ ] Area balance constraint enforced
- [ ] pg_partman configured (90-day retention)
- [ ] Indexes created
- [ ] Alembic migration tested
- [ ] Unit tests pass (≥80% coverage)
- [ ] Integration tests verify 4-band workflow
- [ ] Partitioning tested
- [ ] Documentation of band-based algorithm
- [ ] PR reviewed and approved
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
