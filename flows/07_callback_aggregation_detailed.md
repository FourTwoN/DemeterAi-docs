# Diagram 07: Callback Aggregation (Celery Chord)

**Version:** 1.0.0
**Date:** 2025-10-08
**Parent Diagram:** 01_complete_pipeline_v4.mmd
**Related Diagrams:** 04_ml_parent_segmentation_detailed.mmd, 05_sahi_detection_child_detailed.mmd, 06_boxes_plugs_detection_detailed.mmd

## Purpose

This diagram documents the **Celery Chord callback task** that aggregates results from ALL parallel child tasks (plant detection + infrastructure detection) into a unified session summary. This is the final step before results are available to the frontend.

## Scope

**Input:**
- `child_results` (List[dict]): Results from all child tasks (diagrams 05 & 06)
- `session_id_pk` (UUID): Session identifier

**Output:**
- `session_summary` (dict): Aggregated statistics, quality scores, field metrics
- Database persistence: `session_summaries` table
- Redis cache: For fast frontend access
- Optional webhook: External notification

**Performance Target:** 100-500ms (fast aggregation, no heavy computation)

## Celery Chord Pattern

### What is a Chord?

```python
from celery import chord, group

# Parent task spawns children
chord(
    group(
        detect_plants_sahi.s(img1_id, img1_data),
        detect_plants_sahi.s(img2_id, img2_data),
        detect_plants_sahi.s(img3_id, img3_data),
        # ... 50 child tasks
    ),
    aggregate_callback.s(session_id_pk)  # THIS DIAGRAM (07)
).apply_async()
```

**How it works:**
1. **Parent** (diagram 04) spawns N child tasks in parallel
2. **Children** (diagrams 05, 06) execute independently on GPU workers
3. **Chord waits** until ALL children complete (or timeout)
4. **Callback** (this diagram) receives list of ALL results
5. **Callback aggregates** and persists session summary

**Critical behavior:**
- Callback BLOCKS until all children finish
- Slowest child determines total session time
- If one child fails, callback still executes with partial results

## Key Components

### 1. Result Validation & Partial Failure Handling (lines 64-121)

**Problem:** What if some child tasks fail?

**Solution:** Continue with partial results, log failures

```python
failures = [r for r in child_results if r['status'] != 'success']
successes = [r for r in child_results if r['status'] == 'success']

failure_summary = {
    'total_images': len(child_results),
    'successful': len(successes),
    'failed': len(failures),
    'failure_details': [...]
}

# INSERT failure logs for debugging
db.execute("""
    INSERT INTO task_failures (session_id, image_id, error_message, ...)
    VALUES (...)
""")
```

**Common failure reasons:**
1. S3 download timeout (network issue)
2. GPU OOM (image too large for VRAM)
3. Model inference error (corrupted image)
4. Database connection lost
5. Child task timeout (exceeded 120s hard limit)

**Design decision:** Don't fail entire session due to 1-2 bad images. Continue with partial results and log failures for later retry.

### 2. Plant Detection Aggregation (lines 151-202)

**Aggregated statistics:**
```python
total_estimated = sum(r['estimated_count'] for r in plant_results)  # 9834
total_detected = sum(r['detected_count'] for r in plant_results)    # 7821

# Session-level confidence (proportion of HIGH confidence images)
high_conf_count = sum(1 for r in plant_results if r['confidence'] == 'HIGH')
if high_conf_count / len(plant_results) > 0.8:
    session_confidence = 'HIGH'  # 80%+ images are HIGH confidence
elif high_conf_count / len(plant_results) > 0.5:
    session_confidence = 'MEDIUM'  # 50-80% images are HIGH
else:
    session_confidence = 'LOW'  # < 50% images are HIGH
```

**Performance tracking:**
```python
avg_processing_time = np.mean([r['processing_time'] for r in plant_results])  # 19.3s
total_gpu_time = sum(r['processing_time'] for r in plant_results)  # 965s = 16 min

# For billing: GPU hours consumed
gpu_hours = total_gpu_time / 3600  # 0.27 hours
```

### 3. Infrastructure Detection Aggregation (lines 211-267)

