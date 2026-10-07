import asyncio
import errno
import struct

from machine import I2C as FakeI2C
from machine import Pin

import asy_i2c_driver
from asy_base_classes import COUNTER_CAP
from asy_i2c_driver import I2C, I2CDevice

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing isn't available on the real MicroPython test interpreter
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
    from typing import Any, ClassVar, TypeVar

    T = TypeVar("T")


def run(coro: "Coroutine[Any, Any, T]") -> "T":  # drives a coroutine to completion for these sync test_* functions
    return asyncio.run(coro)


# @tunable l1.asy_i2c_driver_gather_wait_s = 1.0
_GATHER_WAIT_S = 1.0
# @tunable l1.asy_i2c_driver_deadlock_wait_s = 0.2
_DEADLOCK_WAIT_S = 0.2
# @tunable l1.asy_i2c_driver_held_scl_timeout_us = 3000
_HELD_SCL_TIMEOUT_US = 3000  # a short bus timeout: a line that never releases ends the wait at it
# Mirrors of asy_i2c_driver's private _REC_* bits (a const() with a leading underscore is no module
# attribute on MicroPython); keep in sync with the driver.
_REC_SDA_LOW = 1
_REC_SDA_STUCK = 2
_REC_SCL_HELD = 4
_REC_NO_CONTROLLER = 8
_SCL, _SDA = 1, 0  # make_i2c()'s pins


def make_i2c(*, timeout: int | None = None) -> I2C:
    # A fresh static bus 0 and fresh lines (no per-test reset in this tier), its construction entry
    # dropped so a test's log assertions see only its own traffic; 0x50 is a register device.
    FakeI2C.reset_id(0)
    Pin.reset_registry()
    i2c = I2C(0, scl_pin=1, sda_pin=0, frequency=100000, timeout=timeout)
    fake(i2c).log.clear()
    fake(i2c).register_device(0x50)
    return i2c


def fake(i2c: I2C) -> FakeI2C:
    return i2c._i2c  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# init / deinit - dropping the reference IS the state change; the forwarded
# machine.I2C.deinit() is a no-op on rp2 (SPECIFICATION.md Part F.5)
# ---------------------------------------------------------------------------


def test_deinit_forwards_to_machine_i2c_and_drops_the_reference() -> None:
    i2c = make_i2c()
    mock = fake(i2c)
    assert i2c.deinit() is True
    assert mock.deinit_called is True  # forwarded, even though rp2 implements it as a no-op
    assert i2c._i2c is None  # this is what actually makes the wrapper report "bus unavailable"


def test_forwarded_machine_i2c_deinit_does_not_disable_the_underlying_bus() -> None:
    # Pins the real rp2 semantics the fake models: machine.I2C.deinit() leaves the .deinit slot NULL, so the
    # peripheral keeps running and every raw bus op still works. Only asy_i2c_driver.I2C's dropped reference
    # makes operations no-op - reattaching the same bus object proves nothing was torn down.
    i2c = make_i2c()
    mock = fake(i2c)
    mock.registers[(0x50, 0x00)] = bytearray(b"\x01\x02")
    assert i2c.deinit() is True
    mock.writeto(0x50, b"\x00", False)
    buf = bytearray(2)
    mock.readfrom_into(0x50, buf)
    assert buf == bytearray(b"\x01\x02")  # underlying bus still fully alive
    i2c._i2c = mock
    assert i2c.get_register_struct(0x50, 0x00, ">H") == 0x0102


def test_reinit_deinits_the_previous_bus_first() -> None:
    # rp2's machine.I2C(id) is one static object per id: a re-init deinits, then re-constructs that
    # same object, which keeps its devices.
    i2c = make_i2c()
    first = fake(i2c)
    i2c.init(0, scl_pin=1, sda_pin=0, frequency=100000)
    assert first.deinit_called is True
    assert fake(i2c) is first
    assert first.log == [("deinit",), ("init", 100000, 50000)]


def test_operations_after_deinit_return_false_or_none() -> None:
    i2c = make_i2c()
    mock = fake(i2c)
    i2c.deinit()
    logged = len(mock.log)
    assert i2c.scan() is None
    assert i2c.writeto(0x50, b"x") is None
    assert i2c.get_bits(0x50, 1, 0x00, 0) is None
    assert i2c.get_register_struct(0x50, 0x00, ">H") is None
    assert i2c.get_register_bytes(0x50, 0x00, 2) is None
    assert i2c.readfrom_into(0x50, bytearray(2)) is False
    assert i2c.set_bits(0x50, 1, 0x00, 0, 1) is False
    assert i2c.set_register_struct(0x50, 0x00, ">H", 1) is False
    assert i2c.writeto_then_readfrom(0x50, b"cmd", bytearray(2)) is False
    assert len(mock.log) == logged  # nothing reached the bus


def test_device_operations_on_an_already_deinitialized_bus_return_false_or_none() -> None:
    # Distinct from the mid-session case above: the bus is deinitialized before any session starts, and
    # every I2CDevice method is exercised directly rather than just readinto via a mid-session probe. A
    # never-initialized bus cannot be observed separately - I2C.__init__ always calls init() immediately.
    i2c = make_i2c()
    device = I2CDevice(i2c, 0x50)
    i2c.deinit()

    async def scenario() -> None:
        assert await device.write(b"x") is False
        assert await device.readinto(bytearray(2)) is False
        assert await device.write_then_readinto(b"cmd", bytearray(2)) is False
        assert await device.set_bits(1, 0x00, 0, 1) is False
        assert await device.get_bits(1, 0x00, 0) is None
        assert await device.set_register_struct(0x00, ">H", 1) is False
        assert await device.get_register_struct(0x00, ">H") is None
        assert await device.get_register_bytes(0x00, 2) is None

    run(scenario())


# ---------------------------------------------------------------------------
# scan / readfrom_into / writeto
# ---------------------------------------------------------------------------


def test_scan_reports_addresses_with_registers_minus_nak() -> None:
    i2c = make_i2c()
    fake(i2c).registers[(0x10, 0x00)] = bytearray(1)
    fake(i2c).registers[(0x20, 0x00)] = bytearray(1)
    fake(i2c).nak_addresses.add(0x20)
    assert i2c.scan() == [0x10]


def test_writeto_returns_ack_count_and_accepts_str() -> None:
    i2c = make_i2c()
    assert i2c.writeto(0x50, b"abc") == 3
    assert i2c.writeto(0x50, "abc") == 3
    assert fake(i2c).log[-1] == ("writeto", 0x50, b"abc", True)


def test_writeto_str_buffer_beyond_latin1_returns_none_instead_of_raising() -> None:
    # Found during review: the str convenience path assumes one byte per character
    # (bytes([ord(x) for x in buffer])) - a real Unicode codepoint above 255 used to raise an
    # uncaught ValueError here, even though `str` itself places no such restriction.
    i2c = make_i2c()
    assert i2c.writeto(0x50, "aሴb") is None
    assert len(fake(i2c).log) == 0  # rejected before ever touching the bus


def test_readfrom_into_and_writeto_respect_start_end_slice() -> None:
    i2c = make_i2c()
    buf = bytearray(b"\x00\x00\x00\x00")
    assert i2c.readfrom_into(0x50, buf, start=1, end=3) is True
    assert fake(i2c).log[-1][0] == "readfrom_into"
    i2c.writeto(0x50, b"XYZ", start=1, end=3)
    assert fake(i2c).log[-1] == ("writeto", 0x50, b"YZ", True)


def test_writeto_then_readfrom_forwards_both() -> None:
    i2c = make_i2c()
    assert i2c.writeto_then_readfrom(0x50, b"cmd", bytearray(2)) is True
    ops = [entry[0] for entry in fake(i2c).log]
    assert ops == ["writeto", "readfrom_into"]


def test_real_bus_failure_propagates_as_oserror() -> None:
    i2c = make_i2c()
    fake(i2c).nak_addresses.add(0x77)
    try:
        i2c.writeto(0x77, b"x")
        raised = False
    except OSError:
        raised = True
    assert raised
    try:
        i2c.scan()  # scan() itself doesn't touch a single address, must not raise
    except OSError:
        raise AssertionError("scan() must not raise for an unrelated nak'd address") from None


# ---------------------------------------------------------------------------
# get_bits / set_bits - bit-field round trips and range guards
# ---------------------------------------------------------------------------


