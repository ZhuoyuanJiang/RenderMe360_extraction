# Mask Extraction Performance Optimization Rationale

## Date: September 18, 2025

## Problem Statement
During extraction of subject 0026/s1_all with 20 cameras, mask extraction from ANNO files was taking approximately 4-5 minutes per camera, compared to only 39 seconds for image extraction from RAW files. This seemed counterintuitive since masks are smaller than images.

## Investigation Process

### Step 1: Initial Observations
- RAW image extraction: ~39 seconds per camera for 2529 frames
- ANNO mask extraction: ~270 seconds per camera for the same 2529 frames
- Question: Why are masks (smaller files) taking 7x longer than images?

### Step 2: File Structure Analysis
Checked existing extraction output:
```bash
# RAW images: 1.6GB per camera, ~607KB per file
ls -lh /ssd4/zhuoyuan/renderme360_temp/test_download/subjects/0026/s1_all/from_raw/images/cam_00/
# Result: 1.6G total, frame_000000.jpg = 607K

# ANNO masks: 185MB per camera, ~76KB per file
ls -lh /ssd4/zhuoyuan/renderme360_temp/test_download/subjects/0026/s1_all/from_anno/masks/cam_00/
# Result: 185M total, frame_000000.png = 76K
```

Masks are 8x smaller but taking 7x longer - clearly an algorithmic issue, not I/O.

### Step 3: HDF5 Read Performance Testing
Created `test_hdf5_performance.py` to test raw HDF5 read speeds:
```python
# Results:
RAW file reads: 2.4 ms per read
ANNO file reads: 0.2 ms per read
```
ANNO reads are actually faster! Problem isn't HDF5 access.

### Step 4: Full Decode Performance Testing
Created `test_decode_performance.py` to test complete extraction pipeline:
```python
# Results:
RAW images (color JPEG):
  - Decode: 37.7 ms
  - Encode: 15.7 ms
  - Total: 53.4 ms per frame

ANNO masks (current method):
  - Decode: 114.1 ms  # <-- Problem found!
  - Encode: 11.6 ms
  - Total: 125.8 ms per frame
```

### Step 5: Root Cause Analysis
Examined the `renderme_360_reader.py` code (lines 126-131):
```python
# Current implementation:
img_byte = self.smc["Camera"][Camera_id][Image_type][Frame_id][()]
img_color = self.__read_color_from_bytes__(img_byte)  # Decodes as 3-channel color
if Image_type == 'mask':
    img_color = np.max(img_color, 2).astype(np.uint8)  # Converts 3-channel to 1-channel
```

The issue: Masks are being decoded as 3-channel color images then converted to grayscale!

### Step 6: Mask Format Investigation
Created `test_mask_format.py` to understand storage format:
```python
# Findings:
- Masks in SMC: PNG format, 77,115 bytes compressed
- First bytes: [137, 80, 78, 71...] = PNG signature
- Decode performance:
  - IMREAD_COLOR: 37.0ms (current method)
  - IMREAD_GRAYSCALE: 22.2ms (optimized)
  - np.max() conversion: 77.9ms
  - Total current: 37.0 + 77.9 = 114.9ms
```

### Step 7: Storage Analysis
Created `check_smc_storage.py`:
```
Mask storage in SMC file:
- Stored as: Compressed PNG bytes (grayscale)
- Size in SMC: 77,115 bytes
- Uncompressed: 5,013,504 bytes (65x compression)
- Format: PNG (8-bit grayscale)
```

Masks are ALREADY grayscale PNGs in the SMC file! The color decoding is completely unnecessary.

### Step 8: Verification of Output Equivalence
Created `compare_mask_methods.py` to ensure optimization produces identical output:

```python
# Comparison results:
Current method shape: (2048, 2448)
Optimized method shape: (2048, 2448)

Equality checks:
Current == Optimized: True
Current == Existing: True
Optimized == Existing: True

File sizes: All 77,115 bytes (identical)

MD5 checksums:
Current: e075c80fd7c651c16a7038caf2e22a40
Optimized: e075c80fd7c651c16a7038caf2e22a40
Existing: e075c80fd7c651c16a7038caf2e22a40
All identical!

Performance:
Current: 107.0ms per frame
Optimized: 19.3ms per frame
Speedup: 5.6x faster
```

## The Optimization

### What was changed:
In `renderme_360_reader.py`, lines 126-131:

**Before:**
```python
img_color = self.__read_color_from_bytes__(img_byte)  # Always decode as color
if Image_type == 'mask':
    img_color = np.max(img_color, 2).astype(np.uint8)  # Convert to grayscale
```

**After:**
```python
if Image_type == 'mask':
    img = cv2.imdecode(img_byte, cv2.IMREAD_GRAYSCALE)  # Direct grayscale decode
else:
    img = self.__read_color_from_bytes__(img_byte)  # Color for images
```

### Why it's safe:
1. **Output identical**: MD5 hashes match perfectly
2. **File format unchanged**: Still 8-bit grayscale PNGs
3. **File size unchanged**: Exactly 77,115 bytes per mask
4. **Pixel values identical**: numpy array_equal returns True
5. **No data loss**: Masks were already grayscale in SMC

### Performance improvement:
- **Per frame**: 107ms → 19ms (5.6x faster)
- **Per camera** (2529 frames): ~4.5 minutes → ~48 seconds
- **20 cameras total**: ~90 minutes → ~16 minutes

## Conclusion

The optimization removes unnecessary color decoding and conversion for masks that are already stored as grayscale. This provides a 5.6x speedup with zero changes to output quality or format. The patch is safe, verified, and recommended for immediate use.