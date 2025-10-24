# 🚀 DemeterAI Flujo Principal - Quick Reference

**Versión**: 1.0 | **Última actualización**: 2025-10-24 | **Estado**: 88% completo

---

## 📍 Dónde Encontrar Todo

### Archivos Principales

| Componente | Archivo | Líneas | Estado |
|-----------|---------|--------|--------|
| **Endpoint API** | `app/controllers/stock_controller.py` | 62-145 | ✅ 100% |
| **Orquestación Upload** | `app/services/photo/photo_upload_service.py` | 45-180 | ⚠️ 85% |
| **S3 Storage** | `app/services/photo/s3_image_service.py` | Completo | ✅ 100% |
| **ML Padre** | `app/tasks/ml_tasks.py` | 176-295 | ✅ 100% |
| **ML Hijo** | `app/tasks/ml_tasks.py` | 302-563 | ✅ 100% |
| **ML Callback** | `app/tasks/ml_tasks.py` | 570-1062 | ⚠️ 95% |
| **Segmentación** | `app/services/ml_processing/segmentation_service.py` | ~200 | ⚠️ 75% |
| **SAHI Detection** | `app/services/ml_processing/sahi_detection_service.py` | Completo | ✅ 100% |
| **Estimación** | `app/services/ml_processing/band_estimation_service.py` | Completo | ✅ 100% |
| **Models** | `app/models/` | 28 modelos | ✅ 100% |
| **Repositories** | `app/repositories/` | 27 repos | ✅ 100% |

---

## 🔗 Flujo de Ejecución Paso a Paso

```
1. USUARIO SUBE FOTO
   └─> POST /api/v1/stock/photo (VALIDACIÓN)
       └─> stock_controller.upload_photo()
           └─> PhoneUploadService.upload_photo()
               ├─ Extrae GPS + EXIF
               ├─ Sube a S3 (original + thumbnail)
               ├─ Crea PhotoProcessingSession
               └─ Dispara ml_parent_task.delay()

2. TAREA PADRE (CPU)
   └─> ml_parent_task (queue=cpu_queue)
       ├─ Valida circuit breaker
       ├─ Marca sesión "processing"
       └─ Dispara CHORD pattern
           └─> [ml_child_task] × N (EN PARALELO)

3. TAREAS HIJAS (GPU) - PARALELO
   └─> ml_child_task (queue=gpu_queue)
       ├─ 1. Carga imagen (3-tier cache)
       ├─ 2. Segmentación (detecta contenedores)
       ├─ 3. Para cada contenedor:
       │   ├─ Crop + SAHI detection (plantas)
       │   └─ Band estimation (plantas ocultas)
       └─ Retorna {total_detected, total_estimated, ...}

4. CALLBACK AGREGACIÓN (CPU)
   └─> ml_aggregation_callback (queue=cpu_queue)
       ├─ Filtra resultados válidos
       ├─ Suma totales
       ├─ Persiste en BD (Detection, Estimation, StockBatch)
       ├─ Genera visualización (OpenCV + AVIF)
       ├─ Upload viz a S3
       ├─ Cleanup temp files
       └─ Marca sesión "completed"

5. FRONTEND POLLING
   └─> GET /api/v1/stock/tasks/{task_id}/status
       ├─ Verifica estado
       ├─ Si completado: retorna resultados
       └─ Muestra visualización con overlays
```

---

## 🎯 Lo Que Está HECHO

### ✅ Completamente Funcional

```python
# 1. SEGMENTATION (EXCEPT: main implementation)
SAHIDetectionService.detect_in_segmento()
  ├─ SAHI tiling: 512x512 con 25% overlap
  ├─ GREEDYNMM merge (quita duplicados en bordes)
  └─ Detects 800+ plants (10x mejor que direct YOLO)

# 2. BAND ESTIMATION
BandEstimationService.estimate_undetected_plants()
  ├─ Division en 4 bandas horizontales
  ├─ HSV vegetation filter + Otsu thresholding
  ├─ Auto-calibration per band
  └─ Formula: count = ceil(area / avg_plant_area * 0.9)

# 3. ML ORCHESTRATION (Celery Chord)
ml_parent_task → [ml_child_task₁, ml_child_task₂, ...] → callback
  ├─ Parent: CPU queue (orquestación)
  ├─ Children: GPU queue (YOLO inference)
  ├─ Callback: CPU queue (agregación)
  └─ Partial failure handling (algunos fallan, callback sigue)

# 4. CIRCUIT BREAKER
check_circuit_breaker()
  ├─ Estados: CLOSED → OPEN (después 5 fallos) → HALF_OPEN
  ├─ Timeout: 5 minutos
  └─ Previene cascada de fallos en S3

# 5. S3 STORAGE
S3ImageService.upload_original() + upload_thumbnail()
  ├─ Original: JPEG
  ├─ Thumbnail: AVIF (50% compresión)
  └─ Binary cache en PostgreSQL (image_data column)

# 6. DATABASE MODELS & REPOS
28 modelos SQLAlchemy + 27 repositorios
  ├─ PhotoProcessingSession (tracking)
  ├─ S3Image (archivos)
  ├─ Detection (plantas detectadas)
  ├─ Estimation (plantas estimadas)
  ├─ StockBatch + StockMovement (inventario)
  └─ StorageLocation, DensityParameter (config)
```

