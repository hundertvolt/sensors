#!/usr/bin/env bash
# Shared helper for run_flash_hardware_suite.sh/run_bench_hardware_suite.sh: runs pytest with the
# given args and requires the result to be genuinely clean - zero failures, and zero skips beyond
# the one currently-known, deliberate, permanent exception below. tests_hardware/'s own fixtures
# skip cleanly (never error) when real hardware isn't reachable, by design (see README.md's own
# "collectible with nothing attached at all" requirement for a no-hardware collection pass) - but
# that same design makes a run against genuinely UNREACHABLE hardware look identical, at the
# exit-code level, to a real clean run (pytest exits 0 for an all-skipped run too, same as an
# all-passed one). These two wrapper scripts exist specifically to run against real, attached
# hardware, so that ambiguity must never pass through silently here - every expected test must show
# PASSED, not quietly skip or fail. (`pytest tests_hardware --collect-only`, the genuinely
# no-hardware-attached case, bypasses this file entirely - it's a plain manual invocation, not run
# through either wrapper script.) The two opt-in-gated categories (--allow-flash-cycle/
# --run-long-soak, tests_hardware/conftest.py) are handled contextually below, not just whitelisted
# outright - their own tests skipping is only acceptable when the matching flag was genuinely
# omitted from this invocation; passing the flag and still getting a skip is a real failure.
set -uo pipefail  # deliberately not -e: this script inspects pytest's own output before deciding its own exit code

# The one currently-known, deliberate, permanent skip: raw-socket off-subnet-source-address
# spoofing feasibility on the bench host isn't confirmed yet (see that test's own skip reason in
# tests_hardware/bench/test_hotspot_role_reversal.py). Add a new name here only for an equally
# deliberate, documented, permanent skip - never to silence a real, unexpected one.
KNOWN_PERMANENT_SKIPS=("test_spoofed_off_subnet_source_address_is_ignored")

# The two opt-in gates (tests_hardware/conftest.py's own pytest_addoption()) are, by design, an
# EXPECTED skip whenever their own flag isn't passed - only add their own tests to the acceptable
# list when the corresponding flag is genuinely absent from this invocation's own args; if the flag
# WAS passed and one of these still skipped, that's a real, unexpected problem and must still fail.
allow_flash_cycle=0
run_long_soak=0
for arg in "$@"; do
    [ "$arg" = "--allow-flash-cycle" ] && allow_flash_cycle=1
    [ "$arg" = "--run-long-soak" ] && run_long_soak=1
done
if [ "$allow_flash_cycle" = 0 ]; then
    KNOWN_PERMANENT_SKIPS+=("test_real_uf2_reflash_and_boot_smoke_test")
fi
if [ "$run_long_soak" = 0 ]; then
    KNOWN_PERMANENT_SKIPS+=(
        "test_real_hardware_memory_does_not_leak_under_real_http_soak_traffic"
        "test_single_core_timing_headroom_holds_under_normal_full_task_load"
        "test_scd30_real_clock_stretch_never_exceeds_the_configured_timeout"
        "test_ticks_ms_real_2pow30_rollover"
    )
fi

logfile="$(mktemp)"
trap 'rm -f "$logfile"' EXIT

uv run pytest "$@" -v 2>&1 | tee "$logfile"
pytest_exit="${PIPESTATUS[0]}"

if [ "$pytest_exit" != "0" ]; then
    echo "" >&2
    echo "FAILED: pytest exited $pytest_exit - see output above." >&2
    exit "$pytest_exit"
fi

# --collect-only never actually runs anything - the skip/pass accounting below doesn't apply.
for arg in "$@"; do
    if [ "$arg" = "--collect-only" ]; then
        exit 0
    fi
done

unexpected_skips=""
while IFS= read -r line; do
    known=0
    for name in "${KNOWN_PERMANENT_SKIPS[@]}"; do
        case "$line" in
            *"$name"*) known=1 ;;
        esac
    done
    if [ "$known" = 0 ]; then
        unexpected_skips="$unexpected_skips$line"$'\n'
    fi
done < <(grep -oE '^tests_hardware/\S+ SKIPPED' "$logfile" | sed -E 's/ SKIPPED$//')

if [ -n "$unexpected_skips" ]; then
    echo "" >&2
    echo "FAILED: unexpected test skip(s) - real hardware is expected to be attached and reachable" >&2
    echo "for this whole run; every expected test must PASS, not silently skip (this almost always" >&2
    echo "means the board/bridge became unreachable partway through, not that these tests genuinely" >&2
    echo "don't apply here):" >&2
    echo "$unexpected_skips" >&2
    exit 1
fi

if ! grep -qE '[0-9]+ passed' "$logfile"; then
    echo "" >&2
    echo "FAILED: zero real passes - real hardware is expected to be attached and reachable for this run." >&2
    exit 1
fi

echo ""
echo "OK: real-hardware suite run clean - no unexpected skips, no failures."
