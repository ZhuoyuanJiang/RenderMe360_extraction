# Annotation Data Directory

This directory should contain annotation `.smc` files from the RenderMe360 dataset.

## Expected Files

For subject 0026:
- `0026_e0_anno.smc` to `0026_e11_anno.smc` - Expression performances
- `0026_s1_all_anno.smc` to `0026_s6_all_anno.smc` - Speech performances  
- `0026_h0_anno.smc` - Head movement performance

## Data Content

Annotation files contain:
- FLAME parameters (expressions only)
- 2D/3D keypoints
- UV textures
- Scan mesh
- Calibration matrices
- Audio (speech only)
- Low-resolution preview images

## Note

The actual `.smc` files are not included in git due to size (~60GB total).
Download them separately from the RenderMe360 dataset.