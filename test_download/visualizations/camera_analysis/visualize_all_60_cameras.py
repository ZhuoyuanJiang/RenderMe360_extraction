#!/usr/bin/env python3
"""
Visualize all 60 cameras from RenderMe360 dataset.
Creates a comprehensive grid showing every camera view.
"""

import json
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from pathlib import Path
import cv2
from typing import Dict

class FullCameraVisualization:
    def __init__(self, base_path: Path, metrics_path: Path):
        """
        Initialize visualizer for all 60 cameras.

        Args:
            base_path: Path to extracted frames (0026_s1_all)
            metrics_path: Path to camera_metrics_60cam.json
        """
        self.base_path = Path(base_path)
        self.metrics_path = Path(metrics_path)
        self.frame_number = 500  # Use frame 500 as sample
        self.camera_metrics = {}
        self.load_metrics()

    def load_metrics(self):
        """Load camera metrics from Phase 1 analysis."""
        with open(self.metrics_path, 'r') as f:
            self.camera_metrics = json.load(f)
        print(f"Loaded metrics for {len(self.camera_metrics)} cameras")

    def load_frame(self, camera_id: int, frame_num: int = None) -> np.ndarray:
        """
        Load a frame from specified camera.

        Args:
            camera_id: Camera ID (0-59)
            frame_num: Frame number (default: self.frame_number)

        Returns:
            Image array or placeholder if not found
        """
        if frame_num is None:
            frame_num = self.frame_number

        # Try to load from extracted data (frame_XXXXXX.jpg format)
        frame_path = self.base_path / f"from_raw/images/cam_{camera_id:02d}/frame_{frame_num:06d}.jpg"

        if not frame_path.exists():
            # Create placeholder image
            placeholder = np.ones((540, 960, 3), dtype=np.uint8) * 128
            # Add text
            cv2.putText(placeholder, f"Camera {camera_id:02d}",
                       (400, 270), cv2.FONT_HERSHEY_SIMPLEX,
                       1.5, (255, 255, 255), 2)
            cv2.putText(placeholder, f"(No data)",
                       (400, 310), cv2.FONT_HERSHEY_SIMPLEX,
                       0.8, (200, 200, 200), 1)
            return placeholder

        # Load and resize image
        img = cv2.imread(str(frame_path))
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        # Resize to smaller size for 60-camera grid
        target_height = 270  # Smaller for 60 cameras
        aspect = img.shape[1] / img.shape[0]
        target_width = int(target_height * aspect)
        img = cv2.resize(img, (target_width, target_height))

        return img

    def create_60_camera_grid(self, output_path: Path):
        """
        Create a grid showing all 60 cameras with detailed information.

        Args:
            output_path: Path to save the output image
        """
        # Sort cameras by yaw angle for logical arrangement
        sorted_cameras = sorted(self.camera_metrics.items(),
                              key=lambda x: x[1]['yaw_deg'])

        # Create figure - 10x6 grid for 60 cameras
        rows, cols = 10, 6
        fig = plt.figure(figsize=(30, 50))

        # Main title
        fig.suptitle("RenderMe360 - All 60 Cameras\n"
                     "Sorted by Yaw Angle (±180°=Front/Face, 0°=Rear/Back of Head)",
                     fontsize=20, fontweight='bold', y=0.995)

        # Create grid
        gs = gridspec.GridSpec(rows, cols, figure=fig,
                             hspace=0.3, wspace=0.2,
                             top=0.99, bottom=0.01)

        # Plot each camera
        for idx, (cam_id_str, metrics) in enumerate(sorted_cameras):
            cam_id = int(cam_id_str)
            row = idx // cols
            col = idx % cols

            if row < rows and col < cols:
                ax = fig.add_subplot(gs[row, col])

                # Load frame
                img = self.load_frame(cam_id)

                # Display image
                ax.imshow(img)

                # Determine color based on position
                yaw = metrics['yaw_deg']
                if yaw > 165 or yaw < -165:
                    color = 'green'  # Front center (face straight on)
                    region = 'FRONT CENTER'
                elif (135 < yaw <= 165) or (-165 <= yaw < -135):
                    color = 'yellowgreen'  # Front sides
                    region = 'FRONT SIDE'
                elif (90 < yaw <= 135) or (-135 <= yaw < -90):
                    color = 'orange'  # Profiles
                    region = 'PROFILE'
                elif (45 < yaw <= 90) or (-90 <= yaw < -45):
                    color = 'salmon'  # Rear sides
                    region = 'REAR SIDE'
                else:  # -45 to 45
                    color = 'red'  # Rear center (back of head)
                    region = 'REAR CENTER'

                # Add title with camera info
                title = f"Cam {cam_id:02d} | {yaw:.1f}°\n"
                title += f"Height: {metrics['height_class']} ({metrics['height']:.2f}m)\n"
                title += f"{region}"
                ax.set_title(title, fontsize=8, color=color, weight='bold')

                # Remove axes
                ax.set_xticks([])
                ax.set_yticks([])

                # Add border color
                for spine in ax.spines.values():
                    spine.set_edgecolor(color)
                    spine.set_linewidth(2)

        # Add legend at bottom
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor='green', label='Front Center (±165° to ±180°) - Face straight on'),
            Patch(facecolor='yellowgreen', label='Front Sides (±135° to ±165°) - 3/4 face views'),
            Patch(facecolor='orange', label='Profiles (±90° to ±135°) - Side views'),
            Patch(facecolor='salmon', label='Rear Sides (±45° to ±90°) - Back angles'),
            Patch(facecolor='red', label='Rear Center (-45° to 45°) - Back of head')
        ]
        fig.legend(handles=legend_elements, loc='lower center',
                  ncol=5, fontsize=12, bbox_to_anchor=(0.5, -0.01))

        # Add statistics text
        stats_text = self.generate_statistics()
        fig.text(0.5, 0.008, stats_text, ha='center', fontsize=10,
                bbox=dict(boxstyle="round,pad=0.3", facecolor="lightgray", alpha=0.5))

        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()

        print(f"Saved 60-camera visualization to {output_path}")

    def generate_statistics(self) -> str:
        """Generate statistics text for the visualization."""
        # Count cameras by region
        regions = {
            'Front Center': 0,
            'Front Sides': 0,
            'Profiles': 0,
            'Rear Sides': 0,
            'Rear Center': 0
        }

        heights = {'U': 0, 'M': 0, 'L': 0}

        for metrics in self.camera_metrics.values():
            yaw = metrics['yaw_deg']
            if yaw > 165 or yaw < -165:
                regions['Front Center'] += 1
            elif (135 < yaw <= 165) or (-165 <= yaw < -135):
                regions['Front Sides'] += 1
            elif (90 < yaw <= 135) or (-135 <= yaw < -90):
                regions['Profiles'] += 1
            elif (45 < yaw <= 90) or (-90 <= yaw < -45):
                regions['Rear Sides'] += 1
            else:
                regions['Rear Center'] += 1

            heights[metrics['height_class']] += 1

        stats = "Camera Distribution: "
        stats += " | ".join([f"{k}: {v}" for k, v in regions.items()])
        stats += f"\nHeight Distribution: Upper: {heights['U']} | Middle: {heights['M']} | Lower: {heights['L']}"

        return stats

    def create_angular_distribution_plot(self, output_path: Path):
        """
        Create a plot showing angular distribution of all cameras.

        Args:
            output_path: Path to save the output image
        """
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10))

        # Extract yaw angles and heights
        yaws = []
        heights = []
        camera_ids = []

        for cam_id, metrics in self.camera_metrics.items():
            yaws.append(metrics['yaw_deg'])
            heights.append(metrics['height'])
            camera_ids.append(int(cam_id))

        # Top plot: Angular distribution
        ax1.scatter(yaws, [1]*len(yaws), c=heights, cmap='viridis', s=100, alpha=0.7)
        for i, cam_id in enumerate(camera_ids):
            ax1.annotate(str(cam_id), (yaws[i], 1),
                        xytext=(0, 5), textcoords='offset points',
                        fontsize=6, ha='center')

        ax1.set_xlabel('Yaw Angle (degrees)', fontsize=12)
        ax1.set_title('Camera Angular Distribution\n(±180°=Front/Face, 0°=Rear/Back)', fontsize=14)
        ax1.set_xlim(-180, 180)
        ax1.set_ylim(0.9, 1.2)
        ax1.set_xticks(np.arange(-180, 181, 30))
        ax1.grid(True, alpha=0.3)
        ax1.axvline(x=0, color='red', linestyle='--', alpha=0.5, label='Rear (back of head)')
        ax1.axvline(x=180, color='green', linestyle='--', alpha=0.5, label='Front (face)')
        ax1.axvline(x=-180, color='green', linestyle='--', alpha=0.5)
        ax1.legend()

        # Bottom plot: Height vs Yaw
        scatter = ax2.scatter(yaws, heights, c=camera_ids, cmap='tab20', s=100, alpha=0.7)
        for i, cam_id in enumerate(camera_ids):
            ax2.annotate(str(cam_id), (yaws[i], heights[i]),
                        xytext=(0, 2), textcoords='offset points',
                        fontsize=6, ha='center')

        ax2.set_xlabel('Yaw Angle (degrees)', fontsize=12)
        ax2.set_ylabel('Height (meters)', fontsize=12)
        ax2.set_title('Camera Height vs Yaw Angle', fontsize=14)
        ax2.set_xlim(-180, 180)
        ax2.set_xticks(np.arange(-180, 181, 30))
        ax2.grid(True, alpha=0.3)
        ax2.axvline(x=0, color='red', linestyle='--', alpha=0.3)
        ax2.axvline(x=180, color='green', linestyle='--', alpha=0.3)
        ax2.axvline(x=-180, color='green', linestyle='--', alpha=0.3)

        plt.colorbar(scatter, ax=ax2, label='Camera ID')

        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()

        print(f"Saved angular distribution plot to {output_path}")


def main():
    """Main execution function."""
    # Paths
    base_path = Path("/ssd2/zhuoyuan/renderme360_temp/FULL_EXTRACTION_BOTH/0026_s1_all")
    metrics_path = Path("/ssd2/zhuoyuan/renderme360_temp/test_download/visualizations/camera_analysis/camera_metrics_60cam.json")
    output_dir = Path("/ssd2/zhuoyuan/renderme360_temp/test_download/visualizations/camera_selection")

    # Initialize visualizer
    viz = FullCameraVisualization(base_path, metrics_path)

    # Create comprehensive 60-camera grid
    grid_path = output_dir / "sample_frames_60_cameras.png"
    viz.create_60_camera_grid(grid_path)

    # Create angular distribution plot
    dist_path = output_dir / "angular_distribution_60_cameras.png"
    viz.create_angular_distribution_plot(dist_path)

    print(f"\nVisualization complete!")
    print(f"Output files:")
    print(f"  - {grid_path}")
    print(f"  - {dist_path}")


if __name__ == "__main__":
    main()