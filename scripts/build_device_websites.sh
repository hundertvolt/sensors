#!/usr/bin/env bash
# Builds every derived device's website (each devices/*.toml except the zz_test_ fixtures) through
# scripts/build_website.sh into <out_root>/<device>/frozen_html.py; stops at the first failure, naming that device.
#
# Usage: scripts/build_device_websites.sh [out_root]   (default out_root: build/generated_html)
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

out_root="${1:-build/generated_html}"
device=""
trap 'status=$?; if (( status != 0 )) && [[ -n "$device" ]]; then echo "error: the website build for device $device failed" >&2; fi' EXIT

for toml in devices/*.toml; do
    device="$(basename "$toml" .toml)"
    if [[ "$device" == zz_test_* ]]; then
        continue
    fi
    scripts/build_website.sh "$device" "$out_root/$device/frozen_html.py"
done
device=""
