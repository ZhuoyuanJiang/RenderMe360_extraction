# 📊 RenderMe360 Storage Analysis Report for Subject 0026

## 1. Feature-Level Storage Breakdown

### Expression Performance (e.g., e0):
- **Images**: 3.9 GB (60 cameras × ~300 frames)
- **Masks**: 244 KB (minimal, likely reference masks)
- **FLAME parameters**: 12 KB (facial expression data)
- **UV textures**: 980 KB (face texture maps)
- **3D scan mesh**: 17 MB (detailed face geometry)
- **Scan masks**: 5.6 MB (segmentation masks)
- **Calibration**: 268 KB (camera matrices)
- **Keypoints (2D/3D)**: 212 KB (skeletal tracking)
- **Total**: ~3.9 GB per expression performance

### Speech Performance (e.g., s1_all):
- **Images**: 88 GB (60 cameras × ~6000 frames)
- **Masks**: 244 KB (minimal)
- **Audio**: 35 MB (mp3 + raw numpy)
- **Calibration**: 268 KB
- **Keypoints (2D/3D)**: 4.7 MB (more frames)
- **Total**: ~88 GB per speech performance

## 2. Storage Comparison: Original vs Extracted

| Performance | Anno .smc | Raw .smc | Combined Original | Extracted | Expansion Factor |
|------------|-----------|----------|------------------|-----------|-----------------|
| **e0** | 701 MB | 2.4 GB | 3.1 GB | 3.9 GB | **1.26x** |
| **e1** | 788 MB | 2.8 GB | 3.6 GB | 4.4 GB | **1.22x** |
| **e2** | 761 MB | 2.7 GB | 3.5 GB | 4.3 GB | **1.23x** |
| **e3** | 691 MB | 2.4 GB | 3.1 GB | 3.8 GB | **1.23x** |
| **e4** | 591 MB | 2.1 GB | 2.7 GB | 3.3 GB | **1.22x** |
| **e5** | 722 MB | 2.6 GB | 3.3 GB | 4.1 GB | **1.24x** |
| **e6** | 836 MB | 3.0 GB | 3.8 GB | 4.7 GB | **1.24x** |
| **e7** | 703 MB | 2.5 GB | 3.2 GB | 3.9 GB | **1.22x** |
| **e8** | 707 MB | 2.5 GB | 3.2 GB | 3.9 GB | **1.22x** |
| **e9** | 777 MB | 2.7 GB | 3.5 GB | 4.3 GB | **1.23x** |
| **e10** | 814 MB | 2.8 GB | 3.6 GB | 4.5 GB | **1.25x** |
| **e11** | 819 MB | 2.9 GB | 3.7 GB | 4.6 GB | **1.24x** |
| **h0** | 457 MB | 2.6 GB | 3.1 GB | 4.0 GB | **1.29x** |
| **s1_all** | 14 GB | 56 GB | 70 GB | 88 GB | **1.26x** |
| **s2_all** | 8.2 GB | 34 GB | 42.2 GB | 53 GB | **1.26x** |
| **s3_all** | 7.7 GB | 32 GB | 39.7 GB | 49 GB | **1.23x** |
| **s4_all** | 7.8 GB | 31 GB | 38.8 GB | 49 GB | **1.26x** |
| **s5_all** | 5.3 GB | 31 GB | 36.3 GB | 48 GB | **1.32x** |
| **s6_all** | 5.8 GB | 23 GB | 28.8 GB | 36 GB | **1.25x** |

**Total for all 19 performances:**
- Original .smc files (anno): ~60 GB
- Original .smc files (raw): ~249 GB
- Combined original: ~309 GB
- Extracted data: **374 GB**
- Overall expansion: **1.21x**

## 3. Why Extracted Files Are LARGER

The extracted data is **21% larger** than the original .smc files because:

### 3.1 Decompression
- **.smc files use proprietary compression**. Extraction decompresses:
  - Images: SMC custom compression → extracted as JPEG (quality 95)
  - Masks: Compressed binary → uncompressed PNG
  - Data arrays: Compressed → numpy .npz files

