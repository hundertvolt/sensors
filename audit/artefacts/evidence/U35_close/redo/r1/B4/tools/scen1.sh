#!/bin/bash
# The scenario jobs at GC -1 for the devices the continuation's parallel launch lost to the port-53 lock: one lock
# held here, as scripts/test.sh holds it, the jobs in parallel beneath it on a shared port 53.
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad
export PICO_TOOLCHAIN_DIR=$S/tc-int
MP=$S/tc-int/micropython/ports/unix/build-standard/micropython
source scripts/_port_lock.sh
trap port_lock_release_all EXIT
port_lock_take 53 b4_scen1
rc=0
for d in "$@"; do
    uv run --no-sync scripts/_digital_twin_scenarios.py --device "$d" --micropython-bin "$MP" --logs-dir "$S/b4work/scen1/$d" --gc-threshold -1 --shared-port-53 > "$S/b4work/scen1_$d.log" 2>&1 &
done
for d in "$@"; do wait -n || rc=1; done
for d in "$@"; do echo "== $d: $(grep -E '^Counts' $S/b4work/scen1_$d.log)"; grep -h 'FAILED' $S/b4work/scen1_$d.log; done
exit $rc
