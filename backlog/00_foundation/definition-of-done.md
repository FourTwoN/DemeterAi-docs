# Definition of Done (DoD) - DemeterAI v2.0
## Checklist Before Card Moves to Done

**Document Version:** 1.0
**Last Updated:** 2025-10-09
**⚠️ Purpose**: Cards must meet DoD before being marked as complete. Ensures production-ready code.

---

## What is Definition of Done?

**DoD** defines criteria a card MUST meet before it can be:
1. Moved from `03_kanban/04_testing/` to `03_kanban/05_done/`
2. Considered "complete" and deployable
3. Archived at sprint end

**Why DoD Matters**:
- Ensures consistent quality across all code
- Prevents technical debt accumulation
- Creates production-ready increments every sprint
- Builds team-wide quality standards

---

## DoD Checklist

### ✅ 1. Code Quality

**Requirements**:
- [ ] All acceptance criteria met and verified
- [ ] Code follows conventions (see `00_foundation/conventions.md`)
- [ ] No commented-out code or debug statements
- [ ] No `print()` statements (use `logger` instead)
- [ ] No hardcoded values (use environment variables or config)
- [ ] No secrets committed (API keys, passwords, tokens)

**Verification**:
```bash
# Manual code review
git diff main...feature-branch

# Check for print statements
grep -r "print(" app/

# Check for commented code
# (manual review in PR)
```

---

### ✅ 2. Type Hints & Docstrings

**Requirements**:
- [ ] All public functions have type hints
- [ ] Return types specified (use `None` for void)
- [ ] All public functions have docstrings (Google style)
- [ ] Complex logic has inline comments

**Example**:
```python
# ✅ GOOD
async def get_stock_movements(
    location_id: int,
    start_date: datetime,
    end_date: datetime
) -> List[StockMovement]:
    """
    Get all stock movements for a location within a date range.

    Args:
        location_id: Storage location ID
        start_date: Start of date range (inclusive)
        end_date: End of date range (inclusive)

    Returns:
        List of stock movements sorted by created_at DESC

    Raises:
        LocationNotFoundException: If location_id doesn't exist
    """
    pass

# ❌ BAD
async def get_stock_movements(location_id, start_date, end_date):
    # No type hints, no docstring
    pass
```

**Verification**:
```bash
# Type checking
mypy app/
```

---

### ✅ 3. Tests Written & Passing

**Requirements**:
- [ ] Unit tests written for all new functions/methods
- [ ] Integration tests written (if applicable - DB/API interactions)
- [ ] All tests pass locally (`pytest`)
- [ ] Code coverage ≥80% for new code (verified by pytest-cov)
- [ ] Edge cases tested (empty inputs, null values, errors)
- [ ] Test data uses fixtures (no hardcoded test data)

**Coverage Target**: **≥80%** for all new code

**Verification**:
```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=app --cov-report=html --cov-report=term

# Check coverage threshold (fails if <80%)
pytest --cov=app --cov-fail-under=80
```

**Example Test**:
```python
# ✅ GOOD
import pytest
from app.services.stock_movement_service import StockMovementService

@pytest.mark.asyncio
async def test_create_manual_init_success(mock_repo, mock_config_service):
    # Arrange
    service = StockMovementService(mock_repo, mock_config_service)
    request = ManualStockInitRequest(location_id=123, quantity=1500)

    # Act
    result = await service.create_manual_initialization(request)

    # Assert
    assert result.quantity == 1500
    mock_repo.create.assert_called_once()

# ❌ BAD
# (no tests written)
```

---

### ✅ 4. Linting & Formatting

**Requirements**:
- [ ] Code passes Ruff linter (`ruff check .`)
- [ ] Code formatted with Ruff (`ruff format .`)
- [ ] No linting warnings or errors
- [ ] Pre-commit hooks pass

**Verification**:
```bash
# Linting
ruff check .

# Formatting
ruff format .

# Pre-commit hooks (runs all checks)
pre-commit run --all-files
```

---

### ✅ 5. Database Migrations (if applicable)

**Requirements**:
- [ ] Alembic migration created (if schema changes)
- [ ] Migration tested locally (upgrade + downgrade)
- [ ] Migration reviewed by DBA or tech lead
- [ ] Migration includes rollback logic
- [ ] Foreign key constraints validated
- [ ] Indexes created for new columns (if frequent queries)

**Verification**:
```bash
# Create migration
alembic revision --autogenerate -m "add stock_movements table"

# Test upgrade
alembic upgrade head

# Test downgrade
alembic downgrade -1

# Re-upgrade
alembic upgrade head
```

**Checklist for Migrations**:
- [ ] Up migration works (no errors)
- [ ] Down migration works (rollback successful)
- [ ] Data integrity preserved (no orphan records)
- [ ] Indexes created for foreign keys
- [ ] No breaking changes without migration path

