"""Real-interpreter checks of ticks_ms()/ticks_diff()/ticks_add() wraparound (SPECIFICATION.md F.1: rp2's 2**30
period vs this rig's 2**62). No src/ tick user subtracts ticks directly; stored ticks and their horizon are checked
by the L0 scan and the 2**30 fake (Part F.1)."""

import asyncio
import os
import select
import time

from _ticks30 import TICKS_PERIOD, Ticks30Time
from _tmp_scratch import TmpScratch
from machine import I2C as FakeI2C
from machine import UART as FakeUART
from machine import LinkPoller, Pin
from rp2 import DMA

import asy_base_classes
import asy_bmp3xx_driver
import asy_i2c_driver
import asy_neopixel_driver
import asy_notification_service
import asy_system_service
import asy_uart_comm
import asy_uart_driver
from asy_base_classes import TickSeconds
from asy_bmp3xx_driver import BMP3XX_I2C
from asy_i2c_driver import I2C
from asy_neopixel_driver import NeopixelDriver
from asy_notification_service import NotificationService
from asy_print_log import LogConfig
from asy_system_service import SystemService
from asy_uart_comm import ROLE_INITIATOR, UARTComm
from asy_uart_driver import UART

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable

_SRC_DIR = "src"  # scripts/test.sh always invokes tests from the repo root
_TWIN_DIR = "digital_twin"
# Every committed module that reads ticks, as a repo path: this file and tests_scripts/test_ticks_wrap_scan.py (which
# also reads the generated device modules) both check it, so a module that starts or stops using ticks shows up.
_KNOWN_TICKS_USERS = (
    "digital_twin/machine.py",
    "src/asy_base_classes.py",
    "src/asy_bmp3xx_driver.py",
    "src/asy_i2c_driver.py",
    "src/asy_isl29125_driver.py",
    "src/asy_neopixel_driver.py",
    "src/asy_notification_service.py",
    "src/asy_system_service.py",
    "src/asy_uart_comm.py",
    "src/asy_uart_driver.py",
)
_REFERENCE_NOW = 10_000  # a start far from any wrap: each crossing case must match the same call made here
_SCL_PIN = 1
_BMP_ADDR = 0x77
_BMP_STATUS = 0x03  # the STATUS register; bit 4 is cmd_rdy (bst-bmp388-ds001 sec 4.3.3)
_BMP_CMD_RDY = 0x10
_LET_GO_READS = 5000  # a wait still running this many clock reads in is ended by the world, so a lost bound fails, not hangs

_scratch = TmpScratch("ticks_rollover")


class _PauseFlag:
    # The storage side of a pause, as FRAMManager.set_pause() takes it.
    def __init__(self) -> None:
        self.paused = False

    def set_pause(self, *, value: bool) -> None:
        self.paused = value


class _SteppingTime(Ticks30Time):
    # Every ticks_ms() read returns the clock, moves it `step_ms` on and runs `on_read(reads)`: a polling loop's
    # length is its read count, and a test changes what the loop polls at a chosen read.
    def __init__(self, now: int, step_ms: int, on_read: "Callable[[int], None] | None" = None) -> None:
        super().__init__(now)
        self.step_ms = step_ms
        self.on_read = on_read
        self.reads = 0

    def ticks_ms(self) -> int:
        value = super().ticks_ms()
        self.now += self.step_ms
        self.reads += 1
        if self.on_read is not None:
            self.on_read(self.reads)
        return value


# This Unix-port test rig's own ticks period, confirmed empirically (see the module docstring) - NOT the
# real RP2040 target's 2**30. Derived by bisection rather than hardcoded, so a future MicroPython or
# toolchain change that alters it fails loudly instead of silently testing the wrong boundary.
def _discover_this_rigs_ticks_period() -> int:
    # time.ticks_add() accepts a delta strictly between -period/2 and period/2
    # (extmod/modtime.c:178-196, v1.29.0) - the bisection finds the positive bound.
    lo, hi = 1, 1 << 63  # largest accepted delta is in (lo, hi)
    while lo + 1 < hi:
        mid = (lo + hi) // 2
        try:
            # Stub gap: typings/time.pyi types ticks_add()'s first parameter as the opaque _Ticks TypeVar,
            # excluding plain int, while its own docstring shows ticks_add(0, -1) as the canonical way to
            # find a port's tick period. Flagged per this project's policy - hence the ignore.
            time.ticks_add(0, mid)  # type: ignore[type-var]
            lo = mid
        except OverflowError:
            hi = mid
    return 2 * (lo + 1)  # lo == period//2 - 1


