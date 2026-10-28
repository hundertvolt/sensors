#!/bin/bash
# pre-commit checks for lane K
SP=/tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad
cd $SP/wt-u18k || exit 9
V=/home/user/sensors/.venv/bin
echo "== pytest whole-tree checks"
nice -n 19 $V/python -m pytest -q -p no:cacheprovider tests_scripts/test_decision_vocabulary.py tests_scripts/test_citations.py tests_scripts/test_comment_block_cap.py tests_scripts/test_tunables_register.py tests_scripts/test_legacy_paths.py tests_scripts/test_import_placement.py tests_scripts/test_code_conventions.py 2>&1 | tail -15
echo "== ruff"
$V/ruff check src/asy_print_log.py tests/test_asy_print_log.py src/asy_base_classes.py tests/test_asy_base_classes.py src/asy_webserver_service.py
echo "== mypy main (no args)"
ln -sfn $SP/wt-u8/typings typings
nice -n 19 $V/mypy --cache-dir=/dev/null 2>&1 | tail -3
echo "== mypy main (src tests tests_hardware/device_scripts)"
nice -n 19 $V/mypy --cache-dir=/dev/null src tests tests_hardware/device_scripts 2>&1 | tail -3
rm typings
git status --short
