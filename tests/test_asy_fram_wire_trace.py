"""Golden wire traces for the FRAM path: every SPI.init(), every CS edge and every transfer's bytes, recorded from the real src/ chain against tests/_fram_chip_fake.py's chip.
A restructure of asy_spi_driver.py/asy_fram_driver.py/asy_fram_manager.py must leave these byte-identical - that is the contract HEAP_REMEDIATION_PLAN.md section 0 puts before any of its work."""
# The recorder decomposes a trace into CS cycles. Every cycle is asserted to be framed by exactly
# one SPI.init() at the fixed bus config and one CS low/high pair, so the goldens below need hold
# only the transfers inside each cycle - the envelope is checked, not dropped (see _cycles()).

import asyncio

import machine
from _fram_chip_fake import FakeMB85RS64V

import asy_spi_driver
from asy_fram_driver import FRAM_SPI
from asy_fram_manager import AsyFramManager, AsyFramTimestampedChunk
from asy_spi_driver import SPI
from crc_checks import CRC32
from print_log import PrintLogHistoryStore

# Same one-process-per-test-file swap as the other asy_fram_* test files - see their own comments.
asy_spi_driver._SPI = FakeMB85RS64V  # type: ignore[misc]

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Coroutine
    from typing import Any, TypeVar

    T = TypeVar("T")

# The one bus config SPIDevice.__aenter__ applies, as one recorded event. Every CS cycle carries it.
_INIT_EVENT = "init 1000000/0/0/8/0"
_WRDI = b"\x04"  # asy_fram_driver.py's own _SPI_OPCODE_WRDI is a const() and so not importable


def run(coro: "Coroutine[Any, Any, T]") -> "T":  # drives a coroutine to completion for these sync test_* functions
    return asyncio.run(coro)


# --------------------------------------------------------------------------- bus recorder
# Patched in permanently at import and inert while _TRACE is None, so an untraced preparation step
# costs nothing. Only the FRAM SPIDevice's own CS pin is watched - a WP edge is not a CS edge.
_TRACE: "list[str] | None" = None
_CS_PIN: "machine.Pin | None" = None

# write()/readinto() are FakeMB85RS64V's own overrides; write_readinto()/init() are machine.SPI's,
# so each wrapper's `self` must be annotated as the class the real method is declared on.
_ORIG_WRITE = FakeMB85RS64V.write
_ORIG_READINTO = FakeMB85RS64V.readinto
_ORIG_WRITE_READINTO = FakeMB85RS64V.write_readinto
_ORIG_INIT = FakeMB85RS64V.init
_ORIG_PIN_VALUE = machine.Pin.value


def _hex(buf: object) -> str:
    return "".join(f"{b:02x}" for b in bytes(buf))  # type: ignore[call-overload]


def _rec_write(self: FakeMB85RS64V, buf: object) -> None:
    if _TRACE is not None:
        _TRACE.append("w:" + _hex(buf))
    _ORIG_WRITE(self, buf)


def _rec_readinto(self: FakeMB85RS64V, buf: "bytearray | memoryview", _write_value: int = 0x00) -> None:
    _ORIG_READINTO(self, buf, _write_value)  # recorded after the call: the bytes received are the event
    if _TRACE is not None:
        _TRACE.append("r:" + _hex(buf))


def _rec_write_readinto(self: machine.SPI, buffer_out: object, buffer_in: "bytearray | memoryview") -> None:
    _ORIG_WRITE_READINTO(self, buffer_out, buffer_in)
    if _TRACE is not None:
        _TRACE.append("x:" + _hex(buffer_out) + ":" + _hex(buffer_in))


def _rec_init(
    self: machine.SPI,
    baudrate: int = -1,
    *,
    polarity: int = -1,
    phase: int = -1,
    bits: int = -1,
    firstbit: int = -1,
) -> None:
    if _TRACE is not None:
        _TRACE.append(f"init {baudrate}/{polarity}/{phase}/{bits}/{firstbit}")
    _ORIG_INIT(self, baudrate, polarity=polarity, phase=phase, bits=bits, firstbit=firstbit)


def _rec_pin_value(self: machine.Pin, x: object = None) -> "int | None":
    if _TRACE is not None and _CS_PIN is not None and self is _CS_PIN and x is not None:
        _TRACE.append("cs1" if x else "cs0")  # active-low CS: value(False) asserts it
    return _ORIG_PIN_VALUE(self, x)


