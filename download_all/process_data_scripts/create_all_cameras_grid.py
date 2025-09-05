#!/usr/bin/env python3
"""
Create a comprehensive grid showing all 38 camera views from s3_all.
"""

import cv2
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import matplotlib.gridspec as gridspec

def create_all_cameras_grid(subject_id="0026", frame_id=100, output_path=None):
    """
    Create a grid showing all 38 camera views from s3_all at the same frame.
    
    Args:
        subject_id: Subject to visualize
        frame_id: Frame number (all cameras show this same frame/timestamp)
        output_path: Where to save the visualization
    """
    # Path to subject data
    base_dir = Path(f'/ssd2/zhuoyuan/renderme360_temp/download_all/subjects/{subject_id}')
    images_dir = base_dir / "s3_all" / "images"
    
    if not images_dir.exists():
        print(f"Error: Images directory not found: {images_dir}")
        return
    
    # Get all available camera directories
    camera_dirs = sorted([d for d in images_dir.iterdir() if d.is_dir() and d.name.startswith("cam_")])
    num_cameras = len(camera_dirs)
    
    print(f"Found {num_cameras} cameras with data")
    
    # Create figure with optimal grid layout
    # For 38 cameras, use 6x7 grid (42 slots, 4 empty)
    grid_rows = 6
    grid_cols = 7
    
    fig = plt.figure(figsize=(28, 24))
    fig.suptitle(f'All {num_cameras} Camera Views - Subject {subject_id} - s3_all - Frame {frame_id}\n'
                 f'(All images from the same timestamp)', fontsize=20, y=1.01)
    
    # Camera IDs that are available
    available_cameras = []
    
    for idx, cam_dir in enumerate(camera_dirs):
        cam_id = int(cam_dir.name.replace("cam_", ""))
        available_cameras.append(cam_id)
        
        # Load image for this camera at the specified frame
        img_path = cam_dir / f"frame_{frame_id:06d}.jpg"
        
        # Create subplot
        ax = plt.subplot(grid_rows, grid_cols, idx + 1)
        
        if img_path.exists():
            # Load and display image
            img = cv2.imread(str(img_path))
            if img is not None:
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                
                # Display at reasonable resolution
                ax.imshow(img)
                ax.set_title(f'Camera {cam_id:02d}', fontsize=12, fontweight='bold')
            else:
                ax.text(0.5, 0.5, f'Camera {cam_id:02d}\n(Error loading)', 
                       ha='center', va='center', fontsize=10)
                ax.set_xlim(0, 1)
                ax.set_ylim(0, 1)
        else:
            ax.text(0.5, 0.5, f'Camera {cam_id:02d}\n(Frame {frame_id} not found)', 
                   ha='center', va='center', fontsize=10)
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
        
        ax.axis('off')
    
    # Hide remaining empty slots
    for empty_idx in range(idx + 2, grid_rows * grid_cols + 1):
        ax = plt.subplot(grid_rows, grid_cols, empty_idx)
        ax.axis('off')
    
    plt.tight_layout()
    
    # Add camera info at the bottom of the figure
    fig.text(0.5, 0.01, f"Cameras present: {available_cameras}", 
             ha='center', fontsize=10, wrap=True)
    
    if output_path:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_file, dpi=100, bbox_inches='tight')
        print(f"All cameras grid saved to: {output_file}")
    else:
        plt.show()
    
    plt.close()
    
    return available_cameras

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Create grid of all camera views')
    parser.add_argument('--subject', default='0026', help='Subject ID')
    parser.add_argument('--frame', type=int, default=100, help='Frame number to display')
    parser.add_argument('--output', 
                       default='/ssd2/zhuoyuan/renderme360_temp/download_all/visualizations/camera_analysis/all_38_cameras_grid.png',
                       help='Output path for visualization')
    
    args = parser.parse_args()
    
    print(f"Creating grid of all cameras for subject {args.subject}, frame {args.frame}...")
    cameras = create_all_cameras_grid(args.subject, args.frame, args.output)
    print(f"\nTotal cameras visualized: {len(cameras) if cameras else 0}")