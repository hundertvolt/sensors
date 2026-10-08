"""Connection-level tests of src/asy_webserver_service.py: every dropped connection counted once in the 24-hour window,
the request-head guard against adversarial clients, the bounded server start, and client faults that print nothing
at DebugLevel 0 (SPECIFICATION.md A.5, A.8). Own stream, clock and server doubles; never a real select.poll()."""

import asyncio
import errno
import json
import socket
import sys
import time

# scripts/test.sh's MICROPYPATH leaves ext/ out; the real vendored ext/microdot.py is reached through this entry.
sys.path.insert(0, "ext")

import microdot
from _error_codes import code
from microdot import Microdot, Request

import asy_print_log
import asy_webserver_service
from asy_print_log import LogConfig
from asy_webserver_service import RouteSources, ServingLimits, WebserverService

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Coroutine, Sequence
    from typing import TypeVar

    import asy_config_manager as cm
    from asy_base_classes import JsonDict, JsonMapping
    from asy_print_log import ErrorLog
    from asy_webserver_service import _ModuleLike

    T = TypeVar("T")
    Sleep = Callable[[float], Awaitable[None]]


def _src_const(name: str) -> str:
    # The shipped value's literal, read from the source: a const() name is no module attribute on MicroPython.
    with open("src/asy_webserver_service.py") as f:
        for line in f:
            if line.startswith(name + " = const("):
                literal: str = line.split("const(", 1)[1].split(")", 1)[0]
                return literal
    raise AssertionError(name + " not found in src/asy_webserver_service.py")


_CHUNK_BYTES = int(_src_const("_DEFAULT_CHUNK_BYTES"))
_MAX_CONNECTIONS = int(_src_const("_DEFAULT_MAX_CONNECTIONS"))
_MAX_CONTENT_LENGTH = int(_src_const("_DEFAULT_MAX_CONTENT_LENGTH"))
_MAX_HEADER_LINES = int(_src_const("_MAX_HEADER_LINES"))
_MAX_HEAD_BYTES = int(_src_const("_MAX_HEAD_BYTES"))
_START_RETRIES = int(_src_const("_START_RETRIES"))
_START_RETRY_S = int(_src_const("_START_RETRY_S"))

_W_PEER_RESET = code("W", "HTTP_PEER_RESET")
_W_CALL_TIMEOUT = code("W", "HTTP_CALL_TIMEOUT")
_W_REQUEST_CAP = code("W", "HTTP_REQUEST_CAP")
_W_SOCKET_ERROR = code("W", "HTTP_SOCKET_ERROR")
_W_REFUSED = code("W", "HTTP_REFUSED")
_W_BAD_HEAD = code("W", "HTTP_BAD_HEAD")
_W_START_FAILED = code("W", "HTTP_START_FAILED")
_E_UNEXPECTED = code("E", "UNEXPECTED")

_HOUR_S = 3600  # the drop window's bin width; keep in sync with src/asy_base_classes.py's _HOUR_S
_STEP_S = 0.005  # the driven clock's advance per scheduler round: a whole request takes well under 0.5 s of it

# This file's own TCP block, below the ephemeral range and clear of every other file's base (SPECIFICATION.md E.1):
# the Unix port has no getsockname(), so a port-0 bind could not be read back.
_PORT_BASE = 18600
_next_port = _PORT_BASE


def _port() -> int:
    global _next_port
    _next_port += 1
    return _next_port


def run(coro: "Coroutine[object, object, T]", limit_s: float = 30.0) -> "T":
    # Bounded in real time, so a defect under test fails fast instead of stalling the suite.
    return asyncio.run(asyncio.wait_for(coro, limit_s))


# ---------------------------------------------------------------------------
# Doubles: streams, the uptime and asyncio's timers, the server start, and the console.
# ---------------------------------------------------------------------------


class _OneStream:
    # MicroPython hands start_server()'s callback one Stream as reader and writer; each double plays one half and
    # fails loudly on a call _serve() never makes on that half.
    def get_extra_info(self, name: str) -> object:
        raise AssertionError("get_extra_info() on the reader half")

    async def aclose(self) -> None:
        raise AssertionError("aclose() on the reader half")

    async def awrite(self, data: bytes) -> None:
        raise AssertionError("awrite() on the reader half")

    def close(self) -> None:
        raise AssertionError("close() on the reader half")

    async def read(self, n: int) -> bytes:
        raise AssertionError("read() on the writer half")

    async def readexactly(self, n: int) -> bytes:
        raise AssertionError("readexactly() on the writer half")

    async def wait_closed(self) -> None:
        raise AssertionError("wait_closed() on the reader half")


async def _no_delay(_t: float) -> None:
    pass


class _Reader(_OneStream):
    # A client's bytes as (delay, chunk) steps on the given sleep; records every read() and readexactly() size. At the
    # script's end it reads as a clean close (eof=True) or hangs as a wedged client would.
    def __init__(self, steps: "list[tuple[float, bytes]]", *, eof: bool = True, sleep: "Sleep" = _no_delay) -> None:
        self._steps = list(steps)
        self._buf = b""
        self._eof = eof
        self._sleep = sleep
        self.read_sizes: list[int] = []
        self.readexactly_sizes: list[int] = []

    async def _pull(self) -> bool:
        if not self._steps:
            if not self._eof:
                await asyncio.Event().wait()  # never set: only a timeout ends this read
            return False
        delay, chunk = self._steps.pop(0)
        if delay:
            await self._sleep(delay)
        self._buf += chunk
        return True

    async def read(self, n: int) -> bytes:
        self.read_sizes.append(n)
        if not self._buf and not await self._pull():
            return b""  # a clean close, as Stream.read() returns it
        data, self._buf = self._buf[:n], self._buf[n:]
        return data

    async def readexactly(self, n: int) -> bytes:
        self.readexactly_sizes.append(n)
        while len(self._buf) < n:
            if not await self._pull():
                raise EOFError  # as extmod/asyncio/stream.py's Stream.readexactly()
        data, self._buf = self._buf[:n], self._buf[n:]
        return data


