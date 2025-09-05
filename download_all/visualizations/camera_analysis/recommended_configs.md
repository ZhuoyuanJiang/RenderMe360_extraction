# Camera Configuration Strategies for RenderMe360 Extraction

## Overview
This document provides recommended configuration strategies for extracting camera subsets from the RenderMe360 dataset, particularly for the multi-view `s3_all` performance. Based on analysis of 3 subjects (0018, 0019, 0026), we've confirmed that all subjects have the same 38 cameras available in s3_all.

## Key Findings
- **s3_all**: Consistently has 38 cameras across all subjects
- **Other performances (s1, s2, s4, s5, s6)**: Only camera 25 has data
- **Camera IDs in s3_all**: [0, 1, 3, 4, 5, 7, 9, 11, 13, 15, 16, 17, 19, 20, 21, 23, 24, 25, 27, 28, 29, 31, 32, 33, 35, 37, 39, 40, 41, 43, 45, 47, 48, 49, 53, 55, 57, 59]

## Configuration Strategies

### Strategy 1: Full Extraction (Baseline)
Extract all available cameras for maximum data preservation.

**config.yaml:**
```yaml
extraction:
  cameras: "all"  # Automatically detects and extracts all available cameras
  performances:
    - "s1_all"
    - "s2_all"
    - "s3_all"
    - "s4_all"
    - "s5_all"
    - "s6_all"
```

**Pros:**
- Complete data preservation
- No manual configuration needed
- Works with any camera setup

**Cons:**
- Maximum storage: ~16GB per subject, ~8TB for 500 subjects
- s3_all alone is ~12GB per subject

**Storage Estimate:**
- Per subject: ~16 GB
- 500 subjects: ~8 TB

---

### Strategy 2: Performance-Specific Camera Selection
Different camera configurations for different performances.

**config.yaml:**
```yaml
extraction:
  # Performance-specific camera selection
  cameras: 
    s1_all: [25]  # Only camera 25 has data
    s2_all: [25]  # Only camera 25 has data
    s3_all: [0, 5, 11, 15, 20, 24, 29, 33, 39, 45, 49, 55]  # 12 evenly distributed cameras
    s4_all: [25]  # Only camera 25 has data
    s5_all: [25]  # Only camera 25 has data
    s6_all: [25]  # Only camera 25 has data
```

**Note:** This requires modifying `extract_streaming_gdrive.py` to handle performance-specific camera lists.

**Pros:**
- Optimal storage efficiency
- Maintains single-view for speech performances
- Good multi-view coverage for s3_all

**Cons:**
- Requires code modification
- Less flexible for different datasets

**Storage Estimate:**
- Per subject: ~6 GB (1GB for 5 single-view + 5GB for s3_all with 12 cameras)
- 500 subjects: ~3 TB

---

### Strategy 3: Minimal Coverage (4 Cameras for s3_all)
For storage-critical scenarios, extract minimal cameras for basic 360° coverage.

**config.yaml:**
```yaml
extraction:
  cameras: [5, 19, 24, 29]  # 4 cameras roughly 90° apart
  performances:
    - "s3_all"  # Only extract multi-view performance
    # Skip single-view performances or extract separately
```

**Pros:**
- Minimal storage: ~1.5GB per subject
- Basic 360° coverage
- Fits easily in limited storage

**Cons:**
- Large gaps between cameras (90°)
- May miss important details
- Lower quality for reconstruction

**Storage Estimate:**
- Per subject: ~1.5 GB (s3_all only with 4 cameras)
- 500 subjects: ~750 GB

---

### Strategy 4: Balanced Quality (8-12 Cameras)
Recommended for most research applications.

#### Option 4A: 8 Cameras
**config.yaml:**
```yaml
extraction:
  cameras: [0, 7, 13, 20, 24, 29, 39, 53]  # 8 cameras, ~45° apart
  performances:
    - "s3_all"
```

**Storage:** ~3GB per subject, ~1.5TB for 500 subjects

#### Option 4B: 12 Cameras (Recommended)
**config.yaml:**
```yaml
extraction:
  cameras: [0, 5, 9, 13, 16, 20, 24, 29, 37, 47, 53, 57]  # 12 cameras, ~30° apart
  performances:
    - "s3_all"
```

**Storage:** ~4.5GB per subject, ~2.2TB for 500 subjects

**Pros:**
- Good balance of coverage and storage
- Sufficient for most 3D reconstruction tasks
- Reasonable angular gaps (30-45°)

**Cons:**
- Still requires 1.5-2.2TB for full dataset
- Some detail loss compared to full extraction

---

### Strategy 5: High Quality (16 Cameras)
For applications requiring high-quality reconstruction.

