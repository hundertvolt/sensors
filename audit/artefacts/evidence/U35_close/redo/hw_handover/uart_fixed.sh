#!/bin/bash
# uart_fixed.sh: the mounted UART scripts again (2026-10-29) with the driver's DMA stop fixed (_rx_stop: unchain, then abort),
# real watchdog; one hard reset after each.
set -uo pipefail
H=$(cd "$(dirname "$0")" && pwd)
L=$H/logs
DAY=$(date -u +%Y%m%d)
MPC=scripts/mpremote_connect.sh
MNT=$PWD/build/mountstage/mpy
D=build/device_scripts
LOG=$L/uart_fixed_$DAY.log
up() { for _ in $(seq 1 90); do timeout 15 $MPC exec "print('up')" >/dev/null 2>&1 && return 0; sleep 1; done; return 1; }
up || exit 1
for s in uart_idle_poll_rate uart_crossover_recovery_none uart_crossover_recovery_crc16 uart_dma_ring_interrupts_off_none \
    uart_dma_ring_interrupts_off_crc16 uart_crossover_exchange_none uart_comm_hazards_crc16 uart_dma_ring_interrupts_off_none_break; do
  echo "### $s $(date -u +%H:%M:%S)" >> "$LOG"
  timeout 600 $MPC mount "$MNT" run "$D/$s.py" >> "$LOG" 2>&1
  echo "rc=$? $(date -u +%H:%M:%S)" >> "$LOG"
  timeout 15 $MPC exec "import machine; print('SUM uart_fixed reset_cause', machine.reset_cause())" >> "$LOG" 2>&1
  timeout 15 $MPC reset >/dev/null 2>&1; sleep 3; up
done
python3 "$H/handback.py" "$L" "$H/HANDBACK.md" "$DAY"
