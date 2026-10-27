#!/bin/bash
# mc_tier.sh: the whole unit tier at -1 and 32768 on S/wt-u35tier against the private toolchain S/tc-int.
R=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u35/lead/run.sh
$R /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/wt-u35tier tier_m1 "export PICO_TOOLCHAIN_DIR=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/tc-int; scripts/test.sh"
$R /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/wt-u35tier tier_32768 "export PICO_TOOLCHAIN_DIR=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/tc-int GC_THRESHOLD=32768; scripts/test.sh"
