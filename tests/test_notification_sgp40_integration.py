"""Cross-module integration: a real SGP40_Reader feeding a real NotificationCoordinator, driving a real NeopixelDriver - fills the WarnVOC gap test_notification_scd30_integration.py leaves (it only exercises WarnCO2).
Only tests/neopixel.py's fake write surface and tests/machine.py's fake I2C bus are mocked; every layer above the raw I2C transaction runs for real."""
# VOC index calibration note (verified directly against voc_algorithm.py): a single raw reading
# never moves the index - _VOCALGORITHM_INITIAL_BLACKOUT (45 sampling intervals) must elapse first,
# and the index then settles toward 100 (the algorithm's "clean air" baseline) under any *constant*
# raw signal - a deviation-from-learned-baseline index, not an absolute-concentration one. A real
# threshold crossing needs two phases: settle near 100, then step away from that raw value. Also
# confirmed: a higher raw tick count moves the index *down* (raw increase = cleaner air on this
# sensor's convention), so the spike-inducing step is a drop in raw, not a rise.

import asyncio
import os

from asy_i2c_driver import I2C
from asy_neopixel_driver import NeopixelDriver
from asy_notification_service import NotificationCoordinator, NotificationSignal
from asy_sgp40_driver import SGP40_Reader

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
    # Same technique as test_asy_sgp40_driver.py's own _FastAsyncSleep: measure_index_and_raw()'s
    # real command-delay sleeps (tens of ms each) would otherwise make the ~180-cycle baseline-settle
    # + threshold-spike sequence below take upward of 15s per test. asyncio.sleep is a shared,
    # process-wide function, restored on exit regardless of how the `with` block exits.
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


_sweep_stale_tmp_dirs("notify_sgp40_")


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
    path = _TMP_DIR + "/notify_sgp40_" + str(_next_dir)
    try:
        os.mkdir(path)
    except OSError:
        pass
    _remove_any(path + "/config_NOTIFY.cfg")
    return path + "/"


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
    reader = SGP40_Reader(i2c, _comp_data, max_module_error=2, cfg_path=_tmp_cfg_dir())
    run(reader.pr.setup())
    return reader, reader.sgp.i2c_sgp40.i2c_device.i2c._i2c


async def voc_value_callback(sgp_reader: SGP40_Reader) -> "int | float | None":
    # Verbatim mirror of improved-quality/sensortask-wozi.py's own voc_value_callback() body.
    sgp_data = await sgp_reader.get_data()
    if sgp_data is None or sgp_data.VOC is None:
        return None
    return int(sgp_data.VOC)


def make_stack(sgp_reader: SGP40_Reader) -> "tuple[NeopixelDriver, NotificationCoordinator]":
    pixel = NeopixelDriver(0, neopixel_freq=100)

    async def get_voc() -> "int | float | None":
        return await voc_value_callback(sgp_reader)

    notify = NotificationCoordinator(pixel.request_signal, _local_time, cfg_path=_tmp_cfg_dir())
    signal = NotificationSignal("WarnVOC", get_voc, (("WarnVOC", "int", 350, 0, 500, None),), (0, 1, 0))
    notify.register(signal)
    notify.finalize()
    run(notify.cfgmgr.setup())
    return pixel, notify


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


def _drive_one_cycle(reader: SGP40_Reader, fake_bus: "Any", raw: int) -> "Any":
    # Exactly what read_loop() itself does per cycle when no FRAM backup is configured (see
    # asy_sgp40_driver.py) - driven directly instead of through the full trigger/timer machinery,
    # which is already exhaustively covered by test_asy_sgp40_driver.py's own tests.
    fake_bus.read_queue.append(_word(raw))
    data, compensated, _serialized = run(reader._read_sgp(None, False, False))
    run(reader._error_check(data, condition=compensated))
    run(reader._store_sgp(data))
    return data


def _settle_and_spike(reader: SGP40_Reader, fake_bus: "Any") -> "Any":
    # Phase 1: settle the algorithm's learned baseline under a constant raw signal (see module
    # docstring's calibration note - _VOCALGORITHM_INITIAL_BLACKOUT=45 plus settling time).
    for _ in range(160):
        data = _drive_one_cycle(reader, fake_bus, 30000)
    assert data.VOC == 100  # confirms the baseline genuinely settled before phase 2 starts
    # Phase 2: step to a much lower raw value - a real, sudden air-quality change from the sensor's
    # own already-learned "clean" baseline - until the index actually crosses WarnVOC's default
    # threshold (350). Loop-until-crossed rather than a hardcoded count: robust to the exact
    # convergence curve, which is fixed-point-arithmetic-derived and not worth pinning exactly.
    for _ in range(40):
        data = _drive_one_cycle(reader, fake_bus, 5000)
        if isinstance(data.VOC, int) and data.VOC > 350:
            return data
    raise AssertionError("VOC index never crossed the WarnVOC threshold - calibration assumption broken")


