#!/usr/bin/env python3
"""
Visualize all 60 cameras from RenderMe360 dataset with full metadata annotations.
Each tile shows: cam_id, azimuth, elevation, distance, fx/fy/cx/cy, position (x,y,z).
Current 4-cam set (cam_28/37/49/54) highlighted with distinct border.
Also exports camera_metadata_60.csv.
"""

import json
import csv
import math
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.patches import FancyBboxPatch
from pathlib import Path
import cv2


def compute_elevation(pos_x, pos_y, pos_z):
    """Compute elevation angle in degrees. pos_y is height (negative = above subject)."""
    horizontal_dist = math.sqrt(pos_x**2 + pos_z**2)
    elev_rad = math.atan2(-pos_y, horizontal_dist)
    return math.degrees(elev_rad)


def compute_azimuth(pos_x, pos_z):
    """Compute azimuth in degrees. Convention: ±180° = front/face, 0° = back of head."""
    return math.degrees(math.atan2(pos_x, pos_z))


def load_all_data(metrics_path, calibration_path):
    """Load camera metrics and calibration data, return unified per-camera dict."""
    # Load metrics
    with open(metrics_path, 'r') as f:
        metrics = json.load(f)

    # Load calibration (for intrinsics K matrix)
    calib = np.load(calibration_path, allow_pickle=True).item()

    cameras = {}
    for cam_id_str, m in metrics.items():
        cam_id = int(cam_id_str)
        cam_key = f"{cam_id:02d}"

        pos = m['position']  # [x, y, z]
        pos_x, pos_y, pos_z = pos[0], pos[1], pos[2]

        # Get intrinsics
        K = calib[cam_key]['K']
        fx, fy = K[0, 0], K[1, 1]
        cx, cy = K[0, 2], K[1, 2]

        cameras[cam_id] = {
            'cam_id': cam_id,
            'azimuth_deg': m['yaw_deg'],
            'elevation_deg': compute_elevation(pos_x, pos_y, pos_z),
            'distance_m': m['distance'],
            'height_m': m['height'],
            'height_class': m['height_class'],
            'pos_x': pos_x,
            'pos_y': pos_y,
            'pos_z': pos_z,
            'fx': fx,
            'fy': fy,
            'cx': cx,
            'cy': cy,
        }

    return cameras


