import asyncio

from asy_neopixel_driver import NeopixelDriver, _clamp_byte, _safe_duration

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing isn't available on the real MicroPython test interpreter
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Coroutine
    from typing import Any, TypeVar

    T = TypeVar("T")


def run(coro: "Coroutine[Any, Any, T]") -> "T":  # drives a coroutine to completion for these sync test_* functions
    return asyncio.run(coro)


def _pixel(driver: NeopixelDriver) -> "Any":
    # tests/neopixel.py's fake, reached through the driver's own attribute - same narrowing
    # convention as test_asy_wifi_service.py's own _wlan() helper.
    return driver.pixel


def make_driver(neopixel_freq: int = 100, led_overl_bri: int = 50, debug: "int | None" = None) -> NeopixelDriver:
    # freq=100 (vs. the real 20 default) keeps every ramp's step count high enough (5 steps per
    # direction at the t=0.1 floor) to observe mid-ramp state, while keeping real wall-clock ramp
    # time short (~0.1s: 10 frames * 0.01s dt) - this file's tests drive real asyncio.sleep(), not a
    # simulated clock, so keeping every ramp fast matters for suite runtime.
    return NeopixelDriver(0, neopixel_freq=neopixel_freq, led_overl_bri=led_overl_bri, debug=debug)


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


# ---------------------------------------------------------------------------
# Overlay (on/off/toggle)
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
    assert driver.led_overl_on is True
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
    assert driver.led_overl_on is False
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
        # finishes (see this file's own module docstring) - create_task here is just to keep the
        # scenario reading top-to-bottom; awaiting it directly would return just as fast.
        asyncio.create_task(driver.request_signal(10, 0, 0, 0.1))
        await asyncio.sleep(0.02)  # ramp has started, is mid-animation, holds led_overl_lock
        assert driver.led_overl_lock.locked() is True
        driver.on()  # queued, must not write yet - the lock is still held by the ramp
        await asyncio.sleep(0)
        assert (99, 99, 99) not in [w[0] for w in _pixel(driver).writes]
        await asyncio.sleep(0.2)  # let the ramp fully finish and the overlay task pick up the restore
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
        # No task started at all - proves this is a synchronous, single-threaded-atomicity check
        # (ext_start_signal.is_set()), not something that needs the relay task to run first.
        r1 = driver.led_signal(30, 0, 0, 0.1)
        r2 = driver.led_signal(0, 30, 0, 0.1)  # zero `await` since r1 - must already see it pending
        return r1, r2

    r1, r2 = run(scenario())
    assert r1 is True
    assert r2 is False


def test_led_signal_returns_true_while_a_previous_request_is_already_animating() -> None:
    # The "must NOT check .locked()" case: start_signal_lock is released again right after a
    # request is queued (see request_signal()'s own body) - it is NOT the busy signal for an
    # in-progress ramp. start_signal_event stays set for the ramp's whole real duration instead,
    # and ext_start_signal (led_signal()'s own one-slot flag) is untouched by an internal request.
    # A wrong implementation using start_signal_lock.locked() as led_signal()'s busy check would
    # see it unlocked here and behave correctly by accident in this specific scenario, but would
    # then wrongly ignore a second real external request already pending - this test instead pins
    # down what the actual state looks like mid-ramp, so a future change can't silently start
    # gating led_signal() on the wrong primitive.
    driver = make_driver()

    async def scenario() -> bool:
        tasks = await _start_all_tasks(driver)
        asyncio.create_task(driver.request_signal(10, 0, 0, 0.3))  # long-ish ramp, still running below
        await asyncio.sleep(0.02)
        assert driver.start_signal_event.is_set() is True  # an animation is genuinely in progress
        assert driver.start_signal_lock.locked() is False  # released right after queuing
        assert driver.ext_start_signal.is_set() is False  # led_signal()'s own slot is free
        result = driver.led_signal(0, 10, 0, 0.1)
        await asyncio.sleep(0.6)  # let both ramps fully finish
        await _cancel_all(tasks)
        return result

    assert run(scenario()) is True


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
        asyncio.create_task(driver.request_signal(10, 0, 0, 0.15))
        await asyncio.sleep(0.02)
        driver.on()  # requested mid-ramp
        driver.off()  # and immediately reversed - only the final requested state should ever show
        await asyncio.sleep(0.02)
        assert (88, 88, 88) not in [w[0] for w in _pixel(driver).writes]  # not visible mid-ramp
        await asyncio.sleep(0.3)
        await _cancel_all(tasks)

    run(scenario())
    # off() was the last call before the ramp finished - restored state must be off, not on.
    assert _pixel(driver).writes[-1][0] == (0, 0, 0)


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------


def test_pr_setup_runs_before_any_ramp_is_committed() -> None:
    driver = make_driver()
    assert driver.pr.initialized is False

    async def scenario() -> None:
        tasks = await _start_all_tasks(driver)
        assert driver.pr.initialized is True  # neopixel_signal() calls pr.setup() before its first wait
        await _cancel_all(tasks)

    run(scenario())


class _FakeFramChunk:
    def __init__(self) -> None:
        self.buf = bytearray(64)

    def get_buffer(self) -> "Any":
        return self

    def get_data_buf(self) -> bytearray:
        return self.buf

    async def write_into(self, buf: "Any", override_pause: bool = False) -> bool:
        self.buf[:] = buf.get_data_buf()
        return True

    async def read_into(self, buf: "Any", override_pause: bool = False) -> bool:
        buf.get_data_buf()[:] = self.buf
        return True


