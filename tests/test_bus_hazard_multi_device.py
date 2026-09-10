"""Mock-level (tests/machine.py fake I2C) bus-hazard/concurrency regression suite - the fast,
deterministic tier of SPECIFICATION.md Part C.8's bus-hazard coverage. See Part C.8 for the
standing rule on extending this file when a new I2C-facing driver is added."""

import asyncio
import struct

from _fram_chip_fake import FakeMB85RS64V
from machine import I2C as FakeI2C

import asy_spi_driver
from asy_bmp3xx_driver import BMP3XX_I2C
from asy_fram_driver import FRAM_SPI
from asy_i2c_driver import I2C
from asy_scd30_driver import SCD30_I2C
from asy_sgp40_driver import SGP40_I2C
from asy_spi_driver import SPI as AsySPI
from print_log import PrintLogHistory

# Same one-process-per-test-file swap test_asy_fram_driver.py's own header comment explains -
# asy_spi_driver.SPI.init() resolves `_SPI` as a plain module global at call time, so this is safe
# to do once here alongside this file's own I2C imports above, independent of them (a different bus
# type entirely).
asy_spi_driver._SPI = FakeMB85RS64V  # type: ignore[misc]

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Coroutine
    from typing import Any, TypeVar

    from typing_extensions import Self

    T = TypeVar("T")


def run(coro: "Coroutine[Any, Any, T]") -> "T":
    return asyncio.run(coro)


async def _gather(a: "Coroutine[Any, Any, Any]", b: "Coroutine[Any, Any, Any]") -> None:
    # asyncio.gather() itself returns a Future, not a Coroutine - mypy rejects passing it straight
    # to run() (which declares a Coroutine[...] parameter), same as test_asy_i2c_driver.py's own
    # scenario()-wrapping convention for this exact call shape.
    await asyncio.gather(a, b)


class _FastAsyncSleep:
    # Same technique as test_asy_scd30_driver.py's/test_asy_sgp40_driver.py's own _FastAsyncSleep -
    # asyncio.sleep is a shared, process-wide function, restored on exit regardless of how the
    # `with` block exits.
    def __enter__(self) -> "Self":
        self._real_sleep = asyncio.sleep

        async def _fast(_seconds: float) -> None:
            await self._real_sleep(0)

        asyncio.sleep = _fast  # type: ignore[assignment]
        return self

    def __exit__(self, *exc_info: object) -> None:
        asyncio.sleep = self._real_sleep


# ---------------------------------------------------------------------------
# Shared fixtures/helpers
# ---------------------------------------------------------------------------

_SCD_ADDR = 0x61
_BMP_ADDR = 0x77
_SGP_ADDR = 0x59
_GENERAL_CALL_ADDR = 0x00
# I2C spec reserved address ranges (0x00-0x07: general call/CBUS/reserved/Hs-mode; 0x78-0x7F:
# 10-bit addressing/reserved) - every real device address this codebase uses must fall outside
# both, and only SGP40's own documented _reset() may ever address 0x00 specifically.
_RESERVED_RANGES = ((0x00, 0x07), (0x78, 0x7F))


def _is_reserved(address: int) -> bool:
    return any(lo <= address <= hi for lo, hi in _RESERVED_RANGES)


def make_i2c(port_id: int = 1) -> I2C:
    return I2C(port_id, scl_pin=19, sda_pin=18, frequency=50000)


def fake(i2c: I2C) -> FakeI2C:
    return i2c._i2c  # type: ignore[return-value]


def _crc8(data: bytes) -> int:
    crc = 0xFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = ((crc << 1) ^ 0x31) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF
    return crc


def _sgp_word(value: int) -> bytes:
    payload = bytes([(value >> 8) & 0xFF, value & 0xFF])
    return payload + bytes([_crc8(payload)])


def _scd_register_frame(value: int) -> bytes:
    payload = struct.pack(">H", value)
    return payload + bytes([_crc8(payload)])


def _scd_data_frame(co2: float, temperature: float, humidity: float) -> bytes:
    frame = bytearray()
    for value in (co2, temperature, humidity):
        raw = struct.pack(">f", value)
        msw, lsw = raw[0:2], raw[2:4]
        frame += msw + bytes([_crc8(msw)]) + lsw + bytes([_crc8(lsw)])
    return bytes(frame)


