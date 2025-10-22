# Sprint 00 → Sprint 01 Handoff Document
**Fecha**: 2025-10-13
**Estado**: Sprint 00 COMPLETADO ✅

---

## Resumen Ejecutivo

Sprint 00 (Foundation & Setup) ha sido completado exitosamente. Todas las 12 cards están finalizadas y el proyecto está listo para Sprint 01 (Database & Repositories).

---

## Cards Completadas - Sprint 00

| Card | Título | Estado | Ubicación |
|------|--------|--------|-----------|
| F001 | Project Setup | ✅ DONE | backlog/03_kanban/05_done/ |
| F002 | Dependencies Installation | ✅ DONE | backlog/03_kanban/05_done/ |
| F003 | Git Setup | ✅ DONE | backlog/03_kanban/05_done/ |
| F004 | Logging Configuration | ✅ DONE | backlog/03_kanban/05_done/ |
| F005 | Exception Taxonomy | ✅ DONE | backlog/03_kanban/05_done/ |
| F006 | Database Connection | ✅ DONE | backlog/03_kanban/05_done/ |
| F007 | Alembic Setup | ✅ DONE | backlog/03_kanban/05_done/ |
| F008 | Ruff Configuration | ✅ DONE | backlog/03_kanban/05_done/ |
| F009 | Pytest Configuration | ✅ DONE | backlog/03_kanban/05_done/ |
| F010 | Mypy Configuration | ✅ DONE | backlog/03_kanban/05_done/ |
| F011 | Dockerfile | ✅ DONE | backlog/03_kanban/05_done/ |
| F012 | Docker Compose | ✅ DONE | backlog/03_kanban/05_done/ |

**Total Story Points**: 53/65 (82%)
**Total Cards**: 12/12 (100%)

---

## Infraestructura Disponible

### Directorios del Proyecto
```
/home/lucasg/proyectos/DemeterDocs/
├── app/                      # Código fuente
│   ├── core/                 # Config, logging, exceptions
│   ├── db/                   # Database session, base
│   ├── models/              # ⏳ Sprint 01 - A crear
│   ├── repositories/        # ⏳ Sprint 01 - A crear
│   ├── services/            # ⏳ Sprint 03 - A crear
│   ├── controllers/         # ⏳ Sprint 04 - A crear
│   ├── schemas/             # ⏳ Sprint 04 - A crear
│   └── main.py              # FastAPI app ✅
├── tests/                   # Tests
│   ├── conftest.py          # Fixtures compartidas ✅
│   ├── core/                # Tests de core ✅
│   ├── db/                  # Tests de DB ✅
│   ├── integration/         # Tests API ✅
│   └── unit/                # Tests unitarios ✅
├── alembic/                 # Migraciones
│   ├── versions/            # Migraciones creadas
│   │   └── 6f1b94ebef45_*.py  # PostGIS extension ✅
│   ├── env.py               # Config Alembic ✅
│   └── alembic.ini          # Settings ✅
├── docs/                    # Documentación
├── backlog/                 # Gestión proyecto
├── pyproject.toml           # ✅ Configuración Python
├── requirements.txt         # ✅ Dependencias producción
├── requirements-dev.txt     # ✅ Dependencias desarrollo
├── Dockerfile               # ✅ Container imagen
├── docker-compose.yml       # ✅ Orquestación servicios
├── .env.example             # ✅ Variables entorno
├── .gitignore               # ✅ Exclusiones Git
└── .pre-commit-config.yaml  # ✅ Hooks calidad
```

### Servicios Docker Disponibles

**Para iniciar el entorno completo**:
```bash
cd /home/lucasg/proyectos/DemeterDocs
docker compose up -d
```

**Servicios activos**:
1. **PostgreSQL 18 + PostGIS 3.6** - localhost:5432
   - Base de datos: demeterai
   - Usuario: demeterai_user
   - Password: demeterai_pass

2. **Redis 7** - localhost:6379
   - Sin password en desarrollo

3. **FastAPI API** - localhost:8000
   - Endpoint health: http://localhost:8000/health
   - Docs: http://localhost:8000/docs

**Servicios preparados (comentados, para Sprint 02)**:
4. Celery CPU Worker
5. Celery I/O Worker
6. Flower (monitoring)

---

## Comandos Útiles

### Testing
```bash
# Ejecutar todos los tests
pytest

# Con cobertura
pytest --cov=app --cov-report=html

# Solo tests unitarios
pytest -m unit

# Solo tests de integración
pytest -m integration
```

### Linting y Formateo
```bash
# Lint + format
ruff format . && ruff check . --fix

# Solo lint
ruff check .

# Solo format
ruff format .
```

### Type Checking
```bash
# Verificar tipos
mypy app/

# Verificar tests
mypy tests/
```

