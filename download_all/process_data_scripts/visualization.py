#!/usr/bin/env python3
"""
Visualization helper for RenderMe360 extraction pipeline.
Creates camera grids and helps with camera selection for 360° coverage.
"""

import cv2
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
import pandas as pd
import json


def create_camera_grid(subject_dir, performance="s1_all", frame_id=0, output_path=None):
    """
    Create a grid visualization of all 60 cameras for a specific frame.
    This helps identify which cameras to select for 360° coverage.
    
    Args:
        subject_dir: Path to extracted subject directory
        performance: Performance name (e.g., "s1_all")
        frame_id: Frame number to visualize
        output_path: Where to save the visualization (optional)
    """
    subject_path = Path(subject_dir)
    perf_path = subject_path / performance
    images_dir = perf_path / "images"
    
    if not images_dir.exists():
        print(f"Error: Images directory not found: {images_dir}")
        return
        
    # Find all camera directories
    camera_dirs = sorted([d for d in images_dir.iterdir() if d.is_dir()])
    num_cameras = len(camera_dirs)
    
    print(f"Found {num_cameras} cameras in {perf_path}")
    
    if num_cameras == 0:
        print("No camera directories found!")
        return
        
    # Determine grid size (aim for roughly square grid)
    grid_cols = int(np.ceil(np.sqrt(num_cameras)))
    grid_rows = int(np.ceil(num_cameras / grid_cols))
    
    # Create figure with subplots
    fig = plt.figure(figsize=(20, 20))
    fig.suptitle(f'Camera Grid - {subject_path.name}/{performance} - Frame {frame_id}', 
                 fontsize=16, y=1.02)
    
    # Load and display each camera view
    for i, cam_dir in enumerate(camera_dirs):
        cam_id = int(cam_dir.name.replace('cam_', ''))
        
        # Load image
        img_path = cam_dir / f'frame_{frame_id:06d}.jpg'
        if not img_path.exists():
            print(f"Warning: Image not found: {img_path}")
            continue
            
        img = cv2.imread(str(img_path))
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # Resize for display (to fit all in grid)
        display_height = 200
        aspect_ratio = img.shape[1] / img.shape[0]
        display_width = int(display_height * aspect_ratio)
        img_small = cv2.resize(img, (display_width, display_height))
        
        # Add to subplot
        ax = plt.subplot(grid_rows, grid_cols, i + 1)
        ax.imshow(img_small)
        ax.set_title(f'Cam {cam_id:02d}', fontsize=10, pad=2)
        ax.axis('off')
        
        # Highlight certain cameras (e.g., every 6th for 360° coverage)
        if cam_id % 6 == 0:
            ax.patch.set_edgecolor('red')
            ax.patch.set_linewidth(3)
            
    plt.tight_layout()
    
    # Save or show
    if output_path:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        print(f"Camera grid saved to: {output_file}")
    else:
        plt.show()
        
    plt.close()
    
    # Print recommendations
    print("\nCamera Selection Recommendations:")
    print("  For 360° coverage with 10 cameras: [0, 6, 12, 18, 24, 30, 36, 42, 48, 54]")
    print("  For 360° coverage with 12 cameras: [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55]")
    print("  For 360° coverage with 15 cameras: [0, 4, 8, 12, 16, 20, 24, 28, 32, 36, 40, 44, 48, 52, 56]")
    

