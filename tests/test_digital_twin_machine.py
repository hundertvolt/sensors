"""Deterministic unit tests for digital_twin/machine.py's bus-level Pin/I2C/SPI/Timer/WDT/RTC fakes - exercises generated-plan dispatch and bus-level fault behavior; per-chip protocol correctness lives in the per-chip test files instead.
test_timer_fires_for_real_on_a_short_period is the one genuine (bounded, generous-timeout) wall-clock exception."""

import asyncio
import errno
import json
import os
import sys
import time

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import TypeVar

    from _twin_devices import TwinWiringPlan

    A = TypeVar("A")

# digital_twin/ must precede tests/ here specifically so `machine` resolves to the twin's own fake rather
# than tests/machine.py's, both files being named `machine`. See test_digital_twin_sgp40.py for why this is
# a per-file sys.path insertion rather than a scripts/test.sh change.
sys.path.insert(0, "digital_twin")

import _flash_stall
import _mem_backup_contract
import _wall_clock
import machine
import microtest
from _async_harness import run
from _crc8 import crc8, word
from _fault_injection import FaultInjector
from _machine_contract import ALL_CHECKS, FAULT_CHECKS
from _ticks30 import Ticks30Time
from _tmp_scratch import TmpScratch
from _twin_common import COUNTER_CAP, LOG_MAXLEN, BoundedLog, StatePaths, fill_buffer, saturating_add
from _twin_devices import generated_devices, wiring_plan
from _twin_random import FixedRandom
from machine import (
    I2C,
    RTC,
    SPI,
    UART,
    WDT,
    Pin,
    SimulatedBootloaderEntryError,
    SimulatedRebootError,
    SimulatedResetError,
    Timer,
    UARTLink,
    bootloader,
    reset,
)

# @tunable l2.machine_wdt_short_timeout_ms = 100
_WDT_SHORT_TIMEOUT_MS = 100
# @tunable l2.machine_wdt_poll_ms = 5
_WDT_POLL_MS = 5
# @tunable l2.machine_wdt_poll_tries = 200
_WDT_POLL_TRIES = 200
# @tunable l2.machine_wdt_second_notice_poll_tries = 600
_WDT_SECOND_NOTICE_POLL_TRIES = 600
# @tunable l2.machine_run_bound_s = 5
_RUN_BOUND_S = 5
# @tunable l2.machine_wdt_fed_timeout_ms = 100
_WDT_FED_TIMEOUT_MS = 100
# @tunable l2.machine_feed_step_ms = 20
_FEED_STEP_MS = 20
# @tunable l2.machine_feed_rounds = 6
_FEED_ROUNDS = 6
# @tunable l2.machine_double_trigger_bound_s = 8
_DOUBLE_TRIGGER_BOUND_S = 8
# @tunable l2.machine_timer_period_ms = 20
_TIMER_PERIOD_MS = 20
# @tunable l2.machine_before_deinit_ms = 60
_BEFORE_DEINIT_MS = 60
# @tunable l2.machine_after_deinit_ms = 80
_AFTER_DEINIT_MS = 80
# @tunable l2.machine_chain_period_ms = 10
_CHAIN_PERIOD_MS = 10
# @tunable l2.machine_chain_poll_ms = 10
_CHAIN_POLL_MS = 10
# @tunable l2.machine_chain_poll_tries = 100
_CHAIN_POLL_TRIES = 100
# @tunable l2.machine_fire_poll_ms = 20
_FIRE_POLL_MS = 20
# @tunable l2.machine_fire_poll_tries = 100
_FIRE_POLL_TRIES = 100


# @tunable l2.machine_timer_short_period_ms = 5
_SHORT_PERIOD_MS = 5
# @tunable l2.machine_timer_rearm_window_ms = 18
_REARM_WINDOW_MS = 18
# @tunable l2.machine_spi_wire_time_us_per_byte = 200
_WIRE_US_PER_BYTE = 200
_RSR_OE = 0x08  # UARTRSR's overrun bit (RP2040 datasheet Table 427)

_scratch = TmpScratch("dtmachine")
# The shared contract's checks this twin still fails, each with the twin change that closes it; the list only shrinks.
_TWIN_PENDING: "tuple[tuple[str, str], ...]" = ()
# The hardware a test needs, per bus: an I2C bus as {address: driver}, an SPI bus as (driver, max_size) or None; it runs
# on the first generated device wiring exactly that (_board()), picked by its wiring as SPECIFICATION.md E.2.1 says.
_BOARD: "dict[str, object]" = {"i2c0": {0x61: "scd30"}, "i2c1": {0x59: "sgp40", 0x77: "bmp3xx"}, "spi0": ("fram", 0x2000), "spi1": None}
_ISL29125_BOARD: "dict[str, object]" = {"i2c1": {0x44: "isl29125", 0x59: "sgp40", 0x61: "scd30"}}

microtest.after_each(machine.reset_test_state)


def _attached(plan: "TwinWiringPlan", bus: str) -> object:
    # One bus of a plan in _BOARD's form.
    if bus.startswith("i2c"):
        return {chip["address"]: chip["driver"] for chip in plan["buses"].get(bus, [])}
    fram = plan["spi"].get(bus)
    return None if fram is None else (fram["driver"], fram["max_size"])


def _board(wiring: "dict[str, object]") -> str:
    # The first generated device whose plan wires exactly `wiring` on every bus it names.
    searched = generated_devices()
    for device in searched:
        plan = wiring_plan(device)
        if all(_attached(plan, bus) == want for bus, want in wiring.items()):
            return device
    raise AssertionError(f"no generated device wires {wiring!r} - searched {searched!r}")


def _contract_failure(check: "Callable[[A], None]", backend: "A") -> "str | None":
    # One check inside one harness run on a fresh _BOARD: a WDT or chip timer it starts is cancelled with the run.
    async def body() -> "str | None":
        try:
            check(backend)
        except Exception as exc:  # the check's failure is the answer here, every kind of it
            return f"{type(exc).__name__}: {exc}"
        return None

    machine.reset_test_state()
    _wire()
    try:
        return run(body())
    finally:
        machine.reset_test_state()


def _errno_of(call: "Callable[[], object]") -> "int | None":
    try:
        call()
    except OSError as e:
        return e.errno
    return None


def _inside_one_run(test: "Callable[[], None]") -> "Callable[[], None]":
    # The twin's WDT and its chips' timers start asyncio tasks when built: the body runs inside one harness call,
    # which cancels every task it created, so no test leaves one parked on the scheduler.
    async def body() -> None:
        test()

    def wrapper() -> None:
        run(body())

    return wrapper


def _on_the_2_30_clock(drive: "Callable[[Ticks30Time, UART, UART], None]") -> None:
    # A link built at zero on rp2's 2**30 tick period (tests/_ticks30.py), the stalls' clock on it from the same zero.
    machine.reset_peripherals()
    a, b = UART(0, tx=Pin(0), rx=Pin(1)), UART(1, tx=Pin(8), rx=Pin(9))
    clock, stall_time = Ticks30Time(), _flash_stall._time  # type: ignore[attr-defined]
    machine.time, _flash_stall._time = clock, clock  # type: ignore[assignment, attr-defined]  # module attribute swaps, restored below
    _flash_stall.restart(0, 0)
    try:
        UARTLink(a, b)
        drive(clock, a, b)
    finally:
        machine.time, _flash_stall._time = time, stall_time  # type: ignore[attr-defined]
        _flash_stall.restart(time.ticks_us(), time.ticks_ms())
        _flash_stall.windows.clear()


def _reports_during(scenario: "Callable[[], object]") -> "list[tuple[str, bool]]":
    # Runs `scenario` with machine's uncaught-callback report recorded rather than printed.
    reported: list[tuple[str, bool]] = []
    report = machine._report_uncaught
    machine._report_uncaught = lambda exc, *, hard: reported.append((str(exc), hard))
    try:
        scenario()
    finally:
        machine._report_uncaught = report
    return reported


def test_the_twin_meets_the_shared_machine_contract_but_for_its_pending_checks() -> None:
    pending = {name for name, _why in _TWIN_PENDING}
    failures = {check.__name__: _contract_failure(check, machine) for check in ALL_CHECKS}
    failures.update({check.__name__: _contract_failure(check, _twin_injector) for check in FAULT_CHECKS})
    assert pending <= set(failures), f"a pending entry names no registered check: {sorted(pending - set(failures))}"
    failing = {name for name, why in failures.items() if why is not None}
    assert failing == pending, f"failing {sorted(failing)}, pending {sorted(pending)}: {failures}"


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


def _stall_on(clock: Ticks30Time) -> None:
    # One flush of 13 page programs and no erase (5.2 ms) on the 2**30 clock, _flash_stall's reads stepping it.
    stall_time, erases, extra = _flash_stall._time, _flash_stall.FLUSH_ERASES, _flash_stall.FLUSH_EXTRA_PAGES  # type: ignore[attr-defined]
    _flash_stall._time, _flash_stall.FLUSH_ERASES, _flash_stall.FLUSH_EXTRA_PAGES = _StallClock(clock), 0, 13  # type: ignore[assignment, attr-defined]
    try:
        _flash_stall.stall(0)
    finally:
        _flash_stall._time, _flash_stall.FLUSH_ERASES, _flash_stall.FLUSH_EXTRA_PAGES = stall_time, erases, extra  # type: ignore[attr-defined]