def test_get_set_bits_round_trip_single_byte() -> None:
    i2c = make_i2c()
    i2c.set_bits(0x50, 3, 0x10, 2, 0x5, reg_width=1)
    assert i2c.get_bits(0x50, 3, 0x10, 2, reg_width=1) == 0x5


def test_get_set_bits_round_trip_multi_byte_lsb_first() -> None:
    i2c = make_i2c()
    i2c.set_bits(0x50, 4, 0x10, 4, 0xA, reg_width=2, lsb_first=True)
    assert fake(i2c).registers[(0x50, 0x10)] == bytearray([0xA0, 0x00])
    assert i2c.get_bits(0x50, 4, 0x10, 4, reg_width=2, lsb_first=True) == 0xA


def test_get_set_bits_round_trip_multi_byte_msb_first() -> None:
    i2c = make_i2c()
    i2c.set_bits(0x50, 4, 0x10, 4, 0xA, reg_width=2, lsb_first=False)
    assert fake(i2c).registers[(0x50, 0x10)] == bytearray([0x00, 0xA0])
    assert i2c.get_bits(0x50, 4, 0x10, 4, reg_width=2, lsb_first=False) == 0xA


def test_get_bits_leaves_surrounding_bits_untouched() -> None:
    i2c = make_i2c()
    fake(i2c).registers[(0x50, 0x10)] = bytearray([0xFF])
    i2c.set_bits(0x50, 3, 0x10, 2, 0x0, reg_width=1)  # clear only bits 2-4
    assert fake(i2c).registers[(0x50, 0x10)] == bytearray([0b11100011])


def test_get_bits_rejects_out_of_range_bitfield() -> None:
    i2c = make_i2c()
    assert i2c.get_bits(0x50, 0, 0x10, 0, reg_width=1) is None  # num_bits <= 0
    assert i2c.get_bits(0x50, 1, 0x10, -1, reg_width=1) is None  # start_bit < 0
    assert i2c.get_bits(0x50, 4, 0x10, 6, reg_width=1) is None  # runs past reg_width*8
    assert i2c.get_bits(0x50, 1, 0x10, 0, reg_width=0) is None  # reg_width <= 0


def test_set_bits_rejects_out_of_range_bitfield_without_touching_bus() -> None:
    i2c = make_i2c()
    i2c.set_bits(0x50, 0, 0x10, 0, 1, reg_width=1)
    i2c.set_bits(0x50, 4, 0x10, 6, 1, reg_width=1)
    assert len(fake(i2c).log) == 0  # rejected before any readfrom_mem/writeto_mem


def test_get_bits_boundary_full_register_accepted() -> None:
    i2c = make_i2c()
    i2c.set_bits(0x50, 8, 0x10, 0, 0xFF, reg_width=1)
    assert i2c.get_bits(0x50, 8, 0x10, 0, reg_width=1) == 0xFF


# ---------------------------------------------------------------------------
# get_register_struct / set_register_struct - byte order from reg_format alone
# ---------------------------------------------------------------------------


def test_register_struct_round_trip_respects_format_byte_order() -> None:
    i2c = make_i2c()
    i2c.set_register_struct(0x50, 0x20, ">H", 0x1234)
    assert fake(i2c).registers[(0x50, 0x20)] == bytearray(b"\x12\x34")
    assert i2c.get_register_struct(0x50, 0x20, ">H") == 0x1234


def test_register_struct_round_trip_little_endian() -> None:
    i2c = make_i2c()
    i2c.set_register_struct(0x50, 0x20, "<H", 0x1234)
    assert fake(i2c).registers[(0x50, 0x20)] == bytearray(b"\x34\x12")
    assert i2c.get_register_struct(0x50, 0x20, "<H") == 0x1234


def test_register_struct_malformed_format_returns_none_and_noop() -> None:
    i2c = make_i2c()
    assert i2c.get_register_struct(0x50, 0x20, "Y") is None  # not a real struct format char
    assert i2c.set_register_struct(0x50, 0x20, "Y", 1) is False
    assert len(fake(i2c).log) == 0


class _FakeStruct:
    # get_register_struct()'s calcsize() and unpack() try/except pair share the same format-string parsing
    # in real MicroPython: any reg_format bad enough to raise out of unpack() already raises out of
    # calcsize() first, both rejecting "Y" identically.
    #
    # So the unpack()-specific except, and the "unpacked value is not int/float/bytes" fallback below it,
    # are unreachable through any real malformed format string - faked here by substituting asy_i2c_driver's
    # own module-level `struct` name, as this project's other suites do.
    def __init__(self, unpack_result: "tuple[Any, ...] | Exception") -> None:
        self._unpack_result = unpack_result

    def calcsize(self, fmt: str) -> int:
        return struct.calcsize(fmt)

    def unpack(self, _fmt: str, _buf: object) -> "tuple[Any, ...]":  # struct.unpack()'s own two
        # arguments are positional-only (a C function), so nothing can name them at a call site.
        if isinstance(self._unpack_result, Exception):
            raise self._unpack_result
        return self._unpack_result

    def pack_into(self, fmt: str, buf: object, offset: int, *values: object) -> None:
        struct.pack_into(fmt, buf, offset, *values)


def test_get_register_struct_returns_none_when_unpack_itself_raises() -> None:
    i2c = make_i2c()
    fake(i2c).registers[(0x50, 0x20)] = bytearray(b"\x12\x34")
    original_struct = asy_i2c_driver.struct
    asy_i2c_driver.struct = _FakeStruct(ValueError("simulated malformed-format failure"))  # type: ignore[assignment]
    try:
        result = i2c.get_register_struct(0x50, 0x20, ">H")
    finally:
        asy_i2c_driver.struct = original_struct
    assert result is None


def test_get_register_struct_returns_none_when_unpacked_value_is_the_wrong_type() -> None:
    i2c = make_i2c()
    fake(i2c).registers[(0x50, 0x20)] = bytearray(b"\x12\x34")
    original_struct = asy_i2c_driver.struct
    asy_i2c_driver.struct = _FakeStruct(("not-a-number",))  # type: ignore[assignment]
    try:
        result = i2c.get_register_struct(0x50, 0x20, ">H")
    finally:
        asy_i2c_driver.struct = original_struct
    assert result is None


def test_set_register_struct_value_out_of_range_truncates_silently() -> None:
    # Confirmed directly against the real interpreter: MicroPython's struct.pack silently
    # truncates an out-of-range value (unlike CPython's struct.error) - set_register_struct's
    # try/except only ever catches a malformed reg_format, never an overflow.
    i2c = make_i2c()
    i2c.set_register_struct(0x50, 0x20, "B", 999)  # doesn't fit in a byte
    assert fake(i2c).registers[(0x50, 0x20)] == bytearray(struct.pack("B", 999))


def test_get_register_struct_float_format() -> None:
    i2c = make_i2c()
    fake(i2c).registers[(0x50, 0x20)] = bytearray(struct.pack("f", 1.5))
    assert i2c.get_register_struct(0x50, 0x20, "f") == 1.5


def test_set_register_struct_accepts_an_actual_float_value() -> None:
    # Found during review: value used to be typed int-only, so mypy would reject a real
    # fractional float even though struct.pack itself handles it fine - not just an int that
    # happens to auto-coerce.
    i2c = make_i2c()
    i2c.set_register_struct(0x50, 0x20, "f", 3.25)
    assert i2c.get_register_struct(0x50, 0x20, "f") == 3.25


def test_set_get_register_struct_float_round_trips_nan_and_inf() -> None:
    # Confirmed directly: struct.pack("f", ...) never raises for NaN/+-inf, unlike an
    # out-of-range int against a float format - these are valid float bit patterns, and a real
    # sensor fault could plausibly produce one (SPECIFICATION.md Part D.12).
    i2c = make_i2c()
    i2c.set_register_struct(0x50, 0x20, "f", float("nan"))
    result = i2c.get_register_struct(0x50, 0x20, "f")
    assert isinstance(result, float) and result != result  # NaN != NaN is the standard check
    i2c.set_register_struct(0x50, 0x20, "f", float("inf"))
    assert i2c.get_register_struct(0x50, 0x20, "f") == float("inf")
    i2c.set_register_struct(0x50, 0x20, "f", float("-inf"))
    assert i2c.get_register_struct(0x50, 0x20, "f") == float("-inf")