class _GateReader(_OneStream):
    # Holds its connection's slot until the test opens the gate, then reads as a close before any byte.
    def __init__(self, gate: "asyncio.Event") -> None:
        self._gate = gate

    async def read(self, n: int) -> bytes:
        await self._gate.wait()
        return b""


class _ResetReader(_OneStream):
    # A peer that reset mid-request: modlwip raises ECONNRESET on the read.
    async def read(self, n: int) -> bytes:
        raise OSError(errno.ECONNRESET)


class _Writer(_OneStream):
    # Records each awrite() the client receives; from write index fail_at on, raises fail_with or, without one, hangs.
    def __init__(self, *, fail_at: int | None = None, fail_with: Exception | None = None) -> None:
        self.writes: list[bytes] = []
        self.attempts = 0
        self.closed = False
        self._fail_at = fail_at
        self._fail_with = fail_with

    def get_extra_info(self, name: str) -> object:
        return ("127.0.0.1", 54321) if name == "peername" else None

    async def aclose(self) -> None:
        self.closed = True

    async def awrite(self, data: bytes) -> None:
        index = self.attempts
        self.attempts += 1
        if self._fail_at is not None and index >= self._fail_at:
            if self._fail_with is None:
                await asyncio.Event().wait()  # never set: only the per-call timeout ends this write
            else:
                raise self._fail_with
        self.writes.append(bytes(data))

    def close(self) -> None:
        self.closed = True

    async def wait_closed(self) -> None:
        pass

    @property
    def written(self) -> bytes:
        return b"".join(self.writes)


class _EagainWriter(_Writer):
    # write() + drain() as extmod/asyncio/stream.py runs them over lwIP's full send queue: each attempt is one
    # scheduler round (POLLOUT answers at once) and a refused send returns None; no poller is registered (CLAUDE.md).
    def __init__(self, eagain_attempts: int) -> None:
        super().__init__()
        self._eagain_left = eagain_attempts
        self.send_attempts = 0

    def _send(self, mv: memoryview) -> int | None:
        self.send_attempts += 1
        if self._eagain_left > 0:
            self._eagain_left -= 1
            return None  # EAGAIN: py/stream.c answers None for a non-blocking send that would block
        self.writes.append(bytes(mv))
        return len(mv)

    async def awrite(self, data: bytes) -> None:
        mv = memoryview(bytes(data))
        off = 0
        while off < len(mv):
            await asyncio.sleep(0)
            sent = self._send(mv[off:])
            if sent is not None:
                off += sent


class _Uptime:
    # The device's SysUptime reader, driven by the test: the drop window moves only when `now` does.
    def __init__(self) -> None:
        self.now = 0

    async def read(self) -> int:
        return self.now


class _Timer:
    # One pending deadline on the driven clock, and what reaching it does: set a sleep's event or cancel a bounded task.
    def __init__(self, deadline: float, wake: "Callable[[], object]") -> None:
        self.deadline = deadline
        self.wake = wake
        self.fired = False


class _DrivenClock:
    # The file's own time double: virtual seconds that move only in _driven(), each due sleep or wait_for() bound firing
    # as they pass, so the order of two deadlines is fixed by the test, never by the host's speed or scheduling.
    def __init__(self) -> None:
        self.now = 0.0
        self._timers: list[_Timer] = []

    def _add(self, delay: float, wake: "Callable[[], object]") -> _Timer:
        timer = _Timer(self.now + delay, wake)
        self._timers.append(timer)
        return timer

    def _drop(self, timer: _Timer) -> None:
        if timer in self._timers:
            self._timers.remove(timer)

    def advance(self, step_s: float) -> None:
        self.now += step_s
        for timer in [t for t in self._timers if t.deadline <= self.now]:
            self._timers.remove(timer)
            timer.fired = True
            timer.wake()

    async def sleep(self, t: float) -> None:
        event = asyncio.Event()
        timer = self._add(t, event.set)
        try:
            await event.wait()
        finally:
            self._drop(timer)

    async def wait_for(self, aw: "Coroutine[object, object, T]", timeout: float) -> "T":
        # asyncio.wait_for()'s contract on this clock: aw's result or exception, else aw cancelled and TimeoutError at the
        # deadline; a cancel of the caller reaches aw too, as Task.cancel() forwards it (extmod/asyncio/task.py).
        task = asyncio.create_task(aw)
        timer = self._add(timeout, task.cancel)
        try:
            return await task
        except asyncio.CancelledError:
            if timer.fired:
                raise asyncio.TimeoutError from None
            raise
        finally:
            self._drop(timer)


async def _driven(clock: _DrivenClock, coro: "Coroutine[object, object, T]") -> "T":
    # Runs coro while the clock advances one step per scheduler round.
    task = asyncio.create_task(coro)
    while not task.done():
        await asyncio.sleep_ms(0)
        clock.advance(_STEP_S)
    return await task


_ASYNCIO_NAMES = ("CancelledError", "Event", "Task", "TimeoutError", "create_task", "gather", "get_event_loop", "sleep", "sleep_ms", "start_server", "wait_for")


class _AsyncioStandIn:
    # The module's `asyncio` global for one test: the real names as instance attributes (so none binds as a method),
    # with the timers or start_server the test replaces; uninstall() puts the module back.
    def __init__(self, **replaced: object) -> None:
        assert set(replaced) <= set(_ASYNCIO_NAMES), sorted(replaced)
        for name in _ASYNCIO_NAMES:
            setattr(self, name, replaced[name] if name in replaced else getattr(asyncio, name))
        asy_webserver_service.asyncio = self  # type: ignore[assignment]  # a namespace of the module's names, not a module

    def uninstall(self) -> None:
        asy_webserver_service.asyncio = asyncio


