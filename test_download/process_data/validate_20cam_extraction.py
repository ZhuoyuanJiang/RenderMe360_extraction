#!/usr/bin/env python3
"""
Validate 20-camera extraction against 60-camera reference extraction.

This script compares the 20 cameras extracted in the new pipeline against
the same 20 cameras in the full 60-camera extraction to ensure data integrity.

Paths:
- New 20-camera extraction: /ssd4/zhuoyuan/renderme360_temp/test_download/subjects/0026/s1_all/
- Reference 60-camera extraction: /ssd4/zhuoyuan/renderme360_temp/test_download/subjects/0026_60cams/s1_all/
"""

import os
import sys
from pathlib import Path
import hashlib
import cv2
import numpy as np
import json
import random

# Define the 20 cameras we extracted
CAMERA_LIST = [0, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 36, 37, 49, 51, 54, 55, 56]

def compute_file_hash(filepath, sample=False):
    """Compute MD5 hash of a file."""
    if not filepath.exists():
        return None

    md5 = hashlib.md5()
    with open(filepath, 'rb') as f:
        if sample:
            # For large files, just sample the beginning and end
            f.seek(0)
            md5.update(f.read(8192))
            f.seek(-8192, 2)
            md5.update(f.read(8192))
        else:
            # Hash entire file
            for chunk in iter(lambda: f.read(8192), b''):
                md5.update(chunk)
    return md5.hexdigest()

def compare_images(img1_path, img2_path):
    """Compare two images pixel by pixel."""
    if not img1_path.exists() or not img2_path.exists():
        return False, "File missing"

    # Check file sizes first
    size1 = img1_path.stat().st_size
    size2 = img2_path.stat().st_size
    if size1 != size2:
        return False, f"Size mismatch: {size1} vs {size2}"

    # Load and compare images
    img1 = cv2.imread(str(img1_path))
    img2 = cv2.imread(str(img2_path))

    if img1 is None or img2 is None:
        return False, "Failed to load image"

    if img1.shape != img2.shape:
        return False, f"Shape mismatch: {img1.shape} vs {img2.shape}"

    # Check if images are identical
    if np.array_equal(img1, img2):
        return True, "Identical"
    else:
        # Calculate difference
        diff = cv2.absdiff(img1, img2)
        max_diff = np.max(diff)
        mean_diff = np.mean(diff)
        return False, f"Pixel difference - max: {max_diff}, mean: {mean_diff:.2f}"

