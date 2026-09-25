#!/usr/bin/env bash
# Runs tests_hardware/flash/ against a real board over mpremote (SPECIFICATION.md Part E.6), passing
# through any extra pytest args. Provisioning: tests_hardware/README.md.
#
# Goes through _require_clean_hardware_run.sh, because a plain exit code cannot see an unexpected
# skip (that script's own header has the reasoning), and excludes the soak markers unconditionally -
# they need their own deliberate invocation even if a caller passes their flag by mistake.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

scripts/_require_clean_hardware_run.sh tests_hardware/flash -m "not long_soak and not multi_day_rollover" "$@"
