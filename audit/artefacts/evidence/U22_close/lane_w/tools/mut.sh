#!/bin/bash
# mut.sh <label> <python-replace-script> <tests...>: copies src/asy_wifi_service.py, applies the mutation, runs the tests.
set -u
SP=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad
WT=$SP/wt-u22w
label=$1; shift; mutation=$1; shift
dir=$SP/u22w_runs/mut/$label
rm -rf "$dir"; mkdir -p "$dir"
python3 - "$WT/src/asy_wifi_service.py" "$dir/asy_wifi_service.py" "$mutation" <<'PY'
import sys
src, dst, spec = sys.argv[1:4]
s = open(src).read()
old, new = spec.split("=>>", 1)
old = old.encode().decode("unicode_escape"); new = new.encode().decode("unicode_escape")
assert s.count(old) == 1, ("mutation site count", s.count(old))
open(dst, "w").write(s.replace(old, new))
PY
cd "$WT" && unshare -n bash -c "ip link set lo up; TZ=UTC MICROPYPATH='$dir:build/generated_src:src:tests:frozen_modules:.frozen' nice -n 19 timeout 300 /root/pico-toolchain/micropython/ports/unix/build-standard/micropython -X heapsize=16M $SP/u22w_tools/sel_runner.py test_asy_wifi_service $*" > "$dir/run.log" 2>&1
echo "$label rc=$? :: $(grep -E '^(PASS|FAIL)' "$dir/run.log" | tr '\n' ' ')"
