"""Mock-level (tests/machine.py's fake I2C and SPI) bus-hazard suite - the fast, deterministic
tier of SPECIFICATION.md Part C.8. Holds only driver-agnostic hazard shapes; a driver-specific
one lives with that driver. Runs alongside test_bus_hazard_generated.py, not a staging area for it."""

import asyncio
import errno
import json

from _async_harness import cancel, run
from _bus_hazard_catalog import (
    BMP_EXPECTED_TEMPERATURE,
    I2C_HAZARD_CATALOG,
    assert_no_transfer_inside_the_recovery,
    crc8,
    fake,
    hold_sda_through_a_stretched_clear,
    i2c_const,
    is_reserved,
    make_i2c,
    recover_marking_the_clear,
    seed_bmp_ready,
    seed_isl_ready,
    sibling_inside_window,
)
from _bus_hazard_catalog import sgp_word as _sgp_word
from _error_codes import code
from _fast_sleep import FastAsyncSleep
from _fram_builders import make_fram_manager
from _fram_chip_fake import _OPCODE_RDSR, _OPCODE_READ, _OPCODE_WRDI, _OPCODE_WREN, _OPCODE_WRITE, FakeMB85RS64V
from _src_const import src_const
from _tmp_scratch import TmpScratch

from asy_bmp3xx_driver import BMP3XX_I2C
from asy_config_manager import ConfigManager
from asy_crc_checks import CRC8, CRC16
from asy_i2c_driver import I2C
from asy_isl29125_driver import ISL29125_I2C, ISL29125_Reader
from asy_scd30_driver import SCD30_I2C
from asy_sgp40_driver import SGP40_I2C
from asy_spi_driver import SPIDevice

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine

    from asy_config_manager import ConfigSchema
    from asy_fram_manager import FRAMChunk, FRAMManager


# ---------------------------------------------------------------------------
# Shared fixtures/helpers
# ---------------------------------------------------------------------------

_SCD_ADDR = 0x61
_BMP_ADDR = 0x77
_SGP_ADDR = 0x59
_ISL_ADDR = 0x44  # hard-wired (FN8424 p15), sharing i2c1 with SCD30 and SGP40 where a TOML puts it there
_GENERAL_CALL_ADDR = 0x00
# How long a sibling's loop may take to finish beside a faulting device; a lock the fault stranded never finishes.
# @tunable l1.bus_fault_isolation_bound_s = 5
_ISOLATION_BOUND_S = 5
# The BMP3XX pressure the catalog's planted calibration and ADC bytes give, by hand: BMP388 datasheet §9.1 and §9.3
# (its temperature is the catalog's BMP_EXPECTED_TEMPERATURE).
_BMP_EXPECTED_PRESSURE_HPA = 713.765147356092


# ---------------------------------------------------------------------------
# 1. Cross-device concurrency: two DIFFERENT devices sharing one bus (the BMP3XX+SGP40 pairing on i2c1)
#    must genuinely interleave, not fully serialize, and both must stay correct.
# ---------------------------------------------------------------------------


def test_cross_device_bmp3xx_and_sgp40_interleave_and_both_stay_correct() -> None:
    bmp_iterations = 6
    sgp_iterations = 4
    for chip_id in (0x50, 0x60):  # both documented BMP3XX chip IDs: BMP384/388 and BMP390
        i2c = make_i2c(1)  # the BMP3XX+SGP40 pairing on i2c1
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

        with FastAsyncSleep():
            run(_gather(bmp_loop(), sgp_loop()))

        assert len(bmp_results) == bmp_iterations, chip_id
        assert len(sgp_results) == sgp_iterations, chip_id
        for pressure, temperature in bmp_results:
            assert abs(pressure - _BMP_EXPECTED_PRESSURE_HPA) < 1e-6
            assert abs(temperature - BMP_EXPECTED_TEMPERATURE) < 1e-6
        assert all(raw == 0x8000 for raw in sgp_results)
        log = list(fake_bus.log)
        assert _register_reads_unbroken(log, _BMP_ADDR) > 0  # every register read, the EVENT read included, atomic
        assert sum(1 for entry in log if entry[:3] == ("writeto", _BMP_ADDR, b"\x10")) == bmp_iterations  # one EVENT read per cycle

        # Genuine interleaving proof: a BMP3xx transfer lands between an SGP40 command and its reply, the conversion
        # wait the driver frees the bus for.
        assert sibling_inside_window(log, _SGP_ADDR), "no sibling transaction landed inside an SGP40 conversion window - the bus was held across the delay"


