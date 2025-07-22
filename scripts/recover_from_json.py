#!/usr/bin/env python3
"""
recover_from_json.py

Recovers EXIF metadata for media files under a Google Takeout export by
matching each media file to its corresponding JSON metadata file, injecting
CreateDate/DateTimeOriginal/ModifyDate, and consolidating JSON files into a
“done” folder. Handles files with special characters like parentheses.
"""

import os
import sys
import subprocess
import re
from tqdm import tqdm
from datetime import datetime

# ─── Configuration ────────────────────────────────────────────────────────────

# 1) Determine TARGET_DIRECTORY and OUTPUT_DIRECTORY
TARGET_DIRECTORY = os.getenv("TARGET_DIR")
OUTPUT_DIRECTORY = os.getenv("OUTPUT_DIR")
if len(sys.argv) > 1 and not TARGET_DIRECTORY:
    TARGET_DIRECTORY = sys.argv[1]
if len(sys.argv) > 2 and not OUTPUT_DIRECTORY:
    OUTPUT_DIRECTORY = sys.argv[2]

if not TARGET_DIRECTORY:
    print("❌ Error: TARGET_DIR must be set (env or first arg).", file=sys.stderr)
    sys.exit(1)

# 2) Paths for “done” and logging
DONE_DIRECTORY     = os.path.join(TARGET_DIRECTORY, "done")
LOG_DIRECTORY      = os.path.join(TARGET_DIRECTORY, "logs")
LOG_FILE_PATH      = os.path.join(LOG_DIRECTORY, "recovered_log.txt")

os.makedirs(DONE_DIRECTORY, exist_ok=True)
os.makedirs(LOG_DIRECTORY, exist_ok=True)
# Truncate the log file
with open(LOG_FILE_PATH, "w", encoding="utf-8"):
    pass

# 3) Supported media extensions and MIME→extension map
MEDIA_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".webp", ".heic",
    ".mp4", ".mov", ".avi", ".3gp", ".mpg", ".m4v", ".gif"
}

MIME_TYPE_TO_EXTENSION_MAP = {
    "image/jpeg":      "jpg",
    "image/png":       "png",
    "image/webp":      "webp",
    "image/heic":      "heic",
    "image/gif":       "gif",
    "video/mp4":       "mp4",
    "video/quicktime": "mov",
    "video/x-msvideo": "avi",
    "video/3gpp":      "3gp",
    "video/mpeg":      "mpg",
    "video/x-m4v":     "m4v",
}

# ─── Helper Functions ─────────────────────────────────────────────────────────

def log_message(message: str):
    """Append a message to the log file."""
    with open(LOG_FILE_PATH, "a", encoding="utf-8") as log_file:
        log_file.write(message + "\n")

def find_all_media_file_paths():
    """Recursively collect all media file paths under TARGET_DIRECTORY, skipping DONE_DIRECTORY."""
    media_file_paths = []
    for root, dirs, files in os.walk(TARGET_DIRECTORY):
        # Skip the DONE_DIRECTORY subtree
        if os.path.commonpath([root, DONE_DIRECTORY]) == DONE_DIRECTORY:
            continue
        for filename in files:
            lower_filename = filename.lower()
            if (lower_filename == ".ds_store" or
                lower_filename.endswith((".json", ".txt", ".md"))):
                continue
            extension = os.path.splitext(filename)[1].lower()
            if extension in MEDIA_EXTENSIONS:
                full_path = os.path.join(root, filename)
                media_file_paths.append(full_path)
    return media_file_paths

def find_all_json_file_paths():
    """Recursively collect all .json file paths under TARGET_DIRECTORY, skipping DONE_DIRECTORY."""
    json_file_paths = []
    for root, dirs, files in os.walk(TARGET_DIRECTORY):
        if os.path.commonpath([root, DONE_DIRECTORY]) == DONE_DIRECTORY:
            continue
        for filename in files:
            if filename.lower().endswith(".json"):
                full_path = os.path.join(root, filename)
                json_file_paths.append(full_path)
    return json_file_paths

# ─── Main Processing ──────────────────────────────────────────────────────────

