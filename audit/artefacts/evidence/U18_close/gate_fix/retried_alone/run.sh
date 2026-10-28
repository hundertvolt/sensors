#!/bin/bash
# The three files that passed only on retry at the gate's 32768 stage, run alone at that stage (three at once on
# four cores, nothing else running), each in its own loopback-only netns: their times against the 240 s limit.
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad; O=$S/evidence_stage_u18/gate_fix/retried_alone
cd $S/wt-u8 || exit 2
B=/root/pico-toolchain/micropython/ports/unix/build-standard/micropython
for f in test_sensortask_dev test_uart_comm_hazard test_digital_twin_uart_link; do
  ( s=$(date +%s); unshare -n bash -c "ip link set lo up; TZ=UTC MICROPYPATH=build/generated_src:src:tests:frozen_modules:.frozen timeout 600 $B -X heapsize=16M tests/_threshold_runner.py tests/$f.py 32768" > $O/$f.log 2>&1; rc=$?
    echo "$f rc=$rc $(( $(date +%s) - s ))s $(grep -E 'passed,' $O/$f.log | tail -1) mem=$(grep -cE 'MemoryError|memory allocation failed' $O/$f.log)" >> $O/summary.txt ) &
done; wait
