#!/bin/bash
# precommit_py.sh: common.md's pre-commit pytest set on wt-u23L (no port; PYTHONPATH=scripts, TZ=UTC, nice 19).
cd /tmp/claude-0/-home-user-sensors/185d5b0e-d0ae-57c0-8798-ed52081f7df8/scratchpad/wt-u23L || exit 2
PYTHONPATH=scripts TZ=UTC nice -n 19 /home/user/sensors/.venv/bin/python -m pytest -q -p no:cacheprovider \
  tests_scripts/test_decision_vocabulary.py tests_scripts/test_citations.py tests_scripts/test_comment_block_cap.py \
  tests_scripts/test_tunables_register.py tests_scripts/test_legacy_paths.py tests_scripts/test_import_placement.py \
  tests_scripts/test_code_conventions.py tests_scripts/test_error_catalog.py tests_scripts/test_host_annotations.py \
  tests_scripts/test_lint_ceilings.py tests_scripts/test_mypy_any_baseline.py tests_scripts/test_memory_error_gate_agreement.py
