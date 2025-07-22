#!/usr/bin/env python3
"""
process_photos.py

Renames media files under TARGET_DIR to a timestamp-based filename using
the EXIF CreateDate (including subseconds) or, if missing, by parsing the
original filename. Matched files are renamed in place; unmatched files are
moved to an “unmatched” folder. Duplicate target names get “(1)”, “(2)”, etc.
"""

import os
import sys
import re
import subprocess
from tqdm import tqdm
from datetime import datetime
from pathlib import Path

# ─── Configuration ────────────────────────────────────────────────────────────

# Read TARGET_DIR from env or first arg
TARGET_DIR = os.getenv("TARGET_DIR") or (sys.argv[1] if len(sys.argv) > 1 else None)
OUTPUT_DIR = os.getenv("OUTPUT_DIR") or (sys.argv[2] if len(sys.argv) > 2 else TARGET_DIR)

if not TARGET_DIR:
    print("❌ Error: TARGET_DIR must be set (env or first arg).", file=sys.stderr)
    sys.exit(1)

# Paths
UNMATCHED_DIR    = os.path.join(TARGET_DIR, "unmatched")
LOG_DIR          = os.path.join(TARGET_DIR, "logs")
MATCHED_LOG_PATH = os.path.join(LOG_DIR, "matched.txt")
UNMATCHED_LOG_PATH = os.path.join(LOG_DIR, "unmatched.txt")
ERROR_LOG_PATH    = os.path.join(LOG_DIR, "errors.txt")

# Prepare directories
os.makedirs(UNMATCHED_DIR, exist_ok=True)
os.makedirs(LOG_DIR,        exist_ok=True)

# Truncate logs
for path in (MATCHED_LOG_PATH, UNMATCHED_LOG_PATH, ERROR_LOG_PATH):
    open(path, "w", encoding="utf-8").close()

# Supported media extensions
MEDIA_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".webp", ".heic",
    ".mp4", ".mov", ".avi", ".3gp", ".mpg", ".m4v", ".gif"
}

# Regex to parse YYYYMMDD and optional HHMMSS from filename
FILENAME_DATE_REGEX = re.compile(
    r'^([0-9]{4})[-._]?([0-9]{2})[-._]?([0-9]{2})(?:[_-]?([0-9]{6}))?'
)