def _twin_injector() -> "tuple[Callable[[int], None], Callable[[], object], Callable[[], int]]":
    # The shared fault check's backend: a chip's FaultInjector, which every twin chip fake builds its faults on.
    injector = FaultInjector()

    def inject(times: int) -> None:
        injector.inject_fault("readinto", OSError, errno.EIO, "planted", times=times)

    return inject, lambda: injector.maybe_raise("readinto"), lambda: injector.pending("readinto")


def _value_error(call: "Callable[[], object]") -> str:
    try:
        call()
    except ValueError as e:
        return str(e)
    raise AssertionError("expected ValueError")


def _wire(wiring: "dict[str, object]" = _BOARD) -> None:
    # One explicit board per test: the generated plan of the device _board() picks for the hardware the test needs.
    machine.configure_wiring(wiring_plan(_board(wiring)))


def test_pin_takes_rp2s_ids_and_names_as_one_object() -> None:
    # machine_pin_find(), machine_pin.c:165-192: a board then a CPU name, or a number below 30 (pins.csv, make-pins.py).
    assert Pin(29).id == 29 and Pin("GP15") is Pin(15) is Pin("GPIO15") and Pin("LED") is Pin("EXT_GPIO0")
    assert Pin(Pin(7)) is Pin(7)
    assert _value_error(lambda: Pin(30)) == _value_error(lambda: Pin(1.5)) == "invalid pin"  # type: ignore[arg-type]
    assert _value_error(lambda: Pin("GP23")) == 'unknown named pin "GP23"'


def test_pin_reconfigured_without_a_pull_loses_it() -> None:
    pin = Pin(21, Pin.IN, Pin.PULL_UP)
    Pin(21, Pin.IN)
    assert not pin.pull
    Pin(21)  # an id alone configures nothing
    assert pin.mode == Pin.IN


def test_pin_alt_takes_only_the_functions_the_pins_row_lists() -> None:
    # ports/rp2/boards/rp2040_af.csv: AFn is GPIO_FUNC n; GPCK (8) exists on GPIO20-25 only, XIP (0) on none.
    Pin(20, Pin.ALT, alt=8)
    assert (Pin(20).mode, Pin(20).alt) == (Pin.ALT, 8)
    assert _value_error(lambda: Pin(5, Pin.ALT, alt=8)) == "invalid pin af: 8"
    assert _value_error(lambda: Pin(5, Pin.ALT, alt=0)) == "invalid pin af: 0"


def test_an_external_pin_refuses_pulls_alternate_functions_and_other_modes() -> None:
    # machine_pin.c:256-262 and machine_pin_cyw43.c: the CYW43's GPIOs are plain IN/OUT lines.
    assert _value_error(lambda: Pin("LED", Pin.OUT, Pin.PULL_UP)) == "pulls are not supported for external pins"
    assert _value_error(lambda: Pin("WL_GPIO1", Pin.IN, alt=Pin.ALT_I2C)) == "alternate functions are not supported for external pins"
    assert _value_error(lambda: Pin("WL_GPIO2", Pin.OPEN_DRAIN)) == "only Pin.OUT and Pin.IN are supported for this pin"
    led = Pin("LED", Pin.OUT, value=1)
    assert led.value() == 1


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
    pin.irq(handler=lambda _p: fired.append(1), trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING)
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


def test_pin_irq_refuses_an_external_pin_and_a_bare_call_keeps_the_handler() -> None:
    # ports/rp2/machine_pin.c:464-476: a WLAN-chip GPIO raises before any argument is read; a call with no argument
    # returns the IRQ object unchanged, while an explicit None clears the handler.
    fired: list[int] = []
    try:
        Pin("LED").irq(handler=lambda _p: None)
    except ValueError as e:
        assert str(e) == "expecting a regular GPIO Pin"
    else:
        raise AssertionError("an external pin took an irq")
    pin = Pin(27)
    pin.off()
    pin.irq(handler=lambda _p: fired.append(1), trigger=Pin.IRQ_RISING)
    assert pin.irq() is pin
    pin.simulate_edge(1)
    assert fired == [1]
    pin.simulate_edge(0)
    pin.irq(None)
    pin.simulate_edge(1)
    assert fired == [1]


@_inside_one_run
def test_i2c_id0_wires_scd30_at_0x61_and_naks_everything_else() -> None:
    _wire()
    Pin.reset_registry()  # isolate from other tests that also touch pin 8 (SCD30's own RDY pin)
    i2c = I2C(0, scl=Pin(13), sda=Pin(12), freq=50000)
    assert i2c.scan() == [0x61]
    try:
        i2c.writeto(0x59, b"\x00")  # SGP40 is not on this bus
        raise AssertionError("expected OSError")
    except OSError:
        pass


@_inside_one_run
def test_configure_random_source_threads_through_to_newly_wired_chips() -> None:
    # Mirrors configure_fram_state_path()'s own module-level-hook shape: set before the bus exists, it reaches
    # every chip that bus wires.
    machine.configure_random_source(FixedRandom())  # unscripted: uniform(a, b) answers a
    _wire()
    i2c0 = I2C(0, scl=Pin(13), sda=Pin(12), freq=50000)
    scd30 = i2c0.devices[0x61]
    assert scd30._co2 == 400.0  # the CO2 walk's lower bound (_scd30_chip.py's default), the fixed source's uniform(a, b) -> a


def test_i2c_id1_wires_sgp40_and_bmp3xx() -> None:
    _wire()
    i2c = I2C(1, scl=Pin(19), sda=Pin(18), freq=50000)
    assert sorted(i2c.scan()) == [0x59, 0x77]


def test_i2c_general_call_address_is_always_tolerated() -> None:
    _wire()
    i2c = I2C(1, scl=Pin(19), sda=Pin(18), freq=50000)
    i2c.writeto(0x00, b"\x06")  # must not raise, regardless of what's wired


def test_i2c_writeto_and_readfrom_into_dispatch_to_the_wired_sgp40_device() -> None:
    _wire()
    i2c = I2C(1, scl=Pin(19), sda=Pin(18), freq=50000)
    i2c.writeto(0x59, b"\x28\x0e")  # self-test
    reply = bytearray(3)
    i2c.readfrom_into(0x59, reply)
    assert bytes(reply)[0] == 0xD4


def test_i2c_readfrom_mem_and_writeto_mem_dispatch_to_the_wired_bmp3xx_device() -> None:
    _wire()
    i2c = I2C(1, scl=Pin(19), sda=Pin(18), freq=50000)
    reply = i2c.readfrom_mem(0x77, 0x00, 1)
    assert reply[0] in (0x50, 0x60)


@_inside_one_run
def test_an_isl29125_board_wires_it_on_i2c1_beside_scd30_and_sgp40() -> None:
    # The twin wires what the plan attaches: three chips on this board's i2c1, two on _BOARD's (asserted above).
    _wire(_ISL29125_BOARD)
    i2c = I2C(1, scl=Pin(15), sda=Pin(14), freq=50000)
    assert sorted(i2c.scan()) == [0x44, 0x59, 0x61]
    assert i2c.readfrom_mem(0x44, 0x00, 1) == bytes([0x7D])  # device ID, p9 Table 2
    i2c.writeto_mem(0x44, 0x01, bytes([0x05, 0x00, 0x00]))  # the driver's own 3-byte burst
    assert i2c.readfrom_mem(0x44, 0x01, 3) == bytes([0x05, 0x00, 0x00])


@_inside_one_run
def test_an_isl29125_board_hands_the_chip_the_same_pin_object_the_driver_constructs() -> None:
    # machine.py's Pin is a per-id registry singleton, and that identity is what lets the chip
    # fake's simulate_edge() reach a handler the driver registered on its own irq Pin. A later "fix"
    # returning fresh objects would break the whole interrupt path with nothing else failing.
    _wire(_ISL29125_BOARD)
    (irq_pin,) = [a["irq_pin"] for a in wiring_plan(_board(_ISL29125_BOARD))["buses"]["i2c1"] if a["driver"] == "isl29125"]
    i2c = I2C(1, scl=Pin(15), sda=Pin(14), freq=50000)
    chip = i2c.devices[0x44]
    driver_side = Pin(irq_pin, mode=Pin.IN, pull=Pin.PULL_UP)
    assert chip._int_pin is driver_side


@_inside_one_run
def test_a_board_without_the_isl29125_wires_none() -> None:
    _wire()
    assert 0x44 not in I2C(1, scl=Pin(19), sda=Pin(18), freq=50000).devices
    assert 0x44 not in I2C(0, scl=Pin(9), sda=Pin(8), freq=50000).devices


@_inside_one_run
def test_configure_scd30_state_path_and_flush_scd30_round_trip_settings() -> None:
    # Same module-level-hook shape as configure_fram_state_path()/flush_fram(), which has no dedicated
    # wiring test either - so this closes the gap for the SCD30 feature at least. Persistence content is
    # tests/test_digital_twin_scd30.py's job; this only checks the hooks reach the chip that is constructed.
    path = _scratch.path("scd30_machine_wiring.json")
    machine.configure_scd30_state_path(path)
    _wire()
    i2c0a = I2C(0, scl=Pin(13), sda=Pin(12), freq=50000)
    payload = bytes([0x46, 0x00, 0x00, 0x0A])  # SET_MEASUREMENT_INTERVAL, arg=10
    i2c0a.devices[0x61].handle_writeto(payload + bytes([crc8(payload[2:4])]))
    machine.flush_scd30()

    machine.reset_test_state()  # the reboot: a fresh I2C(0) whose SCD30 loads the saved state
    machine.configure_scd30_state_path(path)
    _wire()
    i2c0b = I2C(0, scl=Pin(13), sda=Pin(12), freq=50000)
    assert i2c0b is not i2c0a
    i2c0b.devices[0x61].handle_writeto(bytes([0x46, 0x00]))
    assert i2c0b.devices[0x61].handle_readfrom_into(3) == word(10)