class _ServerStub:
    def __init__(self) -> None:
        self.waited = False

    async def wait_closed(self) -> None:
        self.waited = True


class _StartServer:
    # asyncio.start_server()'s double: raises each scripted failure in turn, then returns a server whose
    # wait_closed() ends at once; sleep() records each retry delay and yields one round.
    def __init__(self, failures: "list[Exception]") -> None:
        self._failures = list(failures)
        self.calls = 0
        self.delays: list[float] = []
        self.server = _ServerStub()

    async def sleep(self, t: float) -> None:
        self.delays.append(t)
        await asyncio.sleep_ms(0)

    async def start_server(self, cb: object, host: str, port: int, backlog: int = 5) -> _ServerStub:
        self.calls += 1
        if self._failures:
            raise self._failures.pop(0)
        return self.server


def _microdot_print_exception() -> object:
    return microdot.print_exception  # type: ignore[attr-defined]  # the vendored stub declares no print_exception


class _Console:
    # Shadows print() in asy_print_log (every logger and console() line) and microdot, recording each call and, with
    # block_ms, stalling the loop as a USB host that never reads does; exceptions=True also records print_exception().
    def __init__(self, *, block_ms: int = 0, exceptions: bool = False) -> None:
        self.lines: list[tuple[object, ...]] = []
        self.exceptions: list[BaseException] = []
        self._block_ms = block_ms
        self._saved = _microdot_print_exception() if exceptions else None
        asy_print_log.print = self  # type: ignore[attr-defined]
        microdot.print = self  # type: ignore[attr-defined]
        if exceptions:
            microdot.print_exception = self._exception  # type: ignore[attr-defined]  # test-only, restored by restore()

    def __call__(self, *args: object, **_kwargs: object) -> None:
        self.lines.append(args)
        if self._block_ms:
            time.sleep_ms(self._block_ms)

    def _exception(self, exc: BaseException) -> None:
        self.exceptions.append(exc)

    def restore(self) -> None:
        del asy_print_log.print  # type: ignore[attr-defined]
        del microdot.print  # type: ignore[attr-defined]
        if self._saved is not None:
            microdot.print_exception = self._saved  # type: ignore[attr-defined]


class _Feeder:
    # The supervisor's stand-in: wakes every 10 ms of real time and keeps the largest gap between two wake-ups.
    def __init__(self) -> None:
        self.worst_ms = 0
        self.running = True

    async def run(self) -> None:
        last = time.ticks_ms()
        while self.running:
            await asyncio.sleep_ms(10)
            now = time.ticks_ms()
            self.worst_ms = max(self.worst_ms, time.ticks_diff(now, last))
            last = now


class _RaisingSensor:
    # A sensor whose GET /measurements handler raises `exc`: the route fault Microdot prints and the catch-all persists.
    def __init__(self, exc: Exception) -> None:
        self.name = "PROBE"
        self.exc = exc

    async def _set_dict_cfg(self, data: "JsonMapping", cfg_vals: "cm.ConfigSchema") -> dict[str, str]:
        return {}

    def get_cfg_schema(self) -> "cm.ConfigSchema":
        return ()

    async def get_dict_cfg(self) -> "dict[str, JsonDict]":
        return {self.name: {}}

    async def get_dict_data(self) -> "dict[str, JsonDict]":
        raise self.exc

    async def get_error_counter(self) -> "ErrorLog":
        return {}

    async def reset_error_counter(self) -> bool:
        return True


def _make_service(
    *,
    max_connections: int = _MAX_CONNECTIONS,
    per_call_timeout_s: float = 1.0,
    outer_cap_s: float = 2.0,
    debug: int | None = None,
    uptime: "_Uptime | None" = None,
    sensors: "Sequence[_ModuleLike]" = (),
    port: int = 80,
) -> WebserverService:
    routes = RouteSources(sensors, None, None, None, None, None, None, (), ())
    serving = ServingLimits(_MAX_CONTENT_LENGTH, _CHUNK_BYTES, max_connections, None, per_call_timeout_s, outer_cap_s, "127.0.0.1", port)
    uptime_s = (uptime or _Uptime()).read
    return WebserverService(Microdot(), routes, serving, uptime_s, None, LogConfig(None, 10, debug))


def _head(*lines: str) -> bytes:
    return ("\r\n".join(lines) + "\r\n\r\n").encode()


_GET_STATUS = _head("GET /status HTTP/1.1", "Host: device.local")


def _response(written: bytes) -> "tuple[int, JsonDict]":
    end = written.find(b"\r\n\r\n")
    assert end > 0, written
    envelope: JsonDict = json.loads(written[end + 4 :])
    return int(written.split(b" ", 2)[1]), envelope


async def _log(service: WebserverService) -> "tuple[int, list[tuple[int, str]]]":
    # WEBSERVER's ErrCount and its used history slots as (code, type), oldest first.
    entry = (await service.get_error_counter())["WEBSERVER"]
    nums, types = entry["ErrNum"], entry["ErrType"]
    return entry["ErrCount"], [(nums[i], types[i]) for i in range(len(nums)) if types[i] != "N"]


async def _slots(service: WebserverService) -> int:
    # The open-connection gauge: a LockedCounter reads None only before its first count, and this one starts at 0.
    value = await service._open_conns.get_value()
    assert value is not None
    return value


async def _hold(service: WebserverService, gate: "asyncio.Event") -> "asyncio.Task[None]":
    # One connection that holds a slot until the gate opens; it then ends as a close before any byte, logging nothing.
    task = asyncio.create_task(service._serve(_GateReader(gate), _Writer()))
    await asyncio.sleep_ms(0)
    assert await _slots(service) == 1
    return task


async def _release(gate: "asyncio.Event", held: "asyncio.Task[None]") -> None:
    gate.set()
    await held


# ---------------------------------------------------------------------------
# Dropped connections: one trace and one count per event, a 24-hour window, cleared by ResetErrors.
# ---------------------------------------------------------------------------


