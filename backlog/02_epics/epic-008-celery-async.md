# Epic 008: Celery & Async Processing

**Status**: Ready
**Sprint**: Sprint-04 (Week 9-10)
**Priority**: critical (ML pipeline execution)
**Total Story Points**: 40
**Total Cards**: 8 (CEL001-CEL008)

---

## Goal

Implement Celery 5.4.0 async task processing with worker configuration for GPU (pool=solo), CPU (prefork), and I/O (gevent) workers, enabling the ML pipeline and background job execution.

---

## Success Criteria

- [ ] All 8 Celery cards implemented
- [ ] GPU workers use pool=solo (MANDATORY - prevents CUDA conflicts)
- [ ] Chord pattern implemented for ML parent/child tasks
- [ ] Task retry with exponential backoff
- [ ] Dead Letter Queue (DLQ) for failed tasks
- [ ] Flower monitoring accessible at localhost:5555
- [ ] Correlation IDs propagate from API to Celery
- [ ] All workers start successfully in docker-compose

---

## Cards List (8 cards, 40 points)

### Worker Configuration (15 points)
- **CEL001**: GPU worker config (pool=solo) (5pts) - **CRITICAL**
- **CEL002**: CPU worker config (prefork) (3pts)
- **CEL003**: I/O worker config (gevent) (3pts)
- **CEL004**: Worker recycling & memory limits (2pts)
- **CEL005**: Flower monitoring setup (2pts)

### Task Implementation (20 points)
- **CEL006**: ML parent task (segmentation) (8pts) - **CRITICAL PATH**
- **CEL007**: ML child tasks (SAHI detection) (8pts) - **CRITICAL PATH**
- **CEL008**: Chord callback (aggregation) (4pts)

### Reliability & Monitoring (5 points)
- **CEL009**: Task retry with exponential backoff (2pts)
- **CEL010**: Dead Letter Queue (DLQ) setup (2pts)
- **CEL011**: Celery beat (periodic tasks - future) (1pt)

---

## Dependencies

**Blocked By**: S031-S039 (ML services), F012 (docker-compose)
**Blocks**: Photo upload workflow, ML pipeline execution

---

## Technical Approach

**CRITICAL: GPU Worker Configuration**
```python
# MANDATORY: pool=solo for GPU workers
CUDA_VISIBLE_DEVICES=0 celery -A app.celery_app worker \
  --pool=solo \             # ← REQUIRED for GPU
  --concurrency=1 \         # ← ONE task per worker
  --queues=gpu_queue_0 \
  --max-tasks-per-child=50 \
  --max-memory-per-child=8000000  # 8GB limit
```

**Why pool=solo?**
- prefork causes CUDA context conflicts
- Model Singleton requires isolated GPU memory
- Industry best practice for GPU workloads

**Chord Pattern (ML Pipeline)**:
```python
from celery import chord, group

@celery_app.task(bind=True)
def ml_parent_task(self, photo_id: int, correlation_id: str):
    """Parent: YOLO segmentation."""
    segments = run_segmentation(photo_id)

    # Spawn child tasks for each segment
    callback = aggregate_results.signature((photo_id,))
    header = group(
        ml_child_task.signature((seg, photo_id)) for seg in segments
    )

    return chord(header)(callback)

@celery_app.task
def ml_child_task(segment: dict, photo_id: int):
    """Child: SAHI detection on segment."""
    return run_sahi_detection(segment)

@celery_app.task
def aggregate_results(results: list, photo_id: int):
    """Callback: Aggregate all child results."""
    total_detected = sum(r['count'] for r in results)
    # Create stock_movements, stock_batches
```

**Task Retry with Backoff**:
```python
@celery_app.task(
    bind=True,
    autoretry_for=(S3Exception, DatabaseException),
    retry_backoff=True,
    retry_kwargs={'max_retries': 3},
    retry_backoff_max=600  # 10 minutes max
)
def upload_to_s3(self, file_path: str):
    # Exponential backoff: 2^retry_num seconds
    # Retry 1: 2s, Retry 2: 4s, Retry 3: 8s
    pass
```

**Correlation ID Propagation**:
```python
# API controller
correlation_id = get_correlation_id()
task = ml_parent_task.delay(photo_id, correlation_id=correlation_id)

# In Celery task
set_correlation_id(correlation_id)  # From F004
logger.info("Processing photo", photo_id=photo_id)
```

---

**Epic Owner**: ML Pipeline Lead
**Created**: 2025-10-09
