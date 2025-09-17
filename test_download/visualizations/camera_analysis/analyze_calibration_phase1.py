#!/usr/bin/env python3
"""
Phase 1: Camera Calibration Analysis for RenderMe360
Extracts and analyzes actual camera parameters from calibration data
to enable informed camera subset selection.
"""

import numpy as np
import json
from pathlib import Path
import math
from typing import Dict, List, Tuple

class CameraCalibrationAnalyzer:
    def __init__(self, calibration_path: Path):
        """
        Initialize analyzer with path to calibration data.

        Args:
            calibration_path: Path to all_cameras.npy file
        """
        self.calibration_path = Path(calibration_path)
        self.calibrations = {}
        self.camera_metrics = {}

    def load_calibrations(self) -> Dict:
        """Load calibration data from numpy file."""
        print(f"Loading calibrations from {self.calibration_path}")
        self.calibrations = np.load(self.calibration_path, allow_pickle=True).item()

        # Convert keys to integers if they're strings
        self.calibrations = {int(k): v for k, v in self.calibrations.items()}
        print(f"Loaded calibrations for {len(self.calibrations)} cameras")
        return self.calibrations

    def extract_camera_position(self, RT: np.ndarray) -> np.ndarray:
        """
        Extract camera position from RT matrix.
        For RenderMe360, the translation vector directly contains camera position.

        Returns:
            Camera position in world coordinates [x, y, z]
        """
        # Camera position is directly in the translation component
        cam_pos = RT[:3, 3]
        return cam_pos

    def compute_yaw_angle(self, position: np.ndarray) -> float:
        """
        Compute yaw angle (azimuth) of camera around subject.

        Args:
            position: Camera position [x, y, z]

        Returns:
            Yaw angle in degrees (±180° = front/face, 0° = back of head,
                                   90° = right profile, -90° = left profile)
        """
        # Assuming subject is at origin and Y is up
        # Yaw is angle in XZ plane
        yaw_rad = math.atan2(position[0], position[2])
        yaw_deg = math.degrees(yaw_rad)
        return yaw_deg

    def classify_height(self, position: np.ndarray, all_heights: List[float]) -> str:
        """
        Classify camera into height ring (Upper/Mid/Lower).

        Args:
            position: Camera position [x, y, z]
            all_heights: List of all camera heights for relative classification

        Returns:
            Height classification: 'U' (Upper), 'M' (Mid), or 'L' (Lower)
        """
        height = position[1]

        # Use absolute thresholds based on actual camera distribution
        # Analysis shows three distinct height clusters:
        # Upper ring: around -1.1m to -1.16m (above eye level)
        # Middle ring: around -0.45m to -0.58m (eye level)
        # Lower ring: around -0.44m to 0.06m (below eye level)

        # Note: Y axis is inverted in RenderMe360 (negative is up)
        if height < -0.9:  # Upper ring cameras
            return 'U'
        elif height < -0.44:  # Middle ring cameras (includes -0.58m cameras)
            return 'M'
        else:  # Lower ring cameras
            return 'L'

    def classify_fov(self, K: np.ndarray, image_width: int = 2448) -> str:
        """
        Classify FOV type based on intrinsic matrix.

        Args:
            K: Camera intrinsic matrix (3x3)
            image_width: Image width in pixels

        Returns:
            FOV type: 'Small' (narrow/telephoto) or 'Large' (wide)
        """
        # Extract focal length (fx)
        fx = K[0, 0]

        # Compute horizontal FOV
        # FOV = 2 * atan(width / (2 * fx))
        fov_rad = 2 * math.atan(image_width / (2 * fx))
        fov_deg = math.degrees(fov_rad)

        # Classify based on FOV
        # Typical ranges: Small FOV < 50°, Large FOV > 60°
        if fov_deg < 55:
            return 'Small'
        else:
            return 'Large'

    def analyze_all_cameras(self) -> Dict:
        """
        Analyze all cameras and compute comprehensive metrics.
        """
        if not self.calibrations:
            self.load_calibrations()

        # First pass: collect all positions and heights
        all_positions = {}
        all_heights = []

        for cam_id, calib in self.calibrations.items():
            RT = calib['RT']
            position = self.extract_camera_position(RT)
            all_positions[cam_id] = position
            all_heights.append(position[1])

        # Second pass: compute all metrics
        for cam_id, calib in self.calibrations.items():
            position = all_positions[cam_id]

            # Compute metrics
            distance = np.linalg.norm(position)
            yaw = self.compute_yaw_angle(position)
            height_class = self.classify_height(position, all_heights)
            fov_type = self.classify_fov(calib['K'])

            # Determine hemisphere (corrected: ±180° is front, 0° is rear)
            # Front hemisphere: cameras facing the subject's face (around ±180°)
            # Rear hemisphere: cameras facing back of head (around 0°)
            hemisphere = 'front' if (yaw > 90 or yaw < -90) else 'rear'

            # Store metrics
            self.camera_metrics[cam_id] = {
                'camera_id': cam_id,
                'position': position.tolist(),
                'distance': float(distance),
                'yaw_deg': float(yaw),
                'height': float(position[1]),
                'height_class': height_class,
                'fov_type': fov_type,
                'hemisphere': hemisphere,
                'focal_length': float(calib['K'][0, 0])
            }

        return self.camera_metrics

    def analyze_angular_sectors(self) -> Dict:
        """
        Analyze camera distribution across 60-degree angular sectors.
        Helps understand the uniformity of camera placement around the subject.

        Returns:
            Dictionary with camera counts per angular sector
        """
        if not self.camera_metrics:
            self.analyze_all_cameras()

        # Define 60° sectors for comprehensive coverage analysis
        sector_counts = {
            'front_center_-30_to_30': 0,     # -30° to 30°
            'right_side_30_to_90': 0,       # 30° to 90°
            'left_side_-90_to_-30': 0,      # -90° to -30°
            'back_center_150_to_-150': 0,   # 150° to -150° (or ±180°)
            'right_back_90_to_150': 0,      # 90° to 150°
            'left_back_-150_to_-90': 0      # -150° to -90°
        }

        # Also track which cameras are in each sector for detailed analysis
        sector_cameras = {
            'front_center_-30_to_30': [],
            'right_side_30_to_90': [],
            'left_side_-90_to_-30': [],
            'back_center_150_to_-150': [],
            'right_back_90_to_150': [],
            'left_back_-150_to_-90': []
        }

        # Classify each camera into its sector
        for cam_id, metrics in self.camera_metrics.items():
            yaw = metrics['yaw_deg']

            if -30 <= yaw <= 30:
                sector_counts['front_center_-30_to_30'] += 1
                sector_cameras['front_center_-30_to_30'].append(cam_id)
            elif 30 < yaw <= 90:
                sector_counts['right_side_30_to_90'] += 1
                sector_cameras['right_side_30_to_90'].append(cam_id)
            elif -90 <= yaw < -30:
                sector_counts['left_side_-90_to_-30'] += 1
                sector_cameras['left_side_-90_to_-30'].append(cam_id)
            elif yaw > 150 or yaw < -150:
                sector_counts['back_center_150_to_-150'] += 1
                sector_cameras['back_center_150_to_-150'].append(cam_id)
            elif 90 < yaw <= 150:
                sector_counts['right_back_90_to_150'] += 1
                sector_cameras['right_back_90_to_150'].append(cam_id)
            elif -150 <= yaw < -90:
                sector_counts['left_back_-150_to_-90'] += 1
                sector_cameras['left_back_-150_to_-90'].append(cam_id)

        # Calculate percentages
        total_cameras = len(self.camera_metrics)
        sector_percentages = {
            sector: (count / total_cameras * 100) if total_cameras > 0 else 0
            for sector, count in sector_counts.items()
        }

        return {
            'counts': sector_counts,
            'percentages': sector_percentages,
            'camera_ids': sector_cameras
        }

    def generate_summary_statistics(self) -> Dict:
        """Generate summary statistics of camera distribution."""
        if not self.camera_metrics:
            self.analyze_all_cameras()

        # Collect statistics
        yaws = [m['yaw_deg'] for m in self.camera_metrics.values()]
        heights = [m['height'] for m in self.camera_metrics.values()]
        distances = [m['distance'] for m in self.camera_metrics.values()]

        # Count by category
        height_counts = {'U': 0, 'M': 0, 'L': 0}
        fov_counts = {'Small': 0, 'Large': 0}
        hemisphere_counts = {'front': 0, 'rear': 0}

        for metrics in self.camera_metrics.values():
            height_counts[metrics['height_class']] += 1
            fov_counts[metrics['fov_type']] += 1
            hemisphere_counts[metrics['hemisphere']] += 1

        # Calculate angular gaps
        sorted_yaws = sorted(yaws)
        gaps = []
        for i in range(len(sorted_yaws)):
            next_i = (i + 1) % len(sorted_yaws)
            gap = sorted_yaws[next_i] - sorted_yaws[i]
            if gap < 0:
                gap += 360
            gaps.append(gap)

        # Get angular sector analysis
        sector_analysis = self.analyze_angular_sectors()

        summary = {
            'total_cameras': len(self.camera_metrics),
            'yaw_range': [min(yaws), max(yaws)],
            'height_range': [min(heights), max(heights)],
            'distance_stats': {
                'mean': float(np.mean(distances)),
                'std': float(np.std(distances)),
                'min': float(min(distances)),
                'max': float(max(distances))
            },
            'height_distribution': height_counts,
            'fov_distribution': fov_counts,
            'hemisphere_distribution': hemisphere_counts,
            'angular_sector_distribution': sector_analysis['counts'],
            'angular_sector_percentages': sector_analysis['percentages'],
            'angular_gaps': {
                'mean': float(np.mean(gaps)),
                'std': float(np.std(gaps)),
                'min': float(min(gaps)),
                'max': float(max(gaps))
            },
            'front_coverage_percentage': (hemisphere_counts['front'] / len(self.camera_metrics)) * 100
        }

        return summary

    def save_results(self, output_dir: Path):
        """
        Save analysis results to JSON files.

        Args:
            output_dir: Directory to save output files
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save detailed metrics
        metrics_file = output_dir / 'camera_metrics_60cam.json'
        with open(metrics_file, 'w') as f:
            json.dump(self.camera_metrics, f, indent=2)
        print(f"Saved camera metrics to {metrics_file}")

        # Save summary statistics
        summary = self.generate_summary_statistics()
        summary_file = output_dir / 'camera_summary_stats.json'
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        print(f"Saved summary statistics to {summary_file}")

        # Generate human-readable report
        report_file = output_dir / 'camera_analysis_report.txt'
        self.generate_text_report(summary, report_file)
        print(f"Saved analysis report to {report_file}")

    def generate_text_report(self, summary: Dict, output_file: Path):
        """Generate human-readable analysis report."""
        with open(output_file, 'w') as f:
            f.write("=" * 70 + "\n")
            f.write("RenderMe360 Camera Calibration Analysis Report\n")
            f.write("Phase 1: Camera Parameter Extraction\n")
            f.write("=" * 70 + "\n\n")

            f.write(f"Total Cameras: {summary['total_cameras']}\n\n")

            f.write("Camera Distribution:\n")
            f.write("-" * 40 + "\n")
            f.write(f"Front Hemisphere: {summary['hemisphere_distribution']['front']} cameras "
                   f"({summary['front_coverage_percentage']:.1f}%)\n")
            f.write(f"Rear Hemisphere:  {summary['hemisphere_distribution']['rear']} cameras "
                   f"({100 - summary['front_coverage_percentage']:.1f}%)\n\n")

            f.write("Height Distribution:\n")
            f.write("-" * 40 + "\n")
            f.write(f"Upper Ring (U):  {summary['height_distribution']['U']} cameras\n")
            f.write(f"Middle Ring (M): {summary['height_distribution']['M']} cameras\n")
            f.write(f"Lower Ring (L):  {summary['height_distribution']['L']} cameras\n")
            f.write(f"Height Range: {summary['height_range'][0]:.3f}m to {summary['height_range'][1]:.3f}m\n\n")

            f.write("Field of View Distribution:\n")
            f.write("-" * 40 + "\n")
            f.write(f"Small FOV (Narrow/Telephoto): {summary['fov_distribution']['Small']} cameras\n")
            f.write(f"Large FOV (Wide):              {summary['fov_distribution']['Large']} cameras\n\n")

            f.write("Angular Coverage:\n")
            f.write("-" * 40 + "\n")
            f.write(f"Yaw Range: {summary['yaw_range'][0]:.1f}° to {summary['yaw_range'][1]:.1f}°\n")
            f.write(f"Average Angular Gap: {summary['angular_gaps']['mean']:.1f}°\n")
            f.write(f"Gap Std Dev: {summary['angular_gaps']['std']:.1f}°\n")
            f.write(f"Min Gap: {summary['angular_gaps']['min']:.1f}°\n")
            f.write(f"Max Gap: {summary['angular_gaps']['max']:.1f}°\n\n")

            f.write("Camera Distance from Subject:\n")
            f.write("-" * 40 + "\n")
            f.write(f"Mean Distance: {summary['distance_stats']['mean']:.3f}m\n")
            f.write(f"Std Dev: {summary['distance_stats']['std']:.3f}m\n")
            f.write(f"Range: {summary['distance_stats']['min']:.3f}m to {summary['distance_stats']['max']:.3f}m\n\n")

            f.write("Key Findings:\n")
            f.write("-" * 40 + "\n")
            f.write(f"1. Front hemisphere contains {summary['front_coverage_percentage']:.0f}% of cameras ")
            f.write("(aligns with RenderMe360's front-dense design)\n")
            f.write(f"2. Camera heights span {summary['height_range'][1] - summary['height_range'][0]:.2f}m ")
            f.write("(multi-ring setup for vertical parallax)\n")
            f.write(f"3. Mixed FOV setup with {summary['fov_distribution']['Small']} narrow and ")
            f.write(f"{summary['fov_distribution']['Large']} wide cameras\n")
            f.write(f"4. Average angular gap of {summary['angular_gaps']['mean']:.1f}° ")
            f.write(f"(ideal would be {360/summary['total_cameras']:.1f}° for uniform distribution)\n\n")

            f.write("Next Steps:\n")
            f.write("-" * 40 + "\n")
            f.write("1. Use these metrics to select optimal camera subsets\n")
            f.write("2. Prioritize front hemisphere Small FOV cameras for facial detail\n")
            f.write("3. Include rear Large FOV cameras for 360° consistency\n")
            f.write("4. Consider multi-height selection at key angles (0°, ±30°)\n")


def main():
    """Main execution function."""
    # Path to calibration data
    calib_path = Path("/ssd4/zhuoyuan/renderme360_temp/FULL_EXTRACTION_BOTH/0026_s1_all/from_anno/calibration/all_cameras.npy")

    # Output directory
    output_dir = Path("/ssd4/zhuoyuan/renderme360_temp/test_download/visualizations/camera_analysis")

    # Initialize analyzer
    analyzer = CameraCalibrationAnalyzer(calib_path)

    # Perform analysis
    print("Starting camera calibration analysis...")
    metrics = analyzer.analyze_all_cameras()

    # Save results
    analyzer.save_results(output_dir)

    print("\nAnalysis complete!")
    print(f"Results saved to: {output_dir}")

    # Print quick summary
    summary = analyzer.generate_summary_statistics()
    print(f"\nQuick Summary:")
    print(f"- Total cameras: {summary['total_cameras']}")
    print(f"- Front hemisphere: {summary['hemisphere_distribution']['front']} cameras")
    print(f"- Height distribution: U={summary['height_distribution']['U']}, "
          f"M={summary['height_distribution']['M']}, L={summary['height_distribution']['L']}")
    print(f"- FOV types: Small={summary['fov_distribution']['Small']}, "
          f"Large={summary['fov_distribution']['Large']}")


if __name__ == "__main__":
    main()