def test_cross_device_isl29125_and_sgp40_interleave_and_both_stay_correct() -> None:
    # The ISL29125+SGP40 pairing on i2c1: the ISL is register-addressed while the SGP40 speaks a raw
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

    with FastAsyncSleep():
        run(_gather(isl_loop(), sgp_loop()))

    assert len(isl_results) == isl_iterations
    assert all(counts == (0x2000, 0x1800, 0x1000) for counts in isl_results)
    assert snapshots == [bytes(3)] * isl_iterations  # the seeded post-reset CONFIG1-3, never torn
    assert _register_reads_unbroken(list(fake_bus.log), _ISL_ADDR) == 3 * isl_iterations  # status, snapshot and counts, each atomic
    assert sgp_results == [0x8000] * sgp_iterations
    assert sibling_inside_window(fake_bus.log, _SGP_ADDR), "no sibling transaction landed inside an SGP40 conversion window - the bus was held across the delay"


# ---------------------------------------------------------------------------
# 2. General-call broadcast hazard: a true I2C general call landing concurrently with a sibling's
#    own multi-step read must not corrupt or interrupt it. A BMP3xx alone on its bus is checked on
#    silicon: tests_hardware/device_scripts/bmp3xx_alone_survives_a_general_call.py.
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

    with FastAsyncSleep():
        run(_gather(bmp_loop(), reset_loop()))

    assert len(bmp_results) == bmp_iterations
    for pressure, temperature in bmp_results:
        assert abs(pressure - _BMP_EXPECTED_PRESSURE_HPA) < 1e-6
        assert abs(temperature - BMP_EXPECTED_TEMPERATURE) < 1e-6

    general_calls = [entry for entry in fake_bus.log if entry[0] == "writeto" and entry[1] == _GENERAL_CALL_ADDR]
    assert len(general_calls) == reset_count
    assert all(entry[2] == b"\x06" for entry in general_calls)


def test_sgp40_general_call_reset_does_not_disturb_a_concurrent_isl29125_read() -> None:
    # The general-call broadcast hazard again, this time against the sibling that actually shares
    # a bus with the SGP40 where a TOML pairs them (SPECIFICATION.md Part C.8's own standing note).
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

    with FastAsyncSleep():
        run(_gather(isl_loop(), broadcaster()))

    assert all(counts == (0x2000, 0x1800, 0x1000) for counts in results)
    assert any(entry[0] == "writeto" and entry[1] == 0x00 for entry in fake_bus.log), "the general call never fired - this test isn't exercising the hazard"


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

    async def bounded() -> None:
        try:
            await asyncio.wait_for(_gather(isl_loop(), sgp_loop()), _ISOLATION_BOUND_S)
        except asyncio.TimeoutError:
            raise AssertionError("the shared I2C lock was not released after the SGP40's EIO - the ISL29125 loop never finished") from None

    with FastAsyncSleep():
        run(bounded())

    assert not i2c.bus_lock.locked(), "the SGP40's EIO left the shared I2C lock held"
    assert len(isl_results) == isl_iterations
    assert all(counts == (0x2000, 0x1800, 0x1000) for counts in isl_results), "SGP40's own bus fault corrupted a concurrent ISL29125 read"
    assert sgp_errors == sgp_attempts, f"expected every faulted SGP40 call to raise, got {sgp_errors}/{sgp_attempts}"


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

    with FastAsyncSleep():
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

    with FastAsyncSleep():
        run(_gather(bmp_loop(), sgp_loop()))
    assert bmp_errors == [5]  # one EIO, then the device answers again
    log = list(fake_bus.log)  # a snapshot of the ring log, oldest first
    stop = log.index(("writeto", _BMP_ADDR, b"", True))
    assert log[stop - 1][0:2] == ("writeto", _BMP_ADDR), "the STOP follows the short write at once"


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
        if isinstance(instance, BMP3XX_I2C):
            with FastAsyncSleep():
                run(instance.setup())
            fake(i2c).registers[(address, 0x03)] = bytearray([0x00])  # STATUS not ready: the poll yields

            def after(i2c: I2C = i2c, address: int = address) -> None:  # bound now: the loop moves on
                fake(i2c).registers[(address, 0x03)] = bytearray([0x10 | 0x60])

        adapter.seed(fake(i2c), address, 1)
        with FastAsyncSleep():
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

    with FastAsyncSleep():
        run(scenario())
    assert_no_transfer_inside_the_recovery(fake_bus, marks[0])


# @tunable l1.bus_hazard_multi_device_host_stall_ms = 60
_HOST_STALL_MS = 60  # a stall past asy_i2c_driver's 50 ms SCL-release bound


def test_a_host_stall_inside_a_stretched_clear_does_not_read_as_a_held_clock() -> None:
    # The planted slave stretches for a count of reads, so the recovery must judge it in poll rounds: a host
    # stall past the driver's 50 ms SCL-release bound, landing inside the first wait, still clears the bus.
    i2c = make_i2c(1)
    hold_sda_through_a_stretched_clear(i2c, pulses=i2c_const("_CLEAR_PULSES") + 1, host_stall_ms=_HOST_STALL_MS)
    status, _mark = run(recover_marking_the_clear(i2c))
    assert status == i2c_const("_REC_SDA_LOW") | i2c_const("_REC_SDA_STUCK"), f"a host stall read as a held clock: status {status}"


