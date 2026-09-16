"""Host-CPython proof of WP7's own read-trigger no-coincidence claim (SPECIFICATION.md Part
C.9.1): replicates system_service.py's own stagger arithmetic exactly (never imports/executes
MicroPython-target code) and confirms, empirically and for the general case, that no two
software-counter-driven sensors' read times ever coincide for any combination of whole-second
periods."""

import math

_TIMER_BASE_PERIOD_MS = 1000  # system_service.py's own _TIMER_BASE_PERIOD


def _stagger_offsets(n: int) -> "list[int]":
    # Exact replica of SystemService._timer_sequencer()'s own arithmetic: a fixed delay of
    # _TIMER_BASE_PERIOD // (n + 1) between each of the n timer starts, so offsets are
    # 0, delay, 2*delay, ..., (n-1)*delay - never system_service.py's own real recursive
    # implementation, since that requires a real machine.Timer/asyncio context this file
    # deliberately never touches (CPython-native, per the project's own testing philosophy).
    if n <= 0:
        return []
    delay = _TIMER_BASE_PERIOD_MS // (n + 1)
    return [i * delay for i in range(n)]


def test_stagger_offsets_are_pairwise_distinct_and_strictly_within_one_second() -> None:
    for n in range(1, 12):  # far beyond any real device's own timer-starter count
        offsets = _stagger_offsets(n)
        assert len(set(offsets)) == n, f"n={n}: duplicate stagger offsets {offsets!r}"
        assert all(0 <= o < _TIMER_BASE_PERIOD_MS for o in offsets), f"n={n}: an offset left [0, 1000) - {offsets!r}"


def test_offsets_are_pairwise_distinct_modulo_one_second() -> None:
    # The one fact the whole no-coincidence proof rests on (SPECIFICATION.md Part C.9.1): since
    # every real period is a whole-second multiple, gcd(period_i, period_j) is always itself a
    # multiple of 1000ms - so two read times can only ever coincide if the two sensors' own
    # stagger offsets are equal modulo 1000ms. Offsets already live in [0, 1000), so this is the
    # same fact as the plain distinctness above, checked as its own explicit claim.
    for n in range(1, 12):
        offsets = _stagger_offsets(n)
        residues = [o % _TIMER_BASE_PERIOD_MS for o in offsets]
        assert len(set(residues)) == n, f"n={n}: offsets collide modulo 1000ms - {offsets!r}"


def _read_times(offset_ms: int, period_s: int, horizon_ms: int) -> "set[int]":
    period_ms = period_s * 1000
    return set(range(offset_ms, horizon_ms, period_ms))


def test_no_two_sensors_ever_share_a_read_time_for_a_realistic_period_combination() -> None:
    # A concrete simulation, not just the symbolic argument above: 5 sensors (more than any real
    # device wires today), assigned every distinct period from asy_bmp3xx_driver.py's own real
    # "@limits trigger_sec 1..3600" range that a 5-way split can sample, over a multi-hour horizon
    # far longer than any of their own periods - if the stagger formula ever regressed (a rounding
    # change, a dropped "+1"), this is what would catch it landing back on a multiple of 1000ms.
    offsets = _stagger_offsets(5)
    periods_s = [1, 2, 3, 7, 3600]  # includes the two schema extremes and three arbitrary values
    horizon_ms = 4 * 3600 * 1000  # four hours - many multiples of even the longest configured period
    all_times: dict[int, int] = {}  # read time -> which sensor index already claimed it
    for i, (offset, period) in enumerate(zip(offsets, periods_s, strict=True)):
        for t in _read_times(offset, period, horizon_ms):
            assert t not in all_times, f"sensor {i} (offset={offset}, period={period}s) collides with sensor {all_times.get(t)} at t={t}ms"
            all_times[t] = i


def test_no_coincidence_holds_for_every_pairwise_period_combination_up_to_ten_seconds() -> None:
    # Exhaustive over the short end of the range (where a beat-frequency collision would be most
    # likely to surface soonest in real operation) rather than one hand-picked combination: every
    # pair of distinct periods from 1..10s, at every stagger position pairing for up to 6 sensors.
    horizon_ms = 120 * 1000  # 120s covers at least 12 full cycles of even the slowest period here
    for n in range(2, 7):
        offsets = _stagger_offsets(n)
        for i in range(n):
            for j in range(i + 1, n):
                for period_i in range(1, 11):
                    for period_j in range(1, 11):
                        if period_i == period_j:
                            continue  # two sensors sharing a period is a separate, allowed case below
                        times_i = _read_times(offsets[i], period_i, horizon_ms)
                        times_j = _read_times(offsets[j], period_j, horizon_ms)
                        assert not (times_i & times_j), (
                            f"n={n} offsets[{i}]={offsets[i]} period={period_i}s vs "
                            f"offsets[{j}]={offsets[j]} period={period_j}s collide"
                        )


def test_two_sensors_sharing_the_identical_period_never_coincide_either() -> None:
    # The one case the mod-argument above states most sharply: gcd(p, p) = p itself, so distinct
    # offsets mod p (not just mod 1000ms) must hold - verified directly rather than assumed, since
    # p > 1000ms makes "mod p" a strictly weaker-looking requirement than "mod 1000ms" that the
    # proof still has to cover.
    for n in range(2, 7):
        offsets = _stagger_offsets(n)
        for period_s in (1, 2, 5, 3600):
            for i in range(n):
                for j in range(i + 1, n):
                    assert (offsets[i] - offsets[j]) % (period_s * 1000) != 0, f"n={n} period={period_s}s offsets[{i}]={offsets[i]} offsets[{j}]={offsets[j]}"


def test_gcd_of_any_two_whole_second_periods_is_itself_a_whole_second_multiple() -> None:
    # The other half of the proof's premise, checked independently of the stagger arithmetic:
    # every real trigger_sec is a whole number of seconds (asy_bmp3xx_driver.py's own "@limits
    # trigger_sec 1..3600"), and gcd distributes over a common scalar factor, so gcd(1000*a,
    # 1000*b) == 1000*gcd(a, b) - always itself a multiple of 1000ms.
    for a in range(1, 30):
        for b in range(1, 30):
            assert math.gcd(1000 * a, 1000 * b) == 1000 * math.gcd(a, b)
