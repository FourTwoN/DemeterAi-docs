# [F008] Ruff Configuration - Linting + Formatting

## Metadata
- **Epic**: epic-001-foundation.md
- **Sprint**: Sprint-00 (Week 1-2)
- **Status**: `backlog`
- **Priority**: `medium`
- **Complexity**: S (3 story points)
- **Area**: `foundation`
- **Assignee**: TBD
- **Dependencies**:
  - Blocks: [Quality gates for all cards]
  - Blocked by: [F001, F002, F003]

## Related Documentation
- **Conventions**: ../../backlog/00_foundation/conventions.md#code-formatting
- **Tech Stack**: ../../backlog/00_foundation/tech-stack.md#testing--quality

## Description

Configure Ruff 0.7.0 for automated linting and formatting with project-specific rules, excluding auto-generated files, and integration with pre-commit hooks.

**What**: Create `pyproject.toml` Ruff configuration with 100-character line length, Python 3.12 target, selected rule sets (E, F, I, N, W), and exclusions for migrations/generated code. Integrate with pre-commit hooks from F003.

**Why**: Ruff is 10-100× faster than Black+Flake8+isort combined. Automated formatting eliminates style debates. Linting catches common bugs before code review. Consistent style improves code readability.

**Context**: Team of 10 developers needs consistent code style. Manual formatting wastes time. Ruff combines linter (Flake8 replacement) and formatter (Black replacement) in one fast tool.

## Acceptance Criteria

- [ ] **AC1**: `pyproject.toml` contains Ruff configuration:
  ```toml
  [tool.ruff]
  line-length = 100
  target-version = "py312"

  [tool.ruff.lint]
  select = ["E", "F", "I", "N", "W", "UP", "B", "C4", "SIM"]
  ignore = ["E501"]  # Line too long (let formatter handle)

  [tool.ruff.format]
  quote-style = "double"
  indent-style = "space"
  ```

- [ ] **AC2**: Exclusions configured:
  ```toml
  [tool.ruff]
  exclude = [
      ".git",
      ".venv",
      "venv",
      "alembic/versions/*.py",
      "__pycache__",
      "build",
      "dist"
  ]
  ```

- [ ] **AC3**: Import sorting configured:
  ```toml
  [tool.ruff.lint.isort]
  known-first-party = ["app"]
  section-order = ["future", "standard-library", "third-party", "first-party", "local-folder"]
  ```

- [ ] **AC4**: Commands work:
  ```bash
  ruff check .          # Linting
  ruff check . --fix    # Auto-fix
  ruff format .         # Formatting
  ```

- [ ] **AC5**: Pre-commit integration (from F003):
  - Ruff check runs on every commit
  - Ruff format runs on every commit
  - Commits blocked if linting fails

- [ ] **AC6**: CI integration (for future):
  ```bash
  ruff check . --output-format=github  # GitHub annotations
  ```

## Technical Implementation Notes

### Architecture
- Layer: Foundation (Code Quality)
- Dependencies: Ruff 0.7.0, pre-commit (F003)
- Design pattern: Quality gate automation

### Code Hints

**pyproject.toml complete configuration:**
```toml
[tool.ruff]
line-length = 100
target-version = "py312"

exclude = [
    ".git",
    ".venv",
    "venv",
    "alembic/versions/*.py",
    "__pycache__",
    "build",
    "dist",
    ".pytest_cache",
    ".mypy_cache"
]

[tool.ruff.lint]
# Enable rule sets:
# E: pycodestyle errors
# F: Pyflakes
# I: isort
# N: pep8-naming
# W: pycodestyle warnings
# UP: pyupgrade
# B: flake8-bugbear
# C4: flake8-comprehensions
# SIM: flake8-simplify
select = ["E", "F", "I", "N", "W", "UP", "B", "C4", "SIM"]

ignore = [
    "E501",    # Line too long (let formatter handle)
    "B008",    # Do not perform function call in argument defaults
    "C901",    # Function is too complex (let developers judge)
    "E712",    # Comparison to True/False (SQLAlchemy uses this)
]

[tool.ruff.lint.per-file-ignores]
"__init__.py" = ["F401"]  # Unused imports OK in __init__.py
"alembic/env.py" = ["F401", "E402"]  # Alembic imports
"tests/**/*.py" = ["S101"]  # Allow assert in tests

[tool.ruff.lint.isort]
known-first-party = ["app"]
section-order = [
    "future",
    "standard-library",
    "third-party",
    "first-party",
    "local-folder"
]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
skip-magic-trailing-comma = false
line-ending = "auto"
```

