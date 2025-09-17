# RenderMe360 Extraction Architecture

## Overview

This document explains the complete extraction architecture we built on top of the `renderme_360_reader.py` library to systematically extract and organize the RenderMe360 dataset.

## Core Architecture: From Methods to Folders

### Complete Method-to-Folder Mapping

We analyzed ALL methods in the `SMCReader` class and created a logical folder structure based on data types:

| Directory | SMCReader Methods | Data Type | Rationale |
|-----------|------------------|-----------|-----------|
| `images/` | `get_img(cam_id, 'color', frame)` | RGB images (2048×2448×3) | Organized by camera/frame for multi-view consistency |
| `masks/` | `get_img(cam_id, 'mask', frame)` | Segmentation masks (2048×2448) | Separate from RGB for different processing pipelines |
| `audio/` | `get_audio()` → `writemp3()` | Speech audio (MP3 + numpy) | Temporal data, only in speech performances |
| `keypoints2d/` | `get_Keypoints2d(cam_id, frame)` | 2D facial landmarks (106×2) | Per-camera view, only cams 18-32 have these |
| `keypoints3d/` | `get_Keypoints3d(frame)` | 3D facial landmarks (106×3) | World-space coordinates, one per frame |
| `flame/` | `get_FLAME(frame)` | FLAME face model params | Complex dict with pose/shape/expression |
| `uv_texture/` | `get_uv(frame)` | UV face textures (1024×1024) | Texture maps for 3D rendering |
| `scan_mesh/` | `get_scanmesh()` → `write_ply()` | High-res 3D scan | Single reference mesh per performance |
| `scan_mask/` | `get_scanmask(cam_id)` | Scan visibility masks | Per-camera scan segmentation |
| `calibration/` | `get_Calibration(cam_id)`<br>`get_Calibration_all()` | Camera matrices (K, D, RT) | Essential for 3D reconstruction |
| `metadata/` | `get_actor_info()`<br>`get_Camera_info()`<br>`actor_id` (property)<br>`performance_part` (property)<br>`capture_date` (property) | Dataset metadata | Centralized info about the capture |
| `visualization/` | (our addition) | Generated overview images | Quick visual validation of extraction |

### Methods NOT Mapped to Folders

You may realize that while we say we create directory folders by mapping functions to each folders, not all functions are designated a folder: These are internal/helper methods that don't produce saveable data directly:

#### 1. Constructor and Initialization
- `__init__(smc_path)` - Initializes the reader with an SMC file

#### 2. Internal Data Processing (Private Methods)
- `_read_from_bytes(data, dtype, shape)` - Generic byte array reader
- `_read_color_from_bytes(data)` - Specialized JPEG decompression for images
- `_decompress_color(data)` - JPEG decompression utility
- `_get_index(cam_id, data_type, frame_id)` - Calculates byte offsets in SMC file

#### 3. Output Utilities (Save Helpers)
- `writemp3(path, sample_rate, audio_array)` - Saves extracted audio to MP3 file
- `write_ply(mesh_dict, path)` - Saves extracted mesh to PLY file

These helpers are used AFTER extraction:
```python
# Two-step process: Extract → Save
audio_data = reader.get_audio()          # Step 1: Extract from SMC
reader.writemp3(path, sr, audio_data)    # Step 2: Save to disk
```

## Why We Created Multiple Extraction Scripts

虽然我们有了这个`renderme_360_reader.py`， 但它只给了几个method来帮我们提取*单个ID*我们想要的data，比如说Image,比如说mp3,具体想要怎么提取和提取多少还是得我们自己写script.比如说想提取所有人的data，然后要把data怎么存（如果不写的话全部mp3, image, 3d Mesh全部都会混在一个文件夹里，就会乱七八糟），我们还是得自己写script. 

### The Problem
The `renderme_360_reader.py` provides low-level access to data but:
- No organized extraction workflow
- No folder structure
- No batch processing
- No progress tracking
- No storage estimates
- Methods must be called individually for each frame/camera

### Our Solution: Layered Extraction Scripts

```
renderme_360_reader.py (Base Library)
           ↓
    Our Extraction Layer
    ├── extract_0026_FULL.py         # Full extraction with separation
    ├── extract_0026_FULL_both.py    # Brute force extraction (checks both files)
    ├── extract_all_0026.sh          # Batch script for all 19 performances
    ├── extract_for_avatar_research.py # Research-optimized
    └── quick_explore_0026.py        # Non-destructive exploration
```

## Understanding Performances

### What is a "Performance"?

