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

echo "[entrypoint] PulseAudio started."
echo

echo "[entrypoint] Setting up Wine prefix..."
export WINEPREFIX="${WINEPREFIX:-/opt/prefix}"
SAVE_ROOT="$WINEPREFIX/drive_c/users/root/Documents/NBGI/DARK SOULS REMASTERED"
echo "[entrypoint] Wine prefix set to $WINEPREFIX."
echo

echo "[entrypoint] To initialize the game instances and run the training, run the following command:"
echo "  python3 /root/scripts/generate_config.py --n <N>"
echo "[entrypoint] Initialization complete."
echo
echo "Welcome to the Dark Souls Remastered Docker container!"
exec "$@"
