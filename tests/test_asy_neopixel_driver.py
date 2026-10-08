import asyncio
import time

import asy_neopixel_driver
import asy_print_log as print_log_module
from asy_base_classes import RegionBuffer
from asy_neopixel_driver import NeopixelDriver, _clamp_byte
from asy_print_log import LogConfig

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing isn't available on the real MicroPython test interpreter
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
    from typing import Any, TypeVar

    import neopixel

    from asy_crc_checks import CRCBase

    T = TypeVar("T")


def run(coro: "Coroutine[Any, Any, T]") -> "T":  # drives a coroutine to completion for these sync test_* functions
    return asyncio.run(coro)


def _pixel(driver: NeopixelDriver) -> "neopixel.NeoPixel":
    # tests/neopixel.py's fake, reached through the driver's own attribute - that fake is what
    # `neopixel` resolves to here (it is not excluded from mypy, unlike tests/network.py).
    return driver._pixel


def make_driver(neopixel_freq: int = 100, led_overl_bri: int = 50, debug: "int | None" = None) -> NeopixelDriver:
    # freq=100, against the real 20 default, keeps every ramp's step count high enough - 5 per direction at
    # the t=0.1 floor - to observe mid-ramp state. A test outside _DrivenClock drives real asyncio.sleep(),
    # so fast ramps keep its runtime short.
    driver = NeopixelDriver(0, neopixel_freq=neopixel_freq, led_overl_bri=led_overl_bri, log=LogConfig(None, 10, debug))
    run(driver.setup())  # the boot batch's setup(), before any task starts
    return driver


async def _start_all_tasks(driver: NeopixelDriver) -> "list[asyncio.Task[None]]":
    starters = driver.get_task_starters()
    tasks = [s() for s in starters]
    await asyncio.sleep(0)  # let each task reach its first await (event.wait()) before returning
    return tasks


async def _cancel_all(tasks: "list[asyncio.Task[None]]") -> None:
    for t in tasks:
        t.cancel()
        try:
            await t
        except asyncio.CancelledError:
            pass


_TICKS_PERIOD = 1 << 30  # rp2's ticks_ms() period (MICROPY_PY_TIME_TICKS_PERIOD on a 32-bit port)


class _YieldOnlyAsyncio:
    # The driver's view of asyncio under _DrivenClock: each frame or poll sleep is one yield, so a ramp of
    # any length runs in yields, never wall-clock time; every other name is the real asyncio's.
    Event = asyncio.Event
    Lock = asyncio.Lock
    ThreadSafeFlag = asyncio.ThreadSafeFlag
    CancelledError = asyncio.CancelledError
    get_event_loop = staticmethod(asyncio.get_event_loop)

    @staticmethod
    async def sleep(_s: float) -> None:
        await asyncio.sleep(0)


