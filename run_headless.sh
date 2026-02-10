#!/usr/bin/env bash
set -euo pipefail

export WINEPREFIX="${WINEPREFIX:-/opt/prefix}"
export WINEARCH="${WINEARCH:-win64}"
export WINEDEBUG="${WINEDEBUG:--all}"
export GAME_ROOT="${GAME_ROOT:-/opt/game}"
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

if [[ -f "${GAME_ROOT}/GAMEDIR" ]]; then
  GAME_DIR="$(cat "${GAME_ROOT}/GAMEDIR")"
else
  GAME_DIR="${GAME_ROOT}"
fi

cd "${GAME_DIR}"
echo "Launching headless from: ${GAME_DIR}"
exec xvfb-run -a -s "-screen 0 1280x720x24" wine DarkSoulsRemastered.exe
