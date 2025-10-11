# Task Progress Update Template

**Use this template to append progress updates to task files in `backlog/03_kanban/`.**

---

## [Agent Name] Progress Update (YYYY-MM-DD HH:MM)

**Status**: [in-progress | review | testing | done | blocked]

### Work Completed
- [Bullet point 1]
- [Bullet point 2]
- [Bullet point 3]

### In Progress
- [ ] [Item currently being worked on]
- [ ] [Another ongoing item]

### Next Steps
- [Next action 1]
- [Next action 2]
- [Next action 3]

### Blockers (if any)
- [Blocker 1: description + who can unblock]
- [Blocker 2: description + what's needed]

### ETA
[Estimated time to completion: X hours/days]

---

## Example Usage (Python Expert)

```markdown
## Python Expert Progress Update (2025-10-11 15:30)

**Status**: in-progress

### Work Completed
- [✅] Created app/services/stock_movement_service.py (150 lines)
- [✅] Implemented create_manual_initialization method
- [✅] Added ProductMismatchException validation
- [✅] Enforced Service→Service pattern (ConfigService, BatchService)

### In Progress
- [ ] Adding comprehensive error handling
- [ ] Adding structured logging

### Next Steps
- Complete error handling (30 min)
- Add docstrings (15 min)
- Request Team Leader review (when done)

### Blockers
None

### ETA
1 hour (completion at ~16:30)
```

---

## Example Usage (Testing Expert)

```markdown
## Testing Expert Progress Update (2025-10-11 16:00)

**Status**: review

### Work Completed
- [✅] Created tests/unit/services/test_stock_movement_service.py (210 lines)
- [✅] Created tests/integration/test_stock_movement_api.py (155 lines)
- [✅] All 17 tests passing
- [✅] Coverage: 84% (target: ≥80%) ✅

### In Progress
- [ ] Adding edge case tests for timeout scenarios

### Next Steps
- Finalize edge cases (optional, coverage already met)
- Report to Team Leader

### Blockers
None

### ETA
Ready for Team Leader review now
```

---

## Example Usage (Team Leader)

```markdown
## Team Leader Progress Update (2025-10-11 17:00)

**Status**: testing

### Work Completed
- [✅] Code review complete (APPROVED)
- [✅] All tests pass (17/17)
- [✅] Coverage verified: 84% ✅
- [✅] Moved task to 04_testing/

### In Progress
- [ ] Running final quality gates

### Next Steps
- Complete quality gate verification (10 min)
- Invoke Git Commit Agent
- Move to 05_done/

### Blockers
None

### ETA
Ready for completion in 15 minutes
```

---

## Usage Instructions

1. **Copy template** to your working document
2. **Replace placeholders**:
   - Agent Name
   - Date and time
   - Status
   - All bullet points with actual progress
3. **Append to task file**:
   ```bash
   cat >> backlog/03_kanban/02_in-progress/S001-*.md <<EOF
   [your update here]
   EOF
   ```
4. **Update regularly** (every 30-60 minutes during active work)
5. **Be specific**: Mention file names, line counts, metrics
6. **Report blockers immediately**: Don't wait if you're stuck

---

## Status Values

- **in-progress**: Actively working on implementation
- **review**: Ready for code review
- **testing**: Tests complete, awaiting verification
- **done**: All criteria met, ready for completion
- **blocked**: Cannot proceed without intervention
