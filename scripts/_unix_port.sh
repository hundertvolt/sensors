#!/usr/bin/env bash
# Sourced, and callable as a command: the one Unix-port probe. A binary is named by the build flavour it reports
# (standard, settrace, lwip), checked against the toolchain record and used under a shared hold of the toolchain lock;
# PICO_TOOLCHAIN_DIR is read only here, the two MICROPYPATH layouts only from scripts/micropypath.toml.

_unix_port_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
_unix_port_lock_fd="${_unix_port_lock_fd:-}"
# The record's input_sha256 keys, in the order toolchain/setup_toolchain.py's _toolchain_record() writes them.
_UNIX_PORT_INPUTS=(versions.toml setup_toolchain.py micropython_overrides.py)
# A build interrupted between its two passes has no frozen asyncio, so the probe imports it (SPECIFICATION.md E.5.2).
_UNIX_PORT_PROBE='import sys, asyncio
try:
    import lwip
except ImportError:
    lwip = None
print("settrace" if hasattr(sys, "settrace") else "lwip" if lwip else "standard")'
# A binary that hangs at start is killed at this bound and reads as unusable, so no caller waits on it.
# @tunable runner.unix_port_probe_timeout_s = 60
_UNIX_PORT_PROBE_TIMEOUT_S=60
_UNIX_PORT_USAGE="Usage: scripts/_unix_port.sh check|ensure|unix_port_bin <standard|settrace|lwip> | micropypath <unit|twin>"

_unix_port_flavour_valid() {
    case "${1:-}" in
        standard | settrace | lwip) ;;
        *) _unix_port_usage_error "error: unknown build flavour '${1:-}' - one of: standard settrace lwip" ;;
    esac
}

