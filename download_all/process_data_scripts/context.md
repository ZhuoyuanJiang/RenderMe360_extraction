# RenderMe360 Streaming Extraction Context

## Current Situation

### Dataset Evolution
We're dealing with the RenderMe360 dataset which has undergone significant changes between releases:

1. **Early 2024 Release (Subject 0026 - What We Have)**
   - Two separate SMC file types per performance:
     - Annotation files (`anno/0026_[perf]_anno.smc`): metadata, calibration, keypoints, masks
     - Raw files (`raw/0026/0026_[perf]_raw.smc`): high-res images, audio
   - We successfully extracted this data using `extract_0026_FULL.py` and `extract_0026_FULL_both.py`
   - Key discovery: Masks are ONLY in anno files, images are ONLY in raw files
   - Full extraction size: ~590GB per subject

2. **August 2024 Google Drive Release (What We Need to Process)**
   - Single raw SMC file per performance: `[subject_id]_[performance]_raw.smc`
   - 500 subjects total, each with 19 performances
   - Total: ~9,500 SMC files on Google Drive
   - **IMPORTANT UPDATE**: The data format has been optimized - each subject now only requires 10-15GB when extracted (vs 590GB in old format)
   - This dramatic size reduction suggests compressed/optimized data or reduced frame counts

### Storage Constraints
- Available space on `/ssd2`: ~1.1TB (with 100GB buffer = 1TB usable)
- New extraction size per subject: ~10-15GB (manageable!)
- Can now store many subjects simultaneously (60-70 subjects in 1TB)
- Streaming approach still beneficial for managing 500 subjects total

### Our Previous Work
Located in `/ssd2/zhuoyuan/renderme360_temp/test_download/process_data/`:
- `renderme_360_reader.py`: Original SMCReader class
- `extract_0026_FULL.py`: Main extraction script (assumes masks in raw files - incorrect)
- `extract_0026_FULL_both.py`: Brute force version that correctly finds masks in anno files
- Successfully extracted subject 0026 with all 19 performances

### New Resources
- `renderme_360_reader_new.py`: Updated official SMCReader (in download_all/process_data_scripts/)
- Google Drive access via rclone (configured as "vllab13" remote)
- Need to handle quota limits and network failures

## Key Challenges

1. **Scale**: 500 subjects × 10-15GB each = ~5-7.5TB total (still need multiple passes)
2. **Network**: Google Drive quotas and download limits
3. **Unknown Format**: New SMC files might have different internal structure
4. **Camera Selection**: 60 cameras per frame might still be excessive

## Our Goal

Create a streaming pipeline that:
1. Downloads only speech performances (s1_all through s6_all) per subject
2. Extracts data while SMC is on disk
3. Deletes SMC immediately after extraction
4. Processes one complete subject before moving to next
5. Initially extracts all 60 cameras for first subject to enable camera selection
6. Then processes remaining subjects with camera subset

## Technical Approach

### Why Streaming?
- Total dataset still exceeds available storage (5-7.5TB vs 1TB)
- Clean processing: one subject at a time
- Immediate cleanup prevents accumulation of temp files
- Can process in batches of ~60-70 subjects if needed

### Why Rclone?
- Direct download with gdown hits quota limits
- Copying to personal Drive doesn't solve quota issues
- Rclone with proper flags handles retries and acknowledges abuse warnings

### Why Speech Performances Only?
- Research focus on audio-driven avatars
- Speech performances have synchronized audio (48kHz stereo)
- 6 performances per subject is manageable
- Skip expressions (e0-e11) and head movement (h0) to save space/time

---

# Implementation Plan

## Core Objective
Create a script in `/ssd2/zhuoyuan/renderme360_temp/download_all/process_data_scripts/` that:
1. Downloads ONLY speech performances (s1_all through s6_all) from Google Drive
2. Processes all 6 speech SMC files for one subject before moving to next
3. Deletes SMC files immediately after extraction to save space
4. Uses rclone to avoid Google Drive quota limits

## Main Script: `extract_streaming_gdrive.py`

