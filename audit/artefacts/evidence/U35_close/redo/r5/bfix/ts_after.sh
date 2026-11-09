#!/bin/bash
# ts_after.sh: tests_scripts once more after the doc-only change, under the heavy lock.
while [ -e /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u35/lead/heavy.lock ]; do sleep 20; done
echo "bfix" > /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u35/lead/heavy.lock
/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u35/lead/run.sh /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/wt-bfix bfix_ts_after "PICO_TOOLCHAIN_DIR=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/tc-int python -m pytest -p no:cacheprovider -q --no-header tests_scripts 2>&1 | tail -15"
