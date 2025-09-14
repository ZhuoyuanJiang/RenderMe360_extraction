#!/usr/bin/env python3
"""
[LEGACY - INCOMPLETE] FULL EXTRACTION Script for RenderMe360 Subject 0026

Status: Does not extract masks - produces incomplete extraction
Issue: Missing mask extraction logic results in incomplete dataset
Recommendation: Use extract_0026_FULL_both.py or extract_subject_FULL_both.py instead
Note: Kept for historical reference only

WARNING: This will extract EVERYTHING EXCEPT masks and require 200-500GB of storage!
"""

import os
import sys
import cv2
import numpy as np
from pathlib import Path
from renderme_360_reader import SMCReader
import json
from datetime import datetime
from tqdm import tqdm
import argparse

def extract_full_performance(anno_file, raw_file, output_dir, separate_sources=True):
    """
    Extract EVERYTHING from both anno and raw files
    
    This extracts:
    - All 60 camera views
    - All frames
    - All data types
    
    Args:
        separate_sources: If True, creates separate folders for anno and raw data
    """
    
    print(f"\n{'='*60}")
    print(f"FULL EXTRACTION")
    print(f"Anno: {anno_file.name}")
    print(f"Raw: {raw_file.name if raw_file and raw_file.exists() else 'Not available'}")
    print(f"Output: {output_dir}")
    print(f"Separate sources: {separate_sources}")
    print(f"{'='*60}")
    
    # Check if extraction is already complete
    completion_marker = output_dir / '.extraction_complete'
    if completion_marker.exists():
        print(f"\n✓ Performance already fully extracted at {output_dir}")
        print(f"  To re-extract, delete {completion_marker}")
        return output_dir
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create separate output directories if requested
    if separate_sources:
        anno_output = output_dir / 'from_anno'
        raw_output = output_dir / 'from_raw'
        anno_output.mkdir(exist_ok=True)
        raw_output.mkdir(exist_ok=True)
    else:
        # Original behavior - everything in one folder
        anno_output = output_dir
        raw_output = output_dir
    
    # Initialize readers
    anno_reader = SMCReader(str(anno_file))
    raw_reader = SMCReader(str(raw_file)) if raw_file and raw_file.exists() else None
    
    # Get info
    camera_info = anno_reader.get_Camera_info()
    actor_info = anno_reader.get_actor_info()
    
    total_frames = camera_info['num_frame']
    total_cameras = camera_info['num_device']
    
    print(f"\nDataset Size:")
    print(f"  Cameras: {total_cameras}")
    print(f"  Frames: {total_frames}")
    print(f"  Total images: {total_cameras * total_frames:,}")
    print(f"  Estimated size: ~{total_cameras * total_frames * 5 / 1024:.1f} GB")
    
    # Save metadata (from anno)
    metadata_dir = anno_output / 'metadata'
    metadata_dir.mkdir(exist_ok=True)
    
    # Convert numpy types to Python native types for JSON serialization
    def convert_numpy_types(obj):
        """Recursively convert numpy types to native Python types"""
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, dict):
            return {key: convert_numpy_types(val) for key, val in obj.items()}
        elif isinstance(obj, list):
            return [convert_numpy_types(item) for item in obj]
        else:
            return obj
    
    metadata = {
        'subject_id': anno_reader.actor_id,
        'performance': anno_reader.performance_part,
        'actor_info': convert_numpy_types(actor_info),
        'camera_info': convert_numpy_types(camera_info),
        'capture_date': anno_reader.capture_date,
        'total_frames': int(total_frames),
        'total_cameras': int(total_cameras),
        'extraction_date': datetime.now().isoformat(),
        'extraction_mode': 'FULL',
        'data_source': 'anno'
    }
    
    with open(metadata_dir / 'info.json', 'w') as f:
        json.dump(metadata, f, indent=2)
    
    # Also save a summary at root level
    if separate_sources:
        with open(output_dir / 'extraction_info.txt', 'w') as f:
            f.write("SEPARATED EXTRACTION RESULTS\n")
            f.write("="*40 + "\n\n")
            f.write("from_anno/: Data from annotation file\n")
            f.write("  - Calibration matrices\n")
            f.write("  - Keypoints (2D and 3D)\n")
            f.write("  - FLAME parameters (expression performances only)\n")
            f.write("  - UV textures (expression performances only)\n")
            f.write("  - Scan mesh (expression performances only)\n")
            f.write("  - Scan masks (expression performances only)\n\n")
            f.write("from_raw/: Data from raw file\n")
            f.write("  - High-resolution images\n")
            f.write("  - High-resolution masks\n")
            f.write("  - Audio (speech performances only)\n")
    
    # 1. Extract calibration (from anno)
    print("\n1. Extracting calibration from ANNO...")
    calib_dir = anno_output / 'calibration'
    calib_dir.mkdir(exist_ok=True)
    
    all_calibs = anno_reader.get_Calibration_all()
    np.save(calib_dir / 'all_cameras.npy', all_calibs)
    
    # Save individual calibrations too
    for cam_id in range(total_cameras):
        calib = anno_reader.get_Calibration(f'{cam_id:02d}')
        if calib:
            np.save(calib_dir / f'cam_{cam_id:02d}.npy', calib)
    
    print(f"   ✓ Saved calibration for {total_cameras} cameras")
    
    # 2. Extract audio (from raw, if available)
    # Note: Audio is stored in RAW files for speech performances, not anno files
    if 's' in anno_reader.performance_part and raw_reader:
        print("\n2. Extracting audio from RAW file...")
        audio_dir = raw_output / 'audio'  # Put in raw_output since it comes from raw file
        
        try:
            audio_data = raw_reader.get_audio()  # Fixed: Use raw_reader instead of anno_reader
            if audio_data:
                audio_dir.mkdir(exist_ok=True)
                sr = int(np.array(audio_data['sample_rate']))
                audio_array = np.array(audio_data['audio'])
                raw_reader.writemp3(str(audio_dir / 'audio.mp3'), sr, audio_array, normalized=True)
                np.savez(audio_dir / 'audio_data.npz', audio=audio_array, sample_rate=sr)
                print(f"   ✓ Audio: {audio_array.shape[0]/sr:.1f} seconds")
        except (KeyError, Exception) as e:
            print(f"   ⚠ No audio data found in raw file")
            # Don't create empty audio directory if no audio
            pass
    
    # 3. Extract all images and masks (from raw if available, else from anno)
    if raw_reader:
        print("\n3. Extracting ALL images and masks from RAW file...")
        print("   This will take a LONG time and use significant storage!")
        
        for cam_id in tqdm(range(total_cameras), desc="Cameras"):
            cam_str = f'{cam_id:02d}'
            
            # Create camera-specific directories IN RAW OUTPUT
            img_dir = raw_output / 'images' / f'cam_{cam_str}'
            mask_dir = raw_output / 'masks' / f'cam_{cam_str}'
            
            # Check if this camera's data already exists
            existing_images = len(list(img_dir.glob('frame_*.jpg'))) if img_dir.exists() else 0
            existing_masks = len(list(mask_dir.glob('frame_*.png'))) if mask_dir.exists() else 0
            
            if existing_images >= total_frames and existing_masks >= total_frames:
                # print(f"   Skipping cam_{cam_str} - already extracted")
                continue
            
            img_dir.mkdir(parents=True, exist_ok=True)
            mask_dir.mkdir(parents=True, exist_ok=True)
            
            for frame_id in range(total_frames):
                # Skip if both files already exist
                img_path = img_dir / f'frame_{frame_id:06d}.jpg'
                mask_path = mask_dir / f'frame_{frame_id:06d}.png'
                
                if img_path.exists() and mask_path.exists():
                    continue
                    
                try:
                    # Color image
                    if not img_path.exists():
                        img = raw_reader.get_img(cam_str, 'color', frame_id)
                        cv2.imwrite(str(img_path), img, [cv2.IMWRITE_JPEG_QUALITY, 95])
                except Exception as e:
                    if "Invalid Image_type" not in str(e):
                        print(f"\n   Error cam{cam_str} frame{frame_id} (color): {e}")
                
                try:
                    # Mask - may not be available for all performances
                    if not mask_path.exists():
                        mask = raw_reader.get_img(cam_str, 'mask', frame_id)
                        cv2.imwrite(str(mask_path), mask)
                except Exception as e:
                    # Silently skip mask errors as they may not be available
                    if "Invalid Image_type" not in str(e):
                        print(f"\n   Error cam{cam_str} frame{frame_id} (mask): {e}")
    else:
        print("\n3. No raw file available, extracting sample images from ANNO (lower resolution)...")
        
        # If no raw file, put low-res images in anno folder
        img_dir = anno_output / 'images_lowres'
        img_dir.mkdir(exist_ok=True)
        
        for cam_id in tqdm(range(min(4, total_cameras)), desc="Sample Cameras"):
            cam_str = f'{cam_id:02d}'
            
            for frame_id in range(min(10, total_frames)):
                try:
                    img = anno_reader.get_img(cam_str, 'color', frame_id)
                    img_path = img_dir / f'cam{cam_str}_frame{frame_id:04d}.jpg'
                    cv2.imwrite(str(img_path), img)
                except:
                    pass
    
    # 4. Extract all keypoints (from anno)
    print("\n4. Extracting all keypoints from ANNO...")
    
    # 2D keypoints (cameras 18-32 have them)
    kpt2d_dir = anno_output / 'keypoints2d'
    kpt2d_dir.mkdir(exist_ok=True)
    
    for cam_id in tqdm(range(18, min(33, total_cameras)), desc="2D Keypoints"):
        cam_str = f'{cam_id:02d}'
        cam_kpts = {}
        
        # Sample every 10 frames to avoid massive files
        for frame_id in range(0, total_frames, 10):
            try:
                kpt = anno_reader.get_Keypoints2d(cam_str, frame_id)
                if kpt is not None:
                    cam_kpts[f'frame_{frame_id}'] = kpt
            except:
                pass
        
        if cam_kpts:
            np.savez_compressed(kpt2d_dir / f'cam_{cam_str}.npz', **cam_kpts)
    
    # 3D keypoints (from anno)
    kpt3d_dir = anno_output / 'keypoints3d'
    kpt3d_dir.mkdir(exist_ok=True)
    
    kpts3d = {}
    for frame_id in tqdm(range(0, total_frames, 10), desc="3D Keypoints"):
        try:
            kpt = anno_reader.get_Keypoints3d(frame_id)
            if kpt is not None:
                kpts3d[f'frame_{frame_id}'] = kpt
        except:
            pass
    
    if kpts3d:
        np.savez_compressed(kpt3d_dir / 'all_frames.npz', **kpts3d)
        print(f"   ✓ 3D keypoints: {len(kpts3d)} frames")
    
    # 5. Extract FLAME (from anno, for expressions)
    if 'e' in anno_reader.performance_part:
        print("\n5. Extracting FLAME parameters from ANNO...")
        flame_dir = anno_output / 'flame'
        flame_dir.mkdir(exist_ok=True)
        
        flame_data = {}
        for frame_id in tqdm(range(0, total_frames, 5), desc="FLAME"):
            try:
                flame = anno_reader.get_FLAME(frame_id)
                if flame:
                    flame_data[f'frame_{frame_id}'] = flame
            except:
                pass
        
        if flame_data:
            np.savez_compressed(flame_dir / 'all_frames.npz', **flame_data)
            print(f"   ✓ FLAME: {len(flame_data)} frames")
        
        # UV textures (from anno)
        print("\n6. Extracting UV textures from ANNO...")
        uv_dir = anno_output / 'uv_textures'
        uv_dir.mkdir(exist_ok=True)
        
        for frame_id in tqdm(range(0, total_frames, 30), desc="UV"):
            try:
                uv = anno_reader.get_uv(frame_id)
                if uv is not None:
                    cv2.imwrite(str(uv_dir / f'frame_{frame_id:06d}.jpg'), uv,
                              [cv2.IMWRITE_JPEG_QUALITY, 90])
            except:
                pass
        
        # Scan mesh (from anno)
        print("\n7. Extracting scan mesh from ANNO...")
        try:
            scan = anno_reader.get_scanmesh()
            if scan:
                scan_dir = anno_output / 'scan'
                scan_dir.mkdir(exist_ok=True)
                
                # Check if plyfile is installed
                try:
                    import plyfile
                    anno_reader.write_ply(scan, str(scan_dir / 'mesh.ply'))
                    print(f"   ✓ Scan: {scan['vertex'].shape[0]} vertices")
                except ImportError:
                    print(f"   ⚠ plyfile not installed. Run: pip install plyfile")
                    print(f"     Scan mesh data exists but cannot be saved without plyfile")
        except Exception as e:
            print(f"   ⚠ Could not extract scan mesh: {e}")
        
        # Scan masks (from anno)
        print("\n8. Extracting scan masks from ANNO...")
        scanmask_dir = anno_output / 'scan_masks'
        scanmask_dir.mkdir(exist_ok=True)
        
        for cam_id in tqdm(range(total_cameras), desc="Scan masks"):
            try:
                mask = anno_reader.get_scanmask(f'{cam_id:02d}')
                if mask is not None:
                    cv2.imwrite(str(scanmask_dir / f'cam_{cam_id:02d}.png'), mask)
            except:
                pass
    
    # Calculate final sizes
    if separate_sources:
        anno_size = sum(f.stat().st_size for f in anno_output.rglob('*') if f.is_file())
        raw_size = sum(f.stat().st_size for f in raw_output.rglob('*') if f.is_file()) if raw_output.exists() else 0
        total_size = anno_size + raw_size
        
        print(f"\n{'='*60}")
        print(f"EXTRACTION COMPLETE!")
        print(f"Output: {output_dir}")
        print(f"Anno data size: {anno_size / (1024**3):.2f} GB")
        print(f"Raw data size: {raw_size / (1024**3):.2f} GB")
        print(f"Total size: {total_size / (1024**3):.2f} GB")
        print(f"{'='*60}")
        
        # Save size summary
        with open(output_dir / 'size_summary.txt', 'w') as f:
            f.write(f"Extraction Size Summary\n")
            f.write(f"="*40 + "\n\n")
            f.write(f"Anno data (from_anno/): {anno_size / (1024**3):.2f} GB\n")
            f.write(f"Raw data (from_raw/): {raw_size / (1024**3):.2f} GB\n")
            f.write(f"Total: {total_size / (1024**3):.2f} GB\n")
    else:
        total_size = sum(f.stat().st_size for f in output_dir.rglob('*') if f.is_file())
        
        print(f"\n{'='*60}")
        print(f"EXTRACTION COMPLETE!")
        print(f"Output: {output_dir}")
        print(f"Total size: {total_size / (1024**3):.2f} GB")
        print(f"{'='*60}")
    
    # Mark extraction as complete
    completion_marker = output_dir / '.extraction_complete'
    with open(completion_marker, 'w') as f:
        f.write(f"Extraction completed at {datetime.now().isoformat()}\n")
        f.write(f"Performance: {anno_reader.performance_part}\n")
        f.write(f"Total size: {total_size / (1024**3):.2f} GB\n")
    
    return output_dir

