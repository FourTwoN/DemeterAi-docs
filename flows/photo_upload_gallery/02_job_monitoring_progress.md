# Diagram 02: Job Monitoring & Progress Tracking

**Version:** 1.0.0
**Date:** 2025-10-08
**Parent Diagram:** 00_comprehensive_view.mmd
**Related Diagrams:** 01_photo_upload_initiation.mmd, 03_photo_gallery_view.mmd

## Purpose

This diagram documents the **job monitoring and progress tracking mechanism** that allows users to track the status of uploaded photos as they undergo ML processing. This provides real-time feedback and maintains visibility for 24-48 hours.

## Scope

**Input:**
- `upload_session_id` (UUID): Returned from upload endpoint
- User authentication token

**Output:**
- Real-time job status updates (every 2 seconds)
- Progress percentage and ETA
- Job list with individual status per photo
- Completion notification

**Performance Target:**
- Poll response: < 50ms (Redis cache)
- Job list visibility: 24-48 hours
- Progress accuracy: Within 10% of actual completion

## Monitoring Strategy

### Why Polling?

**Problem:** ML processing takes 2-3 minutes per photo. Users need feedback without blocking.

**Solution:** HTTP long polling with 2-second interval

**Alternatives considered:**
1. **WebSockets** - More efficient, but requires persistent connections (infrastructure complexity) ❌
2. **Server-Sent Events (SSE)** - One-way push, less browser support ❌
3. **HTTP Polling** - Simple, universally supported, chosen ✓

**Future optimization:** Migrate to WebSocket for real-time updates (v2.0)

### Polling Configuration

```javascript
const pollingConfig = {
    interval: 2000,           // 2 seconds (fixed)
    maxPolls: 2160,          // 2160 × 2s = ~120 minutes max
    timeout: 120000,         // 2 minutes per request timeout
    backoffEnabled: false,   // Constant interval (no backoff)
    stopOnComplete: true,    // Stop when all jobs complete
    persistResults: true     // Cache last known state
}
```

**Why 2-second interval?**
- **Fast enough**: Users see updates quickly (sub-3s latency)
- **Not too fast**: Doesn't overload server (30 requests/minute)
- **Good balance**: Between responsiveness and efficiency

**Cost calculation:**
- 50 photos × 7 min avg = 350 seconds total (with 4 parallel workers)
- 350 seconds × 0.5 polls/second = 175 total poll requests
- Cost: 175 × 2ms (cache hit) = ~0.35 seconds total overhead

## Key Components

### 1. Job List UI Component (lines 120-200)

**What users see:**
- **Job list table** with columns:
  - Thumbnail (small preview)
  - Filename
  - Status badge (pending/processing/completed/failed)
  - Progress bar (fake, based on average time)
  - ETA countdown
- **Overall progress** at top (X of Y complete)
- **Auto-refresh** every 2 seconds

