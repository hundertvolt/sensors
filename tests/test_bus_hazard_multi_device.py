"""Mock-level (tests/machine.py's fake I2C and SPI) bus-hazard suite - the fast, deterministic
tier of SPECIFICATION.md Part C.8. Holds only driver-agnostic hazard shapes; a driver-specific
one lives with that driver. Runs alongside test_bus_hazard_generated.py, not a staging area for it."""

import asyncio
import struct

from _bus_hazard_catalog import I2C_HAZARD_CATALOG, assert_no_transfer_inside_the_recovery, crc8, fake, hold_sda_through_a_stretched_clear, make_i2c, recover_marking_the_clear, seed_isl_ready
from _bus_hazard_catalog import sgp_word as _sgp_word
from _error_codes import code
from _tmp_scratch import TmpScratch

from asy_bmp3xx_driver import BMP3XX_I2C
from asy_i2c_driver import I2C
from asy_isl29125_driver import ISL29125_I2C, ISL29125_Reader
from asy_sgp40_driver import SGP40_I2C
from asy_spi_driver import SPI, SPIDevice

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
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
_ISL_ADDR = 0x44  # hard-wired (FN8424 p15) - dev-only, sharing i2c1 with SCD30 and SGP40
_GENERAL_CALL_ADDR = 0x00
# I2C spec reserved address ranges (0x00-0x07: general call/CBUS/reserved/Hs-mode; 0x78-0x7F:
# 10-bit addressing/reserved) - every real device address this codebase uses must fall outside
# both, and only SGP40's own documented _reset() may ever address 0x00 specifically.
_RESERVED_RANGES = ((0x00, 0x07), (0x78, 0x7F))


def _is_reserved(address: int) -> bool:
    return any(lo <= address <= hi for lo, hi in _RESERVED_RANGES)


# BMP3xx: a fixed, reproducible calibration/ADC dataset, the same one test_asy_bmp3xx_driver.py uses - not
# re-deriving the expected values here, correctness of the compensation math being covered there. This file
# needs only a deterministic, known-good reading to detect corruption.
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


def seed_bmp_ready(i2c: I2C, address: int = _BMP_ADDR, chip_id: int = 0x50) -> None:
    # STATUS: cmd_rdy | drdy_press | drdy_temp: ERR_REG and EVENT clear - see test_asy_bmp3xx_driver.py's
    # own ready_bmp() for the same shape. The driver's burst reads ERR_REG, STATUS and the data from 0x02.
    status = 0x10 | 0x60
    fake(i2c).registers[(address, 0x03)] = bytearray([status])  # _REGISTER_STATUS
    fake(i2c).registers[(address, 0x02)] = bytearray([0x00, status]) + _bmp_data6(_BMP_ADC_P, _BMP_ADC_T)  # _REGISTER_ERR to 0x09
    fake(i2c).registers[(address, 0x10)] = bytearray([0x00])  # _REGISTER_EVENT
    fake(i2c).registers[(address, 0x00)] = bytearray([chip_id])  # _REGISTER_CHIPID: 0x50 BMP384/388, 0x60 BMP390
    fake(i2c).registers[(address, 0x31)] = bytearray(_BMP_CAL_RAW)  # _REGISTER_CAL_DATA


# ---------------------------------------------------------------------------
# 1. Cross-device concurrency: two DIFFERENT devices sharing one bus (BMP3xx + SGP40 on i2c1,
#    matching wozi's wiring) must genuinely interleave, not fully serialize, and both must stay correct.
# ---------------------------------------------------------------------------


