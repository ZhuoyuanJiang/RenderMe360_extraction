#!/usr/bin/env python3
"""
Create improved 3D cylindrical visualization of camera positions.
Shows cameras arranged in a cylinder around the subject.
"""

import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from pathlib import Path
import matplotlib.patches as mpatches

def create_cylindrical_visualization(output_path=None):
    """Create improved 3D visualization showing cylindrical camera arrangement."""
    
    # Load calibration data
    base_dir = Path('/ssd4/zhuoyuan/renderme360_temp/download_all/subjects/0026')
    calib_file = base_dir / 's3_all' / 'calibration' / 'all_cameras.npy'
    
    if not calib_file.exists():
        print(f"Calibration file not found: {calib_file}")
        return
    
    calibs = np.load(calib_file, allow_pickle=True).item()
    
    # Extract camera positions using correct method
    camera_positions = {}
    for cam_id_str, calib in calibs.items():
        cam_id = int(cam_id_str)
        RT = calib['RT']
        R = RT[:3, :3]
        t = RT[:3, 3]
        # Use Method 2: camera position = -t (cameras surround subject)
        cam_pos = -t
        camera_positions[cam_id] = cam_pos
    
    # Prepare data for visualization
    cam_ids = sorted(camera_positions.keys())
    positions = np.array([camera_positions[cid] for cid in cam_ids])
    
    # Calculate cylindrical coordinates
    r = np.sqrt(positions[:, 0]**2 + positions[:, 1]**2)  # radial distance
    theta = np.arctan2(positions[:, 1], positions[:, 0])  # azimuth angle
    z = positions[:, 2]  # height
    
    # Create figure with multiple views
    fig = plt.figure(figsize=(20, 16))
    
    # 1. 3D Cylindrical view
    ax1 = fig.add_subplot(221, projection='3d')
    
    # Draw cylinder wireframe to show the arrangement
    u = np.linspace(0, 2 * np.pi, 50)
    h = np.linspace(min(z) - 0.1, max(z) + 0.1, 10)
    x_cyl = np.outer(np.mean(r), np.cos(u))
    y_cyl = np.outer(np.mean(r), np.sin(u))
    z_cyl = np.outer(np.ones(np.size(u)), h)
    
    # Plot cylinder surface (very transparent)
    ax1.plot_surface(x_cyl.T, y_cyl.T, z_cyl, alpha=0.1, color='gray')
    
    # Color cameras by height
    heights_normalized = (z - z.min()) / (z.max() - z.min())
    colors = plt.cm.viridis(heights_normalized)
    
    # Plot cameras
    scatter = ax1.scatter(positions[:, 0], positions[:, 1], positions[:, 2],
                         c=z, cmap='viridis', s=150, alpha=0.9, edgecolors='black')
    
    # Add camera labels
    for i, cam_id in enumerate(cam_ids):
        ax1.text(positions[i, 0], positions[i, 1], positions[i, 2],
                f'{cam_id}', fontsize=8, ha='center')
    
    # Add subject at origin
    ax1.scatter([0], [0], [np.mean(z)], color='red', s=300, marker='*', 
               label='Subject', edgecolors='black', linewidth=2)
    
    # Add vertical axis line
    ax1.plot([0, 0], [0, 0], [min(z) - 0.2, max(z) + 0.2], 
            'r--', alpha=0.5, linewidth=2)
    
    ax1.set_xlabel('X (m)', fontsize=10)
    ax1.set_ylabel('Y (m)', fontsize=10)
    ax1.set_zlabel('Z (m)', fontsize=10)
    ax1.set_title('3D Cylindrical Camera Arrangement', fontsize=12, fontweight='bold')
    ax1.view_init(elev=20, azim=45)
    
    # Add colorbar
    cbar1 = plt.colorbar(scatter, ax=ax1, pad=0.1, shrink=0.8)
    cbar1.set_label('Height (m)', fontsize=10)
    
    # 2. Top-down view with polar grid
    ax2 = fig.add_subplot(222, projection='polar')
    
    # Plot cameras in polar coordinates
    scatter2 = ax2.scatter(theta, r, c=z, cmap='viridis', s=100, alpha=0.9)
    
    # Add camera labels
    for i, cam_id in enumerate(cam_ids):
        ax2.annotate(str(cam_id), (theta[i], r[i]), fontsize=8, ha='center')
    
    # Mark subject at center
    ax2.scatter([0], [0], color='red', s=200, marker='*')
    
    ax2.set_title('Top-Down View (Polar)', fontsize=12, fontweight='bold', pad=20)
    ax2.set_ylim(0, max(r) * 1.1)
    
    # Add radial distance labels
    ax2.set_rlabel_position(90)
    ax2.set_ylabel('Distance (m)', labelpad=30)
    
    # 3. Unwrapped cylindrical view (angle vs height)
    ax3 = fig.add_subplot(223)
    
    # Convert theta to degrees for easier reading
    theta_deg = np.degrees(theta)
    
    # Sort by angle for connected line
    sort_idx = np.argsort(theta_deg)
    theta_sorted = theta_deg[sort_idx]
    z_sorted = z[sort_idx]
    cam_ids_sorted = [cam_ids[i] for i in sort_idx]
    
    # Plot cameras
    scatter3 = ax3.scatter(theta_sorted, z_sorted, c=z_sorted, cmap='viridis', 
                          s=100, alpha=0.9, edgecolors='black')
    
    # Add camera labels
    for i, cam_id in enumerate(cam_ids_sorted):
        ax3.annotate(str(cam_id), (theta_sorted[i], z_sorted[i]), 
                    fontsize=8, ha='center', va='bottom')
    
    # Add grid
    ax3.grid(True, alpha=0.3)
    ax3.set_xlabel('Azimuth Angle (degrees)', fontsize=10)
    ax3.set_ylabel('Height (m)', fontsize=10)
    ax3.set_title('Unwrapped Cylinder View', fontsize=12, fontweight='bold')
    ax3.set_xlim(-180, 180)
    
    # Add horizontal lines for height levels
    unique_heights = np.unique(np.round(z, 1))
    for h in unique_heights:
        ax3.axhline(y=h, color='gray', alpha=0.2, linestyle='--')
    
    # 4. Height distribution
    ax4 = fig.add_subplot(224)
    
    # Create bar chart of camera heights
    bars = ax4.bar(range(len(cam_ids)), z[np.argsort(cam_ids)], 
                   color=colors[np.argsort(cam_ids)], alpha=0.9, edgecolor='black')
    
    ax4.set_xlabel('Camera ID', fontsize=10)
    ax4.set_ylabel('Height (m)', fontsize=10)
    ax4.set_title('Camera Height Distribution', fontsize=12, fontweight='bold')
    ax4.set_xticks(range(0, len(cam_ids), 5))
    ax4.set_xticklabels([cam_ids[i] for i in np.argsort(cam_ids)][::5], rotation=45)
    ax4.grid(True, alpha=0.3, axis='y')
    
    # Add median line
    median_height = np.median(z)
    ax4.axhline(y=median_height, color='red', linestyle='--', 
               label=f'Median: {median_height:.2f}m', alpha=0.7)
    ax4.legend()
    
    # Main title
    fig.suptitle('Camera Setup Analysis - Full 360° Cylindrical Arrangement\n'
                 f'{len(cam_ids)} Cameras Surrounding Subject in s3_all Performance',
                 fontsize=16, fontweight='bold', y=0.98)
    
    # Add legend explaining the visualization
    legend_text = (
        "Visualization Notes:\n"
        "• Cameras arranged in cylinder surrounding subject\n"
        "• Colors represent camera height (purple=low, yellow=high)\n"
        "• Red star marks subject position at origin\n"
        "• Numbers are camera IDs"
    )
    fig.text(0.02, 0.02, legend_text, fontsize=9, 
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    plt.tight_layout()
    
    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"Cylindrical visualization saved to: {output_path}")
    else:
        plt.show()
    
    plt.close()
    
    # Print summary statistics
    print("\nCamera Position Statistics:")
    print(f"  Total cameras: {len(cam_ids)}")
    print(f"  Height range: {z.min():.2f}m to {z.max():.2f}m")
    print(f"  Radial distance: {r.min():.2f}m to {r.max():.2f}m")
    print(f"  Average radius: {r.mean():.2f}m")
    
    # Identify height levels
    height_levels = {}
    for i, cid in enumerate(cam_ids):
        h_level = round(z[i], 1)
        if h_level not in height_levels:
            height_levels[h_level] = []
        height_levels[h_level].append(cid)
    
    print(f"\nCameras by height level:")
    for h_level in sorted(height_levels.keys()):
        print(f"  {h_level:.1f}m: {len(height_levels[h_level])} cameras - {height_levels[h_level]}")

if __name__ == "__main__":
    output_path = Path('/ssd4/zhuoyuan/renderme360_temp/download_all/visualizations/camera_analysis/cylindrical_camera_visualization.png')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    create_cylindrical_visualization(output_path)