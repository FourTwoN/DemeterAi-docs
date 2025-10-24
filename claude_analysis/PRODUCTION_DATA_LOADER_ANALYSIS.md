# INVESTIGACIÓN EXHAUSTIVA: CARGA DE DATOS DE PRODUCCIÓN FALLIDA

## RESUMEN EJECUTIVO

Se encontraron MÚLTIPLES ERRORES CRÍTICOS en el loader de datos que explican por qué casi ningún dato se carga:

1. **ERROR PRINCIPAL**: `PackagingCatalog.description` NO EXISTE en el modelo
2. **FALTA DE CAMPOS REQUERIDOS**: `PackagingCatalog` carece de `code`, `packaging_type_id`, etc.
3. **PROBLEMAS DE DEPENDENCIAS**: Product states y families no se cargan correctamente
4. **ARCHIVOS DE DATOS**: Existen pero el loader tiene lógica incorrecta

---

## PARTE 1: ANÁLISIS DEL MODELO PackagingCatalog

### ¿Qué campos tiene REALMENTE?
```
id: INTEGER (PK)
packaging_type_id: INTEGER (FK) - REQUERIDO
packaging_material_id: INTEGER (FK) - REQUERIDO
packaging_color_id: INTEGER (FK) - REQUERIDO
sku: VARCHAR(50) - REQUERIDO, UNIQUE
name: VARCHAR(200) - REQUERIDO
volume_liters: NUMERIC(10,2) - NULLABLE
diameter_cm: NUMERIC(10,2) - NULLABLE
height_cm: NUMERIC(10,2) - NULLABLE
```

### ¿Qué campo NO existe pero se usa en el código?
**`description` - NO EXISTE**

### Ubicación del error en load_production_data.py:

**LÍNEA 1549**: Query que falla
```python
stmt = select(PackagingCatalog).where(
    PackagingCatalog.description.ilike(f"%{maceta}%")  # ❌ NO EXISTE
)
```

**LÍNEAS 1556-1559**: Creación que falla
```python
packaging = PackagingCatalog(
    code=sku[:20] if sku else f"PKG{count:04d}",      # ❌ NO EXISTE
    description=maceta[:200],                           # ❌ NO EXISTE
)
```

### CAMPOS REQUERIDOS QUE FALTAN EN LA CREACIÓN:
- `packaging_type_id` (REQUERIDO, FK) ❌
- `packaging_material_id` (REQUERIDO, FK) ❌
- `packaging_color_id` (REQUERIDO, FK) ❌
- `sku` (REQUERIDO, UNIQUE) ❌

Actualmente intentas crear PackagingCatalog sin estos campos, lo que causará:
```
IntegrityError: NOT NULL constraint failed: packaging_catalog.packaging_type_id
```

---

## PARTE 2: ANÁLISIS DE ARCHIVOS DE DATOS DE PRODUCCIÓN

### GeoJSON - GPS Layers
✅ **EXISTEN** estos archivos:
1. `/home/lucasg/proyectos/DemeterDocs/production_data/gps_layers/naves.geojson` (6286 líneas)
2. `/home/lucasg/proyectos/DemeterDocs/production_data/gps_layers/canteros.geojson` (11894 líneas)
3. `/home/lucasg/proyectos/DemeterDocs/production_data/gps_layers/claros.geojson` (49026 líneas)
4. `/home/lucasg/proyectos/DemeterDocs/production_data/gps_layers/Exported 29 fields, 12 lines.geojson` (1 línea = JSON minificado con 12 features)

**Estado**: El loader usa "Exported 29 fields..." como fuente principal (fallback a otros). Este archivo contiene:
- 8 Warehouses (Nave 1-8) ✅
- 8 Storage Areas (Madres norte/sur, Sombráculos, Tunnels) ✅
- 12 Storage Locations (Canteros) ✅

El loader debería FUNCIONAR para warehouses, pero reporta 0 cargados.

### Categorías de Productos - CSV
✅ **EXISTEN**:
1. `/home/lucasg/proyectos/DemeterDocs/production_data/product_category/categories.csv` (13KB)
2. `/home/lucasg/proyectos/DemeterDocs/production_data/product_category/categories_2.csv` (78KB)

Formato: CSV sin header, columna 0 = tipo de producto (SUCCULENT, CACTUS, etc.)

### Lista de Precios - CSV
✅ **EXISTE**:
`/home/lucasg/proyectos/DemeterDocs/production_data/price_list/price_list.csv` (8.7KB)

Estructura (después de 3 filas de header):
```
Columna 0: CATEGORIA (CACTUS, SUCULENTAS, etc.)
Columna 1: MACETA (Descripción - "Rígida 5 cuadrada terracota")
Columna 2: PRECIO (string con $, ej: "$950")
Columna 3: SKU (Código de producto)
...
```

---

## PARTE 3: PROBLEMAS IDENTIFICADOS

### Problema 1: PackagingCatalog.description (CRÍTICO)
**Ubicación**: `load_production_data.py` líneas 1549 y 1558

**Síntomas**:
```
AttributeError: type object 'PackagingCatalog' has no attribute 'description'
```