def test_cross_device_bmp3xx_and_sgp40_interleave_and_both_stay_correct() -> None:
    bmp_iterations = 6
    sgp_iterations = 4
    for chip_id in (0x50, 0x60):  # both documented BMP3XX chip IDs: BMP384/388 and BMP390
        i2c = make_i2c(1)  # matches wozi's real i2c1 port id
        bmp = BMP3XX_I2C(i2c, address=_BMP_ADDR)
        sgp = SGP40_I2C(i2c)
        fake_bus = fake(i2c)
        seed_bmp_ready(i2c, chip_id=chip_id)
        run(bmp.setup())  # populates _temp_calib/_pressure_calib from the seeded CAL_DATA - required before any real _read()
        fake_bus.log.clear()

        for _ in range(sgp_iterations):
            fake_bus.read_queue.append(_sgp_word(0x8000))  # a fixed, known-good raw measurement word

        bmp_results: list[tuple[float, float]] = []
        sgp_results: list[int | None] = []

        async def bmp_loop(bmp: BMP3XX_I2C = bmp, bmp_results: "list[tuple[float, float]]" = bmp_results) -> None:
            for _ in range(bmp_iterations):
                assert await bmp.take_por_detected() is False  # the reader's per-cycle EVENT read, then the conversion
                pressure, temperature = await bmp.get_pressure_and_temperature()
                bmp_results.append((pressure, temperature))
                await asyncio.sleep(0)

        async def sgp_loop(sgp: SGP40_I2C = sgp, sgp_results: "list[int | None]" = sgp_results) -> None:
            for _ in range(sgp_iterations):
                raw = await sgp.measure_raw(temperature=25, relative_humidity=50)
                sgp_results.append(raw)
                await asyncio.sleep(0)

        with _FastAsyncSleep():
            run(_gather(bmp_loop(), sgp_loop()))

        assert len(bmp_results) == bmp_iterations, chip_id
        assert len(sgp_results) == sgp_iterations, chip_id
        for pressure, temperature in bmp_results:
            assert abs(pressure - _BMP_EXPECTED_PRESSURE_HPA) < 1e-6
            assert abs(temperature - _BMP_EXPECTED_TEMPERATURE) < 1e-6
        assert all(raw == 0x8000 for raw in sgp_results)
        log = list(fake_bus.log)
        assert _register_reads_unbroken(log, _BMP_ADDR) > 0  # every register read, the EVENT read included, atomic
        assert sum(1 for entry in log if entry[:3] == ("writeto", _BMP_ADDR, b"\x10")) == bmp_iterations  # one EVENT read per cycle

        # Genuine interleaving proof: addressed log entries must not form two separate contiguous
        # blocks (one fully before the other). BMP3xx's register access (an address writeto, then
        # readfrom_into) and SGP40's raw words both log as writeto/readfrom_into.
        addressed = [entry[1] for entry in fake_bus.log if entry[0] in ("writeto", "readfrom_into")]
        # Plain index-based comparison, not zip(strict=...): MicroPython's builtin zip() doesn't accept
        # keyword arguments (confirmed against the pinned Unix-port interpreter).
        switches = sum(1 for i in range(len(addressed) - 1) if addressed[i] != addressed[i + 1])
        assert switches >= 2, f"only {switches} address switch(es) across the whole run - looks fully serialized, not interleaved: {addressed}"


def test_cross_device_isl29125_and_sgp40_interleave_and_both_stay_correct() -> None:
    # dev's own i2c1 grouping: the ISL is register-addressed while the SGP40 speaks a raw
    # word protocol, so the two exercise completely different transaction shapes on one bus.
    i2c = make_i2c(1)
    isl = ISL29125_I2C(i2c)
    sgp = SGP40_I2C(i2c)
    fake_bus = fake(i2c)
    seed_isl_ready(i2c)

    isl_iterations = 6
    sgp_iterations = 4
    for _ in range(sgp_iterations):
        fake_bus.read_queue.append(_sgp_word(0x8000))

    isl_results: list[tuple[int, int, int]] = []
    sgp_results: list[int | None] = []
    snapshots: list[bytes] = []

    async def isl_loop() -> None:
        for _ in range(isl_iterations):
            await isl.read_status()  # the reader's cycle: STATUS, the CONFIG snapshot, then the counts
            snapshots.append(bytes(await isl.get_config_snapshot()))
            isl_results.append(await isl.read_counts())
            await asyncio.sleep(0)

    async def sgp_loop() -> None:
        for _ in range(sgp_iterations):
            sgp_results.append(await sgp.measure_raw(temperature=25, relative_humidity=50))
            await asyncio.sleep(0)

    with _FastAsyncSleep():
        run(_gather(isl_loop(), sgp_loop()))

    assert len(isl_results) == isl_iterations
    assert all(counts == (0x2000, 0x1800, 0x1000) for counts in isl_results)
    assert snapshots == [bytes(3)] * isl_iterations  # the seeded post-reset CONFIG1-3, never torn
    assert _register_reads_unbroken(list(fake_bus.log), _ISL_ADDR) == 3 * isl_iterations  # status, snapshot and counts, each atomic
    assert sgp_results == [0x8000] * sgp_iterations
    addressed = [entry[1] for entry in fake_bus.log if entry[0] in ("writeto", "readfrom_into")]
    switches = sum(1 for i in range(len(addressed) - 1) if addressed[i] != addressed[i + 1])
    assert switches >= 2, f"only {switches} address switch(es) - looks fully serialized, not interleaved: {addressed}"


