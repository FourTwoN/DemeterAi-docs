# [CEL007] Callback Aggregation

## Metadata
- **Epic**: epic-008
- **Sprint**: Sprint-04
- **Priority**: critical ⚡
- **Complexity**: S (3 points)
- **Dependencies**: Blocked by [CEL006]

## Description
Callback that aggregates all child task results and updates PhotoProcessingSession to 'completed'.

## Acceptance Criteria
- [ ] Callback `ml_callback(results, session_code)`
- [ ] Aggregates total detections, estimations
- [ ] Updates session status to 'completed' or 'warning'
- [ ] Calculates average confidence
- [ ] Sets completed_at timestamp

## Implementation
```python
@app.task
def ml_callback(results, session_code):
    total_detections = sum(r['detections'] for r in results)
    total_estimations = sum(r['estimations'] for r in results)
    
    session_repo.update({
        'status': 'completed',
        'total_plants_detected': total_detections,
        'total_plants_estimated': total_detections + total_estimations,
        'completed_at': datetime.utcnow()
    })
```

---
**Card Created**: 2025-10-09
