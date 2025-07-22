#!/usr/bin/env bash

# ------------------------------------------------------------------------------
# Google Takeout Photo Organizer – Archive Extractor (macOS)
# Extracts .tar/.tgz/.tar.gz files from TAR_SOURCE into EXTRACT_DIR with tqdm.
# ------------------------------------------------------------------------------

set -euo pipefail
IFS=$'\n\t'

# === Check required environment variables
if [[ -z "${TAR_SOURCE:-}" || -z "${TARGET_DIR:-}" ]]; then
  echo "❌ TAR_SOURCE and TARGET_DIR must be set before running this script."
  exit 1
fi

echo "🔍 Searching for .tar/.tgz files in: $TAR_SOURCE"
archive_list=$(find "$TAR_SOURCE" -type f \( -name "*.tar" -o -name "*.tgz" -o -name "*.tar.gz" \))
archive_count=$(echo "$archive_list" | wc -l)

if [[ "$archive_count" -eq 0 ]]; then
  echo "⚠️ No archive files found in $TAR_SOURCE"
  exit 0
fi

echo "$archive_list" | python3 -c "
import sys, subprocess
from tqdm import tqdm

archives = [line.strip() for line in sys.stdin if line.strip()]
for archive in tqdm(archives, total=len(archives), desc='📦 Extracting archives', unit='file'):
    subprocess.run(['tar', '-xf', archive, '-C', '${TARGET_DIR}'],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
"

echo -e "✅ Extraction complete.\n\n"
