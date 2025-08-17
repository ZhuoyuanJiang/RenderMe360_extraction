#!/usr/bin/env python3
"""
Quick exploration script for RenderMe360 Subject 0026
This script provides a quick overview of available data without full extraction
"""

import sys
from pathlib import Path
from renderme_360_reader import SMCReader
import numpy as np

def explore_smc_file(smc_path):
    """Quick exploration of a single SMC file"""
    
    print(f"\n{'='*60}")
    print(f"Exploring: {smc_path.name}")
    print(f"File size: {smc_path.stat().st_size / (1024**3):.2f} GB")
    print(f"{'='*60}")
    
    reader = SMCReader(str(smc_path))
    
    # Basic info
    print(f"\n📊 Basic Information:")
    print(f"  Actor ID: {reader.actor_id}")
    print(f"  Performance: {reader.performance_part}")
    print(f"  Capture Date: {reader.capture_date}")
    print(f"  Actor Info: {reader.get_actor_info()}")
    
    camera_info = reader.get_Camera_info()
    print(f"\n📷 Camera Information:")
    print(f"  Number of cameras: {camera_info['num_device']}")
    print(f"  Number of frames: {camera_info['num_frame']}")
    print(f"  Resolution: {camera_info['resolution']}")
    
    # Check available data types
    print(f"\n✅ Available Data Types:")
    
    # Check for images
    try:
        test_img = reader.get_img('00', 'color', 0)
        print(f"  ✓ Color images: {test_img.shape}")
    except:
        print(f"  ✗ Color images: Not available")
    
    try:
        test_mask = reader.get_img('00', 'mask', 0)
        print(f"  ✓ Masks: {test_mask.shape}")
    except:
        print(f"  ✗ Masks: Not available")
    
    # Check for audio (speech performances)
    if 's' in reader.performance_part:
        try:
            audio = reader.get_audio()
            if audio:
                print(f"  ✓ Audio: shape={audio['audio'].shape}, rate={audio['sample_rate']}")
        except:
            print(f"  ✗ Audio: Not available")
    
    # Check for keypoints
    try:
        kpt2d = reader.get_Keypoints2d('25', 0)
        if kpt2d is not None:
            print(f"  ✓ 2D Keypoints: {kpt2d.shape}")
    except:
        print(f"  ✗ 2D Keypoints: Not available")
    
    try:
        kpt3d = reader.get_Keypoints3d(0)
        if kpt3d is not None:
            print(f"  ✓ 3D Keypoints: {kpt3d.shape}")
    except:
        print(f"  ✗ 3D Keypoints: Not available")
    
    # Check for FLAME (expression performances)
    if 'e' in reader.performance_part:
        try:
            flame = reader.get_FLAME(0)
            if flame:
                print(f"  ✓ FLAME parameters: {len(flame)} components")
                print(f"    - Vertices shape: {flame['verts'].shape}")
        except:
            print(f"  ✗ FLAME: Not available")
        
        try:
            uv = reader.get_uv(0)
            if uv is not None:
                print(f"  ✓ UV texture: {uv.shape}")
        except:
            print(f"  ✗ UV texture: Not available")
        
        try:
            scan = reader.get_scanmesh()
            if scan:
                print(f"  ✓ Scan mesh: vertices={scan['vertex'].shape}, faces={scan['vertex_indices'].shape}")
        except:
            print(f"  ✗ Scan mesh: Not available")
    
    # Memory usage estimate
    print(f"\n💾 Estimated Data Volume:")
    if camera_info:
        img_size = 2048 * 2448 * 3  # bytes per image
        total_imgs = camera_info['num_device'] * camera_info['num_frame']
        est_size = (total_imgs * img_size) / (1024**3)
        print(f"  Raw images only: ~{est_size:.1f} GB")
        print(f"  Total frames: {total_imgs:,}")

def main():
    # Define paths
    anno_dir = Path('/ssd2/zhuoyuan/renderme360_temp/test_download/anno')
    raw_dir = Path('/ssd2/zhuoyuan/renderme360_temp/test_download/raw/0026')
    
    print("="*60)
    print("RenderMe360 Quick Explorer - Subject 0026")
    print("="*60)
    
    # Get all files for subject 0026
    anno_files = sorted(anno_dir.glob('0026_*_anno.smc'))
    raw_files = sorted(raw_dir.glob('0026_*_raw.smc'))
    
    print(f"\n📁 Available Files:")
    print(f"\nAnnotation files ({len(anno_files)}):")
    for f in anno_files:
        size_gb = f.stat().st_size / (1024**3)
        print(f"  - {f.name}: {size_gb:.2f} GB")
    
    print(f"\nRaw files ({len(raw_files)}):")
    for f in raw_files:
        size_gb = f.stat().st_size / (1024**3)
        print(f"  - {f.name}: {size_gb:.2f} GB")
    
    # Explore different performance types
    print("\n" + "="*60)
    print("PERFORMANCE TYPES EXPLANATION:")
    print("="*60)
    print("  - e0-e11: Expression performances (with FLAME, UV, scan)")
    print("  - s1-s4: Speech performances (with audio)")
    print("  - h0: Head movement performance")
    
    # Explore one of each type
    sample_files = [
        anno_dir / '0026_e0_anno.smc',  # Expression
        anno_dir / '0026_s1_all_anno.smc',  # Speech
        anno_dir / '0026_h0_anno.smc',  # Head movement
    ]
    
    for smc_file in sample_files:
        if smc_file.exists():
            try:
                explore_smc_file(smc_file)
            except Exception as e:
                print(f"Error exploring {smc_file.name}: {e}")
    
    print("\n" + "="*60)
    print("USAGE TIPS:")
    print("="*60)
    print("1. anno files: Contain processed annotations (keypoints, FLAME, etc.)")
    print("2. raw files: Contain raw camera images and masks")
    print("3. Use anno files for annotations, raw files for full-res images")
    print("4. Each performance has different data:")
    print("   - Expression (e*): FLAME, UV texture, scan mesh")
    print("   - Speech (s*): Audio data")
    print("   - All: Images, masks, keypoints, calibration")

if __name__ == '__main__':
    main()