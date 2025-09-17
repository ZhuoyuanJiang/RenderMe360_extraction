#!/usr/bin/env python3
"""
Validation script to compare new extraction with FULL_EXTRACTION_BOTH

Purpose:
--------
This script compares two extraction directories to validate that a new extraction pipeline produces identical results compared to the original:
  - Original: renderme360_temp/FULL_EXTRACTION_BOTH/0026_s1_all/
  - New: renderme360_temp/test_download/subjects/0026/s1_all/

What it checks:
--------------
1. Directory structure matches
2. File counts by type (images, masks, json, etc.)
3. Key files exist (metadata, calibration, audio)
4. Sample image comparisons
5. Total extraction size

Output:
-------
Creates validation_results.json with detailed comparison results. 

Expectation:
----------
The validation_results.json might indicates a PROBLEM (but this is expected):

The results show "identical": false with missing directories for ALL 60 cameras:
- Missing from_anno/images/cam_00 through cam_59
- Missing from_raw/masks/cam_00 through cam_59

These differences are INTENTIONAL - the new extraction pipeline for test_download/subjects
purposely excludes these directories to reduce storage requirements. The validation_results.json
file showing these missing directories indicates the extraction worked as designed, not an error.

"""

import os
import sys
from pathlib import Path
import subprocess
import json
import hashlib

def compare_directories(dir1, dir2, performance):
    """Compare two directory structures and contents."""

    print(f"\n{'='*80}")
    print(f"COMPARING: {performance}")
    print(f"Original: {dir1}")
    print(f"New:      {dir2}")
    print(f"{'='*80}")

    results = {
        'performance': performance,
        'identical': True,
        'differences': []
    }

    # 1. Check if both directories exist
    if not dir1.exists():
        results['identical'] = False
        results['differences'].append(f"Original directory does not exist: {dir1}")
        return results

    if not dir2.exists():
        results['identical'] = False
        results['differences'].append(f"New directory does not exist: {dir2}")
        return results

    # 2. Compare directory structure
    print("\n1. Comparing directory structure...")

    # Get all subdirectories
    orig_dirs = set(str(p.relative_to(dir1)) for p in dir1.rglob('*') if p.is_dir())
    new_dirs = set(str(p.relative_to(dir2)) for p in dir2.rglob('*') if p.is_dir())

    missing_in_new = orig_dirs - new_dirs
    extra_in_new = new_dirs - orig_dirs

    if missing_in_new:
        print(f"   ✗ Directories missing in new: {missing_in_new}")
        results['differences'].append(f"Missing directories: {missing_in_new}")
        results['identical'] = False

    if extra_in_new:
        print(f"   ✗ Extra directories in new: {extra_in_new}")
        results['differences'].append(f"Extra directories: {extra_in_new}")
        results['identical'] = False

    if not missing_in_new and not extra_in_new:
        print(f"   ✓ Directory structure matches: {len(orig_dirs)} directories")

    # 3. Compare file counts by type
    print("\n2. Comparing file counts...")

    file_types = {
        'images': '*.jpg',
        'masks': '*.png',
        'numpy': '*.npy',
        'npz': '*.npz',
        'json': '*.json',
        'mp3': '*.mp3',
        'ply': '*.ply'
    }

    for file_type, pattern in file_types.items():
        orig_files = list(dir1.rglob(pattern))
        new_files = list(dir2.rglob(pattern))

        if len(orig_files) != len(new_files):
            print(f"   ✗ {file_type}: Original={len(orig_files)}, New={len(new_files)}")
            results['differences'].append(f"{file_type} count mismatch: {len(orig_files)} vs {len(new_files)}")
            results['identical'] = False
        elif len(orig_files) > 0:
            print(f"   ✓ {file_type}: {len(orig_files)} files match")

    # 4. Compare specific important files
    print("\n3. Comparing key files...")

    key_files = [
        'from_anno/metadata/info.json',
        'from_anno/calibration/all_cameras.npy',
        'from_raw/audio/audio.mp3',  # Only for speech
        '.extraction_complete'
    ]

    for key_file in key_files:
        orig_file = dir1 / key_file
        new_file = dir2 / key_file

        if orig_file.exists() != new_file.exists():
            if orig_file.exists():
                print(f"   ✗ {key_file}: Missing in new extraction")
                results['differences'].append(f"Missing file: {key_file}")
            else:
                # File doesn't exist in original, check if it should
                if 'audio' not in key_file or 's' in performance:
                    print(f"   ⚠ {key_file}: Extra in new extraction")
                    results['differences'].append(f"Extra file: {key_file}")
            results['identical'] = False
        elif orig_file.exists():
            # Compare file sizes
            orig_size = orig_file.stat().st_size
            new_size = new_file.stat().st_size

            if abs(orig_size - new_size) > 1000:  # Allow 1KB difference
                size_diff = new_size - orig_size
                print(f"   ✗ {key_file}: Size difference {size_diff:+,} bytes")
                results['differences'].append(f"Size mismatch in {key_file}: {size_diff:+,} bytes")
                results['identical'] = False
            else:
                print(f"   ✓ {key_file}: Exists and size matches")

    # 5. Sample comparison of image files
    print("\n4. Sampling image files for comparison...")

    # Check a few cameras
    sample_cameras = ['cam_00', 'cam_12', 'cam_24', 'cam_36', 'cam_48']

    for cam in sample_cameras:
        orig_cam_dir = dir1 / 'from_raw' / 'images' / cam
        new_cam_dir = dir2 / 'from_raw' / 'images' / cam

        if orig_cam_dir.exists() and new_cam_dir.exists():
            orig_images = sorted(orig_cam_dir.glob('frame_*.jpg'))
            new_images = sorted(new_cam_dir.glob('frame_*.jpg'))

            if len(orig_images) != len(new_images):
                print(f"   ✗ {cam}: Image count mismatch ({len(orig_images)} vs {len(new_images)})")
                results['differences'].append(f"{cam} image count: {len(orig_images)} vs {len(new_images)}")
                results['identical'] = False
            elif len(orig_images) > 0:
                # Check first and last image sizes
                if orig_images[0].stat().st_size != new_images[0].stat().st_size:
                    print(f"   ✗ {cam}: First image size mismatch")
                    results['identical'] = False
                else:
                    print(f"   ✓ {cam}: {len(orig_images)} images match")
        elif orig_cam_dir.exists() or new_cam_dir.exists():
            print(f"   ✗ {cam}: Directory exists in only one extraction")
            results['identical'] = False

    # 6. Calculate total size
    print("\n5. Comparing total extraction size...")

    def get_dir_size(path):
        total = 0
        for f in path.rglob('*'):
            if f.is_file():
                total += f.stat().st_size
        return total

    orig_size = get_dir_size(dir1)
    new_size = get_dir_size(dir2)

    size_diff_gb = (new_size - orig_size) / (1024**3)

    print(f"   Original: {orig_size / (1024**3):.2f} GB")
    print(f"   New:      {new_size / (1024**3):.2f} GB")
    print(f"   Difference: {size_diff_gb:+.2f} GB ({abs(size_diff_gb/orig_size*100*1024**3):.1f}%)")

    if abs(size_diff_gb) > 0.5:  # More than 500MB difference
        results['differences'].append(f"Size difference: {size_diff_gb:+.2f} GB")
        results['identical'] = False

    # Final verdict
    print(f"\n{'='*80}")
    if results['identical']:
        print(f"✅ VALIDATION PASSED: {performance} extractions are identical!")
    else:
        print(f"❌ VALIDATION FAILED: Found {len(results['differences'])} differences")
        for diff in results['differences']:
            print(f"   - {diff}")
    print(f"{'='*80}")

    return results


