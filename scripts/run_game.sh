set -euo pipefail

# Helper functions
log() { echo "[$(date +%H:%M:%S)] $*"; }
die() { echo "ERROR: $*" >&2; exit 1; }
have() { command -v "$1" >/dev/null 2>&1; }

# Usage function
usage() {
  echo "usage: $0 {gui|headless|headless-vnc}" >&2
  exit 2
}

is_rtx_5090() {
  # Prefer nvidia-smi (most reliable in your container); fall back to vulkaninfo if needed
  nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | grep -qi "RTX 5090" && return 0
  vulkaninfo --summary 2>/dev/null | grep -qi "NVIDIA GeForce RTX 5090" && return 0
  return 1
}

wineserver -k >/dev/null 2>&1 || true

# Parse the mode from the command-line arguments
MODE="${1:-}"
case "$MODE" in
  headless-vnc) MODE="headless"; export ENABLE_VNC=1 ;;
  gui|headless) ;;
  *) usage ;;
esac

# Set the Wine prefix and other environment variables
export WINEPREFIX="${WINEPREFIX:-/opt/prefix}"
export WINEARCH="${WINEARCH:-win64}"
export GAME_ROOT="${GAME_ROOT:-/root/Dark.Souls.Remastered.v1.04}"
export WINEDLLOVERRIDES="${WINEDLLOVERRIDES:-winemenubuilder.exe=d;mscoree,mshtml=}"
export WINEDEBUG="${WINEDEBUG:--all}"

supports_vulkan_13() {
  vulkaninfo --summary 2>/dev/null | grep -Eq 'Vulkan Instance Version: *1\.3|apiVersion *= *1\.3'
}


enable_dxvk_overrides() {
  wine reg add "HKCU\Software\Wine\DllOverrides" /v d3d11     /t REG_SZ /d native,builtin /f >/dev/null 2>&1 || true
  wine reg add "HKCU\Software\Wine\DllOverrides" /v dxgi      /t REG_SZ /d native,builtin /f >/dev/null 2>&1 || true
  wine reg add "HKCU\Software\Wine\DllOverrides" /v d3d10core /t REG_SZ /d native,builtin /f >/dev/null 2>&1 || true
}

disable_dxvk_overrides() {
  # Delete overrides so Wine can use builtin again
  wine reg delete "HKCU\Software\Wine\DllOverrides" /v d3d11     /f >/dev/null 2>&1 || true
  wine reg delete "HKCU\Software\Wine\DllOverrides" /v dxgi      /f >/dev/null 2>&1 || true
  wine reg delete "HKCU\Software\Wine\DllOverrides" /v d3d10core /f >/dev/null 2>&1 || true
}

if is_rtx_5090; then
  log "Detected RTX 5090 -> enabling DXVK overrides."
  enable_dxvk_overrides
elif supports_vulkan_13; then
  log "Vulkan 1.3 available -> enabling DXVK overrides."
  enable_dxvk_overrides
else
  log "No Vulkan 1.3 -> disabling DXVK overrides (use Wine builtin/wined3d)."
  disable_dxvk_overrides
fi

# Set the desktop name and resolution
DESKTOP_NAME="${DESKTOP_NAME:-DSR}"
DESKTOP_RES="${DESKTOP_RES:-800x600}"

# Set the XDG runtime directory
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/tmp/xdg}"
mkdir -p "$XDG_RUNTIME_DIR"
chmod 700 "$XDG_RUNTIME_DIR"

# Initialize variables
STARTED_XORG=0
XORG_PID=""
STARTED_VNC=0
VNC_PID=""

