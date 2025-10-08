# Diagram 08: Frontend Polling & Result Retrieval

**Version:** 1.0.0
**Date:** 2025-10-08
**Parent Diagram:** 01_complete_pipeline_v4.mmd
**Related Diagrams:** 02_api_entry_detailed.mmd, 07_callback_aggregation_detailed.mmd

## Purpose

This diagram documents the **frontend real-time polling mechanism** that allows web/mobile clients to track processing progress and retrieve final results. This is the final piece connecting the backend pipeline (diagrams 02-07) to the user interface.

## Scope

**Input:**
- `session_id` (UUID): Returned from initial upload API (diagram 02)
- User authentication token

**Output:**
- Real-time progress updates (every 2 seconds)
- Final session summary when complete
- Rendered UI with results, quality assessment, download links

**Performance Target:**
- Poll response: < 100ms (cached)
- Final summary fetch: < 500ms
- Total UI render: < 200ms

## Polling Strategy

### Why Polling?

**Problem:** Backend processes images asynchronously (15-30 minutes). Frontend cannot block waiting.

**Solution:** Long polling with fixed 2-second interval

**Alternatives considered:**
1. **WebSockets** - More efficient, but requires persistent connections (infrastructure complexity)
2. **Server-Sent Events (SSE)** - One-way push, simpler than WebSocket but less browser support
3. **Long Polling (HTTP)** - Simple, universally supported, chosen approach ✓

**Future optimization:** Migrate to WebSocket for real-time updates (reduce server load by 95%)

### Polling Configuration

```javascript
const pollingConfig = {
    interval: 2000,           // 2 seconds (fixed)
    maxRetries: 180,          // 180 × 2s = 6 minutes timeout
    retryBackoff: false,      // Constant interval (could add exponential backoff)
    cacheResults: true,       // Cache last known progress (offline-first)
    stopOnComplete: true      // Stop polling when status === 'completed'
}
```

**Poll rate calculation:**
- 50 images × 20s avg = 1000s total = ~16 minutes
- 16 minutes × 30 polls/minute = 480 total poll requests
- Cost: 480 × 2ms (cache hit) = ~1 second total overhead

**Cost-benefit analysis:**
- Server load: Negligible (Redis cache, 2ms per poll)
- User experience: Excellent (real-time feedback, no page refresh)
- Network cost: Minimal (small JSON payloads, ~1KB each)

## Key Components

### 1. Polling Loop Implementation (lines 84-120)

**JavaScript/TypeScript:**
```javascript
async function startPolling(sessionId) {
    const pollingState = {
        sessionId,
        pollInterval: 2000,
        maxRetries: 180,
        retryCount: 0,
        isPolling: true
    }

    while (pollingState.isPolling && pollingState.retryCount < pollingState.maxRetries) {
        try {
            const progress = await fetchProgress(sessionId)

            if (progress.status === 'completed') {
                // Stop polling, fetch full summary
                await handleCompletion(sessionId)
                break
            }

            // Update UI with progress
            updateProgressUI(progress)

            // Wait for next poll
            await sleep(pollingState.pollInterval)
            pollingState.retryCount++

        } catch (error) {
            handlePollingError(error, pollingState)
        }
    }

    if (pollingState.retryCount >= pollingState.maxRetries) {
        showTimeoutError(sessionId)
    }
}
```

**Key patterns:**
- `async/await` for clean asynchronous code
- `while` loop with exit conditions (completed or timeout)
- Error handling with retry logic
- State management (`pollingState` object)

### 2. Progress Endpoint Handler (lines 160-231)

**FastAPI implementation:**
```python
@router.get('/sessions/{session_id}/progress')
async def get_session_progress(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    current_user: User = Depends(get_current_user)
):
    """Get real-time progress for session"""

    # Permission check
    session = await db.get(Session, session_id)
    if session.user_id != current_user.id:
        raise HTTPException(403, 'Forbidden')

    # Try Redis cache first (CRITICAL for performance)
    cache_key = f'session_progress:{session_id}'
    cached = await redis.get(cache_key)
    if cached:
        return JSONResponse(json.loads(cached))

    # Calculate progress from database
    progress = await calculate_progress(session, db)

    # Cache for 1 second (balance freshness vs load)
    await redis.setex(cache_key, 1, json.dumps(progress))

    # Return 202 Accepted (not 200) if still processing
    status_code = 200 if progress['status'] == 'completed' else 202
    return JSONResponse(progress, status_code=status_code)
```

