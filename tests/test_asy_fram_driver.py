import asyncio

from _error_codes import code
from _fram_chip_fake import FakeMB85RS64V

import asy_fram_driver
import asy_spi_driver
from asy_fram_driver import FRAM_SPI
from asy_print_log import PrintLogHistory
from asy_spi_driver import SPI

# Swaps the stateful MB85RS64V chip fake in for the whole process (one test file per scripts/test.sh
# invocation, SPECIFICATION.md Part E.3): asy_spi_driver.SPI.init() resolves `_SPI` as a module global at
# call time, so reassigning it before any bus is constructed needs no per-test patch/restore.
asy_spi_driver._SPI = FakeMB85RS64V  # type: ignore[misc]

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Coroutine
    from typing import Any, TypeVar

    T = TypeVar("T")


def run(coro: "Coroutine[Any, Any, T]") -> "T":  # drives a coroutine to completion for these sync test_* functions
    return asyncio.run(coro)


# @tunable l1.asy_fram_driver_lock_wait_s = 1.0
_LOCK_WAIT_S = 1.0


def make_bus() -> SPI:
    return SPI(0, sck_pin=2, mosi_pin=3, miso_pin=4)


def make_fram(
    max_size: int = 0x2000, *, wp: bool = False, wp_pin: int | None = None,
) -> tuple[FRAM_SPI, FakeMB85RS64V]:
    bus = make_bus()
    fram = FRAM_SPI(bus, 1, logger=PrintLogHistory(name="TESTFRAM"), wp=wp, wp_pin=wp_pin, max_size=max_size)
    chip = fram._spidev.spi._spi
    assert isinstance(chip, FakeMB85RS64V)
    chip.wp_pin = fram._wp_pin  # lets the fake model the datasheet's WP-pin status-register lock
    return fram, chip


async def setup_fram(fram: FRAM_SPI) -> None:
    assert await fram.setup() is True


def _driver_const(name: str) -> int:
    # A const() is not a module attribute on MicroPython: the shipped literal, read from the source.
    with open("src/asy_fram_driver.py") as f:
        for line in f:
            if line.startswith(name + " = const("):
                return int(line.split("const(", 1)[1].split(")", 1)[0], 0)
    raise AssertionError(name + " not found in src/asy_fram_driver.py")


async def _write_one(fram: FRAM_SPI, data: bytes = b"ok", addr: int = 0x20) -> bool:
    async with fram:
        return await fram.set_values(data, addr)


async def _read_then_write(fram: FRAM_SPI) -> "tuple[bool, bool]":
    async with fram:
        return await fram.get_values(bytearray(2), 0), await fram.set_values(b"x", 0)


def _count(fram: FRAM_SPI, entry: int) -> int:
    return list(fram.pr.history).count(entry)


# ---------------------------------------------------------------------------
# setup() - device identification, the fixed RDID byte-order + and/or bug
# ---------------------------------------------------------------------------


def test_get_size_returns_the_configured_max_size() -> None:
    fram, _chip = make_fram(max_size=0x1234)
    assert run(fram.get_size()) == 0x1234


def test_setup_succeeds_with_correct_device_id() -> None:
    fram, _chip = make_fram()
    run(setup_fram(fram))
    assert fram.initialized is True


def test_setup_raises_on_wrong_manufacturer_id() -> None:
    fram, chip = make_fram()
    chip.rdid_response = bytes([0x05, 0x7F, 0x03, 0x02])
    try:
        run(setup_fram(fram))
        message = ""
    except OSError as e:
        message = str(e)
    assert message == "FRAM SPI device not found"
    assert fram.initialized is False


def test_setup_raises_on_wrong_continuation_code() -> None:
    fram, chip = make_fram()
    chip.rdid_response = bytes([0x04, 0x00, 0x03, 0x02])
    try:
        run(setup_fram(fram))
        raised = False
    except OSError:
        raised = True
    assert raised


def test_setup_raises_on_wrong_product_id_with_correct_manufacturer_id() -> None:
    # Regression test for a real bug found during this promotion: the legacy check was `manf_wrong AND
    # prod_wrong`, so a correct manufacturer byte alone made the whole check pass regardless of the byte-
    # order-swapped product ID - silently accepting a different Fujitsu part or a corrupted ID pair.
    fram, chip = make_fram()
    chip.rdid_response = bytes([0x04, 0x7F, 0x99, 0x99])
    try:
        run(setup_fram(fram))
        raised = False
    except OSError:
        raised = True
    assert raised


def test_setup_product_id_byte_order_is_1st_byte_high_2nd_byte_low() -> None:
    # Pins down the exact fix: datasheet order is Product ID 1st byte (0x03, more significant),
    # then 2nd byte (0x02) - swapping them (the original bug) must fail this check.
    fram, chip = make_fram()
    chip.rdid_response = bytes([0x04, 0x7F, 0x02, 0x03])  # swapped vs. the real 0x03, 0x02
    try:
        run(setup_fram(fram))
        raised = False
    except OSError:
        raised = True
    assert raised


def test_setup_succeeds_with_the_256kb_chips_real_device_id() -> None:
    # Real hardware finding: MB85RS2MTA reports product ID bytes 0x48, 0x03 (datasheets/fram/
    # MB85RS2MTA-DS501-00032-3v0-E.pdf p.10) - only passes once the expected product ID is looked
    # up per max_size (_KNOWN_PRODUCT_IDS), not hardcoded to the smaller chip.
    fram, chip = make_fram(max_size=0x40000)
    chip.rdid_response = bytes([0x04, 0x7F, 0x48, 0x03])
    run(setup_fram(fram))
    assert fram.initialized is True


def test_setup_raises_when_configured_size_does_not_match_the_reported_chip() -> None:
    # The real chip present (8KB MB85RS64V's ID) doesn't match the size the driver was configured
    # for (256KB) - must raise rather than silently accept a smaller chip than the caller expects.
    fram, chip = make_fram(max_size=0x40000)
    chip.rdid_response = bytes([0x04, 0x7F, 0x03, 0x02])  # the 8KB chip's real ID, not the 256KB one
    try:
        run(setup_fram(fram))
        raised = False
    except OSError:
        raised = True
    assert raised
    assert fram.initialized is False


def test_setup_raises_when_small_chip_configured_but_256kb_chips_id_reported() -> None:
    # Mismatch in the opposite direction from test_setup_raises_when_configured_size_does_not_match_
    # the_reported_chip: configured for the 8KB chip, but the 256KB chip's real ID is what's present.
    fram, chip = make_fram(max_size=0x2000)
    chip.rdid_response = bytes([0x04, 0x7F, 0x48, 0x03])  # the 256KB chip's real ID, not the 8KB one
    try:
        run(setup_fram(fram))
        raised = False
    except OSError:
        raised = True
    assert raised
    assert fram.initialized is False


def test_setup_raises_when_256kb_configured_size_reports_the_wrong_manufacturer_id() -> None:
    # Mirrors test_setup_raises_on_wrong_manufacturer_id, but for the size-keyed 256KB path -
    # confirms the manufacturer check still runs (and still gates the result) once the expected
    # product ID comes from a dict lookup instead of a single hardcoded module constant.
    fram, chip = make_fram(max_size=0x40000)
    chip.rdid_response = bytes([0x05, 0x7F, 0x48, 0x03])
    try:
        run(setup_fram(fram))
        raised = False
    except OSError:
        raised = True
    assert raised
    assert fram.initialized is False


def test_setup_raises_when_256kb_configured_size_reports_the_wrong_continuation_code() -> None:
    fram, chip = make_fram(max_size=0x40000)
    chip.rdid_response = bytes([0x04, 0x00, 0x48, 0x03])
    try:
        run(setup_fram(fram))
        raised = False
    except OSError:
        raised = True
    assert raised
    assert fram.initialized is False


def test_setup_raises_when_256kb_configured_size_reports_a_garbage_product_id() -> None:
    fram, chip = make_fram(max_size=0x40000)
    chip.rdid_response = bytes([0x04, 0x7F, 0x99, 0x99])
    try:
        run(setup_fram(fram))
        raised = False
    except OSError:
        raised = True
    assert raised
    assert fram.initialized is False


def test_setup_256kb_product_id_byte_order_is_1st_byte_high_2nd_byte_low() -> None:
    # Mirrors test_setup_product_id_byte_order_is_1st_byte_high_2nd_byte_low for the 256KB chip's
    # own real bytes (0x48, 0x03) - the byte-order fix must hold for both entries in
    # _KNOWN_PRODUCT_IDS, not just the one it was originally found against.
    fram, chip = make_fram(max_size=0x40000)
    chip.rdid_response = bytes([0x04, 0x7F, 0x03, 0x48])  # swapped vs. the real 0x48, 0x03
    try:
        run(setup_fram(fram))
        raised = False
    except OSError:
        raised = True
    assert raised
    assert fram.initialized is False