# ---------------------------------------------------------------------------
# 2. General-call broadcast hazard: a true I2C general call landing concurrently with a sibling's
#    own multi-step read must not corrupt or interrupt it - including the case where the bus's
#    lone occupant has no broadcaster of its own at all.
# ---------------------------------------------------------------------------


def test_sgp40_general_call_reset_does_not_disturb_a_concurrent_bmp3xx_read() -> None:
    i2c = make_i2c(1)
    bmp = BMP3XX_I2C(i2c, address=_BMP_ADDR)
    sgp = SGP40_I2C(i2c)
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


def test_sgp40_general_call_reset_does_not_disturb_a_concurrent_isl29125_read() -> None:
    # The general-call broadcast hazard again, this time against the sibling that actually shares
    # a bus with the SGP40 on dev (SPECIFICATION.md Part C.8's own standing note).
    i2c = make_i2c(1)
    isl = ISL29125_I2C(i2c)
    sgp = SGP40_I2C(i2c)
    fake_bus = fake(i2c)
    seed_isl_ready(i2c)
    results: list[tuple[int, int, int]] = []

    async def isl_loop() -> None:
        for _ in range(6):
            results.append(await isl.read_counts())
            await asyncio.sleep(0)

    async def broadcaster() -> None:
        await asyncio.sleep(0)
        await sgp._reset()  # a true I2C general call to address 0x00

    with _FastAsyncSleep():
        run(_gather(isl_loop(), broadcaster()))

    assert all(counts == (0x2000, 0x1800, 0x1000) for counts in results)
    assert any(entry[0] == "writeto" and entry[1] == 0x00 for entry in fake_bus.log), "the general call never fired - this test isn't exercising the hazard"


def test_general_call_absent_sibling_bmp3xx_alone_on_the_bus_survives_a_broadcast_too() -> None:
    # BMP3xx is the only device on this bus, matching dev's real i2c0 wiring, and the broadcast is issued
    # directly against the raw I2C wrapper to prove BMP3xx alone tolerates a general call whoever issues it.
    #
    # This is the ROGUE-broadcast case tests/_bus_hazard_catalog.py's TOML-driven scheme cannot generate, it
    # only ever firing a general call a catalog occupant's own adapter issues, so it stays hand-written.
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
# 3. Fault isolation: one occupant's own bus-level failure (NAK/timeout) must stay isolated to
#    itself and never corrupt or stall a concurrent sibling's own transactions on the same bus.
# ---------------------------------------------------------------------------


def test_sgp40_bus_fault_does_not_corrupt_or_stall_a_concurrent_isl29125_read() -> None:
    i2c = make_i2c(1)
    isl = ISL29125_I2C(i2c)
    sgp = SGP40_I2C(i2c)
    fake_bus = fake(i2c)
    seed_isl_ready(i2c)
    fake_bus.nak_addresses.add(_SGP_ADDR)  # simulates a wedged/timed-out SGP40 sharing this bus

    isl_iterations = 6
    sgp_attempts = 4
    isl_results: list[tuple[int, int, int]] = []
    sgp_errors = 0

    async def isl_loop() -> None:
        for _ in range(isl_iterations):
            isl_results.append(await isl.read_counts())
            await asyncio.sleep(0)

    async def sgp_loop() -> None:
        nonlocal sgp_errors
        for _ in range(sgp_attempts):
            try:
                await sgp.measure_raw(temperature=25, relative_humidity=50)
            except OSError:
                sgp_errors += 1
            await asyncio.sleep(0)

    with _FastAsyncSleep():
        run(_gather(isl_loop(), sgp_loop()))

    assert len(isl_results) == isl_iterations
    assert all(counts == (0x2000, 0x1800, 0x1000) for counts in isl_results), "SGP40's own bus fault corrupted a concurrent ISL29125 read"
    assert sgp_errors == sgp_attempts, f"expected every faulted SGP40 call to raise, got {sgp_errors}/{sgp_attempts}"


def _register_reads_unbroken(log: "list[Any]", address: int) -> int:
    # Every no-stop register-address write to `address` is followed at once by its readfrom_into, never by
    # a sibling's transfer between the two. Returns how many such reads the log holds.
    count = 0
    for i, entry in enumerate(log):
        if entry[0] == "writeto" and entry[1] == address and not entry[3] and entry[2]:
            assert i + 1 < len(log) and log[i + 1][0:2] == ("readfrom_into", address), f"a transfer landed inside a register read at log index {i}: {log[i : i + 2]}"
            count += 1
    return count