def validate_camera_data(new_dir, ref_dir, cam_id, data_type='images', source='from_raw'):
    """Validate data for a specific camera."""
    cam_str = f'cam_{cam_id:02d}'

    new_cam_dir = new_dir / source / data_type / cam_str
    ref_cam_dir = ref_dir / source / data_type / cam_str

    results = {
        'camera': cam_str,
        'data_type': data_type,
        'source': source,
        'valid': True,
        'issues': []
    }

    # Check if directories exist
    if not new_cam_dir.exists():
        results['valid'] = False
        results['issues'].append(f"New extraction missing: {cam_str}")
        return results

    if not ref_cam_dir.exists():
        results['valid'] = False
        results['issues'].append(f"Reference missing: {cam_str}")
        return results

    # Get file lists
    if data_type == 'images':
        pattern = 'frame_*.jpg'
    elif data_type == 'masks':
        pattern = 'frame_*.png'
    else:
        pattern = '*'

    new_files = sorted(new_cam_dir.glob(pattern))
    ref_files = sorted(ref_cam_dir.glob(pattern))

    # Check file counts
    if len(new_files) != len(ref_files):
        results['valid'] = False
        results['issues'].append(f"File count mismatch: {len(new_files)} vs {len(ref_files)}")
        return results

    results['file_count'] = len(new_files)

    # Sample comparison - check first, middle, last, and a few random frames
    total_files = len(new_files)
    if total_files > 0:
        sample_indices = [0, total_files//2, total_files-1]  # First, middle, last

        # Add a few random samples
        if total_files > 10:
            sample_indices.extend(random.sample(range(1, total_files-1), min(5, total_files-2)))

        sample_indices = sorted(set(sample_indices))

        for idx in sample_indices:
            new_file = new_files[idx]
            ref_file = ref_files[idx]

            # Compare file sizes
            new_size = new_file.stat().st_size
            ref_size = ref_file.stat().st_size

            if new_size != ref_size:
                results['valid'] = False
                results['issues'].append(f"Size mismatch in {new_file.name}: {new_size} vs {ref_size}")

            # For images/masks, do pixel comparison on a subset
            if idx in [0, total_files//2, total_files-1]:  # Only detailed check on key frames
                if data_type in ['images', 'masks']:
                    identical, msg = compare_images(new_file, ref_file)
                    if not identical:
                        results['valid'] = False
                        results['issues'].append(f"{new_file.name}: {msg}")

    return results

def validate_metadata(new_dir, ref_dir):
    """Validate metadata files."""
    results = {'valid': True, 'issues': []}

    # Check calibration files
    new_calib = new_dir / 'from_anno' / 'calibration' / 'all_cameras.npy'
    ref_calib = ref_dir / 'from_anno' / 'calibration' / 'all_cameras.npy'

    if new_calib.exists() and ref_calib.exists():
        new_data = np.load(new_calib, allow_pickle=True).item()
        ref_data = np.load(ref_calib, allow_pickle=True).item()

        # Check our 20 cameras
        for cam_id in CAMERA_LIST:
            cam_str = f'{cam_id:02d}'
            if cam_str in new_data and cam_str in ref_data:
                # Compare calibration matrices
                for matrix_type in ['K', 'D', 'RT']:
                    if not np.allclose(new_data[cam_str][matrix_type],
                                     ref_data[cam_str][matrix_type],
                                     rtol=1e-5):
                        results['valid'] = False
                        results['issues'].append(f"Calibration mismatch for camera {cam_str}, matrix {matrix_type}")
            elif cam_str not in new_data:
                results['valid'] = False
                results['issues'].append(f"Missing calibration for camera {cam_str}")
    else:
        results['valid'] = False
        results['issues'].append("Calibration file missing")

    # Check audio
    new_audio = new_dir / 'from_raw' / 'audio' / 'audio.mp3'
    ref_audio = ref_dir / 'from_raw' / 'audio' / 'audio.mp3'

    if new_audio.exists() and ref_audio.exists():
        new_size = new_audio.stat().st_size
        ref_size = ref_audio.stat().st_size

        if abs(new_size - ref_size) > 100:  # Allow tiny differences
            results['valid'] = False
            results['issues'].append(f"Audio size mismatch: {new_size} vs {ref_size}")

    return results

def main():
    """Main validation function."""

    # Define paths
    new_extraction = Path('/ssd4/zhuoyuan/renderme360_temp/test_download/subjects/0026/s1_all')
    ref_extraction = Path('/ssd4/zhuoyuan/renderme360_temp/test_download/subjects/0026_60cams/s1_all')

    print("="*80)
    print("20-CAMERA EXTRACTION VALIDATION")
    print("="*80)
    print(f"New extraction (20 cameras): {new_extraction}")
    print(f"Reference (60 cameras):      {ref_extraction}")
    print(f"Cameras to validate: {CAMERA_LIST}")
    print("="*80)

    # Check if directories exist
    if not new_extraction.exists():
        print(f"❌ Error: New extraction not found at {new_extraction}")
        return 1

    if not ref_extraction.exists():
        print(f"❌ Error: Reference extraction not found at {ref_extraction}")
        print(f"   You may need to extract or copy the 60-camera version first.")
        return 1

    all_valid = True
    validation_results = {
        'extraction_path': str(new_extraction),
        'reference_path': str(ref_extraction),
        'cameras': CAMERA_LIST,
        'results': []
    }

    # 1. Validate metadata
    print("\n1. Validating metadata and calibration...")
    metadata_results = validate_metadata(new_extraction, ref_extraction)
    if metadata_results['valid']:
        print("   ✓ Metadata and calibration match")
    else:
        print("   ✗ Metadata validation failed:")
        for issue in metadata_results['issues']:
            print(f"     - {issue}")
        all_valid = False

    # 2. Validate images
    print("\n2. Validating images from RAW...")
    image_issues = []
    validated_count = 0

    for cam_id in CAMERA_LIST:
        result = validate_camera_data(new_extraction, ref_extraction, cam_id, 'images', 'from_raw')
        validation_results['results'].append(result)

        if result['valid']:
            validated_count += 1
        else:
            image_issues.extend(result['issues'])
            all_valid = False

    print(f"   ✓ Validated {validated_count}/{len(CAMERA_LIST)} cameras")
    if image_issues:
        print(f"   ✗ Issues found:")
        for issue in image_issues[:5]:  # Show first 5 issues
            print(f"     - {issue}")
        if len(image_issues) > 5:
            print(f"     ... and {len(image_issues)-5} more issues")

    # 3. Validate masks
    print("\n3. Validating masks from ANNO...")
    mask_issues = []
    validated_count = 0

    for cam_id in CAMERA_LIST:
        result = validate_camera_data(new_extraction, ref_extraction, cam_id, 'masks', 'from_anno')
        validation_results['results'].append(result)

        if result['valid']:
            validated_count += 1
        else:
            mask_issues.extend(result['issues'])
            all_valid = False

    print(f"   ✓ Validated {validated_count}/{len(CAMERA_LIST)} cameras")
    if mask_issues:
        print(f"   ✗ Issues found:")
        for issue in mask_issues[:5]:  # Show first 5 issues
            print(f"     - {issue}")
        if len(mask_issues) > 5:
            print(f"     ... and {len(mask_issues)-5} more issues")

    # 4. Save results
    results_file = Path('validation_results_20cam.json')
    with open(results_file, 'w') as f:
        json.dump(validation_results, f, indent=2)
    print(f"\n4. Detailed results saved to: {results_file}")

    # Final verdict
    print("\n" + "="*80)
    if all_valid:
        print("✅ VALIDATION PASSED: 20-camera extraction matches reference!")
    else:
        print("❌ VALIDATION FAILED: Some differences found (see details above)")
    print("="*80)

    return 0 if all_valid else 1

if __name__ == "__main__":
    sys.exit(main())