def test_setup_raises_for_a_max_size_with_no_known_product_id() -> None:
    # A max_size that isn't one of this codebase's two known real chips (_KNOWN_PRODUCT_IDS) must
    # raise clearly rather than silently skip the device-ID check.
    fram, chip = make_fram(max_size=0x8000)
    chip.rdid_response = bytes([0x04, 0x7F, 0x03, 0x02])  # a real chip's ID - still must not matter
    try:
        run(setup_fram(fram))
        raised = False
    except ValueError:
        raised = True
    assert raised
    assert fram.initialized is False


def test_setup_raises_for_max_sizes_one_off_from_each_known_size() -> None:
    # Near-miss boundary values, not just wildly-off ones (0x8000 above): one byte below/above each
    # of the two known chip sizes must still be treated as unrecognized, not fuzzily matched.
    for max_size in (0x1FFF, 0x2001, 0x3FFFF, 0x40001):
        fram, chip = make_fram(max_size=max_size)
        chip.rdid_response = bytes([0x04, 0x7F, 0x03, 0x02])
        try:
            run(setup_fram(fram))
            raised = False
        except ValueError:
            raised = True
        assert raised
        assert fram.initialized is False


def test_verify_present_true_for_the_256kb_chip() -> None:
    fram, _chip = make_fram(max_size=0x40000)
    _chip.rdid_response = bytes([0x04, 0x7F, 0x48, 0x03])
    run(setup_fram(fram))

    async def scenario() -> bool:
        return await fram.verify_present()

    assert run(scenario()) is True
    assert fram.initialized is True


def test_verify_present_false_for_the_256kb_chip_after_id_changes() -> None:
    fram, chip = make_fram(max_size=0x40000)
    chip.rdid_response = bytes([0x04, 0x7F, 0x48, 0x03])
    run(setup_fram(fram))
    chip.rdid_response = bytes([0xFF, 0xFF, 0xFF, 0xFF])  # simulated disturbance / device gone

    async def scenario() -> bool:
        return await fram.verify_present()

    assert run(scenario()) is False
    assert fram.initialized is False


def test_a_chip_that_never_identifies_is_asked_id_attempts_times_before_setup_raises() -> None:
    fram, chip = make_fram()
    chip.rdid_response = bytes([0xFF, 0xFF, 0xFF, 0xFF])
    try:
        run(setup_fram(fram))
        message = ""
    except OSError as e:
        message = str(e)
    assert message == "FRAM SPI device not found"
    assert chip.rdid_count == _driver_const("_ID_ATTEMPTS")  # each attempt its own CS cycle
    assert fram.initialized is False
    assert not fram.session_lock.locked()
    assert not fram._bus_lock.locked()


def test_setup_succeeds_when_the_chip_answers_garbage_once_then_its_id() -> None:
    fram, chip = make_fram()
    chip.rdid_once = bytes([0xFF, 0xFF, 0xFF, 0xFF])
    run(setup_fram(fram))
    assert fram.initialized is True
    assert chip.rdid_count == 2
    assert _count(fram, 0x80 + code("W", "FRAM_ID_RETRIED")) == 1
    assert fram.pr._err_count == 1


def test_a_first_time_identification_logs_nothing() -> None:
    fram, chip = make_fram()
    run(setup_fram(fram))
    assert chip.rdid_count == 1
    assert fram.pr._err_count == 0


def test_a_partly_protected_status_register_is_reported_and_writes_refused() -> None:
    # BP1/BP0 01, 10 and 11 protect part or all of the array (MB85RS64V p.11): any of them reads as
    # protected. WPEN alone protects only the status register, so the array stays writable.
    for status in (0x04, 0x08, 0x0C, 0x84):
        fram, chip = make_fram()
        chip.status = status
        run(setup_fram(fram))
        assert run(fram.get_write_protected()) is True, hex(status)
        assert _count(fram, code("E", "FRAM_WP_PARTIAL")) == 1, hex(status)
        assert run(_write_one(fram)) is False, hex(status)
        assert list(fram.pr.history)[-1] == 0x80 + code("W", "FRAM_WRITE_PROTECTED")
        assert bytes(chip.memory[0x20:0x22]) == b"\x00\x00"
    fram, chip = make_fram()
    chip.status = 0x80
    run(setup_fram(fram))
    assert run(fram.get_write_protected()) is False
    assert _count(fram, code("E", "FRAM_WP_PARTIAL")) == 1
    assert run(fram.set_write_protected(value=False)) is True
    assert chip.status == 0x00
    assert run(_write_one(fram)) is True
    assert bytes(chip.memory[0x20:0x22]) == b"ok"


def test_a_fully_set_or_clear_status_register_is_not_reported_as_partial() -> None:
    for status in (0x8C, 0x00):
        fram, chip = make_fram()
        chip.status = status
        run(setup_fram(fram))
        assert fram.pr._err_count == 0, hex(status)


# ---------------------------------------------------------------------------
# get_values / set_values - guards (initialized, lock, range) and real data
# ---------------------------------------------------------------------------


def test_get_values_before_setup_returns_false() -> None:
    fram, _chip = make_fram()

    async def scenario() -> bool:
        return await fram.get_values(bytearray(4), 0)

    assert run(scenario()) is False


def test_get_values_without_outer_lock_returns_false() -> None:
    fram, _chip = make_fram()
    run(setup_fram(fram))

    async def scenario() -> bool:
        return await fram.get_values(bytearray(4), 0)  # no `async with fram:` wrapper

    assert run(scenario()) is False


def test_get_values_out_of_range_returns_false() -> None:
    fram, _chip = make_fram(max_size=0x2000)
    run(setup_fram(fram))

    async def scenario() -> tuple[bool, bool]:
        async with fram:
            neg = await fram.get_values(bytearray(4), -1)
            over = await fram.get_values(bytearray(4), 0x2000 - 2)
        return neg, over

    neg, over = run(scenario())
    assert neg is False
    assert over is False


def test_set_values_before_setup_returns_false() -> None:
    fram, _chip = make_fram()

    async def scenario() -> bool:
        return await fram.set_values(b"x", 0)

    assert run(scenario()) is False


def test_set_values_without_outer_lock_returns_false() -> None:
    fram, _chip = make_fram()
    run(setup_fram(fram))

    async def scenario() -> bool:
        return await fram.set_values(b"x", 0)

    assert run(scenario()) is False


def test_set_values_out_of_range_returns_false() -> None:
    fram, _chip = make_fram(max_size=0x2000)
    run(setup_fram(fram))

    async def scenario() -> tuple[bool, bool]:
        async with fram:
            neg = await fram.set_values(b"x", -1)
            over = await fram.set_values(bytearray(4), 0x2000 - 2)
        return neg, over

    neg, over = run(scenario())
    assert neg is False
    assert over is False


def test_set_values_then_get_values_round_trip() -> None:
    fram, chip = make_fram()
    run(setup_fram(fram))

    async def scenario() -> bytearray:
        async with fram:
            ok = await fram.set_values(b"hello!!!", 0x10)
            assert ok is True
            buf = bytearray(8)
            ok = await fram.get_values(buf, 0x10)
            assert ok is True
        return buf

    result = run(scenario())
    assert result == bytearray(b"hello!!!")
    assert bytes(chip.memory[0x10:0x18]) == b"hello!!!"


# ---------------------------------------------------------------------------
# _write() - write-enable-latch verification (the new bus-disturbance detection)
# ---------------------------------------------------------------------------


def test_write_aborts_and_does_not_touch_memory_when_wren_is_disturbed() -> None:
    fram, chip = make_fram()
    run(setup_fram(fram))
    chip.drop_wren = True  # simulated bus disturbance: WREN opcode never actually latches

    async def scenario() -> bool:
        async with fram:
            return await fram.set_values(b"bad!", 0x00)

    ok = run(scenario())
    assert ok is False
    assert bytes(chip.memory[0x00:0x04]) == b"\x00\x00\x00\x00"  # untouched


def test_write_succeeds_normally_when_wrdi_is_not_disturbed() -> None:
    fram, chip = make_fram()
    run(setup_fram(fram))

    async def scenario() -> bool:
        async with fram:
            return await fram.set_values(b"ok!!", 0x00)

    assert run(scenario()) is True
    assert chip.wel is False  # WRDI cleared it as expected