def test_a_register_read_is_two_transfers_with_no_sibling_transfer_between_them() -> None:
    # A register read writes the address with no stop, then reads: both inside one bus session, so a
    # concurrent sibling's transfer can never land between the two halves.
    i2c = make_i2c(1)
    bmp = BMP3XX_I2C(i2c, address=_BMP_ADDR)
    sgp = SGP40_I2C(i2c)
    fake_bus = fake(i2c)
    seed_bmp_ready(i2c)
    run(bmp.setup())
    for _ in range(4):
        fake_bus.read_queue.append(_sgp_word(0x8000))

    async def bmp_loop() -> None:
        for _ in range(6):
            await bmp.get_pressure_and_temperature()
            await asyncio.sleep(0)

    async def sgp_loop() -> None:
        for _ in range(4):
            assert await sgp.measure_raw(temperature=25, relative_humidity=50) == 0x8000
            await asyncio.sleep(0)

    with _FastAsyncSleep():
        run(_gather(bmp_loop(), sgp_loop()))
    assert _register_reads_unbroken(list(fake_bus.log), _BMP_ADDR) >= 6 * 2  # STATUS and the burst per cycle


def test_a_short_ack_on_one_device_fails_only_that_device_and_leaves_sibling_reads_valid() -> None:
    i2c = make_i2c(1)
    bmp = BMP3XX_I2C(i2c, address=_BMP_ADDR)
    sgp = SGP40_I2C(i2c)
    fake_bus = fake(i2c)
    seed_bmp_ready(i2c)
    run(bmp.setup())
    for _ in range(4):
        fake_bus.read_queue.append(_sgp_word(0x8000))
    fake_bus.log.clear()  # drop setup()'s own traffic, its zero-length probe included
    fake_bus.short_ack(_BMP_ADDR, 0)  # the BMP3xx NACKs the next register byte it is sent
    bmp_errors: list[int | None] = []

    async def bmp_loop() -> None:
        for _ in range(3):
            try:
                await bmp.get_config_snapshot()
            except OSError as e:
                bmp_errors.append(e.errno)
            await asyncio.sleep(0)

    async def sgp_loop() -> None:
        for _ in range(4):
            assert await sgp.measure_raw(temperature=25, relative_humidity=50) == 0x8000
            await asyncio.sleep(0)

    with _FastAsyncSleep():
        run(_gather(bmp_loop(), sgp_loop()))
    assert bmp_errors == [5]  # one EIO, then the device answers again
    log = list(fake_bus.log)  # a snapshot of the ring log, oldest first
    stop = log.index(("writeto", _BMP_ADDR, b"", True))
    assert log[stop - 1][0:2] == ("writeto", _BMP_ADDR), "the STOP follows the short write at once"


async def _recover_between_halves(i2c: I2C, target: int, trigger: bytes, read: "Coroutine[Any, Any, None]", after_recovery: "Callable[[], None] | None" = None) -> None:
    # Runs `read`, and i2c.recover() the moment `trigger` (its first half's write) has reached the bus.
    bus = fake(i2c)
    real_writeto = bus.writeto
    fired = asyncio.Event()

    def watching(address: int, buf: object, stop: bool = True) -> int:  # noqa: FBT001, FBT002  # machine.I2C's own positional stop
        n = real_writeto(address, buf, stop)
        if address == target and bytes(buf) == trigger:  # type: ignore[call-overload]
            fired.set()
        return n

    async def recovery() -> None:
        await fired.wait()
        await i2c.recover()
        if after_recovery is not None:
            after_recovery()

    bus.writeto = watching  # type: ignore[method-assign]
    try:
        await asyncio.gather(read, recovery())
    finally:
        bus.writeto = real_writeto  # type: ignore[method-assign]


def _assert_recovery_between(i2c: I2C, address: int, trigger: bytes) -> None:
    # The second half ends with the transaction's last read (BMP3XX: the data burst after its STATUS polls).
    log = list(fake(i2c).log)  # a snapshot of the ring log, oldest first
    first = log.index(("writeto", address, trigger, True))
    init = next(i for i in range(first, len(log)) if log[i][0] == "init")
    last = max(i for i in range(first + 1, len(log)) if log[i][0] == "readfrom_into" and log[i][1] == address)
    assert first < init < last, f"the recovery did not land between the two halves: {log[first : last + 1]}"


