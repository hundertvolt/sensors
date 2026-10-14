"""Fidelity tests for the tests/ hardware fakes other suites lean on: each case states what rp2 does (the machine
contract, Timer one-shots, network bounds and seeds, Pin/I2C/RTC/UART per-peripheral state); a fake that drifts from
silicon lets a test pass for code that fails on the board."""

import errno

import _machine_contract
import machine
import network
import rp2
from machine import I2C, RTC, SPI, UART, WDT, Pin, Timer
from neopixel import NeoPixel

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Protocol

    from _protocols import WLANLike

    class _FakeWLAN(WLANLike, Protocol):
        # The product's WLAN surface plus the fake's test-only names these cases read: mypy resolves `network` to the
        # board stub, which has none of them (tests/network.py is outside the main pass, B.15).
        constructions: dict[int, int]
        connect_calls: list[tuple[str | None, str | None]]
        status_calls: list[str | None]
        deinit_called: bool
        _connected: bool
        _rssi: int


def _arm_one_construction_failure() -> None:
    I2C.raise_on_construct = OSError(errno.EIO, "planted")


def _assert_every_machine_knob_at_its_default() -> None:
    assert (Timer.raise_on_arm, Timer.raise_on_arm_exc, Timer.clock_ms, Timer.all_timers) == (False, OSError, 0, [])
    assert RTC.raise_exc is None
    assert RTC().datetime() == (2021, 1, 1, 4, 0, 0, 0, 0)  # rp2's boot value (ports/rp2/main.c:143), a Friday
    assert (UART.would_have_blocked_bytes, UART.real_poll_queries, len(UART._live)) == (0, 0, 0)
    assert (Pin(5).mode, Pin(5).pull, len(Pin.value_log(5))) == (None, None, 0)
    assert (I2C.raise_on_construct, I2C(1, scl=Pin(3), sda=Pin(2)).registers) == (None, {})
    assert (machine.reset_count, machine.bootloader_count, machine.reset_cause()) == (0, 0, machine.PWRON_RESET)
    assert (machine.watchdog_reason_value, machine.chip_reset_value) == (0, 0x100)
    assert (list(machine.mem_backup(0)), list(machine.mem_backup(1)), len(machine.mem32.log)) == ([0] * 4, [0] * 3, 0)
    assert machine._DMA_CHANNELS == {}


def _bus(bus_id: int = 0) -> I2C:
    I2C.reset_id(bus_id)  # a power-cycled controller: the test starts from an empty bus
    return I2C(bus_id, scl=Pin(1), sda=Pin(0))


def _errno(call: "Callable[[], object]") -> "int | None":
    exc = _raised(call)
    return exc.errno if isinstance(exc, OSError) else None


def _i2c_injector() -> "tuple[Callable[[int], None], Callable[[], object], Callable[[], int]]":
    bus = _bus()
    return (
        lambda times: bus.inject_fault("writeto", OSError, errno.EIO, "planted", times=times),
        lambda: bus.writeto(0x61, b"\x01"),
        lambda: bus.pending("writeto"),
    )


def _leave_every_machine_knob_set() -> None:
    Timer.raise_on_arm = True
    Timer.raise_on_arm_exc = RuntimeError
    Timer.clock_ms = 5
    Timer.all_timers.append(Timer())
    RTC().datetime((2030, 6, 1, 0, 0, 0, 0, 0))
    RTC.raise_exc = OSError(errno.EIO, "planted")
    UART.would_have_blocked_bytes = 3
    UART(0, tx=Pin(0), rx=Pin(1))
    Pin.set_external_level(5, 0)
    Pin(5, Pin.OUT, Pin.PULL_UP).value(1)
    I2C(1, scl=Pin(3), sda=Pin(2)).registers[(0x44, 0x01)] = bytearray([1])
    _arm_one_construction_failure()
    machine.reset_count = machine.bootloader_count = 2
    machine.reset_cause_value = machine.WDT_RESET
    machine.watchdog_reason_value = 2
    machine.chip_reset_value = 0
    machine.mem_backup(0)[0] = 7
    machine.mem_backup(1)[2] = 7
    machine.mem32.log.append(("read", 0, 0))
    rp2.DMA()  # a claimed channel a soft reset's finaliser would free


