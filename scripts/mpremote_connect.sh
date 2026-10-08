#!/usr/bin/env bash
# Thin wrapper around `uv run mpremote connect <device>` for talking to a real RP2040 over USB
# serial. `exec`/`run`/`ls`/`cat` stay RAM-only and never touch flash; `cp`/`rm`/`mkdir`/`rmdir` do
# write flash - be deliberate before passing those. Device path defaults to /dev/ttyACM0.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then
    cat <<'USAGE'
Usage: scripts/mpremote_connect.sh [mpremote arguments]

Runs `uv run mpremote connect <device>` with the given arguments. exec/run/ls/cat stay RAM-only;
cp/rm/mkdir/rmdir write the board's flash.
Other arguments go to mpremote. Environment: MPREMOTE_DEVICE (the board's serial device; default
/dev/ttyACM0).
USAGE
    exit 0
fi

device="${MPREMOTE_DEVICE:-/dev/ttyACM0}"
uv run mpremote connect "$device" "$@"