# ---------------------------------------------------------------------------
# 3b. The participant rungs mid-traffic (SPECIFICATION.md C.7, C.8): each chip's own recovery command lands at
# every timing offset into its siblings' read loops on a shared i2c1 (SCD30, SGP40, ISL29125); every
# sibling read stays valid, through the catalog adapters' own corruption checks.
# ---------------------------------------------------------------------------

_RUNG_OFFSETS = 6  # as many offsets as each loop has reads, the catalog scenarios' own default
_SHARED_I2C1 = (("scd30", _SCD_ADDR), ("sgp40", _SGP_ADDR), ("isl29125", _ISL_ADDR))
_scratch = TmpScratch("bus_hazard_multi_device")


def test_an_scd30_soft_reset_mid_read_leaves_every_sibling_read_valid() -> None:
    # The SCD30's participant rung is its soft reset (0xD304, Interface Description 1.4.10); its 2.5 s restart
    # wait runs outside the bus lock, so the siblings keep reading through it.
    def scenario(offset: int) -> None:
        i2c, instances = _shared_i2c1()
        scd30 = instances["scd30"]
        assert isinstance(scd30, SCD30_I2C)
        with FastAsyncSleep():
            run(_rung_beside_sibling_reads(i2c, instances, ("sgp40", "isl29125"), scd30.reset, offset))
        to_scd = [entry for entry in fake(i2c).log if entry[0] == "writeto" and entry[1] == _SCD_ADDR]
        assert to_scd == [("writeto", _SCD_ADDR, b"\xd3\x04", True)], to_scd

    _across_offsets(scenario)


def test_sgp40_heater_off_does_not_disturb_a_concurrent_scd30_read_loop() -> None:
    # The SGP40's participant rung, 0x3615 to 0x59 alone (datasheet Table 14), beside the SCD30 and ISL29125 loops.
    def scenario(offset: int) -> None:
        i2c, instances = _shared_i2c1()
        sgp40 = instances["sgp40"]
        assert isinstance(sgp40, SGP40_I2C)
        with FastAsyncSleep():
            run(_rung_beside_sibling_reads(i2c, instances, ("scd30", "isl29125"), sgp40.turn_heater_off, offset))
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

    with FastAsyncSleep():
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
    # through the reader's ladder (one W DEVICE_RECOVERY) beside the SCD30 and SGP40 loops on the shared i2c1.
    def scenario(offset: int) -> None:
        i2c, instances = _shared_i2c1()
        reader = ISL29125_Reader(i2c, 15, cfg_path=_scratch.dir())
        seed_isl_ready(i2c, _ISL_ADDR)
        run(reader.setup())
        fake(i2c).log.clear()
        reader._err_cnt_internal = 2  # the streak at the participant rung

        async def rung() -> None:
            await reader._climb_ladder()

        with FastAsyncSleep():
            run(_rung_beside_sibling_reads(i2c, instances, ("scd30", "sgp40"), rung, offset))
        log = run(reader.get_error_counter())["ISL29125"]
        recoveries = [i for i in range(len(log["ErrNum"])) if log["ErrType"][i] == "W" and log["ErrNum"][i] == code("W", "DEVICE_RECOVERY")]
        assert len(recoveries) == 1 and log["ErrType"].count("E") == 0, log
        writes = [entry[2] for entry in fake(i2c).log if entry[0] == "writeto" and entry[1] == _ISL_ADDR and entry[3]]
        assert any(w[:1] == b"\x01" and len(w) == 4 for w in writes), f"no whole CONFIG1-3 burst: {writes}"
        assert any(w[:1] == b"\x04" for w in writes), f"the thresholds were not re-armed: {writes}"  # auto-range's thresholds
        assert bytes(fake(i2c).registers[(_ISL_ADDR, 0x01)]) == reader._isl.encode_shadow(), "the chip's CONFIG1-3 differ from the shadow"

    _across_offsets(scenario)


def test_an_isl29125_interrupt_rearm_mid_read_leaves_every_sibling_read_valid() -> None:
    # The dead-line rung: five periodic-only range decisions warn once and re-arm the interrupt (CONFIG1-3 and the
    # thresholds re-written) beside the SCD30 and SGP40 loops on the shared i2c1; every sibling read stays valid.
    def scenario(offset: int) -> None:
        i2c, instances = _shared_i2c1()
        reader = ISL29125_Reader(i2c, 15, cfg_path=_scratch.dir())
        seed_isl_ready(i2c, _ISL_ADDR)
        run(reader.setup())
        fake(i2c).log.clear()

        async def rung() -> None:
            for _ in range(5):
                await reader._note_decision_source(threshold_fired=False)

        with FastAsyncSleep():
            run(_rung_beside_sibling_reads(i2c, instances, ("scd30", "sgp40"), rung, offset))
        log = run(reader.get_error_counter())["ISL29125"]
        assert [(log["ErrType"][i], log["ErrNum"][i]) for i in range(len(log["ErrNum"])) if log["ErrType"][i] != "N"] == [("W", code("W", "ISL_PERIODIC_ONLY"))], log
        writes = [entry[2] for entry in fake(i2c).log if entry[0] == "writeto" and entry[1] == _ISL_ADDR and entry[3]]
        assert [w for w in writes if w[:1] == b"\x01" and len(w) == 4], f"no whole CONFIG1-3 burst: {writes}"
        assert any(w[:1] == b"\x04" for w in writes), f"the thresholds were not re-armed: {writes}"
        assert bytes(fake(i2c).registers[(_ISL_ADDR, 0x01)]) == reader._isl.encode_shadow(), "the chip's CONFIG1-3 differ from the shadow"

    _across_offsets(scenario)