A performance is one recording session of a specific type. Subject 0026 has **19 different performances**:

- **e0-e11** (12 performances): Different facial expressions
- **s1_all-s6_all** (6 performances): Different speech recordings with audio
- **h0** (1 performance): Head movement recording

Each performance is stored as separate .smc files in both `/anno` and `/raw`.

## Understanding Masks vs Scan Masks

One of the most confusing aspects of the RenderMe360 dataset is the difference between regular **masks** and **scan masks**. Here's a detailed explanation:

### Regular Masks (`get_img(cam_id, 'mask', frame)`)
- **Type:** Dynamic segmentation masks that change over time
- **Quantity:** One mask per frame per camera
- **Example:** For e0: 110 frames × 60 cameras = 6,600 mask files
- **Purpose:** Frame-by-frame subject segmentation throughout the entire performance
- **Usage:** Track the subject's silhouette as they move/express over time
- **File Structure:** `masks/cam_XX/frame_XXXXXX.png`
- **Resolution:** 2048×2448 (matching the RGB images)
- **Data Nature:** Binary masks showing which pixels belong to the subject in each frame

### Scan Masks (`get_scanmask(cam_id)`)
- **Type:** Static reference masks for the 3D scan
- **Quantity:** ONE mask per camera (60 total, regardless of frames)
- **Example:** For e0: 60 scan mask files (one per camera)
- **Purpose:** Shows visibility/segmentation of the 3D scan mesh from each camera's viewpoint
- **Usage:** For projecting/rendering the 3D scan back to 2D camera views
- **File Structure:** `scan_masks/cam_XX.png` (no frame number!)
- **Resolution:** 2048×2448
- **Data Nature:** Shows which pixels of the 3D scan are visible from each camera angle

### The Relationship Visualized
```
3D Scan Mesh (1 file: mesh.ply with ~133k vertices)
     ↓
Projected to 60 camera views
     ↓  
60 Scan Masks (one per camera showing scan visibility)

Meanwhile, separately:
Performance video (110 frames × 60 cameras)
     ↓
6,600 Regular Masks (tracking subject through entire performance)
```

### Why Only One 3D Scan Instead of Per-Frame Scans?

This is a critical design decision in RenderMe360, driven by practical and computational constraints:

#### 1. **Capture Technology Limitations**
- High-resolution 3D scanning (132,998 vertices) requires specialized equipment and significant capture time
- The scan likely uses photogrammetry or structured light scanning which needs the subject to stay perfectly still
- Capturing 110 high-res 3D scans would require the subject to freeze at each frame - impossible for natural motion

#### 2. **Storage and Computational Costs**
- One scan mesh: 17 MB
- If per-frame for e0: 17 MB × 110 frames = 1.87 GB just for meshes
- If per-frame for s1_all: 17 MB × 2,529 frames = 43 GB of mesh data alone!
- Processing time would increase 100x-2500x

#### 3. **Different Data Types for Different Purposes**
- **3D Scan:** High-quality reference geometry for detailed face/body modeling (static)
- **FLAME Parameters:** Lightweight per-frame 3D representation (only for expression performances)
- **2D Masks + Multi-view:** Can reconstruct rough 3D using visual hull/MVS if needed

#### 4. **The RenderMe360 Hybrid Approach**
```
Static High-Quality Geometry: 1 detailed 3D scan (reference)
               +
Dynamic Low-Dimensional Data: FLAME parameters per frame (expressions only)
               +  
Multi-View Coverage: 60 cameras × all frames (for reconstruction if needed)
```

#### 5. **What You Get Instead of Per-Frame Scans**
- **For expression performances (e0-e11):** FLAME parameters provide per-frame 3D face shape/expression
- **For all performances:** 60 synchronized camera views allow multi-view stereo reconstruction
- **Single high-res scan:** Provides detailed reference geometry that FLAME can't capture

### Key Insight
- **Regular masks** = temporal data (changes every frame as subject moves)
- **Scan masks** = spatial data (static projection of single 3D scan to each camera)
- The scan is captured at ONE reference moment, while regular masks track the entire performance sequence

This hybrid approach balances quality, storage, and practical capture constraints. If you need per-frame 3D, you would either use the FLAME parameters (for faces) or apply multi-view reconstruction algorithms to the 60 camera views.

## Script Comparison

