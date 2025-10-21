# Mini-Plan E: GitHub Actions CI/CD Pipeline

**Created**: 2025-10-21
**Team Leader**: Orchestration Agent
**Epic**: sprint-05-deployment
**Priority**: MEDIUM (automation important but not blocking deployment)
**Complexity**: 7 points (Medium)

---

## Task Overview

Implement GitHub Actions CI/CD pipeline for automated linting, testing, and Docker image building. Keep it simple, local-first, and focused on quality gates.

---

## Current State Analysis

**Existing CI/CD**:
- None (manual testing only)

**Existing Quality Tools**:
- pytest (tests exist)
- No linter configured (need ruff or black)
- No pre-commit hooks
- Docker build works manually

**Missing**:
- GitHub Actions workflow files
- Linting configuration
- Automated test execution
- Docker build automation
- Quality gate enforcement

---

## Architecture

**Layer**: Infrastructure (CI/CD Layer)
**Pattern**: Git Push → GitHub Actions → Lint → Test → Build → (Optional Deploy)

**Dependencies**:
- GitHub repository
- Existing tests (tests/ directory)
- Docker and docker-compose files
- New: Linting tools (ruff), GitHub Actions workflows

**Files to Create/Modify**:
- [ ] `.github/workflows/ci.yml` (create - main CI pipeline)
- [ ] `.github/workflows/docker-build.yml` (create - Docker build workflow)
- [ ] `pyproject.toml` (modify - add ruff/black configuration)
- [ ] `requirements-dev.txt` (create - development dependencies)
- [ ] `.pre-commit-config.yaml` (optional - local quality gates)

---

## Implementation Strategy

### Phase 1: Add Development Dependencies

**Create requirements-dev.txt**:
```
# Development dependencies (not needed in production)
pytest==8.3.5
pytest-asyncio==0.25.3
pytest-cov==6.0.0
pytest-xdist==3.6.1
ruff==0.9.3
black==25.10.0
mypy==1.14.5
httpx==0.28.2
```

### Phase 2: Configure Linting (pyproject.toml)

