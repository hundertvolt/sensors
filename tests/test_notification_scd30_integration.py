"""Cross-module integration: a real asy_scd30_driver.py.SCD30_Reader (against a fake I2C bus, same
mocking boundary as test_asy_scd30_driver.py's own integration-level tests) feeding a real
asy_notification_service.py.NotificationCoordinator via a get_value() wrapper that mirrors
improved-quality/sensortask-wozi.py's own co2_value_callback()/hum_value_callback() exactly (that
file itself is out of scope for testing - see CLAUDE.md - so the wrapper is reproduced locally, not
imported), driving a real asy_neopixel_driver.py.NeopixelDriver. Only tests/neopixel.py's fake write
surface and tests/machine.py's fake I2C bus are mocked; every layer above the raw I2C transaction
(SCD30_Reader's own protocol/error handling, the notify poll loop, gating, NeopixelDriver's
arbitration/ramp) runs for real.

Exercises the one thing none of the other integration files cover: how a genuine hardware fault on
one driver (SCD30) propagates - or, correctly, does NOT propagate - into a sibling driver's
(NOTIFY's) own error accounting, matching DRIVER_SPEC.md's "each driver owns its own error log"
separation of concerns.
"""

import asyncio
import os
import struct

from machine import I2C as FakeI2C

from asy_i2c_driver import I2C
from asy_neopixel_driver import NeopixelDriver
from asy_notification_service import NotificationCoordinator, NotificationSignal
from asy_scd30_driver import SCD30_Reader
from crc_checks import CRC8

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


_TMP_DIR = "tests/_tmp"
_next_dir = 0


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
    path = _TMP_DIR + "/notify_scd30_" + str(_next_dir)
    try:
        os.mkdir(path)
    except OSError:
        pass
    _remove_any(path + "/config_NOTIFY.cfg")
    return path + "/"


class _FakeTime:
    def __init__(self, hour: int, minute: int) -> None:
        self.hour = hour
        self.minute = minute


async def _local_time() -> _FakeTime:
    return _FakeTime(12, 0)


def make_scd_reader() -> "tuple[SCD30_Reader, FakeI2C]":
    i2c = I2C(0, scl_pin=1, sda_pin=0, frequency=100000)
    reader = SCD30_Reader(i2c, irq_pin=5, trigger_sec=3, max_i2c_err=5)
    return reader, reader.scd.i2c_scd30.i2c_device.i2c._i2c  # type: ignore[return-value]


def _last_two_err_nums(log: "dict[str, Any]", name: str) -> "list[int | str]":
    # Same isinstance-narrowing pattern as test_asy_sgp40_driver.py's own _last_err() helper -
    # ErrNum's static type is int | list[int] | list[str] (get_log()'s shape covers ErrCount too),
    # so a plain [-2:] slice isn't statically known to be valid without narrowing first.
    value = log[name]["ErrNum"]
    assert isinstance(value, list)
    return value[-2:]


def crc8_byte(data: bytes) -> int:
    added = run(CRC8().add(bytearray(data)))
    assert added is not None
    return added[-1]


def register_frame(value: int) -> bytes:
    payload = struct.pack(">H", value)
    return payload + bytes([crc8_byte(payload)])


def data_frame(co2: float, temperature: float, humidity: float) -> bytes:
    frame = bytearray()
    for value in (co2, temperature, humidity):
        raw = struct.pack(">f", value)
        msw, lsw = raw[0:2], raw[2:4]
        frame += msw + bytes([crc8_byte(msw)]) + lsw + bytes([crc8_byte(lsw)])
    return bytes(frame)


async def co2_value_callback(scd_reader: SCD30_Reader) -> "int | float | None":
    # Verbatim mirror of improved-quality/sensortask-wozi.py's own co2_value_callback() body.
    scd_data = await scd_reader.get_data()
    if scd_data is None or scd_data.CO2 is None:
        return None
    return float(scd_data.CO2)


async def hum_value_callback(scd_reader: SCD30_Reader) -> "int | float | None":
    # Verbatim mirror of improved-quality/sensortask-wozi.py's own hum_value_callback() body -
    # same SCD30_Reader instance backs both WarnCO2 and WarnHum in the real wiring (one sensor,
    # two notification signals off its own .Hum/.CO2 fields), but no test file exercised the real
    # WarnHum chain before this one - only WarnCO2 had integration coverage.
    scd_data = await scd_reader.get_data()
    if scd_data is None or scd_data.Hum is None:
        return None
    return float(scd_data.Hum)


