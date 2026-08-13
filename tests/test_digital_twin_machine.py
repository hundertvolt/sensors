"""Deterministic unit tests for digital_twin/machine.py - the bus-level Pin/I2C/SPI/Timer/WDT/RTC
fakes that stand in for the Unix port's real (absent) machine module during a Step 5 integration
run. Exercises real-wozi-wiring dispatch (i2c id 0 -> SCD30@0x61, id 1 -> SGP40@0x59+BMP3xx@0x77,
spi id 0 -> FRAM) and bus-level fault behavior (unknown-address NAK, general-call tolerance).
Per-chip protocol correctness is covered by tests/test_digital_twin_sgp40.py/_scd30.py/_bmp3xx.py/
_fram.py - this file only checks that machine.py routes to the right chip and behaves like a real
bus otherwise. The one exception to this step's "not flaky wall-clock-timing assertions" criterion
is test_timer_fires_for_real_on_a_short_period below: a short period + a generous asyncio.wait_for
bound, checking the scheduling mechanism works at all - not a precise-cadence assertion.
"""

import asyncio
import sys

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Coroutine
    from typing import Any, TypeVar

    T = TypeVar("T")

# digital_twin/ must precede tests/ here specifically so `machine` resolves to the twin's own
# fake, not tests/machine.py's (which would otherwise shadow it - both files are named `machine`).
# See test_digital_twin_sgp40.py's own comment for why this is a per-file sys.path insertion
# rather than a scripts/test.sh/MICROPYPATH change.
sys.path.insert(0, "digital_twin")

import machine  # noqa: E402 - whole-module import, needed for the live reset_count/bootloader_count globals below
from machine import (  # noqa: E402
    I2C,
    RTC,
    SPI,
    WDT,
    Pin,
    SimulatedBootloaderEntry,
    SimulatedReboot,
    SimulatedReset,
    Timer,
    bootloader,
    reset,
)


def run(coro: "Coroutine[Any, Any, T]") -> "T":
    return asyncio.run(coro)


def test_pin_shares_identity_by_id_matching_real_hardware() -> None:
    # Two Pin(8) constructions (one inside machine.I2C's own SCD30 wiring, one from
    # src/asy_scd30_driver.py's own SCD30_Reader.__init__) must refer to the same physical pin.
    p1 = Pin(8, mode=Pin.IN)
    p2 = Pin(8, mode=Pin.IN)
    p1.on()
    assert p2.value() == 1
    p2.off()
    assert p1.value() == 0


def test_pin_rejects_invalid_id() -> None:
    try:
        Pin(99)
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


def test_pin_value_setter_form_sets_and_returns_none() -> None:
    pin = Pin(21)
    assert pin.value(1) is None
    assert pin.value() == 1
    assert pin.value(0) is None
    assert pin.value() == 0


def test_pin_toggle_flips_the_current_value() -> None:
    pin = Pin(22)
    pin.off()
    pin.toggle()
    assert pin.value() == 1
    pin.toggle()
    assert pin.value() == 0


def test_pin_simulate_edge_to_the_same_value_does_not_fire_the_irq_handler() -> None:
    fired: list[int] = []
    pin = Pin(23)
    pin.off()
    pin.irq(handler=lambda p: fired.append(1), trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING)
    pin.simulate_edge(0)  # already 0 - not a real transition, must be a no-op
    assert fired == []


def test_pin_irq_fires_on_simulate_edge_rising() -> None:
    fired: list[int | None] = []
    pin = Pin(20)
    pin.off()
    pin.irq(handler=lambda p: fired.append(p.value()), trigger=Pin.IRQ_RISING)
    pin.simulate_edge(1)
    assert fired == [1]
    pin.simulate_edge(0)  # falling edge - not registered, handler must not fire again
    assert fired == [1]


def test_i2c_id0_wires_scd30_at_0x61_and_naks_everything_else() -> None:
    Pin.reset_registry()  # isolate from other tests that also touch pin 8 (SCD30's own RDY pin)
    i2c = I2C(0, scl=Pin(13), sda=Pin(12), freq=50000)
    assert i2c.scan() == [0x61]
    try:
        i2c.writeto(0x59, b"\x00")  # SGP40 is not on this bus
        raise AssertionError("expected OSError")
    except OSError:
        pass


