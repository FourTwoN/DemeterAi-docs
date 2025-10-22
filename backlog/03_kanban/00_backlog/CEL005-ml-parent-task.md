# [CEL005] ML Parent Task ⚡⚡

## Metadata

- **Epic**: epic-008
- **Sprint**: Sprint-04
- **Priority**: critical ⚡⚡ **CRITICAL PATH**
- **Complexity**: M (5 points)
- **Dependencies**: Blocks [Sprint completion], Blocked by [ML009, CEL004]

## Description

Parent task that spawns ML child tasks (one per image) using chord pattern. **CRITICAL PATH** -
blocks Sprint 04 completion.

## Acceptance Criteria

- [ ] Task `ml_parent_task(session_code, image_ids)`
- [ ] Spawns one child task per image_id
- [ ] Uses chord pattern → callback
- [ ] Updates PhotoProcessingSession status to 'processing'
- [ ] Error handling with warning states

## Implementation

```python
@app.task(bind=True)
def ml_parent_task(self, session_code, image_ids):
    # Update session status
    session_repo.update_status(session_code, 'processing')

    # Create child tasks
    children = [
        ml_child_task.s(session_code, img_id)
        for img_id in image_ids
    ]

    # Chord: children → callback
    chord(children)(ml_callback.s(session_code))
```

---
**Card Created**: 2025-10-09
**Critical Path**: ⚡⚡ YES
