# 🎞️ Google Takeout Photo Organizer MacOS

A **friendly**, **easy-to-use** set of scripts to **process**, **inject metadata**, **rename**, and **organize** your Google Takeout photos & videos—no programming required!

---

## 🚀 TL;DR (Quick Start)

```bash
# 1. Clone or download this repo
git clone https://github.com/christtyne/takeout_fixer_macOS.git
cd takeout-photo-organizer

# 2. Make the setup script executable and run it
chmod +x takeout_photo_setup.py
./takeout_photo_setup.py
```

**Follow the on-screen prompts**: pick your Takeout folder, choose where to save organized files, and press Enter. 
Enjoy a neatly organized photo library! 🎉

---

## 🔧 Features

- **Archive Extraction**: Unpack `.tar`/`.tgz` archives  
- **Metadata Recovery**: Inject EXIF from JSON sidecars  
- **Timestamp Rename**: Rename files in-place by original timestamp (with milliseconds)  
- **Date Organization**: Move into `Year/` or `Year/Month/` based on filename  
- **Cleanup**: Delete empty or `.DS_Store`–only folders  

---

## 🛠️ Prerequisites

- **Python 3.8+**  
- **macOS** (AppleScript dialog) or any Unix-like shell  
- **Homebrew** (macOS) or equivalent package manager  

```bash
brew install exiftool jq coreutils
pip3 install tqdm rich
```

---

## 📚 Usage (Detailed)

1. **Archive Extraction** (`extract_archives.sh`):  
   Unpack `.tar`/`.tgz` archives into your Takeout folder.
2. **Select Takeout Folder**  
   Choose your Google Takeout export folder.  
3. **Select Output Folder**  
   Pick where to save the organized files. 
4. **Metadata Recovery** (`recover_from_json.py`):  
   Reads JSON sidecars, injects `CreateDate`, `DateTimeOriginal` & `ModifyDate` into each media file’s EXIF, and consolidates JSON files into a `done/` folder. Handles duplicates, special characters, “-edited” suffixes, and GIF `-ani`/`-an` mismatch.
5. **Filename-Fallback Processing** (`process_photos.py`):  
   Infers dates from the filename, renames in place to `YYYY-MM-DD_HH-MM-SS[.MS]`, and moves truly unmatched files to `unmatched/`.
6. **Organization by Date** (`organize_by_year_month.py`):  
   Parses `YYYY` (and optionally month) directly from filenames, and moves files into `OUTPUT_DIR/YYYY[/month_name]/`. Logs errors for any names that don’t match the pattern.
7. **Cleanup Empty Folders** (`clean_empty_folders.py`):  
   Finds and removing empty directories recursively.


---

## 📂 Logs

All logs are saved under your selected folder in the `logs/` subdirectory.

---

## 🎨 Customization

Edit any `.py` or `.sh` script to tweak patterns, formats, or add new features—everything is plain text.

---

## 📝 License

**This project is free and open-source.** Use, modify, and share it however you like—no restrictions!  
