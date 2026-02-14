#!/usr/bin/env bash
set -euo pipefail

export WINEPREFIX="${WINEPREFIX:-/opt/prefix}"
export WINEARCH="${WINEARCH:-win64}"
export GAME_ROOT="${GAME_ROOT:-/root/Dark.Souls.Remastered.v1.04}"

XVFB_RES="${XVFB_RES:-800x600}"
XVFB_DEPTH="${XVFB_DEPTH:-24}"
XVFB_SERVER_ARGS="${XVFB_SERVER_ARGS:--screen 0 ${XVFB_RES}x${XVFB_DEPTH}}"

export WINEDEBUG="${WINEDEBUG:--all}"
export WINEDLLOVERRIDES="${WINEDLLOVERRIDES:-winemenubuilder.exe=d;mscoree,mshtml=}"

if [[ ! -f "$WINEPREFIX/system.reg" ]]; then
  xvfb-run -a --server-args="$XVFB_SERVER_ARGS" wineboot --init
fi

wine reg add "HKCU\Software\Wine\Drivers" /v Audio /t REG_SZ /d "pulse" /f >/dev/null 2>&1 || true

GAME_EXE="${GAME_EXE:-$(find "$GAME_ROOT" -type f -iname 'DarkSoulsRemastered.exe' -print -quit)}"

cd "$(dirname "$GAME_EXE")"
exec xvfb-run -a --server-args="$XVFB_SERVER_ARGS" wine "$(basename "$GAME_EXE")"
