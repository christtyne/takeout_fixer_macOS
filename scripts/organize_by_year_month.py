#!/usr/bin/env python3
"""
organize_by_year_month.py

Organizes media files from TARGET_DIR into OUTPUT_DIR by parsing year and
month directly from each filename. You can choose to group by:

  [1] Year only (YYYY)
  [2] Year and month name (YYYY/month)

Filenames must include a 4-digit year (20xx) optionally separated by “-” or “_”
and a 2-digit month (01–12). Files missing that pattern are logged as errors.

Errors are written to TARGET_DIR/logs/organize_log.txt.
"""

import os
import sys
import re
import calendar
import shutil
from pathlib import Path
from tqdm import tqdm

# ─── Constants ────────────────────────────────────────────────────────────────

MEDIA_EXTENSIONS   = {
    ".jpg", ".jpeg", ".png", ".webp", ".heic",
    ".mp4", ".mov", ".avi", ".3gp", ".mpg", ".m4v", ".gif",
}
IGNORE_FILENAMES   = {".ds_store", ".txt", ".md", ".json"}
YEAR_MONTH_PATTERN = re.compile(r"(20\d{2})[-_]?([01]\d)")

# ─── Configuration ────────────────────────────────────────────────────────────

TARGET_DIRECTORY = Path(
    os.getenv("TARGET_DIR") or
    (sys.argv[1] if len(sys.argv) > 1 else "")
)
OUTPUT_DIRECTORY = Path(
    os.getenv("OUTPUT_DIR") or
    (sys.argv[2] if len(sys.argv) > 2 else "")
)

if not TARGET_DIRECTORY or not OUTPUT_DIRECTORY:
    print(
        "❌ Error: TARGET_DIR and OUTPUT_DIR must be set "
        "(via environment or as arguments)",
        file=sys.stderr
    )
    sys.exit(1)

# Ask the user how to structure folders
print("📁 How do you want to organize your files?")
print("  [1] Year only (YYYY)")
print("  [2] Year and month name (YYYY/month)")
_choice = input("Select 1 or 2: ").strip()
ORGANIZE_BY_MONTH = (_choice == "2")

# ─── Logging Setup ────────────────────────────────────────────────────────────

LOG_DIRECTORY = TARGET_DIRECTORY / "logs"
LOG_DIRECTORY.mkdir(parents=True, exist_ok=True)
LOG_FILE_PATH = LOG_DIRECTORY / "organize_log.txt"
LOG_FILE_PATH.write_text("")  # truncate existing

def log_error(message: str) -> None:
    """Append an error message to the log file."""
    with LOG_FILE_PATH.open("a", encoding="utf-8") as f:
        f.write(message + "\n")

# ─── Utility Functions ────────────────────────────────────────────────────────

def make_unique_path(dest_dir: Path, base_name: str, extension: str, original_path: Path = None) -> Path:
    """
    Return dest_dir/base_name+extension if it doesn't exist or is the same
    as original_path; otherwise append (1), (2), ... until unique.
    """
    candidate = dest_dir / f"{base_name}{extension}"
    if not candidate.exists() or (
        original_path and candidate.samefile(original_path)
    ):
        return candidate

    index = 1
    while True:
        numbered = dest_dir / f"{base_name}({index}){extension}"
        if not numbered.exists():
            return numbered
        index += 1

# ─── Main Processing ─────────────────────────────────────────────────────────

def main() -> None:
    # Gather all media files under TARGET_DIRECTORY
    media_files = [
        path for path in TARGET_DIRECTORY.rglob("*")
        if path.is_file()
        and path.name.lower() not in IGNORE_FILENAMES
        and path.suffix.lower() in MEDIA_EXTENSIONS
        and not path.is_relative_to(OUTPUT_DIRECTORY)
    ]

    if not media_files:
        print(f"ℹ️  No media files found under {TARGET_DIRECTORY}.")
        return

    print(f"🔍 Found {len(media_files)} media files under {TARGET_DIRECTORY}.\n")

    # Process each file with a live progress bar
    for media_file in tqdm(
        media_files,
        desc=f"📂 Organizing by {_choice}",
        unit="file",
        file=sys.stderr
    ):
        stem      = media_file.stem
        extension = media_file.suffix.lower()

        match = YEAR_MONTH_PATTERN.search(stem)
        if not match:
            log_error(f"❌ No year/month in filename: {media_file.name}")
            continue

        year, month_num = match.group(1), match.group(2)
        if ORGANIZE_BY_MONTH:
            month_name = calendar.month_name[int(month_num)].lower()
            dest_dir   = OUTPUT_DIRECTORY / year / month_name
        else:
            dest_dir   = OUTPUT_DIRECTORY / year

        dest_dir.mkdir(parents=True, exist_ok=True)

        new_path = make_unique_path(
            dest_dir,
            stem,
            extension,
            original_path=media_file
        )
        try:
            shutil.move(str(media_file), str(new_path))
        except Exception as error:
            log_error(f"❌ Failed to move {media_file.name}: {error}")

    print(f"\n✅ Files organized into: {OUTPUT_DIRECTORY}")
    print(f"📝 Errors logged to: {LOG_FILE_PATH}")

if __name__ == "__main__":
    main()