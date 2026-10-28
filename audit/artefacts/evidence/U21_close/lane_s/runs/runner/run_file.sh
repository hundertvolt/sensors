#!/usr/bin/env bash
# Scratch: scripts/test.sh's own _flag_memory_errors() and run_test_file(), extracted, on the lwIP file and build-lwip.
set -euo pipefail
cd "$1"
results_dir="$2"; coverage=0; micropython_bin=/nonexistent/standard; max_attempts=3; per_file_timeout_s=240
declare -A per_file_timeout_overrides_s=()
eval "$(sed -n '/^_flag_memory_errors() {/,/^}/p;/^run_test_file() {/,/^}/p' scripts/test.sh)"
run_test_file tests/lwip_host/test_modlwip_eagain.py "$results_dir/test_modlwip_eagain.status" "$3"
