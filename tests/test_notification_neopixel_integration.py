"""Cross-module integration: a real asy_neopixel_driver.py.NeopixelDriver wired to a real
asy_notification_service.py.NotificationService via request_signal_cb=pixel.request_signal - the shape every generated
sensortask module wires (SPECIFICATION.md L.2).

Only tests/neopixel.py's fake write surface is mocked; overlay/arbitration, the poll loop, gating, config, and logging
all run for real end to end.
"""

import asyncio

from _async_harness import cancel_all, run
from _fake_time import DrivenTime, FakeTime, Rp2Gmtime
from _tmp_scratch import TmpScratch

import asy_base_classes
import asy_neopixel_driver
import asy_notification_service
import asy_ntp_client
from asy_base_classes import ValueRef
from asy_neopixel_driver import NeopixelDriver
from asy_notification_service import NotificationService, NotificationSignal
from asy_ntp_client import NTPClient, NtpTiming

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing isn't available on the real MicroPython test interpreter
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from typing import Protocol

    class _HourMinute(Protocol):
        # The local-time callback's answer as the service reads it (its own _LocalTime): read-only hour and minute.
        @property
        def hour(self) -> int: ...
        @property
        def minute(self) -> int: ...


class _FakeSource:
    # A controllable NotificationSignal producer (Part C.14.3): get_data() returns self, exposing exactly
    # one attribute - whatever field name the caller configures - at a fixed value, matching every removed
    # inline closure's own fixed-return shape.
    def __init__(self, field: str, value: int) -> None:
        setattr(self, field, value)

    async def get_data(self) -> "_FakeSource":
        return self


# Per-test config-file isolation via the shared tests/_tmp_scratch.py helper - see that
# module's own docstring and tests/test_tmp_scratch.py for the mechanism/regression coverage.
_scratch = TmpScratch("notify_neopixel")


def _co2_signal(value: int = 2000) -> NotificationSignal:
    return NotificationSignal("WarnCO2", ValueRef(_FakeSource("WarnCO2", value), "WarnCO2"), (("WarnCO2", "int", 1600, 0, 3000, None),), (1, 0, 0))


async def _cycle(clock: DrivenTime, notify: NotificationService, flashes: int, ramp_ms: int | None = None) -> None:
    # The monitor's first cycle by the service's own rule: each flash's ramp (FlashDur on a real LED), then FlashDur
    # dark, so 1 ms before that end the loop has not parked on its next cycle yet; then it parks FlashInterval after.
    cfg = (await notify.get_dict_cfg())["NOTIFY"]
    flash_dur, interval = cfg["FlashDur"], cfg["FlashInterval"]
    assert isinstance(flash_dur, float) and isinstance(interval, float), cfg
    start = clock.now
    end = start + flashes * ((round(flash_dur * 1000) if ramp_ms is None else ramp_ms) + round(flash_dur * 1000))
    if end > start:
        await clock.elapse(end - 1 - start)
        assert start + round(interval * 1000) not in clock.wakes(), f"the cycle ended by virtual t={clock.now} ms: {clock.wakes()}"
    await clock.elapse(end - clock.now)
    assert clock.wakes()[-1] == start + round(interval * 1000), f"at virtual t={clock.now} ms the loop waits for {clock.wakes()}"


def _driven() -> DrivenTime:
    # The driver's and the service's time and asyncio on one driven clock for the block: every frame, settle, overlay
    # and pause wait parks on it, and time moves only when the test moves it.
    return DrivenTime(asy_neopixel_driver, asy_notification_service, sleeps=True)


def _lit_frames(pixel: NeopixelDriver) -> "list[tuple[int, ...]]":
    return [w[0] for w in pixel._pixel.writes if w[0] != (0, 0, 0)]


async def _local_time() -> FakeTime:
    return FakeTime(12, 0)


def _make_pair(
    signals: "tuple[NotificationSignal, ...]", local_time: "Callable[[], Awaitable[_HourMinute | None]]" = _local_time,
) -> "tuple[NeopixelDriver, NotificationService]":
    pixel = NeopixelDriver(0)  # at the shipped frame rate: FlashDur's 0.5 s floor still plays several frames a direction
    notify = NotificationService(pixel.request_signal, local_time, signals, cfg_path=_tmp_cfg_dir())
    run(notify.setup())
    return pixel, notify


