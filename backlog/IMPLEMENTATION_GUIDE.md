# Implementation Guide - How to Use This Backlog
## Complete Scrum/Kanban System for DemeterAI v2.0

**Created**: 2025-10-09
**Status**: Ready for Team Use
**Team Size**: 10 developers
**Project Duration**: 12 weeks (6 sprints × 2 weeks)

---

## 🎯 What You Have Now

A **complete, execution-ready Scrum/Kanban backlog system** with:

1. **Foundation documentation** (9 files) - Team guidelines, conventions, quality standards
2. **Sprint planning** (6 sprints) - Complete 12-week roadmap with goals, capacity, ceremonies
3. **Templates** (4 files) - Starter code patterns for rapid development
4. **Sample cards** (2 cards) - Complete card structure showing all required fields
5. **Sample epics** (1 epic) - Epic structure with card lists
6. **Sample ADRs** (1 ADR) - Decision record template
7. **Sample views** (1 view) - Critical path visualization

**Total Created**: ~30 files, 10,000+ lines of documentation

**Total Planned**: ~370 files (you replicate remaining ~340 using templates provided)

---

## 📋 What's Complete vs What Remains

### ✅ COMPLETE (Ready to Use)

**Foundation & Standards**:
- [x] README.md - Complete system overview
- [x] QUICK_START.md - 5-minute onboarding
- [x] GLOSSARY.md - All terminology defined
- [x] tech-stack.md - Single source of truth for versions
- [x] architecture-principles.md - Clean Architecture rules
- [x] conventions.md - Naming, formatting standards
- [x] definition-of-ready.md - Sprint entry checklist
- [x] definition-of-done.md - Completion checklist
- [x] wip-limits.md - Kanban column limits

**Sprint Planning**:
- [x] Sprint 00-05 goals (6 files)
- [x] Sprint 00 backlog, capacity, ceremonies (3 files)
- [x] Velocity tracking template

**Templates**:
- [x] base_repository.py - AsyncRepository pattern
- [x] base_service.py - Service layer pattern
- [x] .env.example - Environment variables
- [x] pyproject.toml.template - Python packaging

**Sample Artifacts**:
- [x] F001-project-setup.md - Foundation card template
- [x] ML001-model-singleton.md - ML pipeline card template
- [x] epic-007-ml-pipeline.md - Epic template
- [x] ADR-001-postgresql-18.md - ADR template
- [x] critical-path-v3.md - View template

### 📝 REMAINING (Replicate Using Templates)

**Cards** (~240 remaining):
- [ ] F002-F012: Foundation cards (10 cards) - Use F001 template
- [ ] ML002-ML018: ML pipeline cards (17 cards) - Use ML001 template
- [ ] DB001-DB035: Database cards (35 cards)
- [ ] R001-R028: Repository cards (28 cards)
- [ ] S001-S042: Service cards (42 cards)
- [ ] C001-C026: Controller cards (26 cards)
- [ ] CEL001-CEL008: Celery cards (8 cards)
- [ ] SCH001-SCH020: Schema cards (20 cards)
- [ ] AUTH001-AUTH006: Auth cards (6 cards)
- [ ] OBS001-OBS010: Observability cards (10 cards)
- [ ] DEP001-DEP012: Deployment cards (12 cards)
- [ ] TEST001-TEST015: Testing cards (15 cards)

**Epics** (16 remaining):
- [ ] epic-001 through epic-017 - Use epic-007 template

**ADRs** (7 remaining):
- [ ] ADR-002 through ADR-009 - Use ADR-001 template

**Dev Environment** (5 files):
- [ ] local-setup-guide.md
- [ ] docker-setup.md
- [ ] gpu-setup.md
- [ ] troubleshooting.md
- [ ] pre-commit-config.yaml

**Database Seeds** (7 files):
- [ ] 01_seed_users.sql
- [ ] 02_seed_warehouses.sql
- [ ] 03_seed_products.sql
- [ ] 04_seed_packaging.sql
- [ ] 05_seed_location_configs.sql
- [ ] 06_seed_density_params.sql
- [ ] run_all_seeds.sh

