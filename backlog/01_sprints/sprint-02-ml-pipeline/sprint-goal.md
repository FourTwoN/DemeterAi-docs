# Sprint 02: ML Pipeline (V3 - CRITICAL PATH)
## Sprint Goal

**Duration**: Week 5-6 (Days 21-30)
**Team Capacity**: 80 story points
**Committed**: 78 story points
**⚠️ CRITICAL**: This is the project's critical path - Sprint 02 success = project success

---

## Goal Statement

> **"Implement complete CPU-first ML pipeline (YOLO v11 + SAHI + band-based estimation) enabling automated plant detection and counting from photos."**

---

## Success Criteria

- [ ] Model Singleton pattern implemented (GPU/CPU support)
- [ ] YOLO v11 segmentation identifies containers (plugs, boxes, segments)
- [ ] SAHI tiled detection works for large segments (640x640 tiles, 20% overlap)
- [ ] Direct detection works for small containers (boxes, plugs)
- [ ] Band-based estimation calculates undetected plants with auto-calibration
- [ ] Pipeline Coordinator orchestrates full workflow (Celery chord pattern)
- [ ] Processing time ≤5-10 minutes per photo on CPU
- [ ] Detections stored in partitioned table
- [ ] Integration tests pass with real test photos

---

## Sprint Scope

### In Scope (18 cards, 78 points)

**Core ML Services (ML001-ML009)**: 50 points
- ML001: Model Singleton pattern (8pts) **CRITICAL**
- ML002: YOLO v11 segmentation service (8pts)
- ML003: SAHI tiled detection (8pts) **CRITICAL**
- ML004: Direct detection service (5pts)
- ML005: Band-based estimation with auto-calibration (8pts) **CRITICAL**
- ML006: Image processing utilities (3pts)
- ML007: Mask generation & smoothing (5pts)
- ML008: GPS extraction & PostGIS localization (3pts)
- ML009: Pipeline Coordinator (Celery chord) (8pts) **CRITICAL**

**Supporting Services (ML010-ML018)**: 28 points
- Feathering, cropping, coordinate mapping, visualization generation, metrics calculation, density parameter updates

### Out of Scope
- ❌ Celery worker setup (Sprint 04)
- ❌ API endpoints (Sprint 04)
- ❌ Manual initialization (Sprint 03)

---

## Key Deliverables

1. `app/services/ml_processing/model_cache.py` - Singleton pattern
2. `app/services/ml_processing/segmentation_service.py` - YOLO segmentation
3. `app/services/ml_processing/detection_service.py` - SAHI + Direct detection
4. `app/services/ml_processing/estimation_service.py` - Band-based estimation
5. `app/services/ml_processing/pipeline_coordinator.py` - Full workflow
6. Integration tests with test photos (5-10 sample images)

---

## Sprint Risks (HIGH)

| Risk | Impact | Mitigation |
|------|--------|------------|
| **GPU setup delays** | Critical path blocker | Use CPU fallback, GPU optional |
| **YOLO model download fails** | Blocks development | Pre-download models, cache locally |
| **SAHI performance issues** | Slow processing | Profile early, optimize tiling params |
| **Celery chord complexity** | Integration issues | Unit test each service independently first |

---

## Dependencies

**Blocked By**: Sprint 01 (DB models for detections, estimations, sessions)
**Blocks**: Sprint 04 (Celery integration needs working pipeline)

---

**Sprint Owner**: ML Lead
**Priority**: ⚡ HIGHEST - Project critical path
**Last Updated**: 2025-10-09
