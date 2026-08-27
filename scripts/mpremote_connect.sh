#!/usr/bin/env bash
# Thin wrapper around `uv run mpremote connect <device>` for talking to a real RP2040 over USB
# serial. `exec`/`run`/`ls`/`cat` stay RAM-only and never touch flash; `cp`/`rm`/`mkdir`/`rmdir` do
# write flash - be deliberate before passing those. Device path defaults to /dev/ttyACM0.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

device="${MPREMOTE_DEVICE:-/dev/ttyACM0}"
uv run mpremote connect "$device" "$@"