| Script | What it Processes | From Which Files | Amount Extracted | Output Size |
|--------|------------------|------------------|------------------|-------------|
| `quick_explore_0026.py` | All performances | Anno (metadata only) | Nothing | 0 MB |
| `extract_0026_FULL.py` | 1 performance at a time | **BOTH anno + raw** | 60 cameras, all frames | 10-50 GB |
| `extract_for_avatar_research.py` | Multiple performances | Both anno + raw | Strategic sampling | ~50-100 GB |

## File Overview

### 1. `extract_0026_FULL.py` (Primary Script - Full Extraction with Separation)

**What it processes when you run `python extract_0026_FULL.py --performance e0`:**

1. `/anno/0026_e0_anno.smc` → Extracts to `from_anno/`:
   - Segmentation masks (THIS IS WHERE ALL MASKS ARE!)
   - FLAME parameters
   - 2D/3D keypoints
   - UV textures
   - Scan mesh
   - Calibration matrices

2. `/raw/0026/0026_e0_raw.smc` → Extracts to `from_raw/`:
   - High-resolution images (2048×2448)
   - Audio (if speech performance)
   
**Note:** extract_0026_FULL.py incorrectly looks for masks in raw files and will miss them!

**Usage:**
```bash
# Default: Separates anno and raw into different folders
python extract_0026_FULL.py --performance e0

# Explicitly specify separation
python extract_0026_FULL.py --performance e0 --separate

# Old behavior: Everything in one folder
python extract_0026_FULL.py --performance e0 --combine

# Custom output location
python extract_0026_FULL.py --performance e0 --output /your/path

# Extract all 19 performances using batch script (recommended)
./extract_all_0026.sh
```

### 1b. `extract_0026_FULL_both.py` (Alternative - Brute Force Extraction)

**Purpose:** Exhaustive extraction that checks BOTH anno and raw files for ALL data types

**Differences from `extract_0026_FULL.py`:**
- Checks both anno and raw files for every data type (not just their expected locations) - For example, `extract_0026_FULL.py` assumes audio is from /raw folder and ignores /anno folder when it finds audios in raw folder. P.S. audio is indeed in raw folder so extract_0026_FULL.py is good in our case. 
- Extracts data from BOTH sources when available (e.g., images might exist in both raw and anno files. While `extract_0026_FULL.py` only looks at expected file type, `extract_0026_FULL_both.py` checks ALL file types - raw and anno)
- May result in duplicate data in different folders (from_anno/ and from_raw/)
- Guarantees nothing is missed but uses more storage and time (KEY MOTIVATION of why we wrote this file!!)

**Important Discovery from Testing:**
We tested `extract_0026_FULL_both.py` on e0 and s1_all performances and discovered it extracts **mask data from annotation files** that `extract_0026_FULL.py` completely misses:
- **e0 performance:** Found 6,600 mask files in from_anno/masks/ (0.41 GB)
- **s1_all performance:** Found 151,740 mask files in from_anno/masks/ (14.93 GB)
- These are the ONLY masks in the dataset - raw files do NOT contain mask data
- The regular extraction script incorrectly assumes masks would be in raw files and misses them entirely
- **Note:** The script may create an empty `from_raw/masks/` folder structure when checking for masks in raw files, but this folder will remain empty since raw files don't contain masks

**When to use:**
- When you suspect data might be missing from expected locations
- For verification that the primary script extracted everything
- When the dataset structure is unknown or has changed
- If you want absolute certainty that all data is extracted
- **If you need the additional masks from annotation files**

**Note:** We developed this after discovering audio was in raw files instead of anno files. While the primary script has been fixed, this brute force version remains available for those who want complete assurance.

**Additional Notes (09/03/2025):** After testing `extract_0026_FULL_both.py` on e0 and s1_all performances, we discovered it successfully extracts additional mask data from annotation files that the regular script misses. This validates the purpose of having this brute-force alternative for comprehensive data extraction. 

**Expected Output Structure:**
```
/output_directory/0026_[performance]/
├── from_anno/              # Data from annotation file
│   ├── calibration/        # Camera calibration matrices
│   ├── metadata/           # Actor and camera info
│   ├── masks/              # Segmentation masks (ALL masks are here)
│   │   ├── cam_00/         # frame_000000.png to frame_XXXXXX.png
│   │   └── cam_59/
│   ├── keypoints2d/        # 2D facial landmarks (cameras 18-32)
│   ├── keypoints3d/        # 3D facial landmarks
│   ├── flame/              # FLAME parameters (expressions only)
│   ├── uv_textures/        # UV texture maps (expressions only)
│   ├── scan/               # 3D mesh scan (expressions only)
│   └── scan_masks/         # Scan visibility masks (expressions only)
└── from_raw/               # Data from raw file
    ├── images/             # High-res RGB images (ALL images are here)
    │   ├── cam_00/         # frame_000000.jpg to frame_XXXXXX.jpg
    │   └── cam_59/
    └── audio/              # Audio tracks (speech performances only)
```