**Usage examples:**
```bash
# Check all files
ruff check .

# Auto-fix issues
ruff check . --fix

# Format code
ruff format .

# Check specific file
ruff check app/services/stock_service.py

# Show all rules
ruff rule --all
```

### Testing Requirements

**Unit Tests**: N/A (configuration card)

**Integration Tests**:
- [ ] Test linting catches errors:
  ```python
  # Create test file with lint errors
  echo "import os; x=1;y=2" > test_lint.py
  ruff check test_lint.py
  # Expected: Errors found

  ruff check test_lint.py --fix
  # Expected: Auto-fixed
  ```

- [ ] Test formatting works:
  ```python
  # Create unformatted file
  echo "def foo(  x,y  ):\n    return x+y" > test_format.py
  ruff format test_format.py
  # Expected: Formatted with proper spacing
  ```

- [ ] Test pre-commit integration:
  ```bash
  # Create bad code
  echo "import os; x=1" > app/bad.py
  git add app/bad.py
  git commit -m "test"
  # Expected: Commit blocked by Ruff
  ```

**Test Command**:
```bash
# Test on all existing code
ruff check .
ruff format . --check  # Dry run
```

### Performance Expectations
- Linting: <2 seconds for entire codebase
- Formatting: <1 second for entire codebase
- Individual file: <100ms

## Handover Briefing

**For the next developer:**
- **Context**: This is the automated code quality gate - all code must pass Ruff before commit
- **Key decisions**:
  - Using Ruff (all-in-one) instead of Black+Flake8+isort (simpler, 10-100× faster)
  - 100-character line length (balance readability vs screen width)
  - Auto-fix enabled (Ruff can fix most issues automatically)
  - Excluding alembic/versions/ (auto-generated, don't lint)
  - SQLAlchemy-specific ignores (E712 for True/False comparisons)
- **Known limitations**:
  - Ruff doesn't replace all Flake8 plugins (some edge cases)
  - Formatting is opinionated (some developers prefer different styles)
  - Line length enforcement can break long URLs/strings
- **Next steps after this card**:
  - All new code automatically linted/formatted via pre-commit (F003)
  - CI/CD will run `ruff check` (Sprint 05)
  - Developers run `ruff format .` before committing
- **Questions to ask**:
  - Should we enable stricter rules? (e.g., type hints required)
  - Should we add Ruff to CI/CD as blocking? (Sprint 05)
  - Should we run Ruff on save in IDEs? (developer productivity)

## Definition of Done Checklist

- [ ] Code passes all tests (pytest)
- [ ] pyproject.toml configured with Ruff rules
- [ ] Ruff check works on entire codebase
- [ ] Ruff format works on entire codebase
- [ ] Pre-commit hook integration tested
- [ ] PR approved by 2+ reviewers
- [ ] Documentation updated (README.md with Ruff commands)
- [ ] All existing code passes Ruff checks

## Time Tracking
- **Estimated**: 3 story points
- **Actual**: TBD (fill after completion)
- **Started**: TBD
- **Completed**: TBD

---

**Card Created**: 2025-10-09
**Last Updated**: 2025-10-09
**Card Owner**: TBD (assign during sprint planning)