def _raised(call: "Callable[[], object]") -> "BaseException | None":
    # The exception a call raised, or None: lets a case assert both the class and rp2's own message.
    try:
        call()
    except BaseException as exc:  # SimulatedRebootError is a BaseException on purpose
        return exc
    return None


def _raises(exc_type: "type[BaseException]", call: "Callable[[], object]", message: "str | None" = None) -> bool:
    exc = _raised(call)
    return isinstance(exc, exc_type) and (message is None or str(exc) == message)


def _spi() -> SPI:
    return SPI(0, sck=Pin(2), mosi=Pin(3), miso=Pin(4))


def _spi_injector() -> "tuple[Callable[[int], None], Callable[[], object], Callable[[], int]]":
    spi = _spi()
    return (
        lambda times: spi.inject_fault("readinto", OSError, errno.EIO, "planted", times=times),
        lambda: spi.readinto(bytearray(32)),
        lambda: spi.pending("readinto"),
    )


def _wlan(if_id: int) -> "_FakeWLAN":
    return network.WLAN(if_id)  # type: ignore[return-value]  # the fake, which mypy sees as the board stub's WLAN


# ---- the shared machine contract ------------------------------------------------------------


def test_the_unit_machine_fake_meets_the_shared_contract() -> None:
    for check in _machine_contract.ALL_CHECKS:
        check(machine)
    for fault_check in _machine_contract.FAULT_CHECKS:
        fault_check(_i2c_injector)
        fault_check(_spi_injector)


def test_every_machine_contract_check_is_registered() -> None:
    # A check defined but never listed would never run on either tier.
    registered = [check.__name__ for check in _machine_contract.ALL_CHECKS] + [check.__name__ for check in _machine_contract.FAULT_CHECKS]
    assert len(registered) == len(set(registered)), "a check is listed twice"
    assert sorted(name for name in dir(_machine_contract) if name.startswith("check_")) == sorted(registered)


# ---- Timer ----------------------------------------------------------------------------------


def test_a_triggered_one_shot_is_spent() -> None:
    fired = []
    timer = Timer()
    timer.init(period=1000, mode=Timer.ONE_SHOT, callback=lambda _t: fired.append(1))
    timer.trigger()
    timer.trigger()  # the period cannot elapse twice for a one-shot
    assert fired == [1]
    assert timer.callback is None


def test_a_triggered_periodic_stays_armed() -> None:
    fired = []
    timer = Timer()
    timer.init(period=1000, mode=Timer.PERIODIC, callback=lambda _t: fired.append(1))
    for _ in range(3):
        timer.trigger()
    assert fired == [1, 1, 1]


def test_a_timer_keeps_only_its_newest_arms() -> None:
    # A one-shot re-armed every period over a long run must not grow the record without bound.
    timer = Timer()
    for k in range(5000):
        timer.init(period=k, mode=Timer.ONE_SHOT, callback=lambda _t: None)
    assert len(timer.arms) <= 4096
    assert timer.arms[-1] == (Timer.clock_ms, 4999, Timer.ONE_SHOT)


def test_a_dropped_one_shot_never_fires_but_a_dropped_periodic_fires_next_period() -> None:
    # Part F.1: a soft callback lost to a full scheduler queue. drop() is that lost period.
    one_shot, periodic = [], []
    a = Timer()
    a.init(period=1000, mode=Timer.ONE_SHOT, callback=lambda _t: one_shot.append(1))
    b = Timer()
    b.init(period=1000, mode=Timer.PERIODIC, callback=lambda _t: periodic.append(1))
    a.drop()
    b.drop()
    a.trigger()
    b.trigger()
    assert (one_shot, periodic) == ([], [1])


def test_a_deinit_timer_neither_fires_nor_minds_a_drop() -> None:
    fired = []
    timer = Timer()
    timer.init(period=1000, mode=Timer.PERIODIC, callback=lambda _t: fired.append(1))
    timer.deinit()
    timer.drop()
    timer.trigger()
    assert fired == []
    assert machine.Timer is Timer


