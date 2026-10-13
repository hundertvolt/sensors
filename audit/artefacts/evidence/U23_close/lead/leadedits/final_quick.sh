#!/bin/bash
# final_quick.sh: the hand-back checks on wt-u23L, sequential, nice 19: rebuild, ruff (8 scopes), mypy x4 (cold cache,
# temporary typings symlink), npm lint/typecheck, the four named pytest files. Results in leadedits/final_*.
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad; O=$S/u23/leadedits; V=/home/user/sensors/.venv/bin
cd $S/wt-u23L || exit 2
export PATH=/root/pico-toolchain/node/node-v24.21.0-linux-x64/bin:$PATH
r() { local tag=$1; shift; "$@" > "$O/final_$tag.log" 2>&1; echo "$tag rc=$?" >> "$O/final_summary.txt"; }
: > "$O/final_summary.txt"
r rebuild $S/u23/rebuild.sh $S/wt-u23L
r ruff nice -n 19 $V/ruff check src tests digital_twin tests_hardware buildgen scripts toolchain tests_scripts
ln -sfn $S/wt-u8/typings typings
r mypy_noargs nice -n 19 $V/mypy --cache-dir=/dev/null
r mypy_ci nice -n 19 $V/mypy --cache-dir=/dev/null src tests tests_hardware/device_scripts
r mypy_twin nice -n 19 $V/mypy --cache-dir=/dev/null --config-file digital_twin/typecheck.ini digital_twin $(ls tests/test_digital_twin_*.py)
r mypy_host nice -n 19 $V/mypy --cache-dir=/dev/null --config-file host_typecheck.ini
rm typings
r npm_lint nice -n 19 npm run lint
r npm_typecheck nice -n 19 npm run typecheck
for f in test_website_layering test_js_api_mirrors test_decision_vocabulary test_tunables_register; do
  r $f env PYTHONPATH=scripts TZ=UTC nice -n 19 $V/python -m pytest -q -p no:cacheprovider tests_scripts/$f.py
done
[ -e typings ] && echo "typings left behind" >> "$O/final_summary.txt"
echo done >> "$O/final_summary.txt"
