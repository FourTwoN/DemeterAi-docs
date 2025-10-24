# 📋 Tareas de Implementación - Flujo Principal

**Generado**: 2025-10-24
**Versión**: 1.0
**Estado Actual**: 88% completo
**Tareas Restantes**: 5 críticas + 5 mejoras

---

## 🎯 Tareas Críticas (Bloquean producción)

### TAREA 0: Crear Upload Tasks para IO_QUEUE ⭐ PRIORITARIA

**Prioridad**: 🔴 CRÍTICA
**Estimado**: 3-6 horas
**Bloqueador**: Callback se bloquea 16-65 segundos esperando S3

#### Descripción
El `io_queue` está completamente configurado pero **NO se usa**. Todas las subidas de visualización en el callback de ML se hacen directamente con boto3 (síncronas, bloqueantes). Esto ralentiza el pipeline ML 3-8x.

#### Ubicación
- **Archivo a crear**: `/home/lucasg/proyectos/DemeterDocs/app/tasks/s3_upload_tasks.py` (NUEVO)
- **Archivo a modificar**: `/home/lucasg/proyectos/DemeterDocs/app/tasks/ml_tasks.py` (líneas 797-887)
- **Documentación completa**: `CORRECCION_IO_QUEUE.md`

#### Problema Actual
```python
# ❌ ACTUAL: Direct boto3 en callback (BLOQUEA)
@app.task(queue="cpu_queue")
def ml_aggregation_callback(results, session_id):
    # ... 8-13 segundos de trabajo...

    # 🔴 DESPUÉS, 16-65 segundos BLOQUEADOS:
    s3_client = boto3.client("s3")
    s3_client.put_object(...)  # Visualization
    s3_client.put_object(...)  # Thumbnail original
    s3_client.put_object(...)  # Thumbnail processed

    db_session.commit()  # Espera todo antes de commit
```

#### Qué Implementar

**Paso 1: Crear archivo `s3_upload_tasks.py`**

```python
# app/tasks/s3_upload_tasks.py

from app.celery_app import app
from app.services.photo.s3_image_service import S3ImageService

@app.task(bind=True, queue="io_queue", max_retries=3)
def upload_original_s3_task(self, file_bytes: bytes, session_id: int, filename: str):
    """Upload original image to S3 using io_queue (gevent worker)."""
    try:
        s3_service = S3ImageService()
        result = s3_service.upload_original(
            file_bytes=file_bytes,
            session_id=session_id,
            filename=filename,
        )
        return {"status": "success", "session_id": session_id, "result": result}
    except Exception as exc:
        countdown = 2 ** self.request.retries  # 2s, 4s, 8s
        raise self.retry(exc=exc, countdown=countdown)


@app.task(bind=True, queue="io_queue", max_retries=3)
def upload_thumbnail_s3_task(self, file_bytes: bytes, session_id: int, filename: str):
    """Upload thumbnail to S3 using io_queue."""
    try:
        s3_service = S3ImageService()
        result = s3_service.upload_thumbnail(
            file_bytes=file_bytes,
            session_id=session_id,
            filename=filename,
        )
        return {"status": "success", "session_id": session_id, "result": result}
    except Exception as exc:
        countdown = 2 ** self.request.retries
        raise self.retry(exc=exc, countdown=countdown)


@app.task(bind=True, queue="io_queue", max_retries=3)
def upload_visualization_s3_task(self, file_bytes: bytes, session_id: int):
    """
    Upload visualization image to S3 using io_queue.
    ⭐ THIS IS THE CRITICAL TASK THAT WAS BLOCKING THE CALLBACK
    """
    try:
        s3_service = S3ImageService()
        s3_key = f"uploads/{session_id}/processed.avif"

        result = s3_service.upload_visualization(
            file_bytes=file_bytes,
            s3_key=s3_key,
            content_type="image/avif",
        )
        return {"status": "success", "session_id": session_id, "s3_key": s3_key}
    except Exception as exc:
        countdown = 2 ** self.request.retries
        raise self.retry(exc=exc, countdown=countdown)
```

**Paso 2: Refactorizar `ml_aggregation_callback()` (líneas 797-887)**