# ---------------------------------------------------------------------------
# 4. Parallel sessions: multiple concurrent CALLERS hitting the SAME device instance, as opposed to
# different devices sharing a bus above, must never scramble each other's commands or reads: the device
# session serializes the callers, and each one's inputs are staged inside it (SPECIFICATION.md Part C.8).
# ---------------------------------------------------------------------------


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

    with FastAsyncSleep():
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
    # Every catalog driver's own default, read from the driver itself, never a hand-kept copy of it.
    for driver, adapter in I2C_HAZARD_CATALOG.items():
        address = adapter.default_address(make_i2c(1))
        assert not is_reserved(address), f"{driver}'s own default address {address:#x} falls inside a reserved I2C range"


# SPI: a real FRAM_SPI, whose block session runs each transfer synchronously under the bus lock, beside another
# device's async session on one bus. The generated TOML-driven scheme cannot produce this shape (every device TOML
# puts the FRAM alone on spi0); it is what "future multi-device SPI compatibility" has to mean concretely.


def test_spi_async_and_synchronous_sessions_share_one_bus_without_cs_overlap() -> None:
    manager, chip = make_fram_manager()  # the FRAM on CS 1, as every FRAM-backed test builds it
    fram = manager.fram
    bus = fram._spidev.spi
    async_device = SPIDevice(bus, 6)
    assert run(fram.setup()) is True
    run(async_device.setup())
    chip.memory[0:4] = b"\x11\x22\x33\x44"
    rounds = 12
    overlap_observed = False
    async_done = fram_done = 0
    reads: list[bytes] = []

    async def async_worker() -> None:
        nonlocal async_done
        for _ in range(rounds):
            async with async_device:
                await async_device.write(_NEIGHBOUR_BYTE)
                await asyncio.sleep(0)  # its CS stays asserted across a scheduler turn
            async_done += 1

    async def fram_worker() -> None:
        # Only FRAM_SPI.__aenter__ taking the bus lock keeps this block out of the other device's CS window.
        nonlocal overlap_observed, fram_done
        buf = bytearray(4)
        for _ in range(rounds):
            async with fram:
                overlap_observed = overlap_observed or async_device._cs_pin.value() == async_device._cs_active_value
                fram._read_address(0, buf)
            reads.append(bytes(buf))
            fram_done += 1
            await asyncio.sleep(0)

    run(_gather(async_worker(), fram_worker()))
    assert not overlap_observed, "the FRAM's block session ran while another device held its CS asserted"
    assert (async_done, fram_done) == (rounds, rounds)
    assert reads == [b"\x11\x22\x33\x44"] * rounds
    assert async_device._cs_pin.value() == 1  # both back to inactive afterwards
    assert fram._spidev._cs_pin.value() == 1
    assert not bus.bus_lock.locked()


def test_spi_synchronous_session_never_leaves_the_bus_locked_when_a_transfer_raises() -> None:
    # Fault isolation across the two session styles: an rx overrun inside the FRAM's block session must not strand
    # the shared lock or the other device's access to the bus.
    manager, chip = make_fram_manager()
    fram = manager.fram
    bus = fram._spidev.spi
    neighbour = SPIDevice(bus, 6)
    assert run(fram.setup()) is True
    run(neighbour.setup())
    chip.rx_overrun = True
    chip.opcodes = []

    async def neighbour_writes() -> None:
        async with neighbour:
            await neighbour.write(_NEIGHBOUR_BYTE)

    async def scenario() -> bool:
        raised = False
        try:
            async with fram:
                fram._read_address(0, bytearray(32))  # 32+ bytes: the DMA path, the only one that can raise
        except OSError:
            raised = True
        try:
            await asyncio.wait_for(neighbour_writes(), _ISOLATION_BOUND_S)
        except asyncio.TimeoutError:
            raise AssertionError("the shared SPI lock was not released after the FRAM's overrun - the neighbour never wrote") from None
        return raised

    assert run(scenario())
    assert chip.opcodes == [_OPCODE_READ, _NEIGHBOUR_BYTE[0]], f"the neighbour's write did not reach the bus: {chip.opcodes}"
    assert fram._spidev._cs_pin.value() == 1
    assert not bus.bus_lock.locked()
    assert not fram.session_lock.locked()


