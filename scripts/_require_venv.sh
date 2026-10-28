#!/usr/bin/env bash
# Sourced: require_project_venv TOOL... returns 1 naming the fix unless VIRTUAL_ENV is this repo's .venv (uv run sets
# it too), uv.lock still describes it (uv sync --locked --check --offline) and every TOOL resolves under it, so a
# system ruff or mypy of another version never runs in place of the pinned one.
(return 0 2>/dev/null) || { echo "error: source scripts/_require_venv.sh, do not run it" >&2; exit 2; }

_require_venv_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"

require_project_venv() {
    local tool found out expected="$_require_venv_root/.venv"
    if [ -z "${VIRTUAL_ENV:-}" ] || [ "$(cd "$VIRTUAL_ENV" 2>/dev/null && pwd -P)" != "$expected" ]; then
        echo "error: activate the project venv first (uv sync && source .venv/bin/activate), or run through uv run" >&2
        return 1
    fi
    if ! out="$(cd "$_require_venv_root" && uv sync --locked --check --offline 2>&1)"; then
        echo "error: the venv does not match uv.lock - run uv sync" >&2
        printf '%s\n' "$out" >&2
        return 1
    fi
    for tool in "$@"; do
        found="$(command -v "$tool" || true)"
        if [ "$found" != "$expected/bin/$tool" ]; then
            echo "error: $tool resolves to ${found:-nothing on PATH}, not the project venv's $expected/bin/$tool - put it first on PATH (source .venv/bin/activate)" >&2
            return 1
        fi
    done
}
