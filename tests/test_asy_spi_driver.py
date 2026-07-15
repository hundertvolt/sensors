import asyncio

from machine import SPI as FakeSPI

from asy_spi_driver import SPI, SPIDevice

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


def make_spi() -> SPI:
    return SPI(0, sck_pin=2, mosi_pin=3, miso_pin=4)


def make_device(spi: SPI, cs_pin: int = 1, cs_active_value: bool = False, call_setup: bool = True) -> SPIDevice:
    # call_setup=True by default so every test gets a real-world-shaped device (every actual
    # caller calls setup() before first use) without needing its own boilerplate; pass False for
    # tests specifically about the pre-setup state or setup() itself.
    device = SPIDevice(spi, cs_pin, cs_active_value=cs_active_value)
    if call_setup:
        run(device.setup())
    return device


def fake(spi: SPI) -> FakeSPI:
    return spi._spi  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# init / deinit - real hardware deinit(), not just dropping the reference
# ---------------------------------------------------------------------------


def test_deinit_calls_real_hardware_deinit() -> None:
    spi = make_spi()
    mock = fake(spi)
    spi.deinit()
    assert mock.deinit_called is True
    assert spi._spi is None


def test_double_deinit_is_idempotent() -> None:
    spi = make_spi()
    mock = fake(spi)
    spi.deinit()
    spi.deinit()  # must not touch the (already gone) bus a second time
    assert mock.deinit_count == 1


def test_reinit_deinits_the_previous_bus_first() -> None:
    spi = make_spi()
    first = fake(spi)
    spi.init(0, sck_pin=2, mosi_pin=3, miso_pin=4)
    assert first.deinit_called is True
    assert fake(spi) is not first


def test_operations_after_deinit_return_none_or_noop() -> None:
    spi = make_spi()
    spi.deinit()
    spi.write(b"x")  # no-op, must not raise
    spi.readinto(bytearray(2))  # no-op, must not raise
    spi.write_readinto(b"xy", bytearray(2))  # no-op, must not raise


def test_device_operations_on_an_already_deinitialized_bus_return_none_or_noop() -> None:
    # Bypasses `async with device:` deliberately: __aenter__ would call configure(), which
    # raises on a deinitialized bus regardless (see test_aenter_leaves_lock_held_if_configure_
    # raises_pre_existing_gap below) - this test is only about SPI's own no-op contract at the
    # write()/readinto()/write_readinto() level, reached directly the way I2CDevice's equivalent
    # test reaches I2C's.
    spi = make_spi()
    device = make_device(spi)
    spi.deinit()

    async def scenario() -> None:
        await device.write(b"x")  # no-op, must not raise
        await device.readinto(bytearray(2))  # no-op, must not raise
        await device.write_readinto(b"xy", bytearray(2))  # no-op, must not raise

    run(scenario())


# ---------------------------------------------------------------------------
# write / readinto / write_readinto - forwarding, and the one real raise path
# ---------------------------------------------------------------------------


def test_write_forwards_buffer_and_returns_none() -> None:
    spi = make_spi()
    spi.write(b"abc")
    assert fake(spi).log[-1] == ("write", b"abc")


def test_readinto_fills_from_the_simulated_downstream_device() -> None:
    spi = make_spi()
    fake(spi).read_queue.append(b"\x01\x02")
    buf = bytearray(2)
    spi.readinto(buf, write_value=0x11)
    assert buf == bytearray(b"\x01\x02")
    assert fake(spi).log[-1] == ("readinto", 2, 0x11)


def test_readinto_default_write_value_is_zero() -> None:
    spi = make_spi()
    spi.readinto(bytearray(1))
    assert fake(spi).log[-1] == ("readinto", 1, 0x00)


def test_write_readinto_matching_lengths_succeeds() -> None:
    # write_readinto is a synchronous full-duplex transfer - buffer_out and buffer_in must be the
    # same length (each clocked-out byte has a corresponding clocked-in byte), unlike write()/
    # readinto()'s independent buffer sizes.
    spi = make_spi()
    fake(spi).read_queue.append(b"\xaa\xbb")
    buffer_in = bytearray(2)
    spi.write_readinto(b"cd", buffer_in)
    assert buffer_in == bytearray(b"\xaa\xbb")
    assert fake(spi).log[-1] == ("write_readinto", b"cd")


def test_write_readinto_mismatched_buffer_lengths_returns_none_instead_of_raising() -> None:
    # machine.SPI.write_readinto() itself raises ValueError("buffers must be the same length")
    # here (confirmed against extmod/machine_spi.c's mp_machine_spi_write_readinto(), shared by
    # hardware and soft SPI) - caught and turned into a None return, matching this driver's
    # non-hardware-failure convention (see e.g. asy_i2c_driver.py's malformed-reg_format handling).
    # Checked in both directions - the underlying check is symmetric (src.len != dest.len), but
    # buffer_out longer than buffer_in and vice versa are both real, distinct caller mistakes.
    spi = make_spi()
    spi.write_readinto(b"abc", bytearray(2))  # buffer_out longer - must not raise
    assert len(fake(spi).log) == 0  # rejected before ever touching the bus
    spi.write_readinto(b"a", bytearray(2))  # buffer_out shorter - must not raise
    assert len(fake(spi).log) == 0