**Why Redis cache with 1-second TTL:**
- **Without cache:** 480 polls × 50ms DB query = 24 seconds total overhead
- **With cache (1s TTL):** 480 polls × 2ms Redis GET = 1 second total overhead
- **Cache hit rate:** ~98% (multiple clients polling same session)
- **Fresh enough:** 1-second staleness acceptable for progress updates

### 3. Progress Calculation Query (lines 190-231)

**PostgreSQL query:**
```sql
SELECT
    s.status,
    s.images_total,
    COUNT(DISTINCT ds.image_id) as images_completed,
    COUNT(DISTINCT CASE WHEN ds.image_id IS NULL THEN si.id END) as images_failed,
    AVG(ds.processing_time_s) as avg_time_per_image,
    s.created_at as started_at
FROM sessions s
LEFT JOIN s3_images si ON si.session_id = s.id
LEFT JOIN detection_summaries ds ON ds.image_id = si.id
WHERE s.id = :session_id
GROUP BY s.id
```

**Calculate metrics:**
```python
progress_percent = (images_completed / images_total) * 100
estimated_remaining_s = (images_total - images_completed) * avg_time_per_image
```

**Result example:**
```json
{
  "session_id": "uuid-...",
  "status": "processing",
  "progress_percent": 72.5,
  "images_total": 50,
  "images_completed": 36,
  "images_failed": 1,
  "avg_time_per_image_s": 18.3,
  "estimated_remaining_s": 256,
  "started_at": "2025-10-08T10:30:00Z",
  "updated_at": "2025-10-08T10:35:15Z"
}
```

**Performance:** ~30-50ms (with proper indexes on `session_id`, `image_id`)

### 4. Completion Detection & Summary Fetch (lines 287-353)

**Two-phase retrieval:**

**Phase 1: Detect completion** (poll endpoint returns 200 OK)
```javascript
if (response.status === 200 && response.data.status === 'completed') {
    clearInterval(pollingInterval)  // Stop polling
    await fetchFullSummary(sessionId)  // Fetch detailed results
}
```

**Phase 2: Fetch full summary** (separate endpoint for large payload)
```javascript
async function fetchFullSummary(sessionId) {
    const response = await fetch(`/api/v1/sessions/${sessionId}/summary`)
    const summary = await response.json()

    // Render results
    renderResultsSummary(summary)
}
```

**Why separate endpoints:**
1. **Progress endpoint:** Lightweight (500 bytes), polled frequently (every 2s)
2. **Summary endpoint:** Heavy (5-50 KB), fetched once when complete
3. **Separation reduces network cost:** 480 × 500B = 240KB vs single 50KB fetch

**Redis cache critical here:**
```python
# Cache populated by callback (diagram 07)
cache_key = f'session_summary:{session_id}'
cached = await redis.get(cache_key)

if cached:
    return JSONResponse(json.loads(cached))  # ~1ms response
else:
    # Fallback to DB (race condition, callback not finished yet)
    summary = await fetch_from_db(session_id)  # ~100ms response
    await redis.setex(cache_key, 3600, json.dumps(summary))
    return summary
```

**Cache hit rate:** ~95% (callback pre-populates before frontend requests)

### 5. UI Rendering (lines 401-509)

**Component hierarchy:**
```
ResultsPage
├── SummaryCards (total plants, density, quality)
├── QualityBadge (⭐⭐⭐⭐⭐ EXCELLENT)
├── ProgressDetails (images processed, processing time)
├── InfrastructureSection (if present)
│   ├── InfrastructureCounts
│   └── InfrastructureMap
├── DownloadButtons
│   ├── PDFReportButton
│   ├── CSVExportButton
│   ├── GeoJSONButton
│   └── RawDataButton
└── FieldMap (if GPS available)
    ├── FieldBoundary
    ├── DensityHeatmap
    └── InfrastructureMarkers
```

**React example:**
```jsx
function ResultsPage({ summary }) {
    return (
        <div className="results-container">
            <SummaryCards
                totalPlants={summary.plant_detection.total_estimated}
                density={summary.field_metrics.plant_density_per_ha}
                qualityScore={summary.quality.overall_score}
            />

            <QualityBadge
                band={summary.quality.quality_band}
                score={summary.quality.overall_score}
                factors={summary.quality.factors}
            />

            <DownloadButtons
                sessionId={summary.session_id}
                links={summary.download_links}
            />

            {summary.infrastructure_detection && (
                <InfrastructureSection
                    data={summary.infrastructure_detection}
                />
            )}

            <FieldMap
                boundary={summary.field_boundary}
                detections={summary.plant_detection}
                infrastructure={summary.infrastructure_detection}
            />
        </div>
    )
}
```