def test_set_get_register_struct_bytes_round_trip() -> None:
    # Found during review: value used to be typed int-only, making it impossible to write back
    # a bytes-format register at all, even though get_register_struct can read one - a real
    # read/write asymmetry, not just a type-annotation nicety.
    i2c = make_i2c()
    i2c.set_register_struct(0x50, 0x20, "4s", b"data")
    assert fake(i2c).registers[(0x50, 0x20)] == bytearray(b"data")
    assert i2c.get_register_struct(0x50, 0x20, "4s") == b"data"


def test_set_register_struct_accepts_bytearray_for_bytes_formats() -> None:
    i2c = make_i2c()
    i2c.set_register_struct(0x50, 0x20, "4s", bytearray(b"data"))
    assert i2c.get_register_struct(0x50, 0x20, "4s") == b"data"


def test_set_register_struct_type_mismatch_returns_false_instead_of_raising() -> None:
    # Found during review: struct.pack raises TypeError, not ValueError, when value's type does not match
    # what reg_format expects - previously uncaught, a real "never raises" contract violation for an in-
    # contract call, not an out-of-domain input the type system already excluded.
    i2c = make_i2c()
    assert i2c.set_register_struct(0x50, 0x20, "4s", 5) is False  # int value, bytes-type format
    assert len(fake(i2c).log) == 0  # rejected before ever touching the bus
    assert i2c.set_register_struct(0x50, 0x20, "f", b"x") is False  # bytes value, float-type format
    assert len(fake(i2c).log) == 0


# ---------------------------------------------------------------------------
# I2CDevice - address binding, shared locking, probing
# ---------------------------------------------------------------------------


def test_device_shares_the_bus_lock() -> None:
    i2c = make_i2c()
    device = I2CDevice(i2c, 0x50)
    assert device.session_lock is i2c.bus_lock


def test_device_context_manager_acquires_and_releases_lock() -> None:
    i2c = make_i2c()
    device = I2CDevice(i2c, 0x50)

    async def scenario() -> None:
        assert not i2c.bus_lock.locked()
        async with device:
            assert i2c.bus_lock.locked()
        assert not i2c.bus_lock.locked()

    run(scenario())


def test_probe_succeeds_when_device_acks() -> None:
    i2c = make_i2c()
    device = I2CDevice(i2c, 0x50)
    assert run(device.setup()) is True


def test_probe_raises_value_error_when_device_missing() -> None:
    i2c = make_i2c()
    fake(i2c).nak_addresses.add(0x50)
    device = I2CDevice(i2c, 0x50)
    try:
        run(device.setup())
        message = ""
    except ValueError as e:
        message = str(e)
    assert message == f"no I2C device at address: {0x50:#x}"


def test_probe_raises_runtime_error_when_bus_uninitialized() -> None:
    i2c = make_i2c()
    i2c.deinit()
    device = I2CDevice(i2c, 0x50)
    try:
        run(device.setup())
        raised = False
    except RuntimeError:
        raised = True
    assert raised


def test_device_readinto_and_write_use_device_address() -> None:
    i2c = make_i2c()
    device = I2CDevice(i2c, 0x50)
    assert run(device.write(b"cmd")) is True
    assert fake(i2c).log[-1] == ("writeto", 0x50, b"cmd", True)
    assert run(device.readinto(bytearray(2))) is True
    assert fake(i2c).log[-1][0:2] == ("readfrom_into", 0x50)


def test_device_write_then_readinto_forwards_both() -> None:
    i2c = make_i2c()
    device = I2CDevice(i2c, 0x50)
    run(device.write_then_readinto(b"cmd", bytearray(2)))
    ops = [entry[0] for entry in fake(i2c).log]
    assert ops == ["writeto", "readfrom_into"]


def test_device_get_set_bits_round_trip() -> None:
    i2c = make_i2c()
    device = I2CDevice(i2c, 0x50)
    run(device.set_bits(3, 0x10, 2, 0x5, reg_width=1))
    assert run(device.get_bits(3, 0x10, 2, reg_width=1)) == 0x5


def test_device_get_set_register_struct_round_trip() -> None:
    i2c = make_i2c()
    device = I2CDevice(i2c, 0x50)
    run(device.set_register_struct(0x20, ">H", 0xBEEF))
    assert run(device.get_register_struct(0x20, ">H")) == 0xBEEF


# ---------------------------------------------------------------------------
# I2C-standard bus fault conditions (real RP2040 errno: EIO / ETIMEDOUT) -
# successful vs failed transfers, at both the I2C and I2CDevice layers
# ---------------------------------------------------------------------------


def test_nak_surfaces_as_eio_matching_real_rp2040_behavior() -> None:
    # Confirmed against ports/rp2/machine_i2c.c: real hardware I2C raises OSError(EIO) for a
    # NAK'd/non-responding device, not ENODEV (that's SoftI2C-specific, a different code path).
    i2c = make_i2c()
    fake(i2c).nak_addresses.add(0x50)
    try:
        i2c.writeto(0x50, b"x")
        raised_errno = None
    except OSError as e:
        raised_errno = e.errno
    assert raised_errno == errno.EIO


def test_bus_busy_surfaces_as_etimedout() -> None:
    # Models a stuck bus / clock stretched too long: the Pico SDK's own timeout, confirmed as
    # OSError(ETIMEDOUT) against ports/rp2/machine_i2c.c. Checked across every op that touches
    # the bus, not just one, since each has its own guard.
    i2c = make_i2c()
    fake(i2c).busy = True
    ops = (
        i2c.scan,
        lambda: i2c.writeto(0x50, b"x"),
        lambda: i2c.readfrom_into(0x50, bytearray(1)),
        lambda: i2c.get_bits(0x50, 1, 0x00, 0),
    )
    for op in ops:
        try:
            op()
            raised_errno = None
        except OSError as e:
            raised_errno = e.errno
        assert raised_errno == errno.ETIMEDOUT


def test_write_half_of_writeto_then_readfrom_can_succeed_while_read_half_fails() -> None:
    # Models a transfer interrupted partway through: the write completes (and is logged) but
    # the subsequent read fails - the two are genuinely separate bus transactions at this layer,
    # not one atomic operation with rollback.
    i2c = make_i2c()
    fake(i2c).inject_fault("readfrom_into", OSError(errno.EIO, "no ACK"))
    try:
        i2c.writeto_then_readfrom(0x50, b"cmd", bytearray(2))
        raised = False
    except OSError:
        raised = True
    assert raised
    assert fake(i2c).log[0][0] == "writeto"  # the write side genuinely went out before the failure


def test_device_probe_converts_any_oserror_to_value_error() -> None:
    # Both real failure modes (EIO/ETIMEDOUT) collapse to the same "no device" message today -
    # documents existing behavior, not a claim that a bus timeout specifically means "no device".
    i2c = make_i2c()
    device = I2CDevice(i2c, 0x50)
    fake(i2c).busy = True
    try:
        run(device.setup())
        raised = False
    except ValueError:
        raised = True
    assert raised


def test_get_bits_propagates_bus_fault() -> None:
    i2c = make_i2c()
    fake(i2c).nak_addresses.add(0x50)
    try:
        i2c.get_bits(0x50, 1, 0x10, 0, reg_width=1)
        raised = False
    except OSError:
        raised = True
    assert raised


def test_set_bits_read_half_can_fail_before_any_write_is_attempted() -> None:
    i2c = make_i2c()
    fake(i2c).inject_fault("readfrom_into", OSError(errno.EIO, "no ACK"), match=0x10)
    try:
        i2c.set_bits(0x50, 3, 0x10, 0, 0x5, reg_width=1)
        raised = False
    except OSError:
        raised = True
    assert raised
    assert fake(i2c).log == [("writeto", 0x50, b"\x10", False)]  # the pointer only: never reached the write