def queue_sgp_successful_init(fake_bus: FakeI2C) -> None:
    fake_bus.read_queue.append(_sgp_word(0x0000) + _sgp_word(0x1234) + _sgp_word(0x5678))
    fake_bus.read_queue.append(_sgp_word(0xD400))


# BMP3xx: a fixed, reproducible calibration/ADC dataset (same one test_asy_bmp3xx_driver.py's own
# _CAL_RAW/_ADC_P/_ADC_T/_EXPECTED_* use) - not re-deriving the expected values independently here
# since correctness of the compensation math is already covered there; this file only needs a
# *deterministic, known-good* reading to detect corruption, not to re-verify the formula.
_BMP_CAL_RAW = struct.pack(
    "<HHbhhbbHHbbhbb",
    28617, 26074, -10, -3944, -10416, 26, 0, 30462, 120, 4, 0, 4285, 22, -60,
)
_BMP_ADC_P = 8300000
_BMP_ADC_T = 8500000
_BMP_EXPECTED_TEMPERATURE = 28.460795242070162
_BMP_EXPECTED_PRESSURE_HPA = 713.765147356092


def _bmp_data6(adc_p: int, adc_t: int) -> bytes:
    def triplet(v: int) -> bytes:
        return bytes([v & 0xFF, (v >> 8) & 0xFF, (v >> 16) & 0xFF])

    return triplet(adc_p) + triplet(adc_t)


def seed_bmp_ready(i2c: I2C, address: int = _BMP_ADDR) -> None:
    # STATUS: cmd_rdy | drdy_press | drdy_temp: ERR_REG clear - see test_asy_bmp3xx_driver.py's
    # own ready_bmp() for the same shape.
    fake(i2c).registers[(address, 0x03)] = bytearray([0x10 | 0x60])  # _REGISTER_STATUS
    fake(i2c).registers[(address, 0x02)] = bytearray([0x00])  # _REGISTER_ERR
    fake(i2c).registers[(address, 0x00)] = bytearray([0x50])  # _REGISTER_CHIPID (BMP388)
    fake(i2c).registers[(address, 0x31)] = bytearray(_BMP_CAL_RAW)  # _REGISTER_CAL_DATA
    fake(i2c).registers[(address, 0x04)] = bytearray(_bmp_data6(_BMP_ADC_P, _BMP_ADC_T))  # _REGISTER_PRESSUREDATA


async def _settle(n: int = 8) -> None:
    for _ in range(n):
        await asyncio.sleep(0)


# ---------------------------------------------------------------------------
# 1. Same-device concurrency: a read must never interleave, at the wire-byte level, with a
#    concurrent write to the SAME device.
# ---------------------------------------------------------------------------


_CMD_GET_DATA_READY = b"\x02\x02"
_CMD_READ_MEASUREMENT = b"\x03\x00"
_CMD_SET_TEMPERATURE_OFFSET = b"\x54\x03"


def _parse_scd30_log(log: list, read_iterations: int) -> None:
    # Command-byte-based proof that same-device ops never interleave on the wire: parses the log
    # into non-overlapping runs and fails outright on any stray/out-of-place entry. A simpler
    # before/after log-length "span" check was tried and rejected - a coroutine legitimately
    # blocked on the lock naturally overlaps the holder's span, which is correct serialization.
    reads_parsed = 0
    writes_parsed = 0
    i = 0
    while i < len(log):
        entry = log[i]
        if entry[0] == "writeto" and bytes(entry[2][:2]) == _CMD_GET_DATA_READY:
            assert i + 3 < len(log), f"truncated read_measurement() sequence at log index {i}: {log[i:]}"
            assert log[i + 1][0] == "readfrom_into", f"expected readfrom_into at index {i + 1}, got {log[i + 1]}"
            assert log[i + 2][0] == "writeto" and bytes(log[i + 2][2][:2]) == _CMD_READ_MEASUREMENT, f"expected writeto(READ_MEASUREMENT) at index {i + 2}, got {log[i + 2]}"
            assert log[i + 3][0] == "readfrom_into", f"expected readfrom_into at index {i + 3}, got {log[i + 3]}"
            reads_parsed += 1
            i += 4
        elif entry[0] == "writeto" and bytes(entry[2][:2]) == _CMD_SET_TEMPERATURE_OFFSET:
            writes_parsed += 1
            i += 1
        else:
            raise AssertionError(f"unexpected/misplaced log entry at index {i} (interleaving corruption): {entry}")
    assert reads_parsed == read_iterations, f"parsed {reads_parsed} read cycles, expected {read_iterations}"
    assert writes_parsed == 1, f"parsed {writes_parsed} write(s), expected exactly 1"