def test_seven_refusals_count_seven_and_spend_one_slot() -> None:
    loud = _make_service(max_connections=1, per_call_timeout_s=30.0, debug=2)
    quiet = _make_service(max_connections=1, per_call_timeout_s=30.0, debug=0)
    console = _Console()

    async def refuse_seven(service: WebserverService) -> "tuple[int, int, list[tuple[int, str]], list[_Writer], int]":
        await service.setup()  # the boot batch readies the logger before the first client
        gate = asyncio.Event()
        held = await _hold(service, gate)
        writers = [_Writer() for _ in range(7)]
        try:
            for writer in writers:
                await service._serve(_Reader([(0, _GET_STATUS)]), writer)
        finally:
            await _release(gate, held)
        count, used = await _log(service)
        return await service.get_dropped_count(), count, used, writers, await _slots(service)

    async def scenario() -> "tuple[tuple[int, int, list[tuple[int, str]], list[_Writer], int], int, tuple[int, int, list[tuple[int, str]], list[_Writer], int]]":
        loud_result = await refuse_seven(loud)
        lines = len(console.lines)
        return loud_result, lines, await refuse_seven(quiet)

    try:
        loud_result, loud_lines, quiet_result = run(scenario())
    finally:
        console.restore()
    for dropped, count, used, writers, open_conns in (loud_result, quiet_result):
        assert (dropped, count, used, open_conns) == (7, 7, [(_W_REFUSED, "W")], 0), (dropped, count, used, open_conns)
        assert all(w.writes == [] and w.closed for w in writers)  # closed with no response, as before the trace
    assert loud_lines == 7, console.lines
    assert all(line == ("WEBSERVER", "Connection refused at the ceiling") for line in console.lines), console.lines
    assert len(console.lines) == loud_lines  # DebugLevel 0 prints none of its seven


def test_dropped_connections_leave_the_count_after_a_day() -> None:
    # The service's own uptime source drives the window; the error log keeps every entry regardless.
    uptime = _Uptime()
    uptime.now = 5000  # not on an hour boundary: the window's edge is the event's hour, 23-24 hours on
    service = _make_service(max_connections=1, per_call_timeout_s=30.0, uptime=uptime)

    async def refuse(times: int) -> None:
        for _ in range(times):
            await service._serve(_Reader([(0, _GET_STATUS)]), _Writer())

    async def scenario() -> "tuple[list[int], int]":
        await service.setup()
        gate = asyncio.Event()
        held = await _hold(service, gate)
        counts = []
        try:
            await refuse(2)
            counts.append(await service.get_dropped_count())
            uptime.now += 23 * _HOUR_S
            counts.append(await service.get_dropped_count())
            uptime.now += _HOUR_S
            counts.append(await service.get_dropped_count())
            await refuse(1)
            counts.append(await service.get_dropped_count())
        finally:
            await _release(gate, held)
        count, _used = await _log(service)
        return counts, count

    counts, err_count = run(scenario())
    assert counts == [2, 2, 0, 1], counts
    assert err_count == 3  # the log forgets nothing: only the window does


def test_reset_errors_clears_the_dropped_count() -> None:
    service = _make_service(max_connections=1, per_call_timeout_s=30.0)
    body = b'{"ResetErrors": true}'
    put = _head("PUT /status HTTP/1.1", "Content-Type: application/json", f"Content-Length: {len(body)}") + body

    async def refusals(times: int) -> None:
        gate = asyncio.Event()
        held = await _hold(service, gate)
        try:
            for _ in range(times):
                await service._serve(_Reader([(0, _GET_STATUS)]), _Writer())
        finally:
            await _release(gate, held)

    async def scenario() -> "tuple[int, bytes, int, int]":
        await service.setup()
        await refusals(3)
        before = await service.get_dropped_count()
        writer = _Writer()
        await service._serve(_Reader([(0, put)]), writer)  # the ResetErrors request, served like any client's
        after = await service.get_dropped_count()
        await refusals(1)
        return before, writer.written, after, await service.get_dropped_count()

    before, written, after, again = run(scenario())
    status, envelope = _response(written)
    assert (status, envelope["result"]) == (200, {"ResetErrors": "Valid"}), (status, envelope)
    assert (before, after, again) == (3, 0, 1), (before, after, again)


def test_a_client_gone_mid_response_counts_one_drop() -> None:
    # Microdot mutes the ECONNRESET of a response write (ext/microdot.py Response.write()); the proxy records it. A
    # write-phase timeout is not an OSError (SPECIFICATION.md F.1) and a socket error Microdot does not mute is logged
    # by its own arm: each keeps its one warning, with no peer-reset entry beside it.
    clock = _DrivenClock()
    gone = _make_service(debug=2)
    stalled = _make_service(per_call_timeout_s=0.5, outer_cap_s=2.0)
    unreachable = _make_service()
    reset_writer = _Writer(fail_at=1, fail_with=OSError(errno.ECONNRESET))  # the head goes out, the first body piece fails
    stand_in = _AsyncioStandIn(wait_for=clock.wait_for, sleep=clock.sleep)
    console = _Console()

    async def outcome(service: WebserverService, writer: _Writer) -> "tuple[int, tuple[int, list[tuple[int, str]]]]":
        await service.setup()
        await service._serve(_Reader([(0, _GET_STATUS)]), writer)
        return await service.get_dropped_count(), await _log(service)

    async def scenario() -> "list[tuple[int, tuple[int, list[tuple[int, str]]]]]":
        return [
            await outcome(gone, reset_writer),
            await outcome(stalled, _Writer(fail_at=1)),  # the first body piece never completes
            await outcome(unreachable, _Writer(fail_at=1, fail_with=OSError(errno.EHOSTUNREACH))),
        ]

    try:
        reset, timed_out, socket_error = run(_driven(clock, scenario()))
    finally:
        console.restore()
        stand_in.uninstall()
    assert reset_writer.written.startswith(b"HTTP/1.0 200 "), reset_writer.written
    assert reset_writer.attempts == 2, reset_writer.attempts  # nothing more is written after the failed piece
    assert reset == (1, (1, [(_W_PEER_RESET, "W")])), reset
    assert console.lines == [("WEBSERVER", "Connection reset by the peer before or during its response")], console.lines
    assert timed_out == (0, (1, [(_W_CALL_TIMEOUT, "W")])), timed_out
    assert socket_error == (0, (1, [(_W_SOCKET_ERROR, "W")])), socket_error


