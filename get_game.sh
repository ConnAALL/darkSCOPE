#!/usr/bin/env bash
set -euo pipefail

if [ -z "${1:-}" ]; then
  echo "Usage: $0 \"<google_drive_link>\""
  exit 1
fi

DRIVE_LINK="$1"

# Use the python from the *active* environment
if ! command -v python &>/dev/null; then
  echo "python not found. Activate your conda env first."
  exit 1
fi

python -m pip show gdown >/dev/null 2>&1 || {
  echo "gdown not found in this environment. Install with:"
  echo "  python -m pip install gdown"
  exit 1
}

python -m gdown --fuzzy "$DRIVE_LINK"
echo "Download completed successfully."
