#!/usr/bin/env python3
"""
Visualize camera selections for RenderMe360 dataset.
Creates sample frame grids for each camera subset configuration.
"""

import json
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from pathlib import Path
from PIL import Image
import cv2
from typing import Dict

class CameraVisualization:
    def __init__(self, base_path: Path, selection_dir: Path):
        """
        Initialize visualizer.

        Args:
            base_path: Path to extracted frames (0026_s1_all)
            selection_dir: Path to camera selection JSONs
        """
        self.base_path = Path(base_path)
        self.selection_dir = Path(selection_dir)
        self.frame_number = 500  # Use frame 500 as sample

    def load_selection(self, config_name: str) -> Dict:
        """Load camera selection details."""
        selection_file = self.selection_dir / f"selection_{config_name}.json"
        with open(selection_file, 'r') as f:
            return json.load(f)

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
            placeholder = np.ones((1080, 1920, 3), dtype=np.uint8) * 128
            # Add text
            cv2.putText(placeholder, f"Camera {camera_id:02d}",
                       (850, 540), cv2.FONT_HERSHEY_SIMPLEX,
                       2, (255, 255, 255), 3)
            cv2.putText(placeholder, f"(No data)",
                       (850, 600), cv2.FONT_HERSHEY_SIMPLEX,
                       1, (200, 200, 200), 2)
            return placeholder

        # Load and resize image
        img = cv2.imread(str(frame_path))
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        # Resize to manageable size for grid
        target_height = 360
        aspect = img.shape[1] / img.shape[0]
        target_width = int(target_height * aspect)
        img = cv2.resize(img, (target_width, target_height))

        return img

    def create_sample_grid(self, selection: Dict, output_path: Path):
        """
        Create a grid of sample frames from selected cameras.

        Args:
            selection: Camera selection dictionary
            output_path: Path to save the output image
        """
        camera_ids = selection['camera_ids']
        n_cameras = len(camera_ids)

        # Determine grid layout
        if n_cameras <= 8:
            rows, cols = 2, 4
        elif n_cameras <= 12:
            rows, cols = 3, 4
        elif n_cameras <= 16:
            rows, cols = 4, 4
        elif n_cameras <= 20:
            rows, cols = 4, 5
        else:  # 21 cameras
            rows, cols = 3, 7

        # Create figure
        fig = plt.figure(figsize=(20, rows * 5))
        fig.suptitle(f"{selection['description']}\n"
                     f"{n_cameras} cameras | "
                     f"Storage: {selection['storage_per_subject_gb']}GB per subject | "
                     f"Total: {selection['total_storage_tb']}TB for 21 subjects",
                     fontsize=14, fontweight='bold')

        # Create grid
        gs = gridspec.GridSpec(rows, cols, figure=fig)

        # Load camera details
        camera_details = {cam['id']: cam for cam in selection['cameras']}

        # Plot each camera view
        for idx, cam_id in enumerate(camera_ids):
            row = idx // cols
            col = idx % cols

            if row < rows and col < cols:
                ax = fig.add_subplot(gs[row, col])

                # Load frame
                img = self.load_frame(cam_id)

                # Display image
                ax.imshow(img)

                # Add title with camera info
                cam_info = camera_details[cam_id]
                title = f"Camera {cam_id:02d}\n"
                title += f"{cam_info['yaw_deg']:.1f}°, Height: {cam_info['height_class']}"
                ax.set_title(title, fontsize=10)

                # Remove axes
                ax.set_xticks([])
                ax.set_yticks([])

                # Add border color based on position
                yaw = cam_info['yaw_deg']
                if -15 <= yaw <= 15:
                    color = 'green'  # Front center
                elif -45 <= yaw <= 45:
                    color = 'yellow'  # Front sides
                elif -90 <= yaw <= 90:
                    color = 'orange'  # Profiles
                else:
                    color = 'red'  # Rear

                for spine in ax.spines.values():
                    spine.set_edgecolor(color)
                    spine.set_linewidth(3)

        # Hide unused subplots
        for idx in range(n_cameras, rows * cols):
            row = idx // cols
            col = idx % cols
            ax = fig.add_subplot(gs[row, col])
            ax.axis('off')

        # Add legend
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor='green', label='Front Center (-15° to 15°)'),
            Patch(facecolor='yellow', label='Front Sides (±15° to ±45°)'),
            Patch(facecolor='orange', label='Profiles (±45° to ±90°)'),
            Patch(facecolor='red', label='Rear (beyond ±90°)')
        ]
        fig.legend(handles=legend_elements, loc='lower center', ncol=4, fontsize=10)

        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()

        print(f"Saved visualization to {output_path}")

    def create_polar_plot(self, selection: Dict, output_path: Path):
        """
        Create a polar plot showing camera positions.

        Args:
            selection: Camera selection dictionary
            output_path: Path to save the output image
        """
        fig = plt.figure(figsize=(10, 10))
        ax = fig.add_subplot(111, projection='polar')

        # Convert angles to radians
        selected_angles = []
        selected_heights = []
        selected_ids = []

        for cam in selection['cameras']:
            angle_rad = np.radians(cam['yaw_deg'])
            selected_angles.append(angle_rad)
            # Map height to radius (inverted since negative is higher)
            radius = 2.0 - (cam['height_m'] + 1.2)  # Normalize to 0.8-2.0 range
            selected_heights.append(radius)
            selected_ids.append(cam['id'])

        # Plot selected cameras
        scatter = ax.scatter(selected_angles, selected_heights,
                           c='red', s=200, alpha=0.8, edgecolors='black', linewidth=2,
                           label='Selected cameras')

        # Add camera IDs as labels
        for angle, height, cam_id in zip(selected_angles, selected_heights, selected_ids):
            ax.annotate(str(cam_id), (angle, height),
                       fontsize=8, ha='center', va='center', color='white', weight='bold')

        # Set labels
        ax.set_theta_zero_location('N')  # 0° at top
        ax.set_theta_direction(-1)  # Clockwise
        ax.set_title(f"{selection['description']}\n{len(selected_ids)} cameras selected",
                    fontsize=12, fontweight='bold', pad=20)

        # Set radial limits and labels
        ax.set_ylim(0, 3)
        ax.set_yticks([0.8, 1.5, 2.2])
        ax.set_yticklabels(['Lower', 'Middle', 'Upper'])

        # Add grid
        ax.grid(True, alpha=0.3)

        # Add angle labels
        angles = np.arange(0, 360, 30)
        ax.set_thetagrids(angles)

        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()

        print(f"Saved polar plot to {output_path}")