**config.yaml:**
```yaml
extraction:
  cameras: [1, 3, 5, 7, 15, 19, 23, 24, 25, 29, 31, 32, 35, 39, 53, 55]  # 16 cameras
  performances:
    - "s3_all"
```

**Pros:**
- Excellent coverage (~22.5° gaps)
- High-quality reconstruction possible
- Good height variation

**Cons:**
- Larger storage: ~6GB per subject
- 3TB for 500 subjects

**Storage Estimate:**
- Per subject: ~6 GB
- 500 subjects: ~3 TB

---

### Strategy 6: Two-Pass Approach (Recommended for Limited Storage)
Extract in two phases based on priority and available storage.

**Phase 1 - Essential Data:**
```yaml
extraction:
  # First pass: Audio + single camera from all performances
  cameras: [25]  # Camera 25 only (works for all performances)
  performances:
    - "s1_all"
    - "s2_all"
    - "s3_all"  # Will get camera 25 from multi-view
    - "s4_all"
    - "s5_all"
    - "s6_all"
  modalities:
    - "audio"
    - "metadata"
    - "calibration"
    - "images"  # Only camera 25
```

**Phase 2 - Multi-view Data:**
```yaml
extraction:
  # Second pass: Additional cameras for s3_all only
  cameras: [0, 5, 9, 13, 16, 20, 24, 29, 37, 47, 53, 57]
  performances:
    - "s3_all"  # Multi-view only
  modalities:
    - "images"  # Additional camera views
```

**Pros:**
- Flexible storage management
- Can start research with Phase 1 data
- Add multi-view later when storage available

**Storage Estimate:**
- Phase 1: ~1GB per subject (500GB total)
- Phase 2: ~4GB per subject (2TB total)
- Combined: ~5GB per subject (2.5TB total)

---

## Decision Guide

### How to Choose Your Configuration:

1. **Available Storage:**
   - < 1TB: Use Strategy 3 (minimal) or Strategy 6 Phase 1
   - 1-2TB: Use Strategy 4A (8 cameras)
   - 2-3TB: Use Strategy 4B (12 cameras) - **Recommended**
   - 3-5TB: Use Strategy 5 (16 cameras)
   - > 8TB: Use Strategy 1 (full extraction)

2. **Research Requirements:**
   - Audio-only research: Extract audio modality only (~25GB total)
   - Single-view video: Use camera 25 only
   - 3D reconstruction: Minimum 8 cameras, ideally 12+
   - High-quality avatars: 16+ cameras recommended

3. **Processing Time:**
   - Fewer cameras = faster extraction
   - Each camera adds ~30 seconds per performance

## Implementation Notes

### Current Extraction Script Limitation
The current `extract_streaming_gdrive.py` expects a single camera list for all performances. To use performance-specific cameras (Strategy 2), you would need to modify the script.

### Quick Modification for Subset Extraction
To extract a specific subset without code changes, update your `config.yaml`:

```yaml
extraction:
  # For s3_all subset extraction
  cameras: [0, 5, 9, 13, 16, 20, 24, 29, 37, 47, 53, 57]  # Your chosen subset
  performances:
    - "s3_all"  # Only extract s3_all with these cameras
```

Then run single-view performances separately:
```yaml
extraction:
  cameras: [25]  # Camera 25 for single-view
  performances:
    - "s1_all"
    - "s2_all"
    - "s4_all"
    - "s5_all"
    - "s6_all"
```

## Quality Scores

Based on our analysis, here are the quality scores for different camera counts:

| Cameras | Angular Gap | Quality Score | Storage (500 subj) | Recommendation |
|---------|------------|---------------|-------------------|----------------|
| 4       | ~90°       | Low           | 750 GB           | Minimal only   |
| 8       | ~45°       | Good          | 1.5 TB           | Acceptable     |
| 12      | ~30°       | Very Good     | 2.2 TB           | **Recommended** |
| 16      | ~22.5°     | Excellent     | 3.0 TB           | High quality   |
| 20      | ~18°       | Outstanding   | 3.7 TB           | Professional   |
| 38      | Variable   | Complete      | 7.5 TB           | Full data      |

## Final Recommendations

### For Most Users:
Use **Strategy 4B** with 12 cameras for s3_all:
- Good balance of quality and storage
- Sufficient for most research applications
- Fits within 2TB budget with some room

### For Storage-Constrained:
Use **Strategy 6** (Two-pass approach):
- Start with Phase 1 for immediate research
- Add Phase 2 when storage available

### For High-Quality Requirements:
Use **Strategy 5** with 16 cameras:
- Excellent coverage for reconstruction
- Still manageable storage (3TB)

---

*Generated from camera analysis of subjects 0018, 0019, 0026*
*Last updated: 2025-09-05*