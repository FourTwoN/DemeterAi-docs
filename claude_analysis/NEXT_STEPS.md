# 🚀 Próximos Pasos - Post Sprint 00

## Estado Actual

✅ Sprint 00 completado (12/12 cards, 53/65 pts)
✅ Infraestructura base lista
✅ Docker + PostgreSQL + Redis funcionando
✅ Tests, linting, type checking configurados

---

## Cómo Continuar

### Opción 1: Continuar Automáticamente (Recomendado)

Puedes pedirle al agente que continúe con Sprint 01:

```
"Continúa con Sprint 01. Empieza con los modelos de la jerarquía geoespacial (DB001-DB005)"
```

El agente:

1. Consultará al Scrum Master para obtener las cards de Sprint 01
2. Delegará al Team Leader card por card
3. Team Leader coordinará Python Expert + Testing Expert
4. Creará cada modelo SQLAlchemy según database/database.mmd
5. Generará migraciones Alembic
6. Escribirá tests completos
7. Hará commits granulares

---

### Opción 2: Revisar Primero (Recomendado para Producción)

Si quieres revisar el código antes de continuar:

```bash
# 1. Revisa la estructura
ls -la app/
ls -la tests/

# 2. Ejecuta los tests
pytest --cov=app

# 3. Verifica linting
ruff check .

# 4. Verifica types
mypy app/

# 5. Inicia Docker y prueba la API
docker compose up -d
curl http://localhost:8000/health
curl http://localhost:8000/docs

# 6. Revisa los logs
docker compose logs api

# 7. Cuando estés listo, pide continuar
```

---

### Opción 3: Sprint 01 Manual

Si prefieres implementar Sprint 01 manualmente:

#### Paso 1: Crear primer modelo (Warehouse)

```python
# app/models/warehouse.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Numeric, func
from geoalchemy2 import Geometry
from app.db.base import Base

class Warehouse(Base):
    __tablename__ = "warehouses"

    id = Column(Integer, primary_key=True)
    code = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # greenhouse|shadehouse|open_field|tunnel
    geojson_coordinates = Column(Geometry('POLYGON', srid=4326))
    centroid = Column(Geometry('POINT', srid=4326))
    area_m2 = Column(Numeric)  # Generated column
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
```

#### Paso 2: Importar en base.py

```python
# app/db/base.py
from app.db.base_class import Base
from app.models.warehouse import Warehouse  # noqa: F401
```

#### Paso 3: Generar migración

```bash
docker compose exec api alembic revision --autogenerate -m "add warehouse model"
```

#### Paso 4: Revisar y aplicar

```bash
# Revisar el archivo generado en alembic/versions/
docker compose exec api alembic upgrade head
```

#### Paso 5: Crear repositorio

```python
# app/repositories/warehouse_repository.py
from app.repositories.base import AsyncRepository
from app.models.warehouse import Warehouse

class WarehouseRepository(AsyncRepository[Warehouse]):
    pass
```

#### Paso 6: Crear tests

```python
# tests/models/test_warehouse.py
@pytest.mark.unit
async def test_warehouse_creation(db_session):
    warehouse = Warehouse(
        code="WH-001",
        name="Test Warehouse",
        type="greenhouse",
        active=True
    )
    db_session.add(warehouse)
    await db_session.commit()

    assert warehouse.id is not None
```

#### Paso 7: Repetir para las otras 27 tablas

---

## Recursos Clave

### Documentos de Referencia

- `SPRINT_00_HANDOFF.md` - Documento de transición completo
- `database/database.mmd` - Schema completo (SOURCE OF TRUTH)
- `backlog/00_foundation/architecture-principles.md` - Reglas de arquitectura
- `engineering_plan/database/README.md` - Diseño de base de datos

### Cards de Sprint 01

- **Ubicación**: `backlog/03_kanban/00_backlog/DB*.md` y `R*.md`
- **Total**: 63 cards (35 modelos + 28 repositorios)
- **Estimación**: 8-12 horas de ejecución con agentes

### Orden Sugerido de Implementación

**Fase 1: Geospatial (5 cards)**

1. DB001: Warehouse
2. DB002: StorageArea
3. DB003: StorageLocation
4. DB004: StorageBin
5. DB005: StorageBinType

**Fase 2: Products (9 cards)**

6. DB015: ProductCategory
7. DB016: ProductFamily
8. DB017: Product
9. DB018: ProductState
10. DB019: ProductSize
11. DB020: PackagingType
12. DB021: PackagingMaterial
13. DB022: PackagingColor
14. DB023: PackagingCatalog

**Fase 3: Stock (4 cards)**

15. DB007: StockMovement
16. DB008: StockBatch
17. DB009: MovementType enum
18. DB010: BatchStatus enum

**Fase 4: ML Pipeline (5 cards)**

19. DB011: S3Image (UUID PK - importante!)
20. DB012: PhotoProcessingSession
21. DB013: Detection (PARTITIONED)
22. DB014: Estimation (PARTITIONED)
23. DB026: Classification

**Fase 5: Config & Users (5 cards)**

24. DB006: User
25. DB024: StorageLocationConfig
26. DB025: DensityParameter
27. DB027: PriceList
28. DB028: ProductSampleImage

**Fase 6: Repositorios (28 cards)**
Crear un repositorio para cada modelo (R001-R028)

---

## Comandos Rápidos

```bash
# Ver estado del proyecto
docker compose ps
pytest --co -q

# Ver cards de Sprint 01
ls backlog/03_kanban/00_backlog/DB*.md | head -10

# Ver schema completo
cat database/database.mmd | head -100

# Iniciar desarrollo
docker compose up -d
docker compose logs -f api

# Ejecutar migración inicial (PostGIS)
docker compose exec api alembic upgrade head

# Verificar PostGIS instalado
docker compose exec db psql -U demeterai_user -d demeterai -c "SELECT PostGIS_Version();"
```

---

## Métricas de Éxito para Sprint 01

Al finalizar Sprint 01 deberías tener:

- ✅ 28 modelos SQLAlchemy creados
- ✅ 28 migraciones Alembic aplicadas
- ✅ 28 repositorios AsyncRepository
- ✅ 28 tablas en PostgreSQL
- ✅ Tests de modelos (≥80% coverage)
- ✅ Tests de repositorios (≥80% coverage)
- ✅ 0 errores de linting (ruff)
- ✅ 0 errores de type checking (mypy)

---

## Contacto

Si encuentras problemas o necesitas clarificaciones:

1. Revisa `SPRINT_00_HANDOFF.md`
2. Consulta `database/database.mmd` para schema
3. Revisa `engineering_plan/` para decisiones arquitectónicas
4. Consulta `backlog/00_foundation/` para estándares

---

**Generado**: 2025-10-13
**Estado**: ✅ LISTO PARA SPRINT 01