def test_a_recovery_between_a_split_session_still_returns_a_valid_value() -> None:
    # SCD30 command -> read, SGP40 command -> read, BMP3XX trigger -> read: each releases the bus between
    # its halves, where a bus clear and controller re-construction may land; the idle slave sees no
    # START, and the transaction's second half still reads a valid value (adapters' read_once checks).
    failures: list[str] = []
    for driver, address, trigger in (
        ("scd30", _SCD_ADDR, b"\x03\x00"),  # read measurement (Interface Description 1.4.5)
        ("sgp40", _SGP_ADDR, _sgp40_measure_command(25, 50)),
        ("bmp3xx", _BMP_ADDR, b"\x1b\x13"),  # PWR_CTRL forced mode
    ):
        adapter = I2C_HAZARD_CATALOG[driver]
        i2c = make_i2c(1)
        instance = adapter.construct(i2c, address)
        after = None
        if driver == "bmp3xx":
            with _FastAsyncSleep():
                run(instance.setup())
            fake(i2c).registers[(address, 0x03)] = bytearray([0x00])  # STATUS not ready: the poll yields

            def after(i2c: I2C = i2c, address: int = address) -> None:  # bound now: the loop moves on
                fake(i2c).registers[(address, 0x03)] = bytearray([0x10 | 0x60])

        adapter.seed(fake(i2c), address, 1)
        with _FastAsyncSleep():
            run(_recover_between_halves(i2c, address, trigger, adapter.read_once(instance), after))
        try:
            _assert_recovery_between(i2c, address, trigger)
        except AssertionError as e:
            failures.append(f"{driver}: {e}")
    assert not failures, failures


def test_a_recovery_during_a_held_bus_clear_lets_no_sibling_transfer_in() -> None:
    # The clear yields under the bus lock (a stretched clock); the sibling read loops queue behind it.
    i2c = make_i2c(1)
    isl = ISL29125_I2C(i2c)
    sgp = SGP40_I2C(i2c)
    fake_bus = fake(i2c)
    seed_isl_ready(i2c)
    for _ in range(4):
        fake_bus.read_queue.append(_sgp_word(0x8000))
    hold_sda_through_a_stretched_clear(i2c)
    marks: list[int] = []

    async def isl_loop() -> None:
        for _ in range(4):
            assert await isl.read_counts() == (0x2000, 0x1800, 0x1000)
            await asyncio.sleep(0)

    async def sgp_loop() -> None:
        for _ in range(4):
            assert await sgp.measure_raw(temperature=25, relative_humidity=50) == 0x8000
            await asyncio.sleep(0)

    async def recovery() -> None:
        await asyncio.sleep(0)
        _status, mark = await recover_marking_the_clear(i2c)
        marks.append(mark)

    async def scenario() -> None:
        await asyncio.gather(isl_loop(), sgp_loop(), recovery())

    with _FastAsyncSleep():
        run(scenario())
    assert_no_transfer_inside_the_recovery(fake_bus, marks[0])


# Mirrors of asy_i2c_driver's clear constants (const() names are not importable) and a stall past its 50 ms bound
_CLEAR_PULSES = 9
_REC_SDA_LOW = 1
_REC_SDA_STUCK = 2
_HOST_STALL_MS = 60


def test_a_host_stall_inside_a_stretched_clear_does_not_read_as_a_held_clock() -> None:
    # The planted slave stretches for a count of reads, so the recovery must judge it in poll rounds: a host
    # stall past the driver's 50 ms SCL-release bound, landing inside the first wait, still clears the bus.
    i2c = make_i2c(1)
    hold_sda_through_a_stretched_clear(i2c, pulses=_CLEAR_PULSES + 1, host_stall_ms=_HOST_STALL_MS)
    status, _mark = run(recover_marking_the_clear(i2c))
    assert status == _REC_SDA_LOW | _REC_SDA_STUCK, f"a host stall read as a held clock: status {status}"


# ---------------------------------------------------------------------------
# 3b. The participant rungs mid-traffic (SPECIFICATION.md C.7, C.8): each chip's own recovery command lands at
# every timing offset into its siblings' read loops on dev's shared i2c1 (SCD30, SGP40, ISL29125); every
# sibling read stays valid, through the catalog adapters' own corruption checks.
# ---------------------------------------------------------------------------

_RUNG_OFFSETS = 6  # as many offsets as each loop has reads, the catalog scenarios' own default
_DEV_I2C1 = (("scd30", _SCD_ADDR), ("sgp40", _SGP_ADDR), ("isl29125", _ISL_ADDR))
_scratch = TmpScratch("bus_hazard_multi_device")


def _dev_i2c1() -> "tuple[I2C, dict[str, Any]]":
    i2c = make_i2c(1)
    return i2c, {driver: I2C_HAZARD_CATALOG[driver].construct(i2c, address) for driver, address in _DEV_I2C1}


