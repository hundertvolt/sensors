#!/bin/bash
while [ -e /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u35/lead/heavy.lock ]; do sleep 20; done
echo "r5c tests_scripts $(date -u +%H:%M:%S)" > /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u35/lead/heavy.lock
/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u35/lead/run.sh /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/wt-r5c r5c_tests_scripts "PICO_TOOLCHAIN_DIR=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/tc-int python -m pytest -p no:cacheprovider -q --no-header tests_scripts 2>&1 | tail -40"
rm /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u35/lead/heavy.lock