def test_configure_random_source_threads_through_to_newly_wired_chips() -> None:
    # Mirrors configure_fram_state_path()'s own module-level-hook shape: must not affect a chip
    # already wired before the call, only chips wired by a *later* I2C() construction.
    Pin.reset_registry()
    try:

        class _FixedRandom:
            def uniform(self, a: float, b: float) -> float:
                return a

            def randint(self, a: int, b: int) -> int:
                return a

            def getrandbits(self, k: int) -> int:
                return 0

        machine.configure_random_source(_FixedRandom())
        i2c0 = I2C(0, scl=Pin(13), sda=Pin(12), freq=50000)
        scd30 = i2c0.devices[0x61]
        assert scd30._co2 == scd30._min_co2  # drawn via the fixed source's uniform(a, b) -> a
    finally:
        machine.configure_random_source(None)  # don't leak into later tests in this file


def test_i2c_id1_wires_sgp40_and_bmp3xx() -> None:
    i2c = I2C(1, scl=Pin(19), sda=Pin(18), freq=50000)
    assert sorted(i2c.scan()) == [0x59, 0x77]


def test_i2c_general_call_address_is_always_tolerated() -> None:
    i2c = I2C(1, scl=Pin(19), sda=Pin(18), freq=50000)
    i2c.writeto(0x00, b"\x06")  # must not raise, regardless of what's wired


def test_i2c_writeto_and_readfrom_into_dispatch_to_the_wired_sgp40_device() -> None:
    i2c = I2C(1, scl=Pin(19), sda=Pin(18), freq=50000)
    i2c.writeto(0x59, b"\x28\x0e")  # self-test
    reply = bytearray(3)
    i2c.readfrom_into(0x59, reply)
    assert bytes(reply)[0] == 0xD4


def test_i2c_readfrom_mem_and_writeto_mem_dispatch_to_the_wired_bmp3xx_device() -> None:
    i2c = I2C(1, scl=Pin(19), sda=Pin(18), freq=50000)
    reply = i2c.readfrom_mem(0x77, 0x00, 1)
    assert reply[0] in (0x50, 0x60)


def test_spi_id0_wires_the_fram_chip() -> None:
    spi = SPI(0, sck=Pin(2), mosi=Pin(3), miso=Pin(4))
    spi.write(bytes([0x9F]))  # RDID
    reply = bytearray(4)
    spi.readinto(reply)
    assert bytes(reply) == bytes([0x04, 0x7F, 0x03, 0x02])


def test_spi_init_updates_settings_and_rejects_lsb_first() -> None:
    spi = SPI(0, sck=Pin(2), mosi=Pin(3), miso=Pin(4))
    spi.init(baudrate=2000000, polarity=1, phase=1, bits=8, firstbit=SPI.MSB)
    assert spi.baudrate == 2000000
    assert spi.polarity == 1
    try:
        spi.init(firstbit=SPI.LSB)  # real rp2 hardware SPI is MSB-first only
        raise AssertionError("expected NotImplementedError")
    except NotImplementedError:
        pass


def test_spi_write_readinto_dispatches_to_the_wired_device() -> None:
    spi = SPI(0, sck=Pin(2), mosi=Pin(3), miso=Pin(4))
    try:
        spi.write_readinto(bytes([0x9F]), bytearray(4))  # mismatched lengths
        raise AssertionError("expected ValueError")
    except ValueError:
        pass  # buffers must be the same length, matching real rp2 hardware SPI
    buffer_out = bytes([0x9F, 0x00, 0x00, 0x00])  # RDID opcode, then 3 don't-care bytes
    buffer_in = bytearray(4)
    spi.write_readinto(buffer_out, buffer_in)
    assert bytes(buffer_in) == bytes([0x04, 0x7F, 0x03, 0x02])  # real MB85RS64V device ID


def test_spi_id1_wires_no_device_and_reads_back_zeroed_bytes() -> None:
    # Only spi0 carries the wozi wiring's own FRAM chip (machine.py's own docstring) - an id nothing
    # wires (see _wire_spi_device()) still behaves like a real, present-but-unconnected bus rather
    # than raising: write() is logged and silently dropped, readinto() zero-fills the buffer.
    spi = SPI(1, sck=Pin(5), mosi=Pin(6), miso=Pin(7))
    assert spi.device is None
    spi.write(bytes([0x9F]))
    buf = bytearray([0xFF, 0xFF, 0xFF])
    spi.readinto(buf)
    assert bytes(buf) == bytes(3)


