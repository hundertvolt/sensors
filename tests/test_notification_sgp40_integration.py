"""Cross-module integration: a real SGP40_Reader feeding a real NotificationService, driving a real NeopixelDriver -
fills the WarnVOC gap test_notification_scd30_integration.py leaves (it only exercises WarnCO2).

Only tests/neopixel.py's fake write surface and tests/machine.py's fake I2C bus are mocked; every layer above the raw
I2C transaction runs for real."""
# VOC index calibration note, verified directly against voc_algorithm.py: a single raw reading never moves
# the index - the 45-interval initial blackout must elapse first - and the index then settles toward 100,
# the "clean air" baseline, under any constant raw signal. It measures deviation, not concentration.
#
# So a real threshold crossing needs two phases: settle near 100, then step away from that raw value. Also
# confirmed: a higher raw tick count moves the index down, raw increase meaning cleaner air on this sensor's
# convention, so the spike-inducing step is a drop in raw, not a rise.

from collections import namedtuple

from _async_harness import cancel_all, run
from _fake_time import DrivenTime, FakeTime, UTCValid
from _fast_sleep import FastAsyncSleep
from _tmp_scratch import TmpScratch
from machine import I2C as _MachineI2C  # tests/machine.py's fake bus, under the driver's own I2C wrapper

import asy_neopixel_driver
import asy_notification_service
from asy_base_classes import ValueRef
from asy_i2c_driver import I2C
from asy_neopixel_driver import NeopixelDriver
from asy_notification_service import NotificationService, NotificationSignal
from asy_sgp40_driver import SGP40_Reader

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing isn't available on the real MicroPython test interpreter
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from asy_print_log import ErrorLog
    from asy_sgp40_driver import SGP40


# Per-test config-file isolation via the shared tests/_tmp_scratch.py helper - see that
# module's own docstring and tests/test_tmp_scratch.py for the mechanism/regression coverage.
_scratch = TmpScratch("notify_sgp40")


def _crc8(data: bytes) -> int:
    crc = 0xFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = ((crc << 1) ^ _CRC_POLY) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF
    return crc


_CRC_POLY = 0x31  # SGP40 datasheet Table 7 - same polynomial as test_asy_sgp40_driver.py's own


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


def _drive_one_cycle(reader: SGP40_Reader, fake_bus: "_MachineI2C", raw: int) -> "SGP40":
    # Exactly what _read_loop() itself does per cycle when no FRAM backup is configured (see
    # asy_sgp40_driver.py) - driven directly instead of through the full trigger/timer machinery,
    # which is already exhaustively covered by test_asy_sgp40_driver.py's own tests.
    fake_bus.read_queue.append(_word(raw))
    with UTCValid():
        data, compensated, _serialized = run(reader._read_sgp(None, serialize=False, deserialize=False))
    run(reader._error_check(data, condition=compensated and data[0] is None))  # the read loop's condition
    run(reader._store_sgp(data))
    return data


def _driven() -> DrivenTime:
    # The driver's and the service's time and asyncio on one driven clock for the block: every frame, settle, overlay
    # and pause wait parks on it, and time moves only when the test moves it.
    return DrivenTime(asy_neopixel_driver, asy_notification_service, sleeps=True)


async def _local_time() -> FakeTime:
    return FakeTime(12, 0)


_CompReading = namedtuple("_CompReading", ("Temp", "Hum"))


class _FakeCompSource:
    # Structural stand-in for temperature_source/humidity_source (SPECIFICATION.md Part C.14,
    # SPECIFICATION.md Part L.6.3) - only get_data() is exercised, matching
    # test_asy_sgp40_driver.py's own identical fixture.
    async def get_data(self) -> "_CompReading":
        return _CompReading(25.0, 50.0)