def test_spi_id0_wires_the_fram_chip() -> None:
    _wire()
    spi = SPI(0, sck=Pin(2), mosi=Pin(3), miso=Pin(4))
    spi.write(bytes([0x9F]))  # RDID
    reply = bytearray(4)
    spi.readinto(reply)
    assert bytes(reply) == bytes([0x04, 0x7F, 0x03, 0x02])


def test_spi_init_updates_settings_and_rejects_lsb_first() -> None:
    _wire()
    spi = SPI(0, sck=Pin(2), mosi=Pin(3), miso=Pin(4))
    spi.init(baudrate=2000000, polarity=1, phase=1, bits=8, firstbit=SPI.MSB)
    assert spi.baudrate == 2000000
    assert spi.polarity == 1
    try:
        spi.init(firstbit=SPI.LSB)  # real rp2 hardware SPI is MSB-first only
        raise AssertionError("expected NotImplementedError")
    except NotImplementedError:
        pass


def test_spi_is_one_object_per_id_that_each_construction_reinitialises() -> None:
    # machine_spi.c:161-214: the static object keeps its chip; a construction re-applies every setting, omitted ones
    # at rp2's defaults.
    _wire()
    first = SPI(0, baudrate=2_000_000, polarity=1, sck=Pin(2), mosi=Pin(3), miso=Pin(4))
    chip = first.device
    again = SPI(0, sck=2, mosi=3, miso=4)
    assert again is first and again.device is chip
    assert (again.baudrate, again.polarity, again.log[-1]) == (1_000_000, 0, ("init", 1_000_000, 0, 0, 8, SPI.MSB))


def test_spi_construction_takes_rp2s_ids_pins_and_bit_order() -> None:
    _wire()
    assert _value_error(lambda: SPI(2, sck=Pin(10), mosi=Pin(11), miso=Pin(12))) == "SPI(2) doesn't exist"
    assert _value_error(lambda: SPI(1, sck=Pin(2), mosi=Pin(11), miso=Pin(12))) == "bad SCK pin"  # SPI0's SCK
    assert _value_error(lambda: SPI(1, sck=Pin(10), mosi=Pin(10), miso=Pin(12))) == "bad MOSI pin"
    assert _value_error(lambda: SPI(1, sck=Pin(10), mosi=Pin(11), miso=Pin(13))) == "bad MISO pin"
    try:
        SPI(1, sck=Pin(10), mosi=Pin(11), miso=Pin(12), firstbit=SPI.LSB)
        raise AssertionError("an LSB-first SPI was constructed")
    except NotImplementedError as e:
        assert str(e) == "LSB"


def test_spi_bit_order_numbers_are_rp2s() -> None:
    # pico-sdk hardware/spi.h:184-187 (SPI_LSB_FIRST 0, SPI_MSB_FIRST 1); a construction defaults to MSB first.
    _wire()
    assert (SPI.MSB, SPI.LSB) == (1, 0)
    assert SPI(1, sck=Pin(10), mosi=Pin(11), miso=Pin(12)).firstbit == SPI.MSB


def test_the_fault_injector_counts_its_pending_entries() -> None:
    injector = FaultInjector()
    injector.inject_fault("readinto", OSError, errno.EIO, "planted", times=2)
    assert (injector.pending("readinto"), injector.pending("write")) == (2, 0)
    try:
        injector.maybe_raise("readinto")
        raise AssertionError("expected the queued fault")
    except OSError:
        pass
    assert injector.pending("readinto") == 1


def test_spi_write_readinto_dispatches_to_the_wired_device() -> None:
    _wire()
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
    # Only spi0 carries the board's own FRAM chip (machine.py's own docstring) - an id nothing
    # wires (see _wire_spi_device()) still behaves like a real, present-but-unconnected bus rather
    # than raising: write() is logged and silently dropped, readinto() zero-fills the buffer.
    _wire()
    spi = SPI(1, sck=Pin(10), mosi=Pin(11), miso=Pin(12))
    assert spi.device is None
    spi.write(bytes([0x9F]))
    buf = bytearray([0xFF, 0xFF, 0xFF])
    spi.readinto(buf)
    assert bytes(buf) == bytes(3)


def test_i2c_and_spi_deinit_are_recorded() -> None:
    _wire()
    i2c = I2C(1, scl=Pin(19), sda=Pin(18), freq=50000)
    i2c.deinit()
    assert i2c.deinit_called is True
    spi = SPI(0, sck=Pin(2), mosi=Pin(3), miso=Pin(4))
    spi.deinit()
    assert spi.deinit_called is True


def test_i2c_log_stays_bounded_across_many_transactions() -> None:
    # I2C.log is a ring of LOG_MAXLEN entries: an unbounded log grows for the life of the process until its
    # reallocation fails on a fragmented heap, as an end-to-end run of the assembled system once showed.
    _wire()
    i2c = I2C(1, scl=Pin(19), sda=Pin(18), freq=50000)
    for _ in range(LOG_MAXLEN + 50):
        i2c.writeto(0x00, b"")  # general-call address - the SGP40 listens, logged every time
    assert (len(i2c.log), i2c.log.dropped) == (LOG_MAXLEN, 51)  # the construction's init entry, then 250 writes
    assert i2c.log[-1] == ("writeto", 0x00, b"", True)  # most recent entry survives, not the oldest


def test_pin_open_drain_reads_the_wired_and_of_its_drive_and_the_line() -> None:
    Pin.reset_registry()
    pin = Pin(16, Pin.OPEN_DRAIN, Pin.PULL_UP)
    assert pin.value() == 1  # released: an undriven line reads high, the bus pull-ups
    pin.value(0)
    assert pin.value() == 0
    pin.value(1)
    Pin.set_external_level(16, 0)  # a slave holds the line low
    assert pin.value() == 0
    assert list(Pin.value_log(16)) == [0, 1]
    Pin.reset_registry()
    assert list(Pin.value_log(16)) == []


def test_pin_init_applies_value_before_the_mode_and_records_alt() -> None:
    Pin.reset_registry()
    cs = Pin(17)
    cs.init(Pin.OUT, value=1)
    assert (cs.mode, cs.value()) == (Pin.OUT, 1)
    scl = Pin(13, Pin.ALT, Pin.PULL_UP, alt=Pin.ALT_I2C)
    assert (scl.mode, scl.pull, scl.alt) == (Pin.ALT, Pin.PULL_UP, Pin.ALT_I2C)
    assert (Pin.OPEN_DRAIN, Pin.ALT, Pin.ALT_I2C) == (2, 3, 3)  # ports/rp2/machine_pin.h:34-37, GPIO_FUNC_I2C
    Pin.reset_registry()


def test_pin_external_level_callable_sees_the_value_log() -> None:
    Pin.reset_registry()
    scl = Pin(13, Pin.OPEN_DRAIN, Pin.PULL_UP, value=1)
    sda = Pin(12, Pin.OPEN_DRAIN, Pin.PULL_UP, value=1)
    Pin.set_external_level(12, lambda _pin_id, _log: 1 if list(Pin.value_log(13)).count(0) >= 3 else 0)
    pulses = 0
    while sda.value() == 0 and pulses < 9:
        scl.value(0)
        scl.value(1)
        pulses += 1
    assert pulses == 3
    Pin.reset_registry()


def test_pin_simulate_edge_drives_the_line_a_pulled_up_input_reads() -> None:
    Pin.reset_registry()
    irq = Pin(6, Pin.IN, Pin.PULL_UP)
    assert irq.value() == 1  # idle high through the pull-up, before any edge
    irq.simulate_edge(0)
    assert irq.value() == 0
    Pin.reset_registry()


def test_i2c_is_one_object_per_id_keeping_chips_and_log_across_constructions() -> None:
    _wire()
    first = I2C(1, scl=Pin(19), sda=Pin(18), freq=50000)
    chip = first.devices[0x77]
    again = I2C(1, scl=Pin(19), sda=Pin(18), freq=100000, timeout=1234)
    assert again is first and again.devices[0x77] is chip
    assert again.log[-1] == ("init", 100000, 1234)
    assert (again.freq, again.timeout) == (100000, 1234)
    machine.reset_peripherals()  # a new board: fresh buses and chips on the same plan
    assert I2C(1, scl=Pin(19), sda=Pin(18), freq=50000) is not first


def test_i2c_address_prefixed_writeto_reaches_the_register_handler() -> None:
    _wire()
    i2c = I2C(1, scl=Pin(19), sda=Pin(18), freq=50000)
    assert i2c.writeto(0x77, bytes([0x1C, 0x05]), True) == 2  # OSR register, one payload byte
    assert i2c.devices[0x77].handle_readfrom_mem(0x1C, 1) == bytes([0x05])
    assert i2c.log[-1] == ("writeto", 0x77, bytes([0x1C, 0x05]), True)


def test_i2c_no_stop_address_write_then_readfrom_into_reads_that_register() -> None:
    _wire()
    i2c = I2C(1, scl=Pin(19), sda=Pin(18), freq=50000)
    assert i2c.writeto(0x77, bytes([0x00]), False) == 1  # CHIP_ID pointer
    reply = bytearray(1)
    i2c.readfrom_into(0x77, reply)
    assert reply[0] in (0x50, 0x60)
    assert [entry[0] for entry in list(i2c.log)[-2:]] == ["writeto", "readfrom_into"]


