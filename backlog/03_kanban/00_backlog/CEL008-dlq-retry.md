# [CEL008] DLQ + Retry Logic

## Metadata
- **Epic**: epic-008
- **Sprint**: Sprint-04
- **Priority**: medium
- **Complexity**: S (3 points)
- **Dependencies**: Blocked by [CEL005-CEL007]

## Description
Dead Letter Queue for permanently failed tasks + exponential backoff retry logic.

## Acceptance Criteria
- [ ] DLQ queue for failed tasks after max retries
- [ ] Exponential backoff: 2s, 4s, 8s
- [ ] Max retries: 3
- [ ] Failed task metadata logged
- [ ] Admin notification on DLQ entry

## Implementation
```python
app.conf.task_reject_on_worker_lost = True
app.conf.task_acks_late = True
app.conf.task_default_retry_delay = 2  # 2s base
app.conf.task_max_retries = 3

@app.task(bind=True, max_retries=3)
def task_with_retry(self):
    try:
        # ... task logic
    except Exception as e:
        countdown = 2 ** self.request.retries
        raise self.retry(exc=e, countdown=countdown)
```

---
**Card Created**: 2025-10-09