def test_a_connection_closed_before_any_byte_is_no_drop() -> None:
    # A browser's preconnect: answered by Microdot's own 400 to nobody, and neither traced nor counted.
    service = _make_service()

    async def scenario() -> "tuple[int, tuple[int, list[tuple[int, str]]], int]":
        await service.setup()
        await service._serve(_Reader([]), _Writer())
        return await service.get_dropped_count(), await _log(service), await _slots(service)

    assert run(scenario()) == (0, (0, []), 0)


# ---------------------------------------------------------------------------
# The request head: every client-controlled size bounded before Microdot parses or allocates it.
# ---------------------------------------------------------------------------


async def _serve_all(service: WebserverService, readers: "list[_Reader]") -> "tuple[list[tuple[bytes, int, int, int]], list[tuple[int, str]]]":
    # Each connection's written bytes, then ErrCount, the drop count and the open slots once it has ended; and the
    # used history slots after the last.
    await service.setup()
    results = []
    used: list[tuple[int, str]] = []
    for reader in readers:
        writer = _Writer()
        await service._serve(reader, writer)
        count, used = await _log(service)
        results.append((writer.written, count, await service.get_dropped_count(), await _slots(service)))
    return results, used


def _check_refused(served: "tuple[list[tuple[bytes, int, int, int]], list[tuple[int, str]]]") -> None:
    # Each one answered the shaped 400 and left exactly one more bad-head trace and drop, its slot freed.
    results, used = served
    for index, (written, count, dropped, open_conns) in enumerate(results, 1):
        status, envelope = _response(written)
        assert (status, envelope["code"]) == (400, 400), (index, written)
        assert (count, dropped, open_conns) == (index, index, 0), (index, count, dropped, open_conns)
    assert used == [(_W_BAD_HEAD, "W")], used


def test_a_negative_content_length_is_refused_before_any_body_is_read() -> None:
    service = _make_service()
    reader = _Reader([(0, _head("PUT /status HTTP/1.1", "Content-Length: -1") + b"x" * 3000)])
    console = _Console(exceptions=True)
    try:
        served = run(_serve_all(service, [reader]))
    finally:
        console.restore()
    _check_refused(served)
    assert reader.readexactly_sizes == []  # readexactly(-1) reads all there is, then asks for less (extmod/asyncio/stream.py)
    assert (console.lines, console.exceptions) == ([], [])


def test_a_content_length_past_the_cap_answers_413_with_the_body_unread() -> None:
    # Digits only, so the guard passes it; Microdot's own cap answers 413 and never reads the body.
    service = _make_service()
    reader = _Reader([(0, _head("PUT /status HTTP/1.1", "Content-Length: 99999999999999999999") + b"{}")])
    console = _Console(exceptions=True)
    try:
        results, used = run(_serve_all(service, [reader]))
    finally:
        console.restore()
    status, envelope = _response(results[0][0])
    assert (status, envelope["code"]) == (413, 413), results
    assert (results[0][1:], used) == ((0, 0, 0), []), (results, used)
    assert reader.readexactly_sizes == []
    assert (console.lines, console.exceptions) == ([], [])


def test_a_non_numeric_or_repeated_content_length_is_a_refused_head() -> None:
    service = _make_service()
    readers = [
        _Reader([(0, _head("PUT /status HTTP/1.1", "Content-Length: abc") + b"{}")]),
        _Reader([(0, _head("PUT /status HTTP/1.1", "Content-Length: 2", "Content-Length: 2") + b"{}")]),
    ]
    console = _Console(exceptions=True)
    try:
        served = run(_serve_all(service, readers))
    finally:
        console.restore()
    _check_refused(served)
    assert [r.readexactly_sizes for r in readers] == [[], []]
    assert (console.lines, console.exceptions) == ([], [])


def test_a_body_cut_short_of_its_content_length_is_refused_quietly() -> None:
    # 20 of 50 bytes, then EOF: the buffered 20 serve first, the stream is asked for the other 30, and its EOFError
    # becomes the quiet refusal instead of Microdot's printed one.
    service = _make_service()
    reader = _Reader([(0, _head("PUT /status HTTP/1.1", "Content-Type: application/json", "Content-Length: 50") + b"x" * 20)])
    console = _Console(exceptions=True)
    try:
        served = run(_serve_all(service, [reader]))
    finally:
        console.restore()
    _check_refused(served)
    assert reader.readexactly_sizes == [30], reader.readexactly_sizes
    assert (console.lines, console.exceptions) == ([], [])


def test_an_overlong_header_line_is_refused_within_one_line_of_reads() -> None:
    service = _make_service()
    request_line = b"GET /status HTTP/1.1\r\n"
    reader = _Reader([(0, request_line + b"X-Long: " + b"a" * 2992)])  # 3,000 B and no line end
    console = _Console(exceptions=True)
    try:
        served = run(_serve_all(service, [reader]))
    finally:
        console.restore()
    _check_refused(served)
    assert sum(reader.read_sizes) - len(request_line) <= Request.max_readline + 1, reader.read_sizes
    assert max(reader.read_sizes) <= _CHUNK_BYTES, reader.read_sizes  # no read allocates more than one piece
    assert (console.lines, console.exceptions) == ([], [])


