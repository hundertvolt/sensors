import asyncio
import errno
import struct

from machine import I2C as FakeI2C

from asy_i2c_driver import I2C, I2CDevice

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


def make_i2c() -> I2C:
    return I2C(0, scl_pin=1, sda_pin=0, frequency=100000)


def fake(i2c: I2C) -> FakeI2C:
    return i2c._i2c  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# init / deinit - real hardware deinit(), not just dropping the reference
# ---------------------------------------------------------------------------


def test_deinit_calls_real_hardware_deinit() -> None:
    i2c = make_i2c()
    mock = fake(i2c)
    i2c.deinit()
    assert mock.deinit_called is True
    assert i2c._i2c is None


def test_reinit_deinits_the_previous_bus_first() -> None:
    i2c = make_i2c()
    first = fake(i2c)
    i2c.init(0, scl_pin=1, sda_pin=0, frequency=100000)
    assert first.deinit_called is True
    assert fake(i2c) is not first


def test_operations_after_deinit_return_none_or_noop() -> None:
    i2c = make_i2c()
    i2c.deinit()
    assert i2c.scan() is None
    assert i2c.writeto(0x50, b"x") is None
    assert i2c.get_bits(0x50, 1, 0x00, 0) is None
    assert i2c.get_register_struct(0x50, 0x00, ">H") is None
    i2c.readfrom_into(0x50, bytearray(2))  # no-op, must not raise
    i2c.set_bits(0x50, 1, 0x00, 0, 1)  # no-op, must not raise
    i2c.set_register_struct(0x50, 0x00, ">H", 1)  # no-op, must not raise


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


def test_readfrom_into_and_writeto_respect_start_end_slice() -> None:
    i2c = make_i2c()
    buf = bytearray(b"\x00\x00\x00\x00")
    i2c.readfrom_into(0x50, buf, start=1, end=3)
    assert fake(i2c).log[-1][0] == "readfrom_into"
    i2c.writeto(0x50, b"XYZ", start=1, end=3)
    assert fake(i2c).log[-1] == ("writeto", 0x50, b"YZ", True)


def test_writeto_then_readfrom_forwards_both() -> None:
    i2c = make_i2c()
    i2c.writeto_then_readfrom(0x50, b"cmd", bytearray(2))
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
    i2c.set_register_struct(0x50, 0x20, "Y", 1)
    assert len(fake(i2c).log) == 0


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


# ---------------------------------------------------------------------------
# I2CDevice - address binding, shared locking, probing
# ---------------------------------------------------------------------------


def test_device_shares_the_bus_lock() -> None:
    i2c = make_i2c()
    device = I2CDevice(i2c, 0x50)
    assert device.asy_lock is i2c.async_lock


def test_device_context_manager_acquires_and_releases_lock() -> None:
    i2c = make_i2c()
    device = I2CDevice(i2c, 0x50)

    async def scenario() -> None:
        assert not i2c.async_lock.locked()
        async with device:
            assert i2c.async_lock.locked()
        assert not i2c.async_lock.locked()

    run(scenario())


def test_probe_succeeds_when_device_acks() -> None:
    i2c = make_i2c()
    device = I2CDevice(i2c, 0x50)
    run(device.setup())  # must not raise


def test_probe_raises_value_error_when_device_missing() -> None:
    i2c = make_i2c()
    fake(i2c).nak_addresses.add(0x50)
    device = I2CDevice(i2c, 0x50)
    try:
        run(device.setup())
        raised = False
    except ValueError:
        raised = True
    assert raised


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
    run(device.write(b"cmd"))
    assert fake(i2c).log[-1] == ("writeto", 0x50, b"cmd", True)
    run(device.readinto(bytearray(2)))
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
        lambda: i2c.scan(),
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
    fake(i2c).inject_fault("readfrom_mem", OSError(errno.EIO, "no ACK"))
    try:
        i2c.set_bits(0x50, 3, 0x10, 0, 0x5, reg_width=1)
        raised = False
    except OSError:
        raised = True
    assert raised
    assert not any(entry[0] == "writeto_mem" for entry in fake(i2c).log)  # never reached the write


def test_set_bits_write_half_can_fail_after_read_half_succeeds() -> None:
    i2c = make_i2c()
    fake(i2c).inject_fault("writeto_mem", OSError(errno.EIO, "no ACK"))
    try:
        i2c.set_bits(0x50, 3, 0x10, 0, 0x5, reg_width=1)
        raised = False
    except OSError:
        raised = True
    assert raised
    assert any(entry[0] == "readfrom_mem" for entry in fake(i2c).log)  # the read did happen first


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
    i2c.deinit()  # must not touch the (already gone) bus a second time
    assert mock.deinit_count == 1


