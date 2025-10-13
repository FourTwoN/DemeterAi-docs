# [CEL004] Chord Pattern Implementation

## Metadata
- **Epic**: epic-008
- **Sprint**: Sprint-04
- **Priority**: critical ⚡
- **Complexity**: M (5 points)
- **Dependencies**: Blocks [CEL005], Blocked by [CEL003]

## Description
Implement Celery chord pattern: parent task → multiple child tasks → callback aggregation.

## Acceptance Criteria
- [ ] Chord pattern: `chord([child1.s(), child2.s(), ...], callback.s())`
- [ ] Parent spawns N child tasks
- [ ] Children run in parallel
- [ ] Callback receives all results
- [ ] Error handling (if one child fails, callback still runs with partial results)

## Implementation
```python
from celery import chord

@app.task
def parent_task(session_id):
    # Create child task signatures
    children = [
        child_task.s(session_id, i)
        for i in range(num_children)
    ]

    # Chord: children → callback
    chord(children)(callback.s(session_id))
```

---
**Card Created**: 2025-10-09
