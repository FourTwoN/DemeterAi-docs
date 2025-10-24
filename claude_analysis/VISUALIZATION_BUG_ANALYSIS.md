# Visualization Bug Analysis & Fix Plan

**Date**: 2025-10-24
**Team Leader**: Claude Code
**Status**: 🔴 CRITICAL BUG IDENTIFIED

---

## Problem Statement

**User Report**:
> "Detection dots are grouped up in the corner instead of being properly positioned across the image. The dots don't align with the underlying image (coordinate system mismatch). The visualization aesthetics are poor (green dots look horrible)."

---

## Root Cause Analysis

### The Bug

**Coordinate System Mismatch**: Detections are stored with **segment-relative coordinates**, but visualization draws them at **full-image absolute coordinates**.

### How the ML Pipeline Works

```
Step 1: SEGMENTATION (SegmentationService)
────────────────────────────────────────────
Input: Full image (4000×3000 px)
Output: Segments with normalized bboxes

Example segment:
  bbox = [0.2, 0.3, 0.6, 0.8]  # normalized (x1, y1, x2, y2)

  Absolute pixels:
    x1 = 0.2 * 4000 = 800px
    y1 = 0.3 * 3000 = 900px
    x2 = 0.6 * 4000 = 2400px
    y2 = 0.8 * 3000 = 2400px

  Segment size: 1600×1500 px
  Segment location: TOP-LEFT at (800, 900) in full image


Step 2: CROPPING (_crop_segment in PipelineCoordinator)
────────────────────────────────────────────────────────
Input: Full image + segment bbox
Output: Cropped segment image

  crop = img[y1_px:y2_px, x1_px:x2_px]
  crop = img[900:2400, 800:2400]  # NumPy slicing

  Result: New image file, 1600×1500 px
  ❌ CRITICAL: New coordinate system starts at (0, 0) for this crop!


Step 3: DETECTION (SAHIDetectionService)
─────────────────────────────────────────
Input: Cropped segment image (1600×1500 px)
Output: Detections with coordinates **RELATIVE TO CROP**

Example detection:
  center_x_px = 100.5  # 100.5 px from LEFT of CROPPED segment
  center_y_px = 200.3  # 200.3 px from TOP of CROPPED segment
  width_px = 50
  height_px = 60

  ❌ These coordinates are RELATIVE TO THE CROP, NOT THE FULL IMAGE!


Step 4: AGGREGATION (PipelineCoordinator)
──────────────────────────────────────────
Detections are converted to dicts:
  {
    "center_x_px": 100.5,  # ❌ Still relative to crop!
    "center_y_px": 200.3,  # ❌ Still relative to crop!
    "width_px": 50,
    "height_px": 60,
    "confidence": 0.92
  }

❌ PROBLEM: Segment offset (800, 900) is LOST!


Step 5: VISUALIZATION (_generate_visualization)
────────────────────────────────────────────────
Input: Full image (4000×3000 px) + detections
Draw: cv2.circle(overlay, (center_x, center_y), radius, ...)

  cv2.circle(overlay, (100, 200), 20, green, -1)

  ❌ BUG: Drawing at (100, 200) in full image
  ✅ SHOULD BE: (100 + 800, 200 + 900) = (900, 1100) in full image
```

### Visualization of the Bug

```
FULL IMAGE (4000×3000 px):
┌────────────────────────────────────────────┐
│ (0,0)                                       │
│                                             │
│         ┌─────────────┐ ← Segment crop     │
│         │ (800, 900)  │   1600×1500 px     │
│         │             │                    │
│         │    🌱      │ ← Plant detected   │
│         │  (900,1100) │   at (100,200)     │
│         │   in full   │   in crop          │
│         │   image     │                    │
│         └─────────────┘                    │
│                                             │
│                                             │
│                             (4000, 3000)    │
└────────────────────────────────────────────┘

CURRENT BUG:
  Detection stored as: (100, 200) relative to crop
  Visualization draws at: (100, 200) in full image ❌
  Result: Dot appears in TOP-LEFT CORNER, not at plant location!

CORRECT BEHAVIOR:
  Detection stored as: (100, 200) relative to crop
  Add segment offset: (100 + 800, 200 + 900) = (900, 1100)
  Visualization draws at: (900, 1100) in full image ✅
  Result: Dot appears at plant location!
```

---

## Solution

### Option 1: Store Segment Offset with Each Detection (RECOMMENDED)

**Modify `PipelineCoordinator` to include segment offset**:

```python
# In pipeline_coordinator.py, _crop_segment() method
async def _crop_segment(...) -> tuple[Path, tuple[int, int]]:
    """Returns (crop_path, (offset_x, offset_y))"""

    # Existing code...
    x1_px = int(x1 * img_width)
    y1_px = int(y1 * img_height)
    # ...

    return crop_path, (x1_px, y1_px)  # Return offset


# In detect_in_segmento loop:
segment_crop_path, segment_offset = await self._crop_segment(...)
detections = await self.sahi_service.detect_in_segmento(segment_crop_path, ...)

# Transform detections to full-image coordinates
for det in detections:
    det.center_x_px += segment_offset[0]
    det.center_y_px += segment_offset[1]
```

**Advantages**:
- ✅ Detections stored in database with CORRECT full-image coordinates
- ✅ Visualization works without modification
- ✅ Future features (clickable detections, etc.) work correctly
- ✅ One-time fix at source

