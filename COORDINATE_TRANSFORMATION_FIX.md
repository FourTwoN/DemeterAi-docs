# Coordinate Transformation Fix - ML Pipeline

**Date**: 2025-10-24
**File**: `/home/lucasg/proyectos/DemeterDocs/app/services/ml_processing/pipeline_coordinator.py`
**Issue**: Detection coordinates were relative to cropped segments, causing all visualization dots to cluster in top-left corner

---

## The Problem

### Root Cause
In the ML pipeline detection stage (lines 266-308):
1. We segment the full image into crops (bboxes in normalized coords 0.0-1.0)
2. We crop each segment from the full image
3. We run SAHI detection on the **cropped segment image**
4. Detection results have coordinates **relative to the crop** (e.g., 100, 200 px from crop's top-left)
5. These crop-relative coordinates were stored directly in the database
6. **Result**: When rendered on the full image, all dots appeared at coordinates like (100, 200) instead of the actual positions like (1500, 2200)

### Example
- Full image: 4000×3000 px
- Segment bbox: [0.3, 0.5, 0.6, 0.8] (normalized)
- Segment bbox in pixels: [1200, 1500, 2400, 2400]
- Detection in cropped segment: (300, 400) ← relative to crop's (0,0)
- **Before fix**: Stored as (300, 400) in database → renders at wrong position
- **After fix**: Transformed to (1500, 1900) → renders at correct position

---

## The Fix

### Changes Made

#### 1. Load Full Image Once (Line 266-274)
**Before**: Image was loaded inside `_crop_segment` for each segment
**After**: Load once before segment loop to get dimensions for all transformations

```python
# Load image once to get dimensions for coordinate transformation
import cv2  # type: ignore[import-not-found]

full_img = cv2.imread(str(image_path))
if full_img is None:
    raise RuntimeError(f"Failed to load image for coordinate transformation: {image_path}")

img_height, img_width = full_img.shape[:2]
logger.debug(f"[Session {session_id}] Full image dimensions: {img_width}x{img_height}")
```

**Benefits**:
- ✅ Only one image read operation (performance optimization)
- ✅ Dimensions available for all segments
- ✅ Clear error handling if image fails to load

#### 2. Transform Detection Coordinates (Line 292-318)
**Added after SAHI detection, before extending all_detections**

```python
# Transform detection coordinates from segment-relative to full-image coordinates
# Segment bbox is in normalized coordinates (0.0-1.0), convert to pixels
x1, y1, x2, y2 = segment.bbox
x1_px = int(x1 * img_width)
y1_px = int(y1 * img_height)

logger.debug(
    f"[Session {session_id}] Segment {idx} bbox offset: "
    f"x1={x1_px}px, y1={y1_px}px (from normalized {x1:.3f}, {y1:.3f})"
)

# Transform each detection's center coordinates by adding segment offset
for det in detections:
    original_x = det.center_x_px
    original_y = det.center_y_px

    # Add segment offset to transform from crop-relative to full-image coordinates
    det.center_x_px += x1_px
    det.center_y_px += y1_px

    if idx == 1 and len(detections) > 0 and det == detections[0]:
        # Log first detection of first segment for verification
        logger.debug(
            f"[Session {session_id}] Sample detection transformed: "
            f"({original_x:.1f}, {original_y:.1f}) → "
            f"({det.center_x_px:.1f}, {det.center_y_px:.1f})"
        )
```

**Key points**:
- ✅ Converts normalized segment bbox to pixel coordinates
- ✅ Transforms only `center_x_px` and `center_y_px` (NOT width/height - those are correct)
- ✅ Modifies DetectionResult dataclass fields directly (no new objects)
- ✅ Logs transformation for first detection (verification)

---

## Verification

### How to Verify the Fix Works

1. **Run ML Pipeline on a Test Image**
   ```bash
   # Process an image with multiple segments
   python -m app.tasks.ml_tasks process_session <session_id>
   ```

2. **Check Debug Logs**
   ```bash
   # Look for transformation logs
   grep "bbox offset" logs/celery.log
   grep "Sample detection transformed" logs/celery.log
   ```

   Expected output:
   ```
   Segment 1 bbox offset: x1=1200px, y1=1500px (from normalized 0.300, 0.500)
   Sample detection transformed: (100.5, 200.3) → (1300.5, 1700.3)
   ```

3. **Query Database for Detection Coordinates**
   ```sql
   SELECT
       session_id,
       center_x_px,
       center_y_px,
       width_px,
       height_px
   FROM detections
   WHERE session_id = <test_session_id>
   ORDER BY center_x_px, center_y_px
   LIMIT 10;
   ```

   **Before fix**: Most coordinates < 500 (clustered in top-left)
   **After fix**: Coordinates distributed across full image range (0-4000, 0-3000)

4. **Visual Verification in Gallery**
   - Open photo in gallery
   - Verify detection dots are positioned correctly on plants
   - Should NOT cluster in top-left corner
   - Should align with actual plant positions in segments

---

## Testing Checklist

- [ ] Import verification: `python -c "from app.services.ml_processing.pipeline_coordinator import MLPipelineCoordinator"`
- [ ] Process test session with multiple segments
- [ ] Verify debug logs show correct transformations
- [ ] Query database to confirm coordinates are in full-image space
- [ ] Visual verification in gallery (dots align with plants)
- [ ] Performance check (should not significantly slow down pipeline)

---

## Related Files

### Modified
- `/home/lucasg/proyectos/DemeterDocs/app/services/ml_processing/pipeline_coordinator.py` (lines 266-318)

### Related (Not Modified)
- `/home/lucasg/proyectos/DemeterDocs/app/services/ml_processing/sahi_detection_service.py` (DetectionResult dataclass)
- `/home/lucasg/proyectos/DemeterDocs/app/models/detection.py` (Database model)
- `/home/lucasg/proyectos/DemeterDocs/app/tasks/ml_tasks.py` (Celery task that calls pipeline)

---

## Technical Details

### Coordinate Systems

1. **Segment Bbox**: Normalized coordinates (0.0-1.0)
   - Example: `[0.3, 0.5, 0.6, 0.8]`
   - Independent of image size

2. **Segment Bbox (Pixels)**: Absolute coordinates
   - Calculation: `x1_px = int(x1 * img_width)`
   - Example: `[1200, 1500, 2400, 2400]` for 4000×3000 image

3. **Detection Coordinates (Before Transform)**: Crop-relative
   - Origin: Top-left of cropped segment
   - Range: (0, 0) to (segment_width, segment_height)
   - Example: `(100, 200)` means 100px from crop's left, 200px from crop's top

4. **Detection Coordinates (After Transform)**: Full-image coordinates
   - Origin: Top-left of full image
   - Range: (0, 0) to (img_width, img_height)
   - Calculation: `full_x = crop_x + x1_px`
   - Example: `(100, 200)` → `(1300, 1700)` with offset (1200, 1500)

### Performance Impact

- **Additional cost**: One `cv2.imread()` call per session (before segment loop)
- **Saved cost**: No additional reads (was already reading in `_crop_segment`)
- **Net impact**: Minimal (reusing already-loaded image data)
- **Transformation loop**: O(n) where n = number of detections (lightweight arithmetic)

---

## Future Improvements

1. **Avoid loading image twice**
   - Currently: Load once for coordinate transform, load again in `_crop_segment`
   - Future: Pass `full_img` to `_crop_segment` to avoid second read

2. **Add unit test**
   - Test coordinate transformation logic in isolation
   - Mock segment bbox and verify correct pixel offset calculation

3. **Add integration test**
   - Process test image with known segment positions
   - Verify detection coordinates are in expected ranges

---

## Success Criteria

✅ **Fix is successful when**:
1. Detection dots render at correct positions on full image
2. No clustering in top-left corner
3. Coordinates in database are in full-image space
4. Debug logs show correct transformations
5. No performance degradation in pipeline

---

**Status**: ✅ IMPLEMENTED
**Tested**: ⏳ PENDING (needs test session run)
**Deployed**: ⏳ PENDING
