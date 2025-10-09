# Backlog Completion Guide
## How to Complete the Remaining ~225 Cards

**Created**: 2025-10-09
**Status**: Critical Path Foundation Complete, Remaining Cards Ready for Creation
**Completed Cards**: 17/~245 (7%)
**Remaining Cards**: ~228 (93%)

---

## ✅ What's Complete (Critical Path Foundation)

### Foundation (12 cards) - **COMPLETE**
- [x] F001-F012: All foundation cards (project setup, dependencies, git, logging, exceptions, DB connection, Alembic, Ruff, pytest, mypy, Dockerfile, docker-compose)

### Critical Database Models (4 cards) - **COMPLETE**
- [x] **DB011**: S3Images model (UUID primary key) ⚡
- [x] **DB012**: PhotoProcessingSession model ⚡
- [x] **DB013**: Detections model (partitioned) ⚡
- [x] **DB014**: Estimations model (partitioned) ⚡

### Critical ML Pipeline (1 card) - **COMPLETE**
- [x] **ML003**: SAHI Detection Service ⚡⚡⚡ **CRITICAL PATH**

### Sample Artifacts - **COMPLETE**
- [x] ML001-ML002: Model Singleton + YOLO Segmentation (samples)
- [x] epic-001, epic-007: Epic templates
- [x] ADR-001: ADR template
- [x] critical-path-v3.md: View template

**Total Complete**: 17 cards fully detailed, production-ready

---

## 📋 What Remains (Organized by Priority)

### **Priority 1: Critical Path (Must Complete First)**

#### ML Pipeline Cards (15 remaining)
```
ML004: Box/Plug Detection Service (5pts) - Direct YOLO for cajones
ML005: Band-Based Estimation Service (8pts) ⚡ CRITICAL PATH
ML006: Density-Based Estimation Service (5pts) - Fallback algorithm
ML007: GPS Localization Service (3pts) - GPS → storage_location
ML008: Mask Generation Service (3pts) - Soft masks around detections
ML009: Pipeline Coordinator Service (8pts) ⚡⚡ CRITICAL PATH
ML010: Image Processing Service (5pts) - Cropping, feathering
ML011: Visualization Service (5pts) - 5 overlay types
ML012: Aggregation Service (5pts) - Detections → StockMovements
ML013: Configuration Service (3pts) - Density params, location config
ML014: Floor Suppression Service (5pts) - HSV/Otsu filtering
ML015: Grouping Service (3pts) - Merge nearby detections
ML016: Calibration Service (5pts) - Auto-calibrate from detections
ML017: Metrics Service (3pts) - Compute averages, confidence dist
ML018: Error Recovery Service (3pts) - Warning states, retry logic
```

#### Celery Cards (8 cards)
```
CEL001: Celery App Setup (3pts) - Broker, result backend config
CEL002: Redis Connection Pool (2pts) - Connection management
CEL003: Worker Topology (5pts) - GPU (solo), CPU (prefork), IO (gevent)
CEL004: Chord Pattern Implementation (5pts) - Parent → children → callback
CEL005: ML Parent Task (5pts) ⚡ CRITICAL PATH - Spawns SAHI tasks
CEL006: ML Child Tasks (5pts) ⚡ CRITICAL PATH - Wraps ML services
CEL007: Callback Aggregation (3pts) - Collects results
CEL008: DLQ + Retry Logic (3pts) - Dead letter queue, exponential backoff
```

---

### **Priority 2: Supporting Infrastructure**

#### Database Models (19 remaining)
```
DB001: Warehouses model (1pt)
DB002: StorageAreas model (1pt)
DB003: StorageLocations model (1pt) - Blocks ML007
DB004: StorageBins model (1pt)
DB005: StorageBinTypes model (1pt)
DB006: Location relationships (1pt)
DB007: StockMovements model (2pts) - Blocks DB013
DB008: StockBatches model (2pts)
DB009: Movement types enum (1pt)
DB010: Batch status enum (1pt)
DB015-DB023: Product catalog models (9pts total)
DB024-DB025: Config models (4pts)
DB026: Classifications model (1pt) - Blocks DB013
DB027: PriceList model (2pts)
DB028: Users model (1pt)
DB029-DB032: Alembic migrations (7pts total)
```

