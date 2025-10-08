# ML Parent - Segmentation & Orchestration

## Purpose

GPU task that orchestrates the entire ML pipeline: loads YOLO model, performs segmentation, validates requirements (GPS, config, density), and spawns parallel child tasks using Celery Chord pattern.

## Scope

- **Level**: Full detail (GPU orchestration)
- **Audience**: ML engineers, system architects
- **Detail**: Model management, warning states, Celery patterns

## Key Components

### 1. Model Singleton Pattern
```python
worker_id = os.getpid() % num_gpus
model_key = f'yolo_v11_seg_{worker_id}'
if model_key not in model_cache:
  model = YOLO('yolo11m-seg.pt')
  model.to(f'cuda:{worker_id}')
  model_cache[model_key] = model
```

**Benefit**: Load model once per GPU worker (~2s), reuse for all subsequent tasks.

### 2. Warning States (Graceful Degradation)

| State | Trigger | Action |
|-------|---------|--------|
| `needs_location` | No GPS or outside cultivation | User assigns location manually |
| `needs_config` | No storage_location_config | Admin configures product + packaging |
| `needs_calibration` | No density_parameters | Manual calibration required |

**Not Failures**: Photo stored, user completes manually.

### 3. PostGIS Geolocation
```sql
SELECT sl.id FROM storage_locations sl
WHERE ST_Contains(
  sl.geojson_coordinates,
  ST_MakePoint(lon, lat)
)
```

**Performance**: ~15ms with SP-GiST spatial index.

### 4. YOLO v11 Segmentation
```python
results = model.predict(
  image,
  conf=0.30,    # Confidence threshold
  iou=0.50,     # NMS threshold
  imgsz=1024,   # Input size
  device='cuda:0',
  half=True     # FP16 for speed
)
```

**Classes**: segment (0), cajon (1), almacigo (2), plug (3)

### 5. Celery Chord Pattern
```python
chord(
  group(*child_tasks),        # Parallel children
  aggregate_results.s(session_id_pk)  # Callback
).apply_async()
```

**Result**: Parent releases GPU, children run in parallel, callback aggregates results.

## Performance

- **Model Load** (first): ~2s
- **Model Load** (cached): ~1ms
- **EXIF Extraction**: ~20ms
- **PostGIS Query**: ~15ms
- **YOLO Segmentation**: ~500ms (GPU)
- **Mask Processing**: ~200ms per mask
- **Total**: ~2-3 minutes (mostly waiting for children)

## Related Diagrams

- **Complete Pipeline**: `flows/01_complete_pipeline_v4.mmd`
- **SAHI Child**: `flows/05_sahi_detection_child_detailed.mmd` (next)
- **Callback**: `flows/07_callback_aggregate_batches_detailed.mmd`

---

**Version**: 1.0 | **Updated**: 2025-10-07
