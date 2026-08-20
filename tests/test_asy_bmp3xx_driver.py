import asyncio
import errno as errno_mod
import os
import struct

from _fram_chip_fake import FakeMB85RS64V
from machine import I2C as FakeI2C
from machine import Timer as FakeTimer

import asy_spi_driver
from asy_bmp3xx_driver import BMP3XX, BMP3XX_I2C, BMP3xx_Reader
from asy_fram_manager import AsyFramManager
from asy_i2c_driver import I2C
from asy_spi_driver import SPI
from print_log import PrintLogHistoryStore

# Same one-process-per-test-file swap as test_print_log.py/test_asy_fram_manager.py: routes
# AsyFramManager's SPI traffic to the simulated FRAM chip instead of unavailable real hardware.
asy_spi_driver._SPI = FakeMB85RS64V  # type: ignore[misc]

# Mirrors of asy_bmp3xx_driver.py's own underscore-prefixed micropython.const() values - these
# are compiled away entirely (confirmed: MicroPython folds a const() name into every use site at
# compile time, so it isn't a real importable module attribute - see SPECIFICATION.md Part E.5.1's "Reading
# the numbers" and BACKLOG.md; `ImportError: can't import name _BMP388_CHIP_ID` confirmed this
# directly). Kept in exact sync with the driver's own values by construction/citation below, not
# re-derived independently.
_BMP388_CHIP_ID = 0x50  # also reported by BMP384
_BMP390_CHIP_ID = 0x60
_REGISTER_CHIPID = 0x00
_REGISTER_ERR = 0x02
_REGISTER_STATUS = 0x03
_REGISTER_PRESSUREDATA = 0x04
_REGISTER_CONTROL = 0x1B
_REGISTER_OSR = 0x1C
_REGISTER_CONFIG = 0x1F
_REGISTER_CAL_DATA = 0x31
_REGISTER_CMD = 0x7E
_OSR_SETTINGS = (1, 2, 4, 8, 16, 32)
_IIR_SETTINGS = (0, 1, 3, 7, 15, 31, 63, 127)

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


async def _settle(n: int = 5) -> None:
    for _ in range(n):
        await asyncio.sleep(0)


class _FastAsyncSleep:
    # I2CDevice.setup()'s _probe_for_device() makes two real 0.1s asyncio.sleep() calls (settle
    # time around the probe write) - fine for a directly-`run()`-awaited coroutine, but far too
    # slow for a test driving read_loop() as a background task through a bounded sleep(0) pump
    # loop (same technique as test_asy_sgp40_driver.py's own _FastAsyncSleep). asyncio.sleep is a
    # shared, process-wide function, restored on exit regardless of how the `with` block exits.
    def __enter__(self) -> "_FastAsyncSleep":
        self._real_sleep = asyncio.sleep

        async def _fast(_seconds: float) -> None:
            await self._real_sleep(0)

        asyncio.sleep = _fast  # type: ignore[assignment]  # deliberate monkeypatch, not a real caller mismatch
        return self

    def __exit__(self, *exc_info: object) -> None:
        asyncio.sleep = self._real_sleep


class _RaiseOnArm:
    # Same technique as test_system_service.py's/test_asy_wifi_service.py's own _RaiseOnArm -
    # toggles tests/machine.py's Timer.raise_on_arm (a shared class attribute, not per-instance)
    # for the duration of the `with` block, simulating a real rp2 Timer.init() that can't arm.
    # `exc` picks which of start_timer()'s two guarded arms gets exercised: the default
    # OSError(ENOMEM) alarm-pool-exhaustion one, or the MemoryError one a failed allocation raises
    # instead (see tests/machine.py's Timer.raise_on_arm_exc). Both class attributes are restored
    # on exit regardless of how the block exits.
    def __init__(self, exc: "type[BaseException]" = OSError) -> None:
        self._exc = exc

    def __enter__(self) -> "_RaiseOnArm":
        FakeTimer.raise_on_arm_exc = self._exc
        FakeTimer.raise_on_arm = True
        return self

    def __exit__(self, *exc_info: object) -> None:
        FakeTimer.raise_on_arm = False
        FakeTimer.raise_on_arm_exc = OSError


_ADDR = 0x77

# A fixed, reproducible calibration/ADC dataset used by the _read() correctness tests: raw NVM
# register bytes chosen within each field's real byte width (format "<HHbhhbbHHbbhbb", see
# _read_coefficients()), plus a matching expected (pressure_hpa, temperature) pair independently
# computed via the same Bosch-documented formula (verified directly against
# datasheets/bmp3xx/bst-bmp388-ds001.pdf sec 9.1-9.3) outside this file, so this is a genuine
# regression check on the driver's own byte-unpacking/scaling/wiring, not a tautology.
_CAL_RAW = bytes(
    struct.pack(
        "<HHbhhbbHHbbhbb",
        28617,  # T1
        26074,  # T2
        -10,  # T3
        -3944,  # P1
        -10416,  # P2
        26,  # P3
        0,  # P4
        30462,  # P5
        120,  # P6
        4,  # P7
        0,  # P8
        4285,  # P9
        22,  # P10
        -60,  # P11
    )
)
_ADC_P = 8300000
_ADC_T = 8500000
_EXPECTED_TEMPERATURE = 28.460795242070162
_EXPECTED_PRESSURE_HPA = 713.765147356092


def _adc_to_data6(adc_p: int, adc_t: int) -> bytes:
    # PRESSUREDATA burst layout: P_XLSB, P_LSB, P_MSB, T_XLSB, T_LSB, T_MSB (datasheet sec 4.3.4/4.3.5).
    def triplet(v: int) -> bytes:
        return bytes([v & 0xFF, (v >> 8) & 0xFF, (v >> 16) & 0xFF])

    return triplet(adc_p) + triplet(adc_t)


def make_i2c() -> I2C:
    return I2C(0, scl_pin=1, sda_pin=0, frequency=100000)


def fake(i2c: I2C) -> FakeI2C:
    return i2c._i2c  # type: ignore[return-value]


def seed_chip_id(i2c: I2C, chip_id: int, address: int = _ADDR) -> None:
    fake(i2c).registers[(address, _REGISTER_CHIPID)] = bytearray([chip_id])


def seed_status(i2c: I2C, value: int, address: int = _ADDR) -> None:
    fake(i2c).registers[(address, _REGISTER_STATUS)] = bytearray([value])


def seed_err(i2c: I2C, value: int, address: int = _ADDR) -> None:
    fake(i2c).registers[(address, _REGISTER_ERR)] = bytearray([value])


def seed_calibration(i2c: I2C, raw: bytes = _CAL_RAW, address: int = _ADDR) -> None:
    fake(i2c).registers[(address, _REGISTER_CAL_DATA)] = bytearray(raw)


def seed_data(i2c: I2C, six_bytes: bytes, address: int = _ADDR) -> None:
    fake(i2c).registers[(address, _REGISTER_PRESSUREDATA)] = bytearray(six_bytes)


# tests/machine.py's fake I2C models exactly the transaction shapes datasheets/bmp3xx/
# bst-bmp388-ds001.pdf sec 5 ("Digital interfaces") documents as supported: single-byte
# read/write (readfrom_mem/writeto_mem with nbytes=1, e.g. seed_chip_id/seed_status/seed_err
# above) and multi-byte read "using a single register address which is auto-incremented" (the
# 6-byte PRESSUREDATA burst, the 21-byte CAL_DATA burst) - readfrom_mem(address, memaddr, nbytes)
# returning one blob keyed by the burst's starting register is a faithful simplification of that
# auto-increment behavior, since this driver only ever requests a burst starting exactly at the
# base register the datasheet documents. The datasheet's other supported shape, "multiple byte
# write (using pairs of register addresses and register data)", is never used by this driver
# (every write here is a single register), so it isn't modeled.
def make_bmp(address: int = _ADDR) -> "tuple[I2C, BMP3XX_I2C]":
    i2c = make_i2c()
    return i2c, BMP3XX_I2C(i2c, address=address)


def ready_bmp(address: int = _ADDR) -> "tuple[I2C, BMP3XX_I2C]":
    # A BMP3XX_I2C pre-seeded so reset()/_read() succeed immediately without any poll retries:
    # STATUS reports both cmd_rdy and data-ready, ERR_REG is clear.
    i2c, bmp = make_bmp(address)
    seed_status(i2c, 0x10 | 0x60, address)  # cmd_rdy | drdy_press | drdy_temp
    seed_err(i2c, 0x00, address)
    return i2c, bmp


class _BadBurstRead:
    # Replaces the device session's own get_register_struct() with a wrapper returning `value`
    # instead of the real 6-byte blob, for the PRESSUREDATA burst only - every other register read
    # (CONTROL/STATUS/CAL_DATA/OSR) still goes to the real fake-I2C bus, so _read() gets all the
    # way past its forced-mode trigger and data-ready poll to the burst-length guard. Same
    # deliberate-monkeypatch technique other test files use for a collaborator they don't own;
    # restored on exit regardless of how the `with` block exits.
    #
    # tests/machine.py's fake I2C can't produce this shape on its own (readfrom_mem always returns
    # exactly nbytes, zero-padded/truncated like real hardware), but asy_i2c_driver.py's own
    # get_register_struct() genuinely can: it returns None on a deinitialized bus, on a malformed
    # format string, and on a zero-field unpack - the exact "not bytes / not 6 bytes" contract
    # violation _read()'s guard exists for, which every register read in this driver is otherwise
    # only protected against at the _read_register()/_get_osr_setting() layer.
    def __init__(self, bmp: BMP3XX_I2C, value: "bytes | None") -> None:
        self._device = bmp.i2c_bmp3xx.i2c_device
        self._value = value

    def __enter__(self) -> "_BadBurstRead":
        self._real = self._device.get_register_struct

        async def _patched(reg_addr: int, reg_format: str, addrsize: "int | None" = None) -> "int | float | bytes | None":
            if reg_addr == _REGISTER_PRESSUREDATA:
                return self._value
            return await self._real(reg_addr, reg_format, addrsize)

        self._device.get_register_struct = _patched  # type: ignore[method-assign]  # deliberate monkeypatch, not a real caller mismatch
        return self

    def __exit__(self, *exc_info: object) -> None:
        self._device.get_register_struct = self._real  # type: ignore[method-assign]


# ---------------------------------------------------------------------------
# setup() / chip ID recognition
# ---------------------------------------------------------------------------


def test_setup_accepts_bmp388_chip_id() -> None:
    i2c, bmp = ready_bmp()
    seed_chip_id(i2c, _BMP388_CHIP_ID)
    seed_calibration(i2c)
    run(bmp.setup())  # must not raise


def test_setup_accepts_bmp390_chip_id() -> None:
    i2c, bmp = ready_bmp()
    seed_chip_id(i2c, _BMP390_CHIP_ID)
    seed_calibration(i2c)
    run(bmp.setup())  # must not raise


