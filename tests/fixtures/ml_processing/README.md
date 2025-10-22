# ML Processing Test Fixtures

This directory contains test fixtures for ML processing integration tests.

## Directory Structure

```
ml_processing/
├── README.md                    # This file
├── segment_with_gaps.jpg        # Test image: segment with undetected areas (TODO)
├── segment_perspective.jpg      # Test image: perspective distortion (TODO)
├── detections_band1.json        # Sample detections for band 1 (far) (TODO)
├── detections_band4.json        # Sample detections for band 4 (close) (TODO)
└── ground_truth.json            # Manually counted plant totals (TODO)
```

## Fixture Descriptions

### Images

#### segment_with_gaps.jpg

- **Purpose**: Test band-based estimation accuracy
- **Dimensions**: 1200×1600 pixels (realistic greenhouse photo size)
- **Content**:
    - Dense vegetation regions (300+ detectable plants)
    - Sparse gaps (75+ undetected plants - estimation target)
    - Soil/floor areas (should be suppressed)
- **Ground Truth**: 575 total plants (manually counted)
- **Expected YOLO Detection Rate**: ~90% (520 detected, 55 missed)

#### segment_perspective.jpg

- **Purpose**: Test perspective compensation across bands
- **Dimensions**: 1200×1600 pixels
- **Content**:
    - Band 1 (y: 0-300): Small plants (far perspective) - 20×20 px
    - Band 4 (y: 900-1200): Large plants (close) - 40×40 px
- **Expected**: Band 1 avg_area < Band 4 avg_area

### Detection JSON Files

#### detections_band1.json

```json
[
  {
    "center_x_px": 100,
    "center_y_px": 50,
    "width_px": 20,
    "height_px": 20,
    "confidence": 0.92
  },
  ...
]
```

#### detections_band4.json

```json
[
  {
    "center_x_px": 100,
    "center_y_px": 920,
    "width_px": 40,
    "height_px": 40,
    "confidence": 0.95
  },
  ...
]
```

#### ground_truth.json

```json
{
  "segment_with_gaps.jpg": {
    "total_plants": 575,
    "dense_region_1": 300,
    "dense_region_2": 200,
    "sparse_center": 75
  },
  "segment_perspective.jpg": {
    "total_plants": 450,
    "band_1_plants": 120,
    "band_4_plants": 100
  }
}
```

## Creating Test Fixtures

### Option 1: Generate Synthetic Images (Current Approach)

Integration tests currently generate synthetic images using `tmp_path` fixtures.
This is sufficient for unit testing but not ideal for accuracy validation.

**Pros**:

- Fast test execution
- No external dependencies
- Deterministic results

**Cons**:

- Not realistic (simple circles, uniform colors)
- Cannot validate true accuracy

### Option 2: Use Real Greenhouse Photos (Future Enhancement)

For production validation, use actual greenhouse photos with manual counts.

**Steps**:

1. Capture high-res greenhouse photos (3000×1500 px)
2. Manually count plants in photo (ground truth)
3. Run YOLO detection (get ~90% detection rate)
4. Save image + detections + ground truth as fixture
5. Use in integration tests for accuracy validation

**Required**:

- Photography equipment
- Manual counting (1-2 hours per image)
- YOLO detection pipeline setup

## Current Status

- **Unit Tests**: Use `tmp_path` synthetic images ✅
- **Integration Tests**: Use `tmp_path` synthetic images ✅
- **Real Fixtures**: Not yet created ⏳

## Next Steps

1. For MVP: Synthetic fixtures sufficient (tests pass)
2. For Production: Create 3-5 real fixture sets with ground truth
3. For CI/CD: Store fixtures in Git LFS (large binary files)

## Usage in Tests

```python
import pytest
from pathlib import Path

@pytest.fixture
def segment_with_gaps():
    """Load pre-created fixture image."""
    fixture_path = Path(__file__).parent / "fixtures/ml_processing/segment_with_gaps.jpg"
    if not fixture_path.exists():
        pytest.skip("Fixture image not available")
    return str(fixture_path)

@pytest.mark.asyncio
async def test_estimation_accuracy(segment_with_gaps):
    # Use real fixture
    estimations = await service.estimate_undetected_plants(segment_with_gaps, ...)
```

## Fixture Maintenance

- Update fixtures when algorithm changes significantly
- Re-count ground truth if detection model updated
- Version fixtures (segment_with_gaps_v1.jpg, v2.jpg, etc.)
- Document fixture creation date and photographer
