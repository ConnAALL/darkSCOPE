#!/usr/bin/env bash
set -euo pipefail

PULSE_DIR="${PULSE_DIR:-/tmp/pulse}"
PULSE_SOCKET="${PULSE_SOCKET:-$PULSE_DIR/native}"
export PULSE_SERVER="unix:$PULSE_SOCKET"

mkdir -p "$PULSE_DIR"
chmod 700 "$PULSE_DIR"

pulseaudio -n --daemonize=yes --exit-idle-time=-1 --log-target=stderr \
  -L "module-native-protocol-unix socket=$PULSE_SOCKET auth-anonymous=1" \
  -L "module-null-sink sink_name=nullsink sink_properties=device.description=NullSink" \
  -L "module-always-sink" || true

exec "$@"