def analyze_camera_coverage(calibration_dir):
    """
    Analyze camera positions from calibration matrices.
    Suggest optimal subset for 360° coverage.
    
    Args:
        calibration_dir: Path to calibration directory
    """
    calib_path = Path(calibration_dir)
    
    # Load all camera calibrations
    all_calib_file = calib_path / "all_cameras.npy"
    if not all_calib_file.exists():
        print(f"Error: Calibration file not found: {all_calib_file}")
        return
        
    all_calibs = np.load(all_calib_file, allow_pickle=True).item()
    
    # Extract camera positions from RT matrices
    camera_positions = []
    camera_ids = []
    
    for cam_id_str, calib_data in sorted(all_calibs.items()):
        cam_id = int(cam_id_str)
        RT = calib_data['RT']
        
        # Camera position in world coordinates: -R^T * t
        R = RT[:3, :3]
        t = RT[:3, 3]
        cam_pos = -R.T @ t
        
        camera_positions.append(cam_pos)
        camera_ids.append(cam_id)
        
    camera_positions = np.array(camera_positions)
    
    # Calculate azimuth angles (angle in XY plane)
    azimuths = np.arctan2(camera_positions[:, 1], camera_positions[:, 0])
    azimuths_deg = np.degrees(azimuths)
    
    # Sort cameras by azimuth
    sorted_indices = np.argsort(azimuths_deg)
    
    print("\nCamera Analysis:")
    print(f"  Total cameras: {len(camera_ids)}")
    print(f"  Azimuth range: {azimuths_deg.min():.1f}° to {azimuths_deg.max():.1f}°")
    
    # Suggest evenly distributed cameras
    for num_cameras in [6, 10, 12, 15, 20]:
        step = len(camera_ids) // num_cameras
        selected_indices = sorted_indices[::step][:num_cameras]
        selected_ids = [camera_ids[i] for i in selected_indices]
        
        print(f"\n  {num_cameras} cameras (every {360/num_cameras:.0f}°):")
        print(f"    Camera IDs: {selected_ids}")
        
    # Create visualization of camera positions
    fig = plt.figure(figsize=(12, 10))
    
    # Top-down view
    ax1 = plt.subplot(2, 2, 1)
    ax1.scatter(camera_positions[:, 0], camera_positions[:, 1], alpha=0.6)
    for i, cam_id in enumerate(camera_ids):
        ax1.annotate(str(cam_id), (camera_positions[i, 0], camera_positions[i, 1]),
                    fontsize=8, alpha=0.8)
    ax1.set_xlabel('X')
    ax1.set_ylabel('Y')
    ax1.set_title('Top-down View')
    ax1.axis('equal')
    ax1.grid(True, alpha=0.3)
    
    # Side view
    ax2 = plt.subplot(2, 2, 2)
    ax2.scatter(camera_positions[:, 0], camera_positions[:, 2], alpha=0.6)
    ax2.set_xlabel('X')
    ax2.set_ylabel('Z')
    ax2.set_title('Side View')
    ax2.axis('equal')
    ax2.grid(True, alpha=0.3)
    
    # Azimuth distribution
    ax3 = plt.subplot(2, 2, 3, projection='polar')
    ax3.scatter(azimuths, np.ones_like(azimuths), alpha=0.6)
    for i, cam_id in enumerate(camera_ids):
        ax3.annotate(str(cam_id), (azimuths[i], 1), fontsize=8, alpha=0.8)
    ax3.set_title('Azimuth Distribution')
    
    # Camera height distribution
    ax4 = plt.subplot(2, 2, 4)
    ax4.bar(camera_ids, camera_positions[:, 2])
    ax4.set_xlabel('Camera ID')
    ax4.set_ylabel('Height (Z)')
    ax4.set_title('Camera Heights')
    ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # Save figure
    output_path = calib_path.parent / "visualizations" / "camera_positions.png"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"\nCamera position analysis saved to: {output_path}")
    
    plt.close()
    
    return camera_positions, camera_ids, azimuths_deg