def test_write_retries_wrdi_once_and_recovers_when_first_wrdi_is_disturbed() -> None:
    fram, chip = make_fram()
    run(setup_fram(fram))
    # WRITE's own datasheet-confirmed WEL auto-clear is disturbed too, so the first (disturbed)
    # WRDI genuinely has something to fail to clear, and the retry genuinely has something to fix.
    chip.disturb_write_autoclear = True
    chip.drop_next_wrdi = 1  # first WRDI attempt is disturbed, the retry is not

    async def scenario() -> bool:
        async with fram:
            return await fram.set_values(b"ok!!", 0x00)

    ok = run(scenario())
    assert ok is True  # the payload write itself still succeeded
    assert bytes(chip.memory[0x00:0x04]) == b"ok!!"
    assert chip.wel is False  # retry recovered the latch


def test_write_reports_data_written_even_if_wrdi_stays_stuck_after_retry() -> None:
    # Leaving WEL asserted is a housekeeping problem, not a "did the payload write happen"
    # problem - a stuck-set WEL after both attempts is only ever warned about, not treated as a
    # failed write (see asy_fram_driver.py's _write()).
    fram, chip = make_fram()
    run(setup_fram(fram))
    chip.disturb_write_autoclear = True  # so WEL genuinely has something to still be stuck at
    chip.drop_next_wrdi = 2  # both the original WRDI and the one retry are disturbed

    async def scenario() -> bool:
        async with fram:
            return await fram.set_values(b"ok!!", 0x00)

    ok = run(scenario())
    assert ok is True
    assert bytes(chip.memory[0x00:0x04]) == b"ok!!"
    assert chip.wel is True  # left stuck, but reported (not silently dropped)


def record_events(fram: FRAM_SPI) -> "list[tuple[object, ...]]":
    recorded: list[tuple[object, ...]] = []
    original = fram.pr.evt

    def capture(*args: object, sep: str = " ", end: str = "\n") -> None:
        recorded.append(args)
        original(*args, sep=sep, end=end)

    fram.pr.evt = capture  # type: ignore[method-assign]
    return recorded


def test_a_write_lands_when_only_the_first_wren_is_dropped() -> None:
    fram, chip = make_fram()
    run(setup_fram(fram))
    chip.drop_next_wren = 1
    chip.opcodes = []
    events = record_events(fram)
    assert run(_write_one(fram)) is True
    assert bytes(chip.memory[0x20:0x22]) == b"ok"
    assert chip.opcodes == [0x06, 0x05, 0x06, 0x05, 0x02, 0x04, 0x05]  # WREN, RDSR, WREN, RDSR, WRITE, WRDI, RDSR
    assert events == [("FRAM write enable latch set on the second WREN",)]
    assert fram.pr._err_count == 0  # a recovered transient spends no slot


def test_a_write_is_refused_when_both_wrens_are_dropped() -> None:
    fram, chip = make_fram()
    run(setup_fram(fram))
    chip.drop_next_wren = 2
    assert run(_write_one(fram)) is False
    assert chip.drop_next_wren == 0  # the one retry was made
    assert bytes(chip.memory[0x20:0x22]) == b"\x00\x00"
    assert _count(fram, 0x80 + code("W", "FRAM_WEL_NOT_SET")) == 1


def test_set_write_protected_retries_a_dropped_wren_once() -> None:
    fram, chip = make_fram()
    run(setup_fram(fram))
    chip.drop_next_wren = 1
    assert run(fram.set_write_protected(value=True)) is True
    assert chip.status & 0x8C == 0x8C
    assert fram.pr._err_count == 0


def _assert_lost_and_quiet(fram: FRAM_SPI, chip: FakeMB85RS64V) -> None:
    assert fram.initialized is False
    assert fram.lost.is_set()
    assert _count(fram, code("E", "FRAM_CHIP_LOST")) == 1
    assert list(fram.pr.history)[-1] == code("E", "FRAM_CHIP_LOST")
    chip.opcodes = []
    logged = len(chip.log)
    assert run(_read_then_write(fram)) == (False, False)
    assert chip.opcodes == []  # no transfer reaches a lost chip
    assert len(chip.log) == logged
    assert not fram.session_lock.locked()
    assert not fram._bus_lock.locked()


def test_a_chip_gone_silent_mid_run_is_probed_once_and_marked_lost() -> None:
    # SO stuck low reads WEL clear, so each write's latch "did not set" (refused, w26): a status byte a
    # live chip could send, so it takes two anomalies in a row before the one ID probe.
    fram, chip = make_fram()
    run(setup_fram(fram))
    chip.silent = 0x00
    rdids = chip.rdid_count
    assert run(_write_one(fram)) is False
    assert chip.rdid_count == rdids  # one anomaly does not probe
    assert not fram.lost.is_set()
    assert run(_write_one(fram)) is False
    assert chip.rdid_count == rdids + 1
    _assert_lost_and_quiet(fram, chip)


def test_the_first_write_to_a_chip_whose_so_reads_high_reports_the_loss_not_a_success() -> None:
    # SO stuck high reads 0xFF: WEL looks set, so the latch "did not clear" and the write would pass as
    # stored. Status bit 0 is fixed at 0 on both parts (datasheets p.6), so no live chip sends this byte.
    fram, chip = make_fram()
    run(setup_fram(fram))
    chip.silent = 0xFF
    rdids = chip.rdid_count
    assert run(_write_one(fram)) is False
    assert chip.rdid_count == rdids + 1  # probed at once
    assert _count(fram, 0x80 + code("W", "FRAM_WEL_STUCK")) == 0
    assert fram.pr._err_count == 1
    _assert_lost_and_quiet(fram, chip)


def test_set_write_protected_on_a_chip_whose_so_reads_high_reports_the_loss() -> None:
    fram, chip = make_fram()
    run(setup_fram(fram))
    chip.silent = 0xFF
    assert run(fram.set_write_protected(value=True)) is False
    assert _count(fram, 0x80 + code("W", "FRAM_WEL_STUCK")) == 0
    assert fram.pr._err_count == 1
    _assert_lost_and_quiet(fram, chip)


def test_a_real_stuck_latch_on_a_live_chip_still_warns_and_succeeds() -> None:
    # Guard: a live chip's stuck latch reads a legal status byte, so the write keeps today's behaviour -
    # stored, one warning, no probe until a second anomaly in a row, whose ID then matches.
    fram, chip = make_fram()
    run(setup_fram(fram))
    chip.disturb_write_autoclear = True
    rdids = chip.rdid_count
    for expected_rdids in (rdids, rdids + 1):
        chip.drop_next_wrdi = 2
        assert run(_write_one(fram)) is True
        assert bytes(chip.memory[0x20:0x22]) == b"ok"
        assert chip.rdid_count == expected_rdids
        assert list(fram.pr.history)[-1] == 0x80 + code("W", "FRAM_WEL_STUCK")
    assert fram.initialized is True
    assert not fram.lost.is_set()
    assert _count(fram, code("E", "FRAM_CHIP_LOST")) == 0


def test_an_anomaly_with_a_matching_id_keeps_the_chip_up() -> None:
    fram, chip = make_fram()
    run(setup_fram(fram))
    chip.drop_wren = True  # a latch problem, not a lost chip: the ID still answers
    rdids = chip.rdid_count
    for _ in range(4):
        assert run(_write_one(fram)) is False
    assert chip.rdid_count == rdids + 2  # one probe per two anomalies: the match resets the count
    assert fram.initialized is True
    assert not fram.lost.is_set()
    assert _count(fram, code("E", "FRAM_CHIP_LOST")) == 0


def test_a_clean_write_between_two_anomalies_resets_the_count() -> None:
    fram, chip = make_fram()
    run(setup_fram(fram))
    rdids = chip.rdid_count
    chip.drop_next_wren = 2
    assert run(_write_one(fram)) is False
    assert run(_write_one(fram)) is True
    chip.drop_next_wren = 2
    assert run(_write_one(fram)) is False
    assert chip.rdid_count == rdids  # never two anomalies in a row, so never a probe


def test_setup_after_a_loss_clears_it_and_the_chip_works_again() -> None:
    fram, chip = make_fram()
    run(setup_fram(fram))
    chip.silent = 0x00
    run(_write_one(fram))
    run(_write_one(fram))
    assert fram.lost.is_set()
    chip.silent = None
    run(setup_fram(fram))
    assert fram.initialized is True
    assert not fram.lost.is_set()
    assert run(_write_one(fram)) is True
    assert bytes(chip.memory[0x20:0x22]) == b"ok"