_THIS_RIGS_TICKS_PERIOD = _discover_this_rigs_ticks_period()


def _bmp3xx_status_wait(start: int, ready_at: "int | None") -> "tuple[bool, int]":
    # BMP3XX_I2C._wait_status_bits() for cmd_rdy, 50 ms bound, 1 ms per clock read from uptime `start`; STATUS turns
    # ready at read `ready_at` (None: at _LET_GO_READS). Returns (ready in time, clock reads).
    FakeI2C.reset_id(0)
    i2c = I2C(0, scl_pin=1, sda_pin=0, frequency=100000)
    bus: FakeI2C = i2c._i2c  # type: ignore[assignment]
    bus.register_device(_BMP_ADDR)
    bus.registers[(_BMP_ADDR, _BMP_STATUS)] = bytearray(1)
    bmp = BMP3XX_I2C(i2c, address=_BMP_ADDR)

    def on_read(reads: int) -> None:
        if reads == (ready_at or _LET_GO_READS):
            bus.registers[(_BMP_ADDR, _BMP_STATUS)] = bytearray([_BMP_CMD_RDY])

    clock = _install_stepping(asy_bmp3xx_driver, start, 1, on_read)

    async def wait() -> bool:
        async with bmp._i2c_bmp3xx as session:
            try:
                await bmp._wait_status_bits(session, _BMP_CMD_RDY, 50)
            except OSError:
                return False
        return True

    try:
        return asyncio.run(wait()), clock.reads
    finally:
        _restore(asy_bmp3xx_driver)


def _drain_outcome(start: int, fed_reads: int) -> "tuple[int, bool, int]":
    # UARTComm._drain() (100 ms timeout: a 600 ms bound) from uptime `start`, 50 ms per clock read, a frame's worth
    # of bytes arriving at each of the first `fed_reads` reads. Returns (bytes drained, bound hit, clock reads).
    driver = _uart_driver()
    comm = UARTComm(driver, ROLE_INITIATOR, payload_size=8, timeout=100)
    assert asyncio.run(comm.setup()) is True
    size = len(comm._rx.get_buf() or b"")
    fake: FakeUART = driver._uart  # type: ignore[assignment]

    def on_read(reads: int) -> None:
        if reads <= fed_reads:
            fake.feed_rx(bytes(size))

    clock = _install_stepping(asy_uart_comm, start, 50, on_read)

    async def drain() -> int:
        async with driver as device:
            return await comm._drain(device)

    try:
        return asyncio.run(drain()), comm._drain_bound_hit, clock.reads
    finally:
        _restore(asy_uart_comm)


def _files_reading_ticks(directory: str) -> "list[str]":
    # Repo paths of the directory's modules naming ticks_ms() or ticks_us(); L1 has no ast, the L0 scan judges each site.
    found = []
    for filename in sorted(f for f in os.listdir(directory) if f.endswith(".py")):
        with open(directory + "/" + filename) as handle:
            text = handle.read()
        if "ticks_ms()" in text or "ticks_us()" in text:
            found.append(directory + "/" + filename)
    return found


def _install(module: object, start: int) -> Ticks30Time:
    # The fake as the module's own `time`, its uptime at `start`; _restore() puts the real module back.
    fake = Ticks30Time(start)
    module.time = fake  # type: ignore[attr-defined]  # a module attribute swap, restored in each test's finally
    return fake


def _install_stepping(module: object, start: int, step_ms: int, on_read: "Callable[[int], None]") -> _SteppingTime:
    # _install() with a _SteppingTime: each of the module's clock reads moves it step_ms on.
    clock = _SteppingTime(start, step_ms, on_read)
    module.time = clock  # type: ignore[attr-defined]  # a module attribute swap, restored in each test's finally
    return clock


