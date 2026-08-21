"""Direct, real-interpreter verification of MicroPython's time.ticks_ms()/time.ticks_diff()/time.ticks_add() wraparound arithmetic - see SPECIFICATION.md Part F.1 for the full rollover facts (rp2's 2**30 vs. this Unix-port rig's 2**62 period, and why time.ticks_ms() can't be monkeypatched).
Every real src/ ticks_ms()/ticks_diff() use site was directly read for this audit: all share the same bounded-short-timeout shape, no raw `now - t0` subtraction anywhere. Built entirely from synthetic time.ticks_add()/ticks_diff() values, never a live time.ticks_ms() reading."""

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
            # Stub gap: typings/time.pyi types ticks_add()'s first param as the opaque _Ticks
            # TypeVar (excludes plain int), but the stub's own docstring demonstrates ticks_add(0,
            # -1) - a literal int - as the canonical way to discover a port's tick period. Confirmed
            # gap, flagged per this project's policy rather than routed around - hence the ignore.
            time.ticks_add(0, mid)  # type: ignore[type-var]
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
