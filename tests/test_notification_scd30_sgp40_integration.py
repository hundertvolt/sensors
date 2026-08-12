"""Cross-module integration: a real asy_scd30_driver.py.SCD30_Reader AND a real
asy_sgp40_driver.py.SGP40_Reader (each against its own fake I2C bus, same mocking boundary as
test_asy_scd30_driver.py's/test_asy_sgp40_driver.py's own tests) simultaneously feeding ONE shared
asy_notification_service.py.NotificationCoordinator/asy_neopixel_driver.py.NeopixelDriver, via
get_value() wrappers that mirror improved-quality/sensortask-wozi.py's own co2_value_callback()/
voc_value_callback() exactly (that file itself is out of scope for testing - see CLAUDE.md - so the
wrappers are reproduced locally, not imported).

test_notification_scd30_integration.py and test_notification_sgp40_integration.py each already cover
their own sensor feeding its own, separate NotificationCoordinator/NeopixelDriver pair - neither
proves the real wiring's actual shape, where WarnCO2/WarnHum (SCD30) and WarnVOC (SGP40) all share
ONE coordinator/pixel (see improved-quality/sensortask-wozi.py's own single `notify`/`pixel`
construction). This file fills that gap: two real sensor chains, one shared downstream stack,
proving (a) both chains can trigger their own signal correctly without cross-contaminating the
other's state, and (b) a genuine hardware fault on one sensor stays isolated to that sensor's own
error log and doesn't block or corrupt the healthy sensor's own notification.
"""

import asyncio
import os
import struct

from asy_i2c_driver import I2C
from asy_neopixel_driver import NeopixelDriver
from asy_notification_service import NotificationCoordinator, NotificationSignal
from asy_scd30_driver import SCD30_Reader
from asy_sgp40_driver import SGP40_Reader
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


class _FastAsyncSleep:
    # Same technique as test_notification_sgp40_integration.py's own _FastAsyncSleep - SGP40's
    # baseline-settle sequence below needs this regardless of which other sensor is also in play.
    def __enter__(self) -> "_FastAsyncSleep":
        self._real_sleep = asyncio.sleep

        async def _fast(_seconds: float) -> None:
            await self._real_sleep(0)

        asyncio.sleep = _fast  # type: ignore[assignment]  # deliberate monkeypatch, not a real caller mismatch
        return self

    def __exit__(self, *exc_info: object) -> None:
        asyncio.sleep = self._real_sleep


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


_sweep_stale_tmp_dirs("notify_dual_")


