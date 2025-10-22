# WIP Limits - DemeterAI v2.0

## Work-In-Progress Constraints for Kanban Flow

**Document Version:** 1.0
**Last Updated:** 2025-10-09
**⚠️ Purpose**: WIP limits prevent bottlenecks, reduce context switching, and increase throughput.

---

## What are WIP Limits?

**WIP (Work-In-Progress) Limits** constrain the number of cards allowed in each Kanban column
simultaneously.

**Why WIP Limits Matter**:

- **Prevent bottlenecks**: Forces team to finish work before starting new work
- **Reduce context switching**: Fewer parallel tasks = better focus
- **Expose blockers**: Makes problems visible quickly
- **Increase throughput**: Counter-intuitive but proven by queuing theory
- **Improve quality**: Less rushed work, more attention to detail

**Core Principle**: "Stop starting, start finishing" - Don't pull new work until current work is
done.

---

## Kanban Columns & WIP Limits

### Overview Table

| Column             | WIP Limit | Rationale                | Violation Action       |
|--------------------|-----------|--------------------------|------------------------|
| **00_backlog**     | None      | Unlimited planning space | N/A                    |
| **01_ready**       | None      | Healthy backlog needed   | N/A                    |
| **02_in-progress** | **5**     | 10 devs, allow pairing   | Stop pulling new cards |
| **03_code-review** | **3**     | Force fast reviews       | Prioritize reviews     |
| **04_testing**     | **2**     | Small batch testing      | Test immediately       |
| **05_done**        | None      | Archive at sprint end    | N/A                    |
| **06_blocked**     | None      | Track all blockers       | Resolve within 1 day   |

---

## Detailed Column Rules

### 00_backlog (No Limit)

**Purpose**: Collect all potential work

**WIP Limit**: **None** (unlimited)

**Rules**:

- Cards can stay here indefinitely
- Must meet DoR before moving to Ready
- Refined during mid-sprint backlog sessions

**Health Check**:

- Backlog should have 150-200 story points (2× sprint capacity)
- If backlog <80 points → Product Owner needs to prepare more cards

---

### 01_ready (No Limit)

**Purpose**: Sprint-ready cards awaiting selection

**WIP Limit**: **None** (unlimited)

**Rules**:

- All cards must meet DoR (see `definition-of-ready.md`)
- Reviewed during sprint planning
- Cards selected from here into sprint backlog

**Health Check**:

- Ready column should have 80-100 story points before sprint planning
- If Ready <60 points → Not enough groomed work, delay sprint planning

---

### 02_in-progress (Limit: 5)

**Purpose**: Actively coding, not yet PR-ready

**WIP Limit**: **5 cards maximum**

**Rationale**:

- Team size: 10 developers
- Allow pair programming (2 devs per card)
- Limit prevents overcommitment
- Forces focus on finishing current work

**Rules**:

- Each card must have assignee (1-2 devs)
- If WIP = 5 → STOP pulling new cards
- If WIP = 5 → Help others finish their cards
- Move to Code Review as soon as PR created

**Violation Handling**:

```
IF in_progress.count() > 5 THEN
  1. Daily standup: Identify bottleneck
  2. Action: Pair program on oldest card
  3. Action: Remove blockers preventing PR submission
  4. DO NOT: Start new cards until <5
END IF
```

**Health Check**:

- Average cycle time (In Progress → Done): ≤2 days
- If cards stay >3 days → Investigate (too complex? blocked?)

---

### 03_code-review (Limit: 3)

**Purpose**: PR submitted, awaiting approval

**WIP Limit**: **3 PRs maximum**

**Rationale**:

- Small batch size forces fast reviews
- Prevents "review backlog"
- Encourages continuous code review
- 3 = manageable for daily review cycles

**Rules**:

- Each PR must have 2+ reviewers assigned
- If WIP = 3 → Team MUST prioritize reviews over new coding
- Target review time: <4 hours
- Move to Testing once 2+ approvals received

**Violation Handling**:

```
IF code_review.count() > 3 THEN
  1. Daily standup: Announce "Review Jam Session"
  2. Action: All devs review at least 1 PR today
  3. Action: Senior devs prioritize reviews
  4. DO NOT: Submit new PRs until <3
END IF
```

**Health Check**:

- Average review time: <4 hours
- If PRs stay >1 day → Not enough reviewers, reassign

---

### 04_testing (Limit: 2)

**Purpose**: Integration testing, QA validation

**WIP Limit**: **2 cards maximum**