def test_setup_accepts_bmp384_since_it_shares_bmp388s_chip_id() -> None:
    # Confirmed directly against datasheets/bmp3xx/bst-bmp384-ds003.pdf's own CHIP_ID register
    # table: BMP384 reports 0x50, the same as BMP388 - not a separate ID the driver needs to know.
    i2c, bmp = ready_bmp()
    seed_chip_id(i2c, 0x50)
    seed_calibration(i2c)
    run(bmp.setup())  # must not raise


def test_setup_rejects_unknown_chip_id() -> None:
    i2c, bmp = ready_bmp()
    seed_chip_id(i2c, 0x99)
    seed_calibration(i2c)
    try:
        run(bmp.setup())
        raised = False
    except RuntimeError:
        raised = True
    assert raised


def test_setup_reads_and_scales_calibration_coefficients() -> None:
    i2c, bmp = ready_bmp()
    seed_chip_id(i2c, _BMP388_CHIP_ID)
    seed_calibration(i2c)
    run(bmp.setup())
    # T1/P5 use the documented 2**-8 / 2**-3 (i.e. *256 / *8) scale factors - the two exponents in
    # the table easiest to get backwards (division instead of multiplication).
    assert bmp._temp_calib[0] == 28617 * 256
    assert bmp._pressure_calib[4] == 30462 * 8


def test_setup_rejects_all_zero_calibration_data() -> None:
    # Real factory-trimmed data is never all one repeated byte - a stuck bus (SDA/SCL disconnected)
    # or a corrupted read commonly reads back as all-0x00 or all-0xFF instead, per Bosch's own
    # self-test app note's "trimming data verification" concept.
    i2c, bmp = ready_bmp()
    seed_chip_id(i2c, _BMP388_CHIP_ID)
    seed_calibration(i2c, raw=bytes(21))
    try:
        run(bmp.setup())
        raised = False
    except RuntimeError:
        raised = True
    assert raised


def test_setup_rejects_all_ff_calibration_data() -> None:
    i2c, bmp = ready_bmp()
    seed_chip_id(i2c, _BMP388_CHIP_ID)
    seed_calibration(i2c, raw=bytes([0xFF] * 21))
    try:
        run(bmp.setup())
        raised = False
    except RuntimeError:
        raised = True
    assert raised


def test_read_coefficients_accepts_plausible_non_uniform_data() -> None:
    # Regression guard: the all-zero/all-ff check must not false-positive on real-looking data.
    i2c, bmp = make_bmp()
    seed_calibration(i2c)
    run(bmp._read_coefficients())  # must not raise
    assert bmp._temp_calib[0] == 28617 * 256


def test_setup_applies_custom_sea_level_pressure_and_wait_time() -> None:
    # Neither optional setup() parameter is exercised by any test above (all call setup() with no
    # args) or by any real caller in this codebase (BMP3xx_Reader._init_bmp() always calls
    # self.bmp.setup() with no args too) - confirms they're at least wired correctly if ever used.
    i2c, bmp = ready_bmp()
    seed_chip_id(i2c, _BMP388_CHIP_ID)
    seed_calibration(i2c)
    run(bmp.setup(sea_level_pressure=950.0, wait_time=0.01))
    assert bmp.sea_level_pressure == 950.0
    assert bmp._wait_time == 0.01


# ---------------------------------------------------------------------------
# reset() - cmd_rdy wait, softreset write, ERR_REG cmd_err verification
# ---------------------------------------------------------------------------


def test_reset_writes_softreset_after_cmd_rdy_ready() -> None:
    i2c, bmp = ready_bmp()
    run(bmp.reset())
    assert fake(i2c).registers[(_ADDR, _REGISTER_CMD)] == bytearray([0xB6])


def test_reset_waits_for_cmd_rdy_before_writing() -> None:
    i2c, bmp = make_bmp()
    seed_status(i2c, 0x00)  # not ready yet
    seed_err(i2c, 0x00)

    async def flip_ready_after_a_tick() -> None:
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        seed_status(i2c, 0x10)  # cmd_rdy

    async def scenario() -> None:
        flipper = asyncio.create_task(flip_ready_after_a_tick())
        await bmp.reset()
        await flipper

    run(scenario())
    assert fake(i2c).registers[(_ADDR, _REGISTER_CMD)] == bytearray([0xB6])


def test_reset_raises_oserror_on_cmd_rdy_timeout() -> None:
    i2c, bmp = make_bmp()
    seed_status(i2c, 0x00)  # never becomes ready
    try:
        run(bmp.reset())
        raised = False
    except OSError:
        raised = True
    assert raised
    assert (_ADDR, _REGISTER_CMD) not in fake(i2c).registers  # never reached the write


def test_reset_raises_oserror_when_bus_deinitialized_mid_poll() -> None:
    # asy_i2c_driver.py's own contract: a deinitialized bus makes get_register_struct() return
    # None rather than raise - _wait_status_bits() treats that the same as "not ready yet" and
    # keeps retrying until its own timeout elapses, then raises OSError. The message reads as a
    # genuine hardware timeout even though the real cause is different, but confirms the poll
    # still terminates within its bounded timeout instead of hanging forever either way.
    i2c, bmp = make_bmp()
    seed_status(i2c, 0x00)  # not ready
    i2c.deinit()
    try:
        run(bmp.reset())
        raised = False
    except OSError:
        raised = True
    assert raised


def test_reset_raises_runtime_error_when_cmd_err_set() -> None:
    i2c, bmp = ready_bmp()
    seed_err(i2c, 0x02)  # cmd_err bit set
    try:
        run(bmp.reset())
        raised = False
    except RuntimeError:
        raised = True
    assert raised
    # the write itself still happened - cmd_err is only checked *after* issuing the command
    assert fake(i2c).registers[(_ADDR, _REGISTER_CMD)] == bytearray([0xB6])


def test_reset_succeeds_when_err_reg_clear() -> None:
    i2c, bmp = ready_bmp()
    run(bmp.reset())  # must not raise


# ---------------------------------------------------------------------------
# _read() / get_pressure() / get_temperature() - forced-mode trigger, status poll,
# compensation math, and the new operating-range sanity check
# ---------------------------------------------------------------------------


def test_read_computes_expected_pressure_and_temperature() -> None:
    i2c, bmp = ready_bmp()
    seed_calibration(i2c)
    seed_data(i2c, _adc_to_data6(_ADC_P, _ADC_T))
    run(bmp._read_coefficients())
    pressure, temperature = run(bmp._read())
    assert abs(temperature - _EXPECTED_TEMPERATURE) < 1e-6
    assert abs(pressure / 100 - _EXPECTED_PRESSURE_HPA) < 1e-6


def test_get_pressure_returns_hpa_and_get_temperature_returns_deg_c() -> None:
    i2c, bmp = ready_bmp()
    seed_calibration(i2c)
    seed_data(i2c, _adc_to_data6(_ADC_P, _ADC_T))
    run(bmp._read_coefficients())
    assert abs(run(bmp.get_pressure()) - _EXPECTED_PRESSURE_HPA) < 1e-6
    assert abs(run(bmp.get_temperature()) - _EXPECTED_TEMPERATURE) < 1e-6


def test_get_pressure_and_temperature_returns_hpa_and_deg_c_from_one_measurement() -> None:
    i2c, bmp = ready_bmp()
    seed_calibration(i2c)
    seed_data(i2c, _adc_to_data6(_ADC_P, _ADC_T))
    run(bmp._read_coefficients())
    pressure, temperature = run(bmp.get_pressure_and_temperature())
    assert abs(pressure - _EXPECTED_PRESSURE_HPA) < 1e-6
    assert abs(temperature - _EXPECTED_TEMPERATURE) < 1e-6


def _count_forced_mode_triggers(i2c: I2C) -> int:
    return sum(
        1
        for entry in fake(i2c).log
        if entry[0] == "writeto_mem" and entry[2] == _REGISTER_CONTROL and bytes(entry[3]) == bytes([0x13])
    )


def test_get_pressure_and_temperature_triggers_exactly_one_measurement_cycle() -> None:
    # Regression test for a real bug present since the original deployed driver (not introduced
    # by this promotion, but never fixed until now): get_pressure() and get_temperature() each
    # independently call _read(), so calling them back-to-back (as _read_bmp() used to) triggered
    # two separate physical conversions instead of one - doubling bus traffic/measurement time
    # and reporting pressure and temperature from two different measurement instants, up to a
    # whole conversion cycle (~129ms at max oversampling) apart. get_pressure_and_temperature()
    # must trigger the forced-mode conversion exactly once.
    i2c, bmp = ready_bmp()
    seed_calibration(i2c)
    seed_data(i2c, _adc_to_data6(_ADC_P, _ADC_T))
    run(bmp._read_coefficients())
    run(bmp.get_pressure_and_temperature())
    assert _count_forced_mode_triggers(i2c) == 1


def test_get_pressure_and_get_temperature_called_separately_do_trigger_two_measurements() -> None:
    # Documents the standalone get_pressure()/get_temperature() behavior as intentional (each is
    # still a valid independent single-value query) - contrasted with the combined getter above,
    # which is what _read_bmp() now uses instead of this two-call pattern.
    i2c, bmp = ready_bmp()
    seed_calibration(i2c)
    seed_data(i2c, _adc_to_data6(_ADC_P, _ADC_T))
    run(bmp._read_coefficients())
    run(bmp.get_pressure())
    run(bmp.get_temperature())
    assert _count_forced_mode_triggers(i2c) == 2


def test_read_triggers_forced_mode() -> None:
    i2c, bmp = ready_bmp()
    seed_calibration(i2c)
    seed_data(i2c, _adc_to_data6(_ADC_P, _ADC_T))
    run(bmp._read_coefficients())
    run(bmp._read())
    assert fake(i2c).registers[(_ADDR, _REGISTER_CONTROL)] == bytearray([0x13])


def test_read_waits_for_data_ready_before_burst_read() -> None:
    i2c, bmp = make_bmp()
    seed_status(i2c, 0x00)  # not ready yet
    seed_calibration(i2c)
    seed_data(i2c, _adc_to_data6(_ADC_P, _ADC_T))
    run(bmp._read_coefficients())

    async def flip_ready_after_a_tick() -> None:
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        seed_status(i2c, 0x60)  # drdy_press | drdy_temp

    async def scenario() -> "tuple[float, float]":
        flipper = asyncio.create_task(flip_ready_after_a_tick())
        result = await bmp._read()
        await flipper
        return result

    pressure, temperature = run(scenario())
    assert abs(temperature - _EXPECTED_TEMPERATURE) < 1e-6


