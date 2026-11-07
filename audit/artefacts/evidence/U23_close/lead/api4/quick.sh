#!/bin/bash
# quick.sh: the lead's quick checks on the API base (wt-u23api): ruff (8 scopes), mypy (4 runs, cold cache), npm lint
# and typecheck, then the wave-1 browser and unit files one at a time in their own netns. Sequential, nice 19.
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad; O=$S/u23/api4; V=/home/user/sensors/.venv/bin
cd $S/wt-u23api || exit 2
export PATH=/root/pico-toolchain/node/node-v24.21.0-linux-x64/bin:$PATH
r() { local tag=$1; shift; "$@" > "$O/$tag.log" 2>&1; echo "$tag rc=$?" >> "$O/summary.txt"; }
: > "$O/summary.txt"
r ruff nice -n 19 $V/ruff check src tests digital_twin tests_hardware buildgen scripts toolchain tests_scripts
ln -sfn $S/wt-u8/typings typings
r mypy_noargs nice -n 19 $V/mypy --cache-dir=/dev/null
r mypy_ci nice -n 19 $V/mypy --cache-dir=/dev/null src tests tests_hardware/device_scripts
r mypy_twin nice -n 19 $V/mypy --cache-dir=/dev/null --config-file digital_twin/typecheck.ini digital_twin $(ls tests/test_digital_twin_*.py)
r mypy_host nice -n 19 $V/mypy --cache-dir=/dev/null --config-file host_typecheck.ini
rm typings
r npm_lint nice -n 19 npm run lint
r npm_typecheck nice -n 19 npm run typecheck
r lint_html nice -n 19 npm run lint:html
r lint_css nice -n 19 npm run lint:css
for f in definitions definitions-shape-corpus source-constants mock-server mock-server-put-matrix generated-definitions-render mock-data-compose definitions-mockdata-coverage app templates render lint-ceilings main api-reference-agreement nav poll-manager shell accessibility site-functions expected-display memory-markers; do
  r vt_$f unshare -n $S/u22/api5/ns.sh nice -n 19 npx vitest run tests_js/$f.test.js
done
echo done >> "$O/summary.txt"
