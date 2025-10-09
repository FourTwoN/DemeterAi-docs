# [TEST011] Test Coverage Reporting

## Metadata
- **Epic**: epic-012-testing
- **Sprint**: Sprint-03
- **Priority**: `medium`
- **Complexity**: S (2 points)
- **Dependencies**: Blocked by [F009]

## Description
Configure pytest-cov for code coverage reporting. Target >80% coverage. Integrate with CI/CD and Codecov.

## Acceptance Criteria
- [ ] pytest-cov configured in pytest.ini
- [ ] Coverage report generated after test run
- [ ] HTML coverage report for local viewing
- [ ] XML coverage report for CI/CD
- [ ] CI fails if coverage <80%
- [ ] Codecov integration (badge in README)

## Implementation
**pytest.ini:**
```ini
[pytest]
addopts =
    --cov=app
    --cov-report=html
    --cov-report=xml
    --cov-report=term-missing
    --cov-fail-under=80
```

**Run tests with coverage:**
```bash
pytest --cov=app --cov-report=html

# View HTML report
open htmlcov/index.html
```

**GitHub Actions integration:**
```yaml
- name: Run tests with coverage
  run: pytest --cov=app --cov-report=xml

- name: Upload coverage to Codecov
  uses: codecov/codecov-action@v3
  with:
    file: ./coverage.xml
    fail_ci_if_error: true
```

**Coverage badge (README.md):**
```markdown
[![codecov](https://codecov.io/gh/org/demeterai/branch/main/graph/badge.svg)](https://codecov.io/gh/org/demeterai)
```

## Testing
- Run pytest with coverage
- Verify coverage report generated
- Verify CI fails if coverage <80%
- View coverage trends in Codecov

---
**Card Created**: 2025-10-09