def test_read_raises_oserror_on_status_timeout() -> None:
    i2c, bmp = make_bmp()
    seed_status(i2c, 0x00)  # never becomes ready
    seed_calibration(i2c)
    run(bmp._read_coefficients())
    try:
        run(bmp._read())
        raised = False
    except OSError:
        raised = True
    assert raised


def test_read_raises_oserror_when_bus_deinitialized_mid_poll() -> None:
    i2c, bmp = make_bmp()
    seed_status(i2c, 0x00)  # not ready
    seed_calibration(i2c)
    run(bmp._read_coefficients())
    i2c.deinit()
    try:
        run(bmp._read())
        raised = False
    except OSError:
        raised = True
    assert raised


def test_read_raises_oserror_when_the_data_burst_returns_an_unexpected_result() -> None:
    # _read()'s defensive guard between the burst read and the compensation math: without it, a
    # None (asy_i2c_driver.py's own "bus not initialized"/"unpack produced nothing" sentinel) would
    # raise a cryptic TypeError from data[2] << 16, and a short/long blob would either raise
    # IndexError or silently compute a pressure from whatever bytes happened to be there. Each
    # flavor must instead surface as one clearly-messaged OSError, exactly like every other bus
    # fault this layer raises.
    for bad in (None, b"\x00\x00\x00", b"\x00" * 7):
        i2c, bmp = ready_bmp()
        seed_calibration(i2c)
        seed_data(i2c, _adc_to_data6(_ADC_P, _ADC_T))
        run(bmp._read_coefficients())
        with _BadBurstRead(bmp, bad):
            try:
                run(bmp._read())
                raised = False
            except OSError as e:
                raised = "unexpected data burst read result" in str(e)
        assert raised


def test_read_bmp_logs_and_degrades_when_the_data_burst_returns_an_unexpected_result() -> None:
    # Caller side of the guard above: _read_bmp()'s blanket try/except turns that OSError into the
    # same logged errno=13 as any other failed read, returns an all-None result, and _store_bmp()
    # then discards it - the read cycle degrades exactly like a NAKed bus instead of crashing
    # read_loop()'s task or storing a half-computed reading.
    i2c, reader = make_clean_reader("bad_burst_reader")
    seed_chip_id(i2c, _BMP388_CHIP_ID)
    seed_calibration(i2c)
    seed_status(i2c, 0x10 | 0x60)
    seed_err(i2c, 0x00)
    seed_data(i2c, _adc_to_data6(_ADC_P, _ADC_T))
    assert run(reader._init_bmp())

    async def scenario() -> "tuple[tuple, dict]":
        results = await reader._read_bmp()
        await reader._store_bmp(results)
        return results, await reader.get_error_counter()

    with _BadBurstRead(reader.bmp, None):
        results, counters = run(scenario())

    assert results == (None, None, None)
    assert counters["BMP3XX"]["ErrNum"][-1] == 13  # errno=13, "Read failed:"
    assert counters["BMP3XX"]["ErrType"][-1] == "E"
    assert run(reader.get_data()) == BMP3XX(None, None, None, None)  # nothing corrupted got stored


def test_read_rejects_pressure_above_datasheet_operating_range() -> None:
    i2c, bmp = ready_bmp()
    seed_calibration(i2c)
    # A huge adc_p pushes the computed pressure far above the 1250 hPa datasheet ceiling.
    seed_data(i2c, _adc_to_data6(0xFFFFFF, _ADC_T))
    run(bmp._read_coefficients())
    try:
        run(bmp._read())
        raised = False
    except ValueError:
        raised = True
    assert raised


def test_read_rejects_temperature_below_datasheet_operating_range() -> None:
    i2c, bmp = ready_bmp()
    seed_calibration(i2c)
    # adc_t == 0 drives the linear temperature term deeply negative, past the -40 degC floor.
    seed_data(i2c, _adc_to_data6(_ADC_P, 0))
    run(bmp._read_coefficients())
    try:
        run(bmp._read())
        raised = False
    except ValueError:
        raised = True
    assert raised


# ---------------------------------------------------------------------------
# get_altitude() - never called by BMP3xx_Reader today (dead from its perspective), but live,
# reachable public API on BMP3XX_I2C that had zero test coverage before this pass.
# ---------------------------------------------------------------------------


def test_get_altitude_computes_a_plausible_value_at_default_sea_level_pressure() -> None:
    i2c, bmp = ready_bmp()
    seed_calibration(i2c)
    seed_data(i2c, _adc_to_data6(_ADC_P, _ADC_T))
    run(bmp._read_coefficients())
    altitude = run(bmp.get_altitude())
    # _EXPECTED_PRESSURE_HPA (~713.77 hPa) is well below the default 1013.25 hPa sea-level
    # reference, so the computed altitude must be a large positive number (the station reads as
    # "above" the reference), not zero/negative/NaN.
    assert altitude > 1000.0


def test_get_altitude_raises_value_error_for_zero_sea_level_pressure() -> None:
    i2c, bmp = ready_bmp()
    bmp.sea_level_pressure = 0.0
    try:
        run(bmp.get_altitude())
        raised = False
    except ValueError:
        raised = True
    assert raised


def test_get_altitude_raises_value_error_for_negative_sea_level_pressure() -> None:
    # Confirmed directly against the real MicroPython Unix-port interpreter: without this guard,
    # a negative sea_level_pressure produces a confusing TypeError("can't convert complex to
    # float") instead - the fractional exponent (** 0.190284) on a negative base produces a
    # complex number, which float() then rejects. An accidental consequence of Python's numeric
    # tower, not an intentional raise - get_altitude() now raises a clear ValueError up front.
    i2c, bmp = ready_bmp()
    bmp.sea_level_pressure = -50.0
    try:
        run(bmp.get_altitude())
        raised = False
    except ValueError:
        raised = True
    assert raised


# ---------------------------------------------------------------------------
# Oversampling / filter coefficient get/set - value validation, round trips,
# and the shared-OSR-register read-modify-write race fix
# ---------------------------------------------------------------------------


def test_pressure_oversampling_round_trip_every_valid_setting() -> None:
    i2c, bmp = ready_bmp()
    for value in _OSR_SETTINGS:
        run(bmp.set_pressure_oversampling(value))
        assert run(bmp.get_pressure_oversampling()) == value


def test_pressure_oversampling_rejects_invalid_values() -> None:
    i2c, bmp = ready_bmp()
    for bad in (0, 3, 5, 33, -1):
        try:
            run(bmp.set_pressure_oversampling(bad))
            raised = False
        except ValueError:
            raised = True
        assert raised
    assert (_ADDR, _REGISTER_OSR) not in fake(i2c).registers  # never touched the bus


def test_temperature_oversampling_round_trip_every_valid_setting() -> None:
    i2c, bmp = ready_bmp()
    for value in _OSR_SETTINGS:
        run(bmp.set_temperature_oversampling(value))
        assert run(bmp.get_temperature_oversampling()) == value


def test_temperature_oversampling_rejects_invalid_values() -> None:
    i2c, bmp = ready_bmp()
    try:
        run(bmp.set_temperature_oversampling(7))
        raised = False
    except ValueError:
        raised = True
    assert raised


def test_pressure_and_temperature_oversampling_share_osr_register_without_clobbering() -> None:
    # Regression test for the read-modify-write race this promotion fixed: the old hand-rolled
    # "read whole OSR byte, mask, write whole OSR byte" pair released the device-session lock
    # between the read and the write, so a set_temperature_oversampling() landing in that gap
    # could be silently overwritten by a stale set_pressure_oversampling() write (and vice versa).
    # get_bits()/set_bits() (used now) do the read-modify-write in one call with no yield in
    # between, so setting one field can never observe or clobber a torn intermediate state of the
    # other - checked here by setting both, in each order, and confirming neither is lost.
    i2c, bmp = ready_bmp()
    run(bmp.set_pressure_oversampling(8))
    run(bmp.set_temperature_oversampling(4))
    assert run(bmp.get_pressure_oversampling()) == 8
    assert run(bmp.get_temperature_oversampling()) == 4

    run(bmp.set_temperature_oversampling(16))
    run(bmp.set_pressure_oversampling(2))
    assert run(bmp.get_pressure_oversampling()) == 2
    assert run(bmp.get_temperature_oversampling()) == 16


def test_set_pressure_oversampling_holds_device_session_lock_for_the_whole_operation() -> None:
    # Structural counterpart to the race-fix test above: while another operation holds the shared
    # per-sensor session lock, set_pressure_oversampling() must block entirely (not partially
    # apply) until that lock is released - it cannot observe or act on a half-finished state.
    i2c, bmp = ready_bmp()

    async def scenario() -> None:
        async with bmp.i2c_bmp3xx:
            task = asyncio.create_task(bmp.set_pressure_oversampling(8))
            await asyncio.sleep(0)
            assert not task.done()
        await task
        assert task.done()

    run(scenario())
    assert run(bmp.get_pressure_oversampling()) == 8


def test_filter_coefficient_round_trip_every_valid_setting() -> None:
    i2c, bmp = ready_bmp()
    for value in _IIR_SETTINGS:
        run(bmp.set_filter_coefficient(value))
        assert run(bmp.get_filter_coefficient()) == value


def test_filter_coefficient_rejects_invalid_values() -> None:
    # 2 is a real coefficient under the old (wrong) power-of-two tuple this codebase used to have,
    # but not under the corrected 2^index-1 encoding (0,1,3,7,15,31,63,127) - a regression check
    # that the fix actually took effect, not just a generic bad-value check.
    i2c, bmp = ready_bmp()
    try:
        run(bmp.set_filter_coefficient(2))
        raised = False
    except ValueError:
        raised = True
    assert raised
    assert (_ADDR, _REGISTER_CONFIG) not in fake(i2c).registers  # never touched the bus


# ---------------------------------------------------------------------------
# Low-level register helpers and real bus-fault propagation
# ---------------------------------------------------------------------------


def test_read_byte_returns_int() -> None:
    i2c, bmp = make_bmp()
    seed_chip_id(i2c, 0x42)
    assert run(bmp._read_byte(_REGISTER_CHIPID)) == 0x42


def test_read_register_returns_bytes_of_requested_length() -> None:
    i2c, bmp = make_bmp()
    seed_calibration(i2c)
    result = run(bmp._read_register(_REGISTER_CAL_DATA, 21))
    assert isinstance(result, bytes)
    assert result == _CAL_RAW


def test_read_byte_propagates_real_bus_fault() -> None:
    i2c, bmp = make_bmp()
    fake(i2c).nak_addresses.add(_ADDR)
    try:
        run(bmp._read_byte(_REGISTER_CHIPID))
        raised = False
    except OSError as e:
        raised = e.errno == errno_mod.EIO
    assert raised