def test_set_bits_write_half_can_fail_after_read_half_succeeds() -> None:
    i2c = make_i2c()
    mock = fake(i2c)
    real_writeto = mock.writeto

    def fail_the_register_write(address: int, buf: object, stop: bool = True) -> int:  # noqa: FBT001, FBT002  # machine.I2C's own positional stop
        if stop:  # the pointer write of the read half is no-stop; the register write is the one with a stop
            raise OSError(errno.EIO, "no ACK")
        return real_writeto(address, buf, stop)

    mock.writeto = fail_the_register_write  # type: ignore[method-assign]
    try:
        i2c.set_bits(0x50, 3, 0x10, 0, 0x5, reg_width=1)
        raised = False
    except OSError:
        raised = True
    assert raised
    assert [entry[0] for entry in mock.log] == ["writeto", "readfrom_into"]  # the read did happen first


# ---------------------------------------------------------------------------
# Regular bus conditions: stop/repeated-start, deinit/reinit (including mid-session)
# ---------------------------------------------------------------------------


def test_stop_flag_propagates_for_repeated_start_sequences() -> None:
    i2c = make_i2c()
    i2c.writeto(0x50, b"reg", stop=False)  # repeated start: no STOP between write and read
    assert fake(i2c).log[-1] == ("writeto", 0x50, b"reg", False)
    i2c.readfrom_into(0x50, bytearray(2), stop=True)
    assert fake(i2c).log[-1][-1] is True


def test_writeto_then_readfrom_defaults_to_stop_true_both_legs() -> None:
    i2c = make_i2c()
    i2c.writeto_then_readfrom(0x50, b"cmd", bytearray(2))
    assert fake(i2c).log[0][-1] is True
    assert fake(i2c).log[1][-1] is True


def test_double_deinit_is_idempotent() -> None:
    i2c = make_i2c()
    mock = fake(i2c)
    i2c.deinit()
    i2c.deinit()  # the wrapper's own `is not None` guard, not anything the hardware enforces
    assert mock.deinit_count == 1


def test_deinit_mid_session_degrades_later_ops_in_the_same_session_cleanly() -> None:
    # A bus torn down (e.g. by unrelated code) while a device session is still open must not
    # crash the rest of that session - later ops on the same still-open session cleanly no-op.
    i2c = make_i2c()
    device = I2CDevice(i2c, 0x50)

    async def scenario() -> bytearray:
        buf = bytearray(b"\x55\x55")
        async with device:
            assert await device.write(b"first") is True
            i2c.deinit()
            assert await device.readinto(buf) is False
        return buf

    result = run(scenario())
    assert result == bytearray(b"\x55\x55")  # untouched: no transfer


def test_reinit_mid_session_re_constructs_the_same_static_bus() -> None:
    # rp2's machine.I2C(id) is one static object per id, as the fake models it: the re-init goes through
    # deinit() and a re-construction of that object, between the session's two writes.
    i2c = make_i2c()
    device = I2CDevice(i2c, 0x50)
    old_mock = fake(i2c)

    async def scenario() -> None:
        async with device:
            await device.write(b"first")
            i2c.init(0, scl_pin=1, sda_pin=0, frequency=100000)
            await device.write(b"second")

    run(scenario())
    assert fake(i2c) is old_mock
    assert old_mock.log == [("writeto", 0x50, b"first", True), ("deinit",), ("init", 100000, 50000), ("writeto", 0x50, b"second", True)]


# ---------------------------------------------------------------------------
# Sessions: single- vs multi-transfer within one lock acquisition, and across
# separate sequential sessions
# ---------------------------------------------------------------------------


def test_single_op_session_releases_lock_immediately_after() -> None:
    i2c = make_i2c()
    device = I2CDevice(i2c, 0x50)

    async def scenario() -> None:
        async with device:
            await device.write(b"x")
        assert not i2c.bus_lock.locked()

    run(scenario())


def test_multi_transfer_session_holds_the_lock_across_every_transfer() -> None:
    i2c = make_i2c()
    device = I2CDevice(i2c, 0x50)

    async def scenario() -> None:
        async with device:
            await device.write(b"cmd1")
            assert i2c.bus_lock.locked()
            await device.readinto(bytearray(2))
            assert i2c.bus_lock.locked()
            await device.write(b"cmd2")
            assert i2c.bus_lock.locked()
        assert not i2c.bus_lock.locked()
        ops = [entry[0] for entry in fake(i2c).log]
        assert ops == ["writeto", "readfrom_into", "writeto"]

    run(scenario())


def test_sequential_sessions_do_not_leak_lock_state_between_them() -> None:
    i2c = make_i2c()
    device = I2CDevice(i2c, 0x50)

    async def scenario() -> None:
        for _ in range(3):
            async with device:
                await device.write(b"x")
            assert not i2c.bus_lock.locked()

    run(scenario())
    assert len(fake(i2c).log) == 3


def test_device_operations_do_not_self_lock_caller_must_wrap_in_async_with() -> None:
    # I2CDevice's read and write methods never acquire self.session_lock themselves - by design, every real
    # caller wraps them in `async with device:`. This makes an easy-to-miss division of responsibility
    # explicit: locking is the caller's job, not something write()/readinto() provide.
    i2c = make_i2c()
    device = I2CDevice(i2c, 0x50)

    async def scenario() -> None:
        await device.write(b"x")  # no `async with device:` wrapper at all
        assert not i2c.bus_lock.locked()  # never touched: write() itself doesn't lock

    run(scenario())


# ---------------------------------------------------------------------------
# asyncio interlock: concurrent bus requests must serialize through the shared lock
# ---------------------------------------------------------------------------


def test_two_devices_sharing_a_bus_never_run_concurrently() -> None:
    i2c = make_i2c()
    device_a = I2CDevice(i2c, 0x50)
    device_b = I2CDevice(i2c, 0x60)
    concurrent = 0
    max_concurrent = 0

    async def worker(device: I2CDevice) -> None:
        nonlocal concurrent, max_concurrent
        async with device:
            concurrent += 1
            max_concurrent = max(max_concurrent, concurrent)
            await asyncio.sleep(0)  # yield - if the lock didn't serialize, the other task runs here
            concurrent -= 1

    async def scenario() -> None:
        await asyncio.gather(worker(device_a), worker(device_b))

    run(scenario())
    assert max_concurrent == 1


def test_four_concurrent_sessions_all_complete_and_stay_serialized() -> None:
    i2c = make_i2c()
    devices = [I2CDevice(i2c, addr) for addr in (0x10, 0x20, 0x30, 0x40)]
    concurrent = 0
    max_concurrent = 0
    completed = 0

    async def worker(device: I2CDevice) -> None:
        nonlocal concurrent, max_concurrent, completed
        async with device:
            concurrent += 1
            max_concurrent = max(max_concurrent, concurrent)
            await asyncio.sleep(0)
            concurrent -= 1
            completed += 1

    async def scenario() -> None:
        await asyncio.wait_for(asyncio.gather(*(worker(d) for d in devices)), _GATHER_WAIT_S)

    run(scenario())
    assert max_concurrent == 1
    assert completed == 4  # no starvation - every waiter eventually got the lock


def test_same_device_used_from_two_concurrent_tasks_serializes_too() -> None:
    i2c = make_i2c()
    device = I2CDevice(i2c, 0x50)
    concurrent = 0
    max_concurrent = 0

    async def worker() -> None:
        nonlocal concurrent, max_concurrent
        async with device:
            concurrent += 1
            max_concurrent = max(max_concurrent, concurrent)
            await asyncio.sleep(0)
            concurrent -= 1

    async def scenario() -> None:
        await asyncio.gather(worker(), worker())

    run(scenario())
    assert max_concurrent == 1


# ---------------------------------------------------------------------------
# Interrupted transfers: exceptions and task cancellation while a session is open
# ---------------------------------------------------------------------------


def test_exception_inside_session_still_releases_the_lock() -> None:
    i2c = make_i2c()
    device = I2CDevice(i2c, 0x50)

    def boom() -> None:  # raised from a helper, so the raise isn't lexically inside the try below
        raise RuntimeError("boom")

    async def scenario() -> None:
        try:
            async with device:
                boom()
        except RuntimeError:
            pass
        assert not i2c.bus_lock.locked()
        async with device:  # must still be acquirable - not left stuck locked
            pass

    run(scenario())


def test_context_manager_does_not_suppress_exceptions() -> None:
    i2c = make_i2c()
    device = I2CDevice(i2c, 0x50)

    async def scenario() -> None:
        async with device:
            raise ValueError("boom")

    try:
        run(scenario())
        raised = False
    except ValueError:
        raised = True
    assert raised


