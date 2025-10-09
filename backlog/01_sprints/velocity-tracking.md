# Velocity Tracking - DemeterAI v2.0

**Purpose**: Track team velocity across sprints to improve estimation and planning.

---

## Sprint Velocity Summary

| Sprint | Planned | Completed | Velocity | Trend |
|--------|---------|-----------|----------|-------|
| **Sprint 00** | 65 | TBD | TBD | Baseline |
| **Sprint 01** | 75 | TBD | TBD | - |
| **Sprint 02** | 78 | TBD | TBD | - |
| **Sprint 03** | 76 | TBD | TBD | - |
| **Sprint 04** | 78 | TBD | TBD | - |
| **Sprint 05** | 70 | TBD | TBD | - |
| **Average** | **74** | **TBD** | **TBD** | - |

**Target Velocity**: 80 points/sprint (10 devs × 8 points)

---

## Velocity Chart

```
Points
90 ┤
80 ┤        TARGET ─────────────────────────────────
70 ┤
60 ┤  [Planned] ▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮
50 ┤
40 ┤  [Actual]  (Update after each sprint)
30 ┤
20 ┤
10 ┤
 0 └──────────────────────────────────────────────
    S0  S1  S2  S3  S4  S5

  Legend:
  ▮ = Planned points
  █ = Completed points (update each sprint)
  ─ = Target velocity (80)
```

---

## Detailed Sprint Data

### Sprint 00: Foundation & Setup

**Dates**: Week 1-2
**Team Size**: 10 developers

| Metric | Value |
|--------|-------|
| Planned Story Points | 65 |
| Completed Story Points | TBD |
| Cards Planned | 12 |
| Cards Completed | TBD |
| Velocity | TBD |
| Completion % | TBD |

**Notes**: First sprint, establishing baseline velocity.

---

### Sprint 01: Database Models & Repositories

**Dates**: Week 3-4
**Team Size**: 10 developers

| Metric | Value |
|--------|-------|
| Planned Story Points | 75 |
| Completed Story Points | TBD |
| Cards Planned | 63 |
| Cards Completed | TBD |
| Velocity | TBD |
| Completion % | TBD |

**Notes**: High card count (63 cards), but many are small model classes.

---

### Sprint 02: ML Pipeline (CRITICAL PATH)

**Dates**: Week 5-6
**Team Size**: 10 developers

| Metric | Value |
|--------|-------|
| Planned Story Points | 78 |
| Completed Story Points | TBD |
| Cards Planned | 18 |
| Cards Completed | TBD |
| Velocity | TBD |
| Completion % | TBD |

**Notes**: ⚡ CRITICAL PATH. Project success depends on Sprint 02.

**Risks**:
- GPU setup may delay work
- SAHI integration complexity
- Celery chord pattern debugging

---

### Sprint 03: Services Layer

**Dates**: Week 7-8
**Team Size**: 10 developers

| Metric | Value |
|--------|-------|
| Planned Story Points | 76 |
| Completed Story Points | TBD |
| Cards Planned | 42 |
| Cards Completed | TBD |
| Velocity | TBD |
| Completion % | TBD |

**Notes**: Large number of services (42), but follow established patterns.

---

### Sprint 04: API Controllers + Celery

**Dates**: Week 9-10
**Team Size**: 10 developers

| Metric | Value |
|--------|-------|
| Planned Story Points | 78 |
| Completed Story Points | TBD |
| Cards Planned | 34 |
| Cards Completed | TBD |
| Velocity | TBD |
| Completion % | TBD |

**Notes**: Integration complexity (FastAPI + Celery).

---

### Sprint 05: Deployment + Observability

**Dates**: Week 11-12
**Team Size**: 10 developers

| Metric | Value |
|--------|-------|
| Planned Story Points | 70 |
| Completed Story Points | TBD |
| Cards Planned | 32 |
| Cards Completed | TBD |
| Velocity | TBD |
| Completion % | TBD |

**Notes**: Buffer sprint (70 vs 80 capacity) for stabilization and polish.

---

## Velocity Analysis

### Factors Affecting Velocity

**Positive Factors**:
- ✅ Established patterns (Repository, Service, Controller templates)
- ✅ Clear architecture principles (Clean Architecture)
- ✅ Good test coverage enforced (≥80%)
- ✅ Pair programming encouraged

**Negative Factors**:
- ❌ First project together (team forming)
- ❌ Complex ML pipeline (YOLO + SAHI new to team)
- ❌ Async programming learning curve
- ❌ Docker/containerization setup time

### Expected Velocity Trend

```
Sprint 00: 55-65 points (85-100% of planned)
  Reason: First sprint, setup overhead

Sprint 01: 65-75 points (87-100% of planned)
  Reason: Team velocity increasing, patterns established

Sprint 02: 70-78 points (90-100% of planned)
  Reason: ML complexity, but critical focus

Sprint 03: 70-76 points (92-100% of planned)
  Reason: Velocity stable, services follow patterns

Sprint 04: 72-78 points (92-100% of planned)
  Reason: Integration complexity balanced by experience

Sprint 05: 68-70 points (97-100% of planned)
  Reason: Polish sprint, most work is refinement
```

---

## How to Update This File

**After Each Sprint (During Retrospective)**:

1. **Update Sprint Table**:
   - Fill in "Completed" story points
   - Calculate velocity (completed points)
   - Add trend arrow (↑ ↓ →)

2. **Update Velocity Chart**:
   - Add █ blocks for completed work

3. **Update Detailed Sprint Data**:
   - Fill in actual completion metrics
   - Add retrospective notes

4. **Analyze Trends**:
   - Compare planned vs actual
   - Identify patterns (overestimation? underestimation?)
   - Adjust future sprint planning

5. **Commit Changes**:
   ```bash
   git add 01_sprints/velocity-tracking.md
   git commit -m "docs: update velocity tracking after Sprint X"
   ```

---

## Velocity Formulas

### Sprint Velocity
```
Velocity = SUM(story points for completed cards)
```

### Average Velocity
```
Avg Velocity = SUM(all sprint velocities) / number of sprints
```

### Completion Percentage
```
Completion % = (Completed Points / Planned Points) × 100
```

### Predictability
```
Predictability = 1 - |Planned - Completed| / Planned
```
Higher predictability (closer to 1.0) = better estimation.

---

## Sprint Capacity Adjustments

**If Average Velocity < 70**:
- Reduce future sprint commitments to 60-65 points
- Review estimation process (cards too large?)
- Check for systemic blockers

**If Average Velocity > 80**:
- Increase future sprint commitments to 85-90 points
- Review estimation (cards too small?)
- Ensure sustainable pace (not burning out)

**If Velocity Unstable (±15 points between sprints)**:
- Improve estimation (planning poker, reference cards)
- Reduce card size variance (split large cards earlier)
- Check for mid-sprint scope changes

---

**Document Owner**: Scrum Master
**Update Frequency**: End of each sprint (during retrospective)
**Last Updated**: 2025-10-09