def test_i2c_and_spi_deinit_are_recorded() -> None:
    i2c = I2C(1, scl=Pin(19), sda=Pin(18), freq=50000)
    i2c.deinit()
    assert i2c.deinit_called is True
    spi = SPI(0, sck=Pin(2), mosi=Pin(3), miso=Pin(4))
    spi.deinit()
    assert spi.deinit_called is True


def test_i2c_log_stays_bounded_across_many_transactions() -> None:
    # Regression test for FINAL_WIRING_PLAN.md's Step 5 baseline-verification pass: I2C.log used to
    # be a plain, unbounded list, growing for the life of the process - the dominant contributor to
    # a real MemoryError reproduced by actually running the assembled system end-to-end (real
    # asyncio/HTTP/bus-transaction churn eventually needed a large-enough contiguous reallocation to
    # grow it, which failed once the heap fragmented). Now a deque(maxlen=_LOG_MAXLEN).
    i2c = I2C(1, scl=Pin(19), sda=Pin(18), freq=50000)
    for _ in range(machine._LOG_MAXLEN + 50):
        i2c.writeto(0x00, b"")  # general-call address - always tolerated, logged every time
    assert len(i2c.log) == machine._LOG_MAXLEN
    assert i2c.log[-1] == ("writeto", 0x00, b"", True)  # most recent entry survives, not the oldest


def test_spi_log_stays_bounded_across_many_transactions() -> None:
    spi = SPI(1, sck=Pin(5), mosi=Pin(6), miso=Pin(7))  # id 1 wires no device - write() still logs
    for _ in range(machine._LOG_MAXLEN + 50):
        spi.write(bytes([0x00]))
    assert len(spi.log) == machine._LOG_MAXLEN
    assert spi.log[-1] == ("write", bytes([0x00]))


def test_wdt_feed_increments_count() -> None:
    wdt = WDT(timeout=8000)
    wdt.feed()
    wdt.feed()
    assert wdt.feed_count == 2


def test_wdt_rejects_a_nonzero_id() -> None:
    # Confirmed directly against the pinned v1.28.0 ports/rp2/machine_wdt.c source: rp2 only ever
    # implements id 0 - WDT(id=1) raises ValueError("WDT(1) doesn't exist") on real hardware.
    try:
        WDT(id=1)
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


def test_wdt_rejects_a_timeout_above_the_rp2040_hard_cap() -> None:
    # Confirmed directly against the same source: WDT_TIMEOUT_MAX is 8388 (0xffffff / 2 / 1000);
    # above it, watchdog_enable() is never even reached - construction itself raises ValueError.
    try:
        WDT(timeout=8389)
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


def test_wdt_accepts_a_timeout_at_exactly_the_hard_cap() -> None:
    wdt = WDT(timeout=8388)
    assert wdt.timeout == 8388


def test_wdt_would_have_triggered_count_and_log_start_at_zero() -> None:
    wdt = WDT(timeout=8000)
    assert wdt.would_have_triggered_count == 0
    assert wdt.would_have_triggered_log == []


def test_wdt_notifies_once_after_a_feed_free_window() -> None:
    # Short timeout + a generous asyncio.wait_for bound - same "does the mechanism work at all"
    # spirit as test_timer_fires_for_real_on_a_short_period below, not a precise-cadence assertion.
    # Polling far finer than the WDT's own period (5ms vs. 150ms) matters here, not just style: the
    # background monitor loops forever rather than stopping after one notification, so a poll
    # granularity close to the WDT's own period races it - the exact count observed depends on how
    # many of its own cycles complete before this loop's next wakeup gets scheduled.
    async def scenario() -> None:
        wdt = WDT(timeout=150)
        for _ in range(200):
            if wdt.would_have_triggered_count >= 1:
                return
            await asyncio.sleep_ms(5)
        raise AssertionError("WDT never noticed a feed-free window")

    run(asyncio.wait_for(scenario(), 5))


def test_wdt_feed_resets_the_countdown_and_prevents_a_notification() -> None:
    async def scenario() -> int:
        wdt = WDT(timeout=100)
        for _ in range(6):  # ~120ms of continuous feeding, comfortably past one 100ms window
            await asyncio.sleep_ms(20)
            wdt.feed()
        return wdt.would_have_triggered_count

    count = run(asyncio.wait_for(scenario(), 5))
    assert count == 0  # kept fed the whole time - never should have noticed a gap


