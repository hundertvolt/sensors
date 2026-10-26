"""Cross-module integration: a real SCD30_Reader AND a real SGP40_Reader simultaneously feeding ONE shared
NotificationService/NeopixelDriver (matching the generated build_system()'s single notification/pixel wiring).

Fills the gap test_notification_scd30_integration.py/test_notification_sgp40_integration.py each leave (their own
separate service/pixel pair): proves both chains trigger correctly without cross-contaminating, and a hardware fault on
one sensor stays isolated to its own error log."""

import errno
import struct
from collections import namedtuple

from _async_harness import cancel_all, run
from _error_codes import code
from _fake_time import DrivenTime, FakeTime, UTCValid
from _fast_sleep import FastAsyncSleep
from _tmp_scratch import TmpScratch
from machine import I2C as FakeI2C

import asy_neopixel_driver
import asy_notification_service
from asy_base_classes import ValueRef
from asy_crc_checks import CRC8
from asy_i2c_driver import I2C
from asy_neopixel_driver import NeopixelDriver
from asy_notification_service import NotificationService, NotificationSignal
from asy_scd30_driver import SCD30_Reader
from asy_sgp40_driver import SGP40_Reader

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing isn't available on the real MicroPython test interpreter
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from asy_scd30_driver import SCDResults
    from asy_sgp40_driver import SGP40


# Per-test config-file isolation via the shared tests/_tmp_scratch.py helper - see that module's
# own docstring and tests/test_tmp_scratch.py for the mechanism/regression coverage. `label`
# (e.g. "scd30"/"sgp40") keeps this file's two-sensors-in-one-service directories readable.
_scratch = TmpScratch("notify_dual")


def _crc8(data: bytes) -> int:
    crc = 0xFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = ((crc << 1) ^ _CRC_POLY) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF
    return crc


async def _cycle(clock: DrivenTime, notify: NotificationService, flashes: int) -> None:
    # The monitor's first cycle by the service's own rule: 2 x FlashDur after each triggered flash, so 1 ms before that
    # end nothing is stored yet; then the loop parks on its next cycle, FlashInterval after its start.
    cfg = (await notify.get_dict_cfg())["NOTIFY"]
    flash_dur, interval = cfg["FlashDur"], cfg["FlashInterval"]
    assert isinstance(flash_dur, float) and isinstance(interval, float), cfg
    start = clock.now
    end = start + flashes * round(flash_dur * 2000)
    if end > start:
        await clock.elapse(end - 1 - start)
        assert notify._datastruct[1] is None, f"the cycle was stored by virtual t={clock.now} ms"  # State: None until stored
    await clock.elapse(end - clock.now)
    assert notify._datastruct[1] is not None, f"no cycle stored at virtual t={clock.now} ms"
    assert clock.wakes()[-1] == start + round(interval * 1000), f"at virtual t={clock.now} ms the loop waits for {clock.wakes()}"


def _drive_scd_cycle(reader: SCD30_Reader) -> "SCDResults":
    # Exactly what _read_loop() itself does per cycle (see asy_scd30_driver.py) - driven directly
    # instead of through the full irq/timer machinery, same convention as the sibling files.
    with UTCValid():
        results, new_data = run(reader._read_scd())
    run(reader._error_check(results))
    run(reader._store_scd(results, new_data))
    return results


def _drive_sgp_cycle(reader: SGP40_Reader, fake_bus: "FakeI2C", raw: int) -> "SGP40":
    fake_bus.read_queue.append(_word(raw))
    with UTCValid():
        data, compensated, _serialized = run(reader._read_sgp(None, serialize=False, deserialize=False))
    run(reader._error_check(data, condition=compensated and data[0] is None))  # the read loop's condition
    run(reader._store_sgp(data))
    return data


# --- SCD30 side: register/data frame builders, verbatim from test_notification_scd30_integration.py ---


def _driven() -> DrivenTime:
    # The driver's and the service's time and asyncio on one driven clock for the block: every frame, settle, overlay
    # and pause wait parks on it, and time moves only when the test moves it.
    return DrivenTime(asy_neopixel_driver, asy_notification_service, sleeps=True)


async def _local_time() -> FakeTime:
    return FakeTime(12, 0)