# ---------------------------------------------------------------------------
# write protection - keep, RDSR-verified, returns bool
# ---------------------------------------------------------------------------


def test_setup_resyncs_wp_from_nonvolatile_hardware_state_over_a_stale_constructor_guess() -> None:
    # Regression for a real bug: WPEN/BP0/BP1 are nonvolatile FRAM cells, unlike WEL which resets at power-
    # on, so real hardware can already be write-protected from a previous session. setup() must trust the
    # real status register over the constructor's wp= guess in both directions.
    fram, chip = make_fram(wp=False)
    chip.status = 0x8C  # hardware was actually left protected by an earlier session

    async def get() -> bool:
        return await fram.get_write_protected()

    run(setup_fram(fram))
    assert run(get()) is True

    fram2, chip2 = make_fram(wp=True)
    chip2.status = 0x00  # hardware was actually left unprotected

    async def get2() -> bool:
        return await fram2.get_write_protected()

    run(setup_fram(fram2))
    assert run(get2()) is False


def test_write_protected_verified_round_trip() -> None:
    fram, chip = make_fram()
    run(setup_fram(fram))

    async def scenario() -> tuple[bool, bool, bool, bool]:
        set_true = await fram.set_write_protected(value=True)
        get_true = await fram.get_write_protected()
        set_false = await fram.set_write_protected(value=False)
        get_false = await fram.get_write_protected()
        return set_true, get_true, set_false, get_false

    set_true, get_true, set_false, get_false = run(scenario())
    assert (set_true, get_true, set_false, get_false) == (True, True, True, False)
    assert chip.status == 0x00  # WPEN/BP0/BP1 cleared, and WRSR's own WEL side effect cleared too


def test_write_protected_readback_mismatch_returns_false_and_does_not_update_cached_state() -> None:
    fram, chip = make_fram()
    run(setup_fram(fram))
    chip.drop_wrsr = True  # simulated bus disturbance: WRSR's status byte never actually lands

    async def scenario() -> bool:
        return await fram.set_write_protected(value=True)

    ok = run(scenario())
    assert ok is False
    assert (chip.status & 0x8C) == 0x00  # hardware never actually got protected

    async def get() -> bool:
        return await fram.get_write_protected()

    assert run(get()) is False  # cached _wp correctly still reflects the failed attempt, not True


def test_set_write_protected_fails_cleanly_when_wren_is_disturbed() -> None:
    fram, chip = make_fram()
    run(setup_fram(fram))
    chip.drop_wren = True  # simulated bus disturbance: WREN opcode never actually latches

    async def scenario() -> bool:
        return await fram.set_write_protected(value=True)

    ok = run(scenario())
    assert ok is False
    assert (chip.status & 0x8C) == 0x00  # WRSR never even attempted - hardware untouched

    async def get() -> bool:
        return await fram.get_write_protected()

    assert run(get()) is False  # cached _wp correctly still reflects the failed attempt


def test_write_protected_blocks_subsequent_writes() -> None:
    fram, chip = make_fram()
    run(setup_fram(fram))

    async def scenario() -> bool:
        assert await fram.set_write_protected(value=True) is True
        async with fram:
            return await fram.set_values(b"nope", 0x00)

    ok = run(scenario())
    assert ok is False
    assert bytes(chip.memory[0x00:0x04]) == b"\x00\x00\x00\x00"


def test_get_write_protected_before_setup_returns_false() -> None:
    fram, _chip = make_fram()

    async def scenario() -> bool:
        return await fram.get_write_protected()

    assert run(scenario()) is False


def test_set_write_protected_before_setup_returns_false() -> None:
    fram, _chip = make_fram()

    async def scenario() -> bool:
        return await fram.set_write_protected(value=True)

    assert run(scenario()) is False


def test_wp_pin_drives_real_pin_and_get_reads_pin_not_cache() -> None:
    fram, chip = make_fram(wp_pin=7)
    run(setup_fram(fram))

    async def scenario() -> tuple[int | None, bool]:
        ok = await fram.set_write_protected(value=True)
        assert fram._wp_pin is not None
        return fram._wp_pin.value(), ok

    pin_value, ok = run(scenario())
    assert ok is True
    assert pin_value == 0  # WP is active-low: protect=True drives the pin LOW to lock the status register
    assert chip.status & 0x8C == 0x8C  # hardware register still verified/updated too


def test_wp_pin_get_write_protected_reads_active_low_pin_correctly() -> None:
    fram, _chip = make_fram(wp_pin=7)
    run(setup_fram(fram))

    async def scenario() -> tuple[bool, bool]:
        await fram.set_write_protected(value=True)
        protected = await fram.get_write_protected()
        await fram.set_write_protected(value=False)
        unprotected = await fram.get_write_protected()
        return protected, unprotected

    protected, unprotected = run(scenario())
    assert protected is True
    assert unprotected is False


def test_wp_pin_protection_can_be_toggled_off_again_after_being_enabled() -> None:
    # Regression for a real bug: per the datasheet's write-protect table, WEL=1/WPEN=1/WP=0 makes the status
    # register itself unwritable, so a wp_pin left low from an earlier protect=True call silently blocked
    # every later WRSR, including the one meant to turn protection off - a permanent lock-in.
    #
    # Multiple round trips here, not just one, prove it is not a one-shot fluke.
    fram, chip = make_fram(wp_pin=7)
    run(setup_fram(fram))

    async def toggle(*, value: bool) -> bool:
        return await fram.set_write_protected(value=value)

    for value in (True, False, True, False):
        assert run(toggle(value=value)) is True
        assert fram._wp_pin is not None
        assert fram._wp_pin.value() == (0 if value else 1)  # WP active-low
        assert (chip.status & 0x8C) == (0x8C if value else 0x00)


def test_wp_pin_restored_to_prior_asserted_level_when_wrsr_readback_fails() -> None:
    # Regression: set_write_protected() deasserts WP before attempting WRSR, so the register's own WP-pin
    # lock does not block that very WRSR, and must restore the pin on failure rather than leave it
    # deasserted - which would silently unlock a status register that is actually still protected.
    fram, chip = make_fram(wp_pin=7)
    run(setup_fram(fram))

    async def protect() -> bool:
        return await fram.set_write_protected(value=True)

    assert run(protect()) is True
    assert fram._wp_pin is not None
    assert fram._wp_pin.value() == 0  # WP asserted (active-low) - protection genuinely in effect
    chip.drop_wrsr = True  # simulated bus disturbance: WRSR's status byte never actually lands

    async def unprotect() -> bool:
        return await fram.set_write_protected(value=False)

    ok = run(unprotect())
    assert ok is False
    assert fram._wp_pin.value() == 0  # restored to asserted - matches hardware still being protected
    assert (chip.status & 0x8C) == 0x8C  # hardware genuinely still protected


async def _while_held(fram: FRAM_SPI, lock: "asyncio.Lock", call: "Coroutine[Any, Any, bool]", chip: FakeMB85RS64V) -> "tuple[int, int, bool]":
    # Holds `lock` on a gate while `call` runs in a second task: returns the chip's status and RDID
    # count seen while held, then the call's result once the gate opens.
    gate = asyncio.Event()

    async def holder() -> None:
        async with lock:
            await gate.wait()

    held = asyncio.create_task(holder())
    await asyncio.sleep(0)
    task = asyncio.create_task(call)
    for _ in range(5):
        await asyncio.sleep(0)
    seen = (chip.status, chip.rdid_count)
    gate.set()
    await held
    return seen[0], seen[1], await task


def test_set_write_protected_and_setup_wait_for_a_held_driver_lock() -> None:
    # The driver lock guards the scratch buffers both use (C.8), so neither may touch the chip while
    # another holder has it - not only while the bus is held.
    fram, chip = make_fram()
    run(setup_fram(fram))
    status, _rdids, ok = run(_while_held(fram, fram.session_lock, fram.set_write_protected(value=True), chip))
    assert status & 0x8C == 0x00  # untouched while the driver lock was held
    assert ok is True
    assert chip.status & 0x8C == 0x8C
    rdids = chip.rdid_count
    _status, seen_rdids, ok = run(_while_held(fram, fram.session_lock, fram.setup(), chip))
    assert seen_rdids == rdids
    assert ok is True
    assert chip.rdid_count == rdids + 1