---

## 🚧 Lo Que FALTA Completar

### 🔴 CRÍTICO (Bloquea producción)

```python
# 1. SEGMENTATION SERVICE - 75% implementado
SegmentationService.segment_image()
  ├─ Archivo: app/services/ml_processing/segmentation_service.py
  ├─ Línea: ~200 (donde comienza stub)
  ├─ Falta: Main implementation loop
  └─ Impacto: SIN segmentación, TODO falla

# 2. GPS LOCATION LOOKUP - Deshabilitado
PhotoUploadService.upload_photo()
  ├─ Archivo: app/services/photo/photo_upload_service.py
  ├─ Líneas: 170-189 (comentadas)
  ├─ Actualmente: storage_location_id = 1 (hardcoded)
  ├─ Debería: self.location_service.get_by_coordinates(lat, lon)
  └─ Impacto: No sabe en qué ubicación procesa
```

### 🟠 IMPORTANTE (Reduce calidad)

```python
# 3. HARDCODED VALUES EN CALLBACK
app/tasks/ml_tasks.py líneas 1740-1762
  ├─ product_id = 1 ❌
  ├─ product_state_id = 1 ❌
  ├─ user_id = 1 ❌
  └─ Debería: Leer de StorageLocationConfig

# 4. VISUALIZACIÓN - Polígonos Simplificados
app/tasks/ml_tasks.py líneas 1905-1914
  ├─ Actualmente: rectangles (bandas)
  ├─ Debería: usar vegetation_polygon real
  └─ Impacto: overlays imprecisos

# 5. EMPTY CONTAINER DETECTION
app/tasks/ml_tasks.py línea 983
  ├─ Actualmente: total_empty_containers = 0
  ├─ Debería: analizar máscaras
  └─ Impacto: no detecta cajas vacías
```

---

## 📊 Estadísticas

```
Implementación por Componente:

  Servicios ML            ████████░░ 90%
  Tareas Celery          ████████░░ 90%
  S3 Integration         ██████████ 100%
  Database Layer         ██████████ 100%
  API Controller         ██████████ 100%
  Circuit Breaker        ██████████ 100%
  Visualization          █████████░ 95%
  GPS Lookup             █░░░░░░░░░ 10%
  Segmentation           ███████░░░ 75%

PROMEDIO GENERAL:        ████████░░ 88%
```

---

## 🛠️ Cómo Completar Lo Que Falta

### Paso 1: Segmentation (CRÍTICO)

```bash
# Archivo: app/services/ml_processing/segmentation_service.py
# Busca: async def segment_image(...)

# Pseudocódigo a implementar:
1. Load YOLO segmentation model from cache
2. Run prediction: results = model.predict(image, conf=0.30, iou=0.50)
3. For each detection:
   - Get class (remap: "cajon"→"box", "plug"→"plug", etc)
   - Get normalized bbox (YOLO returns 0.0-1.0)
   - Get polygon from mask
   - Create SegmentResult
4. Return List[SegmentResult]

# Aproximadamente: 20-30 líneas de código
```

### Paso 2: GPS Lookup (CRÍTICO)

```bash
# Archivo: app/services/photo/photo_upload_service.py
# Busca: líneas 170-189 (comentadas)

# Cambiar de:
# storage_location_id = 1  # hardcoded

# A:
gps_coords = extract_gps_from_exif(image)
if gps_coords:
    location = await self.location_service.get_by_coordinates(
        lat=gps_coords[0],
        lon=gps_coords[1]
    )
    storage_location_id = location.id if location else 1
else:
    storage_location_id = 1
```

### Paso 3: Fijar Hardcoded Values (IMPORTANTE)

```bash
# Archivo: app/tasks/ml_tasks.py
# Líneas: 1740-1762 (función _persist_ml_results)

# Cambiar de:
product_id = 1
product_state_id = 1
user_id = 1

# A:
# Fetch PhotoProcessingSession
photo_session = session.query(PhotoProcessingSession).get(session_id)

# Get StorageLocationConfig
config = session.query(StorageLocationConfig).filter_by(
    storage_location_id=photo_session.storage_location_id
).first()

product_id = config.product_id if config else 1
product_state_id = config.expected_product_state_id if config else 1
user_id = config.ml_processor_user_id if config else 1  # Sistema user
```

---

## 🔍 Buscar en el Código

```bash
# Buscar TODOs y FIXMEs
grep -r "TODO\|FIXME" app/

# Buscar hardcoded values
grep -r "= 1\b" app/services/ app/tasks/

# Buscar pass statements (stubs incompletos)
grep -n "^\s*pass$" app/services/ml_processing/

# Encontrar líneas comentadas del GPS
grep -n "# GPS\|# location" app/services/photo/

# Ver todos los CircuitBreakerException
grep -r "CircuitBreakerException" app/
```

---

## 🧪 Testing