def create_extraction_summary(manifest_path, output_dir=None):
    """
    Create visual summary of extraction progress from manifest.
    
    Args:
        manifest_path: Path to MANIFEST.csv
        output_dir: Where to save summary figures (optional)
    """
    manifest_file = Path(manifest_path)
    
    if not manifest_file.exists():
        print(f"Manifest not found: {manifest_file}")
        return
        
    # Load manifest
    df = pd.read_csv(manifest_file)
    
    print("\nExtraction Summary:")
    print(f"  Total entries: {len(df)}")
    
    # Status summary
    status_counts = df['status'].value_counts()
    print("\n  Status breakdown:")
    for status, count in status_counts.items():
        print(f"    {status}: {count}")
        
    # Create visualizations
    fig = plt.figure(figsize=(15, 10))
    
    # Status pie chart
    ax1 = plt.subplot(2, 3, 1)
    ax1.pie(status_counts.values, labels=status_counts.index, autopct='%1.1f%%')
    ax1.set_title('Extraction Status')
    
    # Size distribution
    if 'size_gb' in df.columns:
        ax2 = plt.subplot(2, 3, 2)
        completed_df = df[df['status'] == 'completed']
        if not completed_df.empty:
            ax2.hist(completed_df['size_gb'].dropna(), bins=20, edgecolor='black')
            ax2.set_xlabel('Size (GB)')
            ax2.set_ylabel('Count')
            ax2.set_title('Size Distribution')
            
    # Subjects progress
    ax3 = plt.subplot(2, 3, 3)
    subject_stats = df.groupby('subject')['status'].value_counts().unstack(fill_value=0)
    subject_stats.plot(kind='bar', stacked=True, ax=ax3)
    ax3.set_xlabel('Subject')
    ax3.set_ylabel('Performances')
    ax3.set_title('Progress by Subject')
    ax3.legend(title='Status', bbox_to_anchor=(1.05, 1), loc='upper left')
    
    # Performance distribution
    ax4 = plt.subplot(2, 3, 4)
    perf_stats = df.groupby('performance')['status'].value_counts().unstack(fill_value=0)
    perf_stats.plot(kind='bar', ax=ax4)
    ax4.set_xlabel('Performance')
    ax4.set_ylabel('Count')
    ax4.set_title('Status by Performance Type')
    ax4.legend(title='Status')
    
    # Timeline (if timestamp available)
    if 'timestamp' in df.columns:
        ax5 = plt.subplot(2, 3, 5)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        timeline = df.groupby(df['timestamp'].dt.date).size()
        timeline.plot(ax=ax5, marker='o')
        ax5.set_xlabel('Date')
        ax5.set_ylabel('Extractions')
        ax5.set_title('Extraction Timeline')
        ax5.grid(True, alpha=0.3)
        
    # Storage usage
    if 'size_gb' in df.columns:
        ax6 = plt.subplot(2, 3, 6)
        cumulative_size = df[df['status'] == 'completed'].sort_values('timestamp')['size_gb'].cumsum()
        if not cumulative_size.empty:
            cumulative_size.plot(ax=ax6, marker='o')
            ax6.set_xlabel('Extraction Number')
            ax6.set_ylabel('Cumulative Size (GB)')
            ax6.set_title('Storage Usage Over Time')
            ax6.grid(True, alpha=0.3)
            
    plt.tight_layout()
    
    # Save or show
    if output_dir:
        output_path = Path(output_dir) / "extraction_summary.png"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"\nSummary saved to: {output_path}")
    else:
        plt.show()
        
    plt.close()
    
    # Print failed extractions if any
    failed_df = df[df['status'] == 'failed']
    if not failed_df.empty:
        print("\nFailed Extractions:")
        for _, row in failed_df.iterrows():
            print(f"  {row['subject']}/{row['performance']}: {row.get('error', 'Unknown error')}")


def suggest_camera_subset(num_cameras_total=60, num_to_select=10):
    """
    Suggest evenly distributed camera IDs for 360° coverage.
    
    Args:
        num_cameras_total: Total number of cameras available
        num_to_select: Number of cameras to select
        
    Returns:
        List of suggested camera IDs
    """
    if num_to_select > num_cameras_total:
        print(f"Warning: Cannot select {num_to_select} cameras from {num_cameras_total} total")
        return list(range(num_cameras_total))
        
    # Calculate step size for even distribution
    step = num_cameras_total / num_to_select
    
    # Select cameras at regular intervals
    selected = []
    for i in range(num_to_select):
        cam_id = int(i * step)
        selected.append(cam_id)
        
    return selected


