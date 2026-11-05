#!/bin/bash
# gate.sh: R0's checks on the integration tree: generated inputs, lint, typecheck, the tests_scripts tier.
bash /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u23/rebuild.sh /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/wt-u35int > /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u35r/r0/gate_rebuild.log 2>&1 || echo "FAILED rebuild"
bash /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u35/lead/lint_direct.sh > /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u35r/r0/gate_lint.log 2>&1 && echo "lint ok" || echo "FAILED lint"
bash scripts/typecheck.sh > /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u35r/r0/gate_typecheck.log 2>&1 && echo "typecheck ok" || echo "FAILED typecheck"
PICO_TOOLCHAIN_DIR=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/tc-int timeout 2400 python -m pytest tests_scripts -q -p no:cacheprovider > /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u35r/r0/gate_pytest.log 2>&1 && echo "pytest ok" || echo "FAILED pytest"
tail -3 /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/u35r/r0/gate_pytest.log