def test_disconnected_wire_is_undetectable_reads_whatever_is_on_the_bus_not_an_exception() -> None:
    # Real, deliberately-not-simulated irregular condition: unlike I2C's NAK, SPI has no ACK, so a
    # physically disconnected MISO/clock wire is invisible at this layer on real RP2040 hardware
    # (confirmed: extmod/machine_spi.c's blocking transfer path has no error return at all once
    # the bus is constructed - see the module docstring and BACKLOG.md's asy_spi_driver.py entry).
    # This test proves that documented claim as a regression, not just a comment: with nothing
    # primed in the fake's read_queue (modeling a device that never drives MISO), readinto() and
    # write_readinto() still succeed and hand back zero-filled bytes instead of raising anything -
    # exactly what "undetectable" means in practice, not an untestable absence.
    spi = make_spi()
    buf = bytearray(b"\xff\xff")
    spi.readinto(buf)
    assert buf == bytearray(2)  # zero-filled, not left as \xff\xff and not an exception
    buffer_in = bytearray(b"\xff\xff")
    spi.write_readinto(b"cd", buffer_in)
    assert buffer_in == bytearray(2)


def test_zero_length_buffer_operations_are_harmless() -> None:
    spi = make_spi()
    spi.write(b"")
    spi.readinto(bytearray(0))
    spi.write_readinto(b"", bytearray(0))
    assert fake(spi).log[-1] == ("write_readinto", b"")


# ---------------------------------------------------------------------------
# configure() - programmer-error guard, applied fresh on every session
# ---------------------------------------------------------------------------


def test_configure_raises_if_lock_not_held() -> None:
    spi = make_spi()
    try:
        spi.configure()
        raised = False
    except RuntimeError:
        raised = True
    assert raised


def test_configure_raises_if_bus_deinitialized_even_with_lock_held() -> None:
    spi = make_spi()
    spi.deinit()

    async def scenario() -> None:
        await spi.async_lock.acquire()
        try:
            spi.configure()
            raised = False
        except RuntimeError:
            raised = True
        finally:
            spi.async_lock.release()
        assert raised

    run(scenario())


def test_configure_succeeds_and_forwards_params_once_lock_is_held() -> None:
    spi = make_spi()

    async def scenario() -> None:
        await spi.async_lock.acquire()
        try:
            spi.configure(baudrate=2000000, polarity=1, phase=1, bits=8, firstbit=0)
        finally:
            spi.async_lock.release()

    run(scenario())
    assert fake(spi).log[-1] == ("init", 2000000, 1, 1, 8, 0)


# ---------------------------------------------------------------------------
# SPIDevice - CS binding, shared locking, setup
# ---------------------------------------------------------------------------


def test_device_shares_the_bus_lock() -> None:
    spi = make_spi()
    device = make_device(spi)
    assert device.asy_lock is spi.async_lock


def test_setup_drives_cs_pin_to_inactive() -> None:
    spi = make_spi()
    device = make_device(spi, cs_active_value=False, call_setup=False)
    assert device.uninitialized is True
    run(device.setup())
    assert device.cs_pin.value() == 1  # inactive = not cs_active_value = not False
    assert device.uninitialized is False


def test_setup_drives_cs_pin_to_inactive_active_high_variant() -> None:
    spi = make_spi()
    device = make_device(spi, cs_active_value=True, call_setup=False)
    run(device.setup())
    assert device.cs_pin.value() == 0  # inactive = not cs_active_value = not True


def test_aenter_raises_if_setup_was_never_called() -> None:
    # Real finding from the architecture-review pass: Pin.value() writes the GPIO output register
    # unconditionally regardless of direction (confirmed against ports/rp2/machine_pin.c), so
    # entering before setup() wouldn't crash on its own - it would silently fail to assert CS on
    # real hardware. This guard converts that into a clear, immediate RuntimeError instead.
    spi = make_spi()
    device = make_device(spi, call_setup=False)

    async def scenario() -> bool:
        try:
            async with device:
                pass
            return False
        except RuntimeError:
            return True

    assert run(scenario())
    assert not spi.async_lock.locked()  # never even attempted to acquire - fails before that


def test_device_context_manager_acquires_and_releases_lock() -> None:
    spi = make_spi()
    device = make_device(spi)

    async def scenario() -> None:
        assert not spi.async_lock.locked()
        async with device:
            assert spi.async_lock.locked()
        assert not spi.async_lock.locked()

    run(scenario())