def create_sample_frames_grid(subject_dir, performance="s1_all", camera_id=0, 
                             num_frames=9, output_path=None):
    """
    Create a grid showing multiple frames from a single camera.
    Useful for checking temporal consistency.
    
    Args:
        subject_dir: Path to extracted subject directory  
        performance: Performance name
        camera_id: Which camera to visualize
        num_frames: Number of frames to show
        output_path: Where to save the visualization
    """
    subject_path = Path(subject_dir)
    cam_dir = subject_path / performance / "images" / f"cam_{camera_id:02d}"
    
    if not cam_dir.exists():
        print(f"Error: Camera directory not found: {cam_dir}")
        return
        
    # Get all available frames
    frame_files = sorted(cam_dir.glob("frame_*.jpg"))
    total_frames = len(frame_files)
    
    if total_frames == 0:
        print("No frames found!")
        return
        
    # Select frames at regular intervals
    frame_step = max(1, total_frames // num_frames)
    selected_frames = frame_files[::frame_step][:num_frames]
    
    # Create grid
    grid_cols = int(np.ceil(np.sqrt(num_frames)))
    grid_rows = int(np.ceil(num_frames / grid_cols))
    
    fig = plt.figure(figsize=(15, 12))
    fig.suptitle(f'Frame Sequence - Camera {camera_id:02d} - {performance}', fontsize=14)
    
    for i, frame_file in enumerate(selected_frames):
        # Extract frame number from filename
        frame_num = int(frame_file.stem.replace('frame_', ''))
        
        # Load image
        img = cv2.imread(str(frame_file))
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # Resize for display
        img_small = cv2.resize(img, (400, 300))
        
        # Add to subplot
        ax = plt.subplot(grid_rows, grid_cols, i + 1)
        ax.imshow(img_small)
        ax.set_title(f'Frame {frame_num}', fontsize=10)
        ax.axis('off')
        
    plt.tight_layout()
    
    if output_path:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        print(f"Frame grid saved to: {output_file}")
    else:
        plt.show()
        
    plt.close()


def main():
    """Main entry point for standalone visualization."""
    import argparse
    
    parser = argparse.ArgumentParser(description='RenderMe360 Visualization Helper')
    parser.add_argument('command', choices=['camera_grid', 'analyze', 'summary', 'frames'],
                       help='Visualization command to run')
    parser.add_argument('--subject_dir', help='Path to extracted subject directory')
    parser.add_argument('--performance', default='s1_all', help='Performance name')
    parser.add_argument('--frame', type=int, default=0, help='Frame ID to visualize')
    parser.add_argument('--camera', type=int, default=0, help='Camera ID for frame sequence')
    parser.add_argument('--output', help='Output path for visualization')
    parser.add_argument('--manifest', help='Path to MANIFEST.csv')
    parser.add_argument('--calibration', help='Path to calibration directory')
    
    args = parser.parse_args()
    
    if args.command == 'camera_grid':
        if not args.subject_dir:
            print("Error: --subject_dir required for camera_grid")
            return
        create_camera_grid(args.subject_dir, args.performance, args.frame, args.output)
        
    elif args.command == 'analyze':
        if not args.calibration:
            # Try to find calibration in subject dir
            if args.subject_dir:
                calib_dir = Path(args.subject_dir) / args.performance / "calibration"
            else:
                print("Error: --calibration or --subject_dir required for analyze")
                return
        else:
            calib_dir = args.calibration
        analyze_camera_coverage(calib_dir)
        
    elif args.command == 'summary':
        if not args.manifest:
            print("Error: --manifest required for summary")
            return
        create_extraction_summary(args.manifest, args.output)
        
    elif args.command == 'frames':
        if not args.subject_dir:
            print("Error: --subject_dir required for frames")
            return
        create_sample_frames_grid(args.subject_dir, args.performance, 
                                 args.camera, output_path=args.output)
        
    # Also print camera subset suggestions
    print("\n" + "="*60)
    print("Camera Selection Suggestions for 360° Coverage:")
    print("="*60)
    for num in [6, 10, 12, 15]:
        subset = suggest_camera_subset(60, num)
        print(f"{num:2d} cameras: {subset}")


if __name__ == '__main__':
    main()