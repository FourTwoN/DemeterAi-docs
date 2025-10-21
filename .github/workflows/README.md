# GitHub Actions Workflows - DemeterAI v2.0

This directory contains CI/CD pipelines for automated testing, security scanning, and deployment.

## Workflows Overview

### 1. CI Pipeline (`ci.yml`)

**Triggers:**
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop`
- Manual dispatch

**Jobs:**

#### Lint & Format Check
- Runs `ruff` linter
- Runs `ruff` formatter check
- Runs `black` formatter check
- Runs `isort` import sorting check

#### Type Check
- Runs `mypy` static type checker
- Validates type hints across codebase

#### Security Scan
- Runs `bandit` security linter
- Runs `safety` dependency vulnerability checker
- Generates security reports

#### Tests & Coverage
- Sets up PostgreSQL 15 + PostGIS 3.3
- Sets up Redis 7
- Runs database migrations
- Runs unit tests
- Runs integration tests
- Generates coverage reports (minimum 80%)
- Uploads coverage artifacts

#### Build Docker Image (main branch only)
- Builds Docker image
- Caches layers for faster builds
- Tests image functionality

**Duration:** ~8-10 minutes

---

### 2. Docker Build & Release (`docker-build.yml`)

**Triggers:**
- Release published
- Tags pushed (v*)
- Manual dispatch

**Jobs:**

#### Build Multi-Platform Image
- Builds for `linux/amd64` and `linux/arm64`
- Pushes to GitHub Container Registry (ghcr.io)
- Tags with version, branch, and SHA
- Uses GitHub Actions cache

#### Test Image
- Pulls built image
- Runs smoke tests

**Duration:** ~15-20 minutes

---

### 3. Security Scan (`security.yml`)

**Triggers:**
- Push to `main` or `develop`
- Pull requests
- Weekly schedule (Mondays at 00:00 UTC)
- Manual dispatch

**Jobs:**

#### Dependency Security Scan
- Runs `safety` for known vulnerabilities
- Runs `pip-audit` for dependency issues

#### Code Security Scan
- Runs `bandit` with medium-high severity checks

#### Secrets Detection
- Runs `TruffleHog` to detect leaked secrets

#### CodeQL Analysis
- Runs GitHub's CodeQL security scanning

**Duration:** ~5-8 minutes

---

## Setup Instructions

### Prerequisites

1. **Install dependencies:**
   ```bash
   pip install -r requirements-dev.txt
   ```

2. **Install pre-commit hooks:**
   ```bash
   pre-commit install
   ```

3. **Initialize secrets baseline:**
   ```bash
   detect-secrets scan > .secrets.baseline
   ```

### Local Testing

Run checks locally before pushing:

```bash
# Lint
ruff check app/ tests/
ruff format --check app/ tests/

# Type check
mypy app/ --ignore-missing-imports

# Security
bandit -r app/ -ll

# Tests
pytest tests/ --cov=app --cov-report=term-missing --cov-fail-under=80
```

### Pre-commit Hooks

Automatically runs before each commit:

```bash
# Manual run on all files
pre-commit run --all-files

# Update hooks to latest versions
pre-commit autoupdate

# Skip hooks (use sparingly)
git commit --no-verify
```

---

## CI/CD Flow

### Development Workflow

```
1. Developer creates feature branch
   ↓
2. Makes changes locally
   ↓
3. Pre-commit hooks run (lint, format, type check)
   ↓
4. Pushes to GitHub
   ↓
5. CI pipeline runs (all checks)
   ↓
6. Creates pull request
   ↓
7. CI runs again on PR
   ↓
8. Code review + approval
   ↓
9. Merge to main
   ↓
10. Full CI + Docker build
```

### Release Workflow

```
1. Create release tag (v1.2.3)
   ↓
2. Push tag to GitHub
   ↓
3. Docker build workflow triggers
   ↓
4. Builds multi-platform images
   ↓
5. Pushes to ghcr.io
   ↓
6. Runs smoke tests
   ↓
