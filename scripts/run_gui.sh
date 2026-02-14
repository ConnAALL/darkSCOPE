#!/usr/bin/env bash
set -euo pipefail

export WINEPREFIX="${WINEPREFIX:-/opt/prefix}"
export WINEARCH="${WINEARCH:-win64}"
export GAME_ROOT="${GAME_ROOT:-/root/Dark.Souls.Remastered.v1.04}"

DESKTOP_NAME="${DESKTOP_NAME:-DSR}"
DESKTOP_RES="${DESKTOP_RES:-800x600}"

export WINEDLLOVERRIDES="winemenubuilder.exe=d;mscoree,mshtml="
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/tmp/xdg}"

mkdir -p "$XDG_RUNTIME_DIR"
chmod 700 "$XDG_RUNTIME_DIR"

if [[ ! -f "$WINEPREFIX/system.reg" ]]; then
  wineboot --init
fi

wine reg add "HKCU\Software\Wine\Drivers" /v Audio /t REG_SZ /d "pulse" /f >/dev/null 2>&1 || true

EXE="$(find "$GAME_ROOT" -type f -iname 'DarkSoulsRemastered.exe' -print -quit)"

cd "$(dirname "$EXE")"
exec wine explorer "/desktop=${DESKTOP_NAME},${DESKTOP_RES}" "$(basename "$EXE")"