FakeMB85RS64V.write = _rec_write  # type: ignore[method-assign]
FakeMB85RS64V.readinto = _rec_readinto  # type: ignore[method-assign]
FakeMB85RS64V.write_readinto = _rec_write_readinto  # type: ignore[method-assign]
FakeMB85RS64V.init = _rec_init  # type: ignore[method-assign]
machine.Pin.value = _rec_pin_value  # type: ignore[method-assign]


def _cycles(trace: "list[str]") -> "tuple[str, ...]":
    # Envelope invariant, asserted rather than assumed: the stream is exactly repeated
    # (init, CS low, transfers..., CS high) groups, with the same bus config every time and no
    # transfer outside a CS window. What survives into the golden is each group's transfers.
    out = []
    i = 0
    while i < len(trace):
        assert trace[i] == _INIT_EVENT, f"event {i}: expected {_INIT_EVENT!r}, got {trace[i]!r}"
        assert i + 1 < len(trace) and trace[i + 1] == "cs0", f"event {i + 1}: CS was not asserted after init"
        i += 2
        group = []
        while i < len(trace) and trace[i] != "cs1":
            assert trace[i][:2] in ("w:", "r:", "x:"), f"event {i}: unexpected {trace[i]!r} inside a CS window"
            group.append(trace[i])
            i += 1
        assert i < len(trace), "trace ended with CS still asserted"
        i += 1
        out.append(" ".join(group))
    return tuple(out)


def _arm(manager: AsyFramManager) -> None:
    global _TRACE, _CS_PIN
    _CS_PIN = manager.fram._spidev.cs_pin
    _TRACE = []


def _disarm() -> "tuple[tuple[str, ...], int]":
    # Returns the per-CS-cycle golden form and the raw recorded event count, so a test can confirm
    # the compact form accounts for every single event rather than quietly summarising them.
    global _TRACE
    trace = _TRACE
    _TRACE = None
    assert trace is not None
    return _cycles(trace), len(trace)


# --------------------------------------------------------------------------- rig
async def _never_synced() -> bool:
    return False  # a fixed, unsynced clock keeps every timestamped trace deterministic


async def _rig() -> "tuple[AsyFramManager, PrintLogHistoryStore, AsyFramTimestampedChunk]":
    # The production shape section 3B priced: one manager, a PrintLogHistoryStore allocated first
    # (SensorReader's own order) and a separate timestamped value chunk second.
    bus = SPI(0, sck_pin=2, mosi_pin=3, miso_pin=4)
    manager = AsyFramManager(bus, 1, max_size=0x2000, debug=None)
    assert await manager.setup()
    logger = PrintLogHistoryStore(manager, 10, None, name="WT")
    chunk = manager.get_timestamped_chunk(8, _never_synced, crc=CRC32())
    assert chunk is not None
    return manager, logger, chunk


# --------------------------------------------------------------------------- goldens
# One line per CS cycle's transfers, in order; w: write, r: bytes a read received, x: full-duplex.
# Opcodes: 06 WREN, 04 WRDI, 05 RDSR, 02 WRITE, 03 READ, 9f RDID, 01 WRSR.
_GOLDEN_BLANK_SETUP = """\
w:03000d r:00
w:06
w:05 r:02
w:02000d w:02
w:04
w:05 r:00
w:03000e r:00
w:06
w:05 r:02
w:02000e w:02
w:04
w:05 r:00
w:03001c r:00
w:06
w:05 r:02
w:02001c w:02
w:04
w:05 r:00
w:03001d r:00
w:06
w:05 r:02
w:02001d w:02
w:04
w:05 r:00
w:06
w:05 r:02
w:02000d w:02
w:04
w:05 r:00
w:06
w:05 r:02
w:02000e w:02
w:04
w:05 r:00
w:06
w:05 r:02
w:020000 w:00000000000000000000000039
w:04
w:05 r:00
w:06
w:05 r:02
w:02000d w:01
w:04
w:05 r:00
w:06
w:05 r:02
w:02000e w:01
w:04
w:05 r:00
w:06
w:05 r:02
w:02001c w:02
w:04
w:05 r:00
w:06
w:05 r:02
w:02001d w:02
w:04
w:05 r:00
w:06
w:05 r:02
w:02000f w:00000000000000000000000039
w:04
w:05 r:00
w:06
w:05 r:02
w:02001c w:01
w:04
w:05 r:00
w:06
w:05 r:02
w:02001d w:01
w:04
w:05 r:00
"""

