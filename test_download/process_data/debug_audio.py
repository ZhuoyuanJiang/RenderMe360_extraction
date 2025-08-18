#!/usr/bin/env python3
"""Debug script to find where audio is stored in speech files"""

import h5py
from pathlib import Path

# Check s1_all anno file structure
anno_file = Path('/ssd2/zhuoyuan/renderme360_temp/test_download/anno/0026_s1_all_anno.smc')

print(f"Inspecting: {anno_file.name}")
print("=" * 60)

with h5py.File(anno_file, 'r') as f:
    def print_structure(name, obj, indent=0):
        """Recursively print HDF5 structure"""
        if indent < 3:  # Limit depth to avoid too much output
            print(" " * indent + name)
            if isinstance(obj, h5py.Group):
                for key in list(obj.keys())[:10]:  # Limit to first 10 keys
                    if key == 'audio' or 'audio' in key.lower():
                        print(" " * (indent+2) + f">>> FOUND AUDIO: {key}")
    
    print("\nHDF5 Structure:")
    f.visititems(print_structure)
    
    print("\nTop-level keys:")
    for key in f.keys():
        print(f"  - {key}")
    
    # Check if audio exists at different locations
    print("\nSearching for audio...")
    
    # Try different possible locations
    locations = [
        "audio",
        "Audio", 
        "Camera/00/audio",
        "Camera/audio",
        "audio_data",
    ]
    
    for loc in locations:
        try:
            parts = loc.split('/')
            obj = f
            for part in parts:
                obj = obj[part]
            print(f"  ✓ Found at: {loc} - Shape: {obj.shape if hasattr(obj, 'shape') else 'Group'}")
        except:
            print(f"  ✗ Not at: {loc}")
    
    # Check what's in Camera/00
    if 'Camera' in f and '00' in f['Camera']:
        print("\nContents of Camera/00:")
        for key in list(f['Camera']['00'].keys())[:20]:
            print(f"  - {key}")