```python
# Imports a agregar
from app.tasks.s3_upload_tasks import (
    upload_visualization_s3_task,
    upload_thumbnail_s3_task,
)

# Cambiar de:
# 🔴 Direct S3 upload (blocking)
s3_client = boto3.client("s3")
s3_client.put_object(
    Bucket=settings.S3_BUCKET_ORIGINAL,
    Key=viz_s3_key,
    Body=viz_bytes,
)

# A:
# ✅ Async task dispatch (non-blocking)
upload_visualization_s3_task.delay(
    file_bytes=viz_bytes,
    session_id=session_id,
)

# Idem para thumbnails:
upload_thumbnail_s3_task.delay(
    file_bytes=thumbnail_original_bytes,
    session_id=session_id,
    filename="thumbnail_original.jpg",
)

upload_thumbnail_s3_task.delay(
    file_bytes=thumbnail_processed_bytes,
    session_id=session_id,
    filename="thumbnail_processed.jpg",
)
```

#### Resultado Esperado

**Tiempo de ejecución ML pipeline**:
- ANTES: 24-78 segundos (bloqueado por S3)
- DESPUÉS: 8-13 segundos (S3 en paralelo)

**Mejora**: 3-8x más rápido ✨

#### Checklist
- [ ] Crear `app/tasks/s3_upload_tasks.py`
- [ ] Implementar `upload_original_s3_task()`
- [ ] Implementar `upload_thumbnail_s3_task()`
- [ ] Implementar `upload_visualization_s3_task()`
- [ ] Refactorizar `ml_aggregation_callback()` para usar tasks
- [ ] Remover imports directos de boto3 de ml_tasks.py
- [ ] Crear tests para nuevas tasks
- [ ] Crear test de integración
- [ ] Startup io_queue worker y verificar
- [ ] Load test con múltiples imágenes simultáneas

---

### TAREA 1: Completar SegmentationService

**Prioridad**: 🔴 CRÍTICO
**Estimado**: 2-3 horas
**Bloqueador**: SIN ESTO, NO FUNCIONA NADA

#### Descripción
El servicio de segmentación está 75% implementado. Falta implementar el método principal `segment_image()` que detecta contenedores (plugs, boxes, segments) en la imagen.

#### Ubicación
- **Archivo**: `/home/lucasg/proyectos/DemeterDocs/app/services/ml_processing/segmentation_service.py`
- **Línea de inicio**: ~200 (donde termina el stub)
- **Clase**: `SegmentationService`
- **Método**: `async def segment_image(...)`

#### Qué Implementar

```python
async def segment_image(
    self,
    image_array: np.ndarray,
    confidence_threshold: float = 0.30,
    iou_threshold: float = 0.50,
) -> List[SegmentResult]:
    """
    Detecta contenedores en la imagen usando YOLO v11.

    Pasos:
    1. Load YOLO model from ModelCache (tipo: SEGMENTATION)
    2. Run prediction: results = model.predict(image, ...)
    3. For each detection in results.masks:
       - Get bbox (normalized 0.0-1.0)
       - Get class name (remap si es necesario)
       - Get polygon mask
       - Create SegmentResult object
    4. Return List[SegmentResult]

    Returns:
        List[SegmentResult]:
            - container_type: "plug" | "box" | "segment"
            - confidence: 0.0-1.0
            - bbox: (x1, y1, x2, y2) normalized
            - polygon: List[(x, y)] normalized
            - mask: np.ndarray binary
    """
```

#### Pseudocódigo a Implementar

```python
# 1. Load model
model = self.model_cache.get_model(ModelType.SEGMENTATION)

# 2. Run prediction
results = await asyncio.to_thread(
    model.predict,
    image_array,
    conf=confidence_threshold,
    iou=iou_threshold,
)

# 3. Process results
segments = []
for detection in results[0].boxes:
    # Get normalized bbox
    bbox = detection.xyxyn[0].cpu().numpy()  # [x1, y1, x2, y2]

    # Get class
    class_id = int(detection.cls)
    class_name = model.names[class_id]

    # Remap class names
    container_type = self.CONTAINER_TYPE_MAPPING.get(class_name, class_name)

    # Get confidence
    confidence = float(detection.conf)

    # Get mask (si existe)
    if hasattr(detection, 'masks') and detection.masks is not None:
        mask = detection.masks.data[0].cpu().numpy()
    else:
        mask = None

    # Get polygon from mask
    polygon = extract_polygon_from_mask(mask) if mask is not None else None

    # Create result
    segment = SegmentResult(
        container_type=container_type,
        confidence=confidence,
        bbox=tuple(bbox),
        polygon=polygon,
        mask=mask,
        area_pixels=int(np.sum(mask)) if mask is not None else 0,
    )
    segments.append(segment)

return segments
```