# ---------------------------------------------------------------------------
# Module-level I2C fault-propagation matrix: both real bus-fault flavors (tests/machine.py's
# I2C fake models RP2040's only two real error codes - EIO for NAK, ETIMEDOUT for a bus-busy/
# clock-stretch timeout, confirmed against ports/rp2/machine_i2c.c per its own docstring), plus
# the reserved-OSR-encoding IndexError regression and the asy_i2c_driver.py "pre-handled
# sentinel" (deinitialized bus) case.
# ---------------------------------------------------------------------------


def test_reset_propagates_bus_busy_fault() -> None:
    i2c, bmp = ready_bmp()
    fake(i2c).busy = True
    try:
        run(bmp.reset())
        raised = False
    except OSError as e:
        raised = e.errno == errno_mod.ETIMEDOUT
    assert raised


def test_read_coefficients_propagates_bus_busy_fault() -> None:
    i2c, bmp = make_bmp()
    fake(i2c).busy = True
    try:
        run(bmp._read_coefficients())
        raised = False
    except OSError as e:
        raised = e.errno == errno_mod.ETIMEDOUT
    assert raised


def test_get_filter_coefficient_propagates_bus_busy_fault() -> None:
    i2c, bmp = ready_bmp()
    fake(i2c).busy = True
    try:
        run(bmp.get_filter_coefficient())
        raised = False
    except OSError as e:
        raised = e.errno == errno_mod.ETIMEDOUT
    assert raised


def test_get_pressure_oversampling_raises_oserror_on_reserved_osr_encoding() -> None:
    # Datasheet (bst-bmp388-ds001.pdf sec 4.3.17): osr_p only documents 3-bit encodings 0-5
    # (x1..x32); 6/7 are undocumented/reserved. A bus disturbance flipping a bit can land exactly
    # here - regression test for this session's exception-safety audit finding: this used to raise
    # a bare, cryptic IndexError from _OSR_SETTINGS[osr] instead of a clearly-messaged OSError.
    i2c, bmp = ready_bmp()
    fake(i2c).registers[(_ADDR, _REGISTER_OSR)] = bytearray([0b110])  # osr_p=6, reserved
    try:
        run(bmp.get_pressure_oversampling())
        raised = False
    except OSError as e:
        raised = "reserved encoding" in str(e)
    assert raised


def test_get_temperature_oversampling_raises_oserror_on_reserved_osr_encoding() -> None:
    i2c, bmp = ready_bmp()
    fake(i2c).registers[(_ADDR, _REGISTER_OSR)] = bytearray([0b111 << 3])  # osr_t=7, reserved
    try:
        run(bmp.get_temperature_oversampling())
        raised = False
    except OSError as e:
        raised = "reserved encoding" in str(e)
    assert raised


def test_bus_deinit_write_no_ops_silently_but_read_raises_oserror() -> None:
    # Demonstrates a real read/write asymmetry in asy_i2c_driver.py's own documented contract:
    # get_bits() returns None on a deinitialized bus (self._i2c is None) - a real, checkable
    # sentinel that _get_osr_setting() turns into a raised OSError - but set_bits() returns None
    # unconditionally, so success and failure look identical and a write-shaped call can silently
    # no-op instead of raising. Not a bug in this driver: it's the lower layer's own deliberate
    # "non-hardware failure" carve-out (a deinitialized bus isn't a real bus disturbance, someone
    # called deinit() without a matching reinit) - documented here rather than assumed.
    i2c, bmp = ready_bmp()
    i2c.deinit()
    run(bmp.set_pressure_oversampling(8))  # must not raise, despite doing nothing
    try:
        run(bmp.get_pressure_oversampling())
        raised = False
    except OSError:
        raised = True
    assert raised


# ---------------------------------------------------------------------------
# BMP3xx_Reader - low-level forwards log failures instead of swallowing them
# ---------------------------------------------------------------------------

_TMP_DIR = "tests/_tmp"


def _tmp_cfg_path(name: str) -> str:
    # cfg_path is a filename *prefix* (ConfigManager builds cfg_path + "config_" + name + ".cfg"),
    # not a directory - each test gets its own prefix so runs never collide with one another.
    try:
        os.mkdir(_TMP_DIR)
    except OSError:
        pass  # already exists
    prefix = _TMP_DIR + "/" + name + "_"
    try:
        os.remove(prefix + "config_BMP3XX.cfg")
    except OSError:
        pass  # already gone
    return prefix


def make_reader(name: str) -> BMP3xx_Reader:
    i2c = make_i2c()
    fake(i2c).nak_addresses.add(_ADDR)  # every bus op on this address fails
    reader = BMP3xx_Reader(i2c, address=_ADDR, cfg_path=_tmp_cfg_path(name))
    run(reader.cfgmgr.setup())
    return reader


def make_clean_reader(name: str, max_module_error: int = 5) -> "tuple[I2C, BMP3xx_Reader]":
    # Unlike make_reader() above, the bus starts untouched (no nak_addresses/busy) - individual
    # tests seed exactly the registers they need for setup()/reads to succeed.
    i2c = make_i2c()
    reader = BMP3xx_Reader(i2c, address=_ADDR, max_module_error=max_module_error, cfg_path=_tmp_cfg_path(name))
    run(reader.cfgmgr.setup())
    return i2c, reader


def test_reader_set_trigger_secs_logs_and_does_not_raise_on_bad_value() -> None:
    # Regression test for this session's exception-safety audit finding: set_trigger_secs() used
    # to call int(value) unguarded, unlike every other low-level forward in this class, so a bad
    # value would raise straight out of it instead of being logged like its siblings.
    reader = make_reader("bad_trigger")  # bus is irrelevant - set_trigger_secs never touches it

    async def scenario() -> dict:
        await reader.set_trigger_secs("not-a-number")  # type: ignore[arg-type]
        await reader.pr.setup()
        return await reader.get_error_counter()

    counters = run(scenario())
    assert counters["BMP3XX"]["ErrCount"] == 1
    assert counters["BMP3XX"]["ErrNum"][-1] == 21


def test_reader_set_trigger_secs_accepts_valid_values() -> None:
    reader = make_reader("good_trigger")
    run(reader.set_trigger_secs(30))
    assert run(reader.trigger_period.get_value()) == 30
    run(reader.set_trigger_secs(45.7))  # int(45.7) == 45, same truncation as the original driver
    assert run(reader.trigger_period.get_value()) == 45


def test_reader_set_trigger_secs_accepts_boundary_values() -> None:
    reader = make_reader("boundary_trigger")
    run(reader.set_trigger_secs(1))
    assert run(reader.trigger_period.get_value()) == 1
    run(reader.set_trigger_secs(3600))
    assert run(reader.trigger_period.get_value()) == 3600


def test_reader_set_trigger_secs_rejects_out_of_range_values() -> None:
    # Bound is 1-3600 seconds, matching the deployed production validation for this exact field
    # (modules/sensortask-wozi.py's `update_valid_json(..., "BMPSampleInterv", "int", res, 1, 3600,
    # ...)`, mirrored across every other sensor's sample interval too). Below/above/zero/negative
    # are all rejected the same way as a bad type - logged (errno=21), the previous value is kept,
    # never raises.
    reader = make_reader("out_of_range_trigger")
    run(reader.set_trigger_secs(30))  # establish a known-good baseline value first
    for bad in (0, -1, 3601, 100000):

        async def scenario(value: int = bad) -> dict:
            await reader.set_trigger_secs(value)
            await reader.pr.setup()
            return await reader.get_error_counter()

        counters = run(scenario())
        assert run(reader.trigger_period.get_value()) == 30  # rejected - kept the prior value
        assert counters["BMP3XX"]["ErrNum"][-1] == 21


def test_reader_set_trigger_secs_rejects_inf_and_nan() -> None:
    # int(float('inf'))/int(float('-inf')) raise OverflowError, not ValueError - confirmed
    # directly against the real MicroPython Unix-port interpreter (int(float('nan')) raises
    # ValueError, already covered by the bad-type/out-of-range cases above). value's own type
    # contract is int | float, so +-inf/NaN are legitimate inputs this must degrade cleanly for.
    reader = make_reader("inf_nan_trigger")
    run(reader.set_trigger_secs(30))  # establish a known-good baseline value first
    for bad in (float("inf"), float("-inf"), float("nan")):

        async def scenario(value: float = bad) -> dict:
            await reader.set_trigger_secs(value)
            await reader.pr.setup()
            return await reader.get_error_counter()

        counters = run(scenario())
        assert run(reader.trigger_period.get_value()) == 30  # rejected - kept the prior value
        assert counters["BMP3XX"]["ErrNum"][-1] == 21


def test_init_bmp_soft_degrades_on_out_of_range_stored_sample_interval() -> None:
    # _init_bmp() routes BMPSampleInterv through set_trigger_secs() (which never raises) rather
    # than writing trigger_period directly, unlike the hardware-facing oversampling/filter values
    # right after it - a stale/out-of-range stored sample interval (e.g. from a config file
    # written before this bound existed) shouldn't fail the whole init attempt and force a task
    # restart the way a genuinely bad hardware value does; it should log and keep going.
    i2c, reader = make_clean_reader("bad_stored_trigger")
    seed_chip_id(i2c, _BMP388_CHIP_ID)
    seed_calibration(i2c)
    seed_status(i2c, 0x10 | 0x60)
    seed_err(i2c, 0x00)
    ok, results = run(reader.cfgmgr.write_config({"SampleInterv": 7200}, _FULL_SCHEMA))
    assert ok is True
    assert results["SampleInterv"] == "Invalid"  # rejected by the schema too (max is 3600)
    # write_config() only accepts the update when the value clears the schema check, so a stale
    # out-of-range value has to be seeded directly into the underlying cache to simulate a config
    # file written before this bound existed - not reachable via write_config() alone anymore.
    reader.cfgmgr._cache["SampleInterv"] = 7200

    assert run(reader._init_bmp()) is True  # doesn't fail the whole init over this
    assert run(reader.get_pressure_oversampling()) == 1  # other config values still applied

    async def error_counter() -> dict:
        return await reader.get_error_counter()

    counters = run(error_counter())["BMP3XX"]
    assert counters["ErrNum"][-1] == 21


def test_reader_get_pressure_oversampling_logs_and_returns_none_on_bus_failure() -> None:
    reader = make_reader("get_pov")

    async def scenario() -> "tuple[int | None, dict]":
        value = await reader.get_pressure_oversampling()
        await reader.pr.setup()
        counters = await reader.get_error_counter()
        return value, counters

    value, counters = run(scenario())
    assert value is None
    assert counters["BMP3XX"]["ErrCount"] > 0


def test_reader_set_pressure_oversampling_logs_and_returns_false_on_bus_failure() -> None:
    reader = make_reader("set_pov")

    async def scenario() -> "tuple[bool, dict]":
        ok = await reader.set_pressure_oversampling(8)
        await reader.pr.setup()
        counters = await reader.get_error_counter()
        return ok, counters

    ok, counters = run(scenario())
    assert ok is False
    assert counters["BMP3XX"]["ErrCount"] > 0


