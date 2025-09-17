#!/usr/bin/env python3
"""
Script to update hardcoded storage paths after server migration
Supports bidirectional updates: /ssd4/ <-> /ssd4/
"""

import os
import re
import json
import sys
from pathlib import Path

def update_file_paths(file_path, source_path, target_path, dry_run=False):
    """Update paths in a single file"""
    try:
        # Handle Jupyter notebooks specially
        if file_path.suffix == '.ipynb':
            with open(file_path, 'r') as f:
                notebook = json.load(f)

            count = 0
            for cell in notebook.get('cells', []):
                if 'source' in cell:
                    if isinstance(cell['source'], list):
                        for i, line in enumerate(cell['source']):
                            if source_path in line:
                                cell['source'][i] = line.replace(source_path, target_path)
                                count += line.count(source_path)
                    else:
                        if source_path in cell['source']:
                            old_count = cell['source'].count(source_path)
                            cell['source'] = cell['source'].replace(source_path, target_path)
                            count += old_count

            if count > 0 and not dry_run:
                with open(file_path, 'w') as f:
                    json.dump(notebook, f, indent=1)
                print(f"✓ Updated {file_path.relative_to(repo_root)}: {count} replacements")
            elif count > 0:
                print(f"  Would update {file_path.relative_to(repo_root)}: {count} replacements")

            return count

        # Regular text files
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        count = content.count(source_path)
        if count == 0:
            return 0

        new_content = content.replace(source_path, target_path)

        if not dry_run:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"✓ Updated {file_path.relative_to(repo_root)}: {count} replacements")
        else:
            print(f"  Would update {file_path.relative_to(repo_root)}: {count} replacements")

        return count
    except Exception as e:
        print(f"✗ Error updating {file_path}: {e}")
        return 0

def find_all_files_with_path(base_dir, search_path):
    """Find all files containing the search path"""
    files_found = []

    # Extensions to check
    extensions = {'.py', '.yaml', '.yml', '.sh', '.json', '.md', '.ipynb', '.txt', '.cfg', '.config'}

    # Directories to skip
    skip_dirs = {'.git', '__pycache__', '.ipynb_checkpoints', 'node_modules', '.venv', 'venv', 'temp_smc'}

    for root, dirs, files in os.walk(base_dir):
        # Skip certain directories
        dirs[:] = [d for d in dirs if d not in skip_dirs]

        for file in files:
            file_path = Path(root) / file
            if file_path.suffix in extensions:
                try:
                    if file_path.suffix == '.ipynb':
                        # Check JSON content for notebooks
                        with open(file_path, 'r') as f:
                            content = f.read()
                            if search_path in content:
                                files_found.append(file_path)
                    else:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            if search_path in f.read():
                                files_found.append(file_path)
                except:
                    pass  # Skip unreadable files

    return files_found

# Global variable for repo root
repo_root = None

def main():
    global repo_root

    print("="*60)
    print("Storage Path Migration Script")
    print("="*60)

    # Parse command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == '--reverse':
            source_path = '/ssd4/'
            target_path = '/ssd4/'
            print("Mode: Reverse migration (/ssd4/ → /ssd4/)")
        else:
            print(f"Unknown argument: {sys.argv[1]}")
            print("Usage: python update_paths_ssd2_to_ssd4.py [--reverse]")
            return
    else:
        source_path = '/ssd4/'
        target_path = '/ssd4/'
        print("Mode: Forward migration (/ssd4/ → /ssd4/)")

    # Find repository root
    script_path = Path(__file__).resolve()
    repo_root = script_path
    while repo_root.name != 'renderme360_temp' and repo_root.parent != repo_root:
        repo_root = repo_root.parent

    if repo_root.name != 'renderme360_temp':
        print("Error: Could not find renderme360_temp directory")
        return

    print(f"Repository root: {repo_root}")
    print(f"\n🔍 Scanning for files containing '{source_path}'...")
    print("-"*40)

    # Find all files
    files_to_update = find_all_files_with_path(repo_root, source_path)

    if not files_to_update:
        print(f"\n✓ No files with '{source_path}' paths found.")
        return

    # Group by directory
    by_dir = {}
    for file_path in files_to_update:
        dir_path = file_path.parent.relative_to(repo_root)
        if dir_path not in by_dir:
            by_dir[dir_path] = []
        by_dir[dir_path].append(file_path.name)

    print(f"\nFound {len(files_to_update)} files in {len(by_dir)} directories:")
    for dir_path in sorted(by_dir.keys()):
        print(f"\n  📁 {dir_path}/")
        for file in sorted(by_dir[dir_path])[:5]:  # Show first 5 files
            print(f"     - {file}")
        if len(by_dir[dir_path]) > 5:
            print(f"     ... and {len(by_dir[dir_path])-5} more files")

    # Dry run first
    print("\n🔍 DRY RUN - Checking replacements needed:")
    print("-"*40)
    total_replacements = 0

    for file_path in files_to_update:
        count = update_file_paths(file_path, source_path, target_path, dry_run=True)
        total_replacements += count

    print(f"\nTotal replacements needed: {total_replacements}")
    print(f"Files to update: {len(files_to_update)}")

    # Ask for confirmation
    print("\n" + "="*40)
    print(f"This will replace ALL occurrences of '{source_path}' with '{target_path}'")
    response = input("Proceed with updates? (yes/no): ").strip().lower()

    if response != 'yes':
        print("Cancelled. No files were modified.")
        return

    # Perform actual updates
    print("\n📝 UPDATING FILES:")
    print("-"*40)
    success_count = 0

    for file_path in files_to_update:
        count = update_file_paths(file_path, source_path, target_path, dry_run=False)
        if count > 0:
            success_count += 1

    print("\n" + "="*60)
    print(f"✅ COMPLETE: Updated {success_count}/{len(files_to_update)} files")
    print(f"Replaced: '{source_path}' → '{target_path}'")
    print("="*60)

    # Next steps
    print("\n📋 NEXT STEPS:")
    print("1. Verify changes: git diff")
    print("2. Test imports: python -c 'from renderme_360_reader import SMCReader'")
    print("3. Run a test to verify everything works")
    print(f"4. Commit: git commit -am 'Update paths from {source_path} to {target_path} for server migration'")
    print(f"\n💡 TIP: To reverse this migration, run: python {Path(__file__).name} --reverse")

if __name__ == "__main__":
    main()