def test_the_header_count_is_bounded() -> None:
    service = _make_service()
    headers = [f"X-H{i}: v" for i in range(_MAX_HEADER_LINES + 1)]
    readers = [
        _Reader([(0, _head("GET /status HTTP/1.1", *headers[:_MAX_HEADER_LINES]))]),
        _Reader([(0, _head("GET /status HTTP/1.1", *headers))]),
    ]
    console = _Console(exceptions=True)
    try:
        results, used = run(_serve_all(service, readers))
    finally:
        console.restore()
    fits, refused = results
    assert (_response(fits[0])[0], fits[1:]) == (200, (0, 0, 0)), fits
    assert (_response(refused[0])[0], refused[1:], used) == (400, (1, 1, 0), [(_W_BAD_HEAD, "W")]), (refused, used)
    assert (console.lines, console.exceptions) == ([], [])


def test_a_head_past_its_byte_cap_is_refused_though_each_line_fits() -> None:
    service = _make_service()
    pads = [f"X-Pad{i}: " + "a" * 610 for i in range(4)]
    head = _head("GET /status HTTP/1.1", *pads)
    assert len(head) > _MAX_HEAD_BYTES and max(len(p) for p in pads) < Request.max_readline, len(head)
    console = _Console(exceptions=True)
    try:
        served = run(_serve_all(service, [_Reader([(0, head)])]))
    finally:
        console.restore()
    _check_refused(served)
    assert (console.lines, console.exceptions) == ([], [])


def test_malformed_head_lines_are_refused_without_a_traceback() -> None:
    # Each would raise inside Microdot's Request.create(), which prints it before answering 400.
    service = _make_service()
    heads = [
        b"GET /\r\n\r\n",  # a request line of two tokens
        b"GET / HTTP1.1\r\n\r\n",  # a version with no "/"
        _head("GET /status HTTP/1.1", "NoColon"),
        b"GET /status HTTP/1.1\r\nX-Bad: \xff\xfe\r\n\r\n",  # not UTF-8
        _head("PUT /status HTTP/1.1", "Transfer-Encoding: chunked") + b"5\r\nhello\r\n0\r\n\r\n",
    ]
    console = _Console(exceptions=True)
    try:
        served = run(_serve_all(service, [_Reader([(0, h)]) for h in heads]))
    finally:
        console.restore()
    _check_refused(served)
    assert (console.lines, console.exceptions) == ([], [])


def test_a_long_query_string_within_the_line_bound_is_served() -> None:
    service = _make_service()
    head = _head("GET /status?q=" + "x" * 1998 + " HTTP/1.1", "Host: d")  # a 2,000 B query
    console = _Console(exceptions=True)
    try:
        results, used = run(_serve_all(service, [_Reader([(0, head)])]))
    finally:
        console.restore()
    assert (_response(results[0][0])[0], results[0][1:], used) == (200, (0, 0, 0), []), results
    assert (console.lines, console.exceptions) == ([], [])


def test_expect_100_continue_is_answered_once_the_late_body_arrives() -> None:
    # An HTTP/1.0 server sends no interim response; curl sends the body after its own 1 s wait.
    clock = _DrivenClock()
    service = _make_service(per_call_timeout_s=2.0, outer_cap_s=5.0)
    body = b'{"ResetErrors": true}'
    head = _head("PUT /status HTTP/1.1", "Expect: 100-continue", "Content-Type: application/json", f"Content-Length: {len(body)}")
    reader = _Reader([(0, head), (1.0, body)], sleep=clock.sleep)
    stand_in = _AsyncioStandIn(wait_for=clock.wait_for, sleep=clock.sleep)
    console = _Console(exceptions=True)
    try:
        results, used = run(_driven(clock, _serve_all(service, [reader])))
    finally:
        console.restore()
        stand_in.uninstall()
    status, envelope = _response(results[0][0])
    assert (status, envelope["result"], results[0][1:], used) == (200, {"ResetErrors": "Valid"}, (0, 0, 0), []), results
    assert clock.now >= 1.0  # the body really came late
    assert (console.lines, console.exceptions) == ([], [])


# ---------------------------------------------------------------------------
# The server start: a bounded retry, and a cancelled task that closes its listening socket.
# ---------------------------------------------------------------------------


async def _start_then_log(service: WebserverService) -> "tuple[int, list[tuple[int, str]]]":
    await service.setup()
    await service._serve_loop()
    return await _log(service)


def test_a_start_that_fails_twice_then_serves() -> None:
    service = _make_service(debug=2)
    starter = _StartServer([OSError(errno.ENOMEM), MemoryError("injected for the start")])
    stand_in = _AsyncioStandIn(start_server=starter.start_server, sleep=starter.sleep)
    console = _Console()
    try:
        log = run(_start_then_log(service))
    finally:
        console.restore()
        stand_in.uninstall()
    assert (starter.calls, starter.delays, starter.server.waited) == (3, [_START_RETRY_S] * 2, True)
    assert [line[1] for line in console.lines] == ["Web server start failed, retrying:"] * 2, console.lines
    assert log == (0, []), log  # a retried failure prints, and persists nothing


def test_a_start_that_fails_three_times_logs_once_and_raises() -> None:
    service = _make_service()
    failures: list[Exception] = [OSError(errno.EADDRINUSE) for _ in range(_START_RETRIES)]
    last = failures[-1]
    starter = _StartServer(failures)
    stand_in = _AsyncioStandIn(start_server=starter.start_server, sleep=starter.sleep)

    async def scenario() -> "tuple[BaseException | None, tuple[int, list[tuple[int, str]]]]":
        await service.setup()
        raised = None
        try:
            await service._serve_loop()
        except OSError as e:
            raised = e
        return raised, await _log(service)

    try:
        raised, log = run(scenario())
    finally:
        stand_in.uninstall()
    assert raised is last  # re-raised, so the task ends and the supervisor's rung takes over
    assert (starter.calls, starter.delays) == (_START_RETRIES, [_START_RETRY_S] * (_START_RETRIES - 1))
    assert log == (1, [(_W_START_FAILED, "W")]), log


