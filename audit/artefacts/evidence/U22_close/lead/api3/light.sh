#!/usr/bin/env bash
# Lead light checks on wt-u22api @ the integration head (W, P, T finals): regen, website, ruff (lint.sh's 8 scopes), mypy x4, L0.
S=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad; W=$S/wt-u22api; O=$S/u22/api3; V=/home/user/sensors/.venv/bin
cd "$W" || exit 1
[ -e typings ] || ln -s $S/wt-u8/typings typings
r() { local n=$1; shift; local t0=$(date +%s.%N); "$@" > "$O/$n.log" 2>&1; local rc=$?; printf '%s rc=%s %.1fs %s\n' "$n" "$rc" "$(echo "$(date +%s.%N) - $t0" | bc)" "$(tail -1 "$O/$n.log" | cut -c1-120)" >> "$O/summary.txt"; }
: > "$O/summary.txt"
r regen nice -n 19 $V/python scripts/_generate_sensortask_modules.py
r site_wozi nice -n 19 scripts/build_website.sh wozi
r site_devices nice -n 19 scripts/build_device_websites.sh
r ruff nice -n 19 $V/ruff check src tests digital_twin tests_hardware buildgen scripts toolchain tests_scripts
r mypy_noargs nice -n 19 $V/mypy --cache-dir=/dev/null
r mypy_ci nice -n 19 $V/mypy --cache-dir=/dev/null src tests tests_hardware/device_scripts
r mypy_twin nice -n 19 $V/mypy --cache-dir=/dev/null --config-file digital_twin/typecheck.ini digital_twin tests/test_digital_twin_*.py
r mypy_host nice -n 19 $V/mypy --cache-dir=/dev/null --config-file host_typecheck.ini
r collect_hw nice -n 19 $V/python -m pytest -q -p no:cacheprovider --collect-only tests_hardware
for f in test_buildgen_definitions test_error_catalog test_mypy_any_baseline test_citations test_decision_vocabulary test_comment_block_cap test_code_conventions test_tunables_register test_memory_error_gate_agreement test_lint_ceilings test_host_annotations test_import_placement test_legacy_paths test_fault_or_warning_never_both test_level_containment test_persistence_write_marker_completeness; do
  r "py_$f" env PYTHONPATH=scripts nice -n 19 $V/python -m pytest -q -p no:cacheprovider "tests_scripts/$f.py"
done
rm -f typings
echo DONE >> "$O/summary.txt"
