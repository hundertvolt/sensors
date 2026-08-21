"""Cross-module integration: a real asy_neopixel_driver.py.NeopixelDriver wired to a real
asy_notification_service.py.NotificationCoordinator via request_signal_cb=pixel.request_signal - the actual production shape src/sensortask_wozi.py wires.
Only tests/neopixel.py's fake write surface is mocked; overlay/arbitration, the poll loop, gating, config, and logging all run for real end to end.
"""

import asyncio
import os

from asy_neopixel_driver import NeopixelDriver
from asy_notification_service import NotificationCoordinator, NotificationSignal

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


class _FakeTime:
    def __init__(self, hour: int, minute: int) -> None:
        self.hour = hour
        self.minute = minute


async def _local_time() -> _FakeTime:
    return _FakeTime(12, 0)


_TMP_DIR = "tests/_tmp"
_next_dir = 0


def _sweep_stale_tmp_dirs(prefix: str) -> None:
    # Sweeps pre-existing <prefix>* scratch dirs left behind by an earlier scripts/test.sh run on
    # this machine - _next_dir always restarts at 0 per process, so without this a later run
    # silently reuses an earlier run's real, persisted config_*.cfg files instead of a genuinely
    # fresh directory. See tests/test_sensortask_wozi.py's own _sweep_stale_tmp_dirs() for the full
    # root-cause writeup (this exact _tmp_cfg_dir() shape is copy-pasted across every test file with
    # its own _TMP_DIR/_next_dir pair - same fix applied uniformly to each).
    try:
        entries = os.listdir(_TMP_DIR)
    except OSError:
        return  # tests/_tmp itself doesn't exist yet - nothing to clean
    for entry in entries:
        if not entry.startswith(prefix):
            continue
        dir_path = _TMP_DIR + "/" + entry
        try:
            for filename in os.listdir(dir_path):
                try:
                    os.remove(dir_path + "/" + filename)
                except OSError:
                    pass
            os.rmdir(dir_path)
        except OSError:
            pass


_sweep_stale_tmp_dirs("notify_neopixel_")


def _remove_any(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        try:
            os.rmdir(path)
        except OSError:
            pass


def _tmp_cfg_dir() -> str:
    global _next_dir
    try:
        os.mkdir(_TMP_DIR)
    except OSError:
        pass
    _next_dir += 1
    path = _TMP_DIR + "/notify_neopixel_" + str(_next_dir)
    try:
        os.mkdir(path)
    except OSError:
        pass
    _remove_any(path + "/config_NOTIFY.cfg")
    return path + "/"


def make_pair() -> "tuple[NeopixelDriver, NotificationCoordinator]":
    # freq=100 keeps ramps fast in real wall-clock time (same reasoning as
    # tests/test_asy_neopixel_driver.py's own make_driver()).
    pixel = NeopixelDriver(0, neopixel_freq=100)
    notify = NotificationCoordinator(pixel.request_signal, _local_time, cfg_path=_tmp_cfg_dir())
    return pixel, notify


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
    pixel, notify = make_pair()

    async def get_value() -> int:
        return 2000  # above the 1600 default threshold

    signal = NotificationSignal("WarnCO2", get_value, (("WarnCO2", "int", 1600, 0, 3000, None),), (1, 0, 0))
    notify.register(signal)
    notify.finalize()
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
    pixel, notify = make_pair()

    async def co2_value() -> int:
        return 2000

    async def voc_value() -> int:
        return 400

    co2 = NotificationSignal("WarnCO2", co2_value, (("WarnCO2", "int", 1600, 0, 3000, None),), (1, 0, 0))
    voc = NotificationSignal("WarnVOC", voc_value, (("WarnVOC", "int", 350, 0, 500, None),), (0, 1, 0))
    notify.register(co2)
    notify.register(voc)
    notify.finalize()
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


def test_led_signal_during_notification_triggered_animation_is_queued_and_eventually_runs() -> None:
    pixel, notify = make_pair()

    async def get_value() -> int:
        return 2000

    signal = NotificationSignal("WarnCO2", get_value, (("WarnCO2", "int", 1600, 0, 3000, None),), (1, 0, 0))
    notify.register(signal)
    notify.finalize()
    run(notify.cfgmgr.setup())

    async def scenario() -> bool:
        await notify._set_dict_cfg({"Interv": 3600.0, "FlashDur": 0.5}, notify.get_cfg_schema())
        tasks = await _start_all(pixel, notify)
        await asyncio.sleep(0.1)  # the notification-triggered ramp is now mid-animation
        result = pixel.led_signal(11, 22, 33, 0.1)  # REST-shaped external request, arrives while busy
        await asyncio.sleep(1.5)  # let both the notification ramp and the queued external one finish
        await _cancel_all(tasks)
        return result

    result = run(scenario())
    assert result is True  # accepted/queued, not rejected
    writes = [w[0] for w in pixel.pixel.writes]
    assert (11, 22, 33) in writes  # the queued external request eventually ran too


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
