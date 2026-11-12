#!/bin/bash
# t.sh GC MODULE [NAME...]: one MicroPython test file (or the named tests of it) at GC stage e (-1) or f (32768).
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad
MP=$S/tc-int/micropython/ports/unix/build-standard/micropython
gc=$1; mod=$2; shift 2
export TZ=UTC MICROPYPATH=build/generated_src:src:tests:frozen_modules:.frozen
if [ $# -gt 0 ]; then
  if [ "$gc" = f ]; then echo "named tests run at stage e only"; exit 2; fi
  exec "$MP" -X heapsize=16M "$S/u35r/r5/uartq/only.py" "$mod" "$@"
fi
if [ "$gc" = f ]; then exec "$MP" -X heapsize=16M tests/_threshold_runner.py "tests/$mod.py" 32768; fi
exec "$MP" -X heapsize=16M "tests/$mod.py"