# ---------------------------------------------------------------------------
# Configuration schema: mirrors of asy_bmp3xx_driver.py's own _VAL_* const() tuples (see the
# module-level comment above about why these can't be imported), exercised through the real
# ConfigManager (config_manager.py) attached to a BMP3xx_Reader - every field's full valid range,
# then single and multiple invalid-field recombinations.
# ---------------------------------------------------------------------------

_VAL_SI = (("SampleInterv", "int", 2, 1, 3600, None),)
_VAL_POV = (("PressOvers", "int", 1, None, None, _OSR_SETTINGS),)
_VAL_TOV = (("TempOvers", "int", 1, None, None, _OSR_SETTINGS),)
_VAL_FC = (("FiltCoeff", "int", 0, None, None, _IIR_SETTINGS),)
_VAL_PO = (("PressOffset", "float", 0.0, -500.0, 500.0, None),)
_VAL_TO = (("TempOffset", "float", 0.0, -10.0, 10.0, None),)
_VAL_SLO = (("SeaLevelOffs", "float", 0.0, -1000.0, 5000.0, None),)
_VAL_ATM = (("MeanAtmTemp", "float", 15.0, -50.0, 50.0, None),)
_FULL_SCHEMA = _VAL_SI + _VAL_POV + _VAL_TOV + _VAL_FC + _VAL_PO + _VAL_TO + _VAL_SLO + _VAL_ATM

# name -> (type, min, max), mirroring each _VAL_* tuple's own (name, type, def, min, max, special) -
# only the genuinely continuous-range fields; PressOvers/TempOvers/FiltCoeff are discrete allowed-
# value sets now (see _DISCRETE_FIELDS below), where "midpoint"/"one below min" have no meaning.
_FIELD_BOUNDS = {
    "SampleInterv": ("int", 1, 3600),
    "PressOffset": ("float", -500.0, 500.0),
    "TempOffset": ("float", -10.0, 10.0),
    "SeaLevelOffs": ("float", -1000.0, 5000.0),
    "MeanAtmTemp": ("float", -50.0, 50.0),
}

# name -> its own legal discrete value set, mirroring _VAL_POV/_VAL_TOV/_VAL_FC's "special" slot.
_DISCRETE_FIELDS: "dict[str, tuple[int, ...]]" = {
    "PressOvers": _OSR_SETTINGS,
    "TempOvers": _OSR_SETTINGS,
    "FiltCoeff": _IIR_SETTINGS,
}

_ALL_FIELD_NAMES = list(_FIELD_BOUNDS) + list(_DISCRETE_FIELDS)


def _midpoint(kind: str, lo: "int | float", hi: "int | float") -> "int | float":
    mid = (lo + hi) / 2
    return int(mid) if kind == "int" else float(mid)


def test_config_write_accepts_every_field_at_its_valid_boundaries_and_midpoint() -> None:
    i2c, reader = make_clean_reader("cfg_valid")
    for name, (kind, lo, hi) in _FIELD_BOUNDS.items():
        for value in (lo, hi, _midpoint(kind, lo, hi)):
            ok, results = run(reader.cfgmgr.write_config({name: value}, _FULL_SCHEMA))
            assert ok is True
            assert results[name] in ("Valid", "Unchanged")
            stored = run(reader.cfgmgr.get_dict([name]))
            assert stored is not None
            assert stored[name] == value


def test_config_write_rejects_single_out_of_range_or_wrong_type_field() -> None:
    i2c, reader = make_clean_reader("cfg_single_invalid")
    for name, (kind, lo, hi) in _FIELD_BOUNDS.items():
        step = 1 if kind == "int" else 0.1
        below = lo - step
        above = hi + step
        wrong_type = "nope" if kind == "int" else 1  # str for int fields, int for float fields
        before_dict = run(reader.cfgmgr.get_dict([name]))
        assert before_dict is not None
        before = before_dict[name]
        for bad in (below, above, wrong_type):
            ok, results = run(reader.cfgmgr.write_config({name: bad}, _FULL_SCHEMA))
            assert ok is True  # the write call itself still succeeds; only the field is rejected
            assert results[name] == "Invalid"
        after_dict = run(reader.cfgmgr.get_dict([name]))
        assert after_dict is not None
        assert after_dict[name] == before  # rejected values never reach storage


def test_config_write_rejects_bool_for_int_field_despite_bool_being_an_int_subclass() -> None:
    # config_manager.py's type_or_range_error() uses `type(x) is not int`, which is strict -
    # bool's exact type is `bool`, not `int`, even though bool subclasses int in Python.
    i2c, reader = make_clean_reader("cfg_bool_reject")
    ok, results = run(reader.cfgmgr.write_config({"SampleInterv": True}, _FULL_SCHEMA))
    assert ok is True
    assert results["SampleInterv"] == "Invalid"


def test_config_write_rejects_multiple_invalid_fields_while_keeping_valid_ones() -> None:
    i2c, reader = make_clean_reader("cfg_multi_invalid")
    before = run(reader.cfgmgr.get_dict(_ALL_FIELD_NAMES))
    assert before is not None
    mixed: dict[str, int | float | str | bool | None] = {
        "SampleInterv": 300,  # valid
        "PressOvers": 999,  # invalid: way above max
        "TempOvers": 8,  # valid
        "FiltCoeff": -5,  # invalid: below min
        "PressOffset": 50.0,  # valid
        "TempOffset": "hot",  # invalid: wrong type
        "SeaLevelOffs": 250.0,  # valid
        "MeanAtmTemp": 18.0,  # valid
    }
    ok, results = run(reader.cfgmgr.write_config(mixed, _FULL_SCHEMA))
    assert ok is True
    for name in ("PressOvers", "FiltCoeff", "TempOffset"):
        assert results[name] == "Invalid"
    for name in ("SampleInterv", "TempOvers", "PressOffset", "SeaLevelOffs", "MeanAtmTemp"):
        assert results[name] == "Valid"
    after = run(reader.cfgmgr.get_dict(_ALL_FIELD_NAMES))
    assert after is not None
    assert after["PressOvers"] == before["PressOvers"]
    assert after["FiltCoeff"] == before["FiltCoeff"]
    assert after["TempOffset"] == before["TempOffset"]
    assert after["SampleInterv"] == 300
    assert after["TempOvers"] == 8
    assert after["PressOffset"] == 50.0
    assert after["SeaLevelOffs"] == 250.0
    assert after["MeanAtmTemp"] == 18.0


def test_init_bmp_fails_and_logs_when_stored_oversampling_is_outside_hardware_domain() -> None:
    # Historically the config schema's own PressOvers range was a plain 1-32 continuous range,
    # wider than the sensor's real discrete domain (1/2/4/8/16/32) - see BACKLOG.md's architecture-
    # review note. config_manager.py's discrete-allowed-value-set validator now closes that gap:
    # write_config() itself rejects 20 as "Invalid" (see
    # test_write_config_rejects_a_value_outside_the_discrete_osr_domain below), so this now
    # simulates a stale config file written before that fix existed - same direct-cache-poke
    # technique as test_init_bmp_soft_degrades_on_out_of_range_stored_sample_interval - to confirm
    # _init_bmp() still degrades cleanly (logged, returns False) for a hardware-invalid value that
    # slipped past validation some other way, not just a freshly-rejected one.
    i2c, reader = make_clean_reader("init_bad_osr_value")
    seed_chip_id(i2c, _BMP388_CHIP_ID)
    seed_calibration(i2c)
    seed_status(i2c, 0x10 | 0x60)
    seed_err(i2c, 0x00)
    ok, results = run(reader.cfgmgr.write_config({"PressOvers": 20}, _FULL_SCHEMA))
    assert ok is True
    assert results["PressOvers"] == "Invalid"  # now correctly rejected at the schema layer
    reader.cfgmgr._cache["PressOvers"] = 20  # simulate a stale value from before this fix existed
    assert run(reader._init_bmp()) is False


# ---------------------------------------------------------------------------
# Discrete allowed-value-set fields (PressOvers/TempOvers/FiltCoeff) - config_manager.py's
# discrete-set validator, exercised end-to-end through the real ConfigManager. Closes the
# schema/hardware discrepancy the test above used to document.
# ---------------------------------------------------------------------------


def test_config_write_accepts_every_legal_discrete_value() -> None:
    i2c, reader = make_clean_reader("discrete_valid")
    for name, legal_values in _DISCRETE_FIELDS.items():
        for value in legal_values:
            ok, results = run(reader.cfgmgr.write_config({name: value}, _FULL_SCHEMA))
            assert ok is True
            assert results[name] in ("Valid", "Unchanged")
            stored = run(reader.cfgmgr.get_dict([name]))
            assert stored is not None
            assert stored[name] == value


def test_write_config_rejects_a_value_outside_the_discrete_osr_domain() -> None:
    # 20 is an "in type, in old-range" int that was never a real legal OSR value (only
    # 1/2/4/8/16/32 are) - exactly the gap this validator closes.
    i2c, reader = make_clean_reader("discrete_invalid_osr")
    for name in ("PressOvers", "TempOvers"):
        before = run(reader.cfgmgr.get_dict([name]))
        assert before is not None
        ok, results = run(reader.cfgmgr.write_config({name: 20}, _FULL_SCHEMA))
        assert ok is True
        assert results[name] == "Invalid"
        after = run(reader.cfgmgr.get_dict([name]))
        assert after == before  # untouched


def test_write_config_rejects_a_value_outside_the_discrete_iir_domain() -> None:
    # 100 is in the old [0, 127] range but not one of the real encoded IIR coefficients.
    i2c, reader = make_clean_reader("discrete_invalid_iir")
    before = run(reader.cfgmgr.get_dict(["FiltCoeff"]))
    ok, results = run(reader.cfgmgr.write_config({"FiltCoeff": 100}, _FULL_SCHEMA))
    assert ok is True
    assert results["FiltCoeff"] == "Invalid"
    assert run(reader.cfgmgr.get_dict(["FiltCoeff"])) == before


def test_write_config_rejects_wrong_type_for_a_discrete_field() -> None:
    i2c, reader = make_clean_reader("discrete_wrong_type")
    ok, results = run(reader.cfgmgr.write_config({"PressOvers": "8"}, _FULL_SCHEMA))
    assert ok is True
    assert results["PressOvers"] == "Invalid"


# ---------------------------------------------------------------------------
# get_dict_cfg(): live sensor readback overlay vs. pure config-file fields
# ---------------------------------------------------------------------------