def _neopixel_wait_outcome(start: int, wait_ms: int, *, release_after_ms: "int | None") -> "tuple[bool, bool, bool]":
    # request_signal() behind a queued signal, its deadline armed at `start`: (still pending one ms before the deadline
    # or after the release, finished at the deadline, returned True); release_after_ms clears the signal that far in.
    driver = NeopixelDriver(0, neopixel_freq=100, led_overl_bri=50, log=LogConfig(None, 10, None))
    asyncio.run(driver.setup())
    fake = _install(asy_neopixel_driver, start)

    async def scenario() -> "tuple[bool, bool, bool]":
        driver._start_signal_event.set()  # a signal is queued and no signal task runs
        waiter = asyncio.create_task(driver.request_signal(0, 10, 0, 0.1))
        await asyncio.sleep(0)  # one yield: the waiter takes its deadline at `start`
        if release_after_ms is not None:
            fake.now = start + release_after_ms
            driver._start_signal_event.clear()
        else:
            fake.now = start + wait_ms - 1
        await asyncio.sleep_ms(50)  # several of the driver's 10 ms polls
        pending = not waiter.done()
        fake.now = start + wait_ms
        for _ in range(200):
            if waiter.done():
                break
            await asyncio.sleep_ms(5)
        finished = waiter.done()
        if not finished:
            waiter.cancel()
        try:
            result = await waiter
        except asyncio.CancelledError:
            result = None
        return pending, finished, result is True

    try:
        return asyncio.run(scenario())
    finally:
        _restore(asy_neopixel_driver)


def _next_sleep_after(start: int, elapsed_ms: int, interv: float) -> float:
    # _next_sleep_s(interv, t0) with t0 taken at `start` and the clock `elapsed_ms` later.
    coordinator = NotificationService(_no_signal, _no_local_time, (), cfg_path=_scratch.dir(), log=LogConfig(None, 10, None))
    fake = _install(asy_notification_service, start)
    try:
        t0 = fake.ticks_ms()
        fake.advance(elapsed_ms)
        return coordinator._next_sleep_s(interv, t0)  # type: ignore[arg-type]  # a ticks value from the fake
    finally:
        _restore(asy_notification_service)


async def _no_local_time() -> None:
    return None


async def _no_signal(_r: int, _g: int, _b: int, _t: float) -> bool:
    return True


def _restore(module: object) -> None:
    module.time = time  # type: ignore[attr-defined]


async def _not_synced() -> bool:
    return False


def _scl_wait(start: int, timeout_us: int, *, sync: bool, held_reads: "int | None") -> "tuple[bool, int]":
    # The I2C SCL-release wait from uptime `start`, 1 ms per SCL read, SCL held for `held_reads` reads (None: until
    # _LET_GO_READS). Returns (released, SCL reads).
    fake = _install(asy_i2c_driver, start)
    reads = [0]

    def scl_level(_pin: int, _log: object) -> int:
        reads[0] += 1
        fake.advance(1)
        return 0 if reads[0] <= (held_reads or _LET_GO_READS) else 1

    Pin.reset_registry()
    Pin.set_external_level(_SCL_PIN, scl_level)
    scl = Pin(_SCL_PIN, Pin.IN, pull=Pin.PULL_UP)
    try:
        released = asy_i2c_driver._scl_released_sync(scl, timeout_us) if sync else asyncio.run(asy_i2c_driver._scl_released(scl, timeout_us))
        return released, reads[0]
    finally:
        _restore(asy_i2c_driver)
        Pin.reset_registry()


