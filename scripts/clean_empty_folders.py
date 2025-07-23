#!/usr/bin/env python3
"""
clean_empty_folders.py

Recursively scans TARGET_DIR for empty directories and, after user confirmation,
deletes them. Mirrors the behavior of the original Bash script.
"""

import os
import sys
from pathlib import Path

def main():
    # 1) Determine TARGET_DIR
    target = os.getenv("TARGET_DIR")
    if not target:
        if len(sys.argv) > 1:
            target = sys.argv[1]
        else:
            print("❌ Error: TARGET_DIR must be set before running this script.")
            sys.exit(1)

    target_path = Path(target)
    if not target_path.is_dir():
        print(f"❌ Error: TARGET_DIR is not a directory: {target}")
        sys.exit(1)

    # 2) Find empty directories bottom-up so parents become empty too
    empty_dirs = []
    for dirpath, dirnames, filenames in os.walk(target_path, topdown=False):
        # normalize filenames to lowercase for comparison
        lower_files = [filename.lower() for filename in filenames]
        # if it’s empty
        if (not dirnames) and (not lower_files or all(filename == ".ds_store" for filename in lower_files)):
            empty_dirs.append(Path(dirpath))
    print(f"{empty_dirs}")
    count = len(empty_dirs)

    if count == 0:
        print(f"✅ No empty folders found in: {target}")
        sys.exit(0)

    # 3) Prompt user
    print(f"🧹 Found {count} empty folder{'s' if count!=1 else ''} under: {target}")
    confirm = input("Do you want to delete them?\n[y/n] ").strip().lower()

    # 4) Delete if confirmed
    if confirm.startswith('y'):
        for directory in empty_dirs:
            # remove .DS_Store if present
            ds_store = directory / ".DS_Store"
            try:
                # Remove .DS_Store if present
                if ds_store.exists():
                    ds_store.unlink()
                # Attempt to remove the directory itself
                directory.rmdir()
                print(f"🗑 Removed: {directory}")
            except Exception:
                # skip those that can't be removed
                pass
        print("✅ All empty folders deleted.\n\n")
    else:
        print("❌ Cleanup canceled. No folders were deleted.\n\n")

if __name__ == "__main__":
    main()