_GOLDEN_VALID_SETUP = """\
w:03000d r:01
w:06
w:05 r:02
w:02000d w:02
w:04
w:05 r:00
w:03000e r:01
w:06
w:05 r:02
w:02000e w:02
w:04
w:05 r:00
w:030000 r:00000000000000000000000039
w:06
w:05 r:02
w:02000d w:01
w:04
w:05 r:00
w:06
w:05 r:02
w:02000e w:01
w:04
w:05 r:00
w:03001c r:01
w:06
w:05 r:02
w:02001c w:02
w:04
w:05 r:00
w:03001d r:01
w:06
w:05 r:02
w:02001d w:02
w:04
w:05 r:00
w:03000f r:0000000000000000
w:030017 r:0000000039
w:06
w:05 r:02
w:02001c w:01
w:04
w:05 r:00
w:06
w:05 r:02
w:02001d w:01
w:04
w:05 r:00
"""

_GOLDEN_TS_WRITE_INTO = """\
w:06
w:05 r:02
w:020032 w:02
w:04
w:05 r:00
w:06
w:05 r:02
w:020033 w:02
w:04
w:05 r:00
w:06
w:05 r:02
w:02001e w:00000000000000001122334455667788e6962c5c
w:04
w:05 r:00
w:06
w:05 r:02
w:020032 w:01
w:04
w:05 r:00
w:06
w:05 r:02
w:020033 w:01
w:04
w:05 r:00
w:06
w:05 r:02
w:020048 w:02
w:04
w:05 r:00
w:06
w:05 r:02
w:020049 w:02
w:04
w:05 r:00
w:06
w:05 r:02
w:020034 w:00000000000000001122334455667788e6962c5c
w:04
w:05 r:00
w:06
w:05 r:02
w:020048 w:01
w:04
w:05 r:00
w:06
w:05 r:02
w:020049 w:01
w:04
w:05 r:00
"""

_GOLDEN_TS_READ_INTO = """\
w:030032 r:01
w:06
w:05 r:02
w:020032 w:02
w:04
w:05 r:00
w:030033 r:01
w:06
w:05 r:02
w:020033 w:02
w:04
w:05 r:00
w:03001e r:00000000000000001122334455667788e6962c5c
w:06
w:05 r:02
w:020032 w:01
w:04
w:05 r:00
w:06
w:05 r:02
w:020033 w:01
w:04
w:05 r:00
w:030048 r:01
w:06
w:05 r:02
w:020048 w:02
w:04
w:05 r:00
w:030049 r:01
w:06
w:05 r:02
w:020049 w:02
w:04
w:05 r:00
w:030034 r:0000000000000000
w:03003c r:1122334455667788
w:030044 r:e6962c5c
w:06
w:05 r:02
w:020048 w:01
w:04
w:05 r:00
w:06
w:05 r:02
w:020049 w:01
w:04
w:05 r:00
"""

_GOLDEN_CLEAR = """\
w:06
w:05 r:02
w:020032 w:00
w:04
w:05 r:00
w:06
w:05 r:02
w:020033 w:00
w:04
w:05 r:00
w:06
w:05 r:02
w:02001e w:0000000000000000000000000000000000000000
w:04
w:05 r:00
w:06
w:05 r:02
w:020048 w:00
w:04
w:05 r:00
w:06
w:05 r:02
w:020049 w:00
w:04
w:05 r:00
w:06
w:05 r:02
w:020034 w:0000000000000000000000000000000000000000
w:04
w:05 r:00
"""


async def _collect() -> "dict[str, tuple[tuple[str, ...], int]]":
    # One rig, five recordings, in the order that makes each one's chip state what it must be:
    # the blank setup leaves a valid pair behind, which is exactly what the valid setup then reads.
    manager, logger, chunk = await _rig()
    out: dict[str, tuple[tuple[str, ...], int]] = {}

    _arm(manager)
    await logger.setup()  # blank chip: _read() finds no valid copy, _write() lays both down
    out["blank"] = _disarm()

    logger.initialized = False
    _arm(manager)
    await logger.setup()  # the chip now carries a valid pair, so _read() succeeds and _write() never runs
    out["valid"] = _disarm()

    buf = chunk.get_buffer()
    dbuf = buf.get_data_buf()
    assert dbuf is not None
    dbuf[:] = b"\x11\x22\x33\x44\x55\x66\x77\x88"

    _arm(manager)
    written = await chunk.write_into(buf)
    out["ts_write"] = _disarm()
    assert written[2]  # (ntp_synced, utc, wrote_ok) - the clock is deliberately unsynced

    _arm(manager)
    read = await chunk.read_into(buf)
    out["ts_read"] = _disarm()
    assert read[0]

    _arm(manager)
    cleared = await chunk.clear()
    out["clear"] = _disarm()
    assert cleared

    return out