def _sequencer_outcome(start: int, delays: "tuple[int, ...]") -> "tuple[list[int], list[int]]":
    # start_timers() over one trigger per delay from uptime `start`, trigger k's starter taking delays[k] ms; each
    # stagger arm fires once the clock has moved its period on. Returns (armed periods, start order).
    clock = _install(asy_system_service, start)
    svc = SystemService(_not_synced)
    timer = svc._sequencer_timer
    started: list[int] = []

    def starter(k: int) -> "Callable[[], None]":
        def start_trigger() -> None:
            started.append(k)
            clock.advance(delays[k])

        return start_trigger

    async def scenario() -> "list[int]":
        task = asyncio.create_task(svc.start_timers([starter(k) for k in range(len(delays))], []))
        periods: list[int] = []
        for _ in range(4 * len(delays)):  # a bounded number of rounds, each one stagger at most
            for _ in range(5):
                await asyncio.sleep(0)
            if task.done():
                break
            if timer.callback is not None:  # armed and not yet fired
                periods.append(timer.period)
                clock.advance(timer.period)
                timer.trigger()
        assert task.done(), (periods, started)
        return periods

    try:
        return asyncio.run(scenario()), started
    finally:
        _restore(asy_system_service)


def _src_const(path: str, name: str) -> int:
    # The shipped value, read from the source: a const() named with a leading underscore is not a module attribute.
    with open(path) as f:
        for line in f:
            if line.startswith(name + " = const("):
                return int(line.split("const(", 1)[1].split(")", 1)[0])
    raise AssertionError(name + " not found in " + path)


def _storage_pause_outcome(start: int) -> "tuple[bool, bool, bool, bool]":
    # A 60 s storage pause armed at uptime `start`, the uptime pass run once a second: (paused, deadline pending) on
    # the pass 1 ms before its deadline, then on the pass at it.
    clock = _install(asy_system_service, start)
    asy_base_classes.time = clock  # type: ignore[assignment]  # the uptime the pass reads, on the same clock
    storage = _PauseFlag()
    svc = SystemService(_not_synced, storage=storage)  # type: ignore[arg-type]  # set_pause() is all a pause uses

    async def one_pass(step_ms: int) -> None:
        clock.advance(step_ms)
        svc._uptime_event.set()
        for _ in range(5):
            await asyncio.sleep(0)

    async def scenario() -> "tuple[bool, bool, bool, bool]":
        task = asyncio.create_task(svc._status_loop())
        await asyncio.sleep(0)
        assert svc.pause_permanent_storage(60) is True
        for step_ms in [1000] * 59 + [999]:
            await one_pass(step_ms)
        before = (storage.paused, svc._unpause_at is not None)
        await one_pass(1)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        return before[0], before[1], storage.paused, svc._unpause_at is not None

    try:
        return asyncio.run(scenario())
    finally:
        _restore(asy_system_service)
        _restore(asy_base_classes)


def _tickseconds_reads(start: int, *, count_down: bool) -> "list[int]":
    # One TickSeconds through a fixed 6 s script from uptime `start`: a read at 0.7 s, a restart at 1.3 s, reads
    # at 1.6 s, 3.4 s and 6 s.
    fake = _install(asy_base_classes, start)
    try:
        ticks = TickSeconds(count_down=count_down)
        ticks.restart(10 if count_down else 0)
        fake.advance(700)
        reads = [ticks.read()]
        fake.advance(600)
        ticks.restart(20 if count_down else 100)
        for step in (300, 1800, 2600):
            fake.advance(step)
            reads.append(ticks.read())
        return reads
    finally:
        _restore(asy_base_classes)


def _uart_cancel_wait(start: int, ack_at: "int | None") -> "tuple[bool, int, int]":
    # UART.cancel_read_timeout(50) against a held session, 1 ms per clock read from uptime `start`; the read path
    # acknowledges at read `ack_at` (None: at _LET_GO_READS). Returns (cancel outstanding, unacknowledged count, clock reads).
    driver = _uart_driver()

    def on_read(reads: int) -> None:
        if reads == (ack_at or _LET_GO_READS):
            driver._ack_cancel()

    clock = _install_stepping(asy_uart_driver, start, 1, on_read)

    async def cancel() -> bool:
        async with driver.session_lock:
            return await driver.cancel_read_timeout(50)

    try:
        return asyncio.run(cancel()), driver.cancel_unacknowledged, clock.reads
    finally:
        _restore(asy_uart_driver)