**Aggregate by class across all images:**
```python
from collections import defaultdict

total_by_class = defaultdict(int)
locations_by_class = defaultdict(list)

for result in infrastructure_results:
    for class_name, data in result['by_class'].items():
        total_by_class[class_name] += data['count']

        # Collect ALL GPS locations across all images
        for loc in data['locations']:
            locations_by_class[class_name].append({
                'image_id': result['image_id'],
                'gps': loc['gps'],
                'confidence': loc['confidence']
            })
```

**Example result:**
```json
{
  "total_infrastructure": 27,
  "by_class": {
    "electrical_box": {
      "count": 15,
      "locations": [
        {"image_id": "...", "gps": [-34.56, -58.12], "confidence": 0.85},
        {"image_id": "...", "gps": [-34.57, -58.13], "confidence": 0.78},
        ...
      ]
    },
    "industrial_plug": {"count": 8, "locations": [...]},
    "electric_meter": {"count": 4, "locations": [...]}
  }
}
```

**Use case:** Generate maintenance map with ALL electrical infrastructure GPS points.

### 4. Field-Level Metrics Calculation (lines 276-331)

**Calculate plant density:**
```python
session = db.query("""
    SELECT field_id, total_area_m2, gps_bounds, images_expected
    FROM sessions WHERE id = :session_id_pk
""").one()

field_area_ha = session.total_area_m2 / 10000  # m² → hectares
plant_density = total_estimated / field_area_ha  # plants/ha

# Example: 9834 plants / 12.5 ha = 787 plants/ha
```

**Industry benchmarks:**
- **Low density:** < 500 plants/ha (sparse planting, extensive farming)
- **Normal density:** 500-1000 plants/ha (standard commercial)
- **High density:** > 1000 plants/ha (intensive farming, greenhouses)

**Partial coverage handling:**
```python
images_processed = len(plant_results)  # 50
images_expected = session.images_expected  # 54
coverage_percent = (images_processed / images_expected) * 100  # 92.3%

# Estimate total if full coverage
if coverage_percent < 100:
    estimated_total = total_estimated / (coverage_percent / 100)
    # 9834 / 0.923 = 10656 plants (estimated)
```

### 5. Quality Score Calculation (lines 340-401) 🔥

**Multi-factor quality assessment:**

```python
quality_factors = []

# Factor 1: Confidence distribution (40% weight) - MOST IMPORTANT
confidence_score = (
    high_conf_count * 1.0 +
    medium_conf_count * 0.7 +
    low_conf_count * 0.4
) / len(plant_results)
quality_factors.append(('confidence', confidence_score, 0.4))

# Factor 2: Coverage completeness (30% weight)
coverage_score = min(coverage_percent / 100, 1.0)
quality_factors.append(('coverage', coverage_score, 0.3))

# Factor 3: Processing consistency (20% weight)
# Low variance = consistent image quality
processing_time_cv = np.std(times) / np.mean(times)  # Coefficient of variation
consistency_score = max(0, 1.0 - processing_time_cv)
quality_factors.append(('consistency', consistency_score, 0.2))

# Factor 4: Failure rate (10% weight)
failure_score = 1.0 - (len(failures) / len(child_results))
quality_factors.append(('failures', failure_score, 0.1))

# Weighted average
overall_quality = sum(score * weight for _, score, weight in quality_factors)
```

**Quality bands:**
- `overall_quality >= 0.85`: **'EXCELLENT'** ⭐⭐⭐⭐⭐ (Report ready for customer)
- `overall_quality >= 0.70`: **'GOOD'** ⭐⭐⭐⭐ (Acceptable)
- `overall_quality >= 0.50`: **'FAIR'** ⭐⭐⭐ (Review recommended)
- `overall_quality < 0.50`: **'POOR'** ⭐⭐ (Re-capture images)

**Example calculation:**
```
Confidence score: 0.92 × 0.4 = 0.368
Coverage score:   0.92 × 0.3 = 0.276
Consistency score: 0.78 × 0.2 = 0.156
Failure score:     1.0 × 0.1 = 0.100
────────────────────────────────
Overall quality:             0.87 → EXCELLENT ⭐⭐⭐⭐⭐
```

### 6. Session Summary Structure (lines 410-467)

