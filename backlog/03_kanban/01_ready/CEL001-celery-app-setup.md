# [CEL001] Celery App Setup

## Metadata

- **Epic**: epic-008-celery-async
- **Sprint**: Sprint-04
- **Priority**: critical ⚡
- **Complexity**: S (3 points)
- **Dependencies**: Blocks [CEL002-CEL008], Blocked by [F002]

## Description

Initialize Celery application with broker (Redis), result backend, and serialization config.

## Acceptance Criteria

- [ ] Celery app in `app/celery_app.py`
- [ ] Broker: `redis://localhost:6379/0`
- [ ] Result backend: `redis://localhost:6379/1`
- [ ] Serialization: JSON (not pickle - security)
- [ ] Task autodiscovery from `app.tasks`
- [ ] Timezone: UTC

## Implementation

```python
from celery import Celery

app = Celery(
    'demeterai',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/1'
)

app.conf.update(
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_autodiscovery=['app.tasks']
)
```

## Testing

- Verify app starts
- Test task registration

---
**Card Created**: 2025-10-09