def _uart_driver() -> UART:
    # A UART whose fed bytes land at once, its receive ring armed; transmit polls through the bounded LinkPoller.
    DMA.reset_registry()  # each armed ring holds two of the twelve channels, and no per-test reset exists
    driver = UART(0, tx_pin=0, rx_pin=1, poll_wait_ms=1, poll_idle_ms=1)
    fake: FakeUART = driver._uart  # type: ignore[assignment]
    fake.rx_rate = float("inf")
    driver.poller = LinkPoller(fake, mask=select.POLLOUT)  # type: ignore[assignment]
    return driver


def _uart_ready_wait(start: int, arrive_at: "int | None") -> "tuple[bool, int]":
    # UART.ready(POLLIN, 50) from uptime `start`, 1 ms per clock read; a byte arrives at read `arrive_at` (None: at
    # _LET_GO_READS). Returns (ready, clock reads).
    driver = _uart_driver()
    assert driver.setup_rx_ring() is True
    fake: FakeUART = driver._uart  # type: ignore[assignment]

    def on_read(reads: int) -> None:
        if reads == (arrive_at or _LET_GO_READS):
            fake.feed_rx(b"x")

    clock = _install_stepping(asy_uart_driver, start, 1, on_read)
    try:
        return asyncio.run(driver.ready(select.POLLIN, 50)), clock.reads
    finally:
        _restore(asy_uart_driver)


def test_this_rigs_ticks_period_is_self_consistent() -> None:
    # Re-derives the exact accepted/rejected boundary independently of the bisection above, as a
    # direct check on the discovered period rather than trusting the bisection's own arithmetic.
    half = _THIS_RIGS_TICKS_PERIOD // 2
    assert time.ticks_add(0, half - 1) == half - 1  # type: ignore[type-var]  # stub gap, see _discover_this_rigs_ticks_period()
    try:
        time.ticks_add(0, half)  # type: ignore[type-var]  # stub gap, see _discover_this_rigs_ticks_period()
        raise AssertionError("expected OverflowError for a delta of exactly period/2")
    except OverflowError:
        pass


def test_ticks_diff_correct_when_now_has_wrapped_past_t0() -> None:
    # t0 sits just before this rig's wraparound and "now" a small elapsed time later, wrapped to a
    # raw value near zero - where a raw `now - t0` computes ~ -period instead. Built via
    # time.ticks_add() only, never a literal near the boundary (it lands there whatever the rig's period).
    t0 = time.ticks_add(0, -50)  # type: ignore[type-var]  # raw value: period - 50, just before the wrap
    now = time.ticks_add(t0, 200)  # type: ignore[type-var]  # 200ms later, having wrapped past zero
    assert time.ticks_diff(now, t0) == 200


def test_ticks_diff_correct_when_t0_has_wrapped_past_now() -> None:
    # The symmetric case, exercised right at the boundary itself: t0's raw value is small (just
    # after the wrap), "now" is a raw value just before that same wrap - representing "not quite
    # elapsed yet" rather than "a full period minus a bit has elapsed".
    t0 = time.ticks_add(0, 5)  # type: ignore[type-var]  # just after the wrap, see _discover_this_rigs_ticks_period()
    now = time.ticks_add(0, -50)  # type: ignore[type-var]  # period - 50, just before the same wrap
    assert time.ticks_diff(now, t0) == -55  # -50 - 5, not a huge bogus swing


def test_ticks_diff_matches_plain_subtraction_away_from_any_wrap() -> None:
    # Sanity check on the harness itself: far from the boundary, ticks_diff() must agree with
    # plain subtraction - proves the two wrap tests above are actually exercising wrap-specific
    # behavior, not some unrelated ticks_diff() quirk that would also show up here.
    t0 = _THIS_RIGS_TICKS_PERIOD // 2
    now = t0 + 300
    assert time.ticks_diff(now, t0) == 300


def test_ticks_diff_timeout_comparison_correct_across_a_wrap() -> None:
    # The exact expression every real src/ use site evaluates, time.ticks_diff(now, t0) >= timeout_ms,
    # driven straight through the wraparound boundary - proving the comparison, not just the raw diff value,
    # comes out right on both sides of a real timeout threshold.
    t0 = time.ticks_add(0, -50)  # type: ignore[type-var]  # just before the wrap, see _discover_this_rigs_ticks_period()
    now_at_150ms = time.ticks_add(t0, 150)  # type: ignore[type-var]
    assert time.ticks_diff(now_at_150ms, t0) >= 100  # timeout already elapsed
    assert not (time.ticks_diff(now_at_150ms, t0) >= 200)  # timeout not yet elapsed


