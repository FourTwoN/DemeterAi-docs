# Critical Path: V3 ML Pipeline Dependency Chain

**Purpose**: Visualize the critical path (V3 ML Pipeline) that determines project success timeline.

**Critical Path Definition**: Longest sequence of dependent cards that cannot be parallelized. Any delay in critical path delays entire project.

---

## Critical Path Visualization

```
SPRINT 00 (Foundation) - MUST COMPLETE FIRST
F001 → F002 → F006 → F007
(Project Setup → Dependencies → DB Connection → Alembic)

        ↓

SPRINT 01 (Database) - BLOCKS ML PIPELINE
DB010 → DB011 → DB012
(Detections Model → Estimations Model → Sessions Model)

        ↓

SPRINT 02 (ML Pipeline) - ⚡ CRITICAL PATH ⚡
┌─────────────────────────────────────────────────┐
│ ML001 (Model Singleton) - 8 points              │
│   ↓                                              │
│ ML002 (YOLO Segmentation) - 8 points            │
│   ↓                                              │
│ ML003 (SAHI Detection) - 8 points               │
│   ↓                                              │
│ ML005 (Band Estimation) - 8 points              │
│   ↓                                              │
│ ML009 (Pipeline Coordinator) - 8 points         │
│                                                  │
│ TOTAL: 40 points (critical path in Sprint 02)   │
└─────────────────────────────────────────────────┘

        ↓

SPRINT 04 (Celery Integration) - DEPENDS ON ML PIPELINE
CEL005 → CEL006 → CEL007
(ML Parent Task → ML Child Tasks → Callback)

        ↓

PROJECT COMPLETE
```

---

## Critical Path Cards Detail

| Card ID | Title | Points | Duration | Blockers | Blocks |
|---------|-------|--------|----------|----------|--------|
| **F001** | Project setup | 5 | 1 day | None | F002-F012 |
| **F006** | DB connection | 5 | 1 day | F001, F002 | F007, DB* |
| **F007** | Alembic setup | 5 | 1 day | F006 | DB* |
| **DB010** | Detections model | 3 | 0.5 day | F007 | ML* |
| **ML001** | Model Singleton | 8 | 2 days | DB010 | ML002-009 |
| **ML002** | YOLO Segmentation | 8 | 2 days | ML001 | ML003 |
| **ML003** | SAHI Detection | 8 | 2 days | ML002 | ML009 |
| **ML005** | Band Estimation | 8 | 2 days | ML003 | ML009 |
| **ML009** | Pipeline Coordinator | 8 | 2 days | ML002-008 | CEL* |
| **CEL005** | ML Parent Task | 5 | 1 day | ML009 | DONE |

**Total Critical Path Duration**: ~16 days (assuming no delays)
**Buffer**: 4 days (20 working days in Sprints 00-02)

---

## Parallel Work (Not Critical Path)

While critical path executes, these can run in parallel:

### Sprint 00 (Parallel)
- F003: Git setup
- F004: Logging
- F005: Exceptions
- F008-F010: Quality tooling

### Sprint 01 (Parallel)
- DB001-DB009: Other models
- R001-R028: All repositories

### Sprint 02 (Parallel)
- ML004, ML006-ML008, ML010-ML018: Supporting ML services

---

## Risk Analysis

### High Risk Cards (On Critical Path)

**ML001 (Model Singleton)** - 8 points
- **Risk**: GPU setup issues, model download fails
- **Mitigation**: CPU fallback, pre-download models
- **Impact if delayed**: Blocks ALL ML work (40 points)

**ML003 (SAHI Detection)** - 8 points
- **Risk**: SAHI library complexity, tiling bugs
- **Mitigation**: Start simple, add complexity incrementally
- **Impact if delayed**: Blocks estimation (ML005) and coordinator (ML009)

**ML009 (Pipeline Coordinator)** - 8 points
- **Risk**: Celery chord pattern debugging
- **Mitigation**: Unit test each service independently first
- **Impact if delayed**: Blocks Celery integration (Sprint 04)

---

## Critical Path Monitoring

**Daily Standup Checks**:
- [ ] Is any critical path card blocked? (Escalate immediately)
- [ ] Is any critical path card in-progress >2 days? (Pair program)
- [ ] Are critical path cards being prioritized? (WIP limits)

**Sprint Review Metrics**:
- Critical path cards completed: __/10
- Critical path velocity: __ points
- Days ahead/behind schedule: __

---

## What Happens If Critical Path Delays?

**1 day delay in Sprint 02** → 1 day project delay (no buffer left)
**2 day delay in Sprint 02** → 2 day project delay
**1 week delay in Sprint 02** → Project deadline missed (12 weeks → 13 weeks)

**Recovery Options**:
1. **Reduce scope**: Cut non-critical features (analytics, auth)
2. **Increase capacity**: Add developers to critical path cards
3. **Extend timeline**: Negotiate with stakeholders

---

**Document Owner**: Project Manager + Scrum Master
**Update Frequency**: Daily (during Sprint 02)
**Last Updated**: 2025-10-09
