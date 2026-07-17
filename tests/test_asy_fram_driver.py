import asyncio

from _fram_chip_fake import FakeMB85RS64V

import asy_fram_driver
import asy_spi_driver
from asy_fram_driver import FRAM_SPI
from asy_spi_driver import SPI
from print_log import PrintLog, PrintLogHistory

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
    chip.wp_pin = fram._wp_pin  # lets the fake model the datasheet's WP-pin status-register lock
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
    # WRITE's own datasheet-confirmed WEL auto-clear is disturbed too, so the first (disturbed)
    # WRDI genuinely has something to fail to clear, and the retry genuinely has something to fix.
    chip.disturb_write_autoclear = True
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
    chip.disturb_write_autoclear = True  # so WEL genuinely has something to still be stuck at
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


def test_setup_resyncs_wp_from_nonvolatile_hardware_state_over_a_stale_constructor_guess() -> None:
    # Regression for a real bug: WPEN/BP0/BP1 are nonvolatile FRAM cells (unlike WEL, which resets
    # at power-on), so real hardware can already be write-protected from a previous session before
    # this object even exists. setup() must trust the real status register over the constructor's
    # wp= guess in both directions - a stale "assumed protected" and a stale "assumed unprotected".
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
        set_true = await fram.set_write_protected(True)
        get_true = await fram.get_write_protected()
        set_false = await fram.set_write_protected(False)
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
    assert pin_value == 0  # WP is active-low: protect=True drives the pin LOW to lock the status register
    assert chip.status & 0x8C == 0x8C  # hardware register still verified/updated too


def test_wp_pin_get_write_protected_reads_active_low_pin_correctly() -> None:
    fram, _chip = make_fram(wp_pin=7)
    run(setup_fram(fram))

    async def scenario() -> tuple[bool, bool]:
        await fram.set_write_protected(True)
        protected = await fram.get_write_protected()
        await fram.set_write_protected(False)
        unprotected = await fram.get_write_protected()
        return protected, unprotected

    protected, unprotected = run(scenario())
    assert protected is True
    assert unprotected is False


def test_wp_pin_protection_can_be_toggled_off_again_after_being_enabled() -> None:
    # Regression for a real bug: per the datasheet's WRITING PROTECT table, WEL=1,WPEN=1,WP=0
    # makes the status register itself unwritable - so a wp_pin left low from an earlier
    # protect=True call used to silently block every later WRSR, including the one meant to turn
    # protection back off, permanently locking this driver into protected mode. Multiple round
    # trips here (not just one) prove it's not a one-shot fluke.
    fram, chip = make_fram(wp_pin=7)
    run(setup_fram(fram))

    async def toggle(value: bool) -> bool:
        return await fram.set_write_protected(value)

    for value in (True, False, True, False):
        assert run(toggle(value)) is True
        assert fram._wp_pin is not None
        assert fram._wp_pin.value() == (0 if value else 1)  # WP active-low
        assert (chip.status & 0x8C) == (0x8C if value else 0x00)


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


def test_verify_present_bounded_wait_returns_false_instead_of_hanging_when_lock_already_held() -> None:
    # verify_present() self-acquires the outer Lockable lock, unlike get_values()/set_values()
    # (which require the caller to already hold it) - calling it from inside an existing
    # `async with fram:` block would otherwise hang the task forever, since asyncio.Lock isn't
    # reentrant. Timeout patched down so the test doesn't have to wait out the real default.
    fram, _chip = make_fram()
    run(setup_fram(fram))
    asy_fram_driver._VERIFY_PRESENT_LOCK_TIMEOUT_S = 0.01

    async def scenario() -> bool:
        async with fram:
            nested = await fram.verify_present()
        return nested

    try:
        result = run(scenario())
    finally:
        asy_fram_driver._VERIFY_PRESENT_LOCK_TIMEOUT_S = 1.0
    assert result is False
    assert fram.uninitialized is False  # a lock-busy timeout isn't a device-identification failure


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
        return await fram.set_write_protected(True)

    ok = run(scenario())
    assert ok is True
    assert chip.status & 0x8C == 0x8C  # protection itself was still applied and verified
    assert chip.wel is True  # left stuck, but reported (not silently dropped)