def main():
    """Main execution function."""
    # Paths
    base_path = Path("/ssd4/zhuoyuan/renderme360_temp/FULL_EXTRACTION_BOTH/0026_s1_all")
    selection_dir = Path("/ssd4/zhuoyuan/renderme360_temp/test_download/visualizations/camera_selection")
    output_dir = selection_dir  # Save visualizations in same directory

    # Initialize visualizer
    viz = CameraVisualization(base_path, selection_dir)

    # Check if we can find sample frames
    sample_cam_path = base_path / "from_raw/images/cam_00"
    if sample_cam_path.exists():
        # List first few files to understand naming convention
        files = list(sample_cam_path.glob("*.jpg"))[:5]
        if files:
            print(f"Found sample files: {[f.name for f in files]}")
            # Use frame 500 as a good middle frame
            viz.frame_number = 500
        else:
            print("Warning: No sample frames found, will use placeholders")

    print(f"Using frame number: {viz.frame_number}")

    # Generate visualizations for each configuration
    configs = ['21cam_360', '20cam', '16cam', '12cam', '8cam']

    for config in configs:
        print(f"\nProcessing {config} configuration...")

        # Load selection
        selection = viz.load_selection(config)

        # Create sample frame grid
        grid_path = output_dir / f"sample_frames_{config.replace('cam', '_cameras')}.png"
        viz.create_sample_grid(selection, grid_path)

        # Create polar plot
        polar_path = output_dir / f"polar_plot_{config}.png"
        viz.create_polar_plot(selection, polar_path)

    print(f"\nAll visualizations complete!")
    print(f"Output directory: {output_dir}")


if __name__ == "__main__":
    main()