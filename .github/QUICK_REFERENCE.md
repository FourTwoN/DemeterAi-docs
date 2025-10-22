# CI/CD Quick Reference Card

**DemeterAI v2.0** | **Sprint 5** | **Updated: 2025-10-21**

---

## 🚀 Quick Start

```bash
# Install dev tools
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Run all checks locally
ruff check app/ tests/ && \
mypy app/ && \
pytest tests/ --cov=app --cov-fail-under=80
```

---

## 📋 Common Commands

### Linting & Formatting

```bash
# Check code
ruff check app/ tests/

# Auto-fix issues
ruff check app/ tests/ --fix

# Format code
ruff format app/ tests/
black app/ tests/

# Sort imports
isort app/ tests/
```

### Type Checking

```bash
# Run MyPy
mypy app/ --ignore-missing-imports

# With verbose output
mypy app/ --show-error-codes --pretty
```

### Testing

```bash
# All tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=app --cov-report=term-missing

# Specific test file
pytest tests/unit/services/test_product_service.py -v

# Fast fail
pytest tests/ -x

# Parallel execution
pytest tests/ -n auto
```

### Security

```bash
# Code security
bandit -r app/ -ll

# Dependency vulnerabilities
safety check
pip-audit

# Secret detection
detect-secrets scan
```

### Pre-commit

```bash
# Run manually
pre-commit run --all-files

# Update hooks
pre-commit autoupdate

# Skip (use sparingly!)
git commit --no-verify
```

---

## 🔧 Workflow Triggers

| Workflow          | Trigger          | Duration   |
|-------------------|------------------|------------|
| **CI Pipeline**   | Push, PR         | ~8-10 min  |
| **Docker Build**  | Release, Tags    | ~15-20 min |
| **Security Scan** | Push, PR, Weekly | ~5-8 min   |

---

## ✅ Quality Gates

Every PR must pass:

- ✅ Ruff linting (no errors)
- ✅ Black formatting
- ✅ MyPy type checking
- ✅ Bandit security scan
- ✅ All tests pass
- ✅ Coverage ≥ 80%

---

## 🐛 Troubleshooting

### Pre-commit fails

```bash
# Fix formatting
ruff format app/ tests/
black app/ tests/

# Update deps
pip install -r requirements-dev.txt
```

### Tests fail in CI

```bash
# Run with same DB
docker compose up db_test -d
pytest tests/
```

### Coverage too low

```bash
# Find uncovered lines
pytest tests/ --cov=app --cov-report=term-missing

# Add tests
```

---

## 📚 Documentation

| File                          | Purpose                |
|-------------------------------|------------------------|
| `.github/workflows/README.md` | Workflow reference     |
| `.github/DEVELOPMENT.md`      | Setup guide            |
| `.github/CI_CD_SUMMARY.md`    | Implementation summary |

---

## 🔗 Useful Links

- [Ruff Docs](https://docs.astral.sh/ruff/)
- [MyPy Docs](https://mypy.readthedocs.io/)
- [Pytest Docs](https://docs.pytest.org/)
- [Pre-commit Docs](https://pre-commit.com/)

---

**Questions?** Check `.github/workflows/README.md` or ask the team.
