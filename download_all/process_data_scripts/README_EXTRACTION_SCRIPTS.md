# RenderMe360 Streaming Extraction Pipeline

## Overview

This is a streaming extraction pipeline for downloading and processing the RenderMe360 dataset from Google Drive. Unlike the previous approach that required separate annotation and raw files, this pipeline handles the new unified format where each performance is stored as a single raw SMC file on Google Drive.

**Key Features:**
- **Streaming Processing**: Downloads and processes one subject at a time to manage storage
- **Selective Extraction**: Only downloads speech performances (s1_all through s6_all)
- **Configurable Cameras**: Support for extracting all 60 cameras or a subset
- **Resume Capability**: Tracks progress in MANIFEST.csv for failure recovery
- **Google Drive Integration**: Uses rclone to handle quotas and retries
- **Optimized Storage**: Each subject only requires 10-15GB (vs 590GB in old format)
- **No Compression**: Saves raw image data without compression for maximum quality

## Prerequisites

### 1. Python Environment
```bash
# Create and activate conda environment
conda create -n RenderMe360_Streaming python=3.9 -y
conda activate RenderMe360_Streaming

# Install dependencies (or use requirements.txt if provided)
pip install opencv-python numpy tqdm pydub h5py pandas matplotlib pyyaml
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install plyfile  # Optional, for 3D mesh extraction

# IMPORTANT: Always activate the environment before running scripts
conda activate RenderMe360_Streaming
```

### 2. Rclone Configuration
Ensure rclone is configured with access to Google Drive:
```bash
# Check if vllab13 remote exists
rclone listremotes | grep vllab13

# Test access (replace with actual folder ID)
rclone ls vllab13: --drive-root-folder-id YOUR_FOLDER_ID --max-depth 1
```

### 3. Storage Requirements
- **Temporary space**: ~50GB for downloaded SMC files
- **Output space**: ~10-15GB per subject
- **Total for 500 subjects**: ~5-7.5TB (process in batches if needed)

## Configuration

Edit `config.yaml` before running:

```yaml
google_drive:
  root_folder_id: "YOUR_ACTUAL_FOLDER_ID"  # ← UPDATE THIS
  remote_name: "vllab13"

extraction:
  subjects: ["0018"]  # Start with one subject for testing
  performances: ["s1_all", "s2_all", "s3_all", "s4_all", "s5_all", "s6_all"]
  cameras: "all"  # Change to subset after visualization
```

## Usage

### Step 1: Test with First Subject

Extract subject 0018 with all 60 cameras:

```bash
# IMPORTANT: Always activate environment first
conda activate RenderMe360_Streaming

# Run extraction for first subject
python extract_streaming_gdrive.py --config config.yaml

# Or process single performance for testing
python extract_streaming_gdrive.py --subject 0018 --performance s1_all

# Monitor logs in real-time (in another terminal)
tail -f /ssd2/zhuoyuan/renderme360_temp/download_all/logs/extraction_*.log
```

### Step 2: Visualize and Select Cameras

After extracting the first subject, create visualization to select camera subset:

```bash
# Create camera grid visualization
python visualization.py camera_grid \
    --subject_dir /ssd2/zhuoyuan/renderme360_temp/download_all/subjects/0018 \
    --performance s1_all \
    --frame 100 \
    --output visualizations/camera_grid.png

# Analyze camera positions from calibration
python visualization.py analyze \
    --subject_dir /ssd2/zhuoyuan/renderme360_temp/download_all/subjects/0018

# View extraction progress
python visualization.py summary \
    --manifest /ssd2/zhuoyuan/renderme360_temp/download_all/MANIFEST.csv
```

### Step 3: Update Configuration for Production

Based on visualization, update `config.yaml`:

```yaml
extraction:
  # Add all subjects
  subjects: ["0018", "0019", "0020", ...]  # Up to 500 subjects
  
  # Select camera subset for 360° coverage
  cameras: [0, 6, 12, 18, 24, 30, 36, 42, 48, 54]  # 10 cameras
```

### Step 4: Run Full Extraction

