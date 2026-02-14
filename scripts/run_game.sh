set -euo pipefail

MODE="${1:-}"
[[ "$MODE" == "gui" || "$MODE" == "headless" ]] || { echo "usage: $0 {gui|headless}" >&2; exit 2; }

export WINEPREFIX="${WINEPREFIX:-/opt/prefix}"
export WINEARCH="${WINEARCH:-win64}"
export GAME_ROOT="${GAME_ROOT:-/root/Dark.Souls.Remastered.v1.04}"

export WINEDLLOVERRIDES="${WINEDLLOVERRIDES:-winemenubuilder.exe=d;mscoree,mshtml=}"

if [[ "$MODE" == "gui" ]]; then
  DESKTOP_NAME="${DESKTOP_NAME:-DSR}"
  DESKTOP_RES="${DESKTOP_RES:-800x600}"

  export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/tmp/xdg}"
  mkdir -p "$XDG_RUNTIME_DIR"
  chmod 700 "$XDG_RUNTIME_DIR"

  if [[ ! -f "$WINEPREFIX/system.reg" ]]; then
    wineboot --init
  fi
else
  XVFB_RES="${XVFB_RES:-800x600}"
  XVFB_DEPTH="${XVFB_DEPTH:-24}"
  XVFB_SERVER_ARGS="${XVFB_SERVER_ARGS:--screen 0 ${XVFB_RES}x${XVFB_DEPTH}}"

  export WINEDEBUG="${WINEDEBUG:--all}"

  if [[ ! -f "$WINEPREFIX/system.reg" ]]; then
    xvfb-run -a --server-args="$XVFB_SERVER_ARGS" wineboot --init
  fi
fi

wine reg add "HKCU\Software\Wine\Drivers" /v Audio /t REG_SZ /d "pulse" /f >/dev/null 2>&1 || true

EXE="${GAME_EXE:-$(find "$GAME_ROOT" -type f -iname 'DarkSoulsRemastered.exe' -print -quit)}"

cd "$(dirname "$EXE")"

if [[ "$MODE" == "gui" ]]; then
  exec wine explorer "/desktop=${DESKTOP_NAME},${DESKTOP_RES}" "$(basename "$EXE")"
else
  exec xvfb-run -a --server-args="$XVFB_SERVER_ARGS" wine "$(basename "$EXE")"
fi