def test_same_device_scd30_concurrent_read_and_write_never_interleave_on_the_wire() -> None:
    i2c = make_i2c(0)
    scd = SCD30_I2C(i2c)
    fake_bus = fake(i2c)
    read_iterations = 6

    for _ in range(read_iterations):
        fake_bus.read_queue.append(_scd_register_frame(1))  # data-ready
        fake_bus.read_queue.append(_scd_data_frame(412.5, 23.4, 45.6))

    reads_completed = 0
    write_completed = False

    async def reader() -> None:
        nonlocal reads_completed
        for _ in range(read_iterations):
            await scd.read_measurement()
            reads_completed += 1

    async def writer() -> None:
        nonlocal write_completed
        await asyncio.sleep(0)  # let the reader get partway into its first cycle first
        await scd.set_temperature_offset(12.34)
        write_completed = True

    with _FastAsyncSleep():
        run(_gather(reader(), writer()))

    assert reads_completed == read_iterations
    assert write_completed
    _parse_scd30_log(fake_bus.log, read_iterations)


# ---------------------------------------------------------------------------
# 2. Cross-device concurrency: two DIFFERENT devices sharing one bus (BMP3xx + SGP40 on i2c1,
#    matching wozi's wiring) must genuinely interleave, not fully serialize, and both must stay correct.
# ---------------------------------------------------------------------------


def test_cross_device_bmp3xx_and_sgp40_interleave_and_both_stay_correct() -> None:
    i2c = make_i2c(1)  # matches wozi's real i2c1 port id
    bmp = BMP3XX_I2C(i2c, address=_BMP_ADDR)
    sgp = SGP40_I2C(i2c, address=_SGP_ADDR)
    fake_bus = fake(i2c)
    seed_bmp_ready(i2c)
    run(bmp.setup())  # populates _temp_calib/_pressure_calib from the seeded CAL_DATA - required before any real _read()

    bmp_iterations = 6
    sgp_iterations = 4
    for _ in range(sgp_iterations):
        fake_bus.read_queue.append(_sgp_word(0x8000))  # a fixed, known-good raw measurement word

    bmp_results: list[tuple[float, float]] = []
    sgp_results: list[int | None] = []

    async def bmp_loop() -> None:
        for _ in range(bmp_iterations):
            pressure, temperature = await bmp.get_pressure_and_temperature()
            bmp_results.append((pressure, temperature))
            await asyncio.sleep(0)

    async def sgp_loop() -> None:
        for _ in range(sgp_iterations):
            raw = await sgp.measure_raw(temperature=25, relative_humidity=50)
            sgp_results.append(raw)
            await asyncio.sleep(0)

    with _FastAsyncSleep():
        run(_gather(bmp_loop(), sgp_loop()))

    assert len(bmp_results) == bmp_iterations
    assert len(sgp_results) == sgp_iterations
    for pressure, temperature in bmp_results:
        assert abs(pressure - _BMP_EXPECTED_PRESSURE_HPA) < 1e-6
        assert abs(temperature - _BMP_EXPECTED_TEMPERATURE) < 1e-6
    assert all(raw == 0x8000 for raw in sgp_results)

    # Genuine interleaving proof: addressed log entries must not form two separate contiguous
    # blocks (one fully before the other). Both op families (BMP3xx's readfrom_mem/writeto_mem,
    # SGP40's writeto/readfrom_into) must be counted or BMP3xx's entries silently drop out.
    addressed = [entry[1] for entry in fake_bus.log if entry[0] in ("writeto", "readfrom_into", "readfrom_mem", "writeto_mem")]
    # Plain index-based comparison, not zip(strict=...): MicroPython's builtin zip() doesn't accept
    # keyword arguments (confirmed against the pinned Unix-port interpreter).
    switches = sum(1 for i in range(len(addressed) - 1) if addressed[i] != addressed[i + 1])
    assert switches >= 2, f"only {switches} address switch(es) across the whole run - looks fully serialized, not interleaved: {addressed}"