def test_set_write_protected_waits_for_a_held_fram_session() -> None:
    # Guard: `async with fram:` holds the bus too, which set_write_protected() already waited for.
    fram, chip = make_fram()
    run(setup_fram(fram))

    async def scenario() -> "tuple[int, bool]":
        gate = asyncio.Event()

        async def holder() -> None:
            async with fram:
                await gate.wait()

        held = asyncio.create_task(holder())
        await asyncio.sleep(0)
        task = asyncio.create_task(fram.set_write_protected(value=True))
        for _ in range(5):
            await asyncio.sleep(0)
        seen = chip.status
        gate.set()
        await held
        return seen, await task

    seen, ok = run(scenario())
    assert seen & 0x8C == 0x00
    assert ok is True
    assert chip.status & 0x8C == 0x8C


def test_a_stuck_latch_with_a_mismatched_readback_persists_only_the_fault() -> None:
    fram, chip = make_fram()
    run(setup_fram(fram))
    chip.drop_wrsr = True  # the readback keeps the old WP bits
    chip.disturb_wrsr_autoclear = True
    chip.drop_next_wrdi = 2  # and the latch stays set through both WRDIs
    assert run(fram.set_write_protected(value=True)) is False
    assert _count(fram, code("E", "FRAM_WP_MISMATCH")) == 1
    assert _count(fram, 0x80 + code("W", "FRAM_WEL_STUCK")) == 0
    assert fram.pr._err_count == 1


# ---------------------------------------------------------------------------
# verify_present() - the post-setup re-probe / self-healing entry point
# ---------------------------------------------------------------------------


def test_verify_present_true_when_device_still_correctly_identifies() -> None:
    fram, _chip = make_fram()
    run(setup_fram(fram))

    async def scenario() -> bool:
        return await fram.verify_present()

    assert run(scenario()) is True
    assert fram.initialized is True


def test_verify_present_false_reverts_to_uninitialized_and_blocks_further_access() -> None:
    fram, chip = make_fram()
    run(setup_fram(fram))
    chip.rdid_response = bytes([0xFF, 0xFF, 0xFF, 0xFF])  # simulated disturbance / device gone

    async def scenario() -> tuple[bool, bool]:
        verified = await fram.verify_present()
        async with fram:
            still_readable = await fram.get_values(bytearray(1), 0)
        return verified, still_readable

    verified, still_readable = run(scenario())
    assert verified is False
    assert fram.initialized is False
    assert fram.lost.is_set()  # the manager's watch task learns of it
    assert _count(fram, code("E", "FRAM_CHIP_LOST")) == 1
    assert still_readable is False  # every other method now safely refuses, as if never set up


def test_verify_present_on_a_dead_chip_persists_chip_lost_once() -> None:
    fram, chip = make_fram()
    run(setup_fram(fram))
    chip.silent = 0xFF
    assert run(fram.verify_present()) is False
    assert _count(fram, code("E", "FRAM_CHIP_LOST")) == 1
    assert fram.pr._err_count == 1
    assert run(fram.verify_present()) is False  # refused at its guard: the same loss, no second E54
    assert _count(fram, code("E", "FRAM_CHIP_LOST")) == 1
    assert not fram.session_lock.locked()
    assert not fram._bus_lock.locked()


def test_setup_again_after_verify_present_failure_recovers() -> None:
    fram, chip = make_fram()
    run(setup_fram(fram))
    chip.rdid_response = bytes([0xFF, 0xFF, 0xFF, 0xFF])
    run_result_1 = run(fram.verify_present())
    assert run_result_1 is False
    chip.rdid_response = bytes([0x04, 0x7F, 0x03, 0x02])  # disturbance cleared up

    assert fram.lost.is_set()
    run(setup_fram(fram))  # the same task-death-and-respawn "fresh setup()" pattern every driver uses
    assert fram.initialized is True
    assert not fram.lost.is_set()


class _RecordingWaitFor:
    # Stands in for asy_fram_driver's asyncio: wait_for_ms() records the bound it is given, then runs
    # the real mechanism on a 1 ms bound so the lock-busy case costs no real second.
    def __init__(self) -> None:
        self.timeouts_ms: list[int] = []

    def __getattr__(self, name: str) -> object:
        return getattr(asyncio, name)

    def wait_for_ms(self, aw: "Coroutine[Any, Any, T]", timeout_ms: int) -> "Coroutine[Any, Any, T]":
        self.timeouts_ms.append(timeout_ms)
        return asyncio.wait_for_ms(aw, 1)


def test_verify_present_bounded_wait_returns_false_instead_of_hanging_when_lock_already_held() -> None:
    # verify_present() takes the driver lock itself: inside an existing `async with fram:` it waits
    # out its bounded timeout instead of hanging (asyncio.Lock is not reentrant).
    fram, _chip = make_fram()
    run(setup_fram(fram))
    recorder = _RecordingWaitFor()

    async def scenario() -> bool:
        async with fram:
            return await fram.verify_present()

    asy_fram_driver.asyncio = recorder  # type: ignore[assignment]
    try:
        result = run(scenario())
    finally:
        asy_fram_driver.asyncio = asyncio
    assert result is False
    assert recorder.timeouts_ms == [1000]  # one wait_for_ms() around the acquire, bounded at 1000 ms
    assert fram.initialized is True  # a lock-busy timeout isn't a device-identification failure
    assert not fram.lost.is_set()
    assert list(fram.pr.history).count(code("E", "LOCK_TIMEOUT")) == 1
    assert run(fram.verify_present()) is True  # the cancelled acquire left the lock usable


# ---------------------------------------------------------------------------
# _setup_addr_buffer - pure function, both address-width branches
# ---------------------------------------------------------------------------


def test_setup_addr_buffer_two_byte_address() -> None:
    fram, _chip = make_fram(max_size=0x2000)
    buf = fram._setup_addr_buffer(0x1234, 0x03)
    assert buf == bytearray([0x03, 0x12, 0x34])


def test_setup_addr_buffer_three_byte_address_for_larger_chips() -> None:
    fram, _chip = make_fram(max_size=0x20000)
    buf = fram._setup_addr_buffer(0x012345, 0x03)
    assert buf == bytearray([0x03, 0x01, 0x23, 0x45])


# ---------------------------------------------------------------------------
# set_write_protected() - shares _write()'s WEL-stuck-after-retry housekeeping
# ---------------------------------------------------------------------------


def test_write_protected_still_reports_success_even_if_wel_stays_stuck_after_retry() -> None:
    # Mirrors test_write_reports_data_written_even_if_wrdi_stays_stuck_after_retry: a stuck WEL
    # is a housekeeping problem, not a "did the protection change happen" problem.
    fram, chip = make_fram()
    run(setup_fram(fram))
    chip.disturb_wrsr_autoclear = True
    chip.drop_next_wrdi = 2  # both the original WRDI and the one retry are disturbed

    async def scenario() -> bool:
        return await fram.set_write_protected(value=True)

    ok = run(scenario())
    assert ok is True
    assert chip.status & 0x8C == 0x8C  # protection itself was still applied and verified
    assert chip.wel is True  # left stuck, but reported (not silently dropped)


# ---------------------------------------------------------------------------
# Configuration matrix - constructor parameters, valid combos and edge/invalid values
# ---------------------------------------------------------------------------


def test_wp_and_wp_pin_combinations_all_construct_and_setup_cleanly() -> None:
    # All 4 combinations of the two independent wp/wp_pin parameters - each on its own is covered elsewhere;
    # this locks in that every pairing constructs and sets up without error, with the pin in the datasheet-
    # correct state.
    #
    # setup() re-syncs _wp from the real nonvolatile status register rather than trusting the constructor,
    # so `wp` here is what the simulated hardware is seeded to hold, not a constructor passthrough.
    for wp in (False, True):
        for wp_pin in (None, 7):
            fram, chip = make_fram(wp=wp, wp_pin=wp_pin)
            chip.status = 0x8C if wp else 0x00
            run(setup_fram(fram))
            assert fram.initialized is True
            if wp_pin is None:
                assert fram._wp_pin is None
            else:
                assert fram._wp_pin is not None
                assert fram._wp_pin.value() == (0 if wp else 1)  # WP active-low


def test_max_size_boundary_values_select_the_correct_address_width() -> None:
    # Exact boundary at the 2-byte/3-byte address-header transition (0xFFFF/0x10000), plus the
    # smallest and a much larger value - not just "some value on each side" as the earlier tests
    # already covered with 0x2000/0x20000.
    for max_size, expect_4_byte_header in ((0x1, False), (0xFFFF, False), (0x10000, True), (0x1000000, True)):
        fram, _chip = make_fram(max_size=max_size)
        buf = fram._setup_addr_buffer(0, 0x03)
        assert len(buf) == (4 if expect_4_byte_header else 3)