### Workflow per subject:
```python
for subject_id in subjects:
    # Download all 6 speech performances for this subject
    for perf in ['s1_all', 's2_all', 's3_all', 's4_all', 's5_all', 's6_all']:
        # Download using rclone
        download_smc_with_rclone(gdrive_folder_id, subject_id, perf, temp_dir)
    
    # Process all 6 speech files for this subject
    for perf in ['s1_all', 's2_all', 's3_all', 's4_all', 's5_all', 's6_all']:
        smc_file = f"{temp_dir}/{subject_id}_{perf}_raw.smc"
        extract_performance(smc_file, subject_id, perf, output_dir)
        os.remove(smc_file)  # Delete immediately after extraction
        update_manifest(subject_id, perf, "completed")
    
    # All 6 performances done for this subject, move to next
```

## Rclone Integration

Download function using rclone:
```python
def download_smc_with_rclone(gdrive_folder_id, subject_id, performance, temp_dir):
    """
    Download specific SMC file from Google Drive subfolder
    Structure: GDrive/[subject_id]/[subject_id]_[performance]_raw.smc
    """
    cmd = f"""
    rclone copy "vllab13:{subject_id}/{subject_id}_{performance}_raw.smc" {temp_dir}/ \
        --drive-root-folder-id {gdrive_folder_id} \
        -P --drive-acknowledge-abuse \
        --transfers 4 --checkers 8 \
        --retries 10 --low-level-retries 20
    """
```

## Configuration File: `config.yaml`
```yaml
google_drive:
  root_folder_id: "YOUR_SHARED_FOLDER_ID"  # Main folder with 500 subject folders
  remote_name: "vllab13"  # Your rclone remote config name
  
extraction:
  subjects: ["0018", "0019", "0026", ...]  # Which subjects to process
  performances: ["s1_all", "s2_all", "s3_all", "s4_all", "s5_all", "s6_all"]
  cameras: "all"  # Start with all 60, later specify subset like [0, 6, 12, 18, 24, 30, 36, 42, 48, 54]
  modalities: ["images", "masks", "audio", "calibration", "keypoints2d", "keypoints3d"]
  
storage:
  temp_dir: "/ssd2/zhuoyuan/renderme360_temp/temp_smc/"
  output_dir: "/ssd2/zhuoyuan/renderme360_temp/download_all/subjects/"
  max_temp_size_gb: 50  # Safety limit for temp directory
```

## Extraction Logic

Based on `extract_0026_FULL_both.py` but adapted for single SMC file:
- No anno/raw separation needed
- Use new SMCReader from `renderme_360_reader_new.py`
- Check for all data types in single file
- Create unified output structure

## Output Structure
```
/ssd2/zhuoyuan/renderme360_temp/download_all/
  subjects/
    0018/
      s1_all/
        calibration/
        images/
          cam_00/
            frame_000000.jpg
            ...
          ...
          cam_59/
        masks/
        audio/
        keypoints2d/
        keypoints3d/
        metadata/
      s2_all/
        ...
      s6_all/
    0019/
      ...
  MANIFEST.csv
  config.yaml
  logs/
```

## Testing Strategy

### Phase 1: Single Subject with All Cameras
1. Download subject 0018's 6 speech performances
2. Extract with ALL 60 cameras
3. Create visualization grid to inspect camera coverage
4. Determine optimal camera subset for 360° coverage

### Phase 2: Production Run
1. Update config with selected camera subset
2. Process remaining 499 subjects
3. Monitor progress via MANIFEST.csv
4. Handle failures with resume capability

## Key Differences from Old System
1. **Google Drive structure**: 500 folders → 19 files each
2. **Single SMC file** per performance (not anno + raw pair)
3. **Selective download**: Only s1_all through s6_all (skip expressions/head)
4. **Batch processing**: All 6 files per subject before moving on
5. **Rclone usage**: Avoid Google Drive quota limits
6. **Optimized size**: 10-15GB per subject (vs 590GB old format)

## Success Metrics
- Successfully download and process one complete subject
- Verify 10-15GB extraction size per subject
- Achieve reasonable extraction time (~30-60 minutes per subject)
- Maintain storage usage under 1TB during processing
- Create reproducible pipeline with clear documentation
- Enable camera selection based on visual inspection

## First Deliverable
Working script that downloads and processes subject 0018's 6 speech performances with all 60 cameras for visualization and camera selection.