def make_stack(scd_reader: SCD30_Reader) -> "tuple[NeopixelDriver, NotificationCoordinator]":
    pixel = NeopixelDriver(0, neopixel_freq=100)

    async def get_co2() -> "int | float | None":
        return await co2_value_callback(scd_reader)

    notify = NotificationCoordinator(pixel.request_signal, _local_time, cfg_path=_tmp_cfg_dir())
    signal = NotificationSignal("WarnCO2", get_co2, (("WarnCO2", "int", 1600, 0, 3000, None),), (1, 0, 0))
    notify.register(signal)
    notify.finalize()
    run(notify.cfgmgr.setup())
    return pixel, notify


def make_hum_stack(scd_reader: SCD30_Reader) -> "tuple[NeopixelDriver, NotificationCoordinator]":
    # Separate stack (own pixel/notify instance) rather than a second signal registered on
    # make_stack()'s own notify - matches WarnCO2's own test scope of one signal per scenario, and
    # avoids the two signals' ramps overlapping in the same pixel.pixel.writes trace.
    pixel = NeopixelDriver(0, neopixel_freq=100)

    async def get_hum() -> "int | float | None":
        return await hum_value_callback(scd_reader)

    notify = NotificationCoordinator(pixel.request_signal, _local_time, cfg_path=_tmp_cfg_dir())
    signal = NotificationSignal("WarnHum", get_hum, (("WarnHum", "float", 65.0, 0.0, 100.0, None),), (0, 0, 1))
    notify.register(signal)
    notify.finalize()
    run(notify.cfgmgr.setup())
    return pixel, notify


async def _cancel_all(tasks: "list[asyncio.Task[None]]") -> None:
    for t in tasks:
        t.cancel()
        try:
            await t
        except asyncio.CancelledError:
            pass


def test_real_sensor_reading_above_threshold_flows_through_to_a_real_ramp() -> None:
    scd_reader, i2c = make_scd_reader()
    i2c.read_queue.append(register_frame(1))
    i2c.read_queue.append(data_frame(2000.0, 22.0, 45.0))  # above the 1600 default threshold
    pixel, notify = make_stack(scd_reader)

    async def scenario() -> None:
        # Exactly what read_loop() itself does per cycle (see asy_scd30_driver.py) - driven directly
        # instead of through the full irq/timer machinery, which is already exhaustively covered by
        # test_asy_scd30_driver.py's own tests and isn't what this file is exercising.
        results = await scd_reader._read_scd()
        assert await scd_reader._error_check(results)
        await scd_reader._store_scd(results)

        await notify._set_dict_cfg({"Interv": 3600.0, "FlashDur": 0.5}, notify.get_cfg_schema())
        tasks = [s() for s in pixel.get_task_starters()] + [s() for s in notify.get_task_starters()]
        await asyncio.sleep(1.3)  # one triggered cycle's real settle time (2*0.5=1.0s) + margin
        await _cancel_all(tasks)

    run(scenario())
    writes = [w[0] for w in pixel.pixel.writes]
    assert (200, 0, 0) in writes  # scaled by the default FlashBri=200, pure red channel
    assert writes[-1] == (0, 0, 0)
    log = run(scd_reader.get_error_counter())
    assert log["SCD30"]["ErrCount"] == 0
    notify_log = run(notify.get_error_counter())
    assert notify_log["NOTIFY"]["ErrCount"] == 0


def test_real_humidity_reading_above_threshold_flows_through_to_a_real_ramp() -> None:
    # Same real read chain as the WarnCO2 test above, driving WarnHum instead - the one other real
    # signal this SCD30_Reader instance backs in the actual wiring (see hum_value_callback() above).
    scd_reader, i2c = make_scd_reader()
    i2c.read_queue.append(register_frame(1))
    i2c.read_queue.append(data_frame(800.0, 22.0, 70.0))  # CO2 well under threshold, Hum above the 65.0 default
    pixel, notify = make_hum_stack(scd_reader)

    async def scenario() -> None:
        results = await scd_reader._read_scd()
        assert await scd_reader._error_check(results)
        await scd_reader._store_scd(results)

        await notify._set_dict_cfg({"Interv": 3600.0, "FlashDur": 0.5}, notify.get_cfg_schema())
        tasks = [s() for s in pixel.get_task_starters()] + [s() for s in notify.get_task_starters()]
        await asyncio.sleep(1.3)
        await _cancel_all(tasks)

    run(scenario())
    writes = [w[0] for w in pixel.pixel.writes]
    assert (0, 0, 200) in writes  # scaled by the default FlashBri=200, pure blue channel (WarnHum's color)
    assert writes[-1] == (0, 0, 0)
    log = run(scd_reader.get_error_counter())
    assert log["SCD30"]["ErrCount"] == 0
    notify_log = run(notify.get_error_counter())
    assert notify_log["NOTIFY"]["ErrCount"] == 0


