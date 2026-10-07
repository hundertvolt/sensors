"""Cross-module integration: a real asy_neopixel_driver.py.NeopixelDriver wired to a real
asy_notification_service.py.NotificationCoordinator via request_signal_cb=pixel.request_signal - the shape every generated sensortask module wires (SPECIFICATION.md L.2).
Only tests/neopixel.py's fake write surface is mocked; overlay/arbitration, the poll loop, gating, config, and logging all run for real end to end.
"""

import asyncio
import time

from _error_codes import code
from _tmp_scratch import TmpScratch

import asy_neopixel_driver
import asy_notification_service
import asy_ntp_client
from asy_neopixel_driver import NeopixelDriver
from asy_notification_service import NotificationCoordinator, NotificationSignal
from asy_ntp_client import AsyNtpClient, NtpTiming
from base_classes import ValueRef

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing isn't available on the real MicroPython test interpreter
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
    from typing import Any, TypeVar

    T = TypeVar("T")


def run(coro: "Coroutine[Any, Any, T]") -> "T":  # drives a coroutine to completion for these sync test_* functions
    return asyncio.run(coro)


class _FakeTime:
    def __init__(self, hour: int, minute: int) -> None:
        self.hour = hour
        self.minute = minute


async def _local_time() -> _FakeTime:
    return _FakeTime(12, 0)


class _FakeSource:
    # A controllable NotificationSignal producer (Part C.14.2): get_data() returns self, exposing exactly
    # one attribute - whatever field name the caller configures - at a fixed value, matching every removed
    # inline closure's own fixed-return shape.
    def __init__(self, field: str, value: int) -> None:
        setattr(self, field, value)

    async def get_data(self) -> "_FakeSource":
        return self


# Per-test config-file isolation via the shared tests/_tmp_scratch.py helper - see that
# module's own docstring and tests/test_tmp_scratch.py for the mechanism/regression coverage.
_scratch = TmpScratch("notify_neopixel")


def _tmp_cfg_dir() -> str:
    return _scratch.dir()


_FREQ_HZ = 100
_FRAME_S = 1.0 / _FREQ_HZ  # the pixel's frame period, also the pace of every condition poll below


def make_pair(
    signals: "tuple[NotificationSignal, ...]", local_time: "Callable[[], Coroutine[Any, Any, Any]]" = _local_time,
) -> "tuple[NeopixelDriver, NotificationCoordinator]":
    # freq=100 keeps ramps fast in real wall-clock time (same reasoning as
    # tests/test_asy_neopixel_driver.py's own make_driver()).
    pixel = NeopixelDriver(0, neopixel_freq=_FREQ_HZ)
    notify = NotificationCoordinator(pixel.request_signal, local_time, signals, cfg_path=_tmp_cfg_dir())
    return pixel, notify


def _co2_signal(value: int = 2000) -> NotificationSignal:
    return NotificationSignal("WarnCO2", ValueRef(_FakeSource("WarnCO2", value), "WarnCO2"), (("WarnCO2", "int", 1600, 0, 3000, None),), (1, 0, 0))


# A hang guard only: every condition below holds once a ramp of at most a second has played.
# @tunable l1.notification_neopixel_wait_until_timeout_ms = 10000
_WAIT_UNTIL_TIMEOUT_MS = 10000


async def _wait_until(predicate: "Callable[[], bool]") -> bool:
    # Polls once per frame period; False once the guard runs out.
    t0 = time.ticks_ms()
    while not predicate():
        if time.ticks_diff(time.ticks_ms(), t0) > _WAIT_UNTIL_TIMEOUT_MS:
            return False
        await asyncio.sleep(_FRAME_S)
    return True


def _lit_frames(pixel: NeopixelDriver) -> "list[tuple[int, ...]]":
    return [w[0] for w in pixel.pixel.writes if w[0] != (0, 0, 0)]


def _ramp_over(pixel: NeopixelDriver) -> bool:
    # A ramp has played and ended: a lit frame, black last, and no signal queued or running.
    writes = pixel.pixel.writes
    return bool(_lit_frames(pixel)) and writes[-1][0] == (0, 0, 0) and not pixel.start_signal_event.is_set()


async def _start_all(pixel: NeopixelDriver, notify: NotificationCoordinator) -> "list[asyncio.Task[None]]":
    tasks = [s() for s in pixel.get_task_starters()] + [s() for s in notify.get_task_starters()]
    await asyncio.sleep(0)
    return tasks