def main():
    parser = argparse.ArgumentParser(description='Full extraction of RenderMe360 data')
    parser.add_argument('--performance', type=str, default='e0',
                      help='Performance to extract (e0, s1_all, etc.)')
    parser.add_argument('--output', type=str, 
                      default='/ssd2/zhuoyuan/renderme360_temp/FULL_EXTRACTION',
                      help='Output directory')
    parser.add_argument('--separate', action='store_true', default=True,
                      help='Separate anno and raw data into different folders (default: True)')
    parser.add_argument('--combine', action='store_true',
                      help='Combine anno and raw data in same folders (legacy behavior)')
    args = parser.parse_args()
    
    # Paths
    anno_dir = Path('/ssd2/zhuoyuan/renderme360_temp/test_download/anno')
    raw_dir = Path('/ssd2/zhuoyuan/renderme360_temp/test_download/raw/0026')
    
    # Files for the specified performance
    perf = args.performance
    anno_file = anno_dir / f'0026_{perf}_anno.smc'
    raw_file = raw_dir / f'0026_{perf}_raw.smc'
    output_dir = Path(args.output) / f'0026_{perf}'
    
    if not anno_file.exists():
        print(f"Error: Anno file not found: {anno_file}")
        sys.exit(1)
    
    # Determine separation mode
    separate_sources = not args.combine  # Default is to separate
    
    print("="*60)
    print("RenderMe360 FULL EXTRACTION")
    print("WARNING: This will extract EVERYTHING!")
    print(f"Performance: {perf}")
    print(f"Separation mode: {'SEPARATE folders' if separate_sources else 'COMBINED folder'}")
    print(f"Estimated size: 10-50 GB depending on performance")
    print("="*60)
    
    if separate_sources:
        print("\nOutput structure will be:")
        print(f"  {output_dir}/")
        print(f"    ├── from_anno/   # Data from annotation file")
        print(f"    └── from_raw/    # Data from raw file")
    
    response = input("\nAre you sure you want to proceed? (yes/no): ")
    if response.lower() != 'yes':
        print("Extraction cancelled.")
        sys.exit(0)
    
    extract_full_performance(anno_file, raw_file, output_dir, separate_sources=separate_sources)

if __name__ == '__main__':
    main()