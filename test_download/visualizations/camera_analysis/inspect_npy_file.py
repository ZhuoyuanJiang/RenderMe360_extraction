#!/usr/bin/env python3
"""
Simple tool to inspect .npy file and see what's inside.
e.g. cam_59.npy
"""

import numpy as np
import sys

def inspect_npy(filepath):
    """Load and display contents of any .npy file."""

    print(f"Inspecting: {filepath}\n")

    # Load the file
    data = np.load(filepath, allow_pickle=True)

    # If it's an object array containing a single item (usually a dict), extract it
    if data.dtype == object:
        try:
            data = data.item()
        except:
            pass  # Keep as is if .item() doesn't work

    # Display the data
    print(f"Type: {type(data)}")

    if isinstance(data, dict):
        print(f"Dictionary with {len(data)} keys")
        print(f"Keys: {list(data.keys())[:10]}{'...' if len(data) > 10 else ''}\n")

        # Show first item as example
        if data:
            first_key = list(data.keys())[0]
            print(f"Example - data['{first_key}']:")
            first_item = data[first_key]
            if isinstance(first_item, dict):
                print(f"  Dict with keys: {list(first_item.keys())}")
                for k, v in first_item.items():
                    if isinstance(v, np.ndarray):
                        print(f"    {k}: array with shape {v.shape}")
                    else:
                        print(f"    {k}: {type(v).__name__}")
            elif isinstance(first_item, np.ndarray):
                print(f"  Array with shape {first_item.shape}, dtype {first_item.dtype}")
            else:
                print(f"  {first_item}")

    elif isinstance(data, np.ndarray):
        print(f"Array shape: {data.shape}")
        print(f"Array dtype: {data.dtype}")
        if data.size < 100:
            print(f"Data:\n{data}")
        else:
            print(f"First few elements:\n{data.flat[:10]}...")
    else:
        print(data)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python inspect_npy_file.py <path_to_npy_file>")
        print("\nExample:")
        print("  python inspect_npy_file.py /path/to/file.npy")
        sys.exit(1)

    inspect_npy(sys.argv[1])