# ---------------------------------------------------------------------------
# Configuration matrix - constructor parameters, valid combos and edge/invalid values
# ---------------------------------------------------------------------------


def test_wp_and_wp_pin_combinations_all_construct_and_setup_cleanly() -> None:
    # All 4 combinations of the two independent wp/wp_pin parameters - each on its own is already
    # covered elsewhere; this locks in that every pairing (not just each parameter in isolation)
    # constructs and sets up without error, with the pin left in the datasheet-correct state.
    # setup() re-syncs _wp from the real (nonvolatile) status register rather than trusting the
    # constructor's wp= guess (see test_setup_resyncs_wp_from_nonvolatile_hardware_state_*), so
    # `wp` here is what the simulated hardware is seeded to already hold, not just a constructor
    # passthrough.
    for wp in (False, True):
        for wp_pin in (None, 7):
            fram, chip = make_fram(wp=wp, wp_pin=wp_pin)
            chip.status = 0x8C if wp else 0x00
            run(setup_fram(fram))
            assert fram.uninitialized is False
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


async def _get_and_set(fram: FRAM_SPI, data: bytes, addr: int) -> tuple[bool, bool]:
    async with fram:
        get_ok = await fram.get_values(bytearray(len(data)), addr)
        set_ok = await fram.set_values(data, addr)
    return get_ok, set_ok


def test_max_size_zero_or_negative_degrades_to_always_rejecting_access_not_a_crash() -> None:
    # Not a validated constructor parameter (int, enforced by the type system alone) - this locks
    # in that a nonsensical value degrades safely (every access rejected) rather than crashing.
    for max_size in (0, -1, -100):
        fram, _chip = make_fram(max_size=max_size)
        run(setup_fram(fram))
        get_ok, set_ok = run(_get_and_set(fram, b"x", 0))
        assert get_ok is False
        assert set_ok is False


def test_multiple_invalid_edge_values_combined_still_degrade_safely() -> None:
    # Several edge values together (not just one at a time): a nonsensical max_size alongside a
    # real wp/wp_pin configuration - each independent code path still behaves exactly as it does
    # in isolation, with no interaction/crash between them. Hardware is seeded to already be
    # protected (see test_wp_and_wp_pin_combinations_all_construct_and_setup_cleanly) since
    # setup() now syncs _wp from the real status register, not the wp= constructor guess.
    fram, chip = make_fram(max_size=-1, wp=True, wp_pin=7)
    chip.status = 0x8C
    run(setup_fram(fram))
    assert fram.uninitialized is False
    assert fram._wp_pin is not None
    assert fram._wp_pin.value() == 0  # wp=True -> WP driven low, independent of max_size
    get_ok, set_ok = run(_get_and_set(fram, b"x", 0))
    assert get_ok is False  # max_size=-1 rejects every access, as in isolation above
    assert set_ok is False


# ---------------------------------------------------------------------------
# Exception-safety: verify_present()'s missing uninitialized guard (found and fixed)
# ---------------------------------------------------------------------------


def test_verify_present_before_setup_returns_false_not_a_raised_runtimeerror() -> None:
    # Real gap found during an exception-safety review: every other public method here guards
    # `uninitialized` first and returns a clean False - verify_present() was the one exception,
    # letting SPIDevice's own "not set up" RuntimeError leak out uncaught if called before the
    # first setup() ever succeeded. Fixed to match every sibling method's contract.
    fram, _chip = make_fram()

    async def scenario() -> bool:
        return await fram.verify_present()

    assert run(scenario()) is False
    assert fram.uninitialized is True


# ---------------------------------------------------------------------------
# Deliberately-allowed exception paths - inherited from asy_spi_driver.py, never caught here
# ---------------------------------------------------------------------------


