#!/usr/bin/env python3
"""
Dynamic camera analysis for s3_all performance in RenderMe360.
Automatically detects available cameras and provides optimal subset recommendations.
No hardcoded camera lists - adapts to actual data.
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
import cv2
from pathlib import Path
import json
from mpl_toolkits.mplot3d import Axes3D
import pandas as pd
from typing import List, Dict, Tuple, Optional
import yaml


class DynamicCameraAnalyzer:
    def __init__(self, subject_dirs: List[Path]):
        """
        Initialize analyzer with multiple subject directories for comparison.
        
        Args:
            subject_dirs: List of paths to extracted subject directories
        """
        self.subject_dirs = [Path(d) for d in subject_dirs]
        self.subjects_data = {}
        
        # Analyze each subject
        for subject_dir in self.subject_dirs:
            subject_id = subject_dir.name
            print(f"Analyzing subject {subject_id}...")
            
            s3_dir = subject_dir / "s3_all"
            if not s3_dir.exists():
                print(f"  Warning: s3_all not found for {subject_id}")
                continue
                
            self.subjects_data[subject_id] = {
                'dir': s3_dir,
                'cameras': self._detect_cameras(s3_dir),
                'calibrations': self._load_calibrations(s3_dir),
                'positions': {},
                'metrics': {}
            }
            
            # Extract positions and calculate metrics
            if self.subjects_data[subject_id]['calibrations']:
                self.subjects_data[subject_id]['positions'] = self._extract_camera_positions(
                    self.subjects_data[subject_id]['calibrations']
                )
                self.subjects_data[subject_id]['metrics'] = self._calculate_metrics(
                    self.subjects_data[subject_id]['positions']
                )
        
        # Find common cameras across all subjects
        self.common_cameras = self._find_common_cameras()
        
    def _detect_cameras(self, s3_dir: Path) -> List[int]:
        """Detect available cameras from the images directory."""
        images_dir = s3_dir / "images"
        if not images_dir.exists():
            return []
        
        cameras = []
        for cam_dir in sorted(images_dir.iterdir()):
            if cam_dir.is_dir() and cam_dir.name.startswith("cam_"):
                cam_id = int(cam_dir.name.replace("cam_", ""))
                # Check if directory actually has images
                if len(list(cam_dir.glob("*.jpg"))) > 0:
                    cameras.append(cam_id)
        
        return sorted(cameras)
    
    def _load_calibrations(self, s3_dir: Path) -> Dict:
        """Load calibration data for all cameras."""
        calib_file = s3_dir / "calibration" / "all_cameras.npy"
        if not calib_file.exists():
            return {}
        
        calibs = np.load(calib_file, allow_pickle=True).item()
        # Convert keys to integers
        return {int(k): v for k, v in calibs.items()}
    
    def _extract_camera_positions(self, calibrations: Dict) -> Dict:
        """Extract 3D positions of all cameras from calibration data."""
        positions = {}
        for cam_id, calib in calibrations.items():
            RT = calib['RT']
            R = RT[:3, :3]
            t = RT[:3, 3]
            # Camera position in world coordinates
            # Using Method 2: cam_pos = -t (cameras surround subject)
            cam_pos = -t
            positions[cam_id] = cam_pos
        return positions
    
    def _calculate_metrics(self, positions: Dict) -> Dict:
        """Calculate various metrics for each camera."""
        metrics = {}
        
        for cam_id, pos in positions.items():
            x, y, z = pos
            r = np.sqrt(x**2 + y**2 + z**2)  # Distance from origin
            azimuth = np.arctan2(y, x)  # Horizontal angle
            elevation = np.arctan2(z, np.sqrt(x**2 + y**2))  # Vertical angle
            
            metrics[cam_id] = {
                'position': pos,
                'distance': r,
                'azimuth_rad': azimuth,
                'azimuth_deg': np.degrees(azimuth),
                'elevation_rad': elevation,
                'elevation_deg': np.degrees(elevation),
                'height': z
            }
        
        return metrics
    
    def _find_common_cameras(self) -> List[int]:
        """Find cameras that are common across all subjects."""
        if not self.subjects_data:
            return []
        
        # Get camera sets for each subject
        camera_sets = [set(data['cameras']) for data in self.subjects_data.values()]
        
        if not camera_sets:
            return []
        
        # Find intersection
        common = camera_sets[0]
        for cam_set in camera_sets[1:]:
            common = common.intersection(cam_set)
        
        return sorted(list(common))
    
    def analyze_coverage_gaps(self, subject_id: Optional[str] = None) -> List[Dict]:
        """Analyze gaps in camera coverage for a specific subject or the common set."""
        if subject_id and subject_id in self.subjects_data:
            metrics = self.subjects_data[subject_id]['metrics']
        else:
            # Use first subject with data
            subject_id = list(self.subjects_data.keys())[0]
            metrics = self.subjects_data[subject_id]['metrics']
        
        # Sort cameras by azimuth
        sorted_cams = sorted(metrics.items(), key=lambda x: x[1]['azimuth_deg'])
        
        gaps = []
        for i in range(len(sorted_cams)):
            curr_cam = sorted_cams[i]
            next_cam = sorted_cams[(i + 1) % len(sorted_cams)]
            
            curr_az = curr_cam[1]['azimuth_deg']
            next_az = next_cam[1]['azimuth_deg']
            
            # Handle wrap-around
            if next_az < curr_az:
                gap = (360 + next_az) - curr_az
            else:
                gap = next_az - curr_az
            
            gaps.append({
                'from_cam': curr_cam[0],
                'to_cam': next_cam[0],
                'gap_degrees': gap
            })
        
        # Sort gaps by size
        gaps.sort(key=lambda x: x['gap_degrees'], reverse=True)
        
        return gaps
    
    def suggest_optimal_subsets(self, target_counts: List[int] = [4, 6, 8, 10, 12, 16, 20]) -> Dict:
        """
        Suggest optimal camera subsets based on coverage metrics.
        Uses the common camera set across all subjects.
        """
        suggestions = {}
        
        # Use common cameras if available, otherwise use first subject
        if self.common_cameras:
            camera_list = self.common_cameras
            # Use metrics from first subject for positions
            subject_id = list(self.subjects_data.keys())[0]
            metrics = {cid: self.subjects_data[subject_id]['metrics'][cid] 
                      for cid in camera_list if cid in self.subjects_data[subject_id]['metrics']}
        else:
            subject_id = list(self.subjects_data.keys())[0]
            metrics = self.subjects_data[subject_id]['metrics']
            camera_list = sorted(metrics.keys())
        
        # Sort cameras by azimuth for even coverage
        sorted_by_azimuth = sorted(metrics.items(), key=lambda x: x[1]['azimuth_deg'])
        cam_ids_sorted = [cam[0] for cam in sorted_by_azimuth]
        
        for num_cams in target_counts:
            if num_cams > len(cam_ids_sorted):
                continue
            
            # Select evenly spaced cameras
            step = len(cam_ids_sorted) / num_cams
            selected_indices = [int(i * step) for i in range(num_cams)]
            selected_cams = [cam_ids_sorted[i] for i in selected_indices]
            
            # Calculate coverage metrics
            selected_metrics = [metrics[cid] for cid in selected_cams]
            azimuths = [m['azimuth_deg'] for m in selected_metrics]
            
            # Calculate gaps
            coverage_gaps = []
            for i in range(len(azimuths)):
                next_i = (i + 1) % len(azimuths)
                gap = azimuths[next_i] - azimuths[i]
                if gap < 0:
                    gap += 360
                coverage_gaps.append(gap)
            
            # Statistics
            max_gap = max(coverage_gaps) if coverage_gaps else 0
            min_gap = min(coverage_gaps) if coverage_gaps else 0
            avg_gap = np.mean(coverage_gaps) if coverage_gaps else 0
            std_gap = np.std(coverage_gaps) if coverage_gaps else 0
            
            # Height diversity
            heights = [metrics[cid]['height'] for cid in selected_cams]
            height_range = max(heights) - min(heights) if heights else 0
            
            # Quality score (lower std = better distribution)
            quality_score = 100 - (std_gap * 2) if std_gap < 50 else 0
            
            # Storage estimate (rough)
            frames_per_perf = 750  # Average
            mb_per_frame = 0.5  # Rough estimate
            storage_gb = (num_cams * frames_per_perf * mb_per_frame) / 1024
            
            suggestions[num_cams] = {
                'cameras': selected_cams,
                'avg_gap': avg_gap,
                'max_gap': max_gap,
                'min_gap': min_gap,
                'gap_std': std_gap,
                'height_range': height_range,
                'quality_score': quality_score,
                'storage_per_subject_gb': storage_gb,
                'storage_500_subjects_gb': storage_gb * 500
            }
        
        return suggestions
    
    def create_3d_visualization(self, output_path: Optional[Path] = None):
        """Create 3D visualization of camera positions."""
        fig = plt.figure(figsize=(16, 12))
        
        # Use first subject for visualization
        subject_id = list(self.subjects_data.keys())[0]
        positions_dict = self.subjects_data[subject_id]['positions']
        metrics = self.subjects_data[subject_id]['metrics']
        
        cam_ids = list(positions_dict.keys())
        positions = np.array([positions_dict[cid] for cid in cam_ids])
        
        # 3D scatter plot
        ax1 = fig.add_subplot(221, projection='3d')
        
        # Color by whether camera is common across subjects
        colors = ['green' if cid in self.common_cameras else 'orange' for cid in cam_ids]
        scatter = ax1.scatter(positions[:, 0], positions[:, 1], positions[:, 2],
                             c=colors, s=100, alpha=0.6)
        
        # Add labels
        for i, cam_id in enumerate(cam_ids):
            ax1.text(positions[i, 0], positions[i, 1], positions[i, 2],
                    str(cam_id), fontsize=8)
        
        # Add origin (subject position)
        ax1.scatter([0], [0], [0], color='red', s=200, marker='*', label='Subject')
        
        ax1.set_xlabel('X (m)')
        ax1.set_ylabel('Y (m)')
        ax1.set_zlabel('Z (m)')
        ax1.set_title(f'3D Camera Positions - {len(cam_ids)} Cameras')
        ax1.legend(['Common', 'Subject-specific', 'Subject'])
        
        # Top-down view
        ax2 = fig.add_subplot(222)
        ax2.scatter(positions[:, 0], positions[:, 1], c=colors, s=100, alpha=0.6)
        for i, cam_id in enumerate(cam_ids):
            ax2.annotate(str(cam_id), (positions[i, 0], positions[i, 1]),
                        fontsize=8, ha='center', va='center')
        ax2.scatter([0], [0], color='red', s=200, marker='*')
        ax2.set_xlabel('X (m)')
        ax2.set_ylabel('Y (m)')
        ax2.set_title('Top-Down View')
        ax2.axis('equal')
        ax2.grid(True, alpha=0.3)
        
        # Azimuth distribution (polar plot)
        ax3 = fig.add_subplot(223, projection='polar')
        azimuths = [metrics[cid]['azimuth_rad'] for cid in cam_ids]
        distances = [metrics[cid]['distance'] for cid in cam_ids]
        
        ax3.scatter(azimuths, distances, c=colors, s=100, alpha=0.6)
        for i, cam_id in enumerate(cam_ids):
            ax3.annotate(str(cam_id), (azimuths[i], distances[i]),
                        fontsize=8, ha='center', va='center')
        ax3.set_title('Azimuth Distribution\n(angle vs distance)')
        ax3.set_ylim(0, max(distances) * 1.1)
        
        # Height distribution
        ax4 = fig.add_subplot(224)
        sorted_cams = sorted(cam_ids)
        heights = [metrics[cid]['height'] for cid in sorted_cams]
        colors_sorted = ['green' if cid in self.common_cameras else 'orange' for cid in sorted_cams]
        bars = ax4.bar(range(len(sorted_cams)), heights, color=colors_sorted, alpha=0.6)
        ax4.set_xticks(range(len(sorted_cams)))
        ax4.set_xticklabels(sorted_cams, rotation=90)
        ax4.set_xlabel('Camera ID')
        ax4.set_ylabel('Height (m)')
        ax4.set_title('Camera Heights')
        ax4.grid(True, alpha=0.3)
        
        # Add horizontal line at median height
        median_height = np.median(heights)
        ax4.axhline(y=median_height, color='red', linestyle='--', alpha=0.5, label=f'Median: {median_height:.2f}m')
        ax4.legend()
        
        plt.suptitle(f'Camera Analysis - {len(self.common_cameras)} Common Cameras across {len(self.subjects_data)} Subjects', 
                    fontsize=14, y=1.02)
        plt.tight_layout()
        
        if output_path:
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            print(f"3D visualization saved to: {output_path}")
        else:
            plt.show()
        
        plt.close()
    
    def create_subset_comparison(self, output_path: Optional[Path] = None):
        """Create visual comparison of different subset configurations."""
        suggestions = self.suggest_optimal_subsets([4, 8, 12, 16])
        
        fig = plt.figure(figsize=(18, 12))
        
        # Use first subject for positions
        subject_id = list(self.subjects_data.keys())[0]
        metrics = self.subjects_data[subject_id]['metrics']
        
        for idx, num_cams in enumerate([4, 8, 12, 16]):
            if num_cams not in suggestions:
                continue
            
            subset_info = suggestions[num_cams]
            selected_cams = subset_info['cameras']
            
            # Polar plot
            ax = fig.add_subplot(2, 4, idx + 1, projection='polar')
            
            # Plot all cameras in light gray
            for cam_id, m in metrics.items():
                if cam_id not in selected_cams:
                    ax.scatter(m['azimuth_rad'], m['distance'],
                             color='lightgray', s=50, alpha=0.3)
                    ax.annotate(str(cam_id), (m['azimuth_rad'], m['distance']),
                              fontsize=6, color='gray', alpha=0.5)
            
            # Plot selected cameras in red
            for cam_id in selected_cams:
                if cam_id in metrics:
                    m = metrics[cam_id]
                    ax.scatter(m['azimuth_rad'], m['distance'],
                             color='red', s=100, alpha=0.8)
                    ax.annotate(str(cam_id), (m['azimuth_rad'], m['distance']),
                              fontsize=8, fontweight='bold')
            
            ax.set_title(f'{num_cams} Cameras\nAvg gap: {subset_info["avg_gap"]:.1f}°\n'
                        f'Quality: {subset_info["quality_score"]:.1f}')
            
            # Top-down view
            ax2 = fig.add_subplot(2, 4, idx + 5)
            
            # Plot all cameras
            for cam_id, m in metrics.items():
                pos = m['position']
                if cam_id not in selected_cams:
                    ax2.scatter(pos[0], pos[1], color='lightgray', s=50, alpha=0.3)
                else:
                    ax2.scatter(pos[0], pos[1], color='red', s=100, alpha=0.8)
                    ax2.annotate(str(cam_id), (pos[0], pos[1]),
                               fontsize=8, fontweight='bold')
            
            # Add subject at origin
            ax2.scatter(0, 0, color='blue', s=200, marker='*')
            
            ax2.set_xlabel('X (m)')
            ax2.set_ylabel('Y (m)')
            ax2.set_title(f'Storage: {subset_info["storage_per_subject_gb"]:.1f} GB/subj\n'
                         f'500 subj: {subset_info["storage_500_subjects_gb"]:.0f} GB')
            ax2.axis('equal')
            ax2.grid(True, alpha=0.3)
        
        plt.suptitle('Camera Subset Comparison for s3_all', fontsize=16)
        plt.tight_layout()
        
        if output_path:
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            print(f"Subset comparison saved to: {output_path}")
        else:
            plt.show()
        
        plt.close()
    
    def create_sample_frames(self, subset_size: int = 8, frame_id: int = 100, 
                           output_path: Optional[Path] = None):
        """Create a grid showing sample frames from a selected subset."""
        suggestions = self.suggest_optimal_subsets([subset_size])
        if subset_size not in suggestions:
            print(f"Cannot create subset of size {subset_size}")
            return
        
        selected_cameras = suggestions[subset_size]['cameras']
        
        # Use first subject with images
        subject_id = None
        images_dir = None
        for sid, data in self.subjects_data.items():
            test_dir = data['dir'] / "images"
            if test_dir.exists():
                subject_id = sid
                images_dir = test_dir
                break
        
        if not images_dir:
            print("No images found to display")
            return
        
        num_cameras = len(selected_cameras)
        grid_cols = int(np.ceil(np.sqrt(num_cameras)))
        grid_rows = int(np.ceil(num_cameras / grid_cols))
        
        fig = plt.figure(figsize=(20, 16))
        fig.suptitle(f's3_all Sample Frames - {num_cameras} Cameras - Frame {frame_id}\n'
                    f'Quality Score: {suggestions[subset_size]["quality_score"]:.1f}',
                    fontsize=16)
        
        for idx, cam_id in enumerate(selected_cameras):
            cam_dir = images_dir / f"cam_{cam_id:02d}"
            img_path = cam_dir / f"frame_{frame_id:06d}.jpg"
            
            ax = plt.subplot(grid_rows, grid_cols, idx + 1)
            
            if img_path.exists():
                # Load and display image
                img = cv2.imread(str(img_path))
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                
                # Resize for display
                display_height = 300
                aspect_ratio = img.shape[1] / img.shape[0]
                display_width = int(display_height * aspect_ratio)
                img_small = cv2.resize(img, (display_width, display_height))
                
                ax.imshow(img_small)
                
                # Add camera info if available
                if subject_id in self.subjects_data and cam_id in self.subjects_data[subject_id]['metrics']:
                    m = self.subjects_data[subject_id]['metrics'][cam_id]
                    title = f'Cam {cam_id:02d}\n'
                    title += f'Az: {m["azimuth_deg"]:.1f}° H: {m["height"]:.2f}m'
                else:
                    title = f'Cam {cam_id:02d}'
            else:
                # Show placeholder
                ax.text(0.5, 0.5, f'Camera {cam_id}\n(No image)', 
                       ha='center', va='center', fontsize=12)
                ax.set_xlim(0, 1)
                ax.set_ylim(0, 1)
                title = f'Cam {cam_id:02d}'
            
            ax.set_title(title, fontsize=10)
            ax.axis('off')
        
        plt.tight_layout()
        
        if output_path:
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            print(f"Sample frames saved to: {output_path}")
        else:
            plt.show()
        
        plt.close()
    
    def generate_report(self) -> str:
        """Generate comprehensive text report on camera setup."""
        report = []
        report.append("=" * 70)
        report.append("DYNAMIC CAMERA ANALYSIS REPORT - s3_all Performance")
        report.append("=" * 70)
        report.append("")
        
        # Subject summary
        report.append("SUBJECTS ANALYZED")
        report.append("-" * 40)
        for subject_id, data in self.subjects_data.items():
            report.append(f"Subject {subject_id}: {len(data['cameras'])} cameras detected")
            report.append(f"  Cameras: {data['cameras'][:10]}{'...' if len(data['cameras']) > 10 else ''}")
        report.append("")
        
        # Common cameras
        report.append("COMMON CAMERAS ACROSS ALL SUBJECTS")
        report.append("-" * 40)
        report.append(f"Total common cameras: {len(self.common_cameras)}")
        report.append(f"Camera IDs: {self.common_cameras}")
        report.append("")
        
        # Camera distribution metrics
        if self.subjects_data:
            subject_id = list(self.subjects_data.keys())[0]
            metrics = self.subjects_data[subject_id]['metrics']
            
            if metrics:
                heights = [m['height'] for m in metrics.values()]
                distances = [m['distance'] for m in metrics.values()]
                
                report.append("CAMERA DISTRIBUTION METRICS")
                report.append("-" * 40)
                report.append(f"Height range: {min(heights):.2f}m to {max(heights):.2f}m")
                report.append(f"Average height: {np.mean(heights):.2f}m")
                report.append(f"Distance range: {min(distances):.2f}m to {max(distances):.2f}m")
                report.append(f"Average distance: {np.mean(distances):.2f}m")
                report.append("")
                
                # Coverage gaps
                gaps = self.analyze_coverage_gaps(subject_id)
                if gaps:
                    report.append("COVERAGE ANALYSIS")
                    report.append("-" * 40)
                    avg_gap = np.mean([g['gap_degrees'] for g in gaps])
                    report.append(f"Average angular gap: {avg_gap:.1f}°")
                    report.append(f"Largest gap: {gaps[0]['gap_degrees']:.1f}° "
                                f"(cameras {gaps[0]['from_cam']} to {gaps[0]['to_cam']})")
                    report.append(f"Ideal gap for {len(metrics)} cameras: {360/len(metrics):.1f}°")
                    report.append("")
        
        # Optimal subset recommendations
        suggestions = self.suggest_optimal_subsets()
        
        report.append("OPTIMAL SUBSET RECOMMENDATIONS")
        report.append("-" * 40)
        
        for num_cams in sorted(suggestions.keys()):
            s = suggestions[num_cams]
            report.append(f"\n{num_cams} Cameras:")
            report.append(f"  Camera IDs: {s['cameras']}")
            report.append(f"  Average gap: {s['avg_gap']:.1f}°")
            report.append(f"  Gap uniformity (std): {s['gap_std']:.1f}°")
            report.append(f"  Quality score: {s['quality_score']:.1f}/100")
            report.append(f"  Storage per subject: ~{s['storage_per_subject_gb']:.1f} GB")
            report.append(f"  Storage for 500 subjects: ~{s['storage_500_subjects_gb']:.0f} GB")
        
        report.append("")
        report.append("RECOMMENDATION SUMMARY")
        report.append("-" * 40)
        report.append("• For minimal storage (4 cameras): Good for basic 360° coverage")
        report.append("• For balanced quality (8-12 cameras): Recommended for most use cases")
        report.append("• For high quality (16+ cameras): When detail is critical")
        report.append("")
        report.append("=" * 70)
        report.append(f"Report generated: {pd.Timestamp.now()}")
        
        return "\n".join(report)


def main():
    """Main execution function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Dynamic camera analysis for s3_all')
    parser.add_argument('--subjects', nargs='+', default=['0018', '0019', '0026'],
                       help='Subject IDs to analyze')
    parser.add_argument('--base_dir', 
                       default='/ssd4/zhuoyuan/renderme360_temp/download_all/subjects',
                       help='Base directory containing subject folders')
    parser.add_argument('--output_dir', 
                       default='/ssd4/zhuoyuan/renderme360_temp/download_all/visualizations/camera_analysis',
                       help='Output directory for visualizations and reports')
    parser.add_argument('--frame', type=int, default=100,
                       help='Frame ID for sample images')
    
    args = parser.parse_args()
    
    # Build subject directories
    subject_dirs = [Path(args.base_dir) / subj for subj in args.subjects]
    
    # Verify directories exist
    valid_dirs = []
    for d in subject_dirs:
        if d.exists():
            valid_dirs.append(d)
        else:
            print(f"Warning: Subject directory not found: {d}")
    
    if not valid_dirs:
        print("Error: No valid subject directories found")
        return
    
    print(f"Analyzing {len(valid_dirs)} subjects...")
    print("-" * 50)
    
    # Create analyzer
    analyzer = DynamicCameraAnalyzer(valid_dirs)
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate visualizations
    print("\nCreating visualizations...")
    analyzer.create_3d_visualization(output_dir / '3d_camera_positions.png')
    analyzer.create_subset_comparison(output_dir / 'subset_comparison.png')
    
    # Create sample frames for different subset sizes
    for subset_size in [4, 8, 12]:
        analyzer.create_sample_frames(
            subset_size=subset_size,
            frame_id=args.frame,
            output_path=output_dir / f'sample_frames_{subset_size}_cameras.png'
        )
    
    # Generate text report
    print("\nGenerating report...")
    report = analyzer.generate_report()
    print(report)
    
    # Save report to file
    report_path = output_dir / 'camera_analysis_report.md'
    with open(report_path, 'w') as f:
        f.write(report)
    print(f"\nReport saved to: {report_path}")
    
    print("\nAnalysis complete!")
    print(f"All outputs saved to: {output_dir}")


if __name__ == '__main__':
    main()