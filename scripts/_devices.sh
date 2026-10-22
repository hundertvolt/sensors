#!/usr/bin/env bash
# Sourced: the derived device set for the shell runners, the rule tests_scripts/_devices.py states for Python - every
# devices/*.toml stem but the reserved zz_test_ fixtures, in byte order. derived_devices lists it; require_device NAME
# exits 2 naming the valid devices unless NAME is one of them.
(return 0 2>/dev/null) || { echo "error: source scripts/_devices.sh, do not run it" >&2; exit 2; }

_devices_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/devices"

# derived_devices: one device per line, sorted as Python sorts the stems; fails when there is none.
derived_devices() {
    local toml name found=()
    for toml in "$_devices_dir"/*.toml; do
        [ -e "$toml" ] || continue
        name="${toml##*/}"
        name="${name%.toml}"
        if [[ "$name" != zz_test_* ]]; then
            found+=("$name")
        fi
    done
    if [ "${#found[@]}" -eq 0 ]; then
        echo "error: no devices/*.toml found" >&2
        return 1
    fi
    printf '%s\n' "${found[@]}" | LC_ALL=C sort
}

# require_device NAME: returns when NAME is a derived device, else exits 2 listing the valid ones.
require_device() {
    local name="${1:-}" devices
    devices="$(derived_devices)" || devices=""
    case $'\n'"$devices"$'\n' in
        *$'\n'"$name"$'\n'*)
            [ -n "$name" ] && return 0
            ;;
    esac
    echo "error: no devices/$name.toml - valid devices: ${devices//$'\n'/ }" >&2
    exit 2
}
