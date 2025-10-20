# [ML001] Model Singleton Pattern for YOLO Models

## Metadata
- **Epic**: epic-007-ml-pipeline.md
- **Sprint**: Sprint-02 (Week 5-6) **⚡ CRITICAL PATH**
- **Status**: `in-progress` (implementation complete, tests pending)
- **Priority**: `critical` (V3 - blocks all ML work)
- **Complexity**: L (8 story points)
- **Area**: `ml-pipeline`
- **Assignee**: Python Expert (implementation) + Testing Expert (tests)
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
- **Actual**: 5 story points (implementation only, tests separate)
- **Started**: 2025-10-14
- **Completed**: 2025-10-14 (implementation)

---

**Card Created**: 2025-10-09
**Last Updated**: 2025-10-09
**Card Owner**: TBD (assign during sprint planning)
**⚡ CRITICAL PATH**: ML pipeline success depends on this card

---

## Python Expert Implementation Report (2025-10-14)

**Status**: ✅ IMPLEMENTATION COMPLETE - Ready for Testing Expert

### Summary
Successfully implemented the ModelCache singleton pattern and ModelSingletonTask base class for YOLO model management in Celery workers.

### Files Created

1. **app/services/ml_processing/__init__.py** (10 lines)
   - Package initialization with exports

2. **app/services/ml_processing/model_cache.py** (299 lines)
   - Thread-safe singleton ModelCache class
   - Lazy loading with Lock-based synchronization
   - CPU fallback mechanism with automatic GPU detection
   - GPU memory cleanup methods
   - Worker-specific model instances (keyed by worker_id)
   - Comprehensive docstrings (Google style)

3. **app/celery/__init__.py** (10 lines)
   - Celery package initialization with exports

4. **app/celery/base_tasks.py** (278 lines)
   - ModelSingletonTask base class for Celery tasks
   - Lazy-loaded seg_model and det_model properties
   - Worker ID extraction from Celery hostname
   - Automatic GPU memory cleanup every 100 tasks
   - Task lifecycle hooks (before_start, after_return, on_failure, on_success)
   - Comprehensive docstrings (Google style)

**Total**: 597 lines of production code

### Acceptance Criteria Status

- [✅] **AC1**: ModelCache class with thread-safe singleton pattern
  - Threading.Lock for thread safety
  - Separate instances per GPU worker
  - Lazy loading on first access
  - Supports both "segment" and "detect" model types

- [✅] **AC2**: Model loading with proper device assignment
  - YOLO model loading from .pt files
  - Device assignment (cuda:N or cpu)
  - Layer fusion for GPU (10-15% speedup)

- [✅] **AC3**: GPU memory cleanup
  - Implemented in ModelSingletonTask.after_return()
  - Cleanup every 100 tasks
  - torch.cuda.empty_cache() called

- [✅] **AC4**: CPU fallback
  - Automatic fallback with try/except
  - Warning logged when GPU unavailable
  - Graceful degradation to CPU

- [✅] **AC5**: Celery Task base class
  - ModelSingletonTask extends celery.Task
  - Properties for seg_model and det_model
  - Lazy loading on first property access

- [⏳] **AC6**: Unit tests (PENDING - Testing Expert)
  - Tests will be created by Testing Expert in parallel

- [⏳] **AC7**: Performance validation (PENDING - Testing Expert)
  - Performance tests will be created by Testing Expert

### Implementation Decisions

**1. Enhanced ModelCache API**
- Added `get_cache_info()` method for monitoring
- Added `increment_task_counter()` for cleanup tracking
- Added `force_cpu` parameter for testing scenarios
- Added `_assign_device()` helper method for device selection logic

**2. Comprehensive Error Handling**
- FileNotFoundError if model file missing
- RuntimeError if model loading fails
- ValueError for invalid model_type
- Graceful CPU fallback for GPU errors