#### Recursos
- **YOLO Docs**: https://docs.ultralytics.com/modes/segment/
- **Modelo**: `yolo11m-seg.pt` (50MB)
- **Clase Referencia**: `SAHIDetectionService` (patrón similar)

#### Checklist
- [ ] Load model from ModelCache
- [ ] Run YOLO prediction
- [ ] Extract bbox (normalized)
- [ ] Extract class name (apply remapping)
- [ ] Extract polygon mask
- [ ] Create SegmentResult objects
- [ ] Return List[SegmentResult]
- [ ] Test con imagen de prueba
- [ ] Verify coordinate normalization (0.0-1.0)

---

### TAREA 2: Habilitar GPS Location Lookup

**Prioridad**: 🔴 CRÍTICO
**Estimado**: 1-2 horas
**Bloqueador**: Sin GPS, no sabe en qué cultivo procesa

#### Descripción
El GPS lookup está completamente comentado. Actualmente hardcoded `storage_location_id = 1` lo que causa que TODOS los uploads vayan a la misma ubicación.

#### Ubicación
- **Archivo**: `/home/lucasg/proyectos/DemeterDocs/app/services/photo/photo_upload_service.py`
- **Líneas**: 170-189
- **Método**: `PhotoUploadService.upload_photo()`

#### Qué Está Comentado

```python
# Líneas 170-189 (COMENTADAS)
# if gps_coords:
#     location = await self.location_service.get_by_coordinates(...)
#     storage_location_id = location.id
```

#### Qué Implementar

```python
# 1. Extrae GPS del EXIF
from piexif import load as exif_load

try:
    img = Image.open(BytesIO(file_bytes))
    exif_data = exif_load(img.info.get("exif", b""))
    gps_coords = extract_gps_from_exif(exif_data)  # Returns (lat, lon) or None
except Exception as e:
    logger.warning(f"Could not extract EXIF: {e}")
    gps_coords = None

# 2. GPS Lookup
if gps_coords:
    try:
        location = await self.location_service.get_by_coordinates(
            latitude=gps_coords[0],
            longitude=gps_coords[1],
        )
        storage_location_id = location.id if location else 1
        logger.info(f"Found location: {location.name}")
    except Exception as e:
        logger.warning(f"GPS lookup failed: {e}. Using default location.")
        storage_location_id = 1
else:
    logger.warning("No GPS coordinates. Using default location.")
    storage_location_id = 1

# 3. Usar storage_location_id para crear sesión
photo_session = await session_repo.create(
    PhotoProcessingSessionCreate(
        storage_location_id=storage_location_id,  # ← Usar aquí
        original_image_id=image_id,
        status="pending",
    )
)
```

#### Método Helper
Buscar o crear `extract_gps_from_exif()`:

```python
def extract_gps_from_exif(exif_dict: dict) -> tuple[float, float] | None:
    """
    Extrae coordenadas GPS del EXIF.

    Returns:
        (latitude, longitude) o None
    """
    try:
        if "GPS" not in exif_dict:
            return None

        gps = exif_dict["GPS"]

        # GPS IFD tags
        # 2: N/S indicator
        # 4: E/W indicator

        lat_data = gps.get(2)  # [(degrees,), (minutes,), (seconds,)]
        lon_data = gps.get(4)

        if not lat_data or not lon_data:
            return None

        # Convert to decimal degrees
        lat = dms_to_decimal(lat_data)
        lon = dms_to_decimal(lon_data)

        # Apply sign (N/S, E/W)
        lat_ref = gps.get(1)  # b'N' or b'S'
        lon_ref = gps.get(3)  # b'E' or b'W'

        if lat_ref == b'S':
            lat = -lat
        if lon_ref == b'W':
            lon = -lon

        return (lat, lon)
    except Exception as e:
        logger.error(f"Failed to extract GPS: {e}")
        return None

def dms_to_decimal(dms_tuple: tuple) -> float:
    """Convert degrees/minutes/seconds to decimal."""
    degrees = dms_tuple[0][0] / dms_tuple[0][1]
    minutes = dms_tuple[1][0] / dms_tuple[1][1]
    seconds = dms_tuple[2][0] / dms_tuple[2][1]
    return degrees + minutes / 60 + seconds / 3600
```

