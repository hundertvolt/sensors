#!/usr/bin/env bash
# Sourced: the one version check before a bare python3 (tomllib and datetime.UTC need 3.11). require_python311 returns
# quietly for 3.11 or newer, else names the calling script, the version found and the fix, and returns 1, so the
# caller's set -e ends it before anything runs.
(return 0 2>/dev/null) || { echo "error: source scripts/_require_python.sh, do not run it" >&2; exit 2; }

require_python311() {
    local found
    if command -v python3 >/dev/null 2>&1 && python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then
        return 0
    fi
    if command -v python3 >/dev/null 2>&1; then
        found="the python3 on PATH is $(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null || echo "unreadable")"
    else
        found="no python3 is on PATH"
    fi
    echo "error: $0 needs python3 >= 3.11 (tomllib, datetime.UTC) - $found; fix: activate the uv venv (uv sync) or put a newer python3 first on PATH" >&2
    return 1
}
