#!/usr/bin/env python3
"""
Create a standalone HTML file with interactive 3D camera visualizations.
This HTML file can be shared and opened by anyone with just a web browser.
"""

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
import json

def load_camera_data(subject_id="0026"):
    """Load camera calibration data and compute positions."""
    
    # Load calibration file
    base_dir = Path(f'/ssd2/zhuoyuan/renderme360_temp/download_all/subjects/{subject_id}')
    calib_file = base_dir / 's3_all' / 'calibration' / 'all_cameras.npy'
    
    if not calib_file.exists():
        print(f"Calibration file not found: {calib_file}")
        return None
    
    calibs = np.load(calib_file, allow_pickle=True).item()
    
    # Extract camera positions and compute metrics
    camera_data = []
    
    for cam_str, calib in calibs.items():
        cam_id = int(cam_str)
        RT = calib['RT']
        R = RT[:3, :3]
        t = RT[:3, 3]
        
        # Camera position (using correct method)
        cam_pos = -t
        
        # Calculate spherical coordinates
        x, y, z = cam_pos
        r_xy = np.sqrt(x**2 + y**2)
        r_total = np.sqrt(x**2 + y**2 + z**2)
        theta = np.degrees(np.arctan2(y, x))
        phi = np.degrees(np.arctan2(z, r_xy))
        
        # Camera viewing direction (optical axis)
        optical_axis = R[2, :]
        
        camera_data.append({
            'id': cam_id,
            'x': float(x),
            'y': float(y),
            'z': float(z),
            'r_xy': float(r_xy),
            'r_total': float(r_total),
            'azimuth': float(theta),
            'elevation': float(phi),
            'optical_x': float(optical_axis[0]),
            'optical_y': float(optical_axis[1]),
            'optical_z': float(optical_axis[2])
        })
    
    return sorted(camera_data, key=lambda x: x['id'])

