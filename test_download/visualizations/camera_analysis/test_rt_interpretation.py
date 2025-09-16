#!/usr/bin/env python3
"""
Test different interpretations of RT matrix to find correct camera positions.
"""

import numpy as np
from pathlib import Path
import math

def test_rt_interpretations():
    """Test different ways to extract camera position from RT matrix."""

    # Load calibration data
    calib_path = Path("/ssd2/zhuoyuan/renderme360_temp/FULL_EXTRACTION_BOTH/0026_s1_all/from_anno/calibration/all_cameras.npy")
    calibrations = np.load(calib_path, allow_pickle=True).item()

    # Convert keys to integers if they're strings
    calibrations = {int(k): v for k, v in calibrations.items()}

    print("Testing different RT matrix interpretations for cameras 0, 15, 30, 45:")
    print("=" * 70)

    test_cameras = [0, 15, 30, 45]

    for cam_id in test_cameras:
        if cam_id not in calibrations:
            continue

        RT = calibrations[cam_id]['RT']
        R = RT[:3, :3]
        t = RT[:3, 3]

        print(f"\nCamera {cam_id}:")
        print(f"  Translation vector t: {t}")

        # Method 1: Direct translation (if RT is world-to-camera)
        pos1 = t
        yaw1 = math.degrees(math.atan2(pos1[0], pos1[2]))
        print(f"  Method 1 (t):        pos={pos1}, yaw={yaw1:.1f}°")

        # Method 2: Negative inverse (if RT is camera-to-world)
        pos2 = -R.T @ t
        yaw2 = math.degrees(math.atan2(pos2[0], pos2[2]))
        print(f"  Method 2 (-R^T @ t): pos={pos2}, yaw={yaw2:.1f}°")

        # Method 3: Negative translation (simple)
        pos3 = -t
        yaw3 = math.degrees(math.atan2(pos3[0], pos3[2]))
        print(f"  Method 3 (-t):       pos={pos3}, yaw={yaw3:.1f}°")

        # Method 4: Extract from inverse of RT
        RT_inv = np.linalg.inv(RT)
        pos4 = RT_inv[:3, 3]
        yaw4 = math.degrees(math.atan2(pos4[0], pos4[2]))
        print(f"  Method 4 (inv(RT)):  pos={pos4}, yaw={yaw4:.1f}°")

    print("\n" + "=" * 70)
    print("\nTesting all 60 cameras with each method to check distribution:")

    for method_num in range(1, 5):
        yaws = []
        for cam_id in range(60):
            if cam_id not in calibrations:
                continue
            RT = calibrations[cam_id]['RT']
            R = RT[:3, :3]
            t = RT[:3, 3]

            if method_num == 1:
                pos = t
            elif method_num == 2:
                pos = -R.T @ t
            elif method_num == 3:
                pos = -t
            elif method_num == 4:
                RT_inv = np.linalg.inv(RT)
                pos = RT_inv[:3, 3]

            yaw = math.degrees(math.atan2(pos[0], pos[2]))
            yaws.append(yaw)

        yaw_range = max(yaws) - min(yaws)
        print(f"\nMethod {method_num}: Yaw range = {min(yaws):.1f}° to {max(yaws):.1f}° (span: {yaw_range:.1f}°)")

        # Check if this looks like 360 coverage
        if yaw_range > 300:
            print("  -> This looks like 360° coverage!")
            # Show distribution
            front = sum(1 for y in yaws if -90 <= y <= 90)
            rear = len(yaws) - front
            print(f"  -> Front: {front} cameras, Rear: {rear} cameras")

if __name__ == "__main__":
    test_rt_interpretations()