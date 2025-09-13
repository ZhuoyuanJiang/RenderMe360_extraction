#!/usr/bin/env python3
"""
Test script for RenderMe360 21ID extraction pipeline
Tests configuration and basic functionality before full extraction
"""

import sys
import yaml
from pathlib import Path

def test_configuration():
    """Test that configuration is properly set up."""
    print("="*60)
    print("Testing RenderMe360 21ID Extraction Configuration")
    print("="*60)
    
    # Check config file exists
    config_path = Path("config_21id.yaml")
    if not config_path.exists():
        print("✗ Config file not found: config_21id.yaml")
        print("  Run the extraction script once to create default config")
        return False
    print("✓ Config file found")
    
    # Load config
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Check Google Drive settings
    print("\nGoogle Drive Configuration:")
    folder_id = config['google_drive']['root_folder_id']
    if folder_id == "YOUR_FOLDER_ID_HERE":
        print("✗ Google Drive folder ID not configured!")
        print("  Edit config_21id.yaml and set the root_folder_id")
        return False
    print(f"✓ Folder ID configured: {folder_id[:20]}...")
    
    remote_name = config['google_drive']['remote_name']
    print(f"✓ Remote name: {remote_name}")
    
    # Check storage paths
    print("\nStorage Configuration:")
    paths_to_check = [
        ('Temp directory', config['storage']['temp_dir']),
        ('Output directory', config['storage']['output_dir']),
        ('Log directory', config['storage']['log_dir'])
    ]
    
    for name, path in paths_to_check:
        p = Path(path)
        if p.exists():
            print(f"✓ {name}: {path} (exists)")
        else:
            print(f"⚠ {name}: {path} (will be created)")
    
    # Check extraction settings
    print("\nExtraction Configuration:")
    subjects = config['extraction']['subjects']
    performances = config['extraction']['performances']
    modalities = config['extraction']['modalities']
    
    print(f"  Subjects to process: {subjects}")
    print(f"  Performances: {len(performances)} performances")
    print(f"  Modalities: {len(modalities)} types")
    print(f"  Camera selection: {config['extraction']['cameras']}")
    print(f"  Separate sources: {config['extraction'].get('separate_sources', True)}")
    
    # Check processing settings
    print("\nProcessing Configuration:")
    print(f"  Delete after extraction: {config['processing']['delete_smc_after_extraction']}")
    print(f"  Force re-extract: {config['processing']['force_reextract']}")
    print(f"  Max retries: {config['processing']['max_retries']}")
    
    print("\n" + "="*60)
    print("Configuration test complete!")
    print("="*60)
    
    return True

def test_dependencies():
    """Test that required dependencies are installed."""
    print("\nTesting Dependencies:")
    print("-"*40)
    
    dependencies = [
        ('numpy', 'import numpy'),
        ('opencv-python', 'import cv2'),
        ('pandas', 'import pandas'),
        ('pyyaml', 'import yaml'),
        ('tqdm', 'import tqdm'),
        ('plyfile (optional)', 'import plyfile')
    ]
    
    all_good = True
    for name, import_cmd in dependencies:
        try:
            exec(import_cmd)
            print(f"✓ {name}")
        except ImportError:
            if 'optional' in name:
                print(f"⚠ {name} - not critical")
            else:
                print(f"✗ {name} - required!")
                all_good = False
    
    # Check rclone
    print("\nChecking rclone:")
    import subprocess
    try:
        result = subprocess.run(['rclone', 'version'], capture_output=True, text=True)
        if result.returncode == 0:
            version = result.stdout.split('\n')[0]
            print(f"✓ rclone installed: {version}")
            
            # Check configured remotes
            result = subprocess.run(['rclone', 'listremotes'], capture_output=True, text=True)
            remotes = result.stdout.strip().split('\n')
            print(f"  Configured remotes: {', '.join(remotes)}")
            
            if 'vllab13:' not in remotes:
                print("  ⚠ Warning: 'vllab13' remote not found")
                print("    Configure with: rclone config")
        else:
            print("✗ rclone not working properly")
            all_good = False
    except FileNotFoundError:
        print("✗ rclone not installed!")
        print("  Install with: curl https://rclone.org/install.sh | sudo bash")
        all_good = False
    
    # Check renderme_360_reader
    print("\nChecking RenderMe360 reader:")
    reader_path = Path("renderme_360_reader.py")
    if reader_path.exists():
        print(f"✓ Reader script found: {reader_path}")
    else:
        print(f"✗ Reader script not found!")
        print(f"  Expected at: {reader_path.absolute()}")
        all_good = False
    
    return all_good

def test_dry_run():
    """Test extraction script in dry-run mode."""
    print("\n" + "="*60)
    print("Testing Extraction Script (Dry Run)")
    print("="*60)
    
    import subprocess
    
    # Run with dry-run flag
    cmd = [
        sys.executable,
        'extract_subject_FULL_both.py',
        '--config', 'config_21id.yaml',
        '--dry-run'
    ]
    
    print(f"Running: {' '.join(cmd)}")
    print("-"*40)
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✓ Dry run successful")
            if result.stdout:
                print("\nOutput preview:")
                lines = result.stdout.split('\n')[:10]
                for line in lines:
                    print(f"  {line}")
        else:
            print("✗ Dry run failed")
            if result.stderr:
                print(f"Error: {result.stderr}")
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print("✗ Script timeout")
        return False
    except Exception as e:
        print(f"✗ Error running script: {e}")
        return False

def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("RENDERME360 21ID EXTRACTION PIPELINE TEST")
    print("="*80)
    
    # Test configuration
    config_ok = test_configuration()
    
    # Test dependencies
    deps_ok = test_dependencies()
    
    # Test dry run if config is OK
    dryrun_ok = False
    if config_ok and deps_ok:
        dryrun_ok = test_dry_run()
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    if config_ok and deps_ok and dryrun_ok:
        print("✓ All tests passed!")
        print("\nReady to run extraction:")
        print("  python extract_subject_FULL_both.py --config config_21id.yaml")
        print("\nOr test with single performance:")
        print("  python extract_subject_FULL_both.py --subject 0026 --performance s1_all")
    else:
        print("✗ Some tests failed. Please fix the issues above.")
        if not config_ok:
            print("\n1. Edit config_21id.yaml and set the Google Drive folder ID")
        if not deps_ok:
            print("\n2. Install missing dependencies:")
            print("   pip install numpy opencv-python pandas pyyaml tqdm")
        
    print("\n" + "="*80)

if __name__ == '__main__':
    main()