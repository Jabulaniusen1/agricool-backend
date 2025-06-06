#!/bin/bash
set -euo pipefail

COMSOL_PWD="$PWD"
export DISPLAY=:0

CONTROL_LOOP_FILE="$COMSOL_PWD/event_loop_control.txt"
CONTROL_ROOT_FILE="$COMSOL_PWD/2025-05-21_DigitalTwin_GenericV8.exe"

# Ensure required env vars are set
: "${COMSOL_CSA_DIR:?COMSOL_CSA_DIR not set}"
: "${COMSOL_SETUP_CONFIG:?COMSOL_SETUP_CONFIG not set}"
: "${COMSOL_PREFS_DIR:?COMSOL_PREFS_DIR not set}"

# Wait for control files to appear
while [ ! -f "$CONTROL_LOOP_FILE" ]; do
    echo "$(date "+%Y-%m-%d %H:%M:%S") - Waiting for $CONTROL_LOOP_FILE to become available..."
    sleep 1
done

while [ ! -f "$CONTROL_ROOT_FILE" ]; do
    echo "$(date "+%Y-%m-%d %H:%M:%S") - Waiting for $CONTROL_ROOT_FILE to become available..."
    sleep 1
done

# Optionally log contents of control files
echo "$(date "+%Y-%m-%d %H:%M:%S") - Contents of $CONTROL_LOOP_FILE:"

# Wait for Xvfb to become ready
echo "$(date "+%Y-%m-%d %H:%M:%S") - Waiting for Xvfb to start..."
TIMEOUT=30
SECONDS=0
while ! xdpyinfo -display "$DISPLAY" >/dev/null 2>&1; do
    echo "$(date "+%Y-%m-%d %H:%M:%S") - Waiting for Xvfb DISPLAY $DISPLAY to be ready..."
    sleep 1
    if [ "$SECONDS" -ge "$TIMEOUT" ]; then
        echo "$(date "+%Y-%m-%d %H:%M:%S") - ERROR: DISPLAY $DISPLAY not available after $TIMEOUT seconds"
        exit 1
    fi
done

# Launch COMSOL
echo "$(date "+%Y-%m-%d %H:%M:%S") - Launching COMSOL..."
START_TIME=$(date +%s)

"$COMSOL_CSA_DIR/2025-05-21_DigitalTwin_GenericV8.sh" \
    -J-Djava.security.manager=disallow \
    -s "$COMSOL_SETUP_CONFIG" \
    -prefsdir "$COMSOL_PREFS_DIR" \
    -run > /dev/null 2>&1 < /dev/null


COMSOL_EXIT_CODE=$?
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

if [ $COMSOL_EXIT_CODE -ne 0 ]; then
    echo "$(date "+%Y-%m-%d %H:%M:%S") - ERROR: COMSOL exited with code $COMSOL_EXIT_CODE"
    echo "$(date "+%Y-%m-%d %H:%M:%S") - Check $STDERR_LOG for details."
    exit $COMSOL_EXIT_CODE
fi

# Wait for COMSOL to fully close
echo "$(date "+%Y-%m-%d %H:%M:%S") - Waiting for COMSOL to finish..."
while pgrep -x "comsollauncher" > /dev/null; do
    sleep 1
done

echo "$(date "+%Y-%m-%d %H:%M:%S") - COMSOL execution complete."
echo "$(date "+%Y-%m-%d %H:%M:%S") - COMSOL runtime: ${DURATION}s"