def _make_sgp_reader() -> "tuple[SGP40_Reader, _MachineI2C]":
    _MachineI2C.reset_id(1)  # a fresh bus 1
    i2c = I2C(1, scl_pin=19, sda_pin=18, frequency=50000)
    comp = _FakeCompSource()
    reader = SGP40_Reader(
        i2c,
        ValueRef(comp, "Temp"),
        ValueRef(comp, "Hum"),
        max_module_error=2,
        cfg_path=_tmp_cfg_dir(),
    )
    run(reader.setup())
    fake_bus = reader._sgp._i2c_sgp40.i2c_device.i2c._i2c
    assert isinstance(fake_bus, _MachineI2C)
    return reader, fake_bus


def _make_stack(sgp_reader: SGP40_Reader) -> "tuple[NeopixelDriver, NotificationService]":
    # A ValueRef(source, field) reference (SPECIFICATION.md Part C.14.2), the registration shape the generated
    # build_system() emits.
    pixel = NeopixelDriver(0)
    pixel.neopixel_freq = 100  # the driver's own fixed state, set from outside
    pixel._frame_ms = 10

    signal = NotificationSignal("WarnVOC", ValueRef(sgp_reader, "VOC"), (("WarnVOC", "int", 350, 0, 500, None),), (0, 1, 0))
    notify = NotificationService(pixel.request_signal, _local_time, (signal,), cfg_path=_tmp_cfg_dir())
    run(pixel.setup())  # the boot batch's setup() for both, before any task starts
    run(notify.setup())
    return pixel, notify


def _settle_and_spike(reader: SGP40_Reader, fake_bus: "_MachineI2C") -> "SGP40":
    # Phase 1: settle the algorithm's learned baseline under a constant raw signal (see module
    # docstring's calibration note - _VOCALGORITHM_INITIAL_BLACKOUT=45 plus settling time).
    for _ in range(160):
        data = _drive_one_cycle(reader, fake_bus, 30000)
    assert data.VOC == 100  # confirms the baseline genuinely settled before phase 2 starts
    # Phase 2: step to a much lower raw value - a sudden air-quality change from the already-learned "clean"
    # baseline - until the index crosses WarnVOC's default threshold of 350. Loop-until-crossed rather than
    # a hardcoded count, being robust to a fixed-point convergence curve not worth pinning exactly.
    for _ in range(40):
        data = _drive_one_cycle(reader, fake_bus, 5000)
        if isinstance(data.VOC, int) and data.VOC > 350:
            return data
    raise AssertionError("VOC index never crossed the WarnVOC threshold - calibration assumption broken")


def _tmp_cfg_dir() -> str:
    return _scratch.dir()


def _word(value: int) -> bytes:
    payload = bytes([(value >> 8) & 0xFF, value & 0xFF])
    return payload + bytes([_crc8(payload)])


def test_real_sensor_reading_above_threshold_flows_through_to_a_real_ramp() -> None:
    with FastAsyncSleep():
        sgp_reader, fake_bus = _make_sgp_reader()
        elevated = _settle_and_spike(sgp_reader, fake_bus)
    assert elevated.VOC is not None and elevated.VOC > 350
    pixel, notify = _make_stack(sgp_reader)

    async def scenario(clock: DrivenTime) -> None:
        await notify._set_dict_cfg({"FlashInterval": 3600.0, "FlashDur": 0.5}, notify.get_cfg_schema())
        tasks = [s() for s in pixel.get_task_starters()] + [s() for s in notify.get_task_starters()]
        await _cycle(clock, notify, 1)
        await cancel_all(tasks, settle_yields=1)

    with _driven() as clock:
        run(scenario(clock))
    writes = [w[0] for w in pixel._pixel.writes]
    assert (0, 200, 0) in writes  # scaled by the default FlashBri=200, pure green channel (WarnVOC's color)
    assert writes[-1] == (0, 0, 0)
    log = run(sgp_reader.get_error_counter())
    assert log["SGP40"]["ErrCount"] == 0
    notify_log = run(notify.get_error_counter())
    assert notify_log["NOTIFY"]["ErrCount"] == 0


