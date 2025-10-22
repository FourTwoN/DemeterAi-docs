# [TEST007] Celery Task Tests

## Metadata

- **Epic**: epic-012-testing
- **Sprint**: Sprint-04
- **Priority**: `medium`
- **Complexity**: M (5 points)
- **Dependencies**: Blocked by [CEL005, TEST001]

## Description

Test Celery tasks in isolation: mock task execution, verify task logic, test retries and error
handling.

## Acceptance Criteria

- [ ] Test task execution without Celery broker
- [ ] Test task retries on failure
- [ ] Test max retry limits
- [ ] Test task result persistence
- [ ] Test chord pattern (parent → children → callback)
- [ ] Test task routing to correct queues

## Implementation

```python
from app.tasks.ml_tasks import segment_photo_task

def test_segment_photo_task(db_session, test_photo):
    """Test segmentation task logic (without Celery)."""
    # Call task directly (synchronous)
    result = segment_photo_task.apply(args=[test_photo.id]).get()

    assert result["status"] == "success"
    assert result["segments_found"] > 0

@pytest.mark.celery
def test_segment_photo_task_with_celery(celery_app, db_session):
    """Test task execution via Celery broker."""
    # Submit task asynchronously
    task = segment_photo_task.delay(photo_id=123)

    # Wait for completion (timeout 30s)
    result = task.get(timeout=30)

    assert result["status"] == "success"

def test_task_retry_on_failure(monkeypatch):
    """Test task retries on transient failure."""
    call_count = 0

    def mock_predict(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise RuntimeError("Transient error")
        return {"segments": [...]}

    monkeypatch.setattr("app.services.ml_processing.segmentation_service.model.predict", mock_predict)

    result = segment_photo_task.apply(args=[123])

    assert call_count == 3  # Retried 2 times
    assert result.status == "SUCCESS"
```

## Testing

- Test tasks with and without Celery
- Test retry logic
- Test DLQ (dead letter queue)
- Verify task results stored

---
**Card Created**: 2025-10-09
