#!/usr/bin/env bash
# `uv sync --locked`, three attempts with 10 s and 20 s pauses: a third party's build-time download (actionlint-py
# fetches its binary) must not read as a red run (owner, 2026-09-26). The one retry definition CI and the hardware
# runners call; toolchain/setup_toolchain.py's run_retried() matches it.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then
    cat <<'USAGE'
Usage: scripts/uv_sync_retried.sh [uv sync arguments]

Runs `uv sync --locked` with the given arguments in this repo, up to three attempts with 10 s and 20 s
pauses between them; the last attempt's exit code is the script's. A failure that outlasts the retries
is named in uv's own output above any test output.
USAGE
    exit 0
fi

# @tunable tool.uv_sync_attempts = 3
attempts=3
# @tunable tool.uv_sync_backoff_step_s = 10
step=10
for ((attempt = 1; attempt < attempts; attempt++)); do
    uv sync --locked "$@" && exit 0
    echo "uv sync failed on attempt $attempt/$attempts; retrying in $((attempt * step))s" >&2
    sleep "$((attempt * step))"
done
exec uv sync --locked "$@"