def test_i2c_bus_fault_degrades_to_not_triggered_and_stays_isolated_to_sgp40s_own_log() -> None:
    sgp_reader, fake_bus = _make_sgp_reader()
    fake_bus.nak_addresses.add(0x59)  # the sensor itself stops acking - same fault as
    # test_asy_sgp40_driver.py's own test_read_sgp_i2c_nak_during_measurement_is_caught_and_counted
    pixel, notify = _make_stack(sgp_reader)
    fake_bus.read_queue.append(_word(30000))

    async def scenario(clock: DrivenTime) -> "tuple[ErrorLog, ErrorLog]":
        # Awaited directly, not through _drive_one_cycle()'s sync run(): this coroutine already runs under run(),
        # which refuses a nested call (tests/_async_harness.py).
        data, compensated, _serialized = await sgp_reader._read_sgp(None, serialize=False, deserialize=False)  # the fault happens inside here
        await sgp_reader._error_check(data, condition=compensated and data[0] is None)
        await sgp_reader._store_sgp(data)

        await notify._set_dict_cfg({"FlashInterval": 3600.0, "FlashDur": 0.5}, notify.get_cfg_schema())
        tasks = [s() for s in pixel.get_task_starters()] + [s() for s in notify.get_task_starters()]
        await _cycle(clock, notify, 0)  # one monitor pass: nothing was triggered, so nothing settles
        await cancel_all(tasks, settle_yields=1)

        sgp_log = await sgp_reader.get_error_counter()
        notify_log = await notify.get_error_counter()
        return sgp_log, notify_log

    with _driven() as clock:
        sgp_log, notify_log = run(scenario(clock))
    # the fault is real and counted, but attributed to SGP40 alone.
    err_count = sgp_log["SGP40"]["ErrCount"]
    assert isinstance(err_count, int)
    assert err_count >= 1
    assert notify_log["NOTIFY"]["ErrCount"] == 0
    # One off-state frame from the signal loop's start and one from the overlay task's start, nothing else: no signal
    # was triggered, data.VOC being None on a faulted cycle, so _check_one() never counts it as above threshold.
    assert [w[0] for w in pixel._pixel.writes] == [(0, 0, 0), (0, 0, 0)]


def test_recovers_and_triggers_normally_after_a_prior_fault() -> None:
    with FastAsyncSleep():
        sgp_reader, fake_bus = _make_sgp_reader()
        # Settle the baseline while the bus is still healthy, then fault a couple of cycles, then
        # recover - proves an earlier fault doesn't permanently poison the algorithm's own learned
        # state the way a naive "reset on error" implementation might.
        for _ in range(160):
            data = _drive_one_cycle(sgp_reader, fake_bus, 30000)
        assert data.VOC == 100
        fake_bus.nak_addresses.add(0x59)
        for _ in range(2):
            _drive_one_cycle(sgp_reader, fake_bus, 30000)
        fake_bus.nak_addresses.discard(0x59)
        elevated = None
        for _ in range(40):
            elevated = _drive_one_cycle(sgp_reader, fake_bus, 5000)
            if isinstance(elevated.VOC, int) and elevated.VOC > 350:
                break
        assert elevated is not None and isinstance(elevated.VOC, int) and elevated.VOC > 350

    pixel, notify = _make_stack(sgp_reader)

    async def scenario(clock: DrivenTime) -> None:
        await notify._set_dict_cfg({"FlashInterval": 3600.0, "FlashDur": 0.5}, notify.get_cfg_schema())
        tasks = [s() for s in pixel.get_task_starters()] + [s() for s in notify.get_task_starters()]
        await _cycle(clock, notify, 1)
        await cancel_all(tasks, settle_yields=1)

    with _driven() as clock:
        run(scenario(clock))
    writes = [w[0] for w in pixel._pixel.writes]
    assert (0, 200, 0) in writes  # the prior fault didn't permanently poison later good reads
    sgp_log = run(sgp_reader.get_error_counter())
    # the earlier fault's log entry is still on record - a later success doesn't erase history.
    err_count = sgp_log["SGP40"]["ErrCount"]
    assert isinstance(err_count, int)
    assert err_count >= 1


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