def test_the_timer_takes_rp2s_keywords_and_only_the_soft_timer_id() -> None:
    # ports/rp2/machine_timer.c: init() takes mode/callback/period/tick_hz/freq/hard, all keywords; any id
    # but -1 raises; a construction with any keyword arms the timer at once.
    timer = Timer(freq=10, hard=False, tick_hz=1000, mode=Timer.ONE_SHOT, callback=lambda _t: None)
    assert len(timer.arms) == 1
    assert len(Timer().arms) == 0
    assert _raises(ValueError, lambda: Timer(0), "Timer doesn't exist")


# ---- network --------------------------------------------------------------------------------


def test_country_takes_exactly_two_bytes() -> None:
    assert network.country("AT") == "AT"
    assert _raises(ValueError, lambda: network.country("A"))
    assert _raises(ValueError, lambda: network.country("AUT"))
    assert _raises(ValueError, lambda: network.country("ÄT"))  # 2 characters and 3 bytes
    assert network.country() == "AT"  # a refused call changes nothing


def test_hostname_takes_at_most_thirty_two_bytes() -> None:
    assert network.hostname("ä" * 16) == "ä" * 16
    assert _raises(ValueError, lambda: network.hostname("ä" * 16 + "x"))
    assert network.hostname() == "ä" * 16


def test_connect_refuses_an_over_long_key_and_ssid() -> None:
    wlan = _wlan(network.STA_IF)
    assert _raises(OSError, lambda: wlan.connect("net", "ä" * 32 + "x"))  # 65 bytes
    assert _raises(AssertionError, lambda: wlan.connect("ä" * 16 + "x", "password"))  # 33 bytes
    wlan.connect("ä" * 16, "ä" * 32)  # both exactly at the bound
    assert wlan.connect_calls[-1] == ("ä" * 16, "ä" * 32)


def test_a_fresh_network_reads_the_pico_w_power_on_seeds() -> None:
    # extmod/modnetwork.c:71 and boards/RPI_PICO_W/mpconfigboard.h:8: what a product that never sets them reads.
    assert (network.country(), network.hostname()) == ("XX", "PicoW")


def test_one_wlan_object_per_interface_counted() -> None:
    # extmod/network_cyw43.c:96-103: WLAN(if) hands back the interface's static object; any id but STA_IF is the AP.
    sta = _wlan(network.STA_IF)
    assert _wlan(network.STA_IF) is sta
    assert network.WLAN() is network.WLAN(network.STA_IF)
    ap = _wlan(network.AP_IF)
    assert ap is not sta
    assert sta.constructions == {network.STA_IF: 4, network.AP_IF: 1}


def test_a_wrapped_wlan_constructor_still_counts_its_constructions() -> None:
    # Consumers swap network.WLAN for a wrapper that builds the real one; the count must not look the class up by
    # that module name, which then names the wrapper.
    real = network.WLAN

    def wrapper(if_id: int) -> object:
        return real(if_id)

    network.WLAN = wrapper  # type: ignore[misc, assignment]  # a module attribute swap, restored below
    try:
        network.WLAN(network.AP_IF)
    finally:
        network.WLAN = real  # type: ignore[misc]
    assert _wlan(network.AP_IF).constructions == {network.AP_IF: 2}


def test_wlan_deinit_drops_both_links() -> None:
    sta = _wlan(network.STA_IF)
    ap = _wlan(network.AP_IF)
    sta.active(True)
    sta._connected = True
    ap.active(True)
    sta.deinit()  # cyw43_deinit() powers the whole chip off (network_cyw43.c:133-137)
    assert (sta.active(), sta.isconnected(), ap.active()) == (False, False, False)
    assert sta.deinit_called