def test_get_dict_cfg_overlays_live_sensor_readback_on_oversampling_and_filter_fields() -> None:
    i2c, reader = make_clean_reader("dict_cfg_live")
    seed_status(i2c, 0x10 | 0x60)
    seed_err(i2c, 0x00)
    run(reader.bmp.set_pressure_oversampling(8))
    run(reader.bmp.set_temperature_oversampling(4))
    run(reader.bmp.set_filter_coefficient(15))
    cfg = run(reader.get_dict_cfg())["BMP3XX"]
    assert cfg["PressOvers"] == 8  # live sensor value, not the config file's stored default (1)
    assert cfg["TempOvers"] == 4
    assert cfg["FiltCoeff"] == 15
    assert cfg["SampleInterv"] == 2  # pure config-file field, no live equivalent to read back


def test_get_dict_cfg_keeps_none_for_oversampling_when_sensor_unreachable() -> None:
    i2c, reader = make_clean_reader("dict_cfg_unreachable")
    fake(i2c).nak_addresses.add(_ADDR)
    cfg = run(reader.get_dict_cfg())["BMP3XX"]
    assert cfg["PressOvers"] is None
    assert cfg["TempOvers"] is None
    assert cfg["FiltCoeff"] is None
    assert cfg["SampleInterv"] == 2  # config-only field, unaffected by the sensor bus failure


# ---------------------------------------------------------------------------
# Integration: BMP3xx_Reader driven together with real print_log.py/base_classes.py/
# asy_i2c_driver.py collaborators (only the raw I2C bus transaction layer is faked) - successful
# interaction, every error type those collaborators can produce, and how a hardware I2C fault
# propagates from the bus all the way up through the Reader's stored state/error counters.
# ---------------------------------------------------------------------------


def test_init_bmp_succeeds_against_healthy_bus_and_applies_stored_config() -> None:
    i2c, reader = make_clean_reader("init_ok")
    seed_chip_id(i2c, _BMP388_CHIP_ID)
    seed_calibration(i2c)
    seed_status(i2c, 0x10 | 0x60)
    seed_err(i2c, 0x00)
    assert run(reader._init_bmp()) is True
    # config-file defaults (PressOvers=1, TempOvers=1, FiltCoeff=0) were pushed to the sensor
    assert run(reader.bmp.get_pressure_oversampling()) == 1
    assert run(reader.bmp.get_temperature_oversampling()) == 1
    assert run(reader.bmp.get_filter_coefficient()) == 0


def test_init_bmp_fails_and_logs_when_setup_raises() -> None:
    i2c, reader = make_clean_reader("init_bad_chip")
    seed_chip_id(i2c, 0x99)  # unrecognized chip ID -> bmp.setup() raises RuntimeError
    seed_calibration(i2c)
    seed_status(i2c, 0x10 | 0x60)

    async def scenario() -> "tuple[bool, dict]":
        ok = await reader._init_bmp()
        counters = await reader.get_error_counter()
        return ok, counters

    ok, counters = run(scenario())
    assert ok is False
    assert counters["BMP3XX"]["ErrCount"] == 1
    assert counters["BMP3XX"]["ErrNum"][-1] == 10  # errno=10, "Error in initial setup"


def test_init_bmp_fails_and_logs_when_config_data_unreadable() -> None:
    i2c, reader = make_clean_reader("init_bad_cfg")
    seed_chip_id(i2c, _BMP388_CHIP_ID)
    seed_calibration(i2c)
    seed_status(i2c, 0x10 | 0x60)
    seed_err(i2c, 0x00)
    reader.cfgmgr.valid = False  # simulate an unreadable/corrupted per-sensor config file

    async def scenario() -> "tuple[bool, dict]":
        ok = await reader._init_bmp()
        counters = await reader.get_error_counter()
        return ok, counters

    ok, counters = run(scenario())
    assert ok is False
    assert counters["BMP3XX"]["ErrNum"][-1] == 11  # errno=11, "Error reading config data!"


def test_store_bmp_falls_back_to_default_compensation_values_when_config_unreadable() -> None:
    # _store_bmp()'s own errno=14 counterpart to _init_bmp()'s errno=11 above - same message text,
    # different call site and different consequence: the compensation values (PressOffset/
    # TempOffset/SeaLevelOffs/MeanAtmTemp) are pure post-processing math inputs, so an unreadable
    # config must not cost the whole reading. It logs, substitutes the documented
    # [0.0, 0.0, 0.0, 15.0] fallback, and stores an uncompensated - but real and complete -
    # measurement instead of raising or writing corrupted data.
    i2c, reader = make_clean_reader("store_fallback_cfg")
    seed_chip_id(i2c, _BMP388_CHIP_ID)
    seed_calibration(i2c)
    seed_status(i2c, 0x10 | 0x60)
    seed_err(i2c, 0x00)
    seed_data(i2c, _adc_to_data6(_ADC_P, _ADC_T))
    ok, results_valid = run(
        reader.cfgmgr.write_config(
            {"PressOffset": 10.0, "TempOffset": 2.0, "SeaLevelOffs": 100.0, "MeanAtmTemp": 25.0}, _FULL_SCHEMA
        )
    )
    assert ok is True
    assert all(status == "Valid" for status in results_valid.values())
    assert run(reader._init_bmp()) is True
    results = run(reader._read_bmp())
    assert results[0] is not None
    assert results[1] is not None

    # Baseline first, with the config readable: the stored offsets really are applied, so the
    # fallback assertions below can't pass just because every offset happened to be 0.0 anyway.
    run(reader._store_bmp(results))
    compensated = run(reader.get_data())
    assert abs(compensated.Pres - (results[0] - 10.0)) < 1e-9
    assert abs(compensated.Temp - (results[1] - 2.0)) < 1e-9

    reader.cfgmgr.valid = False  # simulate an unreadable/corrupted per-sensor config file

    async def scenario() -> dict:
        await reader._store_bmp(results)
        return await reader.get_error_counter()

    counters = run(scenario())["BMP3XX"]
    assert counters["ErrNum"][-1] == 14  # errno=14, "Error reading config data!"
    assert counters["ErrType"][-1] == "E"

    fallback = run(reader.get_data())
    assert fallback.Pres == results[0]  # PressOffset fell back to 0.0, not the stored 10.0
    assert fallback.Temp == results[1]  # TempOffset fell back to 0.0, not the stored 2.0
    # SeaLevelOffs fell back to 0.0 too, and altitude_baro()'s height offset is then exactly zero,
    # so the sea-level-reduced pressure equals the local one (e^0 == 1) - which also means the
    # MeanAtmTemp fallback (15.0) has no observable effect at this height offset, by construction.
    assert fallback.SLPres == results[0]
    assert fallback.SLPres != compensated.SLPres  # the stored 100.0 offset really did change it
    assert fallback.TS == results[2]  # timestamp is passed through untouched either way


def test_reader_read_error_check_threshold_and_self_heal() -> None:
    # base_classes.py's real _error_check(): a bus disturbance appearing mid-operation (after a
    # clean init) must accumulate consecutive failures past max_module_error before giving up, and a
    # later successful read must start unwinding that streak again - the same self-healing
    # behavior read_loop() relies on to tolerate a transient disconnect without a full restart.
    i2c, reader = make_clean_reader("threshold", max_module_error=2)
    seed_chip_id(i2c, _BMP388_CHIP_ID)
    seed_calibration(i2c)
    seed_status(i2c, 0x10 | 0x60)
    seed_err(i2c, 0x00)
    seed_data(i2c, _adc_to_data6(_ADC_P, _ADC_T))

    async def scenario() -> "list[bool]":
        assert await reader._init_bmp()
        fake(i2c).nak_addresses.add(_ADDR)
        outcomes = []
        for _ in range(3):  # max_module_error=2 -> the 3rd consecutive failure crosses the threshold
            results = await reader._read_bmp()
            outcomes.append(await reader._error_check(results))
        fake(i2c).nak_addresses.discard(_ADDR)
        recovered = await reader._read_bmp()
        outcomes.append(await reader._error_check(recovered))
        return outcomes

    assert run(scenario()) == [True, True, False, True]


def test_reader_error_counter_reflects_read_failures_via_print_log() -> None:
    i2c, reader = make_clean_reader("err_counter_shape")
    seed_chip_id(i2c, _BMP388_CHIP_ID)
    seed_calibration(i2c)
    seed_status(i2c, 0x10 | 0x60)
    seed_err(i2c, 0x00)

    async def scenario() -> dict:
        assert await reader._init_bmp()
        fake(i2c).nak_addresses.add(_ADDR)
        await reader._read_bmp()  # errno=13, "Lesefehler:"
        return await reader.get_error_counter()

    counters = run(scenario())["BMP3XX"]
    assert counters["ErrCount"] == 1
    assert counters["ErrNum"][-1] == 13
    assert counters["ErrType"][-1] == "E"


def test_reader_read_bmp_triggers_exactly_one_measurement_cycle() -> None:
    # Reader-level counterpart of test_get_pressure_and_temperature_triggers_exactly_one_
    # measurement_cycle above: confirms _read_bmp() itself (not just the low-level method it now
    # calls) only triggers one physical conversion per read cycle, not the two independent ones
    # the old get_pressure()+get_temperature() two-call pattern used to produce.
    i2c, reader = make_clean_reader("single_measurement")
    seed_chip_id(i2c, _BMP388_CHIP_ID)
    seed_calibration(i2c)
    seed_status(i2c, 0x10 | 0x60)
    seed_err(i2c, 0x00)
    seed_data(i2c, _adc_to_data6(_ADC_P, _ADC_T))
    assert run(reader._init_bmp())
    fake(i2c).log.clear()  # only count triggers from the read itself, not setup()'s own traffic

    results = run(reader._read_bmp())

    assert results[0] is not None
    assert results[1] is not None
    assert _count_forced_mode_triggers(i2c) == 1


