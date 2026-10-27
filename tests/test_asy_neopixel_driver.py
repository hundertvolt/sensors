"""NeopixelDriver: the signal ramp and its queue, the overlay task, refused and clamped values, restarts under the
supervisor and its FRAM-backed log."""

import asyncio
import sys

# asy_webserver_service imports the vendored ext/microdot.py, which scripts/test.sh's MICROPYPATH leaves out (the
# convention of tests/test_asy_webserver_service.py).
sys.path.insert(0, "ext")

from _async_harness import cancel_all, run
from _error_codes import code
from _fake_time import DrivenTime
from _fast_sleep import check_sleep_ms
from _recording_print import record_prints
from _src_const import src_const, src_int
from _task_names import task_names_of

import asy_neopixel_driver
import asy_webserver_service
from asy_base_classes import RegionBuffer
from asy_neopixel_driver import NeopixelDriver, _clamp_byte
from asy_print_log import LogConfig
from asy_system_service import SystemService

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing isn't available on the real MicroPython test interpreter
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine

    import neopixel

    from asy_crc_checks import CRCBase

_OVERLAY_REFRESH_MS: int = src_int("src/asy_neopixel_driver.py", "_OVERLAY_REFRESH_MS")
_SIGNAL_WAIT_MS: int = src_int("src/asy_neopixel_driver.py", "_SIGNAL_WAIT_MS")


def _colours(driver: NeopixelDriver) -> "list[tuple[int, ...]]":
    return [w[0] for w in _pixel(driver).writes]


def _driven() -> DrivenTime:
    # The driver module's time and asyncio on one driven clock for the block: every frame, poll and overlay wait parks
    # on it, and time moves only when the test moves it.
    return DrivenTime(asy_neopixel_driver, sleeps=True)


def _event_driver() -> NeopixelDriver:
    return _make_driver(debug=4)  # DebugLevel 4 (events, SPEC A.8): event-level console lines reach record_prints()


def _frame_added(driver: NeopixelDriver) -> "Callable[[], bool]":
    # True once the pixel has a frame more than now.
    n = len(_pixel(driver).writes)
    return lambda: len(_pixel(driver).writes) > n


def _last_colour_is(driver: NeopixelDriver, colour: "tuple[int, ...]") -> "Callable[[], bool]":
    return lambda: _colours(driver)[-1:] == [colour]


def _make_driver(freq: int = 100, overlay_bri: int = 50, debug: "int | None" = None) -> NeopixelDriver:
    # 100 Hz keeps five frames per ramp direction at the 0.1 s floor, so mid-ramp state is observable; time is driven,
    # not waited. The fixed values are the driver's own state, set from outside.
    driver = NeopixelDriver(0, log=LogConfig(None, 10, debug))
    driver.neopixel_freq = freq
    driver._frame_ms = 1000 // freq
    driver._overlay_bri = overlay_bri
    run(driver.setup())  # the boot batch's setup(), before any task starts
    return driver


async def _never_synced() -> bool:
    return False


def _pixel(driver: NeopixelDriver) -> "neopixel.NeoPixel":
    # tests/neopixel.py's fake, reached through the driver's own attribute - that fake is what
    # `neopixel` resolves to here (it is not excluded from mypy, unlike tests/network.py).
    return driver._pixel


