#!/usr/bin/env python3
"""
process_photos.py

Renames media files under TARGET_DIR to a timestamp-based filename using
the EXIF CreateDate (including subseconds) or, if missing, by parsing the
original filename. Matched files are renamed in place; unmatched files are
moved to an “unmatched” folder. Duplicate target names get “(1)”, “(2)”, etc.

Logs are written to TARGET_DIR/logs/process_errors.txt
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
TARGET_DIR = Path(os.getenv("TARGET_DIR") or (sys.argv[1] if len(sys.argv) > 1 else ""))

if not TARGET_DIR or not TARGET_DIR.exists():
    print("❌ Error: TARGET_DIR must be set (env or first arg) and exist.", file=sys.stderr)
    sys.exit(1)

# Paths
UNMATCHED_DIR      = TARGET_DIR / "unmatched"
LOG_DIR            = TARGET_DIR / "logs"
MATCHED_LOG_PATH   = LOG_DIR / "matched.txt"
UNMATCHED_LOG_PATH = LOG_DIR / "unmatched.txt"
ERROR_LOG_PATH     = LOG_DIR / "process_errors.txt"

# Prepare directories
UNMATCHED_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

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

def list_media_file_paths():
    """Return list of all media file paths under TARGET_DIR (excluding 'unmatched' and 'logs')."""
    paths = []
    for root, dirs, files in os.walk(TARGET_DIR):
        root_path = Path(root)
        # Skip our own output folders
        if UNMATCHED_DIR in root_path.parents or root_path == UNMATCHED_DIR:
            continue
        if LOG_DIR in root_path.parents or root_path == LOG_DIR:
            continue
        for filename in files:
            ext = Path(filename).suffix.lower()
            if ext in MEDIA_EXTENSIONS:
                paths.append(root_path / filename)
    return paths

def extract_exif_create_date(media_file_path: str):
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
            str(media_file_path)
        ], stderr=subprocess.DEVNULL).decode("utf-8", "ignore").splitlines()
        
        if not output:
            return None, None
        
        exif_create_date = output[0].strip()
        sub_second      = output[1].strip() if len(output) > 1 else ""
        return exif_create_date, sub_second

    except Exception as e:
        log_error(f"❌ EXIF read failed for {media_file_path}: {e}")
        return None, None

def parse_date_from_filename(filename: str):
    """
    Parse YYYY MM DD and optional HHMMSS from filename.
    Returns (year,month,day,hh,mm,ss) or None.
    """
    m = FILENAME_DATE_REGEX.match(filename)
    if not m:
        return None
    year, month, day, timepart = m.groups()
    if timepart:
        hh, mm, ss = timepart[:2], timepart[2:4], timepart[4:6]
    else:
        hh, mm, ss = "00", "00", "00"
    return year, month, day, hh, mm, ss
    
def make_unique_path(destination_directory: Path, base_name: str, extension: str, original_file_path: Path = None) -> Path:
    """
    If dest_dir/base_name+extension exists *and* is not the same as original_file_path,
    append (1), (2), ... before the extension. Otherwise return the straight path.
    """
    candidate = destination_directory / f"{base_name}{extension}"
    # if it doesn't exist, or it *is* our original file, use it
    if not candidate.exists() or (original_file_path and candidate.samefile(original_file_path)):
        return candidate

    index = 1
    while True:
        candidate = destination_directory / f"{base_name}({index}){extension}"
        if not candidate.exists():
            return candidate
        index += 1

def main():
    media_file_paths = list_media_file_paths()
    if not media_file_paths:
        print(f"ℹ️  No media files found under {TARGET_DIR}.")
        return

    print(f"📅 Processing {len(media_file_paths)} media file(s)")

    for media_file_path in tqdm(media_file_paths, desc="📅 Inferring dates", unit="file", file=sys.stderr):
        filename        = media_file_path.name
        file_stem, file_extension  = media_file_path.stem, media_file_path.suffix.lower()

        # 1) Try EXIF CreateDate
        exif_create_date, sub_second = extract_exif_create_date(media_file_path)
        new_base_name = None

        if exif_create_date:
            try:
                date_part, time_part = exif_create_date.split(" ")
                date_string = date_part.replace(":", "-")
                time_string = time_part.replace(":", "-")
                new_base_name = f"{date_string}_{time_string}"
                if sub_second:
                    # take only the first 2 digits of the sub-second value
                    sub_second_two_digits = (sub_second[:2]).ljust(2, "0")
                    new_base_name += f"-{sub_second_two_digits}"
            except Exception as e:
                log_error(f"❌ EXIF parse error for {filename}: {e}")
                exif_create_date = None  # fallback to filename

        # 2) Fallback: parse filename
        if not new_base_name:
            parsed = parse_date_from_filename(file_stem)
            if parsed:
                year, month, day, hh, mm, ss = parsed
                date_string = f"{year}-{month}-{day}"
                time_string = f"{hh}-{mm}-{ss}"
                new_base_name = f"{date_string}_{time_string}"
                sub_second = ""
            else:
                # Unmatched: move to UNMATCHED_DIR
                new_file_path = make_unique_path(UNMATCHED_DIR, file_stem, file_extension)
                try:
                    media_file_path.rename(new_file_path)
                    log_unmatched(f"⚠️ {filename} → {new_file_path.name}")
                except Exception as e:
                    log_error(f"❌ Failed to move unmatched {filename}: {e}")
                continue

        # 3) Rename in place (keep directory)
        parent_dir = media_file_path.parent
        new_path = make_unique_path(parent_dir, new_base_name, file_extension, original_file_path=media_file_path)
        if new_path != media_file_path:
           media_file_path.rename(new_path)
           log_matched(f"✅ Renamed: {filename} → {new_path.name}")

    print(f"✅ Renamed files in place; unmatched moved to: {UNMATCHED_DIR}")
    print(f"📝 Matched log:   {MATCHED_LOG_PATH}")
    print(f"📝 Unmatched log: {UNMATCHED_LOG_PATH}")
    print(f"📝 Errors log:    {ERROR_LOG_PATH}\n\n")

if __name__ == "__main__":
    main()