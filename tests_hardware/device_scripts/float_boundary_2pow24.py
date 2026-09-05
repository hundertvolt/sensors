"""Isolated-driver device script for flash-tier candidate A.5: RP2040's real firmware is
MICROPY_FLOAT_IMPL_FLOAT (24-bit mantissa, exact integer range up to 2**24) - SPECIFICATION.md
Part F.1, confirmed against real ports/rp2/mpconfigport.h. The Unix-port test rig is
MICROPY_FLOAT_IMPL_DOUBLE and structurally cannot reproduce this boundary (tests/test_config_manager.py
proves coerce_numeric() exact up to 2**53 there, which says nothing about the stricter real-hardware
2**24 limit). Targets config_manager.coerce_numeric()'s int->float path directly - the one place
this currently matters (see SPECIFICATION.md Part F.1's own note on config_manager.py).

coerce_numeric(value, target_type) -> (ok: bool, converted_value) - a 2-tuple, not a bare value
(confirmed directly against src/config_manager.py's own signature after an earlier draft of this
script got the shape wrong and was caught by a stray `mypy tests_hardware` run - not part of this
project's formal type-check scope, but worth running anyway; see SPECIFICATION.md Part E.6). Its
own int->float branch is documented as a deliberate, always-accepted gap with "No exact-round-trip
check on this direction" - so this script's real assertion isn't "does it get accepted" (it always
does), it's "does the *value* it stores silently lose precision on real single-precision hardware,
where the Unix-port rig's double precision never would".

Run via `mpremote run <this> soft-reset`. Prints "RESULT: PASS ..." or "RESULT: FAIL <reason>"."""

import sys

sys.path.insert(0, "/")  # frozen src/ modules are already importable without this on real firmware;
# kept only for parity with how isolated-driver scripts are documented to work (HARDWARE_TEST_PLAN.md §6.2)

from config_manager import coerce_numeric  # type: ignore[import-not-found]

failures = []

# Below the boundary: every int up to 2**24 must round-trip exactly through float() on any build.
below = 2**24 - 1
ok, coerced = coerce_numeric(below, float)
if not ok or coerced != float(below):
    failures.append(f"2**24-1 did not round-trip: ok={ok} coerced={coerced!r} != {float(below)!r}")

# At/above the boundary: real single-precision float can no longer represent every integer exactly
# - 2**24 + 1 is the smallest int a real 24-bit-mantissa float cannot represent exactly (rounds to
# 2**24 or 2**24+2, both even). coerce_numeric() itself always accepts (ok=True) by design for this
# direction - the interesting assertion is whether the *stored value* silently lost precision, which
# the Unix port's double-precision rig can never reproduce (2**24+1 round-trips exactly there).
above = 2**24 + 1
ok, coerced = coerce_numeric(above, float)
if not ok:
    failures.append(f"coerce_numeric() rejected an int->float coercion it should always accept per its own documented behavior: ok={ok} coerced={coerced!r}")
elif int(coerced) == above:
    # NOTE: deliberately NOT `coerced == float(above)` - float(above) is itself recomputed on this
    # same real single-precision hardware, so it would always equal `coerced` regardless of whether
    # precision was actually lost, making that comparison unable to ever catch anything. Comparing
    # against the exact mathematical int `above` is precision-independent.
    failures.append(
        f"2**24+1 unexpectedly round-tripped exactly ({coerced!r}) - either this build isn't really "
        "single-precision float, or MicroPython's own int->float conversion is more precise than assumed here"
    )
elif coerced != float(2**24):
    failures.append(f"2**24+1 coerced to an unexpected value {coerced!r}, expected {float(2**24)!r} (round-to-even)")

if failures:
    print(f"RESULT: FAIL {'; '.join(failures)}")
else:
    print("RESULT: PASS single-precision float boundary at 2**24 confirmed on real hardware")
