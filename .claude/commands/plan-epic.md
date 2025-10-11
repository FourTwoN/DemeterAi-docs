---
description: Break an epic into atomic tasks, prioritize by dependencies, and move unblocked tasks to ready queue. Usage: /plan-epic <epic-id> (e.g., /plan-epic epic-004)
---

You are the **Scrum Master** executing the `/plan-epic` command.

## Task

Break epic `{{epic-id}}` into atomic tasks and prepare them for implementation.

## Steps

1. **Read Epic File**:
```bash
cat backlog/02_epics/{{epic-id}}-*.md
```

2. **Extract Card List**:
   - Identify all cards (e.g., S001-S042 for services epic)
   - Note story points per card
   - Total points for epic

3. **Analyze Dependencies**:
   - Check "Dependencies" section in epic file
   - Identify which cards are blocked by others
   - Note which cards are unblocked and ready to start

4. **Prioritize Tasks**:
   - Critical path cards (⚡⚡ symbol) → highest priority
   - Unblocked cards → move to `01_ready/`
   - Blocked cards → remain in `00_backlog/`

5. **Move Unblocked Tasks**:
```bash
# Move first batch of unblocked tasks
mv backlog/03_kanban/00_backlog/[CARD-ID]-*.md backlog/03_kanban/01_ready/
```

6. **Update Status**:
```bash
cat >> backlog/03_kanban/DATABASE_CARDS_STATUS.md <<EOF

## Epic Planning: {{epic-id}} ($(date +%Y-%m-%d\ %H:%M))

### Summary
- Total cards: [X]
- Total points: [Y]
- Moved to ready: [Z cards]
- Remaining in backlog: [W cards] (blocked by dependencies)

### Ready Queue
- [CARD-ID]: [Title] ([X]pts) - HIGH priority
- [CARD-ID]: [Title] ([Y]pts) - MEDIUM priority

### Blocked
- [CARD-ID]: [Title] - Blocked by: [BLOCKER-CARD-ID]

### Critical Path
- [CARD-ID]: ⚡⚡ [Title] (critical for Sprint-XX)

**Next**: Team Leader can start tasks from 01_ready/
EOF
```

7. **Report Results**:
   - List cards moved to ready
   - List cards still blocked
   - Highlight critical path items
   - Provide epic completion ETA

## Example

**Command**: `/plan-epic epic-004`

**Output**:
```
Reading epic-004-services.md...

Epic 004: Service Layer
- Total: 42 cards (210 points)
- Sprint: Sprint-03

Analyzing dependencies...

Unblocked tasks (ready to start):
✅ S001: StockMovementService (8pts, HIGH)
✅ S007: WarehouseService (3pts, MEDIUM)
✅ S013: ProductService (3pts, MEDIUM)
✅ S023: PhotoSessionService (8pts, CRITICAL ⚡⚡)
✅ S031: PipelineCoordinatorService (8pts, CRITICAL ⚡⚡)

Blocked tasks (remain in backlog):
⏸️ S002: StockBatchService (blocked by S001)
⏸️ S003: ManualInitializationService (blocked by S001, S028)
⏸️ S032: LocalizationService (blocked by S031)

Moving unblocked tasks to ready queue:
```bash
mv backlog/03_kanban/00_backlog/S001-*.md backlog/03_kanban/01_ready/
mv backlog/03_kanban/00_backlog/S007-*.md backlog/03_kanban/01_ready/
mv backlog/03_kanban/00_backlog/S013-*.md backlog/03_kanban/01_ready/
mv backlog/03_kanban/00_backlog/S023-*.md backlog/03_kanban/01_ready/
mv backlog/03_kanban/00_backlog/S031-*.md backlog/03_kanban/01_ready/
```

Updated DATABASE_CARDS_STATUS.md

Status:
- Ready: 5 cards (30 points)
- Blocked: 37 cards (180 points)
- Critical path items: 2 (S023, S031)

Epic completion ETA: 3-4 sprints (with parallel development)

Next action: Team Leader can start with S001 or S023 (critical)
```