**Add to pyproject.toml** (or create if doesn't exist):
```toml
[project]
name = "demeterai"
version = "2.0.0"
requires-python = ">=3.12"

[tool.ruff]
# Linting configuration
line-length = 100
target-version = "py312"

# Enable specific linting rules
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # pyflakes
    "I",   # isort (import sorting)
    "B",   # flake8-bugbear
    "UP",  # pyupgrade
]

# Ignore specific rules
ignore = [
    "E501",  # Line too long (handled by formatter)
    "B008",  # Do not perform function calls in argument defaults
]

# Exclude directories
exclude = [
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "alembic/versions",
    "*.egg-info",
]

[tool.ruff.format]
# Formatting configuration (like black)
quote-style = "double"
indent-style = "space"

[tool.black]
line-length = 100
target-version = ['py312']
include = '\.pyi?$'

[tool.mypy]
python_version = "3.12"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = false
ignore_missing_imports = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "-v --strict-markers --tb=short"
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    "integration: marks tests as integration tests",
]
```

### Phase 3: Create GitHub Actions CI Workflow

**Create .github/workflows/ci.yml**:
```yaml
name: CI Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  lint:
    name: Lint & Format Check
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements-dev.txt

      - name: Run ruff linter
        run: ruff check app/ tests/

      - name: Check code formatting
        run: ruff format --check app/ tests/

      - name: Type checking with mypy
        run: mypy app/ --ignore-missing-imports
        continue-on-error: true  # Don't fail build on type errors (yet)

  test:
    name: Run Tests
    runs-on: ubuntu-latest
    needs: lint

    services:
      postgres:
        image: postgis/postgis:18-3.6
        env:
          POSTGRES_USER: demeter_test
          POSTGRES_PASSWORD: demeter_test_password
          POSTGRES_DB: demeterai_test
        ports:
          - 5434:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install -r requirements-dev.txt

      - name: Run database migrations
        env:
          DATABASE_URL: postgresql+asyncpg://demeter_test:demeter_test_password@localhost:5434/demeterai_test
          DATABASE_URL_SYNC: postgresql+psycopg2://demeter_test:demeter_test_password@localhost:5434/demeterai_test
        run: |
          alembic upgrade head

      - name: Run unit tests
        env:
          DATABASE_URL: postgresql+asyncpg://demeter_test:demeter_test_password@localhost:5434/demeterai_test
          DATABASE_URL_SYNC: postgresql+psycopg2://demeter_test:demeter_test_password@localhost:5434/demeterai_test
          REDIS_URL: redis://localhost:6379/0
        run: |
          pytest tests/unit/ -v --cov=app --cov-report=xml --cov-report=term-missing

      - name: Run integration tests
        env:
          DATABASE_URL: postgresql+asyncpg://demeter_test:demeter_test_password@localhost:5434/demeterai_test
          DATABASE_URL_SYNC: postgresql+psycopg2://demeter_test:demeter_test_password@localhost:5434/demeterai_test
          REDIS_URL: redis://localhost:6379/0
        run: |
          pytest tests/integration/ -v

      - name: Upload coverage to Codecov (optional)
        uses: codecov/codecov-action@v4
        with:
          file: ./coverage.xml
          fail_ci_if_error: false
        continue-on-error: true

  security:
    name: Security Checks
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install safety bandit

      - name: Check for known vulnerabilities
        run: safety check --json || true
        continue-on-error: true

      - name: Run bandit security linter
        run: bandit -r app/ -ll
        continue-on-error: true

  build:
    name: Build Docker Image
    runs-on: ubuntu-latest
    needs: [lint, test]
    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Build Docker image
        uses: docker/build-push-action@v5
        with:
          context: .
          file: ./Dockerfile
          push: false
          tags: demeterai:${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

      - name: Verify image size
        run: |
          docker images demeterai:${{ github.sha }}
          IMAGE_SIZE=$(docker images demeterai:${{ github.sha }} --format "{{.Size}}")
          echo "Image size: $IMAGE_SIZE"
          # TODO: Add size check (<500MB)
```

### Phase 4: Create Docker Build Workflow

**Create .github/workflows/docker-build.yml**:
```yaml
name: Docker Build & Push

on:
  push:
    tags:
      - 'v*.*.*'  # Trigger on version tags (v1.0.0, v2.0.0, etc.)

jobs:
  build-and-push:
    name: Build and Push Docker Image
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Log in to Docker Hub (optional)
        uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKERHUB_USERNAME }}
          password: ${{ secrets.DOCKERHUB_TOKEN }}
        continue-on-error: true

      - name: Extract version from tag
        id: version
        run: echo "VERSION=${GITHUB_REF#refs/tags/v}" >> $GITHUB_OUTPUT

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          file: ./Dockerfile
          push: false  # Set to true when ready to push
          tags: |
            demeterai:latest
            demeterai:${{ steps.version.outputs.VERSION }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

      - name: Verify image size
        run: |
          docker images demeterai:latest
          IMAGE_SIZE_MB=$(docker images demeterai:latest --format "{{.Size}}" | sed 's/MB//')
          echo "Image size: ${IMAGE_SIZE_MB}MB"
```

### Phase 5: Create Pre-Commit Hooks (Optional)

**Create .pre-commit-config.yaml**:
```yaml
# Pre-commit hooks - run locally with: pre-commit run --all-files
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
        args: ['--maxkb=1000']
      - id: check-merge-conflict

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.9.3
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.14.5
    hooks:
      - id: mypy
        args: [--ignore-missing-imports]
        additional_dependencies: [types-all]
```

---

## Acceptance Criteria

- [ ] `.github/workflows/ci.yml` created with lint, test, security, build jobs
- [ ] `.github/workflows/docker-build.yml` created for release builds
- [ ] `requirements-dev.txt` created with development dependencies
- [ ] `pyproject.toml` configured with ruff, black, mypy, pytest settings
- [ ] `.pre-commit-config.yaml` created (optional but recommended)
- [ ] CI pipeline runs on push to main/develop branches
- [ ] CI pipeline runs on pull requests
- [ ] Linting passes (ruff, black)
- [ ] All tests pass in CI
- [ ] Docker build succeeds in CI
- [ ] GitHub Actions badge added to README (optional)

---

## Testing Procedure

```bash
# 1. Test locally before pushing

# Install development dependencies
pip install -r requirements-dev.txt

# Run linting
ruff check app/ tests/
ruff format --check app/ tests/

# Run type checking
mypy app/ --ignore-missing-imports

# Run tests
pytest tests/ -v --cov=app

# Build Docker image
docker build -t demeterai:test .

# 2. Commit and push to trigger CI
git add .github/ pyproject.toml requirements-dev.txt
git commit -m "feat(ci): add GitHub Actions CI/CD pipeline"
git push origin develop

# 3. Check GitHub Actions
# Go to: https://github.com/YOUR_USERNAME/DemeterDocs/actions
# Verify all jobs pass (lint, test, security, build)

# 4. Create a pull request
# CI should run automatically
# Verify status checks pass

# 5. Test pre-commit hooks (optional)
pip install pre-commit
pre-commit install
pre-commit run --all-files
```

---

## Performance Expectations

- Lint job: <2 minutes
- Test job: <5 minutes (depends on test suite size)
- Security job: <2 minutes
- Build job: <5 minutes
- Total CI pipeline: <10 minutes

---

## Dependencies

**Blocked By**: None (can run in parallel)
**Blocks**: None (automation for future development)

**External Dependency**: GitHub repository

---

## Notes

- CI pipeline runs on every push to main/develop
- Can be extended with deployment steps (out of scope for Sprint 5)
- Consider adding branch protection rules (require CI to pass before merge)
- Docker Hub credentials needed if pushing images (optional)
- Security checks (safety, bandit) are set to `continue-on-error` (informational only)
- Coverage reports can be uploaded to Codecov (optional)
- Pre-commit hooks are local quality gates (run before commit)

---

## GitHub Repository Setup

**Branch Protection Rules** (recommended):
1. Go to Settings → Branches
2. Add rule for `main` branch:
   - Require pull request reviews before merging
   - Require status checks to pass (ci, lint, test)
   - Require branches to be up to date
   - Include administrators

**Secrets Configuration** (if pushing to Docker Hub):
1. Go to Settings → Secrets and variables → Actions
2. Add secrets:
   - DOCKERHUB_USERNAME
   - DOCKERHUB_TOKEN

---

## Future Enhancements (Out of Scope)

- Automated deployment to staging environment
- Performance benchmarking
- Dependency updates (Dependabot)
- Release notes generation
- Slack/Discord notifications on build failure
