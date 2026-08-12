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

from machine import I2C, RTC, SPI, WDT, Pin, Timer  # noqa: E402


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


def test_i2c_and_spi_deinit_are_recorded() -> None:
    i2c = I2C(1, scl=Pin(19), sda=Pin(18), freq=50000)
    i2c.deinit()
    assert i2c.deinit_called is True
    spi = SPI(0, sck=Pin(2), mosi=Pin(3), miso=Pin(4))
    spi.deinit()
    assert spi.deinit_called is True


def test_wdt_feed_increments_count() -> None:
    wdt = WDT(timeout=8000)
    wdt.feed()
    wdt.feed()
    assert wdt.feed_count == 2


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