**Note:** The modified script only creates folders when actual data exists, so you won't see empty directories.

**Important:** This script has NOT been tested on the full dataset. We only used and tested `extract_0026_FULL.py` (via `extract_all_0026.sh`) for our extraction. The brute force version is provided as-is for users who want to verify nothing was missed, but they will need to test it themselves.

### 2. `extract_all_0026.sh` (Batch Extraction Script)

**Purpose:** Automated batch extraction of all 19 performances for subject 0026 using `extract_0026_FULL.py`

**Features:**
- Uses `extract_0026_FULL.py` internally to process each performance
- Automatically activates the RenderMe360_Data_Processing conda environment
- Extracts all performances in sequence: e0-e11, s1_all-s6_all, h0
- Shows progress tracking (X/19 performances completed)
- Built-in resume capability - skips already extracted performances
- Calculates and displays total extracted size at completion
- Handles user confirmation automatically

**Usage:**
```bash
# Make executable (first time only)
chmod +x extract_all_0026.sh

# Run the batch extraction
./extract_all_0026.sh
```

This is the recommended way to extract the complete dataset as it handles all the details automatically.

### 3. `extract_for_avatar_research.py`

**What it processes:**
- Multiple performances optimized for avatar research
- Speech performances: Extracts audio + strategic camera views
- Expression performances: Extracts FLAME parameters
- Uses both anno and raw files strategically

### 3. `quick_explore_0026.py`

**What it processes:**
- Reads metadata from all .smc files
- Shows what data is available
- Does NOT extract anything to disk

## Directory Structure Rationale

### Why This Organization?

Our folder structure follows these principles:

1. **Data Type Separation**: Each data type gets its own folder for modular processing
2. **Camera-Frame Hierarchy**: Images/masks organized as `camera/frame` for multi-view consistency
3. **Temporal Grouping**: Frame-based data uses consistent naming (`frame_000000.jpg`)
4. **Metadata Centralization**: All descriptive info in one place
5. **Processing Pipeline Ready**: Structure supports common CV/ML workflows

### Detailed Folder Rationale

```
extracted_data/
└── [performance_name]/
    ├── metadata/          # WHY: Central info hub, loaded once
    │   ├── info.json     # Machine-readable for pipelines
    │   └── info.txt      # Human-readable for quick checks
    │
    ├── calibration/       # WHY: Shared across all frames
    │   ├── all_cameras.npy    # Efficient: load all at once
    │   └── cam_XX.npy         # Flexible: load specific camera
    │
    ├── images/            # WHY: Largest data, needs structure
    │   └── cam_XX/        # Organized by camera for multi-view
    │       └── frame_XXXXXX.jpg  # Sequential for video processing
    │
    ├── masks/             # WHY: Same structure as images for pairing
    │   └── cam_XX/        # Easy to match: image[i] ↔ mask[i]
    │
    ├── audio/             # WHY: Temporal data, different processing
    │   ├── audio.mp3      # Compressed for playback
    │   └── audio_data.npz # Raw array for processing
    │
    ├── keypoints2d/       # WHY: Camera-specific landmarks
    │   └── cam_XX.npz     # Each camera has different 2D projection
    │
    ├── keypoints3d/       # WHY: World coordinates, frame-independent
    │   └── all_frames.npz # Single file, all frames together
    │
    ├── flame/             # WHY: Animation parameters
    │   └── all_frames.npz # Compressed storage for sequences
    │
    ├── uv_texture/        # WHY: Appearance data for rendering
    │   └── frame_XXXXXX.jpg  # Per-frame texture variations
    │
    ├── scan_mesh/         # WHY: Reference geometry
    │   └── mesh.ply       # Single high-quality scan
    │
    └── scan_mask/         # WHY: Scan visibility per camera
        └── cam_XX.png     # Which parts visible from each view
```

## Recommended Workflow

### Step 1: Explore First (2 minutes)
```bash
python quick_explore_0026.py
```

### Step 2: Full Extraction with Separation (1-2 hours, 10-50GB)
```bash
# Expression performance (smaller, ~10-15GB)
python extract_0026_FULL.py --performance e0

# Speech performance (larger, ~30-50GB)
python extract_0026_FULL.py --performance s1_all

# Extract all 19 performances using the batch script (300-500GB)
./extract_all_0026.sh

# Alternative: Manual loop for all performances
for p in e{0..11} s{1..6}_all h0; do
    python extract_0026_FULL.py --performance $p
done
```