---

### ✅ 6. Code Review Approved

**Requirements**:
- [ ] Pull request created with descriptive title
- [ ] PR uses template (`04_templates/pr-template.md`)
- [ ] At least **2 reviewers** approved PR
- [ ] All review comments addressed or resolved
- [ ] No unresolved conversations
- [ ] CI/CD pipeline passes (green checkmark)

**Review Checklist** (for reviewers):
- [ ] Code follows architecture principles (Service → Service rule)
- [ ] No business logic in controllers
- [ ] No direct repository calls from services (only via other services)
- [ ] Error handling appropriate (custom exceptions, not generic)
- [ ] N+1 queries avoided (eager loading used)
- [ ] Async/await used correctly (no blocking calls in async functions)

**Verification**:
```bash
# Check CI/CD status
gh pr checks  # GitHub CLI

# Check approvals
gh pr view  # GitHub CLI
```

---

### ✅ 7. Integration Tests Pass

**Requirements**:
- [ ] Integration tests pass with real test database
- [ ] Database fixtures used (test data seeded)
- [ ] Test database cleaned up after tests
- [ ] No flaky tests (run 3 times to verify)

**Verification**:
```bash
# Run integration tests
pytest tests/integration/

# Run 3 times to check for flakiness
for i in {1..3}; do pytest tests/integration/ || break; done
```

---

### ✅ 8. Documentation Updated

**Requirements**:
- [ ] API documentation updated (if new endpoints)
- [ ] README updated (if setup/deployment changes)
- [ ] Configuration documented (if new env vars)
- [ ] Architectural decisions recorded (ADR if cross-cutting change)
- [ ] Card handover briefing completed

**Documentation Checklist**:
- [ ] OpenAPI/Swagger docs accurate (FastAPI generates automatically)
- [ ] Environment variables documented in `.env.example`
- [ ] Complex algorithms explained in code comments or separate doc
- [ ] Known limitations documented

**Verification**:
```bash
# Check OpenAPI docs
# Visit http://localhost:8000/docs after starting server

# Check .env.example
cat .env.example
```

---

### ✅ 9. No Breaking Changes (or Migration Path)

**Requirements**:
- [ ] Backward compatibility maintained (if API/schema changes)
- [ ] Migration path documented (if breaking change unavoidable)
- [ ] Dependent systems notified (if breaking change)
- [ ] Deprecation warnings added (if phasing out feature)

**Verification**:
```bash
# API version consistency check
# Ensure v1 endpoints remain unchanged

# Database schema check
# Ensure existing queries still work
```

---

### ✅ 10. Performance Acceptable

**Requirements**:
- [ ] No significant performance regression
- [ ] Query performance verified (if database changes)
- [ ] Memory usage reasonable (no leaks)
- [ ] API endpoints respond within SLA (<200ms for p95)

**Performance Benchmarks**:
| Operation | Target | Verification |
|-----------|--------|--------------|
| API endpoint (simple) | <50ms (p95) | Load test or manual timing |
| API endpoint (complex) | <200ms (p95) | Load test or manual timing |
| Database query | <50ms (p95) | `EXPLAIN ANALYZE` |
| Bulk insert (1000 rows) | <1s | Timer in test |

**Verification**:
```bash
# Profile code
python -m cProfile -o output.prof app/main.py

# Analyze SQL queries
EXPLAIN ANALYZE SELECT * FROM stock_movements WHERE ...;

# Load test API (optional, for critical endpoints)
ab -n 1000 -c 10 http://localhost:8000/api/stock/movements
```

---

### ✅ 11. CI/CD Pipeline Passes

**Requirements**:
- [ ] All CI/CD checks pass (GitHub Actions or equivalent)
- [ ] Linting passes
- [ ] Tests pass (unit + integration)
- [ ] Coverage check passes (≥80%)
- [ ] Build succeeds (Docker image builds)

**CI/CD Checks**:
1. Ruff linting (`ruff check .`)
2. Unit tests (`pytest tests/unit/`)
3. Integration tests (`pytest tests/integration/`)
4. Coverage (`pytest --cov=app --cov-fail-under=80`)
5. Docker build (`docker build -t demeterai-backend .`)

**Verification**:
```bash
# Check CI/CD status
gh pr checks

# Run CI/CD locally (simulate)
./scripts/ci_local.sh
```

---

### ✅ 12. Manual Testing (if UI/API changes)

**Requirements**:
- [ ] Feature tested manually in local environment
- [ ] Happy path verified (normal user flow)
- [ ] Error cases tested (invalid inputs, edge cases)
- [ ] Screenshots/recordings captured (if visual changes)

**Manual Test Checklist**:
- [ ] Start local environment (`docker-compose up`)
- [ ] Test happy path (expected behavior works)
- [ ] Test error cases (system handles gracefully)
- [ ] Test edge cases (empty inputs, null values, large datasets)
- [ ] Verify logs (no errors, warnings are acceptable)

