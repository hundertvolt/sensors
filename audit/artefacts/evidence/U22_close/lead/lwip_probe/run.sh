#!/bin/bash
# run.sh <rounds> <threshold> <out>: one probe run in wt-u8 (read-only), its own network namespace.
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad
cd "$S/wt-u8" || exit 2
TZ=UTC MICROPYPATH="tests/lwip_host:tests:src:.frozen" timeout 180 unshare -n /root/pico-toolchain/micropython/ports/unix/build-lwip/micropython -X heapsize=16M "$S/u22/lwip_probe/probe.py" "$1" "$2" > "$3" 2>&1
echo "rc=$?" >> "$3"
