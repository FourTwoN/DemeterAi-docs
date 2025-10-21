# Development Setup Guide - DemeterAI v2.0

Quick guide for setting up your local development environment with CI/CD tools.

## Prerequisites

- Python 3.12
- Docker & Docker Compose
- Git

## Initial Setup

### 1. Clone Repository

```bash
git clone https://github.com/your-org/DemeterDocs.git
cd DemeterDocs
```

### 2. Install Python Dependencies

```bash
# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install production dependencies
pip install -r requirements.txt

# Install development tools
pip install -r requirements-dev.txt
```

### 3. Install Pre-commit Hooks

```bash
# Install pre-commit
pre-commit install

# Run on all files (initial check)
pre-commit run --all-files
```

### 4. Initialize Secrets Baseline

```bash
# Create baseline for secret detection
detect-secrets scan > .secrets.baseline

# Update baseline when adding legitimate patterns
detect-secrets scan --baseline .secrets.baseline
```

### 5. Setup Database

```bash
# Start PostgreSQL test database
docker compose up db_test -d

# Wait for database to be ready
docker exec demeterai-db-test pg_isready

# Run migrations
alembic upgrade head
```

## Development Workflow

### Before Starting Work

```bash
# Pull latest changes
git pull origin main

# Create feature branch
git checkout -b feature/your-feature-name

# Ensure dependencies are up to date
pip install -r requirements.txt -r requirements-dev.txt
```

### During Development

```bash
# Run linting
ruff check app/ tests/

# Auto-fix linting issues
ruff check app/ tests/ --fix

# Format code
ruff format app/ tests/
black app/ tests/

# Sort imports
isort app/ tests/

# Type check
mypy app/ --ignore-missing-imports

# Run tests
pytest tests/ -v

# Check coverage
pytest tests/ --cov=app --cov-report=term-missing
```

### Before Committing

Pre-commit hooks will automatically run when you commit. They check:

✅ Ruff linting
✅ Ruff formatting
✅ MyPy type checking
✅ Secret detection
✅ YAML/JSON/TOML validation
✅ Trailing whitespace
✅ Large files (>5MB blocked)

```bash
# Commit (hooks run automatically)
git add .
git commit -m "feat: add new feature"

# If hooks fail, fix issues and retry
# To bypass hooks (use sparingly):
git commit --no-verify
```

### Push & Pull Request

```bash
# Push branch
git push origin feature/your-feature-name

# Create pull request on GitHub
# CI pipeline will run automatically
```

## Common Tasks

### Run All Local Checks (Same as CI)

```bash
# Create a script to run all checks
cat > run-ci-checks.sh <<'EOF'
#!/bin/bash
set -e

echo "🔍 Running Ruff linter..."
ruff check app/ tests/

echo "🎨 Running Ruff formatter..."
ruff format --check app/ tests/

echo "🔤 Running Black formatter..."
black --check app/ tests/

echo "📦 Running isort..."
isort --check-only app/ tests/

echo "🔎 Running MyPy type checker..."
mypy app/ --ignore-missing-imports

echo "🔒 Running Bandit security scan..."
bandit -r app/ -ll

echo "🧪 Running tests with coverage..."
pytest tests/ --cov=app --cov-report=term-missing --cov-fail-under=80

echo "✅ All checks passed!"
EOF

chmod +x run-ci-checks.sh
./run-ci-checks.sh
```

### Fix Formatting Issues

```bash
# Auto-fix all formatting
ruff check app/ tests/ --fix
ruff format app/ tests/
black app/ tests/
isort app/ tests/
```

### Update Pre-commit Hooks

```bash
# Update to latest versions
pre-commit autoupdate

# Re-install hooks
pre-commit install --install-hooks
```

### Run Specific Test Categories

```bash
# Unit tests only
pytest tests/unit/ -v

# Integration tests only
pytest tests/integration/ -v

# Specific test file
pytest tests/unit/services/test_product_service.py -v

# Specific test function
pytest tests/unit/services/test_product_service.py::test_create_product -v

# Run with coverage for specific module
pytest tests/unit/services/ --cov=app/services --cov-report=term-missing
```

### Security Scans