#### Checklist
- [ ] Descomenta líneas 170-189
- [ ] Implementa extract_gps_from_exif()
- [ ] Implementa GPS lookup con StorageLocationService
- [ ] Add error handling (fallback a location_id=1)
- [ ] Test con foto con GPS
- [ ] Test con foto sin GPS
- [ ] Verify location ID en PhotoProcessingSession

---

### TAREA 3: Fijar Hardcoded Values en Callback

**Prioridad**: 🟠 IMPORTANTE
**Estimado**: 2-3 horas
**Bloqueador**: Batches creados con datos incorrectos

#### Descripción
El callback persistencia tiene 3 valores hardcoded que debería leer de la configuración:
- `product_id = 1`
- `product_state_id = 1`
- `user_id = 1` (usuario ML)

#### Ubicación
- **Archivo**: `/home/lucasg/proyectos/DemeterDocs/app/tasks/ml_tasks.py`
- **Función**: `_persist_ml_results()`
- **Líneas**: 1740-1762

#### Código Actual

```python
# MALO ❌
product_id = 1              # Hardcoded
product_state_id = 1        # Hardcoded
user_id = 1                 # Hardcoded ML user
```

#### Código Nuevo

```python
# BUENO ✅
# 1. Fetch PhotoProcessingSession
photo_session = session.query(PhotoProcessingSession).filter_by(
    id=session_id
).first()

if not photo_session:
    raise ValueError(f"Session {session_id} not found")

# 2. Get StorageLocationConfig (contains product/state rules)
storage_location_config = session.query(StorageLocationConfig).filter_by(
    storage_location_id=photo_session.storage_location_id,
    active=True,
).first()

# 3. Read from config, fallback to defaults
if storage_location_config:
    product_id = storage_location_config.product_id
    product_state_id = storage_location_config.expected_product_state_id
    user_id = storage_location_config.ml_processor_user_id  # New field
else:
    # Fallback if no config exists
    logger.warning(f"No config for location {photo_session.storage_location_id}")
    product_id = 1
    product_state_id = 1
    user_id = 1

logger.info(f"Using product={product_id}, state={product_state_id}, user={user_id}")
```

#### Schema Changes Needed

Extender `StorageLocationConfig`:

```python
# app/models/storage_location_config.py

class StorageLocationConfig(Base):
    # ... existing fields ...

    # New fields to add:
    expected_product_state_id: int = Column(
        Integer,
        ForeignKey("product_states.product_state_id"),
        nullable=True,
        doc="Expected state for plants in this location (SEED, SEEDLING, etc)"
    )

    ml_processor_user_id: int = Column(
        Integer,
        ForeignKey("users.user_id"),
        nullable=True,
        doc="User ID for ML processing (sistema user)"
    )
```

#### Checklist
- [ ] Extender StorageLocationConfig (add 2 nuevos fields)
- [ ] Crear migration Alembic
- [ ] Modificar _persist_ml_results() para leer de config
- [ ] Add fallback a defaults
- [ ] Agregar logging
- [ ] Test con config existente
- [ ] Test sin config (fallback)

---

### TAREA 4: Mejorar Visualización (Polígonos Reales)

**Prioridad**: 🟠 IMPORTANTE
**Estimado**: 1-2 horas
**Impacto**: Visualizaciones más precisas

#### Descripción
La visualización usa polígonos simplificados (rectangles por banda). Debería usar las máscaras reales de estimación.

#### Ubicación
- **Archivo**: `/home/lucasg/proyectos/DemeterDocs/app/tasks/ml_tasks.py`
- **Función**: `_generate_visualization()`
- **Líneas**: 1905-1914

#### Código Actual

```python
# MALO ❌ - Polígono simplificado rectangular
points = np.array([
    [0, band_y_start],
    [image.shape[1], band_y_start],
    [image.shape[1], band_y_end],
    [0, band_y_end],
], np.int32)

cv2.fillPoly(overlay, [points], (255, 0, 0))
```

#### Problema Principal
1. Polígonos son rectángulos simples (no refleja área real)
2. Ancho de imagen hardcoded a `image.shape[1]` (asume 4000px)