def test_i2c_zero_length_write_to_a_register_chip_is_the_probe() -> None:
    # A zero-length write goes through soft I2C, where a NAK reads ENODEV and a timeout stays ETIMEDOUT
    # (ports/rp2/machine_i2c.c:127-145, extmod/machine_i2c.c:199-203, v1.29.0).
    _wire()
    i2c = I2C(1, scl=Pin(19), sda=Pin(18), freq=50000)
    i2c.devices[0x77].fault.inject_fault("writeto", OSError, errno.EIO, "probe NAK")
    i2c.devices[0x77].fault.inject_fault("writeto", OSError, errno.ETIMEDOUT, "probe stretched")
    assert (_errno_of(lambda: i2c.writeto(0x77, b"")), _errno_of(lambda: i2c.writeto(0x77, b""))) == (errno.ENODEV, errno.ETIMEDOUT)


def test_i2c_an_empty_write_to_an_absent_address_reads_enodev_a_data_write_eio() -> None:
    _wire()
    i2c = I2C(1, scl=Pin(19), sda=Pin(18))
    assert (_errno_of(lambda: i2c.writeto(0x10, b"")), _errno_of(lambda: i2c.writeto(0x10, b"\x00"))) == (errno.ENODEV, errno.EIO)
    assert _errno_of(lambda: i2c.readfrom_into(0x10, bytearray(1))) == errno.EIO


@_inside_one_run
def test_i2c_a_general_call_reaches_only_the_chips_that_listen() -> None:
    # The SGP40 documents the general-call reset (datasheet Table 17); a bus with no listener gets no ACK.
    _wire()
    i2c1 = I2C(1, scl=Pin(19), sda=Pin(18))
    heard: list[bytes] = []
    i2c1.devices[0x59].handle_general_call = lambda data: heard.append(bytes(data))
    assert i2c1.writeto(0x00, b"\x06") == 1
    assert heard == [b"\x06"] and i2c1.log[-1] == ("writeto", 0x00, b"\x06", True)
    i2c0 = I2C(0, scl=Pin(13), sda=Pin(12))
    assert _errno_of(lambda: i2c0.writeto(0x00, b"\x06")) == errno.EIO


def test_i2c_takes_rp2s_ids_and_pin_pairs_and_hands_the_pins_to_the_controller() -> None:
    # machine_i2c.c:80-115 and machine_i2c.h:65-66: SCL odd, SDA even, bit 1 the bus; the init sets function and pull-up.
    _wire()
    I2C(1, scl=19, sda=18)
    assert (Pin(19).mode, Pin(19).alt, Pin(19).pull, Pin(18).mode) == (Pin.ALT, Pin.ALT_I2C, Pin.PULL_UP, Pin.ALT)
    assert _value_error(lambda: I2C(2, scl=Pin(19), sda=Pin(18))) == "I2C(2) doesn't exist"
    assert _value_error(lambda: I2C(1, scl=Pin(18), sda=Pin(19))) == "bad SCL pin"
    assert _value_error(lambda: I2C(1, scl=Pin(19), sda=Pin(16))) == "bad SDA pin"


class _ShortChip:
    # Answers fewer bytes than asked, as a chip read past its last register can.
    def handle_readfrom_into(self, _nbytes: int) -> bytes:
        return b"\x01"


def test_i2c_reads_fill_the_callers_buffer_whatever_its_type() -> None:
    _wire()
    i2c = I2C(1, scl=Pin(19), sda=Pin(18))
    i2c.devices[0x10] = _ShortChip()
    buf = bytearray(b"\xff\xff\xff")
    i2c.readfrom_into(0x10, buf)
    view = memoryview(bytearray(3))
    i2c.readfrom_into(0x10, view)
    assert (buf, bytes(view)) == (bytearray(b"\x01\x00\x00"), b"\x01\x00\x00")


def test_i2c_register_faults_keep_the_chip_keys() -> None:
    _wire()
    i2c = I2C(1, scl=Pin(19), sda=Pin(18), freq=50000)
    i2c.devices[0x77].fault.inject_fault("readfrom_mem", OSError, 5, "read fault")
    i2c.writeto(0x77, bytes([0x04]), False)
    try:
        i2c.readfrom_into(0x77, bytearray(6))
        raise AssertionError("expected OSError")
    except OSError:
        pass


def test_i2c_nack_after_returns_the_short_count_and_records_the_stop() -> None:
    _wire()
    i2c = I2C(1, scl=Pin(19), sda=Pin(18), freq=50000)
    osr = i2c.devices[0x77].handle_readfrom_mem(0x1C, 1)  # its reset value, whatever the chip models
    i2c.nack_after[0x77] = 1
    assert i2c.writeto(0x77, bytes([0x1C, 0x07]), True) == 1  # the data byte NACKed
    assert i2c.devices[0x77].handle_readfrom_mem(0x1C, 1) == osr  # the chip took nothing
    i2c.nack_after[0x77] = 0
    assert i2c.writeto(0x77, bytes([0x04]), False) == 0  # the register byte NACKed, no stop
    i2c.writeto(0x77, b"", True)  # the STOP the driver sends after a short no-stop write
    assert list(i2c.log)[-2:] == [("writeto", 0x77, bytes([0x04]), False), ("writeto", 0x77, b"", True)]
    assert i2c.writeto(0x77, bytes([0x1C, 0x07]), True) == 2  # the knob is spent


def test_spi_log_stays_bounded_across_many_transactions() -> None:
    _wire()
    spi = SPI(1, sck=Pin(10), mosi=Pin(11), miso=Pin(12))  # id 1 wires no device - write() still logs
    for _ in range(LOG_MAXLEN + 50):
        spi.write(bytes([0x00]))
    assert (len(spi.log), spi.log.dropped) == (LOG_MAXLEN, 51)  # the construction's init entry, then 250 writes
    assert spi.log[-1] == ("write", bytes([0x00]))


def test_bounded_log_reads_oldest_first_before_and_after_it_wraps() -> None:
    # Every read sees the entries oldest first once the oldest are overwritten in place, the head back at slot 0 included.
    for appended in (3, 4, 6, 8, 9):
        log: BoundedLog[int] = BoundedLog(4)
        for entry in range(appended):
            log.append(entry)
        expected = list(range(max(0, appended - 4), appended))
        assert list(log) == expected, (appended, list(log))
        assert [log[i] for i in range(len(log))] == expected
        assert [log[-i] for i in range(1, len(log) + 1)] == expected[::-1]
        assert log[1:3] == expected[1:3]
        assert log == expected
        assert (len(log), log.dropped) == (len(expected), appended - len(expected))
        assert expected[0] in log and expected[0] - 1 not in log
        for outside in (len(log), -len(log) - 1):
            try:
                log[outside]
            except IndexError:
                pass
            else:
                raise AssertionError(f"index {outside} of {appended} read {log[outside]!r}")


def test_bounded_log_clear_starts_over_at_slot_zero() -> None:
    log: BoundedLog[int] = BoundedLog(4)
    for entry in range(6):
        log.append(entry)
    log.clear()
    for entry in (10, 11, 12):
        log.append(entry)
    assert (list(log), log[0], log[-1]) == ([10, 11, 12], 10, 12)


@_inside_one_run
def test_wdt_feed_increments_count() -> None:
    wdt = WDT(timeout=8000)
    wdt.feed()
    wdt.feed()
    assert wdt.feed_count == 2


@_inside_one_run
def test_wdt_logs_count_what_they_drop_and_its_counters_saturate() -> None:
    wdt = WDT(timeout=8000)
    for _ in range(LOG_MAXLEN + 5):
        wdt._record_would_trigger()
        wdt.feed()
    assert (len(wdt.would_have_triggered_log), wdt.would_have_triggered_log.dropped) == (LOG_MAXLEN, 5)
    assert (len(wdt.feed_times), wdt.feed_times.dropped) == (LOG_MAXLEN, 5)
    wdt.feed_count = wdt.would_have_triggered_count = COUNTER_CAP
    wdt.feed()
    wdt._record_would_trigger()
    assert (wdt.feed_count, wdt.would_have_triggered_count) == (COUNTER_CAP, COUNTER_CAP)


def test_wdt_rejects_a_nonzero_id() -> None:
    # Confirmed directly against the pinned v1.29.0 ports/rp2/machine_wdt.c source: rp2 only ever
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


@_inside_one_run
def test_wdt_accepts_a_timeout_at_exactly_the_hard_cap() -> None:
    wdt = WDT(timeout=8388)
    assert wdt.timeout == 8388


@_inside_one_run
def test_wdt_would_have_triggered_count_and_log_start_at_zero() -> None:
    wdt = WDT(timeout=8000)
    assert wdt.would_have_triggered_count == 0
    assert len(wdt.would_have_triggered_log) == 0  # a deque, not a list - see machine.py's own comment


def test_wdt_notifies_once_after_a_feed_free_window() -> None:
    # Short timeout plus a generous run() bound - the same "does the mechanism work at all"
    # spirit as the short-period timer test below, not a precise-cadence assertion.
    #
    # Polling far finer than the WDT's own period (5ms vs. 100ms) matters here, not just as style: the
    # background monitor loops forever rather than stopping after one notification, so a granularity close
    # to its period races it, the observed count depending on scheduling.
    async def scenario() -> None:
        wdt = WDT(timeout=_WDT_SHORT_TIMEOUT_MS)
        for _ in range(_WDT_POLL_TRIES):
            if wdt.would_have_triggered_count >= 1:
                return
            await asyncio.sleep_ms(_WDT_POLL_MS)
        raise AssertionError("WDT never noticed a feed-free window")

    run(scenario(), _RUN_BOUND_S)