**Raíz**: El código intenta usar un campo que NO existe en el modelo.

**Impacto**: 
- La carga de price_list falla completamente
- PackagingCatalog nunca se crea
- price_list = 0

---

### Problema 2: PackagingCatalog creado incorrectamente (CRÍTICO)
**Ubicación**: `load_production_data.py` líneas 1556-1559

**Código actual (INCORRECTO)**:
```python
packaging = PackagingCatalog(
    code=sku[:20] if sku else f"PKG{count:04d}",  # ❌ NO EXISTE
    description=maceta[:200],                      # ❌ NO EXISTE
)
```

**Campos faltantes (REQUERIDOS)**:
- `packaging_type_id` - ¿De dónde obtenerlo? NO ESTÁ EN EL CSV
- `packaging_material_id` - ¿De dónde obtenerlo? NO ESTÁ EN EL CSV
- `packaging_color_id` - ¿De dónde obtenerlo? SE PUEDE EXTRAER DEL TEXT "maceta"
- `sku` - DEBE VENIR DEL CSV O GENERARSE (está en columna 3)
- `name` - DEBE VENIR DE "maceta" (columna 1)

**Problema**: El CSV de price_list NO TIENE columnas para packaging_type_id o material_id.
Solo tiene descriptions de texto libre como "Rígida 5 cuadrada terracota" que hay que parsear.

---

### Problema 3: Almacenamiento del estado de carga (CRÍTICO)
**Ubicación**: `load_production_data.py` líneas 70-81 y 1612-1643

**Síntoma**: Los contadores muestran 0 para casi todo.

**Análisis del load_all_async()**:
```python
await self.load_warehouses()           # Reporta 0 (debería ser 8)
await self.load_storage_areas()        # Reporta 0 (debería ser 8-10)
await self.load_storage_locations()    # Reporta 12 ✅ (¡Esto funciona!)
await self.load_product_categories()   # Reporta 0 (debería ser 5+ del CSV)
await self.load_product_states()       # Reporta 0 (HARDCODED, debería cargar 11)
await self.load_product_families()     # Reporta 0 (HARDCODED, necesita categories)
await self.load_products()             # Reporta 0 (HARDCODED, necesita families)
await self.load_storage_bin_types()    # Reporta 0 (HARDCODED, debería cargar 4)
await self.load_storage_location_config() # Reporta 0 (necesita products)
await self.load_price_list()           # Reporta 0 (CSV parsing falla)
```

¿Por qué storage_locations (12) sí funciona pero los demás no?
- Probablemente es el último que se ejecutó antes de que algo fallara
- O hay diferencias en el manejo de errores

---

### Problema 4: Orden de dependencias incorrecto
**Ubicación**: `load_all_async()` línea 1633-1643

**Dependencias reales**:
```
load_product_categories()           # Necesita CSV
  ↓
load_product_families()             # Necesita categorías (product_categories_id)
  ↓
load_products()                     # Necesita families
  ↓
load_storage_location_config()      # Necesita products + storage_locations
```

**Orden actual**: CORRECTO ✅

**Pero hay problemas**:
1. `load_product_categories()` carece de manejo de errores explícito
2. Si falla, las siguientes también fallarán silenciosamente
3. No hay rollback explícito entre funciones

---

## PARTE 4: DETALLES DE ERRORES ESPECÍFICOS

### Error A: Warehouses = 0
**Esperado**: 8 (Nave 1-8 del GeoJSON)
**Obtenido**: 0

**Ubicación**: `load_production_data.py` líneas 87-143

**Posibles causas**:
1. Archivo GeoJSON no se procesa correctamente
2. `_parse_warehouse_feature()` filtra incorrectamente
3. Falla silenciosa en línea 127-130 (try-except sin log visible)

**Análisis del código**:
```python
# Línea 162-165
if "nave" not in name.lower() or "cantero" in name.lower():
    return None
```

El GeoJSON tiene:
- "Nave 1", "Nave 2", ... "Nave 8" ✅ (son naves)
- "Nave 5 norte", "Nave 5 sur" ❌ (tienen "norte/sur" pero el código no filtra por eso)

¿Problema?: No, el código incluye "Nave 5 norte" como warehouse. Pero el ERD dice que estos son STORAGE AREAS, no warehouses.

---

### Error B: Storage Areas = 0
**Esperado**: 8-10 (Madres, Tunnels, Sombráculos)
**Obtenido**: 0

**Ubicación**: `load_production_data.py` líneas 192-277

**Análisis**:
1. Línea 216-222: Obtiene el primer warehouse (default_warehouse)
2. Si no hay warehouses (porque cargaron 0), devuelve 0
3. Esto es una cascada de errores: si warehouses fallan, storage_areas también

---

### Error C: Product States = 0 (HARDCODED, debería funcionar)
**Esperado**: 11 estados
**Obtenido**: 0

**Ubicación**: `load_production_data.py` líneas 925-1041

**Análisis**:
- Línea 1020-1037: Loop para crear product_states
- Línea 1023-1025: SELECT para verificar si existe
- Línea 1027-1030: Si no existe, crea uno
- Línea 1038: await self.session.commit()