```bash
# Run extraction for all configured subjects
python extract_streaming_gdrive.py

# Monitor progress in another terminal
tail -f /ssd2/zhuoyuan/renderme360_temp/download_all/MANIFEST.csv
```

## Workflow Details

### Processing Flow

1. **For each subject in config**:
   - Download all 6 speech SMC files from Google Drive
   - Extract each performance sequentially
   - Delete SMC files after extraction
   - Update manifest with results
   - Move to next subject

2. **For each performance**:
   - Initialize SMCReader with downloaded SMC file
   - Extract configured modalities:
     - Metadata and calibration
     - Images from selected cameras
     - Masks (if available)
     - Audio track
     - 2D/3D keypoints
   - Save to structured output directory
   - Mark as complete

### Logging

The pipeline provides comprehensive logging to track extraction progress:

### Log Files
- Location: `/ssd2/zhuoyuan/renderme360_temp/download_all/logs/`
- Format: `extraction_YYYYMMDD_HHMMSS.log`
- Contains both console output and detailed debug information

### What Gets Logged
- **Download Progress**: Subject ID, performance, file size
- **Extraction Status**: Success/failure for each performance
- **Error Details**: Full error messages for failed operations
- **Statistics**: Total size, processing time, success rate
- **Summary**: List of completed and failed extractions

### Monitoring Logs
```bash
# Real-time monitoring
tail -f /ssd2/zhuoyuan/renderme360_temp/download_all/logs/extraction_*.log

# Check for errors
grep ERROR /ssd2/zhuoyuan/renderme360_temp/download_all/logs/extraction_*.log

# View summary statistics
grep "EXTRACTION SUMMARY" -A 20 /ssd2/zhuoyuan/renderme360_temp/download_all/logs/extraction_*.log
```

## Output Structure

```
/ssd2/zhuoyuan/renderme360_temp/download_all/
├── subjects/
│   ├── 0018/
│   │   ├── s1_all/
│   │   │   ├── metadata/
│   │   │   │   └── info.json
│   │   │   ├── calibration/
│   │   │   │   ├── all_cameras.npy
│   │   │   │   └── cam_XX.npy
│   │   │   ├── images/
│   │   │   │   ├── cam_00/
│   │   │   │   │   ├── frame_000000.jpg
│   │   │   │   │   └── ...
│   │   │   │   └── cam_59/
│   │   │   ├── masks/
│   │   │   ├── audio/
│   │   │   │   ├── audio.mp3
│   │   │   │   └── audio_data.npz
│   │   │   ├── keypoints2d/
│   │   │   ├── keypoints3d/
│   │   │   └── .extraction_complete
│   │   └── s2_all/
│   └── 0019/
├── MANIFEST.csv
├── config.yaml
└── logs/
```

### Manifest Format

The `MANIFEST.csv` tracks extraction progress:

| Column | Description |
|--------|------------|
| subject | Subject ID (e.g., "0018") |
| performance | Performance name (e.g., "s1_all") |
| status | completed/failed/download_failed |
| cameras_extracted | Number of cameras extracted |
| frames | Number of frames in performance |
| size_gb | Extracted data size in GB |
| timestamp | When extraction occurred |
| error | Error message if failed |

## Camera Selection Guide

### Recommended Camera Subsets

Based on 60 cameras arranged in a circle:

- **6 cameras** (every 60°): `[0, 10, 20, 30, 40, 50]`
- **10 cameras** (every 36°): `[0, 6, 12, 18, 24, 30, 36, 42, 48, 54]`
- **12 cameras** (every 30°): `[0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55]`
- **15 cameras** (every 24°): `[0, 4, 8, 12, 16, 20, 24, 28, 32, 36, 40, 44, 48, 52, 56]`

### Selection Criteria

1. **360° Coverage**: Ensure cameras are evenly distributed around subject
2. **Height Variation**: Include cameras at different heights if available
3. **Quality**: Skip cameras with occlusions or poor lighting
4. **Processing Time**: Fewer cameras = faster extraction

## Troubleshooting

### Common Issues

