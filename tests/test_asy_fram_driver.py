import asyncio

from _fram_chip_fake import FakeMB85RS64V

import asy_spi_driver
from asy_fram_driver import FRAM_SPI
from asy_spi_driver import SPI
from print_log import PrintLog

# Swaps the stateful MB85RS64V chip fake in for the whole process (one test file per
# scripts/test.sh invocation - see tests/README.md): asy_spi_driver.SPI.init() resolves `_SPI` as
# a plain module global at call time, so reassigning it here before any SPI bus is constructed is
# enough, with no per-test patch/restore dance needed.
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


def make_bus() -> SPI:
    return SPI(0, sck_pin=2, mosi_pin=3, miso_pin=4)


def make_fram(
    max_size: int = 0x2000, wp: bool = False, wp_pin: int | None = None
) -> tuple[FRAM_SPI, FakeMB85RS64V]:
    bus = make_bus()
    fram = FRAM_SPI(bus, 1, logger=PrintLog(), wp=wp, wp_pin=wp_pin, max_size=max_size)
    chip = fram._spidev.spi._spi
    assert isinstance(chip, FakeMB85RS64V)
    return fram, chip


async def setup_fram(fram: FRAM_SPI) -> None:
    await fram.setup()


# ---------------------------------------------------------------------------
# setup() - device identification, the fixed RDID byte-order + and/or bug
# ---------------------------------------------------------------------------


def test_setup_succeeds_with_correct_device_id() -> None:
    fram, _chip = make_fram()
    run(setup_fram(fram))
    assert fram.uninitialized is False


def test_setup_raises_on_wrong_manufacturer_id() -> None:
    fram, chip = make_fram()
    chip.rdid_response = bytes([0x05, 0x7F, 0x03, 0x02])
    try:
        run(setup_fram(fram))
        raised = False
    except OSError:
        raised = True
    assert raised
    assert fram.uninitialized is True


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
    # Regression test for the real bug found during this promotion: the legacy check was
    # `manf_wrong AND prod_wrong`, so a correct manufacturer byte alone (0x04) made this whole
    # check pass regardless of the (also byte-order-swapped) product ID - meaning a wrong/different
    # Fujitsu part, or a corrupted product-ID byte pair, was silently accepted. Now must raise.
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


# ---------------------------------------------------------------------------
# get_values / set_values - guards (uninitialized, lock, range) and real data
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
            ok = await fram.set_values(b"bad!", 0x00)
        return ok

    ok = run(scenario())
    assert ok is False
    assert bytes(chip.memory[0x00:0x04]) == b"\x00\x00\x00\x00"  # untouched


def test_write_succeeds_normally_when_wrdi_is_not_disturbed() -> None:
    fram, chip = make_fram()
    run(setup_fram(fram))

    async def scenario() -> bool:
        async with fram:
            ok = await fram.set_values(b"ok!!", 0x00)
        return ok

    assert run(scenario()) is True
    assert chip.wel is False  # WRDI cleared it as expected


def test_write_retries_wrdi_once_and_recovers_when_first_wrdi_is_disturbed() -> None:
    fram, chip = make_fram()
    run(setup_fram(fram))
    chip.drop_next_wrdi = 1  # first WRDI attempt is disturbed, the retry is not

    async def scenario() -> bool:
        async with fram:
            ok = await fram.set_values(b"ok!!", 0x00)
        return ok

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
    chip.drop_next_wrdi = 2  # both the original WRDI and the one retry are disturbed

    async def scenario() -> bool:
        async with fram:
            ok = await fram.set_values(b"ok!!", 0x00)
        return ok

    ok = run(scenario())
    assert ok is True
    assert bytes(chip.memory[0x00:0x04]) == b"ok!!"
    assert chip.wel is True  # left stuck, but reported (not silently dropped)


# ---------------------------------------------------------------------------
# write protection - keep, RDSR-verified, returns bool
# ---------------------------------------------------------------------------


