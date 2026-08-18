"""Step 6 (BACKLOG.md open question #6, "ticks_ms()/ticks_diff() rollover" category): direct,
real-interpreter verification of MicroPython's time.ticks_ms()/time.ticks_diff()/time.ticks_add()
wraparound arithmetic.

Every real src/ ticks_ms()/ticks_diff() use site (asy_bmp3xx_driver.py's _wait_status_bits(),
asy_notification_service.py's _next_sleep_secs(), asy_uart_driver.py's ready(),
asy_udp_socket.py's ready()) was directly read for this audit: all four share the identical
bounded-short-timeout shape (`t0 = time.ticks_ms()` once; loop; `time.ticks_diff(time.ticks_ms(),
t0)` compared against a millisecond-or-low-second `timeout_ms`) - no raw `now - t0` subtraction
anywhere, and no timeout value anywhere near the correctness window ticks_diff() guarantees (half
of the platform's own ticks period). No code fix was needed in src/ for this category; this file
is the "check, don't just look" regression evidence for that conclusion.

**A real, confirmed Unix-port-testing-scope gap, found while writing this file (same class of
finding as BACKLOG.md open question #5's UDP/NTP Unix-port quirk - a genuine platform difference,
not a bug):** the real RP2040 target's time.ticks_ms() rolls over every `2**30` ms (~12.4 days) -
confirmed directly against the pinned v1.28.0 source, py/mpconfig.h's
`MICROPY_PY_TIME_TICKS_PERIOD = MP_SMALL_INT_POSITIVE_MASK + 1`, which resolves per
py/smallint.h's MICROPY_OBJ_REPR_A formula to `2**30` on rp2's 32-bit machine word. **This
project's own MicroPython Unix-port test rig (`ports/unix`'s "standard" build, what scripts/
test.sh actually runs everything under) has a *different* period - confirmed empirically against
the real built binary (bisection: a time.ticks_add() delta of `2**60` succeeds, `2**61` raises
OverflowError), consistent with the same MICROPY_OBJ_REPR_A formula evaluated for a 64-bit machine
word instead: `2**62`.** Neither ports/rp2/mpconfigport.h nor ports/unix/mpconfigport.h overrides
MICROPY_OBJ_REPR/MICROPY_PY_TIME_TICKS_PERIOD - the difference is purely the host word size the
shared py/mpconfig.h formula is compiled against. **Net effect: the real RP2040-specific
2**30/~12.4-day boundary cannot be empirically exercised under this project's own Unix-port test
rig at all** - a synthetic ticks-space value built via time.ticks_add() wraps at *this rig's*
2**62 boundary, not rp2's 2**30 one, and time.ticks_ms() itself cannot be monkeypatched to fake a
value near the real boundary (see below). Confidence that real rp2 hardware behaves correctly
rests on code identity, not empirical measurement at the real boundary: ticks_diff()/ticks_add()
are one shared, period-parametric C implementation (extmod/modtime.c) used unchanged by every
port, with only the compiled-in period constant differing - the tests below empirically prove that
shared implementation's wraparound math is correct at *this build's own* period boundary, which by
code identity (not by re-measurement) implies the same correctness at rp2's differently-valued
boundary. Positively confirming the literal 2**30 point would need either real rp2 hardware left
running past a real ~12.4-day boundary, or a custom-built Unix-port variant compiled with a 32-bit
object representation to force period=2**30 here too - both out of proportion to what this audit
category needs beyond the code-identity argument above; flagged for the project owner rather than
pursued further.

time.ticks_ms() itself cannot be monkeypatched to force a real call site through a live wraparound
under test - confirmed directly against py/objmodule.c: a builtin C module's globals dict is built
via MP_DEFINE_CONST_DICT (map.is_fixed = 1), and mp_obj_module_t's store-attribute path explicitly
rejects storing to a fixed map for every module except `builtins` (MICROPY_CAN_OVERRIDE_BUILTINS's
special-cased override dict, which `time` doesn't get) - unlike a plain `.py`-sourced module (e.g.
tests/test_captive_dns.py's `captive_dns_module.DNSQuery = ...`), whose globals dict is an
ordinary, mutable Python dict. This is why every test below is built entirely from
time.ticks_add()/time.ticks_diff() with synthetic values, never by trying to control what a live
time.ticks_ms() call returns - the same technique test_asy_notification_service.py's own
pre-existing test_next_sleep_secs_floors_at_point_one_... test already uses
(time.ticks_add(time.ticks_ms(), -100000)), just pushed all the way to this rig's own period
boundary instead of an ordinary elapsed-time offset.

**A confirmed gap in the third-party micropython-rp2-rpi_pico_w-stubs package** (same class of
finding as CLAUDE.md's already-documented bare-Timer()/I2C.deinit() stub gaps): `typings/time.pyi`
types `ticks_add()`'s first parameter as the opaque `_Ticks` TypeVar (bound only to `_TicksMs`/
`_TicksUs`/`_TicksCPU`, deliberately excluding plain `int` to catch raw-arithmetic misuse
elsewhere - a real, useful feature this stub package added), but the stub's *own* docstring
demonstrates `ticks_add(0, -1)` as the canonical way to discover a port's own tick period - a
literal `int`, which its declared signature cannot actually accept. This file needs exactly that
pattern (seeding wraparound-boundary values from a known `0`, not from a real `time.ticks_ms()`
reading, for reproducible test values) - `# type: ignore[type-var]` on each seeding call, not a
restructure around the gap, matching this project's established policy of flagging (not silently
routing around) third-party stub gaps.
"""