def _remove_any(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        try:
            os.rmdir(path)
        except OSError:
            pass


def _tmp_cfg_dir(label: str) -> str:
    global _next_dir
    try:
        os.mkdir(_TMP_DIR)
    except OSError:
        pass
    _next_dir += 1
    path = _TMP_DIR + "/notify_dual_" + label + "_" + str(_next_dir)
    try:
        os.mkdir(path)
    except OSError:
        pass
    _remove_any(path + "/config_NOTIFY.cfg")
    _remove_any(path + "/config_SGP40.cfg")
    return path + "/"


class _FakeTime:
    def __init__(self, hour: int, minute: int) -> None:
        self.hour = hour
        self.minute = minute


async def _local_time() -> _FakeTime:
    return _FakeTime(12, 0)


async def _cancel_all(tasks: "list[asyncio.Task[None]]") -> None:
    for t in tasks:
        t.cancel()
        try:
            await t
        except asyncio.CancelledError:
            pass


# --- SCD30 side: register/data frame builders, verbatim from test_notification_scd30_integration.py ---


def make_scd_reader() -> "tuple[SCD30_Reader, Any]":
    i2c = I2C(0, scl_pin=1, sda_pin=0, frequency=100000)
    reader = SCD30_Reader(i2c, irq_pin=5, trigger_sec=3, max_module_error=5)
    return reader, reader.scd.i2c_scd30.i2c_device.i2c._i2c


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


def drive_scd_cycle(reader: SCD30_Reader) -> "Any":
    # Exactly what read_loop() itself does per cycle (see asy_scd30_driver.py) - driven directly
    # instead of through the full irq/timer machinery, same convention as the sibling files.
    results = run(reader._read_scd())
    run(reader._error_check(results))
    run(reader._store_scd(results))
    return results


# --- SGP40 side: word/CRC builders, verbatim from test_notification_sgp40_integration.py ---

_CRC_POLY = 0x31  # SGP40 datasheet Table 7 - same polynomial as test_asy_sgp40_driver.py's own


def _crc8(data: bytes) -> int:
    crc = 0xFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = ((crc << 1) ^ _CRC_POLY) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF
    return crc


def _word(value: int) -> bytes:
    payload = bytes([(value >> 8) & 0xFF, value & 0xFF])
    return payload + bytes([_crc8(payload)])


async def _comp_data() -> "list[float | None]":
    return [25.0, 50.0]


def make_sgp_reader() -> "tuple[SGP40_Reader, Any]":
    i2c = I2C(1, scl_pin=19, sda_pin=18, frequency=50000)
    reader = SGP40_Reader(i2c, _comp_data, max_module_error=2, cfg_path=_tmp_cfg_dir("sgp"))
    run(reader.pr.setup())
    return reader, reader.sgp.i2c_sgp40.i2c_device.i2c._i2c


async def voc_value_callback(sgp_reader: SGP40_Reader) -> "int | float | None":
    # Verbatim mirror of improved-quality/sensortask-wozi.py's own voc_value_callback() body.
    sgp_data = await sgp_reader.get_data()
    if sgp_data is None or sgp_data.VOC is None:
        return None
    return int(sgp_data.VOC)


def _drive_sgp_cycle(reader: SGP40_Reader, fake_bus: "Any", raw: int) -> "Any":
    fake_bus.read_queue.append(_word(raw))
    data, compensated, _serialized = run(reader._read_sgp(None, False, False))
    run(reader._error_check(data, condition=compensated))
    run(reader._store_sgp(data))
    return data


def _settle_and_spike(reader: SGP40_Reader, fake_bus: "Any") -> "Any":
    # See test_notification_sgp40_integration.py's own module docstring for the calibration note
    # this two-phase sequence relies on.
    for _ in range(160):
        data = _drive_sgp_cycle(reader, fake_bus, 30000)
    assert data.VOC == 100
    for _ in range(40):
        data = _drive_sgp_cycle(reader, fake_bus, 5000)
        if isinstance(data.VOC, int) and data.VOC > 350:
            return data
    raise AssertionError("VOC index never crossed the WarnVOC threshold - calibration assumption broken")


# --- shared downstream stack: one NeopixelDriver, one NotificationCoordinator, both signals ---


def make_dual_stack(scd_reader: SCD30_Reader, sgp_reader: SGP40_Reader) -> "tuple[NeopixelDriver, NotificationCoordinator]":
    pixel = NeopixelDriver(0, neopixel_freq=100)

    async def get_co2() -> "int | float | None":
        return await co2_value_callback(scd_reader)

    async def get_voc() -> "int | float | None":
        return await voc_value_callback(sgp_reader)

    notify = NotificationCoordinator(pixel.request_signal, _local_time, cfg_path=_tmp_cfg_dir("notify"))
    co2_signal = NotificationSignal("WarnCO2", get_co2, (("WarnCO2", "int", 1600, 0, 3000, None),), (1, 0, 0))
    voc_signal = NotificationSignal("WarnVOC", get_voc, (("WarnVOC", "int", 350, 0, 500, None),), (0, 1, 0))
    notify.register(co2_signal)
    notify.register(voc_signal)
    notify.finalize()
    run(notify.cfgmgr.setup())
    return pixel, notify


def test_both_sensors_crossing_threshold_together_trigger_their_own_signal_without_cross_contamination() -> None:
    scd_reader, scd_i2c = make_scd_reader()
    scd_i2c.read_queue.append(register_frame(1))
    scd_i2c.read_queue.append(data_frame(2000.0, 22.0, 45.0))  # CO2 above the 1600 default threshold

    with _FastAsyncSleep():
        sgp_reader, sgp_i2c = make_sgp_reader()
        elevated = _settle_and_spike(sgp_reader, sgp_i2c)
    assert elevated.VOC is not None and elevated.VOC > 350

    drive_scd_cycle(scd_reader)
    pixel, notify = make_dual_stack(scd_reader, sgp_reader)

    async def scenario() -> None:
        await notify._set_dict_cfg({"Interv": 3600.0, "FlashDur": 0.5}, notify.get_cfg_schema())
        tasks = [s() for s in pixel.get_task_starters()] + [s() for s in notify.get_task_starters()]
        # Both signals' own ramps (2*0.5=1.0s each) may run one after another rather than
        # simultaneously, depending on NeopixelDriver's own arbitration (unit-tested elsewhere,
        # not re-derived here) - generous margin covers either ordering.
        await asyncio.sleep(2.6)
        await _cancel_all(tasks)

    run(scenario())
    writes = [w[0] for w in pixel.pixel.writes]
    assert (200, 0, 0) in writes  # WarnCO2's own color, scaled by the default FlashBri=200
    assert (0, 200, 0) in writes  # WarnVOC's own color, scaled by the default FlashBri=200
    assert writes[-1] == (0, 0, 0)  # settles back to off once both ramps finish

    scd_log = run(scd_reader.get_error_counter())
    sgp_log = run(sgp_reader.get_error_counter())
    notify_log = run(notify.get_error_counter())
    assert scd_log["SCD30"]["ErrCount"] == 0
    assert sgp_log["SGP40"]["ErrCount"] == 0
    assert notify_log["NOTIFY"]["ErrCount"] == 0


def test_one_sensor_i2c_fault_stays_isolated_and_the_healthy_sibling_still_triggers() -> None:
    # SCD30 faults; SGP40 stays healthy and already-spiked - proves a real hardware fault on one
    # sensor's own driver neither blocks nor corrupts the sibling sensor's independent chain, and is
    # attributed only to the faulted sensor's own error log (matching DRIVER_SPEC.md's "each driver
    # owns its own error log" separation of concerns, now proven across two real sensors sharing one
    # downstream coordinator rather than just one sensor in isolation).
    scd_reader, scd_i2c = make_scd_reader()
    scd_i2c.inject_fault("writeto", OSError(5, "simulated bus fault"))

    with _FastAsyncSleep():
        sgp_reader, sgp_i2c = make_sgp_reader()
        elevated = _settle_and_spike(sgp_reader, sgp_i2c)
    assert elevated.VOC is not None and elevated.VOC > 350

    faulted = drive_scd_cycle(scd_reader)  # the bus fault happens inside here
    assert faulted[0] is None  # (co2, temp, hum, ts) - a no-op store, get_co2 will return None
    pixel, notify = make_dual_stack(scd_reader, sgp_reader)

    async def scenario() -> None:
        await notify._set_dict_cfg({"Interv": 3600.0, "FlashDur": 0.5}, notify.get_cfg_schema())
        tasks = [s() for s in pixel.get_task_starters()] + [s() for s in notify.get_task_starters()]
        await asyncio.sleep(1.3)  # one triggered cycle's real settle time (2*0.5=1.0s) + margin
        await _cancel_all(tasks)

    run(scenario())
    writes = [w[0] for w in pixel.pixel.writes]
    assert (0, 200, 0) in writes  # the healthy SGP40 chain still triggers normally
    assert (200, 0, 0) not in writes  # the faulted SCD30 chain never triggers - data.CO2 was None
    assert writes[-1] == (0, 0, 0)

    scd_log = run(scd_reader.get_error_counter())
    sgp_log = run(sgp_reader.get_error_counter())
    notify_log = run(notify.get_error_counter())
    assert scd_log["SCD30"]["ErrCount"] == 2  # attributed to SCD30 alone - see the SCD30-only file's own comment
    assert sgp_log["SGP40"]["ErrCount"] == 0  # the healthy sibling's own log is untouched
    assert notify_log["NOTIFY"]["ErrCount"] == 0  # a per-driver read failure is not a NOTIFY-layer failure


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