# ---------------------------------------------------------------------------
# 3. General-call broadcast hazard: SGP40's _reset() (true I2C general call) landing concurrently
#    with BMP3xx's own multi-step read must not corrupt or interrupt it.
# ---------------------------------------------------------------------------


def test_sgp40_general_call_reset_does_not_disturb_a_concurrent_bmp3xx_read() -> None:
    i2c = make_i2c(1)
    bmp = BMP3XX_I2C(i2c, address=_BMP_ADDR)
    sgp = SGP40_I2C(i2c, address=_SGP_ADDR)
    fake_bus = fake(i2c)
    seed_bmp_ready(i2c)
    run(bmp.setup())  # populates _temp_calib/_pressure_calib from the seeded CAL_DATA - required before any real _read()

    bmp_iterations = 5
    reset_count = 3
    bmp_results: list[tuple[float, float]] = []

    async def bmp_loop() -> None:
        for _ in range(bmp_iterations):
            bmp_results.append(await bmp.get_pressure_and_temperature())
            await asyncio.sleep(0)

    async def reset_loop() -> None:
        for _ in range(reset_count):
            await sgp._reset()
            await asyncio.sleep(0)

    with _FastAsyncSleep():
        run(_gather(bmp_loop(), reset_loop()))

    assert len(bmp_results) == bmp_iterations
    for pressure, temperature in bmp_results:
        assert abs(pressure - _BMP_EXPECTED_PRESSURE_HPA) < 1e-6
        assert abs(temperature - _BMP_EXPECTED_TEMPERATURE) < 1e-6

    general_calls = [entry for entry in fake_bus.log if entry[0] == "writeto" and entry[1] == _GENERAL_CALL_ADDR]
    assert len(general_calls) == reset_count
    assert all(entry[2] == b"\x06" for entry in general_calls)
    # And BMP3xx's own address must never appear mixed into a general-call entry - the broadcast
    # is its own, separate log entry, not something that silently merged into BMP3xx's own bus ops.
    assert all(entry[1] != _BMP_ADDR for entry in general_calls)


def test_general_call_absent_sibling_bmp3xx_alone_on_the_bus_survives_a_broadcast_too() -> None:
    # BMP3xx is the only device on this bus (matching dev's real i2c0 wiring); the broadcast is
    # issued directly against the raw I2C wrapper (no SGP40_I2C instance) to prove BMP3xx alone
    # tolerates a general call regardless of who issues it.
    i2c = make_i2c(0)  # matches dev's real i2c0 port id
    bmp = BMP3XX_I2C(i2c, address=_BMP_ADDR)
    fake_bus = fake(i2c)
    seed_bmp_ready(i2c)
    run(bmp.setup())  # populates _temp_calib/_pressure_calib from the seeded CAL_DATA - required before any real _read()
    fake_bus.nak_addresses.add(_GENERAL_CALL_ADDR)  # BMP3xx doesn't ack general calls (datasheet-confirmed)

    bmp_results: list[tuple[float, float]] = []

    async def bmp_loop() -> None:
        for _ in range(5):
            bmp_results.append(await bmp.get_pressure_and_temperature())
            await asyncio.sleep(0)

    async def rogue_broadcast_loop() -> None:
        for _ in range(3):
            try:
                i2c.writeto(_GENERAL_CALL_ADDR, b"\x06")
            except OSError:
                pass  # expected - nothing acks it, same as SGP40_I2C._reset()'s own tolerance
            await asyncio.sleep(0)

    with _FastAsyncSleep():
        run(_gather(bmp_loop(), rogue_broadcast_loop()))

    assert len(bmp_results) == 5
    for pressure, temperature in bmp_results:
        assert abs(pressure - _BMP_EXPECTED_PRESSURE_HPA) < 1e-6
        assert abs(temperature - _BMP_EXPECTED_TEMPERATURE) < 1e-6


# ---------------------------------------------------------------------------
# 4. Address/command sweep: every promoted I2C driver's public API must never touch any address
#    other than its own configured one, except SGP40's documented general call (0x00) from _reset().
# ---------------------------------------------------------------------------