import time


# This Unix-port test rig's own ticks period, confirmed empirically (see module docstring) - NOT
# the real RP2040 target's 2**30. Derived here via bisection rather than hardcoded, so a future
# MicroPython/toolchain change that alters it (e.g. a different unix build variant) fails loudly
# instead of silently testing the wrong boundary.
def _discover_this_rigs_ticks_period() -> int:
    # time.ticks_add()'s own accepted-delta range is exactly [-period/2, period/2) (confirmed
    # against extmod/modtime.c) - bisect for the largest accepted positive delta (period/2 - 1)
    # rather than assuming a delta of "the whole period" is itself valid to pass (it isn't - see
    # the self-consistency test below, which hit exactly this while this file was being written).
    lo, hi = 1, 1 << 63  # largest accepted delta is in (lo, hi)
    while lo + 1 < hi:
        mid = (lo + hi) // 2
        try:
            time.ticks_add(0, mid)  # type: ignore[type-var]  # stub gap, see module docstring
            lo = mid
        except OverflowError:
            hi = mid
    return 2 * (lo + 1)  # lo == period//2 - 1


_THIS_RIGS_TICKS_PERIOD = _discover_this_rigs_ticks_period()


def test_this_rigs_ticks_period_is_self_consistent() -> None:
    # Re-derives the exact accepted/rejected boundary independently of the bisection above, as a
    # direct check on the discovered period rather than trusting the bisection's own arithmetic.
    half = _THIS_RIGS_TICKS_PERIOD // 2
    assert time.ticks_add(0, half - 1) == half - 1  # type: ignore[type-var]  # stub gap, see docstring
    try:
        time.ticks_add(0, half)  # type: ignore[type-var]  # stub gap, see module docstring
        raise AssertionError("expected OverflowError for a delta of exactly period/2")
    except OverflowError:
        pass


def test_ticks_diff_correct_when_now_has_wrapped_past_t0() -> None:
    # t0 sits just before this rig's own wraparound; "now" is a small, real elapsed time later,
    # having wrapped around to a small raw value near zero. A raw subtraction (now - t0) would
    # compute a huge negative number (~ -period) here instead of the true small positive elapsed
    # time. Built entirely via time.ticks_add() (never a raw literal near the period boundary -
    # see module docstring for why an unwrapped literal there gives ticks_diff() an out-of-domain
    # input and garbage results).
    t0 = time.ticks_add(0, -50)  # type: ignore[type-var]  # raw value: period - 50, just before the wrap
    now = time.ticks_add(t0, 200)  # type: ignore[type-var]  # 200ms later, having wrapped past zero
    assert time.ticks_diff(now, t0) == 200


def test_ticks_diff_correct_when_t0_has_wrapped_past_now() -> None:
    # The symmetric case, exercised right at the boundary itself: t0's raw value is small (just
    # after the wrap), "now" is a raw value just before that same wrap - representing "not quite
    # elapsed yet" rather than "a full period minus a bit has elapsed".
    t0 = time.ticks_add(0, 5)  # type: ignore[type-var]  # just after the wrap, see module docstring
    now = time.ticks_add(0, -50)  # type: ignore[type-var]  # period - 50, just before the same wrap
    assert time.ticks_diff(now, t0) == -55  # -50 - 5, not a huge bogus swing


def test_ticks_diff_matches_plain_subtraction_away_from_any_wrap() -> None:
    # Sanity check on the harness itself: far from the boundary, ticks_diff() must agree with
    # plain subtraction - proves the two wrap tests above are actually exercising wrap-specific
    # behavior, not some unrelated ticks_diff() quirk that would also show up here.
    t0 = _THIS_RIGS_TICKS_PERIOD // 2
    now = t0 + 300
    assert time.ticks_diff(now, t0) == 300


def test_ticks_diff_timeout_comparison_correct_across_a_wrap() -> None:
    # The exact expression every real src/ use site evaluates
    # (time.ticks_diff(now, t0) >= timeout_ms), driven straight through the wraparound boundary -
    # proves the *comparison*, not just the raw diff value, comes out right on both sides of a
    # real timeout threshold.
    t0 = time.ticks_add(0, -50)  # type: ignore[type-var]  # just before the wrap, see module docstring
    now_at_150ms = time.ticks_add(t0, 150)  # type: ignore[type-var]
    assert time.ticks_diff(now_at_150ms, t0) >= 100  # timeout already elapsed
    assert not (time.ticks_diff(now_at_150ms, t0) >= 200)  # timeout not yet elapsed


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
