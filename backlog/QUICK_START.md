# Quick Start Guide - DemeterAI v2.0

## Get Coding in 5 Minutes

**Target Audience**: New developers joining the project
**Time Required**: 5-10 minutes
**Prerequisites**: Docker installed, git configured

---

## Step 1: Clone & Setup (2 minutes)

```bash
# Clone repository
git clone https://github.com/your-org/demeterai-backend.git
cd demeterai-backend

# Create Python virtual environment
python3.12 -m venv venv
source venv/bin/activate  # Linux/Mac
# OR: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

---

## Step 2: Start Local Environment (2 minutes)

```bash
# Start database + Redis with Docker Compose
docker-compose up -d db redis

# Wait for PostgreSQL to be ready (30 seconds)
docker-compose logs -f db  # Watch until "database system is ready"
# Press Ctrl+C when ready

# Run database migrations
alembic upgrade head

# Seed test data (optional but recommended)
bash 06_database/seed-scripts/run_all_seeds.sh
```

---

## Step 3: Run Tests (1 minute)

```bash
# Run all tests
pytest

# Expected output:
# ==================== test session starts ====================
# collected 0 items (will increase as you add tests)
# ==================== no tests ran in 0.01s ====================
```

---

## Step 4: Start API Server (30 seconds)

```bash
# Start FastAPI development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Open browser: http://localhost:8000/docs
# You should see Swagger API documentation
```

---

## Step 5: Pick Your First Card (1 minute)

```bash
# Navigate to kanban board
cd ../DemeterDocs/backlog/03_kanban/01_ready/

# Pick a card (start with S or M size)
# Read card file (example):
cat F001-project-setup.md

# Move card to in-progress
mv 01_ready/F001-project-setup.md 02_in-progress/

# Assign yourself
# (edit card file, add your name to "Assignee" field)
```

---

## Verification Checklist

- [ ] PostgreSQL running (`docker ps` shows demeterai_db)
- [ ] Redis running (`docker ps` shows demeterai_redis)
- [ ] Database migrated (`alembic current` shows latest revision)
- [ ] Tests pass (`pytest` completes without errors)
- [ ] API server starts (`http://localhost:8000/docs` shows Swagger UI)
- [ ] Card selected and moved to in-progress

---

## What's Next?

### Read These Docs (30 minutes)

1. **Architecture**: `00_foundation/architecture-principles.md` - Clean Architecture rules
2. **Tech Stack**: `00_foundation/tech-stack.md` - PostgreSQL 18, Python 3.12, FastAPI
3. **Conventions**: `00_foundation/conventions.md` - Naming, formatting standards
4. **DoR/DoD**: `00_foundation/definition-of-ready.md` + `definition-of-done.md`

### Understand the System (1 hour)

5. **Database Schema**: `../../database/database.mmd` - 28 tables ERD
6. **Engineering Plan**: `../../engineering_plan/README.md` - Complete system design
7. **ML Pipeline Flow**: `../../flows/procesamiento_ml_upload_s3_principal/PIPELINE_OVERVIEW.md`

### Write Your First Code (4 hours)

8. **Pick a small card**: Start with S or M complexity (1-5 story points)
9. **Follow card template**: All cards have acceptance criteria, tech notes, test requirements
10. **Write tests first**: TDD encouraged (see `04_templates/test-templates/`)
11. **Submit PR**: Use `04_templates/pr-template.md`
12. **Get review**: 2+ approvals required

---

## Common Commands

### Development

```bash
# Run linter
ruff check .

# Run formatter
ruff format .

# Run type checker
mypy app/

# Run tests with coverage
pytest --cov=app --cov-report=html

# View coverage report
open htmlcov/index.html  # Mac
xdg-open htmlcov/index.html  # Linux
```

### Database

```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1

# Check current revision
alembic current
```

### Docker

```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# View logs
docker-compose logs -f db
docker-compose logs -f redis

# Rebuild after dependency changes
docker-compose build
```

---

## Troubleshooting

### Problem: PostgreSQL won't start

```bash
# Check if port 5432 is already in use
sudo lsof -i :5432

# Kill existing PostgreSQL process
sudo killall postgres

# Restart Docker Compose
docker-compose down
docker-compose up -d
```

### Problem: Tests fail with database errors

```bash
# Ensure test database exists
createdb demeterai_test

# Run migrations on test database
DATABASE_URL=postgresql://user:pass@localhost/demeterai_test alembic upgrade head
```

### Problem: Import errors

```bash
# Ensure virtual environment is activated
which python  # Should show path to venv/bin/python

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### Problem: Ruff not found

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Verify installation
ruff --version
```

---

## Getting Help

### Stuck on Setup?

1. Check `05_dev-environment/troubleshooting.md` for common issues
2. Ask in daily standup
3. Ping #backend-help channel (Slack)

### Unclear Architecture?

1. Read `00_foundation/architecture-principles.md`
2. Check `GLOSSARY.md` for terminology
3. Ask tech lead in sprint planning

### Card Blocked?

1. Document blocker in card file
2. Move card to `03_kanban/06_blocked/`
3. Raise in daily standup
4. Escalate if blocker >1 day

---

## Your First Week Goals

### Day 1: Setup & Onboarding

- ✅ Complete this quick start guide
- ✅ Read foundation docs (architecture, conventions, DoR/DoD)
- ✅ Attend team standup, introduce yourself

### Day 2: Architecture Deep Dive

- ✅ Review database schema (`../../database/database.mmd`)
- ✅ Understand ML pipeline flow
- ✅ Watch sprint planning (or recording)

### Day 3: First Card

- ✅ Pick S or M card from `03_kanban/01_ready/`
- ✅ Write failing test first (TDD)
- ✅ Implement feature
- ✅ Submit PR

### Day 4-5: Code Review & Learning

- ✅ Address PR feedback
- ✅ Review 2-3 other PRs (learn from team)
- ✅ Complete first card (move to Done)

### Week 1 Target: 8-15 story points

- Complete 2-3 cards (S or M size)
- Learn team workflow
- Ask lots of questions!

---

## Congratulations! 🎉

You're ready to start contributing to DemeterAI v2.0.

**Remember**:

- 🎯 Focus on finishing cards (WIP limits prevent overcommitment)
- 🧪 Write tests first (TDD saves time)
- 📚 Read card documentation (all acceptance criteria, tech notes included)
- 🤝 Ask for help when blocked (team collaboration > solo struggle)
- 🔄 Review others' code (learn from team, improve code quality)

**Welcome to the team!**

---

**Document Owner**: Onboarding Coordinator
**Last Updated**: 2025-10-09
**Feedback**: If steps unclear, update this guide (continuous improvement)