**React/TypeScript implementation:**
```tsx
interface Job {
    job_id: string
    image_id: string
    filename: string
    status: 'pending' | 'processing' | 'completed' | 'failed'
    progress_percent: number
    started_at?: string
    completed_at?: string
    error_message?: string
    result?: {
        session_id: string
        total_detected: number
        storage_location_id?: number
    }
}

interface JobListProps {
    uploadSessionId: string
}

function JobList({ uploadSessionId }: JobListProps) {
    const [jobs, setJobs] = useState<Job[]>([])
    const [summary, setSummary] = useState({
        total: 0,
        pending: 0,
        processing: 0,
        completed: 0,
        failed: 0,
        overall_progress: 0
    })
    const [isPolling, setIsPolling] = useState(true)

    useEffect(() => {
        let pollingInterval: NodeJS.Timeout

        const pollStatus = async () => {
            try {
                const response = await fetch(
                    `/api/v1/photos/jobs/status?upload_session_id=${uploadSessionId}`,
                    {
                        headers: {
                            'Authorization': `Bearer ${getToken()}`
                        }
                    }
                )

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`)
                }

                const data = await response.json()
                setJobs(data.jobs)
                setSummary(data.summary)

                // Stop polling if all jobs complete or failed
                if (data.summary.completed + data.summary.failed >= data.summary.total) {
                    setIsPolling(false)
                    clearInterval(pollingInterval)
                    showCompletionNotification(data.summary)
                }

            } catch (error) {
                console.error('Polling error:', error)
                // Continue polling (don't stop on transient errors)
            }
        }

        // Initial fetch
        pollStatus()

        // Start polling
        if (isPolling) {
            pollingInterval = setInterval(pollStatus, 2000)
        }

        return () => clearInterval(pollingInterval)

    }, [uploadSessionId, isPolling])

    return (
        <div className="job-list-container">
            <ProgressSummary summary={summary} />
            <JobTable jobs={jobs} />
        </div>
    )
}
```

### 2. Progress Summary Component (lines 240-300)

**Visual design:**
```tsx
function ProgressSummary({ summary }: { summary: Summary }) {
    const { total, completed, failed, processing, pending, overall_progress } = summary

    return (
        <div className="progress-summary">
            <div className="progress-bar-container">
                <div
                    className="progress-bar-fill"
                    style={{ width: `${overall_progress}%` }}
                />
                <div className="progress-text">
                    {completed + failed} of {total} photos processed ({overall_progress.toFixed(1)}%)
                </div>
            </div>

            <div className="status-badges">
                {processing > 0 && (
                    <span className="badge badge-blue">
                        {processing} Processing
                    </span>
                )}
                {pending > 0 && (
                    <span className="badge badge-gray">
                        {pending} Pending
                    </span>
                )}
                {completed > 0 && (
                    <span className="badge badge-green">
                        {completed} Completed
                    </span>
                )}
                {failed > 0 && (
                    <span className="badge badge-red">
                        {failed} Failed
                    </span>
                )}
            </div>

            {processing > 0 && (
                <div className="eta-message">
                    Estimated time remaining: {calculateETA(processing, 7)} minutes
                </div>
            )}
        </div>
    )
}
```

### 3. Fake Progress Bar Logic (lines 340-420)

**Why "fake" progress?**
- **Problem**: Celery doesn't provide accurate progress during ML inference
- **Solution**: Simulate progress based on average processing time
- **Accuracy**: Within 10-20% of actual (good enough for UX)

**Implementation:**
```javascript
function calculateFakeProgress(job: Job): number {
    /*
    Fake progress bar based on elapsed time and average processing time

    Formula:
        progress = min(95, (elapsed / avg_time) * 100)

    We cap at 95% to avoid showing 100% before actual completion
    */

    if (job.status === 'completed') {
        return 100
    }

    if (job.status === 'failed') {
        return 0
    }

    if (job.status === 'pending') {
        return 0
    }

    if (!job.started_at) {
        return 0
    }

    // Calculate elapsed time
    const startTime = new Date(job.started_at).getTime()
    const now = Date.now()
    const elapsedSeconds = (now - startTime) / 1000

    // Average processing time (from historical data)
    const avgProcessingTimeSeconds = 420  // 7 minutes

    // Calculate progress
    const progress = Math.min(95, (elapsedSeconds / avgProcessingTimeSeconds) * 100)

    return Math.round(progress)
}

function calculateETA(job: Job): string {
    /*
    Calculate estimated time remaining

    Returns:
        "2 minutes" or "30 seconds"
    */

    if (job.status !== 'processing') {
        return 'N/A'
    }

    const startTime = new Date(job.started_at).getTime()
    const now = Date.now()
    const elapsedSeconds = (now - startTime) / 1000

    const avgProcessingTimeSeconds = 420  // 7 minutes
    const remainingSeconds = Math.max(0, avgProcessingTimeSeconds - elapsedSeconds)

    if (remainingSeconds > 60) {
        const minutes = Math.ceil(remainingSeconds / 60)
        return `${minutes} minute${minutes > 1 ? 's' : ''}`
    } else {
        return `${Math.ceil(remainingSeconds)} seconds`
    }
}
```

**Visual feedback:**
```
Photo 1: greenhouse_a.jpg
[████████████████████████████░░] 95% - Processing... (~20s remaining)

Photo 2: greenhouse_b.jpg
[██████████████████░░░░░░░░░░░] 60% - Processing... (~3 minutes remaining)

Photo 3: greenhouse_c.jpg
[░░░░░░░░░░░░░░░░░░░░░░░░░░░░] 0% - Pending...
```

### 4. Backend: Poll Status Endpoint (lines 460-580)

**FastAPI implementation:**
```python
from typing import List, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
import json
from datetime import datetime, timedelta

router = APIRouter()