def test_every_known_ticks_user_is_actually_covered_by_this_audit() -> None:
    # The scans prove nothing about a file they never read. This is what keeps their coverage
    # honest when a module is added, renamed, or stops measuring time.
    using_ticks = _files_reading_ticks(_SRC_DIR) + _files_reading_ticks(_TWIN_DIR)
    for expected in _KNOWN_TICKS_USERS:
        assert expected in using_ticks, f"{expected} no longer measures elapsed time - update _KNOWN_TICKS_USERS"
    unlisted = [f for f in using_ticks if f not in _KNOWN_TICKS_USERS]
    assert unlisted == [], f"new ticks user(s) not yet listed in this audit: {unlisted}"


def test_ticks30_matches_the_real_module_away_from_the_wrap() -> None:
    # The fake against an independent reference: where no 2**30 wrap is involved its results are the real module's.
    fake = Ticks30Time()
    samples = (0, 1, 999, 1000, 65_535, 1 << 20, 1 << 28, (1 << 29) - 1, 1 << 29, (1 << 29) + 1, TICKS_PERIOD - (1 << 28), TICKS_PERIOD - 1)
    deltas = (-((1 << 29) - 1), -1000, -1, 0, 1, 1000, (1 << 29) - 1)
    compared = 0
    for a in samples:
        fake.now = a
        assert fake.ticks_ms() == a
        for b in samples:
            if -(1 << 29) < a - b < (1 << 29):
                assert fake.ticks_diff(a, b) == time.ticks_diff(a, b), (a, b)
                compared += 1
        for d in deltas:
            if 0 <= a + d < TICKS_PERIOD:
                assert fake.ticks_add(a, d) == time.ticks_add(a, d), (a, d)  # type: ignore[type-var]  # stub gap
                compared += 1
    assert compared > 150  # the guards above leave most pairs in, so the comparison is not vacuous


def test_ticks30_wraps_and_refuses_where_the_board_does() -> None:
    # rp2's 2**30 period per extmod/modtime.c (v1.29.0); the rig's own 2**62 period shows none of this.
    fake = Ticks30Time(TICKS_PERIOD + 7)
    assert fake.ticks_ms() == 7
    assert fake.ticks_add(TICKS_PERIOD - 3, 5) == 2
    assert fake.ticks_add(2, -5) == TICKS_PERIOD - 3
    assert fake.ticks_diff(2, TICKS_PERIOD - 3) == 5
    assert fake.ticks_diff(TICKS_PERIOD - 3, 2) == -5
    assert fake.ticks_diff((1 << 29) - 1, 0) == (1 << 29) - 1
    assert fake.ticks_diff(1 << 29, 0) == -(1 << 29)  # half a period apart already reads as the past
    assert fake.ticks_add(0, (1 << 29) - 1) == (1 << 29) - 1
    assert fake.ticks_add(0, -((1 << 29) - 1)) == (1 << 29) + 1
    for delta in (1 << 29, -(1 << 29), 1 << 40):
        try:
            fake.ticks_add(0, delta)
            raise AssertionError(f"expected OverflowError for a delta of {delta}")
        except OverflowError:
            pass
    for bad in ((None, 0), (0, None), (TICKS_PERIOD, 0), (0, 1.5)):
        try:
            fake.ticks_diff(bad[0], bad[1])  # type: ignore[arg-type]  # a non-tick argument on purpose
            raise AssertionError(f"expected TypeError for ticks_diff{bad}")
        except TypeError:
            pass
    try:
        fake.ticks_add(0, 1.5)  # type: ignore[arg-type]  # a float delta, as the board refuses
        raise AssertionError("expected TypeError for a float delta")
    except TypeError:
        pass