def test_aexit_tolerates_a_lock_already_released_inside_the_block() -> None:
    i2c = make_i2c()
    device = I2CDevice(i2c, 0x50)

    async def scenario() -> None:
        async with device:
            device.session_lock.release()  # released early by hand
        # __aexit__'s own release() must swallow the resulting RuntimeError, not propagate it

    run(scenario())  # must not raise
    assert not i2c.bus_lock.locked()


def test_task_cancellation_while_holding_the_lock_still_releases_it() -> None:
    # Interrupts a transfer via real asyncio cancellation (not just an exception raised by our
    # own code) - confirmed directly that MicroPython's asyncio still runs __aexit__ via
    # CancelledError propagating through `async with`, same as CPython.
    i2c = make_i2c()
    device = I2CDevice(i2c, 0x50)
    started = False

    async def holder() -> None:
        nonlocal started
        async with device:
            started = True
            await asyncio.sleep(10)

    async def scenario() -> None:
        task = asyncio.create_task(holder())
        while not started:
            await asyncio.sleep(0)
        assert i2c.bus_lock.locked()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        assert not i2c.bus_lock.locked()

    run(scenario())


def test_reentrant_acquisition_on_the_same_device_deadlocks_and_cleans_up() -> None:
    # Not reentrant by design, being a plain asyncio.Lock: nesting `async with device:` on one device within
    # one task deadlocks rather than silently succeeding, bounded by wait_for so the test cannot hang. It
    # raises TimeoutError and still leaves the lock released, wait_for's cancellation unwinding it.
    i2c = make_i2c()
    device = I2CDevice(i2c, 0x50)

    async def reentrant() -> None:
        async with device, device:
            pass

    async def scenario() -> bool:
        try:
            await asyncio.wait_for(reentrant(), _DEADLOCK_WAIT_S)
        except asyncio.TimeoutError:
            return True
        else:
            return False

    assert run(scenario())
    assert not i2c.bus_lock.locked()


def test_aenter_returns_the_device_itself() -> None:
    i2c = make_i2c()
    device = I2CDevice(i2c, 0x50)

    async def scenario() -> None:
        async with device as entered:
            assert entered is device

    run(scenario())


# ---------------------------------------------------------------------------
# Invalid parameters and buffer/slice edge cases
# ---------------------------------------------------------------------------


def test_start_end_slicing_clamps_gracefully_never_raises() -> None:
    # Confirmed directly against the real interpreter: memoryview slicing clamps out-of-range
    # start/end exactly like plain bytes/list slicing (no IndexError/ValueError), so these can
    # never actually crash readfrom_into/writeto - not just assumed safe.
    i2c = make_i2c()
    buf = bytearray(b"ABCD")
    i2c.readfrom_into(0x50, buf, start=1, end=100)  # end far beyond buffer length
    assert fake(i2c).log[-1][0] == "readfrom_into"
    i2c.writeto(0x50, b"ABCD", start=3, end=1)  # start > end -> empty slice, not an error
    assert fake(i2c).log[-1] == ("writeto", 0x50, b"", True)


def test_zero_length_buffer_operations_are_harmless() -> None:
    i2c = make_i2c()
    i2c.readfrom_into(0x50, bytearray(0))  # must not raise
    assert i2c.writeto(0x50, b"") == 0


def test_empty_reg_format_returns_none_instead_of_raising() -> None:
    # A real gap found by testing: struct.unpack("", ...) returns an empty
    # tuple, so indexing [0] unconditionally used to raise IndexError for this legitimate (if
    # degenerate) reg_format - fixed to return None like any other non-hardware failure.
    i2c = make_i2c()
    assert i2c.get_register_struct(0x50, 0x20, "") is None
    i2c.set_register_struct(0x50, 0x20, "", 1)  # must not raise either


def test_pad_byte_only_reg_format_returns_none() -> None:
    # Same empty-tuple gap, reached via a nonzero-calcsize format that still has zero data
    # fields (confirmed: calcsize("2x") == 2, but unpack("2x", ...) == ()) - a size>0 guard
    # alone would have missed this.
    i2c = make_i2c()
    assert i2c.get_register_struct(0x50, 0x20, "2x") is None


def test_set_register_struct_multi_field_format_silently_zero_pads_missing_values() -> None:
    # Documents a real MicroPython-specific quirk, not a bug in this driver: struct.pack silently zero-fills
    # a field this single-value method never supplies, rather than raising as CPython's struct.error would.
    # set_register_struct is deliberately single-value-only; this is what a multi-field format does anyway.
    i2c = make_i2c()
    i2c.set_register_struct(0x50, 0x20, ">HH", 5)
    assert fake(i2c).registers[(0x50, 0x20)] == bytearray(struct.pack(">HH", 5, 0))


def test_out_of_range_address_is_transparently_forwarded_not_validated() -> None:
    # This driver deliberately doesn't range-check `address` itself (SPECIFICATION.md Part D.2's
    # "don't defend against out-of-contract input" - the type contract is plain `int`; address
    # validity is the real machine.I2C's job, mirrored by the mock rather than duplicated here).
    i2c = make_i2c()
    assert i2c.writeto(200, b"x") == 1  # not a valid 7-bit address, but not rejected here either
    assert fake(i2c).log[-1][1] == 200


# ---------------------------------------------------------------------------
# timeout / addrsize - optional, forwarded only when given (no default drift)
# ---------------------------------------------------------------------------


def test_timeout_omitted_leaves_the_bus_default_untouched() -> None:
    i2c = make_i2c()
    assert fake(i2c).timeout == 50000  # the mock's (and real machine.I2C's) own default


def test_timeout_explicit_value_is_forwarded() -> None:
    i2c = make_i2c(timeout=12345)
    assert fake(i2c).timeout == 12345


def test_addrsize_omitted_writes_one_address_byte() -> None:
    # A register read is a no-stop address write then a read, as read_mem() issues it on rp2; 8 bits is
    # machine.I2C's own default address size.
    i2c = make_i2c()
    fake(i2c).registers[(0x50, 0x10)] = bytearray([0x07])
    assert i2c.get_bits(0x50, 3, 0x10, 0, reg_width=1) == 0x07
    assert fake(i2c).log == [("writeto", 0x50, b"\x10", False), ("readfrom_into", 0x50, b"\x07", True)]
    fake(i2c).log.clear()
    i2c.set_register_struct(0x50, 0x10, "B", 0x42, addrsize=8)
    assert fake(i2c).log == [("writeto", 0x50, b"\x10\x42", True)]


def test_addrsize_16_writes_two_address_bytes_most_significant_first() -> None:
    i2c = make_i2c()
    fake(i2c).register_device(0x50, addrsize=16)
    assert i2c.set_bits(0x50, 3, 0x0110, 0, 0x5, reg_width=1, addrsize=16) is True
    assert fake(i2c).log == [
        ("writeto", 0x50, b"\x01\x10", False),
        ("readfrom_into", 0x50, b"\x00", True),
        ("writeto", 0x50, b"\x01\x10\x05", True),
    ]
    assert i2c.get_bits(0x50, 3, 0x0110, 0, reg_width=1, addrsize=16) == 0x5
    fake(i2c).log.clear()
    assert i2c.set_register_struct(0x50, 0x0110, ">H", 0x1234, addrsize=16) is True
    assert fake(i2c).log == [("writeto", 0x50, b"\x01\x10\x12\x34", True)]
    assert i2c.get_register_struct(0x50, 0x0110, ">H", addrsize=16) == 0x1234


def test_an_addrsize_machine_i2c_refuses_still_raises_value_error() -> None:
    # machine.I2C's fill_memaddr_buf() raises for a non-multiple of 8 or more than 32 bits; the helpers keep that.
    i2c = make_i2c()
    for addrsize in (12, 40):
        try:
            i2c.get_register_bytes(0x50, 0x10, 1, addrsize)
            raised = False
        except ValueError:
            raised = True
        assert raised, addrsize
    assert fake(i2c).log == []


def test_device_forwards_addrsize_for_bits_and_struct() -> None:
    i2c = make_i2c()
    fake(i2c).register_device(0x50, addrsize=16)
    device = I2CDevice(i2c, 0x50)
    assert run(device.set_bits(3, 0x10, 0, 0x5, reg_width=1, addrsize=16)) is True
    assert fake(i2c).log[-1] == ("writeto", 0x50, b"\x00\x10\x05", True)
    assert run(device.set_register_struct(0x20, ">H", 0x1234, addrsize=16)) is True
    assert fake(i2c).log[-1] == ("writeto", 0x50, b"\x00\x20\x12\x34", True)
    assert run(device.get_register_bytes(0x20, 2, addrsize=16)) == b"\x12\x34"


