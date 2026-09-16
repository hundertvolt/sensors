#!/usr/bin/env bash
# The full GC-policy matrix on real hardware (SPECIFICATION.md Part I.6): builds, flashes and runs
# each pass in turn, ending with the shipped build back on the board.
#
#   pass 1  reactive               full bench suite       the vital bar - no proactive collection
#   pass 2  reactive + pressure    -m memory_pressure     the same design with the heap made scarce
#   pass 3  threshold              full bench suite       the shipped defense in depth, still clean
#
# Pass 1 is the one that must hold: a threshold is additive margin on an already-safe design, never
# the reason something passes (CLAUDE.md's memory-safety discipline, Part I.4(e)/(f)). Pass 3 runs
# last so the bench is left on the firmware it normally carries.
#
# Spends no SCD30 NVM writes, and needs no flag of its own to say so: every real SCD30 write now
# sits behind conftest.py's --allow-scd30-writes, which is off by default. This script runs the full
# suite twice, so that default is what keeps the sensor's finite write-wear budget untouched here.
#
# THIS FLASHES THE BOARD THREE TIMES. That is the point of the script, but it is not a routine
# action - it needs the project owner's go-ahead like everything else in this tier, plus
# --allow-flash-cycles here so it can never happen as a side effect of running some other suite.
#
# Usage: scripts/run_bench_gc_matrix.sh --allow-flash-cycles [extra pytest args]
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

if [ "${1:-}" != "--allow-flash-cycles" ]; then
    echo "Usage: $0 --allow-flash-cycles [extra pytest args]" >&2
    echo "This script flashes the attached dev board three times - pass the flag deliberately." >&2
    exit 2
fi
shift

echo "=============================================================================="
echo "== Pass 1/3: reactive GC, full bench suite (the vital bar)"
echo "=============================================================================="
uv run scripts/flash_dev_firmware.py --gc-policy reactive
scripts/run_bench_hardware_suite.sh --expect-gc-policy reactive "$@"

echo "=============================================================================="
echo "== Pass 2/3: reactive GC + allocator churn, pressure tests only"
echo "=============================================================================="
uv run scripts/flash_dev_firmware.py --gc-policy reactive --memory-pressure
scripts/_require_clean_hardware_run.sh tests_hardware/flash tests_hardware/bench \
    -m "memory_pressure and not long_soak and not multi_day_rollover" --expect-gc-policy reactive "$@"

echo "=============================================================================="
echo "== Pass 3/3: threshold GC (what ships), full bench suite"
echo "=============================================================================="
uv run scripts/flash_dev_firmware.py --gc-policy threshold
scripts/run_bench_hardware_suite.sh --expect-gc-policy threshold "$@"

echo ""
echo "OK: the whole GC-policy matrix passed - reactive, reactive+pressure, and threshold."
