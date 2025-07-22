# Google Takeout Photo Organizer

A suite of scripts (Python & Bash) to process, inject metadata, rename, and organize photos and videos exported via Google Takeout.

## Features

1. **Archive Extraction** (`extract_archives.sh`):  
   Unpack `.tar`/`.tgz` archives into your Takeout folder.

2. **Metadata Recovery** (`recover_from_json.py`):  
   Reads JSON sidecars, injects `CreateDate`, `DateTimeOriginal` & `ModifyDate` into each media file’s EXIF, and consolidates JSON files into a `done/` folder. Handles duplicates, special characters, “-edited” suffixes, and GIF `-ani`/`-an` mismatch.

3. **Filename-Fallback Processing** (`process_photos.py`):  
   For any files still lacking EXIF dates (or that ended up in an `error/` folder), parses EXIF (including subseconds) or infers from the filename, renames in place to `YYYY-MM-DD_HH-MM-SS[.MS]`, and moves truly unmatched files to `unmatched/`.

4. **Organization by Date** (`organize_by_year_month.py`):  
   Parses `YYYY` (and optionally month) directly from filenames, and moves files into `OUTPUT_DIR/YYYY[/month_name]/`. Logs errors for any names that don’t match the pattern.

5. **Cleanup Empty Folders** (`clean_empty_folders.py`):  
   Finds and deletes any folders that are empty—or contain only a `.DS_Store`—recursively.

6. **Orchestration** (`takeout_photo_setup.py`):  
   A Python driver that prompts you step-by-step: extract archives, set `TARGET_DIR`, set `OUTPUT_DIR`, run each stage in order, choose organization structure, and optionally clean up.

---

## Prerequisites

- **macOS** (uses AppleScript for folder dialogs)
- **Homebrew** for installing CLI tools:
  ```bash
  brew install exiftool jq coreutils
  pip3 install tqdm