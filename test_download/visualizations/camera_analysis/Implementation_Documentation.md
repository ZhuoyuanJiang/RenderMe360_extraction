# Camera Analysis Implementation Documentation

## Overview
This document details the implementation process for analyzing RenderMe360 camera calibration data to enable informed camera subset selection for the 21ID dataset extraction.

## Data Source
- **Subject**: 0026
- **Performance**: s1_all (speech performance 1)
- **Calibration File**: `/ssd2/zhuoyuan/renderme360_temp/FULL_EXTRACTION_BOTH/0026_s1_all/from_anno/calibration/all_cameras.npy`
- **Note**: Camera calibration is **static across all frames** in a performance. The calibration matrices define the camera setup and don't change frame-to-frame.



# Phase 1:

## File Descriptions

### 1. `analyze_calibration_phase1.py` - Main Analysis Script
**Purpose**: Extracts and computes camera metrics from raw calibration data

**What it does**:
- Loads `all_cameras.npy` from the extraction (raw calibration data from RenderMe360)
- Performs multiple computations on each camera's calibration data
- Generates all output files (JSON metrics, stats, report)

**Key processing steps**:
1. **Loads raw calibration** - The `.npy` file contains raw matrices from RenderMe360
2. **Extracts camera positions** - From RT matrix using direct translation vector
3. **Computes derived metrics** for each camera
4. **Generates statistics** across all cameras
5. **Saves results** in multiple formats

**Usage**:
```bash
python analyze_calibration_phase1.py
```

**Input**:
- Calibration file: `/ssd2/zhuoyuan/renderme360_temp/FULL_EXTRACTION_BOTH/0026_s1_all/from_anno/calibration/all_cameras.npy`
- Expected format: Dictionary with camera IDs as keys, each containing 'K', 'D', 'RT' matrices

**Output Files** (saved to `/ssd2/zhuoyuan/renderme360_temp/download_all/visualizations/camera_analysis/`):
- `camera_metrics_60cam.json` - Detailed metrics for each camera (position, yaw, height, FOV, etc.)
- `camera_summary_stats.json` - Statistical summary and distributions
- `camera_analysis_report.txt` - Human-readable report

**Key Methods**:
1. **`load_calibrations()`** - Loads the `.npy` file containing RenderMe360 calibration data
2. **`extract_camera_position(RT)`** - Extracts world position from RT matrix using `RT[:3, 3]`
3. **`compute_yaw_angle(position)`** - Calculates azimuth angle using `atan2(x, z)`
4. **`classify_height(position, all_heights)`** - Categorizes cameras into Upper/Middle/Lower terciles
5. **`classify_fov(K, image_width)`** - Determines FOV type from intrinsic matrix
6. **`analyze_angular_sectors()`** - Analyzes distribution across 60° sectors
7. **`analyze_all_cameras()`** - Main processing pipeline combining all metrics
8. **`generate_summary_statistics()`** - Aggregates statistics across all cameras
9. **`save_results(output_dir)`** - Saves all outputs to specified directory

**Key Processing Formulas**:
```python
# Extract camera position (world coordinates)
position = RT[:3, 3]  # Direct translation vector

# Compute yaw angle (azimuth around subject)
yaw = atan2(position[0], position[2])  # Result in radians, convert to degrees

# Calculate distance from origin
distance = np.linalg.norm(position)

# Determine field of view
fov = 2 * atan(image_width / (2 * focal_length))  # image_width = 2448 pixels

# Classify into categories:
- Height: Upper/Middle/Lower based on terciles of Y coordinates
- Hemisphere: Front (-90° ≤ yaw ≤ 90°) or Rear
- FOV Type: Small (<55°) or Large (≥55°)
- Angular Sector: 60° sectors for uniformity analysis
```

### 2. `camera_metrics_60cam.json` - Processed Camera Metrics
**This is PROCESSED DATA, not raw!**

**How it was generated from raw calibration**:

For each camera, the script computed:

1. **`position`** - Extracted from RT matrix (after correction, used direct translation vector)
   - Raw: 4×4 RT matrix in `all_cameras.npy`
   - Processed: `[x, y, z]` coordinates in meters
   - **Formula**: `position = RT[:3, 3]` (direct extraction of translation component)