def test_wdt_keeps_monitoring_after_a_would_have_triggered_notification() -> None:
    # "keeps monitoring so a long-unfed stretch can notify more than once" - not a one-shot.
    async def scenario() -> None:
        wdt = WDT(timeout=150)
        for _ in range(600):
            if wdt.would_have_triggered_count >= 2:
                return
            await asyncio.sleep_ms(5)
        raise AssertionError("WDT never reached a second would-have-triggered notification")

    run(asyncio.wait_for(scenario(), 8))


def test_wdt_would_have_triggered_log_records_the_feed_count_at_each_notification() -> None:
    async def scenario() -> "list[int]":
        wdt = WDT(timeout=150)
        wdt.feed()
        wdt.feed()  # feed_count is 2 going into the unfed stretch below
        for _ in range(200):
            if wdt.would_have_triggered_count >= 1:
                return wdt.would_have_triggered_log
            await asyncio.sleep_ms(5)
        raise AssertionError("WDT never noticed a feed-free window")

    log = run(asyncio.wait_for(scenario(), 5))
    assert log[0] == 2  # the first notification must reflect feed_count as of the unfed stretch


def test_wdt_on_would_trigger_callback_fires_with_the_wdt_instance() -> None:
    async def scenario() -> "list[WDT]":
        seen: list[WDT] = []
        _wdt = WDT(timeout=150, on_would_trigger=lambda w: seen.append(w))
        for _ in range(200):
            if seen:
                return seen
            await asyncio.sleep_ms(5)
        raise AssertionError("on_would_trigger callback never fired")

    seen = run(asyncio.wait_for(scenario(), 5))
    assert seen[0].would_have_triggered_count >= 1


def test_reset_increments_the_module_counter_then_raises_simulated_reset() -> None:
    before = machine.reset_count
    try:
        reset()
        raise AssertionError("expected SimulatedReset")
    except SimulatedReset:
        pass
    assert machine.reset_count == before + 1


def test_bootloader_increments_the_module_counter_then_raises_simulated_bootloader_entry() -> None:
    before = machine.bootloader_count
    try:
        bootloader()
        raise AssertionError("expected SimulatedBootloaderEntry")
    except SimulatedBootloaderEntry:
        pass
    assert machine.bootloader_count == before + 1


def test_simulated_reset_and_bootloader_entry_are_both_simulated_reboot() -> None:
    assert issubclass(SimulatedReset, SimulatedReboot)
    assert issubclass(SimulatedBootloaderEntry, SimulatedReboot)
    try:
        reset()
        raise AssertionError("expected SimulatedReboot")
    except SimulatedReboot:
        pass  # caught via the base class, not the specific subclass


def test_rtc_datetime_round_trips() -> None:
    rtc = RTC()
    rtc.datetime((2026, 1, 1, 4, 12, 0, 0, 0))
    assert rtc.datetime()[0:3] == (2026, 1, 1)


def test_timer_deinit_stops_further_callbacks() -> None:
    calls: list[int] = []
    timer = Timer()
    timer.init(period=20, mode=Timer.PERIODIC, callback=lambda t: calls.append(1))

    async def scenario() -> "tuple[int, int]":
        await asyncio.sleep_ms(60)
        timer.deinit()
        count_at_deinit = len(calls)
        await asyncio.sleep_ms(80)
        return count_at_deinit, len(calls)

    count_at_deinit, count_after = run(scenario())
    assert count_at_deinit >= 1
    assert count_after == count_at_deinit  # nothing fired after deinit()


def test_timer_fires_for_real_on_a_short_period() -> None:
    # The one live-timing test in this whole package (see module docstring): a very short period
    # with a generous asyncio.wait_for bound, checking the asyncio-task-scheduled mechanism itself
    # actually fires at least once - not a precise-cadence assertion.
    fired: list[int] = []
    timer = Timer()

    async def scenario() -> None:
        timer.init(period=20, mode=Timer.ONE_SHOT, callback=lambda t: fired.append(1))
        for _ in range(100):  # up to ~2s total, generous relative to the 20ms period
            if fired:
                return
            await asyncio.sleep_ms(20)
        raise AssertionError("Timer callback never fired")

    run(asyncio.wait_for(scenario(), 5))
    assert fired == [1]


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
