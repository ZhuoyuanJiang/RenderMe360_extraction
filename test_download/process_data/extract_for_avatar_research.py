#!/usr/bin/env python3
"""
Optimized RenderMe360 extraction for audio-driven 3D avatar research
Extracts exactly what you need for your research project
"""

import os
import sys
import cv2
import numpy as np
from pathlib import Path
from renderme_360_reader import SMCReader
import json
from tqdm import tqdm
from datetime import datetime

class AvatarDataExtractor:
    def __init__(self, subject_id='0026', output_base=None):
        self.subject_id = subject_id
        self.anno_dir = Path('/ssd4/zhuoyuan/renderme360_temp/test_download/anno')
        self.raw_dir = Path(f'/ssd4/zhuoyuan/renderme360_temp/test_download/raw/{subject_id}')
        
        # Put output in a research-friendly location
        if output_base is None:
            self.output_base = Path(f'/ssd4/zhuoyuan/renderme360_temp/avatar_research_data/{subject_id}')
        else:
            self.output_base = Path(output_base) / subject_id
        
        self.output_base.mkdir(parents=True, exist_ok=True)
        
    def extract_speech_performance(self, performance_id='s1_all', 
                                 extract_all_frames=False, 
                                 extract_all_cameras=False,
                                 frame_sampling_rate=10):
        """
        Extract speech performance data optimized for audio-driven avatar research
        
        Args:
            performance_id: 's1_all', 's2_all', 's3_all', or 's4_all'
            extract_all_frames: If True, extract all frames (warning: large!)
            extract_all_cameras: If True, extract all 60 views (warning: very large!)
            frame_sampling_rate: If not extracting all, sample every N frames
        """
        
        print(f"\n{'='*60}")
        print(f"Extracting Speech Performance: {performance_id}")
        print(f"Purpose: Audio-visual synchronization training data")
        print(f"{'='*60}")
        
        # Setup paths
        anno_file = self.anno_dir / f'{self.subject_id}_{performance_id}_anno.smc'
        raw_file = self.raw_dir / f'{self.subject_id}_{performance_id}_raw.smc'
        output_dir = self.output_base / f'speech_{performance_id}'
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Extract from anno file (smaller, has audio + keypoints)
        print("\n1. Extracting from annotation file...")
        anno_reader = SMCReader(str(anno_file))
        
        # Extract audio - CRITICAL for your research
        print("   Extracting audio...")
        audio_data = anno_reader.get_audio()
        if audio_data:
            sr = int(np.array(audio_data['sample_rate']))
            audio_array = np.array(audio_data['audio'])
            
            # Save audio
            audio_path = output_dir / 'audio.mp3'
            anno_reader.writemp3(str(audio_path), sr, audio_array, normalized=True)
            
            # Save audio metadata
            np.savez(output_dir / 'audio_data.npz', 
                    audio=audio_array, 
                    sample_rate=sr)
            
            print(f"   ✓ Audio saved: {audio_array.shape}, SR={sr}")
        
        # Camera setup for your 360° requirement
        if extract_all_cameras:
            camera_ids = [f'{i:02d}' for i in range(60)]
        else:
            # Strategic camera selection for 360° coverage
            camera_ids = [
                '00', '06', '12', '18', '24', '30', '36', '42', '48', '54',  # Every 6th camera
                '15', '45',  # Additional side views
                '25', '26', '27'  # Front arc for lip sync
            ]
        
        camera_info = anno_reader.get_Camera_info()
        total_frames = camera_info['num_frame']
        
        # Frame selection
        if extract_all_frames:
            frame_ids = list(range(total_frames))
        else:
            frame_ids = list(range(0, total_frames, frame_sampling_rate))
        
        print(f"\n2. Extraction plan:")
        print(f"   Cameras: {len(camera_ids)} views")
        print(f"   Frames: {len(frame_ids)} / {total_frames} total")
        
        # Extract calibration (essential for 3D reconstruction)
        print("\n3. Extracting camera calibration...")
        calibrations = anno_reader.get_Calibration_all()
        np.save(output_dir / 'calibration.npy', calibrations)
        
        # Save selected camera list
        with open(output_dir / 'cameras.json', 'w') as f:
            json.dump(camera_ids, f)
        
        # Extract keypoints for lip sync
        print("\n4. Extracting keypoints for lip synchronization...")
        keypoints_2d = {}
        keypoints_3d = {}
        
        for frame_id in tqdm(frame_ids[:100], desc="Extracting keypoints"):  # Sample first 100
            # 3D keypoints
            kpt3d = anno_reader.get_Keypoints3d(frame_id)
            if kpt3d is not None:
                keypoints_3d[frame_id] = kpt3d
            
            # 2D keypoints from front camera
            kpt2d = anno_reader.get_Keypoints2d('25', frame_id)
            if kpt2d is not None:
                if '25' not in keypoints_2d:
                    keypoints_2d['25'] = {}
                keypoints_2d['25'][frame_id] = kpt2d
        
        np.savez(output_dir / 'keypoints_3d.npz', **keypoints_3d)
        np.savez(output_dir / 'keypoints_2d_cam25.npz', **keypoints_2d.get('25', {}))
        
        # Extract images from raw file (high resolution)
        if raw_file.exists():
            print("\n5. Extracting high-resolution images from raw file...")
            raw_reader = SMCReader(str(raw_file))
            
            # Create organized structure
            for cam_id in tqdm(camera_ids[:3], desc="Extracting cameras"):  # Demo: first 3 cameras
                cam_dir = output_dir / 'images' / f'cam_{cam_id}'
                cam_dir.mkdir(parents=True, exist_ok=True)
                
                for frame_id in frame_ids[:10]:  # Demo: first 10 frames
                    img = raw_reader.get_img(cam_id, 'color', frame_id)
                    img_path = cam_dir / f'frame_{frame_id:06d}.jpg'
                    cv2.imwrite(str(img_path), img, [cv2.IMWRITE_JPEG_QUALITY, 95])
        
        # Create metadata file
        metadata = {
            'subject_id': self.subject_id,
            'performance': performance_id,
            'type': 'speech',
            'audio_available': True,
            'total_frames': total_frames,
            'extracted_frames': len(frame_ids),
            'cameras': camera_ids,
            'resolution': camera_info['resolution'],
            'keypoints_106': True,  # 106 facial landmarks
            'useful_for': [
                'audio_driven_animation',
                'lip_sync_training', 
                '360_degree_consistency',
                'talking_head_generation'
            ]
        }
        
        with open(output_dir / 'metadata.json', 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"\n✓ Speech performance extracted to: {output_dir}")
        return output_dir
    
    def extract_expression_performance(self, performance_id='e0', 
                                      extract_flame=True,
                                      extract_uv=True,
                                      frame_sampling_rate=10):
        """
        Extract expression performance for FLAME parameters and 3D face modeling
        """
        
        print(f"\n{'='*60}")
        print(f"Extracting Expression Performance: {performance_id}")
        print(f"Purpose: 3D face animation parameters")
        print(f"{'='*60}")
        
        # Setup paths
        anno_file = self.anno_dir / f'{self.subject_id}_{performance_id}_anno.smc'
        output_dir = self.output_base / f'expression_{performance_id}'
        output_dir.mkdir(parents=True, exist_ok=True)
        
        reader = SMCReader(str(anno_file))
        camera_info = reader.get_Camera_info()
        total_frames = camera_info['num_frame']
        frame_ids = list(range(0, total_frames, frame_sampling_rate))
        
        if extract_flame:
            print("\n1. Extracting FLAME parameters...")
            flame_params = {}
            
            for frame_id in tqdm(frame_ids[:50], desc="FLAME extraction"):
                flame = reader.get_FLAME(frame_id)
                if flame:
                    flame_params[frame_id] = {
                        'global_pose': flame['global_pose'],
                        'neck_pose': flame['neck_pose'],
                        'jaw_pose': flame['jaw_pose'],
                        'shape': flame['shape'],
                        'exp': flame['exp'],
                        'trans': flame['trans']
                    }
            
            np.savez(output_dir / 'flame_params.npz', **flame_params)
            print(f"   ✓ FLAME parameters saved for {len(flame_params)} frames")
        
        if extract_uv:
            print("\n2. Extracting UV textures...")
            uv_dir = output_dir / 'uv_textures'
            uv_dir.mkdir(exist_ok=True)
            
            for frame_id in frame_ids[:5]:  # Sample first 5
                uv = reader.get_uv(frame_id)
                if uv is not None:
                    cv2.imwrite(str(uv_dir / f'uv_{frame_id:06d}.jpg'), uv)
        
        # Extract scan mesh (reference geometry)
        print("\n3. Extracting reference scan mesh...")
        scan = reader.get_scanmesh()
        if scan:
            ply_path = output_dir / 'scan_mesh.ply'
            reader.write_ply(scan, str(ply_path))
            print(f"   ✓ Scan mesh saved: {scan['vertex'].shape[0]} vertices")
        
        print(f"\n✓ Expression performance extracted to: {output_dir}")
        return output_dir
    
    def create_research_summary(self):
        """Create a summary optimized for your avatar research"""
        
        summary_path = self.output_base / 'RESEARCH_SUMMARY.md'
        
        with open(summary_path, 'w') as f:
            f.write(f"# RenderMe360 Data - Subject {self.subject_id}\n\n")
            f.write("## For Audio-Driven 3D Avatar Research\n\n")
            
            f.write("### Available Data Types\n\n")
            f.write("1. **Speech Performances (s1-s4)**\n")
            f.write("   - Synchronized audio and multi-view video\n")
            f.write("   - 60 camera views for 360° coverage\n")
            f.write("   - 106 facial landmarks per frame\n")
            f.write("   - Perfect for audio-to-visual training\n\n")
            
            f.write("2. **Expression Performances (e0-e11)**\n")
            f.write("   - FLAME face model parameters\n")
            f.write("   - UV texture maps\n") 
            f.write("   - High-res 3D scan mesh\n")
            f.write("   - Good for expression transfer\n\n")
            
            f.write("### Recommended Usage\n\n")
            f.write("**For Head-Only Avatar (Scope A):**\n")
            f.write("- Use speech performances for audio-lip sync training\n")
            f.write("- Use FLAME parameters from expressions for 3D control\n")
            f.write("- Cameras 24-27 best for frontal lip reading\n\n")
            
            f.write("**For Upper Body (Scope B):**\n")
            f.write("- Full image crops needed (not just face)\n")
            f.write("- Use calibration for 3D pose estimation\n\n")
            
            f.write("**Key Files:**\n")
            f.write("- `speech_*/audio.mp3`: Synchronized speech audio\n")
            f.write("- `speech_*/keypoints_3d.npz`: 3D facial landmarks\n")
            f.write("- `expression_*/flame_params.npz`: FLAME animation parameters\n")
            f.write("- `*/calibration.npy`: Camera matrices for 3D reconstruction\n\n")
            
            f.write("### Data Statistics\n")
            f.write(f"- Subject ID: {self.subject_id}\n")
            f.write("- Image Resolution: 2048 x 2448\n")
            f.write("- Camera Views: 60\n")
            f.write("- Facial Landmarks: 106 points\n")
            f.write("- FLAME Parameters: shape(100), expression(50)\n")
        
        print(f"\nResearch summary saved to: {summary_path}")