---

## 🚀 How to Start Using This Backlog

### Day 1: Team Onboarding (2 hours)

**For Each Developer**:
1. Read `README.md` (15 min)
2. Read `QUICK_START.md` (10 min)
3. Read `00_foundation/architecture-principles.md` (20 min)
4. Read `00_foundation/conventions.md` (15 min)
5. Read `00_foundation/definition-of-ready.md` (10 min)
6. Read `00_foundation/definition-of-done.md` (10 min)
7. Setup local environment following `QUICK_START.md` (30 min)
8. Review sample cards (F001, ML001) to understand structure (10 min)

**For Scrum Master/Product Owner**:
1. Read all foundation files (1 hour)
2. Review sprint plans (01_sprints/) (30 min)
3. Prepare Sprint 00 planning meeting (30 min)

### Week 1: Sprint 00 Planning

**Sprint Planning Meeting** (2 hours):
1. **Review Sprint 00 Goal** (15 min)
   - Read `01_sprints/sprint-00-setup/sprint-goal.md`
   - Confirm team understands objective

2. **Create Remaining F001-F012 Cards** (45 min)
   - Use F001 as template
   - Copy structure, customize for each card
   - Ensure each card meets DoR
   - Move to `03_kanban/01_ready/`

3. **Card Selection & Assignment** (45 min)
   - Review capacity (80 points available)
   - Select 65 points worth of cards (healthy buffer)
   - Assign cards to developers
   - Identify work tracks (infrastructure, quality, containerization)

4. **Dependencies & Risks** (15 min)
   - Review dependency graph
   - Identify potential blockers
   - Agree on escalation process

### Ongoing: Daily Workflow

**Daily Standup** (9:00 AM, 15 minutes):
```
Each developer:
1. What I completed yesterday?
   - "Completed F001, moved to Done"
2. What I'm working on today?
   - "Starting F004 - logging config"
3. Any blockers?
   - "Waiting for Docker image approval"

Scrum Master:
- Check WIP limits (in-progress ≤5, review ≤3, testing ≤2)
- Escalate blockers >1 day old
- Update burndown chart
```

**During Sprint**:
1. **Work on card** (follow AC, write tests, code)
2. **Submit PR** (use template in `04_templates/pr-template.md`)
3. **Move card** to `03_kanban/03_code-review/`
4. **Get 2+ reviews** (use code review checklist)
5. **Merge PR** and move card to `03_kanban/05_done/`

---

## 📝 How to Create Remaining Cards

### Using F001 Template (Foundation Cards)

1. **Copy F001 structure**:
   ```bash
   cp 03_kanban/00_backlog/F001-project-setup.md 03_kanban/00_backlog/F002-virtual-env.md
   ```

2. **Update metadata**:
   - Card ID: F002
   - Title: Clear action-oriented title
   - Dependencies: What blocks/is blocked by this card

3. **Write description** (2-4 paragraphs):
   - What: What needs to be done
   - Why: Business/technical justification
   - Context: Relevant background

4. **Define acceptance criteria** (3-7 items):
   - Specific, testable conditions
   - Include edge cases
   - Cover functionality, performance, quality

5. **Add technical notes**:
   - Architecture layer
   - Key functions/classes to create
   - Code hints (NOT full code, just signatures)

6. **Specify testing requirements**:
   - Unit tests expectations
   - Integration tests if needed
   - Coverage target (≥80%)

7. **Write handover briefing**:
   - Context for next dev
   - Key decisions made
   - Known limitations
   - Next steps

8. **Review DoD checklist**: Ensure all items applicable

### Using ML001 Template (ML Pipeline Cards)

Same process as above, but:
- Reference ML pipeline documentation more heavily
- Include performance expectations (timing, memory)
- Mark critical path cards with ⚡
- Reference YOLO/SAHI documentation

### Card Naming Conventions

