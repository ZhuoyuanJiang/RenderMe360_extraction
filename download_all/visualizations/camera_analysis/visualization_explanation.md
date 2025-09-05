# Camera Visualization Explanations

## Files Generated

### 1. `3d_camera_positions.png`
This visualization shows camera positions in 3D space with multiple views:

- **Color coding:**
  - **Green dots**: Cameras that are common across ALL analyzed subjects (0018, 0019, 0026)
  - **Orange dots**: Cameras that are specific to individual subjects (shouldn't appear if all have same cameras)
  - In our case, ALL cameras are green because all 38 cameras are present in all 3 subjects

- **Four panels:**
  1. **3D scatter plot**: Shows cameras in 3D space around the subject (red star)
  2. **Top-down view**: Bird's eye view of camera arrangement
  3. **Polar plot**: Shows angular distribution and distance from center
  4. **Height distribution**: Bar chart showing camera heights

### 2. `cylindrical_camera_visualization.png` (New improved version)
Better visualization showing the cylindrical arrangement:

- **Color gradient**: Purple (low cameras) to Yellow (high cameras)
- **Cylindrical wireframe**: Shows the approximate cylinder cameras are arranged on
- **Four views:**
  1. **3D Cylindrical view**: Shows cameras on a transparent cylinder
  2. **Polar top-down view**: Angular distribution with distance
  3. **Unwrapped cylinder**: Angle vs height plot (like unrolling the cylinder)
  4. **Height distribution**: Sorted by camera ID

### 3. `all_38_cameras_grid.png`
- Shows actual images from ALL 38 cameras at the same frame/timestamp
- 6x7 grid layout displaying frame 100 from each camera
- Allows visual assessment of coverage and image quality

### 4. `subset_comparison.png`
- Compares different camera subset sizes (4, 8, 12, 16 cameras)
- Shows which cameras would be selected for each configuration
- Includes quality scores and storage estimates

### 5. `sample_frames_X_cameras.png`
- Shows sample frames for specific subset sizes (4, 8, 12 cameras)
- Demonstrates actual visual coverage with different camera counts

## Key Findings from Visualizations

1. **Cylindrical Arrangement**: Cameras are arranged in an approximate cylinder around the subject, not a perfect circle
2. **Height Levels**: Cameras are at 4 distinct height levels (1.0m, 1.1m, 1.3m, 1.5m)
3. **Irregular Gaps**: There's a large gap between cameras 49 and 29 (342°), indicating non-uniform distribution
4. **Consistent Pattern**: All 3 subjects have identical camera configurations