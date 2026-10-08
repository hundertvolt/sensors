"""Unit tests for src/asy_uart_comm.py (SPECIFICATION.md Part J): construction
and readiness, frame build/validate/ACK, the acknowledged exchange and its recovery, and the
transaction layer. The comm-hazard tier lives in test_uart_comm_hazard.py and test_uart_comm_cancel_sweep.py."""

import asyncio
import gc
import select
import struct
import time

from _error_codes import code
from _fram_chip_fake import FakeMB85RS64V
from _ticks30 import TICKS_PERIOD, Ticks30Time
from _uart_comm_harness import (
    PAYLOAD_SIZE,
    POLL_WAIT_MS,
    RUN_LIMIT_S,
    TIMEOUT_MS,
    Pair,
    PollRoundClock,
    accept_set,
    build_pair,
    copied_out,
    echo_get,
    fake_of,
    frames,
    run,
    transfer_limits,
)
from machine import LinkPoller, UARTLink
from rp2 import DMA

import asy_print_log as print_log_module
import asy_spi_driver
import asy_uart_comm
from asy_base_classes import COUNTER_CAP, PieceBuffer, RegionBuffer
from asy_crc_checks import CRC16
from asy_fram_manager import FRAMManager
from asy_framing_codecs import FramingCOBS
from asy_print_log import LogConfig, PrintLogHistoryStore, make_logger
from asy_spi_driver import SPI
from asy_uart_comm import (
    DEFAULT_LIMITS,
    ROLE_INITIATOR,
    ROLE_RESPONDER,
    ListenResult,
    ResponderCallbacks,
    TransferLimits,
    UARTComm,
)
from asy_uart_driver import UART

asy_spi_driver._SPI = FakeMB85RS64V  # type: ignore[misc]  # one process per test file: the FRAM-backed log case

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any

_SRC = "src/asy_uart_comm.py"

_CMD_ACK = 0x01
_CMD_GET = 0x02
_CMD_SET = 0x04
_UID = 0
_CMD = 1
_SIZE = 2
_CHUNKS = 3
_CUR = 4
_PAYLOAD = 5
_FRAME = 5 + PAYLOAD_SIZE

# @tunable l1.asy_uart_comm_short_reply_timeout_ms = 30
_SHORT_REPLY_TIMEOUT_MS = 30
# @tunable l1.asy_uart_comm_step_bound_s = 10
_STEP_BOUND_S = 10
# @tunable l1.asy_uart_comm_loop_survival_wait_ms = 20
_LOOP_SURVIVAL_WAIT_MS = 20
# @tunable l1.asy_uart_comm_silent_bound_s = 15
_SILENT_BOUND_S = 15
# @tunable l1.asy_uart_comm_listener_run_bound_s = 25
_LISTENER_RUN_BOUND_S = 25
# @tunable l1.asy_uart_comm_short_bound_s = 5
_SHORT_BOUND_S = 5
# @tunable l1.asy_uart_comm_past_deadline_bound_s = 2
_PAST_DEADLINE_BOUND_S = 2
# @tunable l1.asy_uart_comm_flood_step_ms = 1
_FLOOD_STEP_MS = 1
# @tunable l1.asy_uart_comm_run_bound_s = 20
_RUN_BOUND_S = 20
# @tunable l1.asy_uart_comm_listener_park_ms = 10
_LISTENER_PARK_MS = 10
# @tunable l1.asy_uart_comm_inside_lock_ms = 5
_INSIDE_LOCK_MS = 5
# @tunable l1.asy_uart_comm_listener_short_bound_s = 8
_LISTENER_SHORT_BOUND_S = 8
# @tunable l1.asy_uart_comm_async_callback_yield_ms = 1
_ASYNC_CALLBACK_YIELD_MS = 1
# @tunable l1.asy_uart_comm_bsec_run_bound_s = 60
_BSEC_RUN_BOUND_S = 60
# @tunable l1.asy_uart_comm_prompt_hold_ms = 5
_PROMPT_HOLD_MS = 5
_PAST_CANCEL_ACK_HOLD_MS = 1300
# @tunable l1.asy_uart_comm_cap_refusals = 50
_REFUSALS = 50
# @tunable l1.asy_uart_comm_hammer_rounds = 200
_HAMMER_ROUNDS = 200
# @tunable l1.asy_uart_comm_hammer_run_bound_s = 120
_HAMMER_RUN_BOUND_S = 120
# @tunable l1.asy_uart_comm_flush_recovery_tries = 5
_FLUSH_RECOVERY_TRIES = 5
# @tunable l1.asy_uart_comm_hold_off_look_ms = 30
_HOLD_OFF_LOOK_MS = 30


def persisted(comm: UARTComm) -> "list[str]":
    # ErrNum holds errnos and wrnnos in one ring and they share the number space, so ErrType is
    # what tells them apart; "N" is an unused slot. Indexed rather than zip()ed - MicroPython's
    # zip() has no strict= parameter to satisfy B905.
    entry = run(comm.get_error_counter())[comm.name]
    nums, kinds = entry["ErrNum"], entry["ErrType"]
    return [f"{kinds[i]}{nums[i]}" for i in range(len(nums)) if kinds[i] != "N"]


def _e(name: str) -> str:  # persisted()'s form of a catalog errno
    return f"E{code('E', name)}"


def _w(name: str) -> str:  # persisted()'s form of a catalog wrnno
    return f"W{code('W', name)}"


def make_comm(**kwargs: "Any") -> UARTComm:
    DMA.reset_registry()  # no per-test reset exists, and each link's ring holds two of the twelve channels
    driver = UART(0, tx_pin=0, rx_pin=1, poll_wait_ms=POLL_WAIT_MS, poll_idle_ms=POLL_WAIT_MS)
    driver._uart.rx_rate = float("inf")  # type: ignore[union-attr]  # fed bytes land at once, not on the fake clock
    driver.poller = LinkPoller(driver._uart, mask=select.POLLOUT)  # type: ignore[assignment,arg-type]
    params: dict[str, Any] = dict(kwargs)
    fields = {n: params.pop(n) for n in ("payload_size", "timeout", "chunk_bytes", "max_transfer_bytes") if n in params}
    if "limits" not in params:
        params["limits"] = transfer_limits(**fields)
    role = params.pop("role", ROLE_INITIATOR)
    bus = params.pop("uart", driver)
    names = ("get_callback", "set_callback", "message_callback")
    if any(n in params for n in names):
        params["callbacks"] = ResponderCallbacks(*(params.pop(n, None) for n in names))
    return UARTComm(bus, role, **params)


def _make_fram_manager(chip: "FakeMB85RS64V | None" = None) -> "tuple[FRAMManager, FakeMB85RS64V]":
    # A fresh manager, over the given chip's memory when one is passed (a simulated reboot).
    manager = FRAMManager(SPI(0, sck_pin=2, mosi_pin=3, miso_pin=4), 1, max_size=0x2000)
    if chip is not None:
        manager.fram._spidev.spi._spi = chip
    own = manager.fram._spidev.spi._spi
    assert isinstance(own, FakeMB85RS64V)
    assert run(manager.setup()) is True
    return manager, own


# ===========================================================================
# Module foundation
# ===========================================================================
# C2 - constructor, parameter validation, readiness gate


def test_valid_construction_sets_the_gate_only_after_setup() -> None:
    comm = make_comm()
    assert comm.initialized is False  # nothing is usable before setup()
    assert run(comm.setup()) is True
    assert comm.initialized is True


def test_payload_size_boundaries_are_accepted_and_refused() -> None:
    # SIZE/CHUNKS are single bytes and a zero-width payload cannot carry the command id.
    for good in (1, 255):
        roomy = UART(0, tx_pin=0, rx_pin=1, poll_wait_ms=POLL_WAIT_MS, poll_idle_ms=POLL_WAIT_MS, rxbuf=2048, rx_ring=2048)
        roomy.poller = LinkPoller(roomy._uart)  # type: ignore[assignment,arg-type]  # never a real select.poll()
        comm = make_comm(payload_size=good, uart=roomy)
        assert comm._init_errno == 0, f"payload_size {good} should be legal"
    for bad in (0, 256, -1):
        comm = make_comm(payload_size=bad)
        assert comm._init_errno != 0, f"payload_size {bad} should be refused"
        assert run(comm.setup()) is False


def test_payload_size_is_never_silently_clamped() -> None:
    # A clamp turns a loud configuration error into a link that desyncs intermittently in the
    # field - the one fault J.6 says the self-healing design cannot heal.
    comm = make_comm(payload_size=500)
    assert comm._payload_size == 500  # kept as given, and refused; not quietly rewritten to 255
    assert comm.initialized is False


def test_non_positive_timeout_is_refused() -> None:
    for bad in (0, -1):
        assert make_comm(timeout=bad)._init_errno != 0


def test_timeout_below_the_gc_pause_floor_is_refused() -> None:
    # Below this a routine collection pause reads as a link fault, and the link resyncs
    # continuously under memory pressure for no reason.
    driver = UART(0, tx_pin=0, rx_pin=1, poll_wait_ms=9, poll_idle_ms=9)  # floor 2 x 9 + 9 + 21 = 48
    driver.poller = LinkPoller(driver._uart)  # type: ignore[assignment,arg-type]
    assert UARTComm(driver, ROLE_INITIATOR, limits=transfer_limits(timeout=30))._init_errno == code("E", "UART_TIMEOUT_PARAM")
    assert UARTComm(driver, ROLE_INITIATOR, limits=transfer_limits(timeout=200))._init_errno == 0


def test_an_idle_poll_rate_the_reply_budget_cannot_cover_is_refused() -> None:
    # J.6 states that poll_idle_ms is the first-byte notice latency and "must stay well under the
    # peer's timeout", and nothing enforced it: an idle responder polling every 5s answers nothing
    # within a 1s budget, so a perfectly sound link fails every request and looks dead.
    def bus(idle_ms: int) -> UART:
        driver = UART(0, tx_pin=0, rx_pin=1, poll_wait_ms=2, poll_idle_ms=idle_ms, rxbuf=1024)
        driver.poller = LinkPoller(driver._uart)  # type: ignore[assignment,arg-type]
        return driver

    assert UARTComm(bus(5000), ROLE_INITIATOR, limits=transfer_limits(timeout=1000))._init_errno != 0
    assert UARTComm(bus(50), ROLE_INITIATOR, limits=transfer_limits(timeout=1000))._init_errno == 0


def test_invalid_role_is_refused_and_has_no_default() -> None:
    assert make_comm(role="listener")._init_errno != 0
    assert make_comm(role=ROLE_INITIATOR)._init_errno == 0
    assert make_comm(role=ROLE_RESPONDER, get_callback=echo_get(b""), set_callback=accept_set())._init_errno == 0


def test_a_none_bus_is_recorded_distinctly_and_never_raises() -> None:
    # Otherwise every call returns a sentinel with no explanation of which thing was wrong.
    comm = make_comm(uart=None)
    assert comm._init_errno != 0
    assert run(comm.setup()) is False
    assert run(comm.uart_set(1, b"x")) is False
    assert run(comm.uart_get(1)) is None
    run(comm.clear())  # must not raise even with no bus at all


def test_construction_performs_no_bus_call() -> None:
    # An allocate-only constructor, so construction can never hang outside any supervisor.
    driver = UART(0, tx_pin=0, rx_pin=1, poll_wait_ms=POLL_WAIT_MS, poll_idle_ms=POLL_WAIT_MS)
    driver.poller = LinkPoller(driver._uart)  # type: ignore[assignment,arg-type]
    before = len(driver._uart.log)  # type: ignore[union-attr]
    UARTComm(driver, ROLE_INITIATOR, limits=transfer_limits())
    assert len(driver._uart.log) == before  # type: ignore[union-attr]


def test_maximum_payload_size_against_the_default_rxbuf_is_refused() -> None:
    # 5 + 255 = 260 bytes against the driver's own 256-byte default rxbuf, so the maximum
    # legal payload_size overruns it outright - a frame that never completes, indistinguishable
    # from a link fault unless it is caught at construction.
    driver = UART(0, tx_pin=0, rx_pin=1, poll_wait_ms=POLL_WAIT_MS, poll_idle_ms=POLL_WAIT_MS)  # rxbuf defaults to 256
    driver.poller = LinkPoller(driver._uart)  # type: ignore[assignment,arg-type]
    refused = UARTComm(driver, ROLE_INITIATOR, limits=transfer_limits(payload_size=255))
    assert refused._init_errno != 0
    roomy = UART(1, tx_pin=8, rx_pin=9, poll_wait_ms=POLL_WAIT_MS, poll_idle_ms=POLL_WAIT_MS, rxbuf=1024, rx_ring=2048)  # the ring sized for a 260-byte frame at a 100 ms timeout
    roomy.poller = LinkPoller(roomy._uart)  # type: ignore[assignment,arg-type]
    assert UARTComm(roomy, ROLE_INITIATOR, limits=transfer_limits(payload_size=255))._init_errno == 0


def test_a_ring_too_small_for_one_poll_interval_is_refused() -> None:
    # A 9ms poll interval plus the module's 5ms of scheduling slack admits ~161 bytes at 115200 baud,
    # so a 64-byte ring loses the tail of anything sustained even though a frame fits.
    driver = UART(0, tx_pin=0, rx_pin=1, baudrate=115200, poll_wait_ms=9, poll_idle_ms=9, rx_ring=64)
    driver.poller = LinkPoller(driver._uart)  # type: ignore[assignment,arg-type]
    assert UARTComm(driver, ROLE_INITIATOR, limits=transfer_limits(timeout=TIMEOUT_MS))._init_errno == code("E", "UART_RXBUF")


