# INVESTIGACIÓN: CARGA DE DATOS DE PRODUCCIÓN - RESUMEN EJECUTIVO

## ESTADO ACTUAL

```
warehouses: 0 (ESPERADO: 8)
storage_areas: 0 (ESPERADO: 8-10)
storage_locations: 12 (✅ FUNCIONA)
product_categories: 0 (ESPERADO: 5+)
product_states: 0 (ESPERADO: 11, HARDCODED)
product_families: 0 (ESPERADO: 20, HARDCODED)
products: 0 (ESPERADO: 5, HARDCODED)
storage_bin_types: 0 (ESPERADO: 4, HARDCODED)
storage_location_config: 0 (ESPERADO: 1+, NUEVO)
price_list: 0 (ESPERADO: 100+)
```

## ERRORES IDENTIFICADOS

### ERROR 1: AttributeError - PackagingCatalog.description NO EXISTE
**Ubicación**: `app/db/load_production_data.py` línea 1549
**Impacto**: price_list=0 (CRÍTICO)
**Causa**: El modelo NO tiene campo `description`

```python
# INCORRECTO
PackagingCatalog.description.ilike(f"%{maceta}%")  # ❌ NO EXISTE

# CORRECTO
PackagingCatalog.name.ilike(f"%{maceta}%")  # ✅ EXISTE
```

---

### ERROR 2: AttributeError - PackagingCatalog.code NO EXISTE
**Ubicación**: `app/db/load_production_data.py` línea 1557
**Impacto**: price_list=0 (CRÍTICO)
**Causa**: El modelo NO tiene campo `code`

```python
# INCORRECTO
PackagingCatalog(
    code=sku[:20] if sku else f"PKG{count:04d}",  # ❌ NO EXISTE
)

# CORRECTO
PackagingCatalog(
    sku=sku[:50] if sku else f"PKG{count:04d}",  # ✅ EXISTE
)
```

---

### ERROR 3: IntegrityError - Campos FK obligatorios faltantes
**Ubicación**: `app/db/load_production_data.py` línea 1556
**Impacto**: price_list=0 (CRÍTICO)
**Causa**: PackagingCatalog requiere 3 FKs que no se proporcionan

```
PackagingCatalog REQUIERE:
- packaging_type_id (FK NOT NULL) ❌ FALTA
- packaging_material_id (FK NOT NULL) ❌ FALTA
- packaging_color_id (FK NOT NULL) ❌ FALTA

ACTUALMENTE se crea sin estos campos → IntegrityError
```

---

### ERROR 4: Cascada de fallos en carga de GeoJSON
**Ubicación**: `app/db/load_production_data.py` línea 216-222
**Impacto**: storage_areas=0, storage_location_config=0 (ALTA)
**Causa**: Depende de warehouses existentes

```
load_warehouses() → 0 (falla)
  ↓ (warehouse needed as default)
load_storage_areas() → 0 (cascada)
  ↓ (cascada)
load_storage_location_config() → 0 (cascada)
```

---

### ERROR 5: Idempotencia silenciosa en datos hardcoded
**Ubicación**: `app/db/load_production_data.py` línea 820-1040
**Impacto**: product_states=0, storage_bin_types=0 (MEDIA)
**Causa**: Si datos ya existen, contador no se actualiza

```
En BD anterior:
- 11 ProductStates ya existen
- 4 StorageBinTypes ya existen

En ejecución actual:
- Se verifica existencia (SELECT ... WHERE code=...)
- Si existe → no se crea → contador=0
- Comportamiento correcto pero confuso en logs
```

---

## ARCHIVOS DE DATOS

### GeoJSON (✅ EXISTEN)
```
production_data/gps_layers/Exported 29 fields, 12 lines.geojson (1 línea comprimida)
├─ 8 Warehouses: Nave 1-8
├─ 8+ Storage Areas: Madres norte/sur, Tunnels 1-3, Sombráculos 1-4, Somb 1
└─ 12 Storage Locations: Canteros nave 1-8, Cantero somb 1-2, etc.

TAMBIÉN EXISTEN (fallback):
- naves.geojson (6286 líneas)
- canteros.geojson (11894 líneas)
- claros.geojson (49026 líneas)
```

### CSV - Product Categories (✅ EXISTE)
```
production_data/product_category/categories.csv (13KB)
production_data/product_category/categories_2.csv (78KB)

Formato: Sin header
- Columna 0: Tipo de producto (CACTUS, SUCULENTAS, etc.)
```

### CSV - Price List (✅ EXISTE)
```
production_data/price_list/price_list.csv (8.7KB)

Estructura:
- Fila 0-2: Headers
- Fila 3+: Datos
  - Columna 0: CATEGORIA (CACTUS, SUCULENTAS, etc.)
  - Columna 1: MACETA ("Rígida 5 cuadrada terracota")
  - Columna 2: PRECIO ("$950")
  - Columna 3: SKU ("C R5 T-1")

PROBLEMA: No tiene columnas para packaging_type_id o material_id
→ Hay que PARSEAR de la descripción de texto libre
```

---

## MODELOS Y ESTRUCTURA

### PackagingCatalog - Campos REALES
```python
id: INTEGER (PK)
packaging_type_id: INTEGER (FK, NOT NULL) ← REQUERIDO
packaging_material_id: INTEGER (FK, NOT NULL) ← REQUERIDO
packaging_color_id: INTEGER (FK, NOT NULL) ← REQUERIDO
sku: VARCHAR(50) (UNIQUE, NOT NULL) ← CORRECTO
name: VARCHAR(200) (NOT NULL) ← CORRECTO
volume_liters: NUMERIC (NULLABLE)
diameter_cm: NUMERIC (NULLABLE)
height_cm: NUMERIC (NULLABLE)
```