def _can_listen(port: int) -> bool:
    # A second listener on the port: Linux refuses it while one listens, SO_REUSEADDR or not.
    probe = socket.socket()
    try:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        probe.bind(socket.getaddrinfo("127.0.0.1", port)[0][-1])
        probe.listen(1)
    except OSError:
        return False
    finally:
        probe.close()
    return True


async def _refused_or_eof(port: int) -> bool:
    # A connect to a closed port fails at once, or, when it went EINPROGRESS, on the first read (stream.py).
    try:
        reader, writer = await asyncio.open_connection("127.0.0.1", port)  # one Stream on MicroPython
    except OSError:
        return True
    try:
        writer.write(_GET_STATUS)
        await writer.drain()
        return await asyncio.wait_for(reader.read(-1), 2.0) == b""
    except OSError:
        return True
    finally:
        writer.close()


async def _until(predicate: "Callable[[], Awaitable[bool]]") -> bool:
    for _ in range(400):
        if await predicate():
            return True
        await asyncio.sleep_ms(5)
    return False


def test_cancelling_the_serve_task_closes_the_listening_port() -> None:
    # Server.wait_closed() awaits the server task and a cancel is forwarded to an awaited task (extmod/asyncio): pinned
    # here because a MicroPython bump could change it. A connection the server took in before the cancel still completes.
    port = _port()
    service = _make_service(port=port)

    async def accepted() -> bool:
        return await _slots(service) == 1

    async def idle() -> bool:
        return await _slots(service) == 0

    async def scenario() -> "tuple[bool, bool, bytes, bool, bool, bool, bool]":
        await service.setup()
        task = service.start_asy_serve()
        await asyncio.sleep_ms(50)  # the start's own bind and listen
        listening = not _can_listen(port)
        reader, writer = await asyncio.open_connection("127.0.0.1", port)
        try:
            admitted = await _until(accepted)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            writer.write(_GET_STATUS)
            await writer.drain()
            response = await asyncio.wait_for(reader.read(-1), 5.0)
        finally:
            writer.close()
        refused = await _refused_or_eof(port)
        return listening, admitted, response, refused, _can_listen(port), task.done(), await _until(idle)

    listening, admitted, response, refused, free, ended, drained = run(scenario())
    assert (listening, admitted) == (True, True)  # the control: a live listener is visible to the probe
    assert response.startswith(b"HTTP/1.0 200 "), response
    assert (refused, free, ended, drained) == (True, True, True, True)


# ---------------------------------------------------------------------------
# The console under client faults, and sends the network stack cannot queue.
# ---------------------------------------------------------------------------


def _trickle(data: bytes, delay_s: float) -> "list[tuple[float, bytes]]":
    return [(delay_s, data[i : i + 1]) for i in range(len(data))]


def test_client_faults_print_nothing_at_debug_level_zero() -> None:
    # A host that holds the USB port without reading stalls each print 500 ms (shared/tinyusb/mp_usbd_cdc.c,
    # ports/rp2/mphalport.h); at DebugLevel 0 no client fault may print, or a burst could starve the watchdog.
    clock = _DrivenClock()
    service = _make_service(per_call_timeout_s=1.0, outer_cap_s=2.0, debug=0)
    rebound = _microdot_print_exception() == service._print_exception
    truncated = _head("PUT /status HTTP/1.1", "Content-Type: application/json", "Content-Length: 50") + b"x" * 20
    bad_head = _head("PUT /status HTTP/1.1", "Transfer-Encoding: chunked")
    feeder = _Feeder()

    async def wave() -> None:
        slow = [asyncio.create_task(service._serve(_Reader(_trickle(_GET_STATUS, 0.25), eof=False, sleep=clock.sleep), _Writer())) for _ in range(_MAX_CONNECTIONS)]
        await clock.sleep(0.5)
        for _ in range(2):  # the six Slowloris clients hold every slot
            await service._serve(_Reader([(0, _GET_STATUS)]), _Writer())
        for task in slow:
            await task  # each reclaimed by the outer cap
        # A truncated body ending in EOF is refused quietly; one ending in silence times out, which Microdot prints
        # through the rebound, level-gated print.
        faults = (_Reader([(0, bad_head)]), _Reader([(0, truncated)]), _Reader([(0, truncated)], eof=False), _ResetReader())
        await asyncio.gather(*(service._serve(reader, _Writer()) for reader in faults))

    async def load() -> "tuple[tuple[int, list[tuple[int, str]]], int, int]":
        await service.setup()
        feeding = asyncio.create_task(feeder.run())
        for start in (2.5, 5.0, 7.5, 10.0):  # four waves over a driven 10 s at least
            await wave()
            await clock.sleep(max(0.0, start - clock.now))
        feeder.running = False
        await feeding
        return await _log(service), await service.get_dropped_count(), await _slots(service)

    stand_in = _AsyncioStandIn(wait_for=clock.wait_for, sleep=clock.sleep)
    console = _Console(block_ms=500)
    try:
        (count, used), dropped, open_conns = run(_driven(clock, load()))
    finally:
        console.restore()
        stand_in.uninstall()
    assert rebound  # Microdot's print_exception() is the service's level-gated one
    assert console.lines == [], console.lines
    assert feeder.worst_ms < 2000, feeder.worst_ms  # the supervisor's 2 s check interval (src/asy_system_service.py)
    # Per wave: six outer-cap reclaims, two refusals, two refused heads, a read timeout and a reset; all counted, the
    # five drops among them too, and none printed.
    assert (count, dropped, open_conns) == (48, 20, 0), (count, dropped, open_conns)
    assert {c for c, _t in used} <= {_W_REQUEST_CAP, _W_REFUSED, _W_BAD_HEAD, _W_CALL_TIMEOUT, _W_PEER_RESET}, used


