#!/usr/bin/env bash
set -euo pipefail

# --- Config (override via env) ---
export WINEPREFIX="${WINEPREFIX:-/opt/prefix}"
export WINEARCH="${WINEARCH:-win64}"
export GAME_ROOT="${GAME_ROOT:-/opt/game}"

DESKTOP_NAME="${DESKTOP_NAME:-DSR}"
DESKTOP_RES="${DESKTOP_RES:-800x600}"

# Avoid Wine first-run prompts
export WINEDLLOVERRIDES="winemenubuilder.exe=d;mscoree,mshtml="

# Isolated runtime dir
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/tmp/xdg}"

fail() { echo "ERROR: $*" >&2; exit 1; }

# --- Prep dirs ---
mkdir -p "$XDG_RUNTIME_DIR"
chmod 700 "$XDG_RUNTIME_DIR"

# --- Ensure prefix exists ---
if [[ ! -f "$WINEPREFIX/system.reg" ]]; then
  wineboot --init
fi

# --- Audio: handled by ENTRYPOINT ---
# Expect PULSE_SERVER to be set (or harmlessly absent)
wine reg add "HKCU\Software\Wine\Drivers" /v Audio /t REG_SZ /d "pulse" /f >/dev/null || true

# --- Locate game exe ---
EXE="$(find "$GAME_ROOT" -type f -iname 'DarkSoulsRemastered.exe' -print -quit)"
[[ -n "$EXE" ]] || fail "DarkSoulsRemastered.exe not found under $GAME_ROOT"

# --- Launch ---
cd "$(dirname "$EXE")"
exec wine explorer "/desktop=${DESKTOP_NAME},${DESKTOP_RES}" "$(basename "$EXE")"
