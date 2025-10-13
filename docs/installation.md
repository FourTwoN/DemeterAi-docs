# Installation Guide - DemeterAI v2.0 Backend

## Prerequisites

### System Requirements
- **Operating System**: Ubuntu 20.04+ / Debian 11+ / macOS 12+ / Windows WSL2
- **Python**: 3.12.x (required)
- **RAM**: Minimum 4GB (8GB+ recommended for ML operations)
- **Disk Space**: 5GB for dependencies + virtual environment

### Required Software
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y python3.12 python3.12-venv python3.12-dev \
                     build-essential git

# Verify Python version
python3.12 --version  # Should output: Python 3.12.x
```

---

## Quick Start

### 1. Clone Repository
```bash
git clone https://github.com/your-org/DemeterDocs.git
cd DemeterDocs
```

### 2. Create Virtual Environment
```bash
# Create venv with Python 3.12
python3.12 -m venv venv

# Activate virtual environment
source venv/bin/activate  # Linux/macOS
# OR
venv\Scripts\activate     # Windows
```

### 3. Upgrade pip
```bash
pip install --upgrade pip
```

### 4. Install Dependencies

**Option A: Full installation (recommended for development)**
```bash
# Install all dependencies (production + dev)
pip install -e ".[dev]"
```

**Option B: Production only**
```bash
# Install production dependencies only
pip install -e .
```

**Option C: From requirements files**
```bash
# Production dependencies
pip install -r requirements.txt

# Add development dependencies
pip install -r requirements-dev.txt
```

### 5. Verify Installation
```bash
# Check for conflicts
pip check

# Verify key packages
pip list | grep -E "(fastapi|sqlalchemy|celery|ultralytics)"
```

Expected output:
```
alembic                  1.14.0
celery                   5.4.0
fastapi                  0.118.2
opencv-python-headless   4.10.0.84
pydantic                 2.10.0
redis                    5.2.0
sqlalchemy               2.0.43
torch                    2.4.0
ultralytics              8.3.0
uvicorn                  0.34.0
```

---

## Installation Verification

### Test Imports
```bash
python -c "
import fastapi
import sqlalchemy
import celery
import ultralytics
import torch
print('All imports successful!')
print(f'PyTorch version: {torch.__version__}')
print(f'CUDA available: {torch.cuda.is_available()}')
"
```

### Run Tests
```bash
# Run all tests (once test suite is ready)
pytest tests/ -v
```

---

## Dependency Details

### Production Dependencies (109 packages)

**Core Framework:**
- fastapi==0.118.2
- uvicorn[standard]==0.34.0
- pydantic==2.10.0
- pydantic-settings==2.6.0

**Database:**
- sqlalchemy==2.0.43
- asyncpg==0.30.0
- alembic==1.14.0

**Async Processing:**
- celery==5.4.0
- redis==5.2.0

**Machine Learning (CPU-First):**
- ultralytics==8.3.0
- opencv-python-headless==4.10.0.84
- pillow==11.0.0
- torch==2.4.0 (CPU version)
- torchvision==0.19.0
- sahi==0.11.18

**Storage & Security:**
- boto3==1.35.0
- python-jose[cryptography]==3.3.0
- passlib[bcrypt]==1.7.4
- pybreaker==1.4.1

### Development Dependencies (9 packages)

**Testing:**
- pytest==8.3.0
- pytest-asyncio==0.24.0
- pytest-cov==6.0.0
- pytest-mock==3.14.0
- httpx==0.27.0

**Code Quality:**
- ruff==0.7.0
- mypy==1.13.0

---

## GPU Support (Optional)

By default, PyTorch installs the CPU version. For GPU acceleration (3-5× speedup):

### Prerequisites
- NVIDIA GPU (CUDA Compute Capability 7.0+)
- CUDA 12.1+ drivers installed

### Installation
```bash
# Uninstall CPU version
pip uninstall torch torchvision

# Install GPU version
pip install torch==2.4.0 torchvision==0.19.0 \
  --index-url https://download.pytorch.org/whl/cu121
```

### Verify GPU
```bash
python -c "
import torch
print(f'CUDA available: {torch.cuda.is_available()}')
print(f'CUDA version: {torch.version.cuda}')
print(f'GPU count: {torch.cuda.device_count()}')
if torch.cuda.is_available():
    print(f'GPU name: {torch.cuda.get_device_name(0)}')
"
```

---

## Clean Environment Test

To ensure reproducibility, test on a clean virtual environment:

```bash
# Remove existing venv
deactivate
rm -rf venv

# Create fresh venv
python3.12 -m venv venv
source venv/bin/activate

# Install from requirements
pip install --upgrade pip
pip install -r requirements.txt

# Verify
pip check
python -c "import fastapi, sqlalchemy, celery, ultralytics; print('Success!')"
```

---

## Troubleshooting

### Issue: "No module named 'app'"
**Solution**: Install in editable mode
```bash
pip install -e .
```

### Issue: "opencv-python-headless version not found"
**Solution**: The exact build number (4.10.0.84) is required. Check available versions:
```bash
pip index versions opencv-python-headless
```

### Issue: "CUDA out of memory" (GPU only)
**Solution**: Reduce batch size or use CPU:
```python
model = YOLO('yolov11m.pt')
model.to('cpu')  # Force CPU inference
```

### Issue: "Permission denied" on Linux
**Solution**: Don't use sudo with pip in venv:
```bash
# Wrong
sudo pip install -r requirements.txt

# Correct
pip install -r requirements.txt
```

---

## Directory Structure

```
DemeterDocs/
├── venv/                      # Virtual environment (gitignored)
├── app/                       # Application code
│   ├── __init__.py
│   ├── main.py               # FastAPI entry point
│   ├── controllers/          # API endpoints
│   ├── services/             # Business logic
│   ├── repositories/         # Database access
│   ├── models/               # SQLAlchemy models
│   └── schemas/              # Pydantic schemas
├── tests/                    # Test suite
├── docs/                     # Documentation
├── pyproject.toml           # Project metadata & dependencies
├── requirements.txt         # Locked production dependencies
├── requirements-dev.txt     # Locked dev dependencies
└── requirements-full.txt    # All dependencies (backup)
```

---

## Next Steps

After successful installation:

1. **Configure Environment**: Copy `.env.example` to `.env` (when available)
2. **Database Setup**: Run migrations `alembic upgrade head` (when ready)
3. **Run Development Server**: `uvicorn app.main:app --reload` (when main.py implemented)
4. **Run Tests**: `pytest tests/ -v --cov` (when tests exist)

---

## Reference

- **Tech Stack Documentation**: `/backlog/00_foundation/tech-stack.md`
- **Engineering Plan**: `/engineering_plan/README.md`
- **Dependency Card**: `/backlog/03_kanban/02_in-progress/F002-dependencies.md`

---

**Last Updated**: 2025-10-13
**Tested On**: Ubuntu 22.04, Python 3.12.4
**Total Dependencies**: 118 packages (109 production + 9 dev)