def test_ticks30_ticks_us_is_now_times_1000_on_the_same_period() -> None:
    fake = Ticks30Time(5)
    assert fake.ticks_us() == 5000
    fake.now = TICKS_PERIOD // 1000  # 1_073_741 ms: its microseconds sit 824 us below the wrap
    before = fake.ticks_us()
    fake.advance(1)
    assert fake.ticks_us() == 176  # wrapped
    assert fake.ticks_diff(fake.ticks_us(), before) == 1000


def test_ticks30_delegates_every_other_name_to_the_real_module() -> None:
    fake = Ticks30Time()
    assert fake.gmtime is time.gmtime
    assert fake.mktime is time.mktime
    assert fake.sleep_ms is time.sleep_ms
    assert fake.time is time.time
    fake.now = 41
    fake.advance(1)
    assert fake.now == 42


def test_tickseconds_read_and_restart_cross_the_ticks_wrap() -> None:
    # Up and down from 1.5 s before 2**30: the restart's stored tick and the read after it straddle the wrap.
    for count_down, expected in ((False, [0, 100, 102, 104]), (True, [10, 20, 18, 16])):
        wrapped = _tickseconds_reads(TICKS_PERIOD - 1500, count_down=count_down)
        assert wrapped == _tickseconds_reads(_REFERENCE_NOW, count_down=count_down), (count_down, wrapped)
        assert wrapped == expected, (count_down, wrapped)


def test_tickseconds_counts_up_to_the_horizon_its_readers_keep() -> None:
    # The horizon its header states, across the wrap: an interval under 2**29 ms counts whole, one of 2**29 counts nothing.
    for start in (TICKS_PERIOD - 1000, _REFERENCE_NOW):
        fake = _install(asy_base_classes, start)
        try:
            ticks = TickSeconds()
            fake.advance((1 << 29) - 1)
            assert ticks.read() == ((1 << 29) - 1) // 1000, start
            ticks.restart(0)
            fake.advance(1 << 29)
            assert ticks.read() == 0, start
        finally:
            _restore(asy_base_classes)


def test_next_sleep_s_crosses_the_ticks_wrap() -> None:
    # t0 1 s before the wrap; 5 s and 70 s later (past a 60 s interval: the floor).
    for elapsed_ms in (5000, 70_000):
        wrapped = _next_sleep_after(TICKS_PERIOD - 1000, elapsed_ms, 60.0)
        assert wrapped == _next_sleep_after(_REFERENCE_NOW, elapsed_ms, 60.0), (elapsed_ms, wrapped)
    assert abs(_next_sleep_after(TICKS_PERIOD - 1000, 5000, 60.0) - 55.0) < 1e-6
    assert _next_sleep_after(TICKS_PERIOD - 1000, 70_000, 60.0) == 0.1


def test_neopixel_signal_deadline_crosses_the_ticks_wrap() -> None:
    # Armed half a wait before the wrap, the deadline lands past it: held one ms before, dropped at it.
    wait_ms = _src_const("src/asy_neopixel_driver.py", "_SIGNAL_WAIT_MS")
    start = TICKS_PERIOD - wait_ms // 2
    assert start + wait_ms > TICKS_PERIOD
    wrapped = _neopixel_wait_outcome(start, wait_ms, release_after_ms=None)
    assert wrapped == _neopixel_wait_outcome(_REFERENCE_NOW, wait_ms, release_after_ms=None)
    assert wrapped == (True, True, False)


def test_neopixel_signal_released_past_the_wrap_is_taken() -> None:
    # The queued signal ends after the wrap, before the deadline: the waiting request is queued, not dropped.
    wait_ms = _src_const("src/asy_neopixel_driver.py", "_SIGNAL_WAIT_MS")
    start = TICKS_PERIOD - wait_ms // 2
    release = wait_ms // 2 + 1000
    wrapped = _neopixel_wait_outcome(start, wait_ms, release_after_ms=release)
    assert wrapped == _neopixel_wait_outcome(_REFERENCE_NOW, wait_ms, release_after_ms=release)
    assert wrapped == (False, True, True)