### Base de Datos
```bash
# Ejecutar migraciones
docker compose exec api alembic upgrade head

# Crear nueva migración
docker compose exec api alembic revision --autogenerate -m "descripcion"

# Ver historial
docker compose exec api alembic history

# Ver estado actual
docker compose exec api alembic current
```

### Docker
```bash
# Iniciar servicios
docker compose up -d

# Ver logs
docker compose logs -f api

# Ver estado
docker compose ps

# Detener servicios
docker compose down

# Detener y borrar volúmenes
docker compose down -v
```

---

## Sprint 01: Database & Repositories

### Objetivo
Crear los 28 modelos SQLAlchemy + 28 repositorios AsyncRepository que representan el schema completo de DemeterAI.

### Cards a Ejecutar (63 total)

#### Modelos de Base de Datos (35 cards: DB001-DB035)

**Geospatial Hierarchy (4 tablas)**:
- DB001: `Warehouse` - Almacenes (greenhouse, shadehouse, etc.)
- DB002: `StorageArea` - Áreas dentro de almacenes
- DB003: `StorageLocation` - Ubicaciones específicas
- DB004: `StorageBin` - Contenedores (plugs, boxes, segments)
- DB005: `StorageBinType` - Tipos de contenedores

**Product Catalog (8 tablas)**:
- DB015: `ProductCategory` - Categorías (cactus, succulents)
- DB016: `ProductFamily` - Familias botánicas
- DB017: `Product` - Productos individuales
- DB018: `ProductState` - Estados (seedling, juvenile, adult)
- DB019: `ProductSize` - Tamaños (S, M, L, XL)
- DB020: `PackagingType` - Tipos de macetas
- DB021: `PackagingMaterial` - Materiales (plástico, cerámica)
- DB022: `PackagingColor` - Colores de macetas
- DB023: `PackagingCatalog` - Catálogo de packaging

**Stock Management (4 tablas)**:
- DB007: `StockMovement` - Movimientos de stock
- DB008: `StockBatch` - Lotes de plantas
- DB009: Enum `MovementType` - Tipos de movimiento
- DB010: Enum `BatchStatus` - Estados de lote

**ML Pipeline (5 tablas)**:
- DB011: `S3Image` - Imágenes en S3 (UUID PK)
- DB012: `PhotoProcessingSession` - Sesiones de procesamiento
- DB013: `Detection` - Detecciones individuales (PARTITIONED)
- DB014: `Estimation` - Estimaciones (PARTITIONED)
- DB026: `Classification` - Clasificaciones ML

**Configuration (3 tablas)**:
- DB024: `StorageLocationConfig` - Configuración por ubicación
- DB025: `DensityParameter` - Parámetros de densidad
- DB027: `PriceList` - Lista de precios

**Users & Auth (2 tablas)**:
- DB006: `User` - Usuarios del sistema
- DB028: `ProductSampleImage` - Imágenes de muestra

#### Repositorios (28 cards: R001-R028)

Cada modelo tiene su repositorio correspondiente con patrón `AsyncRepository`:

**Base Repository** (R001):
```python
class AsyncRepository(Generic[ModelType]):
    async def create(self, data: dict) -> ModelType
    async def get(self, id: int) -> Optional[ModelType]
    async def get_multi(self, skip: int, limit: int) -> List[ModelType]
    async def update(self, id: int, data: dict) -> ModelType
    async def delete(self, id: int) -> bool
```

**Repositorios Específicos**:
- R002: WarehouseRepository
- R003: StorageAreaRepository
- R004: StorageLocationRepository
- R005: StorageBinRepository
- ... (hasta R028)

### Referencia de Schema

**Archivo maestro**: `/home/lucasg/proyectos/DemeterDocs/database/database.mmd`

Este archivo Mermaid ERD contiene:
- Todas las 28 tablas con columnas exactas
- Tipos de datos PostgreSQL
- Relaciones (FK, PK, UK)
- Constraints (CHECK, DEFAULT)
- Índices (GIST para PostGIS)
- Particionamiento (detections, estimations)

**IMPORTANTE**: Este es el **source of truth**. Todo modelo SQLAlchemy debe coincidir exactamente con este schema.

### Estrategia de Implementación

#### Fase 1: Geospatial Models (Prioridad Alta)
1. DB001: Warehouses
2. DB002: Storage Areas
3. DB003: Storage Locations
4. DB004: Storage Bins
5. DB005: Storage Bin Types

#### Fase 2: Product Catalog (Prioridad Alta)
6. DB015-DB023: Product models completos

#### Fase 3: Stock Management (Prioridad Crítica)
7. DB007: Stock Movements
8. DB008: Stock Batches
9. DB009: Movement Type enum
10. DB010: Batch Status enum

