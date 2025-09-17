#!/usr/bin/env python3
"""
Visual inspection tool for extracted RenderMe360 data
Creates an HTML overview with sample images and statistics
"""

import os
from pathlib import Path
import numpy as np
import cv2
import json
from datetime import datetime

def create_html_overview(extraction_dir, output_file="extraction_overview.html"):
    """Create an HTML file with visual overview of extracted data"""
    
    extraction_path = Path(extraction_dir)
    performances = sorted([d for d in extraction_path.iterdir() if d.is_dir() and d.name.startswith('0026_')])
    
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>RenderMe360 Extraction Overview</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
            .performance { background: white; margin: 20px 0; padding: 20px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
            .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 10px; margin: 20px 0; }
            .grid img { width: 100%; height: auto; border-radius: 5px; }
            .stats { background: #f0f0f0; padding: 10px; border-radius: 5px; margin: 10px 0; }
            h1 { color: #333; }
            h2 { color: #666; border-bottom: 2px solid #ddd; padding-bottom: 5px; }
            .meta { color: #888; font-size: 0.9em; }
            table { width: 100%; border-collapse: collapse; margin: 10px 0; }
            th, td { padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }
            th { background: #f0f0f0; }
        </style>
    </head>
    <body>
        <h1>🎬 RenderMe360 Extraction Overview</h1>
        <p class="meta">Generated: """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """</p>
    """
    
    # Overall statistics
    total_size = 0
    total_images = 0
    
    for perf_dir in performances:
        perf_name = perf_dir.name
        
        # Check if extraction is complete
        if not (perf_dir / '.extraction_complete').exists():
            html_content += f'<div class="performance"><h2>{perf_name} - ⚠️ Incomplete</h2></div>'
            continue
            
        html_content += f'<div class="performance">'
        html_content += f'<h2>{perf_name}</h2>'
        
        # Read metadata
        metadata_file = perf_dir / 'from_anno' / 'metadata' / 'info.json'
        if metadata_file.exists():
            with open(metadata_file) as f:
                metadata = json.load(f)
                html_content += f'<div class="stats">'
                html_content += f'<table>'
                html_content += f'<tr><th>Property</th><th>Value</th></tr>'
                html_content += f'<tr><td>Performance Type</td><td>{metadata.get("performance", "Unknown")}</td></tr>'
                html_content += f'<tr><td>Total Frames</td><td>{metadata.get("total_frames", 0)}</td></tr>'
                html_content += f'<tr><td>Total Cameras</td><td>{metadata.get("total_cameras", 0)}</td></tr>'
                html_content += f'<tr><td>Capture Date</td><td>{metadata.get("capture_date", "Unknown")}</td></tr>'
                html_content += f'</table>'
                html_content += f'</div>'
        
        # Sample images from different cameras
        images_dir = perf_dir / 'from_raw' / 'images'
        if images_dir.exists():
            html_content += '<h3>Sample Images (Frame 0 from different cameras)</h3>'
            html_content += '<div class="grid">'
            
            # Get sample cameras (every 10th camera)
            camera_dirs = sorted([d for d in images_dir.iterdir() if d.is_dir()])
            sample_cameras = camera_dirs[::10][:6]  # Get 6 cameras max
            
            for cam_dir in sample_cameras:
                frame_0 = cam_dir / 'frame_000000.jpg'
                if frame_0.exists():
                    # Create relative path for HTML
                    rel_path = frame_0.relative_to(extraction_path.parent)
                    html_content += f'<div>'
                    html_content += f'<img src="{rel_path}" alt="{cam_dir.name}">'
                    html_content += f'<p style="text-align:center; font-size:0.8em;">{cam_dir.name}</p>'
                    html_content += f'</div>'
            
            html_content += '</div>'
            
            # Count total images
            image_count = sum(1 for _ in images_dir.rglob('*.jpg'))
            total_images += image_count
            html_content += f'<p>Total images: {image_count:,}</p>'
        
        # Check for special data
        special_data = []
        if (perf_dir / 'from_anno' / 'flame').exists():
            special_data.append("FLAME")
        if (perf_dir / 'from_anno' / 'uv_textures').exists():
            special_data.append("UV Textures")
        if (perf_dir / 'from_anno' / 'scan').exists():
            special_data.append("3D Scan")
        if (perf_dir / 'from_anno' / 'audio').exists():
            special_data.append("Audio")
            
        if special_data:
            html_content += f'<p><strong>Special data:</strong> {", ".join(special_data)}</p>'
        
        # Size information
        size_file = perf_dir / 'size_summary.txt'
        if size_file.exists():
            with open(size_file) as f:
                size_info = f.read()
                html_content += f'<pre style="background:#f0f0f0; padding:10px; border-radius:5px;">{size_info}</pre>'
        
        html_content += '</div>'
    
    # Summary
    html_content += f"""
    <div class="performance" style="background: #e8f4f8;">
        <h2>📊 Summary</h2>
        <table>
            <tr><th>Total Performances</th><td>{len(performances)}</td></tr>
            <tr><th>Total Images</th><td>{total_images:,}</td></tr>
        </table>
    </div>
    </body>
    </html>
    """
    
    # Save HTML
    output_path = extraction_path.parent / output_file
    with open(output_path, 'w') as f:
        f.write(html_content)
    
    print(f"✅ Created visual overview: {output_path}")
    print(f"   Open in browser: firefox {output_path} &")
    return output_path

def create_sample_grid(extraction_dir, performance="0026_e0", output_file="sample_grid.jpg"):
    """Create a grid image showing multiple cameras and frames"""
    
    perf_dir = Path(extraction_dir) / performance
    images_dir = perf_dir / 'from_raw' / 'images'
    
    if not images_dir.exists():
        print(f"❌ No images found for {performance}")
        return
    
    # Get sample cameras and frames
    cameras = sorted([d.name for d in images_dir.iterdir() if d.is_dir()])[:4]  # First 4 cameras
    frames = [0, 10, 20, 30]  # Sample frames
    
    grid_images = []
    for cam in cameras:
        row_images = []
        for frame in frames:
            img_path = images_dir / cam / f'frame_{frame:06d}.jpg'
            if img_path.exists():
                img = cv2.imread(str(img_path))
                # Resize to thumbnail
                img = cv2.resize(img, (256, 256))
                # Add label
                cv2.putText(img, f"{cam} F{frame}", (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                row_images.append(img)
            else:
                # Create placeholder
                img = np.zeros((256, 256, 3), dtype=np.uint8)
                row_images.append(img)
        
        if row_images:
            grid_images.append(np.hstack(row_images))
    
    if grid_images:
        final_grid = np.vstack(grid_images)
        output_path = Path(extraction_dir).parent / output_file
        cv2.imwrite(str(output_path), final_grid)
        print(f"✅ Created sample grid: {output_path}")
        print(f"   View image: eog {output_path} &")
        return output_path

def quick_stats(extraction_dir):
    """Print quick statistics about extracted data"""
    
    extraction_path = Path(extraction_dir)
    performances = sorted([d for d in extraction_path.iterdir() if d.is_dir() and d.name.startswith('0026_')])
    
    print("\n" + "="*60)
    print("EXTRACTION STATISTICS")
    print("="*60)
    
    for perf_dir in performances:
        perf_name = perf_dir.name
        complete = (perf_dir / '.extraction_complete').exists()
        
        if complete:
            # Count images
            images_dir = perf_dir / 'from_raw' / 'images'
            if images_dir.exists():
                n_cameras = len(list(images_dir.iterdir()))
                sample_cam = next(images_dir.iterdir(), None)
                if sample_cam:
                    n_frames = len(list(sample_cam.glob('*.jpg')))
                else:
                    n_frames = 0
                
                print(f"\n{perf_name}: ✅ Complete")
                print(f"  Cameras: {n_cameras}")
                print(f"  Frames: {n_frames}")
                print(f"  Total images: {n_cameras * n_frames:,}")
            else:
                print(f"\n{perf_name}: ✅ Complete (no images)")
        else:
            print(f"\n{perf_name}: ⚠️ Incomplete")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Inspect extracted RenderMe360 data')
    parser.add_argument('--dir', default='/ssd4/zhuoyuan/renderme360_temp/FULL_EXTRACTION',
                        help='Extraction directory')
    parser.add_argument('--html', action='store_true', help='Create HTML overview')
    parser.add_argument('--grid', action='store_true', help='Create sample grid image')
    parser.add_argument('--stats', action='store_true', help='Print statistics')
    parser.add_argument('--performance', default='0026_e0', help='Performance for grid')
    
    args = parser.parse_args()
    
    if not any([args.html, args.grid, args.stats]):
        args.stats = True  # Default to stats
    
    if args.stats:
        quick_stats(args.dir)
    
    if args.html:
        create_html_overview(args.dir)
    
    if args.grid:
        create_sample_grid(args.dir, args.performance)