```python
# Test Upload Flow
pytest tests/integration/test_photo_upload.py -v

# Test ML Processing
pytest tests/integration/test_ml_pipeline.py -v

# Test Celery Tasks
pytest tests/unit/tasks/test_ml_tasks.py -v

# Test Circuit Breaker
pytest tests/unit/tasks/test_circuit_breaker.py -v

# Test Models
pytest tests/unit/models/ -v

# Full Test Suite
pytest tests/ -v --cov=app --cov-report=html
```

---

## 📚 Documentos Relacionados

| Documento | Ubicación | Propósito |
|-----------|-----------|----------|
| **Flujo Principal (este)** | `FLUJO_PRINCIPAL_DOCUMENTACION.md` | Documentación completa del flujo |
| **Diagrama Mermaid** | `FLUJO PRINCIPAL V3-2025-10-07-201442.mmd` | Visualización del flujo |
| **Database Schema** | `database/database.mmd` | Modelo de datos (source of truth) |
| **Architecture** | `engineering_plan/03_architecture_overview.md` | Patrones de arquitectura |
| **Critical Issues** | `CRITICAL_ISSUES.md` | Lecciones de Sprint 02 |
| **Sprint Plan** | `backlog/01_sprints/sprint-03-services/` | Plan actual |

---

## 💡 Key Patterns Usados

### Patrón 1: Service → Service (NUNCA Service → Repository)
```python
# ✅ CORRECTO
class PhotoUploadService:
    def __init__(self,
                 s3_service: S3ImageService,           # Service
                 location_service: StorageLocationService):  # Service
        self.s3_service = s3_service
        self.location_service = location_service

# ❌ INCORRECTO
class PhotoUploadService:
    def __init__(self,
                 s3_repo: S3ImageRepository):  # Repository - WRONG!
```

### Patrón 2: Celery Chord para Paralelismo
```python
# Parent task crea signatures de children + callback
chord(
    [child_task.s(arg1), child_task.s(arg2), ...]
)(callback_task.s(session_id=123))

# Ejecución:
# 1. Child tasks EN PARALELO (GPU queue)
# 2. Callback después que TODOS terminan (CPU queue)
```

### Patrón 3: Circuit Breaker para Resilencia
```python
try:
    check_circuit_breaker()  # Throw si está abierto
    # Operación (upload, request, etc)
    record_circuit_breaker_success()
except CircuitBreakerException:
    # Rechazar request inmediatamente
except TemporaryError:
    record_circuit_breaker_failure()
    # Retry si < max_retries
```

### Patrón 4: 3-Tier Cache
```python
# Image loading (de más rápido a más lento)
1. PostgreSQL binary cache (image_data column)
2. /tmp local file cache
3. S3 download (fallback)
```

---

## 🚨 Problemas Conocidos

| Problema | Ubicación | Severidad | Workaround |
|----------|-----------|-----------|-----------|
| GPS lookup deshabilitado | photo_upload_service.py:170 | 🔴 CRÍTICO | Usar storage_location_id=1 por ahora |
| Segmentation incomplete | segmentation_service.py:200 | 🔴 CRÍTICO | No hay (sin segmentación todo falla) |
| Hardcoded product_id=1 | ml_tasks.py:1740 | 🟠 IMPORTANTE | Usar primero config.product_id |
| Circuit breaker en RAM | ml_tasks.py:72 | 🟡 MEJORA | Se reinicia si caen workers |
| Visualización imprecisa | ml_tasks.py:1905 | 🟡 MEJORA | Usar polígonos simplificados por ahora |

---

## 📞 Contacto & Soporte

- **Documentación Completa**: `FLUJO_PRINCIPAL_DOCUMENTACION.md`
- **Código Fuente**: Archivos listados en "Dónde Encontrar Todo"
- **Sprint Plan**: `backlog/01_sprints/sprint-03-services/`
- **Team**: DemeterAI Engineering

---

## ⚡ Cheat Sheet

```bash
# VER ESTADO DEL FLUJO
cat flows/procesamiento_ml_upload_s3_principal/FLUJO_PRINCIPAL_DOCUMENTACION.md | head -50

# ENCONTRAR ARCHIVO ESPECÍFICO
find app/services -name "*photo*"
find app/tasks -name "*ml*"

# VER ESTRUCTURA DE UN SERVICIO
cat app/services/photo/photo_upload_service.py | head -100

# VER UN MODELO
cat app/models/photo_processing_session.py

# VER TESTS
ls tests/integration/test_*upload*.py
ls tests/unit/tasks/test_ml*.py

# EJECUTAR TESTS
pytest tests/integration/test_photo_upload.py -v -s

# VER ERRORES COMUNES
grep -r "raise\|Error\|Exception" app/tasks/ml_tasks.py | head -20

# CONTAR LÍNEAS DE CÓDIGO
wc -l app/tasks/ml_tasks.py
find app/services -name "*.py" -exec wc -l {} + | tail -1
```

---

**Última actualización**: 2025-10-24
**Documento**: Quick Reference para Flujo Principal
**Responsable**: DemeterAI Engineering Team