def test_max_size_zero_or_negative_raises_at_setup_as_an_unrecognized_size() -> None:
    # Not a validated constructor parameter (int, enforced by the type system alone) - but setup()'s
    # device-ID check is keyed by max_size (see _KNOWN_PRODUCT_IDS), so a nonsensical value now fails
    # loudly here instead of silently completing setup() and only rejecting every access afterward.
    for max_size in (0, -1, -100):
        fram, _chip = make_fram(max_size=max_size)
        try:
            run(setup_fram(fram))
            raised = False
        except ValueError:
            raised = True
        assert raised
        assert fram.initialized is False


def test_unrecognized_max_size_raises_at_setup_regardless_of_wp_settings() -> None:
    # Several edge values together, not one at a time: an unrecognized max_size alongside a real wp/wp_pin
    # configuration. _check_device_id(), now keyed by max_size, runs before any status-register handling in
    # setup(), so it must raise the same way whatever wp/wp_pin are - no interaction between them.
    fram, chip = make_fram(max_size=-1, wp=True, wp_pin=7)
    chip.status = 0x8C
    try:
        run(setup_fram(fram))
        raised = False
    except ValueError:
        raised = True
    assert raised
    assert fram.initialized is False


# ---------------------------------------------------------------------------
# Exception-safety: verify_present()'s missing uninitialized guard (found and fixed)
# ---------------------------------------------------------------------------


def test_verify_present_before_setup_returns_false_not_a_raised_runtimeerror() -> None:
    # Real gap found during an exception-safety review: every other public method here guards `initialized`
    # first and returns a clean False, and verify_present() was the one exception, letting SPIDevice's own
    # "not set up" RuntimeError leak out if called before the first successful setup().
    fram, _chip = make_fram()

    async def scenario() -> bool:
        return await fram.verify_present()

    assert run(scenario()) is False
    assert fram.initialized is False


# ---------------------------------------------------------------------------
# Construction errors raise at boot (asy_spi_driver.py's contract); a bus that goes down later is
# reported by status, never raised.
# ---------------------------------------------------------------------------


def test_construction_with_an_out_of_range_wp_pin_raises_uncaught_at_boot() -> None:
    # __init__ constructs a real Pin object for wp_pin - a one-time at-boot misconfiguration is allowed to
    # raise loudly rather than silently produce a permanently nonfunctional driver, the carve-out
    # asy_spi_driver.py already established. 99 is outside the real RP2040's GPIO0-28 range.
    bus = make_bus()
    try:
        FRAM_SPI(bus, 1, logger=PrintLogHistory(), wp_pin=99)
        raised = False
    except ValueError:
        raised = True
    assert raised


def test_construction_with_an_out_of_range_spi_cs_raises_uncaught_at_boot() -> None:
    # Same carve-out, for the required spi_cs parameter instead of the optional wp_pin.
    bus = make_bus()
    try:
        FRAM_SPI(bus, 99, logger=PrintLogHistory())
        raised = False
    except ValueError:
        raised = True
    assert raised


def _bus_down_entries(fram: FRAM_SPI) -> int:
    log = run(fram.pr.get_log())[fram.pr.name]
    nums, kinds = log["ErrNum"], log["ErrType"]
    return sum(1 for i in range(len(nums)) if kinds[i] == "E" and nums[i] == code("E", "FRAM_BUS_DOWN"))


def test_bus_deinit_mid_operation_returns_false_and_logs_bus_down() -> None:
    # A deinitialised bus is reported as bus-down by the driver (bool SPI results, C.3), not raised.
    fram, chip = make_fram()
    run(setup_fram(fram))
    fram._spidev.spi.deinit()
    logged = len(chip.log)

    async def scenario() -> bool:
        async with fram:
            return await fram.get_values(bytearray(1), 0)

    assert run(scenario()) is False
    assert _bus_down_entries(fram) == 1
    assert fram.pr._err_count == 1
    assert len(chip.log) == logged  # no transfer was made


def test_set_values_on_a_bus_that_went_down_returns_false_and_logs_bus_down() -> None:
    fram, chip = make_fram()
    run(setup_fram(fram))
    before = bytes(chip.memory[0:2])
    fram._spidev.spi.deinit()

    async def scenario() -> bool:
        async with fram:
            return await fram.set_values(b"\x5a\xa5", 0)

    assert run(scenario()) is False
    assert _bus_down_entries(fram) == 1
    assert fram.pr._err_count == 1
    assert bytes(chip.memory[0:2]) == before


def test_verify_present_and_set_write_protected_report_a_bus_down_after_setup() -> None:
    fram, _chip = make_fram()
    run(setup_fram(fram))
    fram._spidev.spi.deinit()
    assert run(fram.verify_present()) is False
    assert _bus_down_entries(fram) == 1
    assert fram.pr._err_count == 1
    assert run(fram.set_write_protected(value=True)) is False
    assert _bus_down_entries(fram) == 1  # the same code again shares the newest slot (C.7.1)
    assert fram.pr._err_count == 2  # one count per call
    assert fram.initialized is True  # a bus that is down is not a lost chip
    assert not fram.session_lock.locked()
    assert not fram._bus_lock.locked()


def test_setup_raises_when_the_bus_is_down() -> None:
    fram, chip = make_fram()
    fram._spidev.spi.deinit()
    try:
        run(setup_fram(fram))
        message = ""
    except OSError as e:
        message = str(e)
    assert message == "SPI bus not initialized"
    assert fram.initialized is False
    assert not [entry for entry in chip.log if entry[0] != "deinit"]  # no RDID was clocked


# ---------------------------------------------------------------------------
# Detection boundary - what this layer cannot catch, by design (not a bug)
# ---------------------------------------------------------------------------


def test_corrupted_write_payload_bytes_are_undetectable_at_this_layer_by_design() -> None:
    # This layer verifies opcodes, latches and device identity, never the payload bytes - raw SPI has no
    # data-integrity check, which is why asy_fram_manager.py's CRC and dual copies exist one layer up.
    # Proven, not asserted: a payload byte landing wrong on the wire still reports a successful write.
    fram, chip = make_fram()
    run(setup_fram(fram))
    chip.corrupt_next_write_data = b"XXXX"  # what actually lands, regardless of what's sent

    async def scenario() -> bool:
        async with fram:
            return await fram.set_values(b"good", 0x00)

    ok = run(scenario())
    assert ok is True  # the driver reports success - it has no way to know otherwise
    assert bytes(chip.memory[0x00:0x04]) == b"XXXX"  # but the real stored bytes are wrong


# ---------------------------------------------------------------------------
# Integration - real asy_print_log.PrintLogHistory, real asy_base_classes.Lockable concurrency/cancellation
# ---------------------------------------------------------------------------


def test_works_correctly_with_the_real_printloghistory_logger_used_in_production() -> None:
    # FRAMManager passes its own real PrintLogHistory as logger in production, shared with every chunk it
    # owns - this confirms doing so does not interfere with FRAM_SPI's behavior. The `logger` parameter is
    # typed PrintLogHistory rather than the narrower PrintLog precisely because it calls err_s()/wrn_s().
    bus = make_bus()
    logger = PrintLogHistory(history_length=5)
    fram = FRAM_SPI(bus, 1, logger=logger, max_size=0x2000)

    async def scenario() -> bool:
        await fram.setup()
        async with fram:
            if not await fram.set_values(b"hi", 0):
                return False
            buf = bytearray(2)
            if not await fram.get_values(buf, 0):
                return False
        return bytes(buf) == b"hi"

    assert run(scenario()) is True


# ---------------------------------------------------------------------------
# Persisted logging - err_s()/wrn_s() for the genuinely actionable hardware-fault paths (not initialized,
# invalid address range, WEL did not set or clear, write-protect readback mismatch, verify_present() lock-
# timeout); the routine caller-contract signals stay on the plain, non-persisted err()/wrn().
# ---------------------------------------------------------------------------


def test_get_write_protected_before_setup_logs_a_persisted_error() -> None:
    fram, _chip = make_fram()

    async def scenario() -> bool:
        return await fram.get_write_protected()

    assert run(scenario()) is False
    assert fram.pr._err_count == 1
    assert list(fram.pr.history)[-1] == code("E", "NOT_INIT")


def test_get_values_before_setup_logs_a_persisted_error() -> None:
    fram, _chip = make_fram()

    async def scenario() -> bool:
        return await fram.get_values(bytearray(4), 0)

    assert run(scenario()) is False
    assert fram.pr._err_count == 1
    assert code("E", "NOT_INIT") in fram.pr.history


def test_get_values_out_of_range_logs_a_persisted_error() -> None:
    fram, _chip = make_fram()
    run(setup_fram(fram))

    async def scenario() -> None:
        async with fram:
            await fram.get_values(bytearray(4), -1)

    run(scenario())
    assert fram.pr._err_count == 1
    assert code("E", "BAD_ARG") in fram.pr.history