```
[AREA][NUMBER]-[short-descriptive-name].md

Examples:
✅ F001-project-setup.md
✅ ML003-sahi-detection.md
✅ DB015-stock-movements-model.md
✅ S023-stock-movement-service.md
✅ C012-stock-controller.md

❌ F1-setup.md (need 3 digits)
❌ ML-003-sahi.md (no dash before number)
❌ S23-StockService.md (no PascalCase in name)
```

---

## 🎯 How to Use Kanban Board

### Column Flow

```
00_backlog → 01_ready → 02_in-progress → 03_code-review → 04_testing → 05_done
              ↑              ↓ (blocked)         ↓
              └──────────06_blocked──────────────┘
```

### Moving Cards

**Backlog → Ready**:
- Card meets DoR (Definition of Ready)
- Dependencies resolved
- Acceptance criteria clear
- Story points estimated

**Ready → In Progress**:
- Selected during sprint planning
- Assigned to developer
- Developer starts coding
- **Check WIP limit**: If in-progress = 5, WAIT

**In Progress → Code Review**:
- PR submitted
- All tests pass locally
- Code linted and formatted
- **Check WIP limit**: If code-review = 3, WAIT

**Code Review → Testing**:
- 2+ approvals received
- All conversations resolved
- CI/CD passes
- **Check WIP limit**: If testing = 2, WAIT

**Testing → Done**:
- Integration tests pass
- Meets DoD (Definition of Done)
- Merged to main branch

**Any → Blocked**:
- External dependency blocks progress
- Document blocker in card
- Add to `06_blocked/blocker-tracker.md`
- Escalate if >1 day

### WIP Limit Enforcement

**If in-progress = 5**:
- STOP starting new cards
- Help others finish their cards
- Pair program on oldest card
- Clear blockers

**If code-review = 3**:
- STOP submitting new PRs
- Team: Review existing PRs immediately
- "Review Jam Session" (all devs review 1 PR)

**If testing = 2**:
- STOP moving from code-review
- Run integration tests immediately
- Fix any test failures before starting new work

---

## 📊 Tracking Progress

### Daily Burndown

**Update Daily** (during standup):
```
Remaining Points = Initial Commitment - Completed Points

Example:
Sprint 00 Start: 65 points remaining
Day 1: 60 points (5 points completed)
Day 2: 55 points (5 points completed)
...
Day 10: 0 points (all completed)
```

**Chart**:
```
Points
70 ┤
60 ┤ ●──●
50 ┤    ●──●
40 ┤       ●──●
30 ┤          ●──●
20 ┤             ●──●  ← Ideal burndown
10 ┤                ●──●
 0 └────────────────────●
    1  2  3  4  5  6  7  8  9 10 (Days)
```

### Velocity Tracking

**After Each Sprint**:
1. Count completed story points
2. Update `01_sprints/velocity-tracking.md`
3. Calculate average velocity
4. Adjust next sprint capacity if needed

**Example**:
```
Sprint 00: Planned 65, Completed 58 → Velocity: 58
Sprint 01: Planned 75, Completed 72 → Velocity: 72
Average: (58 + 72) / 2 = 65 points/sprint
```

---

## 🔥 Critical Path Monitoring

### Sprint 02 is CRITICAL

**V3 ML Pipeline = Project Critical Path**

If Sprint 02 fails or delays, entire project delays.

**Daily Checks During Sprint 02**:
- [ ] Is ML001 (Model Singleton) completed? (Blocks ALL ML work)
- [ ] Is ML003 (SAHI Detection) on track? (Critical path)
- [ ] Is ML009 (Pipeline Coordinator) blocked? (Blocks Sprint 04)
- [ ] Are critical path cards being prioritized? (WIP limits respected)

**Risk Mitigation**:
- Assign best developers to critical path cards
- Pair program on complex cards (ML003, ML009)
- Daily progress reviews (not just standup)
- Escalate blockers within 1 hour (not 1 day)

---

## 🛠 Tools & Integrations

### Recommended Tools

