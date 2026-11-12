#!/bin/bash
# chain.sh: the merged head's checks, one after another: rebuild, lint and mypy, the system-service file, coverage.
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad; L=$S/u35/lead; W=$S/wt-u35int
B=$S/tc-int/micropython/ports/unix/build-standard/micropython
M="TZ=UTC MICROPYPATH=build/generated_src:src:tests:frozen_modules:.frozen"
"$L/run.sh" "$W" b7i_rebuild "$S/u23/rebuild.sh $W" || exit 1
"$L/checks.sh" "$W" b7i "$S/u35r/r1/B7/int/readers.txt" || exit 1
"$L/run.sh" "$W" b7i_sys_m1 "$M $B -X heapsize=16M tests/test_asy_system_service.py" || exit 1
"$L/run.sh" "$W" b7i_sys_32768 "$M $B -X heapsize=16M tests/_threshold_runner.py tests/test_asy_system_service.py 32768" || exit 1
"$L/run.sh" "$W" b7i_cov "$L/mc_cov.sh"
