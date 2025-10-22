# R022: Detection Repository (with asyncpg COPY Bulk Insert)

## Metadata

- **Epic**: [epic-003-repositories.md](../../02_epics/epic-003-repositories.md)
- **Sprint**: Sprint-02
- **Status**: `backlog`
- **Priority**: `CRITICAL` (V1 - ML pipeline bottleneck)
- **Complexity**: L (8 story points)
- **Area**: `repositories`
- **Assignee**: TBD
- **Dependencies**:
    - Blocks: [ML009, S019]
    - Blocked by: [F006, F007, DB013, R019, R024]

## Related Documentation

- **Engineering Plan
  **: [../../engineering_plan/backend/repository_layer.md](../../engineering_plan/backend/repository_layer.md)
- **Database ERD**: [../../database/database.mmd](../../database/database.mmd#L261-L276)

## Description

**What**: Implement repository class for `detections` table (partitioned by created_at) with CRUD
operations and **asyncpg COPY bulk insert** for ML pipeline performance.

**Why**: Detections store individual plant detections from YOLO (1000s per photo). **ORM insert is
too slow (2-5s per photo)**. asyncpg COPY enables **<100ms bulk insert** for 1000+ detections.
CRITICAL for ML pipeline performance.

**Context**: Partitioned table (daily partitions). Each photo generates 100-2000 detections. Bulk
insert is NON-NEGOTIABLE for performance. ML pipeline creates detections → stock movements → batch
updates.

## Acceptance Criteria

- [ ] **AC1**: `DetectionRepository` class inherits from `AsyncRepository[Detection]`
- [ ] **AC2**: Implements `get_by_session_id(session_id: int)` for photo detections
- [ ] **AC3**: **CRITICAL**: Implements `bulk_insert_with_copy(detections: List[dict])` using
  asyncpg COPY (10-50x faster than ORM)
- [ ] **AC4**: Implements `get_by_classification_id(classification_id: int)` for species filtering
- [ ] **AC5**: Implements `get_empty_containers(session_id: int)` for empty bin detection
- [ ] **AC6**: Handles partitioned table queries (created_at partitions)
- [ ] **AC7**: Performance: bulk insert <100ms for 1000 detections, session query <50ms

## Technical Implementation Notes

### asyncpg COPY Bulk Insert (CRITICAL)

```python
async def bulk_insert_with_copy(
    self,
    detections: List[dict]
) -> int:
    """Bulk insert detections using asyncpg COPY (10-50x faster than ORM)

    CRITICAL: ORM insert = 2-5s per photo. COPY = <100ms.
    This is THE performance bottleneck for ML pipeline.
    """
    from io import StringIO
    import csv

    # Create CSV in memory
    csv_buffer = StringIO()
    writer = csv.writer(csv_buffer)

    for det in detections:
        writer.writerow([
            det["session_id"],
            det["stock_movement_id"],
            det["classification_id"],
            det["center_x_px"],
            det["center_y_px"],
            det["width_px"],
            det["height_px"],
            # area_px is GENERATED column - skip
            json.dumps(det["bbox_coordinates"]),
            det["detection_confidence"],
            det.get("is_empty_container", False),
            det.get("is_alive", True),
            datetime.now()
        ])

    csv_buffer.seek(0)

    # Use asyncpg raw connection for COPY
    async with self.session.connection() as conn:
        raw_conn = await conn.get_raw_connection()
        await raw_conn.driver_connection.copy_to_table(
            "detections",
            source=csv_buffer,
            columns=[
                "session_id", "stock_movement_id", "classification_id",
                "center_x_px", "center_y_px", "width_px", "height_px",
                "bbox_coordinates", "detection_confidence",
                "is_empty_container", "is_alive", "created_at"
            ],
            format="csv"
        )

    return len(detections)


async def get_by_session_id(
    self,
    session_id: int,
    include_empty: bool = False
) -> List[Detection]:
    """Get all detections for a photo session"""
    stmt = (
        select(Detection)
        .where(Detection.session_id == session_id)
        .options(
            joinedload(Detection.classification)
            .joinedload(Classification.product)
        )
    )

    if not include_empty:
        stmt = stmt.where(Detection.is_empty_container == False)

    result = await self.session.execute(stmt)
    return list(result.scalars().unique().all())


async def get_empty_containers(
    self,
    session_id: int
) -> List[Detection]:
    """Get empty container detections (for capacity planning)"""
    stmt = (
        select(Detection)
        .where(Detection.session_id == session_id)
        .where(Detection.is_empty_container == True)
        .options(joinedload(Detection.classification))
    )
    result = await self.session.execute(stmt)
    return list(result.scalars().all())
```

### Partitioned Table Handling

Detections table is partitioned by `created_at` (daily partitions). Repository must handle partition
pruning for performance.

## Testing Requirements

**Unit Tests**:

```python
@pytest.mark.asyncio
async def test_detection_repo_bulk_insert_with_copy(db_session):
    """Test asyncpg COPY bulk insert (CRITICAL for performance)"""
    repo = DetectionRepository(db_session)

    # Generate 1000 detections
    detections = [
        {
            "session_id": 1,
            "stock_movement_id": 100,
            "classification_id": 1,
            "center_x_px": 100.5 + i,
            "center_y_px": 200.3 + i,
            "width_px": 50,
            "height_px": 60,
            "bbox_coordinates": {"x1": 75, "y1": 170, "x2": 125, "y2": 230},
            "detection_confidence": 0.95,
            "is_empty_container": False,
            "is_alive": True
        }
        for i in range(1000)
    ]

    # Time the bulk insert
    import time
    start = time.time()
    count = await repo.bulk_insert_with_copy(detections)
    elapsed = time.time() - start

    assert count == 1000
    assert elapsed < 0.5  # Must be <500ms for 1000 detections
    print(f"Bulk insert: {count} detections in {elapsed:.3f}s")

@pytest.mark.asyncio
async def test_detection_repo_by_session(db_session, session_with_detections):
    """Test retrieving detections by session"""
    repo = DetectionRepository(db_session)
    detections = await repo.get_by_session_id(1)

    assert len(detections) > 0
    assert all(d.session_id == 1 for d in detections)

@pytest.mark.asyncio
async def test_detection_repo_empty_containers(db_session, session_with_empty):
    """Test filtering empty container detections"""
    repo = DetectionRepository(db_session)
    empties = await repo.get_empty_containers(1)

    assert len(empties) > 0
    assert all(d.is_empty_container == True for d in empties)
```

**Performance Benchmarks**:

- **CRITICAL**: Bulk insert 1000 detections: <100ms (asyncpg COPY) vs 2-5s (ORM insert)
- get_by_session_id: <50ms for 1000 detections (with partition pruning)
- get_empty_containers: <30ms (filtered query)

## Handover Briefing

**For the next developer:**

- **Context**: THIS IS THE #1 PERFORMANCE BOTTLENECK for ML pipeline. asyncpg COPY is
  NON-NEGOTIABLE.
- **Critical decisions**:
    - **asyncpg COPY**: 10-50x faster than ORM insert. Enables real-time ML processing.
    - Partitioned table: Daily partitions for performance. Use created_at in WHERE clauses for
      partition pruning.
    - area_px is GENERATED column: Never insert directly, PostgreSQL calculates automatically.
    - CSV format for COPY: Must match column order exactly (see code example).
- **Performance targets**:
    - 1000 detections: <100ms bulk insert
    - Single photo processing: <10s total (including YOLO inference)
- **Known limitations**:
    - COPY bypasses ORM validations (validate data BEFORE calling bulk_insert_with_copy)
    - Partitioned table requires partition maintenance (automated via cron)
- **Next steps**: R023 (EstimationRepository) uses same asyncpg COPY pattern

## Definition of Done Checklist

- [ ] Code written following AsyncRepository pattern
- [ ] **asyncpg COPY bulk insert implemented and tested with 1000+ detections**
- [ ] **Performance benchmark: <100ms for 1000 detections (MANDATORY)**
- [ ] Partitioned table queries tested
- [ ] Empty container filtering tested
- [ ] Unit tests pass (≥85% coverage)
- [ ] Linting passes (ruff check)
- [ ] Type hints validated (mypy)
- [ ] PR reviewed (2+ approvals, including performance review)
- [ ] Integration test with ML pipeline (end-to-end)

## Time Tracking

- **Estimated**: 8 story points (~16 hours)
- **Actual**: TBD

---

**Card Created**: 2025-10-09
**Last Updated**: 2025-10-09
**Card Owner**: TBD
**CRITICAL PATH**: ML pipeline performance depends on this card