async def _cancel_all(tasks: "list[asyncio.Task[None]]") -> None:
    for t in tasks:
        t.cancel()
        try:
            await t
        except asyncio.CancelledError:
            pass


def test_real_threshold_crossing_produces_an_actual_ramp_with_scaled_color() -> None:
    source = _FakeSource("WarnCO2", 2000)  # above the 1600 default threshold
    signal = NotificationSignal("WarnCO2", ValueRef(source, "WarnCO2"), (("WarnCO2", "int", 1600, 0, 3000, None),), (1, 0, 0))
    pixel, notify = make_pair((signal,))
    run(notify.cfgmgr.setup())

    async def scenario() -> None:
        await notify._set_dict_cfg({"Interv": 3600.0, "FlashDur": 0.5}, notify.get_cfg_schema())
        tasks = await _start_all(pixel, notify)
        await asyncio.sleep(1.3)  # one triggered cycle's real settle time (2*0.5=1.0s) + margin
        await _cancel_all(tasks)

    run(scenario())
    writes = [w[0] for w in pixel.pixel.writes]
    assert (200, 0, 0) in writes  # scaled by the default FlashBri=200, pure red channel
    assert writes[-1] == (0, 0, 0)  # ramp ends black


def test_multiple_simultaneous_crossings_produce_sequential_correctly_colored_ramps() -> None:
    co2 = NotificationSignal(
        "WarnCO2", ValueRef(_FakeSource("WarnCO2", 2000), "WarnCO2"), (("WarnCO2", "int", 1600, 0, 3000, None),), (1, 0, 0),
    )
    voc = NotificationSignal(
        "WarnVOC", ValueRef(_FakeSource("WarnVOC", 400), "WarnVOC"), (("WarnVOC", "int", 350, 0, 500, None),), (0, 1, 0),
    )
    pixel, notify = make_pair((co2, voc))
    run(notify.cfgmgr.setup())

    async def scenario() -> None:
        await notify._set_dict_cfg({"Interv": 3600.0, "FlashDur": 0.5}, notify.get_cfg_schema())
        tasks = await _start_all(pixel, notify)
        await asyncio.sleep(2.5)  # both triggered cycles' settle time (2*1.0s) + margin
        await _cancel_all(tasks)

    run(scenario())
    writes = [w[0] for w in pixel.pixel.writes]
    red_frames = [i for i, w in enumerate(writes) if w[0] > 0]
    green_frames = [i for i, w in enumerate(writes) if w[1] > 0]
    assert red_frames and green_frames
    # registration order (CO2 then VOC) must produce a fully-contiguous red block before any green
    # frame, not interleaved - the same real arbitration primitive both entrypoints share.
    assert max(red_frames) < min(green_frames)


def test_led_signal_during_a_notification_ramp_is_refused_at_once() -> None:
    pixel, notify = make_pair((_co2_signal(),))
    run(notify.setup())

    async def scenario() -> "tuple[bool, bool, bool]":
        await notify._set_dict_cfg({"Interv": 3600.0, "FlashDur": 0.5}, notify.get_cfg_schema())
        tasks = await _start_all(pixel, notify)
        mid_ramp = await _wait_until(lambda: bool(_lit_frames(pixel)))
        result = pixel.led_signal(11, 22, 33, 0.1)  # the REST command, sync: refused or not with no await
        ended = await _wait_until(lambda: _ramp_over(pixel))
        await _cancel_all(tasks)
        return mid_ramp, result, ended

    mid_ramp, result, ended = run(scenario())
    assert mid_ramp is True
    assert result is False  # refused at once, never queued
    assert ended is True  # the ramp ended with nothing queued behind it
    assert (11, 22, 33) not in [w[0] for w in pixel.pixel.writes]
    assert run(notify.get_error_counter())["NOTIFY"]["ErrCount"] == 0  # the notification's own request went through


class _LateTicks:
    # Stands in for the driver's `time`: every ticks_ms() read after the first lies 2**28 ms later, past
    # any deadline ticks_diff() can express (2**29 ms). The values never near a wrap: plain arithmetic.
    def __init__(self) -> None:
        self._reads = 0

    def ticks_ms(self) -> int:
        self._reads += 1
        return 0 if self._reads == 1 else 1 << 28

    def ticks_add(self, ticks: int, delta: int) -> int:
        return ticks + delta

    def ticks_diff(self, end: int, start: int) -> int:
        return end - start