### 6. Quality Badge Rendering (lines 441-474)

**Visual design:**
```javascript
function QualityBadge({ band, score, factors }) {
    const config = {
        'EXCELLENT': {
            color: '#51cf66',
            icon: '⭐⭐⭐⭐⭐',
            message: 'High-quality results ready for customer delivery'
        },
        'GOOD': {
            color: '#4dabf7',
            icon: '⭐⭐⭐⭐',
            message: 'Good results. Minor quality factors noted.'
        },
        'FAIR': {
            color: '#ffd43b',
            icon: '⭐⭐⭐',
            message: 'Fair results. Manual review recommended.'
        },
        'POOR': {
            color: '#ff6b6b',
            icon: '⭐⭐',
            message: 'Low quality. Consider re-capturing images.'
        }
    }

    const { color, icon, message } = config[band]

    return (
        <div className="quality-badge" style={{ borderColor: color }}>
            <div className="quality-icon">{icon}</div>
            <div className="quality-score">{(score * 100).toFixed(1)}%</div>
            <div className="quality-message">{message}</div>
            <FactorBreakdown factors={factors} />
        </div>
    )
}
```

**Factor breakdown:**
```
Confidence: 92% ✓
Coverage:   92% ✓
Consistency: 78% ⚠️
Failures:   100% ✓
```

### 7. Download Options (lines 483-509)

**Available exports:**

| Format | Description | Generation Time | Size | Use Case |
|--------|-------------|----------------|------|----------|
| **PDF Report** | Executive summary, maps, recommendations | ~5s (on-demand) | 2-5 MB | Customer delivery, presentations |
| **CSV Export** | Per-image statistics, coordinates | Instant (pre-generated) | 50-500 KB | Excel analysis, data science |
| **GeoJSON** | Field boundaries, detection points | ~2s (on-demand) | 100-500 KB | QGIS, ArcGIS, geospatial analysis |
| **Raw Data (ZIP)** | Original images, JSON metadata | Instant (pre-signed S3 URLs) | 500MB-2GB | Archival, re-processing |

**PDF report generation:**
```python
@router.get('/sessions/{session_id}/report.pdf')
async def generate_pdf_report(session_id: UUID):
    # Check cache first (report generated previously)
    cache_key = f'pdf_report:{session_id}'
    cached_url = await redis.get(cache_key)
    if cached_url:
        return RedirectResponse(cached_url)

    # Generate PDF on-demand
    summary = await get_session_summary(session_id)
    pdf_bytes = await generate_pdf(summary)

    # Upload to S3
    s3_url = await upload_to_s3(pdf_bytes, f'reports/{session_id}.pdf')

    # Cache S3 URL for 7 days
    await redis.setex(cache_key, 604800, s3_url)

    return RedirectResponse(s3_url)
```

## Performance Breakdown

**Complete user journey timing:**

| Phase | Time | Details |
|-------|------|---------|
| **Upload images** | 5-30s | Multipart form upload, S3 transfer |
| **Initial response** | 100ms | API creates session, returns `session_id` |
| **Start polling** | 1ms | Initialize polling loop |
| **Poll iterations** | 480 × 2ms = 1s | Redis cache hits, 2s interval |
| **Processing (backend)** | 15-30 min | GPU inference (diagrams 04-07) |
| **Completion detection** | 2ms | Poll returns 200 OK |
| **Fetch summary** | 1ms | Redis cache hit |
| **Render UI** | 100-200ms | React rendering, map initialization |
| **Total overhead** | ~30s | Network + polling + render |

**User perceives:**
- Upload: 10s
- "Processing" state: 16 minutes (with live progress bar)
- Results appear: Instant (< 500ms after completion)

## Error Handling

### 1. Polling Timeout (6 minutes)

**Scenario:** Session takes > 6 minutes (unusual)

