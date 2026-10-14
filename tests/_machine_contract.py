"""Backend-agnostic checks both machine fakes are held to (tests/machine.py, digital_twin/machine.py): each takes the
module under test, the fault check a backend factory; the tiers may differ in fidelity, never in these semantics.
tests/test_fakes.py and tests/test_digital_twin_machine.py run every one (SPECIFICATION.md E.4)."""

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import ModuleType

    # make_injector() -> (inject(times), trigger(), pending()): one op's fault queue on either tier. inject queues
    # `times` OSError(EIO) faults, trigger makes one call of that op, pending counts what is still queued.
    InjectorFactory = Callable[[], tuple[Callable[[int], None], Callable[[], object], Callable[[], int]]]

_EIO = 5  # errno.EIO on every port this runs on (py/mperrno.h)
_WDT_TIMEOUT_MAX_MS = 8388  # ports/rp2/machine_wdt.c:32-38, the RP2040's cap


def _raised(call: "Callable[[], object]") -> "BaseException | None":
    try:
        call()
    except KeyboardInterrupt:
        raise  # the per-file timeout's interrupt ends the run, never a check's answer
    except BaseException as exc:  # a simulated reset is a BaseException on purpose
        return exc
    return None


def check_i2c_state_survives_reconstruction(m: "ModuleType") -> None:
    # rp2's I2C(id) is one static object (machine_i2c.c:50-53, 87): a re-construction re-initialises it in place.
    first = m.I2C(1, scl=m.Pin(3), sda=m.Pin(2))
    assert m.I2C(1, scl=m.Pin(3), sda=m.Pin(2), freq=100000) is first


def check_inject_fault_fifo(make_injector: "InjectorFactory") -> None:
    # One op's queue: `times` faults fire in turn, each a fresh exception, the count falls to zero, the next call runs.
    inject, trigger, pending = make_injector()
    inject(2)
    assert pending() == 2
    first = _raised(trigger)
    assert isinstance(first, OSError)
    assert first.errno == _EIO
    assert pending() == 1
    second = _raised(trigger)
    assert isinstance(second, OSError)
    assert second is not first, "each raise must be a fresh exception"
    assert pending() == 0
    assert _raised(trigger) is None


def check_irq_edge_values(m: "ModuleType") -> None:
    # GPIO_IRQ_EDGE_FALL and _RISE (ports/rp2/machine_pin.c:507-508).
    assert (m.Pin.IRQ_FALLING, m.Pin.IRQ_RISING) == (0x04, 0x08)


def check_pin_constants(m: "ModuleType") -> None:
    # ports/rp2/machine_pin.h:34-37 and machine_pin.c:505-506, 513.
    assert (m.Pin.IN, m.Pin.OUT, m.Pin.OPEN_DRAIN, m.Pin.ALT) == (0, 1, 2, 3)
    assert (m.Pin.PULL_UP, m.Pin.PULL_DOWN, m.Pin.ALT_I2C) == (1, 2, 3)


def check_pin_defaults(m: "ModuleType") -> None:
    # machine_pin.c:243-248, 317-323: an id alone configures nothing, and a None mode keeps the mode.
    pin = m.Pin(20, m.Pin.OUT, value=1)
    m.Pin(20)
    assert (pin.mode, pin.value()) == (m.Pin.OUT, 1)
    m.Pin(20, None, m.Pin.PULL_DOWN)
    assert pin.mode == m.Pin.OUT


def check_pin_pull_semantics(m: "ModuleType") -> None:
    # machine_pin.c:300-306: any configuring call sets the pull, an omitted or None pull meaning none.
    pin = m.Pin(21, m.Pin.IN, m.Pin.PULL_UP)
    m.Pin(21, m.Pin.IN)
    assert not pin.pull
    m.Pin(21, m.Pin.IN, m.Pin.PULL_UP)
    pin.init(m.Pin.IN, None)
    assert not pin.pull


def check_readfrom_mem_into_delegates(m: "ModuleType") -> None:
    # readfrom_mem_into() answers what readfrom_mem() does for the same register: one implementation behind both.
    bus = m.I2C(1, scl=m.Pin(3), sda=m.Pin(2))
    buf = bytearray(1)
    bus.readfrom_mem_into(0x77, 0x00, buf)
    assert bytes(buf) == bus.readfrom_mem(0x77, 0x00, 1)


def check_reset_never_returns(m: "ModuleType") -> None:
    # A real reset()/bootloader() never returns: each counts, sets rp2's watchdog cause, then raises past the caller,
    # and no `except Exception` in the product can swallow what it raises.
    assert issubclass(m.SimulatedResetError, m.SimulatedRebootError)
    assert issubclass(m.SimulatedBootloaderEntryError, m.SimulatedRebootError)
    assert not issubclass(m.SimulatedRebootError, Exception), "an `except Exception` would swallow the reset"
    for action, counter, error in ((m.reset, "reset_count", m.SimulatedResetError), (m.bootloader, "bootloader_count", m.SimulatedBootloaderEntryError)):
        before = getattr(m, counter)
        assert isinstance(_raised(action), error)
        assert getattr(m, counter) == before + 1
        assert m.reset_cause() == m.WDT_RESET
    m.power_on()


def check_scan_never_raises(m: "ModuleType") -> None:
    # extmod/machine_i2c.c:341-356: scan() tests each probe's result, so it answers a sorted list of 7-bit addresses.
    found = m.I2C(1, scl=m.Pin(3), sda=m.Pin(2)).scan()
    assert found == sorted(found)
    assert all(0x08 <= address < 0x78 for address in found)


def check_spi_bit_order(m: "ModuleType") -> None:
    # pico-sdk hardware/spi.h:184-187 (SPI_LSB_FIRST 0, SPI_MSB_FIRST 1); a construction defaults to MSB first.
    assert (m.SPI.MSB, m.SPI.LSB) == (1, 0)
    assert m.SPI(1, sck=m.Pin(10), mosi=m.Pin(11), miso=m.Pin(12)).firstbit == m.SPI.MSB


def check_wdt_feed_times(m: "ModuleType") -> None:
    # Each feed() is counted and its ticks_ms() kept, oldest first, so a test reads the gaps between feeds.
    wdt = m.WDT(timeout=8000)
    wdt.feed()
    wdt.feed()
    assert wdt.feed_count == 2
    times = list(wdt.feed_times)
    assert len(times) == 2
    assert times[0] <= times[1]


def check_wdt_timeout_bounds(m: "ModuleType") -> None:
    # ports/rp2/machine_wdt.c:55-57: above the RP2040's cap construction raises; at or below it the watchdog starts.
    assert m.WDT(timeout=8000).timeout == 8000
    assert m.WDT(timeout=_WDT_TIMEOUT_MAX_MS).timeout == _WDT_TIMEOUT_MAX_MS
    assert isinstance(_raised(lambda: m.WDT(timeout=_WDT_TIMEOUT_MAX_MS + 1)), ValueError)


ALL_CHECKS = (
    check_i2c_state_survives_reconstruction,
    check_irq_edge_values,
    check_pin_constants,
    check_pin_defaults,
    check_pin_pull_semantics,
    check_readfrom_mem_into_delegates,
    check_reset_never_returns,
    check_scan_never_raises,
    check_spi_bit_order,
    check_wdt_feed_times,
    check_wdt_timeout_bounds,
)
FAULT_CHECKS = (check_inject_fault_fifo,)  # these take the backend's injector factory, not the module