**Complete summary object:**
```json
{
  "session_id": "uuid-...",
  "field_id": "uuid-...",
  "completed_at": "2025-10-08T15:45:23Z",

  "plant_detection": {
    "total_estimated": 9834,
    "total_detected": 7821,
    "avg_per_image": 196,
    "confidence": "HIGH",
    "images_processed": 50
  },

  "infrastructure_detection": {
    "total_count": 27,
    "by_class": {
      "electrical_box": {"count": 15, "locations": [...]},
      "industrial_plug": {"count": 8, "locations": [...]},
      "electric_meter": {"count": 4, "locations": [...]}
    },
    "images_processed": 12
  },

  "field_metrics": {
    "area_ha": 12.5,
    "plant_density_per_ha": 787,
    "coverage_percent": 92.3,
    "estimated_total_if_full": 10656
  },

  "quality": {
    "overall_score": 0.87,
    "quality_band": "EXCELLENT",
    "factors": {
      "confidence": 0.92,
      "coverage": 0.92,
      "consistency": 0.78,
      "failures": 1.0
    }
  },

  "performance": {
    "total_processing_time_s": 965,
    "avg_processing_time_s": 19.3,
    "images_failed": 0,
    "failure_rate": 0.0
  },

  "status": "completed",
  "warnings": null
}
```

### 7. Webhook Notification (lines 531-579) - Optional

**Notify external systems:**
```python
webhook_url = session.webhook_url  # Optional, configured per session

payload = {
    'event': 'session.completed',
    'session_id': str(session_id_pk),
    'completed_at': datetime.utcnow().isoformat(),
    'summary': session_summary
}

# Async HTTP POST (don't block callback)
async with httpx.AsyncClient() as client:
    try:
        response = await client.post(
            webhook_url,
            json=payload,
            timeout=5.0
        )
    except httpx.HTTPError as e:
        # Log but don't fail callback
        logger.warning(f'Webhook failed: {e}')
```

**Use cases:**
1. **Farm management software:** Notify external system that analysis is complete
2. **PDF report generation:** Trigger downstream report generation service
3. **Email/SMS:** Send notification to farmer with link to results
4. **Billing system:** Trigger invoice generation (GPU hours consumed)

**Design decision:** Webhook failure does NOT fail the callback. Logging only.

### 8. Redis Cache for Frontend (lines 588-618)

**Why cache:**
```python
cache_key = f'session_summary:{session_id_pk}'

redis_client.setex(
    cache_key,
    ttl=3600,  # 1 hour TTL
    value=json.dumps(session_summary)
)
```

**Performance impact:**
| Scenario | Without Cache | With Cache | Speedup |
|----------|--------------|------------|---------|
| Frontend poll (every 2s) | 50ms (DB query) | 1ms (Redis GET) | **50x** |
| User downloads report | 100ms (complex query) | 1ms (Redis GET) | **100x** |

**TTL reasoning:**
- User typically views report immediately after completion
- After 1 hour, report viewed → cache can expire
- Next access: Re-fetch from DB (infrequent, acceptable latency)

## Performance Breakdown

Total time: **100-500ms**

| Phase | Time | % of Total | Notes |
|-------|------|------------|-------|
| Result validation | 5ms | ~2% | Simple list filtering |
| Plant aggregation | 50ms | ~25% | NumPy operations |
| Infrastructure aggregation | 30ms | ~15% | Dictionary operations |
| Field metrics | 10ms | ~5% | 1 DB query + math |
| Quality score | 5ms | ~2% | NumPy statistics |
| DB persist (INSERT + UPDATE) | 15ms | ~7% | 2 queries |
| Redis cache | 5ms | ~2% | Single SET |
| Webhook (optional) | 100ms | ~40% | Async HTTP (if configured) |
| Other | 10ms | ~5% | Python overhead |

**Bottleneck:** Webhook HTTP request (optional, async, non-blocking)

**Why so fast compared to child tasks (15-30s)?**
- No GPU computation
- No image processing
- Simple aggregation (sum, mean, groupby)
- Lightweight database operations
- Runs on CPU pool (gevent, high concurrency)

## Error Handling

### Partial Failures

**Scenario:** 2 out of 50 images failed

**Behavior:**
1. Separate successes (48) from failures (2)
2. Log failures to `task_failures` table
3. Continue aggregation with 48 successful results
4. Include failure count in summary
5. Set warning if failure rate > 10%

```python
if len(failures) / len(child_results) > 0.10:
    warnings.append('high_failure_rate')
    # Alert ops team (> 10% failure unusual)
```

### Database Connection Lost

**Scenario:** Callback executes but DB is down