### Step 3: Research-Specific Extraction
```bash
python extract_for_avatar_research.py
```

## Data Types by Performance

| Performance | Has Audio | Has FLAME | Has UV | Size (Full) |
|------------|-----------|-----------|---------|-------------|
| e0-e11 | ❌ | ✅ | ✅ | ~10-15 GB |
| s1-s4 | ✅ | ❌ | ❌ | ~30-50 GB |
| h0 | ❌ | ❌ | ❌ | ~5-10 GB |

## Storage Estimates

### Full Single Performance
- Expression (e0): ~10-15 GB
- Speech (s1_all): ~30-50 GB  
- Head (h0): ~5-10 GB

### Full Subject (All Performances)
- 12 expressions + 4 speech + 1 head = **~300-500 GB**

## For Our Research

Based on audio-driven 3D avatar project, you might need:

1. **Speech performances (s1-s4)** - Has synchronized audio
2. **Expression performances (e0-e11)** - Has FLAME parameters
3. **Selected cameras** - Not all 60, maybe 10-15 for 360° coverage
4. **Sampled frames** - Not all frames, maybe every 10th or 30th

**Recommended extraction:**
```bash
# Extract one speech performance fully to understand the data
python extract_0026_FULL.py --performance s1_all --output /ssd2/zhuoyuan/avatar_research_data

# Then use the research-optimized script for remaining data
python extract_for_avatar_research.py
```

## Output Directory Structure

### NEW: Separated Structure (Default)

Output location: `/ssd2/zhuoyuan/renderme360_temp/FULL_EXTRACTION/`

```
FULL_EXTRACTION/
└── 0026_[performance]/
    ├── extraction_info.txt    # Explains separation
    ├── size_summary.txt       # Size breakdown
    │
    ├── from_anno/             # Data from annotation file
    │   ├── metadata/          # Actor/camera info
    │   ├── calibration/       # Camera matrices
    │   ├── masks/             # Segmentation masks (ALL masks are HERE!)
    │   │   ├── cam_00/
    │   │   │   └── frame_000000.png
    │   │   └── cam_59/
    │   ├── keypoints2d/       # 2D landmarks (cam 18-32)
    │   ├── keypoints3d/       # 3D landmarks
    │   ├── flame/             # FLAME params (e* only)
    │   ├── uv_textures/       # UV maps (e* only)
    │   ├── scan/              # 3D mesh (e* only)
    │   └── scan_masks/        # Scan masks (e* only)
    │
    └── from_raw/              # Data from raw file
        ├── images/            # High-res images (2048×2448)
        │   ├── cam_00/
        │   │   └── frame_000000.jpg
        │   └── cam_59/
        └── audio/             # Audio (s* only)
```

### Combined Structure (Legacy, use --combine flag)

```
FULL_EXTRACTION/
└── 0026_[performance]/
    ├── metadata/
    ├── calibration/
    ├── images/
    ├── masks/
    ├── audio/
    ├── keypoints2d/
    ├── keypoints3d/
    ├── flame/
    ├── uv_textures/
    ├── scan/
    └── scan_masks/
```

## Tips

1. **Start small:** Use sample mode first
2. **Check storage:** Ensure you have enough space before full extraction
3. **Use progress bars:** Full extraction shows progress
4. **Parallel extraction:** Can run multiple performances in parallel if you have CPU/storage
5. **Clean up:** Delete samples after full extraction to save space

## Complete Method Accounting

### All SMCReader Methods Categorized

To ensure completeness, here's every single method/property in `renderme_360_reader.py`:

#### Data Extraction Methods (15 methods → 11 folders)
1. `get_img(cam_id, 'color', frame)` → `images/`
2. `get_img(cam_id, 'mask', frame)` → `masks/`
3. `get_audio()` → `audio/`
4. `get_Keypoints2d(cam_id, frame)` → `keypoints2d/`
5. `get_Keypoints3d(frame)` → `keypoints3d/`
6. `get_FLAME(frame)` → `flame/`
7. `get_uv(frame)` → `uv_texture/`
8. `get_scanmesh()` → `scan_mesh/`
9. `get_scanmask(cam_id)` → `scan_mask/`
10. `get_Calibration(cam_id)` → `calibration/`
11. `get_Calibration_all()` → `calibration/`
12. `get_actor_info()` → `metadata/`
13. `get_Camera_info()` → `metadata/`
14. `actor_id` (property) → `metadata/`
15. `performance_part` (property) → `metadata/`
16. `capture_date` (property) → `metadata/`