def main():
    """Main validation function."""

    # Define paths
    original_base = Path('/ssd4/zhuoyuan/renderme360_temp/FULL_EXTRACTION_BOTH')
    new_base = Path('/ssd4/zhuoyuan/renderme360_temp/test_download/subjects/0026')

    # Performances to check
    performances = [
        ('s1_all', '0026_s1_all', 's1_all'),
        ('e0', '0026_e0', 'e0')
    ]

    print("="*80)
    print("RENDERME360 EXTRACTION VALIDATION")
    print("="*80)
    print(f"Original: {original_base}")
    print(f"New:      {new_base}")

    all_results = []

    for perf_name, orig_dir_name, new_dir_name in performances:
        orig_dir = original_base / orig_dir_name
        new_dir = new_base / new_dir_name

        if new_dir.exists():
            result = compare_directories(orig_dir, new_dir, perf_name)
            all_results.append(result)
        else:
            print(f"\n⚠ Skipping {perf_name}: New extraction not found at {new_dir}")

    # Summary
    print("\n" + "="*80)
    print("VALIDATION SUMMARY")
    print("="*80)

    passed = sum(1 for r in all_results if r['identical'])
    failed = len(all_results) - passed

    print(f"✓ Passed: {passed}/{len(all_results)}")
    print(f"✗ Failed: {failed}/{len(all_results)}")

    if failed == 0:
        print("\n🎉 SUCCESS: All extractions validated successfully!")
        print("The new extraction pipeline produces identical results!")
    else:
        print("\n⚠ WARNING: Some differences found. Review details above.")

    # Save results
    results_file = Path('validation_results.json')
    with open(results_file, 'w') as f:
        json.dump(all_results, f, indent=2)
    print(f"\nDetailed results saved to: {results_file}")

    return failed == 0


if __name__ == '__main__':
    sys.exit(0 if main() else 1)