**Behavior:**
- Celery automatic retry (3 attempts with exponential backoff)
- If all retries fail → task moved to dead letter queue
- Results still in Celery backend (Redis) for 24 hours
- Manual recovery possible

### Redis Unavailable

**Scenario:** Redis cache is down

**Behavior:**
- Cache write fails (non-critical)
- Log warning but continue
- Frontend falls back to DB queries (slower but functional)

## Database Schema

### Tables Used

**`session_summaries`** (INSERT):
```sql
CREATE TABLE session_summaries (
    session_id UUID PRIMARY KEY REFERENCES sessions(id),
    field_id UUID NOT NULL REFERENCES fields(id),
    completed_at TIMESTAMP NOT NULL,

    -- Plant detection
    total_plants_estimated INT NOT NULL,
    total_plants_detected INT NOT NULL,
    plant_density_per_ha FLOAT NOT NULL,
    coverage_percent FLOAT NOT NULL,

    -- Infrastructure
    total_infrastructure INT,
    infrastructure_by_class JSONB,

    -- Quality
    quality_score FLOAT NOT NULL CHECK (quality_score BETWEEN 0 AND 1),
    quality_band VARCHAR(20) CHECK (quality_band IN ('EXCELLENT', 'GOOD', 'FAIR', 'POOR')),

    -- Performance
    total_processing_time_s FLOAT NOT NULL,
    images_processed INT NOT NULL,
    images_failed INT NOT NULL,

    -- Full summary
    summary_json JSONB NOT NULL  -- Complete session_summary dict
);

CREATE INDEX idx_summaries_field ON session_summaries(field_id);
CREATE INDEX idx_summaries_quality ON session_summaries(quality_score DESC);
CREATE INDEX idx_summaries_completed ON session_summaries(completed_at DESC);
```

**`sessions`** (UPDATE):
```sql
UPDATE sessions
SET
    status = 'completed',
    completed_at = NOW(),
    total_plants_estimated = :total_estimated,
    quality_score = :quality_score,
    processing_time_s = :total_processing_time
WHERE id = :session_id_pk;
```

**`task_failures`** (INSERT):
```sql
CREATE TABLE task_failures (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES sessions(id),
    image_id UUID REFERENCES s3_images(id),
    task_type VARCHAR(50),
    error_message TEXT,
    traceback TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_failures_session ON task_failures(session_id);
```

## Code Patterns

### Pattern 1: Weighted Quality Score
```python
def calculate_weighted_score(factors):
    """
    factors: List of (name, score, weight) tuples
    Returns: Weighted average score
    """
    total_score = sum(score * weight for _, score, weight in factors)
    total_weight = sum(weight for _, _, weight in factors)

    assert abs(total_weight - 1.0) < 0.01, "Weights must sum to 1.0"

    return total_score
```

### Pattern 2: Safe Webhook Sending
```python
async def send_webhook_safe(url, payload, timeout=5.0):
    """Send webhook with error handling (don't fail callback)"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=timeout)
            response.raise_for_status()
            return True
    except httpx.HTTPError as e:
        logger.warning(f'Webhook failed: {e}', extra={'url': url})
        return False
```

### Pattern 3: Redis Cache with Fallback
```python
def get_session_summary(session_id):
    """Get summary from cache, fallback to DB"""
    cache_key = f'session_summary:{session_id}'

    # Try cache first
    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached)

    # Fallback to DB
    summary = db.query("""
        SELECT summary_json FROM session_summaries WHERE session_id = :id
    """, {'id': session_id}).scalar()

    # Re-populate cache
    if summary:
        redis_client.setex(cache_key, 3600, json.dumps(summary))

    return summary
```

## Related Diagrams

- **04_ml_parent_segmentation_detailed.mmd:** Spawns the chord that leads to this callback
- **05_sahi_detection_child_detailed.mmd:** Plant detection child task
- **06_boxes_plugs_detection_detailed.mmd:** Infrastructure detection child task
- **08_frontend_polling_detailed.mmd:** Frontend consumes this callback's results

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-10-08 | Initial detailed callback aggregation subflow |

---

**Notes:**
- This is the **final task** in the detection pipeline before frontend presentation
- Quality score is critical for customer trust (transparent quality assessment)
- Redis cache is essential for responsive frontend (50x speedup)
- Partial failure handling ensures robust production system
