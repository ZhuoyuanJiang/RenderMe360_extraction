# RenderMe360 Data Download and Processing Guide

Great question! Here's a **step-by-step guide** for reproducing this setup in the future:

## Method 1: The Clean Way (Recommended for others)

**For others cloning your repository:**

```bash
# 1. Create the parent directory
mkdir -p /ssd2/username/renderme360_temp

# 2. Clone directly into the directory (this is the key!)
cd /ssd2/username/renderme360_temp
git clone https://github.com/ZhuoyuanJiang/RenderMe360_extraction.git .
#                                                                    ^ Note the dot!
```

The **dot (`.`) at the end** tells git to clone directly into the current directory instead of creating a subdirectory.

然后开始下载data的过程：

## 📋 Complete Step-by-Step Guide for Future Reproduction

Here's the exact process to download both Google Drive folders:

### 1. **Setup Directory Structure**

```bash
cd /ssd2/zhuoyuan/renderme360_temp
mkdir -p test_download/raw test_download/anno
```

### 2. **Test Rclone Connection** (optional but recommended)

```bash
# Verify rclone works
rclone listremotes

# Test access to raw data folder
rclone --drive-root-folder-id 18ko2qXBaTYoO9HIorhHa6J9HSSFFJnBL ls vllab13: | head -5

# Test access to annotation folder
rclone --drive-root-folder-id 1HqW0-FwfeV_Ekr5lA1nLEJ-v9yVwm4dA ls vllab13: | head -5
```

### 3. **Download Raw Data** (First folder)

```bash
rclone copy vllab13: test_download/raw/ \
  --drive-root-folder-id 18ko2qXBaTYoO9HIorhHa6J9HSSFFJnBL \
  -P --drive-acknowledge-abuse \
  --transfers 8 --checkers 16 --fast-list \
  --retries 10 --low-level-retries 20
```

### 4. **Download Annotation Data** (Second folder)

```bash
rclone copy vllab13: test_download/anno/ \
  --drive-root-folder-id 1HqW0-FwfeV_Ekr5lA1nLEJ-v9yVwm4dA \
  -P --drive-acknowledge-abuse \
  --transfers 8 --checkers 16 --fast-list \
  --retries 10 --low-level-retries 20
```

## 🔑 Key Points for Reproduction:

### **Folder IDs:**

- **Raw data:** `18ko2qXBaTYoO9HIorhHa6J9HSSFFJnBL`
- **Annotation data:** `1HqW0-FwfeV_Ekr5lA1nLEJ-v9yVwm4dA`

### **Expected Download Sizes:**

- **Raw data:** ~12GB total (5 files in 0026/ subdirectory)
- **Annotation data:** ~48GB total (6 files directly in anno/)

### **Final Structure After Download:**

```
test_download/
├── raw/
│   └── 0026/                    # Auto-created from Google Drive structure
│       ├── Copy of 0026_e0_raw.smc
│       ├── Copy of 0026_e1_raw.smc
│       ├── Copy of 0026_e3_raw.smc
│       ├── Copy of 0026_e4_raw.smc
│       └── Copy of 0026_e5_raw.smc
└── anno/
    ├── Copy of 0026_s1_all_anno.smc
    ├── Copy of 0026_s2_all_anno.smc
    ├── Copy of 0026_s3_all_anno.smc
    ├── Copy of 0026_s4_all_anno.smc
    ├── Copy of 0026_s5_all_anno.smc
    └── Copy of 0026_s6_all_anno.smc
```

## 📝 Step 5: Remove "Copy of " from File Names

After downloading, all files will have "Copy of " prefix in their names. Here's how to batch rename them:

### **Rename All at Once (from base directory)**

If you want to rename all files in both directories with a single command:

```bash
# From the test_download directory
cd /ssd2/zhuoyuan/renderme360_temp/test_download

# Rename all files in anno directory
for file in anno/"Copy of "*.smc; do 
    [ -f "$file" ] && mv "$file" "anno/${file#anno/Copy of }"
done

# Rename all files in raw/0026 directory
for file in raw/0026/"Copy of "*.smc; do 
    [ -f "$file" ] && mv "$file" "raw/0026/${file#raw/0026/Copy of }"
done
```

### **Expected Output:**

You should see output like:
```
Renamed: Copy of 0026_e0_anno.smc -> 0026_e0_anno.smc
Renamed: Copy of 0026_e1_anno.smc -> 0026_e1_anno.smc
...
```

### **Final Clean Structure:**

```
test_download/
├── raw/
│   └── 0026/
│       ├── 0026_e0_raw.smc
│       ├── 0026_e1_raw.smc
│       ├── 0026_e3_raw.smc
│       ├── 0026_e4_raw.smc
│       └── 0026_e5_raw.smc
└── anno/
    ├── 0026_s1_all_anno.smc
    ├── 0026_s2_all_anno.smc
    ├── 0026_s3_all_anno.smc
    ├── 0026_s4_all_anno.smc
    ├── 0026_s5_all_anno.smc
    └── 0026_s6_all_anno.smc
```