# Cleanup function for the SIGTERM signal
cleanup() {
  if [[ "${STARTED_VNC}" == "1" && -n "${VNC_PID}" ]]; then
    kill -TERM "$VNC_PID" >/dev/null 2>&1 || true
  fi
  if [[ "${STARTED_XORG}" == "1" && -n "${XORG_PID}" ]]; then
    kill -TERM "$XORG_PID" >/dev/null 2>&1 || true
  fi
  wineserver -k >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

# Parse the resolution string into width and height
parse_res() {
  local res="$1"
  [[ "$res" =~ ^([0-9]+)x([0-9]+)$ ]] || return 1
  echo "${BASH_REMATCH[1]} ${BASH_REMATCH[2]}"
}

# Start the headless Xorg server
start_headless_x() {
  local display_num="${DISPLAY_NUM:-99}"
  export DISPLAY=":${display_num}"

  local depth="${XORG_DEPTH:-24}"
  local xorg_log="${XORG_LOG:-/tmp/Xorg.${display_num}.log}"

  local tpl_dir="${XORG_TPL_DIR:-/root/scripts/xorg}"
  local conf_dir="/tmp/xorg"
  local conf="${conf_dir}/xorg.conf"

  local tpl=""
  if have_nvidia; then
    tpl="${tpl_dir}/xorg-nvidia.conf.in"
  else
    tpl="${tpl_dir}/xorg-igpu.conf.in"
  fi

  local w h
  read -r w h < <(parse_res "$DESKTOP_RES") || die "Invalid DESKTOP_RES='$DESKTOP_RES'"
  [[ -f "$tpl" ]] || die "Missing Xorg template: $tpl"

  mkdir -p "$conf_dir"
  sed \
    -e "s/{{XORG_DEPTH}}/${depth}/g" \
    -e "s/{{VIRTUAL_W}}/${w}/g" \
    -e "s/{{VIRTUAL_H}}/${h}/g" \
    "$tpl" > "$conf"

  mkdir -p /tmp/.X11-unix
  chmod 1777 /tmp/.X11-unix
  rm -f "/tmp/.X${display_num}-lock" || true

  log "Starting Xorg on $DISPLAY using $(basename "$tpl")..."
  Xorg "$DISPLAY" -noreset -nolisten tcp -logfile "$xorg_log" -config "$conf" >/dev/null 2>&1 &
  XORG_PID="$!"
  STARTED_XORG=1

  for _ in {1..120}; do
    xdpyinfo -display "$DISPLAY" >/dev/null 2>&1 && return 0
    sleep 0.1
  done

  tail -n 200 "$xorg_log" 2>/dev/null || true
  die "Xorg failed to start on $DISPLAY"
}


start_vnc() {
  [[ "${ENABLE_VNC:-0}" == "1" ]] || return 0

  local port="${VNC_PORT:-5900}"
  local display_num="${DISPLAY_NUM:-99}"
  local vnc_log="${VNC_LOG:-/tmp/x11vnc.${display_num}.log}"

  have x11vnc || die "ENABLE_VNC=1 but x11vnc not found"

  log "Starting VNC on port ${port}..."
  x11vnc -display "$DISPLAY" -rfbport "$port" \
    -forever -shared -xkb -noxdamage \
    -nopw \
    -o "$vnc_log" >/dev/null 2>&1 &
  VNC_PID="$!"
  STARTED_VNC=1
}

have_nvidia() { command -v nvidia-smi >/dev/null 2>&1; }

have_dri() { [[ -c /dev/dri/renderD128 || -d /dev/dri ]]; }

start_headless_xvfb() {
  local display_num="${DISPLAY_NUM:-99}"
  export DISPLAY=":${display_num}"

  local w h
  read -r w h < <(parse_res "$DESKTOP_RES") || die "Invalid DESKTOP_RES='$DESKTOP_RES'"

  log "Starting Xvfb on $DISPLAY (${w}x${h}x24)..."
  Xvfb "$DISPLAY" -screen 0 "${w}x${h}x24" +extension GLX +render -noreset >/dev/null 2>&1 &
  XORG_PID="$!"
  STARTED_XORG=1

  for _ in {1..120}; do
    xdpyinfo -display "$DISPLAY" >/dev/null 2>&1 && return 0
    sleep 0.1
  done
  die "Xvfb failed to start on $DISPLAY"
}

if [[ "$MODE" == "headless" ]]; then
  # Use real Xorg whenever a real GPU device is available (NVIDIA or /dev/dri iGPU).
  if have_nvidia || have_dri; then
    start_headless_x
  else
    start_headless_xvfb
  fi
  start_vnc
fi


wine reg add "HKCU\Software\Wine\Drivers" /v Audio /t REG_SZ /d "pulse" /f >/dev/null 2>&1 || true

EXE="${GAME_EXE:-}"
EXE="$(find "$GAME_ROOT" -type f -iname 'DarkSoulsRemastered.exe' -print -quit || true)"
cd "$(dirname "$EXE")"

if [[ ! -f "$WINEPREFIX/system.reg" ]]; then
  log "Initializing Wine prefix..."
  wineboot --init
fi

cmd=(wine explorer "/desktop=${DESKTOP_NAME},${DESKTOP_RES}" /Unix "$(pwd)" start /wait "" "$(basename "$EXE")")

if [[ "$MODE" == "gui" ]]; then
  exec "${cmd[@]}"
else
  "${cmd[@]}"
fi
