#!/bin/bash
# Check mask extraction progress for each camera

mask_dir="/ssd4/zhuoyuan/renderme360_temp/test_download/subjects/0026/s1_all/from_anno/masks"

for cam_dir in "$mask_dir"/cam_*; do
    if [ -d "$cam_dir" ]; then
        cam_name=$(basename "$cam_dir")
        count=$(ls "$cam_dir"/*.png 2>/dev/null | wc -l)
        echo "$cam_name: $count/2529 frames"
    fi
done