# 🚨 CORRECCIÓN CRÍTICA: IO_QUEUE Orfanado - S3 Uploads No Usando Celery

**Fecha**: 2025-10-24
**Prioridad**: 🔴 CRÍTICA
**Impacto**: Arquitectura vs Implementación no alineadas

---

## 📋 Resumen Ejecutivo

Se descubrió una **discrepancia CRÍTICA** entre lo que la arquitectura planea y lo que está implementado:

### ❌ Lo que DEBERÍA pasar
```
S3 uploads (original, thumbnail, visualization)
  → Despachan tareas Celery
    → Routan a io_queue
      → Workers gevent (50 concurrent)
        → Ejecutan en paralelo
```

### ✅ Lo que REALMENTE pasa
```
Original upload → Service sync (asyncio.to_thread) ✓
Thumbnail upload → Service sync (asyncio.to_thread) ✓
Visualization uploads → ml_aggregation_callback DIRECT boto3 (BLOQUEA) ✗
```

---

## 🔍 Lo Que Encontramos

### El io_queue ESTÁ declarado pero NO se usa

**Ubicación**: `app/celery_app.py`

#### ✅ CONFIGURADO (Líneas 110-121)
```python
app.conf.task_queues = (
    Queue("default", Exchange("default"), routing_key="default"),
    Queue("gpu_queue", Exchange("gpu", type="direct"), routing_key="gpu"),
    Queue("cpu_queue", Exchange("cpu", type="direct"), routing_key="cpu"),
    Queue("io_queue", Exchange("io", type="direct"), routing_key="io"),  # ← AQUÍ
)
```

#### ✅ WORKER CONFIGURADO (Líneas 188-194)
```bash
# Worker con gevent pool para 50 tareas concurrentes
celery -A app.celery_app worker \
  --pool=gevent \
  --concurrency=50 \
  --queues=io_queue \
  --hostname=io@%h
```

#### ✅ ROUTING PATTERN DEFINIDO (Línea 69-78)
```python
task_routes={
    "app.tasks.upload_*": {"queue": "io_queue"},  # ← Pattern para tasks upload_*
}
```

#### ❌ PERO NO HAY TASKS QUE USEN ESTE PATRÓN

**En `/app/tasks/ml_tasks.py` NO existen:**
- ❌ `upload_original_s3_task()`
- ❌ `upload_thumbnail_s3_task()`
- ❌ `upload_visualization_s3_task()`
- ❌ Ninguna tarea matching `app.tasks.upload_*`

---

## 🔴 DÓNDE SUCEDEN LOS S3 UPLOADS ACTUALMENTE

### 1. UPLOAD ORIGINAL (API Layer)
**Archivo**: `app/services/photo/photo_upload_service.py:247-278`
**Tipo**: Service call (async)
**Implementación**:
```python
async def upload_photo(self, file: UploadFile, user_id: int):
    # ...
    original_image = await self.s3_service.upload_original(
        file_bytes=file_bytes,
        session_id=session.session_id,
    )
```

**Cómo funciona**:
```python
# app/services/photo/s3_image_service.py:106
async def upload_original(self, ...):
    await asyncio.to_thread(
        self.s3_client.put_object,  # boto3 sync call wrapped
        Bucket=bucket,
        Key=s3_key,
        Body=file_bytes,
    )
```

**Problema**: Se ejecuta en el thread de FastAPI durante el request
**Solución**: Debería usar `upload_original_s3_task.delay()`

---

### 2. UPLOAD THUMBNAIL (API Layer)
**Archivo**: `app/services/photo/photo_upload_service.py:280-312`
**Tipo**: Service call (async)
**Implementación**:
```python
thumbnail_bytes = generate_thumbnail(file_bytes, size=300)
thumbnail_image = await self.s3_service.upload_thumbnail(
    file_bytes=thumbnail_bytes,
    session_id=session.session_id,
)
```

**Problema**: Se ejecuta en el thread de FastAPI durante el request
**Solución**: Debería usar `upload_thumbnail_s3_task.delay()`

---

### 3. UPLOAD VISUALIZATION (Callback Layer) 🚨 MÁS CRÍTICO
**Archivo**: `app/tasks/ml_tasks.py:797-887` (en `ml_aggregation_callback()`)
**Tipo**: Direct boto3 calls (SYNC, BLOCKING)