**Behavior:**
```javascript
if (retryCount >= maxRetries) {
    showError({
        title: 'Processing Timeout',
        message: 'Processing is taking longer than expected.',
        actions: [
            { label: 'Refresh', onClick: () => location.reload() },
            { label: 'Contact Support', onClick: () => openSupport(sessionId) }
        ]
    })
}
```

**Recovery options:**
1. Manual refresh (continue polling)
2. Email notification when ready (backend sends email)
3. Contact support with `session_id`

### 2. Network Errors

**Scenario:** API unavailable, network timeout

**Exponential backoff:**
```javascript
async function handleNetworkError(error, pollingState) {
    const retryDelay = Math.min(30, Math.pow(2, pollingState.errorCount)) * 1000
    pollingState.errorCount++

    // Show warning after 3 failed attempts
    if (pollingState.errorCount >= 3) {
        showNetworkWarning()
    }

    // Wait with backoff, then retry
    await sleep(retryDelay)

    // Max 5 retries before showing fatal error
    if (pollingState.errorCount >= 5) {
        showFatalError('Network unavailable')
    }
}
```

**Retry delays:**
- Retry 1: 2s delay
- Retry 2: 4s delay
- Retry 3: 8s delay (show warning)
- Retry 4: 16s delay
- Retry 5: 30s delay (max)
- After 5: Fatal error

### 3. Authentication Expiration (401)

**Scenario:** User token expires during long processing

**Behavior:**
```javascript
if (response.status === 401) {
    // Save current state
    sessionStorage.setItem('resume_session_id', sessionId)

    // Redirect to login
    window.location.href = '/login?return=/results'
}

// After login, resume polling
const resumeSessionId = sessionStorage.getItem('resume_session_id')
if (resumeSessionId) {
    startPolling(resumeSessionId)
}
```

### 4. Rate Limiting (429)

**Scenario:** Too many requests (unusual, frontend respects 2s interval)

**Behavior:**
```javascript
if (response.status === 429) {
    const retryAfter = response.headers.get('Retry-After') || 10

    // Double the poll interval temporarily
    pollingState.pollInterval *= 2

    await sleep(retryAfter * 1000)
}
```

## Optimization Opportunities

### 1. Migrate to WebSocket (Future)

**Current:** HTTP polling every 2s

**Future:** WebSocket push notifications

**Benefits:**
- Reduce server load by 95% (no polling, only push on updates)
- Instant notifications (no 2s delay)
- Lower network cost (no redundant requests)

**Trade-offs:**
- Infrastructure complexity (WebSocket server, connection pooling)
- Browser compatibility (though widely supported now)
- Firewall/proxy issues (some corporate networks block WebSockets)

**Implementation:**
```javascript
const ws = new WebSocket(`wss://api.demeterai.com/sessions/${sessionId}/subscribe`)

ws.onmessage = (event) => {
    const progress = JSON.parse(event.data)

    if (progress.status === 'completed') {
        ws.close()
        await fetchFullSummary(sessionId)
    } else {
        updateProgressUI(progress)
    }
}
```

### 2. Service Worker Cache (PWA)

**Benefit:** Offline-first, cache progress for instant page loads

```javascript
// Service worker caches last known progress
self.addEventListener('fetch', (event) => {
    if (event.request.url.includes('/progress')) {
        event.respondWith(
            caches.match(event.request)
                .then(cached => cached || fetch(event.request))
        )
    }
})
```

### 3. Adaptive Poll Interval

**Current:** Fixed 2s interval

**Future:** Adapt based on progress rate

```javascript
// Slow down polling as session completes
if (progress.progress_percent < 50) {
    pollInterval = 2000  // 2s (fast updates early)
} else if (progress.progress_percent < 90) {
    pollInterval = 5000  // 5s (slower near end)
} else {
    pollInterval = 10000  // 10s (very slow at 90%+)
}
```

**Benefit:** Reduce server load by 60% with no UX impact

## Related Diagrams

- **02_api_entry_detailed.mmd:** Initial upload that returns `session_id`
- **07_callback_aggregation_detailed.mmd:** Generates the summary fetched by frontend
- **04_ml_parent_segmentation_detailed.mmd:** Backend processing tracked by polling

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-10-08 | Initial detailed frontend polling subflow |

---

**Notes:**
- Polling is simple and reliable (chosen for MVP)
- Redis cache is CRITICAL for performance (2ms vs 50ms responses)
- WebSocket migration recommended for v2.0 (95% load reduction)
- Quality badge builds customer trust (transparent quality assessment)