# ---------------------------------------------------------------------------
# writeto_then_readfrom / write_then_readinto - independent out_stop/in_stop
# ---------------------------------------------------------------------------


def test_out_stop_and_in_stop_are_independent() -> None:
    # The real point of this method: a repeated-start register read (no stop between the write
    # and the read) while still stopping normally after the read - previously inexpressible
    # since one shared `stop` forced both legs to the same value.
    i2c = make_i2c()
    assert i2c.writeto_then_readfrom(0x50, b"reg", bytearray(2), out_stop=False, in_stop=True) is True
    assert fake(i2c).log[0] == ("writeto", 0x50, b"reg", False)
    assert fake(i2c).log[1][-1] is True


def test_writeto_then_readfrom_defaults_are_unchanged() -> None:
    # Both legs still default to stop=True (two separate transactions) - the fix only adds the
    # ability to override each leg independently, it doesn't change default behavior.
    i2c = make_i2c()
    i2c.writeto_then_readfrom(0x50, b"cmd", bytearray(2))
    assert fake(i2c).log[0][-1] is True
    assert fake(i2c).log[1][-1] is True


def test_device_write_then_readinto_forwards_out_stop_and_in_stop() -> None:
    i2c = make_i2c()
    device = I2CDevice(i2c, 0x50)
    run(device.write_then_readinto(b"reg", bytearray(2), out_stop=False, in_stop=True))
    assert fake(i2c).log[0] == ("writeto", 0x50, b"reg", False)
    assert fake(i2c).log[1][-1] is True


# ---------------------------------------------------------------------------
# set_bits - an oversized value must be masked, not corrupt adjacent bits
# ---------------------------------------------------------------------------


def test_set_bits_masks_an_oversized_value_instead_of_corrupting_adjacent_bits() -> None:
    # Found during review: value was previously shifted in unmasked, so a value wider than
    # num_bits silently set bits above the intended field instead of being confined to it.
    i2c = make_i2c()
    fake(i2c).registers[(0x50, 0x10)] = bytearray([0b00000000])
    i2c.set_bits(0x50, 3, 0x10, 2, 0xFF, reg_width=1)  # 0xFF is far wider than the 3-bit field
    # Only bits 2-4 (the 3-bit field at start_bit=2) may be set; bits 5-7 must stay untouched.
    assert fake(i2c).registers[(0x50, 0x10)] == bytearray([0b00011100])
    assert i2c.get_bits(0x50, 3, 0x10, 2, reg_width=1) == 0x7  # field itself reads back all-ones


# ---------------------------------------------------------------------------
# shared read scratch - the address and the read share one buffer, no allocation per read
# ---------------------------------------------------------------------------


def test_register_access_writes_the_address_then_reads_into_the_scratch_never_a_mem_call() -> None:
    # A register read is writeto(address, stop=False) then readfrom_into(), the sequence read_mem() issues
    # on rp2 but with the ACK count tested; a register write is one writeto() of address and payload.
    i2c = make_i2c()
    mock = fake(i2c)
    mem_calls: list[str] = []

    def no_mem_call(*_args: object, **_kwargs: object) -> None:
        mem_calls.append("mem")

    mock.readfrom_mem_into = no_mem_call  # type: ignore[method-assign]
    mock.readfrom_mem = no_mem_call  # type: ignore[method-assign, assignment]
    mock.writeto_mem = no_mem_call  # type: ignore[method-assign]
    mock.registers[(0x42, 0x10)] = bytearray(b"\x01\x02\x03")
    assert i2c.get_register_struct(0x42, 0x10, "3s") == b"\x01\x02\x03"
    assert i2c.get_bits(0x42, 4, 0x10, 0, 1) == 0x1
    assert i2c.set_bits(0x42, 4, 0x10, 0, 0x5, 1) is True
    assert mem_calls == []
    assert mock.log == [
        ("writeto", 0x42, b"\x10", False),
        ("readfrom_into", 0x42, b"\x01\x02\x03", True),
        ("writeto", 0x42, b"\x10", False),
        ("readfrom_into", 0x42, b"\x01", True),
        ("writeto", 0x42, b"\x10", False),
        ("readfrom_into", 0x42, b"\x01", True),
        ("writeto", 0x42, b"\x10\x05", True),
    ]


def test_a_read_result_is_copied_out_of_the_scratch_not_aliased_to_it() -> None:
    # The buffer is shared across every device on the bus, so a returned value that still pointed
    # into it would silently change under its owner at the next read on any of them.
    i2c = make_i2c()
    mock = fake(i2c)
    mock.registers[(0x42, 0x10)] = bytearray(b"\xaa\xbb\xcc")
    mock.registers[(0x43, 0x10)] = bytearray(b"\x11\x22\x33")
    first = i2c.get_register_struct(0x42, 0x10, "3s")
    assert first == b"\xaa\xbb\xcc"
    i2c.get_register_struct(0x43, 0x10, "3s")  # a second device, same bus, same scratch
    assert first == b"\xaa\xbb\xcc", "the first read's value moved when a later read reused the buffer"


def test_a_read_larger_than_the_scratch_still_works() -> None:
    # Nothing in src/ reads more than BMP3XX's 21-byte calibration block today, so this path is the
    # "zero callers now, maybe callers tomorrow" kind - it must not be a refusal.
    i2c = make_i2c()
    mock = fake(i2c)
    size = 40  # asy_i2c_driver._SCRATCH_SIZE is 32, and const() folds the name out of the module
    mock.registers[(0x42, 0x20)] = bytearray(range(size))
    assert i2c.get_register_struct(0x42, 0x20, f"{size}s") == bytes(range(size))


# ---------------------------------------------------------------------------
# bool results: every completed transfer and write is True; a short ACK count is an EIO
# ---------------------------------------------------------------------------


def test_every_completed_transfer_and_write_returns_true() -> None:
    i2c = make_i2c()
    device = I2CDevice(i2c, 0x50)
    assert i2c.readfrom_into(0x50, bytearray(2)) is True
    assert i2c.writeto_then_readfrom(0x50, b"\x10", bytearray(2)) is True
    assert i2c.set_bits(0x50, 1, 0x10, 0, 1) is True
    assert i2c.set_register_struct(0x50, 0x10, "B", 1) is True

    async def scenario() -> None:
        assert await device.readinto(bytearray(2)) is True
        assert await device.write(b"\x10") is True
        assert await device.write_then_readinto(b"\x10", bytearray(2)) is True
        assert await device.set_bits(1, 0x10, 0, 1) is True
        assert await device.set_register_struct(0x10, "B", 1) is True

    run(scenario())


def _eio(call: "Callable[[], object]") -> bool:
    try:
        call()
    except OSError as e:
        return e.errno == errno.EIO
    return False


def test_a_short_ack_count_raises_eio_and_a_no_stop_write_then_sends_the_stop() -> None:
    i2c = make_i2c()
    fake(i2c).short_ack(0x60, 2)
    assert _eio(lambda: i2c.writeto(0x60, b"abc"))
    assert fake(i2c).log == [("writeto", 0x60, b"abc", True)]
    fake(i2c).log.clear()
    fake(i2c).short_ack(0x60, 2)
    assert _eio(lambda: i2c.writeto(0x60, b"abc", stop=False))
    assert fake(i2c).log == [("writeto", 0x60, b"abc", False), ("writeto", 0x60, b"", True)]
    assert i2c.writeto(0x60, b"abc") == 3  # the next full ACK count is a plain success again


def test_a_short_no_stop_write_raises_eio_even_when_its_stop_is_refused() -> None:
    # read_mem() ignores the result of the STOP it sends after a short address write; so does the
    # driver, so the caller sees the EIO of the short count, never the STOP's own error.
    i2c = make_i2c()
    mock = fake(i2c)
    real_writeto = mock.writeto

    def refuse_the_stop(address: int, buf: object, stop: bool = True) -> int:  # noqa: FBT001, FBT002  # machine.I2C's own positional stop
        if not len(buf):  # type: ignore[arg-type]
            raise OSError(errno.ENODEV, "zero-length write NACKed")
        return real_writeto(address, buf, stop)

    mock.writeto = refuse_the_stop  # type: ignore[method-assign]
    mock.short_ack(0x50, 0)
    try:
        i2c.get_register_bytes(0x50, 0x20, 2)
        raised = None
    except OSError as e:
        raised = e.errno
    assert raised == errno.EIO


