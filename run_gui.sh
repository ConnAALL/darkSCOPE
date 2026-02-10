#!/usr/bin/env bash
set -euo pipefail

export WINEPREFIX="${WINEPREFIX:-/opt/prefix}"
export WINEARCH="${WINEARCH:-win64}"
export GAME_ROOT="${GAME_ROOT:-/opt/game}"

# Disable menu integration in containers (prevents winemenubuilder spam)
export WINEDLLOVERRIDES="winemenubuilder.exe=d;mscoree,mshtml="

log="${WINEPREFIX}/darkscope_gui_init.log"

die() {
  echo "ERROR: $*" >&2
  if [[ -f "$log" ]]; then
    echo "--- last 200 lines of $log ---" >&2
    tail -n 200 "$log" >&2 || true
  fi
  exit 1
}

init_prefix() {
  mkdir -p "$WINEPREFIX"

  if [[ -f "${WINEPREFIX}/.darkscope_prefix_ready" ]]; then
    return 0
  fi

  # IMPORTANT:
  # Prefix initialization should NOT depend on host X access.
  # If the container can't authenticate to your host X server (common when running as root),
  # wineboot/winetricks fail and the script would exit early (set -e), leaving a broken prefix.
  echo "Initializing Wine prefix (GUI mode; init runs under Xvfb)..." | tee "$log"
  xvfb-run -a --server-args="-screen 0 1280x720x24" wineboot --init >>"$log" 2>&1 || die "wineboot failed"
  wineserver -w >>"$log" 2>&1 || true

  echo "Installing winetricks deps (GUI mode; under Xvfb)..." | tee -a "$log"
  xvfb-run -a --server-args="-screen 0 1280x720x24" \
    winetricks -q win10 corefonts vcrun2019 d3dcompiler_47 xact dxvk >>"$log" 2>&1 || die "winetricks failed"
  wineserver -w >>"$log" 2>&1 || true

  touch "${WINEPREFIX}/.darkscope_prefix_ready"
}

check_host_x() {
  echo "DISPLAY=${DISPLAY:-<unset>}"
  echo "WINEPREFIX=$WINEPREFIX"

  if [[ -z "${DISPLAY:-}" ]]; then
    die "DISPLAY is not set. Pass -e DISPLAY and mount /tmp/.X11-unix."
  fi

  if [[ ! -d /tmp/.X11-unix ]]; then
    die "/tmp/.X11-unix is not mounted. Add: -v /tmp/.X11-unix:/tmp/.X11-unix"
  fi

  # xdpyinfo is provided by x11-utils (installed in the image)
  if ! xdpyinfo -display "$DISPLAY" >/dev/null 2>&1; then
    cat >&2 <<EOF
ERROR: Cannot connect/authenticate to host X display "$DISPLAY".

Most common fixes (pick ONE approach):
  1) Allow root on the host X server (quickest):
     xhost +si:localuser:root

  2) Use Xauthority cookies (more secure):
     docker run ... -e XAUTHORITY=/root/.Xauthority -v "\$XAUTHORITY:/root/.Xauthority:ro" ...

  3) Run the container as your user (often easiest with Xauthority):
     docker run ... --user \$(id -u):\$(id -g) -e XAUTHORITY=/tmp/.Xauthority -v "\$XAUTHORITY:/tmp/.Xauthority:ro" ...

Then re-run the container with the same DISPLAY and /tmp/.X11-unix mount.
EOF
    exit 1
  fi
}

init_prefix
check_host_x

# Find the exe
EXE="$(find "$GAME_ROOT" -type f -iname 'DarkSoulsRemastered.exe' -print -quit)"
if [[ -z "${EXE}" ]]; then
  echo "ERROR: DarkSoulsRemastered.exe not found under $GAME_ROOT"
  exit 1
fi

cd "$(dirname "$EXE")"
exec wine "$(basename "$EXE")"
