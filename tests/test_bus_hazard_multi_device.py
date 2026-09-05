"""Mock-level (tests/machine.py fake I2C) bus-hazard/concurrency regression suite - the fast,
deterministic, every-CI-run counterpart to tests_hardware/flash/test_bus_concurrency.py's real-
hardware proof of the same SPECIFICATION.md Part C.8 locking model. Covers what a real-hardware run
can't cheaply cover on every push: byte-exact wire-log proof that same-device operations never
interleave, genuine cross-device interleaving with correct final results, the SGP40 general-call
broadcast landing mid a sibling's own transaction, and a full address/command sweep across every
promoted I2C driver's public API.

**Standing rule - read before adding a new I2C-facing driver to src/:** add a
`test_<driver>_never_touches_any_address_but_its_own` function for it (section 4 below - see the
existing SCD30/BMP3xx/SGP40 ones for the pattern), and, if the new driver issues any
non-addressed-to-itself bus operation like SGP40's general call, extend section 3 with its own
concurrent-hazard test too. This is the "flag it here so it's never silently missed" enforcement
point for CLAUDE.md's src/ bird's-eye-scan requirement, applied to the bus-hazard surface
specifically - see SPECIFICATION.md Part C.8's own note on this.
"""

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
    def __enter__(self) -> "_FastAsyncSleep":
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
# 1. Same-device concurrency: a read in flight must never interleave, at the wire-byte level,
#    with a concurrent write to the SAME device (SCD30_DeviceSession's own device-session lock).
# ---------------------------------------------------------------------------


_CMD_GET_DATA_READY = b"\x02\x02"
_CMD_READ_MEASUREMENT = b"\x03\x00"
_CMD_SET_TEMPERATURE_OFFSET = b"\x54\x03"


def _parse_scd30_log(log: list, read_iterations: int) -> None:
    # Precise, command-byte-based proof that same-device operations never interleave on the wire -
    # NOT a before/after log-length "span" comparison (an earlier version of this test used that
    # and produced a false positive: a coroutine legitimately *blocked* waiting for the
    # device-session lock naturally has its own outer await span overlap whoever currently holds
    # it - that's proof of correct serialization, not evidence of interleaving, since nothing that
    # blocked coroutine does can append to the log until the lock is actually released).
    #
    # SCD30's own three commands used in this test are wire-distinguishable by their first two
    # payload bytes (asy_scd30_driver.py's own _CMD_* constants), so the log can be parsed into
    # non-overlapping runs: a read_measurement() cycle is always exactly
    # [writeto(GET_DATA_READY), readfrom_into, writeto(READ_MEASUREMENT), readfrom_into] as one
    # atomic 4-entry group (this test always seeds "data ready", so the short 2-entry not-ready
    # path never applies); set_temperature_offset() is always exactly
    # [writeto(SET_TEMPERATURE_OFFSET)] as one atomic 1-entry group. If the device-session lock
    # ever let the two interleave, this parse fails outright - a stray or out-of-place entry has
    # nowhere valid to go, rather than silently producing a plausible-looking wrong grouping.
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
#    matching production wozi wiring - see sensortask_wozi.py) must genuinely interleave (not
#    fully serialize), and each must still produce fully correct, uncorrupted results.
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

    # Genuine interleaving proof: the two devices' own addressed log entries must not form two
    # separate contiguous blocks (one fully before the other) - if they did, the bus lock's
    # fine-grained per-transaction scope (SPECIFICATION.md Part C.8) would not actually be letting
    # them interleave, just accidentally running one after the other in full.
    # BMP3xx uses readfrom_mem/writeto_mem (register-address-based); SGP40 uses writeto/readfrom_into
    # (raw command-based) - both op families must be counted, or BMP3xx's own entries silently drop
    # out of this check entirely (found the hard way: an earlier version only checked
    # writeto/readfrom_into and always reported "1 switch" - BMP3xx's own address never appeared at
    # all, not because it wasn't interleaving, but because none of its ops were being counted).
    addressed = [entry[1] for entry in fake_bus.log if entry[0] in ("writeto", "readfrom_into", "readfrom_mem", "writeto_mem")]
    # Plain index-based comparison, not zip(strict=...) - confirmed directly against the real
    # MicroPython Unix-port interpreter that its builtin zip() doesn't accept keyword arguments at
    # all (TypeError), unlike CPython 3.10+'s strict= parameter ruff's B905 rule would otherwise ask for.
    switches = sum(1 for i in range(len(addressed) - 1) if addressed[i] != addressed[i + 1])
    assert switches >= 2, f"only {switches} address switch(es) across the whole run - looks fully serialized, not interleaved: {addressed}"


