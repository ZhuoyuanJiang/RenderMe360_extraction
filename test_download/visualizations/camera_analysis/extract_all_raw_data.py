#!/usr/bin/env python3
"""
Extract ALL raw calibration data from all_cameras.npy and save to JSON.
Simple and straightforward - just load and save everything.
"""

import numpy as np
import json

def extract_all_raw_data():
    """Extract all raw calibration data and save to JSON."""

    # Load the calibration file
    calib_path = "/ssd2/zhuoyuan/renderme360_temp/FULL_EXTRACTION_BOTH/0026_s1_all/from_anno/calibration/all_cameras.npy"
    print(f"Loading: {calib_path}")

    # Load the data
    data = np.load(calib_path, allow_pickle=True).item()
    print(f"Loaded {len(data)} cameras")

    # Convert numpy arrays to lists for JSON serialization
    json_data = {}
    for cam_id, cam_data in data.items():
        json_data[cam_id] = {
            'K': cam_data['K'].tolist(),
            'D': cam_data['D'].tolist(),
            'RT': cam_data['RT'].tolist()
        }

    # Save to JSON
    output_path = "ALL_raw_calibration_data.json"
    with open(output_path, 'w') as f:
        json.dump(json_data, f, indent=2)

    print(f"Saved all raw data to: {output_path}")

    # Show what we saved
    first_cam = list(json_data.keys())[0]
    print(f"\nEach camera contains: {list(json_data[first_cam].keys())}")
    print("This is the complete raw calibration data from RenderMe360")

if __name__ == "__main__":
    extract_all_raw_data()