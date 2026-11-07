#!/bin/bash
# checks.sh: ruff (8 scopes), the four cold-cache mypy runs (temporary typings symlink, removed after) and four
# tests_scripts files on wt-u23w, sequential, nice 19; one summary line per check with rc and wall time.
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad; O=$S/u23/of129p; V=/home/user/sensors/.venv/bin
cd $S/wt-u23w || exit 2
r() { local tag=$1; shift; local t0; t0=$(date +%s.%N); "$@" > "$O/logs/chk_$tag.log" 2>&1; local rc=$?
  printf '%s rc=%s %ss\n' "$tag" "$rc" "$(python3 -c "import time; print(f'{time.time() - $t0:.1f}')")" >> "$O/summary.txt"; }
: > "$O/summary.txt"
r ruff nice -n 19 $V/ruff check src tests digital_twin tests_hardware buildgen scripts toolchain tests_scripts
ln -sfn $S/wt-u8/typings typings
r mypy_noargs nice -n 19 $V/mypy --cache-dir=/dev/null
r mypy_ci nice -n 19 $V/mypy --cache-dir=/dev/null src tests tests_hardware/device_scripts
r mypy_twin nice -n 19 $V/mypy --cache-dir=/dev/null --config-file digital_twin/typecheck.ini digital_twin $(ls tests/test_digital_twin_*.py)
r mypy_host nice -n 19 $V/mypy --cache-dir=/dev/null --config-file host_typecheck.ini
rm typings
for f in test_comment_block_cap test_decision_vocabulary test_code_conventions test_error_catalog; do
  r "$f" nice -n 19 $V/python -m pytest -q -p no:cacheprovider "tests_scripts/$f.py"
done
echo done >> "$O/summary.txt"
