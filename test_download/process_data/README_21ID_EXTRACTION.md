# RenderMe360 21ID Dataset Extraction Pipeline

## Overview

This extraction pipeline is specifically designed for the RenderMe360 21ID dataset version, which has a different Google Drive structure than the 500ID version. The pipeline combines:

- **Complete extraction logic** from `extract_0026_FULL_both.py` (ensures nothing is missed)
- **Google Drive streaming** from `extract_streaming_gdrive.py` (download → extract → cleanup)
- **Dual SMC bundle support** for the 21ID structure (separate anno/raw folders)
- **Selective extraction** via configuration file

## Key Features

1. **Streaming Extraction**: Downloads from Google Drive, extracts data, and cleans up temporary files to save space
2. **Dual Source Support**: Handles both annotation (anno) and raw data bundles
3. **Complete Extraction**: Extracts ALL data types to ensure nothing is missed
4. **Selective Control**: Configure which subjects, performances, cameras, and modalities to extract
5. **Progress Tracking**: Maintains a manifest CSV file to track extraction status
6. **Robust Error Handling**: Automatic retries and detailed logging

## Prerequisites

### 1. Install Dependencies
```bash
pip install numpy opencv-python pandas pyyaml tqdm
# Optional for 3D mesh extraction:
pip install plyfile
```

### 2. Configure rclone
```bash
# Install rclone if not already installed
curl https://rclone.org/install.sh | sudo bash

# Configure Google Drive remote named "vllab13"
rclone config
# Follow prompts to set up Google Drive remote
```

### 3. Get Google Drive Folder ID
- Open your 21ID dataset Google Drive link
- Extract the folder ID from the URL: `https://drive.google.com/drive/folders/[FOLDER_ID]`
- This ID will be used in the configuration

## Quick Start

### 1. Test the Setup
```bash
python test_extraction_21id.py
```
This will verify:
- Configuration file is properly set up
- All dependencies are installed
- rclone is configured correctly
- Extraction script can run

### 2. Configure the Pipeline
Edit `config_21id.yaml`:
```yaml
google_drive:
  root_folder_id: "YOUR_ACTUAL_FOLDER_ID"  # Replace with your folder ID
  
extraction:
  subjects: ["0026"]  # Start with one subject
  performances: ["s1_all"]  # Start with one performance
  cameras: "all"  # Or specify list: [0, 12, 24, 36, 48]
```

### 3. Run Extraction

#### Test with Single Performance:
```bash
python extract_subject_FULL_both.py --subject 0026 --performance s1_all
```

#### Run Full Extraction:
```bash
python extract_subject_FULL_both.py --config config_21id.yaml
```

#### Dry Run (Test Without Downloading):
```bash
python extract_subject_FULL_both.py --dry-run
```

## Google Drive Structure

The 21ID dataset has a different structure than the 500ID version:

```
RenderMe-360_release/
├── anno/                    # Annotation data
│   ├── 0026/               # Subject folder
│   │   ├── 0026_e0_anno.smc/       # Expression 0 annotations
│   │   ├── 0026_s1_all_anno.smc/   # Speech 1 annotations
│   │   └── ...
│   └── [other subjects]/
└── raw/                     # Raw capture data
    ├── 0026/               # Subject folder
    │   ├── 0026_e0_raw.smc/        # Expression 0 raw data
    │   ├── 0026_s1_all_raw.smc/    # Speech 1 raw data
    │   └── ...
    └── [other subjects]/
```

## Output Structure

Extracted data is organized as follows:

```
subjects/
└── 0026/                           # Subject ID
    └── s1_all/                      # Performance
        ├── from_anno/               # Data from annotation bundle
        │   ├── metadata/            # Actor info, camera info
        │   ├── calibration/         # Camera calibration matrices
        │   ├── masks/               # Segmentation masks
        │   │   ├── cam_00/         # Per-camera masks
        │   │   └── ...
        │   ├── keypoints2d/         # 2D facial landmarks
        │   ├── keypoints3d/         # 3D facial landmarks
        │   ├── flame/               # FLAME parameters (expressions only)
        │   ├── uv_textures/         # UV textures (expressions only)
        │   ├── scan/                # 3D scan mesh (expressions only)
        │   └── scan_masks/          # Scan masks (expressions only)
        ├── from_raw/                # Data from raw bundle
        │   ├── images/              # High-resolution RGB images
        │   │   ├── cam_00/         # Per-camera images
        │   │   └── ...
        │   └── audio/               # Audio track (speech only)
        └── .extraction_complete     # Completion marker
```

## Configuration Options

### Selective Extraction

#### Extract Specific Cameras:
```yaml
extraction:
  cameras: [0, 12, 24, 36, 48]  # 5 cameras evenly distributed
```

#### Extract Only Essential Modalities:
```yaml
extraction:
  modalities:
    - "metadata"
    - "calibration"
    - "images"
    - "audio"
```

#### Process Multiple Subjects:
```yaml
extraction:
  subjects: ["0026", "0041", "0042"]
```

### Performance Optimization

#### Adjust Cleanup Settings:
```yaml
processing:
  delete_smc_after_extraction: true  # Delete temp files immediately
```