2. **`yaw_deg`** - Computed from position
   - **Formula**: `atan2(x, z)` converted to degrees
   - Indicates camera's angle around subject (0°=front, ±90°=sides, ±180°=back)

3. **`height`** - Y-coordinate of position
   - Direct extraction from position vector
   - Negative values mean camera is above subject (Y-axis inverted in RenderMe360)

4. **`height_class`** - Classified into U/M/L
   - Computed by sorting all heights and dividing into terciles
   - U = Upper third (most negative Y values)
   - M = Middle third
   - L = Lower third (near 0 or positive Y values)

5. **`distance`** - Euclidean distance from origin
   - **Formula**: `sqrt(x² + y² + z²)`

6. **`fov_type`** - Classified from intrinsic matrix K
   - Computed horizontal FOV: `2 * atan(image_width / (2 * focal_length))`
   - Threshold: <55° = "Small", >55° = "Large"
   - **Result**: All 60 cameras have ~29° FOV (narrow/telephoto)
   - **Note**: While RenderMe360 website mentions mixed FOV cameras, this particular subject/performance has uniform narrow FOV

7. **`hemisphere`** - Determined from yaw angle
   - Front: -90° ≤ yaw ≤ 90°
   - Rear: yaw < -90° or yaw > 90°

8. **`focal_length`** - Extracted from K matrix
   - Raw value from `K[0, 0]` (fx component)

### 3. `camera_summary_stats.json` - Statistical Summary
**Derived from the processed metrics above**

Contains:
- **Total camera count**: 60
- **Yaw range**: -170.7° to 171.2° (confirming 360° coverage)
- **Height range**: -1.161m to 0.059m (1.22m vertical span)
- **Distance statistics**: mean, std, min, max from subject
- **Distribution counts**:
  - Hemispheres: 31 front, 29 rear
  - Heights: 21 upper, 19 middle, 20 lower
  - FOV types: 60 small, 0 large
- **Angular gap analysis**: Computed gaps between adjacent cameras when sorted by yaw
- **Coverage percentage**: 51.7% front, 48.3% rear

### 4. `test_rt_interpretation.py` - Diagnostic Script
**Purpose**: Figured out the correct way to extract camera positions from RT matrices

**Why it was needed**:
- Initial analysis showed all cameras clustered at 0-7° yaw (clearly wrong for a 360° setup)
- Tested 4 different methods to interpret RT matrix:

**Methods tested**:
1. **Direct translation `t`**: `position = RT[:3, 3]`
2. **Inverse transform**: `position = -R^T @ t`
3. **Negative translation**: `position = -t`
4. **Full inverse**: `position = inv(RT)[:3, 3]`

**Result**:
- Method 1 (direct translation) gave proper 360° coverage (-170° to 171°)
- Method 2 & 4 gave incorrect clustering (all cameras 0-7°)
- Method 3 gave inverted but plausible distribution

**Conclusion**: RenderMe360 stores camera world positions directly in the translation component of RT

### 5. `extract_all_raw_data.py` - Raw Data Extraction Script
**Purpose**: Extract all raw calibration data from all_cameras.npy to JSON

**What it does**:
- Loads the raw calibration data from the .npy file
- Converts numpy arrays to JSON-serializable format
- Saves everything to `ALL_raw_calibration_data.json`
- Confirms raw data contains only K, D, RT as documented on RenderMe360 website

**Output**:
- `ALL_raw_calibration_data.json` - Complete raw calibration data for all 60 cameras

### 6. `inspect_npy_file.py` - NPY File Inspector Tool
**Purpose**: General tool to inspect ANY .npy file and see what's inside

**Usage**:
```bash
python inspect_npy_file.py <path_to_npy_file>
```

**What it does**:
- Loads any .npy file and displays its contents
- Shows data type, structure, and dimensions
- Works with dictionaries, arrays, and pickled objects
- Provides example of first item for complex structures

**Example usage**:
```bash
# Inspect calibration data
python inspect_npy_file.py /path/to/all_cameras.npy

# Inspect any other .npy file
python inspect_npy_file.py /path/to/any/file.npy
```

### 7. `camera_analysis_report.txt` - Human-Readable Report
**Generated from the summary statistics**

