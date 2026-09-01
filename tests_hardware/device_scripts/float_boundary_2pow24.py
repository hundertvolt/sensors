"""Isolated-driver device script for flash-tier candidate A.5: RP2040's real firmware is
MICROPY_FLOAT_IMPL_FLOAT (24-bit mantissa, exact integer range up to 2**24) - SPECIFICATION.md
Part F.1, confirmed against real ports/rp2/mpconfigport.h. The Unix-port test rig is
MICROPY_FLOAT_IMPL_DOUBLE and structurally cannot reproduce this boundary (tests/test_config_manager.py
proves coerce_numeric() exact up to 2**53 there, which says nothing about the stricter real-hardware
2**24 limit). Targets config_manager.coerce_numeric()'s int->float path directly - the one place
this currently matters (see SPECIFICATION.md Part F.1's own note on config_manager.py).
Run via `mpremote run <this> soft-reset`. Prints "RESULT: PASS ..." or "RESULT: FAIL <reason>"."""

import sys

sys.path.insert(0, "/")  # frozen src/ modules are already importable without this on real firmware;
# kept only for parity with how isolated-driver scripts are documented to work (HARDWARE_TEST_PLAN.md §6.2)

from config_manager import coerce_numeric  # type: ignore[import-not-found]

failures = []

# Below the boundary: every int up to 2**24 must round-trip exactly through float().
below = 2**24 - 1
if coerce_numeric(below, float) != float(below):
    failures.append(f"2**24-1 did not round-trip: {coerce_numeric(below, float)!r} != {float(below)!r}")

# At/above the boundary: real single-precision float can no longer represent every integer exactly
# - 2**24 + 1 is the smallest int that a real 24-bit-mantissa float cannot represent exactly
# (rounds to 2**24 or 2**24+2, both even). This is the exact case the Unix port's double-precision
# rig can never reproduce (2**24+1 round-trips exactly under double precision).
above = 2**24 + 1
coerced = coerce_numeric(above, float)
if coerced == float(above):
    failures.append(
        f"2**24+1 unexpectedly round-tripped exactly ({coerced!r}) - either this build isn't really "
        "single-precision float, or MicroPython's own int->float conversion is more precise than assumed here"
    )

if failures:
    print(f"RESULT: FAIL {'; '.join(failures)}")
else:
    print("RESULT: PASS single-precision float boundary at 2**24 confirmed on real hardware")