#### Set Storage Limits:
```yaml
limits:
  max_temp_size_gb: 200  # Maximum temp directory size
  min_free_space_gb: 100  # Stop if disk space is low
```

## Data Modalities

| Modality | Description | Source | Performances |
|----------|-------------|--------|--------------|
| metadata | Actor info, camera info | anno | All |
| calibration | Camera calibration matrices | anno | All |
| images | RGB images from cameras | raw | All |
| masks | Segmentation masks | anno | All |
| audio | Audio track | raw | Speech only |
| keypoints2d | 2D facial landmarks | anno | All |
| keypoints3d | 3D facial landmarks | anno | All |
| flame | FLAME face parameters | anno | Expressions only |
| uv_textures | UV texture maps | anno | Expressions only |
| scan | 3D scan mesh | anno | Expressions only |
| scan_masks | Scan visibility masks | anno | Expressions only |

## Progress Tracking

The pipeline creates `MANIFEST_21ID.csv` to track extraction progress:

| Column | Description |
|--------|-------------|
| subject | Subject ID |
| performance | Performance name |
| status | completed/failed/download_failed |
| cameras_extracted | Number of cameras extracted |
| frames | Number of frames |
| size_gb | Total extraction size |
| anno_size_gb | Size of anno data |
| raw_size_gb | Size of raw data |
| timestamp | Extraction timestamp |
| error | Error message if failed |

## Monitoring Extraction Progress

### Real-time Download Monitoring
```bash
# Watch download progress (file size growing)
watch -n 2 'ls -lah /ssd4/zhuoyuan/renderme360_temp/temp_smc/*.smc 2>/dev/null | awk "{print \$5, \$9}"'
```

This command shows:
- Current file size (updates every 2 seconds)
- File name being downloaded
- Press `Ctrl+C` to exit

Expected file sizes:
- **s1_all**: ~14GB (anno) + ~59GB (raw) = 73GB total
- **s2_all to s6_all**: Similar to s1_all
- **e0 to e11**: ~700MB (anno) + ~2.5GB (raw) = 3.2GB each
- **h0**: ~500MB (anno) + ~2.7GB (raw) = 3.2GB total

### Check Extraction Log
```bash
# Follow the latest log file
tail -f /ssd4/zhuoyuan/renderme360_temp/test_download/logs/extraction_*.log
```

## Troubleshooting

### Google Drive Authentication Issues
```bash
# Re-authenticate rclone
rclone config reconnect vllab13:

# Test connection
rclone lsd vllab13: --drive-root-folder-id YOUR_FOLDER_ID
```

### Out of Disk Space
- Check `config_21id.yaml` and ensure `delete_smc_after_extraction: true`
- Reduce number of cameras or modalities to extract
- Increase `min_free_space_gb` limit

### Download Failures
- Increase retry settings in config:
```yaml
processing:
  max_retries: 5
  retry_delay: 60
```

### Missing Dependencies
```bash
# Install all required packages
pip install numpy opencv-python pandas pyyaml tqdm plyfile
```

## Storage Requirements

Approximate sizes per subject (all performances):
- Full extraction (all cameras, all modalities): 200-500 GB
- Images only (all cameras): 150-400 GB
- Audio + keypoints only: 1-5 GB
- Single performance: 10-50 GB

## Example Commands

### Extract everything for one subject:
```bash
python extract_subject_FULL_both.py --subject 0026
```

### Extract only speech performance 1:
```bash
python extract_subject_FULL_both.py --subject 0026 --performance s1_all
```

### Extract with custom config:
```bash
python extract_subject_FULL_both.py --config my_config.yaml
```

### Test configuration without downloading:
```bash
python extract_subject_FULL_both.py --dry-run
```

## Comparison with Previous Scripts

| Feature | extract_0026_FULL_both.py | extract_streaming_gdrive.py | extract_subject_FULL_both.py (NEW) |
|---------|---------------------------|------------------------------|-------------------------------------|
| Google Drive streaming | ❌ | ✅ | ✅ |
| Handles any subject ID | ❌ (hardcoded 0026) | ✅ | ✅ |
| Dual SMC support (anno+raw) | ✅ | ❌ | ✅ |
| Complete extraction | ✅ | ❌ | ✅ |
| Selective extraction | ❌ | ✅ | ✅ |
| Cleanup after extraction | ❌ | ✅ | ✅ |
| 21ID structure support | ❌ | ❌ | ✅ |

## Next Steps

1. **Test with single performance**: Verify the pipeline works with your Google Drive setup
2. **Analyze extracted data**: Check which cameras actually have data for optimization
3. **Configure selective extraction**: Based on analysis, update config to extract only needed data
4. **Scale up**: Process all 21 subjects with optimized settings
5. **Create visualization**: Use extracted data for your research

## Support

If you encounter issues:
1. Check the log files in `/ssd4/zhuoyuan/renderme360_temp/test_download/logs/`
2. Review the MANIFEST_21ID.csv for extraction status
3. Run `test_extraction_21id.py` to verify setup
4. Ensure Google Drive folder ID is correctly configured