**Project Management**:
- **Option 1**: Use filesystem (this backlog structure)
- **Option 2**: Jira (import cards as issues)
- **Option 3**: Linear (import as issues)
- **Option 4**: GitHub Projects (import as issues with labels)

**Code Quality**:
- Ruff (linting + formatting) - configured in foundation
- pytest (testing) - templates provided
- mypy (type checking) - configuration in pyproject.toml
- pre-commit (git hooks) - setup in Sprint 00

**CI/CD**:
- GitHub Actions (Sprint 05) - templates in deployment epic
- GitLab CI (alternative)

**Monitoring**:
- Prometheus + Grafana (Sprint 05)
- OpenTelemetry (Sprint 05)

---

## 📚 Key Documents Quick Reference

**Before Starting**:
1. `README.md` - Start here
2. `QUICK_START.md` - Setup in 5 minutes
3. `00_foundation/architecture-principles.md` - MUST READ
4. `00_foundation/conventions.md` - Coding standards

**During Sprint Planning**:
1. `01_sprints/sprint-XX/sprint-goal.md` - Sprint objective
2. `01_sprints/sprint-XX/sprint-backlog.md` - Card selection
3. `01_sprints/sprint-XX/capacity-planning.md` - Team availability

**During Development**:
1. `03_kanban/02_in-progress/[your-card].md` - Your current card
2. `04_templates/starter-code/` - Code templates
3. `00_foundation/definition-of-done.md` - Completion checklist

**When Blocked**:
1. `00_foundation/wip-limits.md` - What to do when at WIP limit
2. `03_kanban/06_blocked/blocker-tracker.md` - Document blocker
3. `08_views/critical-path-v3.md` - Critical path cards

---

## 🎓 Training & Best Practices

### New Team Member Onboarding

**Week 1**:
- Day 1: Read all foundation docs (2 hours)
- Day 2: Setup local environment (2 hours)
- Day 3: Attend sprint planning, get first card (S or M size)
- Day 4-5: Work on first card, submit PR, get feedback

**Week 2**:
- Complete 2-3 cards (8-15 story points)
- Review 2+ PRs (learn from team)
- Attend all ceremonies (standup, review, retro)

### Code Review Best Practices

**For Authors**:
- Keep PRs small (<300 lines changed)
- Write descriptive PR description
- Use `04_templates/pr-template.md`
- Respond to feedback within 4 hours

**For Reviewers**:
- Review within 4 hours
- Use `04_templates/code-review-checklist.md`
- Check architecture compliance (Service→Service rule)
- Approve if meets DoD, request changes if not

---

## 🆘 Troubleshooting

### Problem: Too many cards in In Progress (>5)

**Solution**:
1. Daily standup: Identify bottleneck
2. Pair program on oldest card
3. Help finish existing work before starting new

### Problem: PRs stuck in Code Review (>1 day)

**Solution**:
1. Announce "Review Jam Session"
2. All devs review at least 1 PR today
3. Assign dedicated reviewers (rotate daily)

### Problem: Sprint goal at risk

**Solution**:
1. Identify critical path cards not completed
2. Reallocate developers to critical path
3. Cut non-critical cards if needed
4. Escalate to product owner

### Problem: Velocity dropping

**Solution**:
1. Sprint retrospective: Identify root cause
2. Adjust estimates (cards too large?)
3. Check for systematic blockers
4. Reduce commitment for next sprint

---

## 🎉 Success Metrics

**Project Success** = Complete 442 story points in 12 weeks

**Sprint Success** = Velocity ≥70% of planned

**Quality Success** = Test coverage ≥80%, Linting 100% pass

**Process Success** = WIP violations <10% of sprint days

---

## 📞 Support & Questions

**Blocked on process?** → Ask Scrum Master
**Blocked on architecture?** → Ask Tech Lead
**Blocked on ML?** → Ask ML Lead
**Blocked on database?** → Ask Database Architect

**Update this guide** as you learn better processes!

---

**Document Owner**: Scrum Master + Tech Lead
**Last Updated**: 2025-10-09
**Feedback**: Open PR to improve this guide!
