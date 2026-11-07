#!/bin/bash
# gate.sh: bfix's gate under the heavy lock: both GC stages of scripts/test.sh, then dev's twin suite and harness at both.
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad
W=$S/wt-bfix
while [ -e /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u35/lead/heavy.lock ]; do sleep 20; done
echo "bfix" > /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u35/lead/heavy.lock
$S/u35/lead/run.sh $W bfix_gate_e "PICO_TOOLCHAIN_DIR=$S/tc-int scripts/test.sh"
$S/u35/lead/run.sh $W bfix_gate_f "PICO_TOOLCHAIN_DIR=$S/tc-int GC_THRESHOLD=32768 scripts/test.sh"
for g in -1 32768; do
  for part in suite harness; do
    $S/u35/lead/run.sh $W "bfix_twin_${g}_${part}" "PICO_TOOLCHAIN_DIR=$S/tc-int scripts/run_digital_twin_ci.sh dev --gc-threshold $g --part $part"
  done
done
rm /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u35/lead/heavy.lock
echo "gate done $(date -u +%H:%M:%S)"
