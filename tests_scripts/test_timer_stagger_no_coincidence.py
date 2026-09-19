"""Host-CPython proof of WP7's read-trigger no-coincidence claim (SPECIFICATION.md Part C.9.1):
replicates system_service.py's stagger arithmetic exactly, never importing MicroPython-target code,
and confirms no two software-counter-driven sensors coincide for any whole-second periods."""

import math

_TIMER_BASE_PERIOD_MS = 1000  # system_service.py's own _TIMER_BASE_PERIOD


def _stagger_offsets(n: int) -> "list[int]":
    # An exact replica of _timer_sequencer()'s arithmetic - a fixed delay between each of the n
    # timer starts - rather than the real recursive implementation, which needs a machine.Timer
    # and asyncio context this CPython-native file deliberately never touches.
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
    # The fact the whole no-coincidence proof rests on (Part C.9.1): every real period being a
    # whole-second multiple makes every pairwise gcd one too, so two reads can coincide only if
    # the offsets match modulo 1000ms - which, offsets living in [0, 1000), is distinctness.
    for n in range(1, 12):
        offsets = _stagger_offsets(n)
        residues = [o % _TIMER_BASE_PERIOD_MS for o in offsets]
        assert len(set(residues)) == n, f"n={n}: offsets collide modulo 1000ms - {offsets!r}"


def _read_times(offset_ms: int, period_s: int, horizon_ms: int) -> "set[int]":
    period_ms = period_s * 1000
    return set(range(offset_ms, horizon_ms, period_ms))


def test_no_two_sensors_ever_share_a_read_time_for_a_realistic_period_combination() -> None:
    # A concrete simulation rather than the symbolic argument above: five sensors, more than any
    # real device wires, sampling the declared trigger_sec range over a multi-hour horizon. A
    # regressed stagger formula - a rounding change, a dropped "+1" - lands back on 1000ms here.
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
    # The case the mod-argument states most sharply: gcd(p, p) is p itself, so offsets must be
    # distinct mod p, not only mod 1000ms. Verified rather than assumed, since p > 1000ms makes
    # that look like the weaker requirement while the proof still has to cover it.
    for n in range(2, 7):
        offsets = _stagger_offsets(n)
        for period_s in (1, 2, 5, 3600):
            for i in range(n):
                for j in range(i + 1, n):
                    assert (offsets[i] - offsets[j]) % (period_s * 1000) != 0, f"n={n} period={period_s}s offsets[{i}]={offsets[i]} offsets[{j}]={offsets[j]}"


def test_gcd_of_any_two_whole_second_periods_is_itself_a_whole_second_multiple() -> None:
    # The premise's other half, checked independently of the stagger arithmetic: every real
    # trigger_sec is a whole number of seconds, and gcd distributes over a common scalar factor,
    # so any pairwise gcd is itself a multiple of 1000ms.
    for a in range(1, 30):
        for b in range(1, 30):
            assert math.gcd(1000 * a, 1000 * b) == 1000 * math.gcd(a, b)
