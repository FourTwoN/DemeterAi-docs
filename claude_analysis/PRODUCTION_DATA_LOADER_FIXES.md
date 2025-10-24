# SOLUCIONES PARA EL LOADER DE DATOS DE PRODUCCIÓN

## RESUMEN EJECUTIVO

5 problemas críticos necesitan arreglarse para que la carga de datos funcione:

1. ✅ **PackagingCatalog.description** → Cambiar a `name`
2. ✅ **PackagingCatalog.code** → Cambiar a `sku`  
3. ✅ **Campos obligatorios faltantes** → Crear packaging type/material/color antes de catalog
4. ✅ **CSV parsing incompleto** → Parsear tipo/material/color de la descripción
5. ✅ **Cascada de errores** → Mejorar manejo de errores y logging

---

## FIX 1: PackagingCatalog.description → name (CRÍTICO)

### Código ACTUAL (INCORRECTO) - Línea 1549:
```python
stmt = select(PackagingCatalog).where(
    PackagingCatalog.description.ilike(f"%{maceta}%")  # ❌ NO EXISTE
)
```

### Código CORRECTO:
```python
stmt = select(PackagingCatalog).where(
    PackagingCatalog.name.ilike(f"%{maceta}%")  # ✅ CORRECTO
)
```

### Cambios necesarios:
- Línea 1549: `PackagingCatalog.description` → `PackagingCatalog.name`
- Línea 1558: `description=maceta[:200]` → `name=maceta[:200]`

---

## FIX 2: PackagingCatalog.code → sku (CRÍTICO)

### Código ACTUAL (INCORRECTO) - Línea 1557:
```python
packaging = PackagingCatalog(
    code=sku[:20] if sku else f"PKG{count:04d}",  # ❌ NO EXISTE
    ...
)
```

### Código CORRECTO:
```python
packaging = PackagingCatalog(
    sku=sku[:50] if sku else f"PKG{count:04d}",  # ✅ CORRECTO
    ...
)
```

### Cambios necesarios:
- Línea 1557: `code=` → `sku=`

---

## FIX 3: Campos obligatorios (packaging_type/material/color) - CRÍTICO

### Problema:
PackagingCatalog requiere:
- `packaging_type_id` (FK, NOT NULL)
- `packaging_material_id` (FK, NOT NULL)
- `packaging_color_id` (FK, NOT NULL)

Pero el CSV no proporciona estos datos directamente.

Ejemplo: "Rígida 5 cuadrada terracota"
- tipo (type) = "Rígida"
- material = "Plástico" (asumir de contexto)
- color = "terracota"

### Solución: Crear helpers para extraer y mapear

```python
async def _get_or_create_packaging_type(self, type_name: str) -> int:
    """Get or create packaging type from name."""
    from app.models.packaging_type import PackagingType
    
    code = re.sub(r"[^A-Za-z0-9_]", "", type_name).upper()[:50]
    
    stmt = select(PackagingType).where(PackagingType.code == code)
    result = await self.session.execute(stmt)
    pkg_type = result.scalar_one_or_none()
    
    if not pkg_type:
        pkg_type = PackagingType(
            code=code,
            name=type_name,
            description=f"Packaging type: {type_name}"
        )
        self.session.add(pkg_type)
        await self.session.flush()
    
    return pkg_type.id

async def _extract_packaging_info(self, maceta_str: str) -> dict:
    """Extract type, color from maceta description.
    
    Example: "Rígida 5 cuadrada terracota" →
    {
        'type': 'Rígida',
        'size': '5',
        'shape': 'cuadrada',
        'color': 'terracota'
    }
    """
    tokens = maceta_str.lower().split()
    info = {
        'type': tokens[0] if tokens else 'Unknown',  # "rígida"
        'size': None,
        'color': None
    }
    
    # Extract size (números)
    for token in tokens:
        if token.isdigit():
            info['size'] = token
            break
    
    # Extract color (match against known colors)
    colors = [
        'terracota', 'dorada', 'gris', 'blanco', 'azul',
        'negra', 'negro', 'violeta', 'rojo', 'verde'
    ]
    for color in colors:
        if color in maceta_str.lower():
            info['color'] = color.upper()
            break
    
    return info
```