# ---------------------------------------------------------------------------
# 6. A commanded shutdown's hazards: the whole-chip FRAM erase against chunk operations in flight and other callers
#    of its bus, a sensor task cancelled inside its session, and a config file under a concurrent reader.
# ---------------------------------------------------------------------------

_CHUNKS = ((24, CRC16), (12, CRC8), (40, CRC16))  # payload size and CRC of each chunk the erase rigs allocate
_CHUNK_OWNERS = ("SYSTEM", "WIFI", "NTP")
_ERASE_OFFSETS = range(0, 100, 10)  # turns the write and the read get before the erase starts: both end by turn 87
_NEIGHBOUR_BYTE = b"\xa5"  # another device's traffic on the FRAM's bus: no MB85RS opcode, so the chip fake ignores it
_CANCEL_OFFSETS = 40  # scheduler turns into the SGP40's setup and measurement; the cycle ends at 26
_COUNT_SCHEMA: "ConfigSchema" = (("Count", "int", 7, 0, 100, None),)


class _EraseWire(FakeMB85RS64V):
    # The FRAM fake checking each write as it is clocked, in fixed-size state (a 256 KB erase is over 5,000 CS cycles):
    # WREN RDSR WRITE, then WRDI RDSR, with no other cycle inside, the part's header width, and per pass: pass 1 one-byte
    # status writes (addresses kept), pass 2 256-byte units ascending from 0. A cycle between two writes is foreign.
    HEADER = 3  # the WRITE opcode and a 2-byte address (MB85RS64V DS501-00015 p.9)

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self.erase_pass = 0  # 0 unchecked, 1 the erase's pass 1, 2 its pass 2
        self.unit = _fram_const("asy_fram_manager", "_ERASE_UNIT")
        self.status_writes: list[int] = []
        self.next_unit = 0
        self.faults = 0
        self.foreign = 0
        self._ring = bytearray(3)  # the opcodes of the last three cycles
        self._closing = 0  # cycles a write still owes: WRDI, then RDSR
        self._header = 0
        self._target = 0

    def _check_write(self, length: int) -> None:
        if bytes(self._ring) != bytes((_OPCODE_WREN, _OPCODE_RDSR, _OPCODE_WRITE)) or self._header != self.HEADER:
            self.faults += 1
        if self.erase_pass == 1 and length == 1:
            self.status_writes.append(self._target)
        elif self.erase_pass == 2 and length == self.unit and self._target == self.next_unit:
            self.next_unit += self.unit
        else:
            self.faults += 1
        self._closing = 2

    def _observe(self, data: bytes) -> None:
        if self._pending_op == _OPCODE_WRITE:  # the data phase of the cycle a WRITE opened
            self._check_write(len(data))
            return
        opcode = data[0]
        if self._closing:
            if opcode != (_OPCODE_WRDI if self._closing == 2 else _OPCODE_RDSR):
                self.faults += 1
            self._closing -= 1
        elif opcode not in (_OPCODE_WREN, _OPCODE_RDSR, _OPCODE_WRITE):
            self.foreign += 1
        if opcode == _OPCODE_WRITE:
            self._header = len(data)
            self._target = self._decode_addr(data)
        self._ring[0], self._ring[1], self._ring[2] = self._ring[1], self._ring[2], opcode

    def write(self, buf: object) -> None:
        if self.erase_pass:
            self._observe(bytes(buf))  # type: ignore[call-overload]
        super().write(buf)


class _EraseWireMB85RS2MTA(_EraseWire):
    # The 256 KB part: its identification (MB85RS2MTA DS501-00032 p.10) and a 3-byte address (p.9).
    SIZE = 0x40000
    RDID = bytes([0x04, 0x7F, 0x48, 0x03])
    HEADER = 4


def _across_offsets(scenario: "Callable[[int], None]") -> None:
    failures = []
    for offset in range(_RUNG_OFFSETS):
        try:
            scenario(offset)
        except AssertionError as e:
            failures.append(f"offset={offset}: {e}")
    assert not failures, f"{len(failures)}/{_RUNG_OFFSETS} timing offset(s) reproduced a hazard: {failures}"


def _arm_wire(manager: "FRAMManager", chip: _EraseWire) -> "Callable[[], None]":
    # Starts the check at pass 1 and returns erase_chip()'s step_done, which turns it to pass 2 after the last chunk.
    steps = [0]

    def step_done() -> None:
        steps[0] += 1
        if steps[0] == len(manager._chunks):
            chip.erase_pass = 2

    chip.erase_pass = 1
    return step_done


def _assert_recovery_between(i2c: I2C, address: int, trigger: bytes) -> None:
    # The second half ends with the transaction's last read (BMP3XX: the data burst after its STATUS polls).
    log = list(fake(i2c).log)  # a snapshot of the ring log, oldest first
    first = log.index(("writeto", address, trigger, True))
    init = next(i for i in range(first, len(log)) if log[i][0] == "init")
    last = max(i for i in range(first + 1, len(log)) if log[i][0] == "readfrom_into" and log[i][1] == address)
    assert first < init < last, f"the recovery did not land between the two halves: {log[first : last + 1]}"