@router.get('/photos/jobs/status')
async def get_job_status(
    upload_session_id: str = Query(...),
    current_user: User = Depends(get_current_user),
    redis: Redis = Depends(get_redis),
    db: AsyncSession = Depends(get_db)
):
    """
    Get status of all jobs in an upload session

    Returns:
        {
            "upload_session_id": "uuid",
            "jobs": [...],
            "summary": {
                "total_jobs": 50,
                "completed": 30,
                "processing": 15,
                "pending": 3,
                "failed": 2,
                "overall_progress_percent": 60.0
            }
        }

    Performance: < 50ms (Redis cache)
    """

    # Try Redis cache first (CRITICAL for performance)
    cache_key = f'upload_session:{upload_session_id}'
    cached = await redis.get(cache_key)

    if not cached:
        raise HTTPException(404, 'Upload session not found or expired')

    session_data = json.loads(cached)

    # Verify user owns this session
    if session_data.get('user_id') != current_user.id:
        raise HTTPException(403, 'Forbidden')

    # Get job statuses from Redis (updated by Celery workers)
    jobs = []
    summary = {
        'total_jobs': 0,
        'pending': 0,
        'processing': 0,
        'completed': 0,
        'failed': 0,
        'overall_progress_percent': 0.0
    }

    for job_data in session_data['jobs']:
        job_id = job_data['job_id']

        # Check job status in Redis
        job_status_key = f'job_status:{job_id}'
        job_status = await redis.get(job_status_key)

        if job_status:
            job_info = json.loads(job_status)
        else:
            # Fallback: Job hasn't started yet
            job_info = {
                'job_id': job_id,
                'status': 'pending',
                'progress_percent': 0
            }

        # Merge with original job data
        job_info.update({
            'image_id': job_data['image_id'],
            'filename': job_data['filename']
        })

        jobs.append(job_info)

        # Update summary
        summary['total_jobs'] += 1
        status = job_info['status']
        summary[status] = summary.get(status, 0) + 1

    # Calculate overall progress
    if summary['total_jobs'] > 0:
        summary['overall_progress_percent'] = round(
            (summary['completed'] + summary['failed']) / summary['total_jobs'] * 100,
            1
        )

    return {
        'upload_session_id': upload_session_id,
        'jobs': jobs,
        'summary': summary,
        'last_updated': datetime.utcnow().isoformat()
    }
```

**Performance:**
- **Redis cache hit**: ~2ms
- **Redis cache miss**: ~50ms (lookup from DB)
- **Database fallback**: ~100-200ms (if Redis unavailable)

### 5. Job Status Updates (Celery Workers)

**IMPORTANT:** Processing happens in **4 distinct phases** with multiple task types. See `flows/procesamiento_ml_upload_s3_principal/` for complete pipeline details.

**Task lifecycle base class:**

```python
from celery import Task
from redis import Redis
import json
from datetime import datetime