async def _rung_beside_sibling_reads(i2c: I2C, instances: "dict[str, Any]", siblings: "tuple[str, ...]", rung: "Callable[[], Coroutine[Any, Any, object]]", offset: int) -> None:
    for driver, address in _DEV_I2C1:
        if driver in siblings:
            I2C_HAZARD_CATALOG[driver].seed(fake(i2c), address, _RUNG_OFFSETS)

    async def reads(driver: str) -> None:
        for _ in range(_RUNG_OFFSETS):
            await I2C_HAZARD_CATALOG[driver].read_once(instances[driver])
            await asyncio.sleep(0)

    async def fire() -> None:
        for _ in range(offset):
            await asyncio.sleep(0)
        await rung()

    await asyncio.gather(*(reads(driver) for driver in siblings), fire())


def _across_offsets(scenario: "Callable[[int], None]") -> None:
    failures = []
    for offset in range(_RUNG_OFFSETS):
        try:
            scenario(offset)
        except AssertionError as e:
            failures.append(f"offset={offset}: {e}")
    assert not failures, f"{len(failures)}/{_RUNG_OFFSETS} timing offset(s) reproduced a hazard: {failures}"


def test_an_scd30_soft_reset_mid_read_leaves_every_sibling_read_valid() -> None:
    # The SCD30's participant rung is its soft reset (0xD304, Interface Description 1.4.10); its 2.5 s restart
    # wait runs outside the bus lock, so the siblings keep reading through it.
    def scenario(offset: int) -> None:
        i2c, instances = _dev_i2c1()
        with _FastAsyncSleep():
            run(_rung_beside_sibling_reads(i2c, instances, ("sgp40", "isl29125"), instances["scd30"].reset, offset))
        to_scd = [entry for entry in fake(i2c).log if entry[0] == "writeto" and entry[1] == _SCD_ADDR]
        assert to_scd == [("writeto", _SCD_ADDR, b"\xd3\x04", True)], to_scd

    _across_offsets(scenario)


def test_sgp40_heater_off_does_not_disturb_a_concurrent_scd30_read_loop() -> None:
    # The SGP40's participant rung, 0x3615 to 0x59 alone (datasheet Table 14), beside the SCD30 and ISL29125 loops.
    def scenario(offset: int) -> None:
        i2c, instances = _dev_i2c1()
        with _FastAsyncSleep():
            run(_rung_beside_sibling_reads(i2c, instances, ("scd30", "isl29125"), instances["sgp40"].turn_heater_off, offset))
        to_sgp = [entry for entry in fake(i2c).log if entry[0] in ("writeto", "readfrom_into") and entry[1] == _SGP_ADDR]
        assert to_sgp == [("writeto", _SGP_ADDR, b"\x36\x15", True)], to_sgp

    _across_offsets(scenario)


def test_heater_off_and_an_sgp40_measure_serialise_through_the_device_session() -> None:
    # Same device: a heater-off issued while a measure waits for its reply never lands between the measure's
    # command and its read - the device session spans the whole measure exchange.
    i2c = make_i2c(1)
    sgp = SGP40_I2C(i2c)
    fake(i2c).read_queue_by_address[_SGP_ADDR] = [_sgp_word(0x8000), _sgp_word(0x8001)]
    results: list[int | None] = []

    async def measure() -> None:
        results.append(await sgp.measure_raw(temperature=25, relative_humidity=50))

    async def scenario() -> None:
        await asyncio.gather(measure(), sgp.turn_heater_off(), measure())

    with _FastAsyncSleep():
        run(scenario())
    log = [entry for entry in fake(i2c).log if entry[0] in ("writeto", "readfrom_into") and entry[1] == _SGP_ADDR]
    kinds = ["heater" if entry[0] == "writeto" and entry[2] == b"\x36\x15" else entry[0] for entry in log]
    assert kinds.count("heater") == 1, kinds
    for i, kind in enumerate(kinds):
        if kind == "writeto":
            assert kinds[i + 1] == "readfrom_into", f"something landed inside a measure exchange: {kinds}"
    assert len(results) == 2 and set(results) == {0x8000, 0x8001}, results


