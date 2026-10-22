#!/usr/bin/env bash
# Scratch (lane S): recompile the probe with build-listenprobe's flags, link that build's firmware once
# for its symbol map, print what lies after the listen pool, then remove the build dir.
set -euo pipefail
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad
B=$S/u21tc-s/micropython/ports/rp2/build-listenprobe
P=$S/u21/s_probe/rp2_listen
flags=$B/CMakeFiles/firmware.dir/flags.make
args="$(grep -E '^C_DEFINES = |^C_INCLUDES = |^C_FLAGS = ' $flags | sed 's/^[A-Z_]* = //' | tr '\n' ' ')"
eval arm-none-eabi-gcc $args -c $P/probe.c -o $P/probe.o
arm-none-eabi-nm -S $P/probe.o | python3 -c 'import sys; [print(p[3], "=", int(p[1], 16)) for p in (l.split() for l in sys.stdin) if len(p) == 4 and p[3].startswith("probe_")]' | sort
make -j2 -C $B > $P/firmware_build.log 2>&1
arm-none-eabi-nm -n -S $B/firmware.elf > $P/firmware_symbols.txt
grep -n -A4 "memp_memory_TCP_PCB_LISTEN_base" $P/firmware_symbols.txt
