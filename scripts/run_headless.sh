#!/usr/bin/env bash
set -euo pipefail

export WINEPREFIX="${WINEPREFIX:-/opt/prefix}"
export WINEARCH="${WINEARCH:-win64}"
export WINEDEBUG="${WINEDEBUG:--all}"
export GAME_ROOT="${GAME_ROOT:-/root/Dark.Souls.Remastered.v1.04}"
export WINEDLLOVERRIDES="${WINEDLLOVERRIDES:-mscoree,mshtml=;winemenubuilder.exe=d}"

log="${WINEPREFIX}/darkscope_init.log"

die() {
  echo "ERROR: $*" >&2
  if [[ -f "$log" ]]; then
    echo "--- last 200 lines of $log ---" >&2
    tail -n 200 "$log" >&2 || true
  fi
  exit 1
}

init_prefix() {
  if [[ -f "${WINEPREFIX}/.darkscope_prefix_ready" ]]; then
    return 0
  fi

  mkdir -p "${WINEPREFIX}"
  echo "Initializing Wine prefix (first run only)..." | tee "$log"
  xvfb-run -a --server-args="-screen 0 1280x720x24" wineboot --init >>"$log" 2>&1 || die "wineboot failed"
  wineserver -w >>"$log" 2>&1 || true

  echo "Installing winetricks deps (first run only)..." | tee -a "$log"
  xvfb-run -a --server-args="-screen 0 1280x720x24" \
    winetricks -q win10 vcrun2019 d3dcompiler_47 xact dxvk >>"$log" 2>&1 || die "winetricks failed"
  wineserver -w >>"$log" 2>&1 || true

  touch "${WINEPREFIX}/.darkscope_prefix_ready"
}

init_prefix

# --- Locate game exe (allow override via $GAME_EXE) ---
GAME_EXE="${GAME_EXE:-}"
if [[ -z "$GAME_EXE" ]]; then
  # Optional indirection for unusual layouts
  if [[ -f "${GAME_ROOT}/GAMEDIR" ]]; then
    GAME_ROOT="$(cat "${GAME_ROOT}/GAMEDIR")"
  fi

  GAME_EXE="$(find "$GAME_ROOT" -type f -iname 'DarkSoulsRemastered.exe' -print -quit)"
fi
[[ -n "$GAME_EXE" ]] || die "DarkSoulsRemastered.exe not found under ${GAME_ROOT} (set GAME_ROOT or GAME_EXE)"

cd "$(dirname "$GAME_EXE")"
echo "Launching headless: ${GAME_EXE}"
exec xvfb-run -a -s "-screen 0 1280x720x24" wine "$(basename "$GAME_EXE")"