def test_an_isl29125_reapply_mid_read_leaves_every_sibling_read_valid() -> None:
    # The ISL29125's participant rung re-writes CONFIG1-3 from its shadow and re-arms the thresholds; it runs
    # through the reader's ladder (one W DEVICE_RECOVERY) beside the SCD30 and SGP40 loops on dev's i2c1.
    def scenario(offset: int) -> None:
        i2c, instances = _dev_i2c1()
        reader = ISL29125_Reader(i2c, 15, cfg_path=_scratch.dir())
        seed_isl_ready(i2c, _ISL_ADDR)
        run(reader.setup())
        fake(i2c).log.clear()
        reader._err_cnt_internal = 2  # the streak at the participant rung

        async def rung() -> None:
            await reader._climb_ladder()

        with _FastAsyncSleep():
            run(_rung_beside_sibling_reads(i2c, instances, ("scd30", "sgp40"), rung, offset))
        log = run(reader.get_error_counter())["ISL29125"]
        recoveries = [i for i in range(len(log["ErrNum"])) if log["ErrType"][i] == "W" and log["ErrNum"][i] == code("W", "DEVICE_RECOVERY")]
        assert len(recoveries) == 1 and log["ErrType"].count("E") == 0, log
        writes = [entry[2] for entry in fake(i2c).log if entry[0] == "writeto" and entry[1] == _ISL_ADDR and entry[3]]
        assert any(w[:1] == b"\x01" and len(w) == 4 for w in writes), f"no whole CONFIG1-3 burst: {writes}"
        assert any(w[:1] == b"\x04" for w in writes), f"the thresholds were not re-armed: {writes}"  # auto-range's thresholds
        assert bytes(fake(i2c).registers[(_ISL_ADDR, 0x01)]) == reader._isl.encode_shadow(), "the chip's CONFIG1-3 differ from the shadow"

    _across_offsets(scenario)


# ---------------------------------------------------------------------------
# 4. Parallel sessions: multiple concurrent CALLERS hitting the SAME device instance, as opposed to
# different devices sharing a bus above, must never scramble each other's commands or reads: the device
# session serializes the callers, and each one's inputs are staged inside it (SPECIFICATION.md Part C.8).
# ---------------------------------------------------------------------------


def _sgp40_measure_command(temperature: int, relative_humidity: int) -> bytes:
    # Independent oracle from the SGP40 datasheet, not the driver's tick helpers: command 0x260F, then the
    # RH word and the T word each with its CRC-8 (Table 9); ticks per Table 10's formulas, rounded half up,
    # which its own 50 % -> 0x8000 row requires; CRC-8 poly 0x31, init 0xFF (Table 7).
    rh_ticks = (relative_humidity * 65535 * 2 + 100) // 200
    t_ticks = ((temperature + 45) * 65535 * 2 + 175) // 350
    rh_word = bytes([rh_ticks >> 8, rh_ticks & 0xFF])
    t_word = bytes([t_ticks >> 8, t_ticks & 0xFF])
    return b"\x26\x0f" + rh_word + bytes([crc8(rh_word)]) + t_word + bytes([crc8(t_word)])


def test_three_concurrent_sessions_on_the_same_sgp40_instance_never_scramble_each_others_reads() -> None:
    i2c = make_i2c(1)
    sgp = SGP40_I2C(i2c)
    fake_bus = fake(i2c)
    assert crc8(b"\xbe\xef") == 0x92  # the oracle's CRC-8 against datasheet Table 7's own example
    assert _sgp40_measure_command(25, 50) == b"\x26\x0f\x80\x00\xa2\x66\x66\x93"  # Table 9's default command
    inputs = ((25, 50), (10, 30), (35, 80))
    expected = {_sgp40_measure_command(t, rh) for t, rh in inputs}
    assert len(expected) == len(inputs)
    fake_bus.read_queue_by_address[_SGP_ADDR] = [_sgp_word(0x8000 + k) for k in range(len(inputs))]
    results: dict[tuple[int, int], int | None] = {}

    async def session(temperature: int, relative_humidity: int) -> None:
        results[(temperature, relative_humidity)] = await sgp.measure_raw(temperature=temperature, relative_humidity=relative_humidity)

    async def scenario() -> None:
        await asyncio.gather(*(session(t, rh) for t, rh in inputs))

    with _FastAsyncSleep():
        run(scenario())

    log = [entry for entry in fake_bus.log if entry[0] in ("writeto", "readfrom_into")]
    assert [(entry[0], entry[1]) for entry in log] == [("writeto", _SGP_ADDR), ("readfrom_into", _SGP_ADDR)] * len(inputs), f"a session's write and read were not adjacent: {log}"
    sent = [bytes(log[i][2]) for i in range(0, len(log), 2)]
    for payload in sent:
        assert crc8(payload[2:4]) == payload[4] and crc8(payload[5:7]) == payload[7], f"a sent command carries a bad CRC: {payload.hex()}"
    assert set(sent) == expected, f"a session's command was overwritten by another's: sent {[p.hex() for p in sent]}"
    word_after = {bytes(log[i][2]): (log[i + 1][2][0] << 8) | log[i + 1][2][1] for i in range(0, len(log), 2)}
    for t, rh in inputs:
        own = word_after[_sgp40_measure_command(t, rh)]
        assert results[(t, rh)] == own, f"the session at {t} C/{rh} % got {results[(t, rh)]}, not the word read after its own write ({own:#x})"