def _blocks(chip: _EraseWire, chunk: "FRAMChunk") -> "list[bytes]":
    span = chunk._block_addr[1] - chunk._block_addr[0]
    return [bytes(chip.memory[addr : addr + span]) for addr in chunk._block_addr]


async def _cancel_sgp40_after(i2c: I2C, isl: ISL29125_I2C, sgp: SGP40_I2C, turns: int) -> "tuple[bool, bool, bool]":
    # Cancels the SGP40's setup and measurement `turns` turns in, an ISL29125 read queued behind whatever it holds;
    # returns which locks the SGP40 held at the cancel and whether its cycle had already ended.
    cycle = asyncio.create_task(_sgp40_setup_and_measure(sgp))
    for _ in range(turns):
        await asyncio.sleep(0)
    held_bus, held_device, ended = i2c.bus_lock.locked(), sgp._i2c_sgp40.session_lock.locked(), cycle.done()
    sibling = asyncio.create_task(isl.read_counts())
    await cancel(cycle)
    assert not i2c.bus_lock.locked(), f"turns={turns}: the bus lock outlived the cancelled session"
    assert not sgp._i2c_sgp40.session_lock.locked(), f"turns={turns}: the SGP40's session lock outlived its cancel"
    assert sgp._command_buffer is sgp._default_command_buffer, f"turns={turns}: the measure command stayed staged"
    assert await sibling == (0x2000, 0x1800, 0x1000), f"turns={turns}: the sibling's read after the cancel"
    return held_bus, held_device, ended


async def _erase_in_flight(manager: "FRAMManager", chip: _EraseWire, chunks: "list[FRAMChunk]", turns: int) -> "list[object] | None":
    # The shutdown's quiesce, then the erase, started `turns` scheduler turns into a write of chunk 0 and a read of
    # chunk 1 (each begun once it holds its chunk's lock); a later write and read, the chip's own probe and another
    # device on its bus run beside the erase. None: both finished before the erase started.
    written, kept = chunks[0], chunks[1]
    writer = asyncio.create_task(written.write(bytes([0x5A]) * written.size))
    reader = asyncio.create_task(kept.read())
    for _ in range(turns):
        await asyncio.sleep(0)
    if writer.done() and reader.done():
        await writer
        await reader
        return None
    begun = [written._op_lock.locked() or writer.done(), kept._op_lock.locked() or reader.done()]
    both_in_flight = begun == [True, True] and not writer.done() and not reader.done()
    blocks = _blocks(chip, written)
    torn_if_cut = blocks[0] != blocks[1]
    await manager.quiesce(lambda: None)
    settled = [writer.done(), reader.done()]  # read as quiesce() returns: it waited out every operation begun
    idle = bytes([_fram_const("asy_fram_manager", "_STATUS_IDLE")]) * 2
    whole = all(_blocks(chip, chunk)[0] == _blocks(chip, chunk)[1] and _blocks(chip, chunk)[0][-2:] == idle for chunk in chunks)
    finished = [await writer is True, await reader == bytearray(bytes([2]) * kept.size)]
    neighbour = SPIDevice(manager.fram._spidev.spi, 6)
    await neighbour.setup()
    stop = asyncio.Event()

    async def probe() -> None:  # the chip watch's probe: both FRAM locks, one RDID cycle
        while not stop.is_set():
            assert await manager.fram.verify_present() is True
            await asyncio.sleep(0)

    async def other_device() -> None:  # the bus lock only, one CS cycle per session
        while not stop.is_set():
            async with neighbour:
                await neighbour.write(_NEIGHBOUR_BYTE)

    later = [asyncio.create_task(written.write(bytes(written.size))), asyncio.create_task(kept.read())]
    callers = [asyncio.create_task(probe()), asyncio.create_task(other_device())]
    erased = await manager.erase_chip(_arm_wire(manager, chip))
    chip.erase_pass = 0
    stop.set()
    refused = [await later[0], await later[1]]
    for caller in callers:
        await caller
    return [begun, both_in_flight, torn_if_cut, settled, finished, whole, refused, erased]


def _erase_rig(part: "type[_EraseWire]") -> "tuple[FRAMManager, _EraseWire, list[FRAMChunk]]":
    # A set-up manager over `part` with three chunks of different sizes and CRCs, each written once (status bytes idle).
    manager, chip = make_fram_manager(part.SIZE, part)
    assert isinstance(chip, _EraseWire)
    assert run(manager.setup()) is True
    chunks = []
    for n, (size, crc) in enumerate(_CHUNKS):
        chunk = manager.get_chunk(size, crc=crc(), owner=_CHUNK_OWNERS[n])
        assert chunk is not None
        assert run(chunk.write(bytes([n + 1]) * size)) is True
        chunks.append(chunk)
    return manager, chip, chunks