**Disadvantages**:
- ⚠️ Changes database records (detections already in DB will be wrong)
- ⚠️ Requires migration or data cleanup

### Option 2: Store Segment Metadata and Transform in Visualization (ALTERNATIVE)

**Store segment offset in detection dict**:

```python
# In pipeline_coordinator.py:
detections_for_db = [
    {
        "center_x_px": det.center_x_px,  # Still relative to crop
        "center_y_px": det.center_y_px,
        "width_px": det.width_px,
        "height_px": det.height_px,
        "confidence": det.confidence,
        "segment_offset_x": segment_offset[0],  # NEW
        "segment_offset_y": segment_offset[1],  # NEW
    }
    for det in all_detections
]

# In visualization:
for det in detections:
    # Transform to full-image coordinates
    center_x = int(det["center_x_px"] + det.get("segment_offset_x", 0))
    center_y = int(det["center_y_px"] + det.get("segment_offset_y", 0))
```

**Advantages**:
- ✅ Preserves original crop-relative coordinates (useful for debugging)
- ✅ Can handle existing DB records (default offset=0)

**Disadvantages**:
- ❌ Every consumer must remember to apply transformation
- ❌ More complex, error-prone

---

## Recommended Fix: Option 1 (Transform at Source)

### Implementation Plan

#### Phase 1: Modify PipelineCoordinator

**File**: `app/services/ml_processing/pipeline_coordinator.py`

**Changes**:
1. Modify `_crop_segment()` to return `(crop_path, offset)`
2. After SAHI detection, transform coordinates to full-image:
   ```python
   for det in detections:
       det.center_x_px += segment_x1_px
       det.center_y_px += segment_y1_px
   ```

#### Phase 2: Improve Visualization Aesthetics

**File**: `app/tasks/ml_tasks.py`, `_generate_visualization()`

**Changes**:
1. Replace circles with bounding boxes (better shape representation)
2. Add confidence-based color coding:
   - Low (0.0-0.5): Red
   - Medium (0.5-0.8): Yellow
   - High (0.8-1.0): Cyan
3. Use semi-transparent overlays (alpha=0.4)
4. Draw both bbox AND center dot for precision

#### Phase 3: Testing

**Tests**:
1. Unit test: Coordinate transformation correctness
2. Integration test: Full pipeline with known segment offset
3. Visual verification: Real greenhouse photos

---

## Files to Modify

### 1. `app/services/ml_processing/pipeline_coordinator.py`

**Lines 451-514** (`_crop_segment`):
- Return `(crop_path, (offset_x, offset_y))`

**Lines 272-292** (SAHI detection loop):
- Capture offset from `_crop_segment()`
- Transform detection coordinates after SAHI

**Lines 384-395** (Aggregation):
- Coordinates now correct, no changes needed

### 2. `app/tasks/ml_tasks.py`

**Lines 1290-1360** (`_generate_visualization`):
- Replace `cv2.circle()` with `cv2.rectangle()`
- Add `_get_confidence_color()` helper function
- Draw center dot for precision
- Update alpha blending

### 3. `tests/integration/tasks/test_visualization_fix.py` (NEW)

**Tests**:
- `test_segment_coordinate_transformation()`
- `test_visualization_coordinates_match_detections()`
- `test_visual_verification_real_image()`

---

## Acceptance Criteria

- [ ] Detections positioned correctly across entire image (not clustered)
- [ ] Coordinates align with actual plants in photos
- [ ] Bounding boxes replace circles
- [ ] Confidence-based color coding (red→yellow→cyan)
- [ ] Semi-transparent overlays (alpha=0.4)
- [ ] Tests verify coordinate transformation
- [ ] Visual verification passes on real photos
- [ ] No regression in ML pipeline performance

---

## Timeline

**Phase 1** (Coordinate Fix): 2-3 hours
- Python Expert: Modify pipeline_coordinator
- Python Expert: Update detection transformation
- Testing Expert: Write coordinate tests

**Phase 2** (Aesthetics): 1-2 hours
- Python Expert: Improve visualization rendering
- Python Expert: Add confidence coloring

**Phase 3** (Testing): 2-3 hours
- Testing Expert: Integration tests
- Testing Expert: Visual verification
- Team Leader: Quality gates

**Total**: 5-8 hours

---

## Risk Assessment

**HIGH RISK**:
- ❌ Existing detections in database have WRONG coordinates
- ❌ Requires data migration or cleanup

**MITIGATION**:
- Run coordinate transformation on existing DB records
- OR: Add migration script to fix historical data
- OR: Accept that old sessions have incorrect visualizations

**RECOMMENDATION**:
Since this is a new system (v2.0), accept that existing visualizations are incorrect and fix going forward. Add note in documentation.

---

## Next Steps

1. **User Confirmation**:
   - Confirm this is the issue (provide sample visualization?)
   - Confirm fix approach (Option 1 vs Option 2)
   - Confirm timeline acceptable

2. **Spawn Agents**:
   - Python Expert: Coordinate transformation
   - Python Expert: Visualization aesthetics
   - Testing Expert: Tests + verification

3. **Quality Gates**:
   - Code review (Team Leader)
   - Tests pass (Testing Expert)
   - Visual verification (Team Leader + User)

---

**Author**: Team Leader (Claude Code)
**Date**: 2025-10-24
**Status**: 🔴 AWAITING USER CONFIRMATION TO PROCEED