#### Repository Cards (28 cards)
```
R001-R006: Location hierarchy repos (6pts)
R007-R010: Stock management repos (4pts)
R011: DetectionRepository (3pts) - asyncpg COPY bulk insert
R012: EstimationRepository (3pts)
R013-R014: Photo processing repos (4pts)
R015-R023: Product/packaging repos (9pts)
R024-R028: Config/user repos (5pts)
```

#### Service Cards (42 cards)
```
S001-S006: Location management services (6pts)
S007-S012: Stock movement services (6pts) - Manual init workflow
S013-S018: Photo processing services (6pts)
S019-S027: Product/packaging services (9pts)
S028-S035: Analytics services (8pts)
S036-S042: Configuration services (7pts)
```

---

### **Priority 3: API Layer**

#### Controller Cards (26 cards)
```
C001-C005: Stock management endpoints (5pts)
C006-C010: Photo upload + gallery (5pts)
C011-C015: Map/navigation endpoints (5pts)
C016-C020: Analytics endpoints (5pts)
C021-C026: Config + price management (6pts)
```

#### Schema Cards (20 cards)
```
SCH001-SCH010: Request schemas (Pydantic) (10pts)
SCH011-SCH020: Response schemas (Pydantic) (10pts)
```

---

### **Priority 4: Cross-Cutting Concerns**

#### Authentication Cards (6 cards)
```
AUTH001: JWT token service (3pts)
AUTH002: Password hashing (bcrypt) (2pts)
AUTH003: User authentication service (3pts)
AUTH004: Authorization middleware (3pts)
AUTH005: Refresh token logic (2pts)
AUTH006: Login/logout endpoints (2pts)
```

#### Observability Cards (10 cards)
```
OBS001: OpenTelemetry setup (3pts)
OBS002: OTLP exporter config (2pts)
OBS003: Trace instrumentation (3pts)
OBS004: Metrics instrumentation (3pts)
OBS005: Logging correlation (2pts)
OBS006: Prometheus metrics endpoint (2pts)
OBS007: Health check endpoint (1pt)
OBS008: Readiness check endpoint (1pt)
OBS009: Grafana dashboard JSON (2pts)
OBS010: Alert rules (2pts)
```

#### Deployment Cards (12 cards)
```
DEP001: Multi-stage Dockerfile (3pts)
DEP002: Docker Compose production (3pts)
DEP003: GPU worker Docker image (3pts)
DEP004: Health checks (2pts)
DEP005: Environment variable validation (2pts)
DEP006: Secrets management (2pts)
DEP007: Database migrations CI/CD (3pts)
DEP008: Container orchestration (3pts)
DEP009: Backup strategy (2pts)
DEP010: Monitoring setup (2pts)
DEP011: CI/CD pipeline (GitHub Actions) (5pts)
DEP012: Production deployment guide (2pts)
```

#### Testing Cards (15 cards)
```
TEST001: Test database setup (2pts)
TEST002: Pytest fixtures (3pts)
TEST003: Factory pattern for models (3pts)
TEST004: Integration test base (3pts)
TEST005: ML pipeline integration tests (5pts)
TEST006: API endpoint tests (5pts)
TEST007: Celery task tests (5pts)
TEST008: Repository layer tests (3pts)
TEST009: Service layer tests (5pts)
TEST010: Mock external services (3pts)
TEST011: Test coverage reporting (2pts)
TEST012: Performance benchmarks (3pts)
TEST013: Load testing (3pts)
TEST014: Smoke tests (2pts)
TEST015: End-to-end tests (5pts)
```

---

## 🎯 How to Create Remaining Cards

### Template Structure (Use F001, DB011, ML003 as References)

Every card MUST include:

