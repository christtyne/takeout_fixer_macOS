#!/usr/bin/env python3
import os
import shutil            
import subprocess 
import sys
import re
import calendar
from pathlib import Path
from tqdm import tqdm


# ─── Setup ────────────────────────────────────────────────────────────────────

# Where this script lives, so we can call the other .py files by full path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Required CLI tools
REQUIRED = ["exiftool", "jq", "gdate", "tar", "file", "osascript"]

def die(msg):
    print(f"❌ {msg}", file=sys.stderr)
    sys.exit(1)

def check_deps():
    missing = [cmd for cmd in REQUIRED if shutil.which(cmd) is None]
    if missing:
        die(f"Missing required tools: {', '.join(missing)}\n"
            "Install via Homebrew: brew install exiftool jq coreutils && pip3 install tqdm")

def ask_yes_no(prompt, default=False):
    yn = input(f"{prompt} [{'Y/N' if default else 'y/n'}] ").strip().lower()
    if not yn:
        return default
    return yn in ("y", "yes")

def pick_folder(prompt):
    try:
        return subprocess.check_output([
            "osascript", "-e",
            f'POSIX path of (choose folder with prompt "{prompt}")'
        ]).decode().strip()
    except subprocess.CalledProcessError:
        return input(f"{prompt} (enter full path): ").strip()

def run_script(script_name, use_shell=False):
    script_path = os.path.join(SCRIPT_DIR, script_name)
    if not os.path.isfile(script_path):
        print(f"\n⚠️ Skipping {script_name} (not found)")
        return

    print(f"\n▶️ Running {script_name}")
    if script_name.endswith(".py"):
        # invoke via the same Python interpreter
        subprocess.run([sys.executable, script_path], check=True)
    else:
        # shell scripts or others
        if not os.access(script_path, os.X_OK):
            print(f"⚠️ {script_name} is not executable, skipping")
            return
        if use_shell:
            subprocess.run(script_path, shell=True, check=True)
        else:
            subprocess.run([script_path], check=True)
        
# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    check_deps()
    
    # 1) Optional archive extraction
    if ask_yes_no("📦 Extract .tar/.tgz files?"):
        archive_folder = pick_folder("📦 Select folder containing your .tar/.tgz files")
        os.environ["TAR_SOURCE"]  = archive_folder
        takeout_folder = pick_folder("📂 Select the folder where to extract the Takeout files")
        os.environ["TARGET_DIR"]  = takeout_folder
        run_script("extract_archives.sh")
    else:
        # pick already‐extracted Takeout folder
        takeout_folder = pick_folder("📂 Select your Takeout folder")
        os.environ["TARGET_DIR"] = takeout_folder
    
    # 2) Pick destination once
    output_folder = pick_folder("💾 Select where to save organized files")
    os.environ["OUTPUT_DIR"] = output_folder

    # 3) JSON recovery
    run_script("recover_from_json.py")

    # 4) EXIF-based processing
    run_script("process_photos.py")

    # 6) Optional folder organization
    if ask_yes_no("📁 Organize into year/ or year/month/ subfolders?"):
        run_script("organize_by_year_month.py")
    

    # 7) Optional cleanup of empty folders
    if ask_yes_no("🧹 Remove empty folders under the Takeout folder?"):
        run_script("clean_empty_folders.py")

    print(f"\n🎉 All done! Your organized photos are in:\n   {output_folder}")

if __name__ == "__main__":
    main()