def test_a_notification_dropped_by_a_busy_led_persists_one_warning() -> None:
    # The LED stays busy: a REST command is queued and no signal task ever plays it.
    pixel, notify = make_pair((_co2_signal(),))
    run(notify.setup())
    assert pixel.led_signal(0, 0, 50, 1.0) is True
    original = asy_neopixel_driver.time
    asy_neopixel_driver.time = _LateTicks()  # type: ignore[assignment]  # a stand-in for the module's time, not a caller mismatch

    async def scenario() -> bool:
        await notify._set_dict_cfg({"Interv": 3600.0, "FlashDur": 0.5}, notify.get_cfg_schema())
        task = notify.start_asy_notify_monitor()
        logged = await _wait_until(lambda: notify.pr.err_count >= 1)
        await _cancel_all([task])
        return logged

    try:
        logged = run(scenario())
    finally:
        asy_neopixel_driver.time = original
    assert logged is True
    log = run(notify.get_error_counter())["NOTIFY"]
    assert log["ErrCount"] == 1
    assert log["ErrNum"][-1] == code("W", "NOTIFY_SIGNAL_DROPPED")
    assert pixel.pixel.writes == []  # nothing played: the queued command waits for a signal task


class _Rp2Gmtime:
    # Stands in for the NTP client's `time`: rp2's gmtime() has 8 fields, this Unix port's 9 (see
    # tests/test_asy_ntp_client.py's cettime() section), and cettime() checks for rp2's shape.
    def gmtime(self, *secs: int) -> "tuple[int, ...]":
        return tuple(time.gmtime(*secs))[:8]

    def mktime(self, t: "tuple[int, ...]") -> int:
        return time.mktime(t)

    def time(self) -> int:
        return time.time()


def test_the_window_check_reads_a_real_ntp_clock() -> None:
    # The production local-time callback: a real NTP client's cettime(), marked synced by the test.
    ntp = AsyNtpClient(asyncio.Lock(), lambda: True, lambda: None, NtpTiming(500, 1, 5000, 10, 600), cfg_path=_tmp_cfg_dir())
    run(ntp.cfgmgr.setup())
    run(ntp._set_synced(value=True))

    def window_cycle(on_min: int, off_min: int) -> "list[tuple[int, ...]]":
        pixel, notify = make_pair((_co2_signal(),), local_time=ntp.cettime)
        run(notify.setup())
        cfg: dict[str, int | float | str | bool | None] = {"OnH": on_min // 60, "OnM": on_min % 60, "OffH": off_min // 60, "OffM": off_min % 60, "Interv": 3600.0, "FlashDur": 0.5}

        async def scenario() -> bool:
            await notify._set_dict_cfg(cfg, notify.get_cfg_schema())
            tasks = await _start_all(pixel, notify)
            done = await _wait_until(lambda: notify._datastruct[-1] is not None)  # TS, NOTIFY's last field: the cycle stored
            await _cancel_all(tasks)
            return done

        assert run(scenario()) is True
        return _lit_frames(pixel)

    original = asy_ntp_client.time
    asy_ntp_client.time = _Rp2Gmtime()  # type: ignore[assignment]  # a stand-in for the module's time, not a caller mismatch
    try:
        now = run(ntp.cettime())
        assert now is not None
        cur = now.hour * 60 + now.minute
        assert window_cycle((cur - 5) % 1440, (cur + 5) % 1440)  # around the NTP time: the signal flashes
        assert window_cycle((cur + 60) % 1440, (cur + 120) % 1440) == []  # an hour away from it: dark
    finally:
        asy_ntp_client.time = original


def test_a_service_on_the_default_sink_completes_a_cycle_silently() -> None:
    sink = asy_notification_service._DefaultSignalSink()
    notify = NotificationCoordinator(sink.request_signal, _local_time, (_co2_signal(),), cfg_path=_tmp_cfg_dir())
    run(notify.setup())

    async def scenario() -> bool:
        await notify._set_dict_cfg({"Interv": 3600.0, "FlashDur": 0.5}, notify.get_cfg_schema())
        task = notify.start_asy_notify_monitor()
        done = await _wait_until(lambda: notify._datastruct[-1] is not None)  # TS, NOTIFY's last field
        await _cancel_all([task])
        return done

    assert run(scenario()) is True
    assert run(notify.get_data()).Triggered is True
    assert run(notify.get_error_counter())["NOTIFY"]["ErrCount"] == 0  # the default sink's False is no LED, not a drop


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