class _DrivenClock:
    # Local driven clock until the shared one lands: the driver module's asyncio becomes _YieldOnlyAsyncio
    # and its ticks_ms() reads `now`, which only the test moves; leaving the block restores both.
    def __init__(self) -> None:
        self.now = 0

    def __enter__(self) -> "_DrivenClock":
        asy_neopixel_driver.asyncio = _YieldOnlyAsyncio  # type: ignore[assignment]
        asy_neopixel_driver.time = self  # type: ignore[assignment]
        return self

    def __exit__(self, *_exc: object) -> None:
        asy_neopixel_driver.asyncio = asyncio
        asy_neopixel_driver.time = time

    def ticks_ms(self) -> int:
        return self.now

    @staticmethod
    def ticks_add(ticks: int, delta: int) -> int:
        return (ticks + delta) % _TICKS_PERIOD

    @staticmethod
    def ticks_diff(ticks1: int, ticks2: int) -> int:
        return (ticks1 - ticks2 + _TICKS_PERIOD // 2) % _TICKS_PERIOD - _TICKS_PERIOD // 2


async def _run_until(predicate: "Callable[[], bool]", max_yields: int) -> bool:
    # A bound in yields, not milliseconds: under _DrivenClock every driver step is one yield.
    for _ in range(max_yields):
        if predicate():
            return True
        await asyncio.sleep(0)
    return predicate()


class _PrintRecorder:
    # Local stand-in for a shared print recorder: shadows print() inside asy_print_log only, so every
    # console line a logger emits is captured with its arguments; restore() removes the shadow.
    def __init__(self) -> None:
        self.lines: list[tuple[object, ...]] = []
        print_log_module.print = self  # type: ignore[attr-defined]

    def __call__(self, *args: object, **_kwargs: object) -> None:
        self.lines.append(args)

    def restore(self) -> None:
        del print_log_module.print  # type: ignore[attr-defined]


def _src_const(name: str) -> int:
    # The shipped value, read from the source: a const() is not a module attribute on MicroPython.
    with open("src/asy_neopixel_driver.py") as f:
        for line in f:
            if line.startswith(name + " = const("):
                return int(line.split("const(", 1)[1].split(")", 1)[0])
    raise AssertionError(name + " not found in src/asy_neopixel_driver.py")


def _colours(driver: NeopixelDriver) -> "list[tuple[int, ...]]":
    return [w[0] for w in _pixel(driver).writes]


def _event_driver() -> NeopixelDriver:
    return make_driver(debug=4)  # DebugLevel 4 (events, SPEC A.8): event-level console lines reach _PrintRecorder


# ---------------------------------------------------------------------------
# Init / logging
# ---------------------------------------------------------------------------


def test_init_bakes_name_into_the_logger() -> None:
    driver = make_driver()
    assert driver.pr.name == "NEOPIXEL"


def test_get_error_counter_forwards_to_the_real_print_log() -> None:
    driver = make_driver()
    log = run(driver.get_error_counter())
    assert log["NEOPIXEL"]["ErrCount"] == 0


def test_get_error_counter_reflects_a_real_logged_error() -> None:
    driver = make_driver()
    run(driver.pr.err_s("boom", errno=1))
    log = run(driver.get_error_counter())
    assert log["NEOPIXEL"]["ErrCount"] == 1


def test_reset_error_counter_returns_true_and_clears() -> None:
    driver = make_driver()
    run(driver.pr.err_s("boom", errno=1))
    assert run(driver.reset_error_counter()) is True
    assert run(driver.get_error_counter())["NEOPIXEL"]["ErrCount"] == 0


# ---------------------------------------------------------------------------
# Overlay behavior: on, off and toggle
# ---------------------------------------------------------------------------


def test_on_sets_pixel_to_overlay_brightness_and_records_a_write() -> None:
    driver = make_driver(led_overl_bri=42)

    async def scenario() -> None:
        tasks = await _start_all_tasks(driver)
        driver.on()
        await asyncio.sleep(0.05)
        await _cancel_all(tasks)

    run(scenario())
    assert _pixel(driver).writes[-1][0] == (42, 42, 42)


def test_off_sets_pixel_to_black_and_records_a_write() -> None:
    driver = make_driver(led_overl_bri=42)

    async def scenario() -> None:
        tasks = await _start_all_tasks(driver)
        driver.on()
        await asyncio.sleep(0.05)
        driver.off()
        await asyncio.sleep(0.05)
        await _cancel_all(tasks)

    run(scenario())
    assert _pixel(driver).writes[-1][0] == (0, 0, 0)


def test_toggle_flips_from_off_to_on() -> None:
    driver = make_driver(led_overl_bri=42)

    async def scenario() -> None:
        tasks = await _start_all_tasks(driver)
        driver.toggle()
        await asyncio.sleep(0.05)
        await _cancel_all(tasks)

    run(scenario())
    assert driver._overlay_on is True
    assert _pixel(driver).writes[-1][0] == (42, 42, 42)


def test_toggle_flips_from_on_to_off() -> None:
    driver = make_driver(led_overl_bri=42)

    async def scenario() -> None:
        tasks = await _start_all_tasks(driver)
        driver.on()
        await asyncio.sleep(0.05)
        driver.toggle()
        await asyncio.sleep(0.05)
        await _cancel_all(tasks)

    run(scenario())
    assert driver._overlay_on is False
    assert _pixel(driver).writes[-1][0] == (0, 0, 0)


def test_repeated_on_is_idempotent_no_crash_one_more_write() -> None:
    driver = make_driver(led_overl_bri=42)

    async def scenario() -> int:
        tasks = await _start_all_tasks(driver)
        driver.on()
        await asyncio.sleep(0.05)
        n_before = len(_pixel(driver).writes)
        driver.on()
        await asyncio.sleep(0.05)
        await _cancel_all(tasks)
        return n_before

    n_before = run(scenario())
    assert len(_pixel(driver).writes) == n_before + 1
    assert _pixel(driver).writes[-1][0] == (42, 42, 42)


def test_overlay_write_deferred_while_ramp_holds_the_overlay_lock() -> None:
    driver = make_driver(led_overl_bri=99)

    async def scenario() -> None:
        tasks = await _start_all_tasks(driver)
        # request_signal() only awaits until the request is queued, not until the ramp itself
        # finishes - create_task here only keeps the scenario reading top-to-bottom; awaiting it
        # directly would return just as fast.
        ramp = asyncio.create_task(driver.request_signal(10, 0, 0, 0.1))
        await asyncio.sleep(0.02)  # ramp has started, is mid-animation, holds _overlay_lock
        assert driver._overlay_lock.locked() is True
        driver.on()  # queued, must not write yet - the lock is still held by the ramp
        await asyncio.sleep(0)
        assert (99, 99, 99) not in [w[0] for w in _pixel(driver).writes]
        await asyncio.sleep(0.2)  # let the ramp fully finish and the overlay task pick up the restore
        await ramp  # long since returned (it only queues) - awaited so no task reference dangles
        await _cancel_all(tasks)

    run(scenario())
    assert _pixel(driver).writes[-1][0] == (99, 99, 99)


# ---------------------------------------------------------------------------
# request_signal() (blocking/internal path)
# ---------------------------------------------------------------------------


def test_request_signal_ramps_up_then_down_and_ends_at_black() -> None:
    driver = make_driver()

    async def scenario() -> None:
        tasks = await _start_all_tasks(driver)
        await driver.request_signal(50, 60, 70, 0.1)
        await asyncio.sleep(0.15)  # let the animation task actually finish committing frames
        await _cancel_all(tasks)

    run(scenario())
    writes = [w[0] for w in _pixel(driver).writes]
    assert writes[-1] == (0, 0, 0)
    assert any(w != (0, 0, 0) for w in writes)  # actually ramped through non-zero frames


def test_request_signal_restores_overlay_on_state_after_ramp() -> None:
    driver = make_driver(led_overl_bri=77)

    async def scenario() -> None:
        tasks = await _start_all_tasks(driver)
        driver.on()
        await asyncio.sleep(0.05)
        await driver.request_signal(10, 0, 0, 0.1)
        await asyncio.sleep(0.15)
        await _cancel_all(tasks)

    run(scenario())
    assert _pixel(driver).writes[-1][0] == (77, 77, 77)


def test_request_signal_restores_overlay_off_state_after_ramp() -> None:
    driver = make_driver(led_overl_bri=77)

    async def scenario() -> None:
        tasks = await _start_all_tasks(driver)
        # overlay never turned on - default state is off
        await driver.request_signal(10, 0, 0, 0.1)
        await asyncio.sleep(0.15)
        await _cancel_all(tasks)

    run(scenario())
    assert _pixel(driver).writes[-1][0] == (0, 0, 0)


def test_two_concurrent_request_signal_calls_run_strictly_sequentially() -> None:
    driver = make_driver()

    async def scenario() -> None:
        tasks = await _start_all_tasks(driver)
        await asyncio.gather(
            driver.request_signal(10, 0, 0, 0.1),
            driver.request_signal(0, 10, 0, 0.1),
        )
        await asyncio.sleep(0.3)  # both ramps' worth of real time, plus margin
        await _cancel_all(tasks)

    run(scenario())
    writes = [w[0] for w in _pixel(driver).writes]
    # A full ramp always ends on (0, 0, 0) before the next one's non-zero frames begin - if the two
    # ramps had interleaved, a red-channel frame and a green-channel frame would appear intermixed
    # instead of in two contiguous blocks each terminated by (0, 0, 0).
    red_frames = [i for i, w in enumerate(writes) if w[0] > 0]
    green_frames = [i for i, w in enumerate(writes) if w[1] > 0]
    assert red_frames and green_frames
    assert max(red_frames) < min(green_frames) or max(green_frames) < min(red_frames)


def test_request_signal_always_returns_true_even_back_to_back() -> None:
    driver = make_driver()

    async def scenario() -> bool:
        tasks = await _start_all_tasks(driver)
        r1 = await driver.request_signal(1, 0, 0, 0.1)
        r2 = await driver.request_signal(0, 1, 0, 0.1)
        await asyncio.sleep(0.3)
        await _cancel_all(tasks)
        return r1 and r2

    assert run(scenario()) is True


def test_request_signal_below_floor_still_produces_at_least_one_step_each_direction() -> None:
    driver = make_driver(neopixel_freq=20)  # matches today's real default

    async def scenario() -> None:
        tasks = await _start_all_tasks(driver)
        await driver.request_signal(10, 0, 0, 0.0)  # below the 0.1s floor
        await asyncio.sleep(0.15)
        await _cancel_all(tasks)

    run(scenario())
    writes = [w[0] for w in _pixel(driver).writes]
    assert (10, 0, 0) in writes  # the single up-step must actually reach full brightness
    assert writes[-1] == (0, 0, 0)


def test_request_signal_low_freq_boundary_never_divides_by_zero() -> None:
    # freq=1 with the 0.1s floor: int(0.1 * 0.5 * 1) == 0 without an explicit steps>=1 clamp - a
    # real ZeroDivisionError risk in the original code's steps_inv = 1.0/steps, not just a
    # theoretical one. Regression test for the exact boundary flagged in the promotion plan.
    driver = make_driver(neopixel_freq=1)

    async def scenario() -> bool:
        tasks = await _start_all_tasks(driver)
        result = await driver.request_signal(10, 0, 0, 0.0)
        await asyncio.sleep(1.5)  # freq=1 -> dt=1s per step, needs real time to actually finish
        await _cancel_all(tasks)
        return result

    result = run(scenario())
    assert result is True
    assert _pixel(driver).writes[-1][0] == (0, 0, 0)


def test_request_signal_large_t_accepted() -> None:
    driver = make_driver(neopixel_freq=20)

    async def scenario() -> bool:
        tasks = await _start_all_tasks(driver)
        result = await driver.request_signal(5, 0, 0, 1.0)
        await asyncio.sleep(1.1)
        await _cancel_all(tasks)
        return result

    result = run(scenario())
    assert result is True
    assert _pixel(driver).writes[-1][0] == (0, 0, 0)


# ---------------------------------------------------------------------------
# led_signal() (non-blocking/external path)
# ---------------------------------------------------------------------------


def test_led_signal_returns_true_and_eventually_ramps_when_idle() -> None:
    driver = make_driver()

    async def scenario() -> bool:
        tasks = await _start_all_tasks(driver)
        result = driver.led_signal(30, 0, 0, 0.1)
        await asyncio.sleep(0.15)
        await _cancel_all(tasks)
        return result

    assert run(scenario()) is True
    assert (30, 0, 0) in [w[0] for w in _pixel(driver).writes]


def test_led_signal_returns_false_for_a_second_call_before_the_first_dispatches() -> None:
    driver = make_driver()

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
    recorder = _PrintRecorder()

    async def scenario() -> "tuple[bool, bool, bool]":
        tasks = await _start_all_tasks(driver)
        await driver.request_signal(10, 0, 0, 0.1)
        assert await _run_until(lambda: any(c[0] > 0 for c in _colours(driver)), 20)
        busy = driver._start_signal_event.is_set()
        result = driver.led_signal(0, 10, 0, 0.1)
        ended = await _run_until(lambda: not driver._start_signal_event.is_set(), 40)
        await _run_until(driver._start_signal_event.is_set, 40)  # a queued request would start here
        await _cancel_all(tasks)
        return busy, result, ended

    with _DrivenClock():
        try:
            busy, result, ended = run(scenario())
        finally:
            recorder.restore()
    assert busy is True
    assert result is False
    assert ended is True
    assert not any(c[1] > 0 for c in _colours(driver))  # the refused colour never reaches the pixel
    assert ("NEOPIXEL", "External LED command refused: busy, retry later.") in recorder.lines


def test_led_signal_is_refused_while_an_internal_request_is_queued_and_no_task_runs() -> None:
    driver = make_driver()

    async def scenario() -> "tuple[bool, bool, bool, bool]":
        queued = await driver.request_signal(10, 0, 0, 0.1)  # no signal task yet: the request stays queued
        refused = driver.led_signal(0, 10, 0, 0.1)  # no await since: the check reads the event, not a task
        tasks = await _start_all_tasks(driver)
        ended = await _run_until(lambda: not driver._start_signal_event.is_set(), 40)
        accepted = driver.led_signal(0, 10, 0, 0.1)
        await _run_until(lambda: not driver._start_signal_event.is_set(), 40)
        await _cancel_all(tasks)
        return queued, refused, ended, accepted

    with _DrivenClock():
        assert run(scenario()) == (True, False, True, True)
    colours = _colours(driver)
    assert max(i for i, c in enumerate(colours) if c[0] > 0) < min(i for i, c in enumerate(colours) if c[1] > 0)


def test_led_signal_color_and_duration_pass_through_unmodified() -> None:
    driver = make_driver()

    async def scenario() -> None:
        tasks = await _start_all_tasks(driver)
        driver.led_signal(12, 34, 56, 0.1)
        await asyncio.sleep(0.15)
        await _cancel_all(tasks)

    run(scenario())
    assert (12, 34, 56) in [w[0] for w in _pixel(driver).writes]


def test_led_signal_accepts_fractional_t_without_truncating() -> None:
    # Regression test for the old `t: int` annotation bug - a fractional duration like 1.5 must
    # actually be honored (more steps/longer ramp), not silently truncated to 1.
    driver = make_driver(neopixel_freq=20)

    async def scenario() -> int:
        tasks = await _start_all_tasks(driver)
        driver.led_signal(10, 0, 0, 1.5)
        await asyncio.sleep(1.6)
        await _cancel_all(tasks)
        return len(_pixel(driver).writes)

    n_writes = run(scenario())
    # steps = int(1.5 * 0.5 * 20) = 15 per direction -> 30 ramp frames + 1 final black frame.
    assert n_writes >= 30


# ---------------------------------------------------------------------------
# Cross-arbitration
# ---------------------------------------------------------------------------


def test_external_and_internal_requests_back_to_back_both_eventually_run() -> None:
    driver = make_driver()

    async def scenario() -> None:
        tasks = await _start_all_tasks(driver)
        driver.led_signal(10, 0, 0, 0.1)
        await driver.request_signal(0, 10, 0, 0.1)
        await asyncio.sleep(0.3)
        await _cancel_all(tasks)

    run(scenario())
    writes = [w[0] for w in _pixel(driver).writes]
    assert any(w[0] > 0 for w in writes)  # the external (red) request was honored
    assert any(w[1] > 0 for w in writes)  # the internal (green) request was honored too


def test_overlay_calls_during_active_ramp_only_become_visible_after_ramp_finishes() -> None:
    driver = make_driver(led_overl_bri=88)

    async def scenario() -> None:
        tasks = await _start_all_tasks(driver)
        # See test_overlay_write_deferred_while_ramp_holds_the_overlay_lock's comment: request_signal()
        # returns once queued, not once the ramp finishes - sleep for the ramp's real duration instead
        # of awaiting the coroutine itself.
        ramp = asyncio.create_task(driver.request_signal(10, 0, 0, 0.15))
        await asyncio.sleep(0.02)
        driver.on()  # requested mid-ramp
        driver.off()  # and immediately reversed - only the final requested state should ever show
        await asyncio.sleep(0.02)
        assert (88, 88, 88) not in [w[0] for w in _pixel(driver).writes]  # not visible mid-ramp
        await asyncio.sleep(0.3)
        await ramp  # long since returned (it only queues) - awaited so no task reference dangles
        await _cancel_all(tasks)

    run(scenario())
    # off() was the last call before the ramp finished - restored state must be off, not on.
    assert _pixel(driver).writes[-1][0] == (0, 0, 0)


def test_request_signal_gives_up_at_its_deadline_when_the_signal_task_never_runs() -> None:
    driver = _event_driver()
    wait_ms = _src_const("_SIGNAL_WAIT_MS")
    frame_ms = 1000 // 100  # make_driver()'s 100 Hz
    recorder = _PrintRecorder()

    async def scenario(clock: _DrivenClock) -> "tuple[bool, bool, bool]":
        driver._start_signal_event.set()  # a signal is queued and its task never runs
        rgbt_before = driver._rgbt
        waiter = asyncio.create_task(driver.request_signal(0, 10, 0, 0.1))
        await asyncio.sleep(0)  # one yield: the waiter takes its deadline at now = 0
        clock.now = wait_ms - frame_ms
        await _run_until(lambda: False, 5)  # several polls at one frame before the deadline
        pending_before = not waiter.done()
        clock.now = wait_ms
        gave_up = await _run_until(waiter.done, 5)
        if not gave_up:
            waiter.cancel()
        try:
            result = await waiter
        except asyncio.CancelledError:
            result = True
        return pending_before, gave_up and result is False, driver._rgbt is rgbt_before

    with _DrivenClock() as clock:
        try:
            pending_before, gave_up_false, untouched = run(scenario(clock))
        finally:
            recorder.restore()
    assert pending_before is True
    assert gave_up_false is True
    assert untouched is True  # the dropped request never replaced the queued values
    assert driver._start_signal_event.is_set() is True
    assert _pixel(driver).writes == []
    assert ("NEOPIXEL", "Internal LED command dropped: signal still busy.") in recorder.lines


def test_request_signal_behind_a_running_ramp_returns_true_only_after_it_ends() -> None:
    driver = make_driver()

    async def scenario() -> "tuple[bool, int]":
        tasks = await _start_all_tasks(driver)
        await driver.request_signal(10, 0, 0, 0.1)
        assert await _run_until(lambda: any(c[0] > 0 for c in _colours(driver)), 20)
        second = asyncio.create_task(driver.request_signal(0, 10, 0, 0.1))
        assert await _run_until(second.done, 40)
        frames_at_return = len(_pixel(driver).writes)
        result = await second
        await _run_until(lambda: not driver._start_signal_event.is_set(), 40)
        await _cancel_all(tasks)
        return result, frames_at_return

    with _DrivenClock():
        result, frames_at_return = run(scenario())
    colours = _colours(driver)
    last_red = max(i for i, c in enumerate(colours) if c[0] > 0)
    assert result is True
    assert colours[last_red + 1 :][:2] == [(0, 0, 0), (0, 0, 0)]  # the ramp's last step, then its final black
    assert frames_at_return >= last_red + 3  # returned only once the first ramp had ended
    assert min(i for i, c in enumerate(colours) if c[1] > 0) > last_red + 2


def test_cancelling_the_signal_task_mid_ramp_leaves_the_pixel_dark_and_the_slot_free() -> None:
    driver = make_driver()

    async def scenario() -> "tuple[tuple[int, ...], bool, list[tuple[int, ...]]]":
        tasks = await _start_all_tasks(driver)
        signal = tasks[1]  # get_task_starters() order: overlay, then signal
        await driver.request_signal(10, 0, 0, 0.5)
        assert await _run_until(lambda: any(c[0] > 0 for c in _colours(driver)), 20)
        await _cancel_all([signal])
        last = _colours(driver)[-1]
        busy = driver._start_signal_event.is_set()
        n = len(_pixel(driver).writes)
        restarted = driver.start_asy_signal()
        await _run_until(lambda: False, 60)  # a replayed ramp of 0.5 s at 100 Hz would show within these steps
        await _cancel_all([t for t in tasks if t is not signal] + [restarted])
        return last, busy, _colours(driver)[n:]

    with _DrivenClock():
        last, busy, after_restart = run(scenario())
    assert last == (0, 0, 0)
    assert busy is False
    assert not any(c[0] > 0 for c in after_restart)  # no frame of the cancelled colour is replayed


def test_a_frame_write_failing_mid_ramp_ends_the_task_with_the_slot_free() -> None:
    driver = make_driver()
    fault = OSError("injected pixel write fault")

    async def scenario() -> "tuple[object, bool]":
        tasks = await _start_all_tasks(driver)
        signal = tasks[1]
        await driver.request_signal(10, 0, 0, 0.5)
        assert await _run_until(lambda: any(c[0] > 0 for c in _colours(driver)), 20)
        _pixel(driver).raise_on_write = fault
        await _run_until(signal.done, 20)
        try:
            await signal
            raised: object = None
        except OSError as e:
            raised = e
        _pixel(driver).raise_on_write = None
        accepted = driver.led_signal(0, 10, 0, 0.1)  # the slot is free again
        await _cancel_all([t for t in tasks if t is not signal])
        return raised, accepted

    with _DrivenClock():
        raised, accepted = run(scenario())
    assert raised is fault  # the failure reaches whoever awaits the task (the supervisor), not swallowed
    assert accepted is True


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------


def test_setup_initialises_the_logger_and_the_driver_before_any_task() -> None:
    driver = NeopixelDriver(0, log=LogConfig(None, 10, None))
    assert driver.pr.initialized is False

    async def scenario() -> bool:
        tasks = await _start_all_tasks(driver)
        started_uninitialised = driver.pr.initialized is False  # no task sets the logger up
        await _cancel_all(tasks)
        return started_uninitialised

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

    async def write_into(self, buf: RegionBuffer) -> bool:
        data = buf.get_data_buf()
        if data is None:
            return False
        self.buf[:] = data
        return True

    async def read_into(self, buf: RegionBuffer) -> bool:
        data = buf.get_data_buf()
        if data is None:
            return False
        data[:] = self.buf
        return True


class _FakeFramManager:
    def __init__(self, chunk: "_FakeFramChunk") -> None:
        self.chunk = chunk

    def get_chunk(self, size: int, crc: "CRCBase | None" = None, verify: int = 0, check_length: int = 8, *, owner: str) -> "_FakeFramChunk":
        return self.chunk


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
    driver = make_driver()
    assert type(driver.pr).__name__ == "PrintLogHistory"  # not the FRAM-backed subclass

    async def scenario() -> None:
        tasks = await _start_all_tasks(driver)
        await driver.request_signal(1, 0, 0, 0.1)
        await asyncio.sleep(0.15)
        await _cancel_all(tasks)

    run(scenario())
    assert _pixel(driver).writes[-1][0] == (0, 0, 0)


# ---------------------------------------------------------------------------
# _clamp_byte() - a real NeoPixel's __setitem__ writes straight into a bytearray and raises ValueError for
# an out-of-range int (confirmed against micropython-lib's real neopixel.py). The callers are correctly-
# typed int/float, all being our own code, but can still legitimately be out-of-range or NaN.
# ---------------------------------------------------------------------------


def test_clamp_byte_direct() -> None:
    assert _clamp_byte(0) == 0
    assert _clamp_byte(255) == 255
    assert _clamp_byte(-1) == 0
    assert _clamp_byte(256) == 255
    assert _clamp_byte(300) == 255
    assert _clamp_byte(3.9) == 3  # int() truncates, matches every other rgb value in this file
    assert _clamp_byte(value=True) == 1  # bool is a legitimate int subtype for a byte value
    # int(inf) raises OverflowError, int(nan) ValueError (Part F.1, v1.29.0). Regression test for the gap
    # _clamp_byte()'s original except (TypeError, ValueError) clause missed entirely.
    assert _clamp_byte(float("inf")) == 0
    assert _clamp_byte(float("-inf")) == 0
    assert _clamp_byte(float("nan")) == 0  # int(nan) raises ValueError - already covered, kept for completeness
    assert _clamp_byte("12") == 0  # not a number: no byte value
    assert _clamp_byte(None) == 0


def test_request_signal_infinite_rgb_clamped_not_raised() -> None:
    driver = make_driver()

    async def scenario() -> None:
        tasks = await _start_all_tasks(driver)
        await driver.request_signal(float("inf"), 0, float("-inf"), 0.1)  # type: ignore[arg-type]
        await asyncio.sleep(0.15)
        await _cancel_all(tasks)

    run(scenario())  # would raise OverflowError out of the pixel write if unclamped
    writes = [w[0] for w in _pixel(driver).writes]
    assert all(w[0] == 0 for w in writes)  # inf clamped to 0, not the byte ceiling
    assert all(w[2] == 0 for w in writes)
    assert writes[-1] == (0, 0, 0)


# ---------------------------------------------------------------------------
# A non-finite t is mapped to the 0.1 s floor by _signal_values() before any ramp runs.
# ---------------------------------------------------------------------------


def test_request_signal_infinite_duration_falls_back_to_floor_not_raised() -> None:
    driver = make_driver(neopixel_freq=20)

    async def scenario() -> bool:
        tasks = await _start_all_tasks(driver)
        result = await driver.request_signal(10, 0, 0, float("inf"))
        await asyncio.sleep(0.15)  # only survivable if t fell back to the 0.1s floor, not inf
        await _cancel_all(tasks)
        return result

    result = run(scenario())  # would raise OverflowError computing steps if unclamped
    assert result is True
    assert _pixel(driver).writes[-1][0] == (0, 0, 0)


def test_request_signal_nan_duration_falls_back_to_floor_not_raised() -> None:
    driver = make_driver(neopixel_freq=20)

    async def scenario() -> bool:
        tasks = await _start_all_tasks(driver)
        result = await driver.request_signal(10, 0, 0, float("nan"))
        await asyncio.sleep(0.15)  # only survivable if t fell back to the 0.1s floor - NaN >= 0.1 is False
        await _cancel_all(tasks)
        return result

    result = run(scenario())
    assert result is True
    assert _pixel(driver).writes[-1][0] == (0, 0, 0)


def test_request_signal_out_of_range_rgb_clamped_not_raised() -> None:
    driver = make_driver()

    async def scenario() -> None:
        tasks = await _start_all_tasks(driver)
        await driver.request_signal(300, -5, 999, 0.1)  # a future misbehaving caller
        await asyncio.sleep(0.15)
        await _cancel_all(tasks)

    run(scenario())  # would raise ValueError out of the pixel write if unclamped
    writes = [w[0] for w in _pixel(driver).writes]
    assert any(w[0] == 255 for w in writes)  # 300 clamped to the byte ceiling
    assert all(w[1] == 0 for w in writes)  # -5 clamped to the floor
    assert any(w[2] == 255 for w in writes)  # 999 clamped to the byte ceiling
    assert writes[-1] == (0, 0, 0)


def test_led_signal_out_of_range_rgb_clamped_not_raised() -> None:
    driver = make_driver()

    async def scenario() -> None:
        tasks = await _start_all_tasks(driver)
        driver.led_signal(-10, 500, 0, 0.1)
        await asyncio.sleep(0.15)
        await _cancel_all(tasks)

    run(scenario())
    writes = [w[0] for w in _pixel(driver).writes]
    assert all(w[0] == 0 for w in writes)
    assert any(w[1] == 255 for w in writes)


def test_overlay_bri_out_of_range_clamped_not_raised() -> None:
    driver = make_driver(led_overl_bri=999)

    async def scenario() -> None:
        tasks = await _start_all_tasks(driver)
        driver.on()
        await asyncio.sleep(0.05)
        await _cancel_all(tasks)

    run(scenario())  # would raise ValueError out of the pixel write if unclamped
    assert _pixel(driver).writes[-1][0] == (255, 255, 255)


def test_a_non_numeric_signal_value_is_refused_without_a_frame() -> None:
    cases = ((None, 0, 0, 0.5), ("10", 0, 0, 0.5), (10, 0, 0, "1"))
    for r, g, b, t in cases:
        driver = make_driver()

        async def scenario(d: NeopixelDriver = driver, r: object = r, g: object = g, b: object = b, t: object = t) -> "tuple[bool, bool]":
            internal = await d.request_signal(r, g, b, t)  # type: ignore[arg-type]
            external = d.led_signal(r, g, b, t)  # type: ignore[arg-type]
            tasks = await _start_all_tasks(d)
            await _run_until(lambda: len(_pixel(d).writes) > 1, 20)
            await _cancel_all(tasks)
            return internal, external

        with _DrivenClock():
            assert run(scenario()) == (False, False), (r, g, b, t)
        assert driver._start_signal_event.is_set() is False
        assert _colours(driver) == [(0, 0, 0)]  # only the signal task's own start frame


def _single_signal_frames(t: float) -> "list[tuple[int, ...]]":
    # The signal task alone at the real 20 Hz: its start frame, the ramp, then the final black.
    driver = make_driver(neopixel_freq=20)

    async def scenario() -> bool:
        signal = driver.start_asy_signal()
        await driver.request_signal(255, 0, 0, t)
        ended = await _run_until(lambda: not driver._start_signal_event.is_set(), 4000)
        await _cancel_all([signal])
        return ended

    with _DrivenClock():
        assert run(scenario()) is True
    return _colours(driver)


def test_a_long_signal_is_capped_at_sixty_seconds() -> None:
    frames = _single_signal_frames(600.0)
    assert (len(frames) - 2) // 2 == int(60 * 0.5 * 20)  # steps per direction, from the frames recorded
    assert len(frames) == 2 + 2 * int(60 * 0.5 * 20)
    assert frames[-1] == (0, 0, 0)


def test_a_negative_duration_takes_the_floor() -> None:
    assert _single_signal_frames(-1.0) == [(0, 0, 0), (255, 0, 0), (0, 0, 0), (0, 0, 0)]  # one step each way


# ---------------------------------------------------------------------------
# Error/edge cases
# ---------------------------------------------------------------------------


def test_get_task_starters_returns_the_overlay_and_signal_starters() -> None:
    driver = make_driver()
    assert [s.__name__ for s in driver.get_task_starters()] == ["start_asy_overlay", "start_asy_signal"]


def test_get_timer_starters_returns_empty_list() -> None:
    driver = make_driver()
    assert driver.get_timer_starters() == []


def test_on_off_toggle_satisfy_led_control_protocol_signatures() -> None:
    driver = make_driver()
    assert callable(driver.on)
    assert callable(driver.off)
    assert callable(driver.toggle)
    driver.on()
    driver.off()
    driver.toggle()  # no exception for any of the three, no task running at all


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
