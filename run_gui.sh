#!/usr/bin/env bash
set -euo pipefail

# --- Config (override via env) ---
export WINEPREFIX="${WINEPREFIX:-/tmp/wineprefix}"
export WINEARCH="${WINEARCH:-win64}"
export GAME_ROOT="${GAME_ROOT:-/opt/game}"

DESKTOP_NAME="${DESKTOP_NAME:-DSR}"
DESKTOP_RES="${DESKTOP_RES:-1920x1080}"

# Avoid Wine first-run prompts
export WINEDLLOVERRIDES="winemenubuilder.exe=d;mscoree,mshtml="

# Container runtime dir (separate from host XDG_RUNTIME_DIR)
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/tmp/xdg}"

# Dummy (blackhole) audio via PulseAudio null sink
PULSE_DIR="${PULSE_DIR:-/tmp/pulse}"
PULSE_SOCKET="${PULSE_SOCKET:-$PULSE_DIR/native}"
export PULSE_SERVER="unix:$PULSE_SOCKET"

fail() { echo "ERROR: $*" >&2; exit 1; }
log()  { echo "== $* =="; }

# --- Prep dirs ---
mkdir -p "$WINEPREFIX" "$XDG_RUNTIME_DIR" "$PULSE_DIR"
chmod 700 "$XDG_RUNTIME_DIR" "$PULSE_DIR"

# --- Sanity checks ---
log "GPU"
nvidia-smi || true

log "Vulkan"
VK_OUT="$(vulkaninfo 2>&1 || true)"
echo "$VK_OUT" | grep -m1 deviceName >/dev/null || fail "No Vulkan device detected"

log "X11"
[[ -n "${DISPLAY:-}" ]] || fail "DISPLAY not set"
[[ -d /tmp/.X11-unix ]] || fail "/tmp/.X11-unix not mounted"
xdpyinfo -display "$DISPLAY" >/dev/null 2>&1 || fail "Cannot connect/auth to X display"

log "Versions"
wine --version || true
winetricks --version || true

# --- Fresh prefix every run (ephemeral mode) ---
log "Reset Wine prefix"
rm -rf "$WINEPREFIX"
mkdir -p "$WINEPREFIX"

log "Initialize prefix (wineboot)"
wineboot --init

# --- Start dummy PulseAudio (null sink) ---
log "Start dummy PulseAudio (null sink)"
pulseaudio -n --daemonize=yes --exit-idle-time=-1 --log-target=stderr \
  -L "module-native-protocol-unix socket=$PULSE_SOCKET auth-anonymous=1" \
  -L "module-null-sink sink_name=nullsink sink_properties=device.description=NullSink" \
  -L "module-always-sink" || true

# Force Wine to use PulseAudio
wine reg add "HKCU\Software\Wine\Drivers" /v Audio /t REG_SZ /d "pulse" /f >/dev/null

# Best-effort: confirm sink exists and set it as default
pactl -s "$PULSE_SERVER" list short sinks || true
pactl -s "$PULSE_SERVER" set-default-sink nullsink || true

# --- Dependencies / tweaks ---
log "Winetricks"
env WINETRICKS_SUPER_QUIET=1 WINETRICKS_VERBOSE=0 \
  winetricks -q --unattended win10 vcrun2022 d3dcompiler_47 dxvk \
  || fail "winetricks failed"

# --- Locate game exe ---
EXE="$(find "$GAME_ROOT" -type f -iname 'DarkSoulsRemastered.exe' -print -quit)"
[[ -n "$EXE" ]] || fail "DarkSoulsRemastered.exe not found under $GAME_ROOT"

# --- Launch ---
log "Launch (virtual desktop ${DESKTOP_RES})"
cd "$(dirname "$EXE")"
exec wine explorer "/desktop=${DESKTOP_NAME},${DESKTOP_RES}" "$(basename "$EXE")"