### Uso en `_load_pricing_entries()`:

```python
# Antes de crear PackagingCatalog (línea 1556)
pkg_info = self._extract_packaging_info(maceta)

# Get or create type
type_id = await self._get_or_create_packaging_type(pkg_info['type'])

# Get or create material (por ahora: asumir Plástico para "Rígida")
material_id = await self._get_or_create_packaging_material('PLASTICO')

# Get or create color
color_id = await self._get_or_create_packaging_color(pkg_info['color'])

# Crear PackagingCatalog con TODOS los campos requeridos
packaging = PackagingCatalog(
    packaging_type_id=type_id,        # ✅ REQUERIDO
    packaging_material_id=material_id, # ✅ REQUERIDO
    packaging_color_id=color_id,      # ✅ REQUERIDO
    sku=sku[:50] if sku else f"PKG{count:04d}",
    name=maceta[:200],
)
```

---

## FIX 4: Helpers para tipos, materiales y colores

### PackagingType helper:
```python
async def _get_or_create_packaging_type(self, type_name: str) -> int:
    """Get or create packaging type."""
    from app.models.packaging_type import PackagingType
    
    code = re.sub(r"[^A-Za-z0-9_]", "", type_name).upper()[:50]
    
    stmt = select(PackagingType).where(PackagingType.code == code)
    result = await self.session.execute(stmt)
    pkg_type = result.scalar_one_or_none()
    
    if not pkg_type:
        pkg_type = PackagingType(
            code=code,
            name=type_name,
            description=f"Packaging type: {type_name}"
        )
        self.session.add(pkg_type)
        await self.session.flush()
        logger.debug(f"  ✓ Created PackagingType: {code}")
    
    return pkg_type.id
```

### PackagingMaterial helper:
```python
async def _get_or_create_packaging_material(self, material_name: str) -> int:
    """Get or create packaging material."""
    from app.models.packaging_material import PackagingMaterial
    
    code = re.sub(r"[^A-Za-z0-9_]", "", material_name).upper()[:50]
    
    stmt = select(PackagingMaterial).where(PackagingMaterial.code == code)
    result = await self.session.execute(stmt)
    pkg_material = result.scalar_one_or_none()
    
    if not pkg_material:
        pkg_material = PackagingMaterial(
            code=code,
            name=material_name,
            description=f"Material: {material_name}"
        )
        self.session.add(pkg_material)
        await self.session.flush()
        logger.debug(f"  ✓ Created PackagingMaterial: {code}")
    
    return pkg_material.id
```

### PackagingColor helper (YA EXISTE, mejorar):
```python
async def _get_or_create_packaging_color(self, color_name: str) -> int:
    """Get or create packaging color."""
    if not color_name:
        # Default color si no se puede extraer
        color_name = 'UNKNOWN'
    
    color_name = color_name.strip().upper()
    
    stmt = select(PackagingColor).where(PackagingColor.name == color_name)
    result = await self.session.execute(stmt)
    pkg_color = result.scalar_one_or_none()
    
    if not pkg_color:
        hex_code = self._generate_hex_for_color(color_name)
        pkg_color = PackagingColor(
            name=color_name,
            hex_code=hex_code
        )
        self.session.add(pkg_color)
        await self.session.flush()
        logger.debug(f"  ✓ Created PackagingColor: {color_name} ({hex_code})")
    
    return pkg_color.id
```

---

## FIX 5: Mejorar manejo de errores y logging

### Problema:
- Muchos try-except sin logs explícitos
- Fallos silenciosos que resultan en contadores = 0
- Sin diferenciación entre "ya existe" y "error"