def test_a_handler_exception_prints_nothing_at_level_zero_and_one_gated_line_above() -> None:
    # Microdot prints a handler's exception before our catch-all runs; the service rebound that print to its logger,
    # except a MemoryError's text, which stays on the console for the memory gates (CLAUDE.md memory rule).
    sensor = _RaisingSensor(ValueError("probe"))
    service = _make_service(sensors=[sensor], debug=0)
    rebound = _microdot_print_exception() == service._print_exception
    request = _head("GET /measurements HTTP/1.1", "Host: d")
    console = _Console()

    async def serve_once() -> "tuple[int, int, list[tuple[object, ...]]]":
        writer = _Writer()
        printed = len(console.lines)
        await service._serve(_Reader([(0, request)]), writer)
        count, used = await _log(service)
        assert used == [(_E_UNEXPECTED, "E")], used  # the catch-all's persisted entry
        return _response(writer.written)[0], count, console.lines[printed:]

    async def scenario() -> "list[tuple[int, int, list[tuple[object, ...]]]]":
        await service.setup()
        quiet = await serve_once()
        service.pr.set_level(1)  # DebugLevel raised, as PUT /system sets it at runtime
        loud = await serve_once()
        service.pr.set_level(0)
        sensor.exc = MemoryError("injected for the handler")
        return [quiet, loud, await serve_once()]

    try:
        quiet, loud, exhausted = run(scenario())
    finally:
        console.restore()
    assert rebound
    assert quiet == (500, 1, []), quiet
    status, count, lines = loud
    assert (status, count) == (500, 2), loud
    # One gated line is Microdot's print; the other the catch-all's own entry, both carrying the text.
    assert [line[1] for line in lines] == ["Microdot caught:", "Unhandled exception in route handler:"], lines
    assert all(str(line[2]) == "probe" for line in lines), lines
    status, count, lines = exhausted
    assert (status, count, [line[:2] for line in lines]) == (500, 3, [("WEBSERVER", "Microdot caught:")]), exhausted
    assert str(lines[0][2]) == "injected for the handler"


def test_sends_the_stack_cannot_queue_end_at_the_per_call_timeout() -> None:
    # lwIP's queue can fail a send with room left (POLLOUT at tcp_sndbuf() > 0): each stuck write spins one round per
    # attempt until the per-call timeout, other tasks served each round (SPECIFICATION.md A.5).
    service = _make_service(per_call_timeout_s=0.5, outer_cap_s=2.0)
    stuck = [_EagainWriter(10**9) for _ in range(_MAX_CONNECTIONS - 1)]
    feeder = _Feeder()

    async def timed(writer: _Writer) -> int:
        start = time.ticks_ms()
        await service._serve(_Reader([(0, _GET_STATUS)]), writer)
        return time.ticks_diff(time.ticks_ms(), start)

    async def scenario() -> "tuple[bytes, list[int], _Writer, tuple[int, list[tuple[int, str]]], int]":
        await service.setup()
        reference = _Writer()
        await service._serve(_Reader([(0, _GET_STATUS)]), reference)  # the same request, served unloaded
        feeding = asyncio.create_task(feeder.run())
        normal = _Writer()
        durations = await asyncio.gather(timed(normal), *(timed(w) for w in stuck))
        feeder.running = False
        await feeding
        return reference.written, durations[1:], normal, await _log(service), await _slots(service)

    expected, durations, normal, log, open_conns = run(scenario())
    assert normal.written == expected  # the concurrent request is served intact, byte for byte
    assert all(ms < 1000 for ms in durations), durations  # per_call_timeout_s + 0.5 s
    assert log == (len(stuck), [(_W_CALL_TIMEOUT, "W")]), log  # one timeout warning each
    assert open_conns == 0
    assert feeder.worst_ms < 500, feeder.worst_ms  # a quarter of the supervisor's 2 s check interval
    assert all(w.send_attempts > 100 for w in stuck), [w.send_attempts for w in stuck]  # the loop yields, never blocks


def test_a_send_refused_a_thousand_times_then_accepted_completes() -> None:
    service = _make_service(per_call_timeout_s=0.5, outer_cap_s=2.0)
    writer = _EagainWriter(1000)

    async def scenario() -> "tuple[tuple[int, list[tuple[int, str]]], int]":
        await service.setup()
        await service._serve(_Reader([(0, _GET_STATUS)]), writer)
        return await _log(service), await _slots(service)

    log, open_conns = run(scenario())
    head_end = writer.written.find(b"\r\n\r\n") + 4
    length = int(writer.written.split(b"Content-Length: ", 1)[1].split(b"\r\n", 1)[0])
    assert writer.written.startswith(b"HTTP/1.0 200 ") and len(writer.written) - head_end == length, writer.written
    assert writer.send_attempts > 1000
    assert (log, open_conns) == ((0, []), 0)


def test_slots_held_by_unsendable_responses_come_back() -> None:
    service = _make_service(per_call_timeout_s=0.5, outer_cap_s=2.0)
    stuck = [_EagainWriter(10**9) for _ in range(_MAX_CONNECTIONS)]

    async def scenario() -> "tuple[_Writer, _Writer, tuple[int, list[tuple[int, str]]], int]":
        await service.setup()
        tasks = [asyncio.create_task(service._serve(_Reader([(0, _GET_STATUS)]), w)) for w in stuck]
        await asyncio.sleep_ms(50)
        refused = _Writer()
        await service._serve(_Reader([(0, _GET_STATUS)]), refused)  # every slot held by a spinning send
        for task in tasks:
            await task
        served = _Writer()
        await service._serve(_Reader([(0, _GET_STATUS)]), served)
        return refused, served, await _log(service), await _slots(service)

    refused, served, log, open_conns = run(scenario())
    assert refused.writes == [] and refused.closed
    assert served.written.startswith(b"HTTP/1.0 200 "), served.written
    count, used = log
    assert (count, used, open_conns) == (_MAX_CONNECTIONS + 1, [(_W_REFUSED, "W"), (_W_CALL_TIMEOUT, "W")], 0), log


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