**Implementación**:
```python
@app.task(queue="cpu_queue")
def ml_aggregation_callback(results, session_id):
    # ... aggregation logic ...

    # 🔴 UPLOAD VISUALIZATION (DIRECT BOTO3 - BLOQUEA)
    s3_client = boto3.client("s3")
    s3_client.put_object(  # ← SYNC, no await, no Celery
        Bucket=settings.S3_BUCKET_ORIGINAL,
        Key=viz_s3_key,
        Body=viz_bytes,
        ContentType="image/avif",
    )

    # 🔴 UPLOAD THUMBNAIL ORIGINAL (DIRECT BOTO3)
    s3_client.put_object(
        Bucket=settings.S3_BUCKET_ORIGINAL,
        Key=thumbnail_original_s3_key,
        Body=thumbnail_original_bytes,
    )

    # 🔴 UPLOAD THUMBNAIL PROCESSED (DIRECT BOTO3)
    s3_client.put_object(
        Bucket=settings.S3_BUCKET_ORIGINAL,
        Key=thumbnail_processed_s3_key,
        Body=thumbnail_processed_bytes,
    )

    # 🔴 COMMIT DATABASE
    db_session.commit()
```

**Problemas**:
1. ❌ **BLOQUEA el callback** - Las 3 uploads son síncronas
2. ❌ **NO usa Celery** - Debería usar `io_queue`
3. ❌ **Sin error handling** - Si S3 falla, toda la sesión falla
4. ❌ **Sin circuit breaker** - A diferencia de S3ImageService
5. ❌ **Ralentiza el pipeline** - La callback se bloquea esperando S3

**Tiempo estimado**:
- Generación visualization: 1-5 segundos
- Upload visualization (3-20MB): 5-30 segundos
- Upload thumbnails (2x 1-5MB): 10-30 segundos
- **Total**: 16-65 segundos **BLOQUEANDO el callback**

---

## 📊 Tabla Comparativa: Upload Locations

| # | Image | Ubicación | Implementación Actual | Cola Celery | Sync/Async | ¿PROBLEMA? |
|---|-------|-----------|----------------------|-------------|-----------|-----------|
| 1 | Original | photo_upload_service.py | S3ImageService (async) | ❌ Ninguna | Async (to_thread) | ⚠️ No usa io_queue |
| 2 | Thumbnail | photo_upload_service.py | S3ImageService (async) | ❌ Ninguna | Async (to_thread) | ⚠️ No usa io_queue |
| 3 | **Visualization** | **ml_tasks.py callback** | **Direct boto3** | **❌ Ninguna** | **Sync (BLOQUEA)** | 🔴 **CRÍTICA** |
| 4 | **Original Thumb (ML)** | **ml_tasks.py callback** | **Direct boto3** | **❌ Ninguna** | **Sync (BLOQUEA)** | 🔴 **CRÍTICA** |
| 5 | **Processed Thumb** | **ml_tasks.py callback** | **Direct boto3** | **❌ Ninguna** | **Sync (BLOQUEA)** | 🔴 **CRÍTICA** |

---

## 🚀 SOLUCIÓN: Crear Tasks de Upload para io_queue

### TAREA 1: Crear `upload_s3_task` Base

**Archivo a crear**: `app/tasks/s3_upload_tasks.py`