def test_wlan_status_raises_where_cyw43_raises() -> None:
    sta = _wlan(network.STA_IF)
    ap = _wlan(network.AP_IF)
    assert sta.status("rssi") == sta._rssi
    assert ap.status("stations") == []
    assert _raises(ValueError, lambda: ap.status("rssi"), "STA required")
    assert _raises(ValueError, lambda: sta.status("stations"), "AP required")
    assert _raises(ValueError, lambda: sta.status("ssid"), "unknown status param")
    assert _raises(TypeError, lambda: sta.status(None))  # type: ignore[call-overload]  # mp_obj_str_get_qstr() of None
    assert sta.status_calls == ["rssi", "stations", "ssid", None]
    ap.active(True)
    assert ap.status() == network.STAT_GOT_IP  # an active AP's netif is up with its address
    ap.active(False)
    assert ap.status() == network.STAT_IDLE


# ---- Pin ------------------------------------------------------------------------------------


def test_a_pin_init_with_no_pull_clears_an_earlier_pull() -> None:
    # ports/rp2/machine_pin.c:300-306: the pull is set unconditionally, an omitted or None pull meaning none.
    pin = Pin(5, Pin.IN, Pin.PULL_UP)
    Pin(5, Pin.IN)
    assert pin.pull == 0
    Pin(5, Pin.IN, Pin.PULL_DOWN)
    pin.init(Pin.IN, None)
    assert pin.pull == 0


def test_a_pin_named_by_id_alone_changes_nothing() -> None:
    # Guard: machine_pin.c:318-323 configures a GPIO only when an argument beyond the id is given.
    pin = Pin(6, Pin.OUT, Pin.PULL_DOWN, value=1)
    Pin(6)
    assert (pin.mode, pin.pull, pin.value()) == (Pin.OUT, Pin.PULL_DOWN, 1)


def test_an_explicit_none_argument_still_configures_the_pin() -> None:
    # machine_pin.c:317: any argument beyond the id runs the init helper, so a None one clears the pull as rp2 does.
    pin = Pin(10, Pin.IN, Pin.PULL_UP)
    Pin(10, None)
    assert pin.pull == 0
    Pin(10, Pin.IN, Pin.PULL_UP)
    Pin(10, pull=None)
    assert pin.pull == 0
    Pin(10, Pin.IN, Pin.PULL_UP)
    Pin(10, value=None)
    assert (pin.mode, pin.pull) == (Pin.IN, 0)


def test_pin_names_and_numbers_share_one_gpio() -> None:
    # Board names (boards/RPI_PICO_W/pins.csv) first, then CPU names (boards/make-pins.py); one state per GPIO.
    Pin(7, Pin.OUT, value=1)
    assert Pin("GP7").value() == 1
    Pin("GPIO7").value(0)
    assert Pin(7).value() == 0
    assert Pin("GPIO29").id == 29
    assert Pin("LED").id == Pin("WL_GPIO0").id == Pin("EXT_GPIO0").id


def test_pin_ids_outside_the_rp2_table_raise_invalid_pin() -> None:
    # machine_pin_find(), machine_pin.c:165-192: 0-29 (NUM_BANK0_GPIOS), a known name, or a Pin.
    assert _raises(ValueError, lambda: Pin(30), "invalid pin")
    assert _raises(ValueError, lambda: Pin(-1), "invalid pin")
    assert _raises(ValueError, lambda: Pin(1.5), "invalid pin")  # type: ignore[arg-type]  # a non-int, non-str id
    assert _raises(ValueError, lambda: Pin(None), "invalid pin")  # type: ignore[arg-type]  # likewise
    assert _raises(ValueError, lambda: Pin("GP23"), 'unknown named pin "GP23"')  # the board names skip GP23-25, GP29
    assert Pin(29).id == 29
    assert Pin(Pin(12)).id == 12


def test_an_external_pin_refuses_a_pull_an_alt_and_open_drain() -> None:
    # machine_pin.c:256-262 and machine_pin_cyw43.c: the WLAN chip's GPIOs take only IN and OUT, no pull, no alt.
    assert _raises(ValueError, lambda: Pin("LED", Pin.IN, Pin.PULL_UP), "pulls are not supported for external pins")
    assert _raises(ValueError, lambda: Pin("WL_GPIO1", Pin.OUT, alt=Pin.ALT_I2C), "alternate functions are not supported for external pins")
    assert _raises(ValueError, lambda: Pin("LED", Pin.OPEN_DRAIN), "only Pin.OUT and Pin.IN are supported for this pin")
    assert Pin("LED", Pin.OUT, value=1).value() == 1