#### Código Nuevo

```python
# BUENO ✅ - Usar máscara real de estimación

# 1. Fetch all estimations para esta sesión
estimations = session.query(Estimation).filter_by(
    session_id=session_id
).all()

# 2. For cada estimation:
for est in estimations:
    # 2a. Get vegetation polygon (GeoJSON o list of points)
    if hasattr(est, 'vegetation_polygon') and est.vegetation_polygon:
        # Parse polygon
        if isinstance(est.vegetation_polygon, str):
            polygon_data = json.loads(est.vegetation_polygon)
        else:
            polygon_data = est.vegetation_polygon

        # Convert GeoJSON to points
        if polygon_data.get("type") == "Polygon":
            coords = polygon_data["coordinates"][0]  # Outer ring
            points = np.array([[int(x), int(y)] for x, y in coords], np.int32)

            # Draw on overlay
            overlay = image.copy()
            cv2.fillPoly(overlay, [points], (255, 0, 0))  # Azul
            overlay = cv2.GaussianBlur(overlay, (9, 9), 0)
            image = cv2.addWeighted(image, 0.8, overlay, 0.2, 0)
    else:
        # Fallback: simplified band (backwards compatibility)
        band_y_start = (est.band_number - 1) * (image.shape[0] // 4)
        band_y_end = est.band_number * (image.shape[0] // 4)

        points = np.array([
            [0, band_y_start],
            [image.shape[1], band_y_start],
            [image.shape[1], band_y_end],
            [0, band_y_end],
        ], np.int32)

        overlay = image.copy()
        cv2.fillPoly(overlay, [points], (255, 0, 0))
        overlay = cv2.GaussianBlur(overlay, (9, 9), 0)
        image = cv2.addWeighted(image, 0.8, overlay, 0.2, 0)
```

#### Schema Changes Needed

Extender `BandEstimation`:

```python
# app/models/estimation.py

class Estimation(Base):
    # ... existing fields ...

    vegetation_polygon: dict = Column(
        JSON,
        nullable=True,
        doc="GeoJSON polygon of vegetation area (Polygon type)"
    )

    # Example GeoJSON:
    # {
    #   "type": "Polygon",
    #   "coordinates": [
    #     [[x1,y1], [x2,y2], [x3,y3], [...], [x1,y1]]
    #   ]
    # }
```

#### Checklist
- [ ] Extender Estimation model (add vegetation_polygon field)
- [ ] Crear migration Alembic
- [ ] Modificar BandEstimationService para generar polygon
- [ ] Modificar _generate_visualization() para usar polygon real
- [ ] Test con polígonos pequeños
- [ ] Test con polígonos grandes
- [ ] Verify GeoJSON format

---

### TAREA 5: Implementar Empty Container Detection

**Prioridad**: 🟠 IMPORTANTE
**Estimado**: 2-3 horas
**Impacto**: Detecta cajas/bandejas vacías

#### Descripción
Actualmente `total_empty_containers` siempre es 0. Debería detectar contenedores sin plantas.

#### Ubicación
- **Archivo**: `/home/lucasg/proyectos/DemeterDocs/app/tasks/ml_tasks.py`
- **Función**: `ml_child_task()` (retorna resultados)
- **Línea**: 983

#### Código Actual

```python
# MALO ❌
total_empty_containers = 0  # Hardcoded
```

#### Algoritmo de Detección

```python
def detect_empty_containers(
    segments: List[SegmentResult],
    detections: List[DetectionResult],
) -> int:
    """
    Detecta contenedores sin plantas.

    Lógica:
    1. Para cada segmento:
       - Calcular área del segmento
       - Calcular área de detecciones en el segmento
       - Si (detected_area / segment_area) < threshold → VACÍO
       - Threshold: 5% de cobertura

    Returns:
        Número de contenedores vacíos
    """

    empty_count = 0

    for segment in segments:
        # Get segment mask area
        segment_area = segment.area_pixels

        # Get detections in this segment
        dets_in_segment = [
            d for d in detections
            if is_detection_in_segment(d, segment)
        ]

        # Calculate detection area
        detection_area = sum(d.width_px * d.height_px for d in dets_in_segment)

        # Calculate coverage percentage
        coverage = detection_area / segment_area if segment_area > 0 else 0.0

        # Check if empty (< 5% coverage)
        if coverage < 0.05:
            empty_count += 1
            logger.info(f"Empty container: {segment.container_type} "
                       f"(coverage: {coverage:.1%})")

    return empty_count

def is_detection_in_segment(detection: DetectionResult, segment: SegmentResult) -> bool:
    """Check if detection center is within segment."""
    x1, y1, x2, y2 = segment.bbox
    center_x_norm = detection.center_x_px / 3000  # Asume 3000px width
    center_y_norm = detection.center_y_px / 2000  # Asume 2000px height

    return x1 <= center_x_norm <= x2 and y1 <= center_y_norm <= y2
```

