#!/bin/bash
# pk_tier.sh: waits for the heavy slot, takes it, runs the tests_scripts tier whole on wt-pk, then releases it.
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad
L="$S/u35/lead"
while [ -e "$L/heavy.lock" ]; do sleep 20; done
echo "pk tests_scripts tier $(date -u +%H:%M:%S)" > "$L/heavy.lock"
"$L/run.sh" "$S/wt-pk" pk_tier "PICO_TOOLCHAIN_DIR=$S/tc-int timeout 2400 python -m pytest tests_scripts -q -p no:cacheprovider"
rc=$?
rm "$L/heavy.lock"
echo "pk_tier done rc=$rc $(date -u +%H:%M:%S)"
