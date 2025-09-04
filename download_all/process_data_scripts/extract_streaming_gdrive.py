#!/usr/bin/env python3
"""
Streaming extraction pipeline for RenderMe360 dataset from Google Drive.
Downloads and processes one subject at a time to manage storage constraints.

Based on extract_0026_FULL_both.py but adapted for:
- Single SMC files from Google Drive (not anno/raw pairs)
- Streaming processing (download -> extract -> delete)
- Configurable camera and modality selection
- Robust error handling and resume capability
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
from pathlib import Path
from datetime import datetime
from tqdm import tqdm
import pandas as pd
import h5py

# Add parent directory to path for importing the reader
sys.path.append(str(Path(__file__).parent))
from renderme_360_reader_new import SMCReader


class StreamingExtractor:
    def __init__(self, config_path="config.yaml"):
        """Initialize the streaming extractor with configuration."""
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
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
            
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
            
        # Validate required fields
        required_fields = ['google_drive', 'extraction', 'storage']
        for field in required_fields:
            if field not in config:
                raise ValueError(f"Missing required config field: {field}")
                
        return config
        
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
        self.logger.info("RenderMe360 Streaming Extraction Pipeline Started")
        self.logger.info(f"Log file: {log_file}")
        self.logger.info(f"Configuration: {self.config}")
        self.logger.info("="*80)
            
    def load_manifest(self):
        """Load or create manifest DataFrame for tracking progress."""
        manifest_path = Path(self.config['storage']['manifest_path'])
        
        if manifest_path.exists():
            return pd.read_csv(manifest_path)
        else:
            # Create new manifest with columns
            columns = ['subject', 'performance', 'status', 'cameras_extracted', 
                      'frames', 'size_gb', 'timestamp', 'error']
            return pd.DataFrame(columns=columns)
            
    def save_manifest(self):
        """Save manifest DataFrame to CSV."""
        self.manifest_df.to_csv(self.config['storage']['manifest_path'], index=False)
        
    def download_smc_with_rclone(self, subject_id, performance):
        """
        Download a specific SMC file from Google Drive using rclone.
        
        Args:
            subject_id: Subject ID (e.g., "0018")
            performance: Performance name (e.g., "s1_all")
            
        Returns:
            Path to downloaded file
        """
        temp_dir = Path(self.config['storage']['temp_dir'])
        remote_name = self.config['google_drive']['remote_name']
        root_folder_id = self.config['google_drive']['root_folder_id']
        
        # Expected file name in Google Drive
        smc_filename = f"{subject_id}_{performance}_raw.smc"
        remote_path = f"{subject_id}/{smc_filename}"
        local_path = temp_dir / smc_filename
        
        # Build rclone command
        cmd = [
            'rclone', 'copy',
            f'{remote_name}:{remote_path}',
            str(temp_dir),
            '--drive-root-folder-id', root_folder_id,
            '-P',  # Show progress
            '--drive-acknowledge-abuse',  # Accept large files
            '--transfers', '4',
            '--checkers', '8',
            '--fast-list',
            '--retries', '10',
            '--low-level-retries', '20'
        ]
        
        self.logger.info(f"Downloading {subject_id}/{performance}: {smc_filename}")
        self.logger.debug(f"Command: {' '.join(cmd)}")
        
        # Execute download
        max_retries = self.config.get('processing', {}).get('max_retries', 3)
        retry_delay = self.config.get('processing', {}).get('retry_delay', 30)
        
        for attempt in range(max_retries):
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                
                # Verify file exists and has reasonable size
                if local_path.exists():
                    size_gb = local_path.stat().st_size / (1024**3)
                    self.logger.info(f"✓ Successfully downloaded {subject_id}/{performance}: {size_gb:.2f} GB")
                    self.stats['performances_downloaded'] += 1
                    return local_path
                else:
                    error_msg = f"File not found after download: {local_path}"
                    self.logger.error(error_msg)
                    raise FileNotFoundError(error_msg)
                    
            except subprocess.CalledProcessError as e:
                self.logger.warning(f"Download attempt {attempt + 1}/{max_retries} failed for {subject_id}/{performance}: {e.stderr}")
                if attempt < max_retries - 1:
                    self.logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    error_msg = f"Failed to download {subject_id}/{performance} after {max_retries} attempts"
                    self.logger.error(error_msg)
                    self.stats['performances_failed'] += 1
                    raise Exception(error_msg)
                    
        return None
        
    def extract_performance(self, smc_file, subject_id, performance):
        """
        Extract all data from a single SMC file.
        Adapted from extract_0026_FULL_both.py but for single SMC file.
        
        Args:
            smc_file: Path to the SMC file
            subject_id: Subject ID (e.g., "0018") 
            performance: Performance name (e.g., "s1_all")
        """
        self.logger.info(f"Starting extraction: {subject_id}/{performance}")
        
        # Create output directory
        output_dir = Path(self.config['storage']['output_dir']) / subject_id / performance
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Check if already extracted
        completion_marker = output_dir / '.extraction_complete'
        if completion_marker.exists() and not self.config.get('processing', {}).get('force_reextract', False):
            self.logger.info(f"✓ Already extracted: {subject_id}/{performance}")
            return output_dir
            
        try:
            # Initialize reader with the SMC file
            reader = SMCReader(str(smc_file))
            
            # Get basic info
            camera_info = reader.get_Camera_info()
            actor_info = reader.get_actor_info()
            
            total_frames = camera_info['num_frame']
            total_cameras = camera_info['num_device']
            
            self.logger.info(f"Dataset info for {subject_id}/{performance}:")
            self.logger.info(f"  Subject ID: {reader.actor_id}")
            self.logger.info(f"  Performance: {reader.performance_part}")
            self.logger.info(f"  Cameras: {total_cameras}")
            self.logger.info(f"  Frames: {total_frames}")
            
            # Determine which cameras to extract by querying actual available cameras
            camera_config = self.config['extraction'].get('cameras', 'all')
            
            # Get actual camera IDs that exist in the SMC file
            available_cameras = sorted([int(cam_id) for cam_id in reader.smc["Camera"].keys()])
            
            if camera_config == 'all':
                camera_list = available_cameras
                self.logger.info(f"  Available cameras in SMC: {available_cameras}")
                self.logger.info(f"  Total available: {len(available_cameras)} cameras (out of {total_cameras} reported by num_device)")
            else:
                # Filter user-specified cameras to only those that actually exist
                camera_list = [cam for cam in camera_config if cam in available_cameras]
                skipped = [cam for cam in camera_config if cam not in available_cameras]
                if skipped:
                    self.logger.warning(f"  Requested cameras not available in SMC: {skipped}")
                self.logger.info(f"  Extracting cameras: {camera_list} ({len(camera_list)} cameras)")
                
            if not camera_list:
                self.logger.warning(f"  WARNING: No valid cameras found to extract!")
            else:
                self.logger.info(f"  Extracting {len(camera_list)} cameras: {camera_list[:5]}{'...' if len(camera_list) > 5 else ''}")
            
            # Extract each modality if configured
            modalities = self.config['extraction'].get('modalities', [])
            
            if 'metadata' in modalities:
                self.extract_metadata(reader, output_dir, actor_info, camera_info)
                
            if 'calibration' in modalities:
                self.extract_calibration(reader, output_dir, camera_list, available_cameras)
                
            if 'audio' in modalities and 's' in performance:
                self.extract_audio(reader, output_dir)
                
            if 'images' in modalities or 'masks' in modalities:
                self.extract_images_and_masks(reader, output_dir, camera_list, 
                                             total_frames, modalities)
                
            if 'keypoints2d' in modalities:
                self.extract_keypoints2d(reader, output_dir, total_frames)
                
            if 'keypoints3d' in modalities:
                self.extract_keypoints3d(reader, output_dir, total_frames)
                
            # Check for expression-specific data (won't be in speech but check anyway)
            if 'e' in performance:
                if 'flame' in modalities:
                    self.extract_flame(reader, output_dir, total_frames)
                if 'uv_textures' in modalities:
                    self.extract_uv_textures(reader, output_dir, total_frames)
                if 'scan' in modalities:
                    self.extract_scan(reader, output_dir)
                if 'scan_masks' in modalities:
                    self.extract_scan_masks(reader, output_dir, available_cameras)
                    
            # Calculate extraction size
            total_size = self.calculate_directory_size(output_dir)
            self.logger.info(f"✓ Extraction complete for {subject_id}/{performance}")
            self.logger.info(f"  Output: {output_dir}")
            self.logger.info(f"  Total size: {total_size:.2f} GB")
            self.logger.info(f"  Cameras: {len(camera_list)}, Frames: {total_frames}")
            
            # Mark as complete
            with open(completion_marker, 'w') as f:
                f.write(f"Extraction completed at {datetime.now().isoformat()}\n")
                f.write(f"Subject: {subject_id}\n")
                f.write(f"Performance: {performance}\n")
                f.write(f"Total size: {total_size:.2f} GB\n")
                f.write(f"Cameras extracted: {len(camera_list)}\n")
                f.write(f"Frames: {total_frames}\n")
                
            # Update statistics
            self.stats['performances_extracted'] += 1
            self.stats['total_size_gb'] += total_size
                
            # Update manifest
            self.update_manifest(subject_id, performance, 'completed', 
                               cameras=len(camera_list), frames=total_frames, 
                               size_gb=total_size)
                               
            return output_dir
            
        except Exception as e:
            self.logger.error(f"✗ Failed to extract {subject_id}/{performance}: {str(e)}")
            self.stats['performances_failed'] += 1
            self.update_manifest(subject_id, performance, 'failed', error=str(e))
            raise
            
    def extract_metadata(self, reader, output_dir, actor_info, camera_info):
        """Extract and save metadata."""
        self.logger.debug("Extracting metadata...")
        metadata_dir = output_dir / 'metadata'
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
            'subject_id': reader.actor_id,
            'performance': reader.performance_part,
            'actor_info': convert_numpy_types(actor_info),
            'camera_info': convert_numpy_types(camera_info),
            'capture_date': reader.capture_date,
            'extraction_date': datetime.now().isoformat()
        }
        
        with open(metadata_dir / 'info.json', 'w') as f:
            json.dump(metadata, f, indent=2)
            
        self.logger.debug(f"  ✓ Saved metadata")
        
    def extract_calibration(self, reader, output_dir, camera_list, available_cameras):
        """Extract camera calibration matrices."""
        self.logger.debug("Extracting calibration...")
        calib_dir = output_dir / 'calibration'
        calib_dir.mkdir(exist_ok=True)
        
        # Get all calibrations (but only for cameras that actually exist)
        all_calibs = reader.get_Calibration_all()
        
        # Filter to only include calibrations for cameras that exist
        filtered_calibs = {}
        for cam_id in available_cameras:
            cam_str = f'{cam_id:02d}'
            if cam_str in all_calibs:
                filtered_calibs[cam_str] = all_calibs[cam_str]
        
        np.save(calib_dir / 'all_cameras.npy', filtered_calibs)
        
        # Also save individual calibrations for selected cameras
        for cam_id in camera_list:
            cam_str = f'{cam_id:02d}'
            if cam_str in filtered_calibs:
                np.save(calib_dir / f'cam_{cam_str}.npy', filtered_calibs[cam_str])
                
        self.logger.debug(f"  ✓ Saved calibration for {len(camera_list)} cameras (from {len(available_cameras)} available)")
        
    def extract_audio(self, reader, output_dir):
        """Extract audio from speech performances."""
        self.logger.debug("Extracting audio...")
        try:
            audio_data = reader.get_audio()
            if audio_data:
                audio_dir = output_dir / 'audio'
                audio_dir.mkdir(exist_ok=True)
                
                sr = int(np.array(audio_data['sample_rate']))
                audio_array = np.array(audio_data['audio'])
                
                # Save as MP3
                reader.writemp3(str(audio_dir / 'audio.mp3'), sr, audio_array, normalized=True)
                
                # Also save raw numpy array
                np.savez(audio_dir / 'audio_data.npz', audio=audio_array, sample_rate=sr)
                
                duration = audio_array.shape[0] / sr
                self.logger.debug(f"  ✓ Extracted audio: {duration:.1f} seconds")
        except Exception as e:
            self.logger.debug(f"  ⚠ No audio data found: {e}")
            
    def extract_images_and_masks(self, reader, output_dir, camera_list, total_frames, modalities):
        """Extract images and/or masks for selected cameras."""
        extract_images = 'images' in modalities
        extract_masks = 'masks' in modalities
        
        if extract_images:
            self.logger.debug(f"Extracting images from {len(camera_list)} cameras...")
        if extract_masks:
            self.logger.debug(f"Extracting masks from {len(camera_list)} cameras...")
            
        for cam_id in tqdm(camera_list, desc="Cameras"):
            cam_str = f'{cam_id:02d}'
            
            # Create directories
            if extract_images:
                img_dir = output_dir / 'images' / f'cam_{cam_str}'
                img_dir.mkdir(parents=True, exist_ok=True)
            if extract_masks:
                mask_dir = output_dir / 'masks' / f'cam_{cam_str}'
                mask_dir.mkdir(parents=True, exist_ok=True)
                
            for frame_id in range(total_frames):
                # Extract image
                if extract_images:
                    img_path = img_dir / f'frame_{frame_id:06d}.jpg'
                    if not img_path.exists():
                        try:
                            img = reader.get_img(cam_str, 'color', frame_id)
                            # Save raw image data without compression
                            cv2.imwrite(str(img_path), img)
                        except Exception as e:
                            if "Invalid Image_type" not in str(e):
                                self.logger.debug(f"  Error extracting image cam{cam_str} frame{frame_id}: {e}")
                                
                # Extract mask  
                if extract_masks:
                    mask_path = mask_dir / f'frame_{frame_id:06d}.png'
                    if not mask_path.exists():
                        try:
                            mask = reader.get_img(cam_str, 'mask', frame_id)
                            cv2.imwrite(str(mask_path), mask)
                        except Exception as e:
                            # Masks might not exist for all performances
                            pass
                            
        self.logger.debug(f"  ✓ Extracted images/masks")
        
    def extract_keypoints2d(self, reader, output_dir, total_frames):
        """Extract 2D keypoints (cameras 18-32 typically have them)."""
        self.logger.debug("Extracting 2D keypoints...")
        kpt2d_dir = output_dir / 'keypoints2d'
        kpt2d_dir.mkdir(exist_ok=True)
        
        # Only cameras 18-32 typically have 2D keypoints
        for cam_id in range(18, min(33, 60)):
            cam_str = f'{cam_id:02d}'
            cam_kpts = {}
            
            # Sample every 10 frames to avoid huge files
            for frame_id in range(0, total_frames, 10):
                try:
                    kpt = reader.get_Keypoints2d(cam_str, frame_id)
                    if kpt is not None:
                        cam_kpts[f'frame_{frame_id}'] = kpt
                except:
                    pass
                    
            if cam_kpts:
                np.savez_compressed(kpt2d_dir / f'cam_{cam_str}.npz', **cam_kpts)
                
        self.logger.debug(f"  ✓ Extracted 2D keypoints")
        
    def extract_keypoints3d(self, reader, output_dir, total_frames):
        """Extract 3D keypoints."""
        self.logger.debug("Extracting 3D keypoints...")
        kpt3d_dir = output_dir / 'keypoints3d'
        kpt3d_dir.mkdir(exist_ok=True)
        
        kpts3d = {}
        # Sample every 10 frames
        for frame_id in range(0, total_frames, 10):
            try:
                kpt = reader.get_Keypoints3d(frame_id)
                if kpt is not None:
                    kpts3d[f'frame_{frame_id}'] = kpt
            except:
                pass
                
        if kpts3d:
            np.savez_compressed(kpt3d_dir / 'all_frames.npz', **kpts3d)
            self.logger.debug(f"  ✓ Extracted 3D keypoints: {len(kpts3d)} frames")
            
    def extract_flame(self, reader, output_dir, total_frames):
        """Extract FLAME parameters (expression performances only)."""
        self.logger.debug("Extracting FLAME parameters...")
        try:
            flame_dir = output_dir / 'flame'
            flame_dir.mkdir(exist_ok=True)
            
            flame_data = {}
            for frame_id in range(0, total_frames, 5):
                flame = reader.get_FLAME(frame_id)
                if flame:
                    flame_data[f'frame_{frame_id}'] = flame
                    
            if flame_data:
                np.savez_compressed(flame_dir / 'all_frames.npz', **flame_data)
                self.logger.debug(f"  ✓ Extracted FLAME: {len(flame_data)} frames")
        except Exception as e:
            self.logger.debug(f"  ⚠ No FLAME data found: {e}")
            
    def extract_uv_textures(self, reader, output_dir, total_frames):
        """Extract UV texture maps (expression performances only)."""
        self.logger.debug("Extracting UV textures...")
        try:
            uv_dir = output_dir / 'uv_textures'
            uv_dir.mkdir(exist_ok=True)
            
            for frame_id in range(0, total_frames, 30):
                uv = reader.get_uv(frame_id)
                if uv is not None:
                    # Save raw UV texture without compression
                    cv2.imwrite(str(uv_dir / f'frame_{frame_id:06d}.jpg'), uv)
                    
            self.logger.debug(f"  ✓ Extracted UV textures")
        except Exception as e:
            self.logger.debug(f"  ⚠ No UV texture data found: {e}")
            
    def extract_scan(self, reader, output_dir):
        """Extract 3D scan mesh (expression performances only)."""
        self.logger.debug("Extracting scan mesh...")
        try:
            scan = reader.get_scanmesh()
            if scan:
                scan_dir = output_dir / 'scan'
                scan_dir.mkdir(exist_ok=True)
                
                # Check if plyfile is installed
                try:
                    import plyfile
                    reader.write_ply(scan, str(scan_dir / 'mesh.ply'))
                    self.logger.debug(f"  ✓ Extracted scan: {scan['vertex'].shape[0]} vertices")
                except ImportError:
                    self.logger.debug(f"  ⚠ plyfile not installed. Run: pip install plyfile")
                    np.savez(scan_dir / 'scan_data.npz', **scan)
                    self.logger.debug(f"  ✓ Saved scan as npz: {scan['vertex'].shape[0]} vertices")
        except Exception as e:
            self.logger.debug(f"  ⚠ No scan mesh data found: {e}")
            
    def extract_scan_masks(self, reader, output_dir, available_cameras):
        """Extract scan masks (expression performances only)."""
        self.logger.debug("Extracting scan masks...")
        try:
            scanmask_dir = output_dir / 'scan_masks'
            scanmask_dir.mkdir(exist_ok=True)
            
            # Only try to extract scan masks for cameras that actually exist
            for cam_id in available_cameras:
                mask = reader.get_scanmask(f'{cam_id:02d}')
                if mask is not None:
                    cv2.imwrite(str(scanmask_dir / f'cam_{cam_id:02d}.png'), mask)
                    
            self.logger.debug(f"  ✓ Extracted scan masks")
        except Exception as e:
            self.logger.debug(f"  ⚠ No scan mask data found: {e}")
            
    def calculate_directory_size(self, path):
        """Calculate total size of directory in GB."""
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                if os.path.exists(filepath):
                    total_size += os.path.getsize(filepath)
        return total_size / (1024**3)  # Convert to GB
        
    def update_manifest(self, subject_id, performance, status, 
                       cameras=None, frames=None, size_gb=None, error=None):
        """Update manifest with extraction status."""
        # Check if entry exists
        mask = (self.manifest_df['subject'] == subject_id) & \
               (self.manifest_df['performance'] == performance)
        
        if mask.any():
            # Update existing entry
            idx = self.manifest_df[mask].index[0]
            self.manifest_df.at[idx, 'status'] = status
            self.manifest_df.at[idx, 'timestamp'] = datetime.now().isoformat()
            if cameras is not None:
                self.manifest_df.at[idx, 'cameras_extracted'] = cameras
            if frames is not None:
                self.manifest_df.at[idx, 'frames'] = frames
            if size_gb is not None:
                self.manifest_df.at[idx, 'size_gb'] = size_gb
            if error is not None:
                self.manifest_df.at[idx, 'error'] = error
        else:
            # Add new entry
            new_row = {
                'subject': subject_id,
                'performance': performance,
                'status': status,
                'cameras_extracted': cameras,
                'frames': frames,
                'size_gb': size_gb,
                'timestamp': datetime.now().isoformat(),
                'error': error
            }
            self.manifest_df = pd.concat([self.manifest_df, pd.DataFrame([new_row])], 
                                        ignore_index=True)
            
        # Save manifest
        self.save_manifest()
        
    def cleanup_temp_files(self, subject_id):
        """Remove temporary SMC files for completed subject."""
        temp_dir = Path(self.config['storage']['temp_dir'])
        
        # Remove all SMC files for this subject
        cleaned_count = 0
        for smc_file in temp_dir.glob(f"{subject_id}_*.smc"):
            self.logger.debug(f"  Removing temporary file: {smc_file.name}")
            smc_file.unlink()
            cleaned_count += 1
            
        # Calculate freed space
        remaining_files = list(temp_dir.glob("*.smc"))
        if cleaned_count > 0:
            self.logger.debug(f"  Cleaned {cleaned_count} temporary files for {subject_id}")
        if not remaining_files:
            self.logger.debug(f"  ✓ Temp directory is clean")
        else:
            self.logger.debug(f"  {len(remaining_files)} files still in temp directory")
            
    def check_storage_space(self):
        """Check if there's enough storage space to continue."""
        import shutil
        
        output_dir = Path(self.config['storage']['output_dir'])
        stat = shutil.disk_usage(output_dir)
        
        free_gb = stat.free / (1024**3)
        min_required = self.config.get('limits', {}).get('min_free_space_gb', 50)
        
        if free_gb < min_required:
            raise Exception(f"Insufficient storage space: {free_gb:.1f}GB free, {min_required}GB required")
            
        return free_gb
        
    def process_subject(self, subject_id):
        """Process all performances for a single subject."""
        self.logger.info(f"\n{'='*80}")
        self.logger.info(f"PROCESSING SUBJECT: {subject_id}")
        self.logger.info(f"{'='*80}")
        
        performances = self.config['extraction']['performances']
        
        # Check storage before starting
        free_space = self.check_storage_space()
        self.logger.info(f"Available storage: {free_space:.1f} GB")
        
        # Track subject start
        self.stats['subjects_processed'] += 1
        
        # Download all SMC files for this subject first
        downloaded_files = []
        for performance in performances:
            try:
                # Check if already completed
                mask = (self.manifest_df['subject'] == subject_id) & \
                       (self.manifest_df['performance'] == performance)
                if mask.any() and self.manifest_df[mask]['status'].values[0] == 'completed':
                    self.logger.info(f"✓ Already completed: {subject_id}/{performance}")
                    continue
                    
                # Download SMC file
                smc_path = self.download_smc_with_rclone(subject_id, performance)
                if smc_path:
                    downloaded_files.append((performance, smc_path))
            except Exception as e:
                self.logger.error(f"✗ Failed to download {subject_id}/{performance}: {e}")
                self.update_manifest(subject_id, performance, 'download_failed', error=str(e))
                
        # Extract each downloaded file
        for performance, smc_path in downloaded_files:
            try:
                self.extract_performance(smc_path, subject_id, performance)
                
                # Delete SMC file immediately after extraction
                if self.config.get('processing', {}).get('delete_smc_after_extraction', True):
                    self.logger.debug(f"  Deleting {smc_path.name}...")
                    smc_path.unlink()
                    
            except Exception as e:
                self.logger.error(f"ERROR extracting {subject_id}/{performance}: {e}")
                
        # Clean up any remaining temp files
        self.cleanup_temp_files(subject_id)
        
        # Report subject completion
        subject_dir = Path(self.config['storage']['output_dir']) / subject_id
        if subject_dir.exists():
            total_size = self.calculate_directory_size(subject_dir)
            self.logger.info(f"✓ Subject {subject_id} complete: {total_size:.2f} GB")
            
    def run(self):
        """Main execution loop for all configured subjects."""
        subjects = self.config['extraction']['subjects']
        
        self.logger.info(f"\n{'='*80}")
        self.logger.info(f"RENDERME360 STREAMING EXTRACTION PIPELINE")
        self.logger.info(f"{'='*80}")
        self.logger.info(f"Subjects to process: {len(subjects)}")
        self.logger.info(f"Performances per subject: {len(self.config['extraction']['performances'])}")
        self.logger.info(f"Output directory: {self.config['storage']['output_dir']}")
        
        # Process each subject
        for i, subject_id in enumerate(subjects, 1):
            self.logger.info(f"\n[{i}/{len(subjects)}] Processing {subject_id}...")
            
            try:
                self.process_subject(subject_id)
            except Exception as e:
                self.logger.error(f"FATAL ERROR processing {subject_id}: {e}")
                continue
                
        # Calculate processing time
        elapsed_time = datetime.now() - self.stats['start_time']
        
        # Final summary
        self.logger.info(f"\n{'='*80}")
        self.logger.info("EXTRACTION SUMMARY")
        self.logger.info(f"{'='*80}")
        
        # Statistics
        self.logger.info(f"Processing Statistics:")
        self.logger.info(f"  Subjects processed: {self.stats['subjects_processed']}")
        self.logger.info(f"  Performances downloaded: {self.stats['performances_downloaded']}")
        self.logger.info(f"  Performances extracted: {self.stats['performances_extracted']}")
        self.logger.info(f"  Performances failed: {self.stats['performances_failed']}")
        self.logger.info(f"  Total size extracted: {self.stats['total_size_gb']:.2f} GB")
        self.logger.info(f"  Processing time: {elapsed_time}")
        
        # Manifest summary
        completed = self.manifest_df[self.manifest_df['status'] == 'completed']
        failed = self.manifest_df[self.manifest_df['status'] == 'failed']
        download_failed = self.manifest_df[self.manifest_df['status'] == 'download_failed']
        
        self.logger.info(f"\nManifest Summary:")
        self.logger.info(f"  Completed: {len(completed)} performances")
        self.logger.info(f"  Failed extraction: {len(failed)} performances")
        self.logger.info(f"  Failed download: {len(download_failed)} performances")
        
        if len(completed) > 0:
            total_size = completed['size_gb'].sum()
            avg_size = completed['size_gb'].mean()
            self.logger.info(f"  Total extracted size: {total_size:.2f} GB")
            self.logger.info(f"  Average size per performance: {avg_size:.2f} GB")
            
        # List failures
        if len(failed) > 0 or len(download_failed) > 0:
            self.logger.warning("\nFailed operations:")
            for _, row in failed.iterrows():
                self.logger.warning(f"  ✗ Extraction failed: {row['subject']}/{row['performance']} - {row.get('error', 'Unknown')}")
            for _, row in download_failed.iterrows():
                self.logger.warning(f"  ✗ Download failed: {row['subject']}/{row['performance']} - {row.get('error', 'Unknown')}")
                
        # Successfully extracted subjects
        if len(completed) > 0:
            subjects_completed = completed['subject'].unique()
            self.logger.info(f"\nSuccessfully extracted subjects: {list(subjects_completed)}")
                
        self.logger.info(f"\nManifest saved to: {self.config['storage']['manifest_path']}")
        self.logger.info(f"Logs saved to: {self.config['storage']['log_dir']}")
        self.logger.info(f"\n{'='*80}")
        self.logger.info("EXTRACTION PIPELINE COMPLETE")
        self.logger.info(f"{'='*80}")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Streaming extraction for RenderMe360')
    parser.add_argument('--config', default='config.yaml', 
                       help='Path to configuration file')
    parser.add_argument('--subject', help='Process single subject (overrides config)')
    parser.add_argument('--performance', help='Process single performance (requires --subject)')
    
    args = parser.parse_args()
    
    # Initialize extractor
    extractor = StreamingExtractor(args.config)
    
    if args.subject:
        if args.performance:
            # Process single performance
            print(f"Processing single performance: {args.subject}/{args.performance}")
            smc_path = extractor.download_smc_with_rclone(args.subject, args.performance)
            if smc_path:
                extractor.extract_performance(smc_path, args.subject, args.performance)
        else:
            # Process single subject
            print(f"Processing single subject: {args.subject}")
            extractor.process_subject(args.subject)
    else:
        # Process all configured subjects
        extractor.run()


if __name__ == '__main__':
    main()