def _ramp_ms(t: float, freq: int = 100) -> int:
    # One signal's length on the driven clock: both directions' frames at the frame period, by the driver's own steps
    # rule (_signal_loop); its final black lands at that instant.
    return 2 * max(int(t * 0.5 * freq), 1) * (1000 // freq)


def _red(colour: "tuple[int, ...]") -> bool:
    return colour[0] > 0 and colour[1] == 0


def _request_frames(driver: NeopixelDriver, rgbt: "tuple[int, int, int, float]", ramp_ms: int) -> "tuple[bool, list[tuple[int, ...]]]":
    # request_signal(*rgbt) with both tasks running: its result, and every frame from the request until ramp_ms later
    # (the ramp, its final black and the overlay task's restore).
    async def scenario(clock: DrivenTime) -> "tuple[bool, list[tuple[int, ...]]]":
        tasks = await _start_all_tasks(driver)
        await clock.elapse(0)  # the tasks' own start frames
        n = len(_pixel(driver).writes)
        accepted = await driver.request_signal(*rgbt)
        await clock.elapse(ramp_ms)
        await cancel_all(tasks, settle_yields=1)
        return accepted, _colours(driver)[n:]

    with _driven() as clock:
        return run(scenario(clock))


# ---------------------------------------------------------------------------
# Init / logging
# ---------------------------------------------------------------------------


def test_init_bakes_name_into_the_logger() -> None:
    driver = _make_driver()
    assert driver.pr.name == "NEOPIXEL"


def test_the_frame_rate_and_overlay_brightness_are_fixed_values_no_caller_passes() -> None:
    driver = NeopixelDriver(0, log=LogConfig(None, 10, None))
    freq = src_int("src/asy_neopixel_driver.py", "_NEOPIXEL_FREQ_HZ")
    assert (driver.neopixel_freq, driver._frame_ms, driver._overlay_bri) == (freq, 1000 // freq, src_const("src/asy_neopixel_driver.py", "_LED_OVERL_BRI"))
    assert type(driver._frame_ms) is int  # the frame sleep's own ms value, no float per frame
    refused = []
    for keyword in ("neopixel_freq", "led_overl_bri"):
        try:
            NeopixelDriver(0, **{keyword: 100})  # type: ignore[arg-type]  # the dict's int values against log's LogConfig
        except TypeError:  # an unexpected keyword argument
            refused.append(keyword)
    assert refused == ["neopixel_freq", "led_overl_bri"], refused


def test_get_error_counter_forwards_to_the_real_print_log() -> None:
    driver = _make_driver()
    log = run(driver.get_error_counter())
    assert log["NEOPIXEL"]["ErrCount"] == 0


def test_get_error_counter_reflects_a_real_logged_error() -> None:
    driver = _make_driver()
    run(driver.pr.err_s("boom", errno=1))
    log = run(driver.get_error_counter())
    assert log["NEOPIXEL"]["ErrCount"] == 1


def test_reset_error_counter_returns_true_and_clears() -> None:
    driver = _make_driver()
    run(driver.pr.err_s("boom", errno=1))
    assert run(driver.reset_error_counter()) is True
    assert run(driver.get_error_counter())["NEOPIXEL"]["ErrCount"] == 0


# ---------------------------------------------------------------------------
# Overlay behavior: on, off and toggle
# ---------------------------------------------------------------------------


def test_on_sets_pixel_to_overlay_brightness_and_records_a_write() -> None:
    driver = _make_driver(overlay_bri=42)

    async def scenario(clock: DrivenTime) -> None:
        tasks = await _start_all_tasks(driver)
        await clock.elapse(0)  # the start frames first: only on() itself can then write the overlay
        driver.on()
        await clock.elapse(0)  # the overlay task's wake and write, and nothing after them
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


def test_overlay_write_deferred_while_ramp_holds_the_overlay_lock() -> None:
    driver = _make_driver(overlay_bri=99)
    lit = (99, 99, 99)

    async def scenario(clock: DrivenTime) -> "tuple[bool, list[bool]]":
        tasks = await _start_all_tasks(driver)
        await driver.request_signal(10, 0, 0, 0.1)  # returns once the request is queued, not once the ramp ends
        await clock.run_until(lambda: any(_red(c) for c in _colours(driver)), 0)  # mid-ramp: the ramp holds the lock
        held = driver._overlay_lock.locked()
        driver.on()  # queued: it must not write while the ramp still holds the lock
        lit_while_held: list[bool] = []

        def released() -> bool:  # at each frame the ramp still holds the lock: is the overlay's colour written?
            if driver._overlay_lock.locked():
                lit_while_held.append(lit in _colours(driver))
                return False
            return True

        await clock.run_until(released, _ramp_ms(0.1))  # at the ramp's end the overlay writes the restore it asked for
        await cancel_all(tasks, settle_yields=1)
        return held, lit_while_held

    with _driven() as clock:
        held, lit_while_held = run(scenario(clock))
    assert held is True
    assert lit_while_held, lit_while_held
    assert not any(lit_while_held), lit_while_held
    assert _pixel(driver).writes[-1][0] == lit


def test_the_overlay_is_rewritten_once_per_refresh_period() -> None:
    # A WS2812 reports nothing, so only a rewrite puts a pixel blanked by a supply dip right: one frame per period
    # with nothing pending, none before it, none into a running ramp, and black while the overlay is off.
    driver = _make_driver(overlay_bri=42)
    period = _OVERLAY_REFRESH_MS
    grey = (42, 42, 42)

    async def scenario(clock: DrivenTime) -> "tuple[list[tuple[int, ...]], ...]":
        tasks = await _start_all_tasks(driver)
        driver.on()
        await clock.run_until(_last_colour_is(driver, grey), 0)  # written at once: the next refresh is a period away
        n = len(_pixel(driver).writes)
        await clock.elapse(period - 1)
        early = _colours(driver)[n:]
        await clock.run_until(lambda: len(_pixel(driver).writes) > n, 1)
        refreshed = _colours(driver)[n:]
        await clock.elapse(period - _ramp_ms(0.5) // 2)
        await driver.request_signal(255, 0, 0, 0.5)  # the next refresh falls due mid-ramp
        await clock.run_until(lambda: not driver._start_signal_event.is_set(), _ramp_ms(0.5))
        colours = _colours(driver)
        last_red = max(i for i, c in enumerate(colours) if _red(c))
        after_ramp = colours[last_red + 1 :]
        driver.off()
        await clock.run_until(_last_colour_is(driver, (0, 0, 0)), 0)
        n = len(_pixel(driver).writes)
        await clock.elapse(period - 1)
        early_off = _colours(driver)[n:]
        await clock.run_until(lambda: len(_pixel(driver).writes) > n, 1)
        off_refresh = _colours(driver)[n:]
        await cancel_all(tasks, settle_yields=1)
        return early, refreshed, after_ramp, early_off, off_refresh

    with _driven() as clock:
        early, refreshed, after_ramp, early_off, off_refresh = run(scenario(clock))
    assert early == []  # nothing before the period
    assert refreshed == [grey]  # one rewrite of the current overlay
    # The ramp's last step and final black, then the refresh that waited for the lock and the ramp's own restore.
    assert after_ramp == [(0, 0, 0), (0, 0, 0), grey, grey], after_ramp
    assert early_off == []
    assert off_refresh == [(0, 0, 0)]


def test_an_overlay_wake_leaves_one_flag_registration_and_no_task_behind() -> None:
    # Guard on the bounded wait's per-wake tasks (a waiter and a runner, extmod/asyncio/funcs.py, v1.29.0): each wake
    # ends both, the IO queue keeps only the flag the next wait registers, and a cancel leaves no task behind.
    driver = _make_driver(overlay_bri=42)
    core = sys.modules["asyncio.core"]
    real_create_task = core.create_task
    created: list[asyncio.Task[object]] = []

    def recording(coro: "Coroutine[object, object, object]") -> "asyncio.Task[object]":
        task: asyncio.Task[object] = real_create_task(coro)
        created.append(task)
        return task

    async def scenario() -> "tuple[int, int, list[object], int]":
        overlay = driver.start_asy_overlay()
        await asyncio.sleep(0)
        core.create_task = recording  # type: ignore[attr-defined]  # a module-attribute swap, restored in the finally
        try:
            for _ in range(3):
                added = _frame_added(driver)
                driver.toggle()
                assert await _yields_until(added, 20)
                await asyncio.sleep(0)  # the next wait's waiter registers its flag
        finally:
            core.create_task = real_create_task  # type: ignore[attr-defined]  # the swap undone
        pending = len([t for t in created if not t.done()])
        streams = [entry[2] for entry in core._io_queue.map.values()]
        await cancel_all([overlay], settle_yields=1)
        return len(created), pending, streams, len([t for t in created if not t.done()])

    created_n, pending, streams, left = run(scenario())
    assert created_n == 6  # a waiter and a runner per wake
    assert pending == 2  # only the wait in progress
    assert streams == [driver._overlay_start]
    assert left == 0


# ---------------------------------------------------------------------------
# request_signal() (blocking/internal path)
# ---------------------------------------------------------------------------


def test_request_signal_ramps_up_then_down_and_ends_at_black() -> None:
    accepted, frames = _request_frames(_make_driver(), (50, 60, 70, 0.1), _ramp_ms(0.1))
    assert accepted is True
    assert len(frames) == 2 * 5 + 2, frames  # five frames each way at 100 Hz, the final black, the overlay's restore
    assert frames[4] == (50, 60, 70)  # the peak
    assert frames[-3:] == [(0, 0, 0)] * 3


def test_request_signal_restores_overlay_on_state_after_ramp() -> None:
    driver = _make_driver(overlay_bri=77)

    async def scenario(clock: DrivenTime) -> None:
        tasks = await _start_all_tasks(driver)
        driver.on()
        await clock.run_until(_last_colour_is(driver, (77, 77, 77)), 0)
        await driver.request_signal(10, 0, 0, 0.1)
        await clock.run_until(lambda: not driver._start_signal_event.is_set(), _ramp_ms(0.1))  # with the restore written
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
        # The second polls once per frame, so it starts one frame after the first ramp's end at the latest.
        await clock.run_until(lambda: second.done() and not driver._start_signal_event.is_set(), 2 * _ramp_ms(0.1) + 10)
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
        r1 = await driver.request_signal(1, 0, 0, 0.1)
        second = asyncio.create_task(driver.request_signal(0, 1, 0, 0.1))
        await clock.run_until(second.done, _ramp_ms(0.1))  # it queues at the first ramp's end
        r2 = await second
        await clock.elapse(_ramp_ms(0.1))
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
    # The busy signal is _start_signal_event, set for the whole ramp; an external request while it is set is
    # refused, never queued (owner, 2026-10-02).
    driver = _event_driver()

    async def scenario(clock: DrivenTime) -> "tuple[bool, bool]":
        tasks = await _start_all_tasks(driver)
        await driver.request_signal(10, 0, 0, 0.1)
        await clock.run_until(lambda: any(c[0] > 0 for c in _colours(driver)), 0)
        busy = driver._start_signal_event.is_set()
        result = driver.led_signal(0, 10, 0, 0.1)
        await clock.run_until(lambda: not driver._start_signal_event.is_set(), _ramp_ms(0.1))
        await clock.elapse(_ramp_ms(0.1))  # a queued request would have run a whole ramp by now
        await cancel_all(tasks, settle_yields=1)
        return busy, result

    with _driven() as clock, record_prints() as recorder:
        busy, result = run(scenario(clock))
    assert busy is True
    assert result is False
    assert not any(c[1] > 0 for c in _colours(driver))  # the refused colour never reaches the pixel
    assert ("NEOPIXEL", "External LED command refused: busy, retry later.") in recorder.lines


def test_led_signal_is_refused_while_an_internal_request_is_queued_and_no_task_runs() -> None:
    driver = _make_driver()

    async def scenario(clock: DrivenTime) -> "tuple[bool, bool, bool]":
        queued = await driver.request_signal(10, 0, 0, 0.1)  # no signal task yet: the request stays queued
        refused = driver.led_signal(0, 10, 0, 0.1)  # no await since: the check reads the event, not a task
        tasks = await _start_all_tasks(driver)
        await clock.run_until(lambda: not driver._start_signal_event.is_set(), _ramp_ms(0.1))
        accepted = driver.led_signal(0, 10, 0, 0.1)
        await clock.run_until(lambda: not driver._start_signal_event.is_set(), _ramp_ms(0.1))
        await cancel_all(tasks, settle_yields=1)
        return queued, refused, accepted

    with _driven() as clock:
        assert run(scenario(clock)) == (True, False, True)
    colours = _colours(driver)
    assert max(i for i, c in enumerate(colours) if c[0] > 0) < min(i for i, c in enumerate(colours) if c[1] > 0)


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
    # steps = int(1.5 * 0.5 * 20) = 15 per direction -> 30 ramp frames + 1 final black frame.
    assert n_writes == 31


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
        assert await internal is True
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
        ramp = asyncio.create_task(driver.request_signal(10, 0, 0, 0.15))  # it only queues the ramp
        await clock.elapse(20)
        driver.on()  # requested mid-ramp
        driver.off()  # and immediately reversed - only the final requested state should ever show
        await clock.elapse(20)
        mid = _colours(driver)[n:]
        await clock.run_until(lambda: not driver._start_signal_event.is_set(), _ramp_ms(0.15) - 40)
        await ramp  # long since returned - awaited so no task reference dangles
        await cancel_all(tasks, settle_yields=1)
        return mid, _colours(driver)[n:]

    with _driven() as clock:
        mid, frames = run(scenario(clock))
    assert len(mid) == 5 and all(_red(c) for c in mid), mid  # the ramp's frames at 0-40 ms, no overlay write between
    # off() was the last call before the ramp finished - restored state must be off, not on: the ramp, its final
    # black, then the overlay write deferred from mid-ramp and the ramp's own restore.
    assert len(frames) == 2 * 7 + 3, frames
    assert (88, 88, 88) not in frames
    assert frames[-1] == (0, 0, 0)


def test_request_signal_gives_up_at_its_deadline_when_the_signal_task_never_runs() -> None:
    driver = _event_driver()
    wait_ms = _SIGNAL_WAIT_MS
    frame_ms = 1000 // 100  # _make_driver()'s 100 Hz

    async def scenario(clock: DrivenTime) -> "tuple[bool, bool, bool]":
        driver._start_signal_event.set()  # a signal is queued and its task never runs
        rgbt_before = driver._rgbt
        waiter = asyncio.create_task(driver.request_signal(0, 10, 0, 0.1))
        await clock.elapse(0)  # the waiter takes its deadline at now = 0
        await clock.jump(wait_ms - frame_ms)  # its next poll comes one frame before the deadline
        pending_before = not waiter.done()
        await clock.run_until(waiter.done, frame_ms)
        return pending_before, await waiter, driver._rgbt is rgbt_before

    with _driven() as clock, record_prints() as recorder:
        pending_before, result, untouched = run(scenario(clock))
    assert pending_before is True
    assert result is False
    assert untouched is True  # the dropped request never replaced the queued values
    assert driver._start_signal_event.is_set() is True
    assert _pixel(driver).writes == []
    assert ("NEOPIXEL", "Internal LED command dropped: signal still busy.") in recorder.lines


def test_request_signal_behind_a_running_ramp_returns_true_only_after_it_ends() -> None:
    driver = _make_driver()

    async def scenario(clock: DrivenTime) -> "tuple[bool, int]":
        tasks = await _start_all_tasks(driver)
        await driver.request_signal(10, 0, 0, 0.1)
        await clock.run_until(lambda: any(c[0] > 0 for c in _colours(driver)), 0)
        second = asyncio.create_task(driver.request_signal(0, 10, 0, 0.1))
        await clock.run_until(second.done, _ramp_ms(0.1))
        frames_at_return = len(_pixel(driver).writes)
        result = await second
        await clock.run_until(lambda: not driver._start_signal_event.is_set(), _ramp_ms(0.1))
        await cancel_all(tasks, settle_yields=1)
        return result, frames_at_return

    with _driven() as clock:
        result, frames_at_return = run(scenario(clock))
    colours = _colours(driver)
    last_red = max(i for i, c in enumerate(colours) if c[0] > 0)
    assert result is True
    assert colours[last_red + 1 :][:2] == [(0, 0, 0), (0, 0, 0)]  # the ramp's last step, then its final black
    assert frames_at_return >= last_red + 3  # returned only once the first ramp had ended
    assert min(i for i, c in enumerate(colours) if c[1] > 0) > last_red + 2


def test_cancelling_the_signal_task_mid_ramp_leaves_the_pixel_dark_and_the_slot_free() -> None:
    driver = _make_driver()

    async def scenario(clock: DrivenTime) -> "tuple[tuple[int, ...], bool, list[tuple[int, ...]]]":
        tasks = await _start_all_tasks(driver)
        signal = tasks[1]  # get_task_starters() order: overlay, then signal
        await driver.request_signal(10, 0, 0, 0.5)
        await clock.run_until(lambda: any(c[0] > 0 for c in _colours(driver)), 20)  # int(0.4 * n) > 0 from the third frame
        await cancel_all([signal], settle_yields=1)
        last = _colours(driver)[-1]
        busy = driver._start_signal_event.is_set()
        n = len(_pixel(driver).writes)
        restarted = driver.start_asy_signal()
        await clock.elapse(_ramp_ms(0.5))  # a replayed ramp would run its whole length in this time
        await cancel_all([t for t in tasks if t is not signal] + [restarted], settle_yields=1)
        return last, busy, _colours(driver)[n:]

    with _driven() as clock:
        last, busy, after_restart = run(scenario(clock))
    assert last == (0, 0, 0)
    assert busy is False
    assert not any(c[0] > 0 for c in after_restart)  # no frame of the cancelled colour is replayed


def test_a_frame_write_failing_mid_ramp_ends_the_task_with_the_slot_free() -> None:
    driver = _make_driver()
    fault = OSError("injected pixel write fault")

    async def scenario(clock: DrivenTime) -> "tuple[object, bool]":
        tasks = await _start_all_tasks(driver)
        signal = tasks[1]
        await driver.request_signal(10, 0, 0, 0.5)
        await clock.run_until(lambda: any(c[0] > 0 for c in _colours(driver)), 20)  # int(0.4 * n) > 0 from the third frame
        _pixel(driver).raise_on_write = fault
        clock.advance(10)  # the ramp's next frame falls due; the overlay's wait is a refresh period away
        assert await _yields_until(signal.done, 20)
        try:
            await signal
            raised: object = None
        except OSError as e:
            raised = e
        _pixel(driver).raise_on_write = None
        accepted = driver.led_signal(0, 10, 0, 0.1)  # the slot is free again
        await cancel_all([t for t in tasks if t is not signal], settle_yields=1)
        return raised, accepted

    with _driven() as clock:
        raised, accepted = run(scenario(clock))
    assert raised is fault  # the failure reaches whoever awaits the task (the supervisor), not swallowed
    assert accepted is True


def test_a_restarted_overlay_task_reapplies_the_overlay() -> None:
    driver = _make_driver(overlay_bri=42)
    grey = (42, 42, 42)

    async def scenario(clock: DrivenTime) -> "list[tuple[int, ...]]":
        overlay = driver.start_asy_overlay()
        driver.on()
        await clock.run_until(_last_colour_is(driver, grey), 0)
        await cancel_all([overlay], settle_yields=1)
        n = len(_pixel(driver).writes)
        restarted = driver.start_asy_overlay()  # no on(): the restart alone
        await clock.elapse(0)
        await cancel_all([restarted], settle_yields=1)
        return _colours(driver)[n:]

    with _driven() as clock:
        assert run(scenario(clock)) == [grey]


def test_a_signal_task_ended_mid_ramp_restarts_dark_and_restores_the_overlay() -> None:
    driver = _make_driver(overlay_bri=42)
    grey = (42, 42, 42)
    fault = OSError("injected pixel write fault")

    async def scenario(clock: DrivenTime) -> "tuple[list[tuple[int, ...]], bool]":
        overlay, signal = await _start_all_tasks(driver)
        driver.on()
        await clock.run_until(_last_colour_is(driver, grey), 0)
        await driver.request_signal(255, 0, 0, 0.5)
        await clock.run_until(lambda: any(_red(c) for c in _colours(driver)), 0)
        _pixel(driver).raise_on_write = fault  # the ramp's next frame and its final black both raise
        clock.advance(10)  # the ramp's next frame falls due; the overlay's wait is a refresh period away
        assert await _yields_until(signal.done, 20)
        _pixel(driver).raise_on_write = None  # cleared before the overlay writes and the supervisor-equivalent restart
        try:
            await signal
        except OSError:
            pass
        await clock.elapse(0)  # the overlay task writes the restore the ended ramp asked for
        n = len(_pixel(driver).writes)
        restarted = driver.start_asy_signal()
        await clock.elapse(0)
        alive = not overlay.done()
        await cancel_all([overlay, restarted], settle_yields=1)
        return _colours(driver)[n:], alive

    with _driven() as clock:
        after_restart, alive = run(scenario(clock))
    assert alive is True
    assert after_restart == [(0, 0, 0), grey]  # dark at the restart, then the overlay; no frame of the old ramp


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


def _single_signal_frames(t: float, ramp_s: float) -> "list[tuple[int, ...]]":
    # The signal task alone at the real 20 Hz: its start frame, the ramp (ramp_s: t within the driver's bounds), then
    # the final black.
    driver = _make_driver(freq=20)

    async def scenario(clock: DrivenTime) -> None:
        signal = driver.start_asy_signal()
        await driver.request_signal(255, 0, 0, t)
        await clock.run_until(lambda: not driver._start_signal_event.is_set(), _ramp_ms(ramp_s, 20))
        await cancel_all([signal], settle_yields=1)

    with _driven() as clock:
        run(scenario(clock))
    return _colours(driver)


def test_the_supervisor_restarts_a_failed_signal_task_with_one_system_entry() -> None:
    driver = _make_driver(overlay_bri=42)
    svc = SystemService(_never_synced)
    grey = (42, 42, 42)
    fault = OSError("injected pixel write fault")

    async def scenario(clock: DrivenTime, passes: _SupervisorPasses) -> "list[tuple[int, ...]]":
        await svc.start_tasks(driver.get_task_starters(), task_names=task_names_of(driver))
        overlay, signal = svc._tasks[0], svc._tasks[1]
        assert overlay is not None and signal is not None
        sup = asyncio.create_task(svc.supervise_tasks())
        driver.on()
        await clock.run_until(_last_colour_is(driver, grey), 0)
        await driver.request_signal(255, 0, 0, 0.5)
        await clock.run_until(lambda: any(_red(c) for c in _colours(driver)), 0)
        _pixel(driver).raise_on_write = fault
        clock.advance(10)  # the ramp's next frame falls due; the overlay's wait is a refresh period away
        assert await _yields_until(signal.done, 20)
        _pixel(driver).raise_on_write = None  # before the overlay writes and the supervisor's next pass
        await clock.elapse(0)
        n = len(_pixel(driver).writes)
        passes.release()  # one supervisor pass: it logs the end and restarts the task
        await clock.run_until(lambda: svc._tasks[1] is not signal, 0)
        await clock.elapse(0)
        assert not overlay.done()
        await cancel_all([sup], settle_yields=1)
        await cancel_all([t for t in svc._tasks if t is not None], settle_yields=1)
        return _colours(driver)[n:]

    with _driven() as clock, _SupervisorPasses() as passes:
        after_restart = run(scenario(clock, passes))
    log = run(svc.get_error_counter())["SYSTEM"]
    assert after_restart == [(0, 0, 0), grey]
    assert log["ErrCount"] == 1
    assert log["ErrNum"][-1] == code("E", "TASK_RAISED")


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------


def test_setup_initialises_the_logger_and_the_driver_before_any_task() -> None:
    driver = NeopixelDriver(0, log=LogConfig(None, 10, None))
    assert driver.pr.initialized is False

    async def scenario() -> bool:
        tasks = await _start_all_tasks(driver)
        started_uninitialised = driver.pr.initialized is False  # no task sets the logger up
        await cancel_all(tasks, settle_yields=1)
        return started_uninitialised

    with _driven():  # the overlay's refresh wait parks on the driven clock and is cancelled there
        assert run(scenario()) is True
    assert run(driver.setup()) is True
    assert driver.pr.initialized is True


class _FakeFramChunk:
    # One chunk's bytes, moved through the real RegionBuffer asy_print_log's _FramChunk Protocol names.
    def __init__(self) -> None:
        self.buf = bytearray(64)
        self._buffer = RegionBuffer(64)

    def get_buffer(self) -> RegionBuffer:
        return self._buffer

    async def read_into(self, buf: RegionBuffer) -> bool:
        data = buf.get_data_buf()
        if data is None:
            return False
        data[:] = self.buf
        return True

    async def write_into(self, buf: RegionBuffer) -> bool:
        data = buf.get_data_buf()
        if data is None:
            return False
        self.buf[:] = data
        return True


class _FakeFramManager:
    def __init__(self, chunk: "_FakeFramChunk") -> None:
        self.chunk = chunk

    def get_chunk(self, size: int, crc: "CRCBase | None" = None, verify: int = 0, check_length: int = 8, *, owner: str) -> "_FakeFramChunk":
        return self.chunk

    def get_pause(self) -> bool:
        return False


def test_fram_backed_variant_survives_a_reboot() -> None:
    chunk = _FakeFramChunk()
    fram = _FakeFramManager(chunk)
    driver1 = NeopixelDriver(0, log=LogConfig(fram, 10, None))  # the fake structurally satisfies asy_print_log's _FramManager Protocol

    async def scenario1() -> None:
        await driver1.setup()
        await driver1.pr.err_s("boom", errno=1)

    run(scenario1())

    driver2 = NeopixelDriver(0, log=LogConfig(fram, 10, None))

    async def scenario2() -> None:
        await driver2.setup()

    run(scenario2())
    assert driver2.pr._err_count == driver1.pr._err_count


def test_the_log_config_sets_the_loggers_length_and_level() -> None:
    driver = NeopixelDriver(0, log=LogConfig(None, 3, 2))
    assert len(driver.pr.history) == 3
    assert driver.pr.level == 2


def test_in_memory_variant_works_without_fram() -> None:
    driver = _make_driver()
    assert type(driver.pr).__name__ == "PrintLogHistory"  # not the FRAM-backed subclass
    accepted, frames = _request_frames(driver, (1, 0, 0, 0.1), _ramp_ms(0.1))
    assert accepted is True
    assert len(frames) == 2 * 5 + 2, frames
    assert frames[-1] == (0, 0, 0)


# ---------------------------------------------------------------------------
# _clamp_byte(): a real NeoPixel stores into a bytearray, so an out-of-range int wraps silently (0x12C stores as
# 0x2C, py/binary.c); every value is clamped where the request enters.
# ---------------------------------------------------------------------------


def test_clamp_byte_direct() -> None:
    assert _clamp_byte(0) == 0
    assert _clamp_byte(255) == 255
    assert _clamp_byte(-1) == 0
    assert _clamp_byte(256) == 255
    assert _clamp_byte(300) == 255
    assert _clamp_byte(value=True) == 1  # a bool counts as 0/1 for a byte value (the clamp's own rule)


# ---------------------------------------------------------------------------
# A non-finite t is mapped to the 0.1 s floor by _signal_values() before any ramp runs.
# ---------------------------------------------------------------------------


def test_request_signal_infinite_duration_falls_back_to_floor_not_raised() -> None:
    # Would raise OverflowError computing steps if unclamped; the floor's ramp at 20 Hz is one step each way.
    accepted, frames = _request_frames(_make_driver(freq=20), (10, 0, 0, float("inf")), _ramp_ms(0.1, 20))
    assert accepted is True
    assert frames == [(10, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0)], frames


def test_request_signal_nan_duration_falls_back_to_floor_not_raised() -> None:
    # NaN >= 0.1 is False: only the explicit non-finite test sends it to the floor.
    accepted, frames = _request_frames(_make_driver(freq=20), (10, 0, 0, float("nan")), _ramp_ms(0.1, 20))
    assert accepted is True
    assert frames == [(10, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0)], frames


def test_request_signal_out_of_range_rgb_clamped_not_raised() -> None:
    driver = _make_driver()

    async def scenario(clock: DrivenTime) -> None:
        tasks = await _start_all_tasks(driver)
        await driver.request_signal(300, -5, 999, 0.1)  # a future misbehaving caller
        await clock.run_until(lambda: not driver._start_signal_event.is_set(), _ramp_ms(0.1))  # the ramp ran to its end
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


# Every cancel_all() here takes one settling yield: a cancelled overlay task's bounded wait ends its runner one hop
# after its waiter, so neither outlives the scenario.
async def _start_all_tasks(driver: NeopixelDriver) -> "list[asyncio.Task[None]]":
    starters = driver.get_task_starters()
    tasks = [s() for s in starters]
    await asyncio.sleep(0)  # one yield lets each task park on its first wait (a limit, not an interleaving claim)
    return tasks


async def _yields_until(predicate: "Callable[[], bool]", max_yields: int) -> bool:
    # A bound in scheduler yields, for an interleaving inside one instant (a fault cleared before the next task writes)
    # and for the one test on the real bounded wait.
    for _ in range(max_yields):
        if predicate():
            return True
        await asyncio.sleep(0)
    return predicate()


def test_a_long_signal_is_capped_at_sixty_seconds() -> None:
    frames = _single_signal_frames(600.0, 60.0)
    assert (len(frames) - 2) // 2 == int(60 * 0.5 * 20)  # steps per direction, from the frames recorded
    assert len(frames) == 2 + 2 * int(60 * 0.5 * 20)
    assert frames[-1] == (0, 0, 0)


def test_a_negative_duration_takes_the_floor() -> None:
    assert _single_signal_frames(-1.0, 0.1) == [(0, 0, 0), (255, 0, 0), (0, 0, 0), (0, 0, 0)]  # one step each way


# ---------------------------------------------------------------------------
# Error/edge cases
# ---------------------------------------------------------------------------


def test_get_task_starters_returns_the_overlay_and_signal_starters() -> None:
    driver = _make_driver()
    assert [s.__name__ for s in driver.get_task_starters()] == ["start_asy_overlay", "start_asy_signal"]


def test_get_timer_starters_returns_empty_list() -> None:
    driver = _make_driver()
    assert driver.get_timer_starters() == []


def test_on_off_toggle_drive_the_pixel_through_the_overlay_task() -> None:
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


def test_the_driver_ceiling_on_a_signal_equals_the_rest_ceiling_on_t() -> None:
    # Two copies of one limit: the driver caps t at _MAX_SIGNAL_S, the REST schema refuses a T above its maximum;
    # if they drift, the driver silently clamps a T the API let through.
    t_field = asy_webserver_service._LIGHT_CMD_FIELDS[3]
    assert t_field[0] == "T"
    assert src_const("src/asy_neopixel_driver.py", "_MAX_SIGNAL_S") == t_field[4]


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