def export_csv(cameras, output_path):
    """Export all 60 cameras' metadata to CSV, sorted by azimuth."""
    fieldnames = [
        'cam_id', 'azimuth_deg', 'elevation_deg', 'distance_m',
        'height_m', 'height_class', 'pos_x', 'pos_y', 'pos_z',
        'fx', 'fy', 'cx', 'cy'
    ]

    sorted_cams = sorted(cameras.values(), key=lambda c: c['azimuth_deg'])

    with open(output_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for cam in sorted_cams:
            row = {}
            for field in fieldnames:
                val = cam[field]
                if isinstance(val, float):
                    row[field] = f"{val:.2f}"
                else:
                    row[field] = val
            writer.writerow(row)

    print(f"Exported {len(sorted_cams)} cameras to {output_path}")


def load_frame(base_path, camera_id, frame_num=500):
    """Load a frame from specified camera."""
    frame_path = base_path / f"from_raw/images/cam_{camera_id:02d}/frame_{frame_num:06d}.jpg"

    if not frame_path.exists():
        placeholder = np.ones((270, 480, 3), dtype=np.uint8) * 128
        cv2.putText(placeholder, f"Cam {camera_id:02d}",
                    (180, 130), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
        cv2.putText(placeholder, "(No data)",
                    (180, 165), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        return placeholder

    img = cv2.imread(str(frame_path))
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    # Resize for grid
    target_height = 270
    aspect = img.shape[1] / img.shape[0]
    target_width = int(target_height * aspect)
    img = cv2.resize(img, (target_width, target_height))

    return img


def create_annotated_grid(cameras, base_path, output_path):
    """
    Create 10x6 grid of all 60 cameras sorted by azimuth, with metadata annotations.
    Current 4-cam set (28/37/49/54) gets a cyan border.
    """
    CURRENT_SET = {28, 37, 49, 54}

    # Sort by azimuth
    sorted_cams = sorted(cameras.values(), key=lambda c: c['azimuth_deg'])

    rows, cols = 10, 6
    fig = plt.figure(figsize=(36, 60))

    fig.suptitle(
        "RenderMe360 — All 60 Cameras with Full Metadata\n"
        "Sorted by Azimuth (±180°=Front/Face, 0°=Back of Head)  |  "
        "Cyan border = current training set (cam 28/37/49/54)",
        fontsize=18, fontweight='bold', y=0.998
    )

    gs = gridspec.GridSpec(rows, cols, figure=fig,
                           hspace=0.45, wspace=0.25,
                           top=0.993, bottom=0.015)

    for idx, cam in enumerate(sorted_cams):
        cam_id = cam['cam_id']
        row = idx // cols
        col = idx % cols

        if row >= rows:
            break

        ax = fig.add_subplot(gs[row, col])

        # Load and display frame
        img = load_frame(base_path, cam_id)
        ax.imshow(img)
        ax.set_xticks([])
        ax.set_yticks([])

        # Border color: cyan for current set, region-based otherwise
        if cam_id in CURRENT_SET:
            border_color = 'cyan'
            border_width = 4
        else:
            azimuth = cam['azimuth_deg']
            if azimuth > 165 or azimuth < -165:
                border_color = 'green'
            elif (135 < azimuth <= 165) or (-165 <= azimuth < -135):
                border_color = 'yellowgreen'
            elif (90 < azimuth <= 135) or (-135 <= azimuth < -90):
                border_color = 'orange'
            elif (45 < azimuth <= 90) or (-90 <= azimuth < -45):
                border_color = 'salmon'
            else:
                border_color = 'red'
            border_width = 2

        for spine in ax.spines.values():
            spine.set_edgecolor(border_color)
            spine.set_linewidth(border_width)

        # Title line 1: cam_id + azimuth + elevation
        current_tag = " [CURRENT]" if cam_id in CURRENT_SET else ""
        line1 = f"Cam {cam_id:02d}{current_tag}  |  Az: {cam['azimuth_deg']:.1f}°  El: {cam['elevation_deg']:.1f}°"

        # Title line 2: distance + height + class
        line2 = f"Dist: {cam['distance_m']:.3f}m  Ht: {cam['height_m']:.3f}m ({cam['height_class']})"

        # Title line 3: intrinsics
        line3 = f"fx:{cam['fx']:.0f} fy:{cam['fy']:.0f} cx:{cam['cx']:.0f} cy:{cam['cy']:.0f}"

        # Title line 4: position
        line4 = f"Pos: ({cam['pos_x']:.3f}, {cam['pos_y']:.3f}, {cam['pos_z']:.3f})"

        title = f"{line1}\n{line2}\n{line3}\n{line4}"

        title_color = 'cyan' if cam_id in CURRENT_SET else 'black'
        ax.set_title(title, fontsize=6.5, fontweight='bold' if cam_id in CURRENT_SET else 'normal',
                     color=title_color, linespacing=1.3)

    # Legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='cyan', edgecolor='cyan', label='Current training set (cam 28/37/49/54)'),
        Patch(facecolor='green', label='Front Center (±165°–±180°)'),
        Patch(facecolor='yellowgreen', label='Front Sides (±135°–±165°)'),
        Patch(facecolor='orange', label='Profiles (±90°–±135°)'),
        Patch(facecolor='salmon', label='Rear Sides (±45°–±90°)'),
        Patch(facecolor='red', label='Rear Center (0°–±45°)'),
    ]
    fig.legend(handles=legend_elements, loc='lower center',
               ncol=6, fontsize=10, bbox_to_anchor=(0.5, 0.001))

    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()

    print(f"Saved annotated 60-camera visualization to {output_path}")


def main():
    # Paths
    metrics_path = Path("/ssd4/zhuoyuan/renderme360_temp/test_download/visualizations/camera_analysis/camera_metrics_60cam.json")
    calibration_path = Path("/ssd4/zhuoyuan/renderme360_temp/test_download/subjects/0026/s1_all/calibration/all_cameras.npy")
    base_path = Path("/ssd4/zhuoyuan/renderme360_temp/FULL_EXTRACTION_BOTH/0026_s1_all")
    output_dir = Path("/ssd4/zhuoyuan/renderme360_temp/test_download/visualizations/camera_selection")

    # Load all data
    cameras = load_all_data(metrics_path, calibration_path)
    print(f"Loaded metadata for {len(cameras)} cameras")

    # Export CSV
    csv_path = output_dir / "camera_metadata_60.csv"
    export_csv(cameras, csv_path)

    # Create annotated visualization
    png_path = output_dir / "sample_frames_60_cameras_annotated.png"
    create_annotated_grid(cameras, base_path, png_path)

    print(f"\nDone! Outputs:")
    print(f"  PNG: {png_path}")
    print(f"  CSV: {csv_path}")


if __name__ == "__main__":
    main()
