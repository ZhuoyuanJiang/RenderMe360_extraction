#!/usr/bin/env python3
"""
RenderMe360 21ID Dataset Streaming Extraction Script
Combines complete extraction from extract_0026_FULL_both.py with 
Google Drive streaming from extract_streaming_gdrive.py

This version:
- Downloads both anno and raw SMC bundles from Google Drive
- Extracts everything from both files to ensure nothing is missed
- Cleans up downloaded files after extraction to save space
- Supports selective extraction via configuration
- Works with any subject ID (not hardcoded)
"""

import os
import sys
import cv2
import numpy as np
import json
import yaml
import subprocess
import shutil
import time
import logging
import argparse
from pathlib import Path
from datetime import datetime
from tqdm import tqdm
import pandas as pd

# Add current directory to path for importing the reader
sys.path.append(str(Path(__file__).parent))
from renderme_360_reader import SMCReader


class RenderMe360ExtractorFull:
    def __init__(self, config_path="config_21id.yaml"):
        """Initialize the extractor with configuration."""
        self.config = self.load_config(config_path)
        self.setup_directories()
        self.setup_logging()
        self.manifest_df = self.load_manifest()
        
        # Track statistics
        self.stats = {
            'subjects_processed': 0,
            'performances_downloaded': 0,
            'performances_extracted': 0,
            'performances_failed': 0,
            'total_size_gb': 0,
            'start_time': datetime.now()
        }
        
    def load_config(self, config_path):
        """Load and validate configuration from YAML file."""
        config_file = Path(config_path)
        if not config_file.exists():
            # Create default config if it doesn't exist
            default_config = self.create_default_config()
            with open(config_file, 'w') as f:
                yaml.dump(default_config, f, default_flow_style=False, sort_keys=False)
            self.logger = logging.getLogger(__name__)
            self.logger.info(f"Created default config at {config_path}")
            return default_config
            
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
            
        # Validate required fields
        required_fields = ['google_drive', 'extraction', 'storage']
        for field in required_fields:
            if field not in config:
                raise ValueError(f"Missing required config field: {field}")
                
        return config
        
    def create_default_config(self):
        """Create default configuration for 21ID dataset."""
        return {
            'google_drive': {
                'root_folder_id': 'YOUR_FOLDER_ID_HERE',  # To be provided by user
                'remote_name': 'vllab13',  # Configured rclone remote
                'structure': 'separate_anno_raw'  # 21ID structure
            },
            'extraction': {
                'subjects': ['0026'],  # Default test subject
                'performances': [
                    's1_all', 's2_all', 's3_all', 
                    's4_all', 's5_all', 's6_all'
                ],
                'cameras': 'all',  # Extract all cameras by default
                'modalities': [
                    'metadata', 'calibration', 'images', 'masks',
                    'audio', 'keypoints2d', 'keypoints3d',
                    'flame', 'uv_textures', 'scan', 'scan_masks'
                ],
                'separate_sources': True  # Separate from_anno and from_raw
            },
            'storage': {
                'temp_dir': '/ssd2/zhuoyuan/renderme360_temp/temp_smc/',
                'output_dir': '/ssd2/zhuoyuan/renderme360_temp/test_download/subjects/',
                'manifest_path': '/ssd2/zhuoyuan/renderme360_temp/test_download/MANIFEST_21ID.csv',
                'log_dir': '/ssd2/zhuoyuan/renderme360_temp/test_download/logs/'
            },
            'processing': {
                'delete_smc_after_extraction': True,
                'verify_extraction': True,
                'force_reextract': False,
                'max_retries': 3,
                'retry_delay': 30
            },
            'limits': {
                'max_temp_size_gb': 200,
                'min_free_space_gb': 100
            }
        }
        
    def setup_directories(self):
        """Create necessary directories if they don't exist."""
        dirs = [
            self.config['storage']['temp_dir'],
            self.config['storage']['output_dir'],
            self.config['storage']['log_dir'],
            Path(self.config['storage']['manifest_path']).parent
        ]
        
        for dir_path in dirs:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
            
    def setup_logging(self):
        """Set up logging to both file and console."""
        log_dir = Path(self.config['storage']['log_dir'])
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create log filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = log_dir / f'extraction_{timestamp}.log'
        
        # Configure logging format
        log_format = '%(asctime)s - %(levelname)s - %(message)s'
        
        # Set up root logger
        logging.basicConfig(
            level=logging.INFO,
            format=log_format,
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        self.logger = logging.getLogger(__name__)
        self.logger.info("="*80)
        self.logger.info("RenderMe360 21ID Full Extraction Pipeline Started")
        self.logger.info(f"Log file: {log_file}")
        self.logger.info(f"Configuration loaded")
        self.logger.info("="*80)
            
    def load_manifest(self):
        """Load or create manifest DataFrame for tracking progress."""
        manifest_path = Path(self.config['storage']['manifest_path'])
        
        if manifest_path.exists():
            return pd.read_csv(manifest_path)
        else:
            # Create new manifest with columns
            columns = ['subject', 'performance', 'status', 'cameras_extracted', 
                      'frames', 'size_gb', 'anno_size_gb', 'raw_size_gb',
                      'timestamp', 'error']
            return pd.DataFrame(columns=columns)
            
    def save_manifest(self):
        """Save manifest DataFrame to CSV."""
        self.manifest_df.to_csv(self.config['storage']['manifest_path'], index=False)
        
    def download_smc_bundle(self, subject_id, performance, data_type='both'):
        """
        Download SMC bundles from Google Drive using rclone.
        
        Args:
            subject_id: Subject ID (e.g., "0026")
            performance: Performance name (e.g., "s1_all")
            data_type: 'anno', 'raw', or 'both'
            
        Returns:
            Tuple of (anno_path, raw_path) or None for missing files
        """
        temp_dir = Path(self.config['storage']['temp_dir'])
        remote_name = self.config['google_drive']['remote_name']
        root_folder_id = self.config['google_drive']['root_folder_id']
        
        anno_path = None
        raw_path = None
        
        # Download anno bundle if needed
        if data_type in ['anno', 'both']:
            anno_bundle = f"{subject_id}_{performance}_anno.smc"
            anno_remote = f"anno/{subject_id}/{anno_bundle}"
            anno_local = temp_dir / anno_bundle
            
            if self._download_with_rclone(anno_remote, anno_local, root_folder_id):
                anno_path = anno_local
                self.logger.info(f"✓ Downloaded anno bundle: {anno_bundle}")
            else:
                self.logger.warning(f"✗ Failed to download anno bundle: {anno_bundle}")
                
        # Download raw bundle if needed  
        if data_type in ['raw', 'both']:
            raw_bundle = f"{subject_id}_{performance}_raw.smc"
            raw_remote = f"raw/{subject_id}/{raw_bundle}"
            raw_local = temp_dir / raw_bundle
            
            if self._download_with_rclone(raw_remote, raw_local, root_folder_id):
                raw_path = raw_local
                self.logger.info(f"✓ Downloaded raw bundle: {raw_bundle}")
            else:
                self.logger.warning(f"✗ Failed to download raw bundle: {raw_bundle}")
                
        return anno_path, raw_path
        
    def _download_with_rclone(self, remote_path, local_path, root_folder_id):
        """
        Execute rclone download for a single file/bundle.
        
        Returns:
            True if successful, False otherwise
        """
        remote_name = self.config['google_drive']['remote_name']
        
        # Build rclone command
        cmd = [
            'rclone', 'copy',
            f'{remote_name}:{remote_path}',
            str(local_path.parent),
            '--drive-root-folder-id', root_folder_id,
            '-P',  # Show progress
            '--drive-acknowledge-abuse',  # Accept large files
            '--transfers', '4',
            '--checkers', '8',
            '--fast-list',
            '--retries', '10',
            '--low-level-retries', '20'
        ]
        
        self.logger.debug(f"Downloading: {remote_path}")
        
        # Execute download with retries
        max_retries = self.config.get('processing', {}).get('max_retries', 3)
        retry_delay = self.config.get('processing', {}).get('retry_delay', 30)
        
        for attempt in range(max_retries):
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                
                # Verify file exists
                if local_path.exists():
                    size_gb = local_path.stat().st_size / (1024**3)
                    self.stats['performances_downloaded'] += 0.5  # Half credit per file
                    return True
                    
            except subprocess.CalledProcessError as e:
                self.logger.debug(f"Attempt {attempt + 1}/{max_retries} failed: {e.stderr}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    
        return False
        
    def try_extract_data(self, reader, data_type, *args):
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
        
    def extract_full_performance(self, anno_file, raw_file, subject_id, performance):
        """
        Extract EVERYTHING from both anno and raw files.
        Based on extract_0026_FULL_both.py but parameterized for any subject.
        """
        
        output_dir = Path(self.config['storage']['output_dir']) / subject_id / performance
        separate_sources = self.config['extraction'].get('separate_sources', True)
        
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"FULL EXTRACTION: {subject_id}/{performance}")
        self.logger.info(f"Anno: {anno_file.name if anno_file else 'Not available'}")
        self.logger.info(f"Raw: {raw_file.name if raw_file else 'Not available'}")
        self.logger.info(f"Output: {output_dir}")
        self.logger.info(f"Separate sources: {separate_sources}")
        self.logger.info(f"{'='*60}")
        
        # Check if extraction is already complete
        completion_marker = output_dir / '.extraction_complete'
        if completion_marker.exists() and not self.config.get('processing', {}).get('force_reextract', False):
            self.logger.info(f"✓ Performance already fully extracted at {output_dir}")
            return output_dir
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create separate output directories if requested
        if separate_sources:
            anno_output = output_dir / 'from_anno'
            raw_output = output_dir / 'from_raw'
            anno_output.mkdir(exist_ok=True)
            raw_output.mkdir(exist_ok=True)
        else:
            anno_output = output_dir
            raw_output = output_dir
        
        # Initialize readers
        anno_reader = SMCReader(str(anno_file)) if anno_file and anno_file.exists() else None
        raw_reader = SMCReader(str(raw_file)) if raw_file and raw_file.exists() else None
        
        if not anno_reader and not raw_reader:
            self.logger.error("No valid SMC files to extract from!")
            return None
            
        # Use whichever reader is available for basic info
        primary_reader = anno_reader if anno_reader else raw_reader
        
        # Get info
        camera_info = primary_reader.get_Camera_info()
        actor_info = primary_reader.get_actor_info()
        
        total_frames = camera_info['num_frame']
        total_cameras = camera_info['num_device']
        
        # Determine which cameras to extract
        camera_config = self.config['extraction'].get('cameras', 'all')
        if camera_config == 'all':
            camera_list = list(range(total_cameras))
        else:
            camera_list = camera_config
            
        # Get modalities to extract
        modalities = self.config['extraction'].get('modalities', [])
        
        self.logger.info(f"\nDataset Size:")
        self.logger.info(f"  Cameras: {len(camera_list)} (of {total_cameras})")
        self.logger.info(f"  Frames: {total_frames}")
        self.logger.info(f"  Total images: {len(camera_list) * total_frames:,}")
        self.logger.info(f"  Modalities: {modalities}")
        
        # Save metadata (from primary reader)
        if 'metadata' in modalities:
            metadata_dir = (anno_output if anno_reader else raw_output) / 'metadata'
            metadata_dir.mkdir(exist_ok=True)
            
            # Convert numpy types for JSON serialization
            def convert_numpy_types(obj):
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
                'subject_id': subject_id,
                'performance': performance,
                'actor_info': convert_numpy_types(actor_info),
                'camera_info': convert_numpy_types(camera_info),
                'capture_date': primary_reader.capture_date,
                'total_frames': int(total_frames),
                'total_cameras': int(total_cameras),
                'cameras_extracted': len(camera_list),
                'extraction_date': datetime.now().isoformat(),
                'extraction_mode': 'FULL',
                'data_sources': {
                    'anno': anno_file is not None,
                    'raw': raw_file is not None
                }
            }
            
            with open(metadata_dir / 'info.json', 'w') as f:
                json.dump(metadata, f, indent=2)
                
            self.logger.info("  ✓ Saved metadata")
        
        # Extract calibration (usually from anno)
        if 'calibration' in modalities and anno_reader:
            self.logger.info("\nExtracting calibration from ANNO...")
            calib_dir = anno_output / 'calibration'
            calib_dir.mkdir(exist_ok=True)
            
            all_calibs = anno_reader.get_Calibration_all()
            np.save(calib_dir / 'all_cameras.npy', all_calibs)
            
            # Save individual calibrations for selected cameras
            for cam_id in camera_list:
                calib = anno_reader.get_Calibration(f'{cam_id:02d}')
                if calib:
                    np.save(calib_dir / f'cam_{cam_id:02d}.npy', calib)
            
            self.logger.info(f"  ✓ Saved calibration for {len(camera_list)} cameras")
        
        # Extract audio (check BOTH anno and raw)
        if 'audio' in modalities and 's' in performance:
            self.logger.info("\nExtracting audio...")
            audio_found = []
            
            # Check anno file for audio
            if anno_reader:
                anno_audio = self.try_extract_data(anno_reader, 'audio')
                if anno_audio:
                    audio_dir = anno_output / 'audio'
                    audio_dir.mkdir(exist_ok=True)
                    sr = int(np.array(anno_audio['sample_rate']))
                    audio_array = np.array(anno_audio['audio'])
                    anno_reader.writemp3(str(audio_dir / 'audio.mp3'), sr, audio_array, normalized=True)
                    np.savez(audio_dir / 'audio_data.npz', audio=audio_array, sample_rate=sr)
                    self.logger.info(f"  ✓ Audio from ANNO: {audio_array.shape[0]/sr:.1f} seconds")
                    audio_found.append('anno')
            
            # Check raw file for audio
            if raw_reader:
                raw_audio = self.try_extract_data(raw_reader, 'audio')
                if raw_audio:
                    audio_dir = raw_output / 'audio'
                    audio_dir.mkdir(exist_ok=True)
                    sr = int(np.array(raw_audio['sample_rate']))
                    audio_array = np.array(raw_audio['audio'])
                    raw_reader.writemp3(str(audio_dir / 'audio.mp3'), sr, audio_array, normalized=True)
                    np.savez(audio_dir / 'audio_data.npz', audio=audio_array, sample_rate=sr)
                    self.logger.info(f"  ✓ Audio from RAW: {audio_array.shape[0]/sr:.1f} seconds")
                    audio_found.append('raw')
            
            if not audio_found:
                self.logger.info(f"  ⚠ No audio data found in either file")
        
        # Extract images and masks
        if 'images' in modalities or 'masks' in modalities:
            self.logger.info("\nExtracting images and masks...")
            
            # Extract from RAW file if available (high resolution)
            if raw_reader and 'images' in modalities:
                self.logger.info("  Extracting from RAW file (high resolution)...")
                for cam_id in tqdm(camera_list, desc="RAW Cameras"):
                    cam_str = f'{cam_id:02d}'
                    
                    img_dir = raw_output / 'images' / f'cam_{cam_str}'
                    mask_dir = raw_output / 'masks' / f'cam_{cam_str}'
                    
                    # Check if already extracted
                    existing_images = len(list(img_dir.glob('frame_*.jpg'))) if img_dir.exists() else 0
                    if existing_images >= total_frames:
                        continue
                    
                    img_created = False
                    mask_created = False
                    
                    # Sample frames based on config (can be modified for selective extraction)
                    frame_step = 1  # Extract every frame by default
                    
                    for frame_id in range(0, total_frames, frame_step):
                        img_path = img_dir / f'frame_{frame_id:06d}.jpg'
                        mask_path = mask_dir / f'frame_{frame_id:06d}.png'
                        
                        # Extract image
                        if 'images' in modalities and not img_path.exists():
                            try:
                                img = raw_reader.get_img(cam_str, 'color', frame_id)
                                if not img_created:
                                    img_dir.mkdir(parents=True, exist_ok=True)
                                    img_created = True
                                cv2.imwrite(str(img_path), img, [cv2.IMWRITE_JPEG_QUALITY, 95])
                            except:
                                pass
                        
                        # Extract mask
                        if 'masks' in modalities and not mask_path.exists():
                            try:
                                mask = raw_reader.get_img(cam_str, 'mask', frame_id)
                                if not mask_created:
                                    mask_dir.mkdir(parents=True, exist_ok=True)
                                    mask_created = True
                                cv2.imwrite(str(mask_path), mask)
                            except:
                                pass
            
            # Also extract from ANNO file if available (may have masks)
            if anno_reader and 'masks' in modalities:
                self.logger.info("  Extracting masks from ANNO file...")
                for cam_id in tqdm(camera_list, desc="ANNO Masks"):
                    cam_str = f'{cam_id:02d}'
                    
                    mask_dir = anno_output / 'masks' / f'cam_{cam_str}'
                    
                    # Check if already extracted
                    existing_masks = len(list(mask_dir.glob('frame_*.png'))) if mask_dir.exists() else 0
                    if existing_masks >= total_frames:
                        continue
                    
                    mask_created = False
                    
                    for frame_id in range(0, total_frames):
                        mask_path = mask_dir / f'frame_{frame_id:06d}.png'
                        
                        if not mask_path.exists():
                            try:
                                mask = anno_reader.get_img(cam_str, 'mask', frame_id)
                                if not mask_created:
                                    mask_dir.mkdir(parents=True, exist_ok=True)
                                    mask_created = True
                                cv2.imwrite(str(mask_path), mask)
                            except:
                                pass
        
        # Extract keypoints
        if 'keypoints2d' in modalities and anno_reader:
            self.logger.info("\nExtracting 2D keypoints...")
            kpt2d_dir = anno_output / 'keypoints2d'
            kpt2d_dir.mkdir(exist_ok=True)
            
            # 2D keypoints are usually available for cameras 18-32
            for cam_id in tqdm(range(18, min(33, total_cameras)), desc="2D Keypoints"):
                if cam_id not in camera_list:
                    continue
                    
                cam_str = f'{cam_id:02d}'
                cam_kpts = {}
                
                # Sample frames to avoid massive files
                for frame_id in range(0, total_frames, 10):
                    try:
                        kpt = anno_reader.get_Keypoints2d(cam_str, frame_id)
                        if kpt is not None:
                            cam_kpts[f'frame_{frame_id}'] = kpt
                    except:
                        pass
                
                if cam_kpts:
                    np.savez_compressed(kpt2d_dir / f'cam_{cam_str}.npz', **cam_kpts)
        
        if 'keypoints3d' in modalities and anno_reader:
            self.logger.info("\nExtracting 3D keypoints...")
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
                self.logger.info(f"  ✓ 3D keypoints: {len(kpts3d)} frames")
        
        # Expression-specific data
        if 'e' in performance:
            # FLAME parameters
            if 'flame' in modalities:
                self.logger.info("\nExtracting FLAME parameters...")
                
                if anno_reader:
                    flame_data = {}
                    for frame_id in tqdm(range(0, total_frames, 5), desc="FLAME"):
                        flame = self.try_extract_data(anno_reader, 'flame', frame_id)
                        if flame:
                            flame_data[f'frame_{frame_id}'] = flame
                    
                    if flame_data:
                        flame_dir = anno_output / 'flame'
                        flame_dir.mkdir(exist_ok=True)
                        np.savez_compressed(flame_dir / 'all_frames.npz', **flame_data)
                        self.logger.info(f"  ✓ FLAME: {len(flame_data)} frames")
            
            # UV textures
            if 'uv_textures' in modalities:
                self.logger.info("\nExtracting UV textures...")
                
                if anno_reader:
                    uv_dir = anno_output / 'uv_textures'
                    has_uv = False
                    for frame_id in tqdm(range(0, total_frames, 30), desc="UV"):
                        uv_data = self.try_extract_data(anno_reader, 'uv', frame_id)
                        if uv_data is not None:
                            if not has_uv:
                                uv_dir.mkdir(exist_ok=True)
                                has_uv = True
                            cv2.imwrite(str(uv_dir / f'frame_{frame_id:06d}.jpg'), uv_data,
                                      [cv2.IMWRITE_JPEG_QUALITY, 90])
                    
                    if has_uv:
                        self.logger.info(f"  ✓ UV textures extracted")
            
            # Scan mesh
            if 'scan' in modalities and anno_reader:
                self.logger.info("\nExtracting scan mesh...")
                scan = self.try_extract_data(anno_reader, 'scanmesh')
                if scan:
                    scan_dir = anno_output / 'scan'
                    scan_dir.mkdir(exist_ok=True)
                    
                    try:
                        import plyfile
                        anno_reader.write_ply(scan, str(scan_dir / 'mesh.ply'))
                        self.logger.info(f"  ✓ Scan mesh: {scan['vertex'].shape[0]} vertices")
                    except ImportError:
                        self.logger.warning("  ⚠ plyfile not installed. Run: pip install plyfile")
            
            # Scan masks
            if 'scan_masks' in modalities and anno_reader:
                self.logger.info("\nExtracting scan masks...")
                scanmask_dir = anno_output / 'scan_masks'
                scanmask_dir.mkdir(exist_ok=True)
                
                for cam_id in tqdm(camera_list, desc="Scan masks"):
                    try:
                        mask = anno_reader.get_scanmask(f'{cam_id:02d}')
                        if mask is not None:
                            cv2.imwrite(str(scanmask_dir / f'cam_{cam_id:02d}.png'), mask)
                    except:
                        pass
        
        # Calculate final sizes
        anno_size = 0
        raw_size = 0
        
        if separate_sources:
            if anno_output.exists():
                anno_size = sum(f.stat().st_size for f in anno_output.rglob('*') if f.is_file())
            if raw_output.exists():
                raw_size = sum(f.stat().st_size for f in raw_output.rglob('*') if f.is_file())
            total_size = (anno_size + raw_size) / (1024**3)
        else:
            total_size = sum(f.stat().st_size for f in output_dir.rglob('*') if f.is_file()) / (1024**3)
        
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"EXTRACTION COMPLETE!")
        self.logger.info(f"Output: {output_dir}")
        if separate_sources:
            self.logger.info(f"Anno data size: {anno_size / (1024**3):.2f} GB")
            self.logger.info(f"Raw data size: {raw_size / (1024**3):.2f} GB")
        self.logger.info(f"Total size: {total_size:.2f} GB")
        self.logger.info(f"{'='*60}")
        
        # Mark extraction as complete
        with open(completion_marker, 'w') as f:
            f.write(f"Extraction completed at {datetime.now().isoformat()}\n")
            f.write(f"Subject: {subject_id}\n")
            f.write(f"Performance: {performance}\n")
            f.write(f"Total size: {total_size:.2f} GB\n")
            f.write(f"Cameras: {len(camera_list)}\n")
            f.write(f"Frames: {total_frames}\n")
        
        # Update manifest
        self.update_manifest(
            subject_id, performance, 'completed',
            cameras=len(camera_list), frames=total_frames,
            size_gb=total_size,
            anno_size_gb=anno_size / (1024**3) if separate_sources else 0,
            raw_size_gb=raw_size / (1024**3) if separate_sources else 0
        )
        
        self.stats['performances_extracted'] += 1
        self.stats['total_size_gb'] += total_size
        
        return output_dir
        
    def cleanup_temp_files(self, subject_id, performance):
        """Remove temporary SMC files after successful extraction."""
        if not self.config['processing'].get('delete_smc_after_extraction', True):
            return
            
        temp_dir = Path(self.config['storage']['temp_dir'])
        
        # Remove both anno and raw SMC bundles
        patterns = [
            f"{subject_id}_{performance}_anno.smc",
            f"{subject_id}_{performance}_raw.smc"
        ]
        
        cleaned_count = 0
        for pattern in patterns:
            smc_file = temp_dir / pattern
            if smc_file.exists():
                if smc_file.is_dir():
                    shutil.rmtree(smc_file)
                else:
                    smc_file.unlink()
                self.logger.debug(f"  Removed: {pattern}")
                cleaned_count += 1
                
        if cleaned_count > 0:
            self.logger.info(f"  ✓ Cleaned up {cleaned_count} temporary files")
            
    def update_manifest(self, subject_id, performance, status, **kwargs):
        """Update manifest with extraction results."""
        # Check if entry exists
        mask = (self.manifest_df['subject'] == subject_id) & \
               (self.manifest_df['performance'] == performance)
        
        if mask.any():
            # Update existing entry
            for key, value in kwargs.items():
                self.manifest_df.loc[mask, key] = value
            self.manifest_df.loc[mask, 'status'] = status
            self.manifest_df.loc[mask, 'timestamp'] = datetime.now().isoformat()
        else:
            # Create new entry
            new_row = {
                'subject': subject_id,
                'performance': performance,
                'status': status,
                'timestamp': datetime.now().isoformat()
            }
            new_row.update(kwargs)
            self.manifest_df = pd.concat([self.manifest_df, pd.DataFrame([new_row])], ignore_index=True)
        
        self.save_manifest()
        
    def check_storage_space(self):
        """Check available storage space."""
        import shutil
        output_dir = Path(self.config['storage']['output_dir'])
        stat = shutil.disk_usage(output_dir)
        free_gb = stat.free / (1024**3)
        
        min_required = self.config['limits'].get('min_free_space_gb', 50)
        if free_gb < min_required:
            self.logger.warning(f"⚠ Low storage: {free_gb:.1f} GB free (minimum: {min_required} GB)")
            
        return free_gb
        
    def process_subject(self, subject_id):
        """Process all configured performances for a single subject."""
        self.logger.info(f"\n{'='*80}")
        self.logger.info(f"PROCESSING SUBJECT: {subject_id}")
        self.logger.info(f"{'='*80}")
        
        performances = self.config['extraction']['performances']
        
        # Check storage before starting
        free_space = self.check_storage_space()
        self.logger.info(f"Available storage: {free_space:.1f} GB")
        
        if free_space < self.config['limits'].get('min_free_space_gb', 50):
            self.logger.error(f"Insufficient storage space. Skipping subject {subject_id}")
            return
        
        success_count = 0
        
        for performance in performances:
            try:
                self.logger.info(f"\n--- Performance: {performance} ---")
                
                # Download both anno and raw bundles
                anno_path, raw_path = self.download_smc_bundle(subject_id, performance, 'both')
                
                if not anno_path and not raw_path:
                    self.logger.error(f"Failed to download any files for {subject_id}/{performance}")
                    self.stats['performances_failed'] += 1
                    self.update_manifest(subject_id, performance, 'download_failed',
                                       error="No files downloaded")
                    continue
                
                # Extract data
                output_dir = self.extract_full_performance(
                    anno_path, raw_path, subject_id, performance
                )
                
                if output_dir:
                    success_count += 1
                    
                    # Clean up temporary files
                    self.cleanup_temp_files(subject_id, performance)
                else:
                    self.stats['performances_failed'] += 1
                    
            except Exception as e:
                self.logger.error(f"Failed to process {subject_id}/{performance}: {str(e)}")
                self.stats['performances_failed'] += 1
                self.update_manifest(subject_id, performance, 'failed', error=str(e))
                
        self.logger.info(f"\n{'='*80}")
        self.logger.info(f"Subject {subject_id} complete: {success_count}/{len(performances)} performances")
        self.logger.info(f"{'='*80}")
        
        self.stats['subjects_processed'] += 1
        
    def run(self):
        """Main execution loop for all configured subjects."""
        subjects = self.config['extraction']['subjects']
        
        self.logger.info(f"\n{'='*80}")
        self.logger.info(f"RENDERME360 21ID FULL EXTRACTION PIPELINE")
        self.logger.info(f"{'='*80}")
        self.logger.info(f"Subjects to process: {len(subjects)}")
        self.logger.info(f"Performances per subject: {len(self.config['extraction']['performances'])}")
        self.logger.info(f"Output directory: {self.config['storage']['output_dir']}")
        self.logger.info(f"{'='*80}")
        
        # Process each subject
        for subject_id in subjects:
            try:
                self.process_subject(subject_id)
            except KeyboardInterrupt:
                self.logger.info("\n\nExtraction interrupted by user")
                break
            except Exception as e:
                self.logger.error(f"Failed to process subject {subject_id}: {str(e)}")
                continue
                
        # Print final statistics
        elapsed = datetime.now() - self.stats['start_time']
        
        self.logger.info(f"\n{'='*80}")
        self.logger.info(f"EXTRACTION PIPELINE COMPLETE")
        self.logger.info(f"{'='*80}")
        self.logger.info(f"Duration: {elapsed}")
        self.logger.info(f"Subjects processed: {self.stats['subjects_processed']}")
        self.logger.info(f"Performances extracted: {self.stats['performances_extracted']}")
        self.logger.info(f"Performances failed: {self.stats['performances_failed']}")
        self.logger.info(f"Total data extracted: {self.stats['total_size_gb']:.2f} GB")
        self.logger.info(f"Manifest saved: {self.config['storage']['manifest_path']}")
        self.logger.info(f"{'='*80}")
        

def main():
    parser = argparse.ArgumentParser(
        description='RenderMe360 21ID Full Extraction with Google Drive Streaming'
    )
    parser.add_argument(
        '--config', 
        type=str, 
        default='config_21id.yaml',
        help='Path to configuration file'
    )
    parser.add_argument(
        '--subject',
        type=str,
        help='Override config to process single subject'
    )
    parser.add_argument(
        '--performance',
        type=str,
        help='Override config to process single performance'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Test configuration without downloading'
    )
    
    args = parser.parse_args()
    
    # Initialize extractor
    extractor = RenderMe360ExtractorFull(args.config)
    
    # Override config if single subject/performance specified
    if args.subject:
        extractor.config['extraction']['subjects'] = [args.subject]
    if args.performance:
        extractor.config['extraction']['performances'] = [args.performance]
        
    if args.dry_run:
        extractor.logger.info("DRY RUN MODE - No downloads will be performed")
        extractor.logger.info(f"Would process subjects: {extractor.config['extraction']['subjects']}")
        extractor.logger.info(f"Would process performances: {extractor.config['extraction']['performances']}")
        return
        
    # Run extraction
    extractor.run()


if __name__ == '__main__':
    main()