---

## DoD Verification Process

### Before Moving to Done

**Who**: Developer (self-check) + 2 reviewers

**Steps**:
1. Developer runs full DoD checklist (12 items)
2. Developer marks card as "ready for review"
3. Reviewer 1 checks code quality, tests, architecture
4. Reviewer 2 checks tests, documentation, performance
5. If all checks pass → Approve PR
6. If any check fails → Request changes, move back to in-progress
7. Once approved → Merge PR
8. Move card to `03_kanban/05_done/`

### Sprint Review Verification

**When**: End of sprint (Friday Week 2)

**Who**: Product Owner + Tech Lead

**Steps**:
1. Review all cards in `05_done/`
2. Spot-check DoD compliance (sample 20% of cards)
3. Demo working features
4. Verify production-ready quality
5. Archive cards in sprint folder (`01_sprints/sprint-XX/done/`)

---

## Common DoD Violations (and How to Fix)

### ❌ Violation 1: Low Test Coverage

**Problem**:
```bash
$ pytest --cov=app --cov-report=term
Coverage: 65%  # Below 80% threshold
```

**Fix**:
1. Identify uncovered lines: `pytest --cov=app --cov-report=html`
2. Open `htmlcov/index.html` in browser
3. Write tests for uncovered code paths
4. Focus on edge cases and error handling
5. Re-run: `pytest --cov=app --cov-fail-under=80`

### ❌ Violation 2: Linting Errors

**Problem**:
```bash
$ ruff check .
app/services/stock_service.py:45:1: E501 Line too long (105 > 100)
app/services/stock_service.py:67:5: F841 Local variable 'result' assigned but never used
```

**Fix**:
```bash
# Auto-format
ruff format .

# Fix linting issues
ruff check --fix .

# Verify
ruff check .
```

### ❌ Violation 3: Missing Type Hints

**Problem**:
```python
async def get_stock(stock_id):  # No type hints
    pass
```

**Fix**:
```python
from typing import Optional
from app.models.stock_movement import StockMovement

async def get_stock(stock_id: int) -> Optional[StockMovement]:
    pass
```

### ❌ Violation 4: No Documentation

**Problem**:
- API endpoint added but `/docs` not updated
- New environment variable but `.env.example` missing entry

**Fix**:
```python
# FastAPI auto-generates docs from docstrings
@router.post("/stock/manual", summary="Initialize stock manually")
async def manual_init(request: ManualStockInitRequest):
    """
    Initialize stock count manually (without photo).

    Validates against storage_location_config.
    """
    pass

# Update .env.example
echo "NEW_CONFIG_VAR=default_value  # Description" >> .env.example
```

---

## DoD Checklist Summary (Quick Reference)

Print this and use during PR review:

```
DEFINITION OF DONE (DoD) - Quick Checklist

Card ID: [________]  PR #: [________]

[ ] 1. Code quality (conventions, no debug code, no secrets)
[ ] 2. Type hints & docstrings (all public functions)
[ ] 3. Tests written & passing (≥80% coverage)
[ ] 4. Linting & formatting (Ruff passes)
[ ] 5. Database migrations (if applicable, tested up/down)
[ ] 6. Code review approved (2+ reviewers)
[ ] 7. Integration tests pass (real test DB)
[ ] 8. Documentation updated (API docs, README, ADR)
[ ] 9. No breaking changes (or migration path documented)
[ ] 10. Performance acceptable (no regression)
[ ] 11. CI/CD pipeline passes (all checks green)
[ ] 12. Manual testing done (if UI/API changes)

PASS = All applicable checked → Merge & move to 05_done/
FAIL = Missing items → Request changes, back to in-progress

Reviewer: [________]  Date: [________]
```

---

## DoD Exemptions (Rare Cases)

**When DoD can be partially waived** (Tech Lead approval required):
- **Spike cards**: Research/investigation cards may skip tests
- **Emergency hotfixes**: Critical production bugs may skip full review (but require follow-up card)
- **Documentation-only**: Pure doc changes may skip integration tests

**Process**:
1. Dev requests exemption in PR description
2. Tech Lead reviews and approves/rejects
3. If approved, add follow-up card to address skipped items
4. Document exemption in sprint retrospective

---

## References

- **Testing Guide**: ../../backlog/04_templates/test-templates/
- **Code Review Checklist**: ../../backlog/04_templates/code-review-checklist.md
- **PR Template**: ../../backlog/04_templates/pr-template.md
- **Conventions**: ../../backlog/00_foundation/conventions.md

---

**Document Owner**: Tech Lead + QA Lead
**Review Frequency**: Every sprint retrospective (adjust if quality issues)
**Enforcement**: PR cannot be merged without DoD compliance