def _touched_addresses(fake_bus: FakeI2C) -> set:
    return {entry[1] for entry in fake_bus.log if entry[0] in ("writeto", "readfrom_into", "readfrom_mem", "writeto_mem")}


def test_scd30_never_touches_any_address_but_its_own() -> None:
    i2c = make_i2c(0)
    scd = SCD30_I2C(i2c)
    fake_bus = fake(i2c)
    for _ in range(40):  # generous - some methods issue more than one read
        fake_bus.read_queue.append(_scd_register_frame(1))
        fake_bus.read_queue.append(_scd_data_frame(400.0, 20.0, 50.0))

    async def exercise() -> None:
        for call in (
            scd.setup,
            scd.reset,
            scd.get_measurement_interval,
            scd.get_self_calibration_enabled,
            scd.get_ambient_pressure,
            scd.get_altitude,
            scd.get_temperature_offset,
            scd.get_forced_recalibration_reference,
            scd.get_config_snapshot,
            scd.read_measurement,
            scd.stop_continuous_measurement,
            lambda: scd.set_measurement_interval(5),
            lambda: scd.set_self_calibration_enabled(True),
            lambda: scd.set_ambient_pressure(1013),
            lambda: scd.set_altitude(100),
            lambda: scd.set_temperature_offset(1.0),
            lambda: scd.set_forced_recalibration_reference(500),
        ):
            try:
                await call()
            except Exception:
                pass

    with _FastAsyncSleep():
        run(exercise())

    touched = _touched_addresses(fake_bus)
    assert touched == {_SCD_ADDR}, f"SCD30_I2C touched unexpected address(es): {touched - {_SCD_ADDR}}"
    assert not _is_reserved(_SCD_ADDR)


def test_bmp3xx_never_touches_any_address_but_its_own() -> None:
    i2c = make_i2c(0)
    bmp = BMP3XX_I2C(i2c, address=_BMP_ADDR)
    fake_bus = fake(i2c)
    seed_bmp_ready(i2c)

    async def exercise() -> None:
        for call in (
            bmp.setup,
            bmp.reset,
            bmp.get_pressure,
            bmp.get_temperature,
            bmp.get_pressure_and_temperature,
            bmp.get_altitude,
            bmp.get_pressure_oversampling,
            bmp.get_temperature_oversampling,
            bmp.get_filter_coefficient,
            bmp.get_config_snapshot,
            lambda: bmp.set_pressure_oversampling(2),
            lambda: bmp.set_temperature_oversampling(2),
            lambda: bmp.set_filter_coefficient(3),
        ):
            try:
                await call()
            except Exception:
                pass

    with _FastAsyncSleep():
        run(exercise())

    touched = _touched_addresses(fake_bus)
    assert touched == {_BMP_ADDR}, f"BMP3XX_I2C touched unexpected address(es): {touched - {_BMP_ADDR}}"
    assert not _is_reserved(_BMP_ADDR)


def test_sgp40_touches_only_its_own_address_except_reset_which_touches_only_the_general_call_address() -> None:
    i2c = make_i2c(1)
    sgp = SGP40_I2C(i2c, address=_SGP_ADDR)
    fake_bus = fake(i2c)
    for _ in range(10):
        fake_bus.read_queue.append(_sgp_word(0x8000))
    queue_sgp_successful_init(fake_bus)

    async def exercise_non_reset() -> None:
        for call in (
            sgp.setup,  # includes one initialize() -> _reset() call - excluded from this half's assertion below
            sgp.get_raw,
            lambda: sgp.measure_raw(25, 50),
            lambda: sgp.measure_index_and_raw(25, 50),
        ):
            try:
                await call()
            except Exception:
                pass

    with _FastAsyncSleep():
        run(exercise_non_reset())

    touched = _touched_addresses(fake_bus)
    # setup() calls initialize() -> _reset(), so 0x00 is expected here too; this sweep's job is
    # only to confirm no *third*, unexpected address shows up beyond {own address, general call}.
    assert touched <= {_SGP_ADDR, _GENERAL_CALL_ADDR}, f"SGP40_I2C touched unexpected address(es): {touched - {_SGP_ADDR, _GENERAL_CALL_ADDR}}"
    assert not _is_reserved(_SGP_ADDR)


