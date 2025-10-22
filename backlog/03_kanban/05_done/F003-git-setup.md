# [F003] Git Setup - Pre-commit Hooks + .gitignore

## Metadata

- **Epic**: epic-001-foundation.md
- **Sprint**: Sprint-00 (Week 1-2)
- **Status**: `backlog`
- **Priority**: `high`
- **Complexity**: S (2 story points)
- **Area**: `foundation`
- **Assignee**: TBD
- **Dependencies**:
    - Blocks: [All cards requiring git commits]
    - Blocked by: [F001]

## Related Documentation

- **Git Best Practices**: ../../engineering_plan/development/README.md
- **Conventions**: ../../backlog/00_foundation/conventions.md
- **Template**: ../../backlog/04_templates/config-templates/.gitignore.template

## Description

Configure Git repository with pre-commit hooks enforcing code quality standards and comprehensive
.gitignore preventing accidental secret commits.

**What**: Set up pre-commit framework with hooks for Ruff (linting/formatting), mypy (type
checking), and secret detection. Create .gitignore covering Python, IDEs, secrets, and OS files.

**Why**: Pre-commit hooks act as the first quality gate, catching issues before code review.
Automated formatting ensures team consistency. .gitignore prevents accidental credential leaks (
critical for AWS keys, JWT secrets, database passwords).

**Context**: This is a foundational card that enables the team to work safely with Git. Without
proper .gitignore, developers risk committing `.env` files or API keys. Without pre-commit hooks,
code quality issues accumulate.

## Acceptance Criteria

- [ ] **AC1**: `.pre-commit-config.yaml` created with hooks:
    - `ruff` check (linting)
    - `ruff` format (formatting)
    - `mypy` type checking
    - `detect-secrets` (prevent credential commits)
    - `trailing-whitespace` removal
    - `end-of-file-fixer`

- [ ] **AC2**: `.gitignore` created covering:
    - Python: `__pycache__/`, `*.pyc`, `.pytest_cache/`, `.coverage`
    - Virtual environments: `venv/`, `.venv/`, `env/`
    - Secrets: `.env`, `.env.*`, `*.pem`, `*.key`
    - IDEs: `.vscode/`, `.idea/`, `*.swp`
    - OS: `.DS_Store`, `Thumbs.db`
    - Project: `uploads/`, `logs/`, `*.log`

- [ ] **AC3**: Pre-commit hooks install successfully:
  ```bash
  pre-commit install
  # Hooks should run on every commit
  ```

- [ ] **AC4**: Pre-commit hooks enforce quality:
    - Create test file with lint errors → commit blocked
    - Fix lint errors → commit succeeds
    - Attempt to commit `.env` file → blocked by detect-secrets

- [ ] **AC5**: `.gitignore` prevents sensitive files:
    - Create `.env` file → `git status` shows no changes
    - Create `.venv/` folder → ignored
    - Create `test.log` → ignored

## Technical Implementation Notes

### Architecture

- Layer: Foundation (Version Control)
- Dependencies: Git, pre-commit framework
- Design pattern: Quality gates at commit time

### Code Hints

**.pre-commit-config.yaml structure:**

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.7.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        additional_dependencies: [types-requests]

  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']
```

**.gitignore critical entries:**

```gitignore
# Secrets (CRITICAL)
.env
.env.*
!.env.example
*.pem
*.key
credentials.json

# Python
__pycache__/
*.py[cod]
*.so
.venv/
venv/

# Testing
.pytest_cache/
.coverage
htmlcov/

# Project-specific
uploads/
logs/
*.log
processed_images/
```

**Installation command:**

```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files  # Test on all existing files
```

### Testing Requirements

**Unit Tests**: N/A (infrastructure card)

**Integration Tests**:

- [ ] Test pre-commit blocks bad code:
  ```bash
  echo "import os; x=1" > test_bad_format.py
  git add test_bad_format.py
  git commit -m "test"
  # Expected: Commit blocked by ruff
  ```

- [ ] Test .gitignore works:
  ```bash
  echo "SECRET_KEY=abc123" > .env
  git status
  # Expected: .env not shown in untracked files
  ```

- [ ] Test detect-secrets:
  ```bash
  echo "AWS_SECRET_KEY=AKIAIOSFODNN7EXAMPLE" > config.py
  git add config.py
  git commit -m "test"
  # Expected: Blocked by detect-secrets
  ```

**Test Command**:

```bash
# Verify pre-commit works
pre-commit run --all-files

# Verify .gitignore
git status --ignored
```

### Performance Expectations

- Pre-commit hook runtime: <10 seconds for typical commit
- Ruff check: <2 seconds
- Detect-secrets: <3 seconds

## Handover Briefing

**For the next developer:**

- **Context**: This card establishes the quality gate pipeline - every commit must pass these checks
- **Key decisions**:
    - Using Ruff (all-in-one linter/formatter) instead of Black+Flake8+isort (simpler, faster)
    - Using detect-secrets for credential detection (industry standard)
    - Pre-commit hooks run on every commit (NOT push - faster feedback)
    - `.env.example` is NOT ignored (template for team)
- **Known limitations**:
    - Pre-commit hooks only run locally (CI/CD will duplicate checks)
    - Developers can bypass with `git commit --no-verify` (trust-based)
- **Next steps after this card**:
    - F004: Logging configuration (uses these quality standards)
    - F005: Exception taxonomy (uses these quality standards)
    - All future commits will run through these hooks
- **Questions to ask**:
    - Should we add additional hooks? (e.g., `black` for stricter formatting)
    - Should we block `--no-verify` commits? (policy decision)

## Definition of Done Checklist

- [ ] Code passes all tests (pytest)
- [ ] Pre-commit hooks installed and tested
- [ ] .gitignore tested with sample sensitive files
- [ ] PR approved by 2+ reviewers
- [ ] Documentation updated (README.md with git setup instructions)
- [ ] No console.log or print() statements (except in hooks themselves)
- [ ] All team members can run `pre-commit install` successfully

## Time Tracking

- **Estimated**: 2 story points
- **Actual**: TBD (fill after completion)
- **Started**: TBD
- **Completed**: TBD

---

**Card Created**: 2025-10-09
**Last Updated**: 2025-10-09
**Card Owner**: TBD (assign during sprint planning)