class _FakeFramManager:
    def __init__(self, chunk: "_FakeFramChunk") -> None:
        self.chunk = chunk

    def get_chunk(self, size: int, crc: "Any" = None, verify: int = 0, check_length: int = 8) -> "_FakeFramChunk":
        return self.chunk


def test_fram_backed_variant_survives_a_reboot() -> None:
    chunk = _FakeFramChunk()
    fram = _FakeFramManager(chunk)
    driver1 = NeopixelDriver(0, fram=fram)  # type: ignore[arg-type]  # structurally satisfies the Protocol

    async def scenario1() -> None:
        await driver1.pr.setup()  # FRAM persistence is inert until setup() runs - matches every
        # other module's real main-loop convention (see base_classes.py's module docstring)
        await driver1.pr.err_s("boom", errno=1)

    run(scenario1())

    driver2 = NeopixelDriver(0, fram=fram)  # type: ignore[arg-type]

    async def scenario2() -> None:
        await driver2.pr.setup()

    run(scenario2())
    assert driver2.pr.err_count == driver1.pr.err_count


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
# _clamp_byte() - a real NeoPixel's __setitem__ writes straight into a bytearray and raises
# ValueError/TypeError for an out-of-range or non-int value (confirmed against micropython-lib's
# real neopixel.py source) - request_signal()/led_signal()/led_overl_bri are only type/range-hinted
# at their current callers, not enforced by this driver, so every write to the physical pixel must
# survive a misbehaving caller (current or future) without raising.
# ---------------------------------------------------------------------------


def test_clamp_byte_direct() -> None:
    assert _clamp_byte(0) == 0
    assert _clamp_byte(255) == 255
    assert _clamp_byte(-1) == 0
    assert _clamp_byte(256) == 255
    assert _clamp_byte(300) == 255
    assert _clamp_byte(3.9) == 3  # int() truncates, matches every other rgb value in this file
    assert _clamp_byte("nope") == 0
    assert _clamp_byte(None) == 0
    assert _clamp_byte(True) == 1  # bool is a legitimate int subtype for a byte value
    # int(float('inf'))/int(float('-inf')) raise OverflowError specifically, not ValueError -
    # confirmed directly against the real MicroPython 1.28.0 Unix-port interpreter. Regression test
    # for the gap _clamp_byte()'s original except (TypeError, ValueError) clause missed entirely.
    assert _clamp_byte(float("inf")) == 0
    assert _clamp_byte(float("-inf")) == 0
    assert _clamp_byte(float("nan")) == 0  # int(nan) raises ValueError - already covered, kept for completeness


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
# _safe_duration() - rgbt[3]/ext_rgbt[3] ("t") is only type/range-hinted at request_signal()/
# led_signal()'s callers, same caveat as the rgb channels above. A non-numeric t raises TypeError
# out of the "t >= 0.1" floor check in neopixel_signal(); t=inf passes that check and then raises
# OverflowError out of the steps computation right after.
# ---------------------------------------------------------------------------


def test_safe_duration_direct() -> None:
    assert _safe_duration(0.1) == 0.1
    assert _safe_duration(5) == 5
    assert _safe_duration(0) == 0
    assert _safe_duration(float("inf")) == 0.0
    assert _safe_duration(float("-inf")) == 0.0
    assert _safe_duration("nope") == 0.0
    assert _safe_duration(None) == 0.0
    assert _safe_duration([1, 2]) == 0.0
    nan = _safe_duration(float("nan"))
    assert nan != nan  # NaN passes through unchanged - the existing ">= 0.1" floor already handles it


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


def test_led_signal_non_numeric_duration_falls_back_to_floor_not_raised() -> None:
    driver = make_driver(neopixel_freq=20)

    async def scenario() -> None:
        tasks = await _start_all_tasks(driver)
        driver.led_signal(10, 0, 0, "bad")  # type: ignore[arg-type]
        await asyncio.sleep(0.15)
        await _cancel_all(tasks)

    run(scenario())  # would raise TypeError out of the ">= 0.1" comparison if unclamped
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


def test_request_signal_non_numeric_rgb_clamped_to_zero_not_raised() -> None:
    driver = make_driver()

    async def scenario() -> None:
        tasks = await _start_all_tasks(driver)
        await driver.request_signal("red", None, 100, 0.1)  # type: ignore[arg-type]
        await asyncio.sleep(0.15)
        await _cancel_all(tasks)

    run(scenario())  # would raise TypeError/ValueError out of the pixel write if unclamped
    writes = [w[0] for w in _pixel(driver).writes]
    assert all(w[0] == 0 for w in writes)
    assert all(w[1] == 0 for w in writes)
    assert any(w[2] == 100 for w in writes)


def test_overlay_bri_out_of_range_clamped_not_raised() -> None:
    driver = make_driver(led_overl_bri=999)

    async def scenario() -> None:
        tasks = await _start_all_tasks(driver)
        driver.on()
        await asyncio.sleep(0.05)
        await _cancel_all(tasks)

    run(scenario())  # would raise ValueError out of the pixel write if unclamped
    assert _pixel(driver).writes[-1][0] == (255, 255, 255)


# ---------------------------------------------------------------------------
# Error/edge cases
# ---------------------------------------------------------------------------


def test_get_task_starters_returns_three_callables() -> None:
    driver = make_driver()
    starters = driver.get_task_starters()
    assert len(starters) == 3
    for s in starters:
        assert callable(s)


def test_get_timer_starters_returns_empty_list() -> None:
    driver = make_driver()
    assert driver.get_task_starters is not None
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
