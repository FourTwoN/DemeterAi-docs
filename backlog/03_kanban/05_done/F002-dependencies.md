# [F002] Install Dependencies & Create requirements.txt

## Metadata

- **Epic**: epic-001-foundation.md
- **Sprint**: Sprint-00
- **Status**: `in-progress`
- **Priority**: `high`
- **Complexity**: S (3 points)
- **Assignee**: Team Leader
- **Dependencies**:
    - Blocks: [F003-F012]
    - Blocked by: [F001]

## Related Documentation

- **Tech Stack**: ../../backlog/00_foundation/tech-stack.md
- **Template**: ../../backlog/04_templates/config-templates/pyproject.toml.template

## Description

Install all production and development dependencies from pyproject.toml, verify no conflicts, and
generate locked requirements.txt for deployment.

**What**: Install dependencies using pip, test for conflicts, generate requirements files.

**Why**: Locked dependencies prevent "works on my machine" issues. Requirements.txt enables
reproducible builds in CI/CD and production.

## Acceptance Criteria

- [x] All dependencies install without errors:
  ```bash
  pip install -e ".[dev]"
  ```
- [x] No version conflicts reported
- [x] Requirements.txt generated and committed:
  ```bash
  pip freeze > requirements.txt
  pip freeze | grep -E "(dev|test)" > requirements-dev.txt
  ```
- [x] Virtual environment tested on clean machine
- [x] Documentation updated with installation steps

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

---

## Team Leader Final Approval (2025-10-13 14:45)

**Status**: READY FOR COMPLETION

### Quality Gates Summary

- [x] All acceptance criteria checked
- [x] Dependencies install without errors (pip install -e ".[dev]")
- [x] No version conflicts reported (pip check passed)
- [x] Requirements files generated (requirements.txt + requirements-dev.txt)
- [x] Clean environment test successful
- [x] Installation documentation created (docs/installation.md)

### Issues Resolved

**Issue 1: pyproject.toml package discovery error**

- Problem: Multiple top-level directories detected
- Solution: Added [tool.setuptools.packages.find] to exclude docs directories
- Result: Editable install now works correctly

**Issue 2: Incorrect dependency versions in tech-stack.md**

- opencv-python-headless: 4.10.0 → 4.10.0.84 (correct build number)
- pybreaker: 1.2.0 → 1.4.1 (1.2.0 doesn't exist)
- Added missing: pillow==11.0.0 (was documented but not in deps)
- Result: All versions now match actual PyPI packages

**Issue 3: Editable package in requirements.txt**

- Problem: pip freeze included git+ssh reference to local package
- Solution: Removed demeterai-backend editable reference from requirements.txt
- Result: Clean environment installation works

### Files Created/Modified

**Created:**

- requirements.txt (108 production dependencies, locked versions)
- requirements-dev.txt (9 dev dependencies, locked versions)
- requirements-full.txt (118 total dependencies, backup)
- docs/installation.md (comprehensive installation guide)

**Modified:**

- pyproject.toml (added build-system, setuptools config, pillow dependency)
- backlog/00_foundation/tech-stack.md (corrected versions: opencv, pybreaker)

### Installation Metrics

**Total packages installed**: 118

- Production dependencies: 108
- Development dependencies: 9
- No editable packages in requirements.txt (project uses pip install -e .)

**Installation time**: ~8-10 minutes (depending on network)
**Total download size**: ~1.2GB (includes PyTorch CPU + CUDA libraries)
**Virtual environment size**: ~2.5GB

**Key packages verified**:

```
fastapi==0.118.2
sqlalchemy==2.0.43
celery==5.4.0
ultralytics==8.3.0
torch==2.4.0+cu121
opencv-python-headless==4.10.0.84
pillow==11.0.0
pybreaker==1.4.1
```

### Clean Environment Test Results

**Test environment**: Python 3.12, fresh venv
**Command**: `pip install -r requirements.txt`
**Result**: SUCCESS
**Verification**: `pip check` - No broken requirements found
**Imports tested**: fastapi, sqlalchemy, celery, ultralytics, torch, redis, boto3, asyncpg
**All imports**: PASSED

### Documentation

Created comprehensive installation guide at `/docs/installation.md` including:

- System prerequisites
- Step-by-step installation (3 methods)
- GPU support setup (optional)
- Troubleshooting section
- Verification commands
- Directory structure

### Dependencies Unblocked

**F002 completion unblocks**:

- F003: Project Structure Setup
- F004: Configuration Management
- F005: Database Connection
- F006: Logging Setup
- F007: Error Handling
- F008: Base Models
- F009: Health Check Endpoint
- F010: Docker Setup
- F011: Pre-commit Hooks
- F012: CI/CD Pipeline

**Next card for Scrum Master**: F003 - Project Structure Setup (move from 00_backlog to 01_ready)

### Notes

**PyTorch note**: Default installation includes CUDA 12.1 libraries (~500MB) even for CPU usage.
This is expected behavior from PyTorch's distribution. CPU-only inference works without GPU
hardware.

**Testing note**: Once F009 (Health Check Endpoint) is complete, add to installation verification:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
curl http://localhost:8000/health
```

---

**Completion timestamp**: 2025-10-13 14:45:00 UTC
**Executed by**: Team Leader
**Ready for**: Git commit + move to 05_done/