7. Marks release as deployed
```

---

## Quality Gates

### All Pull Requests Must Pass:

✅ **Lint & Format**
- Ruff linting (no errors)
- Black formatting (consistent style)
- Import sorting (organized imports)

✅ **Type Checking**
- MyPy passes (no type errors)
- All functions have type hints

✅ **Security**
- Bandit passes (no high-severity issues)
- No secrets detected
- No known dependency vulnerabilities

✅ **Tests**
- All tests pass
- Coverage ≥ 80%
- No failing integration tests

### Main Branch Additional Requirements:

✅ **Docker Build**
- Image builds successfully
- Smoke tests pass
- Multi-platform support (amd64 + arm64)

---

## Environment Variables

### CI Pipeline

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `REDIS_URL` | Redis connection string | Yes |
| `TESTING` | Flag for test environment | Yes |

### Docker Build

| Variable | Description | Required |
|----------|-------------|----------|
| `GITHUB_TOKEN` | GitHub authentication | Auto-provided |
| `REGISTRY` | Container registry URL | Auto-set |

---

## Artifacts

### Generated Artifacts

**CI Pipeline:**
- `coverage-reports/` - HTML and XML coverage reports
- `security-reports/` - JSON security scan results

**Security Scan:**
- `dependency-scan-reports/` - Dependency vulnerability reports
- `bandit-report/` - Code security analysis

**Retention:** 90 days

### Accessing Artifacts

1. Go to workflow run in GitHub Actions
2. Scroll to "Artifacts" section
3. Download ZIP file

---

## Troubleshooting

### Common Issues

#### Tests Failing in CI but Pass Locally

**Cause:** Database state differences

**Solution:**
```bash
# Run with same PostgreSQL version
docker compose up db_test -d
pytest tests/ --cov=app
```

#### Docker Build Fails

**Cause:** Missing dependencies or incorrect Dockerfile

**Solution:**
```bash
# Test locally
docker build -t demeterai:test .
docker run --rm demeterai:test python --version
```

#### Coverage Below 80%

**Cause:** Insufficient test coverage

**Solution:**
```bash
# Find uncovered lines
pytest tests/ --cov=app --cov-report=term-missing

# Add tests for uncovered code
```

#### Type Check Failures

**Cause:** Missing type hints or incorrect types

**Solution:**
```bash
# Run locally with verbose output
mypy app/ --show-error-codes --pretty

# Add type hints where missing
```

---

## Performance Optimization

### Caching Strategy

1. **Pip Dependencies:** Cached by `actions/cache`
2. **Docker Layers:** Cached by BuildX
3. **Pre-commit Environments:** Cached by pre-commit.ci

### Parallel Execution

Jobs run in parallel:
- Lint (2-3 min)
- Type Check (3-4 min)
- Security (2-3 min)
- Tests (5-8 min)

Total time: ~8-10 min (not 15-18 min sequential)

---

## Security Best Practices

### Secrets Management

❌ **Never commit:**
- API keys
- Passwords
- Private keys
- Database credentials

✅ **Use GitHub Secrets:**
1. Go to Settings → Secrets and variables → Actions
2. Add secret
3. Reference in workflow: `${{ secrets.SECRET_NAME }}`

### Dependency Updates

Run weekly:
```bash
# Update pre-commit hooks
pre-commit autoupdate

# Check for security updates
pip-audit
safety check
```

---

## Monitoring & Alerts

### GitHub Actions Notifications

Configure in `.github/workflows/*.yml`:

```yaml
# Add notification step
- name: Notify on failure
  if: failure()
  uses: actions/github-script@v7
  with:
    script: |
      github.rest.issues.create({
        owner: context.repo.owner,
        repo: context.repo.repo,
        title: 'CI Failure: ${{ github.workflow }}',
        body: 'Workflow failed on commit ${{ github.sha }}'
      })
```

### Status Badges

Add to README.md:

```markdown
![CI](https://github.com/USERNAME/REPO/workflows/CI%20Pipeline/badge.svg)
![Security](https://github.com/USERNAME/REPO/workflows/Security%20Scan/badge.svg)
```

---

## Future Enhancements

### Planned Improvements

- [ ] Add performance benchmarking
- [ ] Deploy to staging environment
- [ ] Add end-to-end tests
- [ ] Implement blue-green deployments
- [ ] Add load testing
- [ ] Integrate with SonarQube
- [ ] Add dependency review action
- [ ] Implement automatic rollback

---

## Support

**Questions?** Check:
1. [GitHub Actions Documentation](https://docs.github.com/en/actions)
2. [Pre-commit Documentation](https://pre-commit.com/)
3. [Project README](../../README.md)

**Issues?** File a bug report in GitHub Issues.

---

**Last Updated:** 2025-10-21
**Maintained By:** DemeterAI Engineering Team