def test_wdt_feed_resets_the_countdown_and_prevents_a_notification() -> None:
    async def scenario() -> int:
        wdt = WDT(timeout=_WDT_FED_TIMEOUT_MS)
        for _ in range(_FEED_ROUNDS):  # ~120ms of continuous feeding, comfortably past one 100ms window
            await asyncio.sleep_ms(_FEED_STEP_MS)
            wdt.feed()
        return wdt.would_have_triggered_count

    count = run(scenario(), _RUN_BOUND_S)
    assert count == 0  # kept fed the whole time - never should have noticed a gap


def test_wdt_keeps_monitoring_after_a_would_have_triggered_notification() -> None:
    # "keeps monitoring so a long-unfed stretch can notify more than once" - not a one-shot.
    async def scenario() -> None:
        wdt = WDT(timeout=_WDT_SHORT_TIMEOUT_MS)
        for _ in range(_WDT_SECOND_NOTICE_POLL_TRIES):
            if wdt.would_have_triggered_count >= 2:
                return
            await asyncio.sleep_ms(_WDT_POLL_MS)
        raise AssertionError("WDT never reached a second would-have-triggered notification")

    run(scenario(), _DOUBLE_TRIGGER_BOUND_S)


def test_wdt_would_have_triggered_log_records_the_feed_count_at_each_notification() -> None:
    async def scenario() -> "BoundedLog[int]":
        wdt = WDT(timeout=_WDT_SHORT_TIMEOUT_MS)
        wdt.feed()
        wdt.feed()  # feed_count is 2 going into the unfed stretch below
        for _ in range(_WDT_POLL_TRIES):
            if wdt.would_have_triggered_count >= 1:
                return wdt.would_have_triggered_log
            await asyncio.sleep_ms(_WDT_POLL_MS)
        raise AssertionError("WDT never noticed a feed-free window")

    log = run(scenario(), _RUN_BOUND_S)
    assert log[0] == 2  # the first notification must reflect feed_count as of the unfed stretch


def test_wdt_on_would_trigger_callback_fires_with_the_wdt_instance() -> None:
    async def scenario() -> "list[WDT]":
        seen: list[WDT] = []
        _wdt = WDT(timeout=_WDT_SHORT_TIMEOUT_MS, on_would_trigger=seen.append)
        for _ in range(_WDT_POLL_TRIES):
            if seen:
                return seen
            await asyncio.sleep_ms(_WDT_POLL_MS)
        raise AssertionError("on_would_trigger callback never fired")

    seen = run(scenario(), _RUN_BOUND_S)
    assert seen[0].would_have_triggered_count >= 1


def test_reset_increments_the_module_counter_then_raises_simulated_reset() -> None:
    before = machine.reset_count
    try:
        reset()
        raise AssertionError("expected SimulatedResetError")
    except SimulatedResetError:
        pass
    assert machine.reset_count == before + 1


def test_bootloader_increments_the_module_counter_then_raises_simulated_bootloader_entry() -> None:
    before = machine.bootloader_count
    try:
        bootloader()
        raise AssertionError("expected SimulatedBootloaderEntryError")
    except SimulatedBootloaderEntryError:
        pass
    assert machine.bootloader_count == before + 1


def test_simulated_reset_and_bootloader_entry_are_both_simulated_reboot() -> None:
    assert issubclass(SimulatedResetError, SimulatedRebootError)
    assert issubclass(SimulatedBootloaderEntryError, SimulatedRebootError)
    try:
        reset()
        raise AssertionError("expected SimulatedRebootError")
    except SimulatedRebootError:
        pass  # caught via the base class, not the specific subclass


def test_mem_backup_has_rp2s_two_regions_of_four_and_three_words() -> None:
    machine.power_on()
    assert len(machine.mem_backup(0)) == 4
    assert len(machine.mem_backup(1)) == 3
    assert list(machine.mem_backup(0)) == [0, 0, 0, 0]
    assert list(machine.mem_backup(1)) == [0, 0, 0]


def test_mem_backup_returns_the_same_view_each_call_and_both_for_minus_one() -> None:
    machine.power_on()
    region0 = machine.mem_backup(0)
    region0[1] = 7
    assert machine.mem_backup(0) is region0
    assert machine.mem_backup(0)[1] == 7
    assert machine.mem_backup() is region0  # region 0 is the default (extmod/machine_mem.c at v1.29.0)
    both = machine.mem_backup(-1)
    assert isinstance(both, tuple)
    assert both[0] is region0
    assert both[1] is machine.mem_backup(1)
    machine.power_on()


def test_mem_backup_refuses_any_other_region() -> None:
    for region in (2, -2):
        try:
            machine.mem_backup(region)
            raise AssertionError("expected ValueError")
        except ValueError as e:
            assert str(e) == "invalid region"


def test_reset_cause_reads_power_on_until_a_reset_then_watchdog() -> None:
    machine.power_on()
    assert machine.reset_cause() == machine.PWRON_RESET
    try:
        reset()
        raise AssertionError("expected SimulatedResetError")
    except SimulatedResetError:
        pass
    assert machine.reset_cause() == machine.WDT_RESET
    machine.power_on()
    assert machine.reset_cause() == machine.PWRON_RESET


def test_bootloader_also_reads_back_as_a_watchdog_reset() -> None:
    machine.power_on()
    try:
        bootloader()
        raise AssertionError("expected SimulatedBootloaderEntryError")
    except SimulatedBootloaderEntryError:
        pass
    assert machine.reset_cause() == machine.WDT_RESET
    machine.power_on()


def test_power_on_clears_both_regions() -> None:
    machine.mem_backup(0)[0] = 1
    machine.mem_backup(1)[2] = 2
    machine.power_on()
    assert list(machine.mem_backup(0)) == [0, 0, 0, 0]
    assert list(machine.mem_backup(1)) == [0, 0, 0]


def test_mem32_answers_the_reset_registers_on_each_reset_path() -> None:
    reason, chip = 0x40058008, 0x40064008  # WATCHDOG REASON, VREG_AND_CHIP_RESET CHIP_RESET
    machine.power_on()
    assert (machine.mem32[reason], machine.mem32[chip]) == (0, 0x100)  # HAD_POR
    for action in (reset, bootloader):
        machine.power_on()
        try:
            action()
        except SimulatedRebootError:
            pass
        assert (machine.mem32[reason], machine.mem32[chip]) == (2, 0x100)  # FORCE; HAD_POR survives
    machine.power_on()

    async def starve() -> None:
        wdt = WDT(timeout=_WDT_SHORT_TIMEOUT_MS)
        for _ in range(_WDT_POLL_TRIES):
            if wdt.would_have_triggered_count:
                return
            await asyncio.sleep_ms(_WDT_POLL_MS)

    run(starve())
    assert machine.mem32[reason] == 1  # TIMER: the reset a starved watchdog makes
    machine.power_on()
    try:
        machine.mem32[0x40058000]
        raise AssertionError("an unmodelled address answered")
    except ValueError:
        pass


def test_rtc_datetime_round_trips() -> None:
    rtc = RTC()
    rtc.datetime((2026, 1, 1, 4, 12, 0, 0, 0))
    assert rtc.datetime()[0:3] == (2026, 1, 1)


class _Holder:
    # A stand-in module: any object whose global `time` is the built-in module, as each loaded src/ module's is.
    def __init__(self, clock: object) -> None:
        self.time = clock


def test_an_uninstalled_rtc_keeps_its_tuple_by_rp2s_rules() -> None:
    # ports/rp2/machine_rtc.c:50-97: no constructor argument, an 8-field set that returns None, a getter that
    # recomputes the weekday and reads field 7 as 0; rp2 boots at 2021-01-01 00:00:00 (ports/rp2/main.c:143).
    rtc = RTC()
    assert rtc.datetime() == (2021, 1, 1, 4, 0, 0, 0, 0)
    assert rtc.datetime((2026, 1, 1, 0, 12, 30, 15, 99)) is None  # a wrong weekday, a non-zero field 7
    assert RTC().datetime() == (2026, 1, 1, 3, 12, 30, 15, 0)
    for call, error in ((lambda: RTC(0), TypeError), (lambda: rtc.datetime((2026, 1, 1, 0, 12, 30, 15)), ValueError)):  # type: ignore[call-arg]
        try:
            call()
            raise AssertionError(f"expected {error.__name__}")
        except error:
            pass


def test_the_wall_clock_answers_rp2s_eight_field_time_tuples() -> None:
    clock = _wall_clock.WallClock()
    assert (clock.gmtime(0), clock.localtime(0)) == ((1970, 1, 1, 0, 0, 0, 3, 1),) * 2  # extmod/modtime.c:55-75
    assert len(clock.gmtime()) == 8 and isinstance(clock.time(), int)
    assert clock.ticks_ms is time.ticks_ms  # every other name is the built-in's


def test_step_moves_the_wall_clock_and_never_the_ticks() -> None:
    clock = _wall_clock.WallClock()
    clock.step(3600)
    assert 3599 <= clock.time() - int(time.time()) <= 3601
    assert clock.gmtime(0) == time.gmtime(0)[:8]


def test_install_rebinds_only_modules_on_the_builtin_time_once() -> None:
    plain, other = _Holder(time), _Holder(object())
    clock = _wall_clock.install([plain, other])
    assert (plain.time, other.time is clock, _wall_clock.installed()) == (clock, False, clock)
    assert _wall_clock.install([plain]) is clock and plain.time is clock
    machine.reset_test_state()
    restored: object = plain.time
    assert restored is time and _wall_clock.installed() is None


