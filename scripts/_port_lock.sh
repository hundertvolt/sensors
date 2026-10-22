#!/usr/bin/env bash
# Sourced lock for the product-fixed ports: one runner per port at a time, the holder's descendants pass, a dead
# holder's lock is taken over.
#
# A lock is ${XDG_RUNTIME_DIR:-/tmp}/sensors-port-<port>.lock/ holding files pid and runner; the owner chain travels
# down as SENSORS_PORT_LOCK_OWNER (pids) and SENSORS_PORT_LOCKS_HELD (ports), both space-separated.
(return 0 2>/dev/null) || { echo "error: source scripts/_port_lock.sh, do not run it" >&2; exit 2; }

_port_lock_alive() {
    # kill -0 fails with EPERM on another user's live process, which /proc still shows.
    [[ "$1" =~ ^[1-9][0-9]*$ ]] && { kill -0 "$1" 2>/dev/null || [ -d "/proc/$1" ]; }
}

_port_lock_clear_stale() {
    # Only the runner whose mkdir of <lock>/takeover succeeds moves that lock away, and only once its pid is
    # still dead after the wait; the rename makes the lock vanish at once rather than file by file.
    local dir="$1"
    if ! mkdir "$dir/takeover" 2>/dev/null; then
        sleep 0.05
        return 0
    fi
    if _port_lock_alive "$(_port_lock_pid "$dir")"; then
        rmdir "$dir/takeover" 2>/dev/null || true
        return 0
    fi
    if mv -T "$dir" "$dir.stale.$$" 2>/dev/null; then
        rm -rf "$dir.stale.$$"
    fi
    return 0
}

_port_lock_has() {
    case " $2 " in
        *" $1 "*) return 0 ;;
    esac
    return 1
}

_port_lock_pid() {
    # A holder writes its pid right after its mkdir, so an empty or missing file is waited for, a second at most;
    # a lock still without one after that was left by a holder that died in between.
    local dir="$1" pid="" tries=0
    while :; do
        pid="$(cat "$dir/pid" 2>/dev/null || true)"
        if [[ "$pid" =~ ^[1-9][0-9]*$ ]] || [ ! -d "$dir" ] || [ "$tries" -ge 20 ]; then
            break
        fi
        sleep 0.05
        tries=$((tries + 1))
    done
    printf '%s' "$pid"
}

_port_lock_root() {
    printf '%s' "${XDG_RUNTIME_DIR:-/tmp}"
}

# port_lock_release_all: removes every lock this runner took (pid equal to its own), from its one EXIT trap.
port_lock_release_all() {
    local dir
    for dir in "$(_port_lock_root)"/sensors-port-*.lock; do
        if [ -d "$dir" ] && [ "$(cat "$dir/pid" 2>/dev/null || true)" = "$$" ] && mv -T "$dir" "$dir.released.$$" 2>/dev/null; then
            rm -rf "$dir.released.$$"
        fi
    done
    return 0
}

# port_lock_take <port> <runner>: holds <port> until port_lock_release_all, or exits 1 naming the live holder.
port_lock_take() {
    local port="${1:-}" runner="${2:-}" root dir pid attempt
    root="$(_port_lock_root)"
    if [[ ! "$port" =~ ^[1-9][0-9]{0,4}$ ]] || [ "$port" -gt 65535 ] || [ -z "$runner" ]; then
        echo "error: port_lock_take <port> <runner> needs a port 1-65535 and a runner name, not '$port' '$runner'" >&2
        exit 2
    fi
    if [ ! -d "$root" ] || [ ! -w "$root" ]; then
        echo "error: port_lock_take: the lock root $root is not a writable directory" >&2
        exit 2
    fi
    dir="$root/sensors-port-$port.lock"
    # @tunable runner.port_lock_attempts = 10
    for attempt in 1 2 3 4 5 6 7 8 9 10; do
        if mkdir "$dir" 2>/dev/null; then
            if { printf '%s\n' "$runner" >"$dir/runner" && printf '%s\n' "$$" >"$dir/pid"; } 2>/dev/null && [ "$(cat "$dir/pid" 2>/dev/null)" = "$$" ]; then
                _port_lock_has "$port" "${SENSORS_PORT_LOCKS_HELD:-}" || SENSORS_PORT_LOCKS_HELD="${SENSORS_PORT_LOCKS_HELD:+$SENSORS_PORT_LOCKS_HELD }$port"
                _port_lock_has "$$" "${SENSORS_PORT_LOCK_OWNER:-}" || SENSORS_PORT_LOCK_OWNER="${SENSORS_PORT_LOCK_OWNER:+$SENSORS_PORT_LOCK_OWNER }$$"
                export SENSORS_PORT_LOCKS_HELD SENSORS_PORT_LOCK_OWNER
                return 0
            fi
            continue
        fi
        pid="$(_port_lock_pid "$dir")"
        if _port_lock_alive "$pid"; then
            if [ "$pid" = "$$" ] || { _port_lock_has "$pid" "${SENSORS_PORT_LOCK_OWNER:-}" && _port_lock_has "$port" "${SENSORS_PORT_LOCKS_HELD:-}"; }; then
                return 0
            fi
            echo "port $port is held by $(cat "$dir/runner" 2>/dev/null || echo "an unnamed runner") (pid $pid) - run the suites one after the other (CLAUDE.md)" >&2
            exit 1
        fi
        if [ -d "$dir" ]; then
            _port_lock_clear_stale "$dir"
        fi
    done
    echo "port $port: its lock $dir could not be taken in $attempt attempts - if no runner holds the port, remove that directory" >&2
    exit 1
}