def test_reader_uses_fram_backed_print_log_when_fram_provided() -> None:
    # print_log.py's PrintLogHistoryStore path (FRAM-backed persistence, survives a reboot) is
    # never exercised by the default in-memory PrintLogHistory tests above - this drives it
    # through a real AsyFramManager against tests/_fram_chip_fake.py's simulated chip, the same
    # pattern tests/test_print_log.py uses directly.
    spi = SPI(0, sck_pin=2, mosi_pin=3, miso_pin=4)
    manager = AsyFramManager(spi, 1, max_size=0x2000)
    run(manager.setup())
    chip = manager.fram._spidev.spi._spi

    i2c = make_i2c()
    fake(i2c).nak_addresses.add(_ADDR)
    cfg_path = _tmp_cfg_path("fram_backed")
    reader = BMP3xx_Reader(i2c, address=_ADDR, cfg_path=cfg_path, fram=manager)
    assert isinstance(reader.pr, PrintLogHistoryStore)

    async def scenario() -> dict:
        # _init_bmp()'s real call order: self.pr.setup() always runs first ("required for all
        # logged warnings and errors", per its own comment) - PrintLogHistoryStore.setup() is a
        # no-op until initialized, so a logged error before setup() would never actually persist.
        await reader.pr.setup()
        await reader.get_pressure_oversampling()  # bus failure -> logs via self.pr (FRAM-backed)
        return await reader.get_error_counter()

    counters = run(scenario())
    assert counters["BMP3XX"]["ErrCount"] == 1

    # Simulate a reboot: a fresh SPI bus/manager/reader pair wired to the SAME underlying chip
    # memory (not the same SPI bus object - a real reboot re-constructs everything downstream of
    # the physical chip), replaying the same get_chunk() call sequence - genuinely round-trips
    # through the real dual-copy+CRC on-chip format, same as test_print_log.py's own
    # reboot-survival test.
    spi2 = SPI(0, sck_pin=2, mosi_pin=3, miso_pin=4)
    manager2 = AsyFramManager(spi2, 1, max_size=0x2000)
    manager2.fram._spidev.spi._spi = chip
    run(manager2.setup())
    rebooted_reader = BMP3xx_Reader(i2c, address=_ADDR, cfg_path=cfg_path, fram=manager2)

    async def reboot_scenario() -> dict:
        await rebooted_reader.pr.setup()  # loads persisted history from FRAM
        return await rebooted_reader.get_error_counter()

    rebooted_counters = run(reboot_scenario())
    assert rebooted_counters["BMP3XX"]["ErrCount"] == 1


# ---------------------------------------------------------------------------
# get_filter_coefficient()/_read_register() - deinitialized-bus fault path (asy_i2c_driver.py's
# "self._i2c is None" sentinel turned into a raised OSError), the read-side counterpart of
# test_bus_deinit_write_no_ops_silently_but_read_raises_oserror above.
# ---------------------------------------------------------------------------


def test_get_filter_coefficient_raises_oserror_on_deinitialized_bus() -> None:
    i2c, bmp = ready_bmp()
    i2c.deinit()
    try:
        run(bmp.get_filter_coefficient())
        raised = False
    except OSError as e:
        raised = "failed to read filter coefficient" in str(e)
    assert raised


def test_read_byte_raises_oserror_on_deinitialized_bus() -> None:
    i2c, bmp = make_bmp()
    i2c.deinit()
    try:
        run(bmp._read_byte(_REGISTER_CHIPID))
        raised = False
    except OSError as e:
        raised = "failed to read" in str(e)
    assert raised


# ---------------------------------------------------------------------------
# Reader.get_data() / get_dict_data() (SPECIFICATION.md Part C.4.2) - never exercised by any test
# above, unlike asy_scd30_driver.py's/asy_sgp40_driver.py's own test files.
# ---------------------------------------------------------------------------


def test_get_data_returns_all_none_before_any_successful_read() -> None:
    reader = make_reader("get_data_initial")
    assert run(reader.get_data()) == BMP3XX(None, None, None, None)


def test_get_data_and_get_dict_data_reflect_a_stored_reading() -> None:
    i2c, reader = make_clean_reader("get_data_stored")
    seed_chip_id(i2c, _BMP388_CHIP_ID)
    seed_calibration(i2c)
    seed_status(i2c, 0x10 | 0x60)
    seed_err(i2c, 0x00)
    seed_data(i2c, _adc_to_data6(_ADC_P, _ADC_T))
    assert run(reader._init_bmp())
    results = run(reader._read_bmp())
    run(reader._store_bmp(results))

    data = run(reader.get_data())
    assert data.Pres is not None
    assert data.Temp is not None
    assert data.SLPres is not None
    assert data.TS is not None

    as_dict = run(reader.get_dict_data())["BMP3XX"]
    assert as_dict["Pres"] == data.Pres
    assert as_dict["Temp"] == data.Temp
    assert as_dict["SLPres"] == data.SLPres
    assert as_dict["TS"] == data.TS


# ---------------------------------------------------------------------------
# Task/timer starters (SPECIFICATION.md Part C.9) - get_task_starters()/get_timer_starters()'s
# shape was never checked, and none of the starter methods they return were ever actually called,
# unlike asy_sgp40_driver.py's own test_start_asy_read_returns_a_real_task.
# ---------------------------------------------------------------------------


def test_get_task_starters_returns_read_and_trigger_starters() -> None:
    reader = make_reader("task_starters")
    assert reader.get_task_starters() == [reader.start_asy_read, reader.start_asy_trigger]


def test_get_cfg_schema_matches_the_full_schema() -> None:
    # get_cfg_schema() is inherited for free from base_classes.py's SensorReaderConfig - no
    # BMP3xx_Reader-specific code needed, unlike asy_wifi_service.py/asy_ntp_client.py, which used
    # to assign self.cfg_schema locally before this getter existed.
    reader = make_reader("cfg_schema")
    assert reader.get_cfg_schema() == _FULL_SCHEMA
    assert reader.get_cfg_schema() == reader.cfg_schema


def test_push_callbacks_registered_for_every_live_field_only() -> None:
    reader = make_reader("push_callbacks")
    assert set(reader._push_callbacks) == {"SampleInterv", "PressOvers", "TempOvers", "FiltCoeff"}
    # PressOffset/TempOffset/SeaLevelOffs/MeanAtmTemp are persist-only compensation-math inputs.


def test_set_dict_cfg_pressure_oversampling_end_to_end_persists_and_pushes() -> None:
    i2c, reader = make_clean_reader("set_dict_cfg_pov")
    seed_status(i2c, 0x10 | 0x60)
    seed_err(i2c, 0x00)
    results = run(reader._set_dict_cfg({"PressOvers": 8}, reader.get_cfg_schema()))
    assert results == {"PressOvers": "Valid"}
    assert run(reader.cfgmgr.get_dict(["PressOvers"])) == {"PressOvers": 8}  # persisted
    assert run(reader.bmp.get_pressure_oversampling()) == 8  # pushed live to the sensor


def test_set_dict_cfg_pressure_oversampling_bus_failure_reports_field_as_failed() -> None:
    # Persisted successfully (config write has no hardware dependency), but the live push fails -
    # per-field status reflects the push outcome, not the persist outcome, once persist succeeded.
    # base_classes.py's failed-push recovery chain then corrects the persisted value back to what
    # it was before this request. BMP3xx does register a _get_callbacks entry for this field, but a
    # blanket address NAK (unlike the write-only fault injected below) fails the getter's own read
    # too, so this specific test still falls through to the pre-write snapshot rung - established as
    # 4 first, distinct from both the requested 8 and the schema default (1), so the assertion below
    # can only pass via that specific rung.
    i2c, reader = make_clean_reader("set_dict_cfg_pov_busfail")
    seed_status(i2c, 0x10 | 0x60)
    seed_err(i2c, 0x00)
    run(reader._set_dict_cfg({"PressOvers": 4}, reader.get_cfg_schema()))

    fake(i2c).nak_addresses.add(_ADDR)
    results = run(reader._set_dict_cfg({"PressOvers": 8}, reader.get_cfg_schema()))
    assert results == {"PressOvers": "Failed"}
    assert run(reader.cfgmgr.get_dict(["PressOvers"])) == {"PressOvers": 4}  # corrected, not left at 8


def test_set_dict_cfg_pressure_oversampling_write_fails_but_getter_recovers_real_sensor_value() -> None:
    # A more realistic, narrower fault than the blanket NAK above: only the write half of
    # set_bits()'s read-modify-write fails (inject_fault on writeto_mem specifically), leaving reads
    # - and therefore the registered _get_callbacks getter - fully functional. Desyncs the sensor's
    # real register state (pushed directly via reader.bmp, bypassing _set_dict_cfg/cfgmgr entirely)
    # from cfgmgr's own persisted value (left at its schema default, 1), so a passing assertion can
    # only come from the getter rung actually being queried and winning - not from it coincidentally
    # agreeing with the pre-write snapshot the way the blanket-NAK test above can't help but do.
    i2c, reader = make_clean_reader("set_dict_cfg_pov_getter_recovers")
    seed_status(i2c, 0x10 | 0x60)
    seed_err(i2c, 0x00)
    run(reader.bmp.set_pressure_oversampling(2))
    assert run(reader.cfgmgr.get_dict(["PressOvers"])) == {"PressOvers": 1}  # untouched schema default

    fake(i2c).inject_fault("writeto_mem", OSError(errno_mod.EIO, "no ACK on write"))
    results = run(reader._set_dict_cfg({"PressOvers": 8}, reader.get_cfg_schema()))
    assert results == {"PressOvers": "Failed"}
    # Recovered via the live getter (2, the sensor's real state) - neither the requested-but-failed
    # 8 nor cfgmgr's own pre-write snapshot (1).
    assert run(reader.cfgmgr.get_dict(["PressOvers"])) == {"PressOvers": 2}
    assert run(reader.bmp.get_pressure_oversampling()) == 2  # sensor register itself untouched


def test_set_dict_cfg_multi_field_discrete_and_continuous_together() -> None:
    i2c, reader = make_clean_reader("set_dict_cfg_multi")
    seed_status(i2c, 0x10 | 0x60)
    seed_err(i2c, 0x00)
    results = run(
        reader._set_dict_cfg(
            {"PressOvers": 20, "FiltCoeff": 15, "PressOffset": 12.5}, reader.get_cfg_schema()
        )
    )
    assert results == {"PressOvers": "Invalid", "FiltCoeff": "Valid", "PressOffset": "Valid"}
    assert run(reader.bmp.get_filter_coefficient()) == 15
    assert run(reader.cfgmgr.get_dict(["PressOffset"])) == {"PressOffset": 12.5}


def test_set_dict_cfg_multiple_simultaneously_invalid_discrete_fields_neither_pushed() -> None:
    # Both PressOvers and FiltCoeff invalid at once - not just one invalid amid otherwise-valid
    # fields, as test_set_dict_cfg_multi_field_discrete_and_continuous_together above already
    # covers. Confirms independence holds and neither push callback fires when two discrete-set
    # fields in the same request are both out of their allowed value set, while a third, valid
    # field in the same call still persists and pushes normally.
    i2c, reader = make_clean_reader("set_dict_cfg_multi_invalid")
    seed_status(i2c, 0x10 | 0x60)
    seed_err(i2c, 0x00)
    results = run(reader._set_dict_cfg({"PressOvers": 20, "FiltCoeff": 99, "TempOvers": 4}, reader.get_cfg_schema()))
    assert results == {"PressOvers": "Invalid", "FiltCoeff": "Invalid", "TempOvers": "Valid"}
    assert run(reader.cfgmgr.get_dict(["PressOvers", "FiltCoeff"])) == {
        "PressOvers": 1,
        "FiltCoeff": 0,
    }  # both untouched, still their schema defaults
    assert run(reader.bmp.get_temperature_oversampling()) == 4  # the one valid field still pushed