def test_an_installed_clock_makes_an_rtc_set_move_the_wall_clock() -> None:
    module = _Holder(time)
    clock = _wall_clock.install([module])
    RTC().datetime((2030, 6, 15, 0, 12, 0, 0, 0))
    assert abs(clock.time() - 1907755200) <= 1  # 2030-06-15T12:00:00Z
    assert RTC().datetime()[:6] == (2030, 6, 15, 5, 12, 0)  # a Saturday, the set second
    clock.step(3600)
    assert RTC().datetime()[4] == 13


def test_timer_deinit_stops_further_callbacks() -> None:
    calls: list[int] = []
    timer = Timer()
    timer.init(period=_TIMER_PERIOD_MS, mode=Timer.PERIODIC, callback=lambda _t: calls.append(1))

    async def scenario() -> "tuple[int, int]":
        await asyncio.sleep_ms(_BEFORE_DEINIT_MS)
        timer.deinit()
        count_at_deinit = len(calls)
        await asyncio.sleep_ms(_AFTER_DEINIT_MS)
        return count_at_deinit, len(calls)

    count_at_deinit, count_after = run(scenario())
    assert count_at_deinit >= 1
    assert count_after == count_at_deinit  # nothing fired after deinit()


def test_timer_reinit_from_within_its_own_callback_does_not_raise() -> None:
    # A self-rearming chain reuses one preallocated Timer (Part F.1), re-init()ing it from its own firing callback:
    # valid on rp2, which only reprograms the alarm. Timer.init()'s deinit() must not cancel the task running that
    # callback, which MicroPython's asyncio rejects with RuntimeError("can't cancel self").
    steps: list[int] = []
    timer = Timer()

    def _chain(_t: "Timer", counter: int = 0) -> None:
        steps.append(counter)
        if counter < 2:
            timer.init(period=_CHAIN_PERIOD_MS, mode=Timer.ONE_SHOT, callback=lambda t: _chain(t, counter + 1))

    async def scenario() -> None:
        timer.init(period=_CHAIN_PERIOD_MS, mode=Timer.ONE_SHOT, callback=_chain)
        for _ in range(_CHAIN_POLL_TRIES):  # generous relative to the 10ms period, matches the sibling test below
            if len(steps) >= 3:
                return
            await asyncio.sleep_ms(_CHAIN_POLL_MS)
        raise AssertionError("chained timer never completed all steps")

    run(scenario(), _RUN_BOUND_S)  # must not raise "can't cancel self"
    assert steps == [0, 1, 2]


def test_timer_deinit_outside_a_running_event_loop_does_not_raise() -> None:
    # Sibling regression test: the self-reinit fix above needs asyncio.current_task() to tell whether
    # deinit() is running inside the timer's own callback, but current_task() itself raises RuntimeError("no
    # running event loop") with no loop running at all, which a plain synchronous caller hits immediately.
    #
    # deinit() must treat that the same as "definitely not my own callback", not let the RuntimeError
    # propagate.
    timer = Timer()
    timer.init(period=1000, mode=Timer.ONE_SHOT, callback=lambda _t: None)
    timer.deinit()  # must not raise, called with no event loop running

    async def one_round() -> None:
        await asyncio.sleep(0)

    run(one_round())  # one loop round retires the task deinit() cancelled, which no loop had yet run


def test_timer_fires_for_real_on_a_short_period() -> None:
    # The one live-timing test in this whole package (see module docstring): a very short period
    # with a generous asyncio.wait_for bound, checking the asyncio-task-scheduled mechanism itself
    # actually fires at least once - not a precise-cadence assertion.
    fired: list[int] = []
    timer = Timer()

    async def scenario() -> None:
        timer.init(period=_TIMER_PERIOD_MS, mode=Timer.ONE_SHOT, callback=lambda _t: fired.append(1))
        for _ in range(_FIRE_POLL_TRIES):  # up to ~2s total, generous relative to the 20ms period
            if fired:
                return
            await asyncio.sleep_ms(_FIRE_POLL_MS)
        raise AssertionError("Timer callback never fired")

    run(scenario(), _RUN_BOUND_S)
    assert fired == [1]


# ---------------------------------------------------------------------------
# The shared twin helpers (_twin_common): the counter cap, the bounded log's drop count, the buffer fill.
# ---------------------------------------------------------------------------


def test_saturating_add_stops_at_the_shared_counter_cap() -> None:
    assert COUNTER_CAP == 0x3FFFFFFF
    assert (saturating_add(5), saturating_add(5, 3)) == (6, 8)
    assert (saturating_add(COUNTER_CAP - 1), saturating_add(COUNTER_CAP), saturating_add(COUNTER_CAP - 2, 5)) == (COUNTER_CAP,) * 3


def test_bounded_log_counts_what_it_drops_and_saturates_at_the_cap() -> None:
    log: BoundedLog[int] = BoundedLog(2)
    for entry in range(5):
        log.append(entry)
    assert (list(log), log.dropped) == ([3, 4], 3)
    log.dropped = COUNTER_CAP
    log.append(5)
    assert (list(log), log.dropped) == ([4, 5], COUNTER_CAP)


def test_fill_buffer_keeps_a_bytearrays_length_and_writes_into_a_memoryview() -> None:
    short = bytearray(b"\xff\xff\xff\xff")
    fill_buffer(short, b"\x01\x02")
    assert short == bytearray(b"\x01\x02\x00\x00")
    view = memoryview(bytearray(3))
    fill_buffer(view, b"\x01\x02\x03\x04")
    assert bytes(view) == b"\x01\x02\x03"
    idle = bytearray(2)
    fill_buffer(idle, b"", 0xFF)
    assert idle == bytearray(b"\xff\xff")


def test_state_paths_carries_the_mem_backup_path() -> None:
    paths = StatePaths(fram="f.json", scd30=None, mem_backup="m.json")
    assert (paths.fram, paths.scd30, paths.mem_backup) == ("f.json", None, "m.json")


# ---------------------------------------------------------------------------
# The peripheral registries, the configure hooks' construction rule and the per-test state reset.
# ---------------------------------------------------------------------------


def test_peripheral_answers_the_registered_bus_or_none() -> None:
    _wire()
    i2c = I2C(1, scl=Pin(19), sda=Pin(18))
    spi = SPI(0, sck=Pin(2), mosi=Pin(3), miso=Pin(4))
    uart = UART(0, tx=Pin(0), rx=Pin(1))
    assert (machine.peripheral("i2c1"), machine.peripheral("spi0"), machine.peripheral("uart0")) == (i2c, spi, uart)
    assert (machine.peripheral("i2c0"), machine.peripheral("spi1"), machine.peripheral("uart1")) == (None, None, None)
    try:
        machine.peripheral("i2c")
        raise AssertionError("a malformed name answered")
    except ValueError:
        pass


def test_reset_peripherals_forgets_every_bus() -> None:
    _wire()
    i2c = I2C(1, scl=Pin(19), sda=Pin(18))
    SPI(0, sck=Pin(2), mosi=Pin(3), miso=Pin(4))
    UART(0, tx=Pin(0), rx=Pin(1))
    machine.reset_peripherals()
    assert [machine.peripheral(name) for name in ("i2c1", "spi0", "uart0")] == [None, None, None]
    assert I2C(1, scl=Pin(19), sda=Pin(18)) is not i2c


def test_every_configure_hook_refuses_once_a_bus_exists() -> None:
    plan = wiring_plan(_board(_BOARD))
    hooks: tuple[tuple[str, Callable[[], object]], ...] = (
        ("configure_wiring", lambda: machine.configure_wiring(plan)),
        ("configure_random_source", lambda: machine.configure_random_source(None)),
        ("configure_scd30_state_path", lambda: machine.configure_scd30_state_path(None)),
        ("configure_fram_state_path", lambda: machine.configure_fram_state_path(None)),
        ("configure_mem_backup_state_path", lambda: machine.configure_mem_backup_state_path(None)),
    )
    for build in (lambda: I2C(1, scl=Pin(19), sda=Pin(18)), lambda: SPI(1, sck=Pin(10), mosi=Pin(11), miso=Pin(12)), lambda: UART(1, tx=Pin(8), rx=Pin(9))):
        machine.configure_wiring(plan)
        build()
        for hook, call in hooks:
            try:
                call()
                raise AssertionError(f"{hook}() after a bus existed was accepted")
            except RuntimeError as e:
                assert str(e).startswith(f"machine.{hook}() after a bus was constructed has no effect"), str(e)
        machine.reset_peripherals()


def test_configure_wiring_never_replaces_the_board_it_wired() -> None:
    _wire()
    first = I2C(1, scl=Pin(19), sda=Pin(18))
    try:
        _wire(_ISL29125_BOARD)  # a board whose i2c1 carries no 0x77, so a replaced board would show
    except RuntimeError:
        pass
    assert I2C(1, scl=Pin(19), sda=Pin(18)) is first and 0x77 in first.devices


def test_a_bus_needs_an_explicit_wiring_plan() -> None:
    try:
        I2C(1, scl=Pin(19), sda=Pin(18))
        raise AssertionError("a bus wired a board nobody configured")
    except RuntimeError as e:
        assert "no wiring plan configured" in str(e)
    assert not hasattr(machine, "configure_i2c_wiring")