Formatted text report showing:
- Total camera count and distributions
- Key findings about the setup
- Recommendations for next steps

### 8. `ALL_raw_calibration_data.json` - Raw Calibration Data
**Complete raw data extracted from all_cameras.npy**

Contains for each camera:
- **K**: 3×3 intrinsic matrix
- **D**: 5 distortion coefficients
- **RT**: 4×4 extrinsic matrix

## Data Processing Flow

```
RAW DATA                    PROCESSING                          OUTPUT
--------                    ----------                          ------
all_cameras.npy      →      analyze_calibration_phase1.py
(60 camera dicts)           │
  ├─ 'RT' (4×4)            ├─ Extract positions from RT[:3,3]
  ├─ 'K' (3×3)             ├─ Compute yaw = atan2(x,z)
  └─ 'D' (distortion)      ├─ Classify heights into terciles
                           ├─ Determine FOV from K matrix
                           └─ Calculate distances from origin
                                    ↓
                           camera_metrics_60cam.json (PROCESSED)
                                    ↓
                           camera_summary_stats.json (STATISTICS)
                                    ↓
                           camera_analysis_report.txt (SUMMARY)
```

## Critical Discovery: RT Matrix Interpretation

### Initial Error
- **Assumption**: RT matrix needed inverse transformation to get camera position
- **Implementation**: `camera_pos = -R^T @ t` where R = RT[:3,:3], t = RT[:3,3]
- **Result**: All cameras appeared in narrow range (-3.9° to 3.1° yaw)
- **Problem**: This would mean all 60 cameras face forward - impossible for 360° capture!

### Testing Process
Created `test_rt_interpretation.py` to test different interpretations:
- Tested 4 cameras (0, 15, 30, 45) with all methods
- Checked which method gave ~360° coverage
- Method 1 (direct translation) showed proper distribution

### Correction
- **Correct formula**: `camera_pos = RT[:3, 3]` (direct translation vector)
- **Result**: Cameras properly distributed from -170.7° to 171.2°
- **Validation**: 31 front, 29 rear cameras - matches expected 360° setup

## Raw Data Structure and Location

**Location of raw data**: `/ssd2/zhuoyuan/renderme360_temp/FULL_EXTRACTION_BOTH/0026_s1_all/from_anno/calibration/all_cameras.npy`

**As documented on RenderMe360 website**, each camera contains exactly three matrices (K, D, RT):
```python
{
    'K': array([[fx,  0, cx],
                [ 0, fy, cy],
                [ 0,  0,  1]]),  # 3×3 intrinsic matrix

    'D': array([...]),           # Distortion coefficients (5 values)

    'RT': array([[r11, r12, r13, tx],
                 [r21, r22, r23, ty],
                 [r31, r32, r33, tz],
                 [  0,   0,   0,  1]])  # 4×4 extrinsic matrix
}
```

Where:
- **K**: Camera intrinsic parameters (focal length, principal point)
  - fx, fy: Focal lengths in pixels
  - cx, cy: Principal point (optical center)
- **D**: Lens distortion coefficients (5 values, all zeros in this dataset)
- **RT**: Camera extrinsic parameters (rotation + translation)
  - Upper-left 3×3: Rotation matrix R
  - Upper-right 3×1: Translation vector t = [tx, ty, tz]
  - The translation component directly gives camera position in world coordinates

## Validation & Verification

### Initial Validation
To verify the analysis:
1. Check that yaw angles span ~360° range ✓
2. Confirm roughly equal front/rear distribution ✓
3. Verify three distinct height clusters ✓
4. Ensure all cameras are ~1-1.6m from origin (realistic for studio setup) ✓

All validation checks passed after correcting the RT interpretation.

## Additional Verification (September 15, 2025)

### 1. FOV Calculation Verification

**Method**: Re-computed FOV for all 60 cameras using the formula:
```python
FOV = 2 * atan(image_width / (2 * focal_length))
```

**Findings**:
- **All 60 cameras have narrow FOV**: ~29° (ranging from 28.79° to 29.35°)
- **Focal lengths are uniform**: All cameras use ~4700 pixel focal length
- **No wide-angle cameras detected**: Despite RenderMe360 documentation mentioning "mixed FOV"