def _ramp_ms(pixel: NeopixelDriver, flash_dur: float) -> int:
    # One signal's length on the driven clock, by the driver's own steps rule (_signal_loop): both directions' frames
    # at the frame period; its final black lands at that instant.
    return 2 * max(int(flash_dur * 0.5 * pixel.neopixel_freq), 1) * pixel._frame_ms


def _ramp_over(pixel: NeopixelDriver) -> bool:
    # A ramp has played and ended: a lit frame, black last, and no signal queued or running.
    writes = pixel._pixel.writes
    return bool(_lit_frames(pixel)) and writes[-1][0] == (0, 0, 0) and not pixel._pending


async def _start_all(pixel: NeopixelDriver, notify: NotificationService) -> "list[asyncio.Task[None]]":
    tasks = [s() for s in pixel.get_task_starters()] + [s() for s in notify.get_task_starters()]
    await asyncio.sleep(0)  # one yield lets each task park on its first wait (a limit, not an interleaving claim)
    return tasks


def _tmp_cfg_dir() -> str:
    return _scratch.dir()


def test_real_threshold_crossing_produces_an_actual_ramp_with_scaled_color() -> None:
    source = _FakeSource("WarnCO2", 2000)  # above the 1600 default threshold
    signal = NotificationSignal("WarnCO2", ValueRef(source, "WarnCO2"), (("WarnCO2", "int", 1600, 0, 3000, None),), (1, 0, 0))
    pixel, notify = _make_pair((signal,))

    async def scenario(clock: DrivenTime) -> None:
        await notify._set_dict_cfg({"FlashInterval": 3600.0, "FlashDur": 0.5}, notify.get_cfg_schema())
        tasks = await _start_all(pixel, notify)
        await _cycle(clock, notify, 1)
        await cancel_all(tasks, settle_yields=1)

    with _driven() as clock:
        run(scenario(clock))
    writes = [w[0] for w in pixel._pixel.writes]
    assert (200, 0, 0) in writes  # scaled by the default FlashBri=200, pure red channel
    assert writes[-1] == (0, 0, 0)  # ramp ends black


def test_multiple_simultaneous_crossings_produce_sequential_correctly_colored_ramps() -> None:
    co2 = NotificationSignal(
        "WarnCO2", ValueRef(_FakeSource("WarnCO2", 2000), "WarnCO2"), (("WarnCO2", "int", 1600, 0, 3000, None),), (1, 0, 0),
    )
    voc = NotificationSignal(
        "WarnVOC", ValueRef(_FakeSource("WarnVOC", 400), "WarnVOC"), (("WarnVOC", "int", 350, 0, 500, None),), (0, 1, 0),
    )
    pixel, notify = _make_pair((co2, voc))

    async def scenario(clock: DrivenTime) -> None:
        await notify._set_dict_cfg({"FlashInterval": 3600.0, "FlashDur": 0.5}, notify.get_cfg_schema())
        tasks = await _start_all(pixel, notify)
        await _cycle(clock, notify, 2)  # one settle after the other, in registration order
        await cancel_all(tasks, settle_yields=1)

    with _driven() as clock:
        run(scenario(clock))
    writes = [w[0] for w in pixel._pixel.writes]
    red_frames = [i for i, w in enumerate(writes) if w[0] > 0]
    green_frames = [i for i, w in enumerate(writes) if w[1] > 0]
    assert red_frames and green_frames
    # registration order (CO2 then VOC) must produce a fully-contiguous red block before any green
    # frame, not interleaved - the same real arbitration primitive both entrypoints share.
    assert max(red_frames) < min(green_frames)


def test_led_signal_during_a_notification_ramp_is_refused_at_once() -> None:
    pixel, notify = _make_pair((_co2_signal(),))

    async def scenario(clock: DrivenTime) -> "tuple[int, bool, int]":
        await notify._set_dict_cfg({"FlashInterval": 3600.0, "FlashDur": 0.5}, notify.get_cfg_schema())
        tasks = await _start_all(pixel, notify)
        lit_at = await clock.run_until(lambda: bool(_lit_frames(pixel)), 0)  # the first frame lands with the request
        result = pixel.led_signal(11, 22, 33, 0.1)  # the REST command, sync: refused or not with no await
        ended_at = await clock.run_until(lambda: _ramp_over(pixel), _ramp_ms(pixel, 0.5))
        await cancel_all(tasks, settle_yields=1)
        return lit_at, result, ended_at

    with _driven() as clock:
        lit_at, result, ended_at = run(scenario(clock))
    assert lit_at == 0
    assert result is False  # refused at once, never queued
    assert ended_at == _ramp_ms(pixel, 0.5)  # the ramp's own length, with nothing queued behind it
    assert (11, 22, 33) not in [w[0] for w in pixel._pixel.writes]
    assert run(notify.get_error_counter())["NOTIFY"]["ErrCount"] == 0  # the notification's own request went through


