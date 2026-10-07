"""Isolated-driver device script: RP2040's real firmware is MICROPY_FLOAT_IMPL_FLOAT (24-bit mantissa,
SPECIFICATION.md Part F.1); the Unix-port rig uses doubles and can't reproduce this. Targets
checked_float()'s int->float path: it always takes the value, so the real check is lost precision."""

import sys

sys.path.insert(0, "/")  # frozen src/ modules are already importable without this on real firmware;
# kept only for parity with how isolated-driver scripts are documented to work

import asy_config_manager as cm

_FIELD: "cm.FieldSchema" = ("Probe", "float", 0.0, None, None, None)  # unbounded: only the coercion is under test

failures = []

# Below the boundary: every int up to 2**24 must round-trip exactly through float() on any build.
below = 2**24 - 1
coerced = cm.checked_float(below, _FIELD)
if coerced is None or coerced != float(below):
    failures.append(f"2**24-1 did not round-trip: coerced={coerced!r} != {float(below)!r}")

# At/above the boundary: 2**24+1 is the smallest int a real 24-bit-mantissa float can't represent
# exactly (rounds to 2**24 or 2**24+2). checked_float() always takes it, as documented; the real
# assertion is whether the stored value silently lost precision.
above = 2**24 + 1
coerced = cm.checked_float(above, _FIELD)
if coerced is None:
    failures.append("checked_float() refused an int->float coercion it should always accept per its own documented behavior")
elif int(coerced) == above:
    # Deliberately not `coerced == float(above)` - float(above) is recomputed on this same
    # single-precision hardware, so it would always match regardless of lost precision.
    failures.append(
        f"2**24+1 unexpectedly round-tripped exactly ({coerced!r}) - either this build isn't really "
        "single-precision float, or MicroPython's own int->float conversion is more precise than assumed here",
    )
elif coerced != float(2**24):
    failures.append(f"2**24+1 coerced to an unexpected value {coerced!r}, expected {float(2**24)!r} (round-to-even)")

if failures:
    print(f"RESULT: FAIL {'; '.join(failures)}")
else:
    print("RESULT: PASS single-precision float boundary at 2**24 confirmed on real hardware")
