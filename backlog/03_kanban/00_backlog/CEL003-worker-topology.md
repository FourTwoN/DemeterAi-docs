# [CEL003] Worker Topology - GPU/CPU/IO

## Metadata
- **Epic**: epic-008
- **Sprint**: Sprint-04
- **Priority**: critical ⚡⚡
- **Complexity**: M (5 points)
- **Dependencies**: Blocks [CEL005-CEL006], Blocked by [CEL001]

## Description
Configure 3 worker types: GPU (pool=solo), CPU (pool=prefork), IO (pool=gevent). **CRITICAL**: pool=solo for GPU workers is MANDATORY.

## Acceptance Criteria
- [ ] GPU worker: `celery -A app worker --pool=solo --concurrency=1 --queues=gpu_queue`
- [ ] CPU worker: `celery -A app worker --pool=prefork --concurrency=4 --queues=cpu_queue`
- [ ] IO worker: `celery -A app worker --pool=gevent --concurrency=50 --queues=io_queue`
- [ ] Route ML tasks to GPU queue
- [ ] Route aggregation to CPU queue
- [ ] Route S3/DB to IO queue

## Implementation
```python
app.conf.task_routes = {
    'app.tasks.ml_*': {'queue': 'gpu_queue'},
    'app.tasks.aggregate_*': {'queue': 'cpu_queue'},
    'app.tasks.upload_*': {'queue': 'io_queue'},
}
```

**CRITICAL**: GPU workers MUST use pool=solo (ADR-005). prefork causes CUDA context conflicts.

---
**Card Created**: 2025-10-09
**Critical**: ⚡⚡ MANDATORY pool=solo for GPU
