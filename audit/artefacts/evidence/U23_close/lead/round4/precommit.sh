#!/bin/bash
# precommit.sh <tag>: wt-u23L pre-commit checks, sequential, nice 19: ruff (8 scopes), npm lint/typecheck,
# lint-ceilings.test.js (own netns), and the pytest pre-commit set plus the files reading the touched JS (own netns).
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad; O=$S/u23/round4/pc_$1; V=/home/user/sensors/.venv/bin
mkdir -p "$O"; cd $S/wt-u23L || exit 2
export PATH=/root/pico-toolchain/node/node-v24.21.0-linux-x64/bin:$PATH
r() { local tag=$1; shift; local t0=$(date +%s); "$@" > "$O/$tag.log" 2>&1; echo "$tag rc=$? $(( $(date +%s) - t0 ))s" >> "$O/summary.txt"; }
: > "$O/summary.txt"
r ruff nice -n 19 $V/ruff check src tests digital_twin tests_hardware buildgen scripts toolchain tests_scripts
r npm_lint nice -n 19 npm run lint
r npm_typecheck nice -n 19 npm run typecheck
r vt_lint-ceilings unshare -n $S/u22/api5/ns.sh nice -n 19 npx vitest run tests_js/lint-ceilings.test.js
F=""
for f in test_decision_vocabulary test_citations test_comment_block_cap test_tunables_register test_legacy_paths test_import_placement test_code_conventions test_error_catalog test_host_annotations test_lint_ceilings test_mypy_any_baseline test_memory_error_gate_agreement test_request_timeout_ceiling test_live_command_device_args test_live_twin_ceiling_parser test_website_layering test_api_reference test_js_api_mirrors; do F="$F tests_scripts/$f.py"; done
r pytest unshare -n $S/u22/api5/ns.sh env PYTHONPATH=scripts TZ=UTC nice -n 19 $V/python -m pytest -q -p no:cacheprovider $F
echo done >> "$O/summary.txt"