def test_an_open_drain_release_reads_the_scripted_line() -> None:
    # Guard: a released open-drain pin reads the external level, a callable one as the value log grows.
    pin = Pin(8, Pin.OPEN_DRAIN, value=1)
    Pin.set_external_level(8, lambda _id, log: 1 if len(log) >= 2 else 0)
    assert pin.value() == 0
    pin.value(0)
    pin.value(1)
    assert pin.value() == 1
    assert list(Pin.value_log(8)) == [0, 1]


def test_alt_mode_records_the_alternate_function() -> None:
    # Guard: machine_pin.c:290-297 hands the pad to the peripheral the alt names.
    pin = Pin(9, Pin.ALT, Pin.PULL_UP, alt=Pin.ALT_I2C)
    assert (pin.mode, pin.pull, pin.alt) == (Pin.ALT, Pin.PULL_UP, Pin.ALT_I2C)


def test_a_pin_irq_registration_reads_back_per_gpio() -> None:
    # machine_pin.c:460-478: irq() defaults to both edges and a soft handler, and replaces the GPIO's registration.
    def handler(_pin: Pin) -> None:
        pass

    pin = Pin(6, Pin.IN)
    assert (pin.irq_handler, pin.irq_trigger, pin.irq_hard) == (None, Pin.IRQ_FALLING | Pin.IRQ_RISING, False)
    pin.irq(handler, Pin.IRQ_RISING, hard=True)
    assert (Pin(6).irq_handler, Pin(6).irq_trigger, Pin(6).irq_hard) == (handler, Pin.IRQ_RISING, True)


# ---- I2C ------------------------------------------------------------------------------------


def test_a_second_i2c_construction_returns_the_same_bus_with_its_state() -> None:
    # rp2's I2C(id) is a static object (machine_i2c.c:50-53, 87): a re-construction re-initialises the controller
    # and keeps the devices, the queued faults and the log.
    first = I2C(0, scl=Pin(1), sda=Pin(0))
    first.registers[(0x44, 0x01)] = bytearray([7])
    first.inject_fault("writeto", OSError, errno.EIO, "planted")
    second = I2C(0, scl=Pin(1), sda=Pin(0), timeout=1234)
    assert second is first
    assert second.registers[(0x44, 0x01)] == bytearray([7])
    assert (second.pending("writeto"), second.timeout) == (1, 1234)
    assert [entry for entry in second.log if entry[0] == "init"][-2:] == [("init", 400000, 50000), ("init", 400000, 1234)]


def test_reset_id_power_cycles_one_bus() -> None:
    # Guard: the next construction after reset_id() is an empty bus, as after a power cycle.
    first = _bus()
    first.registers[(0x44, 0x01)] = bytearray([7])
    second = _bus()
    assert second is not first
    assert second.registers == {}


def test_raise_on_construct_raises_once() -> None:
    # Guard: the knob a recovery test uses to fail one re-construction.
    _arm_one_construction_failure()
    assert _errno(lambda: I2C(0, scl=Pin(1), sda=Pin(0))) == errno.EIO
    assert I2C.raise_on_construct is None
    I2C(0, scl=Pin(1), sda=Pin(0))


def test_an_i2c_id_outside_the_two_controllers_raises() -> None:
    assert _raises(ValueError, lambda: I2C(2, scl=Pin(1), sda=Pin(0)), "I2C(2) doesn't exist")  # machine_i2c.c:82-84


def test_a_zero_length_probe_answers_as_rp2s_soft_transfer() -> None:
    # machine_i2c.c:127-145: a zero-length write is a soft-I2C transfer, ENODEV on a NAK, ETIMEDOUT on a held SCL.
    bus = _bus()
    bus.attached.add(0x61)
    bus.registers[(0x44, 0x00)] = bytearray([0x7D])
    assert (bus.writeto(0x61, b""), bus.writeto(0x44, b"")) == (0, 0)
    bus.nak_addresses.add(0x61)
    assert _errno(lambda: bus.writeto(0x61, b"")) == errno.ENODEV  # a NAKed device
    assert _errno(lambda: bus.writeto(0x10, b"")) == errno.ENODEV  # an address nothing answers on
    assert _errno(lambda: bus.writeto(0x61, b"\x00")) == errno.EIO  # a non-empty write keeps the hardware path's EIO
    bus.busy = True
    assert _errno(lambda: bus.writeto(0x44, b"")) == errno.ETIMEDOUT


