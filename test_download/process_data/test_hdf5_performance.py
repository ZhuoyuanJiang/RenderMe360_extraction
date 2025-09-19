#!/usr/bin/env python3
"""Test HDF5 read performance for RAW vs ANNO files."""

import h5py
import time
import numpy as np

def test_read_performance(file_path, dataset_path, num_reads=10):
    """Test sequential read performance of HDF5 dataset."""
    with h5py.File(file_path, 'r') as f:
        print(f"\nFile: {file_path}")
        print(f"Dataset: {dataset_path}")

        # Navigate to dataset
        parts = dataset_path.split('/')
        dset = f
        for part in parts:
            if part:
                dset = dset[part]

        # Get dataset info
        if hasattr(dset, 'chunks'):
            print(f"Chunks: {dset.chunks}")
        if hasattr(dset, 'compression'):
            print(f"Compression: {dset.compression}")
        if hasattr(dset, 'shape'):
            print(f"Shape: {dset.shape}")

        # Test read performance
        keys = list(dset.keys())[:num_reads] if hasattr(dset, 'keys') else []

        if keys:
            start = time.time()
            for key in keys:
                data = dset[key][()]
                if isinstance(data, np.ndarray):
                    _ = data.shape  # Force data to be read
            elapsed = time.time() - start
            print(f"Read {len(keys)} items in {elapsed:.2f} seconds")
            print(f"Average: {elapsed/len(keys)*1000:.1f} ms per read")

# Test both files
print("Testing HDF5 read performance...")

# Test RAW file image reads
test_read_performance(
    '/ssd4/zhuoyuan/renderme360_temp/temp_smc/0026_s1_all_raw.smc',
    'Camera/00/color',
    num_reads=10
)

# Test ANNO file mask reads
test_read_performance(
    '/ssd4/zhuoyuan/renderme360_temp/temp_smc/0026_s1_all_anno.smc',
    'Camera/00/mask',
    num_reads=10
)