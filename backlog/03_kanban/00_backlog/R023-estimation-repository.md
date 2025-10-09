# R023: Estimation Repository (with asyncpg COPY Bulk Insert)

## Metadata
- **Epic**: [epic-003-repositories.md](../../02_epics/epic-003-repositories.md)
- **Sprint**: Sprint-02
- **Status**: `backlog`
- **Priority**: `CRITICAL` (V1 - ML pipeline bottleneck)
- **Complexity**: L (8 story points)
- **Area**: `repositories`
- **Assignee**: TBD
- **Dependencies**:
  - Blocks: [ML009, S020]
  - Blocked by: [F006, F007, DB014, R019, R024]

## Related Documentation
- **Engineering Plan**: [../../engineering_plan/backend/repository_layer.md](../../engineering_plan/backend/repository_layer.md)
- **Database ERD**: [../../database/database.mmd](../../database/database.mmd#L277-L289)

## Description

**What**: Implement repository class for `estimations` table (partitioned by created_at) with CRUD operations and **asyncpg COPY bulk insert** for ML pipeline performance.

**Why**: Estimations store vegetation area-based plant counts (100s per photo). **ORM insert is too slow**. asyncpg COPY enables **<50ms bulk insert** for 500+ estimations. CRITICAL for band-estimation ML pipeline.

**Context**: Partitioned table (daily partitions). Each photo generates 50-500 estimations (one per segment). Bulk insert required for performance. Complements detections (individual plants vs. vegetation areas).

## Acceptance Criteria

- [ ] **AC1**: `EstimationRepository` class inherits from `AsyncRepository[Estimation]`
- [ ] **AC2**: Implements `get_by_session_id(session_id: int)` for photo estimations
- [ ] **AC3**: **CRITICAL**: Implements `bulk_insert_with_copy(estimations: List[dict])` using asyncpg COPY
- [ ] **AC4**: Implements `get_by_calculation_method(session_id: int, method: str)` for method filtering
- [ ] **AC5**: Implements `get_high_confidence_estimations(session_id: int, threshold: float)` for filtering
- [ ] **AC6**: Handles partitioned table queries (created_at partitions)
- [ ] **AC7**: Performance: bulk insert <50ms for 500 estimations, session query <30ms

## Technical Implementation Notes

### asyncpg COPY Bulk Insert (CRITICAL)

```python
async def bulk_insert_with_copy(
    self,
    estimations: List[dict]
) -> int:
    """Bulk insert estimations using asyncpg COPY (10-50x faster than ORM)

    Same pattern as DetectionRepository but for estimations.
    """
    from io import StringIO
    import csv

    csv_buffer = StringIO()
    writer = csv.writer(csv_buffer)

    for est in estimations:
        writer.writerow([
            est["session_id"],
            est["stock_movement_id"],
            est["classification_id"],
            json.dumps(est["vegetation_polygon"]),
            est["detected_area_cm2"],
            est["estimated_count"],
            est["calculation_method"],
            est.get("estimation_confidence", 0.70),
            est.get("used_density_parameters", False),
            datetime.now()
        ])

    csv_buffer.seek(0)

    async with self.session.connection() as conn:
        raw_conn = await conn.get_raw_connection()
        await raw_conn.driver_connection.copy_to_table(
            "estimations",
            source=csv_buffer,
            columns=[
                "session_id", "stock_movement_id", "classification_id",
                "vegetation_polygon", "detected_area_cm2", "estimated_count",
                "calculation_method", "estimation_confidence",
                "used_density_parameters", "created_at"
            ],
            format="csv"
        )

    return len(estimations)


async def get_by_calculation_method(
    self,
    session_id: int,
    calculation_method: str
) -> List[Estimation]:
    """Get estimations by calculation method (band/density/grid)"""
    stmt = (
        select(Estimation)
        .where(Estimation.session_id == session_id)
        .where(Estimation.calculation_method == calculation_method)
        .options(
            joinedload(Estimation.classification)
            .joinedload(Classification.product)
        )
    )
    result = await self.session.execute(stmt)
    return list(result.scalars().unique().all())


async def get_high_confidence_estimations(
    self,
    session_id: int,
    confidence_threshold: float = 0.70
) -> List[Estimation]:
    """Get high-confidence estimations (for quality filtering)"""
    stmt = (
        select(Estimation)
        .where(Estimation.session_id == session_id)
        .where(Estimation.estimation_confidence >= confidence_threshold)
        .options(joinedload(Estimation.classification))
        .order_by(Estimation.estimation_confidence.desc())
    )
    result = await self.session.execute(stmt)
    return list(result.scalars().unique().all())
```

## Testing Requirements

**Performance Benchmarks**:
- **CRITICAL**: Bulk insert 500 estimations: <50ms (asyncpg COPY) vs 1-3s (ORM insert)
- get_by_session_id: <30ms for 500 estimations (with partition pruning)
- get_by_calculation_method: <20ms (filtered query)

## Handover Briefing

**For the next developer:**
- **Context**: Same asyncpg COPY pattern as R022 (DetectionRepository). Critical for band-estimation pipeline performance.
- **Critical decisions**:
  - calculation_method enum: band_estimation | density_estimation | grid_analysis
  - estimation_confidence default 0.70 (lower than detection confidence due to indirect counting)
  - vegetation_polygon is JSONB (GeoJSON format)
- **Performance targets**:
  - 500 estimations: <50ms bulk insert
  - Band-estimation photo: <15s total (including YOLO + band analysis)

## Definition of Done Checklist

- [ ] Code written following AsyncRepository pattern
- [ ] **asyncpg COPY bulk insert implemented and tested with 500+ estimations**
- [ ] **Performance benchmark: <50ms for 500 estimations (MANDATORY)**
- [ ] Partitioned table queries tested
- [ ] Calculation method filtering tested
- [ ] Unit tests pass (≥85% coverage)
- [ ] PR reviewed (2+ approvals)

## Time Tracking
- **Estimated**: 8 story points (~16 hours)
- **Actual**: TBD

---

**Card Created**: 2025-10-09
**Last Updated**: 2025-10-09
**Card Owner**: TBD
**CRITICAL PATH**: ML pipeline performance depends on this card