def log_matched(message: str):
    with open(MATCHED_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(message + "\n")

def log_unmatched(message: str):
    with open(UNMATCHED_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(message + "\n")

def log_error(message: str):
    with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(message + "\n")

def list_all_media_files():
    """Return list of all media file paths under TARGET_DIR (excluding 'unmatched' and 'logs')."""
    paths = []
    for root, dirs, files in os.walk(TARGET_DIR):
        # Skip our own output folders
        if os.path.commonpath([root, UNMATCHED_DIR]) == UNMATCHED_DIR:
            continue
        if os.path.commonpath([root, LOG_DIR]) == LOG_DIR:
            continue
        for filename in files:
            ext = os.path.splitext(filename)[1].lower()
            if ext in MEDIA_EXTENSIONS:
                paths.append(os.path.join(root, filename))
    return paths

def extract_exif_create_date(media_path: str):
    """
    Reads the EXIF CreateDate and SubSecTimeOriginal directly from the media file.
    Returns a tuple (create_date_str, subseconds) or (None, None) on failure.
    """
    try:
        # -s3 : print tag values only, one-per-line
        # CreateDate → e.g. "2023:05:06 12:34:56"
        # SubSecTimeOriginal → e.g. "123"
        output = subprocess.check_output([
            "exiftool", "-s3",
            "-CreateDate",       # tag for the main timestamp
            "-SubSecTimeOriginal",  # tag for sub-seconds
            media_path
        ], stderr=subprocess.DEVNULL).decode("utf-8", "ignore").splitlines()
        
        if not output:
            return None, None
        
        create_date = output[0].strip()
        subsec      = output[1].strip() if len(output) > 1 else ""
        return create_date, subsec

    except Exception as e:
        log_error(f"❌ EXIF read failed for {media_path}: {e}")
        return None, None

def parse_date_from_filename(name: str):
    """
    Parse YYYY MM DD and optional HHMMSS from name.
    Returns (year,month,day,hh,mm,ss) or None.
    """
    m = FILENAME_DATE_REGEX.match(name)
    if not m:
        return None
    year, month, day, timepart = m.groups()
    if timepart:
        hh, mm, ss = timepart[:2], timepart[2:4], timepart[4:6]
    else:
        hh, mm, ss = "00", "00", "00"
    return year, month, day, hh, mm, ss
    
def make_unique_path(directory: Path, base_name: str, extension: str, original_path: Path = None) -> Path:
    """
    If dest_dir/base_name+extension exists *and* is not the same as original_path,
    append (1), (2), ... before the extension. Otherwise return the straight path.
    """
    candidate = directory / f"{base_name}{extension}"
    # if it doesn't exist, or it *is* our original file, use it
    if not candidate.exists() or (original_path and candidate.samefile(original_path)):
        return candidate

    index = 1
    while True:
        candidate = directory / f"{base_name}({index}){extension}"
        if not candidate.exists():
            return candidate
        index += 1

def main():
    media_paths = list_all_media_files()
    if not media_paths:
        print(f"ℹ️  No media files found under {TARGET_DIR}.")
        return

    print(f"📅 Processing {len(media_paths)} media file(s)")

    for media_path in tqdm(media_paths, desc="📅 Inferring dates", unit="file", file=sys.stderr):
        filename        = os.path.basename(media_path)
        name_root, ext  = os.path.splitext(filename)
        ext             = ext.lower()

        # 1) Try EXIF CreateDate
        create_date, subseconds = extract_exif_create_date(media_path)
        new_base = None

        if create_date:
            try:
                date_part, time_part = create_date.split(" ")
                date_fmt = date_part.replace(":", "-")
                time_fmt = time_part.replace(":", "-")
                new_base = f"{date_fmt}_{time_fmt}"
                if subseconds:
                    # take only the first 2 digits of the sub-second value
                    ms2 = (subseconds[:2]).ljust(2, "0")
                    new_base += f"-{ms2}"
            except Exception as e:
                log_error(f"❌ EXIF parse error for {filename}: {e}")
                create_date = None  # fallback to filename

        # 2) Fallback: parse filename
        if not new_base:
            parsed = parse_date_from_filename(name_root)
            if parsed:
                year, month, day, hh, mm, ss = parsed
                date_fmt = f"{year}-{month}-{day}"
                time_fmt = f"{hh}-{mm}-{ss}"
                new_base = f"{date_fmt}_{time_fmt}"
                subseconds = ""
            else:
                # Unmatched: move to UNMATCHED_DIR
                dest = make_unique_path(UNMATCHED_DIR, name_root, ext)
                try:
                    os.rename(media_path, dest)
                    log_unmatched(f"⚠️ {filename} → {os.path.basename(dest)}")
                except Exception as e:
                    log_error(f"❌ Failed to move unmatched {filename}: {e}")
                continue

        # 3) Rename in place (keep directory)
        parent_dir = Path(media_path).parent
        new_path = make_unique_path(parent_dir, new_base, ext, original_path=Path(media_path))
        if new_path != Path(media_path):
           os.rename(media_path, new_path)
           log_matched(f"✅ Renamed: {filename} → {new_path.name}")

    print(f"\n🎉 Done. Renamed files in place; unmatched moved to: {UNMATCHED_DIR}")
    print(f"📝 Matched log:   {MATCHED_LOG_PATH}")
    print(f"📝 Unmatched log: {UNMATCHED_LOG_PATH}")
    print(f"📝 Errors log:    {ERROR_LOG_PATH}")

if __name__ == "__main__":
    main()