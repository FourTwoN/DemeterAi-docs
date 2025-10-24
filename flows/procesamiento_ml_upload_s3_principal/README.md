# 📊 DemeterAI v2.0 - Flujo Principal de Procesamiento ML

> **Documentación Completa del Flujo de Upload, S3 y Procesamiento ML**

---

## 🎯 Resumen Ejecutivo

Este directorio contiene la **documentación completa del flujo principal de DemeterAI v2.0**, que es el corazón de la aplicación.

### ¿Qué es el Flujo Principal?

Es el proceso de **extremo a extremo** que:

1. **Recibe** fotografías de cultivos vía API
2. **Almacena** en S3 con circuit breaker
3. **Procesa** con ML (YOLO v11 + SAHI)
4. **Estima** plantas no detectadas
5. **Genera** visualizaciones
6. **Crea** lotes de inventario automáticamente

### Capacidades

- ✅ Procesa **600,000+ plantas** en inventario
- ✅ Detecta **800+ plantas por foto** (SAHI)
- ✅ Estima plantas **ocultas/ocluidas**
- ✅ **88% implementado** (ready para producción)
- ✅ Manejo de **fallos parciales** (fault-tolerant)

---

## 📚 Documentos en Este Directorio

### 1. **FLUJO_PRINCIPAL_DOCUMENTACION.md** (50+ páginas)
La documentación **más completa y detallada**.

```
Contiene:
  • Arquitectura general del flujo
  • Descripción FASE por FASE
  • Código actual de cada componente
  • Estado de implementación (88%)
  • Clases y servicios utilizados
  • Detalle de archivos
  • QUÉ FALTA completar
  • Mejoras identificadas
  • Checklist de completitud

USO: Leer cuando necesites entender TODO en profundidad
```

**Ir a**: `FLUJO_PRINCIPAL_DOCUMENTACION.md`

---

### 2. **QUICK_REFERENCE.md** (Quick Lookup)
Referencia **rápida** para encontrar información.

```
Contiene:
  • Índice rápido de archivos
  • Dónde encontrar cada componente
  • Flujo de ejecución (paso a paso)
  • Lo que ESTÁ HECHO ✅
  • Lo que FALTA 🚧
  • Estadísticas de implementación
  • Patrones clave usados
  • Bash commands útiles
  • Cheat sheet

USO: Usar cuando necesites buscar algo específico RÁPIDO
```

**Ir a**: `QUICK_REFERENCE.md`

---

### 3. **IMPLEMENTACION_TASKS.md** (Execution Plan)
**Plan ejecutable** de qué falta completar.

```
Contiene:
  • 5 Tareas CRÍTICAS (bloquean producción)
  • 5 Mejoras (nice-to-have)
  • Para cada tarea:
    - Descripción
    - Ubicación exacta
    - Pseudocódigo
    - Checklist
    - Estimado de horas

  CRÍTICAS (8-11 horas):
    1. SegmentationService (75% → 100%)
    2. GPS Location Lookup (0% → 100%)
    3. Hardcoded Values (90% → 100%)
    4. Visualización (95% → 100%)
    5. Empty Container Detection (0% → 100%)

USO: Cuando estés listo para IMPLEMENTAR las correcciones
```

**Ir a**: `IMPLEMENTACION_TASKS.md`

---

### 4. **FLUJO PRINCIPAL V3-2025-10-07-201442.mmd**
Diagrama **visual** del flujo (Mermaid).

```
Contiene:
  • Visualización completa en Mermaid
  • 6 fases coloreadas
  • 250+ nodos
  • Flujos de éxito y error
  • Legenda y estilos

Renderizar con:
  - GitHub (automático)
  - Mermaid Live Editor
  - VSCode (Mermaid extension)

USO: Para entender VISUALMENTE cómo funciona
```

---

## 🗂️ Estructura de Lectura Recomendada