def test_i2c_bus_fault_degrades_to_not_triggered_and_stays_isolated_to_scd30s_own_log() -> None:
    scd_reader, i2c = make_scd_reader()
    i2c.inject_fault("writeto", OSError(5, "simulated bus fault"))
    pixel, notify = make_stack(scd_reader)

    async def scenario() -> "tuple[dict[str, Any], dict[str, Any], bool]":
        results = await scd_reader._read_scd()  # the bus fault happens inside here
        still_running = await scd_reader._error_check(results)
        await scd_reader._store_scd(results)  # a no-op: results has None fields, nothing committed

        await notify._set_dict_cfg({"Interv": 3600.0, "FlashDur": 0.5}, notify.get_cfg_schema())
        tasks = [s() for s in pixel.get_task_starters()] + [s() for s in notify.get_task_starters()]
        await asyncio.sleep(0.2)  # one monitor_loop() pass - nothing to settle, nothing was triggered
        await _cancel_all(tasks)

        scd_log = await scd_reader.get_error_counter()
        notify_log = await notify.get_error_counter()
        return scd_log, notify_log, still_running

    scd_log, notify_log, still_running = run(scenario())
    assert still_running is True  # one failure, well under max_i2c_err=5 - not a give-up condition
    # the fault is real and counted, but attributed to SCD30 alone - one faulted cycle logs twice
    # (asy_scd30_driver.py's own _read_scd() catch, errno=11, then base_classes.py's generic
    # _error_check() streak-counter increment, errno=1 - see read_loop()'s own two-call sequence).
    assert scd_log["SCD30"]["ErrCount"] == 2
    # ErrNum is the whole fixed-length history deque (_NO_ERR-padded), not just what was actually
    # recorded - only the trailing entries are this fault's own (see PrintLogHistory.get_log()).
    assert _last_two_err_nums(scd_log, "SCD30") == [11, 1]
    assert notify_log["NOTIFY"]["ErrCount"] == 0
    # neopixel_signal()'s own startup sets a defined (0,0,0) off state once, unconditionally -
    # nothing beyond that single boot-time write, since no signal was ever triggered.
    assert [w[0] for w in pixel.pixel.writes] == [(0, 0, 0)]


def test_recovers_and_triggers_normally_after_a_prior_fault() -> None:
    scd_reader, i2c = make_scd_reader()
    i2c.inject_fault("writeto", OSError(5, "simulated bus fault"))
    pixel, notify = make_stack(scd_reader)
    # Built outside scenario() deliberately: register_frame()/data_frame() call crc8_byte(), which
    # runs its own asyncio.run() - calling that from inside scenario() while it's already running
    # under this file's own run()/asyncio.run() is a nested asyncio.run() call. MicroPython's
    # asyncio doesn't reject that with a clean RuntimeError the way CPython's does - it corrupts the
    # scheduler badly enough to segfault the whole interpreter (confirmed by direct reproduction
    # isolating this exact pattern down to a two-line repro, independent of anything in
    # asy_scd30_driver.py/asy_i2c_driver.py). Not a production bug: no real driver code calls
    # asyncio.run() from within a coroutine either. Keep every frame-building call at this same
    # sync top level, matching test_asy_scd30_driver.py's own established convention.
    frame1 = register_frame(1)
    frame2 = data_frame(2000.0, 22.0, 45.0)

    async def scenario() -> None:
        faulted = await scd_reader._read_scd()
        await scd_reader._error_check(faulted)
        await scd_reader._store_scd(faulted)

        i2c.read_queue.append(frame1)
        i2c.read_queue.append(frame2)
        recovered = await scd_reader._read_scd()
        assert await scd_reader._error_check(recovered)
        await scd_reader._store_scd(recovered)

        await notify._set_dict_cfg({"Interv": 3600.0, "FlashDur": 0.5}, notify.get_cfg_schema())
        tasks = [s() for s in pixel.get_task_starters()] + [s() for s in notify.get_task_starters()]
        await asyncio.sleep(1.3)
        await _cancel_all(tasks)

    run(scenario())
    writes = [w[0] for w in pixel.pixel.writes]
    assert (200, 0, 0) in writes  # the prior fault didn't permanently poison later good reads
    scd_log = run(scd_reader.get_error_counter())
    # the earlier fault's two log entries are still on record - a later success doesn't erase
    # history, it only decrements the internal consecutive-failure streak (a plain sync pr.err(),
    # not pr.err_s() - see base_classes.py's _error_check() - so it adds no new history entry).
    assert scd_log["SCD30"]["ErrCount"] == 2
    assert _last_two_err_nums(scd_log, "SCD30") == [11, 1]


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
