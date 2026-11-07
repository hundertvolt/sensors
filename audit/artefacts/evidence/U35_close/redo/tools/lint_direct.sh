#!/bin/bash
# lint_direct.sh: scripts/lint.sh's passes run one by one with the shared venv's pinned tools, because lint.sh's venv
# guard accepts only the worktree's own .venv (resolved, so a link does not pass). The generated tree is rebuild.sh's.
[ -c /dev/null ] || exit 9
rc=0
ruff --version; ruff check src tests digital_twin tests_hardware buildgen scripts toolchain tests_scripts build/generated_src || { echo "FAILED ruff"; rc=1; }
shellcheck scripts/*.sh || { echo "FAILED shellcheck"; rc=1; }
actionlint || { echo "FAILED actionlint"; rc=1; }
zizmor --offline .github/ || { echo "FAILED zizmor"; rc=1; }
if grep -rn "type: ignore\[[^]]*method-assign" src/; then echo "FAILED method-assign guard"; rc=1; fi
python3 scripts/_check_gc_collect_sites.py || { echo "FAILED gc sites"; rc=1; }
echo "lint_direct rc=$rc"
exit $rc