### Opción A: Entender Todo (30 min)
1. **Leer este README** (2 min)
2. **Ver el diagrama Mermaid** (5 min)
3. **Leer QUICK_REFERENCE: "Lo que ESTÁ HECHO"** (10 min)
4. **Leer QUICK_REFERENCE: "Lo que FALTA"** (10 min)

### Opción B: Ir Directo a Implementar (2-3 horas)
1. **IMPLEMENTACION_TASKS.md: TAREA 1** (Segmentation)
2. **Implementar + Tesear**
3. **IMPLEMENTACION_TASKS.md: TAREA 2** (GPS Lookup)
4. **etc...**

### Opción C: Entender en Profundidad (2-3 horas)
1. **FLUJO_PRINCIPAL_DOCUMENTACION.md: Resumen Ejecutivo**
2. **FLUJO_PRINCIPAL_DOCUMENTACION.md: Arquitectura General**
3. **Leer cada FASE del flujo**
4. **Revisar Clases y Servicios**

---

## 🎨 Diagrama Visual (Simplificado)

```
┌─────────────────────────────────────────────────────────────┐
│                    USUARIO SUBE FOTO                         │
│              POST /api/v1/stock/photo                        │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│          FASE 1: Validación & Upload                        │
│  ✅ Valida archivo (20MB, JPEG/PNG/WebP)                  │
│  ✅ Extrae GPS (EXIF)                                      │
│  ✅ Upload a S3 (original + thumbnail)                     │
│  ✅ Crea PhotoProcessingSession (BD)                       │
│  ⚠️  GPS lookup deshabilitado (TODO)                       │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│          FASE 2: Orquestación ML (Celery)                   │
│  ✅ Verifica circuit breaker                               │
│  ✅ Dispara patrón CHORD (paralelo)                        │
│  ✅ CPU worker (parent task)                               │
└───────────────────────┬─────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
    ┌─────────┐    ┌─────────┐    ┌─────────┐
    │ GPU #1  │    │ GPU #2  │    │ GPU #3  │
    │ Worker  │    │ Worker  │    │ Worker  │
    │         │    │         │    │         │
    │ ml_     │    │ ml_     │    │ ml_     │
    │ child   │    │ child   │    │ child   │
    └────┬────┘    └────┬────┘    └────┬────┘
         │               │              │
         │  Cada worker: │              │
         │  1. Segment   │              │
         │  2. SAHI Detect             │
         │  3. Band Estimate            │
         │                              │
         └──────────────┬───────────────┘
                        │ (Aggregation)
                        ▼
        ┌──────────────────────────────┐
        │  FASE 4: Callback (CPU)      │
        │  ✅ Persist a BD             │
        │  ✅ Generar visualización    │
        │  ✅ Upload viz a S3          │
        │  ✅ Crear stock batches      │
        │  ✅ Cleanup                  │
        └──────────────┬───────────────┘
                       │
                       ▼
        ┌──────────────────────────────┐
        │  FASE 5: Frontend Polling    │
        │  ✅ GET /api/v1/stock/tasks/ │
        │  ✅ Mostrar resultados       │
        └──────────────────────────────┘
```

---

## 📊 Estado de Implementación

```
COMPONENTE                    ESTADO      AVANCE
═══════════════════════════════════════════════════════════
API Controller               ✅ 100%      ██████████
S3 Service                   ✅ 100%      ██████████
SAHI Detection               ✅ 100%      ██████████
Band Estimation              ✅ 100%      ██████████
ML Orchestration             ✅ 100%      ██████████
Celery Tasks                 ✅ 100%      ██████████
Circuit Breaker              ✅ 100%      ██████████
Models (28)                  ✅ 100%      ██████████
Repositories (27)            ✅ 100%      ██████████
Schemas (26)                 ✅ 100%      ██████████
───────────────────────────────────────────────────────────
Photo Upload                 ⚠️  85%      █████████░
ML Callback                  ⚠️  95%      █████████░
Segmentation                 ⚠️  75%      ███████░░░
Visualization                ⚠️  95%      █████████░
GPS Lookup                   ⚠️  10%      █░░░░░░░░
───────────────────────────────────────────────────────────
TOTAL                        🟠 88%      ████████░░
```

