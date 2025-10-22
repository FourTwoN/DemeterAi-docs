# [TEST005] ML Pipeline Integration Tests

## Metadata

- **Epic**: epic-012-testing
- **Sprint**: Sprint-05
- **Priority**: `high`
- **Complexity**: L (8 points)
- **Dependencies**: Blocked by [ML009, TEST001, TEST002]

## Description

End-to-end tests for ML pipeline using sample photos: segmentation → detection → estimation → batch
creation.

## Acceptance Criteria

- [ ] Sample test photos in `tests/fixtures/photos/`
- [ ] Test full pipeline with real photo
- [ ] Test with known ground truth (verify counts)
- [ ] Test edge cases (empty photo, no plants, low quality)
- [ ] Test GPU and CPU code paths
- [ ] Test async Celery task execution (or mock)

## Implementation

**tests/integration/test_ml_pipeline.py:**

```python
@pytest.mark.asyncio
async def test_ml_pipeline_full_workflow(db_session, test_photo):
    """Test complete ML pipeline with sample photo."""
    # 1. Upload photo
    photo_session = await create_photo_session(
        file_path=test_photo,
        location_id=1
    )

    # 2. Run ML pipeline (synchronous for testing)
    await ml_pipeline_coordinator.process_photo(photo_session.id)

    # 3. Verify results
    detections = await detection_repo.get_by_photo_session(photo_session.id)
    assert len(detections) > 0

    estimations = await estimation_repo.get_by_photo_session(photo_session.id)
    assert len(estimations) > 0

    # 4. Verify stock movements created
    movements = await stock_movement_repo.get_by_photo_session(photo_session.id)
    assert movements.movement_type == "foto"
    assert movements.quantity == sum(e.plant_count for e in estimations)

@pytest.mark.parametrize("photo_file,expected_count", [
    ("test_10_plants.jpg", 10),
    ("test_50_plants.jpg", 50),
    ("test_empty.jpg", 0),
])
def test_ml_pipeline_ground_truth(photo_file, expected_count):
    """Test ML pipeline accuracy with known ground truth."""
    result = run_ml_pipeline(f"tests/fixtures/photos/{photo_file}")

    # Allow 10% error margin
    assert abs(result.total_count - expected_count) <= expected_count * 0.1
```

## Testing

- Run tests with GPU (if available)
- Run tests with CPU fallback
- Verify timing (GPU faster than CPU)
- Verify accuracy within acceptable range

---
**Card Created**: 2025-10-09