1. **Google Drive Quota Exceeded**
   ```
   Error: User rate limit exceeded
   ```
   **Solution**: Wait 24 hours or use different Google account

2. **Rclone Not Configured**
   ```
   Error: Remote "vllab13" not found
   ```
   **Solution**: Configure rclone with Google Drive access

3. **Insufficient Storage**
   ```
   Error: Insufficient storage space
   ```
   **Solution**: Clean temp directory or increase min_free_space_gb limit

4. **SMC File Not Found**
   ```
   Error: Failed to download X_sY_all_raw.smc
   ```
   **Solution**: Check if subject exists in Google Drive folder

5. **Extraction Fails Mid-Process**
   ```
   Error: Failed to extract performance
   ```
   **Solution**: Check manifest, delete incomplete folder, re-run

### Resume After Failure

The pipeline automatically resumes from where it left off:

```bash
# Check what's completed
grep completed /ssd2/zhuoyuan/renderme360_temp/download_all/MANIFEST.csv

# Re-run extraction (skips completed performances)
python extract_streaming_gdrive.py

# Force re-extraction of specific performance
rm -rf /ssd2/zhuoyuan/renderme360_temp/download_all/subjects/0018/s1_all
python extract_streaming_gdrive.py --subject 0018 --performance s1_all
```

### Monitoring Progress

```bash
# Watch manifest updates
watch -n 5 'tail -20 /ssd2/zhuoyuan/renderme360_temp/download_all/MANIFEST.csv'

# Check storage usage
du -sh /ssd2/zhuoyuan/renderme360_temp/download_all/subjects/*

# Monitor temp directory
ls -lh /ssd2/zhuoyuan/renderme360_temp/temp_smc/
```

## Differences from Old Pipeline

### Old System (`extract_0026_FULL.py`)
- Required separate anno and raw SMC files
- Extracted from two sources (from_anno/ and from_raw/)
- Full extraction was 590GB per subject
- Masks were in anno files, images in raw files
- Designed for single subject (0026)

### New System (`extract_streaming_gdrive.py`)
- Single raw SMC file per performance
- Unified output structure (no anno/raw split)
- Optimized to 10-15GB per subject
- Streams from Google Drive
- Handles 500 subjects with resume capability
- Configurable camera and modality selection

### Key Improvements
1. **Storage Efficiency**: 40x reduction in storage requirements
2. **Scalability**: Handles 500 subjects vs single subject
3. **Robustness**: Resume capability and error handling
4. **Flexibility**: Configurable extraction parameters
5. **Integration**: Direct Google Drive download with rclone

## Advanced Usage

### Batch Processing

Process subjects in batches:

```python
# In config.yaml, specify batch
extraction:
  subjects: ["0018", "0019", "0020", "0021", "0022"]  # Batch 1

# After completion, update for next batch
extraction:
  subjects: ["0023", "0024", "0025", "0026", "0027"]  # Batch 2
```

### Custom Modality Selection

Extract only specific data types:

```yaml
extraction:
  modalities:
    - "audio"       # Only audio for speech synthesis
    - "keypoints3d" # Only 3D landmarks for animation
```

### Parallel Processing

Run multiple instances with different subjects:

```bash
# Terminal 1
python extract_streaming_gdrive.py --subject 0018

# Terminal 2  
python extract_streaming_gdrive.py --subject 0019
```

## Performance Metrics

Expected extraction times and sizes:

| Metric | Value |
|--------|-------|
| Download speed | 10-50 MB/s (depends on connection) |
| Extraction speed | ~5-10 minutes per performance |
| Total per subject | ~30-60 minutes |
| Storage per subject | 10-15 GB |
| Storage per performance | 1.5-2.5 GB |

## Support and Issues

For issues or questions:
1. Check the troubleshooting section
2. Review MANIFEST.csv for error messages
3. Check logs in `/ssd2/zhuoyuan/renderme360_temp/download_all/logs/`
4. Refer to `context.md` for background information

## Next Steps

After successful extraction:
1. Use the extracted data for audio-driven avatar research
2. Process with downstream models
3. Create visualizations and demos
4. Share processed data with team

