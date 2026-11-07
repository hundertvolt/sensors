#!/bin/bash
# final.sh: the hand-back checks on wt-u23L, sequential, nice 19: rebuild, ruff (8 scopes), npm lint/typecheck, nine
# vitest files and test_tunables_register (own netns each), then live-backend.test.js alone (waits for <=4 heavy).
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad; O=$S/u23/lead2/final; V=/home/user/sensors/.venv/bin
mkdir -p "$O"; cd $S/wt-u23L || exit 2
export PATH=/root/pico-toolchain/node/node-v24.21.0-linux-x64/bin:$PATH
r() { local tag=$1; shift; local t0=$(date +%s); "$@" > "$O/$tag.log" 2>&1; echo "$tag rc=$? $(( $(date +%s) - t0 ))s" >> "$O/summary.txt"; }
: > "$O/summary.txt"
r rebuild $S/u23/rebuild.sh $S/wt-u23L
r ruff nice -n 19 $V/ruff check src tests digital_twin tests_hardware buildgen scripts toolchain tests_scripts
r npm_lint nice -n 19 npm run lint
r npm_typecheck nice -n 19 npm run typecheck
for f in render poll-manager shell main app generated-definitions-render site-functions templates accessibility; do
  r vt_$f unshare -n $S/u22/api5/ns.sh nice -n 19 npx vitest run tests_js/$f.test.js
done
r tunables unshare -n $S/u22/api5/ns.sh env PYTHONPATH=scripts TZ=UTC nice -n 19 $V/python -m pytest -q -p no:cacheprovider tests_scripts/test_tunables_register.py
while [ "$($S/u23/lead2/heavy.sh | head -1 | cut -d= -f2)" -gt 4 ]; do sleep 5; done
r live_backend unshare -n $S/u22/api5/ns.sh nice -n 19 npx vitest run tests_js/live-backend.test.js
echo done >> "$O/summary.txt"