def test_set_values_before_setup_logs_a_persisted_error() -> None:
    fram, _chip = make_fram()

    async def scenario() -> bool:
        return await fram.set_values(b"x", 0)

    assert run(scenario()) is False
    assert fram.pr._err_count == 1
    assert code("E", "NOT_INIT") in fram.pr.history


def test_set_values_out_of_range_logs_a_persisted_error() -> None:
    fram, _chip = make_fram()
    run(setup_fram(fram))

    async def scenario() -> None:
        async with fram:
            await fram.set_values(b"x", -1)

    run(scenario())
    assert fram.pr._err_count == 1
    assert code("E", "BAD_ARG") in fram.pr.history


def test_set_write_protected_before_setup_logs_a_persisted_error() -> None:
    fram, _chip = make_fram()

    async def scenario() -> bool:
        return await fram.set_write_protected(value=True)

    assert run(scenario()) is False
    assert fram.pr._err_count == 1
    assert code("E", "NOT_INIT") in fram.pr.history


def test_write_protected_readback_mismatch_logs_a_persisted_error() -> None:
    fram, chip = make_fram()
    run(setup_fram(fram))
    chip.drop_wrsr = True  # simulated bus disturbance: WRSR's status byte never actually lands

    async def scenario() -> bool:
        return await fram.set_write_protected(value=True)

    assert run(scenario()) is False
    assert code("E", "FRAM_WP_MISMATCH") in fram.pr.history


def test_verify_present_before_setup_logs_a_persisted_error() -> None:
    fram, _chip = make_fram()

    async def scenario() -> bool:
        return await fram.verify_present()

    assert run(scenario()) is False
    assert code("E", "NOT_INIT") in fram.pr.history


def test_write_wel_did_not_set_logs_a_persisted_warning() -> None:
    fram, chip = make_fram()
    run(setup_fram(fram))
    chip.drop_wren = True  # simulated bus disturbance: WREN opcode never actually latches

    async def scenario() -> bool:
        async with fram:
            return await fram.set_values(b"bad!", 0x00)

    assert run(scenario()) is False
    assert 0x80 + code("W", "FRAM_WEL_NOT_SET") in fram.pr.history  # wrn_s()'s history entries are offset by _NO_WRN (0x80)


def test_set_write_protected_wel_did_not_set_logs_a_persisted_warning() -> None:
    fram, chip = make_fram()
    run(setup_fram(fram))
    chip.drop_wren = True  # simulated bus disturbance: WREN opcode never actually latches

    async def scenario() -> bool:
        return await fram.set_write_protected(value=True)

    assert run(scenario()) is False
    assert 0x80 + code("W", "FRAM_WEL_NOT_SET") in fram.pr.history  # wrn_s()'s history entries are offset by _NO_WRN (0x80)


def test_wrdi_stuck_after_retry_logs_a_persisted_warning() -> None:
    fram, chip = make_fram()
    run(setup_fram(fram))
    chip.disturb_write_autoclear = True
    chip.drop_next_wrdi = 2  # both the original WRDI and the one retry are disturbed

    async def scenario() -> bool:
        async with fram:
            return await fram.set_values(b"ok!!", 0x00)

    ok = run(scenario())
    assert ok is True  # the payload write itself still succeeded, only WEL housekeeping is stuck
    assert 0x80 + code("W", "FRAM_WEL_STUCK") in fram.pr.history  # wrn_s()'s history entries are offset by _NO_WRN (0x80)


def test_write_protected_and_access_not_locked_are_now_persisted() -> None:
    # "Currently write protected" (a benign, expected refusal, as the manager's "communication paused") and "access
    # not locked" (a caller contract violation, so an errno) both persist.
    fram, _chip = make_fram()
    run(setup_fram(fram))
    assert run(fram.set_write_protected(value=True)) is True

    async def scenario() -> tuple[bool, bool]:
        no_lock = await fram.get_values(bytearray(1), 0)  # no `async with fram:` wrapper - CONTRACT
        async with fram:
            still_protected = await fram.set_values(b"x", 0)  # locked, so this reaches _write() - FRAM_WRITE_PROTECTED
        return no_lock, still_protected

    no_lock, still_protected = run(scenario())
    assert no_lock is False
    assert still_protected is False
    assert fram.pr._err_count == 2
    log = run(fram.pr.get_log())[fram.pr.name]
    assert log["ErrNum"][-2:] == [code("E", "CONTRACT"), code("W", "FRAM_WRITE_PROTECTED")]
    assert log["ErrType"][-2:] == ["E", "W"]


def test_two_operations_on_the_same_fram_never_run_concurrently() -> None:
    # FRAM_SPI's own outer Lockable lock (asy_base_classes.py), not the SPI bus's - test_asy_spi_driver.py
    # already proves the bus-level lock serializes; this proves the same one level up, for the lock every
    # real caller actually wraps chunk operations in.
    fram, _chip = make_fram()
    run(setup_fram(fram))
    concurrent = 0
    max_concurrent = 0

    async def worker(data: bytes, addr: int) -> None:
        nonlocal concurrent, max_concurrent
        async with fram:
            concurrent += 1
            max_concurrent = max(max_concurrent, concurrent)
            await fram.set_values(data, addr)
            await asyncio.sleep(0)
            concurrent -= 1

    async def scenario() -> None:
        await asyncio.gather(worker(b"aaaa", 0x00), worker(b"bbbb", 0x10))

    run(scenario())
    assert max_concurrent == 1


def test_task_cancelled_while_holding_frams_own_lock_still_releases_it() -> None:
    fram, _chip = make_fram()
    run(setup_fram(fram))
    started = False

    async def holder() -> None:
        nonlocal started
        async with fram:
            started = True
            await asyncio.sleep(10)

    async def scenario() -> None:
        task = asyncio.create_task(holder())
        while not started:
            await asyncio.sleep(0)
        assert fram.session_lock.locked()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        assert not fram.session_lock.locked()

    run(scenario())


# ---------------------------------------------------------------------------
# Bus-hazard coverage moved from tests/test_bus_hazard_multi_device.py (SPECIFICATION.md Part
# C.8): FRAM is SPI, no address/bus-sharing concept, so same-device concurrency is its whole slice.
# Complements the concurrency-counter proof above with a real read/write data-integrity check.
# ---------------------------------------------------------------------------

_HAZARD_READ_REGION = (0x0000, 16)  # (start_address, length) - never touched by the writer below
_HAZARD_WRITE_REGION = (0x1000, 16)  # disjoint from the read region, well within the 0x2000 chip's range
_HAZARD_SEED_PATTERN = bytes(range(16))  # 0x00..0x0F - fixed, known, easy to spot corruption in
_HAZARD_WRITE_PATTERN = bytes(range(0xF0, 0x100))  # 0xF0..0xFF - deliberately distinct from the seed


def test_same_device_concurrent_read_and_write_never_corrupt_each_other() -> None:
    fram, chip = make_fram()
    run(setup_fram(fram))
    chip.memory[_HAZARD_READ_REGION[0] : _HAZARD_READ_REGION[0] + _HAZARD_READ_REGION[1]] = _HAZARD_SEED_PATTERN

    read_iterations = 20
    reads_completed = 0
    write_completed = False
    read_mismatches: list[str] = []
    first_read_done = asyncio.Event()

    async def reader() -> None:
        nonlocal reads_completed
        buf = bytearray(_HAZARD_READ_REGION[1])
        for i in range(read_iterations):
            ok = await fram.get_values(buf, addr_start=_HAZARD_READ_REGION[0])
            if not ok or bytes(buf) != _HAZARD_SEED_PATTERN:
                read_mismatches.append(f"iter {i}: ok={ok} got={bytes(buf).hex()} expected={_HAZARD_SEED_PATTERN.hex()}")
            reads_completed += 1
            first_read_done.set()

    async def writer() -> None:
        nonlocal write_completed
        # A completed read gates the write, outside the lock: a writer holding it would block that read.
        await first_read_done.wait()
        async with fram:
            ok = await fram.set_values(_HAZARD_WRITE_PATTERN, addr_start=_HAZARD_WRITE_REGION[0])
        assert ok, "FRAM write failed outright under concurrent read load"
        write_completed = True

    async def locked_call(coro: "Coroutine[Any, Any, None]") -> None:
        async with fram:
            await coro

    async def scenario() -> None:
        await asyncio.gather(locked_call(reader()), writer())

    run(scenario())

    assert reads_completed == read_iterations
    assert write_completed
    assert not read_mismatches, f"{len(read_mismatches)} corrupted/torn read(s) under concurrent write: {read_mismatches[:5]}"
    written_back = bytes(chip.memory[_HAZARD_WRITE_REGION[0] : _HAZARD_WRITE_REGION[0] + _HAZARD_WRITE_REGION[1]])
    assert written_back == _HAZARD_WRITE_PATTERN, f"write region shows {written_back.hex()}, expected {_HAZARD_WRITE_PATTERN.hex()} - torn/corrupted write"


