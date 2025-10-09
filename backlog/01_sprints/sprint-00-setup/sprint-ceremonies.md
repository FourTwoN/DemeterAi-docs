# Sprint 00: Sprint Ceremonies Schedule

**Sprint Duration**: Week 1-2 (10 working days)
**Team Size**: 10 developers

---

## Sprint Calendar

```
WEEK 1
┌─────────────────────────────────────────────────────────────┐
│ MON (Day 1)  │ TUE (Day 2) │ WED (Day 3) │ THU (Day 4) │ FRI (Day 5) │
│ 9:00 Sprint  │ 9:00 Daily  │ 9:00 Daily  │ 9:00 Daily  │ 9:00 Daily  │
│ Planning     │ Standup     │ Standup     │ Standup     │ Standup     │
│ (2 hrs)      │ (15 min)    │ (15 min)    │ (15 min)    │ (15 min)    │
│              │             │ 2:00 Backlog│             │             │
│              │             │ Refinement  │             │             │
│              │             │ (1.5 hrs)   │             │             │
└─────────────────────────────────────────────────────────────┘

WEEK 2
┌─────────────────────────────────────────────────────────────┐
│ MON (Day 6)  │ TUE (Day 7) │ WED (Day 8) │ THU (Day 9) │ FRI (Day 10) │
│ 9:00 Daily   │ 9:00 Daily  │ 9:00 Daily  │ 9:00 Daily  │ 9:00 Daily  │
│ Standup      │ Standup     │ Standup     │ Standup     │ Standup     │
│ (15 min)     │ (15 min)    │ (15 min)    │ (15 min)    │ (15 min)    │
│              │             │             │             │ 2:00 Sprint │
│              │             │             │             │ Review      │
│              │             │             │             │ (1 hr)      │
│              │             │             │             │ 3:15 Sprint │
│              │             │             │             │ Retro       │
│              │             │             │             │ (1 hr)      │
└─────────────────────────────────────────────────────────────┘
```

---

## 1. Sprint Planning

**When**: Monday, Week 1, Day 1
**Time**: 9:00 AM - 11:00 AM (2 hours)
**Location**: Conference Room / Zoom
**Attendees**: Full team (10 devs + Product Owner + Scrum Master)

### Agenda

**Part 1: Sprint Goal & Capacity (30 min)**
- Review sprint goal: "Establish production-ready dev environment"
- Review team capacity: 80 points available
- Review Definition of Ready for all candidate cards

**Part 2: Card Selection (60 min)**
- Present cards from Ready column (F001-F012)
- Team discusses each card (5 min per card)
- Estimate story points (planning poker if needed)
- Select cards until reaching 65-75 points
- Identify dependencies and risks

**Part 3: Task Breakdown & Assignment (30 min)**
- Break down cards into sub-tasks (if needed)
- Assign cards to developers
- Identify parallel work tracks
- Confirm sprint commitment

### Outputs
- Sprint backlog (65 points committed)
- Card assignments
- Work tracks identified
- Sprint risks documented

---

## 2. Daily Standup

**When**: Every day, 9:00 AM - 9:15 AM (15 minutes)
**Location**: Team area / Zoom
**Attendees**: Full team (optional: Product Owner)

### Format

Each developer answers 3 questions (1 min each):
1. **What did I complete yesterday?**
   - "Completed F001 - project setup"
2. **What will I work on today?**
   - "Starting F004 - logging configuration"
3. **Any blockers?**
   - "Waiting for Docker image approval"

### Facilitator Checklist
- [ ] Check WIP limits (In Progress ≤5, Code Review ≤3, Testing ≤2)
- [ ] Identify blockers and escalate if >1 day old
- [ ] Update burndown chart with remaining points
- [ ] Announce if any ceremony today (e.g., refinement, review)

### Anti-Patterns to Avoid
- ❌ Status reports to manager (this is peer-to-peer sync)
- ❌ Problem-solving discussions (take offline)
- ❌ Going over 15 minutes (timebox strictly)

---

## 3. Backlog Refinement

**When**: Wednesday, Week 1, Day 3
**Time**: 2:00 PM - 3:30 PM (1.5 hours)
**Location**: Conference Room / Zoom
**Attendees**: 5-6 developers + Product Owner + Tech Lead

### Purpose
Prepare cards for Sprint 01 (Database Models & Repositories)

### Agenda

**Review Sprint 01 Candidates (90 min)**
- DB001-DB028: Database models (28 cards)
- R001-R028: Repositories (28 cards)
- DB029-DB035: Alembic migrations (7 cards)