def test_deinit_mid_session_degrades_later_ops_in_the_same_session_cleanly() -> None:
    # A bus torn down (e.g. by unrelated code) while a device session is still open must not
    # crash the rest of that session - later ops on the same still-open session cleanly no-op.
    i2c = make_i2c()
    device = I2CDevice(i2c, 0x50)

    async def scenario() -> bytearray:
        buf = bytearray(2)
        async with device:
            await device.write(b"first")
            i2c.deinit()
            await device.readinto(buf)  # must not raise
        return buf

    result = run(scenario())
    assert result == bytearray(2)  # untouched: readinto no-op'd, buffer stays as allocated


def test_reinit_mid_session_switches_to_a_fresh_bus() -> None:
    i2c = make_i2c()
    device = I2CDevice(i2c, 0x50)
    old_mock = fake(i2c)

    async def scenario() -> None:
        async with device:
            await device.write(b"first")
            i2c.init(0, scl_pin=1, sda_pin=0, frequency=100000)
            await device.write(b"second")

    run(scenario())
    assert old_mock.log[0] == ("writeto", 0x50, b"first", True)
    assert old_mock.log[-1] == ("deinit",)  # init() deinits the old bus before swapping it out
    assert fake(i2c).log[-1] == ("writeto", 0x50, b"second", True)
    assert fake(i2c) is not old_mock


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
        assert not i2c.async_lock.locked()

    run(scenario())


def test_multi_transfer_session_holds_the_lock_across_every_transfer() -> None:
    i2c = make_i2c()
    device = I2CDevice(i2c, 0x50)

    async def scenario() -> None:
        async with device:
            await device.write(b"cmd1")
            assert i2c.async_lock.locked()
            await device.readinto(bytearray(2))
            assert i2c.async_lock.locked()
            await device.write(b"cmd2")
            assert i2c.async_lock.locked()
        assert not i2c.async_lock.locked()
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
            assert not i2c.async_lock.locked()

    run(scenario())
    assert len(fake(i2c).log) == 3


def test_device_operations_do_not_self_lock_caller_must_wrap_in_async_with() -> None:
    # I2CDevice's read/write methods never acquire self.asy_lock themselves - by design, every
    # real caller (SCD30_I2C/SGP40_I2C/BMP3XX_I2C) wraps them in `async with device:` itself.
    # Makes explicit an easy-to-miss division of responsibility: locking is the caller's job,
    # not something write()/readinto() provide on their own.
    i2c = make_i2c()
    device = I2CDevice(i2c, 0x50)

    async def scenario() -> None:
        await device.write(b"x")  # no `async with device:` wrapper at all
        assert not i2c.async_lock.locked()  # never touched: write() itself doesn't lock

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
        await asyncio.wait_for(asyncio.gather(*(worker(d) for d in devices)), 1.0)

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

    async def scenario() -> None:
        try:
            async with device:
                raise RuntimeError("boom")
        except RuntimeError:
            pass
        assert not i2c.async_lock.locked()
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
            device.asy_lock.release()  # released early by hand
        # __aexit__'s own release() must swallow the resulting RuntimeError, not propagate it

    run(scenario())  # must not raise
    assert not i2c.async_lock.locked()


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
        assert i2c.async_lock.locked()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        assert not i2c.async_lock.locked()

    run(scenario())


def test_reentrant_acquisition_on_the_same_device_deadlocks_and_cleans_up() -> None:
    # Not reentrant by design (a plain asyncio.Lock): nesting `async with device:` on the same
    # device within one task deadlocks rather than silently succeeding - bounded by wait_for so
    # the test itself can't hang. Confirmed directly this raises TimeoutError and still leaves
    # the lock released afterward (wait_for's own cancellation unwinds the inner `async with`).
    i2c = make_i2c()
    device = I2CDevice(i2c, 0x50)

    async def reentrant() -> None:
        async with device:
            async with device:
                pass

    async def scenario() -> bool:
        try:
            await asyncio.wait_for(reentrant(), 0.2)
            return False
        except asyncio.TimeoutError:
            return True

    assert run(scenario())
    assert not i2c.async_lock.locked()


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
    # A real gap this session's own testing found: struct.unpack("", ...) returns an empty
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
    # Documents a real MicroPython-specific quirk (not a bug in this driver): struct.pack
    # silently zero-fills a field this single-value method never supplies, rather than raising
    # like CPython's struct.error would. set_register_struct is deliberately single-value-only;
    # this is what happens if a caller mistakenly passes a multi-field format anyway.
    i2c = make_i2c()
    i2c.set_register_struct(0x50, 0x20, ">HH", 5)
    assert fake(i2c).registers[(0x50, 0x20)] == bytearray(struct.pack(">HH", 5, 0))


def test_out_of_range_address_is_transparently_forwarded_not_validated() -> None:
    # This driver deliberately doesn't range-check `address` itself (src/README.md section 2's
    # "don't defend against out-of-contract input" - the type contract is plain `int`; address
    # validity is the real machine.I2C's job, mirrored by the mock rather than duplicated here).
    i2c = make_i2c()
    assert i2c.writeto(200, b"x") == 1  # not a valid 7-bit address, but not rejected here either
    assert fake(i2c).log[-1][1] == 200


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