def test_construction_with_an_out_of_range_wp_pin_raises_uncaught_at_boot() -> None:
    # __init__ constructs a real Pin object for wp_pin - a one-time, at-boot misconfiguration is
    # allowed to raise loudly rather than silently produce a permanently nonfunctional driver
    # (same carve-out asy_spi_driver.py's own __init__ already established). 99 is outside the
    # real RP2040's GPIO0-28 range (tests/machine.py's fake Pin validates this).
    bus = make_bus()
    try:
        FRAM_SPI(bus, 1, logger=PrintLog(), wp_pin=99)
        raised = False
    except ValueError:
        raised = True
    assert raised


def test_construction_with_an_out_of_range_spi_cs_raises_uncaught_at_boot() -> None:
    # Same carve-out, for the required spi_cs parameter instead of the optional wp_pin.
    bus = make_bus()
    try:
        FRAM_SPI(bus, 99, logger=PrintLog())
        raised = False
    except ValueError:
        raised = True
    assert raised


def test_bus_deinit_mid_operation_raises_uncaught_runtimeerror() -> None:
    # The other deliberately-allowed path: if the underlying bus is deinitialized by something
    # else out from under an in-flight FRAM_SPI (not a hardware disturbance - a real electrical
    # disturbance never touches this Python-level lifecycle state, only an explicit .deinit()/
    # .init() call elsewhere does), SPIDevice.__aenter__'s own configure() call raises
    # RuntimeError, uncaught here, matching asy_spi_driver.py's own already-signed-off precedent
    # that this is the caller's responsibility, not this driver's.
    fram, _chip = make_fram()
    run(setup_fram(fram))
    fram._spidev.spi.deinit()

    async def scenario() -> bool:
        async with fram:
            ok = await fram.get_values(bytearray(1), 0)
        return ok

    try:
        run(scenario())
        raised = False
    except RuntimeError:
        raised = True
    assert raised


# ---------------------------------------------------------------------------
# Detection boundary - what this layer cannot catch, by design (not a bug)
# ---------------------------------------------------------------------------


def test_corrupted_write_payload_bytes_are_undetectable_at_this_layer_by_design() -> None:
    # This layer verifies opcodes/latches/device identity, never the payload bytes themselves -
    # raw SPI has no equivalent of a data-integrity check (see asy_spi_driver.py), which is
    # exactly why asy_fram_manager.py's CRC + dual-copy redundancy exists one layer up (see this
    # file's own module docstring). Proven here, not just asserted in prose: a payload byte that
    # lands wrong on the wire still reports a fully successful write.
    fram, chip = make_fram()
    run(setup_fram(fram))
    chip.corrupt_next_write_data = b"XXXX"  # what actually lands, regardless of what's sent

    async def scenario() -> bool:
        async with fram:
            ok = await fram.set_values(b"good", 0x00)
        return ok

    ok = run(scenario())
    assert ok is True  # the driver reports success - it has no way to know otherwise
    assert bytes(chip.memory[0x00:0x04]) == b"XXXX"  # but the real stored bytes are wrong


# ---------------------------------------------------------------------------
# Integration - real print_log.PrintLogHistory, real base_classes.Lockable concurrency/cancellation
# ---------------------------------------------------------------------------


def test_works_correctly_with_the_real_printloghistory_logger_used_in_production() -> None:
    # AsyFramManager passes a real PrintLogHistory (not a bare PrintLog) as logger in production -
    # this confirms FRAM_SPI's own narrower `PrintLog` type hint is genuinely satisfied by the
    # subclass in practice, not just assumed from the type hint, and that using it doesn't
    # interfere with FRAM_SPI's own behavior (FRAM_SPI never calls the subclass-only
    # err_s()/wrn_s() methods - a deliberate, unchanged design boundary, not tested here since
    # it isn't this file's contract to keep).
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


def test_two_operations_on_the_same_fram_never_run_concurrently() -> None:
    # FRAM_SPI's own outer Lockable lock (base_classes.py), not the SPI bus's - test_asy_spi_
    # driver.py already proves the bus-level lock serializes; this proves the same property one
    # level up, for the lock every real caller (asy_fram_manager.py) actually wraps chunk
    # operations in.
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
        assert fram.asy_lock.locked()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        assert not fram.asy_lock.locked()

    run(scenario())


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