def test_set_dict_cfg_temperature_oversampling_end_to_end_persists_and_pushes() -> None:
    i2c, reader = make_clean_reader("set_dict_cfg_tov")
    seed_status(i2c, 0x10 | 0x60)
    seed_err(i2c, 0x00)
    results = run(reader._set_dict_cfg({"TempOvers": 4}, reader.get_cfg_schema()))
    assert results == {"TempOvers": "Valid"}
    assert run(reader.cfgmgr.get_dict(["TempOvers"])) == {"TempOvers": 4}
    assert run(reader.bmp.get_temperature_oversampling()) == 4


def test_set_dict_cfg_sample_interv_end_to_end_persists_and_pushes() -> None:
    # SampleInterv's "push" is a pure in-memory software knob (trigger_period), not I2C - no bus
    # seeding needed.
    reader = make_reader("set_dict_cfg_si")
    results = run(reader._set_dict_cfg({"SampleInterv": 45}, reader.get_cfg_schema()))
    assert results == {"SampleInterv": "Valid"}
    assert run(reader.cfgmgr.get_dict(["SampleInterv"])) == {"SampleInterv": 45}
    assert run(reader.trigger_period.get_value()) == 45


def test_push_wrapper_functions_reject_a_non_int_value_defensively() -> None:
    # _set_dict_cfg only ever invokes these with an already schema-validated int (see each
    # wrapper's own comment) - calling them directly with the wrong type exercises the defensive
    # branch a real caller can't actually reach.
    reader = make_reader("push_wrapper_reject")
    for wrapper_name in ("_push_trigger_secs", "_push_pressure_oversampling", "_push_temperature_oversampling", "_push_filter_coefficient"):
        wrapper = getattr(reader, wrapper_name)
        assert run(wrapper("not an int")) is False
        assert run(wrapper(1.5)) is False
        assert run(wrapper(True)) is False  # bool is not int for this purpose, matching config_manager.py


def test_get_timer_starters_returns_the_trigger_timer_starter() -> None:
    reader = make_reader("timer_starters")
    assert reader.get_timer_starters() == [reader.start_timer]


def test_start_asy_read_returns_a_real_task() -> None:
    reader = make_reader("start_read")

    async def scenario() -> bool:
        task = reader.start_asy_read()
        await asyncio.sleep(0)
        is_task = isinstance(task, asyncio.Task)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        return is_task

    assert run(scenario()) is True


def test_start_asy_trigger_returns_a_real_task() -> None:
    reader = make_reader("start_trigger")

    async def scenario() -> bool:
        task = reader.start_asy_trigger()
        await asyncio.sleep(0)
        is_task = isinstance(task, asyncio.Task)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        return is_task

    assert run(scenario()) is True


def test_start_timer_arms_a_real_periodic_timer_that_drives_base_trigger_event() -> None:
    FakeTimer.all_timers.clear()
    reader = make_reader("start_timer")
    reader.start_timer()
    assert reader.trigger_timer.mode == FakeTimer.PERIODIC
    assert reader.trigger_timer.period == 1000

    reader.trigger_timer.trigger()

    async def scenario() -> bool:
        fired = True
        try:
            await asyncio.wait_for(reader.base_trigger_event.wait(), 1)
        except asyncio.TimeoutError:
            fired = False
        return fired

    assert run(scenario()) is True
    FakeTimer.all_timers.clear()


def test_start_timer_degrades_gracefully_when_the_trigger_timer_cannot_be_armed() -> None:
    # Real rp2 Timer.init() raises OSError(ENOMEM) when the alarm pool is exhausted (confirmed
    # against ports/rp2/machine_timer.c) - start_timer() must log via self.pr.err() and return
    # normally, since its caller is system_service.py's synchronous start_timers() sequencer:
    # raising here would take down the whole timer-start chain over one sensor that simply never
    # gets triggered this cycle.
    FakeTimer.all_timers.clear()
    reader = make_reader("start_timer_oserror")
    with _RaiseOnArm():
        reader.start_timer()  # must not raise despite the timer failing to arm
    assert reader.trigger_timer.period == -1  # never actually armed
    assert reader.trigger_timer.callback is None  # nothing wired to base_trigger_event either
    # start_timer() is synchronous, so it logs via the plain, non-counting pr.err() rather than
    # awaiting pr.err_s() - this failure prints but is deliberately never recorded as a numbered
    # error in the counter, unlike every err_s() call site in this driver.
    assert run(reader.get_error_counter())["BMP3XX"]["ErrCount"] == 0
    FakeTimer.all_timers.clear()


def test_start_timer_degrades_gracefully_on_a_memory_error_while_arming() -> None:
    # MemoryError is not an OSError subclass (see SPECIFICATION.md Part F), so start_timer()'s
    # `except (OSError, MemoryError)` needs that second arm spelled out explicitly - without it, a
    # heap-exhausted arming attempt would propagate straight out of this synchronous starter
    # instead of degrading the same way the ENOMEM case above does.
    FakeTimer.all_timers.clear()
    reader = make_reader("start_timer_memoryerror")
    with _RaiseOnArm(MemoryError):
        reader.start_timer()  # must not raise despite the timer failing to arm
    assert reader.trigger_timer.period == -1  # never actually armed
    assert reader.trigger_timer.callback is None
    FakeTimer.all_timers.clear()


def test_stop_timer_deinits_the_trigger_timer() -> None:
    FakeTimer.all_timers.clear()
    reader = make_reader("stop_timer")
    reader.start_timer()
    reader.stop_timer()
    assert reader.trigger_timer.deinit_called is True
    FakeTimer.all_timers.clear()


# ---------------------------------------------------------------------------
# _base_trigger() - the 1Hz base tick divided down by trigger_period into the "real" trigger_event
# (SPECIFICATION.md Part C.9's "second small _base_trigger() task" pattern).
# ---------------------------------------------------------------------------


def test_base_trigger_sets_trigger_event_only_once_the_configured_period_elapses() -> None:
    reader = make_reader("base_trigger")
    run(reader.set_trigger_secs(3))

    async def scenario() -> "tuple[int, int, bool]":
        task = asyncio.create_task(reader._base_trigger())
        await _settle(3)  # let _base_trigger() reach its first wait()
        reader.base_trigger_event.set()
        await _settle(3)
        counter_after_1 = reader.trigger_counter
        reader.base_trigger_event.set()
        await _settle(3)
        counter_after_2 = reader.trigger_counter
        reader.base_trigger_event.set()
        await _settle(3)
        fired = True
        try:
            await asyncio.wait_for(reader.trigger_event.wait(), 1)
        except asyncio.TimeoutError:
            fired = False
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        return counter_after_1, counter_after_2, fired

    counter_after_1, counter_after_2, fired = run(scenario())
    assert counter_after_1 == 1
    assert counter_after_2 == 2
    assert fired is True
    assert reader.trigger_counter == 0  # reset back to 0 once the period fires


# ---------------------------------------------------------------------------
# Reader-level set_temperature_oversampling()/set_filter_coefficient() - only their protocol-layer
# counterparts and set_pressure_oversampling()'s own Reader wrapper were exercised above; these two
# forwards share the same success/log-and-return-False shape (SPECIFICATION.md Part C.7).
# ---------------------------------------------------------------------------


def test_reader_set_temperature_oversampling_applies_the_value_and_returns_true() -> None:
    i2c, reader = make_clean_reader("set_tov_ok")
    assert run(reader.set_temperature_oversampling(8)) is True
    assert run(reader.bmp.get_temperature_oversampling()) == 8


def test_reader_set_temperature_oversampling_logs_and_returns_false_on_bus_failure() -> None:
    reader = make_reader("set_tov_fail")

    async def scenario() -> "tuple[bool, dict]":
        ok = await reader.set_temperature_oversampling(4)
        await reader.pr.setup()
        counters = await reader.get_error_counter()
        return ok, counters

    ok, counters = run(scenario())
    assert ok is False
    assert counters["BMP3XX"]["ErrNum"][-1] == 18


def test_reader_set_filter_coefficient_applies_the_value_and_returns_true() -> None:
    i2c, reader = make_clean_reader("set_fc_ok")
    assert run(reader.set_filter_coefficient(15)) is True
    assert run(reader.bmp.get_filter_coefficient()) == 15


def test_reader_set_filter_coefficient_logs_and_returns_false_on_bus_failure() -> None:
    reader = make_reader("set_fc_fail")

    async def scenario() -> "tuple[bool, dict]":
        ok = await reader.set_filter_coefficient(31)
        await reader.pr.setup()
        counters = await reader.get_error_counter()
        return ok, counters

    ok, counters = run(scenario())
    assert ok is False
    assert counters["BMP3XX"]["ErrNum"][-1] == 20


# ---------------------------------------------------------------------------
# read_loop() - end-to-end wiring, driven via real trigger events and cancellation (matches
# asy_scd30_driver.py's/asy_sgp40_driver.py's own read_loop() test convention).
# ---------------------------------------------------------------------------


def test_read_loop_stores_a_result_after_one_trigger() -> None:
    i2c, reader = make_clean_reader("read_loop_happy")
    seed_chip_id(i2c, _BMP388_CHIP_ID)
    seed_calibration(i2c)
    seed_status(i2c, 0x10 | 0x60)
    seed_err(i2c, 0x00)
    seed_data(i2c, _adc_to_data6(_ADC_P, _ADC_T))

    async def scenario() -> BMP3XX:
        task = asyncio.create_task(reader.read_loop())
        await _settle(10)  # let _init_bmp() (real, but small: 2ms) settle-sleeps complete
        reader.trigger_event.set()
        await _settle(10)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        return await reader.get_data()

    with _FastAsyncSleep():
        data = run(scenario())
    assert data.Pres is not None
    assert data.Temp is not None
    assert data.TS is not None


def test_read_loop_gives_up_and_returns_false_after_max_errors() -> None:
    i2c, reader = make_clean_reader("read_loop_giveup", max_module_error=2)
    seed_chip_id(i2c, _BMP388_CHIP_ID)
    seed_calibration(i2c)
    seed_status(i2c, 0x10 | 0x60)
    seed_err(i2c, 0x00)
    seed_data(i2c, _adc_to_data6(_ADC_P, _ADC_T))

    async def scenario() -> bool:
        task = asyncio.create_task(reader.read_loop())
        await _settle(10)
        fake(i2c).nak_addresses.add(_ADDR)  # every read from here on fails
        for _ in range(4):  # max_module_error=2 -> the 3rd consecutive failure crosses the threshold
            reader.trigger_event.set()
            await _settle(10)
            if task.done():
                return await task
        raise AssertionError("read_loop never gave up")

    with _FastAsyncSleep():
        assert run(scenario()) is False


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