def _golden(text: str) -> "tuple[str, ...]":
    return tuple(text.strip().split("\n"))


def _assert_trace(name: str, got: "tuple[str, ...]", want: "tuple[str, ...]") -> None:
    for i in range(min(len(got), len(want))):
        assert got[i] == want[i], f"{name}: CS cycle {i} changed - recorded {got[i]!r}, golden {want[i]!r}"
    assert len(got) == len(want), f"{name}: {len(got)} CS cycles recorded, golden has {len(want)}"


# --------------------------------------------------------------------------- the traces themselves
def test_blank_setup_wire_trace_matches_the_golden() -> None:
    _assert_trace("blank setup", run(_collect())["blank"][0], _golden(_GOLDEN_BLANK_SETUP))


def test_valid_setup_wire_trace_matches_the_golden() -> None:
    _assert_trace("valid setup", run(_collect())["valid"][0], _golden(_GOLDEN_VALID_SETUP))


def test_timestamped_write_into_wire_trace_matches_the_golden() -> None:
    _assert_trace("timestamped write_into", run(_collect())["ts_write"][0], _golden(_GOLDEN_TS_WRITE_INTO))


def test_timestamped_read_into_wire_trace_matches_the_golden() -> None:
    _assert_trace("timestamped read_into", run(_collect())["ts_read"][0], _golden(_GOLDEN_TS_READ_INTO))


def test_timestamped_clear_wire_trace_matches_the_golden() -> None:
    _assert_trace("clear", run(_collect())["clear"][0], _golden(_GOLDEN_CLEAR))


# --------------------------------------------------------------------------- the shape of the traces
def test_cs_cycle_counts_are_the_measured_figures() -> None:
    # The headline numbers HEAP_FRAGMENTATION_MEASUREMENTS.md section 3B prices the FRAM path by.
    # Every one of these cycles is required by the chip; the restructure removes allocations, not
    # CS cycles, so a change here is a protocol change and not an optimisation.
    traces = run(_collect())
    assert len(traces["blank"][0]) == 74
    assert len(traces["valid"][0]) == 47
    assert len(traces["ts_write"][0]) == 50
    assert len(traces["ts_read"][0]) == 48
    assert len(traces["clear"][0]) == 30


def test_compact_goldens_account_for_every_recorded_event() -> None:
    # Guards the golden form itself: each CS cycle contributes its init, its two CS edges and its
    # own transfers, so the per-cycle goldens above cover the raw event stream with nothing elided.
    for name, (cycles, events) in run(_collect()).items():
        counted = sum(3 + len(cycle.split()) for cycle in cycles)
        assert counted == events, f"{name}: {counted} events in the golden form, {events} recorded"


def test_a_single_dropped_wrdi_breaks_the_blank_golden() -> None:
    # The golden's whole purpose, checked rather than assumed: one command removed from the wire
    # must fail it. The chip auto-clears WEL after a WRITE, so the skipped WRDI's own verification
    # still passes - the only trace left of it is the missing CS cycle, which is the point.
    original = FRAM_SPI._send_command
    dropped: list[int] = []

    def _drop_first_wrdi(self: FRAM_SPI, command: "bytes | bytearray") -> None:
        if bytes(command) == _WRDI and not dropped:
            dropped.append(_WRDI[0])
            return
        original(self, command)

    async def _body() -> "tuple[str, ...]":
        manager, logger, _chunk = await _rig()  # built before the patch: setup() stays untouched
        FRAM_SPI._send_command = _drop_first_wrdi  # type: ignore[method-assign]
        try:
            _arm(manager)
            await logger.setup()
            return _disarm()[0]
        finally:
            FRAM_SPI._send_command = original  # type: ignore[method-assign]

    got = run(_body())
    assert dropped == [_WRDI[0]]
    assert got != _golden(_GOLDEN_BLANK_SETUP)



if __name__ == "__main__":
    import microtest

    microtest.run(globals())
