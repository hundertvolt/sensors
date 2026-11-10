"""NeopixelDriver: the signal ramp and the one lock its requests queue on, the direct overlay write, refused and clamped
values, and no error log."""

import asyncio

import micropython
from _async_harness import cancel_all, run
from _error_codes import code
from _fake_time import DrivenTime
from _fast_sleep import check_sleep_ms
from _recording_print import record_prints
from _src_const import src_const, src_int
from _task_names import task_names_of

import asy_neopixel_driver
from asy_neopixel_driver import NeopixelDriver, _clamp_byte
from asy_print_log import LogConfig
from asy_system_service import SystemService

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing isn't available on the real MicroPython test interpreter
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable

    import neopixel


def _colours(driver: NeopixelDriver) -> "list[tuple[int, ...]]":
    return [w[0] for w in _pixel(driver).writes]


def _driven() -> DrivenTime:
    # The driver module's time and asyncio on one driven clock for the block: every frame, poll and overlay wait parks
    # on it, and time moves only when the test moves it.
    return DrivenTime(asy_neopixel_driver, sleeps=True)


def _event_driver() -> NeopixelDriver:
    return _make_driver(debug=4)  # DebugLevel 4 (events, SPEC A.8): event-level console lines reach record_prints()


def _last_colour_is(driver: NeopixelDriver, colour: "tuple[int, ...]") -> "Callable[[], bool]":
    return lambda: _colours(driver)[-1:] == [colour]


def _make_driver(freq: int = 100, overlay_bri: int = 50, debug: "int | None" = None) -> NeopixelDriver:
    # 100 Hz keeps five frames per ramp direction at the 0.1 s floor, so mid-ramp state is observable; time is driven,
    # not waited.
    return NeopixelDriver(0, neopixel_freq=freq, led_overl_bri=overlay_bri, log=LogConfig(None, 10, debug))


def _pixel(driver: NeopixelDriver) -> "neopixel.NeoPixel":
    # fakes/neopixel.py's fake, reached through the driver's own attribute - that fake is what
    # `neopixel` resolves to here (it is not excluded from mypy, unlike tests/network.py).
    return driver._pixel


