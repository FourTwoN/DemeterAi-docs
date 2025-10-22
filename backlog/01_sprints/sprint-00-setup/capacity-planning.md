# Sprint 00: Capacity Planning

**Sprint Duration**: 2 weeks (10 working days)
**Team Size**: 10 developers
**Total Capacity**: 80 story points

---

## Team Availability

| Developer | Days Available | Story Points  | Notes             |
|-----------|----------------|---------------|-------------------|
| Dev 1     | 10             | 8             | Full availability |
| Dev 2     | 10             | 8             | Full availability |
| Dev 3     | 10             | 8             | Full availability |
| Dev 4     | 10             | 8             | Full availability |
| Dev 5     | 10             | 8             | Full availability |
| Dev 6     | 10             | 8             | Full availability |
| Dev 7     | 10             | 8             | Full availability |
| Dev 8     | 10             | 8             | Full availability |
| Dev 9     | 10             | 8             | Full availability |
| Dev 10    | 10             | 8             | Full availability |
| **TOTAL** | **100 days**   | **80 points** |                   |

---

## Capacity Calculation

### Formula

```
Capacity = Team Size × Points per Dev per Sprint × Availability Factor
         = 10 devs × 8 points × 100% availability
         = 80 story points
```

### Assumptions

- **8 story points per dev**: Industry standard for 2-week sprints
- **100% availability**: First sprint, no holidays, no planned PTO
- **No meetings buffer**: Assumes ceremonies fit within working hours

---

## Sprint Commitment

### Planned Work: 65 story points (81% of capacity)

**Why 81% and not 100%?**

1. **First sprint buffer** (15% reserve for unknowns)
2. **Onboarding time** (new team members may need 1-2 days)
3. **Documentation time** (not all work is card-based)
4. **Meetings & ceremonies** (~4 hours/week)

### Buffer Allocation (15 points)

- **Onboarding**: 5 points (pair programming, setup help)
- **Documentation**: 5 points (README, CONTRIBUTING.md, troubleshooting)
- **Unexpected issues**: 5 points (dependency conflicts, OS-specific problems)

---

## Work Distribution by Track

| Track                  | Story Points | Developers | Duration          |
|------------------------|--------------|------------|-------------------|
| **Infrastructure**     | 25           | 3          | Week 1-2          |
| **Quality Tooling**    | 10           | 2          | Week 1            |
| **Containerization**   | 13           | 2          | Week 2            |
| **Project Foundation** | 8            | 3          | Week 1 (Days 1-2) |
| **Buffer**             | 15           | Flexible   | As needed         |
| **TOTAL**              | **65**       | **10**     | 2 weeks           |

---

## Daily Commitment

### Week 1 (5 days, 40 points capacity)

- **Committed**: 35 points
- **Buffer**: 5 points
- **Daily target**: 7 points/day

### Week 2 (5 days, 40 points capacity)

- **Committed**: 18 points
- **Buffer**: 10 points (documentation, testing, review)
- **Daily target**: 4 points/day (lighter, allows polish)

---

## Velocity Tracking

### Sprint 00 Baseline

- **Planned**: 65 points
- **Completed**: TBD (will update at sprint end)
- **Velocity**: TBD points/sprint

### Historical Velocity (N/A - first sprint)

- Sprint 00: 65 points (planned)
- Sprint 01: Estimate 70-75 points (based on Sprint 00 actuals)
- Sprint 02: Estimate 75-80 points (team velocity stabilizes)

---

## Capacity Adjustments

### If Velocity Lower Than Expected (<55 points completed)

**Reasons**:

- Onboarding took longer
- Technical blockers (Docker, dependencies)
- Cards were underestimated

**Actions**:

- Sprint 01: Reduce commitment to 60 points
- Improve estimation in retrospective
- Add more buffer for unknowns

### If Velocity Higher Than Expected (>70 points completed)

**Reasons**:

- Cards were overestimated
- Team is more experienced than expected
- Good pair programming efficiency

**Actions**:

- Sprint 01: Increase commitment to 75-80 points
- Adjust estimation baseline
- Maintain sustainable pace (don't burn out)

---

## Holiday & PTO Planning

### Sprint 00: No holidays

- No team members on PTO
- No company holidays in these 2 weeks

### Future Sprints

- Track PTO in capacity planning
- Reduce commitment proportionally
- Formula: `Adjusted Points = Base Points × (Available Days / Total Days)`

---

## Meeting Time Budget

### Sprint Ceremonies (8 hours total)

- **Sprint Planning**: 2 hours (Day 1)
- **Daily Standups**: 15 min × 10 days = 2.5 hours
- **Sprint Review**: 1 hour (Day 10)
- **Sprint Retrospective**: 1 hour (Day 10)
- **Backlog Refinement**: 1.5 hours (mid-sprint)

### Overhead (20% of sprint)

- Meetings: 8 hours
- Context switching: 4 hours
- Code reviews: 8 hours
- **Total overhead**: 20 hours (25% of 80-hour sprint)

**Impact on velocity**: Already accounted for in 8 points/dev baseline

---

## Capacity Risks

| Risk                   | Impact     | Mitigation                                     |
|------------------------|------------|------------------------------------------------|
| **New team members**   | -10 points | Pair programming, mentoring                    |
| **Technical blockers** | -5 points  | Early Docker testing, troubleshooting guide    |
| **Scope creep**        | -5 points  | Strict sprint backlog, no mid-sprint additions |

---

**Last Updated**: 2025-10-09
**Reviewed By**: Scrum Master + Tech Lead
**Next Review**: Sprint Retrospective (Day 10)
