#!/bin/bash
# Runs the whole exposure sweep sequentially (one interpreter at a time - no synthetic host load).
WT=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/wt-u11rc
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u11rc
MP=/root/pico-toolchain/micropython/ports/unix/build-standard/micropython
cd "$WT" || exit 1
sweep() {  # file D stride substr out
    echo "== start $5 $(date +%T)"
    TZ=UTC MICROPYPATH="build/generated_src:src:tests:frozen_modules:.frozen" timeout 7000 "$MP" -X heapsize=16M "$S/exposure_sweep.py" "$1" "$2" 100000 "$3" "$4" > "$S/logs/$5" 2>&1
    echo "== end $5 rc=$? $(date +%T)"
}
sweep "$S/orig/test_uart_comm_hazard.py" 40 0 _nocrc exposure_hazard_nocrc_D40.log
sweep tests/test_asy_uart_comm.py 110 -60 - exposure_asy_uart_comm_D110.log
sweep tests/test_asy_uart_link_driver.py 110 -60 - exposure_asy_uart_link_driver_D110.log
sweep tests/test_asy_uart_driver.py 210 -40 - exposure_asy_uart_driver_D210.log
sweep "$S/orig/test_uart_comm_hazard.py" 250 -40 _crc16 exposure_hazard_crc16_D250.log
echo ALLDONE
