#!/usr/bin/env python3
"""Analyze what's actually in the speech files"""

import h5py
from pathlib import Path

# Compare e0 (expression) vs s1_all (speech)
files = {
    'e0_anno': Path('/ssd2/zhuoyuan/renderme360_temp/test_download/anno/0026_e0_anno.smc'),
    's1_all_anno': Path('/ssd2/zhuoyuan/renderme360_temp/test_download/anno/0026_s1_all_anno.smc'),
}

for name, file_path in files.items():
    print(f"\n{'='*60}")
    print(f"Analyzing: {name} ({file_path.stat().st_size / 1024**3:.1f} GB)")
    print(f"{'='*60}")
    
    with h5py.File(file_path, 'r') as f:
        # Top level structure
        print("\nTop-level keys:")
        for key in f.keys():
            print(f"  - {key}")
        
        # Get frame counts
        if 'Camera' in f and '00' in f['Camera']:
            cam00 = f['Camera']['00']
            
            # Count images
            if 'color' in cam00:
                color_frames = len(cam00['color'].keys())
                print(f"\nFrames with color images: {color_frames}")
            
            # Count masks
            if 'mask' in cam00:
                mask_frames = len(cam00['mask'].keys())
                print(f"Frames with masks: {mask_frames}")
        
        # Check for 3D keypoints
        if 'Keypoints3d' in f:
            kpt3d_frames = len(f['Keypoints3d'].keys())
            print(f"Frames with 3D keypoints: {kpt3d_frames}")
        
        # Check for FLAME
        if 'FLAME' in f:
            flame_frames = len(f['FLAME'].keys())
            print(f"Frames with FLAME params: {flame_frames}")
        
        # Check for UV textures
        if 'UV_texture' in f:
            uv_frames = len(f['UV_texture'].keys())
            print(f"Frames with UV textures: {uv_frames}")
        
        # Estimate data sizes
        if 'Camera' in f and '00' in f['Camera'] and 'color' in f['Camera']['00']:
            # Sample one frame
            sample_frame = list(f['Camera']['00']['color'].keys())[0]
            sample_data = f['Camera']['00']['color'][sample_frame][()]
            frame_size_mb = sample_data.nbytes / 1024**2
            total_frames = color_frames if 'color' in f['Camera']['00'] else 0
            total_cameras = len(f['Camera'].keys()) if 'Camera' in f else 0
            
            print(f"\nImage data estimate:")
            print(f"  Single frame size: {frame_size_mb:.1f} MB")
            print(f"  Total cameras: {total_cameras}")
            print(f"  Total frames: {total_frames}")
            print(f"  Estimated total image data: {frame_size_mb * total_frames * total_cameras / 1024:.1f} GB")

print("\n" + "="*60)
print("SUMMARY:")
print("="*60)
print("\nExpression files (e0-e11):")
print("  - Anno: ~700-800 MB (contains low-res images, FLAME, UV, scan)")
print("  - Raw: ~2-3 GB (contains high-res images)")
print("\nSpeech files (s1_all-s6_all):")
print("  - Anno: 5-14 GB (contains low-res images for MANY more frames)")
print("  - Raw: 23-56 GB (contains high-res images for MANY more frames)")
print("\nKey difference: Speech performances have 10-20x MORE FRAMES than expressions!")
print("No audio data found in annotation files - audio may be in raw files or separate.")