#### Código a Implementar

En `ml_child_task()`, cambiar:

```python
# ANTES
total_empty_containers = 0

# DESPUÉS
total_empty_containers = detect_empty_containers(segments, detections)
```

#### Checklist
- [ ] Implementar detect_empty_containers()
- [ ] Implementar is_detection_in_segment()
- [ ] Add coverage threshold (5%)
- [ ] Add logging para debugging
- [ ] Test con segmentos vacíos
- [ ] Test con segmentos llenos
- [ ] Verify counting

---

## 🟡 Tareas de Mejora (Nice-to-have)

### MEJORA 1: Circuit Breaker con Redis Persistence

**Prioridad**: 🟡 MEJORA
**Estimado**: 1-2 horas
**Beneficio**: Persiste estado entre reinicio de workers

#### Problema
Circuit breaker state se pierde si el worker reinicia.

#### Solución
Usar Redis para almacenar el estado.

```python
# app/services/circuit_breaker_service.py

class CircuitBreakerService:
    def __init__(self, redis_client):
        self.redis = redis_client
        self.key_prefix = "circuit_breaker:"
        self.timeout = 300  # 5 min

    def check_state(self, name: str) -> bool:
        """Check if circuit is open. Raises if open."""
        state = self.redis.get(f"{self.key_prefix}{name}:state")
        opened_at = self.redis.get(f"{self.key_prefix}{name}:opened_at")

        if state == "open":
            if int(time.time()) - int(opened_at) > self.timeout:
                # Timeout expired, go to half_open
                self.redis.setex(
                    f"{self.key_prefix}{name}:state",
                    10,  # 10 seg para probar
                    "half_open"
                )
                return True
            else:
                raise CircuitBreakerException(f"Circuit {name} is OPEN")

        return True

    def record_failure(self, name: str):
        """Record a failure, potentially open circuit."""
        failures = self.redis.incr(f"{self.key_prefix}{name}:failures")

        if failures >= 5:
            self.redis.setex(
                f"{self.key_prefix}{name}:state",
                self.timeout,
                "open"
            )
            self.redis.set(
                f"{self.key_prefix}{name}:opened_at",
                int(time.time())
            )
            # Alert ops
```

---

### MEJORA 2: Category Counts Aggregation

**Prioridad**: 🟡 MEJORA
**Estimado**: 1 hora
**Beneficio**: Estadísticas por tipo de planta

#### Problema
`category_counts = {}` siempre está vacío.

#### Solución

```python
# En ml_aggregation_callback()

# Query all detections grouped by class
category_counts = {}
detections = session.query(Detection).filter_by(
    session_id=session_id
).all()

for det in detections:
    class_name = det.class_name
    category_counts[class_name] = category_counts.get(class_name, 0) + 1

logger.info(f"Category breakdown: {category_counts}")

# Actualizar PhotoProcessingSession
photo_session.category_counts = category_counts
```

---

### MEJORA 3: Better Confidence Calculation

**Prioridad**: 🟡 MEJORA
**Estimado**: 1-2 horas
**Beneficio**: Confianza más realista en estimaciones

#### Problema
`estimation_confidence = 0.75` es hardcoded.

#### Solución

```python
def calculate_estimation_confidence(
    band_estimation: BandEstimation,
    total_detections: int,
) -> float:
    """Calculate confidence based on detection density."""

    # Factors:
    # 1. If many detections in band → high confidence
    # 2. If smooth area → high confidence
    # 3. If empty area → low confidence

    # Band detection ratio
    band_area_px = (band_estimation.band_y_end - band_estimation.band_y_start) * 3000
    if band_area_px == 0:
        return 0.5

    detection_density = band_estimation.processed_area_px / band_area_px

    # Confidence based on density
    if detection_density > 0.7:
        confidence = 0.85  # Many detections → reliable
    elif detection_density > 0.3:
        confidence = 0.70  # Some detections
    else:
        confidence = 0.50  # Few detections → less reliable

    return confidence
```