def test_no_reserved_i2c_address_collides_with_any_promoted_devices_own_address() -> None:
    # Regression guard for future device additions (SPECIFICATION.md Part C.8): a new driver whose
    # default address falls in a reserved I2C range is caught here before reaching real hardware.
    for name, address in (("SCD30", _SCD_ADDR), ("BMP3xx", _BMP_ADDR), ("SGP40", _SGP_ADDR)):
        assert not _is_reserved(address), f"{name}'s own address {address:#x} falls inside a reserved I2C range"


# ---------------------------------------------------------------------------
# 5. FRAM (SPI) - no I2C address concept and no bus-sharing (sections 2/3 don't apply), so
#    same-device concurrency is its whole applicable slice of this file's standing rule. Proven by
#    outcome (final memory state) rather than wire-log parsing, since FakeMB85RS64V overrides the
#    base fake's methods and doesn't feed the shared SPI.log.
# ---------------------------------------------------------------------------


def make_fram_bus() -> AsySPI:
    return AsySPI(0, sck_pin=2, mosi_pin=3, miso_pin=4)


def make_fram(max_size: int = 0x2000) -> "tuple[FRAM_SPI, FakeMB85RS64V]":
    bus = make_fram_bus()
    fram = FRAM_SPI(bus, 1, logger=PrintLogHistory(name="TESTFRAM"), max_size=max_size)
    chip = fram._spidev.spi._spi
    assert isinstance(chip, FakeMB85RS64V)
    return fram, chip


_FRAM_READ_REGION = (0x0000, 16)  # (start_address, length) - never touched by the writer below
_FRAM_WRITE_REGION = (0x1000, 16)  # disjoint from the read region, well within the 0x2000 chip's range
_FRAM_SEED_PATTERN = bytes(range(16))  # 0x00..0x0F - fixed, known, easy to spot corruption in
_FRAM_WRITE_PATTERN = bytes(range(0xF0, 0x100))  # 0xF0..0xFF - deliberately distinct from the seed


def test_fram_same_device_concurrent_read_and_write_never_corrupt_each_other() -> None:
    fram, chip = make_fram()
    run(setup_fram_test(fram))
    chip.memory[_FRAM_READ_REGION[0] : _FRAM_READ_REGION[0] + _FRAM_READ_REGION[1]] = _FRAM_SEED_PATTERN

    read_iterations = 20
    reads_completed = 0
    write_completed = False
    read_mismatches: list[str] = []

    async def reader() -> None:
        nonlocal reads_completed
        buf = bytearray(_FRAM_READ_REGION[1])
        for i in range(read_iterations):
            ok = await fram.get_values(buf, addr_start=_FRAM_READ_REGION[0])
            if not ok or bytes(buf) != _FRAM_SEED_PATTERN:
                read_mismatches.append(f"iter {i}: ok={ok} got={bytes(buf).hex()} expected={_FRAM_SEED_PATTERN.hex()}")
            reads_completed += 1

    async def writer() -> None:
        nonlocal write_completed
        await asyncio.sleep(0)  # let the reader get partway into its run first, matching section 1's own pattern
        ok = await fram.set_values(_FRAM_WRITE_PATTERN, addr_start=_FRAM_WRITE_REGION[0])
        assert ok, "FRAM write failed outright under concurrent read load"
        write_completed = True

    async def locked_call(coro: "Coroutine[Any, Any, None]") -> None:
        async with fram:
            await coro

    with _FastAsyncSleep():
        run(_gather(locked_call(reader()), locked_call(writer())))

    assert reads_completed == read_iterations
    assert write_completed
    assert not read_mismatches, f"{len(read_mismatches)} corrupted/torn read(s) under concurrent write: {read_mismatches[:5]}"
    written_back = bytes(chip.memory[_FRAM_WRITE_REGION[0] : _FRAM_WRITE_REGION[0] + _FRAM_WRITE_REGION[1]])
    assert written_back == _FRAM_WRITE_PATTERN, f"write region shows {written_back.hex()}, expected {_FRAM_WRITE_PATTERN.hex()} - torn/corrupted write"


async def setup_fram_test(fram: FRAM_SPI) -> None:
    await fram.setup()


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