```markdown
# [CARD_ID] Card Title

## Metadata
- **Epic**: epic-XXX-name.md
- **Sprint**: Sprint-XX
- **Status**: `backlog`
- **Priority**: `critical` | `high` | `medium` | `low`
- **Complexity**: XS/S/M/L/XL (1/2/3/5/8 story points)
- **Area**: `database` | `services` | `controllers` | `ml_processing` | etc.
- **Assignee**: TBD
- **Dependencies**:
  - Blocks: [CARD_ID1, CARD_ID2]
  - Blocked by: [CARD_ID3, CARD_ID4]

## Related Documentation
- **Engineering Plan**: ../../engineering_plan/...
- **Database ERD**: ../../database/database.mmd (if applicable)
- **Flows**: ../../flows/... (if applicable)

## Description

**What**: 2-3 sentences on what needs to be built
**Why**: Business/technical justification
**Context**: Background information, architectural decisions

## Acceptance Criteria

- [ ] **AC1**: Specific, testable condition
- [ ] **AC2**: Another specific condition
- [ ] **AC3**: Code structure/organization
- [ ] **AC4**: Performance expectation
- [ ] **AC5**: Error handling
- [ ] **AC6**: Integration with other components
- [ ] **AC7**: Documentation/comments

(3-7 acceptance criteria per card)

## Technical Implementation Notes

### Architecture
- Layer: (Database | Services | Controllers | etc.)
- Dependencies: Card dependencies
- Design pattern: (Repository, Service, etc.)

### Code Hints
```python
# Signature-level hints, NOT full implementations
# Just enough to guide the developer
```

### Testing Requirements

**Unit Tests**:
```python
# Test scenarios with examples
```

**Integration Tests**:
```python
# Integration scenarios
```

**Coverage Target**: ≥80% (or specify)

### Performance Expectations
- Timing benchmarks
- Resource usage
- Scalability notes

## Handover Briefing

**For the next developer:**
- **Context**: Why this card matters
- **Key decisions**: Architectural choices made
- **Known limitations**: What this doesn't solve
- **Next steps**: What cards depend on this
- **Questions to validate**: Checks for next developer

## Definition of Done Checklist

- [ ] Code written and follows patterns
- [ ] Tests pass (≥X% coverage)
- [ ] Linting passes (ruff check)
- [ ] PR reviewed (2+ approvals)
- [ ] Documentation updated
- [ ] Integration tested
- [ ] (Other specific criteria)

## Time Tracking
- **Estimated**: X story points
- **Actual**: TBD
- **Started**: TBD
- **Completed**: TBD

---

**Card Created**: 2025-10-09
**Last Updated**: 2025-10-09
**Card Owner**: TBD
```

---

## 📝 Card Creation Workflow

### Step 1: Choose Card to Create
Prioritize in this order:
1. **Critical Path**: ML005, ML009, CEL005-CEL007 (blocks everything)
2. **Supporting ML**: ML004, ML006-ML018
3. **Database**: DB001-DB010, DB015-DB032
4. **Repositories**: R001-R028
5. **Services**: S001-S042
6. **Controllers**: C001-C026
7. **Schemas**: SCH001-SCH020
8. **Everything else**

### Step 2: Research Card Context
- Read engineering_plan/ sections related to card
- Check database/database.mmd for data model
- Review flows/ for business logic
- Check context/past_chats_summary.md for decisions

### Step 3: Copy Template
- Use F001 for foundation cards
- Use DB011-DB014 for database models
- Use ML003 for ML services
- Adapt structure as needed

### Step 4: Fill in Metadata
- **Epic**: Match to correct epic file
- **Sprint**: Based on sprint-XX-name/ folders
- **Priority**: critical (blocks others) > high > medium > low
- **Complexity**: XS(1) S(2) M(3) L(5) XL(8) story points
- **Dependencies**: Review dependency graph

### Step 5: Write Description
- **What**: Clear, action-oriented (2-3 sentences)
- **Why**: Business value or technical necessity
- **Context**: Background, decisions, architectural fit

### Step 6: Define Acceptance Criteria
- 3-7 specific, testable conditions
- Include: functionality, performance, error handling, integration
- Use `- [ ]` checkbox format

### Step 7: Add Technical Notes
- **Architecture**: Layer, dependencies, pattern
- **Code Hints**: Signatures, key algorithms (NOT full code)
- **Testing**: Unit + integration scenarios
- **Performance**: Benchmarks, scalability notes

### Step 8: Write Handover Briefing
- Context for next developer
- Key decisions made in this card
- Known limitations
- Next steps (dependent cards)
- Questions to validate correctness

