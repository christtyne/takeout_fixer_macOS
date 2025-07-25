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
from pathlib import Path
from shutil import move
from tqdm import tqdm

# ─── Constants ────────────────────────────────────────────────────────────────

MEDIA_EXTENSIONS   = {
    ".jpg", ".jpeg", ".png", ".webp", ".heic",
    ".mp4", ".mov", ".avi", ".3gp", ".mpg", ".m4v", ".gif",
}
IGNORE_FILENAMES   = {".ds_store", ".txt", ".md", ".json"}
YEAR_MONTH_PATTERN = re.compile(r"(20\d{2})[-_]?([01]\d)")

# ─── Configuration ────────────────────────────────────────────────────────────

# Determine TARGET_DIRECTORY as a Path
target_env = os.getenv("TARGET_DIR")
if target_env:
    TARGET_DIRECTORY = Path(target_env)
elif len(sys.argv) > 1:
    TARGET_DIRECTORY = Path(sys.argv[1])
else:
    print("❌ Error: TARGET_DIR must be set (env or first arg).", file=sys.stderr)
    sys.exit(1)

# Determine OUTPUT_DIRECTORY as a Path (defaults to TARGET_DIRECTORY)
output_env = os.getenv("OUTPUT_DIR")
if output_env:
    OUTPUT_DIRECTORY = Path(output_env)
elif len(sys.argv) > 2:
    OUTPUT_DIRECTORY = Path(sys.argv[2])
else:
    OUTPUT_DIRECTORY = TARGET_DIRECTORY

# Ask the user how to structure folders
print("📁 How do you want to organize your files?")
print("  [1] Year only (YYYY)")
print("  [2] Year and month name (YYYY/month)")
_choice = input("Select 1 or 2: ").strip()
ORGANIZE_BY_MONTH = (_choice == "2")
if _choice == 1:
    structure = "Year"
else:
    structure = "Year and month"

# ─── Logging Setup ────────────────────────────────────────────────────────────

LOG_DIRECTORY = TARGET_DIRECTORY / "logs"
LOG_DIRECTORY.mkdir(parents=True, exist_ok=True)
LOG_FILE_PATH = LOG_DIRECTORY / "organize_log.txt"
LOG_FILE_PATH.write_text("")  # truncate existing

def log_error(message: str) -> None:
    #Append an error message to the log file
    with LOG_FILE_PATH.open("a", encoding="utf-8") as f:
        f.write(message + "\n")

# ─── Main Processing ─────────────────────────────────────────────────────────

def main() -> None:
    # Gather all media files under TARGET_DIRECTORY
    media_files = [
        path for path in TARGET_DIRECTORY.rglob("*")
        if path.is_file()
        and path.name.lower() not in IGNORE_FILENAMES
        and path.suffix.lower() in MEDIA_EXTENSIONS
    ]

    if not media_files:
        print(f"\nℹ️  No media files found under {TARGET_DIRECTORY}.")
        return

    print(f"\n🔍 Found {len(media_files)} media files under {TARGET_DIRECTORY}.")

    # Process each file with a live progress bar
    for media_file in tqdm(
        media_files,
        desc=f"📂 Organizing by {structure}",
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

        try:
            destination = dest_dir / media_file.name
            move(str(media_file), str(destination))
        except Exception as error:
            log_error(f"❌ Failed to move {media_file.name}: {error}")

    print(f"✅ Files organized into: {OUTPUT_DIRECTORY}")
    print(f"📝 Errors logged to: {LOG_FILE_PATH}\n\n")

if __name__ == "__main__":
    main()