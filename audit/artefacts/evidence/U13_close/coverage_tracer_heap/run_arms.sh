#!/bin/bash
cd /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/wt-u13int
U=/root/pico-toolchain/micropython/ports/unix
MP="build/generated_src:src:tests:frozen_modules:.frozen"
one() { # name bin args...
  local name=$1; shift
  echo "== $name $(date +%T)"
  unshare -n bash -c "ip link set lo up; TZ=UTC MICROPYPATH=$MP timeout 600 $* 2>&1" | grep -E "PROBE|PASS test_|FAIL test_|Error|passed," | cut -c1-300
}
for i in 1 2 3; do
  one old_runner $U/build-settrace/micropython -X heapsize=16M /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u13cov_probe/_probe_runner.py tests/_probe_drift.py /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u13cov_probe/old_$i.json
  one new_runner $U/build-settrace/micropython -X heapsize=16M tests/_coverage_runner.py tests/_probe_drift.py /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u13cov_probe/new_$i.json
  one settrace_notracer $U/build-settrace/micropython -X heapsize=16M tests/_probe_drift.py
done
one standard $U/build-standard/micropython -X heapsize=16M tests/_probe_drift.py
echo "done $(date +%T)"