---

## 🔴 Crítico - Lo Que Bloquea Producción

| Ítem | Archivo | Estado | Estimado |
|------|---------|--------|----------|
| **IO_QUEUE Orfanado** ⭐ **NUEVO** | `ml_tasks.py` | No usado (0%) | 3-6h |
| **SegmentationService** | `segmentation_service.py` | Incompleto (75%) | 2-3h |
| **GPS Location Lookup** | `photo_upload_service.py` | Deshabilitado (10%) | 1-2h |
| **Circuit Breaker Tests** | Necesita verificación | Untested | 1h |

**Total para 100%**: ~11-16 horas

⚠️ **NUEVA PRIORIDAD**: IO_QUEUE debe ser PRIMERA (bloquea el pipeline 16-65 segundos)

---

## 🚀 Cómo Empezar

### Para LEER (Entender)
```bash
# Opción 1: Todo detallado
cat FLUJO_PRINCIPAL_DOCUMENTACION.md | less

# Opción 2: Quick reference
cat QUICK_REFERENCE.md | grep -A 20 "Lo que ESTÁ HECHO"

# Opción 3: Solo tareas pendientes
cat IMPLEMENTACION_TASKS.md | grep "TAREA"
```

### Para IMPLEMENTAR (Corregir)
```bash
# Ver tareas pendientes
cat IMPLEMENTACION_TASKS.md

# Ir a archivo específico
vim /home/lucasg/proyectos/DemeterDocs/app/services/ml_processing/segmentation_service.py

# Buscar línea específica
grep -n "def segment_image" app/services/ml_processing/segmentation_service.py
```

### Para VISUALIZAR (Entender)
```bash
# Ver diagrama (si tienes MermaidJS)
mermaid "FLUJO PRINCIPAL V3-2025-10-07-201442.mmd"

# O en GitHub (renderiza automático)
# Abre en GitHub: flows/procesamiento_ml_upload_s3_principal/FLUJO PRINCIPAL V3-2025-10-07-201442.mmd
```

---

## 📝 Tabla de Contenidos Rápida

### FLUJO_PRINCIPAL_DOCUMENTACION.md
- [x] Resumen Ejecutivo
- [x] Arquitectura General
- [x] Fases del Flujo (1-5)
- [x] Estado de Implementación
- [x] Clases y Servicios
- [x] Detalle de Archivos
- [x] **Qué Falta**
- [x] Mejoras Identificadas
- [x] Checklist de Completitud

### QUICK_REFERENCE.md
- [x] Dónde Encontrar Todo
- [x] Flujo de Ejecución Paso a Paso
- [x] Lo Que Está HECHO
- [x] Lo Que FALTA Completar
- [x] Estadísticas
- [x] Cómo Completar Lo Que Falta
- [x] Testing
- [x] Bash Cheat Sheet

### IMPLEMENTACION_TASKS.md
- [x] TAREA 1: Segmentation (CRÍTICA)
- [x] TAREA 2: GPS Lookup (CRÍTICA)
- [x] TAREA 3: Hardcoded Values (IMPORTANTE)
- [x] TAREA 4: Visualización (IMPORTANTE)
- [x] TAREA 5: Empty Containers (IMPORTANTE)
- [x] MEJORA 1-5: Optimizaciones
- [x] Plan de Ejecución
- [x] Checklist Final

---

## 🎯 Próximos Pasos (Prioridad)

### Semana 1 (Sprint 1)
1. ✅ **Leer** documentación (1-2 horas)
2. ⏳ **Completar SegmentationService** (2-3 horas)
3. ⏳ **Habilitar GPS Lookup** (1-2 horas)
4. ⏳ **Tests & Verificación** (1-2 horas)