def _make_dual_stack(scd_reader: SCD30_Reader, sgp_reader: SGP40_Reader) -> "tuple[NeopixelDriver, NotificationService]":
    # ValueRef(source, field) references (SPECIFICATION.md Part C.14.2), the registration shape the generated
    # build_system() emits.
    pixel = NeopixelDriver(0)
    pixel.neopixel_freq = 100  # the driver's own fixed state, set from outside
    pixel._frame_ms = 10

    co2_signal = NotificationSignal("WarnCO2", ValueRef(scd_reader, "CO2"), (("WarnCO2", "int", 1600, 0, 3000, None),), (1, 0, 0))
    voc_signal = NotificationSignal("WarnVOC", ValueRef(sgp_reader, "VOC"), (("WarnVOC", "int", 350, 0, 500, None),), (0, 1, 0))
    notify = NotificationService(pixel.request_signal, _local_time, (co2_signal, voc_signal), cfg_path=_tmp_cfg_dir("notify"))
    run(pixel.setup())  # the boot batch's setup() for both, before any task starts
    run(notify.setup())
    return pixel, notify


def _make_scd_reader() -> "tuple[SCD30_Reader, FakeI2C]":
    # The reader owns config_SCD30.cfg (its FRC settings): a scratch directory, set up as at boot, on a fresh bus 0.
    FakeI2C.reset_id(0)
    i2c = I2C(0, scl_pin=1, sda_pin=0, frequency=100000)
    reader = SCD30_Reader(i2c, irq_pin=5, trigger_s=3, max_module_error=5, cfg_path=_tmp_cfg_dir("scd"))
    run(reader.setup())
    return reader, reader._scd._i2c_scd30.i2c_device.i2c._i2c  # type: ignore[return-value]  # the fake behind asy_i2c_driver.I2C


def _make_sgp_reader() -> "tuple[SGP40_Reader, FakeI2C]":
    FakeI2C.reset_id(1)  # a fresh bus 1
    i2c = I2C(1, scl_pin=19, sda_pin=18, frequency=50000)
    comp = _FakeCompSource()
    reader = SGP40_Reader(
        i2c,
        ValueRef(comp, "Temp"),
        ValueRef(comp, "Hum"),
        max_module_error=2,
        cfg_path=_tmp_cfg_dir("sgp"),
    )
    run(reader.setup())
    fake_bus = reader._sgp._i2c_sgp40.i2c_device.i2c._i2c
    assert fake_bus is not None  # type-narrowing only - I2C() always builds its raw bus
    return reader, fake_bus


def _settle_and_spike(reader: SGP40_Reader, fake_bus: "FakeI2C") -> "SGP40":
    # See test_notification_sgp40_integration.py's own top-of-file comment for the calibration note
    # this two-phase sequence relies on.
    for _ in range(160):
        data = _drive_sgp_cycle(reader, fake_bus, 30000)
    assert data.VOC == 100
    for _ in range(40):
        data = _drive_sgp_cycle(reader, fake_bus, 5000)
        if isinstance(data.VOC, int) and data.VOC > 350:
            return data
    raise AssertionError("VOC index never crossed the WarnVOC threshold - calibration assumption broken")


# --- SGP40 side: word/CRC builders, verbatim from test_notification_sgp40_integration.py ---

_CRC_POLY = 0x31  # SGP40 datasheet Table 7 - same polynomial as test_asy_sgp40_driver.py's own


def _tmp_cfg_dir(label: str) -> str:
    return _scratch.dir(label)


def _word(value: int) -> bytes:
    payload = bytes([(value >> 8) & 0xFF, value & 0xFF])
    return payload + bytes([_crc8(payload)])


_CompReading = namedtuple("_CompReading", ("Temp", "Hum"))


class _FakeCompSource:
    # Structural stand-in for temperature_source/humidity_source (SPECIFICATION.md Parts C.14 and L.6.3) - a
    # fixed value independent of this test's real scd_reader, matching the removed stub's own fixed [25.0,
    # 50.0] return exactly.
    #
    # scd_reader's real reading is deliberately not used: _settle_and_spike() below needs 200 compensated
    # SGP40 cycles well before this test ever drives scd_reader for its own real measurement.
    async def get_data(self) -> "_CompReading":
        return _CompReading(25.0, 50.0)


def crc8_byte(data: bytes) -> int:
    added = run(CRC8().add(bytearray(data)))
    assert added is not None
    return added[-1]