### Soluciones:

1. **En load_warehouses (línea 127-130)**:
```python
# ANTES (sin log explícito)
except Exception as db_error:
    await self.session.rollback()
    logger.error(f"  ✗ Database error: {str(db_error)}")

# DESPUÉS (con contexto)
except Exception as db_error:
    await self.session.rollback()
    logger.error(
        f"  ✗ Database error loading warehouse {warehouse.code}: {str(db_error)}",
        exc_info=True
    )
```

2. **Separar contadores por tipo**:
```python
async def load_warehouses(self) -> int:
    count_created = 0
    count_skipped = 0
    
    for feature in geojson_data.get("features", []):
        try:
            warehouse = self._parse_warehouse_feature(feature)
            if warehouse:
                existing = ...
                if not existing:
                    self.session.add(warehouse)
                    count_created += 1
                else:
                    count_skipped += 1
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
    
    self.loaded_count["warehouses"] = count_created
    logger.info(f"✅ Loaded {count_created} warehouses (skipped {count_skipped} existing)")
    return count_created
```

3. **En load_product_states (línea 1020-1037)**:
```python
# Actualizar contador incluso si ya existen
count = 0  # Solo contar NUEVOS
skipped = 0  # Contar existentes

for state_data in product_states:
    stmt = select(ProductState).where(ProductState.code == state_data["code"])
    result = await self.session.execute(stmt)
    existing = result.scalar_one_or_none()
    
    if not existing:
        product_state = ProductState(**state_data)
        self.session.add(product_state)
        count += 1
        logger.info(f"  ✓ ProductState: {state_data['code']}")
    else:
        skipped += 1
        logger.debug(f"  ⊘ ProductState exists: {state_data['code']}")

await self.session.commit()
self.loaded_count["product_states"] = count
logger.info(f"✅ Loaded {count} product states (skipped {skipped} existing)")
return count
```

---

## IMPLEMENTACIÓN PASO A PASO

### Paso 1: Backup del archivo original
```bash
cp app/db/load_production_data.py app/db/load_production_data.py.backup
```

### Paso 2: Importar modelos necesarios (línea ~38-50)
```python
from app.models import (
    PackagingCatalog,
    PackagingColor,
    PackagingMaterial,      # ✅ ADD
    PackagingType,          # ✅ ADD
    PriceList,
    Product,
    ProductCategory,
    ProductFamily,
    ProductState,
    StorageArea,
    StorageBinType,
    StorageLocation,
    StorageLocationConfig,
    Warehouse,
)
```

### Paso 3: Agregar métodos helper (antes de load_price_list())
```python
# Después de _generate_hex_for_color() ~línea 740

async def _extract_packaging_info(self, maceta_str: str) -> dict:
    """Extract packaging info from description."""
    # ... (ver código arriba)

async def _get_or_create_packaging_type(self, type_name: str) -> int:
    """Get or create packaging type."""
    # ... (ver código arriba)

async def _get_or_create_packaging_material(self, material_name: str) -> int:
    """Get or create packaging material."""
    # ... (ver código arriba)

async def _get_or_create_packaging_color(self, color_name: str) -> int:
    """Get or create packaging color."""
    # ... (ver código arriba)
```

### Paso 4: Corregir línea 1549
```python
# ANTES
stmt = select(PackagingCatalog).where(
    PackagingCatalog.description.ilike(f"%{maceta}%")
)

# DESPUÉS
stmt = select(PackagingCatalog).where(
    PackagingCatalog.name.ilike(f"%{maceta}%")
)
```