```bash
# Check for known vulnerabilities
safety check

# Audit dependencies
pip-audit

# Security linting
bandit -r app/ -ll -f screen

# Find secrets
detect-secrets scan
```

## CI/CD Pipeline

### What Runs on Push

When you push to GitHub, the following runs automatically:

1. **Lint & Format Check** (~2 min)
   - Ruff linting
   - Black formatting
   - Import sorting

2. **Type Check** (~3 min)
   - MyPy static analysis

3. **Security Scan** (~2 min)
   - Bandit security linting
   - Safety vulnerability check

4. **Tests & Coverage** (~8 min)
   - PostgreSQL + Redis setup
   - Database migrations
   - Unit tests
   - Integration tests
   - Coverage report (must be ≥80%)

5. **Docker Build** (~5 min, main branch only)
   - Multi-platform image build
   - Smoke tests

**Total:** ~8-10 minutes (jobs run in parallel)

### Viewing CI Results

1. Go to your pull request on GitHub
2. Scroll to "Checks" section at bottom
3. Click on failing check to see logs
4. Fix issues locally and push again

### Debugging Failed CI

```bash
# Pull the exact error from GitHub Actions logs
# Then reproduce locally:

# For lint failures:
ruff check app/ tests/ --output-format=github

# For test failures:
pytest tests/ -v --tb=short

# For coverage failures:
pytest tests/ --cov=app --cov-report=term-missing

# For type check failures:
mypy app/ --show-error-codes --pretty
```

## Docker Development

### Build Image Locally

```bash
# Build image
docker build -t demeterai:local .

# Run image
docker run --rm demeterai:local python --version

# Run tests in container
docker run --rm -v $(pwd):/app demeterai:local pytest tests/
```

### Docker Compose Development

```bash
# Start all services
docker compose up -d

# View logs
docker compose logs -f

# Run migrations
docker compose exec app alembic upgrade head

# Run tests
docker compose exec app pytest tests/

# Stop services
docker compose down
```

## Troubleshooting

### Pre-commit Hook Failures

**Issue:** `mypy` fails with missing imports

**Solution:**
```bash
# Install mypy dependencies
pip install -r requirements.txt -r requirements-dev.txt

# Or skip mypy temporarily
SKIP=mypy git commit -m "message"
```

### Coverage Below 80%

**Issue:** Coverage check fails

**Solution:**
```bash
# Find uncovered lines
pytest tests/ --cov=app --cov-report=term-missing

# Add tests for uncovered code in tests/
```

### Docker Build Fails

**Issue:** Image won't build

**Solution:**
```bash
# Check Dockerfile syntax
docker build -t demeterai:test .

# Clear build cache
docker builder prune -a
```

### Database Connection Errors

**Issue:** Tests fail with database connection errors

**Solution:**
```bash
# Restart database
docker compose down
docker compose up db_test -d

# Wait for readiness
sleep 5

# Run migrations
alembic upgrade head
```

## Best Practices

### Commit Messages

Follow Conventional Commits:

```
feat: add user authentication
fix: resolve database connection timeout
docs: update API documentation
test: add integration tests for products
refactor: simplify stock calculation logic
chore: update dependencies
```

### Code Style

- Use type hints on all functions
- Write docstrings for public APIs
- Keep functions under 50 lines
- Follow PEP 8 (enforced by ruff/black)
- Use async/await for I/O operations

### Testing

- Write tests for all new features
- Maintain ≥80% coverage
- Use real database (no mocks for business logic)
- Test edge cases and error conditions

### Security

- Never commit secrets
- Use environment variables for config
- Keep dependencies updated
- Run security scans regularly

## Resources

- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [Black Documentation](https://black.readthedocs.io/)
- [MyPy Documentation](https://mypy.readthedocs.io/)
- [Pre-commit Documentation](https://pre-commit.com/)
- [Pytest Documentation](https://docs.pytest.org/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)

## Getting Help

- Check workflow documentation: `.github/workflows/README.md`
- Review architecture docs: `engineering_plan/`
- Ask in team chat
- Create GitHub issue

---

**Last Updated:** 2025-10-21
**Maintained By:** DemeterAI Engineering Team