### Semana 2 (Sprint 2)
5. ⏳ Fijar hardcoded values
6. ⏳ Mejorar visualización
7. ⏳ Implementar empty container detection

### Semana 3+ (Mejoras)
8. ⏳ Circuit breaker con Redis
9. ⏳ Category counts
10. ⏳ Performance optimizations

---

## 💡 Tips Importantes

### Tip 1: Arquitectura
El flujo sigue **Clean Architecture**: Controller → Service → Repository
```python
# ✅ CORRECTO: Service → Service
PhotoUploadService(S3ImageService, LocationService)

# ❌ INCORRECTO: Service → Repository
PhotoUploadService(S3ImageRepository)
```

### Tip 2: Celery Pattern
Usa **Chord** para paralelismo:
```python
chord([child_task] × N)(callback_task)
# Ejecuta N child tasks en paralelo → callback con resultados agregados
```

### Tip 3: GPU Workers
DEBE usar `--pool=solo` (no prefork/threads):
```bash
celery worker --pool=solo --concurrency=1 --queues=gpu_queue
```

### Tip 4: 3-Tier Cache para Imágenes
```
PostgreSQL (rápido) → /tmp (local) → S3 (fallback)
```

---

## 📞 Preguntas Frecuentes

**P: ¿Por dónde empiezo?**
R: Lee QUICK_REFERENCE.md (10 min), luego decide si lees todo o vas directo a implementar.

**P: ¿Cuál es la tarea más urgente?**
R: SegmentationService (bloquea TODO el flujo).

**P: ¿Cuándo estará 100% completo?**
R: ~8-11 horas de desarrollo (1 sprint).

**P: ¿Dónde está el código?**
R: Ver QUICK_REFERENCE.md → "Dónde Encontrar Todo"

**P: ¿Qué pruebas existen?**
R: Ver QUICK_REFERENCE.md → "Testing"

---

## 📂 Archivos en Este Directorio

```
flows/procesamiento_ml_upload_s3_principal/
├── README.md                                    ← Estás aquí
├── FLUJO_PRINCIPAL_DOCUMENTACION.md            ← Documentación completa
├── QUICK_REFERENCE.md                          ← Quick lookup
├── IMPLEMENTACION_TASKS.md                     ← Tareas por hacer
└── FLUJO PRINCIPAL V3-2025-10-07-201442.mmd   ← Diagrama Mermaid
```

---

## ✅ Checklist de Lectura

- [ ] Leer este README (5 min)
- [ ] Ver diagrama Mermaid (5 min)
- [ ] Leer QUICK_REFERENCE completo (20 min)
- [ ] Elegir: Implementar o Leer Todo
  - [ ] Si implementar: Ir a IMPLEMENTACION_TASKS.md
  - [ ] Si leer: Ir a FLUJO_PRINCIPAL_DOCUMENTACION.md

---

## 🎓 Recursos Adicionales

Otros documentos en el proyecto relacionados:

```bash
# Base de datos (source of truth)
database/database.mmd

# Arquitectura
engineering_plan/03_architecture_overview.md

# Problemas de Sprint 02
CRITICAL_ISSUES.md

# Plan del sprint actual
backlog/01_sprints/sprint-03-services/sprint-goal.md

# Tareas en el kanban
backlog/03_kanban/01_ready/     # Listas para empezar
backlog/03_kanban/02_in-progress/  # En progreso
```

---

## 🏆 Conclusión

El flujo principal de DemeterAI es un **sistema robusto y escalable** que maneja **600,000+ plantas**. Está **88% implementado** y listo para completarse en **~1 sprint** (8-11 horas).

**Próximo paso**: Elige uno de los documentos anteriores y empieza. 🚀

---

**Documento**: README del Flujo Principal
**Versión**: 1.0
**Última actualización**: 2025-10-24
**Estado**: 🟠 88% Implementado

**¿Preguntas?** Consulta los documentos específicos o revisa el código fuente directo.