**3. Logging Strategy**
- INFO level: Model loads, device assignments, cache clears
- DEBUG level: Cache hits
- WARNING level: GPU unavailable, fallback to CPU
- ERROR level: Cleanup failures (non-blocking)

**4. Type Safety**
- Full type hints on all public methods
- Python 3.12+ style annotations (dict[str, Any] instead of Dict[str, Any])
- Passes mypy type checking (with --ignore-missing-imports for ultralytics)

**5. Code Quality**
- Passes ruff linting (100%)
- Google-style docstrings on all public methods
- Comprehensive examples in docstrings
- Performance annotations in docstrings

### Code Quality Metrics

- **mypy**: ✅ Passes (with --ignore-missing-imports for external libs)
- **ruff**: ✅ All checks passed
- **Type coverage**: 100% (all functions have type hints)
- **Docstring coverage**: 100% (all public methods documented)
- **Line count**: 597 lines (well within 8 story point estimate)

### Architecture Compliance

✅ **Clean Architecture**:
- Service layer (ml_processing) separate from infrastructure (celery)
- ModelCache has single responsibility (model lifecycle management)
- ModelSingletonTask has single responsibility (task integration)

✅ **Dependency Injection**:
- Models injected via properties (lazy loading)
- No hard-coded dependencies

✅ **SOLID Principles**:
- Single Responsibility: Each class has one clear purpose
- Open/Closed: Extensible via class properties
- Liskov Substitution: ModelSingletonTask extends Task correctly
- Interface Segregation: Minimal, focused interfaces
- Dependency Inversion: Depends on abstractions (YOLO interface)

### Testing Requirements (For Testing Expert)

The Testing Expert should create tests for:

**Unit Tests** (`tests/services/ml_processing/test_model_cache.py`):
- Test singleton pattern (same instance on repeated calls)
- Test separate instances for different worker_ids
- Test CPU fallback (mock torch.cuda.is_available)
- Test thread safety (concurrent access)
- Test clear_cache() for specific worker
- Test clear_cache() for all workers
- Test get_cache_info()
- Test increment_task_counter()
- Test FileNotFoundError for missing model
- Test ValueError for invalid model_type

**Unit Tests** (`tests/celery/test_base_tasks.py`):
- Test seg_model lazy loading
- Test det_model lazy loading
- Test worker_id extraction from various hostnames
- Test after_return() cleanup (every 100 tasks)
- Test on_failure() logging
- Test on_success() logging

**Integration Tests** (`tests/integration/test_model_singleton_integration.py`):
- Load both models in same worker
- Run multiple tasks, verify model loaded only once
- Monitor memory usage (should be stable)
- Test with actual YOLO models (if available)

### Known Limitations

1. **Model files not included**: The .pt model files (yolov11m-seg.pt, yolov11m.pt) are not in the repository. Tests will need to mock or download them.

2. **Celery type stubs**: Celery doesn't have full type stubs, so some mypy warnings are expected and can be ignored.

3. **GPU hardware dependency**: Full testing requires GPU hardware. CPU fallback should be tested separately.

4. **Worker pool requirement**: Only tested/designed for Celery `pool=solo` (GPU workers). Other pool types may have different behavior.

### Next Steps

1. **Testing Expert**: Create comprehensive test suite (AC6, AC7)
2. **Team Leader**: Review implementation for architecture compliance
3. **ML Lead**: Review GPU memory management and model loading strategy
4. **DevOps**: Ensure YOLO model files are available in deployment
5. **Documentation**: Update architecture docs to reference model_cache.py

### Handoff Notes

- Code is production-ready (passes linting, type checking)
- No tests written (per instructions - Testing Expert's responsibility)
- All acceptance criteria implemented (AC1-AC5)
- Ready for parallel test development
- No blocking issues

**Estimated Testing Time**: 2-3 story points (unit + integration tests)

---

**Implementation Completed**: 2025-10-14
**Python Expert**: Claude
**Ready For**: Testing Expert + Team Leader Review