```python
from app.celery_app import app
from app.services.photo.s3_image_service import S3ImageService

@app.task(bind=True, queue="io_queue", max_retries=3)
def upload_original_s3_task(self, file_bytes: bytes, session_id: int, filename: str):
    """
    Upload original image to S3 using io_queue (gevent worker).

    Args:
        file_bytes: Image binary data
        session_id: PhotoProcessingSession ID
        filename: S3 key/filename

    Returns:
        dict with S3 upload result
    """
    try:
        s3_service = S3ImageService()

        # Upload to S3
        result = s3_service.upload_original(
            file_bytes=file_bytes,
            session_id=session_id,
            filename=filename,
        )

        return {
            "status": "success",
            "session_id": session_id,
            "filename": filename,
            "result": result,
        }

    except Exception as exc:
        # Retry with exponential backoff
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

        return {
            "status": "success",
            "session_id": session_id,
            "filename": filename,
            "result": result,
        }

    except Exception as exc:
        countdown = 2 ** self.request.retries
        raise self.retry(exc=exc, countdown=countdown)


@app.task(bind=True, queue="io_queue", max_retries=3)
def upload_visualization_s3_task(self, file_bytes: bytes, session_id: int):
    """
    Upload visualization image to S3 using io_queue.

    This is the CRITICAL task that was blocking the callback.
    """
    try:
        s3_service = S3ImageService()

        s3_key = f"uploads/{session_id}/processed.avif"

        result = s3_service.upload_visualization(
            file_bytes=file_bytes,
            s3_key=s3_key,
            content_type="image/avif",
        )

        return {
            "status": "success",
            "session_id": session_id,
            "s3_key": s3_key,
            "result": result,
        }

    except Exception as exc:
        countdown = 2 ** self.request.retries
        raise self.retry(exc=exc, countdown=countdown)
```

---

### TAREA 2: Refactorizar `ml_aggregation_callback()` para usar tasks

**Archivo**: `app/tasks/ml_tasks.py`

#### ANTES (BLOQUEA):
```python
@app.task(queue="cpu_queue")
def ml_aggregation_callback(results, session_id):
    # ... aggregation ...

    # 🔴 DIRECT S3 UPLOAD - BLOQUEA
    s3_client = boto3.client("s3")
    s3_client.put_object(
        Bucket=settings.S3_BUCKET_ORIGINAL,
        Key=viz_s3_key,
        Body=viz_bytes,
        ContentType="image/avif",
    )

    # 🔴 MORE DIRECT UPLOADS...
```

#### DESPUÉS (ASÍNCRONO):
```python
from app.tasks.s3_upload_tasks import (
    upload_visualization_s3_task,
    upload_thumbnail_s3_task,
)

@app.task(queue="cpu_queue")
def ml_aggregation_callback(results, session_id):
    # ... aggregation ...

    # ✅ DISPATCH VISUALIZATION UPLOAD (no bloquea)
    upload_task = upload_visualization_s3_task.delay(
        file_bytes=viz_bytes,
        session_id=session_id,
    )

    # ✅ DISPATCH THUMBNAIL UPLOADS (no bloquea)
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

    # ✅ UPDATE SESSION (sin esperar S3)
    _mark_session_completed(session_id, ...)

    return {
        "status": "success",
        "session_id": session_id,
        "upload_tasks": {
            "visualization": str(upload_task.id),
            "thumbnails": "2 tasks dispatched",
        }
    }
```

---

### TAREA 3: Refactorizar `PhotoUploadService` para usar tasks (OPCIONAL)

**Archivo**: `app/services/photo/photo_upload_service.py`

#### OPCIÓN A: Mantener como está (service sync)
```python
# ✓ Actual: Direct async boto3 en FastAPI request
await self.s3_service.upload_original(file_bytes, session_id)
```

**Ventaja**: Rápido, simple
**Desventaja**: No aprovecha io_queue

#### OPCIÓN B: Usar tasks de Celery
```python
from app.tasks.s3_upload_tasks import upload_original_s3_task

# Dispatch async task
upload_original_s3_task.delay(
    file_bytes=file_bytes,
    session_id=session_id,
    filename=f"{session_id}/original.jpg",
)

# Return 202 ACCEPTED sin esperar upload
return PhotoUploadResponse(
    task_id=upload_task.id,
    session_id=session_id,
    status="pending",
)
```

**Ventaja**: Libera FastAPI thread, usa io_queue
**Desventaja**: Upload ocurre en background

**Recomendación**: MANTENER OPCIÓN A (actual) - ya es async

---

## 📊 Impacto de la Solución

### ANTES (Estado Actual)
```
ML Pipeline Execution Time:
├─ Segmentation: 2-3s
├─ SAHI Detection: 3-5s
├─ Band Estimation: 2-3s
├─ Aggregation: 1-2s
└─ S3 Uploads (BLOQUEADO): 16-65s  🔴 CRÍTICO
────────────────────────────────
TOTAL: 24-78 segundos
```