### Paso 5: Corregir líneas 1556-1559
```python
# ANTES
if not packaging:
    packaging = PackagingCatalog(
        code=sku[:20] if sku else f"PKG{count:04d}",
        description=maceta[:200],
    )

# DESPUÉS
if not packaging:
    try:
        # Extract packaging information
        pkg_info = self._extract_packaging_info(maceta)
        
        # Get or create required foreign keys
        type_id = await self._get_or_create_packaging_type(pkg_info['type'])
        material_id = await self._get_or_create_packaging_material('PLASTICO')  # Default
        color_id = await self._get_or_create_packaging_color(pkg_info.get('color'))
        
        # Create packaging catalog with all required fields
        packaging = PackagingCatalog(
            packaging_type_id=type_id,
            packaging_material_id=material_id,
            packaging_color_id=color_id,
            sku=sku[:50] if sku else f"PKG{count:04d}",
            name=maceta[:200],
        )
        logger.debug(f"  ✓ New packaging created: {packaging.sku}")
    except Exception as e:
        logger.error(f"  ✗ Error creating packaging: {str(e)}", exc_info=True)
        continue
```

### Paso 6: Verificar imports
```bash
cd /home/lucasg/proyectos/DemeterDocs
python3 -c "from app.db.load_production_data import ProductionDataLoader; print('✅ Imports OK')"
```

---

## TESTING

### Paso 1: Limpiar datos previos (OPTIONAL - solo para test limpio)
```sql
-- En la BD de test
DELETE FROM price_list;
DELETE FROM packaging_catalog;
DELETE FROM packaging_colors;
DELETE FROM packaging_materials;
DELETE FROM packaging_types;
DELETE FROM product_states;
DELETE FROM storage_bin_types;
```

### Paso 2: Ejecutar loader
```bash
cd /home/lucasg/proyectos/DemeterDocs
python3 << 'PYTHON'
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.db.load_production_data import ProductionDataLoader
from app.core.config import settings

async def test_loader():
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        loader = ProductionDataLoader(session)
        results = await loader.load_all_async()
        print("\n=== LOAD RESULTS ===")
        for key, count in results.items():
            print(f"{key}: {count}")

asyncio.run(test_loader())
PYTHON
```

### Paso 3: Verificar en BD
```sql
SELECT 'warehouses' as table_name, COUNT(*) FROM warehouses
UNION ALL
SELECT 'storage_areas', COUNT(*) FROM storage_areas
UNION ALL
SELECT 'storage_locations', COUNT(*) FROM storage_locations
UNION ALL
SELECT 'product_categories', COUNT(*) FROM product_categories
UNION ALL
SELECT 'product_states', COUNT(*) FROM product_states
UNION ALL
SELECT 'product_families', COUNT(*) FROM product_families
UNION ALL
SELECT 'products', COUNT(*) FROM products
UNION ALL
SELECT 'packaging_types', COUNT(*) FROM packaging_types
UNION ALL
SELECT 'packaging_materials', COUNT(*) FROM packaging_materials
UNION ALL
SELECT 'packaging_colors', COUNT(*) FROM packaging_colors
UNION ALL
SELECT 'packaging_catalog', COUNT(*) FROM packaging_catalog
UNION ALL
SELECT 'price_list', COUNT(*) FROM price_list;
```

---

## RESUMEN DE CAMBIOS

| Archivo | Líneas | Cambio |
|---------|--------|--------|
| load_production_data.py | 38-50 | Agregar imports de PackagingType/Material |
| load_production_data.py | 741-900 | Agregar 4 métodos helper |
| load_production_data.py | 1549 | `.description` → `.name` |
| load_production_data.py | 1557 | `code=` → `sku=` |
| load_production_data.py | 1556-1559 | Cambiar lógica de creación (agregar FK + manejo de errores) |

---

## DEPENDENCIAS

Asegúrate que estos modelos existen:
- ✅ `app.models.packaging_type.PackagingType`
- ✅ `app.models.packaging_material.PackagingMaterial`
- ✅ `app.models.packaging_color.PackagingColor` (YA EXISTE)
- ✅ `app.models.packaging_catalog.PackagingCatalog` (YA EXISTE)

