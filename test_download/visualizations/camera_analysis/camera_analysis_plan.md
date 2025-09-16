# Project Status and Next Steps - September 14, 2025

## Current Project Status

### What We're Building
We're developing a data extraction pipeline for the RenderMe360 21ID dataset (21 subjects, multi-view video capture) for audio-driven avatar research. The dataset has 60 cameras per frame, which is excessive for our needs.

### What's Been Completed

1. **Extraction Pipeline** 
   - Created `extract_subject_FULL_both.py` - streaming extraction from Google Drive
   - Fixed critical resume bug (checks completion before downloading)
   - Successfully extracted subject 0026, performance s1_all (101.69 GB)
   - Validated extraction matches original perfectly

2. **Google Drive Issue** 
   - Hit rate limiting on shared files (not personal quota)
   - Decision: Copy files to personal Drive (750GB/day limit)
   - Will process in daily batches of ~700GB

3. **Documentation** 
   - Created validation scripts
   - Added monitoring commands
   - Marked legacy scripts
   - Created basic README structure

### Current Challenge
- Full dataset: 60 cameras � 2529 frames = 151,740 images per performance (too much!)
- Storage limit: 1.8TB available (full dataset is 5.8TB)
- Need to reduce to a subset of cameras to fit storage.

## Next Task: Camera Selection Analysis

### Context

You are helping with a computer vision research project. We have a 360-degree camera setup with 60 cameras arranged in a cylinder around a human subject. We need to select the optimal subset cameras for audio-driven 360 degree consistent avatar research (focusing on facial animation synchronized with speech).

**Your task**: Analyze the camera setup and recommend which cameras to keep.

**Available Resources**:
1. **Existing extraction** at `/ssd2/zhuoyuan/renderme360_temp/FULL_EXTRACTION_BOTH/0026_s1_all/`
   - Contains images from all 60 cameras
   - Structure: `from_raw/images/cam_00/` through `cam_59/`
   - Each camera has 2529 frames 

2. **Calibration data** at `/ssd2/zhuoyuan/renderme360_temp/FULL_EXTRACTION_BOTH/0026_s1_all/from_anno/calibration/`
   - Camera matrices for all 60 cameras
   - Can be loaded with numpy: `np.load('all_cameras.npy', allow_pickle=True)`

3. **Previous Camera selection thought process** at `/ssd2/zhuoyuan/renderme360_temp/test_download/process_data/camera_analysis_20250915.md`
   - Some camera position analysis already done, evaluate the analysis and tell me what do you think
   - Check `camera_analysis.ipynb` for previous work

**Specific Tasks**:

1. **Camera Position Analysis**
   - Visualize camera arrangement like `/ssd2/zhuoyuan/renderme360_temp/download_all/visualizations/camera_analysis/all_38_cameras_grid.png` for all cameras
   - Visualize camera arrangement of your propose solution (or solutions) like `/ssd2/zhuoyuan/renderme360_temp/download_all/visualizations/camera_analysis/sample_frames_12_cameras.png` by creating a `/ssd2/zhuoyuan/renderme360_temp/test_download/visualizations/camera_analysis` folder and put solutions there.
   - Load calibration data to get 3D camera positions if possible (put this in the end because this might be complicated, ask me if I want you to do this and only do after my permission)
   - Identify front-facing vs side vs back cameras

2. **Camera Selection Criteria**
   - evaluate the `/ssd2/zhuoyuan/renderme360_temp/test_download/process_data/camera_analysis_20250915.md` and propose selection methods 

3. **You can consider Implementation**
   ```python
   # Sample code structure
   import numpy as np
   import matplotlib.pyplot as plt
   from mpl_toolkits.mplot3d import Axes3D

   # Load calibration
   calibs = np.load('path/to/all_cameras.npy', allow_pickle=True).item()

   # Extract camera positions (from extrinsic matrices)
   camera_positions = []
   for cam_id in range(60):
       # Extract translation from extrinsic matrix
       # Usually the last column of the 3x4 matrix
       pass

   # Visualize and select
   # Plot cameras in 3D space
   # Identify optimal subset
   ```

4. **Expected Output**
   - List of camera IDs to keep (e.g., [0, 12, 24, 36, 48])
   - Visualization showing selected cameras
   - Justification for selection
   - Config update for extraction:
   ```yaml
   extraction:
     cameras: [ID, ID, ID, ID, ID, ...]  # Your selected cameras
   ```