def test_the_bmp3xx_status_wait_crosses_the_ticks_wrap() -> None:
    # Started 20 ms before the wrap: STATUS never ready ends at the 50 ms bound, STATUS ready after the wrap is taken.
    for ready_at, expected in ((None, (False, 51)), (40, (True, 40)), (50, (True, 50))):
        wrapped = _bmp3xx_status_wait(TICKS_PERIOD - 20, ready_at)
        assert wrapped == _bmp3xx_status_wait(_REFERENCE_NOW, ready_at), (ready_at, wrapped)
        assert wrapped == expected, (ready_at, wrapped)


def test_the_uart_drain_bound_crosses_the_ticks_wrap() -> None:
    # Started 300 ms before the wrap: a peer that never stops ends at the 600 ms bound, one that stops is drained dry.
    for fed_reads, expected in ((1000, (True, 14)), (3, (False, 5))):
        wrapped = _drain_outcome(TICKS_PERIOD - 300, fed_reads)
        assert wrapped == _drain_outcome(_REFERENCE_NOW, fed_reads), (fed_reads, wrapped)
        assert wrapped[0] > 0 and wrapped[1:] == expected, (fed_reads, wrapped)


def test_the_uart_ready_wait_crosses_the_ticks_wrap() -> None:
    # Started 20 ms before the wrap: no byte ends the wait past its 50 ms bound, a byte after the wrap is reported.
    for arrive_at, expected in ((None, (False, 52)), (40, (True, 40)), (51, (True, 51))):
        wrapped = _uart_ready_wait(TICKS_PERIOD - 20, arrive_at)
        assert wrapped == _uart_ready_wait(_REFERENCE_NOW, arrive_at), (arrive_at, wrapped)
        assert wrapped == expected, (arrive_at, wrapped)


def test_the_uart_cancel_ack_wait_crosses_the_ticks_wrap() -> None:
    # Started 20 ms before the wrap: no acknowledgement ends at the 50 ms bound and counts it, one after the wrap ends it.
    for ack_at, expected in ((None, (True, 1, 52)), (40, (True, 0, 40))):
        wrapped = _uart_cancel_wait(TICKS_PERIOD - 20, ack_at)
        assert wrapped == _uart_cancel_wait(_REFERENCE_NOW, ack_at), (ack_at, wrapped)
        assert wrapped == expected, (ack_at, wrapped)


def test_the_i2c_scl_release_waits_cross_the_ticks_us_wrap() -> None:
    # Both waits start 824 us before ticks_us() wraps and end where they end far from it: at the bus timeout for a
    # held clock, at the release for one let go inside it.
    start = TICKS_PERIOD // 1000
    assert (start * 1000) % TICKS_PERIOD > TICKS_PERIOD - 1000
    for sync in (True, False):
        for held_reads, expected in ((None, (False, 200)), (150, (True, 151)), (199, (True, 200))):
            wrapped = _scl_wait(start, 200_000, sync=sync, held_reads=held_reads)
            assert wrapped == _scl_wait(_REFERENCE_NOW, 200_000, sync=sync, held_reads=held_reads), (sync, held_reads, wrapped)
            assert wrapped == expected, (sync, held_reads, wrapped)


def test_the_trigger_stagger_crosses_the_ticks_wrap() -> None:
    # One shared start 300 ms before the wrap, slots 200 ms apart: the slot past the wrap waits what it waits far from
    # it, and a slot an over-long starter already passed starts at once, unarmed.
    delays = (0, 50, 250, 0)
    wrapped = _sequencer_outcome(TICKS_PERIOD - 300, delays)
    assert wrapped == _sequencer_outcome(_REFERENCE_NOW, delays), wrapped
    assert wrapped == ([200, 150], [0, 1, 2, 3]), wrapped


def test_the_storage_pause_deadline_crosses_the_ticks_wrap() -> None:
    # Armed 30 s before the wrap, the 60 s deadline lands past it: still paused on the pass 1 ms before, released at it.
    wrapped = _storage_pause_outcome(TICKS_PERIOD - 30_000)
    assert wrapped == _storage_pause_outcome(_REFERENCE_NOW), wrapped
    assert wrapped == (True, True, False, False), wrapped


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