def _ring_floor(payload_size: int, timeout: int, poll_ms: int) -> int:
    # The floor from its own inputs: one framed frame, one poll interval's bytes, and what the
    # stop-and-wait peer sends while one config flush holds the loop, rounded up to a power of two.
    wire = 5 + payload_size
    per_poll = (115200 // 10) * (poll_ms + 5) // 1000
    flush = wire * (1 + _src_const("_FLASH_HOLD_MAX_MS") // (4 * timeout))
    floor = max(wire, per_poll, flush)
    size = 1
    while size < floor:
        size *= 2
    return size


def test_the_ring_floor_covers_a_config_flush() -> None:
    # At a long timeout the peer re-initiates nothing inside the hold, at a short one it does; either way
    # the floor itself constructs and the next smaller power of two is refused with the rxbuf code.
    for timeout, rises in ((1000, False), (100, True)):
        floor = _ring_floor(48, timeout, 2)
        assert (floor > _ring_floor(48, 10**6, 2)) is rises, (timeout, floor)
        for ring, expected in ((floor, 0), (floor // 2, code("E", "UART_RXBUF"))):
            bus = UART(0, tx_pin=0, rx_pin=1, baudrate=115200, poll_wait_ms=2, poll_idle_ms=2, rx_ring=ring)
            bus.poller = LinkPoller(bus._uart)  # type: ignore[assignment,arg-type]  # never a real select.poll()
            comm = UARTComm(bus, ROLE_INITIATOR, limits=transfer_limits(payload_size=48, timeout=timeout))
            assert comm._init_errno == expected, (timeout, ring)
            assert comm._min_rx_ring() == floor


def test_a_codec_that_failed_its_allocation_refuses_construction() -> None:
    # Every codec has a ready() to report a failed scratch allocation, and nothing read it.
    # A dead codec constructed cleanly, passed setup() and then failed every single write with
    # _ERR_UART_WRITE_FAILED - the link looking broken instead of the configuration being refused.
    dead = UART(0, tx_pin=0, rx_pin=1, poll_wait_ms=POLL_WAIT_MS, poll_idle_ms=POLL_WAIT_MS, rxbuf=1024, framing=FramingCOBS(-1))
    dead.poller = LinkPoller(dead._uart)  # type: ignore[assignment,arg-type]
    assert dead.framing.ready() is False
    comm = UARTComm(dead, ROLE_INITIATOR, limits=transfer_limits())
    assert comm._init_errno == code("E", "ALLOC")
    assert run(comm.setup()) is False
    live = UART(0, tx_pin=0, rx_pin=1, poll_wait_ms=POLL_WAIT_MS, poll_idle_ms=POLL_WAIT_MS, rxbuf=1024, framing=FramingCOBS(128))
    live.poller = LinkPoller(live._uart)  # type: ignore[assignment,arg-type]
    assert UARTComm(live, ROLE_INITIATOR, limits=transfer_limits())._init_errno == 0


def _src_const(name: str, path: str = _SRC) -> int:
    # The shipped value, read from the source: a const() is not a module attribute on MicroPython.
    with open(path) as f:
        for line in f:
            if line.startswith(name + " = const("):
                return int(line.split("const(", 1)[1].split(")", 1)[0], 0)
    raise AssertionError(name + " not found in " + path)


class _PrintRecorder:
    # Local stand-in for a shared print recorder: shadows print() inside asy_print_log only, so every
    # console line a logger emits is captured with its arguments; restore() removes the shadow.
    def __init__(self) -> None:
        self.lines: list[tuple[object, ...]] = []
        print_log_module.print = self  # type: ignore[attr-defined]

    def __call__(self, *args: object, **_kwargs: object) -> None:
        self.lines.append(args)

    def restore(self) -> None:
        del print_log_module.print  # type: ignore[attr-defined]

    def text(self) -> str:
        return "\n".join(" ".join(str(a) for a in line) for line in self.lines)


class _SleepRecorder:
    # Stands in for asyncio inside asy_uart_comm only: every sleep_ms() the module asks for is recorded,
    # then slept for at most cap_ms by the stand-in it replaced; restore() puts that one back.
    def __init__(self, cap_ms: int) -> None:
        self.cap_ms = cap_ms
        self.delays: list[int] = []
        self._inner = asy_uart_comm.asyncio
        asy_uart_comm.asyncio = self  # type: ignore[assignment]

    def __getattr__(self, name: str) -> object:
        return getattr(self._inner, name)

    def restore(self) -> None:
        asy_uart_comm.asyncio = self._inner

    def sleep_ms(self, ms: int) -> "Any":
        self.delays.append(ms)
        return self._inner.sleep_ms(min(ms, self.cap_ms))


def _on_poll_rounds(test: "Callable[[], None]") -> "Callable[[], None]":
    # Runs a live exchange's reply budgets on the UART modules' own poll rounds (SPECIFICATION.md J.7): a host
    # stall no longer expires a budget the exchange itself never used up.
    def on_the_clock() -> None:
        with PollRoundClock():
            test()

    return on_the_clock


def _poll_bus(poll_ms: int) -> UART:
    driver = UART(0, tx_pin=0, rx_pin=1, poll_wait_ms=poll_ms, poll_idle_ms=poll_ms, rxbuf=2048)
    driver.poller = LinkPoller(driver._uart)  # type: ignore[assignment,arg-type]  # never a real select.poll()
    return driver


def test_the_four_link_limits_arrive_as_one_transfer_limits() -> None:
    # The two wire parameters and the two receive limits travel as one object, unpacked onto the
    # attributes every reader of the frame size, the deadlines and the cap already uses.
    comm = UARTComm(_poll_bus(POLL_WAIT_MS), ROLE_INITIATOR, limits=TransferLimits(16, 300, 32, 64))
    assert (comm._payload_size, comm._timeout, comm._chunk_bytes, comm._max_transfer_bytes) == (16, 300, 32, 64)
    assert comm._init_errno == 0
    default = UARTComm(_poll_bus(POLL_WAIT_MS), ROLE_INITIATOR)
    assert (default._payload_size, default._timeout) == (48, 1000)  # agreed out of band with the peer (J.6)
    assert default._chunk_bytes == DEFAULT_LIMITS.chunk_bytes


def test_the_default_limits_are_the_source_defaults_and_refuse_no_train() -> None:
    # The default cap is the largest train the default frame can declare, so no train the link
    # carried before the cap existed is refused at the defaults.
    default = DEFAULT_LIMITS
    assert default == TransferLimits(
        _src_const("_DEFAULT_PAYLOAD_SIZE"),
        _src_const("_DEFAULT_TIMEOUT_MS"),
        _src_const("_DEFAULT_CHUNK_BYTES"),
        _src_const("_DEFAULT_MAX_TRANSFER_BYTES"),
    )
    assert default.max_transfer_bytes == (_src_const("_CHUNKS_MAX") - 1) * default.payload_size


def test_chunk_bytes_outside_its_range_is_refused() -> None:
    # chunk_bytes below one byte or a cap below one frame's payload cannot carry a train; the wire
    # parameters are checked first, so a refused payload_size still reports its own code.
    assert make_comm(chunk_bytes=0)._init_errno == code("E", "BAD_ARG")
    assert make_comm(max_transfer_bytes=PAYLOAD_SIZE - 1)._init_errno == code("E", "BAD_ARG")
    assert make_comm(max_transfer_bytes=PAYLOAD_SIZE)._init_errno == 0
    assert make_comm(chunk_bytes=1)._init_errno == 0
    assert make_comm(payload_size=0, chunk_bytes=0)._init_errno == code("E", "UART_PAYLOAD_SIZE")


def test_a_poll_rate_outside_one_to_nine_ms_is_refused() -> None:
    # J.6: a transaction polls at single-digit milliseconds; a two-digit poll_wait_ms spends most of
    # the reply budget between looks at the line, and zero would spin the loop.
    for bad in (0, 10):
        comm = UARTComm(_poll_bus(bad), ROLE_INITIATOR, limits=transfer_limits(timeout=TIMEOUT_MS))
        assert comm._init_errno == code("E", "UART_POLL_RATE"), bad
    for good in (1, 9):
        assert UARTComm(_poll_bus(good), ROLE_INITIATOR, limits=transfer_limits(timeout=TIMEOUT_MS))._init_errno == 0, good


def test_the_timeout_ceiling_keeps_every_deadline_a_valid_tick_delay() -> None:
    # The drain bound, 6 x timeout, is the longest deadline derived from timeout, and the backoff
    # cap 5 x timeout; both must stay below ticks_diff()'s 2**29 ms horizon (Part F.1).
    ceiling = 89_478_485
    comm = make_comm(timeout=ceiling)
    assert comm._init_errno == 0
    assert comm._resync_window_ms() * 4 < 2**29
    assert comm._backoff_max_ms < 2**29
    assert make_comm(timeout=ceiling + 1)._init_errno == code("E", "UART_TIMEOUT_PARAM")


def test_a_codec_below_one_frame_is_refused() -> None:
    # A delimited codec sized below one whole frame drops every frame it is handed, so the link
    # looks dead while the configuration is what is wrong.
    frame = 5 + PAYLOAD_SIZE + CRC16().length()
    for size, expected in ((frame - 1, code("E", "UART_CODEC_SIZE")), (frame, 0)):
        bus = UART(0, tx_pin=0, rx_pin=1, poll_wait_ms=POLL_WAIT_MS, poll_idle_ms=POLL_WAIT_MS, rxbuf=1024, crc=CRC16(), framing=FramingCOBS(size))
        bus.poller = LinkPoller(bus._uart)  # type: ignore[assignment,arg-type]  # never a real select.poll()
        assert UARTComm(bus, ROLE_INITIATOR, limits=transfer_limits())._init_errno == expected, size


@_on_poll_rounds
def test_a_pair_on_exact_sized_codecs_completes_a_get_and_a_set() -> None:
    # A guard: a codec sized at exactly one frame is the lowest size construction takes, and both directions
    # carry whole frames through it, with no CRC and with CRC16.
    for crc in (None, CRC16):
        frame = 5 + PAYLOAD_SIZE + (crc().length() if crc else 0)
        DMA.reset_registry()  # each link's ring holds two of the twelve channels
        buses = []
        for port, pins in ((0, (0, 1)), (1, (8, 9))):
            bus = UART(port, tx_pin=pins[0], rx_pin=pins[1], poll_wait_ms=POLL_WAIT_MS, poll_idle_ms=POLL_WAIT_MS, rxbuf=1024, crc=crc() if crc else None, framing=FramingCOBS(frame))
            fake_of(bus).rx_rate = float("inf")  # bytes land at once, not on the fake clock
            bus.poller = LinkPoller(fake_of(bus), mask=select.POLLOUT)  # type: ignore[assignment]  # never a real select.poll()
            buses.append(bus)
        UARTLink(fake_of(buses[0]), fake_of(buses[1]))
        initiator = UARTComm(buses[0], ROLE_INITIATOR, limits=transfer_limits(), name="UART_A")
        responder = UARTComm(buses[1], ROLE_RESPONDER, limits=transfer_limits(), callbacks=ResponderCallbacks(echo_get(b"answer"), accept_set(), None), name="UART_B")
        assert (initiator._init_errno, responder._init_errno) == (0, 0)

        async def scenario(initiator: UARTComm = initiator, responder: UARTComm = responder) -> "tuple[bytes | None, bool, ListenResult]":
            assert await initiator.setup() and await responder.setup()
            listener = asyncio.create_task(responder.uart_listen())
            answer = copied_out(await initiator.uart_get(1))
            await asyncio.wait_for(listener, _STEP_BOUND_S)
            listener = asyncio.create_task(responder.uart_listen())
            sent = await initiator.uart_set(2, bytes(range(3 * PAYLOAD_SIZE)))
            return answer, sent, await asyncio.wait_for(listener, _STEP_BOUND_S)

        answer, sent, result = run(scenario(), limit=_LISTENER_RUN_BOUND_S)
        assert answer == b"answer", crc
        assert sent is True, crc
        assert copied_out(result.payload) == bytes(range(3 * PAYLOAD_SIZE)), crc


def test_every_public_method_is_gated_before_setup() -> None:
    # Operating on unallocated state must return the method's own sentinel, never raise.
    comm = make_comm()
    assert run(comm.uart_set(1, b"a")) is False
    assert run(comm.uart_set_into(1, bytearray(2), 2)) is False
    assert run(comm.uart_set_stream(1, 4, lambda chunk, buf: 0)) is False
    assert run(comm.uart_get(1)) is None
    assert run(comm.uart_get_into(1, bytearray(4))) is None
    assert run(comm.uart_get_stream(1, lambda chunk, buf: True)) is None
    assert run(comm.uart_listen()) == ListenResult(None, None, None)


# C3 - logger injection, name, errno catalog


def test_logger_injection_uses_both_routes() -> None:
    own = make_comm(name="UART_X")
    assert own.name == "UART_X"
    assert own.pr.name == own.name  # registration keys on one and the history on the other
    shared = make_comm(logger=own.pr)
    assert shared.pr is own.pr  # the FRAMManager-style reach-through


def test_a_fram_backed_log_reads_back_through_a_second_logger() -> None:
    manager, chip = _make_fram_manager()
    comm = make_comm(name="UART_X", log=LogConfig(manager, 10, None))
    assert isinstance(comm.pr, PrintLogHistoryStore)
    assert run(comm.setup()) is True
    assert run(comm.uart_set(1, b"x"), limit=_RUN_BOUND_S) is False  # nothing is on the line: a silent peer
    assert persisted(comm)[-1] == _e("UART_NO_ACK"), persisted(comm)
    rebooted, _ = _make_fram_manager(chip)
    second = make_logger(LogConfig(rebooted, 10, None), "UART_X")
    run(second.setup())
    entry = run(second.get_log())["UART_X"]
    assert entry["ErrNum"][-1] == code("E", "UART_NO_ACK")
    assert entry["ErrType"][-1] == "E"


def test_get_error_counter_returns_the_shared_envelope() -> None:
    comm = make_comm(name="UART_X")
    log = run(comm.get_error_counter())
    assert "UART_X" in log
    entry = log["UART_X"]
    assert "ErrCount" in entry
    assert "ErrNum" in entry
    assert "ErrType" in entry


def test_reset_clears_the_history_and_the_streak_state() -> None:
    # A reset the caller expects to be total must not leave the escalate-once state behind.
    comm = make_comm(name="UART_X")
    run(comm._err(code("E", "UART_FRAME_INVALID"), "synthetic"))
    comm._valid_frames = 5
    comm._blind_resyncs = 2
    assert run(comm.get_error_counter())["UART_X"]["ErrCount"] > 0
    assert run(comm.reset_error_counter()) is True
    assert run(comm.get_error_counter())["UART_X"]["ErrCount"] == 0
    assert comm._blind_resyncs == 0


_DIAG_RESYNC_STREAK = 2  # mirrors asy_uart_comm.py's const: blind resyncs before the link diagnostic fires


def _noisy_resyncs(pair: Pair) -> None:
    # Resyncs that each drain a few bytes no frame validates from: the diagnostic's own input.
    async def scenario() -> None:
        async with pair.driver_a as device:
            for _ in range(_DIAG_RESYNC_STREAK):
                pair.fake_a.feed_rx(b"xyz")
                await pair.initiator._resync(device)

    run(scenario(), limit=_RUN_BOUND_S)


def test_reset_errors_keeps_the_valid_frame_count() -> None:
    # The valid-frame count is link evidence, not error history: a reset on a link that has worked
    # must not re-arm the unintelligible-link diagnostic; a fresh link still raises it (control).
    worked = run(build_pair(get_callback=echo_get(b""), set_callback=accept_set()))
    worked.initiator._note_valid_frame()
    worked.initiator._blind_resyncs = 1
    assert run(worked.initiator.reset_error_counter()) is True
    assert worked.initiator._valid_frames == 1
    assert worked.initiator._blind_resyncs == 0
    _noisy_resyncs(worked)
    assert _e("UART_LINK_UNINTELLIGIBLE") not in persisted(worked.initiator), persisted(worked.initiator)

    fresh = run(build_pair(get_callback=echo_get(b""), set_callback=accept_set()))
    _noisy_resyncs(fresh)
    assert _e("UART_LINK_UNINTELLIGIBLE") in persisted(fresh.initiator), persisted(fresh.initiator)


def test_a_repeated_identical_fault_spends_one_slot_and_counts_every_time() -> None:
    # A link failing once a second must not bury every other module's entries under one repeated
    # code: the central newest-entry rule (C.7.1) keeps one slot while ErrCount counts each fault.
    comm = make_comm(name="UART_X")
    for _ in range(21):
        run(comm._err(code("E", "UART_FRAME_INVALID"), "again"))
    assert persisted(comm) == [_e("UART_FRAME_INVALID")], persisted(comm)
    assert run(comm.get_error_counter())["UART_X"]["ErrCount"] == 21
    comm._note_valid_frame()  # the link recovers: nothing is logged for it
    assert run(comm.get_error_counter())["UART_X"]["ErrCount"] == 21
    run(comm._err(code("E", "UART_NO_ACK"), "a different fault"))
    assert persisted(comm) == [_e("UART_FRAME_INVALID"), _e("UART_NO_ACK")], persisted(comm)


def test_a_single_transient_fault_leaves_one_entry_not_a_pair() -> None:
    # A lone transient followed by a recovery costs one slot, never a matched pair.
    comm = make_comm(name="UART_X")
    run(comm._err(code("E", "UART_FRAME_INVALID"), "one-off"))
    comm._note_valid_frame()
    assert run(comm.get_error_counter())["UART_X"]["ErrCount"] == 1


def test_the_valid_frame_count_saturates() -> None:
    # Read only for its zero test (the blind-resync diagnostic), so it stops at the shared cap rather
    # than growing without bound; one more validated frame leaves it there.
    comm = make_comm(name="UART_X")
    comm._valid_frames = COUNTER_CAP
    comm._note_valid_frame()
    assert comm._valid_frames == COUNTER_CAP


@_on_poll_rounds
def test_the_blind_resync_streak_saturates() -> None:
    # Only the threshold test reads the streak, so it stops there; a further blind resync still
    # persists the diagnostic.
    pair = run(build_pair(get_callback=echo_get(b""), set_callback=accept_set()))
    comm = pair.initiator
    comm._blind_resyncs = _DIAG_RESYNC_STREAK

    async def blind_resync() -> None:
        async with pair.driver_a as device:
            pair.fake_a.feed_rx(b"\x01\x02\x03")  # bytes on the line, and no frame ever valid
            await comm._resync(device)

    run(blind_resync(), limit=_RUN_BOUND_S)
    assert comm._blind_resyncs == _DIAG_RESYNC_STREAK
    assert _e("UART_LINK_UNINTELLIGIBLE") in persisted(comm), persisted(comm)


@_on_poll_rounds
def test_bytes_a_failed_frame_read_dropped_count_toward_the_link_diagnostic() -> None:
    # A peer that only speaks when spoken to leaves nothing for the drain: its mismatched frames die
    # inside the failing read. The driver counts what that read dropped, and the resync reads the rise.
    pair = Pair(get_callback=echo_get(b""), set_callback=accept_set())
    pair.driver_a.discarded_bytes = 40  # dropped before setup: not this link's evidence
    assert run(pair.initiator.setup()) is True
    async def resyncs(dropped: int) -> None:
        async with pair.driver_a as device:
            for _ in range(_DIAG_RESYNC_STREAK):
                pair.driver_a.discarded_bytes += dropped
                await pair.initiator._resync(device)

    run(resyncs(0), limit=_RUN_BOUND_S)
    assert _e("UART_LINK_UNINTELLIGIBLE") not in persisted(pair.initiator), persisted(pair.initiator)
    run(resyncs(_FRAME - 1), limit=_RUN_BOUND_S)  # each a frame cut short and dropped inside the read
    assert _e("UART_LINK_UNINTELLIGIBLE") in persisted(pair.initiator), persisted(pair.initiator)


def test_the_discard_count_is_read_across_its_wrap() -> None:
    # discarded_bytes is a masked sequence, so the rise is the modular difference, never a negative.
    comm = make_comm()
    comm._discarded_seen = COUNTER_CAP - 3
    comm._uart.discarded_bytes = 5  # type: ignore[union-attr]  # 9 bytes later, across the wrap
    assert comm._take_discarded() == 9
    assert comm._take_discarded() == 0


def test_a_delimited_frame_of_the_wrong_length_counts_as_discarded() -> None:
    # A delimited codec hands back a frame that decoded cleanly but is not one frame long; the read
    # fails, and its bytes count toward the mismatch diagnostic like any other dropped frame (J.6).
    bus = UART(0, tx_pin=0, rx_pin=1, poll_wait_ms=POLL_WAIT_MS, poll_idle_ms=POLL_WAIT_MS, rxbuf=1024, framing=FramingCOBS(64))
    bus.poller = LinkPoller(bus._uart)  # type: ignore[assignment,arg-type]  # never a real select.poll()
    fake_of(bus).rx_rate = float("inf")  # fed bytes land at once, not on the fake clock
    comm = UARTComm(bus, ROLE_INITIATOR, limits=transfer_limits())
    assert run(comm.setup()) is True

    async def scenario() -> "tuple[bool, int]":
        short = bytearray(b"\x01\x02\x03\x04\x05")
        encoded = await FramingCOBS(64).encode_into(short, len(short))
        assert encoded is not None
        async with bus as device:
            fake_of(bus).feed_rx(bytes(encoded))
            got = await comm._read_frame(device, TIMEOUT_MS)
        return got, comm._take_discarded()

    got, dropped = run(scenario(), limit=_RUN_BOUND_S)
    assert got is False
    assert dropped >= 5


def test_a_repeatedly_declined_command_does_not_refill_the_history() -> None:
    # A declined command persists W56 each time; identical codes share one slot under the central rule
    # (C.7.1), whatever the id.
    def decline(cmd_id: int) -> "tuple[bool, None]":
        return False, None

    pair = run(build_pair(timeout=_SHORT_REPLY_TIMEOUT_MS, get_callback=decline, set_callback=accept_set()))
    for _ in range(5):
        assert run(pair.with_listener(pair.initiator.uart_get(0x42)), limit=_STEP_BOUND_S) is None
    assert persisted(pair.responder) == [_w("UART_CMD_DECLINED")], persisted(pair.responder)
    assert run(pair.responder.get_error_counter())[pair.responder.name]["ErrCount"] == 5
    assert run(pair.with_listener(pair.initiator.uart_get(0x43)), limit=_STEP_BOUND_S) is None
    assert persisted(pair.responder) == [_w("UART_CMD_DECLINED")], persisted(pair.responder)
    assert run(pair.responder.get_error_counter())[pair.responder.name]["ErrCount"] == 6


# C4 - frame buffers and scratch allocation


def test_tx_and_rx_buffers_are_separate() -> None:
    # One shared buffer means a received frame overwrites the frame being acknowledged.
    comm = make_comm()
    tx = comm._tx.get_buf()
    rx = comm._rx.get_buf()
    assert tx is not None
    assert rx is not None
    assert tx is not rx
    tx[0] = 0x11
    rx[0] = 0x22
    assert tx[0] == 0x11


def test_a_failed_buffer_allocation_degrades_every_entry_point() -> None:
    # RegionBuffer returns None rather than raising, and every consumer's first act is to
    # check for it.
    comm = make_comm()
    run(comm.setup())
    comm._tx._buf = None
    comm._rx._buf = None
    assert run(comm.uart_set(1, b"x")) is False
    assert run(comm.uart_get(1)) is None


def test_a_partially_failed_allocation_refuses_construction_outright() -> None:
    # _allocate() guards the three scratch buffers as one group, so a heap exhausted after the two
    # frame buffers returns zero-length ones. Checking only the TX frame let that object open the
    # gate: padding then shrank the TX buffer and the id write raised out of a never-raise module.
    real_allocate = UARTComm._allocate

    def starved(self: UARTComm) -> "Any":
        tx, rx, _ack, _zero, _cmd = real_allocate(self)
        return tx, rx, bytearray(0), bytearray(0), bytearray(0)

    UARTComm._allocate = starved  # type: ignore[method-assign]
    try:
        comm = make_comm()
    finally:
        UARTComm._allocate = real_allocate  # type: ignore[method-assign]
    assert comm._init_errno == code("E", "ALLOC")
    assert run(comm.setup()) is False, "the gate must stay shut, so nothing reaches the short buffers"
    assert run(comm.uart_set(1, b"x")) is False


def test_padding_is_zero_filled_from_the_preallocated_buffer() -> None:
    # Leaving the remainder unwritten transmits the previous frame's payload remnants - a
    # real data leak between unrelated messages.
    comm = make_comm()
    assert comm._prepare_tx(1, _CMD_SET, 2, 2, b"\xaa" * PAYLOAD_SIZE, PAYLOAD_SIZE) is True
    assert comm._prepare_tx(2, _CMD_SET, 2, 2, b"\xbb", 1) is True
    buf = comm._tx.get_buf()
    assert buf is not None
    assert buf[_PAYLOAD] == 0xBB
    assert bytes(buf[_PAYLOAD + 1 : _PAYLOAD + PAYLOAD_SIZE]) == bytes(PAYLOAD_SIZE - 1)


def test_payload_size_is_immutable_after_construction() -> None:
    comm = make_comm()
    assert not hasattr(comm, "set_payload_size")  # no setter exists


# C5/C6 - lifecycle, starters, listen loop


def test_starter_lists_match_the_role() -> None:
    # An initiator exposing a listen task would mean both ends initiate, and the protocol
    # has no arbitration for that.
    initiator = make_comm(role=ROLE_INITIATOR)
    responder = make_comm(role=ROLE_RESPONDER, get_callback=echo_get(b""), set_callback=accept_set())
    assert initiator.get_task_starters() == []
    assert responder.get_task_starters() == [responder.start_asy_listen]
    assert initiator.get_timer_starters() == []
    assert responder.get_timer_starters() == []  # no machine.Timer anywhere


def test_the_module_constructs_no_timer_at_all() -> None:
    # E3's whole point: a soft one-shot Timer callback can be silently dropped, and the flag it
    # would have set is then never set - the legacy module's permanent hang. Asserted against the
    # source because "there is no Timer" is a structural property, not an observable behaviour.
    with open(_SRC) as handle:
        code = [line.split("#")[0] for line in handle.read().split("\n")]
    assert not any("Timer(" in line or "machine" in line for line in code)


def test_setup_drains_a_partial_frame_left_over_from_before() -> None:
    # A peer mid-train, or one that outlived this side's reset, leaves bytes in the driver's
    # rxbuf. A boot-time drain is not a fault and must not be counted.
    pair = Pair(get_callback=echo_get(b"ok"), set_callback=accept_set())
    pair.fake_b.feed_rx(b"\x01\x02\x03")  # a partial frame, as if the peer was mid-transmission
    assert run(pair.responder.setup()) is True
    assert pair.fake_b.rx_queue == bytearray()
    # Not counted: an entry here would land in the FRAM history on every boot of a live link,
    # indistinguishable from a real fault - which is the one diagnostic a reboot does not erase.
    assert run(pair.responder.get_error_counter())["UART_B"]["ErrCount"] == 0


def test_a_ring_refused_at_setup_names_its_cause() -> None:
    # The driver says why it could not build the ring; setup() keeps the one code and puts the cause in
    # its message, so "no bus" and a refused DMA channel no longer read alike.
    comm = make_comm()
    comm._uart.rx_ring = 100  # type: ignore[union-attr]  # not a power of two: the ring cannot wrap
    comm.pr.set_level(1)
    recorder = _PrintRecorder()
    try:
        assert run(comm.setup()) is False
    finally:
        recorder.restore()
    assert persisted(comm) == [_e("UART_NO_BUS")], persisted(comm)
    assert "ring size" in recorder.text(), recorder.text()


def test_a_responder_without_callbacks_is_refused_at_construction() -> None:
    # Every GET and SET would be unanswerable, discovered only when the peer first asks.
    assert make_comm(role=ROLE_RESPONDER)._init_errno != 0
    assert make_comm(role=ROLE_RESPONDER, get_callback=echo_get(b""))._init_errno != 0


def test_the_listen_loop_backs_off_on_a_dead_link_and_resets_after_success() -> None:
    # A zero-delay retry is asy_captive_dns.py's measured recovery storm; a backoff that
    # never resets leaves a recovered link throttled at the cap forever.
    comm = make_comm(role=ROLE_RESPONDER, get_callback=echo_get(b""), set_callback=accept_set())
    assert comm._backoff_initial_ms == TIMEOUT_MS // 2
    assert comm._backoff_max_ms == TIMEOUT_MS * 5
    assert comm._backoff_max_ms > comm._backoff_initial_ms


def test_the_listen_loop_survives_a_raising_callback() -> None:
    # uart_listen() is contracted never to raise, but a contract is not an enforcement.
    def explode(cmd_id: int) -> "tuple[bool, Any]":
        raise ValueError("callback blew up")

    pair = Pair(get_callback=explode, set_callback=accept_set())
    assert run(pair.setup()) is True

    async def scenario() -> bool:
        loop = asyncio.create_task(pair.responder._listen_loop())
        got = await pair.initiator.uart_get(7)
        await asyncio.sleep_ms(_LOOP_SURVIVAL_WAIT_MS)
        alive = not loop.done()
        loop.cancel()
        return alive and got is None

    assert run(scenario(), limit=_STEP_BOUND_S) is True


# ===========================================================================
# Frame layer
# ===========================================================================


@_on_poll_rounds
def test_a_declined_get_does_not_back_off_the_next_answer() -> None:
    # After a validated command - answered, declined or aborted - the responder listens again at once,
    # so its backoff never outlasts the initiator's own recovery before it retries (J.5).
    def get_cb(cmd_id: int) -> "tuple[bool, bytes]":
        return cmd_id == 1, b"answer"

    pair = run(build_pair(get_callback=get_cb, set_callback=accept_set()), RUN_LIMIT_S)
    recorder = _SleepRecorder(_FLOOD_STEP_MS)
    initial = pair.responder._backoff_initial_ms

    async def scenario() -> "tuple[list[PieceBuffer | None], PieceBuffer | None]":
        task = pair.responder.start_asy_listen()
        try:
            declined: list[PieceBuffer | None] = []
            while len(declined) < 4:  # no await inside a comprehension on MicroPython
                declined.append(await pair.initiator.uart_get(9))
            return declined, await pair.initiator.uart_get(1)
        finally:
            task.cancel()

    try:
        declined, answer = run(scenario(), limit=_LISTENER_RUN_BOUND_S)
    finally:
        recorder.restore()
    assert declined == [None, None, None, None]
    assert copied_out(answer) == b"answer"
    assert [d for d in recorder.delays if d >= initial] == [], recorder.delays


@_on_poll_rounds
def test_a_dead_link_still_doubles_its_backoff() -> None:
    # A listen that returns no command kind - noise that never validates - backs off, doubling to its cap.
    pair = run(build_pair(get_callback=echo_get(b""), set_callback=accept_set()), RUN_LIMIT_S)
    recorder = _SleepRecorder(_FLOOD_STEP_MS)
    responder = pair.responder

    async def scenario() -> None:
        task = responder.start_asy_listen()
        fed = 0
        try:
            while len(recorder.delays) < 5:
                parked = responder._busy and not responder._in_resync and not pair.fake_b.rx_queue
                if parked and fed == len(recorder.delays):
                    pair.fake_b.feed_rx(b"\xff" * _FRAME)  # one frame-sized burst of noise per listen round
                    fed += 1
                await asyncio.sleep_ms(_FLOOD_STEP_MS)
        finally:
            task.cancel()

    try:
        run(scenario(), limit=_LISTENER_RUN_BOUND_S)
    finally:
        recorder.restore()
    initial = responder._backoff_initial_ms
    assert recorder.delays == [initial, initial * 2, initial * 4, initial * 8, responder._backoff_max_ms], recorder.delays


def test_the_backoff_stays_a_valid_tick_delay_at_the_timeout_ceiling() -> None:
    # At the largest timeout construction accepts, the doubling backoff still never asks sleep_ms()
    # for a delay outside ticks_add()'s 2**29 ms range (Part F.1).
    comm = make_comm(role=ROLE_RESPONDER, timeout=89_478_485, get_callback=echo_get(b""), set_callback=accept_set())
    assert run(comm.setup()) is True
    recorder = _SleepRecorder(0)

    async def no_command() -> ListenResult:
        return ListenResult(None, None, None)

    async def scenario() -> None:
        task = comm.start_asy_listen()
        while len(recorder.delays) < 8:
            await asyncio.sleep_ms(1)
        task.cancel()

    comm.uart_listen = no_command  # type: ignore[method-assign,assignment]
    try:
        run(scenario(), limit=_STEP_BOUND_S)
    finally:
        recorder.restore()
    expected = [min(comm._backoff_initial_ms * 2**i, comm._backoff_max_ms) for i in range(8)]
    assert recorder.delays[:8] == expected, recorder.delays
    assert expected[-1] == comm._backoff_max_ms
    assert all(d < 2**29 for d in recorder.delays)


def test_header_fields_land_at_their_documented_offsets() -> None:
    comm = make_comm()
    assert comm._prepare_tx(0x2A, _CMD_SET, 3, 2, b"\x01\x02", 2) is True
    buf = comm._tx.get_buf()
    assert buf is not None
    assert buf[_UID] == 0x2A
    assert buf[_CMD] == _CMD_SET
    assert buf[_SIZE] == 2
    assert buf[_CHUNKS] == 3
    assert buf[_CUR] == 2
    assert bytes(buf[_PAYLOAD : _PAYLOAD + 2]) == b"\x01\x02"


def test_out_of_range_header_fields_are_rejected_not_truncated() -> None:
    # struct.pack() truncates silently on this platform, so an out-of-range CHUNKS would
    # become a plausible wrong value instead of an error.
    comm = make_comm()
    assert comm._prepare_tx(0xFF, _CMD_SET, 2, 1, b"\x01", 1) is False  # UID 0xFF is never emitted
    assert comm._prepare_tx(1, 0x03, 2, 1, b"\x01", 1) is False  # not a real command
    assert comm._prepare_tx(1, _CMD_SET, 256, 1, b"\x01", 1) is False
    assert comm._prepare_tx(1, _CMD_SET, 2, 3, b"\x01", 1) is False  # cur_chunk beyond chunks


def test_a_payload_longer_than_the_region_is_rejected() -> None:
    comm = make_comm()
    assert comm._prepare_tx(1, _CMD_SET, 2, 2, b"x" * (PAYLOAD_SIZE + 1), PAYLOAD_SIZE + 1) is False


def test_size_always_matches_the_bytes_actually_copied() -> None:
    # A SIZE passed independently of the copy lets the peer read padding as payload.
    comm = make_comm()
    assert comm._prepare_tx(1, _CMD_SET, 2, 2, b"\x01\x02", 4) is False  # claims more than it has


def test_the_uid_cycle_covers_every_legal_value_and_never_0xff() -> None:
    # The 0xFE -> 0 wrap is a deliberate off-by-one barrier and keeps the UID space exactly
    # as large as the longest train, so no UID repeats inside one transfer.
    from asy_uart_comm import _next_uid

    seen = []
    uid = 0
    for _ in range(255):
        seen.append(uid)
        uid = _next_uid(uid)
    assert uid == 0  # wrapped exactly once
    assert sorted(seen) == list(range(255))
    assert 0xFF not in seen


def test_the_next_uid_prediction_is_correct_at_the_wrap_boundary() -> None:
    # A bare +1 mispredicts precisely here, once every 255 frames.
    from asy_uart_comm import _next_uid

    assert _next_uid(0xFD) == 0xFE
    assert _next_uid(0xFE) == 0


def build_frame(uid: int = 1, cmd: int = _CMD_SET, size: int = 1, chunks: int = 2, cur: int = 1, payload: bytes = b"\x07") -> bytearray:
    frame = bytearray(_FRAME)
    frame[_UID] = uid
    frame[_CMD] = cmd
    frame[_SIZE] = size
    frame[_CHUNKS] = chunks
    frame[_CUR] = cur
    frame[_PAYLOAD : _PAYLOAD + len(payload)] = payload
    return frame


def test_validation_accepts_every_legal_frame_shape() -> None:
    comm = make_comm()
    assert comm._validate(build_frame(), _CMD_SET, 1, None, None) == 0
    assert comm._validate(build_frame(cmd=_CMD_GET, chunks=1), _CMD_GET, 1, None, None) == 0
    assert comm._validate(build_frame(cmd=_CMD_ACK, size=0, chunks=1, cur=1), _CMD_ACK, 1, 1, 1) == 0
    full = build_frame(size=PAYLOAD_SIZE, chunks=3, cur=2, uid=2)
    assert comm._validate(full, _CMD_SET, 2, 3, 2) == 0


def test_a_multi_bit_command_is_rejected_rather_than_falling_through() -> None:
    # Today's bitmask test lets 0x03 and 0x06 pass validation and then match no dispatch
    # branch, so a malformed frame is silently mishandled instead of rejected.
    comm = make_comm()
    for bad in (0x03, 0x06, 0x00, 0x07):
        assert comm._validate(build_frame(cmd=bad), _CMD_SET, 1, None, None) != 0


def test_an_undefined_command_is_distinguished_from_a_valid_but_unexpected_one() -> None:
    # The exact-match membership test separates "not a command at all" from "a command, but not the
    # one due here" - only the second is the peer's contract violation, which gets its own
    # errno. A bitmask collapses the two, since 0x06 shares bits with both GET and SET.
    comm = make_comm()
    undefined = comm._validate(build_frame(cmd=0x06), _CMD_ACK, 1, 1, 1)
    wrong_kind = comm._validate(build_frame(cmd=_CMD_SET), _CMD_ACK, 1, 1, 1)
    assert undefined != 0
    assert wrong_kind != 0
    assert undefined != wrong_kind, "an undefined command and a wrong-kind one must log differently"


def test_a_changed_chunks_total_is_rejected() -> None:
    # Otherwise a peer truncates a transfer mid-train by re-declaring the total, and the
    # receiver reports success on partial data.
    comm = make_comm()
    assert comm._validate(build_frame(size=PAYLOAD_SIZE, chunks=2, cur=2, uid=2), _CMD_SET, 2, 3, 2) != 0


def test_a_stale_data_chunk_is_rejected_by_its_uid() -> None:
    # Invisible before - only ACKs were UID-checked.
    comm = make_comm()
    assert comm._validate(build_frame(size=PAYLOAD_SIZE, chunks=3, cur=2, uid=9), _CMD_SET, 2, 3, 2) != 0


def test_a_first_chunk_with_the_wrong_size_is_rejected() -> None:
    # Else the command id is silently read from a padding byte, usually 0.
    comm = make_comm()
    assert comm._validate(build_frame(size=0), _CMD_SET, 1, None, None) != 0
    assert comm._validate(build_frame(size=2), _CMD_SET, 1, None, None) != 0


def test_a_short_middle_chunk_is_rejected() -> None:
    # The payload is silently corrupted, and the length still adds up if a later chunk
    # compensates.
    comm = make_comm()
    assert comm._validate(build_frame(size=PAYLOAD_SIZE - 1, chunks=4, cur=2, uid=2), _CMD_SET, 2, 4, 2) != 0


def test_an_empty_chunk_is_legal_only_as_a_two_chunk_trains_last() -> None:
    # An empty middle chunk must not be misread as a genuinely empty payload.
    comm = make_comm()
    assert comm._validate(build_frame(size=0, chunks=2, cur=2, uid=2), _CMD_SET, 2, 2, 2) == 0
    assert comm._validate(build_frame(size=0, chunks=3, cur=3, uid=3), _CMD_SET, 3, 3, 3) != 0


def test_a_set_declaring_a_single_chunk_is_rejected() -> None:
    # No data chunk exists to acknowledge, and a conforming sender floors at 2.
    comm = make_comm()
    assert comm._validate(build_frame(chunks=1, cur=1), _CMD_SET, 1, None, None) != 0


def test_a_zero_chunk_train_is_rejected() -> None:
    comm = make_comm()
    assert comm._validate(build_frame(chunks=0, cur=1), _CMD_SET, 1, None, None) != 0


def test_a_get_declaring_any_chunk_count_but_one_is_refused() -> None:
    # J.4 defines a GET as a one-chunk train; a GET declaring more chunks was answered as though it
    # were one. Refused like any invalid frame, so no ACK is emitted for it.
    comm = make_comm()
    assert comm._validate(build_frame(cmd=_CMD_GET, chunks=1), _CMD_GET, 1, None, None) == 0
    for chunks in (0, 2, 3, 255):
        assert comm._validate(build_frame(cmd=_CMD_GET, chunks=chunks), _CMD_GET, 1, None, None) == code("E", "UART_FRAME_INVALID"), chunks


def test_a_malformed_ack_is_rejected() -> None:
    # A malformed ACK accepted as valid confirmation is worse than no ACK at all.
    comm = make_comm()
    assert comm._validate(build_frame(cmd=_CMD_ACK, size=1, chunks=1, cur=1), _CMD_ACK, 1, 1, 1) != 0
    assert comm._validate(build_frame(cmd=_CMD_ACK, size=0, chunks=2, cur=1), _CMD_ACK, 1, 1, 1) != 0
    assert comm._validate(build_frame(cmd=_CMD_ACK, size=0, chunks=1, cur=1, uid=9), _CMD_ACK, 1, 1, 1) != 0


def test_a_frame_of_the_wrong_kind_is_rejected_at_each_read_site() -> None:
    # A data frame where an ACK is due, or a GET arriving at an initiator, is the
    # peer's violation and must be visible as such.
    comm = make_comm()
    assert comm._validate(build_frame(cmd=_CMD_SET), _CMD_ACK, 1, 1, 1) != 0
    assert comm._validate(build_frame(cmd=_CMD_GET, chunks=1), _CMD_ACK, 1, 1, 1) != 0
    assert comm._validate(build_frame(cmd=_CMD_ACK, size=0, chunks=1), _CMD_SET, 1, None, None) != 0


def test_validation_never_raises_on_a_short_or_missing_buffer() -> None:
    # An exception escaping a module contracted never to raise.
    comm = make_comm()
    assert comm._validate(None, _CMD_SET, 1, None, None) != 0
    assert comm._validate(bytearray(2), _CMD_SET, 1, None, None) != 0
    assert comm._validate(bytearray(0), _CMD_SET, 1, None, None) != 0


def test_a_received_uid_of_0xff_is_rejected() -> None:
    # Out of contract - a conforming peer never sends it.
    comm = make_comm()
    assert comm._validate(build_frame(uid=0xFF), _CMD_SET, 1, None, None) != 0


def test_the_ack_frame_is_byte_exact() -> None:
    # D5: the protocol's only positive signal, so its shape is asserted rather than assumed.
    pair = Pair(get_callback=echo_get(b""), set_callback=accept_set())
    assert run(pair.setup()) is True

    async def scenario() -> None:
        async with pair.driver_b as device:
            await pair.responder._send_ack(device, 0x42)

    run(scenario())
    pair.link.settle()
    ack = pair.wire_from_responder()
    assert len(ack) == _FRAME
    assert ack[_UID] == 0x42
    assert ack[_CMD] == _CMD_ACK
    assert ack[_SIZE] == 0
    assert ack[_CHUNKS] == 1
    assert ack[_CUR] == 1
    assert bytes(ack[_PAYLOAD:]) == bytes(PAYLOAD_SIZE)


def test_an_ack_is_sent_even_while_the_write_hold_off_is_active() -> None:
    # If the hold-off gated ACKs too, both sides would back off simultaneously and the
    # link would stall with neither at fault.
    pair = Pair(get_callback=echo_get(b""), set_callback=accept_set())
    assert run(pair.setup()) is True
    pair.responder._hold_off_writes()

    async def scenario() -> bool:
        async with pair.driver_b as device:
            return await pair.responder._send_ack(device, 0x07)

    assert run(scenario()) is True
    pair.link.settle()
    assert len(pair.wire_from_responder()) == _FRAME


# ===========================================================================
# Exchange layer
# ===========================================================================


@_on_poll_rounds
def test_a_clean_write_round_trip_is_acknowledged() -> None:
    pair = run(build_pair(get_callback=echo_get(b""), set_callback=accept_set()))
    assert run(pair.with_listener(pair.initiator.uart_set(3, b"hi"))) is True


@_on_poll_rounds
def test_a_responder_that_never_finishes_its_rounds_fails_the_exchange() -> None:
    # A second listen round no frame will ever reach: the initiator's call succeeds, and the
    # stalled responder must fail the test instead of being cancelled out of sight.
    pair = run(build_pair(get_callback=echo_get(b""), set_callback=accept_set()))
    try:
        run(pair.with_listener(pair.initiator.uart_set(3, b"hi"), rounds=2))
    except AssertionError as exc:
        assert "did not finish" in str(exc), exc
    else:
        raise AssertionError("a stalled responder was cancelled silently")


@_on_poll_rounds
def test_a_stall_the_test_declares_is_not_a_failure() -> None:
    pair = run(build_pair(get_callback=echo_get(b""), set_callback=accept_set()))
    assert run(pair.with_listener(pair.initiator.uart_set(3, b"hi"), rounds=2, listener_may_stall=True)) is True


def test_a_missing_ack_bounds_the_wait_and_resyncs() -> None:
    # Without the bound the sender waits forever; with it, the failure is reported and both
    # sides quiesce so the next transfer starts on a clean frame boundary.
    pair = run(build_pair(get_callback=echo_get(b""), set_callback=accept_set()))
    pair.link.direction_from(pair.fake_b).silent = True  # the responder's ACKs never arrive
    assert run(pair.with_listener(pair.initiator.uart_set(3, b"hi")), limit=_SILENT_BOUND_S) is False
    assert pair.initiator._holdoff_active is True  # the hold-off that follows a resync


@_on_poll_rounds
def test_a_write_that_never_reaches_the_peer_fails_the_same_way() -> None:
    # Indistinguishable from a lost ACK at this layer, and the distinction is not invented.
    pair = run(build_pair(get_callback=echo_get(b""), set_callback=accept_set()))
    pair.link.direction_from(pair.fake_a).silent = True
    assert run(pair.with_listener(pair.initiator.uart_set(3, b"hi"), listener_may_stall=True), limit=_SILENT_BOUND_S) is False


def test_a_stale_ack_uid_is_rejected() -> None:
    # The UID space is exactly as large as the longest train, so no UID repeats inside one
    # transfer and a stale ACK can never be mistaken for the current one.
    comm = make_comm()
    ack = build_frame(cmd=_CMD_ACK, size=0, chunks=1, cur=1, uid=5)
    assert comm._validate(ack, _CMD_ACK, 1, 1, 5) == 0
    assert comm._validate(ack, _CMD_ACK, 1, 1, 6) != 0


@_on_poll_rounds
def test_a_lost_final_ack_reports_failure_while_the_receiver_reports_success() -> None:
    # J.9: the two-generals case, folded into failure (owner, 2026-09-11, `b131169`). There is no
    # retransmission to hang a third state on and a caller could not act differently anyway.
    def remember(cmd_id: int) -> "tuple[bool, int | None]":
        return True, None

    pair = Pair(get_callback=echo_get(b""), set_callback=remember)
    assert run(pair.setup()) is True
    # b"abc" is a two-chunk train, so the responder emits exactly two ACKs: one for the command
    # header and the deferred final one. Cutting the direction after the first is deterministic -
    # a watcher task racing the wire log would not be.
    pair.link.direction_from(pair.fake_b).truncate_after = _FRAME

    async def scenario() -> "tuple[bool, ListenResult]":
        listener = asyncio.create_task(pair.responder.uart_listen())
        sent = await pair.initiator.uart_set(3, b"abc")
        return sent, await asyncio.wait_for(listener, _STEP_BOUND_S)

    sent, result = run(scenario(), limit=_LISTENER_RUN_BOUND_S)
    assert sent is False  # the sender cannot know, so it reports failure
    assert result.cmd_id == 3  # the receiver genuinely has the data
    assert copied_out(result.payload) == b"abc"


def test_the_write_hold_off_uses_a_deadline_and_expires() -> None:
    # E3: a deadline cannot be dropped the way a soft one-shot Timer callback can.
    comm = make_comm()
    run(comm.setup())
    # Sampled into locals and asserted together: asserting the same attribute's identity twice in
    # sequence narrows it to a literal and makes the rest of the test statically unreachable.
    before = comm._holdoff_active
    comm._hold_off_writes()
    during = comm._holdoff_active
    run(asyncio.wait_for(comm._await_write_gate(), _SHORT_BOUND_S))
    after = comm._holdoff_active
    assert (before, during, after) == (False, True, False)  # expired by time, not by a callback


def test_the_hold_off_window_derives_from_timeout() -> None:
    # Changelog A4: both constants are 1.5 x timeout and neither is hardcoded, because a peer
    # draining for less transmits into the other's drain window.
    assert make_comm(timeout=100)._resync_window_ms() == 150
    assert make_comm(timeout=400)._resync_window_ms() == 600


def test_the_hold_off_deadline_survives_the_ticks_rollover() -> None:
    # Armed 5 ms before rp2's 2**30 ms wrap, the deadline lands past it: still held one ms before it, released one
    # ms after. A raw subtraction misreads exactly this, once per uptime period, and waiting never reaches it.
    comm = make_comm()
    clock = Ticks30Time(TICKS_PERIOD - 5)
    asy_uart_comm.time = clock  # type: ignore[assignment]

    async def scenario() -> "tuple[bool, bool, bool]":
        comm._hold_off_writes()
        window = comm._resync_window_ms()
        assert clock.now + window > TICKS_PERIOD
        gate = asyncio.create_task(comm._await_write_gate())
        await asyncio.sleep_ms(5)  # the gate's first look, still before the wrap
        held_before_the_wrap = not gate.done()
        clock.advance(window - 1)
        await asyncio.sleep_ms(5)  # several of the gate's rounds, each sleeping the 1 ms left
        held_past_it = not gate.done()
        clock.advance(2)
        await asyncio.wait_for(gate, _PAST_DEADLINE_BOUND_S)
        return held_before_the_wrap, held_past_it, comm._holdoff_active

    try:
        assert run(scenario()) == (True, True, False)
    finally:
        asy_uart_comm.time = time


def _hold_off_after(comm: UARTComm, clock: Ticks30Time, steps: "list[int]") -> "list[bool]":
    # Arms the hold-off, then for each step advances the fake clock and reports whether the gate is
    # still held once it has had time for a few of its own rounds (each sleeps at most 20 ms).
    async def scenario() -> "list[bool]":
        comm._hold_off_writes()
        gate = asyncio.create_task(comm._await_write_gate())
        held = []
        for step in steps:
            clock.advance(step)
            await asyncio.sleep_ms(_HOLD_OFF_LOOK_MS)
            held.append(not gate.done())
        gate.cancel()
        return held

    asy_uart_comm.time = clock  # type: ignore[assignment]
    try:
        return run(scenario())
    finally:
        asy_uart_comm.time = time


def test_a_hold_off_aged_past_the_tick_horizon_expires() -> None:
    # Idle for more than 2**29 ms, the stored deadline reads as days ahead; one more than a window
    # away cannot be a deadline this side set, so it has expired.
    comm = make_comm()
    clock = Ticks30Time(1000)
    assert _hold_off_after(comm, clock, [2**29 + 1000]) == [False]
    assert comm._holdoff_active is False


def test_the_aliased_band_holds_at_most_one_window() -> None:
    # A guard: in the last window of the 2**30 period the aged deadline reads as one inside the window,
    # so it holds, but never longer than the one window a normal hold-off costs.
    comm = make_comm()
    window = comm._resync_window_ms()
    clock = Ticks30Time(1000)
    assert _hold_off_after(comm, clock, [TICKS_PERIOD + window // 2, window // 2 - 1, 2]) == [True, True, False]


def test_an_unaged_hold_off_releases_at_its_window() -> None:
    # A guard: the ordinary hold-off is unchanged, held one ms short of its window and released after it.
    comm = make_comm()
    window = comm._resync_window_ms()
    assert _hold_off_after(comm, Ticks30Time(1000), [window - 1, 2]) == [True, False]


@_on_poll_rounds
def test_listening_clears_the_hold_off() -> None:
    # If the peer is requesting something it is definitely up again - the one documented
    # reset besides the deadline itself.
    pair = run(build_pair(get_callback=echo_get(b"v"), set_callback=accept_set()))
    pair.responder._hold_off_writes()
    assert run(pair.with_listener(pair.initiator.uart_get(9))) is not None
    assert pair.responder._holdoff_active is False


@_on_poll_rounds
def test_a_frame_read_failing_on_a_receive_error_persists_the_overrun_warning() -> None:
    # The frame fails under its own code, and the overrun that caused it is named beside it, so a
    # silent peer and a receive overrun no longer read alike.
    pair = run(build_pair(timeout=_SHORT_REPLY_TIMEOUT_MS, get_callback=echo_get(b""), set_callback=accept_set()))
    pair.fake_a.plant_rx_error(0x08)  # UARTRSR OE: the ACK this side waits for is lost to an overrun
    assert run(pair.initiator.uart_set(1, b"x"), limit=_STEP_BOUND_S) is False
    assert persisted(pair.initiator) == [_w("UART_RX_OVERRUN"), _e("UART_NO_ACK")], persisted(pair.initiator)


@_on_poll_rounds
def test_a_transmit_that_never_drains_fails_within_the_link_timeout() -> None:
    # A stalled transmitter used to hold the write forever; the write now gives up at the link's
    # reply timeout and fails like any other write, so the link resyncs and recovers.
    pair = run(build_pair(timeout=_SHORT_REPLY_TIMEOUT_MS, get_callback=echo_get(b""), set_callback=accept_set()))
    pair.fake_a.tx_pending_rounds = 1 << 30  # txdone() never answers True
    assert run(pair.initiator.uart_set(1, b"x"), limit=_STEP_BOUND_S) is False
    assert persisted(pair.initiator)[0] == _e("UART_WRITE_FAILED"), persisted(pair.initiator)


def test_the_drain_ends_once_the_line_is_quiet() -> None:
    pair = run(build_pair(get_callback=echo_get(b""), set_callback=accept_set()))
    pair.fake_a.feed_rx(b"garbage bytes")

    async def scenario() -> int:
        async with pair.driver_a as device:
            return await pair.initiator._drain(device)

    assert run(scenario(), limit=_STEP_BOUND_S) == len(b"garbage bytes")


def test_the_drain_is_bounded_against_a_peer_that_never_stops() -> None:
    # The legacy module's unbounded `while True` never sees quiet against a stuck sender.
    pair = run(build_pair(get_callback=echo_get(b""), set_callback=accept_set()))

    async def flood() -> None:
        while True:
            pair.fake_a.feed_rx(b"\xff" * 32)
            await asyncio.sleep_ms(_FLOOD_STEP_MS)

    async def scenario() -> bool:
        flooder = asyncio.create_task(flood())
        try:
            async with pair.driver_a as device:
                await asyncio.wait_for(pair.initiator._drain(device), _STEP_BOUND_S)
        finally:
            flooder.cancel()
        return True

    assert run(scenario(), limit=_RUN_BOUND_S) is True  # terminates at the bound instead of looping forever


def test_a_drain_that_hits_its_bound_persists_the_drain_warning() -> None:
    # W54 separates a babbling or misconfigured peer from ordinary line noise; a quiet resync only prints.
    pair = run(build_pair(get_callback=echo_get(b""), set_callback=accept_set()))

    async def flood() -> None:
        while True:
            pair.fake_a.feed_rx(b"\xff" * 32)
            await asyncio.sleep_ms(_FLOOD_STEP_MS)

    async def scenario() -> bool:
        flooder = asyncio.create_task(flood())
        try:
            async with pair.driver_a as device:
                await asyncio.wait_for(pair.initiator._resync(device), _STEP_BOUND_S)
        finally:
            flooder.cancel()
        return True

    assert run(scenario(), limit=_RUN_BOUND_S) is True
    assert persisted(pair.initiator) == [_w("UART_DRAIN_BOUND")], persisted(pair.initiator)


def test_a_quiet_resync_persists_nothing() -> None:
    # The other side of the choice above: a routine resync is a console line only.
    pair = run(build_pair(get_callback=echo_get(b""), set_callback=accept_set()))

    async def scenario() -> None:
        async with pair.driver_a as device:
            await pair.initiator._resync(device)

    run(scenario(), limit=_STEP_BOUND_S)
    assert persisted(pair.initiator) == [], persisted(pair.initiator)
    assert pair.initiator._holdoff_active is True  # the resync itself still ran


def test_one_fault_on_a_quiet_line_adds_one_entry() -> None:
    # The fault persists its errno; the resync it performs prints only.
    pair = run(build_pair(get_callback=echo_get(b""), set_callback=accept_set()))
    pair.link.direction_from(pair.fake_b).silent = True
    assert run(pair.initiator.uart_set(1, b"x"), limit=_RUN_BOUND_S) is False
    assert persisted(pair.initiator) == [_e("UART_NO_ACK")], persisted(pair.initiator)
    assert run(pair.initiator.get_error_counter())[pair.initiator.name]["ErrCount"] == 1
    assert pair.initiator._holdoff_active is True  # the resync ran


def test_one_fault_hitting_the_drain_bound_adds_the_errno_and_w54() -> None:
    # Two conditions, two entries: the fault's errno, then the drain bound its resync reached.
    pair = run(build_pair(get_callback=echo_get(b""), set_callback=accept_set()))

    async def flood() -> None:
        while True:
            pair.fake_a.feed_rx(b"\xff" * 32)
            await asyncio.sleep_ms(_FLOOD_STEP_MS)

    async def scenario() -> None:
        flooder = asyncio.create_task(flood())
        try:
            async with pair.driver_a as device:
                await asyncio.wait_for(pair.initiator._fault(device, code("E", "UART_NO_ACK"), "synthetic"), _STEP_BOUND_S)
        finally:
            flooder.cancel()

    run(scenario(), limit=_RUN_BOUND_S)
    assert persisted(pair.initiator) == [_e("UART_NO_ACK"), _w("UART_DRAIN_BOUND")], persisted(pair.initiator)
    assert run(pair.initiator.get_error_counter())[pair.initiator.name]["ErrCount"] == 2


def test_a_boot_drain_that_hits_its_bound_persists_nothing() -> None:
    # setup()'s drain is deliberately not a fault and not counted, but it shares _drain() - and while
    # the bound logged itself, a babbling peer put an entry in FRAM on every single boot.
    comm = make_comm()

    async def flood() -> None:
        while True:
            comm._uart._uart.feed_rx(b"\xff" * 32)  # type: ignore[union-attr]
            await asyncio.sleep_ms(_FLOOD_STEP_MS)

    async def scenario() -> bool:
        flooder = asyncio.create_task(flood())
        try:
            await asyncio.wait_for(comm.setup(), _STEP_BOUND_S)
        finally:
            flooder.cancel()
        return True

    assert run(scenario(), limit=_RUN_BOUND_S) is True
    assert comm._drain_bound_hit is True  # the bound really was reached, so the check is not vacuous
    assert persisted(comm) == [], persisted(comm)


def test_a_flood_that_laps_the_ring_drains_to_its_bound_not_as_quiet() -> None:
    # A peer sending faster than the drain reads laps the receive ring, and the read reports that overrun as a
    # failure: the drain must keep going (the line is anything but quiet) until its bound, then log W54.
    pair = run(build_pair(get_callback=echo_get(b""), set_callback=accept_set()))

    async def flood() -> None:
        while True:
            pair.fake_a.feed_rx(b"\xff" * 600)  # more than the 512-byte ring holds, every round
            await asyncio.sleep_ms(_FLOOD_STEP_MS)

    async def scenario() -> None:
        flooder = asyncio.create_task(flood())
        try:
            async with pair.driver_a as device:
                await asyncio.wait_for(pair.initiator._resync(device), _STEP_BOUND_S)
        finally:
            flooder.cancel()

    run(scenario(), limit=_RUN_BOUND_S)
    assert pair.driver_a.rx_overruns > 0  # the case under test really happened
    assert pair.initiator._drain_bound_hit is True
    assert persisted(pair.initiator) == [_w("UART_DRAIN_BOUND")], persisted(pair.initiator)


def test_the_drain_reads_into_the_scratch_buffer() -> None:
    # read() would allocate per round, on exactly the degraded link where the heap is most
    # fragmented. Asserted on the driver calls the drain makes.
    pair = run(build_pair(get_callback=echo_get(b""), set_callback=accept_set()))
    pair.fake_a.feed_rx(b"xyz")
    calls: list[str] = []
    driver = pair.driver_a
    real_read, real_readinto = driver.read, driver.readinto

    async def spy_read(nbytes: "int | None" = None, timeout_ms: int = -1) -> "bytes | None":
        calls.append("read")
        return await real_read(nbytes, timeout_ms)

    async def spy_readinto(buf: bytearray, nbytes: "int | None" = None, timeout_ms: int = -1) -> "int | None":
        calls.append("readinto")
        return await real_readinto(buf, nbytes, timeout_ms)

    driver.read = spy_read  # type: ignore[method-assign]
    driver.readinto = spy_readinto  # type: ignore[method-assign]

    async def scenario() -> int:
        async with driver as device:
            return await pair.initiator._drain(device)

    assert run(scenario(), limit=_STEP_BOUND_S) == 3
    assert "read" not in calls
    assert "readinto" in calls


def test_a_resync_is_not_re_entrant() -> None:
    # A fault during a resync continues the drain, it never starts a second one.
    pair = run(build_pair(get_callback=echo_get(b""), set_callback=accept_set()))
    pair.initiator._in_resync = True

    async def scenario() -> None:
        async with pair.driver_a as device:
            await pair.initiator._resync(device)

    run(scenario(), limit=_STEP_BOUND_S)
    assert pair.initiator._holdoff_active is False  # the nested call did nothing at all


def test_every_public_entry_point_converges_on_its_own_sentinel() -> None:
    # A caller must never believe a failed transfer succeeded.
    pair = run(build_pair(get_callback=echo_get(b"v"), set_callback=accept_set()))
    pair.link.direction_from(pair.fake_b).silent = True  # nothing ever answers
    assert run(pair.initiator.uart_set(1, b"x"), limit=_SILENT_BOUND_S) is False
    assert run(pair.initiator.uart_get(1), limit=_SILENT_BOUND_S) is None
    assert run(pair.initiator.uart_get_into(1, bytearray(16)), limit=_SILENT_BOUND_S) is None
    assert run(pair.initiator.uart_set_into(1, bytearray(4), 4), limit=_SILENT_BOUND_S) is False


def test_clear_cancels_first_and_drains_exactly_once() -> None:
    # Taking the lock before attempting the cancel deadlocks against the very listener
    # this exists to free, and two drains double the recovery time for no benefit.
    pair = run(build_pair(get_callback=echo_get(b""), set_callback=accept_set()))
    drains = []
    original = pair.responder._drain

    async def counting_drain(device: UART, first_ms: int | None = None) -> int:
        drains.append(1)
        return await original(device, first_ms)

    pair.responder._drain = counting_drain  # type: ignore[method-assign]

    async def scenario() -> None:
        listener = asyncio.create_task(pair.responder.uart_listen())
        await asyncio.sleep_ms(_LISTENER_PARK_MS)  # let it park in the unbounded read, holding the bus lock
        await asyncio.wait_for(pair.responder.clear(), _STEP_BOUND_S)
        listener.cancel()

    run(scenario(), limit=_RUN_BOUND_S)
    assert len(drains) == 1


def test_clear_with_nothing_in_flight_takes_the_lock_and_drains() -> None:
    pair = run(build_pair(get_callback=echo_get(b""), set_callback=accept_set()))
    pair.fake_a.feed_rx(b"leftovers")
    run(pair.initiator.clear(), limit=_STEP_BOUND_S)
    assert pair.fake_a.rx_queue == bytearray()


def test_only_a_rise_in_the_drivers_unacked_count_is_reported() -> None:
    # cancel_unacknowledged is cumulative, and clear() read it as a flag: once any holder had ever
    # wedged, every later cancel - healthy ones included - persisted W55 again, which is the
    # bounded-history churn Part C.7.1 exists to prevent, on a link that had already recovered.
    pair = Pair()
    run(pair.setup())
    bus = pair.initiator._uart
    assert bus is not None

    async def hold(ms: int) -> None:
        async with bus:  # the cancel is acknowledged on leaving the locked region, never before
            await asyncio.sleep_ms(ms)

    async def scenario(hold_ms: int) -> None:
        holder = asyncio.create_task(hold(hold_ms))
        await asyncio.sleep_ms(_INSIDE_LOCK_MS)
        await pair.initiator.clear()
        await holder

    run(scenario(_PAST_CANCEL_ACK_HOLD_MS), limit=_RUN_BOUND_S)  # past the driver's own 1000ms acknowledgement bound
    assert bus.cancel_unacknowledged == 1
    assert persisted(pair.initiator) == [_w("UART_CANCEL_UNACKED")]
    run(scenario(_PROMPT_HOLD_MS), limit=_RUN_BOUND_S)  # a holder that acknowledges promptly: nothing new to report
    assert bus.cancel_unacknowledged == 1
    assert persisted(pair.initiator) == [_w("UART_CANCEL_UNACKED")]


# ===========================================================================
# Transaction layer
# ===========================================================================


@_on_poll_rounds
def test_a_payload_less_command_still_produces_two_chunks() -> None:
    # F1: even a payload-less command has one data chunk to acknowledge, so it is confirmed end to
    # end rather than merely heard.
    pair = run(build_pair(get_callback=echo_get(b""), set_callback=accept_set()))
    assert run(pair.with_listener(pair.initiator.uart_set(5, None))) is True
    sent = frames(pair.wire_from_initiator(), _FRAME)
    assert len(sent) == 2
    assert sent[0][_CHUNKS] == 2
    assert sent[0][_SIZE] == 1
    assert sent[0][_PAYLOAD] == 5
    assert sent[1][_SIZE] == 0


@_on_poll_rounds
def test_the_wire_log_of_a_multi_chunk_set_is_byte_exact() -> None:
    payload = bytes(range(PAYLOAD_SIZE + 3))  # spans two data chunks
    pair = run(build_pair(get_callback=echo_get(b""), set_callback=accept_set()))
    assert run(pair.with_listener(pair.initiator.uart_set(0x11, payload))) is True
    sent = frames(pair.wire_from_initiator(), _FRAME)
    assert len(sent) == 3
    assert [f[_CHUNKS] for f in sent] == [3, 3, 3]  # constant across the whole train
    assert [f[_CUR] for f in sent] == [1, 2, 3]
    assert [f[_SIZE] for f in sent] == [1, PAYLOAD_SIZE, 3]
    assert sent[1][_PAYLOAD : _PAYLOAD + PAYLOAD_SIZE] == payload[:PAYLOAD_SIZE]
    assert sent[2][_PAYLOAD : _PAYLOAD + 3] == payload[PAYLOAD_SIZE:]
    uids = [f[_UID] for f in sent]
    assert len(set(uids)) == 3  # a fresh UID per frame, none repeated within the train


def test_chunk_counts_at_the_payload_size_boundaries() -> None:
    comm = make_comm()
    assert comm._chunk_count(0) == 2
    assert comm._chunk_count(PAYLOAD_SIZE - 1) == 2
    assert comm._chunk_count(PAYLOAD_SIZE) == 2
    assert comm._chunk_count(PAYLOAD_SIZE + 1) == 3
    assert comm._chunk_count(254 * PAYLOAD_SIZE) == 255  # the largest legal train
    assert comm._chunk_count(254 * PAYLOAD_SIZE + 1) is None  # rejected, never mis-declared


def test_an_oversize_payload_is_rejected_before_the_first_frame() -> None:
    # Never partially sent - a half-delivered train is worse than a refused one.
    pair = run(build_pair(get_callback=echo_get(b""), set_callback=accept_set()))
    too_big = bytes(254 * PAYLOAD_SIZE + 1)
    assert run(pair.initiator.uart_set(1, too_big), limit=_SILENT_BOUND_S) is False
    assert pair.wire_from_initiator() == b""


def test_a_missing_ack_at_each_train_position_aborts_and_resyncs() -> None:
    # Nothing is re-sent - that is the design, not a gap. A PAYLOAD_SIZE + 1 payload is a
    # three-chunk train, so the responder emits three ACKs (header, middle chunk, deferred final);
    # each is dropped in turn by cutting its direction after exactly that many whole frames.
    for kept_acks in (0, 1, 2):
        pair = run(build_pair(get_callback=echo_get(b""), set_callback=accept_set()))
        pair.link.direction_from(pair.fake_b).truncate_after = kept_acks * _FRAME
        result = run(pair.with_listener(pair.initiator.uart_set(1, bytes(PAYLOAD_SIZE + 1))), limit=_LISTENER_RUN_BOUND_S)
        assert result is False, f"a train losing the ACK after {kept_acks} should fail"
        assert pair.initiator._holdoff_active is True, "every abort quiesces the link"


@_on_poll_rounds
def test_a_multi_chunk_payload_arrives_byte_identical() -> None:
    got: list[Any] = []

    def remember(cmd_id: int) -> "tuple[bool, int | None]":
        return True, None

    payload = bytes((i * 7) & 0xFF for i in range(PAYLOAD_SIZE * 3 + 2))
    pair = Pair(get_callback=echo_get(b""), set_callback=remember)
    assert run(pair.setup()) is True

    async def scenario() -> ListenResult:
        listener = asyncio.create_task(pair.responder.uart_listen())
        sent = await pair.initiator.uart_set(0x21, payload)
        result = await asyncio.wait_for(listener, _SHORT_BOUND_S)
        got.append(sent)
        return result

    result = run(scenario(), limit=_RUN_BOUND_S)
    assert got == [True]
    assert result.cmd_id == 0x21
    assert copied_out(result.payload) == payload


@_on_poll_rounds
def test_all_three_expected_size_modes() -> None:
    # F2: don't care, exactly empty, exactly N - enforced incrementally and finally.
    for exp, payload, ok in ((None, b"abc", True), (0, b"", True), (3, b"abc", True), (4, b"abc", False), (0, b"abc", False)):
        pair = Pair(get_callback=echo_get(b""), set_callback=accept_set(exp))
        assert run(pair.setup()) is True

        async def scenario(data: bytes = payload, link: Pair = pair) -> bool:
            listener = asyncio.create_task(link.responder.uart_listen())
            sent = await link.initiator.uart_set(1, data)
            await asyncio.wait_for(listener, _LISTENER_SHORT_BOUND_S)
            return sent

        assert run(scenario(), limit=_LISTENER_RUN_BOUND_S) is ok, f"exp_size={exp} payload={payload!r}"


@_on_poll_rounds
def test_an_empty_payload_is_a_distinct_outcome_from_failure() -> None:
    # J.9: None means failure and a zero-length result means genuinely empty; if the
    # two ever collapse, a caller cannot tell an empty answer from a dead link.
    pair = run(build_pair(get_callback=echo_get(b""), set_callback=accept_set()))
    answer = run(pair.with_listener(pair.initiator.uart_get(4)))
    assert answer is not None
    assert len(answer) == 0


def test_an_expected_size_the_train_could_never_deliver_is_rejected_early() -> None:
    # The transfer is doomed the moment CHUNKS is known, so it does not run to completion
    # first.
    comm = make_comm()
    assert comm._dest_size(2, PAYLOAD_SIZE) == PAYLOAD_SIZE
    assert comm._dest_size(2, PAYLOAD_SIZE + 1) is None
    assert comm._dest_size(3, -1) == 2 * PAYLOAD_SIZE


@_on_poll_rounds
def test_a_get_round_trip_returns_the_answer() -> None:
    payload = bytes(range(PAYLOAD_SIZE + 2))
    pair = run(build_pair(get_callback=echo_get(payload), set_callback=accept_set()))
    answer = run(pair.with_listener(pair.initiator.uart_get(0x33)))
    assert answer is not None
    assert copied_out(answer) == payload


def test_the_get_answer_echoes_the_requested_command_id() -> None:
    # Otherwise the initiator accepts an answer to a question it never asked.
    pair = run(build_pair(get_callback=echo_get(b"v"), set_callback=accept_set()))
    run(pair.with_listener(pair.initiator.uart_get(0x44)))
    answer = frames(pair.wire_from_responder(), _FRAME)
    headers = [f for f in answer if f[_CMD] == _CMD_SET and f[_CUR] == 1]
    assert headers
    assert headers[0][_PAYLOAD] == 0x44


def test_a_rejected_get_callback_reports_a_distinct_outcome() -> None:
    # Withhold the answer, resync, and tell the responder's own caller which command was
    # refused - not silently nothing.
    def refuse(cmd_id: int) -> "tuple[bool, Any]":
        return False, None

    pair = Pair(get_callback=refuse, set_callback=accept_set())
    assert run(pair.setup()) is True

    async def scenario() -> "tuple[PieceBuffer | None, ListenResult]":
        listener = asyncio.create_task(pair.responder.uart_listen())
        answer = await pair.initiator.uart_get(0x55)
        return answer, await asyncio.wait_for(listener, _STEP_BOUND_S)

    answer, result = run(scenario(), limit=_LISTENER_RUN_BOUND_S)
    assert answer is None
    assert result.cmd_id is None
    assert result.cmd == _CMD_GET  # which kind was refused is still reported


def test_uart_listen_returns_the_namedtuple_on_every_path() -> None:
    # A bare None makes a caller's three-way unpack raise inside a module contracted never
    # to raise.
    pair = run(build_pair(get_callback=echo_get(b""), set_callback=accept_set()))
    refused = run(pair.initiator.uart_listen())  # wrong role
    assert isinstance(refused, tuple)
    assert len(refused) == 3
    assert refused.cmd_id is None


@_on_poll_rounds
def test_both_sync_and_async_callbacks_work() -> None:
    async def async_get(cmd_id: int) -> "tuple[bool, bytes]":
        await asyncio.sleep_ms(_ASYNC_CALLBACK_YIELD_MS)
        return True, b"async"

    pair = run(build_pair(get_callback=async_get, set_callback=accept_set()))
    answer = run(pair.with_listener(pair.initiator.uart_get(1)))
    assert answer is not None
    assert copied_out(answer) == b"async"


def test_a_callback_returning_the_wrong_shape_is_treated_like_a_raise() -> None:
    # A TypeError on unpacking is the same escape by another route.
    comm = make_comm()
    assert comm._pair(None) is None
    assert comm._pair(42) is None
    assert comm._pair((True,)) is None
    assert comm._pair((True, b"x", 3)) is None
    assert comm._pair(("yes", b"x")) is None  # a truthy non-bool is not a validity flag
    assert comm._pair((True, b"x")) == (True, b"x")


def test_a_callback_returning_a_non_buffer_payload_is_rejected() -> None:
    # The callback-return guard again: the payload's type is part of the return shape, so a str here must not reach
    # the frame builder.
    def wrong_type(cmd_id: int) -> "tuple[bool, Any]":
        return True, "not a buffer"

    pair = Pair(get_callback=wrong_type, set_callback=accept_set())
    assert run(pair.setup()) is True

    async def scenario() -> "PieceBuffer | None":
        listener = asyncio.create_task(pair.responder.uart_listen())
        answer = await pair.initiator.uart_get(1)
        await asyncio.wait_for(listener, _STEP_BOUND_S)
        return answer

    assert run(scenario(), limit=_LISTENER_RUN_BOUND_S) is None


def test_a_callback_asking_for_an_impossible_size_is_rejected() -> None:
    # Otherwise it propagates into the sizing and allocates nonsense.
    for bad in (-5, 255 * PAYLOAD_SIZE * 4):
        pair = Pair(get_callback=echo_get(b""), set_callback=accept_set(bad))
        assert run(pair.setup()) is True

        async def scenario(link: Pair = pair) -> bool:
            listener = asyncio.create_task(link.responder.uart_listen())
            sent = await link.initiator.uart_set(1, b"ab")
            await asyncio.wait_for(listener, _STEP_BOUND_S)
            return sent

        assert run(scenario(), limit=_LISTENER_RUN_BOUND_S) is False, f"exp_size {bad} should be refused"


def test_a_re_entrant_callback_is_refused_instead_of_deadlocking() -> None:
    # asyncio.Lock is not reentrant, so a callback that calls back in would await a lock its
    # own caller holds - the task deadlocks with the bus held and nothing times out, because
    # nothing is waiting on the wire. The bounded run() here is what proves it is not merely slow.
    pair = Pair(get_callback=echo_get(b""), set_callback=accept_set())
    assert run(pair.setup()) is True
    outcome: list[Any] = []

    async def reentrant(cmd_id: int) -> "tuple[bool, bytes]":
        outcome.append(await pair.responder.uart_set(9, b"nested"))
        return True, b"v"

    pair.responder._get_callback = reentrant

    async def scenario() -> "PieceBuffer | None":
        listener = asyncio.create_task(pair.responder.uart_listen())
        answer = await pair.initiator.uart_get(1)
        await asyncio.wait_for(listener, _STEP_BOUND_S)
        return answer

    run(scenario(), limit=_LISTENER_RUN_BOUND_S)
    assert outcome == [False]  # refused with a sentinel, never awaited into a deadlock


def test_the_role_gate_refuses_the_wrong_direction() -> None:
    # The lock is released between listen calls, so an application could otherwise interleave
    # an initiation into a responder's loop and cause exactly the simultaneous initiation the
    # design has no arbitration for.
    pair = run(build_pair(get_callback=echo_get(b""), set_callback=accept_set()))
    assert run(pair.responder.uart_set(1, b"x")) is False
    assert run(pair.responder.uart_get(1)) is None
    assert run(pair.initiator.uart_listen()).cmd_id is None


@_on_poll_rounds
def test_a_responder_still_answers_a_get_while_the_role_gate_is_active() -> None:
    # The answer runs through the internal unlocked SET path. If the gate blocked it too, a
    # responder could never answer anything and the protocol would simply stop working.
    pair = run(build_pair(get_callback=echo_get(b"answer"), set_callback=accept_set()))
    assert run(pair.responder.uart_set(1, b"x")) is False  # the gate is genuinely active
    answer = run(pair.with_listener(pair.initiator.uart_get(1)))
    assert answer is not None
    assert copied_out(answer) == b"answer"


def test_the_role_is_immutable_after_construction() -> None:
    comm = make_comm()
    assert not hasattr(comm, "set_role")


@_on_poll_rounds
def test_both_halves_of_each_pair_move_identical_bytes() -> None:
    # A zero-copy path that exists for reads but not writes is worse than neither, because
    # it looks complete.
    payload = bytes(range(PAYLOAD_SIZE + 1))
    via_convenience = run(build_pair(get_callback=echo_get(b""), set_callback=accept_set()))
    assert run(via_convenience.with_listener(via_convenience.initiator.uart_set(2, payload))) is True
    via_into = run(build_pair(get_callback=echo_get(b""), set_callback=accept_set()))
    assert run(via_into.with_listener(via_into.initiator.uart_set_into(2, bytearray(payload), len(payload)))) is True
    assert via_convenience.wire_from_initiator() == via_into.wire_from_initiator()

    by_value = run(build_pair(get_callback=echo_get(payload), set_callback=accept_set()))
    answer = run(by_value.with_listener(by_value.initiator.uart_get(2)))
    by_buffer = run(build_pair(get_callback=echo_get(payload), set_callback=accept_set()))
    dest = bytearray(PAYLOAD_SIZE * 4)
    written = run(by_buffer.with_listener(by_buffer.initiator.uart_get_into(2, dest)))
    assert answer is not None
    assert written == len(payload)
    assert copied_out(answer) == bytes(dest[:written])


def test_an_into_destination_that_is_too_small_is_refused() -> None:
    # Checked before the first data ACK, so nothing is overrun and nothing is reported
    # as success.
    pair = run(build_pair(get_callback=echo_get(bytes(PAYLOAD_SIZE * 2)), set_callback=accept_set()))
    assert run(pair.with_listener(pair.initiator.uart_get_into(1, bytearray(2))), limit=_RUN_BOUND_S) is None


def test_an_into_destination_of_none_returns_the_sentinel() -> None:
    # A failed RegionBuffer hands its owner None; an AttributeError here would be the
    # worst possible moment for one.
    comm = make_comm()
    run(comm.setup())
    assert run(comm.uart_get_into(1, None)) is None


@_on_poll_rounds
def test_a_payload_can_be_streamed_from_a_pull_callback() -> None:
    # F7: what makes "large payloads over little buffers" true rather than half-true - the whole
    # payload never exists in RAM at either end.
    source = bytes((i * 3) & 0xFF for i in range(PAYLOAD_SIZE * 2 + 3))
    got: list[Any] = []

    def pull(chunk: int, buf: memoryview) -> int:
        start = (chunk - 2) * PAYLOAD_SIZE
        part = source[start : start + len(buf)]
        buf[: len(part)] = part
        return len(part)

    def remember(cmd_id: int) -> "tuple[bool, int | None]":
        return True, len(source)

    pair = Pair(get_callback=echo_get(b""), set_callback=remember)
    assert run(pair.setup()) is True

    async def scenario() -> ListenResult:
        listener = asyncio.create_task(pair.responder.uart_listen())
        got.append(await pair.initiator.uart_set_stream(0x60, len(source), pull))
        return await asyncio.wait_for(listener, _STEP_BOUND_S)

    result = run(scenario(), limit=_LISTENER_RUN_BOUND_S)
    assert got == [True]
    assert copied_out(result.payload) == source


@_on_poll_rounds
def test_a_payload_can_be_streamed_into_a_push_callback() -> None:
    source = bytes(range(PAYLOAD_SIZE * 2))
    chunks_seen: list[bytes] = []

    def push(chunk: int, buf: memoryview) -> bool:
        chunks_seen.append(bytes(buf))
        return True

    pair = run(build_pair(get_callback=echo_get(source), set_callback=accept_set()))
    written = run(pair.with_listener(pair.initiator.uart_get_stream(1, push)))
    assert written == len(source)
    assert b"".join(chunks_seen) == source


def test_a_pull_callback_short_filling_a_non_final_chunk_aborts_locally() -> None:
    # The peer would reject it anyway, but the fault is this side's and must be
    # caught before anything is sent.
    def stingy(chunk: int, buf: memoryview) -> int:
        return 1  # always one byte, however much the chunk needs

    pair = run(build_pair(get_callback=echo_get(b""), set_callback=accept_set()))
    assert run(pair.with_listener(pair.initiator.uart_set_stream(1, PAYLOAD_SIZE * 2, stingy)), limit=_RUN_BOUND_S) is False


def test_a_pull_callback_returning_a_wrong_shape_is_guarded() -> None:
    # The same escape as the other callback returns, so it gets the same guard.
    def wrong(chunk: int, buf: memoryview) -> str:
        return "lots"

    pair = run(build_pair(get_callback=echo_get(b""), set_callback=accept_set()))
    assert run(pair.with_listener(pair.initiator.uart_set_stream(1, 4, wrong)), limit=_RUN_BOUND_S) is False


def test_a_push_callback_failing_mid_train_aborts() -> None:
    # Half the payload is stored otherwise, with the caller none the wiser.
    def refuse_second(chunk: int, buf: memoryview) -> bool:
        return chunk < 3

    pair = run(build_pair(get_callback=echo_get(bytes(PAYLOAD_SIZE * 3)), set_callback=accept_set()))
    assert run(pair.with_listener(pair.initiator.uart_get_stream(1, refuse_second)), limit=_RUN_BOUND_S) is None


def test_a_streamed_total_size_must_be_declared() -> None:
    # CHUNKS has to be in chunk 1, so an unknown length is out of scope by design.
    pair = run(build_pair(get_callback=echo_get(b""), set_callback=accept_set()))
    assert run(pair.initiator.uart_set_stream(1, -1, lambda chunk, buf: 0)) is False


# ---- caller-supplied arguments (audit pass) ------------------------------------------------------
# Each case was confirmed against the real interpreter before its guard existed: it either raised
# out of a module contracted never to raise, or succeeded while sending something else entirely.


# ---- General-purpose initiator API: no product caller; kept as the standalone module's API (owner, 2026-09-29) ----


def test_every_initiator_entry_point_answers_not_initialised_before_setup() -> None:
    # The readiness gate comes before every argument check, so an unready instance says so whatever it
    # was handed (J.9's one order).
    comm = make_comm(name="UART_X")
    assert run(comm.uart_get_into(1, None)) is None
    assert run(comm.uart_get_stream(1, None)) is None
    assert run(comm.uart_set_stream(1, 4, None)) is False
    assert run(comm.uart_get(256)) is None
    assert persisted(comm) == [_e("NOT_INIT")], persisted(comm)
    assert run(comm.get_error_counter())["UART_X"]["ErrCount"] == 4


def test_a_responder_refuses_the_role_before_any_argument() -> None:
    comm = make_comm(name="UART_X", role=ROLE_RESPONDER, get_callback=echo_get(b""), set_callback=accept_set())
    assert run(comm.setup()) is True
    assert run(comm.uart_set(256, 5)) is False  # type: ignore[arg-type]
    assert run(comm.uart_set_into(256, "x", -1)) is False  # type: ignore[arg-type]
    assert run(comm.uart_set_stream(256, -1, None)) is False
    assert run(comm.uart_get(256, -5)) is None
    assert run(comm.uart_get_into(256, None, -1)) is None
    assert run(comm.uart_get_stream(256, None, -1)) is None
    assert persisted(comm) == [_e("UART_ROLE_REFUSED")], persisted(comm)
    assert run(comm.get_error_counter())["UART_X"]["ErrCount"] == 6


def test_the_command_id_is_checked_first_on_an_initiator() -> None:
    comm = make_comm()
    assert run(comm.setup()) is True
    comm.pr.set_level(1)
    recorder = _PrintRecorder()
    try:
        assert run(comm.uart_set_stream(256, -1, None)) is False
        assert run(comm.uart_get_into(256, None)) is None
    finally:
        recorder.restore()
    assert persisted(comm) == [_e("BAD_ARG")], persisted(comm)
    assert [line for line in recorder.text().split("\n") if "UART error" in line] == ["UART UART error: command id 256 is not a byte value"] * 2, recorder.text()


@_on_poll_rounds
def test_an_empty_answer_into_a_buffer_is_zero_not_none() -> None:
    # J.9: zero bytes is an outcome distinct from failure, and the destination is left as it was.
    pair = run(build_pair(get_callback=echo_get(b""), set_callback=accept_set()))
    dest = bytearray(b"\xaa" * PAYLOAD_SIZE)  # room for the train's upper bound, checked before its first ACK
    assert run(pair.with_listener(pair.initiator.uart_get_into(1, dest)), limit=_RUN_BOUND_S) == 0
    assert dest == bytearray(b"\xaa" * PAYLOAD_SIZE)
    assert run(pair.with_listener(pair.initiator.uart_get_stream(1, lambda chunk, buf: True)), limit=_RUN_BOUND_S) == 0


@_on_poll_rounds
def test_an_answer_that_misses_its_expected_size_is_refused_before_its_final_ack() -> None:
    pair = run(build_pair(timeout=_SHORT_REPLY_TIMEOUT_MS, get_callback=echo_get(b"four"), set_callback=accept_set()))
    got = run(pair.with_listener(pair.initiator.uart_get_into(1, bytearray(8), exp_size=5), listener_may_stall=True), limit=_LISTENER_RUN_BOUND_S)
    assert got is None
    acks = [f for f in frames(pair.wire_from_initiator(), _FRAME) if f[_CMD] == _CMD_ACK]
    assert len(acks) == 1, acks  # the answer header's ACK only: the last chunk is never acknowledged
    empty = run(build_pair(get_callback=echo_get(b""), set_callback=accept_set()))
    assert run(empty.with_listener(empty.initiator.uart_get_into(1, bytearray(4), exp_size=0)), limit=_RUN_BOUND_S) == 0


@_on_poll_rounds
def test_an_empty_set_is_delivered_as_a_distinct_outcome() -> None:
    for args in ((None,), (bytearray(4), 0)):
        pair = run(build_pair(get_callback=echo_get(b""), set_callback=accept_set()))

        async def scenario(pair: Pair = pair, args: "tuple[Any, ...]" = args) -> "tuple[bool, ListenResult]":
            listener = asyncio.create_task(pair.responder.uart_listen())
            sent = await pair.initiator.uart_set_into(0x31, *args)
            return sent, await asyncio.wait_for(listener, _STEP_BOUND_S)

        sent, result = run(scenario(), limit=_LISTENER_RUN_BOUND_S)
        assert sent is True, args
        assert result == ListenResult(0x31, _CMD_SET, None), result


@_on_poll_rounds
def test_a_zero_size_stream_sends_one_empty_data_chunk() -> None:
    regions: list[int] = []

    def pull(chunk: int, buf: memoryview) -> int:
        regions.append(len(buf))
        return 0

    pair = run(build_pair(get_callback=echo_get(b""), set_callback=accept_set()))
    assert run(pair.with_listener(pair.initiator.uart_set_stream(1, 0, pull)), limit=_RUN_BOUND_S) is True
    sent = frames(pair.wire_from_initiator(), _FRAME)
    assert [(f[_CHUNKS], f[_CUR], f[_SIZE]) for f in sent] == [(2, 1, 1), (2, 2, 0)]
    assert regions == [0]


@_on_poll_rounds
def test_a_stream_of_the_largest_declarable_size_completes_and_one_more_byte_is_refused() -> None:
    total = 254 * PAYLOAD_SIZE
    source = bytes(i & 0xFF for i in range(total))

    def pull(chunk: int, buf: memoryview) -> int:
        start = (chunk - 2) * PAYLOAD_SIZE
        buf[0 : len(buf)] = source[start : start + len(buf)]
        return len(buf)

    pair = run(build_pair(get_callback=echo_get(b""), set_callback=accept_set()))
    sent, result = _stream_with_listener(pair, total, pull)
    assert sent is True
    assert copied_out(result.payload) == source
    assert len(frames(pair.wire_from_initiator(), _FRAME)) == 255
    refused = run(build_pair(get_callback=echo_get(b""), set_callback=accept_set()))
    assert run(refused.initiator.uart_set_stream(1, total + 1, pull)) is False
    assert refused.wire_from_initiator() == b""


@_on_poll_rounds
def test_a_buffer_is_borrowed_only_for_the_call() -> None:
    # J.9: neither a destination nor a source is held past the call that was handed it.
    pair = run(build_pair(get_callback=echo_get(b"first"), set_callback=accept_set()))
    dest = bytearray(8)
    assert run(pair.with_listener(pair.initiator.uart_get_into(1, dest)), limit=_RUN_BOUND_S) == 5
    kept = bytes(dest)
    pair.responder._get_callback = echo_get(b"second")
    assert run(pair.with_listener(pair.initiator.uart_get_into(1, bytearray(8))), limit=_RUN_BOUND_S) == 6
    assert bytes(dest) == kept
    src = bytearray(b"source")
    assert run(pair.with_listener(pair.initiator.uart_set_into(2, src, 6)), limit=_RUN_BOUND_S) is True
    before = pair.wire_from_initiator()
    src[0:6] = b"XXXXXX"
    assert run(pair.with_listener(pair.initiator.uart_set(3, None)), limit=_RUN_BOUND_S) is True
    assert pair.wire_from_initiator()[: len(before)] == before
    assert b"XXXXXX" not in pair.wire_from_initiator()


def _stream_with_listener(pair: Pair, total: int, pull: "Any") -> "tuple[bool, ListenResult]":
    async def scenario() -> "tuple[bool, ListenResult]":
        listener = asyncio.create_task(pair.responder.uart_listen())
        sent = await pair.initiator.uart_set_stream(0x32, total, pull)
        return sent, await asyncio.wait_for(listener, _LISTENER_SHORT_BOUND_S)

    return run(scenario(), limit=_LISTENER_RUN_BOUND_S)


@_on_poll_rounds
def test_an_out_of_range_command_id_is_refused_not_truncated() -> None:
    # bytearray assignment truncates silently on this platform, so 0x101 went out as 0x01 - a
    # different, valid command the peer executed while the call reported success. The header
    # fields were already guarded against exactly this (_prepare_tx); the command id was not.
    pair = run(build_pair(get_callback=echo_get(b"hi"), set_callback=accept_set()))
    assert run(pair.with_listener(pair.initiator.uart_set(0x101, b"x"), listener_may_stall=True), limit=_RUN_BOUND_S) is False
    assert pair.wire_from_initiator() == b"", "a refused command id must not put a frame on the wire"
    assert run(pair.initiator.uart_set(-1, b"x")) is False
    assert run(pair.initiator.uart_get(0x100)) is None
    assert run(pair.initiator.uart_set_stream(256, 0, lambda chunk, buf: 0)) is False


def test_a_non_integer_command_id_returns_a_sentinel_instead_of_raising() -> None:
    pair = run(build_pair(get_callback=echo_get(b"hi"), set_callback=accept_set()))
    assert run(pair.initiator.uart_get("banner")) is None  # type: ignore[arg-type]
    assert run(pair.initiator.uart_set(None, b"x")) is False  # type: ignore[arg-type]


def test_a_non_integer_size_returns_a_sentinel_instead_of_raising() -> None:
    # Both of these reached a comparison against an int and raised TypeError straight through.
    pair = run(build_pair(get_callback=echo_get(b"hi"), set_callback=accept_set()))
    assert run(pair.initiator.uart_set_into(1, b"abc", "2")) is False  # type: ignore[arg-type]
    assert run(pair.initiator.uart_get(1, "5")) is None  # type: ignore[arg-type]


@_on_poll_rounds
def test_a_negative_expected_size_is_refused_not_read_as_dont_care() -> None:
    # -1 is the module's own internal "don't care" sentinel. A caller's negative exp_size used to
    # land on it, silently turning an exact-size GET into an unchecked one.
    pair = run(build_pair(get_callback=echo_get(b"hello"), set_callback=accept_set()))
    # Refused before anything is sent, so the responder's listen round never completes.
    assert run(pair.with_listener(pair.initiator.uart_get(1, -5), listener_may_stall=True), limit=_RUN_BOUND_S) is None
    # The contrast case: None really does mean don't care, and still works.
    assert copied_out(run(pair.with_listener(pair.initiator.uart_get(1)), limit=_RUN_BOUND_S)) == b"hello"


def test_a_non_buffer_payload_returns_a_sentinel_instead_of_raising() -> None:
    # len(5) and "abc"[0:n] both raise TypeError; the responder's own get_callback payload was
    # already type-checked, the initiator's was not.
    pair = run(build_pair(get_callback=echo_get(b"hi"), set_callback=accept_set()))
    assert run(pair.initiator.uart_set(1, 5)) is False  # type: ignore[arg-type]
    assert run(pair.initiator.uart_set(1, "abc")) is False  # type: ignore[arg-type]


def test_an_immutable_destination_is_refused_before_the_train_starts() -> None:
    # bytes has no slice assignment, so this failed mid-train with a TypeError after the peer had
    # already been acknowledged - the worst possible moment to discover it.
    pair = run(build_pair(get_callback=echo_get(b"hi"), set_callback=accept_set()))
    assert run(pair.initiator.uart_get_into(1, b"\x00\x00")) is None  # type: ignore[arg-type]
    assert pair.wire_from_initiator() == b""


def test_a_refused_argument_is_logged_with_its_own_errno() -> None:
    pair = run(build_pair(get_callback=echo_get(b"hi"), set_callback=accept_set()))
    assert run(pair.initiator.uart_set(0x101, b"x")) is False
    log = run(pair.initiator.get_error_counter())["UART_A"]
    assert "E" in log["ErrType"], log
    assert code("E", "BAD_ARG") in log["ErrNum"], log


# ---- caller-supplied arguments, second pass -------------------------------------------------------
# Same class as the section above, found by carrying its question into the two entry points it had
# not reached: the constructor, and the streaming forms' own callbacks.


def test_a_non_integer_payload_size_is_refused_instead_of_raising() -> None:
    # _validate_config() already caught the type - but _frame_size was derived from the raw value
    # first, so `5 + "48"` raised TypeError out of __init__ itself. The constructor is the one
    # entry point that cannot answer with a sentinel: there is no object yet to ask.
    for bad in ("48", None, 1.5):
        comm = make_comm(payload_size=bad)
        assert comm._init_errno != 0, bad
        assert comm._payload_size == bad, "the caller's own value stays on self, for the log to name"
        assert run(comm.setup()) is False


def test_a_non_integer_timeout_is_refused_instead_of_raising() -> None:
    # The backoff was computed before validation ran, so `"1000" // 2` raised first.
    for bad in ("1000", None):
        comm = make_comm(timeout=bad)
        assert comm._init_errno != 0, bad
        assert run(comm.setup()) is False


@_on_poll_rounds
def test_a_read_only_destination_is_refused_before_the_train_starts() -> None:
    # memoryview(b"...") is a memoryview like any other, so the type check passed and the first
    # slice assignment raised TypeError mid-train - after the peer had already been acknowledged.
    pair = run(build_pair(get_callback=echo_get(b"hello"), set_callback=accept_set()))
    assert run(pair.initiator.uart_get_into(1, memoryview(b"\x00" * 64))) is None
    assert pair.wire_from_initiator() == b""
    # The contrast case: a writable memoryview is still a perfectly good destination.
    dest = bytearray(64)
    assert run(pair.with_listener(pair.initiator.uart_get_into(1, memoryview(dest), 5)), limit=_RUN_BOUND_S) == 5
    assert dest[0:5] == bytearray(b"hello")


def test_a_stream_without_its_pull_callback_sends_nothing() -> None:
    # _send_train's no-pull branch means "the payload argument carries the data", and this entry
    # point has no payload argument - so the train went out as total_size bytes of padding and
    # uart_set_stream() returned True.
    pair = run(build_pair(get_callback=echo_get(b""), set_callback=accept_set()))
    assert run(pair.initiator.uart_set_stream(1, 12, None)) is False
    assert pair.wire_from_initiator() == b"", "nothing may reach the wire without a source for it"


def test_a_stream_without_its_push_callback_reports_failure_not_a_byte_count() -> None:
    # With neither a push callback nor a destination, _recv_train counts every chunk and drops it,
    # so the call reported the byte count of an answer nobody received.
    pair = run(build_pair(get_callback=echo_get(b"abcdefghij"), set_callback=accept_set()))
    assert run(pair.initiator.uart_get_stream(1, None)) is None
    assert pair.wire_from_initiator() == b""


# ---- fault history under the central newest-entry rule -------------------------------------------


def test_a_repeating_fault_spends_one_slot() -> None:
    # A permanently faulty link must not refill the bounded history: each fault persists its errno,
    # the resync it drags along only prints, and the central rule keeps the repeats in one slot.
    pair = run(build_pair(get_callback=echo_get(b"hi"), set_callback=accept_set()))
    pair.link.direction_from(pair.fake_b).silent = True  # the peer never answers
    for _ in range(5):
        run(pair.initiator.uart_set(1, b"x"), limit=_RUN_BOUND_S)
    log = run(pair.initiator.get_error_counter())["UART_A"]
    # Index-based, not zip(strict=...): MicroPython's builtin zip() does not accept it, which is
    # the same reason test_bus_hazard_multi_device.py pairs its own lists this way.
    recorded = [(log["ErrType"][i], log["ErrNum"][i]) for i in range(len(log["ErrNum"])) if log["ErrType"][i] != "N"]
    assert recorded == [("E", code("E", "UART_NO_ACK"))], recorded
    assert log["ErrCount"] == 5


@_on_poll_rounds
def test_a_recovered_link_counts_every_later_fault() -> None:
    # Central rule (C.7.1): a recovery logs nothing, so the next identical fault still matches the newest
    # entry - counted every time, no new slot.
    pair = run(build_pair(get_callback=echo_get(b"hi"), set_callback=accept_set()))
    direction = pair.link.direction_from(pair.fake_b)
    direction.silent = True
    run(pair.initiator.uart_set(1, b"x"), limit=_RUN_BOUND_S)
    run(pair.initiator.uart_set(1, b"x"), limit=_RUN_BOUND_S)
    direction.silent = False
    run(pair.responder.clear())
    run(pair.initiator.clear())
    assert run(pair.with_listener(pair.initiator.uart_set(1, b"x")), limit=_RUN_BOUND_S) is True
    direction.silent = True
    run(pair.initiator.uart_set(1, b"x"), limit=_RUN_BOUND_S)
    log = run(pair.initiator.get_error_counter())["UART_A"]
    # Index-based, not zip(strict=...): MicroPython's builtin zip() does not accept it, which is
    # the same reason test_bus_hazard_multi_device.py pairs its own lists this way.
    recorded = [(log["ErrType"][i], log["ErrNum"][i]) for i in range(len(log["ErrNum"])) if log["ErrType"][i] != "N"]
    assert recorded == [("E", code("E", "UART_NO_ACK"))], recorded
    assert log["ErrCount"] == 3


def test_a_rejected_command_is_distinguishable_from_a_link_fault() -> None:
    # A history entry must tell "the peer asked for something this side does not implement" from
    # "the link broke" - the exact diagnostic loss C.7.1 is about.
    def only_one(cmd_id: int) -> "tuple[bool, bytes | None]":
        return (cmd_id == 1), None

    pair = run(build_pair(get_callback=only_one, set_callback=accept_set()))
    run(pair.with_listener(pair.initiator.uart_get(2)), limit=_RUN_BOUND_S)
    log = run(pair.responder.get_error_counter())["UART_B"]
    # Index-based, not zip(strict=...): MicroPython's builtin zip() does not accept it, which is
    # the same reason test_bus_hazard_multi_device.py pairs its own lists this way.
    recorded = [(log["ErrType"][i], log["ErrNum"][i]) for i in range(len(log["ErrNum"])) if log["ErrType"][i] != "N"]
    assert ("W", code("W", "UART_CMD_DECLINED")) in recorded, recorded  # its own code


# ---- the owned listen loop's delivery point (audit pass) -----------------------------------------


@_on_poll_rounds
def test_the_owned_listen_loop_delivers_a_received_payload() -> None:
    # Without this the loop consumed the ListenResult and dropped it: a responder wired the
    # documented way (get_task_starters()) could never see a SET's data at all.
    seen: list[Any] = []

    def record(cmd_id: int, cmd: int, payload: "PieceBuffer | None") -> None:
        seen.append((cmd_id, cmd, copied_out(payload)))

    pair = run(build_pair(get_callback=echo_get(b""), set_callback=accept_set(), message_callback=record))

    async def exchange() -> bool:
        task = pair.responder.start_asy_listen()
        try:
            return await pair.initiator.uart_set(7, b"payload")
        finally:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:  # expected; anything else is a real failure
                pass

    assert run(exchange(), limit=_RUN_BOUND_S) is True
    assert seen == [(7, _CMD_SET, b"payload")], seen


@_on_poll_rounds
def test_a_raising_message_callback_does_not_kill_the_listen_loop() -> None:
    # The same reasoning applies to this callback: it is owner-supplied code running inside the
    # loop the supervisor would otherwise restart as a task death.
    def explode(cmd_id: int, cmd: int, payload: "PieceBuffer | None") -> None:
        raise ValueError("owner code")

    pair = run(build_pair(get_callback=echo_get(b""), set_callback=accept_set(), message_callback=explode))

    async def exchange() -> "tuple[bool, bool]":
        task = pair.responder.start_asy_listen()
        try:
            first = await pair.initiator.uart_set(7, b"one")
            second = await pair.initiator.uart_set(7, b"two")
            return first, second
        finally:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    assert run(exchange(), limit=_RUN_BOUND_S) == (True, True), "the loop must survive its owner's raise"


def test_a_responder_without_a_message_callback_is_still_constructible() -> None:
    # Optional by design: a GET-only responder has nothing to deliver, so its absence is not the
    # unanswerable-request case construction refuses outright.
    pair = run(build_pair(get_callback=echo_get(b"hi"), set_callback=accept_set()))
    assert pair.responder._message_callback is None
    assert pair.responder.initialized is True


# ===========================================================================
# Receive limits - pieces of at most chunk_bytes, and the transfer cap
# ===========================================================================


def _largest_piece(pb: "PieceBuffer") -> int:
    largest = 0
    for piece in pb.pieces():
        largest = max(largest, len(piece))
    return largest


def _set_with_listener(pair: Pair, set_id: int, payload: bytes) -> "tuple[bool, ListenResult]":
    async def scenario() -> "tuple[bool, ListenResult]":
        listener = asyncio.create_task(pair.responder.uart_listen())
        sent = await pair.initiator.uart_set(set_id, payload)
        return sent, await asyncio.wait_for(listener, _STEP_BOUND_S)

    return run(scenario(), limit=_LISTENER_RUN_BOUND_S)


@_on_poll_rounds
def test_a_dont_care_get_arrives_in_pieces_no_larger_than_chunk_bytes() -> None:
    payload = bytes(range(5 * PAYLOAD_SIZE + 3))
    pair = run(build_pair(limits=transfer_limits(chunk_bytes=5), get_callback=echo_get(payload), set_callback=accept_set()))
    answer = run(pair.with_listener(pair.initiator.uart_get(0x21)), limit=_RUN_BOUND_S)
    assert isinstance(answer, PieceBuffer)
    assert len(answer) == len(payload)  # the bytes received, not the train's upper bound
    assert _largest_piece(answer) <= 5
    assert copied_out(answer) == payload


@_on_poll_rounds
def test_a_dont_care_set_is_assembled_in_pieces_no_larger_than_chunk_bytes() -> None:
    payload = bytes(range(3 * PAYLOAD_SIZE + 1))
    pair = run(build_pair(limits=transfer_limits(chunk_bytes=3), get_callback=echo_get(b""), set_callback=accept_set()))
    sent, result = _set_with_listener(pair, 0x22, payload)
    assert sent is True
    assert result.cmd_id == 0x22
    assert isinstance(result.payload, PieceBuffer)
    assert _largest_piece(result.payload) <= 3
    assert copied_out(result.payload) == payload


class _CountingPieceBuffer(PieceBuffer):
    # Rebound as the module's PieceBuffer: counts every receive destination the module builds.
    built = 0

    def __init__(self, size: int, piece_bytes: int) -> None:
        _CountingPieceBuffer.built += 1
        super().__init__(size, piece_bytes)


def _counting_pieces() -> None:
    _CountingPieceBuffer.built = 0
    asy_uart_comm.PieceBuffer = _CountingPieceBuffer  # type: ignore[misc]


def _real_pieces() -> None:
    asy_uart_comm.PieceBuffer = PieceBuffer  # type: ignore[misc]


def _scrub(pair: Pair) -> None:
    # The fakes' call and wire logs are scaffolding a test reads back, not something the protocol retains.
    for direction in (pair.link.a_to_b, pair.link.b_to_a):
        direction.wire_log.clear()
    pair.fake_a.log.clear()
    pair.fake_b.log.clear()


def _cap_pair(cap_side: str, answer: bytes = b"") -> Pair:
    # The default cap on one end, a two-frame cap on the other: the refusing end is the receiver.
    pair = Pair(timeout=_SHORT_REPLY_TIMEOUT_MS, get_callback=echo_get(answer), set_callback=accept_set())
    assert run(pair.setup()) is True
    (pair.responder if cap_side == "responder" else pair.initiator)._max_transfer_bytes = 2 * PAYLOAD_SIZE
    return pair


def test_the_default_chunk_bytes_is_the_reasoned_one() -> None:
    # The webserver's piece size (Part I.3): one bound for the largest single receive allocation device-wide.
    assert _src_const("_DEFAULT_CHUNK_BYTES") == _src_const("_DEFAULT_CHUNK_BYTES", "src/asy_webserver_service.py")
    assert DEFAULT_LIMITS.chunk_bytes == _src_const("_DEFAULT_CHUNK_BYTES")


@_on_poll_rounds
def test_a_caller_supplied_destination_is_still_filled_in_place() -> None:
    # The zero-copy path: a caller's buffer is written directly and no piece is built for it.
    payload = bytes(range(3 * PAYLOAD_SIZE))
    pair = run(build_pair(limits=transfer_limits(chunk_bytes=4), get_callback=echo_get(payload), set_callback=accept_set()))
    dest = bytearray(4 * PAYLOAD_SIZE)
    _counting_pieces()
    try:
        assert run(pair.with_listener(pair.initiator.uart_get_into(1, dest)), limit=_RUN_BOUND_S) == len(payload)
    finally:
        _real_pieces()
    assert _CountingPieceBuffer.built == 0
    assert bytes(dest[: len(payload)]) == payload


@_on_poll_rounds
def test_a_declared_size_over_max_transfer_bytes_is_refused_before_any_allocation() -> None:
    # The declared size, (CHUNKS - 1) x payload_size, is known from the command frame alone, so the
    # train is refused before anything is allocated or acknowledged: the sender sees J's rejection.
    asked: list[int] = []

    def counting_set(cmd_id: int) -> "tuple[bool, None]":
        asked.append(cmd_id)
        return True, None

    pair = _cap_pair("responder")
    pair.responder._set_callback = counting_set
    _counting_pieces()
    try:
        sent, result = _set_with_listener(pair, 0x23, bytes(2 * PAYLOAD_SIZE + 1))
    finally:
        _real_pieces()
    assert sent is False
    assert (result.cmd_id, result.cmd) == (None, asy_uart_comm.CMD_SET)
    assert asked == []  # refused before the callback, which runs after the ACK
    assert _CountingPieceBuffer.built == 0
    assert pair.wire_from_responder() == b""  # the ACK withheld
    assert persisted(pair.responder) == [_e("UART_TRANSFER_CAP")], persisted(pair.responder)

    async def refusals(n: int) -> None:
        for _ in range(n):
            await pair.responder._accept_set(pair.driver_b, counting_set, 0x23, 0, 4)

    async def measured() -> "list[int]":
        # Sampled around each whole refusals() call, so its own frame and loop are born and freed inside the window
        # (sampled within it, they read as 64 B of retention); no ambient subtraction, a no-op control frees 64 B.
        await refusals(1)  # every path taken once before the heap is sampled
        nets = [0, 0, 0]
        for k in range(3):
            gc.collect()
            before = gc.mem_alloc()
            await refusals(_REFUSALS)
            gc.collect()
            nets[k] = gc.mem_alloc() - before
        return nets

    # The collector scans the C stack conservatively, so one window can keep or free a few stale blocks: a
    # per-refusal leak shows in all three windows (one block each is 800 B), so the least must be 0.
    nets = run(measured(), limit=_LISTENER_RUN_BOUND_S)
    assert min(nets) <= 0, f"{nets} bytes grown over {_REFUSALS} refusals, in each of three windows"


@_on_poll_rounds
def test_an_expected_size_over_the_cap_is_refused_before_any_allocation() -> None:
    pair = _cap_pair("initiator", bytes(2 * PAYLOAD_SIZE + 1))
    _counting_pieces()
    try:
        answer = run(pair.with_listener(pair.initiator.uart_get(0x25), listener_may_stall=True), limit=_LISTENER_RUN_BOUND_S)
    finally:
        _real_pieces()
    assert answer is None
    assert _CountingPieceBuffer.built == 0
    assert len(frames(pair.wire_from_initiator(), _FRAME)) == 1  # the GET itself; its answer never acknowledged
    assert persisted(pair.initiator) == [_e("UART_TRANSFER_CAP")], persisted(pair.initiator)


@_on_poll_rounds
def test_a_train_at_the_cap_is_accepted() -> None:
    pair = _cap_pair("responder")
    sent, result = _set_with_listener(pair, 0x24, bytes(range(2 * PAYLOAD_SIZE)))
    assert sent is True
    assert copied_out(result.payload) == bytes(range(2 * PAYLOAD_SIZE))
    pair = _cap_pair("initiator", bytes(range(2 * PAYLOAD_SIZE)))
    assert copied_out(run(pair.with_listener(pair.initiator.uart_get(0x26)), limit=_RUN_BOUND_S)) == bytes(range(2 * PAYLOAD_SIZE))


@_on_poll_rounds
def test_a_transfer_over_the_own_cap_is_refused_before_anything_is_sent() -> None:
    # The sender knows its own cap, so a train its peer would refuse is refused at the argument
    # checks; the declared size is the same (CHUNKS - 1) x payload_size the receiver compares.
    cap = 2 * PAYLOAD_SIZE
    pair = run(build_pair(limits=transfer_limits(max_transfer_bytes=cap), get_callback=echo_get(b""), set_callback=accept_set()))
    over = cap + 1
    assert run(pair.initiator.uart_set(1, bytes(over))) is False
    assert run(pair.initiator.uart_set_into(1, bytearray(over), over)) is False
    assert run(pair.initiator.uart_set_stream(1, over, lambda chunk, buf: len(buf))) is False
    assert run(pair.initiator.uart_get(1, exp_size=over)) is None
    assert run(pair.initiator.uart_get_into(1, bytearray(over), exp_size=over)) is None
    assert run(pair.initiator.uart_get_stream(1, lambda chunk, buf: True, exp_size=over)) is None
    assert pair.wire_from_initiator() == b""
    assert persisted(pair.initiator) == [_e("UART_TRANSFER_CAP")], persisted(pair.initiator)
    assert run(pair.with_listener(pair.initiator.uart_set(2, bytes(cap))), limit=_RUN_BOUND_S) is True


@_on_poll_rounds
def test_repeated_maximum_size_and_over_cap_trains_keep_the_heap_flat() -> None:
    # Alternating trains at the cap and over it, in each direction: every one at the cap intact, every
    # one over it refused, and the heap after the run no larger than after the first train of each kind.
    cap = 2 * PAYLOAD_SIZE
    at_cap = bytes(range(cap))
    limits = transfer_limits(timeout=_SHORT_REPLY_TIMEOUT_MS, chunk_bytes=PAYLOAD_SIZE, max_transfer_bytes=cap)
    pair = run(build_pair(limits=limits, get_callback=echo_get(at_cap), set_callback=accept_set()))
    intact = refused = 0

    async def one_round(i: int) -> None:
        nonlocal intact, refused
        listener = asyncio.create_task(pair.responder.uart_listen())
        over = i % 2 == 1
        if i % 4 < 2:  # towards the responder: the initiator's own cap raised, so the responder refuses
            pair.initiator._max_transfer_bytes = 3 * cap
            ok = await pair.initiator.uart_set(1, bytes(cap + 1) if over else at_cap)
        else:  # towards the initiator: an answer is never capped by its sender, so the initiator refuses
            pair.initiator._max_transfer_bytes = cap
            pair.responder._get_callback = echo_get(bytes(cap + 1) if over else at_cap)
            got = await pair.initiator.uart_get(2)
            ok = got is not None and copied_out(got) == at_cap
        if over:
            refused += 0 if ok else 1
        else:
            intact += 1 if ok else 0
        try:
            await asyncio.wait_for(listener, _STEP_BOUND_S)
        except asyncio.TimeoutError:
            listener.cancel()
        _scrub(pair)

    async def scenario() -> "list[int]":
        # The first half takes every path and lets the one-time fills settle (160 B within the first 100 trains
        # on the settrace build, then flat to 1,200, measured); three windows of the second half are sampled.
        for i in range(_HAMMER_ROUNDS // 2):
            await one_round(i)
        grew = [0, 0, 0]
        window = _HAMMER_ROUNDS // 8
        for k in range(3):
            gc.collect()
            first = gc.mem_alloc()
            for i in range(_HAMMER_ROUNDS // 2 + k * window, _HAMMER_ROUNDS // 2 + (k + 1) * window):
                await one_round(i)
            gc.collect()
            grew[k] = gc.mem_alloc() - first
        for i in range(_HAMMER_ROUNDS // 2 + 3 * window, _HAMMER_ROUNDS):
            await one_round(i)
        return grew

    grew = run(scenario(), limit=_HAMMER_RUN_BOUND_S)
    assert (intact, refused) == (_HAMMER_ROUNDS // 2, _HAMMER_ROUNDS // 2), (intact, refused)
    # The collector scans the C stack conservatively, so one window can keep a stale block: a per-train leak
    # shows in all three windows, so the least must be 0.
    assert min(grew) <= 0, f"the heap grew {grew} bytes over three windows of {_HAMMER_ROUNDS // 8} trains"


@_on_poll_rounds
def test_a_lapped_ring_is_a_receive_overrun_and_the_link_resyncs() -> None:
    # More arrives than the ring holds while the responder's consumer is held: the read reports the lap as
    # J.7's receive overrun, named once by its code, and no lapped byte reaches a callback.
    asked: list[int] = []

    def counting_set(cmd_id: int) -> "tuple[bool, None]":
        asked.append(cmd_id)
        return True, None

    pair = run(build_pair(get_callback=echo_get(b"ok"), set_callback=counting_set))

    async def scenario() -> ListenResult:
        pair.fake_b.feed_rx(b"\x04" * (pair.driver_b.rx_ring + _FRAME))
        return await pair.responder.uart_listen()

    assert run(scenario(), limit=_LISTENER_RUN_BOUND_S) == ListenResult(None, None, None)
    assert pair.driver_b.rx_overruns > 0
    assert persisted(pair.responder)[0] == _w("UART_RX_OVERRUN"), persisted(pair.responder)
    assert persisted(pair.responder).count(_w("UART_RX_OVERRUN")) == 1
    assert asked == []
    assert copied_out(run(pair.with_listener(pair.initiator.uart_get(1)), limit=_RUN_BOUND_S)) == b"ok"


def test_a_ring_below_its_floor_is_refused() -> None:
    floor = _ring_floor(PAYLOAD_SIZE, TIMEOUT_MS, POLL_WAIT_MS)
    bus = UART(0, tx_pin=0, rx_pin=1, baudrate=115200, poll_wait_ms=POLL_WAIT_MS, poll_idle_ms=POLL_WAIT_MS, rx_ring=floor // 2)
    bus.poller = LinkPoller(bus._uart)  # type: ignore[assignment,arg-type]  # never a real select.poll()
    assert UARTComm(bus, ROLE_INITIATOR, limits=transfer_limits())._init_errno == code("E", "UART_RXBUF")


@_on_poll_rounds
def test_a_ring_at_its_floor_holds_a_config_flush() -> None:
    # The responder reads nothing for one config flush while the initiator keeps initiating through its own
    # recovery: what arrives fits the ring at its floor, the outlasted transactions fail, the next completes.
    pair = Pair(get_callback=echo_get(b"ok"), set_callback=accept_set())
    pair.driver_b.rx_ring = pair.responder._min_rx_ring()
    assert run(pair.setup()) is True
    hold_ms = _src_const("_FLASH_HOLD_MAX_MS")

    async def scenario() -> "tuple[int, PieceBuffer | None]":
        clock = asy_uart_comm.time  # the poll-round clock: the hold is measured in the modules' own time
        start = clock.ticks_ms()
        failed = 0
        while clock.ticks_diff(clock.ticks_ms(), start) < hold_ms:
            failed += 1 if await pair.initiator.uart_get(1) is None else 0
        listener = asyncio.create_task(_listen_forever(pair))
        try:
            for _ in range(_FLUSH_RECOVERY_TRIES):
                got = await pair.initiator.uart_get(1)
                if got is not None:
                    return failed, got
            return failed, None
        finally:
            listener.cancel()

    failed, got = run(scenario(), limit=_LISTENER_RUN_BOUND_S)
    assert failed >= 1
    assert copied_out(got) == b"ok"
    assert pair.driver_b.rx_overruns == 0  # no lap
    assert _w("UART_RX_OVERRUN") not in persisted(pair.responder), persisted(pair.responder)


async def _listen_forever(pair: Pair) -> None:
    while True:  # an idle uart_listen() parks until a frame arrives, so the task is cancelled out
        await pair.responder.uart_listen()


# ===========================================================================
# Coverage close-out - the sentinel paths a healthy exchange never reaches
# ===========================================================================


def returns(value: "Any") -> "Any":
    # A callback whose return shape is the thing under test, so it is supplied rather than computed.
    def callback(cmd_id: int) -> "Any":
        return value

    return callback


def test_a_bus_cleared_after_construction_is_refused_at_every_entry_point() -> None:
    # The handle is read fresh on every call, not captured at construction, so each entry point carries its
    # own None check and reaches its own sentinel, never an AttributeError out of a module contracted not to
    # raise. setup() re-checks too: a restart must refuse, not drain through a gone handle.
    def pull(chunk: int, buf: memoryview) -> int:
        return 0

    pair = run(build_pair(get_callback=echo_get(b"v"), set_callback=accept_set()))
    initiator, responder = pair.initiator, pair.responder
    initiator._uart = None
    responder._uart = None
    assert run(initiator.uart_set(1, b"x")) is False
    assert run(initiator.uart_set_into(1, bytearray(4), 4)) is False
    assert run(initiator.uart_set_stream(1, 4, pull)) is False
    assert run(initiator.uart_get(1)) is None
    assert run(initiator.uart_get_into(1, bytearray(4))) is None
    assert run(responder.uart_listen()).cmd_id is None
    assert run(initiator.setup()) is False
    # The two construction floors are read off the bus too, so they answer for a missing one.
    assert initiator._min_timeout() == 0
    assert initiator._min_rxbuf() == 0


def test_a_declared_size_larger_than_its_buffer_is_refused_before_the_train() -> None:
    # size is the caller's own declaration and the buffer is what actually backs it. A declaration
    # the buffer cannot honour would put padding on the wire that the peer counts as payload.
    comm = make_comm()
    run(comm.setup())
    assert run(comm.uart_set_into(1, b"abc", 4)) is False
    assert run(comm.uart_set_into(1, None, 3)) is False  # nothing to take the bytes from at all
    assert persisted(comm) == [_e("UART_SIZE_MISMATCH")], persisted(comm)  # the repeat is counted, spending no slot


@_on_poll_rounds
def test_an_answer_the_train_could_never_carry_is_refused_at_its_header() -> None:
    # On the wire rather than in _dest_size() alone: CHUNKS arrives in the answer's first
    # frame, so an expected size the train cannot deliver is refused right there - before a single
    # data chunk is acknowledged, not after the whole transfer has run to completion.
    pair = run(build_pair(get_callback=echo_get(b"ab"), set_callback=accept_set()))
    assert run(pair.with_listener(pair.initiator.uart_get(1, exp_size=PAYLOAD_SIZE + 1)), limit=_RUN_BOUND_S) is None
    assert _e("UART_SIZE_MISMATCH") in persisted(pair.initiator), persisted(pair.initiator)
    # "Early" is the whole claim, and the wire is what proves it: the GET request went out and
    # nothing else did. Refused later, the initiator would have acknowledged the answer header
    # first and only then discovered the train it had just committed to could not satisfy it.
    assert len(frames(pair.wire_from_initiator(), _FRAME)) == 1, frames(pair.wire_from_initiator(), _FRAME)


@_on_poll_rounds
def test_an_answer_that_exactly_fills_its_train_arrives_intact() -> None:
    # A payload that exactly fills the chunks it needed fills its destination with no trimming left to do.
    payload = bytes(range(PAYLOAD_SIZE))  # exactly one data chunk, fully used
    pair = run(build_pair(get_callback=echo_get(payload), set_callback=accept_set()))
    answer = run(pair.with_listener(pair.initiator.uart_get(2)), limit=_RUN_BOUND_S)
    assert copied_out(answer) == payload, answer


def test_a_set_callback_returning_an_unusable_result_is_treated_like_a_raise() -> None:
    # The callback-return guard on the SET half. The GET half already had this; a set_callback's return is unpacked the
    # same way, so a bare None or a wrong-shaped tuple must be refused rather than indexed into.
    for bad in (None, "yes", (True,), (1, None)):
        pair = Pair(timeout=_SHORT_REPLY_TIMEOUT_MS, get_callback=echo_get(b""), set_callback=returns(bad))
        assert run(pair.setup()) is True

        async def scenario(link: Pair = pair) -> "tuple[bool, ListenResult]":
            listener = asyncio.create_task(link.responder.uart_listen())
            sent = await link.initiator.uart_set(1, b"ab")
            return sent, await asyncio.wait_for(listener, _STEP_BOUND_S)

        sent, result = run(scenario(), limit=_LISTENER_RUN_BOUND_S)
        assert sent is False, f"{bad!r} should not have been accepted"
        assert result.cmd_id is None


def test_a_declined_set_is_a_distinct_outcome_just_like_a_declined_get() -> None:
    # The SET half: the responder tells its own caller which kind of command it refused, and the
    # peer learns it by timing out - the same shape the GET half already had.
    pair = Pair(timeout=_SHORT_REPLY_TIMEOUT_MS, get_callback=echo_get(b""), set_callback=returns((False, None)))
    assert run(pair.setup()) is True

    async def scenario() -> "tuple[bool, ListenResult]":
        listener = asyncio.create_task(pair.responder.uart_listen())
        sent = await pair.initiator.uart_set(0x61, b"data")
        return sent, await asyncio.wait_for(listener, _STEP_BOUND_S)

    sent, result = run(scenario(), limit=_LISTENER_RUN_BOUND_S)
    assert sent is False
    assert result.cmd_id is None
    assert result.cmd == _CMD_SET  # which kind was refused is still reported
    assert persisted(pair.responder) == [_w("UART_CMD_DECLINED")], persisted(pair.responder)


def test_a_set_callback_asking_for_more_than_this_train_carries_is_refused() -> None:
    # Legal in the abstract but impossible for the CHUNKS that just arrived - refused at the header
    # rather than after a train that could never have satisfied it. The neighbouring check catches
    # a size no train could ever carry; this one is the per-train bound.
    pair = Pair(timeout=_SHORT_REPLY_TIMEOUT_MS, get_callback=echo_get(b""), set_callback=accept_set(PAYLOAD_SIZE + 1))
    assert run(pair.setup()) is True

    async def scenario() -> bool:
        listener = asyncio.create_task(pair.responder.uart_listen())
        sent = await pair.initiator.uart_set(1, b"ab")  # one data chunk, so PAYLOAD_SIZE at most
        await asyncio.wait_for(listener, _STEP_BOUND_S)
        return sent

    assert run(scenario(), limit=_LISTENER_RUN_BOUND_S) is False
    # Refused at the header, so the train's own frames were never accepted: one validated frame -
    # the SET header itself. Refused only at the end, the responder would have taken the data
    # chunk in and then discovered it could not have satisfied the size it had already asked for.
    assert pair.responder._valid_frames == 1, pair.responder._valid_frames


def test_a_listener_whose_callbacks_were_cleared_refuses_instead_of_dispatching() -> None:
    # Construction refuses a responder with no callbacks, but they are plain attributes an
    # owner can reassign, so uart_listen() re-checks what it is about to dispatch to.
    pair = run(build_pair(get_callback=echo_get(b""), set_callback=accept_set()))
    pair.responder._get_callback = None
    assert run(pair.responder.uart_listen()).cmd_id is None
    assert persisted(pair.responder) == [_e("BAD_ARG")], persisted(pair.responder)

def fail_write_after(fake: "Any", successes: int) -> None:
    # machine.py's own write_limit is a fixed per-call cap; these paths need the Nth write of an
    # exchange to fail instead, which is what a TX path dying mid-transaction actually looks like.
    # None is the real rp2 return: its internal per-byte timeout hit before anything was sent.
    real = fake.write
    left = [successes]

    def counted(buf: object) -> "int | None":
        if left[0] <= 0:
            return None
        left[0] -= 1
        return real(buf)  # type: ignore[no-any-return]

    fake.write = counted


@_on_poll_rounds
def test_a_write_failing_at_each_point_of_a_get_reports_and_resyncs() -> None:
    # Every writefrom() in the module is checked, and one GET passes through six: the request, its ACK, the
    # answer's header frame, the initiator's ACK for that, a mid-train ACK and the final one. All six report
    # UART_WRITE_FAILED and resync - a silent no-op write is what desynchronises the two sides.
    def get_with_a_failed_write(side: str, successes: int, answer: bytes) -> "tuple[PieceBuffer | None, list[str], bool]":
        pair = Pair(timeout=_SHORT_REPLY_TIMEOUT_MS, get_callback=echo_get(answer), set_callback=accept_set())
        assert run(pair.setup()) is True
        initiating = side == "initiator"
        fail_write_after(pair.fake_a if initiating else pair.fake_b, successes)
        # A write cut at any point can leave the responder's round unfinished; that is the case under test.
        got = run(pair.with_listener(pair.initiator.uart_get(1), listener_may_stall=True), limit=_LISTENER_RUN_BOUND_S)
        failing = pair.initiator if initiating else pair.responder
        return got, persisted(failing), failing._holdoff_active

    long_answer = bytes(PAYLOAD_SIZE + 1)  # three chunks, so there is a mid-train ACK to lose
    cases = (
        ("initiator", 0, b"ab", "the GET request itself"),
        ("responder", 0, b"ab", "the ACK for that request"),
        ("responder", 1, b"ab", "the answer's own header frame"),
        ("initiator", 1, b"ab", "the ACK for that header"),
        ("initiator", 2, b"ab", "the final ACK of a two-chunk answer"),
        ("initiator", 2, long_answer, "a mid-train ACK of a three-chunk answer"),
    )
    for side, successes, answer, what in cases:
        got, log, resynced = get_with_a_failed_write(side, successes, answer)
        assert got is None, what
        assert _e("UART_WRITE_FAILED") in log, (what, log)
        assert resynced is True, what  # every fault also resyncs, without exception


def test_a_responder_that_cannot_acknowledge_a_set_reports_and_resyncs() -> None:
    # The SET half of the same rule: the ACK for a SET's header is the one write a responder makes
    # before it has even asked its callback, so its failure must not read as a refused command.
    pair = Pair(timeout=_SHORT_REPLY_TIMEOUT_MS, get_callback=echo_get(b""), set_callback=accept_set())
    assert run(pair.setup()) is True
    fail_write_after(pair.fake_b, 0)

    async def scenario() -> "tuple[bool, ListenResult]":
        listener = asyncio.create_task(pair.responder.uart_listen())
        sent = await pair.initiator.uart_set(1, b"ab")
        return sent, await asyncio.wait_for(listener, _STEP_BOUND_S)

    sent, result = run(scenario(), limit=_LISTENER_RUN_BOUND_S)
    assert sent is False
    assert result.cmd is None  # _LISTEN_FAILED, not a refusal: nothing was ever asked
    assert persisted(pair.responder) == [_e("UART_WRITE_FAILED")], persisted(pair.responder)


@_on_poll_rounds
def test_a_peer_answering_a_different_question_is_refused() -> None:
    # Over the wire: the answer's first chunk echoes the command id, and an echo that does not
    # match is a desynced or confused peer - accepting it would hand the caller another command's
    # data under the id it actually asked for.
    pair = Pair(timeout=_SHORT_REPLY_TIMEOUT_MS, get_callback=echo_get(b"ab"), set_callback=accept_set())
    assert run(pair.setup()) is True
    real_send_train = pair.responder._send_train

    async def answers_the_wrong_question(
        device: "Any", cmd_id: int, payload: "Any", total: int, pull: "Any",
    ) -> bool:
        return await real_send_train(device, (cmd_id + 1) & 0xFF, payload, total, pull)

    pair.responder._send_train = answers_the_wrong_question  # type: ignore[method-assign]
    assert run(pair.with_listener(pair.initiator.uart_get(0x40)), limit=_LISTENER_RUN_BOUND_S) is None
    assert persisted(pair.initiator) == [_e("UART_GET_ID_MISMATCH")], persisted(pair.initiator)

class _StarvedAlloc:
    # Shadows asy_uart_comm.py's module-global `bytearray` - tests/'s usual reassign-a-module-name
    # mocking pointed at an allocation (SPECIFICATION.md Part E.4). Armed and one-shot, since every
    # degraded path allocates too; `skip` names the allocation to starve by position, not by count.
    def __init__(self) -> None:
        self.skip = 0
        self.armed = False
        self.fired = 0

    def arm(self, skip: int = 0) -> None:
        self.skip = skip
        self.armed = True

    def __call__(self, *args: "Any") -> bytearray:
        if self.armed:
            if self.skip:
                self.skip -= 1
            else:
                self.armed = False
                self.fired += 1
                raise MemoryError("starved")
        return bytearray(*args)

    def __enter__(self) -> "_StarvedAlloc":
        asy_uart_comm.bytearray = self  # type: ignore[attr-defined]
        return self

    def __exit__(self, *exc: object) -> None:
        asy_uart_comm.bytearray = bytearray  # type: ignore[attr-defined]


def test_a_scratch_allocation_that_fails_during_construction_refuses_the_object() -> None:
    # The real MemoryError behind the hand-starved refusal above, which substitutes _allocate()
    # wholesale and so never reaches its except clause: the three scratch buffers are guarded as
    # one group, and a heap that gives out between them leaves zero-length ones behind.
    with _StarvedAlloc() as starved:
        starved.arm()
        comm = make_comm()
    assert starved.fired == 1
    assert comm._init_errno == code("E", "ALLOC")
    assert run(comm.setup()) is False


def test_every_internal_buffer_read_rechecks_rather_than_indexing_none() -> None:
    # J.8 below the public entry points. The frame read, the ACK scratch, the drain and the
    # stream region each fetch their buffer again and answer with their own sentinel, because an
    # AttributeError here would land in the middle of a transaction in a never-raise module.
    def pull(chunk: int, buf: memoryview) -> int:
        return 0

    pair = run(build_pair(get_callback=echo_get(b""), set_callback=accept_set()))
    comm = pair.responder
    bus = comm._uart
    assert bus is not None
    comm._tx._buf = None
    comm._rx._buf = None
    comm._ack = bytearray(0)

    async def internals() -> "tuple[Any, Any, Any, Any]":
        async with bus as device:
            return (
                await comm._read_frame(device, 10),
                await comm._send_ack(device, 1),
                await comm._drain(device, first_ms=1),
                await comm._pull_chunk(device, pull, 2, 4, is_last=False),
            )

    frame, ack, drained, pulled = run(internals(), limit=_RUN_BOUND_S)
    assert frame is False
    assert ack is False
    assert drained == 0
    assert pulled is None
    # _pull_chunk aborts mid-train, so it resyncs like any other fault - the drain reads through
    # the same missing buffer and returns 0 rather than raising, which is the point.
    assert persisted(comm) == [_e("ALLOC")], persisted(comm)

def test_a_cancelled_transaction_still_releases_the_re_entrancy_flag() -> None:
    # _busy is cleared in a finally rather than on the return path, so a task cancelled while holding the
    # bus - a supervisor restart, or clear() unsticking a wedged link - does not leave the instance refusing
    # every later call as re-entrant. The flag is not the lock: `async with` releases that, not this.
    def pull(chunk: int, buf: memoryview) -> int:
        return 0

    pair = run(build_pair(get_callback=echo_get(b"v"), set_callback=accept_set()))
    initiator = pair.initiator
    bus = initiator._uart
    assert bus is not None
    pair.link.direction_from(pair.fake_b).silent = True  # nothing answers, so every call parks

    async def cancel_midway(work: "Any") -> None:
        task = asyncio.create_task(work)
        await asyncio.sleep_ms(_INSIDE_LOCK_MS)  # long enough to be inside the transaction, not before it
        # Asserted rather than assumed: cancelling a task that had not started yet would leave
        # _busy False for the trivial reason and read as a pass without testing anything.
        assert bus.session_lock.locked() is True, "the transaction was not in flight when cancelled"
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:  # expected; anything else is a real failure
            pass

    for work in (
        initiator.uart_set(1, b"x"),
        initiator.uart_set_stream(1, 4, pull),
        initiator.uart_get(1),
        initiator.uart_get_into(1, bytearray(16)),
    ):
        run(cancel_midway(work), limit=_SILENT_BOUND_S)
        assert initiator._busy is False, work
        # The lock is the more serious of the two: a leaked one is a permanently dead link, and it
        # would otherwise show only as the next iteration timing out rather than as a named failure.
        assert bus.session_lock.locked() is False, work

def test_two_declined_ids_in_rotation_do_not_refill_the_history_either() -> None:
    # Alternating declined ids are one code, W56: one slot, every refusal counted (C.7.1).
    pair = run(build_pair(timeout=_SHORT_REPLY_TIMEOUT_MS, get_callback=returns((False, None)), set_callback=accept_set()))
    for _ in range(6):
        for cmd_id in (0x42, 0x43):
            assert run(pair.with_listener(pair.initiator.uart_get(cmd_id)), limit=_STEP_BOUND_S) is None
    assert persisted(pair.responder) == [_w("UART_CMD_DECLINED")], persisted(pair.responder)
    assert run(pair.responder.get_error_counter())[pair.responder.name]["ErrCount"] == 12

    assert run(pair.with_listener(pair.initiator.uart_get(0x44)), limit=_STEP_BOUND_S) is None
    assert persisted(pair.responder) == [_w("UART_CMD_DECLINED")], persisted(pair.responder)
    run(pair.responder.reset_error_counter())
    assert run(pair.with_listener(pair.initiator.uart_get(0x42)), limit=_STEP_BOUND_S) is None
    assert persisted(pair.responder) == [_w("UART_CMD_DECLINED")], persisted(pair.responder)


@_on_poll_rounds
def test_a_pull_callback_failing_mid_train_quiesces_like_any_other_fault() -> None:
    # Chunk 1 is already sent and acknowledged by the time a pull callback is first asked for anything, so
    # every abort here leaves the peer mid-train: it drains for 1.5 x timeout while this side, without a
    # hold-off, is free to transmit into that window, where the drain swallows a real payload as a fault.
    def aborting_pull(kind: str) -> "Any":
        def pull(chunk: int, buf: memoryview) -> "Any":
            if chunk != 2:
                return len(buf)
            if kind == "short":
                return 1  # a short non-final chunk: UART_STREAM_SHORT
            if kind == "bool":
                return True  # not a byte count, and not an int on this runtime either (F.1)
            raise ValueError("callback exploded")  # CALLBACK through the guarded dispatch

        return pull

    for kind, errno in (("short", _e("UART_STREAM_SHORT")), ("bool", _e("CALLBACK")), ("raise", _e("CALLBACK"))):
        pair = Pair(timeout=_SHORT_REPLY_TIMEOUT_MS, get_callback=echo_get(b""), set_callback=accept_set())
        assert run(pair.setup()) is True

        async def scenario(link: Pair = pair, how: str = kind) -> bool:
            listener = asyncio.create_task(link.responder.uart_listen())
            try:
                return await link.initiator.uart_set_stream(0x50, 2 * PAYLOAD_SIZE, aborting_pull(how))
            finally:
                listener.cancel()
                try:
                    await listener
                except asyncio.CancelledError:  # expected; anything else is a real failure
                    pass

        assert run(scenario(), limit=_LISTENER_RUN_BOUND_S) is False, kind
        assert persisted(pair.initiator) == [errno], (kind, persisted(pair.initiator))
        assert pair.initiator._holdoff_active is True, kind

# ===========================================================================
# Conformance with the legacy BSEC use case (legacy/dev_drivers/asy_bsec_driver.py)
# ===========================================================================
# A demonstration, deliberately not a constraint - the module is standalone and this use case
# constrains nothing about its design (SPECIFICATION.md Part J.1). Sizes and command ids are the
# ones legacy/dev_drivers/sensortask-dev.py actually deployed.

_BSEC_GET_MEASUREMENTS = 0x20
_BSEC_GET_STATE = 0x21
_BSEC_GET_SYSTEM_STATE = 0x22
_BSEC_SET_START = 0x30
_BSEC_SET_STATE = 0x31
_BSEC_SET_RESET = 0x32
_BSEC_SET_TEMP_COMP = 0x33
_BSEC_SET_DEBUG = 0x34
_BSEC_DATAFIELDS = 13
_BSEC_STATE_SIZE = 221
_BSEC_PAYLOAD_SIZE = 20  # BME688_Reader's own default, not this module's
# "<" pins the layout: the Unix port is 64-bit, so a native "L" is 8 bytes there and 4 on the
# rp2040 - the legacy code's bare "bbbbL" against a hardcoded size of 8 only holds on the target.
_BSEC_SYSTEM_STATE = struct.pack("<bbbbL", 0, 0, 0, 0, 12345)
_BSEC_FIELD_VALUES = [1.5] * _BSEC_DATAFIELDS + [1, 1]  # the trailing pair is valid/new_data
_BSEC_MEASUREMENTS = struct.pack("<" + _BSEC_DATAFIELDS * "f" + "HH", *_BSEC_FIELD_VALUES)
_BSEC_STATE = bytes((i * 7) & 0xFF for i in range(_BSEC_STATE_SIZE))


@_on_poll_rounds
def test_the_legacy_bsec_command_set_still_runs_end_to_end() -> None:
    # All five shapes the legacy driver used, opcode and payload kept separate, every transaction
    # initiated from this side only (SPECIFICATION.md Part J.1). clear() is included because the
    # legacy reset ran SET -> wait -> clear -> read status, and the hold-off must not break that.
    answers = {
        _BSEC_GET_SYSTEM_STATE: _BSEC_SYSTEM_STATE,
        _BSEC_GET_MEASUREMENTS: _BSEC_MEASUREMENTS,
        _BSEC_GET_STATE: _BSEC_STATE,
    }
    accepted = (_BSEC_SET_START, _BSEC_SET_STATE, _BSEC_SET_RESET, _BSEC_SET_TEMP_COMP, _BSEC_SET_DEBUG)
    received: dict[int, bytes] = {}

    def peer_get(cmd_id: int) -> "tuple[bool, bytes | None]":
        return cmd_id in answers, answers.get(cmd_id)

    def peer_set(cmd_id: int) -> "tuple[bool, None]":
        return cmd_id in accepted, None

    pair = Pair(payload_size=_BSEC_PAYLOAD_SIZE, get_callback=peer_get, set_callback=peer_set)
    assert run(pair.setup()) is True
    bme = pair.initiator

    async def peer() -> None:
        while True:  # an idle uart_listen() waits forever by design, so the task is cancelled out
            result = await pair.responder.uart_listen()
            got = copied_out(result.payload)
            if result.cmd_id is not None and got is not None:
                received[result.cmd_id] = got

    async def system_status() -> "tuple[Any, ...] | None":
        res = copied_out(await bme.uart_get(_BSEC_GET_SYSTEM_STATE, exp_size=len(_BSEC_SYSTEM_STATE)))
        return None if res is None else struct.unpack("<bbbbL", res)

    async def scenario() -> "dict[str, Any]":
        listener = asyncio.create_task(peer())
        out: dict[str, Any] = {}
        try:
            out["status"] = await system_status()
            out["start"] = await bme.uart_set(_BSEC_SET_START, None)  # a command with no payload
            measurements = copied_out(await bme.uart_get(_BSEC_GET_MEASUREMENTS, exp_size=(4 * _BSEC_DATAFIELDS) + 4))
            out["measurements"] = None if measurements is None else struct.unpack("<" + _BSEC_DATAFIELDS * "f" + "HH", measurements)
            out["temp_comp"] = await bme.uart_set(_BSEC_SET_TEMP_COMP, struct.pack("<l", 21500))
            sized = await bme.uart_get(_BSEC_GET_STATE, exp_size=_BSEC_STATE_SIZE)
            out["state_sized"] = copied_out(sized)
            dont_care = await bme.uart_get(_BSEC_GET_STATE)  # the FRAM size was not always known
            out["state_dont_care"] = copied_out(dont_care)
            out["set_state"] = await bme.uart_set(_BSEC_SET_STATE, _BSEC_STATE)
            out["debug"] = await bme.uart_set(_BSEC_SET_DEBUG, struct.pack("<b", 1))
            out["reset"] = await bme.uart_set(_BSEC_SET_RESET, None)
            await bme.clear()  # the legacy reset sequence's own unstick, hold-off and all
            out["status_after_clear"] = await system_status()
        finally:
            listener.cancel()
            try:
                await listener
            except asyncio.CancelledError:  # expected; anything else is a real failure
                pass
        return out

    out = run(scenario(), limit=_BSEC_RUN_BOUND_S)
    assert out["status"] == (0, 0, 0, 0, 12345), out["status"]
    assert out["start"] is True
    assert out["measurements"] == tuple(_BSEC_FIELD_VALUES), out["measurements"]
    assert out["temp_comp"] is True
    assert out["state_sized"] == _BSEC_STATE, "a 221-byte answer must arrive byte-identical"
    assert out["state_dont_care"] == _BSEC_STATE, "and identically without a declared size"
    assert out["set_state"] is True
    assert out["debug"] is True
    assert out["reset"] is True
    assert out["status_after_clear"] == (0, 0, 0, 0, 12345), "clear() must not break what follows"
    # The opcode reached the peer as its own field, and the payload arrived beside it intact.
    assert received[_BSEC_SET_STATE] == _BSEC_STATE
    assert struct.unpack("<l", received[_BSEC_SET_TEMP_COMP])[0] == 21500
    assert _BSEC_SET_START not in received, "a payload-less command carries no payload"


@_on_poll_rounds
def test_the_two_spellings_the_boards_own_uart_script_used_still_work() -> None:
    # legacy/dev_drivers/ext_uart.py, the exploratory script found on the board, exercised two shapes
    # the BSEC driver does not: a GET declaring an expected size of exactly zero - an answer that must be
    # empty, a different claim from "don't care" - and a SET whose payload is an empty bytearray, not None.
    pair = run(build_pair(get_callback=echo_get(b""), set_callback=accept_set(0)))
    empty = run(pair.with_listener(pair.initiator.uart_get(0x3C, exp_size=0)), limit=_RUN_BOUND_S)
    assert empty is not None and len(empty) == 0, empty  # empty, not None (J.9)

    async def scenario() -> bool:
        listener = asyncio.create_task(pair.responder.uart_listen())
        sent = await pair.initiator.uart_set(0x30, bytearray())
        await asyncio.wait_for(listener, _LISTENER_SHORT_BOUND_S)
        return sent

    assert run(scenario(), limit=_LISTENER_RUN_BOUND_S) is True, "an empty bytearray is as good a payload as None"

    # And the rejection half: a peer answering a zero-size GET with data is refused, not delivered.
    loud = run(build_pair(get_callback=echo_get(b"data"), set_callback=accept_set()))
    assert run(loud.with_listener(loud.initiator.uart_get(0x3C, exp_size=0)), limit=_RUN_BOUND_S) is None


def test_the_legacy_bsec_bus_parameters_meet_every_floor_but_one() -> None:
    # The one value a legacy-faithful port has to change: the deployed rxbuf of 32 clears J.6's
    # 27-byte whole-frame floor but not its 80-byte per-poll floor. Kept rather than relaxed (agent, 2026-09-13), a
    # drain must survive a peer that does not stop (SPECIFICATION.md Part J.1).
    def deployed(rxbuf: int) -> UARTComm:
        bus = UART(0, tx_pin=0, rx_pin=1, baudrate=115200, rxbuf=rxbuf, poll_wait_ms=2, poll_idle_ms=50, crc=CRC16())
        bus.poller = LinkPoller(bus._uart)  # type: ignore[assignment,arg-type]
        return UARTComm(bus, ROLE_INITIATOR, limits=transfer_limits(payload_size=_BSEC_PAYLOAD_SIZE, timeout=1000))

    assert deployed(256)._min_rxbuf() == 80
    assert deployed(32)._init_errno == code("E", "UART_RXBUF"), "the deployed value is refused, not accepted quietly"
    assert deployed(64)._init_errno == code("E", "UART_RXBUF")
    assert deployed(128)._init_errno == 0
    # Everything else the legacy link declared is accepted unchanged: 115200 baud, a 1000ms reply
    # budget, payload_size 20, and a CRC16 underneath the protocol.
    assert deployed(128)._payload_size == _BSEC_PAYLOAD_SIZE


def test_a_drain_that_cannot_run_clears_the_previous_drains_verdict() -> None:
    # _drain()'s verdict outlives the call - the resync that called it reads it afterwards - so it is
    # cleared before the early return, not after. A construction whose RX buffer failed is the only
    # way to reach that return, and it must not hand the next resync the last drain's answer.
    comm = make_comm()
    comm._drain_bound_hit = True
    comm._rx = RegionBuffer(-1)  # a failed allocation, which is what hands its owner None
    assert comm._rx.get_buf() is None  # the early return really is the path taken
    assert run(comm._drain(comm._uart)) == 0  # type: ignore[arg-type]
    assert comm._drain_bound_hit is False


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