@_inside_one_run
def test_reset_test_state_restores_every_machine_knob() -> None:
    machine.configure_random_source(FixedRandom())
    machine.configure_fram_state_path(_scratch.path("knob_fram.json"))
    machine.configure_scd30_state_path(_scratch.path("knob_scd30.json"))
    machine.configure_mem_backup_state_path(_scratch.path("knob_mem_backup.json"))
    _wire()
    I2C(0, scl=Pin(13), sda=Pin(12))
    SPI(0, sck=Pin(2), mosi=Pin(3), miso=Pin(4))
    UART(0, tx=Pin(0), rx=Pin(1))
    machine.set_alarm_pool_free(0)
    UART.would_have_blocked_bytes = 5
    Timer.drop_next_soft_callbacks = 2
    machine.reset_count = machine.bootloader_count = 3
    machine.mem_backup(0)[0] = 7
    RTC().datetime((2026, 1, 1, 4, 12, 0, 0, 0))
    _flash_stall.use_max = True
    _flash_stall.windows.append((0, 1))
    machine.reset_test_state()
    assert (_flash_stall.use_max, len(_flash_stall.windows)) == (False, 0)
    assert (machine._wiring_plan, machine._random_source, machine._fram_state_path, machine._scd30_state_path, machine._mem_backup_state_path) == (None,) * 5
    assert (machine._current_fram_chip, machine._current_scd30_chip, machine._ALARMS_FREE) == (None, None, 16)
    assert [machine.peripheral(name) for name in ("i2c0", "spi0", "uart0")] == [None, None, None]
    assert (UART.would_have_blocked_bytes, Timer.drop_next_soft_callbacks, machine.reset_count, machine.bootloader_count) == (0, 0, 0, 0)
    assert (list(machine.mem_backup(0)), machine.reset_cause(), RTC().datetime()) == ([0] * 4, machine.PWRON_RESET, (2021, 1, 1, 4, 0, 0, 0, 0))
    assert Pin._registry == {}


# ---------------------------------------------------------------------------
# mem_backup() across a simulated reset: the reset handler's flush, the next launch's configure.
# ---------------------------------------------------------------------------


def test_the_twin_meets_the_shared_mem_backup_contract() -> None:
    for check in _mem_backup_contract.ALL_CHECKS:
        check(machine)


def test_a_flushed_mem_backup_reaches_the_next_launch_once() -> None:
    path = _scratch.path("mem_backup_round_trip.json")
    machine.configure_mem_backup_state_path(path)
    assert machine.reset_cause() == machine.PWRON_RESET  # no file yet: a power-on
    machine.mem_backup(0)[2] = 0xDEADBEEF
    machine.mem_backup(1)[0] = 5
    try:
        reset()
    except SimulatedResetError:
        machine.flush_mem_backup()
    machine.reset_test_state()  # the next launch is a fresh process: power-on state until the file is read
    machine.configure_mem_backup_state_path(path)
    assert (list(machine.mem_backup(0)), list(machine.mem_backup(1))) == ([0, 0, 0xDEADBEEF, 0], [5, 0, 0])
    assert (machine.reset_cause(), machine.mem32[0x40058008], machine.mem32[0x40064008]) == (machine.WDT_RESET, 2, 0x100)
    try:
        os.stat(path)
        raise AssertionError("the state file outlived the launch that read it")
    except OSError:
        pass
    machine.reset_test_state()
    machine.configure_mem_backup_state_path(path)
    assert (machine.reset_cause(), list(machine.mem_backup(0))) == (machine.PWRON_RESET, [0] * 4)


def test_a_bad_mem_backup_state_file_boots_as_a_power_on() -> None:
    path = _scratch.path("mem_backup_bad.json")
    good = {"cause": 3, "watchdog_reason": 2, "chip_reset": 256, "regions": [[1, 2, 3, 4], [5, 6, 7]]}
    for text in ("{", json.dumps(dict(good, regions=[[1, 2, 3], [5, 6, 7]])), json.dumps(dict(good, cause="3")), json.dumps(dict(good, regions=[[1, 2, 3, 4], [5, 6, -7]])), json.dumps([good])):
        with open(path, "w") as f:
            f.write(text)
        machine.reset_test_state()
        machine.configure_mem_backup_state_path(path)
        assert (machine.reset_cause(), list(machine.mem_backup(0)), list(machine.mem_backup(1))) == (machine.PWRON_RESET, [0] * 4, [0] * 3), text


def test_an_unreadable_mem_backup_state_path_raises_rather_than_booting_as_a_power_on() -> None:
    # Only a missing file means no reset preceded this launch; a path that cannot be read is the runner's own fault.
    path = _scratch.path("mem_backup_dir")
    os.mkdir(path)
    try:
        machine.configure_mem_backup_state_path(path)
        raise AssertionError("an unreadable state path read as a power-on")
    except OSError as e:
        assert e.errno == errno.EISDIR, e
    finally:
        os.rmdir(path)


# ---------------------------------------------------------------------------
# The reset exceptions, the power-loss sibling and their counters.
# ---------------------------------------------------------------------------


def test_a_reset_and_a_power_loss_are_no_exceptions_a_product_can_swallow() -> None:
    assert issubclass(SimulatedRebootError, BaseException) and not issubclass(SimulatedRebootError, Exception)
    assert issubclass(machine.SimulatedPowerLoss, BaseException) and not issubclass(machine.SimulatedPowerLoss, Exception)
    assert not issubclass(machine.SimulatedPowerLoss, SimulatedRebootError)


def test_a_timer_calling_reset_ends_the_loop_past_an_except_exception_sibling() -> None:
    survived: list[int] = []

    async def swallowing() -> None:
        while True:
            try:
                await asyncio.sleep_ms(_SHORT_PERIOD_MS)
                survived.append(1)
            except Exception:  # a product loop that keeps going on any Exception
                pass

    async def scenario() -> None:
        sibling = asyncio.create_task(swallowing())
        Timer(mode=Timer.ONE_SHOT, period=_SHORT_PERIOD_MS, callback=lambda _t: reset())
        await asyncio.sleep_ms(_RUN_BOUND_S * 1000)
        sibling.cancel()

    try:
        run(scenario(), _RUN_BOUND_S + 1)
        raise AssertionError("the loop outlived machine.reset()")
    except SimulatedResetError:
        pass


def test_the_reset_counters_saturate_at_the_counter_cap() -> None:
    machine.reset_count = machine.bootloader_count = COUNTER_CAP
    for action in (reset, bootloader):
        try:
            action()
        except SimulatedRebootError:
            pass
    assert (machine.reset_count, machine.bootloader_count) == (COUNTER_CAP, COUNTER_CAP)


# ---------------------------------------------------------------------------
# Timer: rp2's signature, the 16-alarm pool, one schedule per Timer, soft and hard callback failures.
# ---------------------------------------------------------------------------


def test_timer_refuses_any_id_but_the_soft_timer() -> None:
    try:
        Timer(0)
        raise AssertionError("Timer(0) constructed")
    except ValueError as e:
        assert str(e) == "Timer doesn't exist"


def test_timer_period_maths_follows_rp2() -> None:
    async def scenario() -> "list[int]":
        timers = [Timer(freq=10), Timer(period=5, tick_hz=1_000_000), Timer(period=0)]
        periods = [timer._period_us for timer in timers]
        for timer in timers:
            timer.deinit()
        return periods

    assert run(scenario()) == [100_000, 5, 1]


def test_the_seventeenth_alarm_raises_enomem_until_one_is_freed() -> None:
    async def scenario() -> None:
        timers = [Timer(period=1000, callback=lambda _t: None) for _ in range(16)]
        bare = Timer()  # no settings: no alarm taken
        try:
            bare.init(period=1000, callback=lambda _t: None)
            raise AssertionError("a 17th alarm was armed")
        except OSError as e:
            assert e.errno == errno.ENOMEM
        timers[0].deinit()
        bare.init(period=1000, callback=lambda _t: None)
        sim = machine._simulation_timer()
        sim.init(period=1000, callback=lambda _t: None)  # a chip's simulation clock never takes an alarm

    run(scenario())


def test_a_fired_one_shot_returns_its_alarm() -> None:
    fired: list[int] = []

    async def scenario() -> None:
        machine.set_alarm_pool_free(1)
        Timer(mode=Timer.ONE_SHOT, period=_SHORT_PERIOD_MS, callback=lambda _t: fired.append(1))
        for _ in range(_CHAIN_POLL_TRIES):
            if fired:
                break
            await asyncio.sleep_ms(_SHORT_PERIOD_MS)
        Timer(mode=Timer.ONE_SHOT, period=1000, callback=lambda _t: None)

    run(scenario(), _RUN_BOUND_S)
    assert fired == [1]


def test_a_timer_rearming_from_its_own_callback_runs_one_schedule() -> None:
    # The first call re-arms with a callback that only counts: a second loop left running would count twice a period.
    calls: list[str] = []
    timer = Timer()

    def rearm(t: Timer) -> None:
        calls.append("first")
        t.init(period=_SHORT_PERIOD_MS, callback=lambda _t: calls.append("next"))

    async def scenario() -> None:
        timer.init(period=_SHORT_PERIOD_MS, callback=rearm)
        await asyncio.sleep_ms(_REARM_WINDOW_MS)

    run(scenario(), _RUN_BOUND_S)
    assert calls[:1] == ["first"] and len(calls) <= _REARM_WINDOW_MS // _SHORT_PERIOD_MS, calls