# Bus-lock granularity and the per-command yield policy: one acquire/release and exactly one
# scheduler pass per byte-level command, whatever its CS-cycle count.


def count_bus_lock_holds(fram: FRAM_SPI) -> "list[int]":
    # Counts acquisitions of the SPI *bus* lock (the innermost of the three), not FRAM_SPI's own.
    holds = [0]
    bus_lock = fram._spidev.spi.bus_lock
    original = bus_lock.acquire

    async def counting_acquire() -> bool:
        holds[0] += 1
        return bool(await original())

    bus_lock.acquire = counting_acquire  # type: ignore[method-assign,assignment]
    return holds


async def passes_during(coro: "Coroutine[Any, Any, Any]") -> int:
    # Scheduler passes a competing task gets while `coro` runs - i.e. how often this path yields.
    passes = [0]

    async def competitor() -> None:
        while True:
            passes[0] += 1
            await asyncio.sleep(0)

    other = asyncio.create_task(competitor())
    await asyncio.sleep(0)  # one yield lets the competitor start and park (a limit, not an interleaving claim)
    before = passes[0]
    await coro
    during = passes[0] - before
    other.cancel()
    try:
        await other
    except asyncio.CancelledError:
        pass
    return during


def test_a_write_command_is_issued_under_one_bus_lock_hold() -> None:
    # A one-byte write is a five-CS envelope (WREN, RDSR, WRITE, WRDI, RDSR); the chip needs every
    # cycle, the bus lock does not need taking five times. One hold per command keeps a shared bus
    # interleavable between commands while making the envelope indivisible (SPECIFICATION.md Part C.8).
    fram, _chip = make_fram()
    run(setup_fram(fram))
    holds = count_bus_lock_holds(fram)

    async def scenario() -> bool:
        async with fram:
            return await fram.set_values(b"\x01", 0)

    assert run(scenario()) is True
    assert holds[0] == 1, f"{holds[0]} bus-lock holds for one write command"


def test_a_read_command_is_issued_under_one_bus_lock_hold() -> None:
    fram, _chip = make_fram()
    run(setup_fram(fram))
    holds = count_bus_lock_holds(fram)

    async def scenario() -> bool:
        async with fram:
            return await fram.get_values(bytearray(4), 0)

    assert run(scenario()) is True
    assert holds[0] == 1, f"{holds[0]} bus-lock holds for one read command"


def test_set_values_yields_exactly_once_per_command() -> None:
    # The per-command yield policy: the scheduling points live in the coroutine that owns the
    # operation, not in the CS window. One command, one pass - enough that a burst of them cannot
    # starve the loop (HEAP_FRAGMENTATION_MEASUREMENTS.md section M7), and no more than that.
    fram, _chip = make_fram()
    run(setup_fram(fram))

    async def scenario() -> int:
        async with fram:
            return await passes_during(fram.set_values(b"\x01", 0))

    assert run(scenario()) == 1


def test_get_values_yields_exactly_once_per_command() -> None:
    fram, _chip = make_fram()
    run(setup_fram(fram))

    async def scenario() -> int:
        async with fram:
            return await passes_during(fram.get_values(bytearray(4), 0))

    assert run(scenario()) == 1


# The three write-path warnings: same number, same message, logged once, from the same public
# entry point - whichever layer actually decides them.


def record_warnings(fram: FRAM_SPI) -> "list[tuple[tuple[object, ...], int]]":
    recorded: list[tuple[tuple[object, ...], int]] = []
    original = fram.pr.wrn_s

    async def capture(*args: object, wrnno: int = 0, sep: str = " ", end: str = "\n") -> None:
        recorded.append((args, wrnno))
        await original(*args, wrnno=wrnno, sep=sep, end=end)

    fram.pr.wrn_s = capture  # type: ignore[method-assign]
    return recorded


def test_write_protected_warning_keeps_its_number_and_message() -> None:
    fram, _chip = make_fram()
    run(setup_fram(fram))
    assert run(fram.set_write_protected(value=True)) is True
    recorded = record_warnings(fram)

    async def scenario() -> bool:
        async with fram:
            return await fram.set_values(b"x", 0)

    assert run(scenario()) is False
    assert recorded == [(("FRAM currently write protected.",), code("W", "FRAM_WRITE_PROTECTED"))]


def test_write_enable_latch_warning_keeps_its_number_and_message() -> None:
    fram, chip = make_fram()
    run(setup_fram(fram))
    chip.drop_wren = True  # simulated bus disturbance: WREN opcode never actually latches
    recorded = record_warnings(fram)

    async def scenario() -> bool:
        async with fram:
            return await fram.set_values(b"bad!", 0x00)

    assert run(scenario()) is False
    assert recorded == [(("FRAM write enable latch did not set, aborting write.",), code("W", "FRAM_WEL_NOT_SET"))]


def test_wrdi_stuck_warning_keeps_its_number_and_message() -> None:
    fram, chip = make_fram()
    run(setup_fram(fram))
    chip.disturb_write_autoclear = True
    chip.drop_next_wrdi = 2  # both the original WRDI and the one retry are disturbed
    recorded = record_warnings(fram)

    async def scenario() -> bool:
        async with fram:
            return await fram.set_values(b"ok!!", 0x00)

    assert run(scenario()) is True  # the payload landed; only the WEL housekeeping is stuck
    assert recorded == [(("FRAM write enable latch did not clear after WRDI retry.",), code("W", "FRAM_WEL_STUCK"))]


# ---------------------------------------------------------------------------
# The two-lock entry/exit itself. __aenter__ takes the driver's own lock and THEN the bus lock, so
# each half has a failure mode of its own that no operation-level test reaches.
# ---------------------------------------------------------------------------


def test_aenter_releases_its_own_lock_if_the_bus_lock_cannot_be_acquired() -> None:
    # Without __aenter__'s try/except the driver's own lock would leak permanently: `async with`
    # never calls __aexit__ when __aenter__ raises, and every later FRAM operation would hang.
    fram, _chip = make_fram()
    run(setup_fram(fram))

    async def boom() -> None:
        raise OSError(5)

    fram._bus_lock.acquire = boom  # type: ignore[method-assign, assignment]  # deliberate monkeypatch

    async def scenario() -> bool:
        try:
            async with fram:
                pass
        except OSError:
            return True
        else:
            return False

    assert run(scenario()) is True
    assert not fram.session_lock.locked(), "the driver's own lock leaked when the bus lock failed"


def test_a_later_operation_still_works_after_a_failed_bus_lock_acquisition() -> None:
    # The consequence of the release above, stated as behavior rather than as lock state: one
    # failed entry must not take the chunk layer down with it for the rest of the uptime.
    fram, _chip = make_fram()
    run(setup_fram(fram))
    real_acquire = fram._bus_lock.acquire
    calls = [0]

    async def fail_once() -> None:
        calls[0] += 1
        if calls[0] == 1:
            raise OSError(5)
        await real_acquire()

    fram._bus_lock.acquire = fail_once  # type: ignore[method-assign, assignment]  # deliberate monkeypatch

    async def first() -> None:
        async with fram:
            pass

    async def second() -> bool:
        async with fram:
            return await fram.set_values(b"ok!!", 0x00)

    try:
        run(first())
    except OSError:
        pass
    # Bounded, not a bare await: a leaked lock makes the second entry wait forever, and a hanging
    # test is never an acceptable failure mode here (CLAUDE.md's standing backstop).
    assert run(asyncio.wait_for(second(), _LOCK_WAIT_S)) is True


def test_aexit_tolerates_a_bus_lock_that_was_already_released() -> None:
    # Same tolerance Lockable's own __aexit__ has, applied to the inner lock. Without it the double
    # release would raise out of __aexit__ and the driver's own lock would never be released.
    fram, _chip = make_fram()
    run(setup_fram(fram))

    async def scenario() -> None:
        async with fram:
            fram._bus_lock.release()  # released early by hand

    run(scenario())  # must not raise
    assert not fram.session_lock.locked(), "the driver's own lock leaked after the inner double release"
    assert not fram._bus_lock.locked()


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