def _fram_const(module: str, name: str) -> int:
    # A folded const() of src/<module>.py, read from its source.
    value = src_const(f"src/{module}.py", name)
    assert isinstance(value, int), (name, value)
    return value


async def _gather(a: "Coroutine[object, object, object]", b: "Coroutine[object, object, object]") -> None:
    # asyncio.gather() itself returns a Future, not a Coroutine - mypy rejects passing it straight
    # to run() (which declares a Coroutine[...] parameter), same as test_asy_i2c_driver.py's own
    # scenario()-wrapping convention for this exact call shape.
    await asyncio.gather(a, b)


async def _read_while_storing(store: ConfigManager, path: str) -> "tuple[int, int, set[str | None]]":
    # Polls the file on every scheduler turn while eight writes flush and the reset's delete removes it: the looks,
    # how many found a text no write stored, and every distinct text (None: no file).
    wholes = {json.dumps({"Count": count}) for count in range(9)}
    seen: set[str | None] = set()
    counts = [0, 0]
    done = asyncio.Event()

    async def reader() -> None:
        while not done.is_set():
            try:
                with open(path) as f:
                    text: str | None = f.read()
            except OSError as e:
                if e.errno != errno.ENOENT:  # only an absent file is a state; any other failure ends the scenario
                    raise
                text = None
            counts[0] += 1
            if text is not None and text not in wholes:
                counts[1] += 1
            seen.add(text)
            await asyncio.sleep(0)

    assert await store.setup() is True
    task = asyncio.create_task(reader())
    for count in range(1, 9):
        assert (await store.write_config({"Count": count}))[0] is True
        await store.flush_pending()
    assert await store.delete_file() is True
    await asyncio.sleep(0)
    done.set()
    await task
    return counts[0], counts[1], seen


def _record_write_statuses(manager: "FRAMManager") -> "list[int]":
    # Every set_values_sync() status from now on, OR-ed into the one element returned.
    seen = [0]
    real = manager.fram.set_values_sync

    def recording(buf: "bytes | bytearray | memoryview", addr_start: int) -> int:
        status = real(buf, addr_start)
        seen[0] |= status
        return status

    manager.fram.set_values_sync = recording  # type: ignore[method-assign]
    return seen


async def _recover_between_halves(i2c: I2C, target: int, trigger: bytes, read: "Coroutine[object, object, None]", after_recovery: "Callable[[], None] | None" = None) -> None:
    # Runs `read`, and i2c.recover() the moment `trigger` (its first half's write) has reached the bus.
    bus = fake(i2c)
    real_writeto = bus.writeto
    fired = asyncio.Event()

    def watching(address: int, buf: object, stop: bool = True) -> int:
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


def _register_reads_unbroken(log: "list[tuple[object, ...]]", address: int) -> int:
    # Every no-stop register-address write to `address` is followed at once by its readfrom_into, never by
    # a sibling's transfer between the two. Returns how many such reads the log holds.
    count = 0
    for i, entry in enumerate(log):
        if entry[0] == "writeto" and entry[1] == address and not entry[3] and entry[2]:
            assert i + 1 < len(log) and log[i + 1][0:2] == ("readfrom_into", address), f"a transfer landed inside a register read at log index {i}: {log[i : i + 2]}"
            count += 1
    return count


async def _rung_beside_sibling_reads(i2c: I2C, instances: "dict[str, object]", siblings: "tuple[str, ...]", rung: "Callable[[], Coroutine[object, object, object]]", offset: int) -> None:
    for driver, address in _SHARED_I2C1:
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


def _sgp40_measure_command(temperature: int, relative_humidity: int) -> bytes:
    # Independent oracle from the SGP40 datasheet, not the driver's tick helpers: command 0x260F, then the
    # RH word and the T word each with its CRC-8 (Table 9); ticks per Table 10's formulas, rounded half up,
    # which its own 50 % -> 0x8000 row requires; CRC-8 poly 0x31, init 0xFF (Table 7).
    rh_ticks = (relative_humidity * 65535 * 2 + 100) // 200
    t_ticks = ((temperature + 45) * 65535 * 2 + 175) // 350
    rh_word = bytes([rh_ticks >> 8, rh_ticks & 0xFF])
    t_word = bytes([t_ticks >> 8, t_ticks & 0xFF])
    return b"\x26\x0f" + rh_word + bytes([crc8(rh_word)]) + t_word + bytes([crc8(t_word)])


async def _sgp40_setup_and_measure(sgp: SGP40_I2C) -> "int | None":
    await sgp.setup()
    return await sgp.measure_raw(temperature=25, relative_humidity=50)


def _shared_i2c1() -> "tuple[I2C, dict[str, object]]":
    i2c = make_i2c(1)
    return i2c, {driver: I2C_HAZARD_CATALOG[driver].construct(i2c, address) for driver, address in _SHARED_I2C1}