def _ramp_ms(t: float, freq: int = 100) -> int:
    # One signal's length on the driven clock: both directions' frames at the frame period, by the driver's own steps
    # rule (_ramp); its final black lands at that instant.
    return 2 * max(int(t * 0.5 * freq), 1) * (1000 // freq)


async def _never_synced() -> bool:
    return False


def _red(colour: "tuple[int, ...]") -> bool:
    return colour[0] > 0 and colour[1] == 0


def _request_frames(driver: NeopixelDriver, rgbt: "tuple[int, int, int, float]", ramp_ms: int) -> "tuple[bool, list[tuple[int, ...]]]":
    # request_signal(*rgbt) with the signal task running: its result, and every frame from the request until its end
    # (the ramp, its final black and the overlay's restore), which comes ramp_ms later.
    async def scenario(clock: DrivenTime) -> "tuple[bool, list[tuple[int, ...]]]":
        tasks = await _start_all_tasks(driver)
        await clock.elapse(0)  # the task's own start frame
        n = len(_pixel(driver).writes)
        request = asyncio.create_task(driver.request_signal(*rgbt))
        assert await clock.run_until(request.done, ramp_ms) == ramp_ms  # it returns at its own ramp's end
        await cancel_all(tasks, settle_yields=1)
        return await request, _colours(driver)[n:]

    with _driven() as clock:
        return run(scenario(clock))


# ---------------------------------------------------------------------------
# Init / logging
# ---------------------------------------------------------------------------


def test_init_bakes_name_into_the_logger() -> None:
    driver = _make_driver()
    assert driver.pr.name == "NEOPIXEL"


def test_the_frame_rate_and_overlay_brightness_default_to_the_module_constants() -> None:
    freq = src_int("src/asy_neopixel_driver.py", "_NEOPIXEL_FREQ_HZ")
    driver = NeopixelDriver(0, log=LogConfig(None, 10, None))
    assert (driver.neopixel_freq, driver._frame_ms, driver._overlay_bri) == (freq, 1000 // freq, src_const("src/asy_neopixel_driver.py", "_LED_OVERL_BRI"))
    assert type(driver._frame_ms) is int  # the frame sleep's own ms value, no float per frame
    custom = NeopixelDriver(0, neopixel_freq=40, led_overl_bri=7, log=LogConfig(None, 10, None))
    assert (custom.neopixel_freq, custom._frame_ms, custom._overlay_bri) == (40, 25, 7)


def test_the_driver_has_no_error_log_and_no_status_entry() -> None:
    # Nothing it does can fail, so its console printer keeps no history, no store and no /status errcount entry.
    driver = _make_driver(debug=2)
    assert type(driver.pr).__name__ == "PrintLog"
    assert driver.pr.level == 2
    assert driver.get_error_sources() == []
    assert driver.get_loggers() == [driver.pr]  # the DebugLevel setter still reaches its event lines
    assert not hasattr(driver, "get_error_counter")
    assert not hasattr(driver, "reset_error_counter")
    assert not hasattr(driver, "setup")  # nothing to set up: buildgen leaves it out of the boot batch


# ---------------------------------------------------------------------------
# Overlay behavior: on, off and toggle
# ---------------------------------------------------------------------------


def test_on_sets_pixel_to_overlay_brightness_and_records_a_write() -> None:
    driver = _make_driver(overlay_bri=42)

    async def scenario(clock: DrivenTime) -> None:
        tasks = await _start_all_tasks(driver)
        await clock.elapse(0)  # the start frames first: only on() itself can then write the overlay
        driver.on()
        assert _pixel(driver).writes[-1][0] == (42, 42, 42)  # on() wrote it at once
        await cancel_all(tasks, settle_yields=1)

    with _driven() as clock:
        run(scenario(clock))
    assert _pixel(driver).writes[-1][0] == (42, 42, 42)


def test_off_sets_pixel_to_black_and_records_a_write() -> None:
    driver = _make_driver(overlay_bri=42)

    async def scenario(clock: DrivenTime) -> None:
        tasks = await _start_all_tasks(driver)
        driver.on()
        await clock.run_until(_last_colour_is(driver, (42, 42, 42)), 0)
        driver.off()
        await clock.elapse(0)
        await cancel_all(tasks, settle_yields=1)

    with _driven() as clock:
        run(scenario(clock))
    assert _pixel(driver).writes[-1][0] == (0, 0, 0)


def test_toggle_flips_from_off_to_on() -> None:
    driver = _make_driver(overlay_bri=42)

    async def scenario(clock: DrivenTime) -> None:
        tasks = await _start_all_tasks(driver)
        await clock.elapse(0)  # the start frames first: only toggle() itself can then write the overlay
        driver.toggle()
        await clock.elapse(0)
        await cancel_all(tasks, settle_yields=1)

    with _driven() as clock:
        run(scenario(clock))
    assert driver._overlay_on is True
    assert _pixel(driver).writes[-1][0] == (42, 42, 42)


def test_toggle_flips_from_on_to_off() -> None:
    driver = _make_driver(overlay_bri=42)

    async def scenario(clock: DrivenTime) -> None:
        tasks = await _start_all_tasks(driver)
        driver.on()
        await clock.run_until(_last_colour_is(driver, (42, 42, 42)), 0)
        driver.toggle()
        await clock.elapse(0)
        await cancel_all(tasks, settle_yields=1)

    with _driven() as clock:
        run(scenario(clock))
    assert driver._overlay_on is False
    assert _pixel(driver).writes[-1][0] == (0, 0, 0)


def test_repeated_on_is_idempotent_no_crash_one_more_write() -> None:
    driver = _make_driver(overlay_bri=42)

    async def scenario(clock: DrivenTime) -> int:
        tasks = await _start_all_tasks(driver)
        driver.on()
        await clock.run_until(_last_colour_is(driver, (42, 42, 42)), 0)
        n_before = len(_pixel(driver).writes)
        driver.on()
        await clock.elapse(0)
        await cancel_all(tasks, settle_yields=1)
        return n_before

    with _driven() as clock:
        n_before = run(scenario(clock))
    assert len(_pixel(driver).writes) == n_before + 1
    assert _pixel(driver).writes[-1][0] == (42, 42, 42)


def test_overlay_write_deferred_while_ramp_holds_the_lock() -> None:
    driver = _make_driver(overlay_bri=99)
    lit = (99, 99, 99)

    async def scenario(clock: DrivenTime) -> "tuple[bool, list[bool]]":
        tasks = await _start_all_tasks(driver)
        tasks.append(asyncio.create_task(_request(driver, 10, 0, 0, 0.1)))
        await clock.run_until(lambda: any(_red(c) for c in _colours(driver)), 0)  # mid-ramp: the ramp holds the lock
        held = driver._led_lock.locked()
        driver.on()  # queued: it must not write while the ramp still holds the lock
        lit_while_held: list[bool] = []

        def released() -> bool:  # at each frame the ramp still holds the lock: is the overlay's colour written?
            if driver._led_lock.locked():
                lit_while_held.append(lit in _colours(driver))
                return False
            return True

        await clock.run_until(released, _ramp_ms(0.1))  # at its end the ramp writes the overlay on() asked for
        await cancel_all(tasks, settle_yields=1)
        return held, lit_while_held

    with _driven() as clock:
        held, lit_while_held = run(scenario(clock))
    assert held is True
    assert lit_while_held, lit_while_held
    assert not any(lit_while_held), lit_while_held
    assert _pixel(driver).writes[-1][0] == lit



# ---------------------------------------------------------------------------
# request_signal() (blocking/internal path)
# ---------------------------------------------------------------------------


def test_request_signal_ramps_up_then_down_and_ends_at_black() -> None:
    accepted, frames = _request_frames(_make_driver(), (50, 60, 70, 0.1), _ramp_ms(0.1))
    assert accepted is True
    assert len(frames) == 2 * 5 + 2, frames  # five frames each way at 100 Hz, the final black, the overlay's restore
    assert frames[4] == (50, 60, 70)  # the peak
    assert frames[:4] == [(10, 12, 14), (20, 24, 28), (30, 36, 42), (40, 48, 56)]  # c * n // steps, exact
    assert frames[-3:] == [(0, 0, 0)] * 3


def test_request_signal_restores_overlay_on_state_after_ramp() -> None:
    driver = _make_driver(overlay_bri=77)

    async def scenario(clock: DrivenTime) -> None:
        tasks = await _start_all_tasks(driver)
        driver.on()
        await clock.run_until(_last_colour_is(driver, (77, 77, 77)), 0)
        request = asyncio.create_task(driver.request_signal(10, 0, 0, 0.1))
        await clock.run_until(request.done, _ramp_ms(0.1))  # with the restore written
        await cancel_all(tasks, settle_yields=1)

    with _driven() as clock:
        run(scenario(clock))
    assert _pixel(driver).writes[-1][0] == (77, 77, 77)


def test_request_signal_restores_overlay_off_state_after_ramp() -> None:
    accepted, frames = _request_frames(_make_driver(overlay_bri=77), (10, 0, 0, 0.1), _ramp_ms(0.1))  # overlay off
    assert accepted is True
    ramp = [(2, 0, 0), (4, 0, 0), (6, 0, 0), (8, 0, 0), (10, 0, 0), (8, 0, 0), (6, 0, 0), (4, 0, 0), (2, 0, 0), (0, 0, 0)]
    assert frames == ramp + [(0, 0, 0), (0, 0, 0)], frames  # the final black, then the overlay's restore of "off"


def test_two_concurrent_request_signal_calls_run_strictly_sequentially() -> None:
    driver = _make_driver()

    async def scenario(clock: DrivenTime) -> None:
        tasks = await _start_all_tasks(driver)
        first = asyncio.create_task(driver.request_signal(10, 0, 0, 0.1))
        second = asyncio.create_task(driver.request_signal(0, 10, 0, 0.1))
        # The second waits on the lock and takes it at the first ramp's end: both end two ramps from now, to the ms.
        assert await clock.run_until(second.done, 2 * _ramp_ms(0.1)) == 2 * _ramp_ms(0.1)
        assert (await first, await second) == (True, True)
        await cancel_all(tasks, settle_yields=1)

    with _driven() as clock:
        run(scenario(clock))
    writes = [w[0] for w in _pixel(driver).writes]
    # A full ramp always ends on (0, 0, 0) before the next one's non-zero frames begin - if the two
    # ramps had interleaved, a red-channel frame and a green-channel frame would appear intermixed
    # instead of in two contiguous blocks each terminated by (0, 0, 0).
    red_frames = [i for i, w in enumerate(writes) if w[0] > 0]
    green_frames = [i for i, w in enumerate(writes) if w[1] > 0]
    assert red_frames and green_frames
    assert max(red_frames) < min(green_frames) or max(green_frames) < min(red_frames)


def test_request_signal_always_returns_true_even_back_to_back() -> None:
    driver = _make_driver()

    async def scenario(clock: DrivenTime) -> "tuple[bool, bool]":
        tasks = await _start_all_tasks(driver)
        first = asyncio.create_task(driver.request_signal(1, 0, 0, 0.1))
        second = asyncio.create_task(driver.request_signal(0, 1, 0, 0.1))
        await clock.run_until(second.done, 2 * _ramp_ms(0.1))  # it plays at the first ramp's end
        r1, r2 = await first, await second
        await cancel_all(tasks, settle_yields=1)
        return r1, r2

    with _driven() as clock:
        assert run(scenario(clock)) == (True, True)
    assert (1, 0, 0) in _colours(driver)
    assert (0, 1, 0) in _colours(driver)  # the second request ran too


def test_request_signal_below_floor_still_produces_at_least_one_step_each_direction() -> None:
    # Below the 0.1 s floor at the shipped rate: one step up to full brightness, one down, the final black, the restore.
    accepted, frames = _request_frames(_make_driver(freq=20), (10, 0, 0, 0.0), _ramp_ms(0.1, 20))
    assert accepted is True
    assert frames == [(10, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0)], frames


def test_request_signal_low_freq_boundary_never_divides_by_zero() -> None:
    # freq=1 with the 0.1s floor: int(0.1 * 0.5 * 1) == 0 without an explicit steps>=1 clamp - a
    # real ZeroDivisionError risk in the original code's steps_inv = 1.0/steps, not just a
    # theoretical one. Regression test for the exact boundary flagged in the promotion plan.
    accepted, frames = _request_frames(_make_driver(freq=1), (10, 0, 0, 0.0), _ramp_ms(0.1, 1))
    assert accepted is True
    assert frames == [(10, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0)], frames  # one 1 s step each way, then black


def test_request_signal_large_t_accepted() -> None:
    accepted, frames = _request_frames(_make_driver(freq=20), (5, 0, 0, 1.0), _ramp_ms(1.0, 20))
    assert accepted is True
    assert len(frames) == 2 * 10 + 2, frames  # ten frames each way at 20 Hz, the final black, the overlay's restore
    assert frames[9] == (5, 0, 0)
    assert frames[-2:] == [(0, 0, 0), (0, 0, 0)]


# ---------------------------------------------------------------------------
# led_signal() (non-blocking/external path)
# ---------------------------------------------------------------------------


def test_led_signal_returns_true_and_eventually_ramps_when_idle() -> None:
    driver = _make_driver()

    async def scenario(clock: DrivenTime) -> bool:
        tasks = await _start_all_tasks(driver)
        result = driver.led_signal(30, 0, 0, 0.1)
        await clock.run_until(lambda: not driver._start_signal_event.is_set(), _ramp_ms(0.1))  # the ramp ran to its end
        await cancel_all(tasks, settle_yields=1)
        return result

    with _driven() as clock:
        assert run(scenario(clock)) is True
    assert (30, 0, 0) in [w[0] for w in _pixel(driver).writes]


def test_led_signal_returns_false_for_a_second_call_before_the_first_dispatches() -> None:
    driver = _make_driver()

    async def scenario() -> "tuple[bool, bool]":
        # No task started: led_signal() decides on _start_signal_event alone, with no await.
        r1 = driver.led_signal(30, 0, 0, 0.1)
        r2 = driver.led_signal(0, 30, 0, 0.1)  # zero `await` since r1 - must already see it pending
        return r1, r2

    r1, r2 = run(scenario())
    assert r1 is True
    assert r2 is False


def test_led_signal_is_refused_at_once_while_a_ramp_runs_and_nothing_is_queued() -> None:
    # An internal ramp holds the lock; an external request meanwhile is refused, never queued (owner, 2026-10-02).
    driver = _event_driver()

    async def scenario(clock: DrivenTime) -> "tuple[bool, bool]":
        tasks = await _start_all_tasks(driver)
        internal = asyncio.create_task(driver.request_signal(10, 0, 0, 0.1))
        await clock.run_until(lambda: any(c[0] > 0 for c in _colours(driver)), 0)
        busy = driver._led_lock.locked()
        result = driver.led_signal(0, 10, 0, 0.1)
        await clock.run_until(internal.done, _ramp_ms(0.1))
        await clock.elapse(_ramp_ms(0.1))  # a queued request would have run a whole ramp by now
        await cancel_all(tasks, settle_yields=1)
        return busy, result

    with _driven() as clock, record_prints() as recorder:
        busy, result = run(scenario(clock))
    assert busy is True
    assert result is False
    assert not any(c[1] > 0 for c in _colours(driver))  # the refused colour never reaches the pixel
    assert ("NEOPIXEL", "External LED command received.") in recorder.lines
    assert ("NEOPIXEL", "External LED command refused: busy, retry later.") in recorder.lines


def test_led_signal_is_refused_while_an_internal_request_waits_its_turn() -> None:
    # External taken, its task not run yet: an internal request queues behind nothing it can see and plays; one
    # more internal request waits on the lock, and an external one is refused until both have ended.
    driver = _make_driver()

    async def scenario(clock: DrivenTime) -> "tuple[bool, bool, bool, bool]":
        first = asyncio.create_task(driver.request_signal(10, 0, 0, 0.1))
        await clock.elapse(0)  # it holds the lock, mid-ramp
        second = asyncio.create_task(driver.request_signal(0, 0, 10, 0.1))
        await clock.elapse(0)  # it waits its turn on the lock
        refused_running = driver.led_signal(0, 10, 0, 0.1)
        await clock.run_until(first.done, _ramp_ms(0.1))
        refused_waiting = driver.led_signal(0, 10, 0, 0.1)  # the second now plays; the first's end freed nothing
        await clock.run_until(second.done, _ramp_ms(0.1))
        tasks = await _start_all_tasks(driver)
        accepted = driver.led_signal(0, 10, 0, 0.1)
        await clock.run_until(lambda: not driver._start_signal_event.is_set(), _ramp_ms(0.1))
        await cancel_all(tasks, settle_yields=1)
        return await first and await second, refused_running, refused_waiting, accepted

    with _driven() as clock:
        assert run(scenario(clock)) == (True, False, False, True)
    colours = _colours(driver)
    red, blue, green = ([i for i, c in enumerate(colours) if c[k] > 0] for k in (0, 2, 1))
    assert max(red) < min(blue) and max(blue) < min(green), colours


def test_led_signal_color_and_duration_pass_through_unmodified() -> None:
    driver = _make_driver()

    async def scenario(clock: DrivenTime) -> None:
        tasks = await _start_all_tasks(driver)
        driver.led_signal(12, 34, 56, 0.1)
        await clock.run_until(lambda: not driver._start_signal_event.is_set(), _ramp_ms(0.1))  # the ramp ran to its end
        await cancel_all(tasks, settle_yields=1)

    with _driven() as clock:
        run(scenario(clock))
    assert (12, 34, 56) in [w[0] for w in _pixel(driver).writes]


def test_led_signal_accepts_fractional_t_without_truncating() -> None:
    # Regression test for the old `t: int` annotation bug - a fractional duration like 1.5 must
    # actually be honored (more steps/longer ramp), not silently truncated to 1.
    driver = _make_driver(freq=20)

    async def scenario(clock: DrivenTime) -> int:
        signal = driver.start_asy_signal()  # the signal task alone: every frame after its start frame is the ramp's
        await clock.elapse(0)
        n = len(_pixel(driver).writes)
        driver.led_signal(10, 0, 0, 1.5)
        await clock.run_until(lambda: not driver._start_signal_event.is_set(), _ramp_ms(1.5, 20))  # the ramp ran to its end
        await cancel_all([signal], settle_yields=1)
        return len(_pixel(driver).writes) - n

    with _driven() as clock:
        n_writes = run(scenario(clock))
    # steps = int(1.5 * 0.5 * 20) = 15 per direction -> 30 ramp frames, the final black, the overlay restore.
    assert n_writes == 32


# ---------------------------------------------------------------------------
# Cross-arbitration
# ---------------------------------------------------------------------------


def test_external_and_internal_requests_back_to_back_both_eventually_run() -> None:
    driver = _make_driver()

    async def scenario(clock: DrivenTime) -> None:
        tasks = await _start_all_tasks(driver)
        driver.led_signal(10, 0, 0, 0.1)
        internal = asyncio.create_task(driver.request_signal(0, 10, 0, 0.1))
        await clock.run_until(lambda: internal.done() and not driver._start_signal_event.is_set(), 2 * _ramp_ms(0.1))
        assert await internal is True  # the internal one took the free lock first; the external one played after it
        await cancel_all(tasks, settle_yields=1)

    with _driven() as clock:
        run(scenario(clock))
    writes = [w[0] for w in _pixel(driver).writes]
    assert any(w[0] > 0 for w in writes)  # the external (red) request was honored
    assert any(w[1] > 0 for w in writes)  # the internal (green) request was honored too


def test_overlay_calls_during_active_ramp_only_become_visible_after_ramp_finishes() -> None:
    driver = _make_driver(overlay_bri=88)

    async def scenario(clock: DrivenTime) -> "tuple[list[tuple[int, ...]], list[tuple[int, ...]]]":
        tasks = await _start_all_tasks(driver)
        await clock.elapse(0)
        n = len(_pixel(driver).writes)
        ramp = asyncio.create_task(driver.request_signal(10, 0, 0, 0.15))
        await clock.elapse(20)
        driver.on()  # requested mid-ramp
        driver.off()  # and immediately reversed - only the final requested state should ever show
        await clock.elapse(20)
        mid = _colours(driver)[n:]
        await clock.run_until(ramp.done, _ramp_ms(0.15) - 40)
        await ramp
        await cancel_all(tasks, settle_yields=1)
        return mid, _colours(driver)[n:]

    with _driven() as clock:
        mid, frames = run(scenario(clock))
    assert len(mid) == 5 and all(_red(c) for c in mid), mid  # the ramp's frames at 0-40 ms, no overlay write between
    # off() was the last call before the ramp finished - restored state must be off, not on: the ramp, its final
    # black, then the ramp's one restore of the overlay.
    assert len(frames) == 2 * 7 + 2, frames
    assert (88, 88, 88) not in frames
    assert frames[-1] == (0, 0, 0)


def test_an_internal_request_waits_past_any_deadline_parks_no_sleep_and_is_never_dropped() -> None:
    # Behind a 60 s external ramp and two 60 s internal ones, a fourth request waits 180 s on the lock: it parks no sleep
    # meanwhile (one wake at its turn, no poll), plays in arrival order, and returns at its own ramp's end. One frame a
    # second: the same 180 s in 182 frames, the most parked wakes kept as one number.
    driver = _make_driver(freq=1)
    parked = [0]

    async def scenario(clock: DrivenTime) -> "tuple[list[bool], int]":
        tasks = await _start_all_tasks(driver)
        assert driver.led_signal(9, 0, 0, 60.0)
        await clock.elapse(0)
        requests = [asyncio.create_task(driver.request_signal(*rgbt)) for rgbt in ((0, 9, 0, 60.0), (0, 0, 9, 60.0), (9, 9, 0, 1.0))]

        def last_done() -> bool:
            parked[0] = max(parked[0], len(clock.wakes()))
            return requests[-1].done()

        took = await clock.run_until(last_done, 3 * _ramp_ms(60.0, 1) + _ramp_ms(1.0, 1))
        await cancel_all(tasks, settle_yields=1)
        results = []
        for request in requests:  # no await inside a comprehension on MicroPython
            results.append(await request)
        return results, took

    with _driven() as clock:
        results, took = run(scenario(clock))
    assert results == [True, True, True]
    assert took == 3 * _ramp_ms(60.0, 1) + _ramp_ms(1.0, 1)
    assert parked[0] == 1, parked[0]  # the running ramp's frame alone: no waiter sleeps
    order = [c for c in _colours(driver) if c[0] == 9 or c[1] == 9 or c[2] == 9]  # each ramp's peak
    assert order == [(9, 0, 0), (0, 9, 0), (0, 0, 9), (9, 9, 0)], order


def test_request_signal_behind_a_running_ramp_returns_true_only_after_its_own_ramp() -> None:
    driver = _make_driver()

    async def scenario(clock: DrivenTime) -> "tuple[bool, int]":
        tasks = await _start_all_tasks(driver)
        first = asyncio.create_task(driver.request_signal(10, 0, 0, 0.1))
        await clock.run_until(lambda: any(c[0] > 0 for c in _colours(driver)), 0)
        second = asyncio.create_task(driver.request_signal(0, 10, 0, 0.1))
        await clock.run_until(second.done, 2 * _ramp_ms(0.1))
        frames_at_return = len(_pixel(driver).writes)
        result = await second and await first
        await cancel_all(tasks, settle_yields=1)
        return result, frames_at_return

    with _driven() as clock:
        result, frames_at_return = run(scenario(clock))
    colours = _colours(driver)
    last_red = max(i for i, c in enumerate(colours) if c[0] > 0)
    assert result is True
    assert colours[last_red + 1 :][:2] == [(0, 0, 0), (0, 0, 0)]  # the ramp's last step, then its final black
    assert frames_at_return == len(colours)  # returned once its own ramp and restore had been written
    assert min(i for i, c in enumerate(colours) if c[1] > 0) > last_red + 2


def _replayed_flash(r: int, t: float) -> "list[tuple[int, ...]]":
    # One whole red flash at _make_driver()'s 100 Hz by the driver's own ramp rule (_ramp), its last step black.
    steps = max(int(t * 0.5 * 100), 1)
    return [(r * n // steps, 0, 0) for n in list(range(1, steps + 1)) + list(range(steps - 1, -1, -1))]


def test_a_cancelled_ramp_keeps_its_slot_and_a_restarted_task_replays_it_then_restores_the_overlay() -> None:
    # A cancel mid-ramp (a supervisor restart, a shutdown) writes nothing more and leaves the command pending; the
    # restarted signal task writes black, plays the flash in full, ends black, and restores the overlay.
    driver = _make_driver(overlay_bri=42)
    grey = (42, 42, 42)

    async def scenario(clock: DrivenTime) -> "tuple[list[tuple[int, ...]], bool, bool, list[tuple[int, ...]]]":
        (signal,) = await _start_all_tasks(driver)
        driver.on()
        assert driver.led_signal(255, 0, 0, 0.5)
        await clock.run_until(lambda: any(_red(c) for c in _colours(driver)), 0)
        await cancel_all([signal], settle_yields=1)
        n = len(_pixel(driver).writes)
        await clock.elapse(_ramp_ms(0.5))  # a ramp running on would have ended by now
        after_cancel, busy = _colours(driver)[n:], driver._start_signal_event.is_set()
        refused = driver.led_signal(0, 255, 0, 0.5)  # still pending: refused
        restarted = driver.start_asy_signal()
        await clock.run_until(lambda: not driver._start_signal_event.is_set(), _ramp_ms(0.5))
        await cancel_all([restarted], settle_yields=1)
        return after_cancel, busy, refused, _colours(driver)[n:]

    with _driven() as clock:
        after_cancel, busy, refused, after_restart = run(scenario(clock))
    assert (after_cancel, busy, refused) == ([], True, False)
    assert driver._pending == 0
    assert after_restart == [(0, 0, 0)] + _replayed_flash(255, 0.5) + [(0, 0, 0), grey], after_restart


class _SupervisorPasses:
    # For the block, a non-zero asyncio.sleep() (the supervisor's pass wait) waits for the test's release(); sleep_ms()
    # (start_tasks()'s stagger) and a zero sleep stay one yield; the driver's own waits are on the driven clock either way.
    def __enter__(self) -> "_SupervisorPasses":
        self._handler = asyncio.get_event_loop().get_exception_handler()
        self._real_sleep = asyncio.sleep
        self._real_sleep_ms = asyncio.sleep_ms
        self._gate = asyncio.Event()
        real_sleep = self._real_sleep
        gate = self._gate

        async def _gated(seconds: float) -> None:
            if seconds:
                await gate.wait()
                gate.clear()
            else:
                await real_sleep(0)

        async def _one_yield(ms: int) -> None:
            check_sleep_ms(ms)
            await real_sleep(0)

        asyncio.sleep = _gated  # type: ignore[assignment]  # a module-attribute swap, restored in __exit__
        asyncio.sleep_ms = _one_yield  # type: ignore[assignment]  # likewise
        return self

    def __exit__(self, *_exc: object) -> None:
        asyncio.sleep = self._real_sleep
        asyncio.sleep_ms = self._real_sleep_ms
        asyncio.get_event_loop().set_exception_handler(self._handler)  # start_tasks() installs one only where none is set

    def release(self) -> None:
        self._gate.set()


def test_the_supervisor_restarts_a_failed_signal_task_with_one_system_entry() -> None:
    # A frame write failing mid-ramp ends the signal task with its slot set; the real supervisor logs one SYSTEM entry
    # and restarts it, and the restart replays the flash from black to black before the overlay is restored.
    driver = _make_driver(overlay_bri=42)
    svc = SystemService(_never_synced)
    grey = (42, 42, 42)
    fault = OSError("injected pixel write fault")

    async def scenario(clock: DrivenTime, passes: _SupervisorPasses) -> "list[tuple[int, ...]]":
        await svc.start_tasks(driver.get_task_starters(), task_names=task_names_of(driver))
        signal = svc._tasks[0]
        assert signal is not None
        sup = asyncio.create_task(svc.supervise_tasks())
        driver.on()
        assert driver.led_signal(255, 0, 0, 0.5)
        await clock.run_until(lambda: any(_red(c) for c in _colours(driver)), 0)
        _pixel(driver).raise_on_write = fault
        clock.advance(10)  # the ramp's next frame falls due
        assert await _yields_until(signal.done, 20)
        _pixel(driver).raise_on_write = None  # before the supervisor's next pass
        n = len(_pixel(driver).writes)
        passes.release()  # one supervisor pass: it logs the end and restarts the task
        await clock.run_until(lambda: svc._tasks[0] is not signal, 0)
        await clock.run_until(lambda: not driver._start_signal_event.is_set(), _ramp_ms(0.5))
        await cancel_all([sup], settle_yields=1)
        await cancel_all([t for t in svc._tasks if t is not None], settle_yields=1)
        return _colours(driver)[n:]

    with _driven() as clock, _SupervisorPasses() as passes:
        after_restart = run(scenario(clock, passes))
    log = run(svc.get_error_counter())["SYSTEM"]
    assert after_restart == [(0, 0, 0)] + _replayed_flash(255, 0.5) + [(0, 0, 0), grey], after_restart
    assert log["ErrCount"] == 1
    assert log["ErrNum"][-1] == code("E", "TASK_RAISED")


def _single_signal_frames(t: float, ramp_s: float) -> "list[tuple[int, ...]]":
    # The signal task alone at the real 20 Hz: its start frame, the ramp (ramp_s: the duration it plays), the final
    # black, then the overlay's restore.
    driver = _make_driver(freq=20)

    async def scenario(clock: DrivenTime) -> None:
        signal = driver.start_asy_signal()
        assert driver.led_signal(255, 0, 0, t)
        await clock.run_until(lambda: not driver._start_signal_event.is_set(), _ramp_ms(ramp_s, 20))
        await cancel_all([signal], settle_yields=1)

    with _driven() as clock:
        run(scenario(clock))
    return _colours(driver)


def test_a_ramp_frame_allocates_nothing() -> None:
    # Integer steps into the one reused frame: a whole ramp's frame computations and stores run with the heap locked.
    driver = _make_driver()
    driver._pixel.write = lambda: None  # type: ignore[method-assign]  # the fake's frame log allocates; silicon's write() does not
    steps = 300
    micropython.heap_lock()
    try:
        for i in range(1, 2 * steps + 1):
            n = steps - abs(steps - i)
            driver._put(255 * n // steps, 7 * n // steps, 0)
    finally:
        micropython.heap_unlock()
    assert driver._frame == [0, 0, 0]


def test_a_dim_ramp_reaches_its_requested_peak() -> None:
    accepted, frames = _request_frames(_make_driver(freq=6), (7, 0, 0, 1.0), _ramp_ms(1.0, 6))  # three steps each way
    assert accepted is True
    assert frames[:6] == [(2, 0, 0), (4, 0, 0), (7, 0, 0), (4, 0, 0), (2, 0, 0), (0, 0, 0)], frames  # a float step stopped at 6


def test_in_memory_variant_works_without_fram() -> None:
    driver = _make_driver()
    accepted, frames = _request_frames(driver, (1, 0, 0, 0.1), _ramp_ms(0.1))
    assert accepted is True
    assert len(frames) == 2 * 5 + 2, frames
    assert frames[-1] == (0, 0, 0)


# ---------------------------------------------------------------------------
# _clamp_byte(): a real NeoPixel stores into a bytearray, so an out-of-range int wraps silently (0x12C stores as
# 0x2C, py/binary.c); every channel is clamped where the ramp reads it.
# ---------------------------------------------------------------------------


def test_clamp_byte_direct() -> None:
    assert _clamp_byte(0) == 0
    assert _clamp_byte(255) == 255
    assert _clamp_byte(-1) == 0
    assert _clamp_byte(256) == 255
    assert _clamp_byte(300) == 255
    assert _clamp_byte(value=True) == 1  # a bool counts as 0/1 for a byte value (the clamp's own rule)
    assert [_clamp_byte(v) for v in (float("nan"), float("inf"), float("-inf"))] == [0, 0, 0]  # int() raises for each


# ---------------------------------------------------------------------------
# A non-finite t never raises: the ramp floors NaN at 0.1 s and plays +inf as one step each way.
# ---------------------------------------------------------------------------


def test_request_signal_infinite_duration_falls_back_to_floor_not_raised() -> None:
    # int() of +inf raises OverflowError computing steps: one step each way, as the floor's ramp at 20 Hz.
    accepted, frames = _request_frames(_make_driver(freq=20), (10, 0, 0, float("inf")), _ramp_ms(0.1, 20))
    assert accepted is True
    assert frames == [(10, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0)], frames


def test_request_signal_nan_duration_falls_back_to_floor_not_raised() -> None:
    # NaN >= 0.1 is False: the ramp's `not t >= floor` sends it to the floor.
    accepted, frames = _request_frames(_make_driver(freq=20), (10, 0, 0, float("nan")), _ramp_ms(0.1, 20))
    assert accepted is True
    assert frames == [(10, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0)], frames


def test_request_signal_out_of_range_rgb_clamped_not_raised() -> None:
    driver = _make_driver()

    async def scenario(clock: DrivenTime) -> None:
        tasks = await _start_all_tasks(driver)
        request = asyncio.create_task(driver.request_signal(300, -5, 999, 0.1))  # a future misbehaving caller
        await clock.run_until(request.done, _ramp_ms(0.1))  # the ramp ran to its end
        await cancel_all(tasks, settle_yields=1)

    with _driven() as clock:
        run(scenario(clock))  # an unclamped value would wrap
    writes = [w[0] for w in _pixel(driver).writes]
    assert any(w[0] == 255 for w in writes)  # 300 clamped to the byte ceiling
    assert all(w[1] == 0 for w in writes)  # -5 clamped to the floor
    assert any(w[2] == 255 for w in writes)  # 999 clamped to the byte ceiling
    assert not any(w[0] == 44 or w[1] == 251 or w[2] == 231 for w in writes)  # 300, -5 and 999 wrapped: absent
    assert writes[-1] == (0, 0, 0)


def test_led_signal_out_of_range_rgb_clamped_not_raised() -> None:
    driver = _make_driver()

    async def scenario(clock: DrivenTime) -> None:
        tasks = await _start_all_tasks(driver)
        driver.led_signal(-10, 500, 0, 0.1)
        await clock.run_until(lambda: not driver._start_signal_event.is_set(), _ramp_ms(0.1))  # the ramp ran to its end
        await cancel_all(tasks, settle_yields=1)

    with _driven() as clock:
        run(scenario(clock))
    writes = [w[0] for w in _pixel(driver).writes]
    assert all(w[0] == 0 for w in writes)
    assert any(w[1] == 255 for w in writes)
    assert not any(w[0] == 246 or w[1] == 244 for w in writes)  # -10 and 500 wrapped: absent


def test_overlay_bri_out_of_range_clamped_not_raised() -> None:
    driver = _make_driver(overlay_bri=999)

    async def scenario(clock: DrivenTime) -> None:
        tasks = await _start_all_tasks(driver)
        await clock.elapse(0)  # the start frames first: only on() itself can then write the overlay
        driver.on()
        await clock.elapse(0)
        await cancel_all(tasks, settle_yields=1)

    with _driven() as clock:
        run(scenario(clock))  # an unclamped value would wrap
    assert _pixel(driver).writes[-1][0] == (255, 255, 255)
    assert (231, 231, 231) not in _colours(driver)  # 999 wrapped: absent


async def _request(driver: NeopixelDriver, r: int, g: int, b: int, t: float) -> None:
    await driver.request_signal(r, g, b, t)  # a task body: create_task() takes a coroutine returning None


async def _start_all_tasks(driver: NeopixelDriver) -> "list[asyncio.Task[None]]":
    starters = driver.get_task_starters()
    tasks = [s() for s in starters]
    await asyncio.sleep(0)  # one yield lets each task park on its first wait (a limit, not an interleaving claim)
    return tasks


async def _yields_until(predicate: "Callable[[], bool]", max_yields: int) -> bool:
    # A bound in scheduler yields, for a cancelled task's end inside one instant.
    for _ in range(max_yields):
        if predicate():
            return True
        await asyncio.sleep(0)
    return predicate()


def test_a_negative_duration_takes_the_floor() -> None:
    assert _single_signal_frames(-1.0, 0.1) == [(0, 0, 0), (255, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0)]  # one step each way


# ---------------------------------------------------------------------------
# Error/edge cases
# ---------------------------------------------------------------------------


def test_get_task_starters_returns_the_signal_starter() -> None:
    driver = _make_driver()
    assert [s.__name__ for s in driver.get_task_starters()] == ["start_asy_signal"]


def test_get_timer_starters_returns_empty_list() -> None:
    driver = _make_driver()
    assert driver.get_timer_starters() == []


def test_on_off_toggle_write_the_pixel_directly_when_the_lock_is_free() -> None:
    driver = _make_driver(overlay_bri=42)
    grey = (42, 42, 42)

    async def scenario(clock: DrivenTime) -> "list[tuple[int, ...]]":
        tasks = await _start_all_tasks(driver)
        seen = []
        for call, colour in ((driver.on, grey), (driver.off, (0, 0, 0)), (driver.toggle, grey)):
            call()
            await clock.run_until(_last_colour_is(driver, colour), 0)
            seen.append(_colours(driver)[-1])
        await cancel_all(tasks, settle_yields=1)
        return seen

    with _driven() as clock:
        assert run(scenario(clock)) == [grey, (0, 0, 0), grey]


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