def test_aenter_returns_the_device_itself() -> None:
    spi = make_spi()
    device = make_device(spi)

    async def scenario() -> None:
        async with device as entered:
            assert entered is device

    run(scenario())


def test_configure_is_applied_fresh_on_every_aenter() -> None:
    spi = make_spi()
    device = make_device(spi)

    async def scenario() -> None:
        async with device:
            pass
        async with device:
            pass

    run(scenario())
    inits = [entry for entry in fake(spi).log if entry[0] == "init"]
    assert len(inits) == 2  # configure() re-applied every session, not cached


# ---------------------------------------------------------------------------
# CS pin sequencing - asserted only inside the session, deasserted on every exit path
# ---------------------------------------------------------------------------


def test_cs_pin_active_only_during_the_session() -> None:
    spi = make_spi()
    device = make_device(spi, cs_active_value=False)
    run(device.setup())

    async def scenario() -> None:
        assert device.cs_pin.value() == 1  # inactive before
        async with device:
            assert device.cs_pin.value() == 0  # active during
        assert device.cs_pin.value() == 1  # inactive after

    run(scenario())


def test_cs_pin_returns_to_inactive_after_exception_inside_session() -> None:
    spi = make_spi()
    device = make_device(spi)
    run(device.setup())

    async def scenario() -> None:
        try:
            async with device:
                assert device.cs_pin.value() == 0  # active (cs_active_value=False -> asserted=0)
                raise RuntimeError("boom")
        except RuntimeError:
            pass

    run(scenario())
    assert device.cs_pin.value() == 1  # deasserted (inactive) despite the exception


def test_cs_pin_returns_to_inactive_after_lock_already_released_inside_block() -> None:
    spi = make_spi()
    device = make_device(spi)
    run(device.setup())

    async def scenario() -> None:
        async with device:
            device.asy_lock.release()  # released early by hand
        # __aexit__ must still deassert CS and swallow the resulting double-release RuntimeError

    run(scenario())  # must not raise
    assert device.cs_pin.value() == 1
    assert not spi.async_lock.locked()


def test_cs_pin_returns_to_inactive_after_task_cancellation() -> None:
    spi = make_spi()
    device = make_device(spi)
    run(device.setup())
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
        assert spi.async_lock.locked()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        assert not spi.async_lock.locked()

    run(scenario())
    assert device.cs_pin.value() == 1  # CS deasserted even though the session was cancelled mid-flight


# ---------------------------------------------------------------------------
# Regular bus conditions: deinit/reinit mid-session
# ---------------------------------------------------------------------------


def test_deinit_mid_session_degrades_later_ops_in_the_same_session_cleanly() -> None:
    spi = make_spi()
    device = make_device(spi)

    async def scenario() -> bytearray:
        buf = bytearray(2)
        async with device:
            await device.write(b"first")
            spi.deinit()
            await device.readinto(buf)  # must not raise
        return buf

    result = run(scenario())
    assert result == bytearray(2)  # untouched: readinto no-op'd


def test_reinit_mid_session_switches_to_a_fresh_bus() -> None:
    spi = make_spi()
    device = make_device(spi)
    old_mock = fake(spi)

    async def scenario() -> None:
        async with device:
            await device.write(b"first")
            spi.init(0, sck_pin=2, mosi_pin=3, miso_pin=4)
            await device.write(b"second")

    run(scenario())
    # old_mock.log[0] is configure()'s own "init" entry from __aenter__, logged before "first"
    old_writes = [entry for entry in old_mock.log if entry[0] == "write"]
    assert old_writes == [("write", b"first")]
    assert old_mock.log[-1] == ("deinit",)  # init() deinits the old bus before swapping it out
    assert fake(spi).log[-1] == ("write", b"second")
    assert fake(spi) is not old_mock


def test_aenter_releases_the_lock_if_configure_raises() -> None:
    # Real bug found and fixed during this promotion (present in the original file too): if the
    # bus is deinitialized before a new session starts, __aenter__ acquires the lock first, then
    # configure() raises RuntimeError - since __aenter__ itself then raises, `async with` never
    # calls __aexit__. Without __aenter__'s own try/except, the lock would leak permanently
    # (see BACKLOG.md). This test proves the fix: the lock is released before the exception
    # propagates.
    spi = make_spi()
    device = make_device(spi)
    spi.deinit()

    async def scenario() -> bool:
        try:
            async with device:
                pass
            return False
        except RuntimeError:
            return True

    assert run(scenario())
    assert not spi.async_lock.locked()  # released, not leaked

    async def retry() -> None:
        spi.init(0, sck_pin=2, mosi_pin=3, miso_pin=4)  # bus usable again
        async with device:
            pass

    run(retry())  # a later session on the same device must still be able to acquire the lock


