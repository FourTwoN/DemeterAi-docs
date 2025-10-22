# Ruff Usage Guide - DemeterAI v2.0

## Overview

Ruff is a fast, all-in-one linter and formatter for Python, replacing Black, Flake8, isort, and more. It's 10-100x faster than traditional tools.

## Quick Start

```bash
# Check code for linting issues
ruff check .

# Auto-fix linting issues
ruff check . --fix

# Format code
ruff format .

# Check formatting without modifying files (dry run)
ruff format . --check
```

## Configuration

Ruff is configured in `pyproject.toml` under `[tool.ruff]`.

### Key Settings

- **Line length**: 100 characters
- **Target version**: Python 3.12
- **Quote style**: Double quotes
- **Indent style**: Spaces

### Enabled Rule Sets

- **E**: pycodestyle errors
- **F**: Pyflakes (undefined variables, unused imports)
- **I**: isort (import sorting)
- **N**: pep8-naming (naming conventions)
- **W**: pycodestyle warnings
- **UP**: pyupgrade (Python version upgrades)
- **B**: flake8-bugbear (common bugs)
- **C4**: flake8-comprehensions (list/dict comprehensions)
- **SIM**: flake8-simplify (code simplification)

### Exclusions

The following directories are excluded from linting:
- `.git`, `.venv`, `venv`
- `alembic/versions/*.py` (auto-generated migrations)
- `__pycache__`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`
- `build`, `dist`

### Ignored Rules

- **E501**: Line too long (formatter handles this)
- **B008**: Function call in argument defaults (FastAPI uses this)
- **C901**: Function too complex (developer judgment)
- **E712**: Comparison to True/False (SQLAlchemy uses this)
- **N818**: Exception naming (AppBaseException is intentional)

## Pre-commit Integration

Ruff runs automatically on every commit via pre-commit hooks.

### Install Pre-commit Hooks

```bash
pre-commit install
```

### Run Pre-commit Manually

```bash
# Run all hooks
pre-commit run --all-files

# Run only Ruff linter
pre-commit run ruff --all-files

# Run only Ruff formatter
pre-commit run ruff-format --all-files
```

### Skip Pre-commit (NOT recommended)

```bash
git commit --no-verify -m "commit message"
```

## Common Workflows

### Before Committing

```bash
# Format and fix issues
ruff format .
ruff check . --fix

# Check what would be fixed (dry run)
ruff check . --diff
```

### Fix Specific File

```bash
ruff check app/services/stock_service.py --fix
ruff format app/services/stock_service.py
```

### Check Only Modified Files

```bash
git diff --name-only --cached | grep '\.py$' | xargs ruff check
git diff --name-only --cached | grep '\.py$' | xargs ruff format --check
```

### Show All Available Rules

```bash
ruff rule --all
```

### Show Specific Rule Details

```bash
ruff rule F401  # Unused import
ruff rule E501  # Line too long
```

## CI/CD Integration (Future)

When CI/CD is implemented, add these checks:

```yaml
# .gitlab-ci.yml or .github/workflows/ci.yml
lint:
  script:
    - ruff check . --output-format=github
    - ruff format . --check
```

## IDE Integration

### VS Code

Install the official Ruff extension:
1. Install: `ms-python.ruff`
2. Add to `settings.json`:

```json
{
  "[python]": {
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.fixAll": true,
      "source.organizeImports": true
    },
    "editor.defaultFormatter": "ms-python.ruff"
  }
}
```

### PyCharm

1. Go to Settings > Tools > External Tools
2. Add new tool:
   - Name: Ruff Format
   - Program: `ruff`
   - Arguments: `format $FilePath$`
   - Working directory: `$ProjectFileDir$`

## Performance

Ruff is extremely fast:
- **Linting**: <2 seconds for entire codebase
- **Formatting**: <1 second for entire codebase
- **Individual file**: <100ms

## Migration from Other Tools

Ruff replaces:
- **Black** → `ruff format`
- **Flake8** → `ruff check` (E, F, W rules)
- **isort** → `ruff check` (I rules)
- **pyupgrade** → `ruff check` (UP rules)
- **flake8-bugbear** → `ruff check` (B rules)

## Troubleshooting

### Pre-commit Hook Fails

```bash
# Update hooks to latest version
pre-commit autoupdate

# Clear cache and reinstall
pre-commit clean
pre-commit install
```

### Ruff Not Found

```bash
# Reinstall Ruff
pip install ruff==0.7.0

# Verify installation
ruff --version
```

### Import Sorting Issues

If imports are not sorted correctly, check:
1. `known-first-party = ["app"]` is set in `pyproject.toml`
2. Run: `ruff check . --fix` to auto-organize imports

### Line Too Long Errors

Ruff ignores E501 (line too long) because the formatter handles it automatically. If you see this error, run `ruff format .` first.

## Best Practices

1. **Always run Ruff before committing**:
   ```bash
   ruff format . && ruff check . --fix
   ```

2. **Fix errors incrementally**: Use `--fix` to auto-fix most issues, then manually fix remaining ones.

3. **Don't ignore rules without reason**: Every ignored rule should have a comment explaining why.

4. **Use per-file ignores**: If a rule doesn't apply to specific files (e.g., `__init__.py`), use `[tool.ruff.lint.per-file-ignores]`.

5. **Keep configuration simple**: Only add exceptions when necessary.

## Example Output

### Successful Check

```bash
$ ruff check .
All checks passed!

$ ruff format .
19 files left unchanged
```

### With Issues

```bash
$ ruff check .
app/services/stock_service.py:42:5: F841 Local variable `result` is assigned to but never used
app/core/config.py:15:1: I001 Import block is un-sorted

Found 2 errors (1 fixed, 1 remaining).
```

## Additional Resources

- **Official Docs**: https://docs.astral.sh/ruff/
- **Rules Reference**: https://docs.astral.sh/ruff/rules/
- **VS Code Extension**: https://marketplace.visualstudio.com/items?itemName=charliermarsh.ruff
- **GitHub**: https://github.com/astral-sh/ruff

---

**Last Updated**: 2025-10-13
**Ruff Version**: 0.7.0
