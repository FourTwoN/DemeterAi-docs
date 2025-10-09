# [ML001] Model Singleton Pattern for YOLO Models

## Metadata
- **Epic**: epic-007-ml-pipeline.md
- **Sprint**: Sprint-02 (Week 5-6) **⚡ CRITICAL PATH**
- **Status**: `backlog`
- **Priority**: `critical` (V3 - blocks all ML work)
- **Complexity**: L (8 story points)
- **Area**: `ml-pipeline`
- **Assignee**: TBD
- **Dependencies**:
  - Blocks: [ML002, ML003, ML004, ML009] (ALL ML services need this)
  - Blocked by: [DB010-detections-model, F006-db-connection]

## Related Documentation
- **Engineering Plan**: ../../engineering_plan/backend/ml_pipeline.md (lines 120-180)
- **Flow Diagram**: ../../flows/procesamiento_ml_upload_s3_principal/PIPELINE_OVERVIEW.md
- **Past Decisions**: ../../context/past_chats_summary.md (lines 622-657)
- **Tech Stack**: ../../backlog/00_foundation/tech-stack.md (YOLO v11, torch==2.4.0)

## Description

Implement Model Singleton pattern to ensure YOLO models are loaded ONCE per Celery worker (not per task), preventing 2-3s model load overhead on every photo.

**What**: Create `ModelCache` class that maintains single model instances per GPU worker, with thread-safe access and proper GPU memory management.

**Why**: Loading YOLO models is expensive (2-3s per load, ~500MB RAM). Processing 600k photos with per-task loading = 300-500 hours wasted. Singleton pattern reduces this to <1 hour total (one-time load per worker).

**Context**: This is the FIRST ML card and blocks ALL other ML work. GPU workers use `pool=solo` (1 task at a time), so singleton is safe. CPU fallback also supported.

## Acceptance Criteria

- [ ] **AC1**: `ModelCache` class created in `app/services/ml_processing/model_cache.py`:
  - Thread-safe singleton (use threading.Lock)
  - Separate instances per GPU (keyed by worker_id)
  - Lazy loading (load on first access, cache thereafter)
  - Supports both segmentation and detection models

- [ ] **AC2**: Model loading with proper device assignment:
  ```python
  from ultralytics import YOLO
  model = YOLO('yolov11m-seg.pt')
  model.to(f'cuda:{worker_id}')  # Or 'cpu' if GPU unavailable
  model.fuse()  # Layer fusion for 10-15% speedup
  ```

- [ ] **AC3**: GPU memory cleanup after N tasks:
  ```python
  if task_count % 100 == 0:
      torch.cuda.empty_cache()
  ```

- [ ] **AC4**: CPU fallback works automatically:
  ```python
  try:
      model.to(f'cuda:{worker_id}')
  except Exception:
      logger.warning("GPU unavailable, using CPU")
      model.to('cpu')
  ```

- [ ] **AC5**: Custom Celery Task base class uses singleton:
  ```python
  class ModelSingletonTask(Task):
      _model_cache = None

      @property
      def model(self):
          if self._model_cache is None:
              self._model_cache = ModelCache.get_model(...)
          return self._model_cache
  ```

- [ ] **AC6**: Unit tests:
  - Test singleton returns same instance on repeated calls
  - Test separate instances for different GPU IDs
  - Test CPU fallback when GPU unavailable
  - Test thread safety (concurrent access)

- [ ] **AC7**: Performance validated:
  - First task: 2-3s (model load)
  - Subsequent tasks: <100ms overhead (cache hit)
  - Memory usage stable (no leaks after 100 tasks)

## Technical Implementation Notes

### Architecture
- Layer: ML Service (Infrastructure)
- Dependencies: Ultralytics (YOLO), PyTorch, threading
- Design pattern: Singleton + Lazy Loading + Thread Safety

### Code Hints