# ---------------------------------------------------------------------------
# 3. General-call broadcast hazard: SGP40's _reset() (true I2C general call, datasheet Table 17)
#    landing concurrently with BMP3xx's own multi-step read must not corrupt or interrupt it -
#    the mock-level regression counterpart of tests_hardware/flash/test_bus_concurrency.py's
#    real-hardware test (see SPECIFICATION.md Part C.8's own "Known structural gap" note).
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
    # The "closest possible simulation when a real second device isn't present" case the project
    # owner asked for: BMP3xx is the *only* device on this bus (matching dev's real i2c0 wiring -
    # sensortask_dev.py), and the bus master itself still issues a general-call broadcast (as if a
    # future SGP40 were added to this same bus) mid a BMP3xx read. No SGP40_I2C instance exists at
    # all here - the broadcast is issued directly against the raw I2C wrapper, the same way
    # SGP40_I2C._reset() itself does, to prove BMP3xx alone tolerates it regardless of who's doing
    # the broadcasting.
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
# 4. Address/command sweep: every promoted I2C driver's public API, exercised end to end, must
#    never touch any address other than its own configured one - except SGP40's own documented
#    general call (0x00), which must appear *only* from _reset(), nowhere else.
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
            except Exception:  # noqa: BLE001 - only the addresses *touched* matter for this sweep, not success
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
            except Exception:  # noqa: BLE001 - see test_scd30's own comment
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
            except Exception:  # noqa: BLE001 - see test_scd30's own comment
                pass

    with _FastAsyncSleep():
        run(exercise_non_reset())

    touched = _touched_addresses(fake_bus)
    # setup() itself calls initialize() -> _reset(), so 0x00 is expected here too - the real
    # assertion (0x00 appears *only* via _reset()'s own single documented call site) is proven by
    # test_sgp40_general_call_reset_does_not_disturb_a_concurrent_bmp3xx_read and
    # tests/test_asy_sgp40_driver.py's own test_reset_writes_single_byte_to_general_call_address_zero
    # / test_reset_tolerates_nak_at_general_call_address; this sweep's own job is narrower - confirm
    # no *third*, unexpected address ever shows up beyond {own address, general call}.
    assert touched <= {_SGP_ADDR, _GENERAL_CALL_ADDR}, f"SGP40_I2C touched unexpected address(es): {touched - {_SGP_ADDR, _GENERAL_CALL_ADDR}}"
    assert not _is_reserved(_SGP_ADDR)


def test_no_reserved_i2c_address_collides_with_any_promoted_devices_own_address() -> None:
    # A permanent regression guard for any *future* device addition (CLAUDE.md's "never forget"
    # rule, SPECIFICATION.md Part C.8) - a new driver whose default address accidentally falls in
    # a reserved I2C range would be caught here immediately, before it ever reaches real hardware.
    for name, address in (("SCD30", _SCD_ADDR), ("BMP3xx", _BMP_ADDR), ("SGP40", _SGP_ADDR)):
        assert not _is_reserved(address), f"{name}'s own address {address:#x} falls inside a reserved I2C range"


# ---------------------------------------------------------------------------
# 5. FRAM (SPI) - the one promoted bus-facing device with no I2C address concept and no bus-
#    sharing: sections 2 (cross-device interleave) and 3 (general-call broadcast) don't apply -
#    both wozi and dev wire exactly one SPI device to its own dedicated bus (sensortask_wozi.py/
#    sensortask_dev.py's own construction comments). Same-device concurrency (this section) is
#    therefore FRAM's whole applicable slice of this file's own standing rule (see this module's
#    own docstring) - previously missing entirely, a real gap against that rule fixed here.
#    Proven by outcome (final memory state, every read exactly matches what it should), not
#    wire-log byte parsing like section 1's SCD30 test: FakeMB85RS64V's own write()/readinto()
#    (tests/_fram_chip_fake.py) don't feed tests/machine.py's shared SPI.log at all (they fully
#    override the base fake's methods rather than delegating to them) - but its own internal
#    _pending_op/_pending_addr two-phase opcode/data state machine is itself corruption-sensitive:
#    a read's opcode phase landing between a write's own opcode-phase and data-phase calls would
#    silently misroute the write's data bytes to the wrong branch, which a plain "did the right
#    bytes end up in the right place" assertion below would still catch directly.
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