### DESPUÉS (Con Upload Tasks)
```
ML Pipeline Execution Time:
├─ Segmentation: 2-3s
├─ SAHI Detection: 3-5s
├─ Band Estimation: 2-3s
├─ Aggregation: 1-2s
└─ S3 Uploads (ASYNC): 0s (dispatched)
────────────────────────────────
TOTAL: 8-13 segundos

S3 Uploads (io_queue, background): 16-65s (paralelo)
```

**Mejora**: 3-8x más rápido para completar ML pipeline

---

## 🎯 Plan de Implementación

### PASO 1: Crear archivo `s3_upload_tasks.py` (1-2 horas)
```bash
touch app/tasks/s3_upload_tasks.py
# Implementar 3 tasks (upload_original, upload_thumbnail, upload_visualization)
```

### PASO 2: Refactorizar `ml_aggregation_callback()` (1-2 horas)
```bash
# En app/tasks/ml_tasks.py
# Cambiar direct boto3 por task.delay() calls
```

### PASO 3: Actualizar tests (1-2 horas)
```bash
# tests/unit/tasks/test_s3_upload_tasks.py
# tests/integration/test_ml_pipeline_with_uploads.py
```

### PASO 4: Verificar io_queue (30 min)
```bash
# Startup io_queue worker
celery -A app.celery_app worker --pool=gevent --queues=io_queue --concurrency=50

# Verify tasks route correctly
```

**Total estimado**: 3-6 horas

---

## 📝 Checklist

- [ ] Crear `app/tasks/s3_upload_tasks.py`
- [ ] Implementar `upload_original_s3_task()`
- [ ] Implementar `upload_thumbnail_s3_task()`
- [ ] Implementar `upload_visualization_s3_task()`
- [ ] Refactorizar `ml_aggregation_callback()` para usar tasks
- [ ] Remover imports de boto3 directo de `ml_tasks.py`
- [ ] Crear tests para las nuevas tasks
- [ ] Crear test de integración (ml_pipeline → io_queue uploads)
- [ ] Documentar en FLUJO_PRINCIPAL_DOCUMENTACION.md
- [ ] Startup io_queue worker
- [ ] Verificar que tasks routan a io_queue
- [ ] Load test con múltiples imágenes simultáneas
- [ ] Verify gevent pool maneja 50 concurrent uploads

---

## 🚨 Discrepancia Detectada

### Arquitectura Planificada (celery_app.py):
```
io_queue configured with:
  - Exchange: "io" (direct type)
  - Routing key: "io"
  - Task pattern: "app.tasks.upload_*"
  - Worker: gevent, concurrency=50
```

### Implementación Real (ml_tasks.py):
```
❌ NO hay tasks matching "app.tasks.upload_*"
❌ S3 uploads happen with direct boto3 in callback
❌ io_queue never receives any tasks
❌ Gevent workers never start with actual work
```

### Resultado:
- ✅ Infrastructure configured (not wasted)
- ❌ Not utilized (orphaned)
- 🔴 Callback blocks on S3 (performance issue)
- 🔴 No error handling (reliability issue)

---

## 📚 Referencias

- **Queue Configuration**: `app/celery_app.py:110-121`
- **Worker Configuration**: `app/celery_app.py:188-194`
- **Task Routing Pattern**: `app/celery_app.py:69-78`
- **Callback S3 Uploads**: `app/tasks/ml_tasks.py:797-887`
- **S3 Service**: `app/services/photo/s3_image_service.py`
- **Test Coverage**: `tests/unit/celery/test_worker_topology.py`

---

## ✅ Conclusión

El `io_queue` está **completamente preparado pero sin tareas que lo usen**. Esta es una **corrección CRÍTICA** porque:

1. **Performance**: Callback se bloquea 16-65s esperando S3
2. **Reliability**: Sin circuit breaker, error handling
3. **Scalability**: No aprovecha gevent workers (50 concurrent)
4. **Architecture**: Desvío entre plan e implementación

**Prioridad**: 🔴 **CRÍTICA** para próximo sprint

Estimar 3-6 horas para implementar las upload tasks y refactorizar callback.

---

**Documento creado**: 2025-10-24
**Autor**: Claude Code + Team Leader
**Estado**: Ready for implementation
