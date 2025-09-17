#!/usr/bin/env python3
"""
[LEGACY] FULL EXTRACTION Script for RenderMe360 Subject 0026 - SMART VERSION

Status: Working but superseded by extract_subject_FULL_both.py
Use Case: Quick local testing when SMC files are pre-downloaded
Requires: SMC files in /ssd4/zhuoyuan/renderme360_temp/test_download/[anno|raw]/
Note: Hardcoded for subject 0026 only. For flexible extraction, use extract_subject_FULL_both.py

This version checks both anno and raw files for all data types to ensure nothing is missed.
WARNING: This will extract EVERYTHING and require 200-500GB of storage!
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

def try_extract_data(reader, data_type, *args):
    """
    Safely try to extract data from a reader, returning None if it fails
    """
    if reader is None:
        return None
    
    try:
        if data_type == 'audio':
            return reader.get_audio()
        elif data_type == 'flame':
            return reader.get_FLAME(*args)
        elif data_type == 'uv':
            return reader.get_uv(*args)
        elif data_type == 'scanmesh':
            return reader.get_scanmesh()
        elif data_type == 'scanmask':
            return reader.get_scanmask(*args)
        elif data_type == 'keypoints2d':
            return reader.get_Keypoints2d(*args)
        elif data_type == 'keypoints3d':
            return reader.get_Keypoints3d(*args)
        elif data_type == 'calibration':
            return reader.get_Calibration(*args)
        elif data_type == 'image':
            return reader.get_Image(*args)
        elif data_type == 'mask':
            return reader.get_mask(*args)
    except Exception as e:
        return None
    
    return None

# NOTE: Removed extract_data_smart() - we now check both sources independently
# to ensure we extract EVERYTHING from both files when available

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
            f.write("  - Metadata (actor info, camera info)\n")
            f.write("  - Keypoints (2D and 3D)\n")
            f.write("  - Masks (segmentation masks for all frames)\n")
            f.write("  - FLAME parameters (expression performances only)\n")
            f.write("  - UV textures (expression performances only)\n")
            f.write("  - Scan mesh (expression performances only)\n")
            f.write("  - Scan masks (expression performances only)\n\n")
            f.write("from_raw/: Data from raw file\n")
            f.write("  - High-resolution images\n")
            f.write("  - Audio (speech performances only)\n")
            f.write("\nNote: Only folders with actual data will be created.\n")
    
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
    
    # 2. Extract audio (check BOTH anno and raw independently)
    if 's' in anno_reader.performance_part:
        print("\n2. Extracting audio (checking both files)...")
        audio_found = []
        
        # Check anno file for audio
        anno_audio = try_extract_data(anno_reader, 'audio')
        if anno_audio:
            audio_dir = anno_output / 'audio'
            audio_dir.mkdir(exist_ok=True)
            sr = int(np.array(anno_audio['sample_rate']))
            audio_array = np.array(anno_audio['audio'])
            anno_reader.writemp3(str(audio_dir / 'audio.mp3'), sr, audio_array, normalized=True)
            np.savez(audio_dir / 'audio_data.npz', audio=audio_array, sample_rate=sr)
            print(f"   ✓ Audio from ANNO: {audio_array.shape[0]/sr:.1f} seconds")
            audio_found.append('anno')
        
        # Check raw file for audio (independently)
        raw_audio = try_extract_data(raw_reader, 'audio')
        if raw_audio:
            audio_dir = raw_output / 'audio'
            audio_dir.mkdir(exist_ok=True)
            sr = int(np.array(raw_audio['sample_rate']))
            audio_array = np.array(raw_audio['audio'])
            raw_reader.writemp3(str(audio_dir / 'audio.mp3'), sr, audio_array, normalized=True)
            np.savez(audio_dir / 'audio_data.npz', audio=audio_array, sample_rate=sr)
            print(f"   ✓ Audio from RAW: {audio_array.shape[0]/sr:.1f} seconds")
            audio_found.append('raw')
        
        if not audio_found:
            print(f"   ⚠ No audio data found in either file")
        elif len(audio_found) == 2:
            print(f"   ℹ Audio found in BOTH files")
    
    # 3. Extract all images and masks (check BOTH anno and raw independently)
    print("\n3. Extracting ALL images and masks (checking both files)...")
    print("   This will take a LONG time and use significant storage!")
    
    # Extract from RAW file if available
    if raw_reader:
        print("   Extracting from RAW file (high resolution)...")
        for cam_id in tqdm(range(total_cameras), desc="RAW Cameras"):
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
            
            # Don't create directories yet - wait to see if we have data
            img_created = False
            mask_created = False
            
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
                        if not img_created:
                            img_dir.mkdir(parents=True, exist_ok=True)
                            img_created = True
                        cv2.imwrite(str(img_path), img, [cv2.IMWRITE_JPEG_QUALITY, 95])
                except Exception as e:
                    if "Invalid Image_type" not in str(e):
                        print(f"\n   Error cam{cam_str} frame{frame_id} (color): {e}")
                
                try:
                    # Mask - may not be available for all performances
                    if not mask_path.exists():
                        mask = raw_reader.get_img(cam_str, 'mask', frame_id)
                        if not mask_created:
                            mask_dir.mkdir(parents=True, exist_ok=True)
                            mask_created = True
                        cv2.imwrite(str(mask_path), mask)
                except Exception as e:
                    # Silently skip mask errors as they may not be available
                    if "Invalid Image_type" not in str(e) and "Invalid Frame_id" not in str(e):
                        pass
    
    # ALSO extract from ANNO file (independently, even if raw exists)
    print("   Extracting from ANNO file (may be lower resolution)...")
    for cam_id in tqdm(range(total_cameras), desc="ANNO Cameras"):
        cam_str = f'{cam_id:02d}'
        
        # Create camera-specific directories IN ANNO OUTPUT
        img_dir = anno_output / 'images' / f'cam_{cam_str}'
        mask_dir = anno_output / 'masks' / f'cam_{cam_str}'
        
        # Check if this camera's data already exists
        existing_images = len(list(img_dir.glob('frame_*.jpg'))) if img_dir.exists() else 0
        existing_masks = len(list(mask_dir.glob('frame_*.png'))) if mask_dir.exists() else 0
        
        if existing_images >= total_frames and existing_masks >= total_frames:
            continue
        
        # Don't create directories yet - wait to see if we have data
        img_created = False
        mask_created = False
        
        for frame_id in range(total_frames):
            # Skip if both files already exist
            img_path = img_dir / f'frame_{frame_id:06d}.jpg'
            mask_path = mask_dir / f'frame_{frame_id:06d}.png'
            
            if img_path.exists() and mask_path.exists():
                continue
                
            try:
                # Color image
                if not img_path.exists():
                    img = anno_reader.get_img(cam_str, 'color', frame_id)
                    if not img_created:
                        img_dir.mkdir(parents=True, exist_ok=True)
                        img_created = True
                    cv2.imwrite(str(img_path), img, [cv2.IMWRITE_JPEG_QUALITY, 85])
            except Exception as e:
                if "Invalid Image_type" not in str(e):
                    print(f"\n   Error ANNO cam{cam_str} frame{frame_id} (color): {e}")
            
            try:
                # Mask - may not be available for all performances
                if not mask_path.exists():
                    mask = anno_reader.get_img(cam_str, 'mask', frame_id)
                    if not mask_created:
                        mask_dir.mkdir(parents=True, exist_ok=True)
                        mask_created = True
                    cv2.imwrite(str(mask_path), mask)
            except Exception as e:
                # Silently skip mask errors as they may not be available
                if "Invalid Image_type" not in str(e) and "Invalid Frame_id" not in str(e):
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
    
    # 5. Extract FLAME (check BOTH anno and raw independently)
    if 'e' in anno_reader.performance_part:
        print("\n5. Extracting FLAME parameters (checking both files)...")
        flame_found = []
        
        # Check anno file for FLAME
        anno_flame_data = {}
        for frame_id in tqdm(range(0, total_frames, 5), desc="FLAME from ANNO"):
            flame = try_extract_data(anno_reader, 'flame', frame_id)
            if flame:
                anno_flame_data[f'frame_{frame_id}'] = flame
        
        if anno_flame_data:
            flame_dir = anno_output / 'flame'
            flame_dir.mkdir(exist_ok=True)
            np.savez_compressed(flame_dir / 'all_frames.npz', **anno_flame_data)
            print(f"   ✓ FLAME from ANNO: {len(anno_flame_data)} frames")
            flame_found.append('anno')
        
        # Check raw file for FLAME (independently)
        if raw_reader:
            raw_flame_data = {}
            for frame_id in tqdm(range(0, total_frames, 5), desc="FLAME from RAW"):
                flame = try_extract_data(raw_reader, 'flame', frame_id)
                if flame:
                    raw_flame_data[f'frame_{frame_id}'] = flame
            
            if raw_flame_data:
                flame_dir = raw_output / 'flame'
                flame_dir.mkdir(exist_ok=True)
                np.savez_compressed(flame_dir / 'all_frames.npz', **raw_flame_data)
                print(f"   ✓ FLAME from RAW: {len(raw_flame_data)} frames")
                flame_found.append('raw')
        
        if not flame_found:
            print(f"   ⚠ No FLAME data found in either file")
        elif len(flame_found) == 2:
            print(f"   ℹ FLAME found in BOTH files")
        
        # UV textures (check BOTH anno and raw independently)
        print("\n6. Extracting UV textures (checking both files)...")
        uv_found = []
        
        # Check anno file for UV textures
        anno_uv_dir = anno_output / 'uv_textures'
        anno_has_uv = False
        for frame_id in tqdm(range(0, total_frames, 30), desc="UV from ANNO"):
            uv_data = try_extract_data(anno_reader, 'uv', frame_id)
            if uv_data is not None:
                if not anno_has_uv:
                    anno_uv_dir.mkdir(exist_ok=True)
                    anno_has_uv = True
                cv2.imwrite(str(anno_uv_dir / f'frame_{frame_id:06d}.jpg'), uv_data,
                          [cv2.IMWRITE_JPEG_QUALITY, 90])
        
        if anno_has_uv:
            print(f"   ✓ UV textures from ANNO")
            uv_found.append('anno')
        
        # Check raw file for UV textures (independently)
        if raw_reader:
            raw_uv_dir = raw_output / 'uv_textures'
            raw_has_uv = False
            for frame_id in tqdm(range(0, total_frames, 30), desc="UV from RAW"):
                uv_data = try_extract_data(raw_reader, 'uv', frame_id)
                if uv_data is not None:
                    if not raw_has_uv:
                        raw_uv_dir.mkdir(exist_ok=True)
                        raw_has_uv = True
                    cv2.imwrite(str(raw_uv_dir / f'frame_{frame_id:06d}.jpg'), uv_data,
                              [cv2.IMWRITE_JPEG_QUALITY, 90])
            
            if raw_has_uv:
                print(f"   ✓ UV textures from RAW")
                uv_found.append('raw')
        
        if not uv_found:
            print(f"   ⚠ No UV texture data found in either file")
        elif len(uv_found) == 2:
            print(f"   ℹ UV textures found in BOTH files")
        
        # Scan mesh (check BOTH anno and raw independently)
        print("\n7. Extracting scan mesh (checking both files)...")
        scan_found = []
        
        # Check anno file for scan mesh
        anno_scan = try_extract_data(anno_reader, 'scanmesh')
        if anno_scan:
            scan_dir = anno_output / 'scan'
            scan_dir.mkdir(exist_ok=True)
            
            # Check if plyfile is installed
            try:
                import plyfile
                anno_reader.write_ply(anno_scan, str(scan_dir / 'mesh.ply'))
                print(f"   ✓ Scan from ANNO: {anno_scan['vertex'].shape[0]} vertices")
                scan_found.append('anno')
            except ImportError:
                print(f"   ⚠ plyfile not installed. Run: pip install plyfile")
                print(f"     Scan mesh found in ANNO but cannot be saved without plyfile")
        
        # Check raw file for scan mesh (independently)
        if raw_reader:
            raw_scan = try_extract_data(raw_reader, 'scanmesh')
            if raw_scan:
                scan_dir = raw_output / 'scan'
                scan_dir.mkdir(exist_ok=True)
                
                # Check if plyfile is installed
                try:
                    import plyfile
                    raw_reader.write_ply(raw_scan, str(scan_dir / 'mesh.ply'))
                    print(f"   ✓ Scan from RAW: {raw_scan['vertex'].shape[0]} vertices")
                    scan_found.append('raw')
                except ImportError:
                    print(f"   ⚠ plyfile not installed. Run: pip install plyfile")
                    print(f"     Scan mesh found in RAW but cannot be saved without plyfile")
        
        if not scan_found:
            print(f"   ⚠ No scan mesh data found in either file")
        elif len(scan_found) == 2:
            print(f"   ℹ Scan mesh found in BOTH files")
        
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
        print(f"SMART EXTRACTION COMPLETE!")
        print(f"Output: {output_dir}")
        print(f"Anno data size: {anno_size / (1024**3):.2f} GB")
        print(f"Raw data size: {raw_size / (1024**3):.2f} GB")
        print(f"Total size: {total_size / (1024**3):.2f} GB")
        print(f"\nNote: This smart version checked both anno and raw files")
        print(f"for all data types to ensure nothing was missed.")
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
                      default='/ssd4/zhuoyuan/renderme360_temp/FULL_EXTRACTION',
                      help='Output directory')
    parser.add_argument('--separate', action='store_true', default=True,
                      help='Separate anno and raw data into different folders (default: True)')
    parser.add_argument('--combine', action='store_true',
                      help='Combine anno and raw data in same folders (legacy behavior)')
    args = parser.parse_args()
    
    # Paths
    anno_dir = Path('/ssd4/zhuoyuan/renderme360_temp/test_download/anno')
    raw_dir = Path('/ssd4/zhuoyuan/renderme360_temp/test_download/raw/0026')
    
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
        print("\nExpected output structure:")
        print(f"  {output_dir}/")
        print(f"    ├── from_anno/   # Data from annotation file")
        print(f"    │   ├── calibration/")
        print(f"    │   ├── metadata/")
        print(f"    │   ├── masks/       # Segmentation masks")
        print(f"    │   ├── keypoints2d/ # (if available)")
        print(f"    │   ├── keypoints3d/")
        print(f"    │   ├── flame/       # (expressions only)")
        print(f"    │   ├── uv_textures/ # (expressions only)")
        print(f"    │   ├── scan/        # (expressions only)")
        print(f"    │   └── scan_masks/  # (expressions only)")
        print(f"    └── from_raw/    # Data from raw file")
        print(f"        ├── images/      # High-res RGB images")
        print(f"        └── audio/       # (speech only)")
        print("\nNote: Only folders with actual data will be created.")
    
    response = input("\nAre you sure you want to proceed? (yes/no): ")
    if response.lower() != 'yes':
        print("Extraction cancelled.")
        sys.exit(0)
    
    extract_full_performance(anno_file, raw_file, output_dir, separate_sources=separate_sources)

if __name__ == '__main__':
    main()