#!/usr/bin/env bash
# Sourced lock for the product-fixed ports: one runner per port at a time, the holder's descendants pass. A lock is
# flock(2) on ${XDG_RUNTIME_DIR:-/tmp}/sensors-port-<port>.flock, which names its runner and pid; the kernel frees it
# with the last descriptor, so a dead holder's lock is never stale. The chain: SENSORS_PORT_LOCK_OWNER, _LOCKS_HELD.
(return 0 2>/dev/null) || { echo "error: source scripts/_port_lock.sh, do not run it" >&2; exit 2; }

_port_lock_fds=()

_port_lock_has() {
    case " $2 " in
        *" $1 "*) return 0 ;;
    esac
    return 1
}

# port_lock_release_all: closes every lock this runner took, from its one EXIT trap.
port_lock_release_all() {
    local fd
    for fd in "${_port_lock_fds[@]}"; do
        exec {fd}>&-
    done
    _port_lock_fds=()
    return 0
}

# port_lock_take <port> <runner>: holds <port> until port_lock_release_all or this runner's exit, or exits 1 naming the
# holder; the holder itself, and a descendant whose inherited chain lists the holder and the port, pass.
port_lock_take() {
    local port="${1:-}" runner="${2:-}" root file fd holder=()
    root="${XDG_RUNTIME_DIR:-/tmp}"
    if [[ ! "$port" =~ ^[1-9][0-9]{0,4}$ ]] || [ "$port" -gt 65535 ] || [ -z "$runner" ]; then
        echo "error: port_lock_take <port> <runner> needs a port 1-65535 and a runner name, not '$port' '$runner'" >&2
        exit 2
    fi
    file="$root/sensors-port-$port.flock"
    if [ ! -d "$root" ] || [ ! -w "$root" ] || ! { exec {fd}>>"$file"; } 2>/dev/null; then
        echo "error: port_lock_take: the lock root $root is not a writable directory" >&2
        exit 2
    fi
    if ! command -v flock >/dev/null 2>&1; then
        echo "error: flock (util-linux) is not on PATH - scripts/_port_lock.sh holds $file with it" >&2
        exit 2
    fi
    if flock -n "$fd"; then
        # In place, never truncated first, so a refused taker reads the old two lines or the new ones, never none.
        printf '%s\n%s\n' "$runner" "$$" 1<>"$file"
        _port_lock_fds+=("$fd")
        _port_lock_has "$port" "${SENSORS_PORT_LOCKS_HELD:-}" || SENSORS_PORT_LOCKS_HELD="${SENSORS_PORT_LOCKS_HELD:+$SENSORS_PORT_LOCKS_HELD }$port"
        _port_lock_has "$$" "${SENSORS_PORT_LOCK_OWNER:-}" || SENSORS_PORT_LOCK_OWNER="${SENSORS_PORT_LOCK_OWNER:+$SENSORS_PORT_LOCK_OWNER }$$"
        export SENSORS_PORT_LOCKS_HELD SENSORS_PORT_LOCK_OWNER
        return 0
    fi
    exec {fd}>&-
    mapfile -t holder <"$file" 2>/dev/null || true
    if [ "${holder[1]:-}" = "$$" ] || { _port_lock_has "${holder[1]:-}" "${SENSORS_PORT_LOCK_OWNER:-}" && _port_lock_has "$port" "${SENSORS_PORT_LOCKS_HELD:-}"; }; then
        return 0
    fi
    echo "port $port is held by ${holder[0]:-an unnamed runner} (pid ${holder[1]:-unknown}) - run the suites one after the other (CLAUDE.md)" >&2
    exit 1
}