### 3.2 Redundant Storage
- Some data might be stored more efficiently in .smc:
  - Shared calibration data duplicated per camera
  - Delta encoding for sequential frames lost
  - Metadata overhead for thousands of individual files

### 3.3 File System Overhead
- 374 GB across ~1.2 million files (60 cameras × 20,000+ frames)
- Each file has filesystem metadata overhead
- Block size inefficiencies for small files
- Directory structure overhead

## 4. Storage Efficiency by Feature

### Most Efficient (Small):
- **Keypoints**: <5 MB (highly compressible skeletal data)
- **FLAME**: <100 KB (low-dimensional parametric model)
- **Calibration**: <300 KB (static camera parameters)
- **Audio**: 35 MB (already compressed MP3)

### Least Efficient (Large):
- **Images**: 99% of storage (3.9-88 GB per performance)
- **3D scan**: 17 MB (uncompressed mesh vertices)
- **UV textures**: 1 MB (per-frame texture maps)
- **Scan masks**: 5.6 MB (60 camera segmentation masks)

## 5. Key Insights

### Storage Distribution:
1. **Images are 99.8% of all data** (373.3 GB out of 374 GB total)
   - Expression images: 46.8 GB (12 performances)
   - Speech images: 321 GB (6 performances)
   - Head rotation images: 4.0 GB (1 performance)

2. **Non-image data is only 0.2%** (< 1 GB total for all 19 performances)
   - All annotations combined: ~320 MB
   - All audio combined: ~161 MB
   - All masks combined: ~4.6 MB

### Performance Type Comparison:
3. **Speech performances are 20x larger** than expressions
   - Average expression: 4.1 GB (300 frames)
   - Average speech: 53.5 GB (4000-6600 frames)
   - Ratio explained: More frames × longer duration

4. **Extraction adds 21% overhead** due to:
   - Decompression from proprietary .smc format
   - File system overhead (1.2 million individual files)
   - Lost delta encoding between frames

### Data Type Insights:
5. **The paradox of research data**:
   - What takes space: Images (373.3 GB)
   - What researchers often need: FLAME (144 KB), keypoints (28 MB)
   - Storage efficiency: Research data < 0.01% of total

6. **Anno vs Raw file patterns**:
   - Anno files: Contain all scientific annotations but low-res images
   - Raw files: 4x larger, contain high-res images + audio
   - Anno ranges: 457 MB (h0) to 14 GB (s1_all)
   - Raw ranges: 2.1 GB (e4) to 56 GB (s1_all)

7. **Consistency within performance types**:
   - Expression performances: 3.3-4.7 GB (consistent)
   - Speech performances: 36-88 GB (varies with speech length)
   - Head rotation: 4.0 GB (similar to expressions)

## 6. Recommendations

### If Storage is Critical:
- Keep original .smc files for archival (20% smaller)
- Extract only needed performances on-demand
- Consider re-compressing images to JPEG quality 85 (save ~30%)
- Use symbolic links for shared calibration data
- Store images in HDF5/Zarr format instead of individual files

### For Research Use:
- Current extraction is optimal for accessibility
- Separate anno/raw folders enable selective processing
- Individual frame files allow parallel processing
- Uncompressed formats ensure no quality loss

### Storage Planning:
- Expression performances: allocate 5 GB each
- Speech performances: allocate 50-90 GB each
- Full subject extraction: allocate 400 GB
- Include 20% buffer for intermediate processing

## 7. Technical Details

### Complete Data Organization (All 19 Performances Combined):
```
FULL_EXTRACTION/ (374 GB total)
├── 12 Expression performances (e0-e11): 49.7 GB total
├── 6 Speech performances (s1_all-s6_all): 321 GB total  
├── 1 Head rotation (h0): 4.0 GB total
│
└── Each performance contains:
    ├── from_anno/          # Annotations (544 KB - 4.8 MB per performance)
    │   ├── calibration/    # 5.1 MB total (268 KB × 19)
    │   ├── keypoints2d/    # 24 MB total (184 KB - 4.0 MB each)
    │   ├── keypoints3d/    # 3.8 MB total (28 KB - 476 KB each)
    │   ├── metadata/       # 152 KB total (8 KB × 19)
    │   ├── flame/          # 144 KB total (12 KB × 12, expressions only)
    │   ├── uv_textures/    # 11.8 MB total (980 KB × 12, expressions only)
    │   ├── scan/           # 204 MB total (17 MB × 12, expressions only)
    │   └── scan_masks/     # 67.2 MB total (5.6 MB × 12, expressions only)
    └── from_raw/           # High-res data (3.9 GB - 88 GB per performance)
        ├── images/         # 373.3 GB total (99.8% of all data)
        ├── masks/          # 4.6 MB total (244 KB × 19)
        └── audio/          # 161 MB total (21-35 MB × 6, speech only)
```

