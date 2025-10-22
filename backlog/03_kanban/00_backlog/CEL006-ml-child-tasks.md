# [CEL006] ML Child Tasks ⚡⚡

## Metadata

- **Epic**: epic-008
- **Sprint**: Sprint-04
- **Priority**: critical ⚡⚡ **CRITICAL PATH**
- **Complexity**: M (5 points)
- **Dependencies**: Blocks [CEL007], Blocked by [CEL005, ML009]

## Description

Child task that processes one image through ML009 pipeline coordinator. Runs on GPU queue.

## Acceptance Criteria

- [ ] Task `ml_child_task(session_code, image_id)`
- [ ] Calls ML009.process_complete_pipeline()
- [ ] Updates progress in PhotoProcessingSession
- [ ] Returns results dict
- [ ] Retry logic: max 3 retries, exponential backoff

## Implementation

```python
@app.task(bind=True, queue='gpu_queue', max_retries=3)
def ml_child_task(self, session_code, image_id):
    try:
        coordinator = MLPipelineCoordinator()
        results = await coordinator.process_complete_pipeline(session_id, image_path)
        return results
    except Exception as e:
        raise self.retry(exc=e, countdown=2**self.request.retries)
```

---
**Card Created**: 2025-10-09
**Critical Path**: ⚡⚡ YES