**Sample verification output**:
```
Camera 0 : fx=4707.0, FOV=29.15°
Camera 15: fx=4708.1, FOV=29.15°
Camera 30: fx=4699.0, FOV=29.20°
Camera 45: fx=4713.2, FOV=29.12°
Min FOV: 28.79°, Max FOV: 29.35°, Mean FOV: 29.11°
```

### 2. Camera Distribution Analysis

**Method**: Analyzed angular distribution across 60° sectors

**Angular Sector Classification Code**:
```python
# Sector definitions for 360° coverage analysis
sectors = {
    'Front center (-30° to 30°)': [],
    'Right side (30° to 90°)': [],
    'Left side (-90° to -30°)': [],
    'Back center (150° to -150°)': [],
    'Right back (90° to 150°)': [],
    'Left back (-150° to -90°)': []
}

# Classify each camera into sectors
for cam_id, data in metrics.items():
    yaw = data['yaw_deg']
    if -30 <= yaw <= 30:
        sectors['Front center (-30° to 30°)'].append(cam_id)
    elif 30 < yaw <= 90:
        sectors['Right side (30° to 90°)'].append(cam_id)
    elif -90 <= yaw < -30:
        sectors['Left side (-90° to -30°)'].append(cam_id)
    elif yaw > 150 or yaw < -150:
        sectors['Back center (150° to -150°)'].append(cam_id)
    elif 90 < yaw <= 150:
        sectors['Right back (90° to 150°)'].append(cam_id)
    elif -150 <= yaw < -90:
        sectors['Left back (-150° to -90°)'].append(cam_id)
```

**Distribution Results**:
- **Front center (-30° to 30°)**: 10 cameras (16.7%)
- **Right side (30° to 90°)**: 11 cameras (18.3%)
- **Left side (-90° to -30°)**: 10 cameras (16.7%)
- **Back center (150° to -150°)**: 11 cameras (18.3%)
- **Right back (90° to 150°)**: 10 cameras (16.7%)
- **Left back (-150° to -90°)**: 8 cameras (13.3%)

**Key Finding**: The distribution is **nearly uniform**, not front-dense as initially expected. Each 60° sector contains 8-11 cameras (13-18% each).

### 3. Hemisphere Analysis Clarification

**Original Classification** (from analyze_calibration_phase1.py):
- Front hemisphere: -90° ≤ yaw ≤ 90° → 31 cameras (51.7%)
- Rear hemisphere: yaw < -90° or yaw > 90° → 29 cameras (48.3%)

This shows a nearly 50/50 split, confirming uniform distribution rather than front-dense setup.

## Implications for Camera Selection (Phase 2)

Given the uniform FOV and distribution findings:

### What We Can't Do:
1. **Can't use FOV mixing** - All cameras have same narrow FOV (~29°)
2. **Can't rely on natural front density** - Distribution is uniform
3. **Can't use wide cameras for sparse rear coverage** - No wide cameras exist

### What We Should Do:
1. **Focus on angular spacing** - Select cameras with even angular gaps
2. **Leverage height variation** - Include all three height levels (U/M/L)
3. **Create artificial front emphasis** - Manually select more front cameras if needed
4. **Ensure coverage continuity** - Avoid large angular gaps (current max gap is 20°)

### Recommended Selection Strategy:
- **For minimal sets (8-12 cameras)**: Prioritize uniform angular spacing
- **For quality sets (16+ cameras)**: Add extra front cameras for facial detail
- **Height strategy**: Include at least one camera from each height at key angles (0°, ±30°, 180°)

## Notes on Dataset Characteristics

### Discovered Properties:
1. **Uniform narrow FOV** across all 60 cameras (~29°)
2. **Nearly uniform angular distribution** (not front-dense)
3. **Three distinct height levels** with 19-21 cameras each
4. **Camera distance variation**: 1.12m to 1.62m from subject

### Comparison to Expected:
- **Expected**: Mixed FOV (wide + narrow), front-dense arrangement
- **Actual**: Uniform narrow FOV, uniform angular distribution

This might be specific to:
- This particular subject (0026)
- This particular performance (s1_all)
- Or could be standard for all RenderMe360 captures

**TODO**: Cross-validate with other subjects/performances to confirm if this is universal.


# Phase 2: 