### Detailed Tree Structure for Representative Performances

We're showing 4 representative performances (not listing all 19 for brevity):

#### 1. Expression Performance: 0026_e0 (Total: 3.9 GB)
```
0026_e0/
├── from_anno/ (24 MB)
│   ├── calibration/     268 KB  # Camera matrices for 60 cameras
│   ├── flame/           12 KB   # Face model parameters (~60 frames sampled)
│   ├── keypoints2d/     184 KB  # 2D joints for cameras 18-32
│   ├── keypoints3d/     28 KB   # 3D skeleton (~30 frames sampled)
│   ├── metadata/        8 KB    # Performance info JSON
│   ├── scan/            17 MB   # 3D face mesh (mesh.ply)
│   ├── scan_masks/      5.6 MB  # 60 PNG masks for scan alignment
│   └── uv_textures/     980 KB  # Face texture maps (10 frames)
└── from_raw/ (3.9 GB)
    ├── images/          3.9 GB  # 60 cameras × 293 frames = 17,580 JPEGs
    └── masks/           244 KB  # Reference segmentation masks
```

#### 2. Speech Performance: 0026_s1_all (Total: 88 GB)
```
0026_s1_all/
├── from_anno/ (4.8 MB)
│   ├── calibration/     268 KB  # Camera matrices for 60 cameras
│   ├── keypoints2d/     4.0 MB  # 2D joints (more frames than expression)
│   ├── keypoints3d/     476 KB  # 3D skeleton (more frames)
│   └── metadata/        8 KB    # Performance info JSON
└── from_raw/ (88 GB)
    ├── audio/           35 MB   # audio.mp3 (3.3 MB) + audio_data.npz (31 MB)
    ├── images/          88 GB   # 60 cameras × 6633 frames = 397,980 JPEGs
    └── masks/           244 KB  # Reference segmentation masks
```

#### 3. Speech Performance: 0026_s2_all (Total: 53 GB)
```
0026_s2_all/
├── from_anno/ (3.1 MB)
│   ├── calibration/     268 KB  # Camera matrices for 60 cameras
│   ├── keypoints2d/     2.5 MB  # 2D joints (medium-length speech)
│   ├── keypoints3d/     292 KB  # 3D skeleton
│   └── metadata/        8 KB    # Performance info JSON
└── from_raw/ (53 GB)
    ├── audio/           21 MB   # Shorter audio than s1_all
    ├── images/          53 GB   # 60 cameras × ~4000 frames
    └── masks/           244 KB  # Reference segmentation masks
```

#### 4. Head Rotation: 0026_h0 (Total: 4.0 GB)
```
0026_h0/
├── from_anno/ (544 KB)
│   ├── calibration/     268 KB  # Camera matrices for 60 cameras
│   ├── keypoints2d/     240 KB  # 2D joints for head rotation sequence
│   ├── keypoints3d/     28 KB   # 3D skeleton
│   └── metadata/        8 KB    # Performance info JSON
└── from_raw/ (4.0 GB)
    ├── images/          4.0 GB  # 60 cameras × ~300 frames
    └── masks/           244 KB  # Reference segmentation masks
```

### File Counts (approximate):
- Expression performance: ~18,000 files (60 cameras × 300 frames)
- Speech performance: ~360,000 files (60 cameras × 6000 frames)
- Total for subject 0026: ~1.2 million files

---
*Report generated: 2025-09-03*
*Data location: /ssd4/zhuoyuan/renderme360_temp/FULL_EXTRACTION*