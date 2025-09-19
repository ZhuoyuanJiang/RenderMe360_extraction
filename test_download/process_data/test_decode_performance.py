#!/usr/bin/env python3
"""Test actual decode performance including cv2.imdecode."""

import h5py
import time
import cv2
import numpy as np

def test_decode_performance(file_path, cam_id='00', img_type='color', num_frames=10):
    """Test full decode performance like in the actual script."""
    with h5py.File(file_path, 'r') as smc:
        print(f"\nFile: {file_path}")
        print(f"Testing: Camera/{cam_id}/{img_type}")

        total_decode_time = 0
        total_write_time = 0

        for frame_id in range(num_frames):
            # Read compressed data
            start = time.time()
            img_byte = smc["Camera"][cam_id][img_type][str(frame_id)][()]
            read_time = time.time() - start

            # Decode image
            start = time.time()
            img_color = cv2.imdecode(img_byte, cv2.IMREAD_COLOR)

            # Additional processing for masks
            if img_type == 'mask':
                img_color = np.max(img_color, 2).astype(np.uint8)
            decode_time = time.time() - start
            total_decode_time += decode_time

            # Simulate write
            start = time.time()
            if img_type == 'color':
                _, encoded = cv2.imencode('.jpg', img_color, [cv2.IMWRITE_JPEG_QUALITY, 95])
            else:
                _, encoded = cv2.imencode('.png', img_color)
            write_time = time.time() - start
            total_write_time += write_time

            if frame_id == 0:
                print(f"  Frame 0 shape: {img_color.shape}")
                print(f"  Read: {read_time*1000:.1f}ms, Decode: {decode_time*1000:.1f}ms, Encode: {write_time*1000:.1f}ms")

        print(f"\nAverage for {num_frames} frames:")
        print(f"  Decode: {total_decode_time/num_frames*1000:.1f} ms")
        print(f"  Write:  {total_write_time/num_frames*1000:.1f} ms")
        print(f"  Total:  {(total_decode_time + total_write_time)/num_frames*1000:.1f} ms per frame")

# Test both
print("Testing full decode performance (including cv2.imdecode)...")

# Test RAW images
test_decode_performance(
    '/ssd4/zhuoyuan/renderme360_temp/temp_smc/0026_s1_all_raw.smc',
    cam_id='00',
    img_type='color',
    num_frames=10
)

# Test ANNO masks
test_decode_performance(
    '/ssd4/zhuoyuan/renderme360_temp/temp_smc/0026_s1_all_anno.smc',
    cam_id='00',
    img_type='mask',
    num_frames=10
)