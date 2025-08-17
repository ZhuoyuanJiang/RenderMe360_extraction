# RenderMe360 Data Processing Pipeline

## Project Structure

```
renderme360_temp/
├── .git/                           # Git repository
├── .gitignore                      # Excludes data files from git
├── README.md                       # This file
│
├── test_download/                  # Main data directory
│   ├── anno/                       # [DATA] Annotation .smc files (~60GB)
│   ├── raw/                        # [DATA] Raw .smc files (~250GB)
│   └── process_data/               # [CODE] Extraction scripts
│       ├── renderme_360_reader.py  # Core library from RenderMe360
│       ├── extract_0026_FULL.py    # Full extraction script
│       ├── extract_for_avatar_research.py  # Research-optimized
│       ├── quick_explore_0026.py   # Data exploration
│       └── README_EXTRACTION_SCRIPTS.md  # Script documentation
│
├── FULL_EXTRACTION/                # [DATA] Extracted data output
├── extracted_data/                 # [DATA] Sample extractions
└── avatar_research_data/           # [DATA] Research-specific output
```

## What's in Git vs What's Not

### ✅ IN GIT (Code & Documentation)
- All Python scripts (`.py`)
- README files (`.md`)
- Configuration files (`.json`, `.yaml`)
- This project structure

### ❌ NOT IN GIT (Data)
- SMC files (`*.smc`) - Raw data ~300GB+
- Extracted images/masks - Can be 100GB+
- Audio files (`*.mp3`)
- 3D meshes (`*.ply`)
- Numpy arrays (`*.npy`, `*.npz`)

## Quick Start

### 1. Clone Repository
```bash
git clone [your-repo-url]
cd renderme360_temp
```

### 2. Download Data (Not in Git)
Place your .smc files in:
- `test_download/anno/` - Annotation files
- `test_download/raw/0026/` - Raw files for subject 0026

### 3. Run Extraction
```bash
cd test_download/process_data

# Explore available data
python quick_explore_0026.py

# Extract one performance
python extract_0026_FULL.py --performance e0

# Extract for research
python extract_for_avatar_research.py
```

## Storage Requirements

| Data Type | Size |
|-----------|------|
| Anno files (downloaded) | ~60 GB |
| Raw files (downloaded) | ~250 GB |
| Single performance extraction | 10-50 GB |
| All 19 performances | 300-500 GB |
| **Total needed** | **~800 GB** |

## Server Requirements

- **Storage**: At least 1TB free space
- **RAM**: 32GB+ recommended
- **CPU**: Multi-core for parallel processing
- **Python**: 3.8+ with numpy, opencv-python, tqdm

## For Server Migration

See `transfer_to_new_server.sh` for easy migration to a server with more storage.

## Research Purpose

This pipeline is designed for audio-driven 3D avatar research, extracting:
- Multi-view synchronized video
- 3D facial landmarks
- FLAME face model parameters
- Audio-visual synchronization data

## Contact

For questions about the extraction pipeline, refer to:
- `process_data/README_EXTRACTION_SCRIPTS.md`

For questions about the dataset:
- [RenderMe360 Official Page]