def test_real_sensor_reading_above_threshold_flows_through_to_a_real_ramp() -> None:
    with _FastAsyncSleep():
        sgp_reader, fake_bus = make_sgp_reader()
        elevated = _settle_and_spike(sgp_reader, fake_bus)
    assert elevated.VOC is not None and elevated.VOC > 350
    pixel, notify = make_stack(sgp_reader)

    async def scenario() -> None:
        await notify._set_dict_cfg({"Interv": 3600.0, "FlashDur": 0.5}, notify.get_cfg_schema())
        tasks = [s() for s in pixel.get_task_starters()] + [s() for s in notify.get_task_starters()]
        await asyncio.sleep(1.3)  # one triggered cycle's real settle time (2*0.5=1.0s) + margin
        await _cancel_all(tasks)

    run(scenario())
    writes = [w[0] for w in pixel.pixel.writes]
    assert (0, 200, 0) in writes  # scaled by the default FlashBri=200, pure green channel (WarnVOC's color)
    assert writes[-1] == (0, 0, 0)
    log = run(sgp_reader.get_error_counter())
    assert log["SGP40"]["ErrCount"] == 0
    notify_log = run(notify.get_error_counter())
    assert notify_log["NOTIFY"]["ErrCount"] == 0


def test_i2c_bus_fault_degrades_to_not_triggered_and_stays_isolated_to_sgp40s_own_log() -> None:
    sgp_reader, fake_bus = make_sgp_reader()
    fake_bus.nak_addresses.add(0x59)  # the sensor itself stops acking - same fault as
    # test_asy_sgp40_driver.py's own test_read_sgp_i2c_nak_during_measurement_is_caught_and_counted
    pixel, notify = make_stack(sgp_reader)
    fake_bus.read_queue.append(_word(30000))

    async def scenario() -> "tuple[dict[str, Any], dict[str, Any]]":
        # Awaited directly, not through _drive_one_cycle()'s sync run() wrapper - this scenario()
        # is itself already running under this file's own top-level run()/asyncio.run(), and a
        # nested asyncio.run() call segfaults the interpreter (see test_notification_scd30_
        # integration.py's own comment on this exact gotcha - found the hard way while writing
        # this test, not copied defensively).
        data, compensated, _serialized = await sgp_reader._read_sgp(None, False, False)  # the fault happens inside here
        await sgp_reader._error_check(data, condition=compensated)
        await sgp_reader._store_sgp(data)

        await notify._set_dict_cfg({"Interv": 3600.0, "FlashDur": 0.5}, notify.get_cfg_schema())
        tasks = [s() for s in pixel.get_task_starters()] + [s() for s in notify.get_task_starters()]
        await asyncio.sleep(0.2)  # one monitor_loop() pass - nothing to settle, nothing was triggered
        await _cancel_all(tasks)

        sgp_log = await sgp_reader.get_error_counter()
        notify_log = await notify.get_error_counter()
        return sgp_log, notify_log

    sgp_log, notify_log = run(scenario())
    # the fault is real and counted, but attributed to SGP40 alone.
    err_count = sgp_log["SGP40"]["ErrCount"]
    assert isinstance(err_count, int)
    assert err_count >= 1
    assert notify_log["NOTIFY"]["ErrCount"] == 0
    # neopixel_signal()'s own startup sets a defined (0,0,0) off state once, unconditionally -
    # nothing beyond that single boot-time write, since no signal was ever triggered (data.VOC is
    # None on a faulted cycle, so voc_value_callback() returns None - never counted as "above
    # threshold").
    assert [w[0] for w in pixel.pixel.writes] == [(0, 0, 0)]


def test_recovers_and_triggers_normally_after_a_prior_fault() -> None:
    with _FastAsyncSleep():
        sgp_reader, fake_bus = make_sgp_reader()
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

    pixel, notify = make_stack(sgp_reader)

    async def scenario() -> None:
        await notify._set_dict_cfg({"Interv": 3600.0, "FlashDur": 0.5}, notify.get_cfg_schema())
        tasks = [s() for s in pixel.get_task_starters()] + [s() for s in notify.get_task_starters()]
        await asyncio.sleep(1.3)
        await _cancel_all(tasks)

    run(scenario())
    writes = [w[0] for w in pixel.pixel.writes]
    assert (0, 200, 0) in writes  # the prior fault didn't permanently poison later good reads
    sgp_log = run(sgp_reader.get_error_counter())
    # the earlier fault's log entry is still on record - a later success doesn't erase history.
    err_count = sgp_log["SGP40"]["ErrCount"]
    assert isinstance(err_count, int)
    assert err_count >= 1


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