def test_a_notification_behind_a_busy_led_waits_its_turn_and_plays_with_no_entry() -> None:
    # A REST command's 1 s ramp holds the LED: the flash waits on the lock, plays in full after it, and logs nothing.
    pixel, notify = _make_pair((_co2_signal(),))
    assert pixel.led_signal(0, 0, 50, 1.0) is True

    async def scenario(clock: DrivenTime) -> None:
        await notify._set_dict_cfg({"FlashInterval": 3600.0, "FlashDur": 0.5}, notify.get_cfg_schema())
        tasks = await _start_all(pixel, notify)
        await _cycle(clock, notify, 1, _ramp_ms(pixel, 1.0) + _ramp_ms(pixel, 0.5))  # behind the busy ramp
        await cancel_all(tasks, settle_yields=1)

    with _driven() as clock:
        run(scenario(clock))
    assert run(notify.get_error_counter())["NOTIFY"]["ErrCount"] == 0
    lit = _lit_frames(pixel)
    assert (0, 0, 50) in lit and (200, 0, 0) in lit  # both played, the busy one first
    assert lit.index((0, 0, 50)) < lit.index((200, 0, 0)), lit


def test_the_window_check_reads_a_real_ntp_clock() -> None:
    # The production local-time callback: a real NTP client's cettime(), marked synced by the test.
    ntp = NTPClient(asyncio.Lock(), lambda: True, lambda: None, NtpTiming(1000, 5000), cfg_path=_tmp_cfg_dir())
    run(ntp.cfgmgr.setup())
    run(ntp._set_synced(value=True))

    def window_cycle(on_min: int, off_min: int, flashes: int) -> "list[tuple[int, ...]]":
        pixel, notify = _make_pair((_co2_signal(),), local_time=ntp.cettime)
        cfg: dict[str, int | float | str | bool | None] = {"OnH": on_min // 60, "OnM": on_min % 60, "OffH": off_min // 60, "OffM": off_min % 60, "FlashInterval": 3600.0, "FlashDur": 0.5}

        async def scenario(clock: DrivenTime) -> None:
            await notify._set_dict_cfg(cfg, notify.get_cfg_schema())
            tasks = await _start_all(pixel, notify)
            await _cycle(clock, notify, flashes)
            await cancel_all(tasks, settle_yields=1)

        with _driven() as clock:
            run(scenario(clock))
        return _lit_frames(pixel)

    original = asy_ntp_client.time
    asy_ntp_client.time = Rp2Gmtime()  # type: ignore[assignment]  # rp2's 8-field gmtime(), which cettime() checks for
    asy_base_classes.set_utc_valid()  # the clock the sync set: cettime() answers only once it is set
    try:
        now = run(ntp.cettime())
        assert now is not None
        cur = now.hour * 60 + now.minute
        assert window_cycle((cur - 5) % 1440, (cur + 5) % 1440, 1)  # around the NTP time: the signal flashes
        assert window_cycle((cur + 60) % 1440, (cur + 120) % 1440, 0) == []  # an hour away from it: dark
    finally:
        asy_ntp_client.time = original
        asy_base_classes._utc_valid = False


def test_a_service_on_the_default_sink_completes_a_cycle_silently() -> None:
    sink = asy_notification_service._DefaultSignalSink()
    notify = NotificationService(sink.request_signal, _local_time, (_co2_signal(),), cfg_path=_tmp_cfg_dir())
    run(notify.setup())

    async def scenario(clock: DrivenTime) -> None:
        await notify._set_dict_cfg({"FlashInterval": 3600.0, "FlashDur": 0.5}, notify.get_cfg_schema())
        task = notify.start_asy_monitor()
        await _cycle(clock, notify, 1, 0)  # the default sink returns at once: FlashDur dark, no ramp
        await cancel_all([task])

    with _driven() as clock:
        run(scenario(clock))
    assert run(notify.get_error_counter())["NOTIFY"]["ErrCount"] == 0  # the default sink's False logs nothing


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
