# DemeterAI v2.0 - Backend Development Backlog

**Version:** 1.0
**Last Updated:** 2025-10-09
**Team Size:** 10 developers
**Project Duration:** 12 weeks (6 sprints × 2 weeks)
**Total Cards:** ~245 cards

---

## 📋 Quick Start

### For New Team Members (5 minutes)

1. **Read this README** (you are here)
2. **Setup local environment**: See `05_dev-environment/local-setup-guide.md`
3. **Understand the workflow**: See [Team Workflow](#team-workflow) below
4. **Pick your first card**: See `03_kanban/01_ready/` for sprint-ready cards
5. **Ask questions**: Check `GLOSSARY.md` for terminology

### For Sprint Planning

1. Review sprint goal in `01_sprints/sprint-XX-name/sprint-goal.md`
2. Check team capacity in `capacity-planning.md`
3. Select cards from `03_kanban/01_ready/` into sprint backlog
4. Assign cards to developers
5. Move selected cards to `03_kanban/02_in-progress/` or keep in ready pool

---

## 🎯 Project Overview

### What is DemeterAI?

**DemeterAI** is an ML-powered automated plant counting and inventory management system for **600,000+ cacti and succulents** across multiple cultivation zones.

**Core Technologies:**
- **PostgreSQL 18** + PostGIS 3.3+ (28 tables, 4-level geospatial hierarchy)
- **Python 3.12** + FastAPI 0.118.2 + SQLAlchemy 2.0.43
- **Celery 5.4.0** + Redis 7+ (async ML processing)
- **YOLO v11** + SAHI (CPU-first ML pipeline)
- **Docker** + docker-compose (containerization)

**Key Features:**
- **Two initialization methods**: Photo-based (ML) + Manual (direct entry)
- **Monthly reconciliation**: Automated sales calculation from photos
- **Clean Architecture**: Controllers → Services → Repositories → Database
- **Event sourcing**: Full audit trail of all plant movements

---

## 📁 Directory Structure

```
backlog/
├── README.md                          ← YOU ARE HERE
├── QUICK_START.md                     ← 5-minute onboarding
├── GLOSSARY.md                        ← Project terminology
│
├── 00_foundation/                     ← Core reference docs
│   ├── tech-stack.md                  ← Single source of truth (versions)
│   ├── architecture-principles.md     ← Clean Architecture rules
│   ├── conventions.md                 ← Naming, formatting standards
│   ├── definition-of-ready.md         ← DoR checklist
│   ├── definition-of-done.md          ← DoD checklist
│   ├── wip-limits.md                  ← Per-column WIP limits
│   └── team-capacity.md               ← 10 devs × story points
│
├── 01_sprints/                        ← Sprint planning & tracking
│   ├── sprint-00-setup/               ← Foundation (week 1-2)
│   ├── sprint-01-database/            ← Models + repos (week 3-4)
│   ├── sprint-02-ml-pipeline/         ← **CRITICAL PATH** (week 5-6)
│   ├── sprint-03-services/            ← Business logic (week 7-8)
│   ├── sprint-04-controllers-celery/  ← API + async (week 9-10)
│   ├── sprint-05-deployment/          ← Docker + observability (week 11-12)
│   └── velocity-tracking.md           ← Historical velocity
│
├── 02_epics/                          ← High-level feature groupings
│   ├── epic-001-foundation.md         ← 12 cards
│   ├── epic-002-database-models.md    ← 35 cards
│   ├── epic-003-repositories.md       ← 28 cards
│   ├── epic-007-ml-pipeline.md        ← 18 cards (V3 CRITICAL)
│   └── ... (17 epics total)
│
├── 03_kanban/                         ← Physical card movement
│   ├── 00_backlog/                    ← All unsized/blocked cards
│   ├── 01_ready/                      ← Meets DoR, ready for sprint
│   ├── 02_in-progress/                ← WIP limit: 5
│   ├── 03_code-review/                ← WIP limit: 3
│   ├── 04_testing/                    ← WIP limit: 2
│   ├── 05_done/                       ← Completed cards
│   └── 06_blocked/                    ← Waiting on dependencies
│
├── 04_templates/                      ← Starter code & patterns
│   ├── starter-code/                  ← Repository, service, controller templates
│   ├── test-templates/                ← Unit, integration test templates
│   ├── config-templates/              ← .env, docker-compose, Ruff
│   └── pr-template.md                 ← Pull request structure
│
├── 05_dev-environment/                ← Local setup guides
│   ├── local-setup-guide.md           ← 5-minute Docker setup
│   ├── database-setup.md              ← PostgreSQL 18 + PostGIS
│   ├── gpu-setup.md                   ← CUDA + YOLO models
│   └── troubleshooting.md             ← Common issues
│
├── 06_database/                       ← Database utilities
│   ├── seed-scripts/                  ← SQL seed data (6 scripts)
│   ├── migration-guide.md             ← Alembic best practices
│   └── partitioning-setup.sql         ← Daily partitions setup
│
├── 07_documentation/                  ← Documentation guides
│   ├── api-documentation-guide.md
│   ├── code-documentation-guide.md
│   └── onboarding-checklist.md
│
├── 08_views/                          ← Special perspectives
│   ├── critical-path-v3.md            ← ML pipeline dependencies
│   ├── blocked-items-tracker.md       ← Real-time blocker dashboard
│   ├── dependencies-global.md         ← Master dependency graph
│   └── risk-register.md               ← Technical risks
│
└── 09_decisions/                      ← Architectural Decision Records
    ├── ADR-001-postgresql-18.md
    ├── ADR-005-celery-pool-solo.md
    └── ... (9 ADRs total)
```

---

## 🔄 Team Workflow

### Daily Flow

**1. Morning Standup (15 minutes)**
- What did I complete yesterday?
- What will I work on today?
- Any blockers?

**2. Work on Card**
- Pick card from `03_kanban/02_in-progress/` (your assigned card)
- Follow card's acceptance criteria
- Write tests (TDD encouraged)
- Commit frequently

**3. Submit PR**
- Use `04_templates/pr-template.md`
- Move card from `02_in-progress/` to `03_code-review/`
- Tag 2+ reviewers

**4. Code Review**
- Review PRs in `03_code-review/` (2+ approvals required)
- Use `04_templates/code-review-checklist.md`
- Approve or request changes

**5. Testing**
- Card moves to `04_testing/`
- Run integration tests
- QA validation (if applicable)

**6. Done**
- Card meets Definition of Done
- Move to `05_done/`
- Archive at sprint end

### Sprint Ceremonies

| Ceremony | Duration | When | Purpose |
|----------|----------|------|---------|
| **Sprint Planning** | 2 hours | Monday Week 1 | Select cards, assign work, set sprint goal |
| **Daily Standup** | 15 minutes | Every morning | Sync progress, identify blockers |
| **Sprint Review** | 1 hour | Friday Week 2 | Demo completed work, show value |
| **Sprint Retrospective** | 1 hour | Friday Week 2 | Reflect on process, improve |

---

## 📊 Kanban Board & WIP Limits

### Column Rules

| Column | WIP Limit | Entry Criteria | Exit Criteria |
|--------|-----------|----------------|---------------|
| **Backlog** | None | Card created | Meets DoR → Ready |
| **Ready** | None | DoR passed, sized | Selected in sprint → In Progress |
| **In Progress** | **5** | Assigned to dev | PR created → Code Review |
| **Code Review** | **3** | PR submitted | 2+ approvals → Testing |
| **Testing** | **2** | Review approved | Tests pass → Done |
| **Done** | None | DoD met | Archive at sprint end |
| **Blocked** | None | Dependency blocker | Blocker resolved → Previous column |

**⚠️ WIP Limit Enforcement:**
- If column reaches WIP limit, **STOP** starting new work
- Finish existing cards before pulling new ones
- Prevents work fragmentation and context switching

---

## 🎯 Sprint Plan (6 Sprints = 12 Weeks)

| Sprint | Weeks | Goal | Cards | Priority |
|--------|-------|------|-------|----------|
| **Sprint 00** | 1-2 | Foundation & setup | F001-F012 (12 cards) | Setup |
| **Sprint 01** | 3-4 | Database & repositories | DB001-DB035, R001-R028 (63 cards) | High |
| **Sprint 02** | 5-6 | **ML Pipeline (V3 CRITICAL)** | ML001-ML018 (18 cards) | **CRITICAL** |
| **Sprint 03** | 7-8 | Services layer | S001-S042 (42 cards) | High |
| **Sprint 04** | 9-10 | Controllers + Celery | C001-C026, CEL001-CEL008 (34 cards) | High |
| **Sprint 05** | 11-12 | Deployment + observability | DEP001-DEP012, OBS001-OBS010 (22 cards) | Medium |

**Total Capacity**: 10 devs × 8 story points/sprint × 6 sprints = **480 story points**
**Total Cards**: ~245 cards (average 2 story points/card)
**Buffer**: 15% for bugs, refactoring, tech debt

---

## 📚 Key Documents to Read

### Must-Read (Before Starting)

1. **Tech Stack**: `00_foundation/tech-stack.md` → Know PostgreSQL 18, Python 3.12, FastAPI 0.118.2
2. **Architecture**: `00_foundation/architecture-principles.md` → Clean Architecture, Service→Service rule
3. **DoR/DoD**: `00_foundation/definition-of-ready.md` + `definition-of-done.md`
4. **Conventions**: `00_foundation/conventions.md` → Naming, formatting standards
5. **Local Setup**: `05_dev-environment/local-setup-guide.md` → 5-minute Docker setup

### Reference Documents

6. **Engineering Plan**: `../../engineering_plan/README.md` → Complete system design
7. **Database Schema**: `../../database/database.mmd` → ERD with all 28 tables
8. **ML Pipeline Flow**: `../../flows/procesamiento_ml_upload_s3_principal/PIPELINE_OVERVIEW.md`
9. **Critical Decisions**: `../../context/past_chats_summary.md` → Past technical decisions

---

## 🚨 Critical Rules (NEVER VIOLATE)

### Architecture Rules

1. **Service → Service Communication**
   ✅ `ServiceA → ServiceB → RepoB`
   ❌ `ServiceA → RepoB` (FORBIDDEN)

2. **Database as Source of Truth**
   All business logic references PostgreSQL schema. ML pipeline, API, frontend derive from DB.

3. **Async Everywhere (I/O-bound)**
   Use `async def` for all I/O operations (DB, S3, Redis).
   Use `def` for CPU-bound operations (FastAPI runs in thread pool).

4. **No N+1 Queries**
   Always use `selectinload()` (one-to-many) or `joinedload()` (many-to-one).

### ML Pipeline Rules (Sprint 02 - CRITICAL)

5. **GPU Workers: pool=solo MANDATORY**
   ```bash
   CUDA_VISIBLE_DEVICES=0 celery -A app worker --pool=solo --concurrency=1
   ```
   Why: prefork causes CUDA context conflicts → crashes

6. **Model Singleton Pattern**
   Load YOLO models once per worker (NOT per task).
   Prevents 2-3s overhead per image.

7. **UUID Generated in API**
   `s3_images.image_id` is UUID generated in API, NOT database SERIAL.
   Prevents race conditions, enables S3 key pre-generation.

### Quality Rules

8. **Tests First, Then Code**
   Write tests before or alongside code (TDD encouraged).
   **Minimum coverage: 80%** for all new code.

9. **No Hardcoded Secrets**
   Use environment variables (`.env` file).
   Secrets Manager for production.

10. **Linting & Formatting**
    ```bash
    ruff check .      # Linting
    ruff format .     # Formatting
    ```
    Pre-commit hooks enforce this automatically.

---

## 📈 Success Metrics

| Metric | Target | How to Track |
|--------|--------|--------------|
| **Sprint Velocity** | 80 points/sprint | `01_sprints/velocity-tracking.md` |
| **Code Coverage** | ≥80% | `pytest --cov=app --cov-report=html` |
| **Cycle Time** | Card ready → done ≤3 days | Kanban board timestamps |
| **WIP Violations** | <5% of sprint days | Daily standup tracking |
| **Blocker Duration** | Resolved within 1 day | `03_kanban/06_blocked/blocker-tracker.md` |
| **PR Review Time** | <4 hours average | GitHub insights |
| **Test Pass Rate** | ≥98% on main | CI/CD pipeline |

---

## 🆘 Getting Help

### When Blocked

1. **Check blockers first**: `03_kanban/06_blocked/blocker-tracker.md`
2. **Ask in daily standup**: Raise blocker, get team help
3. **Escalate if >1 day**: Move to `06_blocked/`, notify tech lead
4. **Document blocker**: Add to blocker tracker with resolution plan

### Common Issues

- **Card unclear?** → Read related docs in card's "Related Documentation" section
- **Test failing?** → Check `05_dev-environment/troubleshooting.md`
- **Architecture question?** → Consult `00_foundation/architecture-principles.md`
- **Tech decision needed?** → Create ADR in `09_decisions/` (use template)

### Resources

- **Glossary**: `GLOSSARY.md` → All project terms defined
- **Troubleshooting**: `05_dev-environment/troubleshooting.md`
- **Code Templates**: `04_templates/starter-code/`
- **Test Templates**: `04_templates/test-templates/`

---

## 🎉 Team Onboarding Checklist

**Day 1: Setup** (2 hours)
- [ ] Read this README
- [ ] Setup local environment (`05_dev-environment/local-setup-guide.md`)
- [ ] Run `docker-compose up` and verify all services start
- [ ] Run database seeds (`06_database/seed-scripts/run_all_seeds.sh`)
- [ ] Run tests (`pytest`) and verify they pass

**Day 2: Architecture** (4 hours)
- [ ] Read `00_foundation/tech-stack.md`
- [ ] Read `00_foundation/architecture-principles.md`
- [ ] Review database schema (`../../database/database.mmd`)
- [ ] Watch ML pipeline flow overview (if recording available)
- [ ] Review Clean Architecture diagram

**Day 3: First Card** (6 hours)
- [ ] Attend sprint planning (or watch recording)
- [ ] Pick first card from `03_kanban/01_ready/` (start with S or M size)
- [ ] Read card's related documentation
- [ ] Write failing test first
- [ ] Implement feature
- [ ] Submit PR

**Week 1: Contribute**
- [ ] Complete 2-3 cards (8-15 story points)
- [ ] Review 2+ PRs
- [ ] Attend all ceremonies (standup, review, retro)
- [ ] Ask questions when blocked

---

## 📝 Frequently Asked Questions

**Q: How do I know what to work on?**
A: Check `03_kanban/02_in-progress/` for your assigned card. If you don't have one, pick from `01_ready/` during sprint planning.

**Q: What if a card is too big?**
A: Break it down during sprint planning. Split XL → multiple L/M cards.

**Q: Can I start a new card before finishing my current one?**
A: Only if current card is blocked. Otherwise, finish current card first (reduces WIP, increases throughput).

**Q: How do I handle bugs?**
A: Create bug card, prioritize in next sprint. Critical bugs: fix immediately, pause current work.

**Q: What if tests fail in CI?**
A: Fix locally first (`pytest`). If stuck, ask in standup. Don't merge until green.

**Q: How do I update the database schema?**
A: Create Alembic migration (`alembic revision --autogenerate -m "description"`). Test locally. Include in PR.

**Q: When should I create an ADR?**
A: For any cross-cutting technical decision (affects >3 cards or multiple epics). Use `09_decisions/ADR-template.md`.

---

## 🚀 Let's Build DemeterAI!

**Project Start**: Sprint 00, Day 1
**Target Completion**: Week 12 (end of Sprint 05)
**Team**: 10 developers
**Goal**: Production-ready backend for 600,000+ plant inventory system

**Remember**:
- 🎯 Focus on critical path (ML pipeline in Sprint 02)
- 🧪 Tests first, then code
- 🔄 WIP limits prevent bottlenecks
- 🤝 Ask for help when blocked
- 📚 Documentation is code

**Good luck! 🌵🌱**

---

**Document Owner**: Backend Team Lead
**Last Updated**: 2025-10-09
**Next Review**: After Sprint 01 (adjust velocity/capacity based on actual performance)