**Important Context**:
- This is for audio-driven avatar research, so facial features are critical
- Storage is limited (1.8TB), so fewer than 30 cameras is better
- The subject is sitting/standing in the center of a camera cylinder
- Cameras are numbered 0-59 in order around the cylinder

**Previous findings** (from earlier analysis):
- Cameras seem to be arranged in a cylindrical pattern
- Some cameras may be at different heights
- Camera 25 often has data in speech performances

**Next Steps After Camera Selection**:
1. Update `config_21id.yaml` with selected cameras or do you think we need to craete another .yaml with selected cameras?
2. Create `config_21id_reduced.yaml` for reduced extraction
3. Start copying data to personal Google Drive (750GB/day)
4. Begin extraction with reduced camera set
5. Monitor progress over the week

**File Locations**:
- Main extraction script: `/ssd2/zhuoyuan/renderme360_temp/test_download/process_data/extract_subject_FULL_both.py`
- Config file: `/ssd2/zhuoyuan/renderme360_temp/test_download/process_data/config_21id.yaml`
- Previous extraction: `/ssd2/zhuoyuan/renderme360_temp/FULL_EXTRACTION_BOTH/`
- New extractions go to: `/ssd2/zhuoyuan/renderme360_temp/test_download/subjects/`

Please analyze the camera setup and provide recommendations for the optimal camera subset for audio-driven avatar research.

---

# Plan: Camera Selection Implementation

## Phase 1: Camera Calibration Analysis (Current Focus)
**Goal**: Extract and analyze actual camera parameters to enable informed selection

### 1.1 Load Calibration Data
- Create a script to inspect one .npy file first to see what each cam_nn.npy file looks like. 
- Load all_cameras.npy from existing extraction and output all 60 camera calibration raw data for inspection. 
- Extract camera positions from RT matrices (camera→world transform)
- Compute intrinsic parameters (focal length → FOV classification)

### 1.2 Compute Camera Metrics
- **Yaw angle**: Azimuth around subject (0°=front, ±90°=sides, 180°=back)
- **Height**: Vertical position (Upper/Mid/Lower rings)
- **Distance**: Radial distance from subject
- **FOV type**: Classify as Small (narrow) or Large (wide) based on focal length

### 1.3 Analyze Distribution
- Identify camera clusters and gaps
- Map front vs rear hemisphere cameras
- Determine height ring membership
- Output: Camera metrics CSV/JSON for selection algorithm

**Output Location**: `/ssd2/zhuoyuan/renderme360_temp/test_download/visualizations/camera_analysis`
- `camera_metrics_60cam.json` - Full metrics for all 60 cameras
- `camera_analysis_report.txt` - Summary statistics

## Phase 2: Research-Aligned Camera Selection
**Goal**: Select optimal subsets based on computed metrics

### 2.1 Implement Selection Algorithm
- Front-dense selection (0°, ±30°, ±60°) with Small FOV preference
- Rear-sparse selection with Large FOV preference
- Multi-height for key angles (0°, ±30°)

### 2.2 Generate Camera Subsets
- **8-camera minimal**: Quick testing, basic coverage
- **12-camera balanced**: Recommended for quality/storage balance
- **16-camera high-quality**: Enhanced 360° consistency

### 2.3 Create Configuration Files
- Generate YAML configs with selected camera lists
- Include storage projections and quality metrics

## Phase 3: Visualization & Validation (Can Be Done Later)
**Goal**: Visual confirmation of selections

### 3.1 3D Camera Arrangement
- Cylindrical visualization of all 60 cameras
- Highlight selected subsets
- Show coverage gaps and density

### 3.2 Sample Frame Grids
- Display actual captured views from selected cameras
- Compare different subset options visually

### 3.3 Cross-Performance Validation (Important)
- Verify calibration consistency across different performances (e0 vs s1_all)
- Check if all 21 subjects share the same camera setup and FOV distribution
- Validate that camera selection will work for all subjects/performances
- Sample calibration from 2-3 different subjects to ensure consistency

## Phase 4: Storage Planning & Execution
**Goal**: Finalize extraction plan within constraints

### 4.1 Storage Calculations
- Accurate per-subject estimates
- Total projection for 21 subjects
- Extraction schedule to stay within 1.8TB

### 4.2 Update Extraction Pipeline
- Modify config_21id.yaml with selected cameras
- Test extraction with one subject
- Scale to remaining subjects




Phase 2 Implementation Plan: 
