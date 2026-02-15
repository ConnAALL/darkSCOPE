#!/usr/bin/env bash
set -euo pipefail

echo "[entrypoint] Starting PulseAudio..."

PULSE_DIR="${PULSE_DIR:-/tmp/pulse}"
PULSE_SOCKET="${PULSE_SOCKET:-$PULSE_DIR/native}"
export PULSE_SERVER="unix:$PULSE_SOCKET"

mkdir -p "$PULSE_DIR"
chmod 700 "$PULSE_DIR"

pkill -9 pulseaudio >/dev/null 2>&1 || true
rm -f "$PULSE_SOCKET"
rm -rf /run/pulse /var/run/pulse 2>/dev/null || true

pulseaudio -n --daemonize=yes --exit-idle-time=-1 --log-target=stderr \
  -L "module-native-protocol-unix socket=$PULSE_SOCKET auth-anonymous=1" \
  -L "module-null-sink sink_name=nullsink sink_properties=device.description=NullSink" \
  -L "module-always-sink" || true

export WINEPREFIX="${WINEPREFIX:-/opt/prefix}"
SAVE_ROOT="$WINEPREFIX/drive_c/users/root/Documents/NBGI/DARK SOULS REMASTERED"

echo "[entrypoint] Checking for existing DSR user ID folder..."

has_id_dir() {
  [[ -d "$SAVE_ROOT" ]] || return 1
  ls -1 "$SAVE_ROOT" 2>/dev/null | grep -Eq '^[0-9]+$'
}

if has_id_dir; then
  echo "[entrypoint] Existing ID folder detected."
else
  echo "[entrypoint] No ID folder found. Launching headless game to generate one..."

  mkdir -p "$SAVE_ROOT"

  /root/scripts/run_game.sh headless >/dev/null 2>&1 &
  GAME_PID=$!
  echo "[entrypoint] Headless game started (PID=$GAME_PID). Waiting for ID folder..."

  TIMEOUT=60
  ELAPSED=0

  while ! has_id_dir; do
    sleep 0.5
    ELAPSED=$((ELAPSED + 1))

    if ! kill -0 "$GAME_PID" >/dev/null 2>&1; then
      echo "[entrypoint] Game process exited before ID folder appeared."
      break
    fi

    if (( ELAPSED >= TIMEOUT * 2 )); then
      echo "[entrypoint] ERROR: Timed out waiting for ID folder."
      kill -KILL "$GAME_PID" >/dev/null 2>&1 || true
      exit 1
    fi
  done

  echo "[entrypoint] ID folder detected. Stopping headless game..."

  kill -TERM "$GAME_PID" >/dev/null 2>&1 || true
  sleep 2
  kill -KILL "$GAME_PID" >/dev/null 2>&1 || true
  wait "$GAME_PID" >/dev/null 2>&1 || true
fi

if ! has_id_dir; then
  echo "[entrypoint] ERROR: No numeric game ID folder found under:"
  echo "  $SAVE_ROOT"
  exit 1
fi

ID="$(ls -1 "$SAVE_ROOT" | grep -E '^[0-9]+$' | head -n 1)"
echo "[entrypoint] Using DSR user ID: $ID"
echo "[entrypoint] Initialization complete."
echo
echo "Welcome to the Dark Souls Remastered Docker container!"
exec "$@"