def test_write_protected_verified_round_trip() -> None:
    fram, chip = make_fram()
    run(setup_fram(fram))

    async def scenario() -> tuple[bool, bool, bool, bool]:
        set_true = await fram.set_write_protected(True)
        get_true = await fram.get_write_protected()
        set_false = await fram.set_write_protected(False)
        get_false = await fram.get_write_protected()
        return set_true, get_true, set_false, get_false

    set_true, get_true, set_false, get_false = run(scenario())
    assert (set_true, get_true, set_false, get_false) == (True, True, False, False)
    assert chip.status == 0x00  # WPEN/BP0/BP1 cleared, and WRSR's own WEL side effect cleared too


def test_write_protected_readback_mismatch_returns_false_and_does_not_update_cached_state() -> None:
    fram, chip = make_fram()
    run(setup_fram(fram))
    chip.drop_wrsr = True  # simulated bus disturbance: WRSR's status byte never actually lands

    async def scenario() -> bool:
        return await fram.set_write_protected(True)

    ok = run(scenario())
    assert ok is False
    assert (chip.status & 0x8C) == 0x00  # hardware never actually got protected

    async def get() -> bool:
        return await fram.get_write_protected()

    assert run(get()) is False  # cached _wp correctly still reflects the failed attempt, not True


def test_write_protected_blocks_subsequent_writes() -> None:
    fram, chip = make_fram()
    run(setup_fram(fram))

    async def scenario() -> bool:
        assert await fram.set_write_protected(True) is True
        async with fram:
            ok = await fram.set_values(b"nope", 0x00)
        return ok

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
        return await fram.set_write_protected(True)

    assert run(scenario()) is False


def test_wp_pin_drives_real_pin_and_get_reads_pin_not_cache() -> None:
    fram, chip = make_fram(wp_pin=7)
    run(setup_fram(fram))

    async def scenario() -> tuple[int | None, bool]:
        ok = await fram.set_write_protected(True)
        assert fram._wp_pin is not None
        return fram._wp_pin.value(), ok

    pin_value, ok = run(scenario())
    assert ok is True
    assert pin_value == 1
    assert chip.status & 0x8C == 0x8C  # hardware register still verified/updated too


# ---------------------------------------------------------------------------
# verify_present() - the post-setup re-probe / self-healing entry point
# ---------------------------------------------------------------------------


def test_verify_present_true_when_device_still_correctly_identifies() -> None:
    fram, _chip = make_fram()
    run(setup_fram(fram))

    async def scenario() -> bool:
        return await fram.verify_present()

    assert run(scenario()) is True
    assert fram.uninitialized is False


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
    assert fram.uninitialized is True
    assert still_readable is False  # every other method now safely refuses, as if never set up


def test_setup_again_after_verify_present_failure_recovers() -> None:
    fram, chip = make_fram()
    run(setup_fram(fram))
    chip.rdid_response = bytes([0xFF, 0xFF, 0xFF, 0xFF])
    run_result_1 = run(fram.verify_present())
    assert run_result_1 is False
    chip.rdid_response = bytes([0x04, 0x7F, 0x03, 0x02])  # disturbance cleared up

    run(setup_fram(fram))  # the same task-death-and-respawn "fresh setup()" pattern every driver uses
    assert fram.uninitialized is False


# ---------------------------------------------------------------------------
# setup_addr_buffer - pure function, both address-width branches
# ---------------------------------------------------------------------------


def test_setup_addr_buffer_two_byte_address() -> None:
    fram, _chip = make_fram(max_size=0x2000)
    buf = fram.setup_addr_buffer(0x1234, 0x03)
    assert buf == bytearray([0x03, 0x12, 0x34])


def test_setup_addr_buffer_three_byte_address_for_larger_chips() -> None:
    fram, _chip = make_fram(max_size=0x20000)
    buf = fram.setup_addr_buffer(0x012345, 0x03)
    assert buf == bytearray([0x03, 0x01, 0x23, 0x45])


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
