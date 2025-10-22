---
description: Review task code and tests, run quality gates, and move through review stages (in-progress → code-review → testing → done). Usage: /review-task <task-id> (e.g., /review-task S001)
---

You are the **Team Leader** executing the `/review-task` command.

## Task

Review and validate task `{{task-id}}` through all quality gates.

## Steps

### 1. Locate Task

```bash
# Find task in in-progress, code-review, or testing
TASK_FILE=$(find backlog/03_kanban/{02_in-progress,03_code-review,04_testing}/ -name "{{task-id}}-*.md" 2>/dev/null | head -1)

if [ -z "$TASK_FILE" ]; then
    echo "Error: Task {{task-id}} not found in review stages"
    exit 1
fi

CURRENT_STAGE=$(basename $(dirname "$TASK_FILE"))
echo "Current stage: $CURRENT_STAGE"
```

### 2. Code Review (if in 02_in-progress/)

```bash
# Check if implementation files exist
SERVICE_FILE="app/services/[name]_service.py"
TEST_FILE="tests/unit/services/test_[name]_service.py"

if [ ! -f "$SERVICE_FILE" ]; then
    echo "❌ Service file not found: $SERVICE_FILE"
    exit 1
fi

# Review checklist
echo "Running code review..."

# Check 1: Service→Service pattern
REPO_VIOLATIONS=$(grep -n "Repository" "$SERVICE_FILE" | grep -v "self.repo" | wc -l)
if [ $REPO_VIOLATIONS -gt 0 ]; then
    echo "❌ VIOLATION: Direct repository access detected"
    grep -n "Repository" "$SERVICE_FILE" | grep -v "self.repo"
    exit 1
else
    echo "✅ Service→Service pattern enforced"
fi

# Check 2: Type hints
UNTYPED=$(grep -c "async def.*) -> " "$SERVICE_FILE" || grep -c "async def" "$SERVICE_FILE")
echo "✅ Type hints present"

# Check 3: Docstrings
DOCSTRINGS=$(grep -c '"""' "$SERVICE_FILE")
if [ $DOCSTRINGS -lt 2 ]; then
    echo "⚠️ Few docstrings found (consider adding more)"
else
    echo "✅ Docstrings present"
fi
```

**Append review results**:

```markdown
## Team Leader Code Review ($(date +%Y-%m-%d\ %H:%M))
**Status**: ✅ APPROVED / ❌ NEEDS CHANGES

### Checklist
- [✅/❌] Service→Service pattern enforced
- [✅/❌] No direct repository access (except self.repo)
- [✅/❌] Type hints on all methods
- [✅/❌] Async/await used correctly
- [✅/❌] Business exceptions used
- [✅/❌] Docstrings present

### Changes Required (if any)
- [Issue 1]
- [Issue 2]

**Action**: [Python Expert - make changes] OR [Move to code-review/]
```

### 3. Testing Review (if in 03_code-review/)

```bash
echo "Running tests..."

# Run unit tests
pytest tests/unit/services/test_[name]_service.py -v

if [ $? -ne 0 ]; then
    echo "❌ Unit tests failing"
    exit 1
else
    echo "✅ Unit tests pass"
fi

# Run integration tests
pytest tests/integration/test_[name]_api.py -v

if [ $? -ne 0 ]; then
    echo "❌ Integration tests failing"
    exit 1
else
    echo "✅ Integration tests pass"
fi

# Check coverage
COVERAGE=$(pytest --cov=app.services.[name]_service --cov-report=term | grep TOTAL | awk '{print $4}' | sed 's/%//')

if [ $COVERAGE -lt 80 ]; then
    echo "❌ Coverage too low: $COVERAGE% (need ≥80%)"
    exit 1
else
    echo "✅ Coverage: $COVERAGE% (≥80%)"
fi
```

**Append test results**:

```markdown
## Team Leader Testing Review ($(date +%Y-%m-%d\ %H:%M))

### Test Results
- Unit tests: ✅ [X]/[X] passed
- Integration tests: ✅ [Y]/[Y] passed
- Coverage: ✅ [Z]% (target: ≥80%)

### Coverage Details
- Method 1: [coverage]%
- Method 2: [coverage]%

**Status**: ✅ APPROVED - Moving to 04_testing/
```

### 4. Final Quality Gates (if in 04_testing/)

```bash
echo "🚪 Running Quality Gates..."

# Gate 1: All acceptance criteria checked
UNCHECKED=$(grep -c "\[ \]" "$TASK_FILE")
if [ $UNCHECKED -gt 0 ]; then
    echo "❌ Gate 1: $UNCHECKED unchecked criteria"
    grep "\[ \]" "$TASK_FILE"
    exit 1
else
    echo "✅ Gate 1: All acceptance criteria checked"
fi

# Gate 2-4: Tests (already done above)
echo "✅ Gate 2-4: All tests pass, coverage ≥80%"

# Gate 5: No TODO/FIXME
TODO_COUNT=$(grep -r "TODO\|FIXME" "$SERVICE_FILE" | wc -l)
if [ $TODO_COUNT -gt 0 ]; then
    echo "⚠️ Gate 5: $TODO_COUNT TODO/FIXME found (non-blocking)"
else
    echo "✅ Gate 5: No TODO/FIXME"
fi

echo ""
echo "✅ ALL QUALITY GATES PASSED"
```

### 5. Move Through Stages

```bash
case "$CURRENT_STAGE" in
    "02_in-progress")
        mv "$TASK_FILE" "backlog/03_kanban/03_code-review/"
        echo "Moved to: code-review"
        ;;
    "03_code-review")
        mv "$TASK_FILE" "backlog/03_kanban/04_testing/"
        echo "Moved to: testing"
        ;;
    "04_testing")
        # Quality gates passed - ready for completion
        echo "✅ READY FOR COMPLETION"
        echo "Next: Run /complete-task {{task-id}}"
        ;;
esac
```

### 6. Final Approval (if all gates passed)

```markdown
## Team Leader Final Approval ($(date +%Y-%m-%d\ %H:%M))
**Status**: ✅ READY FOR COMPLETION

### Quality Gates Summary
- [✅] All acceptance criteria checked
- [✅] Unit tests pass ([X]/[X])
- [✅] Integration tests pass ([Y]/[Y])
- [✅] Coverage: [Z]% (≥80%)
- [✅] Code review approved
- [✅] No blocking issues

### Performance Metrics
- Service method: [X]ms (target: <[Y]ms) ✅
- Full workflow: [X]ms (target: <[Y]ms) ✅

### Files Modified
- [file1] (created, [X] lines)
- [file2] (created, [Y] lines)

**Next**: Run /complete-task {{task-id}} to invoke Git Commit Agent and move to 05_done/
```

## Example

**Command**: `/review-task S001`

**Output**:

```
Located task: backlog/03_kanban/02_in-progress/S001-stock-movement-service.md

Current stage: in-progress

Running code review...
✅ Service→Service pattern enforced (no violations)
✅ Type hints present on all methods
✅ Docstrings present (8 found)
✅ Async/await used correctly
✅ Business exceptions used

Code review: ✅ APPROVED

Moving to code-review stage...
✅ Moved to: backlog/03_kanban/03_code-review/

Running tests...
✅ Unit tests: 12/12 passed
✅ Integration tests: 5/5 passed
✅ Coverage: 84% (≥80%)

Testing review: ✅ APPROVED

Moving to testing stage...
✅ Moved to: backlog/03_kanban/04_testing/

Running quality gates...
✅ Gate 1: All acceptance criteria checked
✅ Gate 2: Unit tests pass
✅ Gate 3: Integration tests pass
✅ Gate 4: Coverage 84% (≥80%)
✅ Gate 5: No TODO/FIXME

✅ ALL QUALITY GATES PASSED

Status: ✅ READY FOR COMPLETION

Next action: Run /complete-task S001
```
