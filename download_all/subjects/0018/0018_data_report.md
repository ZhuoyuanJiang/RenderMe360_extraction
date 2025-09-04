# Subject 0018 Data Analysis Report

## Summary
Subject 0018 extraction completed on 2025-09-03 with significant camera availability issues discovered. The dataset shows extremely sparse camera coverage, with most performances having only 1 camera available despite metadata reporting 60 cameras.

## Subject Information
- **Subject ID**: 0018
- **Gender**: Male
- **Age**: 27
- **Height**: 182.0 cm
- **Weight**: 65.3 kg
- **Capture Date**: 2022-08-20
- **Total Extracted Size**: 12.07 GB

## Camera Availability Analysis

### Critical Finding
**The SMC files report 60 cameras in metadata, but actual camera data availability is extremely limited:**

| Performance | Reported Cameras | Actual Cameras with Data | Coverage % |
|------------|------------------|-------------------------|------------|
| s1_all | 60 | 1 (cam_25 only) | 1.67% |
| s2_all | 60 | 1 (cam_25 only) | 1.67% |
| s3_all | 60 | 38 cameras | 63.33% |
| s4_all | 60 | 1 (cam_25 only) | 1.67% |
| s5_all | 60 | 1 (cam_25 only) | 1.67% |
| s6_all | 60 | 1 (cam_25 only) | 1.67% |

### Camera Distribution Details

#### s3_all - Most Complete Performance (38 cameras)
Available cameras: 00, 01, 03, 04, 05, 07, 09, 11, 13, 15, 16, 17, 19, 20, 21, 23, 24, 25, 27, 28, 29, 31, 32, 33, 35, 37, 39, 40, 41, 43, 45, 47, 48, 49, 53, 55, 57, 59

Missing cameras (22): 02, 06, 08, 10, 12, 14, 18, 22, 26, 30, 34, 36, 38, 42, 44, 46, 50, 51, 52, 54, 56, 58

#### Other Performances (s1, s2, s4, s5, s6)
- **Only camera 25 has data** across all these performances
- This represents a single viewpoint for speech data
- Camera 25 appears to be the most reliable/central camera

## Performance Statistics

| Performance | Frames | Size (GB) | Images | Audio | Calibration |
|------------|--------|-----------|--------|-------|-------------|
| s1_all | 1,911 | 1.04 | ✓ (cam_25) | ✓ | ✓ |
| s2_all | 1,871 | 1.02 | ✓ (cam_25) | ✓ | ✓ |
| s3_all | 9,391 | 8.99 | ✓ (38 cams) | ✓ | ✓ |
| s4_all | 897 | 0.49 | ✓ (cam_25) | ✓ | ✓ |
| s5_all | 659 | 0.36 | ✓ (cam_25) | ✓ | ✓ |
| s6_all | 791 | 0.44 | ✓ (cam_25) | ✓ | ✓ |

## Data Quality Issues

### 1. Severe Camera Sparsity
- **Expected**: 60 cameras × 6 performances = 360 camera-performance combinations
- **Actual**: 43 camera-performance combinations (11.9% of expected)
- Most performances have 98.3% camera data missing

### 2. Inconsistent Camera Availability
- s3_all has reasonable multi-view coverage (38 cameras)
- All other performances limited to single view
- No clear pattern for missing cameras

### 3. Extraction Errors
The original extraction script generated thousands of errors due to assuming all 60 cameras existed:
- "Invalid Camera_id" errors for cameras 44, 46, and many others
- Attempted to extract from non-existent cameras 0-59

## Implications for Research

### For Audio-Driven Avatar Research
1. **Limited Multi-View Data**: Only s3_all provides multi-view synchronized data
2. **Single View Dominance**: Most speech data (s1, s2, s4, s5, s6) only available from camera 25
3. **3D Reconstruction Challenges**: Insufficient camera coverage for robust 3D reconstruction in most performances

### Recommended Usage
- **For single-view models**: Use camera 25 data from all performances
- **For multi-view models**: Focus on s3_all performance only
- **For testing**: s3_all provides best camera coverage for evaluation

## Storage Optimization
Despite missing camera data, extraction still resulted in 12.07 GB:
- Most space from s3_all (8.99 GB with 38 cameras)
- Single camera performances are storage-efficient (0.36-1.04 GB each)

## Recommendations

### Immediate Actions
1. ✅ **Fixed extraction script** to detect actual available cameras dynamically
2. ✅ **Updated logging** to report actual vs. expected camera counts
3. **Verify other subjects** for similar camera availability issues

### For Full Dataset Processing
1. **Expect high variability** in camera availability across subjects
2. **Prioritize camera 25** as it appears most reliable
3. **Consider s3_all** as primary source for multi-view data
4. **Update storage estimates** - actual storage may be less than expected due to missing cameras

## Technical Notes

### Original Issue
The extraction script incorrectly assumed cameras 0-59 all existed based on `num_device=60` in metadata, causing thousands of extraction errors.

### Solution Implemented
Modified `extract_streaming_gdrive.py` to:
- Query actual available cameras from SMC file structure
- Only attempt extraction from cameras that exist
- Log actual vs. reported camera counts
- Handle sparse camera arrangements gracefully

### Verification
After fixes, extraction should complete without "Invalid Camera_id" errors and properly report which cameras are available for each performance.

---

*Report generated: 2025-09-04*
*Analysis based on extracted data from RenderMe360 Google Drive release (August 2024)*