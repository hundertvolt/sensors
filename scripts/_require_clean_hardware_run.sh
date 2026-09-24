#!/usr/bin/env bash
# Shared helper for run_flash_hardware_suite.sh/run_bench_hardware_suite.sh: runs pytest with the
# given args and requires a genuinely clean result - zero failures, and zero skips beyond the
# deliberate classes below. Why an exit code cannot do this: tests_hardware/README.md.
set -uo pipefail  # deliberately not -e: the verdict comes from pytest's own output, not its exit code

# The one permanent skip: off-subnet source-address spoofing on the bench host is unconfirmed (that
# test's own skip reason has it). Add a name here only for an equally deliberate, documented,
# permanent skip - never to silence a real one.
KNOWN_PERMANENT_SKIPS=("test_spoofed_off_subnet_source_address_is_ignored")

# The opt-in gates (tests_hardware/conftest.py's pytest_addoption()) are an EXPECTED skip only while
# their own flag is absent from this invocation - so each is whitelisted contextually below. Flag
# passed and still skipped is a real failure.
allow_flash_cycle=0
soak_tier=0
allow_multi_day_rollover=0
allow_neopixel_sweep=0
for arg in "$@"; do
    [ "$arg" = "--allow-flash-cycle" ] && allow_flash_cycle=1
    [ "$arg" = "--soak-tier" ] && soak_tier=1
    [ "$arg" = "--allow-multi-day-rollover-wait" ] && allow_multi_day_rollover=1
    [ "$arg" = "--allow-neopixel-sweep" ] && allow_neopixel_sweep=1
done
if [ "$allow_flash_cycle" = 0 ]; then
    KNOWN_PERMANENT_SKIPS+=("test_real_uf2_reflash_and_boot_smoke_test")
fi
if [ "$soak_tier" = 0 ]; then
    KNOWN_PERMANENT_SKIPS+=(
        "test_real_hardware_memory_does_not_leak_under_real_http_soak_traffic"
        "test_real_hardware_survives_extended_max_speed_hammer_load_with_fram_diagnostics_preserved"
        "test_single_core_timing_headroom_holds_under_normal_full_task_load"
        "test_scd30_real_clock_stretch_never_exceeds_the_configured_timeout"
    )
fi
if [ "$allow_multi_day_rollover" = 0 ]; then
    KNOWN_PERMANENT_SKIPS+=("test_ticks_ms_real_2pow30_rollover")
fi
# The two NeoPixel-rig light programs are gated on a PHYSICAL rig rather than on wear or wall clock
# - without it they fail outright rather than mis-measure (tests_hardware/README.md's "NeoPixel
# sweep rig"). Same contextual rule as the gates above.
if [ "$allow_neopixel_sweep" = 0 ]; then
    KNOWN_PERMANENT_SKIPS+=(
        "test_isl29125_mechanism_envelope_holds_across_range_resolution_and_calibration"
        "test_isl29125_survives_recombined_realistic_lighting_scenarios"
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

# [1-9][0-9]* rather than [0-9]+: a literal "0 passed" must not satisfy a check whose entire job is
# refusing a vacuous run. pytest omits the word entirely today, so this is defensive, not observed.
if ! grep -qE '[1-9][0-9]* passed' "$logfile"; then
    echo "" >&2
    echo "FAILED: zero real passes - real hardware is expected to be attached and reachable for this run." >&2
    exit 1
fi

# Deselected tests are invisible to every check above (see the header's own note), so the verdict
# names them rather than implying everything ran. pytest prints the count in its own summary line.
deselected="$(grep -oE '[0-9]+ deselected' "$logfile" | tail -1)"
echo ""
if [ -n "$deselected" ]; then
    echo "OK: real-hardware suite run clean - no unexpected skips, no failures."
    echo "    NOTE: $deselected by an opt-in gate and therefore never executed - this run does NOT"
    echo "    cover them. Add --allow-persistence-writes (and/or the other --allow-* flags) to."
else
    echo "OK: real-hardware suite run clean - no unexpected skips, no failures, nothing deselected."
fi