## 💡 Pro Tips:

- Run both downloads in **separate terminal sessions** for parallel downloads
- Use `screen` or `tmux` for long-running transfers
- The `-P` flag shows progress; remove it for cleaner logs
- Adjust `--transfers` based on your bandwidth (8 is usually good)
- The renaming script uses parameter expansion `${file#Copy of }` to remove the prefix
- The `[ -f "$file" ]` check ensures we only rename actual files

## 🎯 Complete One-Liner for Brave Souls:

If you want to rename all "Copy of " files recursively in one go:

```bash
find /ssd2/zhuoyuan/renderme360_temp/test_download -name "Copy of *.smc" -type f | while read file; do
    dir=$(dirname "$file")
    basename=$(basename "$file")
    newname="${basename#Copy of }"
    mv "$file" "$dir/$newname"
    echo "Renamed: $basename -> $newname"
done
```

This exact process should work on any server with your rclone configuration!

## 📦 Step 6: Extract All RenderMe360 Data

**⚠️ IMPORTANT: Understand What You're Extracting**

The RenderMe360 dataset contains **multi-view video recordings**, not just static images:
- **Expression performances (e0-e11)**: Short clips (~110 frames, 3-4 seconds) of facial expressions
- **Speech performances (s1_all-s6_all)**: Long videos (~1500-2500 frames, 50-85 seconds) of people speaking
- **Head movement (h0)**: Head rotation sequences (~150 frames, 5 seconds)

**Note:** Despite the name "speech", the s*_all files contain VIDEO data only. No audio tracks were found in the downloaded files.

After downloading and renaming the .smc files, here's how to extract all the data:

### **6.1 Create Conda Environment**

```bash
# Create dedicated environment for data processing
conda create -n RenderMe360_Data_Processing python=3.9 -y

# Activate the environment
source ~/miniconda3/etc/profile.d/conda.sh
conda activate RenderMe360_Data_Processing

# Install all required dependencies
pip install opencv-python numpy tqdm pydub ffmpeg-python matplotlib pillow scipy h5py
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

### **6.2 Navigate to Processing Directory**

```bash
cd /ssd2/zhuoyuan/renderme360_temp/test_download/process_data
```

### **6.3 Extract Performances**

**Option A: Quick Start - Extract Only Expressions (Recommended for First-Time Users)**

```bash
# Extract only expression and head performances (fast, ~50GB total)
source ~/miniconda3/etc/profile.d/conda.sh
conda activate RenderMe360_Data_Processing

# Extract all expressions + head movement (takes ~30 minutes)
for perf in e0 e1 e2 e3 e4 e5 e6 e7 e8 e9 e10 e11 h0; do
    echo "Extracting $perf..."
    echo "yes" | python extract_0026_FULL.py --performance $perf --separate
done
```

**Option B: Extract Everything Including Speech (Warning: 6-18 hours, ~590GB)**

```bash
# Make the extraction script executable
chmod +x extract_all_0026.sh

# Run the complete extraction (INCLUDING massive speech files)
./extract_all_0026.sh
```

**Option C: Extract Individual Performances**

```bash
# Activate environment first
source ~/miniconda3/etc/profile.d/conda.sh
conda activate RenderMe360_Data_Processing

# Extract a specific performance (e.g., e0)
echo "yes" | python extract_0026_FULL.py --performance e0 --separate

# Available performances:
# Expressions: e0, e1, e2, e3, e4, e5, e6, e7, e8, e9, e10, e11
# Speech: s1_all, s2_all, s3_all, s4_all, s5_all, s6_all
# Head movement: h0
```

### **6.4 Key Features of the Extraction**

✅ **Resume Capability**: If extraction is interrupted, simply run the script again. It will skip already extracted data.

✅ **Separated Output**: Anno and raw data are organized in separate folders for clarity.

✅ **Progress Tracking**: Shows real-time extraction progress with tqdm progress bars.

✅ **Error Handling**: Gracefully handles missing mask data and other errors.

### **6.5 Expected Output Structure**

```
/ssd2/zhuoyuan/renderme360_temp/FULL_EXTRACTION/
└── 0026_[performance]/
    ├── .extraction_complete      # Marker file indicating successful completion
    ├── extraction_info.txt       # Describes the separation structure
    ├── size_summary.txt          # Size breakdown of extracted data
    │
    ├── from_anno/                # Data from annotation file
    │   ├── metadata/             # Actor and camera information
    │   ├── calibration/          # Camera calibration matrices
    │   ├── keypoints2d/          # 2D facial landmarks (cameras 18-32)
    │   ├── keypoints3d/          # 3D facial landmarks
    │   ├── flame/                # FLAME face model parameters (expressions ONLY - e0-e11)
    │   ├── uv_textures/          # UV texture maps (expressions ONLY - e0-e11)
    │   ├── scan/                 # High-res 3D mesh scan (expressions ONLY - e0-e11)
    │   ├── scan_masks/           # Scan visibility masks (expressions ONLY - e0-e11)
    │   └── audio/                # NOT FOUND - no audio data in downloaded files
    │
    └── from_raw/                 # Data from raw file
        ├── images/               # High-resolution RGB images (2048×2448)
        │   ├── cam_00/
        │   │   ├── frame_000000.jpg
        │   │   ├── frame_000001.jpg
        │   │   └── ...
        │   └── cam_59/
        └── masks/                # Segmentation masks (if available)
            ├── cam_00/
            └── cam_59/