class CallbackTask(Task):
    """Custom task base class with status tracking"""

    def on_success(self, retval, task_id, args, kwargs):
        """Called when task completes successfully"""
        self.update_job_status(task_id, 'completed', result=retval)

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Called when task fails"""
        self.update_job_status(
            task_id,
            'failed',
            error_message=str(exc)
        )

    def update_job_status(self, job_id: str, status: str, **kwargs):
        """Update job status in Redis"""
        redis_client = Redis.from_url('redis://localhost:6379')

        job_data = {
            'job_id': job_id,
            'status': status,
            'updated_at': datetime.utcnow().isoformat(),
            **kwargs
        }

        # Store job status (TTL: 48 hours)
        redis_client.setex(
            f'job_status:{job_id}',
            172800,  # 48 hours
            json.dumps(job_data)
        )
```

**Phase 1: S3 Upload (Chunked - 20 images/batch)**

See: `flows/procesamiento_ml_upload_s3_principal/03_s3_upload_circuit_breaker_detailed.mmd`

```python
@celery_app.task(name='upload_s3_batch', base=CallbackTask, bind=True)
def upload_s3_batch(self, chunk: List[str]):
    """Upload batch to S3 with circuit breaker"""

    for i, image_id in enumerate(chunk):
        progress = int((i / len(chunk)) * 20)  # 0-20% of total
        self.update_job_status(
            self.request.id,
            'processing',
            phase='s3_upload',
            current_image=i+1,
            total_images=len(chunk),
            progress_percent=progress
        )

        # Extract EXIF, upload original + thumbnail
        # (see detailed flow)
```

**Phase 2: ML Parent Task (Segmentation & Classification)**

See: `flows/procesamiento_ml_upload_s3_principal/04_ml_parent_segmentation_detailed.mmd`

```python
@celery_app.task(name='process_photo_ml', base=CallbackTask, bind=True)
def process_photo_ml(self, image_id: str):
    """ML parent task - segmentation and classification"""

    # 20%: Geolocate
    self.update_job_status(
        self.request.id, 'processing',
        phase='geolocation', progress_percent=20
    )
    location_result = geolocate_image(image_id)

    # Check warning states
    if location_result.get('warning'):
        self.update_job_status(
            self.request.id, 'completed_with_warning',
            warning_type=location_result['warning'],
            progress_percent=100
        )
        return {'status': 'warning', 'type': location_result['warning']}

    # 30%: YOLO segmentation
    self.update_job_status(
        self.request.id, 'processing',
        phase='segmentation', progress_percent=30
    )
    masks = run_yolo_segmentation(image_id)

    # 35%: Classify masks
    self.update_job_status(
        self.request.id, 'processing',
        phase='classification', progress_percent=35
    )
    classified_masks = classify_masks(masks)

    # 40%: Build chord and spawn children
    self.update_job_status(
        self.request.id, 'processing',
        phase='spawning_children', progress_percent=40
    )

    # Spawn child tasks (SAHI + Direct)
    # (see Phase 3)
```

**Phase 3: Child Tasks (Parallel Detection)**

See: `flows/procesamiento_ml_upload_s3_principal/05_sahi_detection_child_detailed.mmd`

```python
@celery_app.task(name='detect_sahi', base=CallbackTask, bind=True)
def detect_sahi(self, segment_data: Dict):
    """SAHI detection for segments (40-70%)"""

    for i, slice_data in enumerate(segment_data['slices']):
        progress = 40 + int((i / len(segment_data['slices'])) * 30)
        self.update_job_status(
            self.request.id, 'processing',
            phase='sahi_detection',
            current_slice=i+1,
            total_slices=len(segment_data['slices']),
            progress_percent=progress
        )

        # Run YOLO detection on slice
        # (see detailed flow)

@celery_app.task(name='detect_direct', base=CallbackTask, bind=True)
def detect_direct(self, boxes_plugs_data: Dict):
    """Direct detection for boxes/plugs (70-90%)"""

    self.update_job_status(
        self.request.id, 'processing',
        phase='direct_detection',
        progress_percent=70
    )

    # Run direct YOLO detection
    # (see detailed flow)

    self.update_job_status(
        self.request.id, 'processing',
        phase='direct_detection_complete',
        progress_percent=90
    )
```

**Phase 4: Callback Task (Aggregation)**

See: `flows/procesamiento_ml_upload_s3_principal/07_callback_aggregation_detailed.mmd`

```python
@celery_app.task(name='aggregate_results', base=CallbackTask, bind=True)
def aggregate_results(self, child_results: List[Dict]):
    """Callback - aggregate all child results"""

    # 90%: Aggregate totals
    self.update_job_status(
        self.request.id, 'processing',
        phase='aggregating', progress_percent=90
    )
    totals = aggregate_detections_estimations(child_results)

    # 93%: Generate visualization
    self.update_job_status(
        self.request.id, 'processing',
        phase='visualization', progress_percent=93
    )
    viz_s3_key = generate_and_upload_viz(totals)

    # 96%: Create stock batches
    self.update_job_status(
        self.request.id, 'processing',
        phase='stock_batches', progress_percent=96
    )
    batches = create_stock_batches(totals)

    # 100%: Complete
    return {
        'session_id': totals['session_id'],
        'total_detected': totals['detected'],
        'total_estimated': totals['estimated'],
        'batches': batches,
        'viz_url': viz_s3_key
    }
```

**Status update frequency:**
- **S3 Upload**: Per-image updates (20 images × 5ms = 100ms overhead)
- **ML Parent**: 4 milestone updates (geolocate, segment, classify, spawn)
- **Child Tasks**: Per-slice updates (SAHI) or single update (Direct)
- **Callback**: 3 milestone updates (aggregate, viz, batches)
- **Redis write time**: ~5ms per update

**Warning states** (not failures):
- `completed_with_warning`: Photo processed but needs manual action
  - `needs_location`: No GPS coordinates
  - `needs_config`: No storage location configuration
  - `needs_calibration`: Density estimation unavailable

### 6. Job List Persistence (lines 760-840)

**Why persist for 24-48 hours?**
- **User convenience**: User can close browser and check back later
- **Debugging**: Support team can review failed jobs
- **Auditing**: Track upload history

**Redis data structure:**
```json
{
  "upload_session:550e8400-e29b-41d4-a716-446655440000": {
    "upload_session_id": "550e8400-e29b-41d4-a716-446655440000",
    "user_id": 42,
    "total_jobs": 50,
    "jobs": [
      {
        "job_id": "celery-task-uuid-1",
        "image_id": "image-uuid-1",
        "filename": "greenhouse_a.jpg"
      },
      {
        "job_id": "celery-task-uuid-2",
        "image_id": "image-uuid-2",
        "filename": "greenhouse_b.jpg"
      }
    ],
    "created_at": "2025-10-08T10:30:00Z"
  }
}
```

**TTL strategy:**
```python
# Upload session metadata: 24 hours
await redis.setex(
    f'upload_session:{upload_session_id}',
    86400,  # 24 hours
    json.dumps(session_data)
)

# Individual job status: 48 hours (outlives session for debugging)
await redis.setex(
    f'job_status:{job_id}',
    172800,  # 48 hours
    json.dumps(job_status)
)
```

**Cleanup policy:**
- **Automatic**: Redis evicts keys after TTL expires
- **Manual**: Admin can flush old sessions with `/admin/cleanup-sessions`

### 7. Completion Notification (lines 880-940)

**When all jobs complete:**

**Frontend detection:**
```javascript
// In polling loop
if (summary.completed + summary.failed >= summary.total) {
    // Stop polling
    setIsPolling(false)

    // Show notification
    if (summary.failed === 0) {
        // All successful
        showSuccessNotification({
            title: 'Processing Complete!',
            message: `Successfully processed ${summary.completed} photos.`,
            actions: [
                {
                    label: 'View Gallery',
                    onClick: () => navigate('/gallery')
                }
            ]
        })
    } else {
        // Some failed
        showWarningNotification({
            title: 'Processing Complete with Errors',
            message: `Completed: ${summary.completed}, Failed: ${summary.failed}`,
            actions: [
                {
                    label: 'View Results',
                    onClick: () => navigate('/gallery')
                },
                {
                    label: 'Review Errors',
                    onClick: () => showErrorDetails()
                }
            ]
        })
    }
}
```

**Optional: Email notification (backend):**
```python
async def send_completion_email(
    user_email: str,
    upload_session_id: str,
    summary: Dict
):
    """Send email when processing completes"""

    if summary['failed'] == 0:
        subject = f"✓ Photo processing complete ({summary['completed']} photos)"
        template = 'processing_success.html'
    else:
        subject = f"⚠ Photo processing complete with errors ({summary['failed']} failed)"
        template = 'processing_partial.html'

    await send_email(
        to=user_email,
        subject=subject,
        template=template,
        context={
            'upload_session_id': upload_session_id,
            'summary': summary,
            'gallery_url': f'https://app.demeterai.com/gallery'
        }
    )
```

## Performance Breakdown

**Complete monitoring flow timing (for 50 photos):**

| Phase | Time | Details |
|-------|------|---------|
| **Initial poll** | 2ms | Redis cache hit |
| **Poll iterations** | 175 × 2ms = 0.35s | 175 polls over ~6 minutes |
| **Status updates** | 50 × 5 × 5ms = 1.25s | 5 updates per job |
| **Completion check** | 2ms | Final poll |
| **Total overhead** | ~1.6s | Over 6 minutes (negligible) |

**Network cost:**
- **Request size**: ~500 bytes (GET with query param)
- **Response size**: ~10KB (50 jobs × 200 bytes each)
- **Total transfer**: 175 × 10KB = ~1.75MB over 6 minutes
- **Bandwidth**: ~5 KB/s average (negligible)

## Error Handling

### 1. Upload Session Not Found

**Scenario:** Redis key expired or invalid upload_session_id

**Response:**
```python
if not cached:
    raise HTTPException(404, 'Upload session not found or expired')
```

**Frontend:**
```javascript
if (response.status === 404) {
    showError({
        title: 'Session Expired',
        message: 'Upload session not found. It may have expired (24 hours).',
        actions: [
            { label: 'Return to Upload', onClick: () => navigate('/upload') }
        ]
    })
}
```

### 2. Network Timeout

**Scenario:** API unavailable, request timeout

**Exponential backoff:**
```javascript
let retryCount = 0
const maxRetries = 5

async function pollWithRetry() {
    try {
        const response = await fetch(pollUrl, { timeout: 5000 })
        retryCount = 0  // Reset on success
        return response
    } catch (error) {
        retryCount++

        if (retryCount >= maxRetries) {
            showError('Network error. Please refresh the page.')
            return
        }

        // Exponential backoff: 2s, 4s, 8s, 16s, 32s
        const delay = Math.min(32, Math.pow(2, retryCount)) * 1000
        await sleep(delay)

        return pollWithRetry()
    }
}
```

### 3. Authentication Expiration

**Scenario:** Token expires during long processing

**Behavior:**
```javascript
if (response.status === 401) {
    // Save current session ID
    sessionStorage.setItem('resume_session_id', uploadSessionId)

    // Redirect to login
    window.location.href = `/login?return=/jobs?session_id=${uploadSessionId}`
}

// After login, resume monitoring
const resumeSessionId = sessionStorage.getItem('resume_session_id')
if (resumeSessionId) {
    startPolling(resumeSessionId)
}
```

### 4. All Jobs Failed

**Scenario:** Systemic issue (e.g., GPU server down)

**Detection:**
```javascript
if (summary.failed === summary.total && summary.total > 5) {
    // Likely systemic issue
    showError({
        title: 'Processing Failed',
        message: 'All photos failed to process. This may be a system issue.',
        actions: [
            { label: 'Contact Support', onClick: () => openSupport() },
            { label: 'Retry Upload', onClick: () => retryAllJobs() }
        ]
    })
}
```

## Optimization Opportunities

### 1. WebSocket Migration (Future)

**Current:** HTTP polling every 2s

**Future:** WebSocket push notifications

**Benefits:**
- Reduce server load by 95% (no polling)
- Instant updates (no 2s delay)
- Lower network cost

**Implementation:**
```python
# Backend: WebSocket endpoint
@app.websocket('/ws/jobs/{upload_session_id}')
async def websocket_job_updates(
    websocket: WebSocket,
    upload_session_id: str
):
    await websocket.accept()

    # Subscribe to Redis pub/sub for job updates
    redis = await get_redis()
    pubsub = redis.pubsub()
    await pubsub.subscribe(f'job_updates:{upload_session_id}')

    try:
        async for message in pubsub.listen():
            if message['type'] == 'message':
                await websocket.send_json(json.loads(message['data']))
    except WebSocketDisconnect:
        await pubsub.unsubscribe(f'job_updates:{upload_session_id}')
```

### 2. Server-Sent Events (SSE)

**Alternative to WebSocket (simpler):**

```python
from fastapi.responses import StreamingResponse

@app.get('/jobs/{upload_session_id}/stream')
async def stream_job_updates(upload_session_id: str):
    """Server-Sent Events endpoint"""

    async def event_generator():
        redis = await get_redis()
        pubsub = redis.pubsub()
        await pubsub.subscribe(f'job_updates:{upload_session_id}')

        async for message in pubsub.listen():
            if message['type'] == 'message':
                yield f"data: {message['data']}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type='text/event-stream'
    )
```

### 3. Adaptive Poll Interval

**Current:** Fixed 2s interval

**Future:** Slow down as jobs complete

```javascript
// Fast polling early (many jobs active)
if (summary.processing > 20) {
    pollInterval = 1000  // 1s
}
// Normal polling mid-way
else if (summary.processing > 5) {
    pollInterval = 2000  // 2s
}
// Slow polling near end
else {
    pollInterval = 5000  // 5s
}
```

## Related Diagrams

- **01_photo_upload_initiation.mmd:** Upload that creates jobs
- **03_photo_gallery_view.mmd:** Gallery view after jobs complete

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-10-08 | Initial job monitoring subflow |

---

**Notes:**
- Polling is simple and reliable (chosen for MVP)
- Redis cache is CRITICAL for performance (2ms vs 200ms)
- Fake progress bar is good enough for UX (within 10-20% accuracy)
- Job list persists for 24-48 hours (user convenience)
- WebSocket migration recommended for v2.0 (95% load reduction)