## ⚠️ Critical Update (2025-09-04): Camera Availability Issue Fixed

### Discovery
Subject 0018 extraction revealed that **RenderMe360 has extremely sparse camera data**:
- Metadata reports 60 cameras via `num_device` field
- **Actual data availability is much lower:**
  - Most performances (s1, s2, s4, s5, s6): Only camera 25 has data
  - s3_all: 38 cameras have data (best coverage)
  - Missing cameras cause thousands of "Invalid Camera_id" errors

### Fix Applied
Modified `extract_streaming_gdrive.py` to dynamically detect available cameras:
```python
# OLD: Assumed all cameras 0-59 exist
camera_list = list(range(total_cameras))

# NEW: Query actual available cameras
available_cameras = sorted([int(cam_id) for cam_id in reader.smc["Camera"].keys()])
```

### Impact
- ✅ Eliminates "Invalid Camera_id" errors
- ✅ Properly handles sparse camera arrangements
- ✅ Logs actual vs reported camera counts
- ✅ Only extracts from cameras that exist

### Recommendations
1. **Camera 25 is most reliable** - present in all performances
2. **Storage will be less than expected** due to missing cameras
3. **Multi-view data limited** - only s3_all has good coverage
4. **Verify each subject** - camera availability may vary

See `/subjects/0018/0018_data_report.md` for detailed analysis.

---

## Implementation Status (2025-09-04)

### ✅ Completed Components

1. **Main Extraction Script (`extract_streaming_gdrive.py`)** *(Updated 2025-09-04)*
   - Full streaming pipeline implementation
   - Rclone integration for Google Drive downloads
   - No image compression - preserves raw quality
   - Immediate SMC deletion after extraction
   - Resume capability via MANIFEST.csv
   - **NEW**: Dynamic camera detection to handle sparse camera data
   - **NEW**: Proper error handling for missing cameras

2. **Configuration (`config.yaml`)**
   - Configured with actual Google Drive folder ID: `1vBmxhazI6atQEcCfi4wstoiAyFyK0-Ig`
   - Set up for test subject 0018
   - All 60 cameras enabled for initial extraction

3. **Visualization Tools (`visualization.py`)**
   - Camera grid visualization
   - Coverage analysis from calibration
   - Progress summary from manifest
   - Camera subset suggestions

4. **Comprehensive Logging**
   - Timestamped log files in `/logs/`
   - Dual console + file output
   - Detailed download/extraction tracking
   - Statistics and failure reporting

5. **Documentation**
   - Complete usage instructions
   - Troubleshooting guide
   - Environment setup with conda

### 🔄 Current Environment

- **Server**: vllab9
- **Conda Environment**: RenderMe360_Data_Processing
- **Dependencies**: All installed (opencv-python, numpy, tqdm, pydub, h5py, pandas, matplotlib, pyyaml)
- **Rclone**: Configured with remote "vllab13"

### ✅ Verified Google Drive Access

- Successfully accessed 501 subject folders
- Confirmed file structure (19 files per subject)
- Speech performances total ~7.36 GB for subject 0018
- Note: s3_all is unusually large (5.97 GB)

### ⚠️ Camera Availability Discovery (2025-09-04)

- **Subject 0018 has very limited camera data:**
  - s1, s2, s4, s5, s6: Only camera 25 has images
  - s3_all: 38 cameras have images (best coverage)
  - Extraction script updated to handle this gracefully

### 🚀 Ready to Run

```bash
# The pipeline is ready for first extraction
conda activate RenderMe360_Data_Processing
python extract_streaming_gdrive.py --config config.yaml
```

### 📊 Expected Results

- Subject 0018 extraction: ~10-15GB total
- 6 speech performances with all 60 cameras
- Logs in `/logs/extraction_YYYYMMDD_HHMMSS.log`
- Progress tracked in `MANIFEST.csv`

## Citation

If using this pipeline, please cite:
- Original RenderMe360 dataset paper
- This extraction pipeline repository

---

*Last updated: 2024-09-04*
*Pipeline version: 1.0*
*Compatible with: RenderMe360 August 2024 Google Drive Release*