def main():
    media_file_paths = find_all_media_file_paths()
    if not media_file_paths:
        print(f"ℹ️ No media files found under {TARGET_DIRECTORY}.")
        return

    json_file_paths = find_all_json_file_paths()
    used_json_file_paths = set()

    for media_file_path in tqdm(
        media_file_paths,
        desc="🔁 Recovering metadata",
        unit="file",
        file=sys.stderr
    ):
        # 1) Detect and correct file extension via MIME type
        try:
            mime_type = subprocess.check_output(
                ["file", "--mime-type", "-b", media_file_path],
                stderr=subprocess.DEVNULL
            ).decode().strip()
        except subprocess.CalledProcessError:
            log_message(f"⚠️ Could not detect MIME for {media_file_path}")
            continue

        original_extension = os.path.splitext(media_file_path)[1].lstrip(".").lower()
        desired_extension  = MIME_TYPE_TO_EXTENSION_MAP.get(mime_type, original_extension).lower()

        if original_extension != desired_extension:
            renamed_path = os.path.splitext(media_file_path)[0] + "." + desired_extension
            log_message(f"🛠️  Renaming extension: {media_file_path} → {renamed_path}")
            os.rename(media_file_path, renamed_path)
            media_file_path = renamed_path

        # 2) Derive base name and attempt to find matching JSON
        base_name = os.path.splitext(os.path.basename(media_file_path))[0].lower()

        # First try matching the full base_name
        matched_json_path = next((
            candidate
            for candidate in json_file_paths
            if base_name in os.path.basename(candidate).lower()
        ), None)

        # If no match, strip trailing "(...)" and retry
        if not matched_json_path:
            stripped_base = re.sub(r'\([^)]*\)$', '', base_name)
            matched_json_path = next((
                candidate
                for candidate in json_file_paths
                if stripped_base in os.path.basename(candidate).lower()
            ), None)
            
        # Strip "-edited" suffix
        if not matched_json_path and base_name.endswith("-edited"):
            stripped_edited = base_name[:-len("-edited")]
            matched_json_path = next((
                candidate
                for candidate in json_file_paths
                if stripped_edited in os.path.basename(candidate).lower()
            ), None)

        # GIF special: strip trailing "i" from "-ani"
        if (not matched_json_path and media_file_path.lower().endswith(".gif") and base_name.endswith("ani")):
            stripped_ani = base_name[:-1]  # remove 'i'
            matched_json_path = next((
                candidate
                for candidate in json_file_paths
                if stripped_ani in os.path.basename(candidate).lower()
             ), None)


        if not matched_json_path or not os.path.isfile(matched_json_path):
            log_message(f"❌ No matching JSON for {media_file_path}")
            continue

        # 3) Extract timestamp from JSON
        try:
            timestamp = subprocess.check_output(
                ["jq", "-r", ".photoTakenTime.timestamp // .creationTime.timestamp", matched_json_path],
                stderr=subprocess.DEVNULL
            ).decode().strip()
        except subprocess.CalledProcessError:
            log_message(f"⚠️ jq failed on {matched_json_path}")
            continue

        if not timestamp.isdigit():
            log_message(f"⚠️ Invalid timestamp in JSON: {matched_json_path}")
            continue

        # 4) Inject EXIF metadata
        exif_datetime = datetime.utcfromtimestamp(int(timestamp)).strftime("%Y:%m:%d %H:%M:%S")
        subprocess.run([
            "exiftool", "-overwrite_original", "-q", "-m",
            f"-EXIF:CreateDate={exif_datetime}",
            f"-EXIF:DateTimeOriginal={exif_datetime}",
            f"-EXIF:ModifyDate={exif_datetime}",
            media_file_path
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        used_json_file_paths.add(matched_json_path)

    # 5) Move each used JSON exactly once
    for json_path in sorted(used_json_file_paths):
        destination_path = os.path.join(DONE_DIRECTORY, os.path.basename(json_path))
        os.replace(json_path, destination_path)

    print("\n✅ Recovery complete.", file=sys.stderr)
    print(f"📝 Detailed log: {LOG_FILE_PATH}")

if __name__ == "__main__":
    main()