#### Internal Processing Methods (5 methods - no folders)
1. `__init__(smc_path)` - Constructor
2. `_read_from_bytes(data, dtype, shape)` - Byte array processing
3. `_read_color_from_bytes(data)` - JPEG decompression
4. `_decompress_color(data)` - Image decompression
5. `_get_index(cam_id, data_type, frame_id)` - File offset calculation

#### Output Utility Methods (2 methods - helpers)
1. `writemp3(path, sample_rate, audio)` - Saves audio after extraction
2. `write_ply(mesh_dict, path)` - Saves mesh after extraction

**Total: 23 methods/properties fully accounted for**

## Architecture Summary

```
RenderMe360 Dataset (.smc files)
         ↓
renderme_360_reader.py (23 methods)
         ↓
Our Extraction Architecture
├── Folder Structure (11 directories)
├── Batch Processing (multiple frames/cameras)
├── Progress Tracking (tqdm integration)
├── Storage Management (size estimation)
├── Metadata Generation (JSON/text outputs)
└── Visualization (matplotlib previews)
         ↓
Research-Ready Organized Data
```

## Key Innovations We Added

1. **Systematic Organization**: Transformed unstructured method calls into organized folder hierarchy
2. **Batch Processing**: Extract multiple frames/cameras efficiently instead of one-by-one
3. **Mode Selection**: Sample vs Full extraction modes for different use cases
4. **Progress Tracking**: Visual feedback for long-running extractions
5. **Storage Awareness**: Size estimation and warnings before extraction
6. **Research Optimization**: Specialized scripts for specific research needs
7. **Safety Measures**: Confirmation prompts for large extractions
8. **Comprehensive Documentation**: This README ensures reproducibility

## Conclusion

This extraction architecture bridges the gap between the low-level `renderme_360_reader.py` library and practical research needs. Every method in the original reader is either:
- Mapped to a specific folder for data organization
- Identified as an internal helper not needing storage
- Used as a utility for saving extracted data

The multi-script approach provides flexibility:
- **Exploration** without commitment (`quick_explore_0026.py`)
- **Full extraction** 
  - with separation (`extract_0026_FULL.py`) 
  - without separation(combined) : (`extract_0026_FULL.py`) 
  - Brute Force (not miss any file): (`extract_0026_FULL_both.py`) 
- **Research-specific** optimization (`extract_for_avatar_research.py`)

This ensures you can work with the 500GB dataset efficiently, extracting only what you need, when you need it.

## Additional Notes

### Understanding Masks in Annotation Files (09/03/2025)

During our testing of `extract_0026_FULL_both.py`, we discovered that annotation files contain mask data without corresponding RGB images. This initially seemed confusing - why have masks without images? Here's what we found:

**The Reality of Data Storage:**
- **Masks ONLY exist in annotation files**, NOT in raw files
- **Images ONLY exist in raw files**, NOT in annotation files
- Anno masks: ~72KB per file (grayscale PNG, 2448×2048 resolution)
- Raw images: ~609KB per file (RGB JPEG, 2448×2048 resolution) 
- Despite both having the same resolution, masks are stored separately from images

**Why This Structure Exists:**
The separation appears to be a dataset organization decision rather than a practical end-user feature:
1. **Annotation workflow**: Different teams might have worked on masks separately from images
2. **Quality control**: Masks could be verified independently during dataset creation
3. **Storage optimization**: Anno files kept lightweight with only essential annotation data

**Practical Reality:**
- Masks alone without corresponding images have very limited use
- Users need BOTH: images from raw files AND masks from anno files to work with the data
- The masks in anno correspond to the same frames as images in raw (e.g., `frame_000000.png` mask matches `frame_000000.jpg` image)
- The `extract_0026_FULL_both.py` script correctly extracts masks from anno files, while the regular script mistakenly looks for them in raw files and finds nothing
- **Important:** The original extraction scripts would create empty folder structures even when no data existed (e.g., from_raw/masks/ folders with no files, from_anno/images/ folders with no files)
- The modified version of `extract_0026_FULL_both.py` now only creates folders when there's actual data to store, preventing these confusing empty directories

This design choice seems to reflect the internal annotation pipeline rather than end-user convenience. For practical use, you'll typically need both anno and raw files to get a complete, usable dataset.