**ModelCache structure:**
```python
from threading import Lock
from typing import Dict, Literal
from ultralytics import YOLO
import torch

class ModelCache:
    _instances: Dict[str, YOLO] = {}
    _lock = Lock()

    @classmethod
    def get_model(
        cls,
        model_type: Literal["segment", "detect"],
        worker_id: int = 0
    ) -> YOLO:
        """Get cached model or load if first access."""
        key = f"yolo_{model_type}_{worker_id}"

        with cls._lock:
            if key not in cls._instances:
                # Load model (happens ONCE per worker)
                model_path = "yolov11m-seg.pt" if model_type == "segment" else "yolov11m.pt"
                model = YOLO(model_path)

                # Device assignment
                device = f"cuda:{worker_id}" if torch.cuda.is_available() else "cpu"
                model.to(device)
                model.fuse()  # Optimization

                cls._instances[key] = model

            return cls._instances[key]
```

**Celery Task integration:**
```python
from celery import Task

class ModelSingletonTask(Task):
    _seg_model = None
    _det_model = None

    @property
    def seg_model(self):
        if self._seg_model is None:
            worker_id = self.get_worker_id()
            self._seg_model = ModelCache.get_model("segment", worker_id)
        return self._seg_model

    def after_return(self, *args, **kwargs):
        # Cleanup every 100 tasks
        if self.request.id % 100 == 0:
            torch.cuda.empty_cache()
```

### Testing Requirements

**Unit Tests**:
- [ ] Test singleton pattern (same instance returned)
- [ ] Test GPU device assignment (`model.device == f'cuda:0'`)
- [ ] Test CPU fallback (mock torch.cuda.is_available = False)
- [ ] Test thread safety (concurrent access from 10 threads)
- [ ] Test memory cleanup (torch.cuda.empty_cache called)

**Integration Tests**:
- [ ] Load both models (segment + detect) in same worker
- [ ] Run 10 tasks, verify model loaded only once
- [ ] Monitor memory usage (should be stable)

**Test Template**: See `04_templates/test-templates/test_service_template.py`

### Performance Expectations
- **First task**: 2-3s (model load + inference)
- **Subsequent tasks**: <100ms (cache hit)
- **Memory**: ~500MB per model (stable, no growth)
- **GPU utilization**: 80-95% during inference

## Handover Briefing

**For the next developer:**
- **Context**: This is THE critical path card for ML pipeline. All other ML cards (ML002-ML018) depend on this.
- **Key decisions**:
  - Singleton per GPU worker (not global singleton)
  - Thread-safe with Lock (prevents race conditions)
  - CPU fallback automatic (enables development without GPU)
  - Cleanup every 100 tasks (prevents memory leaks)
- **Known limitations**:
  - Only works with Celery `pool=solo` (verified in Sprint 00)
  - GPU worker recycling every 50 tasks (configured in Celery)
- **Next steps after this card**:
  - ML002: YOLO Segmentation Service (uses this singleton)
  - ML003: SAHI Detection Service (uses this singleton)
  - ML009: Pipeline Coordinator (orchestrates all ML services)
- **Questions to ask**:
  - If GPU unavailable, should task fail or fallback to CPU? (Answer: Fallback to CPU, log warning)
  - How to get worker_id in Celery? (Answer: Parse from `self.request.hostname`)

## Definition of Done Checklist

- [ ] Code passes all tests (pytest)
- [ ] Coverage ≥85% for model_cache.py
- [ ] Linted and formatted (ruff check + ruff format)
- [ ] Type hints added (mypy passes)
- [ ] Docstrings for public methods (Google style)
- [ ] Integration tests pass (load model, run inference)
- [ ] Performance validated (timing logged for first vs subsequent tasks)
- [ ] PR approved by 2+ reviewers (including ML Lead)
- [ ] Documentation updated (add model_cache.py to architecture docs)
- [ ] GPU memory monitoring added (log GPU usage every 10 tasks)

## Time Tracking
- **Estimated**: 8 story points
- **Actual**: TBD
- **Started**: TBD
- **Completed**: TBD

---

**Card Created**: 2025-10-09
**Last Updated**: 2025-10-09
**Card Owner**: TBD (assign during sprint planning)
**⚡ CRITICAL PATH**: ML pipeline success depends on this card
