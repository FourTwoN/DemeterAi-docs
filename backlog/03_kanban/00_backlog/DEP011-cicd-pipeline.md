# [DEP011] CI/CD Pipeline (GitHub Actions)

## Metadata

- **Epic**: epic-011-deployment
- **Sprint**: Sprint-03
- **Priority**: `high`
- **Complexity**: L (8 points)
- **Dependencies**: Blocked by [F008, F009, DEP001]

## Description

Implement complete CI/CD pipeline: lint, test, build, deploy on every commit to main.

## Acceptance Criteria

- [ ] **CI (Continuous Integration)**:
    - Lint with Ruff on every commit
    - Run pytest on every commit
    - Build Docker image
    - Push to Docker registry

- [ ] **CD (Continuous Deployment)**:
    - Run database migrations
    - Deploy to staging (on merge to develop)
    - Deploy to production (on merge to main)
    - Rollback on failure

- [ ] **Quality gates**:
    - Tests must pass (>80% coverage)
    - No lint errors
    - Security scan (Trivy for Docker images)

## Implementation

**.github/workflows/ci.yml:**

```yaml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: pip install ruff
      - name: Lint with Ruff
        run: ruff check app/

  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgis/postgis:18-3.3
        env:
          POSTGRES_PASSWORD: test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: pip install -e ".[dev]"
      - name: Run tests
        run: pytest --cov=app --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3

  build:
    needs: [lint, test]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build Docker image
        run: docker build -t demeterai:${{ github.sha }} .
      - name: Security scan
        run: |
          docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
            aquasec/trivy image demeterai:${{ github.sha }}
      - name: Push to registry
        run: |
          echo ${{ secrets.DOCKER_PASSWORD }} | docker login -u ${{ secrets.DOCKER_USERNAME }} --password-stdin
          docker push demeterai:${{ github.sha }}
```

**.github/workflows/deploy.yml:**

```yaml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to production
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.PROD_HOST }}
          username: ${{ secrets.PROD_USER }}
          key: ${{ secrets.PROD_SSH_KEY }}
          script: |
            cd /opt/demeterai
            docker-compose pull
            docker-compose up -d --no-deps api
            docker-compose exec -T api alembic upgrade head
```

## Testing

- Create PR → verify CI runs
- Merge PR → verify deploy runs
- Check production logs
- Test rollback procedure

---
**Card Created**: 2025-10-09
