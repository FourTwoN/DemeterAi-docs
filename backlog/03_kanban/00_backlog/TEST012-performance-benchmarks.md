# [TEST012] Performance Benchmarks (pytest-benchmark)

## Metadata

- **Epic**: epic-012-testing
- **Sprint**: Sprint-07
- **Priority**: `low`
- **Complexity**: M (5 points)
- **Dependencies**: Blocked by [TEST005]

## Description

Benchmark critical code paths: API endpoints, ML inference, database queries. Track performance
regressions.

## Acceptance Criteria

- [ ] pytest-benchmark installed
- [ ] Benchmark API endpoints (<100ms target)
- [ ] Benchmark ML inference (CPU vs GPU)
- [ ] Benchmark database queries (<50ms)
- [ ] Compare benchmarks across runs
- [ ] CI fails if performance regresses >20%

## Implementation

```python
def test_api_benchmark_stock_summary(benchmark, client, auth_headers):
    """Benchmark stock summary endpoint."""
    def get_summary():
        return client.get("/api/stock/summary", headers=auth_headers)

    result = benchmark(get_summary)
    assert result.status_code == 200

def test_ml_benchmark_segmentation(benchmark, test_photo):
    """Benchmark YOLO segmentation."""
    from app.services.ml_processing.segmentation_service import segment_image

    result = benchmark(segment_image, test_photo)
    assert len(result) > 0

def test_db_benchmark_complex_query(benchmark, db_session):
    """Benchmark complex database query."""
    from app.repositories.stock_movement_repository import StockMovementRepository

    repo = StockMovementRepository(StockMovement, db_session)

    async def query():
        return await repo.get_summary_by_location(location_id=1)

    result = benchmark(lambda: asyncio.run(query()))
    assert result is not None
```

**Run benchmarks:**

```bash
pytest tests/benchmarks/ --benchmark-only

# Compare with baseline
pytest tests/benchmarks/ --benchmark-compare=0001
```

**Benchmark report:**

```
Name                           Min      Max      Mean    StdDev
test_api_benchmark_summary     45ms     60ms     52ms     3ms
test_ml_benchmark_segment      2.5s     3.0s     2.7s     0.1s
test_db_benchmark_query        25ms     35ms     30ms     2ms
```

## Testing

- Run benchmarks on representative hardware
- Store baseline results
- Detect performance regressions
- Optimize slow code paths

---
**Card Created**: 2025-10-09
