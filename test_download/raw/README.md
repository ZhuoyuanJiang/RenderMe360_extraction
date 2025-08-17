# Raw Data Directory

This directory should contain raw .smc files from the RenderMe360 dataset.

## Expected Structure

```
raw/
├── 0026/
│   ├── 0026_e0_raw.smc
│   ├── 0026_e1_raw.smc
│   ├── ... (all expression performances)
│   ├── 0026_s1_all_raw.smc
│   ├── ... (all speech performances)
│   └── 0026_h0_raw.smc
└── [other subjects]/
```

## Data Content

Raw files contain:
- High-resolution images (2048×2448)
- High-resolution masks

## Note

The actual .smc files are not included in git due to size (~250GB for subject 0026).
Download them separately from the RenderMe360 dataset.