def main():
    print("="*60)
    print("RenderMe360 Extraction for Avatar Research")
    print("Optimized for audio-driven 3D talking head generation")
    print("="*60)
    
    extractor = AvatarDataExtractor(subject_id='0026')
    
    # For initial exploration, extract samples
    print("\n📊 EXTRACTION PLAN FOR YOUR RESEARCH:")
    print("1. One speech performance (for audio-visual sync)")
    print("2. One expression performance (for FLAME parameters)")
    print("3. Strategic camera selection for 360° coverage")
    print("4. Sampled frames to manage storage\n")
    
    # Extract one speech performance (most important for your research)
    extractor.extract_speech_performance(
        performance_id='s1_all',
        extract_all_frames=False,  # Set True for full dataset
        extract_all_cameras=False,  # Set True for all 60 views
        frame_sampling_rate=30  # Every 30th frame for initial exploration
    )
    
    # Extract one expression performance (for FLAME)
    extractor.extract_expression_performance(
        performance_id='e0',
        extract_flame=True,
        extract_uv=True,
        frame_sampling_rate=10
    )
    
    # Create research summary
    extractor.create_research_summary()
    
    print("\n" + "="*60)
    print("EXTRACTION COMPLETE!")
    print(f"Data saved to: {extractor.output_base}")
    print("\nNext steps for your research:")
    print("1. Check speech_s1_all/ for audio-visual data")
    print("2. Check expression_e0/ for FLAME parameters")
    print("3. Read RESEARCH_SUMMARY.md for usage guide")
    print("4. Adjust extraction parameters and re-run for full data")
    print("="*60)

if __name__ == '__main__':
    main()