**Rationale**:

- Small batch testing catches issues fast
- Prevents "testing backlog"
- Forces immediate integration test runs
- 2 = allows parallel testing of independent features

**Rules**:

- Integration tests must pass
- Manual testing (if applicable)
- If WIP = 2 → Team helps with testing (don't start new work)
- Move to Done once all tests pass

**Violation Handling**:

```
IF testing.count() > 2 THEN
  1. Daily standup: Identify testing bottleneck
  2. Action: Run integration tests immediately
  3. Action: If tests fail → Fix bugs, don't start new work
  4. DO NOT: Move cards from Code Review until <2
END IF
```

**Health Check**:

- Average testing time: <4 hours
- If cards stay >1 day → Flaky tests? Need automation?

---

### 05_done (No Limit)

**Purpose**: Completed, production-ready work

**WIP Limit**: **None** (unlimited)

**Rules**:

- All DoD criteria met (see `definition-of-done.md`)
- Code merged to main branch
- Archived at sprint end (moved to `01_sprints/sprint-XX/done/`)

**Health Check**:

- Velocity: 80 story points per sprint (10 devs × 8 points)
- If velocity <70 → Investigate (estimates off? blockers? quality issues?)

---

### 06_blocked (No Limit)

**Purpose**: Track cards waiting on dependencies

**WIP Limit**: **None** (track all blockers)

**Rules**:

- Cards with unresolved dependencies
- Blocker must be documented in `blocker-tracker.md`
- Target resolution time: **<1 business day**
- If blocker >2 days → Escalate to tech lead/product owner

**Violation Handling** (Escalation):

```
IF blocker.days_blocked > 2 THEN
  1. Daily standup: Escalate blocker
  2. Action: Tech lead/PO resolves blocker today
  3. Action: Consider alternative solution (unblock work)
  4. Document: Add blocker to retrospective for process improvement
END IF
```

**Health Check**:

- Average blocker resolution time: <1 day
- If >5 cards blocked simultaneously → Systemic issue, review dependencies

---

## WIP Limit Enforcement

### Daily Standup Checks

**Facilitator Responsibility**:

1. Count cards in each WIP-limited column
2. Announce if any column at/over limit
3. Identify bottleneck and action plan

**Script**:

```
"Good morning team. WIP check:
- In Progress: 4/5 (healthy)
- Code Review: 3/3 (AT LIMIT - prioritize reviews today)
- Testing: 1/2 (healthy)
- Blocked: 2 cards (escalate if >1 day)

Action: All devs review at least 1 PR before writing new code today."
```

### Sprint Retrospective Review

**Questions to Ask**:

1. Did we violate WIP limits this sprint? How many times?
2. What caused violations? (overcommitment, unclear DoR, blockers)
3. Should we adjust limits? (increase/decrease based on flow)
4. What process improvements can prevent future violations?

**Metrics to Track**:

- **Violation Count**: # of days WIP limit exceeded per sprint
- **Average Cycle Time**: Card Ready → Done (target: ≤3 days)
- **Throughput**: Cards completed per sprint (target: 40-50 cards)

---

## WIP Limit Adjustment Rules

### When to Increase Limits

**Scenario 1**: Consistent high velocity, no bottlenecks

- Current: In Progress = 5, consistently at 4-5 cards
- Proposal: Increase In Progress to 6 for 1 sprint (experiment)
- Measure: Did cycle time increase? Did quality decrease?
- Decision: Keep if metrics stable, revert if metrics degrade

**Scenario 2**: Team size increase

- Current: 10 developers, In Progress = 5
- Change: 12 developers join
- Proposal: Increase In Progress to 6
- Rationale: Maintain 0.5× ratio (6 cards / 12 devs)

### When to Decrease Limits

**Scenario 1**: Frequent violations, quality issues

- Current: In Progress = 5, violated 8/10 sprint days
- Problem: Too much parallel work, context switching
- Proposal: Decrease In Progress to 4 for 1 sprint
- Measure: Did violations decrease? Did quality improve?

**Scenario 2**: Slow review cycle

- Current: Code Review = 3, PRs stay 2-3 days
- Problem: Not enough review capacity
- Proposal: Decrease Code Review to 2 (force faster reviews)
- Measure: Did review time decrease?

### Adjustment Process

1. **Propose** change in sprint retrospective
2. **Justify** with data (violation count, cycle time, throughput)
3. **Experiment** for 1 sprint (2 weeks)
4. **Measure** impact (same metrics as before)
5. **Decide** keep, revert, or adjust further
6. **Document** decision in retrospective notes

---

## WIP Limit Violations (Common Scenarios)

### Scenario 1: In Progress = 6 (Exceeds Limit of 5)

**Symptoms**:

- 6 cards in In Progress column
- Developers starting new work instead of finishing current work

**Root Causes**:

- Overcommitment in sprint planning
- Unclear acceptance criteria (cards take longer than expected)
- Blockers not escalated (cards stuck, devs start new work)

**Actions**:

1. **Immediate**: Stop pulling new cards until In Progress <5
2. **Short-term**: Pair program on oldest card to finish faster
3. **Long-term**: Review sprint planning estimates (adjust velocity)

### Scenario 2: Code Review = 4 (Exceeds Limit of 3)

**Symptoms**:

- 4 PRs awaiting review
- Reviews taking >1 day

**Root Causes**:

- Not enough reviewers available
- PRs too large (>500 lines changed)
- Complex changes requiring deep review

**Actions**:

1. **Immediate**: Announce "Review Jam Session" - all devs review 1 PR
2. **Short-term**: Assign dedicated reviewers (rotate daily)
3. **Long-term**: Enforce PR size limit (<300 lines), break large changes into smaller PRs

### Scenario 3: Testing = 3 (Exceeds Limit of 2)

**Symptoms**:

- 3 cards in Testing column
- Integration tests taking >4 hours

**Root Causes**:

- Flaky tests (random failures)
- Test environment unstable
- Manual testing bottleneck

**Actions**:

1. **Immediate**: Run tests in parallel (if independent)
2. **Short-term**: Fix flaky tests, stabilize test environment
3. **Long-term**: Automate manual testing, invest in test infrastructure

---

## Metrics & Health Indicators

### Cycle Time (Card Ready → Done)

**Target**: ≤3 days average

**Measurement**:

```
Cycle Time = date(Done) - date(Ready)
Average Cycle Time = SUM(cycle_times) / COUNT(cards)
```

**Health Indicators**:

- ✅ Green: <3 days average
- ⚠️ Yellow: 3-5 days average (investigate bottlenecks)
- ❌ Red: >5 days average (systemic issues)

### Throughput (Cards Completed per Sprint)

**Target**: 40-50 cards per sprint (10 devs × 4-5 cards)

**Measurement**:

```
Throughput = COUNT(cards in 05_done at sprint end)
```

**Health Indicators**:

- ✅ Green: 40-50 cards
- ⚠️ Yellow: 30-40 cards (below capacity)
- ❌ Red: <30 cards (investigate blockers)

### WIP Limit Violation Rate

**Target**: <10% of sprint days

**Measurement**:

```
Violation Rate = (days_with_violations / total_sprint_days) × 100
```

**Health Indicators**:

- ✅ Green: 0-10% (0-1 violations per sprint)
- ⚠️ Yellow: 10-30% (2-3 violations per sprint)
- ❌ Red: >30% (4+ violations per sprint, adjust limits)

---

## References

- **Kanban Board Structure**: ../03_kanban/README.md
- **Definition of Ready**: ./definition-of-ready.md
- **Definition of Done**: ./definition-of-done.md
- **Sprint Planning**: ../01_sprints/sprint-00-setup/sprint-ceremonies.md

---

## Quick Reference Card (Print & Post)

```
╔═══════════════════════════════════════════════════════╗
║             WIP LIMITS - QUICK REFERENCE               ║
╠═══════════════════════════════════════════════════════╣
║ Column          │ WIP Limit │ Action if At Limit      ║
╟─────────────────┼───────────┼─────────────────────────╢
║ Backlog         │ None      │ N/A                     ║
║ Ready           │ None      │ N/A                     ║
║ In Progress     │ 5         │ STOP pulling new cards  ║
║ Code Review     │ 3         │ Prioritize reviews      ║
║ Testing         │ 2         │ Test immediately        ║
║ Done            │ None      │ N/A                     ║
║ Blocked         │ None      │ Escalate if >1 day      ║
╚═══════════════════════════════════════════════════════╝

GOLDEN RULE: "Stop starting, start finishing"

IF column at WIP limit THEN
  Don't start new work
  Help finish existing work
  Remove blockers
END IF

Daily Standup: Check WIP limits, announce violations, plan actions
```

---

**Document Owner**: Scrum Master / Team Facilitator
**Review Frequency**: Every sprint retrospective (adjust limits if needed)
**Enforcement**: Daily standup facilitator + team self-management