**For Each Card**:
1. Review Description & Acceptance Criteria (5 min)
2. Clarify technical approach (3 min)
3. Identify dependencies (2 min)
4. Estimate story points (planning poker, 5 min)
5. Mark as Ready (move to 01_ready/ column)

**Target**: 15-20 cards refined (enough for Sprint 01 selection)

### Outputs
- 60-80 points worth of cards moved to Ready
- All cards meet Definition of Ready
- Dependencies documented

---

## 4. Sprint Review

**When**: Friday, Week 2, Day 10
**Time**: 2:00 PM - 3:00 PM (1 hour)
**Location**: Conference Room / Zoom
**Attendees**: Full team + Product Owner + Stakeholders

### Agenda

**Introduction (5 min)**
- Review sprint goal
- Summarize completed vs planned work

**Demo (40 min)**
- **Demo 1**: Project setup and local environment (10 min)
  - Show `docker-compose up` bringing up all services
  - Show database migrations running successfully
  - Show pytest running
  - Show pre-commit hooks in action

- **Demo 2**: Code quality tooling (10 min)
  - Show Ruff linting and formatting
  - Show mypy type checking
  - Show test coverage report

- **Demo 3**: Containerization (10 min)
  - Show Docker multi-stage build
  - Show docker-compose with all services
  - Show logs and health checks

- **Demo 4**: Documentation (10 min)
  - Walk through README.md
  - Show CONTRIBUTING.md
  - Show troubleshooting guide

**Feedback & Questions (10 min)**
- Stakeholder questions
- Product Owner acceptance

**Metrics Review (5 min)**
- Velocity: Planned vs Actual
- Burndown chart
- Quality metrics (test coverage, linting pass rate)

### Outputs
- Stakeholder feedback
- Sprint acceptance (yes/no)
- Velocity baseline for Sprint 01

---

## 5. Sprint Retrospective

**When**: Friday, Week 2, Day 10
**Time**: 3:15 PM - 4:15 PM (1 hour)
**Location**: Conference Room / Zoom (team only, no stakeholders)
**Attendees**: Full team + Scrum Master

### Agenda

**Set the Stage (5 min)**
- Reminder: Blameless, focus on process improvement
- Review retrospective goals

**Gather Data (15 min)**
- What went well? (each person shares 1 thing)
- What didn't go well? (each person shares 1 thing)
- Surprises or learnings?

**Generate Insights (20 min)**
- Group similar items
- Identify root causes
- Prioritize top 3 issues to address

**Decide Actions (15 min)**
- For each top issue, define concrete action:
  - What will we do differently?
  - Who owns this action?
  - How will we measure success?

**Close (5 min)**
- Recap action items
- Assign owners
- Schedule follow-up (check actions in Sprint 01 retro)

### Example Topics

**What Went Well?**
- Docker setup was smooth
- Pair programming helped onboarding
- Clear documentation helped

**What Didn't Go Well?**
- Windows users had Docker issues
- Some cards took longer than estimated
- Code review bottleneck on Day 8

**Actions (Example)**:
1. **Action**: Create WSL2 setup guide for Windows users
   - **Owner**: Dev 3
   - **By When**: Before Sprint 01
2. **Action**: Adjust estimation baseline (reduce by 10%)
   - **Owner**: Tech Lead
   - **By When**: Sprint 01 planning
3. **Action**: Assign dedicated reviewers daily
   - **Owner**: Scrum Master
   - **By When**: Sprint 01 Day 1

### Outputs
- 3-5 concrete action items with owners
- Documented in `retrospective.md`
- Reviewed in next sprint planning

---

## Ceremony Best Practices

### For All Ceremonies
- ✅ Start on time, end on time (respect timebox)
- ✅ Come prepared (read agenda, review materials)
- ✅ Participate actively (no multitasking)
- ✅ Focus on outcomes (not just attendance)

### For Facilitators
- ✅ Send calendar invites with agenda
- ✅ Prepare materials beforehand (cards, metrics, demos)
- ✅ Keep discussions on track (parking lot for off-topic)
- ✅ Document decisions and actions

### For Team Members
- ✅ Update cards before standup (move cards, update status)
- ✅ Bring blockers to standup (don't wait)
- ✅ Prepare demos for review (practice beforehand)
- ✅ Be constructive in retrospective (blameless culture)

---

**Last Updated**: 2025-10-09
**Facilitator**: Scrum Master
**Next Review**: Sprint Retrospective (adjust ceremony schedule if needed)