### Step 9: Complete DoD Checklist
- Code, tests, linting, PR, docs
- Specific to card type

### Step 10: Save and Validate
- Save as `backlog/03_kanban/00_backlog/[CARD_ID]-[name].md`
- Verify links work
- Add to epic's card list
- Update sprint backlog if pre-assigned

---

## 🔗 Dependency Management

### Global Dependency Rules
1. **Foundation → Database → Repositories → Services → Controllers**
2. **ML Pipeline**: DB (sessions/detections) → ML Services → Celery → Controllers
3. **No circular dependencies**: If A blocks B, B cannot block A

### How to Specify Dependencies

```markdown
**Dependencies**:
  - Blocks: [DB012, ML001, CEL005]  # Cards that need THIS card
  - Blocked by: [F007, DB011]       # Cards THIS card needs first
```

### Updating Dependencies
- When you create a card, check which cards it blocks
- Update those cards' `Blocked by` lists
- Update critical-path-v3.md if on critical path

---

## 🎓 Examples for Different Card Types

### Database Model Card (Pattern: DB011-DB014)
```
Use when: Creating SQLAlchemy models
Key sections:
- Model definition with all columns
- Relationships with other models
- Indexes for performance
- Alembic migration steps
- Partitioning if high-volume
- N+1 query prevention
```

### ML Service Card (Pattern: ML003)
```
Use when: Creating ML processing services
Key sections:
- Service class with clear methods
- Model singleton usage
- Performance benchmarks (CPU + GPU)
- Edge case handling
- Integration with ModelCache
- SAHI/YOLO library usage
```

### Repository Card (Pattern: R011-R012)
```
Use when: Creating repository layer
Key sections:
- Inherit from AsyncRepository
- CRUD methods
- Complex queries with eager loading
- Bulk insert optimization (asyncpg COPY)
- Transaction management
```

### Service Card (Pattern: S007-S012)
```
Use when: Creating business logic services
Key sections:
- Service class with injected repositories
- Service-to-Service communication (NOT Repo)
- Business rule validation
- Transaction boundaries
- Schema ↔ Model transformation
```

### Controller Card (Pattern: C001-C010)
```
Use when: Creating FastAPI endpoints
Key sections:
- Route definitions (@router.get/post)
- Pydantic schema validation
- Service layer calls
- HTTP status codes
- Error handling
- OpenAPI documentation
```

### Celery Card (Pattern: CEL001-CEL008)
```
Use when: Creating async tasks
Key sections:
- Task definitions (@app.task)
- Chord pattern (parent → children → callback)
- Worker pool configuration
- Retry logic with exponential backoff
- DLQ for permanent failures
```

---

## 📊 Progress Tracking

### After Creating Each Card
1. Move card file to `03_kanban/00_backlog/`
2. Update epic's card list
3. Update sprint backlog if sprint is known
4. Update global dependency map
5. Commit with format: `docs: add [CARD_ID] - [title]`

### Sprint Planning
1. Review all `00_backlog/` cards
2. Cards meeting DoR → move to `01_ready/`
3. During sprint planning → assign and move to `02_in-progress/`

---

## 🚀 Quick Start for Team

### For Scrum Master / Tech Lead
1. Assign critical path cards (ML005, ML009, CEL005-CEL007) to senior devs
2. Create epic files for epics 003-006, 008-017
3. Create sprint backlog files for Sprints 01-05
4. Setup ADRs for remaining decisions (ADR-002 through ADR-009)

### For Developers
1. Pick a card from critical path or your sprint assignment
2. Read this guide
3. Use F001, DB011, or ML003 as template
4. Fill in all sections
5. Submit PR for review
6. Repeat

---

## 📞 Support

**Questions about card structure?** → See examples (F001, DB011, ML003)
**Questions about dependencies?** → See `08_views/dependencies-global.md`
**Questions about sprints?** → See `01_sprints/sprint-XX/sprint-goal.md`
**Questions about epics?** → See `02_epics/epic-XXX.md`

---

**Document Owner**: Tech Lead + Scrum Master
**Last Updated**: 2025-10-09
**Next Review**: After Sprint 00 (adjust based on velocity)