def test_a_nacked_data_byte_in_a_register_write_raises_eio_and_stores_nothing() -> None:
    i2c = make_i2c()
    fake(i2c).registers[(0x50, 0x20)] = bytearray(b"\xaa\xbb")
    fake(i2c).short_ack(0x50, 1)  # the register byte ACKed, the first data byte not
    assert _eio(lambda: i2c.set_register_struct(0x50, 0x20, ">H", 0x1234))
    assert fake(i2c).log == [("writeto", 0x50, b"\x20\x12\x34", True)]
    assert fake(i2c).registers[(0x50, 0x20)] == bytearray(b"\xaa\xbb")
    fake(i2c).log.clear()
    mock = fake(i2c)
    real_read = mock.readfrom_into

    def nack_the_following_write(address: int, buf: object, stop: bool = True) -> None:  # noqa: FBT001, FBT002  # machine.I2C's own positional stop
        real_read(address, buf, stop)
        mock.short_ack(address, 1)  # set_bits()'s read half done: its register write is NACKed

    mock.readfrom_into = nack_the_following_write  # type: ignore[method-assign]
    assert _eio(lambda: i2c.set_bits(0x50, 4, 0x20, 0, 0x5))
    assert mock.log[-1] == ("writeto", 0x50, b"\x20\xa5", True)  # one writeto: address, then the merged value
    assert mock.registers[(0x50, 0x20)] == bytearray(b"\xaa\xbb")


def test_a_nacked_register_byte_raises_eio_instead_of_a_stale_read() -> None:
    # readfrom_mem_into() would return with the buffer untouched here; the helpers see the short count.
    i2c = make_i2c()
    fake(i2c).registers[(0x50, 0x20)] = bytearray(b"\x01\x02")
    fake(i2c).short_ack(0x50, 0)
    assert _eio(lambda: i2c.get_register_bytes(0x50, 0x20, 2))
    assert fake(i2c).log == [("writeto", 0x50, b"\x20", False), ("writeto", 0x50, b"", True)]  # the STOP, no read
    fake(i2c).short_ack(0x50, 0)
    assert _eio(lambda: i2c.get_register_struct(0x50, 0x20, ">H"))
    fake(i2c).short_ack(0x50, 0)
    assert _eio(lambda: i2c.get_bits(0x50, 1, 0x20, 0))
    assert i2c.get_register_bytes(0x50, 0x20, 2) == b"\x01\x02"  # a full ACK count reads as before


def test_a_general_call_no_device_acks_raises_eio() -> None:
    # SGP40's _reset() catches it and stays best-effort (test_asy_sgp40_driver.py).
    i2c = make_i2c()
    fake(i2c).nak_addresses.add(0x00)
    assert _eio(lambda: i2c.writeto(0x00, b"\x06"))


# ---------------------------------------------------------------------------
# get_register_bytes() - exactly `length` bytes, copied out of the shared scratch
# ---------------------------------------------------------------------------


def test_get_register_bytes_returns_a_copy_of_exactly_length_bytes() -> None:
    i2c = make_i2c()
    fake(i2c).registers[(0x50, 0x04)] = bytearray(b"\x10\x20\x30\x40")
    value = i2c.get_register_bytes(0x50, 0x04, 3)
    assert value == b"\x10\x20\x30"
    i2c._scratch[:4] = b"\xff\xff\xff\xff"
    assert value == b"\x10\x20\x30"  # a copy: the scratch's next use leaves it alone
    assert i2c.get_register_bytes(0x50, 0x04, 0) is None
    assert i2c.get_register_bytes(0x50, 0x04, -1) is None
    assert fake(i2c).log[-1][0] == "readfrom_into"  # the two refusals made no transfer


def test_get_register_bytes_above_the_scratch_uses_the_allocating_fallback() -> None:
    i2c = make_i2c()
    size = 40  # above the driver's 32-byte scratch
    fake(i2c).registers[(0x50, 0x20)] = bytearray(range(size))
    scratch_before = bytes(i2c._scratch)
    assert i2c.get_register_bytes(0x50, 0x20, size) == bytes(range(size))
    assert bytes(i2c._scratch)[1:] == scratch_before[1:]  # only the address byte went through the scratch


def test_get_register_bytes_lets_a_bus_oserror_propagate() -> None:
    i2c = make_i2c()
    fake(i2c).inject_fault("readfrom_into", OSError(errno.ETIMEDOUT, "stretch"), match=0x20)
    try:
        i2c.get_register_bytes(0x50, 0x20, 2)
        raised = None
    except OSError as e:
        raised = e.errno
    assert raised == errno.ETIMEDOUT


def test_a_set_register_struct_above_the_scratch_still_writes_address_and_payload() -> None:
    i2c = make_i2c()
    payload = bytes(range(40))
    assert i2c.set_register_struct(0x50, 0x20, "40s", payload) is True
    assert fake(i2c).log == [("writeto", 0x50, b"\x20" + payload, True)]


# ---------------------------------------------------------------------------
# The bus rungs: the boot clear before the controller exists, then clear() and recover() at runtime
# ---------------------------------------------------------------------------


def _released_after(pulses: int) -> "Callable[[int, object], int]":
    # SDA held low by a slave until SCL has risen `pulses` times.
    def level(_pin: int, _log: object) -> int:
        return 1 if list(Pin.value_log(_SCL)).count(1) >= pulses else 0

    return level


def _stretching(reads: int) -> "Callable[[int, object], int]":
    # SCL held low by a slave for `reads` reads after every release the driver makes; a new drive is a
    # change in the line's drive count (the value log is a ring: its len() stops at its capacity).
    state = [-1, 0]

    def level(_pin: int, _log: object) -> int:
        log = Pin.value_log(_SCL)
        drives = len(log) + log.dropped
        if drives != state[0]:
            state[0], state[1] = drives, 0
        state[1] += 1
        return 1 if state[1] > reads else 0

    return level


def _build(*, sda: "int | Callable[[int, object], int]" = 1, scl: "int | Callable[[int, object], int]" = 1, timeout: int | None = None) -> I2C:
    FakeI2C.reset_id(0)
    Pin.reset_registry()
    Pin.set_external_level(_SDA, sda)
    Pin.set_external_level(_SCL, scl)
    return I2C(0, scl_pin=_SCL, sda_pin=_SDA, frequency=100000, timeout=timeout)


def _pulses_then_stop(pulses: int) -> list[int]:
    return [0, 1] * pulses + [0, 1]  # each pulse low then released, then the STOP's SCL low and release


def test_the_boot_clear_leaves_a_free_bus_untouched() -> None:
    i2c = _build()
    assert list(Pin.value_log(_SCL)) == []
    assert list(Pin.value_log(_SDA)) == []
    assert i2c.take_boot_clear_status() == 0
    assert fake(i2c).log == [("init", 100000, 50000)]


def test_the_boot_clear_stops_pulsing_once_the_slave_releases_sda() -> None:
    i2c = _build(sda=_released_after(3))
    assert list(Pin.value_log(_SCL)) == _pulses_then_stop(3)
    assert list(Pin.value_log(_SDA)) == [0, 1]  # the STOP: driven low while SCL is low, released after SCL
    assert i2c.take_boot_clear_status() == _REC_SDA_LOW
    assert i2c.take_boot_clear_status() == 0  # taken once


def test_the_boot_clear_gives_up_after_nine_pulses_and_construction_proceeds() -> None:
    i2c = _build(sda=0)
    assert list(Pin.value_log(_SCL)) == _pulses_then_stop(9)
    assert i2c.take_boot_clear_status() == _REC_SDA_LOW | _REC_SDA_STUCK
    assert fake(i2c).log == [("init", 100000, 50000)]
    assert i2c.get_register_bytes(0x50, 0x00, 1) is not None  # the controller exists