### PackagingCatalog - Campos que EL CÓDIGO ESPERA (INCORRECTOS)
```python
code: ❌ NO EXISTE
description: ❌ NO EXISTE
```

---

## SOLUCIONES REQUERIDAS

### Solución 1: Corregir referencias a campos inexistentes
```
Línea 1549: PackagingCatalog.description → PackagingCatalog.name
Línea 1557: code= → sku=
Línea 1558: description= → name=
```

### Solución 2: Crear helpers para parsing de CSV
```python
async def _extract_packaging_info(self, maceta_str: str) -> dict:
    """Extract type, size, color from "Rígida 5 cuadrada terracota"
    
    Returns: {
        'type': 'Rígida',
        'size': '5',
        'color': 'TERRACOTA'
    }
    """
    # Ver documento PRODUCTION_DATA_LOADER_FIXES.md para código completo
```

### Solución 3: Crear helpers para FK obligatorios
```python
async def _get_or_create_packaging_type(self, type_name: str) -> int:
async def _get_or_create_packaging_material(self, material_name: str) -> int:
async def _get_or_create_packaging_color(self, color_name: str) -> int:
    # Ver documento PRODUCTION_DATA_LOADER_FIXES.md para código completo
```

### Solución 4: Usar helpers en la creación de PackagingCatalog
```python
# Antes de crear:
pkg_info = self._extract_packaging_info(maceta)
type_id = await self._get_or_create_packaging_type(pkg_info['type'])
material_id = await self._get_or_create_packaging_material('PLASTICO')
color_id = await self._get_or_create_packaging_color(pkg_info.get('color'))

# Crear con TODOS los campos requeridos:
packaging = PackagingCatalog(
    packaging_type_id=type_id,        # ← AHORA INCLUIDO
    packaging_material_id=material_id, # ← AHORA INCLUIDO
    packaging_color_id=color_id,      # ← AHORA INCLUIDO
    sku=sku[:50] if sku else f"PKG{count:04d}",
    name=maceta[:200],
)
```

### Solución 5: Mejorar manejo de errores y logging
- Separar contadores para NUEVOS vs EXISTENTES
- Agregar logs explícitos en catch blocks
- Usar exc_info=True para stack traces

---

## DOCUMENTOS GENERADOS

1. **PRODUCTION_DATA_INVESTIGATION_SUMMARY.md** (ESTE)
   - Resumen ejecutivo para presentación rápida

2. **PRODUCTION_DATA_LOADER_ANALYSIS.md**
   - Análisis exhaustivo (7 partes, 20+ páginas)
   - Detalles técnicos completos

3. **PRODUCTION_DATA_LOADER_FIXES.md**
   - Soluciones concretas paso a paso
   - Código completo listo para copiar-pegar
   - Plan de testing

---

## IMPACTO

### Impacto en ML Pipeline
El loader fallido significa:
- ❌ Sin datos de GPS (warehouses, storage areas)
- ❌ Sin precios (price_list)
- ✅ Storage locations (12) SÍ se cargan
- ✅ Product states, families, products (HARDCODED) se cargan

**Resultado**: Pipeline parcialmente funcional pero sin datos de negocio.

### Impacto en Tests
- ❌ Tests de price_list fallarán (no hay datos)
- ❌ Tests de warehouse hierarchy fallarán (no hay datos)
- ⚠️ Tests de product_states/families pasarán (hardcoded)

---

## ESTIMACIÓN DE ESFUERZO

| Tarea | Tiempo | Dificultad |
|-------|--------|-----------|
| Corregir campos (description → name, code → sku) | 5 min | Trivial |
| Crear _extract_packaging_info() helper | 10 min | Fácil |
| Crear helpers para FK (type/material/color) | 15 min | Fácil |
| Integrar helpers en _load_pricing_entries() | 15 min | Fácil |
| Mejorar logging y manejo de errores | 15 min | Fácil |
| Testing y verificación | 30 min | Fácil |
| **TOTAL** | **90 min** | **FÁCIL** |

---

## PRÓXIMOS PASOS

1. Revisar documento detallado: `PRODUCTION_DATA_LOADER_ANALYSIS.md`
2. Revisar soluciones: `PRODUCTION_DATA_LOADER_FIXES.md`
3. Implementar cambios (90 minutos)
4. Ejecutar tests
5. Verificar en BD que todos los contadores sean > 0

---

## REFERENCIA RÁPIDA

### Campos que EXISTEN en PackagingCatalog:
- `id` (PK)
- `packaging_type_id` (FK)
- `packaging_material_id` (FK)
- `packaging_color_id` (FK)
- `sku` (UNIQUE)
- `name`
- `volume_liters`
- `diameter_cm`
- `height_cm`

### Campos que EL CÓDIGO USA (INCORRECTOS):
- `code` ❌ NO EXISTE
- `description` ❌ NO EXISTE

### Mapeo de correcciones:
| Incorrecto | Correcto |
|-----------|----------|
| `.description` | `.name` |
| `code=` | `sku=` |
| `description=` | `name=` |
| (falta) `packaging_type_id=` | (agregar) |
| (falta) `packaging_material_id=` | (agregar) |
| (falta) `packaging_color_id=` | (agregar) |