```

### **6.6 Storage Requirements and Time Estimates**

| Performance Type | Frames | Extracted Size | Extraction Time | What It Contains |
|-----------------|--------|----------------|-----------------|------------------|
| **Expressions (e0-e11)** | ~110 each | ~3.8 GB each | 2-3 min each | Short facial expressions, FLAME params, UV textures |
| **Speech (s1_all-s6_all)** | ~1500-2500 each | ~80-100 GB each | 1-3 hours each | Long videos of speaking (NO audio), keypoints only |
| **Head movement (h0)** | ~150 | ~4 GB | 3-4 min | Head rotation sequence |

**Total Dataset Size:**
- Expression performances (12×3.8GB): **~46 GB** ✅ Quick to extract
- Speech performances (6×90GB): **~540 GB** ⚠️ Very slow to extract  
- Head movement (1×4GB): **4 GB** ✅ Quick to extract
- **TOTAL: ~590 GB** (requires 6-18 hours for full extraction)

**⚠️ WARNING:** Speech performances are massive! Each contains:
- s1_all: 2,529 frames × 60 cameras = 151,740 images
- s2_all: 1,536 frames × 60 cameras = 92,160 images
- etc.

Consider if you really need the speech data - expressions might be sufficient for many use cases.

### **6.7 Monitoring Extraction Progress**

While extraction is running, you can monitor progress in another terminal:

```bash
# Check which performances are complete
ls -la /ssd2/zhuoyuan/renderme360_temp/FULL_EXTRACTION/*/extraction_complete 2>/dev/null

# Check current extraction size
du -sh /ssd2/zhuoyuan/renderme360_temp/FULL_EXTRACTION/

# Watch real-time size growth
watch -n 5 'du -sh /ssd2/zhuoyuan/renderme360_temp/FULL_EXTRACTION/*/ | sort -h'
```

### **6.8 Known Issues and Troubleshooting**

**Known Issues:**

1. **No audio in speech files**: Despite being named "speech" performances, no audio data was found in the annotation files. The speech files contain only video frames of people speaking.

2. **Speech extraction appears to "hang"**: This is normal - speech files have 20x more frames than expressions. Extraction is working but very slow.

3. **Huge storage requirements for speech**: Each speech performance expands to 80-100GB when extracted.

**If extraction fails:**

1. Check if conda environment is activated
2. Verify all dependencies are installed
3. Ensure sufficient disk space (need ~600GB free for complete extraction)
4. Check error messages for missing dependencies

**To restart a failed extraction:**

```bash
# Remove the incomplete extraction marker
rm /ssd2/zhuoyuan/renderme360_temp/FULL_EXTRACTION/0026_[performance]/.extraction_complete

# Run extraction again - it will resume from where it left off
./extract_all_0026.sh
```

**To completely re-extract a performance:**

```bash
# Remove the entire performance directory
rm -rf /ssd2/zhuoyuan/renderme360_temp/FULL_EXTRACTION/0026_[performance]/

# Run extraction again
./extract_all_0026.sh
```

## 📊 Summary of Scripts and Important Notes

### **Essential Scripts:**

1. **`extract_all_0026.sh`** - Main batch extraction script with resume capability
2. **`extract_0026_FULL.py`** - Core extraction engine (modified with fixes)

### **Key Modifications Made:**

1. **`extract_0026_FULL.py`** - Fixed to handle:
   - JSON serialization of numpy types
   - Missing audio data in speech files  
   - Resume capability (skips existing files)
   - Missing mask data gracefully
   - Separated output structure (anno vs raw)

### **Environment Required:**

- **`RenderMe360_Data_Processing`** - Conda environment with all dependencies

### **Important Expectations:**

- **Expression extraction**: Fast (~30 minutes total), small (~50GB)
- **Speech extraction**: VERY slow (6-18 hours), massive (~540GB)
- **No audio data**: Speech files contain only video, no audio tracks
- **Resume capability**: Script can be safely interrupted and restarted

### **Recommended Approach:**

For most research purposes, **extract only the expression performances first** (e0-e11, h0). These are quick and contain rich facial data with FLAME parameters. Only extract speech performances if you specifically need long video sequences.

This guide ensures reproducible extraction of the RenderMe360 dataset with realistic expectations about data content, storage requirements, and processing time!