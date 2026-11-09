#!/bin/bash
# bchain's gate: the plain and GC-stage unit tiers, then dev's twin suite and harness at both GC stages, one after another.
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad
W=$S/wt-bchain
TC="PICO_TOOLCHAIN_DIR=$S/tc-int"
R=$S/u35/lead/run.sh
$R $W bchain_gate_e "$TC scripts/test.sh"
$R $W bchain_gate_f "$TC GC_THRESHOLD=32768 scripts/test.sh"
for gc in -1 32768; do
    for part in suite harness; do
        $R $W "bchain_twin_${gc}_${part}" "$TC scripts/run_digital_twin_ci.sh dev --gc-threshold $gc --part $part"
    done
done
echo "bchain gate done $(date -u +%T)"
