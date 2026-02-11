#!/usr/bin/env bash
set -euo pipefail

export WINEPREFIX="${WINEPREFIX:-/tmp/wineprefix}"
export WINEARCH="${WINEARCH:-win64}"
export GAME_ROOT="${GAME_ROOT:-/opt/game}"

export WINEDLLOVERRIDES="winemenubuilder.exe=d;mscoree,mshtml="
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/tmp/xdg}"
mkdir -p "$WINEPREFIX" "$XDG_RUNTIME_DIR"
chmod 700 "$XDG_RUNTIME_DIR"

# Pick a safe fixed desktop size (avoids mode switches / fullscreen issues)
DESKTOP_NAME="${DESKTOP_NAME:-DSR}"
DESKTOP_RES="${DESKTOP_RES:-1920x1080}"

fail(){ echo "ERROR: $*" >&2; exit 1; }
log(){ echo "== $* =="; }

log "GPU"
nvidia-smi || true

log "Vulkan"
VK_OUT="$(vulkaninfo 2>&1 || true)"
echo "$VK_OUT" | grep -m1 deviceName || fail "No Vulkan device detected"

log "X11"
[[ -n "${DISPLAY:-}" ]] || fail "DISPLAY not set"
[[ -d /tmp/.X11-unix ]] || fail "/tmp/.X11-unix not mounted"
xdpyinfo -display "$DISPLAY" >/dev/null 2>&1 || fail "Cannot connect/auth to X display"

log "Versions"
wine --version || true
winetricks --version || true

# Fresh prefix every run (ephemeral mode)
rm -rf "$WINEPREFIX"
mkdir -p "$WINEPREFIX"

log "wineboot"
timeout 180s wineboot --init || fail "wineboot failed/timed out"

log "winetricks"
timeout 1200s env WINETRICKS_SUPER_QUIET=0 WINETRICKS_VERBOSE=1 \
  winetricks win10 vcrun2022 d3dcompiler_47 xact dxvk \
  || fail "winetricks failed"

EXE="$(find "$GAME_ROOT" -type f -iname 'DarkSoulsRemastered.exe' -print -quit)"
[[ -n "$EXE" ]] || fail "DarkSoulsRemastered.exe not found under $GAME_ROOT"

log "Launch (virtual desktop ${DESKTOP_RES})"
cd "$(dirname "$EXE")"

# This prevents the game from messing with the host mode and tends to stop the DXVK swapchain crash.
exec wine explorer "/desktop=${DESKTOP_NAME},${DESKTOP_RES}" "$(basename "$EXE")"
