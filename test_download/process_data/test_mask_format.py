#!/usr/bin/env python3
"""Investigate mask storage format and decoding."""

import h5py
import cv2
import numpy as np
import time

with h5py.File('/ssd4/zhuoyuan/renderme360_temp/temp_smc/0026_s1_all_anno.smc', 'r') as smc:
    # Check raw bytes
    mask_bytes = smc["Camera"]["00"]["mask"]["0"][()]
    print(f"Mask bytes shape: {mask_bytes.shape}")
    print(f"Mask bytes dtype: {mask_bytes.dtype}")
    print(f"Mask bytes size: {len(mask_bytes):,} bytes")

    # Check first few bytes to identify format
    print(f"First 10 bytes: {mask_bytes[:10]}")

    # Check if PNG
    if mask_bytes[:8].tolist() == [137, 80, 78, 71, 13, 10, 26, 10]:
        print("Format: PNG")
    # Check if JPEG
    elif mask_bytes[:2].tolist() == [255, 216]:
        print("Format: JPEG")
    else:
        print("Format: Unknown")

    # Test decode as different formats
    print("\nTesting decode performance:")

    # Standard decode
    start = time.time()
    img1 = cv2.imdecode(mask_bytes, cv2.IMREAD_COLOR)
    time1 = time.time() - start
    print(f"IMREAD_COLOR: {time1*1000:.1f}ms, shape: {img1.shape if img1 is not None else 'None'}")

    # Grayscale decode
    start = time.time()
    img2 = cv2.imdecode(mask_bytes, cv2.IMREAD_GRAYSCALE)
    time2 = time.time() - start
    print(f"IMREAD_GRAYSCALE: {time2*1000:.1f}ms, shape: {img2.shape if img2 is not None else 'None'}")

    # As-is decode
    start = time.time()
    img3 = cv2.imdecode(mask_bytes, cv2.IMREAD_UNCHANGED)
    time3 = time.time() - start
    print(f"IMREAD_UNCHANGED: {time3*1000:.1f}ms, shape: {img3.shape if img3 is not None else 'None'}")

    # Check if there's redundant processing
    if img1 is not None:
        print(f"\nOriginal processing (np.max(img_color, 2)):")
        start = time.time()
        processed = np.max(img1, 2).astype(np.uint8)
        time4 = time.time() - start
        print(f"Time: {time4*1000:.1f}ms")
        print(f"Processed shape: {processed.shape}")

        # Check if img2 (grayscale) gives same result
        if img2 is not None:
            print(f"Are grayscale and processed identical? {np.array_equal(img2, processed)}")