_unix_port_help() {
    cat <<EOF
$_UNIX_PORT_USAGE
  check <flavour>          print the binary's path, or exit 1 naming the flavour it reports; builds nothing
  ensure <flavour>         as check, after one \`uv run toolchain/setup_toolchain.py setup\` when the binary is missing
                           or of another flavour, or the toolchain record is missing or names other inputs
  unix_port_bin <flavour>  print where that flavour's binary lives
  micropypath <unit|twin>  print that MICROPYPATH layout from scripts/micropypath.toml

Sourced, it defines the functions micropypath, unix_port_bin, unix_port_check, unix_port_ensure (one or more
flavours, one setup for them all), unix_port_flavour and unix_port_toolchain_dir. A run holds <toolchain>/.toolchain.lock shared while it uses the binaries, so a setup or
firmware build (which holds it exclusive) and a run refuse each other at once rather than wait.

Environment:
  PICO_TOOLCHAIN_DIR   toolchain cache (default: ~/pico-toolchain)
  SKIP_APT=1           ensure: skip the system-package step of the toolchain build (default: 0)

Exit codes: 0 done; 1 the binary or the toolchain is not usable, named on stderr; 2 a usage error.
EOF
}

_unix_port_lock_shared() {
    # Held for the life of the calling shell; a setup or firmware build holding it exclusive refuses this run at once.
    local dir lock holder=""
    [ -z "$_unix_port_lock_fd" ] || return 0
    dir="$(unix_port_toolchain_dir)"
    [ -d "$dir" ] || return 0
    lock="$dir/.toolchain.lock"
    if ! command -v flock >/dev/null 2>&1; then
        echo "error: flock (util-linux) is not on PATH - scripts/_unix_port.sh holds $lock with it" >&2
        exit 1
    fi
    if ! { exec {_unix_port_lock_fd}>>"$lock"; } 2>/dev/null; then
        _unix_port_lock_fd=""
        echo "error: cannot open the toolchain lock $lock - is $dir writable?" >&2
        exit 1
    fi
    if ! flock -s -n "$_unix_port_lock_fd"; then
        IFS= read -r holder <"$lock" || true
        _unix_port_unlock
        echo "error: the toolchain at $dir is in use by a setup or firmware build (pid ${holder:-unknown}, holding $lock) - wait for it to finish, or use another PICO_TOOLCHAIN_DIR" >&2
        exit 1
    fi
}

_unix_port_main() {
    case "${1:-}" in
        -h | --help)
            _unix_port_help
            exit 0
            ;;
        check | ensure | unix_port_bin)
            [ "$#" -eq 2 ] || _unix_port_usage_error "error: $1 needs one build flavour"
            _unix_port_flavour_valid "$2"
            if [ "$1" = "check" ]; then
                unix_port_check "$2"
            elif [ "$1" = "ensure" ]; then
                unix_port_ensure "$2"
            fi
            unix_port_bin "$2"
            ;;
        micropypath)
            [ "$#" -eq 2 ] || _unix_port_usage_error "error: micropypath needs one layout, unit or twin"
            micropypath "$2"
            ;;
        "") _unix_port_usage_error "error: no command given" ;;
        *) _unix_port_usage_error "error: unknown command '$1'" ;;
    esac
}

_unix_port_need_timeout() {
    if ! command -v timeout >/dev/null 2>&1; then
        echo "error: timeout (coreutils) is not on PATH - scripts/_unix_port.sh bounds the Unix-port probe with it" >&2
        exit 1
    fi
}

_unix_port_probe_said() {
    # " (the probe said: <its last line>)" for a binary the probe found unusable, or nothing: the cause to rebuild for.
    local out line last="" rc=0
    out="$(timeout -s KILL "$_UNIX_PORT_PROBE_TIMEOUT_S" "$1" -c "$_UNIX_PORT_PROBE" 2>&1)" || rc=$?
    if [ "$rc" -eq 137 ]; then
        printf ' (the probe was killed, exit 137: it hung past its %s s bound or died by SIGKILL)' "$_UNIX_PORT_PROBE_TIMEOUT_S"
        return 0
    fi
    while IFS= read -r line; do
        if [ -n "$line" ]; then
            last="$line"
        fi
    done <<<"$out"
    if [ -n "$last" ]; then
        printf ' (the probe said: %s)' "$last"
    fi
}

_unix_port_stale_input() {
    # The first recorded input whose hash is missing from the record or differs from this tree's file; nothing if none.
    local record="$1" name line actual in_block=0
    local -A recorded=()
    if ! command -v sha256sum >/dev/null 2>&1; then
        echo "error: sha256sum (coreutils) is not on PATH - scripts/_unix_port.sh compares the toolchain record's input hashes with it" >&2
        exit 1
    fi
    while IFS= read -r line || [ -n "$line" ]; do
        if [ "$line" = '  "input_sha256": {' ]; then
            in_block=1
        elif [ "$in_block" = "1" ] && [[ "$line" == "  }"* ]]; then
            break
        elif [ "$in_block" = "1" ] && [[ "$line" =~ ^\ {4}\"([^\"]+)\":\ \"([0-9a-f]{64})\",?$ ]]; then
            recorded["${BASH_REMATCH[1]}"]="${BASH_REMATCH[2]}"
        fi
    done <"$record"
    for name in "${_UNIX_PORT_INPUTS[@]}"; do
        actual="$(sha256sum "$_unix_port_root/toolchain/$name" 2>/dev/null)" || actual=""
        if [ "${recorded[$name]:-}" != "${actual%% *}" ] || [ -z "$actual" ]; then
            printf '%s\n' "$name"
            return 0
        fi
    done
}

_unix_port_unlock() {
    if [ -n "$_unix_port_lock_fd" ]; then
        exec {_unix_port_lock_fd}>&-
        _unix_port_lock_fd=""
    fi
}

_unix_port_usage_error() {
    printf '%s\n%s\n' "$1" "$_UNIX_PORT_USAGE" >&2
    exit 2
}

_unix_port_why_rebuild() {
    # Why the flavour's binary cannot be used as it stands, or nothing: the conditions under which ensure runs setup.
    local flavour="$1" bin record stale found
    bin="$(unix_port_bin "$flavour")"
    record="$(unix_port_toolchain_dir)/toolchain-record.json"
    if [ ! -f "$bin" ] || [ ! -x "$bin" ]; then
        printf 'MicroPython Unix port not found at %s' "$bin"
        return 0
    fi
    found="$(unix_port_flavour "$bin")"
    if [ "$found" != "$flavour" ]; then
        printf "%s reports itself as the '%s' build flavour, not '%s'%s" "$bin" "$found" "$flavour" "$([ "$found" != unusable ] || _unix_port_probe_said "$bin")"
        return 0
    fi
    if [ ! -f "$record" ]; then
        printf 'no toolchain record at %s (an interrupted or older setup)' "$record"
        return 0
    fi
    stale="$(_unix_port_stale_input "$record")" || exit 1
    if [ -n "$stale" ]; then
        printf "the toolchain record at %s names other inputs than this tree's toolchain/%s" "$record" "$stale"
    fi
}

# micropypath <unit|twin>: that layout's value, read from its one line in scripts/micropypath.toml.
micropypath() {
    local layout="${1:-}" file="$_unix_port_root/scripts/micropypath.toml" line value="" count=0
    case "$layout" in
        unit | twin) ;;
        *) _unix_port_usage_error "error: unknown MICROPYPATH layout '$layout' - one of: unit twin" ;;
    esac
    if [ ! -f "$file" ]; then
        echo "error: no MICROPYPATH layout file at $file" >&2
        exit 1
    fi
    while IFS= read -r line || [ -n "$line" ]; do
        if [[ "$line" =~ ^$layout\ =\ \"([^\"]*)\"$ ]]; then
            value="${BASH_REMATCH[1]}"
            count=$((count + 1))
        fi
    done <"$file"
    if [ "$count" -ne 1 ]; then
        echo "error: $file has no single $layout = \"…\" line" >&2
        exit 1
    fi
    printf '%s\n' "$value"
}

# unix_port_bin <flavour>: where that build flavour's binary lives under the toolchain directory.
unix_port_bin() {
    _unix_port_flavour_valid "${1:-}"
    printf '%s\n' "$(unix_port_toolchain_dir)/micropython/ports/unix/build-$1/micropython"
}

# unix_port_check <flavour>: returns once the binary exists and reports that flavour, else exits 1 naming what it found.
unix_port_check() {
    local flavour="${1:-}" bin found
    _unix_port_flavour_valid "$flavour"
    _unix_port_lock_shared
    _unix_port_need_timeout
    bin="$(unix_port_bin "$flavour")"
    if [ ! -f "$bin" ] || [ ! -x "$bin" ]; then
        echo "error: no MicroPython Unix port at $bin - build it with: uv run toolchain/setup_toolchain.py setup" >&2
        exit 1
    fi
    found="$(unix_port_flavour "$bin")"
    if [ "$found" != "$flavour" ]; then
        echo "error: $bin reports itself as the '$found' build flavour, not '$flavour'$([ "$found" != unusable ] || _unix_port_probe_said "$bin") - rebuild with: uv run toolchain/setup_toolchain.py setup --clean" >&2
        exit 1
    fi
}

# unix_port_ensure <flavour>...: as unix_port_check for each, after one setup when a binary or the record says it is
# needed. Call it directly, never inside $(...): the shared lock it takes is held by the shell that calls it.
unix_port_ensure() {
    local flavour why="" dir bin record found stale rc=0 skip_apt=()
    [ "$#" -gt 0 ] || _unix_port_usage_error "error: unix_port_ensure needs a build flavour"
    for flavour in "$@"; do
        _unix_port_flavour_valid "$flavour"
    done
    _unix_port_lock_shared
    _unix_port_need_timeout
    for flavour in "$@"; do
        why="$(_unix_port_why_rebuild "$flavour")" || exit 1
        [ -z "$why" ] || break
    done
    [ -n "$why" ] || return 0
    echo "== $why - rebuilding the Unix ports" >&2
    dir="$(unix_port_toolchain_dir)"
    if [ "${SKIP_APT:-0}" = "1" ]; then
        skip_apt=(--skip-apt)
    fi
    # setup takes the lock exclusive, so this shell's shared hold goes first and is taken again after.
    _unix_port_unlock
    (cd "$_unix_port_root" && uv run toolchain/setup_toolchain.py setup --toolchain-dir "$dir" "${skip_apt[@]}") || rc=$?
    if [ "$rc" -ne 0 ]; then
        echo "error: uv run toolchain/setup_toolchain.py setup --toolchain-dir $dir failed (exit $rc) - its output above names the cause" >&2
        exit 1
    fi
    _unix_port_lock_shared
    record="$dir/toolchain-record.json"
    for flavour in "$@"; do
        bin="$(unix_port_bin "$flavour")"
        if [ ! -f "$bin" ] || [ ! -x "$bin" ]; then
            echo "error: $bin is still missing after setup - rebuild with: uv run toolchain/setup_toolchain.py setup --clean" >&2
            exit 1
        fi
        found="$(unix_port_flavour "$bin")"
        if [ "$found" != "$flavour" ]; then
            echo "error: $bin reports itself as the '$found' build flavour after setup, not '$flavour'$([ "$found" != unusable ] || _unix_port_probe_said "$bin") - rebuild with: uv run toolchain/setup_toolchain.py setup --clean" >&2
            exit 1
        fi
    done
    if [ ! -f "$record" ]; then
        echo "error: setup left no toolchain record at $record - rebuild with: uv run toolchain/setup_toolchain.py setup --clean" >&2
        exit 1
    fi
    stale="$(_unix_port_stale_input "$record")" || exit 1
    if [ -n "$stale" ]; then
        echo "error: the toolchain record at $record still names other inputs than this tree's toolchain/$stale after setup - rebuild with: uv run toolchain/setup_toolchain.py setup --clean" >&2
        exit 1
    fi
}

# unix_port_flavour <binary>: the build flavour the binary reports (standard, settrace or lwip) within the probe's
# bound, or unusable. Always returns 0, so set -e never fires inside the caller's substitution.
unix_port_flavour() {
    local probe=""
    if [ -f "${1:-}" ] && [ -x "$1" ]; then
        probe="$(timeout -s KILL "$_UNIX_PORT_PROBE_TIMEOUT_S" "$1" -c "$_UNIX_PORT_PROBE" 2>/dev/null)" || probe=""
    fi
    case "$probe" in
        standard | settrace | lwip) printf '%s\n' "$probe" ;;
        *) printf 'unusable\n' ;;
    esac
}

# unix_port_toolchain_dir: $PICO_TOOLCHAIN_DIR (default ~/pico-toolchain), made absolute against the caller's directory.
unix_port_toolchain_dir() {
    local dir="${PICO_TOOLCHAIN_DIR:-}"
    if [ -z "$dir" ]; then
        dir="${HOME:?HOME is unset - set PICO_TOOLCHAIN_DIR to the toolchain directory}/pico-toolchain"
    fi
    case "$dir" in
        /*) ;;
        *) dir="$PWD/$dir" ;;
    esac
    printf '%s\n' "$dir"
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then
    set -euo pipefail
    _unix_port_main "$@"
fi
