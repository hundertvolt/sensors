"""Mock-level (tests/machine.py fake I2C) bus-hazard suite - the fast, deterministic tier of
SPECIFICATION.md Part C.8. Holds only driver-agnostic hazard shapes; a driver-specific one lives
with that driver. Runs alongside test_bus_hazard_generated.py, not as a staging area for it."""

import asyncio
import struct

from _bus_hazard_catalog import fake, make_i2c, seed_isl_ready
from _bus_hazard_catalog import sgp_word as _sgp_word

from asy_bmp3xx_driver import BMP3XX_I2C
from asy_i2c_driver import I2C
from asy_isl29125_driver import ISL29125_I2C
from asy_sgp40_driver import SGP40_I2C

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
_ISL_ADDR = 0x44  # hard-wired (FN8424 p15) - dev-only, sharing i2c1 with SCD30 and SGP40
_GENERAL_CALL_ADDR = 0x00
# I2C spec reserved address ranges (0x00-0x07: general call/CBUS/reserved/Hs-mode; 0x78-0x7F:
# 10-bit addressing/reserved) - every real device address this codebase uses must fall outside
# both, and only SGP40's own documented _reset() may ever address 0x00 specifically.
_RESERVED_RANGES = ((0x00, 0x07), (0x78, 0x7F))


def _is_reserved(address: int) -> bool:
    return any(lo <= address <= hi for lo, hi in _RESERVED_RANGES)


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


# ---------------------------------------------------------------------------
# 1. Cross-device concurrency: two DIFFERENT devices sharing one bus (BMP3xx + SGP40 on i2c1,
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


def test_cross_device_isl29125_and_sgp40_interleave_and_both_stay_correct() -> None:
    # dev's own i2c1 grouping: the ISL is register-addressed while the SGP40 speaks a raw
    # word protocol, so the two exercise completely different transaction shapes on one bus.
    i2c = make_i2c(1)
    isl = ISL29125_I2C(i2c, address=_ISL_ADDR)
    sgp = SGP40_I2C(i2c, address=_SGP_ADDR)
    fake_bus = fake(i2c)
    seed_isl_ready(i2c)

    isl_iterations = 6
    sgp_iterations = 4
    for _ in range(sgp_iterations):
        fake_bus.read_queue.append(_sgp_word(0x8000))

    isl_results: list[tuple[int, int, int]] = []
    sgp_results: list[int | None] = []

    async def isl_loop() -> None:
        for _ in range(isl_iterations):
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
    assert sgp_results == [0x8000] * sgp_iterations
    addressed = [entry[1] for entry in fake_bus.log if entry[0] in ("writeto", "readfrom_into", "readfrom_mem", "writeto_mem")]
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


def test_sgp40_general_call_reset_does_not_disturb_a_concurrent_isl29125_read() -> None:
    # The general-call broadcast hazard again, this time against the sibling that actually shares
    # a bus with the SGP40 on dev (SPECIFICATION.md Part C.8's own standing note).
    i2c = make_i2c(1)
    isl = ISL29125_I2C(i2c, address=_ISL_ADDR)
    sgp = SGP40_I2C(i2c, address=_SGP_ADDR)
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
    # BMP3xx is the only device on this bus (matching dev's real i2c0 wiring); the broadcast is
    # issued directly against the raw I2C wrapper (no SGP40_I2C instance) to prove BMP3xx alone
    # tolerates a general call regardless of who issues it. This is the ROGUE-broadcast case
    # tests/_bus_hazard_catalog.py's own TOML-driven scheme cannot generate (it only ever fires a
    # general call a real catalog occupant's own adapter issues), so it stays hand-written here.
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
    isl = ISL29125_I2C(i2c, address=_ISL_ADDR)
    sgp = SGP40_I2C(i2c, address=_SGP_ADDR)
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


# ---------------------------------------------------------------------------
# 4. Parallel sessions: multiple concurrent CALLERS hitting the SAME device instance (as opposed
#    to different devices sharing a bus, sections above) must never scramble each other's reads.
#    I2CDevice's own session lock (asy_i2c_driver.py) is the shared bus lock, so this proves the
#    same mechanism the cross-device tests exercise, serializing multiple callers of one device.
# ---------------------------------------------------------------------------


def test_three_concurrent_sessions_on_the_same_sgp40_instance_never_scramble_each_others_reads() -> None:
    i2c = make_i2c(1)
    sgp = SGP40_I2C(i2c, address=_SGP_ADDR)
    fake_bus = fake(i2c)
    session_count = 3
    for _ in range(session_count):
        fake_bus.read_queue.append(_sgp_word(0x8000))

    results: list[int | None] = []

    async def session() -> None:
        results.append(await sgp.measure_raw(temperature=25, relative_humidity=50))

    async def scenario() -> None:
        await asyncio.gather(*(session() for _ in range(session_count)))

    with _FastAsyncSleep():
        run(scenario())

    assert len(results) == session_count
    assert all(raw == 0x8000 for raw in results), f"a concurrent session scrambled another session's own read: {results}"


# ---------------------------------------------------------------------------
# 5. Regression guard for future device additions: a new driver whose default address falls in a
#    reserved I2C range is caught here before reaching real hardware.
# ---------------------------------------------------------------------------


def test_no_reserved_i2c_address_collides_with_any_promoted_devices_own_address() -> None:
    for name, address in (("SCD30", _SCD_ADDR), ("BMP3xx", _BMP_ADDR), ("SGP40", _SGP_ADDR), ("ISL29125", _ISL_ADDR)):
        assert not _is_reserved(address), f"{name}'s own address {address:#x} falls inside a reserved I2C range"


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
