#!/usr/bin/env bash
# _preflight.sh [--bench]: whether this tree can run its checks now, one OK/WARN/FAIL line each with the fix, in
# seconds and touching nothing (.claude/skills/tree-care). --bench adds the bench host's facts, still no board contact.
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
bench=0

usage() {
    cat <<'EOF'
Usage: scripts/_preflight.sh [--bench]
  --bench      also the bench host's facts: its environment variables and a MicroPython board on USB (no contact)
  -h, --help   print this help and exit
Each line reads OK, WARN or FAIL, then the fix. Exit 1 when a line reads FAIL, 0 otherwise, 2 on a usage error.
EOF
}

for arg in "$@"; do
    case "$arg" in
        -h|--help) usage; exit 0 ;;
        --bench) bench=1 ;;
        *) echo "error: unknown argument '$arg' (scripts/_preflight.sh --help)" >&2; exit 2 ;;
    esac
done
cd "$root"
fails=0
say() { # say OK|WARN|FAIL TEXT
    echo "$1 $2"
    [ "$1" != FAIL ] || fails=1
}

head_line="$(git rev-parse --short HEAD 2>/dev/null || echo none) on $(git branch --show-current 2>/dev/null || echo detached)"
dirty="$({ git status --porcelain --untracked-files=no 2>/dev/null || true; } | wc -l)"
say OK "tree: $root at $head_line, $dirty modified tracked file(s)"

want_uv="$(sed -n 's/^required-version = "==\(.*\)"$/\1/p' pyproject.toml)"
have_uv="$({ uv --version 2>/dev/null || true; } | cut -d' ' -f2)"
if [ -z "$have_uv" ]; then say FAIL "uv: not on PATH - install uv $want_uv"
elif [ "$have_uv" != "$want_uv" ]; then say FAIL "uv: $have_uv, pyproject.toml pins $want_uv - install that version"
else say OK "uv: $have_uv"; fi

venv_fix="uv sync && source .venv/bin/activate"
if [ -n "${UV_PROJECT_ENVIRONMENT:-}" ] && [ "$UV_PROJECT_ENVIRONMENT" != "$root/.venv" ]; then venv_fix="deactivate; unset UV_PROJECT_ENVIRONMENT; $venv_fix"; fi
if [ "${VIRTUAL_ENV:-}" = "$root/.venv" ]; then say OK "venv: this tree's .venv is active"
elif [ -n "${VIRTUAL_ENV:-}" ]; then say WARN "venv: $VIRTUAL_ENV is active; lint.sh and typecheck.sh accept only this tree's - $venv_fix"
else say WARN "venv: none active - $venv_fix"; fi

# shellcheck source=/dev/null  # linted on its own, as one of scripts/*.sh
source scripts/_require_python.sh
if require_python311 2> /dev/null; then say OK "python3: $(python3 --version 2>&1 | cut -d' ' -f2)"
else say FAIL "python3: missing or older than 3.11 - activate this tree's venv or put a newer python3 first on PATH"; fi

want_node="$(tr -d 'v \n' < .nvmrc)"
have_node="$({ node --version 2>/dev/null || true; } | tr -d v)"
if [ -z "$have_node" ]; then say FAIL "node: not on PATH; the host tier needs it - uv run toolchain/setup_toolchain.py env --tier generic, then its Node on PATH"
elif [ "${have_node%%.*}" != "${want_node%%.*}" ]; then say WARN "node: $have_node, .nvmrc pins $want_node"
else say OK "node: $have_node"; fi
if [ -d node_modules ]; then say OK "node_modules: present"; else say WARN "node_modules: missing - npm ci"; fi

# shellcheck source=/dev/null  # linted on its own, as one of scripts/*.sh
source scripts/_unix_port.sh
for flavour in standard lwip; do
    why="$(_unix_port_why_rebuild "$flavour" 2>&1 || true)"
    if [ -z "$why" ]; then say OK "unix port $flavour: $(unix_port_bin "$flavour")"
    else say WARN "unix port $flavour: $why - scripts/test.sh rebuilds it first (minutes), or uv run toolchain/setup_toolchain.py setup"; fi
done
bin="$(unix_port_bin standard)"
if [ -x "$bin" ] && command -v getcap > /dev/null && ! { getcap "$bin" 2>/dev/null || true; } | grep -q cap_net_bind_service; then
    say WARN "unix port: no cap_net_bind_service, so the port-53 DNS test cannot bind - scripts/test.sh grants it (setcap)"
fi
if [ -d build/generated_src ] && [ -f frozen_modules/frozen_html.py ]; then say OK "generated inputs: present"
else say WARN "generated inputs: missing (a single-file run needs them) - one scripts/test.sh run builds them"; fi
if [ -d typings ]; then say OK "typings: present"; else say WARN "typings: missing - scripts/typecheck.sh installs them"; fi

free_gb="$(df -P -BG . | awk 'NR == 2 { gsub("G", "", $4); print $4 }')"
if [ "$free_gb" -ge 3 ]; then say OK "disk: ${free_gb} GB free"; else say WARN "disk: ${free_gb} GB free, below 3 GB - scripts/_tidy.sh"; fi

for lock in "${XDG_RUNTIME_DIR:-/tmp}"/sensors-port-*.lock; do
    [ -d "$lock" ] || continue
    pid="$(cat "$lock/pid" 2>/dev/null || echo 0)"
    if kill -0 "$pid" 2> /dev/null; then say WARN "port lock: $(basename "$lock") held by $(cat "$lock/runner" 2>/dev/null || echo a runner) (pid $pid) - wait for it"
    else say OK "port lock: $(basename "$lock") is stale and is taken over by the next runner"; fi
done

if [ "$bench" = 1 ]; then
    for name in MPREMOTE_DEVICE BENCH_DEVICE; do
        if [ -n "${!name:-}" ]; then say OK "bench: $name is set"; else say WARN "bench: $name is not set (tests_hardware/README.md, Environment variables)"; fi
    done
    boards="$({ find /dev/serial/by-id -maxdepth 1 -name '*MicroPython*' 2> /dev/null || true; } | wc -l)"
    if [ "$boards" -eq 1 ]; then say OK "bench: one MicroPython board on USB"; else say WARN "bench: $boards MicroPython boards on USB, one expected"; fi
    say OK "bench: load $(cut -d' ' -f1-3 /proc/loadavg); no board run while a chroot leg or twin run is going"
fi
exit "$fails"