def test_the_boot_clear_counts_a_stretched_pulse_only_once_scl_is_released() -> None:
    i2c = _build(sda=0, scl=_stretching(2))
    assert list(Pin.value_log(_SCL)) == _pulses_then_stop(9)
    assert i2c.take_boot_clear_status() == _REC_SDA_LOW | _REC_SDA_STUCK


def test_the_boot_clear_reports_a_held_scl_and_pulses_nothing() -> None:
    # Like the runtime clear, the boot clear first waits for SCL up to the bus timeout: a slave holding
    # SCL is reported as such, never as a free bus nor as SDA cleared, and no pulse is sent.
    for sda in (0, 1):
        i2c = _build(sda=sda, scl=0, timeout=_HELD_SCL_TIMEOUT_US)
        assert list(Pin.value_log(_SCL)) == [], sda
        assert list(Pin.value_log(_SDA)) == [], sda
        assert i2c.take_boot_clear_status() == _REC_SCL_HELD, sda
        assert fake(i2c).log == [("init", 100000, _HELD_SCL_TIMEOUT_US)]  # construction proceeds


def test_the_boot_clear_proceeds_once_scl_is_released_inside_the_timeout() -> None:
    held = [3]  # SCL reads low three times at boot, then is let go

    def scl_level(_pin: int, _log: object) -> int:
        if held[0]:
            held[0] -= 1
            return 0
        return 1

    i2c = _build(sda=_released_after(2), scl=scl_level, timeout=_HELD_SCL_TIMEOUT_US)
    assert held == [0]
    assert list(Pin.value_log(_SCL)) == _pulses_then_stop(2)
    assert i2c.take_boot_clear_status() == _REC_SDA_LOW


def test_a_later_init_never_clears() -> None:
    i2c = _build()
    Pin.set_external_level(_SDA, 0)
    i2c.init(0, _SCL, _SDA, 100000)
    assert list(Pin.value_log(_SCL)) == []


class _PinSpy(Pin):
    # Records each Pin construction's (id, mode, pull, alt): the pins a clear hands back to the controller.
    made: "ClassVar[list[tuple[int, int, int, int]]]" = []

    def __init__(self, id: int, mode: int = -1, pull: int = -1, *, value: object = None, alt: int = Pin._ALT_SIO) -> None:  # noqa: A002  # machine.Pin's own parameter name
        super().__init__(id, mode, pull, value=value, alt=alt)
        _PinSpy.made.append((id, mode, pull, alt))


def _clear(i2c: I2C, *, recover: bool = False) -> "tuple[int, list[tuple[int, int, int, int]]]":
    _PinSpy.made = []
    asy_i2c_driver.Pin = _PinSpy  # type: ignore[misc]
    try:
        status = run(i2c.recover() if recover else i2c.clear())
    finally:
        asy_i2c_driver.Pin = Pin  # type: ignore[misc]
    return status, _PinSpy.made


_HANDED_BACK = [(_SCL, Pin.ALT, Pin.PULL_UP, Pin.ALT_I2C), (_SDA, Pin.ALT, Pin.PULL_UP, Pin.ALT_I2C)]


def test_clear_on_a_free_bus_pulses_nothing_and_hands_the_pins_back() -> None:
    i2c = _build()
    fake(i2c).log.clear()
    status, made = _clear(i2c)
    assert status == 0
    assert list(Pin.value_log(_SCL)) == []
    assert made[-2:] == _HANDED_BACK
    assert fake(i2c).log == []  # a clear constructs no controller
    assert i2c.recoveries == 1


def test_clear_stops_once_sda_is_released_and_reports_it() -> None:
    i2c = _build()
    Pin.set_external_level(_SDA, _released_after(4))
    status, made = _clear(i2c)
    assert status == _REC_SDA_LOW
    assert list(Pin.value_log(_SCL)) == _pulses_then_stop(4)
    assert made[-2:] == _HANDED_BACK


def test_clear_of_a_held_sda_sends_nine_pulses_and_a_stop() -> None:
    i2c = _build()
    Pin.set_external_level(_SDA, 0)
    status, _made = _clear(i2c)
    assert status == _REC_SDA_LOW | _REC_SDA_STUCK
    assert list(Pin.value_log(_SCL)) == _pulses_then_stop(9)
    assert list(Pin.value_log(_SDA)) == [0, 1]


def test_clear_waits_out_a_stretched_clock_and_still_sends_nine_effective_pulses() -> None:
    i2c = _build()
    Pin.set_external_level(_SDA, 0)
    Pin.set_external_level(_SCL, _stretching(2))
    status, _made = _clear(i2c)
    assert status == _REC_SDA_LOW | _REC_SDA_STUCK
    assert list(Pin.value_log(_SCL)) == _pulses_then_stop(9)


def test_clear_with_scl_held_past_the_timeout_pulses_nothing() -> None:
    i2c = _build(timeout=_HELD_SCL_TIMEOUT_US)
    Pin.set_external_level(_SDA, 0)
    Pin.set_external_level(_SCL, 0)
    status, made = _clear(i2c)
    assert status == _REC_SCL_HELD
    assert list(Pin.value_log(_SCL)) == []
    assert made[-2:] == _HANDED_BACK  # handed back even so


def test_recover_clears_then_re_constructs_with_the_stored_frequency_and_timeout() -> None:
    i2c = _build(timeout=20000)
    fake(i2c).register_device(0x50)
    fake(i2c).log.clear()
    Pin.set_external_level(_SDA, _released_after(2))
    status, _made = _clear(i2c, recover=True)
    assert status == _REC_SDA_LOW
    assert fake(i2c).log == [("deinit",), ("init", 100000, 20000)]
    assert i2c.recoveries == 1
    assert i2c.writeto(0x50, b"\x00") == 1  # the rebuilt controller works


def test_recover_re_constructs_even_after_a_held_scl() -> None:
    i2c = _build(timeout=_HELD_SCL_TIMEOUT_US)
    fake(i2c).log.clear()
    Pin.set_external_level(_SCL, 0)
    status, _made = _clear(i2c, recover=True)
    assert status == _REC_SCL_HELD
    assert fake(i2c).log == [("deinit",), ("init", 100000, _HELD_SCL_TIMEOUT_US)]


def test_recover_reports_a_controller_that_will_not_construct_and_leaves_no_bus() -> None:
    i2c = _build()
    FakeI2C.raise_on_construct = OSError(errno.EIO, "construction failed")
    try:
        status, _made = _clear(i2c, recover=True)
    finally:
        FakeI2C.raise_on_construct = None
    assert status == _REC_NO_CONTROLLER
    assert i2c._i2c is None
    assert i2c.get_register_bytes(0x50, 0x00, 1) is None  # the unavailable-bus path
    assert i2c.recoveries == 1


def test_each_clear_and_recover_steps_recoveries_once_and_the_sequence_wraps() -> None:
    i2c = _build()
    run(i2c.clear())
    run(i2c.recover())
    assert i2c.recoveries == 2
    i2c.recoveries = COUNTER_CAP
    run(i2c.clear())
    assert i2c.recoveries == 0  # compared for equality only, so it wraps rather than saturating


def test_a_session_holding_the_bus_delays_clear_and_a_session_started_during_it_waits() -> None:
    i2c = _build()
    Pin.set_external_level(_SDA, 0)
    Pin.set_external_level(_SCL, _stretching(1))  # every pulse yields once: the clear spans many passes
    device = I2CDevice(i2c, 0x50)
    order: list[str] = []

    async def holder(release: asyncio.Event) -> None:
        async with device:
            order.append("holder in")
            await release.wait()
            order.append("holder out")

    async def clearer() -> None:
        await i2c.clear()
        order.append("clear done")

    async def late_session() -> None:
        async with device:
            order.append("late in")

    async def scenario() -> None:
        release = asyncio.Event()
        first = asyncio.create_task(holder(release))
        await asyncio.sleep(0)
        clearing = asyncio.create_task(clearer())
        for _ in range(3):
            await asyncio.sleep(0)
        assert list(Pin.value_log(_SCL)) == []  # the clear waits for the session
        release.set()
        while not Pin.value_log(_SCL):
            await asyncio.sleep(0)
        late = asyncio.create_task(late_session())  # started while the clear holds the bus
        await asyncio.gather(first, clearing, late)

    run(scenario())
    assert order == ["holder in", "holder out", "clear done", "late in"], order


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