def data_frame(co2: float, temperature: float, humidity: float) -> bytes:
    frame = bytearray()
    for value in (co2, temperature, humidity):
        raw = struct.pack(">f", value)
        msw, lsw = raw[0:2], raw[2:4]
        frame += msw + bytes([crc8_byte(msw)]) + lsw + bytes([crc8_byte(lsw)])
    return bytes(frame)


def register_frame(value: int) -> bytes:
    payload = struct.pack(">H", value)
    return payload + bytes([crc8_byte(payload)])


def test_both_sensors_crossing_threshold_together_trigger_their_own_signal_without_cross_contamination() -> None:
    scd_reader, scd_i2c = _make_scd_reader()
    scd_i2c.read_queue.append(register_frame(1))
    scd_i2c.read_queue.append(data_frame(2000.0, 22.0, 45.0))  # CO2 above the 1600 default threshold

    with FastAsyncSleep():
        sgp_reader, sgp_i2c = _make_sgp_reader()
        elevated = _settle_and_spike(sgp_reader, sgp_i2c)
    assert elevated.VOC is not None and elevated.VOC > 350

    _drive_scd_cycle(scd_reader)
    pixel, notify = _make_dual_stack(scd_reader, sgp_reader)

    async def scenario(clock: DrivenTime) -> None:
        await notify._set_dict_cfg({"FlashInterval": 3600.0, "FlashDur": 0.5}, notify.get_cfg_schema())
        tasks = [s() for s in pixel.get_task_starters()] + [s() for s in notify.get_task_starters()]
        await _cycle(clock, notify, 2)  # both signals flash, one settle after the other
        await cancel_all(tasks, settle_yields=1)

    with _driven() as clock:
        run(scenario(clock))
    writes = [w[0] for w in pixel._pixel.writes]
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
    # SCD30 faults while SGP40 stays healthy and already-spiked - proving a real hardware fault on one
    # sensor's driver neither blocks nor corrupts the sibling's independent chain, and is attributed only to
    # the faulted sensor's own error log.
    #
    # That is Part C.7's per-module logging (each module's own `self.pr`), now proven across two real
    # sensors sharing one downstream coordinator rather than one sensor in isolation.
    scd_reader, scd_i2c = _make_scd_reader()
    scd_i2c.inject_fault("writeto", OSError, errno.EIO, "simulated bus fault")

    with FastAsyncSleep():
        sgp_reader, sgp_i2c = _make_sgp_reader()
        elevated = _settle_and_spike(sgp_reader, sgp_i2c)
    assert elevated.VOC is not None and elevated.VOC > 350

    faulted = _drive_scd_cycle(scd_reader)  # the bus fault happens inside here
    assert faulted[0] is None  # (co2, temp, hum, ts) - a no-op store, get_co2 will return None
    pixel, notify = _make_dual_stack(scd_reader, sgp_reader)

    async def scenario(clock: DrivenTime) -> None:
        await notify._set_dict_cfg({"FlashInterval": 3600.0, "FlashDur": 0.5}, notify.get_cfg_schema())
        tasks = [s() for s in pixel.get_task_starters()] + [s() for s in notify.get_task_starters()]
        await _cycle(clock, notify, 1)
        await cancel_all(tasks, settle_yields=1)

    with _driven() as clock:
        run(scenario(clock))
    writes = [w[0] for w in pixel._pixel.writes]
    assert (0, 200, 0) in writes  # the healthy SGP40 chain still triggers normally
    assert (200, 0, 0) not in writes  # the faulted SCD30 chain never triggers - data.CO2 was None
    assert writes[-1] == (0, 0, 0)

    scd_log = run(scd_reader.get_error_counter())
    sgp_log = run(sgp_reader.get_error_counter())
    notify_log = run(notify.get_error_counter())
    assert scd_log["SCD30"]["ErrCount"] == 2  # attributed to SCD30 alone - see the SCD30-only file's own comment
    assert scd_log["SCD30"]["ErrNum"][-2:] == [code("E", "READ"), code("E", "STREAK")]  # the driver's, then the streak's
    assert sgp_log["SGP40"]["ErrCount"] == 0  # the healthy sibling's own log is untouched
    assert notify_log["NOTIFY"]["ErrCount"] == 0  # a per-driver read failure is not a NOTIFY-layer failure


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
