#!/bin/bash
# mut.sh <overlay_dir> <device> names...  (gc-1; the overlay's modules shadow build/generated_src and src)
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad
ov=$1; shift
cd $S/wt-u20i
unshare -n bash -c "ip link set lo up; TZ=UTC MICROPYPATH='$ov:build/generated_src:src:tests:frozen_modules:.frozen' nice -n 19 timeout 900 /root/pico-toolchain/micropython/ports/unix/build-standard/micropython -X heapsize=16M $S/u20i_runs/probe_scripts/pick.py $*" 2>&1 | grep -E '^(PASS|FAIL|[0-9]+/[0-9]+ passed)|Error'