---

### MEJORA 4: Operational Alerts

**Prioridad**: 🟡 MEJORA
**Estimado**: 1-2 horas
**Beneficio**: Alertas cuando circuit abre

#### Implementación

```python
# En ml_tasks.py

def alert_ops_team(message: str):
    """Send alert to ops via email/Slack."""
    # Option 1: Email
    send_email(
        to=config.OPS_EMAIL,
        subject="DemeterAI Alert: Circuit Breaker Opened",
        body=message
    )

    # Option 2: Slack
    slack_client = WebClient(token=config.SLACK_BOT_TOKEN)
    slack_client.chat_postMessage(
        channel="ops-alerts",
        text=f":red_circle: {message}"
    )

# Usage:
if failures >= 5:
    alert_ops_team(f"Circuit breaker OPEN for S3 uploads after {failures} failures")
```

---

### MEJORA 5: Performance Optimizations

**Prioridad**: 🟡 MEJORA
**Estimado**: 2-4 horas
**Beneficio**: 5-10x más rápido

#### 1. Async Bulk Insert

```python
# Actual (ORM, lento)
session.bulk_save_objects(detections)

# Mejorado (asyncpg COPY, 100x más rápido)
from sqlalchemy import insert

await session.execute(
    insert(Detection).values(detections_dicts)
)
```

#### 2. Thread Pool para S3

```python
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(max_workers=10)

# S3 uploads en paralelo
futures = [
    executor.submit(upload_to_s3, obj)
    for obj in objects
]

results = [f.result() for f in futures]
```

#### 3. GPU Memory Management

```python
# En ml_child_task

import torch

# Process in batches
for i in range(0, len(segments), batch_size=10):
    batch = segments[i:i+batch_size]
    # Process batch

    # Clear GPU cache every 10 batches
    if i % 100 == 0:
        torch.cuda.empty_cache()
```

---

## 📊 Summary de Tareas

| Tarea | Prioridad | Horas | Bloqueador | Status |
|-------|-----------|-------|-----------|--------|
| SegmentationService | 🔴 CRÍTICO | 2-3 | SI | ⏳ TODO |
| GPS Lookup | 🔴 CRÍTICO | 1-2 | SI | ⏳ TODO |
| Hardcoded Values | 🟠 IMPORTANTE | 2-3 | NO | ⏳ TODO |
| Visualización | 🟠 IMPORTANTE | 1-2 | NO | ⏳ TODO |
| Empty Containers | 🟠 IMPORTANTE | 2-3 | NO | ⏳ TODO |
| **SUBTOTAL CRÍTICO** | | **8-11** | | |
| Redis Circuit Breaker | 🟡 MEJORA | 1-2 | NO | ⏳ TODO |
| Category Counts | 🟡 MEJORA | 1 | NO | ⏳ TODO |
| Confidence Calc | 🟡 MEJORA | 1-2 | NO | ⏳ TODO |
| Ops Alerts | 🟡 MEJORA | 1-2 | NO | ⏳ TODO |
| Performance | 🟡 MEJORA | 2-4 | NO | ⏳ TODO |
| **SUBTOTAL MEJORAS** | | **6-11** | | |
| **TOTAL** | | **14-22** | | |

---

## 🚀 Plan de Ejecución Recomendado

### Sprint 1 (3-4 días)
1. SegmentationService (CRÍTICO)
2. GPS Lookup (CRÍTICO)
3. Testing de ambas

### Sprint 2 (2-3 días)
4. Hardcoded Values
5. Visualización
6. Empty Containers

### Sprint 3 (1 día)
7. Mejoras (todas las 🟡)

---

## ✅ Checklist Final

- [ ] Todas las tareas CRÍTICAS completadas
- [ ] Tests pasando (pytest -v)
- [ ] Coverage ≥ 80%
- [ ] Code review completado
- [ ] Documentación actualizada
- [ ] Producción lista (100% del flujo)

---

**Documento**: Plan de Implementación
**Generado**: 2025-10-24
**Responsable**: DemeterAI Engineering Team