def test_scan_never_raises_and_lists_what_answers_a_probe() -> None:
    # extmod/machine_i2c.c:341-356: scan() probes 0x08-0x77 and keeps each address whose probe returned 0.
    bus = _bus()
    bus.attached.update((0x61, 0x59, 0x05))  # 0x05 is reserved: never probed
    bus.registers[(0x44, 0x00)] = bytearray([0x7D])
    bus.nak_addresses.add(0x59)
    assert bus.scan() == [0x44, 0x61]
    bus.busy = True
    assert bus.scan() == []


def test_an_i2c_op_that_cannot_raise_is_refused() -> None:
    # An injected fault no call can reach would leave its test checking nothing.
    bus = _bus()
    assert _raises(ValueError, lambda: bus.inject_fault("scan", OSError, errno.EIO))
    assert _raises(ValueError, lambda: bus.inject_fault("readfrom_mem_into", OSError, errno.EIO))
    assert _raises(ValueError, lambda: bus.inject_fault("writeto", OSError, errno.EIO, times=0))
    assert bus.pending("writeto") == 0


def test_an_i2c_fault_fires_fresh_exceptions_in_order_and_counts_down() -> None:
    bus = _bus()
    bus.inject_fault("writeto", OSError, errno.EIO, "first", times=2)
    bus.inject_fault("writeto", OSError, errno.ETIMEDOUT, "second")
    assert bus.pending("writeto") == 3
    first = _raised(lambda: bus.writeto(0x61, b"\x01"))
    second = _raised(lambda: bus.writeto(0x61, b"\x01"))
    assert (_errno(lambda: bus.writeto(0x61, b"\x01")), _errno(lambda: bus.writeto(0x61, b"\x01"))) == (errno.ETIMEDOUT, None)
    assert isinstance(first, OSError)
    assert isinstance(second, OSError)
    assert (first.errno, second.errno, first is second) == (errno.EIO, errno.EIO, False)
    assert bus.pending("writeto") == 0


def test_an_i2c_fault_aimed_at_a_register_or_an_address_spares_the_rest() -> None:
    # match is the register a register-device access names (memaddr for *_mem); address= filters the device.
    bus = _bus()
    bus.inject_fault("readfrom_mem", OSError, errno.EIO, match=0x02)
    bus.inject_fault("writeto", OSError, errno.EIO, address=0x45)
    bus.readfrom_mem(0x44, 0x01, 1)
    bus.writeto(0x44, b"\x01\x02")
    assert (bus.pending("readfrom_mem"), bus.pending("writeto")) == (1, 1)
    assert _raises(OSError, lambda: bus.readfrom_mem(0x44, 0x02, 1))
    assert _raises(OSError, lambda: bus.writeto(0x45, b"\x01"))
    assert (bus.pending("readfrom_mem"), bus.pending("writeto")) == (0, 0)


def test_a_multi_byte_register_access_spans_consecutive_registers() -> None:
    # A burst reads and writes consecutive registers (ISL29125 FN8424 p.7-8, the address pointer auto-increments).
    bus = _bus()
    for register, value in ((0x01, 0x11), (0x02, 0x22), (0x03, 0x33)):
        bus.registers[(0x44, register)] = bytearray([value])
    assert bus.readfrom_mem(0x44, 0x01, 3) == b"\x11\x22\x33"
    bus.writeto(0x44, b"\x01", False)
    buf = bytearray(3)
    bus.readfrom_into(0x44, buf)
    assert buf == b"\x11\x22\x33"
    block = _bus()
    block.registers[(0x44, 0x01)] = bytearray(3)  # CONFIG1-3 seeded as one block
    block.writeto(0x44, b"\x02\xaa\xbb")  # a burst from CONFIG2
    assert block.readfrom_mem(0x44, 0x01, 3) == b"\x00\xaa\xbb"
    assert block.registers[(0x44, 0x01)] == bytearray(b"\x00\xaa\xbb")


