#!/usr/bin/env bash
# Thin wrapper around `uv run --no-sync mpremote connect <board>` for a real RP2040 over USB serial.
# `exec`/`run`/`ls`/`cat` stay RAM-only and never touch flash; `cp`/`rm`/`mkdir`/`rmdir` do write flash - be deliberate
# before passing those. The board is $MPREMOTE_DEVICE, else the one `toolchain/setup_toolchain.py board` resolves.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then
    cat <<'USAGE'
Usage: scripts/mpremote_connect.sh [mpremote arguments]

Runs `uv run --no-sync mpremote connect <board>` with the given arguments. exec/run/ls/cat stay RAM-only;
cp/rm/mkdir/rmdir write the board's flash.
Other arguments go to mpremote. Environment: MPREMOTE_DEVICE (the board's serial device; default: the
one MicroPython board found by its /dev/serial/by-id name, as `toolchain/setup_toolchain.py board` prints it).
USAGE
    exit 0
fi

# The one retried sync (scripts/uv_sync_retried.sh) first: every uv run below is --no-sync.
if ! scripts/uv_sync_retried.sh; then
    echo "error: the retried uv sync failed - its output above names the cause; nothing reached the board" >&2
    exit 1
fi
# No board or several: the resolver's own error reaches the user unchanged, and set -e exits with its code.
device="${MPREMOTE_DEVICE:-$(uv run --no-sync toolchain/setup_toolchain.py board)}"
# --no-sync: talking to a board never triggers an implicit sync of the dev group.
uv run --no-sync mpremote connect "$device" "$@"