def _status_bytes() -> "list[int]":
    # Each chunk is two equal blocks [payload][CRC][status 1][status 2], allocated upward from 0, in request order.
    status_bytes = _fram_const("asy_fram_manager", "_NUM_STATUS_BYTES")
    expected = []
    top = 0
    for size, crc in _CHUNKS:
        for _block in range(2):
            top += size + crc().length() + status_bytes
            expected += list(range(top - status_bytes, top))
    return expected


def test_the_erase_writes_each_status_byte_then_every_unit_once_ascending_at_the_parts_address_width() -> None:
    # Pass 1 writes exactly the status bytes of each allocated block, pass 2 every 256-byte unit of the chip once,
    # ascending from 0; every WRITE carries the part's address width and no write status bit is ever set.
    for part in (_EraseWire, _EraseWireMB85RS2MTA):
        manager, chip, _chunks = _erase_rig(part)
        statuses = _record_write_statuses(manager)
        assert run(manager.erase_chip(_arm_wire(manager, chip))) is True
        chip.erase_pass = 0
        assert (chip.faults, chip.foreign) == (0, 0), part
        assert sorted(chip.status_writes) == _status_bytes(), (part, chip.status_writes)
        assert chip.next_unit == part.SIZE, (part, chip.next_unit)
        assert statuses[0] == 0, f"a write status {statuses[0]:#x} (_SV_BAD_RANGE is {_fram_const('asy_fram_driver', '_SV_BAD_RANGE'):#x})"


def test_an_erase_lets_a_write_and_a_read_in_flight_finish_whole_refuses_later_ones_and_holds_each_unit_whole() -> None:
    # At offsets into a chunk write and a chunk read: each one begun finishes, each chunk's two copies end equal and
    # idle, one not begun and later ones are refused, and each erase write's five CS cycles stay contiguous while the
    # chip's probe and another device on its bus land between them (the unit holds both FRAM locks).
    failures = []
    in_flight = torn = 0
    for turns in _ERASE_OFFSETS:
        manager, chip, chunks = _erase_rig(_EraseWire)
        facts = run(_erase_in_flight(manager, chip, chunks, turns))
        if facts is None:
            break
        begun, both_in_flight, torn_if_cut, settled, finished, whole, refused, erased = facts
        in_flight += bool(both_in_flight)
        torn += bool(torn_if_cut)
        wire = [chip.faults, chip.foreign > 0, chip.next_unit, sorted(chip.status_writes) == _status_bytes()]
        if [settled, finished, whole, refused, erased, wire] != [begun, begun, True, [False, None], True, [0, True, _EraseWire.SIZE, True]]:
            failures.append(f"turns={turns}: begun={begun} settled={settled} finished={finished} whole={whole} refused={refused} erased={erased} wire={wire}")
    else:
        raise AssertionError(f"the write and the read were still in flight after {max(_ERASE_OFFSETS)} turns")
    assert not failures, failures
    assert in_flight > 0, "no offset caught the write and the read both in flight"
    assert torn > 0, "no offset caught the write between its two copies"


def test_a_sensor_cancelled_inside_its_session_leaves_the_bus_free_and_the_sibling_read_valid() -> None:
    # The shutdown cancels each supervised task where it waits: the SGP40 at every turn of its setup and measurement,
    # inside its bus session (the presence probe) and its device session (the measurement wait) among them.
    held = set()
    for turns in range(_CANCEL_OFFSETS):
        i2c = make_i2c(1)
        isl = ISL29125_I2C(i2c)
        sgp = SGP40_I2C(i2c)
        seed_isl_ready(i2c)
        fake(i2c).attached.add(_SGP_ADDR)
        serial, self_test = _sgp_word(0x0000) + _sgp_word(0x1234) + _sgp_word(0x5678), _sgp_word(0xD400)
        fake(i2c).read_queue_by_address[_SGP_ADDR] = [serial, self_test, _sgp_word(0x8000)]
        with FastAsyncSleep():
            held_bus, held_device, ended = run(_cancel_sgp40_after(i2c, isl, sgp, turns))
        if ended:
            break
        held.add((held_bus, held_device))
    else:
        raise AssertionError(f"the SGP40's cycle was still running after {_CANCEL_OFFSETS} turns")
    assert (True, True) in held, f"no cancel landed inside the bus session: {held}"
    assert (False, True) in held, f"no cancel landed inside the device session alone: {held}"


def test_a_concurrent_reader_never_sees_a_config_file_half_written_or_half_deleted() -> None:
    # The store's writes and its delete have no suspension point inside them: every look finds one stored text whole,
    # or no file once the reset deleted it.
    path = _scratch.dir("store") + "config_HAZARD.cfg"
    looks, torn, seen = run(_read_while_storing(ConfigManager(path, _COUNT_SCHEMA, "HAZARD"), path))
    assert torn == 0, f"{torn} of {looks} looks found a text no write stored: {seen}"
    assert None in seen, "the reader never saw the deleted file"
    assert len(seen) >= 3, f"the reader saw too few states to have raced anything: {seen}"


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
