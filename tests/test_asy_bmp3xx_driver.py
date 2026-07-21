import asyncio
import errno as errno_mod
import os
import struct

from machine import I2C as FakeI2C

from asy_bmp3xx_driver import BMP3XX_I2C, BMP3xx_Reader
from asy_i2c_driver import I2C

# Mirrors of asy_bmp3xx_driver.py's own underscore-prefixed micropython.const() values - these
# are compiled away entirely (confirmed: MicroPython folds a const() name into every use site at
# compile time, so it isn't a real importable module attribute - see tests/README.md's "Reading
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
_IIR_SETTINGS = (0, 2, 4, 8, 16, 32, 64, 128)

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
    i2c, bmp = ready_bmp()
    try:
        run(bmp.set_filter_coefficient(1))
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
    return BMP3xx_Reader(i2c, address=_ADDR, cfg_path=_tmp_cfg_path(name))


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


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