# ---------------------------------------------------------------------------
# 5. Regression guard for future device additions: a new driver whose default address falls in a
#    reserved I2C range is caught here before reaching real hardware.
# ---------------------------------------------------------------------------


def test_no_reserved_i2c_address_collides_with_any_promoted_devices_own_address() -> None:
    for name, address in (("SCD30", _SCD_ADDR), ("BMP3xx", _BMP_ADDR), ("SGP40", _SGP_ADDR), ("ISL29125", _ISL_ADDR)):
        assert not _is_reserved(address), f"{name}'s own address {address:#x} falls inside a reserved I2C range"


# SPI: two devices on one bus, one through the async session and one through the synchronous one.
# The generated TOML-driven scheme cannot produce this shape (every device TOML puts the FRAM alone
# on spi0), and it is what "future multi-device SPI compatibility" has to mean concretely.


def test_spi_async_and_synchronous_sessions_share_one_bus_without_cs_overlap() -> None:
    bus = SPI(0, sck_pin=2, mosi_pin=3, miso_pin=4)
    async_device = SPIDevice(bus, 1)
    sync_device = SPIDevice(bus, 6)
    run(async_device.setup())
    run(sync_device.setup())
    rounds = 12
    overlap_observed = False
    async_done = sync_done = 0

    def both_asserted() -> bool:
        return (
            async_device._cs_pin.value() == async_device._cs_active_value
            and sync_device._cs_pin.value() == sync_device._cs_active_value
        )

    async def async_worker() -> None:
        nonlocal overlap_observed, async_done
        for _ in range(rounds):
            async with async_device:
                overlap_observed = overlap_observed or both_asserted()
                await async_device.write(b"\x05")
            async_done += 1

    async def sync_worker() -> None:
        # The pattern asy_fram_driver.py's own command bodies use: take the bus lock, run the
        # whole CS cycle synchronously, release, then yield - never yielding with CS asserted.
        nonlocal overlap_observed, sync_done
        for _ in range(rounds):
            await bus.bus_lock.acquire()
            try:
                sync_device.session_begin()
                try:
                    overlap_observed = overlap_observed or both_asserted()
                    sync_device.write_sync(b"\x06")
                finally:
                    sync_device.session_end()
            finally:
                bus.bus_lock.release()
            sync_done += 1
            await asyncio.sleep(0)

    async def scenario() -> None:
        await asyncio.gather(async_worker(), sync_worker())

    run(scenario())
    assert not overlap_observed
    assert async_done == rounds
    assert sync_done == rounds
    assert async_device._cs_pin.value() == 1  # both back to inactive afterwards
    assert sync_device._cs_pin.value() == 1
    assert not bus.bus_lock.locked()


def test_spi_synchronous_session_never_leaves_the_bus_locked_when_a_transfer_raises() -> None:
    # Fault isolation across the two session styles: an rx overrun inside the synchronous
    # session must not strand the shared lock or the other device's access to the bus.
    bus = SPI(0, sck_pin=2, mosi_pin=3, miso_pin=4)
    faulting = SPIDevice(bus, 1)
    neighbour = SPIDevice(bus, 6)
    run(faulting.setup())
    run(neighbour.setup())
    bus._spi.rx_overrun = True  # type: ignore[union-attr]  # the fake SPI behind the wrapper
    neighbour_ok = False

    async def scenario() -> bool:
        raised = False
        await bus.bus_lock.acquire()
        try:
            faulting.session_begin()
            try:
                faulting.readinto_sync(bytearray(32))  # 32+ bytes: the DMA path, the only one that can raise
            except OSError:
                raised = True
            finally:
                faulting.session_end()
        finally:
            bus.bus_lock.release()
        nonlocal neighbour_ok
        async with neighbour:
            neighbour_ok = True
            await neighbour.write(b"\x05")
        return raised

    assert run(scenario())
    assert neighbour_ok
    assert not bus.bus_lock.locked()
    assert faulting._cs_pin.value() == 1

if __name__ == "__main__":
    import microtest

    microtest.run(globals())
