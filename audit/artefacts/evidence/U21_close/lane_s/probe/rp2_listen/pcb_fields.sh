#!/usr/bin/env bash
set -euo pipefail
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad
B=$S/u21tc-s/micropython/ports/rp2/build-listenprobe
P=$S/u21/s_probe/rp2_listen
args="$(grep -E '^C_DEFINES = |^C_INCLUDES = |^C_FLAGS = ' $B/CMakeFiles/firmware.dir/flags.make | sed 's/^[A-Z_]* = //' | tr '\n' ' ')"
eval arm-none-eabi-gcc $args -c $P/pcb_fields.c -o $P/pcb_fields.o
arm-none-eabi-nm -S $P/pcb_fields.o | python3 -c 'import sys; [print(p[3][7:-6], int(p[1], 16) - 1) for p in (l.split() for l in sys.stdin) if len(p) == 4]' | sort -k2 -n
