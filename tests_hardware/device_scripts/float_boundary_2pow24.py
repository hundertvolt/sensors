"""Isolated-driver device script: RP2040's real firmware is MICROPY_FLOAT_IMPL_FLOAT (24-bit
mantissa, SPECIFICATION.md Part F.1) - the Unix-port test rig uses doubles and can't reproduce this.
Targets coerce_numeric()'s int->float path: always accepted, so the real check is lost precision."""

import sys

sys.path.insert(0, "/")  # frozen src/ modules are already importable without this on real firmware;
# kept only for parity with how isolated-driver scripts are documented to work

from config_manager import coerce_numeric  # type: ignore[import-not-found]

failures = []

# Below the boundary: every int up to 2**24 must round-trip exactly through float() on any build.
below = 2**24 - 1
ok, coerced = coerce_numeric(below, float)
if not ok or coerced != float(below):
    failures.append(f"2**24-1 did not round-trip: ok={ok} coerced={coerced!r} != {float(below)!r}")

# At/above the boundary: 2**24+1 is the smallest int a real 24-bit-mantissa float can't represent
# exactly (rounds to 2**24 or 2**24+2). coerce_numeric() always accepts this by design; the real
# assertion is whether the stored value silently lost precision.
above = 2**24 + 1
ok, coerced = coerce_numeric(above, float)
if not ok:
    failures.append(f"coerce_numeric() rejected an int->float coercion it should always accept per its own documented behavior: ok={ok} coerced={coerced!r}")
elif int(coerced) == above:
    # Deliberately not `coerced == float(above)` - float(above) is recomputed on this same
    # single-precision hardware, so it would always match regardless of lost precision.
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
