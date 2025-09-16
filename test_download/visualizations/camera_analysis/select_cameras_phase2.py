#!/usr/bin/env python3
"""
Phase 2: Camera Selection for RenderMe360 Dataset
Selects optimal camera subsets based on Phase 1 calibration analysis
for audio-driven avatar research with facial animation focus.
"""

import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple
import yaml

class CameraSelector:
    def __init__(self, metrics_path: Path):
        """
        Initialize with camera metrics from Phase 1.

        Args:
            metrics_path: Path to camera_metrics_60cam.json
        """
        self.metrics_path = Path(metrics_path)
        self.camera_metrics = {}
        self.load_metrics()

    def load_metrics(self):
        """Load camera metrics from Phase 1 analysis."""
        with open(self.metrics_path, 'r') as f:
            self.camera_metrics = json.load(f)
        print(f"Loaded metrics for {len(self.camera_metrics)} cameras")

    def categorize_cameras(self) -> Dict[str, List]:
        """
        Categorize cameras by angular regions for facial research.
        CORRECTED: ±180° is front (face), 0° is rear (back of head)

        Returns:
            Dictionary with categorized camera lists
        """
        categories = {
            'front_center': [],      # ±165° to ±180° - Face straight on
            'front_left': [],        # -165° to -135° - Left front quarter
            'front_right': [],       # 135° to 165° - Right front quarter
            'left_profile': [],      # -135° to -90° - Left profile
            'right_profile': [],     # 90° to 135° - Right profile
            'rear_left': [],         # -90° to -45° - Left rear quarter
            'rear_right': [],        # 45° to 90° - Right rear quarter
            'rear_center': []        # -45° to 45° - Back of head
        }

        for cam_id, metrics in self.camera_metrics.items():
            yaw = metrics['yaw_deg']
            height = metrics['height_class']
            entry = {
                'id': int(cam_id),
                'yaw': yaw,
                'height': height,
                'height_m': metrics['height']
            }

            # Corrected categorization based on actual orientation
            if yaw > 165 or yaw < -165:
                categories['front_center'].append(entry)
            elif -165 <= yaw < -135:
                categories['front_left'].append(entry)
            elif 135 < yaw <= 165:
                categories['front_right'].append(entry)
            elif -135 <= yaw < -90:
                categories['left_profile'].append(entry)
            elif 90 < yaw <= 135:
                categories['right_profile'].append(entry)
            elif -90 <= yaw < -45:
                categories['rear_left'].append(entry)
            elif 45 < yaw <= 90:
                categories['rear_right'].append(entry)
            else:  # -45 <= yaw <= 45
                categories['rear_center'].append(entry)

        # Sort each category by yaw
        for cat in categories:
            categories[cat].sort(key=lambda x: x['yaw'])

        return categories

    def select_16_cameras(self) -> Dict:
        """
        Select 16-camera optimal set for maximum quality.
        Prioritizes facial coverage with multi-height variation.
        CORRECTED: Focus on front (±180°) for facial research.
        """
        categories = self.categorize_cameras()
        selected = []

        # Front Center: ALL cameras (critical for facial animation - around ±180°)
        selected.extend([cam['id'] for cam in categories['front_center']])

        # Front Sides: Take all or most (these show 3/4 face views)
        # Left front side
        if categories['front_left']:
            selected.extend([cam['id'] for cam in categories['front_left'][:3]])

        # Right front side
        if categories['front_right']:
            selected.extend([cam['id'] for cam in categories['front_right'][:3]])

        # Profile Views: 2 cameras (one per side for profile views)
        # Left profile
        if categories['left_profile']:
            # Pick middle of left profile range
            selected.append(categories['left_profile'][len(categories['left_profile'])//2]['id'])

        # Right profile
        if categories['right_profile']:
            # Pick middle of right profile range
            selected.append(categories['right_profile'][len(categories['right_profile'])//2]['id'])

        # Rear: Minimal coverage (back of head - around 0°)
        # Only 2 cameras for basic 360° consistency
        if categories['rear_center']:
            # Pick two with different heights from rear center
            rear_sorted = sorted(categories['rear_center'], key=lambda x: abs(x['yaw']))
            if rear_sorted:
                selected.append(rear_sorted[0]['id'])  # Closest to 0°
                if len(rear_sorted) > 5:
                    selected.append(rear_sorted[5]['id'])  # Another one with some spacing

        return {
            'camera_ids': sorted(selected),
            'count': len(selected),
            'description': '16-camera optimal set with maximum facial coverage',
            'storage_per_subject_gb': 75,
            'total_storage_tb': 1.55
        }

    def select_12_cameras(self) -> Dict:
        """
        Select 12-camera balanced set.
        Good quality with reduced storage.
        CORRECTED: Focus on front (±180°) for facial research.
        """
        categories = self.categorize_cameras()
        selected = []

        # Front Center: Take most/all (around ±180°, face straight on)
        front_center = categories['front_center']
        if len(front_center) >= 4:
            # Select with height variation
            selected.extend([cam['id'] for cam in front_center[:4]])
        else:
            selected.extend([cam['id'] for cam in front_center])

        # Front Sides: 4 cameras (2 per side)
        # Left front side
        if categories['front_left']:
            selected.extend([cam['id'] for cam in categories['front_left'][:2]])

        # Right front side
        if categories['front_right']:
            selected.extend([cam['id'] for cam in categories['front_right'][:2]])

        # Profiles: 2 cameras (one per side)
        if categories['left_profile']:
            selected.append(categories['left_profile'][0]['id'])
        if categories['right_profile']:
            selected.append(categories['right_profile'][0]['id'])

        # Rear: 2 cameras for minimal back coverage (around 0°)
        if categories['rear_center']:
            rear_sorted = sorted(categories['rear_center'], key=lambda x: abs(x['yaw']))
            if rear_sorted:
                selected.append(rear_sorted[0]['id'])
                if len(rear_sorted) > 3:
                    selected.append(rear_sorted[3]['id'])

        return {
            'camera_ids': sorted(selected),
            'count': len(selected),
            'description': '12-camera balanced set for quality/storage balance',
            'storage_per_subject_gb': 57,
            'total_storage_tb': 1.16
        }

    def select_8_cameras(self) -> Dict:
        """
        Select 8-camera minimal set for testing.
        Basic coverage with minimal storage.
        CORRECTED: Focus on front (±180°) for facial research.
        """
        categories = self.categorize_cameras()
        selected = []

        # Front Center: 3 cameras (around ±180°, different heights if possible)
        front_center = categories['front_center']
        if len(front_center) >= 3:
            # Pick with height variety
            selected.extend([cam['id'] for cam in front_center[:3]])
        else:
            selected.extend([cam['id'] for cam in front_center])

        # Front Sides: 2 cameras (one per side)
        if categories['front_left']:
            selected.append(categories['front_left'][0]['id'])
        if categories['front_right']:
            selected.append(categories['front_right'][0]['id'])

        # Profiles: 1 camera (alternate sides or pick most important)
        if categories['left_profile']:
            selected.append(categories['left_profile'][0]['id'])
        elif categories['right_profile']:
            selected.append(categories['right_profile'][0]['id'])

        # Rear: 2 cameras for basic 360° coverage (around 0°)
        if categories['rear_center']:
            rear_sorted = sorted(categories['rear_center'], key=lambda x: abs(x['yaw']))
            if rear_sorted:
                selected.append(rear_sorted[0]['id'])
                if len(rear_sorted) > 2:
                    selected.append(rear_sorted[2]['id'])

        return {
            'camera_ids': sorted(selected),
            'count': len(selected),
            'description': '8-camera minimal set for quick testing',
            'storage_per_subject_gb': 38,
            'total_storage_tb': 0.77
        }

    def generate_config(self, camera_ids: List[int], config_name: str, output_path: Path):
        """
        Generate YAML configuration file with selected cameras.

        Args:
            camera_ids: List of selected camera IDs
            config_name: Name for the configuration
            output_path: Path to save the config file
        """
        # Load base config as template
        base_config_path = Path("/ssd2/zhuoyuan/renderme360_temp/test_download/process_data/config_21id.yaml")
        with open(base_config_path, 'r') as f:
            config = yaml.safe_load(f)

        # Update with selected cameras
        config['extraction']['cameras'] = camera_ids
        config['extraction']['camera_selection'] = {
            'type': config_name,
            'count': len(camera_ids),
            'camera_list': camera_ids
        }

        # Save config
        with open(output_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

        print(f"Saved config to {output_path}")

    def print_selection_summary(self, selection: Dict):
        """Print summary of selected cameras with details."""
        print(f"\n{'='*60}")
        print(f"{selection['description']}")
        print(f"{'='*60}")
        print(f"Number of cameras: {selection['count']}")
        print(f"Camera IDs: {selection['camera_ids']}")
        print(f"Storage per subject: {selection['storage_per_subject_gb']}GB")
        print(f"Total storage (21 subjects): {selection['total_storage_tb']}TB")

        # Print details for each camera
        print(f"\nDetailed camera information:")
        for cam_id in selection['camera_ids']:
            metrics = self.camera_metrics[str(cam_id)]
            print(f"  Cam {cam_id:2d}: {metrics['yaw_deg']:6.1f}°, "
                  f"Height: {metrics['height_class']} ({metrics['height']:.2f}m)")

    def save_selection_json(self, selection: Dict, output_path: Path):
        """Save selection details to JSON file."""
        # Add detailed camera info
        detailed_selection = selection.copy()
        detailed_selection['cameras'] = []

        for cam_id in selection['camera_ids']:
            metrics = self.camera_metrics[str(cam_id)]
            detailed_selection['cameras'].append({
                'id': cam_id,
                'yaw_deg': metrics['yaw_deg'],
                'height_class': metrics['height_class'],
                'height_m': metrics['height'],
                'position': metrics['position']
            })

        with open(output_path, 'w') as f:
            json.dump(detailed_selection, f, indent=2)

        print(f"Saved selection details to {output_path}")


def main():
    """Main execution function."""
    # Path to camera metrics from Phase 1
    metrics_path = Path("/ssd2/zhuoyuan/renderme360_temp/test_download/visualizations/camera_analysis/camera_metrics_60cam.json")

    # Output directory for configs and selections
    output_dir = Path("/ssd2/zhuoyuan/renderme360_temp/test_download/visualizations/camera_selection")
    output_dir.mkdir(parents=True, exist_ok=True)

    config_dir = Path("/ssd2/zhuoyuan/renderme360_temp/test_download/process_data")

    # Initialize selector
    selector = CameraSelector(metrics_path)

    # Generate all three selections
    print("Generating camera selections for RenderMe360 dataset...")

    # 16-camera optimal set
    selection_16 = selector.select_16_cameras()
    selector.print_selection_summary(selection_16)
    selector.save_selection_json(selection_16, output_dir / "selection_16cam.json")
    selector.generate_config(selection_16['camera_ids'], '16cam_optimal',
                            config_dir / "config_21id_16cam.yaml")

    # 12-camera balanced set
    selection_12 = selector.select_12_cameras()
    selector.print_selection_summary(selection_12)
    selector.save_selection_json(selection_12, output_dir / "selection_12cam.json")
    selector.generate_config(selection_12['camera_ids'], '12cam_balanced',
                            config_dir / "config_21id_12cam.yaml")

    # 8-camera minimal set
    selection_8 = selector.select_8_cameras()
    selector.print_selection_summary(selection_8)
    selector.save_selection_json(selection_8, output_dir / "selection_8cam.json")
    selector.generate_config(selection_8['camera_ids'], '8cam_minimal',
                            config_dir / "config_21id_8cam.yaml")

    print(f"\nAll selections complete!")
    print(f"Selection details saved to: {output_dir}")
    print(f"Config files saved to: {config_dir}")


if __name__ == "__main__":
    main()