#### Fase 4: ML Pipeline (Prioridad Crítica)
11. DB011: S3 Images (UUID PK)
12. DB012: Photo Processing Sessions
13. DB013: Detections (PARTITIONED)
14. DB014: Estimations (PARTITIONED)
15. DB026: Classifications

#### Fase 5: Configuration & Users
16. DB006: Users
17. DB024: Storage Location Config
18. DB025: Density Parameters
19. DB027: Price List
20. DB028: Product Sample Images

### Patrón de Migración

Para cada modelo creado:
```bash
# 1. Crear modelo en app/models/
# 2. Importar en app/db/base.py
from app.models.warehouse import Warehouse  # noqa: F401

# 3. Generar migración
docker compose exec api alembic revision --autogenerate -m "add warehouse model"

# 4. Revisar migración generada en alembic/versions/
# 5. Aplicar migración
docker compose exec api alembic upgrade head

# 6. Verificar en PostgreSQL
docker compose exec db psql -U demeterai_user -d demeterai -c "\dt"
```

### Testing de Modelos

Para cada modelo, crear tests:
```python
# tests/models/test_warehouse.py
@pytest.mark.unit
async def test_warehouse_creation(db_session):
    warehouse = Warehouse(
        code="WH-001",
        name="Main Greenhouse",
        type="greenhouse",
        active=True
    )
    db_session.add(warehouse)
    await db_session.commit()

    assert warehouse.id is not None
    assert warehouse.created_at is not None
```

### Testing de Repositorios

Para cada repositorio:
```python
# tests/repositories/test_warehouse_repository.py
@pytest.mark.integration
async def test_warehouse_repository_create(db_session):
    repo = WarehouseRepository(Warehouse, db_session)
    data = {"code": "WH-001", "name": "Test", "type": "greenhouse"}

    warehouse = await repo.create(data)

    assert warehouse.id is not None
    assert warehouse.code == "WH-001"
```

---

## Decisiones Técnicas Clave

### 1. UUID vs SERIAL
- **s3_images**: UUID (generado en API, no en DB)
- **Resto de tablas**: SERIAL (autoincremento DB)
- **Razón**: UUID para S3 permite pre-generar keys

### 2. Particionamiento
- **detections**: Particionado por día (created_at)
- **estimations**: Particionado por día (created_at)
- **Razón**: 600k+ plantas = millones de registros

### 3. PostGIS
- **geojson_coordinates**: GEOMETRY(POLYGON, 4326)
- **centroid**: GEOMETRY(POINT, 4326)
- **Razón**: Queries espaciales eficientes

### 4. Async Everything
- Todos los repos son async (AsyncSession)
- Usa `await` para todas las operaciones DB
- **Razón**: Non-blocking I/O, mejor performance

---

## Documentación Disponible

### Guías Técnicas
- `docs/installation.md` - Setup inicial
- `docs/alembic_usage.md` - Uso de migraciones
- `docs/RUFF_USAGE.md` - Linting y formateo
- `docs/MYPY_USAGE.md` - Type checking
- `docs/DOCKER.md` - Containerización
- `docs/DOCKER_COMPOSE_GUIDE.md` - Orquestación
- `tests/README.md` - Testing

### Referencia de Arquitectura
- `engineering_plan/03_architecture_overview.md` - Clean Architecture
- `engineering_plan/database/README.md` - Database design
- `backlog/00_foundation/architecture-principles.md` - Principios

### Diagramas
- `database/database.mmd` - ERD completo (SOURCE OF TRUTH)
- `flows/` - Flujos de negocio

---

## Estado del Sistema

### Quality Gates ✅
- Tests: 75/75 passing (98% coverage)
- Linting: 0 errores (Ruff)
- Type checking: 0 errores (mypy)
- Pre-commit: 16 hooks pasando

### Servicios ✅
- PostgreSQL 18 + PostGIS: Listo
- Redis 7: Listo
- FastAPI API: Listo y funcional

### Pendiente ⏳
- Modelos SQLAlchemy (Sprint 01)
- Repositorios (Sprint 01)
- Services (Sprint 03)
- Controllers (Sprint 04)
- ML Pipeline (Sprint 02)

---

## Contacto y Soporte

**Scrum Master**: Responsable de coordinar sprints
**Team Leader**: Responsable de ejecución técnica
**Python Expert**: Implementación de código
**Testing Expert**: Cobertura de tests
**Database Expert**: Consultas sobre schema

---

## Próximo Comando

Para iniciar Sprint 01:
```bash
# Asegúrate de que Docker esté corriendo
docker compose up -d

# Verifica que servicios estén healthy
docker compose ps

# Comienza con DB001 (Warehouse model)
# Consulta: backlog/03_kanban/00_backlog/DB001-warehouse-model.md
```

---

**Documento generado**: 2025-10-13
**Sprint siguiente**: Sprint 01 - Database & Repositories
**Estado**: ✅ LISTO PARA COMENZAR