# ---- SPI ------------------------------------------------------------------------------------


def test_spi_bit_order_numbers_are_rp2s() -> None:
    # pico-sdk hardware/spi.h:184-187 (SPI_LSB_FIRST 0, SPI_MSB_FIRST 1); rp2 implements MSB first only.
    assert (SPI.MSB, SPI.LSB) == (1, 0)
    spi = _spi()
    assert spi.firstbit == SPI.MSB
    assert _raises(NotImplementedError, lambda: spi.init(firstbit=SPI.LSB))
    assert _raises(NotImplementedError, lambda: SPI(0, sck=Pin(2), mosi=Pin(3), miso=Pin(4), firstbit=SPI.LSB))


def test_an_spi_read_fault_waits_for_a_dma_sized_transfer() -> None:
    # ports/rp2/machine_spi.c:267-318: only a transfer of 32+ bytes takes the DMA path whose overrun raises.
    spi = _spi()
    spi.inject_fault("readinto", OSError, errno.EIO, "overrun", times=2)
    spi.readinto(bytearray(4))
    assert spi.pending("readinto") == 2
    first = _raised(lambda: spi.readinto(bytearray(32)))
    second = _raised(lambda: spi.readinto(bytearray(32)))
    assert isinstance(first, OSError)
    assert first is not second
    assert spi.pending("readinto") == 0


def test_an_spi_fault_aimed_at_an_opcode_spares_the_other_commands() -> None:
    spi = _spi()
    spi.inject_fault("readinto", OSError, errno.EIO, match=0x03)
    spi.write(b"\x05")
    spi.readinto(bytearray(32))
    spi.write(b"\x03\x00\x00")
    assert _raises(OSError, lambda: spi.readinto(bytearray(32)))


def test_an_spi_write_fault_is_refused() -> None:
    # A write-only transfer ignores an RX overrun (machine_spi.c:312-315): nothing for a queued fault to raise.
    spi = _spi()
    assert _raises(ValueError, lambda: spi.inject_fault("write", OSError, errno.EIO))


# ---- UART -----------------------------------------------------------------------------------


def test_a_uart_buffer_below_thirty_two_bytes_is_clamped() -> None:
    # ports/rp2/machine_uart.c:372-373, 387-388: below MIN_BUFFER_SIZE is raised to it, above MAX refused.
    uart = UART(0, tx=Pin(0), rx=Pin(1), rxbuf=8, txbuf=1)
    assert (uart.rxbuf, uart.txbuf) == (32, 32)
    assert _raises(ValueError, lambda: UART(0, tx=Pin(0), rx=Pin(1), rxbuf=32767), "rxbuf too large")


# ---- RTC, WDT, reset ------------------------------------------------------------------------


def test_the_rtc_setter_takes_exactly_eight_fields() -> None:
    # ports/rp2/machine_rtc.c:84: mp_obj_get_array_fixed_n(args[1], 8, ...).
    rtc = RTC()
    rtc.datetime((2026, 9, 30, 2, 12, 0, 0, 0))
    assert _raises(ValueError, lambda: rtc.datetime((2026, 9, 30, 2, 12, 0, 0)), "tuple/list has wrong length")
    assert rtc.datetime() == (2026, 9, 30, 2, 12, 0, 0, 0)  # the refused set changed nothing


def test_the_rtc_getter_recomputes_the_date_and_weekday() -> None:
    # machine_rtc.c:67-92: the setter keeps seconds (weekday and subseconds ignored), the getter recomputes.
    rtc = RTC()
    rtc.datetime((2026, 9, 30, 0, 12, 0, 0, 99))
    assert rtc.datetime() == (2026, 9, 30, 2, 12, 0, 0, 0)  # a Wednesday, subseconds 0
    rtc.datetime((2026, 2, 29, 0, 0, 0, 0, 0))
    assert rtc.datetime() == (2026, 3, 1, 6, 0, 0, 0, 0)
    assert RTC().datetime() == rtc.datetime()  # one peripheral