def test_aenter_releases_the_lock_if_cancelled_during_the_settle_sleep() -> None:
    spi = make_spi()
    device = make_device(spi)
    entered = False

    async def enter_only() -> None:
        nonlocal entered
        async with device:
            entered = True  # pragma: no cover - not expected to be reached before cancellation

    async def scenario() -> None:
        task = asyncio.create_task(enter_only())
        await asyncio.sleep(0)  # let it start: acquire lock, configure(), assert CS, hit sleep(0.001)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        assert not entered
        assert not spi.async_lock.locked()  # released via __aenter__'s own except, not leaked
        assert device.cs_pin.value() == 1  # deasserted too, not left stuck asserted

    run(scenario())


# ---------------------------------------------------------------------------
# Sessions: single- vs multi-transfer, and sequential sessions
# ---------------------------------------------------------------------------


def test_single_op_session_releases_lock_immediately_after() -> None:
    spi = make_spi()
    device = make_device(spi)

    async def scenario() -> None:
        async with device:
            await device.write(b"x")
        assert not spi.async_lock.locked()

    run(scenario())


def test_multi_transfer_session_holds_the_lock_across_every_transfer() -> None:
    spi = make_spi()
    device = make_device(spi)

    async def scenario() -> None:
        async with device:
            await device.write(b"cmd1")
            assert spi.async_lock.locked()
            await device.readinto(bytearray(2))
            assert spi.async_lock.locked()
            await device.write(b"cmd2")
            assert spi.async_lock.locked()
        assert not spi.async_lock.locked()
        ops = [entry[0] for entry in fake(spi).log if entry[0] != "init"]
        assert ops == ["write", "readinto", "write"]

    run(scenario())


def test_sequential_sessions_do_not_leak_lock_state_between_them() -> None:
    spi = make_spi()
    device = make_device(spi)

    async def scenario() -> None:
        for _ in range(3):
            async with device:
                await device.write(b"x")
            assert not spi.async_lock.locked()

    run(scenario())
    assert len([entry for entry in fake(spi).log if entry[0] == "write"]) == 3


def test_device_operations_do_not_self_lock_caller_must_wrap_in_async_with() -> None:
    spi = make_spi()
    device = make_device(spi)

    async def scenario() -> None:
        await device.write(b"x")  # no `async with device:` wrapper at all
        assert not spi.async_lock.locked()  # never touched: write() itself doesn't lock

    run(scenario())


# ---------------------------------------------------------------------------
# asyncio interlock: concurrent bus requests must serialize through the shared lock
# ---------------------------------------------------------------------------


def test_two_devices_sharing_a_bus_never_run_concurrently() -> None:
    spi = make_spi()
    device_a = make_device(spi, cs_pin=1)
    device_b = make_device(spi, cs_pin=6)
    concurrent = 0
    max_concurrent = 0

    async def worker(device: SPIDevice) -> None:
        nonlocal concurrent, max_concurrent
        async with device:
            concurrent += 1
            max_concurrent = max(max_concurrent, concurrent)
            await asyncio.sleep(0)
            concurrent -= 1

    async def scenario() -> None:
        await asyncio.gather(worker(device_a), worker(device_b))

    run(scenario())
    assert max_concurrent == 1


def test_four_concurrent_sessions_all_complete_and_stay_serialized() -> None:
    spi = make_spi()
    devices = [make_device(spi, cs_pin=pin) for pin in (1, 6, 7, 8)]
    concurrent = 0
    max_concurrent = 0
    completed = 0

    async def worker(device: SPIDevice) -> None:
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
    assert completed == 4


def test_same_device_used_from_two_concurrent_tasks_serializes_too() -> None:
    spi = make_spi()
    device = make_device(spi)
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
    spi = make_spi()
    device = make_device(spi)

    async def scenario() -> None:
        try:
            async with device:
                raise RuntimeError("boom")
        except RuntimeError:
            pass
        assert not spi.async_lock.locked()
        async with device:  # must still be acquirable - not left stuck locked
            pass

    run(scenario())


def test_context_manager_does_not_suppress_exceptions() -> None:
    spi = make_spi()
    device = make_device(spi)

    async def scenario() -> None:
        async with device:
            raise ValueError("boom")

    try:
        run(scenario())
        raised = False
    except ValueError:
        raised = True
    assert raised


def test_task_cancellation_while_holding_the_lock_still_releases_it() -> None:
    spi = make_spi()
    device = make_device(spi)
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
        assert spi.async_lock.locked()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        assert not spi.async_lock.locked()

    run(scenario())


def test_reentrant_acquisition_on_the_same_device_deadlocks_and_cleans_up() -> None:
    spi = make_spi()
    device = make_device(spi)

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
    assert not spi.async_lock.locked()


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
