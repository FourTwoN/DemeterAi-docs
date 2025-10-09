# [F002] Install Dependencies & Create requirements.txt

## Metadata
- **Epic**: epic-001-foundation.md
- **Sprint**: Sprint-00
- **Status**: `backlog`
- **Priority**: `high`
- **Complexity**: S (3 points)
- **Assignee**: TBD
- **Dependencies**:
  - Blocks: [F003-F012]
  - Blocked by: [F001]

## Related Documentation
- **Tech Stack**: ../../backlog/00_foundation/tech-stack.md
- **Template**: ../../backlog/04_templates/config-templates/pyproject.toml.template

## Description

Install all production and development dependencies from pyproject.toml, verify no conflicts, and generate locked requirements.txt for deployment.

**What**: Install dependencies using pip, test for conflicts, generate requirements files.

**Why**: Locked dependencies prevent "works on my machine" issues. Requirements.txt enables reproducible builds in CI/CD and production.

## Acceptance Criteria

- [ ] All dependencies install without errors:
  ```bash
  pip install -e ".[dev]"
  ```
- [ ] No version conflicts reported
- [ ] Requirements.txt generated and committed:
  ```bash
  pip freeze > requirements.txt
  pip freeze | grep -E "(dev|test)" > requirements-dev.txt
  ```
- [ ] Virtual environment tested on clean machine
- [ ] Documentation updated with installation steps

## Technical Notes

**Installation command**:
```bash
python3.12 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -e ".[dev]"
```

**Verify versions match tech-stack.md**:
```bash
pip list | grep -E "(fastapi|sqlalchemy|celery|ultralytics)"
```

---

**Created**: 2025-10-09