def test_a_wdt_timeout_above_the_rp2040_cap_raises() -> None:
    # ports/rp2/machine_wdt.c:32-38, 55-57: 8388 ms is the RP2040's cap; only id 0 exists.
    assert WDT(timeout=8388).timeout == 8388
    assert _raises(ValueError, lambda: WDT(timeout=8389), "timeout exceeds 8388")
    assert _raises(ValueError, lambda: WDT(timeout=9000), "timeout exceeds 8388")
    assert _raises(ValueError, lambda: WDT(timeout=-1), "timeout exceeds 8388")  # rp2 takes it as a uint32_t
    assert _raises(ValueError, lambda: WDT(id=1), "WDT(1) doesn't exist")


def test_reset_and_bootloader_count_then_never_return() -> None:
    # A real reset never returns: the fake counts it, sets the cause rp2 then reports, and raises past the test.
    before = (machine.reset_count, machine.bootloader_count)
    exc = _raised(machine.reset)
    assert isinstance(exc, machine.SimulatedResetError)
    assert not isinstance(exc, Exception)  # no `except Exception` in the product can swallow it
    assert machine.reset_cause() == machine.WDT_RESET
    assert isinstance(_raised(machine.bootloader), machine.SimulatedBootloaderEntryError)
    assert issubclass(machine.SimulatedBootloaderEntryError, machine.SimulatedRebootError)
    assert (machine.reset_count, machine.bootloader_count) == (before[0] + 1, before[1] + 1)


# ---- NeoPixel -------------------------------------------------------------------------------


def test_a_neopixel_stores_grb_bytes_in_a_bytearray() -> None:
    # micropython-lib neopixel.py:9-46: a bytearray in G-R-B order, so an int store wraps and a float raises.
    strip = NeoPixel(Pin(16), 2)
    strip[0] = (1, 2, 3)
    strip[1] = (300, -1, 0)
    assert strip.buf == bytearray([2, 1, 3, 0xFF, 0x2C, 0])
    assert (strip[0], strip[1]) == ((1, 2, 3), (0x2C, 0xFF, 0))
    assert _raises(TypeError, lambda: strip.__setitem__(0, (1.5, 2, 3)))  # type: ignore[assignment]  # an unclamped float
    assert _raises(IndexError, lambda: strip.__setitem__(0, (1, 2)))
    assert Pin(16).mode == Pin.OUT


def test_a_neopixel_fill_len_and_timing_follow_the_library() -> None:
    strip = NeoPixel(Pin(16), 3, timing=0)
    strip.fill((4, 5, 6))
    strip.write()
    assert (len(strip), strip.ORDER, strip.timing) == (3, (1, 0, 2, 3), 0)
    assert strip.writes[-1] == [(4, 5, 6)] * 3


def test_a_neopixel_write_log_keeps_the_newest_frames_and_counts_the_rest() -> None:
    strip = NeoPixel(Pin(16), 1)
    for k in range(4097):
        strip[0] = (k & 0xFF, 0, 0)
        strip.write()
    assert (len(strip.writes), strip.writes.dropped) == (4096, 1)
    assert strip.writes[0] == [(1, 0, 0)]
    assert strip.writes[-1] == [(4096 & 0xFF, 0, 0)]


# ---- the per-test reset hook ----------------------------------------------------------------


def test_reset_test_state_restores_every_machine_knob() -> None:
    _leave_every_machine_knob_set()
    machine.reset_test_state()
    _assert_every_machine_knob_at_its_default()


def test_the_reset_hook_1_leaves_every_knob_set() -> None:
    # With the next test: the after-each hooks both fakes register at import restore what this one left set.
    _leave_every_machine_knob_set()
    network.country("AT")
    network.hostname("planted")
    _wlan(network.AP_IF).active(True)


def test_the_reset_hook_2_sees_every_default() -> None:
    _assert_every_machine_knob_at_its_default()
    assert (network.country(), network.hostname()) == ("XX", "PicoW")
    ap = _wlan(network.AP_IF)
    assert (ap.constructions, ap.active()) == ({network.AP_IF: 1}, False)


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