**Probable causa**: Todos los 11 estados ya existen en la DB (de ejecuciones previas).
Esto es CORRECTO (idempotent), pero los contadores no se actualizan.

**Verificar**: ¿Hay product_states en la BD?
```sql
SELECT COUNT(*) FROM product_states;
```

---

### Error D: Storage Bin Types = 0 (HARDCODED, debería funcionar)
**Esperado**: 4 tipos (SEGMENTO, PLUGS, ALMACIGOS, CAJONES)
**Obtenido**: 0

**Ubicación**: `load_production_data.py` líneas 761-842

**Mismo problema que Error C**: Probablemente ya existen.

---

### Error E: Price List = 0 (CSV parsing + PackagingCatalog error)
**Esperado**: 100+ entries
**Obtenido**: 0

**Ubicación**: `load_production_data.py` líneas 1379-1606

**Causas**:
1. `_load_packaging_metadata()` falla al crear PackagingColor (línea 1461 intenta crear sin error explícito)
2. `_load_pricing_entries()` falla en línea 1549 (PackagingCatalog.description)
3. `_load_pricing_entries()` falla en líneas 1556-1559 (campos obligatorios faltantes)

---

## PARTE 5: FLUJO DE DATOS DEL PRICE LIST CSV

### Datos disponibles en CSV (Columna 0-3):
```
CACTUS, "Rígida 5 cuadrada terracota", "$950", "C R5 T-1"
CACTUS, "Rígida cuadrada 5 dorada",     "$1.05", "C R5 D-2"
...
```

### Información que FALTA pero SE NECESITA:
Para crear PackagingCatalog necesitas:
1. `packaging_type_id` - De dónde sacarlo?
   - El CSV dice "Rígida 5" = tipo "Rígida"
   - Pero NO EXISTE tabla de tipos creada
   - El código intenta crear uno pero MAL (línea 1549 busca en .description)

2. `packaging_material_id` - De dónde sacarlo?
   - El CSV no lo especifica directamente
   - "Rígida" podría ser un material

3. `packaging_color_id` - Se puede extraer ✅
   - "terracota" → buscar/crear PackagingColor con name="TERRACOTA"
   - "dorada" → buscar/crear PackagingColor con name="DORADA"

---

## PARTE 6: ARCHIVOS DE DATOS REALES

### Contenido GeoJSON ("Exported 29 fields, 12 lines.geojson")
El archivo contiene features con estos Names:
- **Warehouses**: Nave 1, Nave 2, Nave 3 norte, Nave 3 sur, Nave 4 norte, Nave 4 sur, Nave 5 norte, Nave 5 sur, Nave 6, Nave 7, Nave 8
- **Storage Areas**: Madres norte, Madres sur, Madres 1 Sur, Madres 2 Sur, etc., Tunnel 1-3, Sombraculo 1-4, Somb 1
- **Storage Locations**: Canteros nave 8, Canteros nave 5 sur, Canteros nave 5 norte, etc., Cantero somb 1-2, Cantero nave 1-7

---

## PARTE 7: SÍNTESIS DE ERRORES CRÍTICOS

| Error | Línea(s) | Impacto | Severidad |
|-------|----------|---------|-----------|
| PackagingCatalog.description NO EXISTE | 1549, 1558 | price_list=0 | CRÍTICA |
| PackagingCatalog.code NO EXISTE | 1557 | price_list=0 | CRÍTICA |
| PackagingCatalog sin packaging_type_id | 1556 | IntegrityError | CRÍTICA |
| PackagingCatalog sin packaging_material_id | 1556 | IntegrityError | CRÍTICA |
| PackagingCatalog sin packaging_color_id | 1556 | IntegrityError | CRÍTICA |
| Cascada: si warehouses=0, storage_areas=0 | 216-222 | storage_areas=0 | ALTA |
| Product_states ya existen, no se actualizan | 1020-1037 | contador=0 | MEDIA |
| Storage_bin_types ya existen, no se actualizan | 824-826 | contador=0 | MEDIA |

---

## CONCLUSIONES

### ¿Por qué storage_locations=12 SÍ funciona?
- Es el único que NO depende de warehouses/storage_areas existentes
- Probablemente es nuevo (no estaba en DB anteriormente)
- El contador se actualiza correctamente

### ¿Por qué los demás = 0?
1. **Cascada de errores**: Warehouses fallan → Storage Areas fallan → Storage Location Config falla
2. **Atributos inexistentes**: PackagingCatalog.description, .code
3. **Idempotencia silenciosa**: ProductStates y StorageBinTypes ya existen, contadores no se actualizan
4. **CSV parsing incompleto**: PriceList no sabe cómo mapear datos a PackagingCatalog

### ¿Qué falta en el modelo?
PackagingCatalog tiene la ESTRUCTURA CORRECTA en la DB, pero el loader espera campos que NO existen:
- `description` (intenta usarlo en línea 1549)
- `code` (intenta usarlo en línea 1557)

El modelo tiene estos campos correctos:
- `sku` (string único)
- `name` (descripción)
- `packaging_type_id`, `packaging_material_id`, `packaging_color_id` (FKs)