def test_a_soft_callback_failure_is_printed_and_the_schedule_goes_on() -> None:
    calls: list[int] = []

    def flaky(_t: Timer) -> None:
        calls.append(1)
        if len(calls) == 1:
            raise ValueError("planted callback failure")

    async def scenario() -> None:
        Timer(period=_SHORT_PERIOD_MS, callback=flaky)
        for _ in range(_CHAIN_POLL_TRIES):
            if len(calls) >= 2:
                return
            await asyncio.sleep_ms(_SHORT_PERIOD_MS)

    reported = _reports_during(lambda: run(scenario(), _RUN_BOUND_S))
    assert len(calls) >= 2
    assert reported == [("planted callback failure", False)]


def test_a_periodic_timer_fires_again_after_its_soft_callbacks_are_dropped() -> None:
    # rp2 loses a soft callback while its depth-8 scheduler queue is full and re-arms a PERIODIC alarm anyway
    # (shared/runtime/mpirq.c:105, ports/rp2/machine_timer.c:50-60, v1.29.0): the next period's call heals the drop.
    drops_left_at_call: list[int] = []
    assert Timer.drop_next_soft_callbacks == 0, "the knob is off by default"

    async def scenario() -> None:
        Timer.drop_next_soft_callbacks = 2
        timer = Timer(period=_SHORT_PERIOD_MS, callback=lambda _t: drops_left_at_call.append(Timer.drop_next_soft_callbacks))
        for _ in range(_CHAIN_POLL_TRIES):
            if drops_left_at_call:
                break
            await asyncio.sleep_ms(_SHORT_PERIOD_MS)
        timer.deinit()

    run(scenario(), _RUN_BOUND_S)
    assert drops_left_at_call[:1] == [0], f"the first delivered call came with {drops_left_at_call[:1]} drops still pending"


def test_a_dropped_one_shot_never_fires_and_frees_its_alarm_while_a_hard_callback_is_never_dropped() -> None:
    calls: list[str] = []

    async def scenario() -> None:
        machine.set_alarm_pool_free(1)
        Timer.drop_next_soft_callbacks = 1
        Timer(period=_SHORT_PERIOD_MS, mode=Timer.ONE_SHOT, callback=lambda _t: calls.append("soft"))
        for _ in range(_CHAIN_POLL_TRIES):
            if Timer.drop_next_soft_callbacks == 0:
                break
            await asyncio.sleep_ms(_SHORT_PERIOD_MS)
        await asyncio.sleep_ms(_SHORT_PERIOD_MS * 3)  # past where a late call would land
        Timer.drop_next_soft_callbacks = 1
        Timer(period=_SHORT_PERIOD_MS, mode=Timer.ONE_SHOT, callback=lambda _t: calls.append("hard"), hard=True)  # the dropped one's alarm, free again
        for _ in range(_CHAIN_POLL_TRIES):
            if calls:
                return
            await asyncio.sleep_ms(_SHORT_PERIOD_MS)

    run(scenario(), _RUN_BOUND_S)
    assert (calls, Timer.drop_next_soft_callbacks) == (["hard"], 1)


def test_a_hard_callback_failure_stops_the_schedule_and_frees_its_alarm() -> None:
    calls: list[int] = []

    def failing(_t: Timer) -> None:
        calls.append(1)
        raise ValueError("planted hard callback failure")

    async def scenario() -> None:
        machine.set_alarm_pool_free(1)
        Timer(period=_SHORT_PERIOD_MS, callback=failing, hard=True)
        await asyncio.sleep_ms(_SHORT_PERIOD_MS * 5 // 2)  # past where a second call would land
        Timer(period=1000, callback=lambda _t: None)  # the failed schedule's alarm is free again

    reported = _reports_during(lambda: run(scenario(), _RUN_BOUND_S))
    assert calls == [1]
    assert reported == [("planted hard callback failure", True)]


# ---------------------------------------------------------------------------
# SPI power loss and wire time; I2C unplug and plug.
# ---------------------------------------------------------------------------


def test_spi_lose_power_after_k_fails_the_next_transaction_with_a_power_loss() -> None:
    _wire()
    spi = SPI(0, sck=Pin(2), mosi=Pin(3), miso=Pin(4))
    spi.lose_power_after(2)
    spi.write(bytes([0x9F]))
    spi.write_readinto(bytes(4), bytearray(4))  # one full-duplex transfer counts once
    transfers: tuple[Callable[[], object], ...] = (lambda: spi.readinto(bytearray(4)), lambda: spi.write(b"\x06"))
    for transfer in transfers:
        try:
            transfer()
            raise AssertionError("a transaction ran after the power loss")
        except machine.SimulatedPowerLoss:
            pass


def test_spi_wire_time_blocks_for_each_byte_moved() -> None:
    _wire()
    spi = SPI(1, sck=Pin(10), mosi=Pin(11), miso=Pin(12))
    spi.wire_time_us_per_byte = _WIRE_US_PER_BYTE
    start = time.ticks_us()
    spi.write(bytes(20))
    assert time.ticks_diff(time.ticks_us(), start) >= 20 * _WIRE_US_PER_BYTE


def test_an_unplugged_chip_answers_nothing_until_plugged_back_powered_up() -> None:
    _wire()
    i2c = I2C(1, scl=Pin(19), sda=Pin(18))
    chip = i2c.devices[0x77]
    cycles: list[int] = []
    chip.power_cycle = lambda: cycles.append(1)
    i2c.unplug(0x77)
    assert 0x77 not in i2c.scan()
    try:
        i2c.readfrom_mem(0x77, 0x00, 1)
        raise AssertionError("an unplugged chip answered")
    except OSError as e:
        assert e.errno == errno.EIO
    i2c.plug(0x77)
    assert (i2c.devices[0x77], cycles) == (chip, [1])
    try:
        i2c.plug(0x77)  # already on the bus
        raise AssertionError("plug() accepted a chip that was never unplugged")
    except ValueError:
        pass
    i2c.unplug(0x77)
    try:
        i2c.unplug(0x77)
        raise AssertionError("unplug() accepted a chip already off the bus")
    except ValueError:
        pass


def test_the_fram_table_names_both_chips_and_refuses_an_unknown_size() -> None:
    plan = wiring_plan(_board(_BOARD))
    plan["spi"]["spi0"]["max_size"] = 0x8000
    machine.configure_wiring(plan)
    try:
        SPI(0, sck=Pin(2), mosi=Pin(3), miso=Pin(4))
        raise AssertionError("an FRAM of unknown size was wired")
    except ValueError as e:
        assert "no FRAM RDID for size 0x8000" in str(e)
    expected = {0x2000: bytes([0x04, 0x7F, 0x03, 0x02]), 0x40000: bytes([0x04, 0x7F, 0x48, 0x03])}  # the two RDIDs the driver knows
    assert expected == machine._FRAM_RDID_BY_MAX_SIZE


class _StallClock:
    # _flash_stall's own clock for one stall: each ticks_us() read moves the shared 2**30 clock 1 ms on, so its wait ends.
    def __init__(self, clock: Ticks30Time) -> None:
        self.clock = clock

    def __getattr__(self, name: str) -> object:
        return getattr(self.clock, name)

    def ticks_us(self) -> int:
        value = self.clock.ticks_us()
        self.clock.advance(1)
        return value


def test_a_link_keeps_its_wire_time_past_half_the_2_30_tick_period() -> None:
    # ticks_diff() misreads past 2**29 us (about 537 s) on rp2's period: a byte still takes its wire time, with traffic
    # every 100 s, then after idle gaps past half and past the whole period.
    def drive(clock: Ticks30Time, a: UART, b: UART) -> None:
        for at_ms in (0, 100_000, 200_000, 300_000, 400_000, 500_000, 600_000, 700_000, 1_400_000, 3_000_000):
            clock.now = at_ms
            a.write(b"\x5a")
            assert b.any() == 0, f"a byte arrived before its wire time {at_ms} ms into the link's life"
            clock.advance(1)
            assert b.read() == b"\x5a", f"a byte sent {at_ms} ms into the link's life never arrived"

    _on_the_2_30_clock(drive)


def test_a_link_finds_a_flash_stall_past_half_the_2_30_tick_period() -> None:
    # 600 s in, a burst due inside a stall meets no RX interrupt: the 32-byte FIFO keeps 32 and sets OE.
    def drive(clock: Ticks30Time, a: UART, b: UART) -> None:
        clock.now = 600_000
        a.write(bytes(40))  # 3.5 ms of wire time at 115200 baud
        _stall_on(clock)  # from the burst's start
        b.any()
        got = (len(b.read() or b""), b.rx_fifo_dropped, b.rsr & _RSR_OE)
        assert got == (32, 8, _RSR_OE), f"(kept, dropped, OE) {got}: the burst missed the stall's window"

    _on_the_2_30_clock(drive)


def test_a_link_misses_a_flash_stall_one_whole_2_30_tick_period_later() -> None:
    # A burst one whole 2**30 us period (about 1074 s) after a stall, at the stall's phase on the tick clock, meets a
    # running RX interrupt: all 40 bytes kept, none dropped, no OE.
    def drive(clock: Ticks30Time, a: UART, b: UART) -> None:
        clock.now = 600_000
        _stall_on(clock)
        clock.now = 1_673_742  # 600 s plus 2**30 us, to the ms: 176 us past the stall's start on the tick clock
        a.write(bytes(40))
        clock.advance(5)
        b.any()
        got = (len(b.read() or b""), b.rx_fifo_dropped, b.rsr & _RSR_OE)
        assert got == (40, 0, 0), f"(kept, dropped, OE) {got}: a burst one period after the stall met its window"

    _on_the_2_30_clock(drive)


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
