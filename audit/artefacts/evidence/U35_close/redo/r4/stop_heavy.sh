#!/bin/bash
# stop_heavy.sh: the stop unit's heavy checks on wt-stop, one at a time, each under the heavy slot (taken when absent,
# released after): the scenario tier for arzi and dev at each GC stage, dev's twin CI suite at each, tests_scripts whole.
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad
L="$S/u35/lead"
W="$S/wt-stop"
O="$S/stop_runs"
MP="$S/tc-int/micropython/ports/unix/build-standard/micropython"
mkdir -p "$O"

heavy() {
    local label="$1" cmd="$2"
    while [ -e "$L/heavy.lock" ]; do sleep 20; done
    echo "stop $label $(date -u +%H:%M:%S)" > "$L/heavy.lock"
    "$L/run.sh" "$W" "$label" "$cmd"
    rm "$L/heavy.lock"
}

for stage in -1 32768; do
    tag=${stage/-/m}
    heavy "stop_scen_$tag" "for d in arzi dev; do timeout 2555 uv run --no-sync scripts/_digital_twin_scenarios.py --device \$d --micropython-bin $MP --logs-dir $O/scen_${tag}_\$d --gc-threshold $stage --shared-port-53 --run-record $O/scen_${tag}_\$d.json; echo \"SCEN \$d stage=$stage rc=\$?\"; done"
done
for stage in -1 32768; do
    tag=${stage/-/m}
    heavy "stop_ci_$tag" "export PICO_TOOLCHAIN_DIR=$S/tc-int; for part in suite harness; do scripts/run_digital_twin_ci.sh dev --gc-threshold $stage --part \$part; echo \"CI dev stage=$stage part=\$part rc=\$?\"; done"
done
heavy stop_tier "PICO_TOOLCHAIN_DIR=$S/tc-int timeout 2400 python -m pytest tests_scripts -q -p no:cacheprovider; echo \"TIER rc=\$?\""
echo "stop_heavy done $(date -u +%H:%M:%S)"
