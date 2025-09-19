#!/usr/bin/env python3
"""Compare current vs optimized mask extraction methods to ensure identical output."""

import h5py
import cv2
import numpy as np
import hashlib

def extract_mask_current_method(smc_file, cam_id='00', frame_id=0):
    """Current method: decode as color, then convert."""
    with h5py.File(smc_file, 'r') as smc:
        mask_bytes = smc["Camera"][cam_id]["mask"][str(frame_id)][()]

        # Current method (slow)
        img_color = cv2.imdecode(mask_bytes, cv2.IMREAD_COLOR)
        mask = np.max(img_color, 2).astype(np.uint8)

        return mask

def extract_mask_optimized_method(smc_file, cam_id='00', frame_id=0):
    """Optimized method: decode directly as grayscale."""
    with h5py.File(smc_file, 'r') as smc:
        mask_bytes = smc["Camera"][cam_id]["mask"][str(frame_id)][()]

        # Optimized method (fast)
        mask = cv2.imdecode(mask_bytes, cv2.IMREAD_GRAYSCALE)

        return mask

def compare_with_existing(existing_file):
    """Load existing extracted mask for comparison."""
    return cv2.imread(existing_file, cv2.IMREAD_GRAYSCALE)

# Test paths
smc_file = '/ssd4/zhuoyuan/renderme360_temp/temp_smc/0026_s1_all_anno.smc'
existing_mask = '/ssd4/zhuoyuan/renderme360_temp/FULL_EXTRACTION_BOTH/0026_s1_all/from_anno/masks/cam_00/frame_000000.png'
current_extraction = '/ssd4/zhuoyuan/renderme360_temp/test_download/subjects/0026/s1_all/from_anno/masks/cam_00/frame_000000.png'

print("Comparing mask extraction methods...")
print("=" * 60)

# Extract using both methods
mask_current = extract_mask_current_method(smc_file)
mask_optimized = extract_mask_optimized_method(smc_file)
mask_existing = compare_with_existing(existing_mask)

# Also check current extraction if it exists
try:
    mask_current_extraction = compare_with_existing(current_extraction)
    has_current = True
except:
    has_current = False

# Compare
print(f"Current method shape: {mask_current.shape}")
print(f"Optimized method shape: {mask_optimized.shape}")
print(f"Existing extracted shape: {mask_existing.shape}")
if has_current:
    print(f"Current extraction shape: {mask_current_extraction.shape}")

print("\nEquality checks:")
print(f"Current == Optimized: {np.array_equal(mask_current, mask_optimized)}")
print(f"Current == Existing: {np.array_equal(mask_current, mask_existing)}")
print(f"Optimized == Existing: {np.array_equal(mask_optimized, mask_existing)}")
if has_current:
    print(f"Current extraction == Existing: {np.array_equal(mask_current_extraction, mask_existing)}")

# Check file sizes when saved
cv2.imwrite('/tmp/mask_current.png', mask_current)
cv2.imwrite('/tmp/mask_optimized.png', mask_optimized)

import os
size_current = os.path.getsize('/tmp/mask_current.png')
size_optimized = os.path.getsize('/tmp/mask_optimized.png')
size_existing = os.path.getsize(existing_mask)

print("\nFile sizes when saved:")
print(f"Current method: {size_current:,} bytes")
print(f"Optimized method: {size_optimized:,} bytes")
print(f"Existing file: {size_existing:,} bytes")
print(f"All sizes identical: {size_current == size_optimized == size_existing}")

# Check MD5 hashes
def get_file_hash(filepath):
    with open(filepath, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()

print("\nMD5 checksums:")
print(f"Current: {get_file_hash('/tmp/mask_current.png')}")
print(f"Optimized: {get_file_hash('/tmp/mask_optimized.png')}")
print(f"Existing: {get_file_hash(existing_mask)}")
if has_current:
    print(f"Current extraction: {get_file_hash(current_extraction)}")

# Performance comparison
import time

print("\nPerformance test (10 frames):")
start = time.time()
for i in range(10):
    _ = extract_mask_current_method(smc_file, frame_id=i)
time_current = time.time() - start

start = time.time()
for i in range(10):
    _ = extract_mask_optimized_method(smc_file, frame_id=i)
time_optimized = time.time() - start

print(f"Current method: {time_current:.2f}s ({time_current/10*1000:.1f}ms per frame)")
print(f"Optimized method: {time_optimized:.2f}s ({time_optimized/10*1000:.1f}ms per frame)")
print(f"Speedup: {time_current/time_optimized:.1f}x faster")