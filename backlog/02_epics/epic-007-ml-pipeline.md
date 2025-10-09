# Epic 007: ML Pipeline (V3 - CRITICAL PATH)

**Status**: Not Started
**Sprint**: Sprint-02 (Week 5-6)
**Priority**: ⚡ CRITICAL PATH (project success depends on this epic)
**Total Story Points**: 78
**Total Cards**: 18 (ML001-ML018)

---

## Goal

Build complete CPU-first ML pipeline (YOLO v11 + SAHI + band-based estimation) enabling automated plant detection and counting from photos with 95%+ accuracy.

---

## Success Criteria

- [ ] Processing time ≤5-10 minutes per photo on CPU
- [ ] Detection accuracy ≥95% (validated against manual counts)
- [ ] SAHI works for large segments (>3000px)
- [ ] Band-based estimation auto-calibrates from real detections
- [ ] Celery chord pattern coordinates parent → children → callback
- [ ] All 18 cards completed and integrated
- [ ] Integration tests pass with real test photos

---

## Cards List

### Core Services (50 points)
- **ML001**: Model Singleton pattern (8pts) ⚡
- **ML002**: YOLO v11 segmentation service (8pts)
- **ML003**: SAHI tiled detection (8pts) ⚡
- **ML004**: Direct detection service (5pts)
- **ML005**: Band-based estimation + auto-calibration (8pts) ⚡
- **ML006**: Image processing utilities (3pts)
- **ML007**: Mask generation & smoothing (5pts)
- **ML008**: GPS extraction & PostGIS localization (3pts)
- **ML009**: Pipeline Coordinator (Celery chord) (8pts) ⚡

### Supporting Services (28 points)
- **ML010**: Feathering technique (3pts)
- **ML011**: Region cropping (3pts)
- **ML012**: Coordinate mapping (3pts)
- **ML013**: Detection grouping (3pts)
- **ML014**: Visualization generation (5pts)
- **ML015**: Metrics calculation (3pts)
- **ML016**: Overlay creation (5 types) (5pts)
- **ML017**: Density parameter updates (3pts)
- **ML018**: Floor/soil suppression (HSV filtering) (3pts)

---

## Dependencies

**Blocked By**:
- Sprint 01: DB models (detections, estimations, sessions)
- Sprint 01: Repositories (for DB access)

**Blocks**:
- Sprint 04: Celery integration (needs working pipeline)
- Sprint 04: API endpoints (POST /api/stock/photo)

---

## Risks & Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| GPU setup delays | Medium | High | Use CPU fallback (GPU optional) |
| SAHI complexity | Medium | High | Start with direct detection, add SAHI incrementally |
| Celery chord bugs | Low | High | Unit test each service independently first |
| Model download fails | Low | Medium | Pre-download models, cache in Docker image |

---

## Technical Approach

**Architecture**: Services in `app/services/ml_processing/`

**Key Patterns**:
1. Model Singleton (prevents 2-3s load overhead per task)
2. Celery Chord (parent → parallel children → callback)
3. Band-based auto-calibration (learns from detections)

**Integration Points**:
- Database: detections, estimations, photo_processing_sessions
- S3: Upload processed images with visualizations
- Redis: Celery task coordination

---

**Epic Owner**: ML Lead
**Created**: 2025-10-09
**Last Updated**: 2025-10-09