def create_standalone_html(output_path):
    """Create a standalone HTML file with all visualizations."""
    
    # Load camera data
    camera_data = load_camera_data()
    if not camera_data:
        print("Failed to load camera data")
        return
    
    # Extract data for plotting
    cam_ids = [c['id'] for c in camera_data]
    x_vals = [c['x'] for c in camera_data]
    y_vals = [c['y'] for c in camera_data]
    z_vals = [c['z'] for c in camera_data]
    r_xy_vals = [c['r_xy'] for c in camera_data]
    azimuth_vals = [c['azimuth'] for c in camera_data]
    
    # Create subplots
    fig = make_subplots(
        rows=2, cols=2,
        specs=[
            [{'type': 'scatter3d', 'colspan': 2}, None],
            [{'type': 'scatter'}, {'type': 'scatter'}]
        ],
        row_heights=[0.6, 0.4],
        subplot_titles=(
            'Interactive 3D Camera Positions (Rotate: Left-click drag | Zoom: Scroll | Pan: Right-click drag)',
            'Top-Down View',
            'Unwrapped Cylindrical View (Azimuth vs Height)'
        )
    )
    
    # 1. Main 3D visualization
    fig.add_trace(
        go.Scatter3d(
            x=x_vals,
            y=y_vals,
            z=z_vals,
            mode='markers+text',
            marker=dict(
                size=8,
                color=z_vals,
                colorscale='Viridis',
                showscale=True,
                colorbar=dict(
                    title="Height (m)",
                    x=0.9,
                    len=0.5,
                    y=0.75
                ),
                line=dict(width=1, color='black')
            ),
            text=[str(cid) for cid in cam_ids],
            textposition="top center",
            textfont=dict(size=8),
            hovertemplate='<b>Camera %{text}</b><br>' +
                         'Position: (%{x:.2f}, %{y:.2f}, %{z:.2f})m<br>' +
                         'Height: %{z:.2f}m<br>' +
                         '<extra></extra>',
            name='Cameras',
            showlegend=True
        ),
        row=1, col=1
    )
    
    # Add subject at origin
    fig.add_trace(
        go.Scatter3d(
            x=[0],
            y=[0],
            z=[0],
            mode='markers',
            marker=dict(
                size=12,
                color='red',
                symbol='diamond'
            ),
            name='Subject',
            hovertemplate='<b>Subject</b><br>Position: Origin (0,0,0)<extra></extra>',
            showlegend=True
        ),
        row=1, col=1
    )
    
    # Add cylindrical wireframe
    theta_wire = np.linspace(0, 2*np.pi, 30)
    avg_radius = np.mean(r_xy_vals)
    
    # Add circular rings at different heights
    for z_level in np.linspace(min(z_vals), max(z_vals), 5):
        x_circle = avg_radius * np.cos(theta_wire)
        y_circle = avg_radius * np.sin(theta_wire)
        z_circle = np.full_like(theta_wire, z_level)
        
        fig.add_trace(
            go.Scatter3d(
                x=x_circle.tolist(),
                y=y_circle.tolist(),
                z=z_circle.tolist(),
                mode='lines',
                line=dict(color='gray', width=1),
                opacity=0.3,
                showlegend=False,
                hoverinfo='skip'
            ),
            row=1, col=1
        )
    
    # Add vertical lines
    for angle in np.linspace(0, 2*np.pi, 8, endpoint=False):
        x_line = [avg_radius * np.cos(angle)] * 2
        y_line = [avg_radius * np.sin(angle)] * 2
        z_line = [min(z_vals), max(z_vals)]
        
        fig.add_trace(
            go.Scatter3d(
                x=x_line,
                y=y_line,
                z=z_line,
                mode='lines',
                line=dict(color='gray', width=1),
                opacity=0.3,
                showlegend=False,
                hoverinfo='skip'
            ),
            row=1, col=1
        )
    
    # 2. Top-down view
    fig.add_trace(
        go.Scatter(
            x=x_vals,
            y=y_vals,
            mode='markers+text',
            marker=dict(
                size=10,
                color=z_vals,
                colorscale='Viridis',
                showscale=False,
                line=dict(width=1, color='black')
            ),
            text=[str(cid) for cid in cam_ids],
            textposition="top center",
            textfont=dict(size=7),
            hovertemplate='<b>Camera %{text}</b><br>' +
                         'X: %{x:.2f}m, Y: %{y:.2f}m<br>' +
                         '<extra></extra>',
            showlegend=False
        ),
        row=2, col=1
    )
    
    # Add subject marker
    fig.add_trace(
        go.Scatter(
            x=[0],
            y=[0],
            mode='markers',
            marker=dict(size=15, color='red', symbol='star'),
            showlegend=False,
            hovertemplate='<b>Subject</b><extra></extra>'
        ),
        row=2, col=1
    )
    
    # Add average radius circle
    theta_circle = np.linspace(0, 2*np.pi, 100)
    fig.add_trace(
        go.Scatter(
            x=(avg_radius * np.cos(theta_circle)).tolist(),
            y=(avg_radius * np.sin(theta_circle)).tolist(),
            mode='lines',
            line=dict(color='gray', dash='dash'),
            opacity=0.5,
            showlegend=False,
            hoverinfo='skip'
        ),
        row=2, col=1
    )
    
    # 3. Unwrapped cylindrical view
    fig.add_trace(
        go.Scatter(
            x=azimuth_vals,
            y=z_vals,
            mode='markers+text',
            marker=dict(
                size=12,
                color=r_xy_vals,
                colorscale='Plasma',
                showscale=True,
                colorbar=dict(
                    title="Radial<br>Distance (m)",
                    x=1.0,
                    len=0.4,
                    y=0.2
                ),
                line=dict(width=1, color='black')
            ),
            text=[str(cid) for cid in cam_ids],
            textposition="top center",
            textfont=dict(size=7),
            hovertemplate='<b>Camera %{text}</b><br>' +
                         'Azimuth: %{x:.1f}°<br>' +
                         'Height: %{y:.2f}m<br>' +
                         '<extra></extra>',
            showlegend=False
        ),
        row=2, col=2
    )
    
    # Update layout
    fig.update_layout(
        title={
            'text': 'RenderMe360 Camera Setup - Interactive 3D Visualization<br>' +
                   '<sub>38 Cameras in s3_all Performance | ' +
                   f'Coverage: {max(azimuth_vals)-min(azimuth_vals):.1f}° | ' +
                   f'Height Range: {min(z_vals):.1f}m to {max(z_vals):.1f}m</sub>',
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 16}
        },
        scene=dict(
            xaxis_title='X (m)',
            yaxis_title='Y (m)',
            zaxis_title='Z (m)',
            aspectmode='data',
            camera=dict(
                eye=dict(x=2, y=2, z=1.5)
            )
        ),
        height=900,
        showlegend=True,
        legend=dict(
            x=0.02,
            y=0.98,
            bgcolor='rgba(255,255,255,0.8)',
            bordercolor='black',
            borderwidth=1
        )
    )
    
    # Update 2D subplot axes
    fig.update_xaxes(title_text="X (m)", row=2, col=1, scaleanchor="y", scaleratio=1)
    fig.update_yaxes(title_text="Y (m)", row=2, col=1)
    
    fig.update_xaxes(title_text="Azimuth (degrees)", row=2, col=2)
    fig.update_yaxes(title_text="Height (m)", row=2, col=2)
    
    # Add grid lines
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='LightGray', row=2, col=1)
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='LightGray', row=2, col=1)
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='LightGray', row=2, col=2)
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='LightGray', row=2, col=2)
    
    # Create HTML with embedded data
    html_str = fig.to_html(
        include_plotlyjs='cdn',  # Use CDN for smaller file size
        div_id="camera-visualization",
        config={'displayModeBar': True, 'displaylogo': False}
    )
    
    # Add custom HTML wrapper with instructions and summary
    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RenderMe360 Camera Visualization</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            border-bottom: 2px solid #4CAF50;
            padding-bottom: 10px;
        }}
        .info-box {{
            background-color: #e8f5e9;
            border-left: 4px solid #4CAF50;
            padding: 15px;
            margin: 20px 0;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }}
        .stat-card {{
            background-color: #f9f9f9;
            padding: 15px;
            border-radius: 5px;
            border: 1px solid #ddd;
        }}
        .stat-label {{
            color: #666;
            font-size: 12px;
            text-transform: uppercase;
        }}
        .stat-value {{
            color: #333;
            font-size: 20px;
            font-weight: bold;
            margin-top: 5px;
        }}
        .instructions {{
            background-color: #fff3e0;
            border-left: 4px solid #ff9800;
            padding: 15px;
            margin: 20px 0;
        }}
        .instructions h3 {{
            margin-top: 0;
            color: #e65100;
        }}
        .instructions ul {{
            margin: 10px 0;
        }}
        .footer {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            color: #666;
            font-size: 12px;
            text-align: center;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🎥 RenderMe360 Camera Setup Visualization</h1>
        
        <div class="info-box">
            <strong>Dataset:</strong> RenderMe360 | <strong>Performance:</strong> s3_all | 
            <strong>Subject:</strong> 0026 | <strong>Total Cameras:</strong> {len(camera_data)}
        </div>
        
        <div class="instructions">
            <h3>📖 How to Use This Visualization</h3>
            <ul>
                <li><strong>3D View (Top Panel):</strong>
                    <ul>
                        <li>🖱️ <strong>Rotate:</strong> Left-click and drag</li>
                        <li>🔍 <strong>Zoom:</strong> Scroll wheel or pinch</li>
                        <li>✋ <strong>Pan:</strong> Right-click and drag</li>
                        <li>🏠 <strong>Reset:</strong> Double-click</li>
                        <li>📷 <strong>Save:</strong> Use camera icon in toolbar</li>
                    </ul>
                </li>
                <li><strong>2D Views (Bottom Panels):</strong>
                    <ul>
                        <li>Left: Top-down view showing XY positions</li>
                        <li>Right: Cylindrical unwrapping (angle vs height)</li>
                    </ul>
                </li>
                <li><strong>Hover</strong> over any camera to see detailed information</li>
            </ul>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-label">Angular Coverage</div>
                <div class="stat-value">{max(azimuth_vals) - min(azimuth_vals):.1f}°</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Height Range</div>
                <div class="stat-value">{min(z_vals):.1f}m to {max(z_vals):.1f}m</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Radial Distance</div>
                <div class="stat-value">{min(r_xy_vals):.2f}m - {max(r_xy_vals):.2f}m</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Mean Radius</div>
                <div class="stat-value">{np.mean(r_xy_vals):.2f}m</div>
            </div>
        </div>
        
        {html_str}
        
        <div class="footer">
            <p>Generated from RenderMe360 calibration data | Camera positions computed using cam_pos = -t from RT matrix</p>
            <p>This is a standalone HTML file that can be shared and opened in any modern web browser.</p>
        </div>
    </div>
</body>
</html>"""
    
    # Write to file
    with open(output_path, 'w') as f:
        f.write(full_html)
    
    print(f"Standalone HTML visualization created: {output_path}")
    print(f"File size: {Path(output_path).stat().st_size / 1024:.1f} KB")
    print("\nThis file can be:")
    print("  ✓ Committed to git")
    print("  ✓ Shared with anyone")
    print("  ✓ Opened in any web browser")
    print("  ✓ Used without Python or any dependencies")

if __name__ == "__main__":
    output_path = Path('/ssd2/zhuoyuan/renderme360_temp/download_all/visualizations/camera_analysis/camera_visualization_interactive.html')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    create_standalone_html(output_path)