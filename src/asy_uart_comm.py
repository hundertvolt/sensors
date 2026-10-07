"""Point-to-point UART message protocol over asy_uart_driver.UART: chunk trains, per-frame ACKs,
quiesce-and-resync recovery. Initiator/responder by construction; see SPECIFICATION.md Part J.
Every method returns a well-defined sentinel, never raises - a link fault is never an exception."""
# Wire constants and recovery timings are a two-implementation contract with the C peer: every
# change to one gets a UART_C_PORT_CHANGELOG.md entry. The write hold-off waits out its deadline
# rather than refusing, so no caller is told "failed" about a link that is merely quiescing (J.5).

import asyncio
import time
from collections import namedtuple

from micropython import const

from asy_base_classes import COUNTER_CAP, LockableBuffer
from asy_print_log import DEFAULT_LOG, PrintLogHistory, make_logger

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    import asyncio as _asyncio
    from collections.abc import Callable
    from typing import Any, NamedTuple, Protocol

    from asy_base_classes import TimerStarter
    from asy_print_log import ErrorLog, LogConfig
    from asy_uart_driver import UART

    # Every callback may be sync or async, so each returns `object`: the result is either the
    # value itself or a coroutine yielding it, and _call() below is what tells the two apart.
    class _GetCallback(Protocol):
        # (valid, payload) for a command id: what the responder should send back.
        def __call__(self, cmd_id: int) -> object: ...

    class _SetCallback(Protocol):
        # (valid, expected_size) for a command id; expected_size None means "don't care".
        def __call__(self, cmd_id: int) -> object: ...

    class _PullCallback(Protocol):
        # Fills one chunk's region in place and returns how many bytes it wrote.
        def __call__(self, chunk: int, buf: memoryview) -> object: ...

    class _PushCallback(Protocol):
        # Consumes one chunk's payload; returns True to continue.
        def __call__(self, chunk: int, buf: memoryview) -> object: ...

    class _MessageCallback(Protocol):
        # Hands the owned listen loop's completed transaction to its owner. Without it a responder
        # wired the documented way - get_task_starters() - can never see a SET's payload at all,
        # because the loop is what consumes the ListenResult.
        def __call__(self, cmd_id: int, cmd: int, payload: bytearray | None) -> object: ...

    # What a payload can be on the way out, and what a destination can be on the way in - the
    # union is the real contract, so nothing here has to fall back to Any.
    Readable = bytes | bytearray | memoryview
    Writable = bytearray | memoryview


_NAME = const("UART")

ROLE_INITIATOR = const("initiator")
ROLE_RESPONDER = const("responder")

# CMD_SET is public: asy_uart_link_driver.py imports it; ACK and GET are module-private.
_CMD_ACK = const(0x01)
_CMD_GET = const(0x02)
CMD_SET = const(0x04)

_HEADER_LEN = const(5)
_MSG_UID = const(0)
_MSG_CMD = const(1)
_MSG_SIZE = const(2)
_MSG_CHUNKS = const(3)
_MSG_CUR_CHUNK = const(4)
_MSG_PAYLOAD = const(5)

_UID_MAX = const(0xFE)  # 0xFF is never emitted - a deliberate off-by-one barrier, see J.3
_CHUNKS_MAX = const(0xFF)
_PAYLOAD_MIN = const(1)
_PAYLOAD_MAX = const(255)

# Recovery timings, as integer numerator/denominator so no float division appears on the target.
# Both are 1.5 x timeout and both are part of the wire contract (changelog A4).
_RESYNC_NUM = const(3)
_RESYNC_DEN = const(2)
# The drain's own hard bound (changelog A5). A multiple of the quiet window, so it can never be
# shorter than the peer's own drain - which is what would let this side transmit into it.
_DRAIN_BOUND_MULT = const(4)
# @tunable uart.gate_step_ms = 20
_GATE_STEP_MS = const(20)  # longest single sleep inside the write gate, so a cancel lands promptly
# @tunable uart.gc_pause_worst_ms = 21
_GC_PAUSE_WORST_MS = const(21)  # measured worst-case collection pause, SPECIFICATION.md Part I
# @tunable uart.poll_jitter_ms = 5
_POLL_JITTER_MS = const(5)  # scheduling slack added to poll_wait_ms when sizing rxbuf
_BACKOFF_MULT = const(2)
_BACKOFF_MAX_MULT = const(5)  # cap = 5 x timeout, matching asy_captive_dns.py's own 0.5s -> 5s shape
# @tunable uart.diag_resync_streak = 2
_DIAG_RESYNC_STREAK = const(2)  # resyncs with bytes seen but no frame ever valid before the diagnostic fires
_MIN_CHUNKS = const(2)  # even a payload-less command carries one data chunk, so it can be confirmed
_CALLBACK_PAIR_LEN = const(2)  # every callback returns exactly (valid, value)
_CMD_ID_MAX = const(0xFF)  # a command id is one payload byte, so this is its whole range

# Codes from the global catalog (buildgen/error_catalog.json): the UART band 75-99 for this module's
# own conditions, the shared codes for the rest. Mirrored in SPECIFICATION.md Part C.7.1.
_ERR_CALLBACK = const(14)
_ERR_NOT_INIT = const(18)
_ERR_ALLOC = const(20)
_ERR_BAD_ARG = const(21)
_ERR_TIMEOUT = const(22)
_ERR_UNEXPECTED = const(23)
_ERR_UART_PAYLOAD_SIZE = const(75)
_ERR_UART_TIMEOUT_PARAM = const(76)
_ERR_UART_NO_BUS = const(77)
_ERR_UART_RXBUF = const(78)
_ERR_UART_ROLE_REFUSED = const(79)
_ERR_UART_FRAME_INVALID = const(80)
_ERR_UART_NO_ACK = const(81)
_ERR_UART_WRITE_FAILED = const(82)
_ERR_UART_PAYLOAD_TOO_LARGE = const(83)
_ERR_UART_SIZE_MISMATCH = const(84)
_ERR_UART_REENTRANT = const(85)
_ERR_UART_WRONG_KIND = const(86)
_ERR_UART_GET_ID_MISMATCH = const(87)
_ERR_UART_PEER_INITIATED = const(88)
_ERR_UART_LINK_UNINTELLIGIBLE = const(89)
_ERR_UART_STREAM_SHORT = const(90)

_WRN_UART_DRAIN_BOUND = const(54)
_WRN_UART_CANCEL_UNACKED = const(55)
_WRN_UART_CMD_DECLINED = const(56)

# A responder's get/set callbacks (both required) and its optional message callback, passed as one object.
if TYPE_CHECKING:

    class ResponderCallbacks(NamedTuple):
        get: "_GetCallback | None"
        set: "_SetCallback | None"
        message: "_MessageCallback | None"

else:
    ResponderCallbacks = namedtuple("ResponderCallbacks", ("get", "set", "message"))

# One allocation per logical message, never per frame (J.9). Returned on every path,
# including the ones that fail - _LISTEN_FAILED is preallocated so even a MemoryError-degraded
# path has a well-formed value to hand back.
ListenResult = namedtuple("ListenResult", ("cmd_id", "cmd", "payload"))
_LISTEN_FAILED = ListenResult(None, None, None)


def _is_writable(buf: "Writable") -> bool:
    # memoryview(b"...") passes any type check and raises only on the first real assignment, by
    # which point the peer is already acknowledged. A zero-length slice assignment allocates
    # nothing and raises in exactly the same case (Part F.1).
    try:
        buf[0:0] = b""
    except TypeError:
        return False
    return True


def _next_uid(uid: int) -> int:
    # The single controlled wrap. Anything predicting a *next* UID uses this, never a bare
    # +1, which mispredicts precisely at the 0xFE -> 0 boundary.
    return 0 if uid >= _UID_MAX else uid + 1


class UARTComm:
    def __init__(
        self,
        uart: "UART | None",
        role: str,
        payload_size: int = 48,
        timeout: int = 1000,
        callbacks: ResponderCallbacks | None = None,
        name: str = _NAME,
        log: "LogConfig" = DEFAULT_LOG,
        logger: PrintLogHistory | None = None,
    ) -> None:
        self.pr = logger if logger is not None else make_logger(log, name)  # reach-through: reuse a directly-bound sibling object's own logger
        self.name = name  # matches self.pr.name - the _ModuleLike registration shape
        # asy_webserver_service.py's registration lists key on (error_sources=/settings=).
        self._uart = uart
        self._role = role
        self._payload_size = payload_size
        self._timeout = timeout
        # Optional, unlike the other two: a GET-only responder has nothing to deliver, so an
        # absent one is not a construction error (only a wholly unanswerable instance is refused).
        if callbacks is None:
            self._get_callback: _GetCallback | None = None
            self._set_callback: _SetCallback | None = None
            self._message_callback: _MessageCallback | None = None
        else:
            self._get_callback, self._set_callback, self._message_callback = callbacks
        self.initialized = False
        self._uid = 0
        self._busy = False  # asyncio.Lock is not reentrant, so re-entry is refused, not awaited
        self._in_resync = False  # a fault during a resync must not start a second one
        self._holdoff_active = False
        self._holdoff_deadline = time.ticks_ms()  # only meaningful while _holdoff_active is set
        self._valid_frames = 0
        self._blind_resyncs = 0  # resyncs that saw bytes but never a valid frame
        self._drain_bound_hit = False  # set by _drain(), read by the resync that called it
        self._cancel_unacked_seen = 0  # the driver's counter is cumulative; only a rise is news
        self._init_errno = self._validate_config()
        # Re-checked locally, never the caller's raw values: `5 + "48"` raises, and __init__ is the
        # one entry point with no object yet to answer through a sentinel. _validate_config() stops
        # at its first finding, so a non-integer can still be sitting here under a different errno.
        payload = self._payload_size if isinstance(self._payload_size, int) else 0
        backoff_base = self._timeout if isinstance(self._timeout, int) and self._timeout > 0 else 1
        self._frame_size = _HEADER_LEN + payload
        self._backoff_initial_ms = max(backoff_base // 2, 1)
        self._backoff_max_ms = max(backoff_base * _BACKOFF_MAX_MULT, self._backoff_initial_ms)
        self._tx, self._rx, self._ack, self._zero, self._cmd_buf = self._allocate()
        if self._init_errno == 0 and not self._buffers_ready(payload):
            self._init_errno = _ERR_ALLOC
        if self._init_errno:
            # __init__ is sync, so the persisted entry is written by setup(); this is the
            # non-persisting counterpart so a construction failure is visible immediately.
            self.pr.err("Construction failed, errno", self._init_errno)

    async def _get_unlocked(
        self, device: "UART", get_id: int, exp_size: int | None, dest: "Writable | None", push: "_PushCallback | None",
    ) -> tuple[int, bytearray | None] | None:
        want = -1 if exp_size is None else exp_size
        self._cmd_buf[0] = get_id
        if not await self._write_frame_with_ack(device, _CMD_GET, 1, 1, self._cmd_buf, 1):
            return None
        # The answer is a SET train in the opposite direction (J.4), which is why one pair of
        # primitives covers all four directions and why this is the responder's own SET path.
        header = await self._read_answer_header(device, get_id)
        if header is None:
            return None
        chunks, uid = header
        room = self._dest_size(chunks, want)
        if room is None:
            await self._fault(device, _ERR_UART_SIZE_MISMATCH, "expected", want, "bytes, the train can carry at most", (chunks - 1) * self._payload_size)
            return None
        own_dest = None
        if push is None:
            if dest is None:
                try:  # allocated before the first data chunk is acknowledged
                    own_dest = bytearray(room)
                except (MemoryError, OverflowError):
                    await self._fault(device, _ERR_ALLOC, "could not allocate", room, "bytes for the answer")
                    return None
                dest = own_dest
            elif len(dest) < room:
                await self._fault(device, _ERR_UART_SIZE_MISMATCH, "destination holds", len(dest), "of", room)
                return None
        if not await self._send_ack(device, uid):
            await self._fault(device, _ERR_UART_WRITE_FAILED, "ACK for the answer header failed")
            return None
        written = await self._recv_train(device, dest, want, push, chunks, uid)
        if written is None:
            return None
        return written, own_dest

    async def _accept_set(self, device: "UART", set_cb: "_SetCallback", cmd_id: int, uid: int, chunks: int) -> ListenResult:
        if not await self._send_ack(device, uid):
            await self._fault(device, _ERR_UART_WRITE_FAILED, "ACK for SET failed")
            return _LISTEN_FAILED
        pair = self._pair(await self._call(set_cb, cmd_id))
        if pair is None:
            await self._fault(device, _ERR_CALLBACK, "set_callback returned an unusable result for", cmd_id)
            return _LISTEN_FAILED
        valid, exp_size = pair
        if not valid:
            await self._reject_wrn(device, cmd_id)
            return ListenResult(None, CMD_SET, None)
        want = -1 if exp_size is None else exp_size
        if not isinstance(want, int) or want < -1 or want > (_CHUNKS_MAX - 1) * self._payload_size:
            await self._fault(device, _ERR_CALLBACK, "set_callback asked for an impossible size", exp_size)
            return ListenResult(None, CMD_SET, None)
        room = self._dest_size(chunks, want)
        if room is None:
            await self._fault(device, _ERR_UART_SIZE_MISMATCH, "expected", want, "bytes, train can carry at most", (chunks - 1) * self._payload_size)
            return ListenResult(None, CMD_SET, None)
        try:  # allocated before any data chunk is acknowledged
            dest = bytearray(room)
        except (MemoryError, OverflowError):
            await self._fault(device, _ERR_ALLOC, "could not allocate", room, "bytes for the incoming train")
            return ListenResult(None, CMD_SET, None)
        written = await self._recv_train(device, dest, want, None, chunks, uid)
        if written is None:
            return ListenResult(None, CMD_SET, None)
        if written == 0:
            # J.9: a genuinely empty payload is a distinct outcome from failure, and
            # the two must not collapse - the cmd_id is what says the message actually arrived.
            return ListenResult(cmd_id, CMD_SET, None)
        if written == len(dest):
            return ListenResult(cmd_id, CMD_SET, dest)
        try:
            return ListenResult(cmd_id, CMD_SET, bytearray(memoryview(dest)[0:written]))
        except (MemoryError, OverflowError):
            await self._err(_ERR_ALLOC, "could not right-size the received train")
            return ListenResult(None, CMD_SET, None)

    def _allocate(self) -> tuple[LockableBuffer, LockableBuffer, bytearray, bytearray, bytearray]:
        # Everything the steady state needs, once: the TX/RX frame buffers, the ACK scratch, the zero
        # padding and the command-id scratch. Nothing is allocated per frame after this - zero bytes
        # retained per transaction, pinned by test_uart_comm_hazard.py.
        if self._uart is None or self._init_errno == _ERR_UART_PAYLOAD_SIZE:
            size = _HEADER_LEN  # a refused construction still needs well-formed attributes
            room = size
        else:
            size = self._frame_size
            room = self._uart.framing.max_encoded(size + self._uart.crc.length())
        tx = LockableBuffer(room, data_start=_HEADER_LEN, data_length=max(size - _HEADER_LEN, 0))
        rx = LockableBuffer(room, data_start=_HEADER_LEN, data_length=max(size - _HEADER_LEN, 0))
        try:
            ack = bytearray(room)
            zero = bytearray(max(size - _HEADER_LEN, 0))
            cmd_buf = bytearray(1)
        except (MemoryError, OverflowError):
            return tx, rx, bytearray(0), bytearray(0), bytearray(0)
        # An ACK's shape is fixed, so only its UID is ever written again.
        if len(ack) >= _HEADER_LEN:
            ack[_MSG_CMD] = _CMD_ACK
            ack[_MSG_SIZE] = 0
            ack[_MSG_CHUNKS] = 1
            ack[_MSG_CUR_CHUNK] = 1
        return tx, rx, ack, zero, cmd_buf

    async def _answer_get(self, device: "UART", get_cb: "_GetCallback", cmd_id: int, uid: int) -> ListenResult:
        if not await self._send_ack(device, uid):
            await self._fault(device, _ERR_UART_WRITE_FAILED, "ACK for GET failed")
            return _LISTEN_FAILED
        pair = self._pair(await self._call(get_cb, cmd_id))
        if pair is None:
            await self._fault(device, _ERR_CALLBACK, "get_callback returned an unusable result for", cmd_id)
            return _LISTEN_FAILED
        valid, payload = pair
        if not valid:
            # A distinct outcome, not silence - the caller is told which command was asked
            # for and that the answer was withheld, while the peer learns it by timing out.
            await self._reject_wrn(device, cmd_id)
            return ListenResult(None, _CMD_GET, None)
        if payload is not None and not isinstance(payload, (bytes, bytearray, memoryview)):
            # The payload's type is part of the return shape, so it is checked rather than
            # trusted - a str or an int here would otherwise reach the frame builder.
            await self._fault(device, _ERR_CALLBACK, "get_callback returned a non-buffer payload for", cmd_id)
            return ListenResult(None, _CMD_GET, None)
        # The answer runs through the internal unlocked SET path, so the role gate that refuses
        # uart_set() on a responder does not stop a responder from ever answering anything.
        total = 0 if payload is None else len(payload)
        if not await self._send_train(device, cmd_id, payload, total, None):
            return ListenResult(None, _CMD_GET, None)
        return ListenResult(cmd_id, _CMD_GET, None)

    async def _await_write_gate(self) -> None:
        # A deadline, never a one-shot Timer: MicroPython's scheduler queue can silently drop a soft
        # callback, and the flag it would have set is then never set - the legacy module's permanent
        # hang. A deadline cannot be dropped, and needs no alarm-pool slot.
        while self._holdoff_active:
            remaining = time.ticks_diff(self._holdoff_deadline, time.ticks_ms())
            if remaining <= 0:
                self._holdoff_active = False
                return
            await asyncio.sleep_ms(min(remaining, _GATE_STEP_MS))

    def _buffers_ready(self, payload: int) -> bool:
        # Every buffer, not only the TX frame: _allocate() guards its three scratch buffers as one
        # group, so a heap exhausted after the frame buffers leaves zero-length ones behind. That
        # object passed the gate, then padding shrank the TX buffer and the id write raised (F.1).
        return (
            self._tx.get_buf() is not None
            and self._rx.get_buf() is not None
            and len(self._ack) >= self._frame_size
            and len(self._zero) >= payload
            and len(self._cmd_buf) >= 1
        )

    async def _call(self, callback: "Callable[..., object]", *args: object) -> object:
        # The established guarded-dispatch shape: caller code runs inside the protocol's critical
        # section, so a raise or a wrong return shape must not escape into it.
        # A coroutine and a plain value are both accepted - a generator-like result is awaited.
        try:
            result = callback(*args)
            # MicroPython has no inspect/iscoroutine, and a coroutine is structurally a generator
            # here - `send` is what distinguishes one from a plain returned value. mypy sees only
            # `object` at this point, which is the honest type of an arbitrary callback's result.
            if result is not None and hasattr(result, "send"):
                result = await result  # type: ignore[misc]
        except Exception as e:  # caller-supplied code; its runtime behaviour is not statically known
            await self._err(_ERR_CALLBACK, "callback raised:", e)
            return None
        return result

    async def _check_buffer(self, buf: object, *, writable: bool) -> bool:
        # The responder already type-checks what a callback hands back; the public entry
        # points trusted their caller instead, so a str or an int reached the frame builder.
        if buf is None:
            return True
        if isinstance(buf, (bytearray, memoryview)):
            if writable and not _is_writable(buf):
                await self._err(_ERR_BAD_ARG, "destination buffer is read-only")
                return False
            return True
        if not writable and isinstance(buf, bytes):
            return True
        await self._err(_ERR_BAD_ARG, "buffer is a", type(buf).__name__, "not a byte buffer")
        return False

    async def _check_cmd_id(self, cmd_id: object) -> bool:
        # A command id goes straight into a payload byte, and bytearray assignment truncates
        # silently here - 0x101 leaves as 0x01, a different valid command the peer executes while
        # the call reports success (the rule _prepare_tx() already states for the header fields).
        if isinstance(cmd_id, int) and 0 <= cmd_id <= _CMD_ID_MAX:
            return True
        await self._err(_ERR_BAD_ARG, "command id", cmd_id, "is not a byte value")
        return False

    async def _check_size(self, size: object, *, allow_none: bool) -> bool:
        # A non-int size reaches a comparison or a len() and raises TypeError straight out of a
        # module contracted never to raise; a negative one silently became "don't care" (the
        # module's own internal sentinel), so a caller's typo turned an exact-size GET into an unchecked one.
        if size is None:
            if allow_none:
                return True
        elif isinstance(size, int) and size >= 0:
            return True
        await self._err(_ERR_BAD_ARG, "size", size, "is not a non-negative integer")
        return False

    def _chunk_count(self, total: int) -> int | None:
        # ceil(total / payload_size) + 1, floored at 2: even a payload-less command has one data
        # chunk to acknowledge. -(-a // b) is the integer ceiling - no float division, no math import.
        chunks = max(-(-total // self._payload_size) + 1, _MIN_CHUNKS)
        if chunks > _CHUNKS_MAX:
            return None
        return chunks

    def _dest_size(self, chunks: int, exp_size: int) -> int | None:
        # The upper bound is known the moment CHUNKS is, and an exp_size the train
        # could never deliver is rejected now rather than after running to completion.
        upper = (chunks - 1) * self._payload_size
        if exp_size < 0:
            return upper
        if exp_size > upper:
            return None
        return exp_size

    async def _drain(self, device: "UART", first_ms: int | None = None) -> int:
        # Reads into the RX scratch, never read(): a degraded link must not allocate hardest on the
        # most fragmented heap, and the loop is hard-bounded against a peer that never stops
        # first_ms shortens only the first probe, so a healthy boot skips a full quiet wait.
        self._drain_bound_hit = False  # before any early return, so no caller reads a previous drain's verdict
        buf = self._rx.get_buf()
        if buf is None:
            return 0
        quiet_ms = self._resync_window_ms()
        bound_ms = quiet_ms * _DRAIN_BOUND_MULT  # derived from timeout, not from poll_wait_ms
        wait_ms = quiet_ms if first_ms is None else max(first_ms, 1)
        start = time.ticks_ms()
        total = 0
        while True:
            if time.ticks_diff(time.ticks_ms(), start) > bound_ms:
                # Visible only, and flagged rather than persisted here: the resync that called it
                # persists W54, and setup()'s boot drain persists nothing (C.7.1).
                self._drain_bound_hit = True
                self.pr.wrn("Drain bound reached, resyncing anyway")
                break
            got = await device.readinto(buf, len(buf), timeout_ms=wait_ms)
            if got is None:  # the line has been quiet for a whole window
                break
            total += got
            wait_ms = quiet_ms
        return total

    async def _err(self, errno: int, *args: object) -> None:
        # Every fault persists its errno; a repeat of the newest code is collapsed by the central rule (C.7.1).
        await self.pr.err_s("UART error:", *args, errno=errno)

    async def _fault(self, device: "UART", errno: int, *args: object) -> None:
        # Every fault this module reports also resyncs, without exception - one helper so that is a
        # single enforced shape rather than a convention repeated at every call site.
        await self._err(errno, *args)
        await self._resync(device)

    async def _gate(self, role: str) -> bool:
        # C.13's readiness-gate treatment throughout: a logged refusal returning the method's own
        # sentinel, never an exception.
        if not await self._ready():
            return False
        if self._role != role:
            await self._err(_ERR_UART_ROLE_REFUSED, "wrong role for this call:", self._role)
            return False
        if self._busy:
            await self._err(_ERR_UART_REENTRANT, "already inside a transaction")
            return False
        return True

    def _hold_off_writes(self) -> None:
        self._holdoff_deadline = time.ticks_add(time.ticks_ms(), self._resync_window_ms())
        self._holdoff_active = True

    async def _listen_loop(self) -> None:
        # Returns only on a readiness failure. A link fault is handled by the resync and the
        # backoff below, never by letting the task die: the supervisor would restart a task that
        # had nothing wrong with it, burning the task-error budget toward a reboot.
        backoff = self._backoff_initial_ms
        while self.initialized:
            try:
                result = await self.uart_listen()
                if result.cmd_id is not None:
                    if self._message_callback is not None:
                        # Through the guarded dispatch like every other callback, so an owner's
                        # raise cannot kill the loop the supervisor would then restart.
                        await self._call(self._message_callback, result.cmd_id, result.cmd, result.payload)
                    backoff = self._backoff_initial_ms  # a clean transaction resets it
                    continue
            except Exception as e:  # uart_listen() is contracted never to raise; a contract is not an enforcement
                await self._err(_ERR_UNEXPECTED, "listen loop caught:", e)
            await asyncio.sleep_ms(backoff)  # cancellable, and never a zero-delay retry
            backoff = min(backoff * _BACKOFF_MULT, self._backoff_max_ms)

    async def _listen_unlocked(self, device: "UART", get_cb: "_GetCallback", set_cb: "_SetCallback") -> ListenResult:
        if not await self._read_frame(device, -1):  # the one legitimate unbounded wait
            await self._fault(device, _ERR_TIMEOUT, "listen read failed or was cancelled")
            return _LISTEN_FAILED
        rx = self._rx.get_buf()
        if rx is None:
            return _LISTEN_FAILED
        cmd = rx[_MSG_CMD]
        exp = _CMD_GET if cmd == _CMD_GET else CMD_SET
        err = self._validate(rx, exp, 1, None, None)
        if err:
            await self._fault(device, err, "unexpected frame while listening")
            return _LISTEN_FAILED
        cmd_id = rx[_MSG_PAYLOAD]
        uid = rx[_MSG_UID]
        chunks = rx[_MSG_CHUNKS]
        self._note_valid_frame()
        if cmd == _CMD_GET:
            return await self._answer_get(device, get_cb, cmd_id, uid)
        return await self._accept_set(device, set_cb, cmd_id, uid, chunks)

    def _min_rxbuf(self) -> int:
        # Two independent floors. One whole framed frame, because stop-and-wait means
        # a complete frame can land before the reader is next scheduled; and one poll interval's
        # worth of arriving bytes, because that is how long the tail has to survive unattended.
        bus = self._uart
        if bus is None:
            return 0
        wire = bus.framing.max_encoded(_HEADER_LEN + self._payload_size + bus.crc.length())
        per_poll = ((bus.baudrate // 10) * (bus.poll_wait_ms + _POLL_JITTER_MS)) // 1000
        return max(wire, per_poll)

    def _min_timeout(self) -> int:
        # J.6's GC-pause floor and its idle-rate rule: the reply budget has to cover the peer's
        # own first-byte notice latency, which is poll_idle_ms - a timeout below it expires before
        # an idle responder has looked at the line even once, and every request fails on a sound link.
        bus = self._uart
        if bus is None:
            return 0
        return (2 * bus.poll_wait_ms) + bus.poll_idle_ms + _GC_PAUSE_WORST_MS

    def _note_valid_frame(self) -> None:
        if self._valid_frames < COUNTER_CAP:  # saturates: only its zero test is ever read
            self._valid_frames += 1
        self._blind_resyncs = 0

    @staticmethod
    def _pair(result: object) -> tuple[bool, object] | None:
        # A malformed return is treated exactly like a raise, never unpacked on trust.
        if result is None:
            return None
        try:
            if len(result) != _CALLBACK_PAIR_LEN:  # type: ignore[arg-type]
                return None
            valid = result[0]  # type: ignore[index]
            payload = result[1]  # type: ignore[index]
        except (IndexError, TypeError):
            return None
        if not isinstance(valid, bool):
            return None
        return valid, payload

    def _prepare_tx(self, uid: int, cmd: int, chunks: int, cur_chunk: int, data: "Readable | None", size: int) -> bool:
        # Written by index with an explicit range check, never struct.pack()'d: pack() truncates
        # silently on this platform, so an out-of-range CHUNKS would become a plausible wrong value.
        buf = self._tx.get_buf()
        if buf is None:
            return False
        if not (0 <= uid <= _UID_MAX) or cmd not in (_CMD_ACK, _CMD_GET, CMD_SET):
            return False
        if not (1 <= chunks <= _CHUNKS_MAX) or not (1 <= cur_chunk <= chunks):
            return False
        if not (0 <= size <= self._payload_size):
            return False
        if data is not None and len(data) < size:
            return False
        buf[_MSG_UID] = uid
        buf[_MSG_CMD] = cmd
        buf[_MSG_SIZE] = size  # always the length actually copied, never passed separately
        buf[_MSG_CHUNKS] = chunks
        buf[_MSG_CUR_CHUNK] = cur_chunk
        if size and data is not None:
            buf[_MSG_PAYLOAD : _MSG_PAYLOAD + size] = data[0:size]
        pad = self._payload_size - size
        if pad:  # from the preallocated zero buffer, so no remnant is ever transmitted
            buf[_MSG_PAYLOAD + size : _MSG_PAYLOAD + self._payload_size] = memoryview(self._zero)[0:pad]
        return True

    async def _pull_chunk(self, device: "UART", pull: "_PullCallback", chunk: int, size: int, *, is_last: bool) -> int | None:
        # The callback fills a memoryview of exactly this chunk's region, so it cannot overrun
        # by construction; a short non-final supply aborts before this chunk is sent. Every abort
        # here is mid-train though, so it quiesces - else this side transmits into the peer's own drain.
        region = self._tx.get_data_buf()
        if region is None:
            await self._fault(device, _ERR_ALLOC, "no TX data region")
            return None
        written = await self._call(pull, chunk, region[0:size])
        if not isinstance(written, int) or written < 0 or written > size:
            await self._fault(device, _ERR_CALLBACK, "pull callback returned", written, "for chunk", chunk)
            return None
        if written < size and not is_last:
            await self._fault(device, _ERR_UART_STREAM_SHORT, "pull callback short-filled non-final chunk", chunk)
            return None
        return written

    async def _read_answer_header(self, device: "UART", get_id: int) -> tuple[int, int] | None:
        if not await self._read_frame(device, self._timeout):
            await self._fault(device, _ERR_TIMEOUT, "no answer to GET", get_id)
            return None
        rx = self._rx.get_buf()
        err = self._validate(rx, CMD_SET, 1, None, None)
        if err or rx is None:
            await self._fault(device, err or _ERR_UART_FRAME_INVALID, "invalid answer to GET", get_id)
            return None
        if rx[_MSG_PAYLOAD] != get_id:
            # Otherwise the initiator accepts an answer to a question it never asked.
            await self._fault(device, _ERR_UART_GET_ID_MISMATCH, "answer echoes id", rx[_MSG_PAYLOAD], "not", get_id)
            return None
        self._note_valid_frame()
        return rx[_MSG_CHUNKS], rx[_MSG_UID]

    async def _read_frame(self, device: "UART", timeout_ms: int) -> bool:
        buf = self._rx.get_buf()
        if buf is None:
            return False
        size = await device.readinto_until_complete(
            buf, self._frame_size, start_timeout_ms=timeout_ms, timeout_ms=self._timeout,
        )
        return size == self._frame_size

    async def _ready(self) -> bool:
        if self.initialized:
            return True
        await self.pr.err_s("Not initialized", errno=self._init_errno or _ERR_NOT_INIT)
        return False

    async def _recv_train(
        self, device: "UART", dest: "Writable | None", exp_size: int, push: "_PushCallback | None", chunks: int, prev_uid: int,
    ) -> int | None:
        written = 0
        cur = 1
        while cur < chunks:
            cur += 1
            if not await self._read_frame(device, self._timeout):
                await self._fault(device, _ERR_TIMEOUT, "train stalled at chunk", cur)
                return None
            rx = self._rx.get_buf()
            err = self._validate(rx, CMD_SET, cur, chunks, _next_uid(prev_uid))
            if err or rx is None:
                await self._fault(device, err or _ERR_UART_FRAME_INVALID, "invalid frame at chunk", cur)
                return None
            prev_uid = rx[_MSG_UID]
            size = rx[_MSG_SIZE]
            if exp_size >= 0 and written + size > exp_size:
                # Checked before the copy, so a desynced or hostile peer cannot overrun.
                await self._fault(device, _ERR_UART_SIZE_MISMATCH, "train overshoots expected size", exp_size)
                return None
            if push is not None:
                ok = await self._call(push, cur, memoryview(rx)[_MSG_PAYLOAD : _MSG_PAYLOAD + size])
                if ok is not True:
                    await self._fault(device, _ERR_CALLBACK, "push callback rejected chunk", cur)
                    return None
            elif dest is not None:
                if written + size > len(dest):
                    await self._fault(device, _ERR_UART_SIZE_MISMATCH, "destination too small at chunk", cur)
                    return None
                # Through a memoryview, like the push branch above: slicing the bytearray would
                # build a fresh payload_size copy per chunk - the repeated same-shaped allocation
                # Part I.1 says to avoid on a non-compacting heap.
                dest[written : written + size] = memoryview(rx)[_MSG_PAYLOAD : _MSG_PAYLOAD + size]
            written += size
            self._note_valid_frame()
            if cur == chunks:
                break  # the final ACK is deferred until after the total-size check below
            if not await self._send_ack(device, prev_uid):
                await self._fault(device, _ERR_UART_WRITE_FAILED, "ACK write failed at chunk", cur)
                return None
        if exp_size >= 0 and written != exp_size:
            await self._fault(device, _ERR_UART_SIZE_MISMATCH, "train delivered", written, "of", exp_size)
            return None
        if not await self._send_ack(device, prev_uid):
            await self._fault(device, _ERR_UART_WRITE_FAILED, "final ACK write failed")
            return None
        return written

    async def _reject_wrn(self, device: "UART", cmd_id: int) -> None:
        # A declined command persists W56 every time (a run of identical codes spends one slot under the
        # central rule) and, like every refusal, resyncs.
        await self.pr.wrn_s("callback rejected command", cmd_id, wrnno=_WRN_UART_CMD_DECLINED)
        await self._resync(device)

    async def _resync(self, device: "UART") -> None:
        if self._in_resync:  # a fault inside a resync continues the drain, never nests one
            return
        self._in_resync = True
        try:
            drained = await self._drain(device)
            # A resync is routine and prints; only a drain that hit its bound (a babbling or misconfigured
            # peer) persists W54. Logged after the drain, which decides which one this is.
            if self._drain_bound_hit:
                await self.pr.wrn_s("Resynced the link - drain bound reached, the peer never stopped sending", wrnno=_WRN_UART_DRAIN_BOUND)
            else:
                self.pr.wrn("Resyncing the link")
            self._hold_off_writes()
            if self._uart is not None:
                self._uart.resync_framing()  # inert unless a delimited codec is selected (Part G.2)
            if drained and self._valid_frames == 0:
                # Bytes keep arriving and not one frame ever validates. That is a CRC,
                # baud or payload_size mismatch, and it is indistinguishable from a wiring fault
                # without saying so - it costs a bench session to find otherwise.
                self._blind_resyncs += 1
                if self._blind_resyncs >= _DIAG_RESYNC_STREAK:
                    await self._err(
                        _ERR_UART_LINK_UNINTELLIGIBLE,
                        "bytes arriving but no frame ever valid - check CRC algorithm, baud rate and payload_size",
                    )
        finally:
            self._in_resync = False

    def _resync_window_ms(self) -> int:
        return (self._timeout * _RESYNC_NUM) // _RESYNC_DEN

    async def _run_get(
        self, get_id: int, exp_size: int | None, dest: "Writable | None" = None, push: "_PushCallback | None" = None,
    ) -> tuple[int, bytearray | None] | None:
        # The shared gate/lock/re-entrancy wrapper for all three GET forms. Returns the bytes
        # written plus the buffer this call allocated itself, if any - so only uart_get() has to
        # care about right-sizing, and the _into/stream forms never allocate at all.
        if not await self._gate(ROLE_INITIATOR):
            return None
        if not await self._check_cmd_id(get_id) or not await self._check_size(exp_size, allow_none=True):
            return None
        bus = self._uart
        if bus is None:
            return None
        self._busy = True
        try:
            async with bus as device:
                return await self._get_unlocked(device, get_id, exp_size, dest, push)
        finally:
            self._busy = False

    async def _send_ack(self, device: "UART", uid: int) -> bool:
        # Built into the preallocated scratch, and never gated by the write hold-off: the hold-off
        # covers *initiating* only, so a side keeps confirming the peer's traffic while backing off
        # from its own. Both sides gating ACKs would stall a healthy link for no reason.
        if len(self._ack) < self._frame_size:
            return False
        self._ack[_MSG_UID] = uid
        return await device.writefrom(self._ack, self._frame_size)

    async def _send_train(self, device: "UART", cmd_id: int, payload: "Readable | None", total: int, pull: "_PullCallback | None") -> bool:
        chunks = self._chunk_count(total)
        if chunks is None:
            await self._err(_ERR_UART_PAYLOAD_TOO_LARGE, "payload of", total, "bytes needs more than", _CHUNKS_MAX, "chunks")
            return False  # rejected before the first frame, never partially sent
        self._cmd_buf[0] = cmd_id
        if not await self._write_frame_with_ack(device, CMD_SET, chunks, 1, self._cmd_buf, 1):
            return False
        view = None if payload is None else memoryview(payload)  # sliced, never re-sliced as bytes
        sent = 0
        cur = 1
        while cur < chunks:
            cur += 1
            size = min(total - sent, self._payload_size)
            if pull is not None:
                # The callback fills the TX data region in place and data=None leaves it there, so
                # the shared writer stamps the header around those bytes instead of copying them in
                # a second time - the whole of what a separate streamed-write path used to do.
                written = await self._pull_chunk(device, pull, cur, size, is_last=cur == chunks)
                if written is None or not await self._write_frame_with_ack(device, CMD_SET, chunks, cur, None, written):
                    return False
                sent += written
                continue
            data = view[sent : sent + size] if (view is not None and size) else None
            if not await self._write_frame_with_ack(device, CMD_SET, chunks, cur, data, size):
                return False
            sent += size
        return True

    def _validate(self, buf: bytearray | None, exp_cmd: int, exp_chunk: int, exp_chunks: int | None, exp_uid: int | None) -> int:
        # Returns 0 for a valid frame, else the errno naming the violation. Every check closes a
        # silent-corruption path, not a crash path - which is why they are worth the bytes.
        if buf is None or len(buf) < self._frame_size:
            return _ERR_UART_FRAME_INVALID  # length checked before any indexing
        cmd = buf[_MSG_CMD]
        if cmd not in (_CMD_ACK, _CMD_GET, CMD_SET):
            return _ERR_UART_FRAME_INVALID  # exact match, never a bitmask
        if cmd != exp_cmd:
            return _ERR_UART_WRONG_KIND  # each read site declares what it expects
        if buf[_MSG_UID] > _UID_MAX:
            return _ERR_UART_FRAME_INVALID  # a conforming peer never emits 0xFF
        if cmd == _CMD_ACK:
            return self._validate_ack(buf, exp_uid)
        return self._validate_data(buf, cmd, exp_chunk, exp_chunks, exp_uid)

    def _validate_ack(self, buf: bytearray, exp_uid: int | None) -> int:
        if buf[_MSG_SIZE] != 0 or buf[_MSG_CHUNKS] != 1 or buf[_MSG_CUR_CHUNK] != 1:
            return _ERR_UART_FRAME_INVALID  # a malformed ACK is not valid confirmation
        if exp_uid is not None and buf[_MSG_UID] != exp_uid:
            return _ERR_UART_NO_ACK  # a stale ACK must not confirm the wrong frame
        return 0

    def _validate_config(self) -> int:
        # Never clamps: a clamped payload_size turns a loud configuration error into a link that
        # desyncs intermittently in the field, the one fault the self-healing design cannot heal.
        if self._uart is None:
            return _ERR_UART_NO_BUS
        if not self._uart.framing.ready():
            # The codec reports a failed scratch allocation and nothing was reading it, so a
            # dead codec constructed cleanly and then failed every single write as if the link were.
            return _ERR_ALLOC
        if not isinstance(self._payload_size, int) or not (_PAYLOAD_MIN <= self._payload_size <= _PAYLOAD_MAX):
            return _ERR_UART_PAYLOAD_SIZE
        if self._role not in (ROLE_INITIATOR, ROLE_RESPONDER):
            return _ERR_BAD_ARG
        if not isinstance(self._timeout, int) or self._timeout <= 0:
            return _ERR_UART_TIMEOUT_PARAM
        if self._timeout < self._min_timeout():
            return _ERR_UART_TIMEOUT_PARAM  # J.6: a GC pause or the peer's idle poll would read as a fault
        if self._role == ROLE_RESPONDER and (self._get_callback is None or self._set_callback is None):
            return _ERR_BAD_ARG  # every request would be unanswerable
        if self._uart.rxbuf < self._min_rxbuf():
            return _ERR_UART_RXBUF
        return 0

    def _validate_data(self, buf: bytearray, cmd: int, exp_chunk: int, exp_chunks: int | None, exp_uid: int | None) -> int:
        chunks = buf[_MSG_CHUNKS]
        cur = buf[_MSG_CUR_CHUNK]
        size = buf[_MSG_SIZE]
        if chunks < 1 or cur < 1 or cur > chunks or cur != exp_chunk:
            return _ERR_UART_FRAME_INVALID  # the chunk-index invariant
        if exp_chunks is not None and chunks != exp_chunks:
            return _ERR_UART_FRAME_INVALID  # latched from chunk 1, compared on every frame after
        if exp_uid is not None and buf[_MSG_UID] != exp_uid:
            return _ERR_UART_FRAME_INVALID  # data chunks are UID-checked too, not only ACKs
        if not (0 <= size <= self._payload_size):
            return _ERR_UART_FRAME_INVALID
        return self._validate_size_for_position(cmd, size, cur, chunks)

    def _validate_size_for_position(self, cmd: int, size: int, cur: int, chunks: int) -> int:
        # The sender's SIZE pattern is fully determined by construction, and almost none of it was
        # checked before: each rule here closes a silent-corruption path (changelog A12).
        if cur == 1:
            if size != 1:
                return _ERR_UART_FRAME_INVALID  # else the command id comes from a padding byte
            if cmd == CMD_SET and chunks < _MIN_CHUNKS:
                return _ERR_UART_FRAME_INVALID  # a SET with no data chunk to acknowledge
        elif cur < chunks:
            if size != self._payload_size:
                return _ERR_UART_FRAME_INVALID  # a short middle chunk corrupts silently
        elif size == 0 and chunks != _MIN_CHUNKS:
            return _ERR_UART_FRAME_INVALID  # an empty chunk is legal only as a two-chunk train's last
        return 0

    async def _write_frame_with_ack(self, device: "UART", cmd: int, chunks: int, cur_chunk: int, data: "Readable | None", size: int) -> bool:
        await self._await_write_gate()
        uid = _next_uid(self._uid)
        if not self._prepare_tx(uid, cmd, chunks, cur_chunk, data, size):
            await self._err(_ERR_UART_FRAME_INVALID, "could not build frame", cur_chunk, "of", chunks)
            return False
        self._uid = uid  # only advanced once the frame is genuinely going out
        buf = self._tx.get_buf()
        if buf is None:
            await self._err(_ERR_ALLOC, "no TX buffer")
            return False
        if not await device.writefrom(buf, self._frame_size):
            await self._fault(device, _ERR_UART_WRITE_FAILED, "frame write failed")
            return False
        if not await self._read_frame(device, self._timeout):
            await self._fault(device, _ERR_UART_NO_ACK, "no ACK for frame", cur_chunk)
            return False
        err = self._validate(self._rx.get_buf(), _CMD_ACK, 1, 1, uid)
        if err:
            if err == _ERR_UART_WRONG_KIND:
                # The peer initiated while this side was mid-transaction. Out of contract (owner, 2026-09-11) -
                # there is no arbitration - so it is logged as the peer's violation, not as noise.
                await self._fault(device, _ERR_UART_PEER_INITIATED, "a data frame arrived where an ACK was due")
            else:
                await self._fault(device, err, "invalid ACK for frame", cur_chunk)
            return False
        self._note_valid_frame()
        return True

    # -- starters ----------------------------------------------------------

    def get_task_starters(self) -> "list[Callable[[], _asyncio.Task[Any]]]":
        # The role decides the task set: an initiator exposing a listen task would mean both ends
        # initiate, and the protocol has no arbitration for that.
        if self._role != ROLE_RESPONDER:
            return []
        return [self.start_asy_listen]

    def get_timer_starters(self) -> "list[TimerStarter]":
        return []  # no machine.Timer anywhere in this module, deliberately

    def start_asy_listen(self) -> "_asyncio.Task[None]":
        evtloop = asyncio.get_event_loop()
        return evtloop.create_task(self._listen_loop())

    # -- getters -----------------------------------------------------------

    async def get_error_counter(self) -> "ErrorLog":
        return await self.pr.get_log()

    # -- others ------------------------------------------------------------

    async def clear(self) -> None:
        # The external unstick. Cancel FIRST, outside the lock: a listening responder holds it
        # indefinitely, so locking first would deadlock against the caller this frees. The
        # cancelled read drains on its own path, so only the idle branch drains here.
        if self._uart is None:
            return
        if not await self._uart.cancel_read_timeout():
            async with self._uart as device:
                await self._resync(device)
        elif self._uart.cancel_unacknowledged != self._cancel_unacked_seen:
            # The driver's counter is cumulative, so reading it as a flag reported every later
            # cancel - healthy ones included - as un-acknowledged, persisting a warning each time.
            self._cancel_unacked_seen = self._uart.cancel_unacknowledged
            await self.pr.wrn_s("Driver cancel was not acknowledged", wrnno=_WRN_UART_CANCEL_UNACKED)

    async def reset_error_counter(self) -> None:
        # Clears the history and the link diagnostic's state behind it (valid-frame count, blind-resync streak).
        self._valid_frames = 0
        self._blind_resyncs = 0
        await self.pr.reset()

    async def setup(self) -> bool:
        await self.pr.setup()  # without this the FRAM history silently never persists
        if self._init_errno:
            await self.pr.err_s("Construction failed, not starting", errno=self._init_errno)
            return False
        bus = self._uart
        if bus is None:
            await self.pr.err_s("No bus handle, not starting", errno=_ERR_UART_NO_BUS)
            return False
        async with bus as device:
            # A peer that outlived this side's reset leaves partial-frame bytes in the rxbuf.
            # Recovering reactively would log a fault on every boot of a live link that the FRAM
            # history cannot tell from a real one. A boot drain is not a fault, and not counted.
            drained = await self._drain(device, first_ms=(bus.poll_wait_ms * 2) + _POLL_JITTER_MS)
        if drained:
            # A boot-time drain is expected on a live link and is deliberately not counted -
            # persisting it would put an entry in the FRAM history on every single boot,
            # indistinguishable there from a real fault.
            self.pr.one("Drained", drained, "stale bytes at setup")
        self.initialized = True
        self.pr.one("UART link ready as", self._role)
        return True

    async def uart_get(self, get_id: int, exp_size: int | None = None) -> bytearray | None:
        # None means failure; a zero-length result means a genuinely empty payload. The two must
        # never collapse into one value (J.9).
        result = await self._run_get(get_id, exp_size)
        if result is None:
            return None
        written, own = result
        if own is None:
            return bytearray(0)
        if written == len(own):
            return own
        # Only the don't-care case lands here: one right-sized copy, against the legacy's 254
        # reallocations and its ~2x peak at the final concatenation.
        try:
            return bytearray(memoryview(own)[0:written])
        except (MemoryError, OverflowError):
            await self._err(_ERR_ALLOC, "could not right-size the answer")
            return None

    async def uart_get_into(self, get_id: int, buf: "Writable | None", exp_size: int | None = None) -> int | None:
        # A failed LockableBuffer hands its owner None, so every _into entry point checks it
        # first rather than raising an AttributeError at the worst possible moment.
        if buf is None:
            await self._err(_ERR_ALLOC, "uart_get_into called with no destination buffer")
            return None
        if not await self._check_buffer(buf, writable=True):
            return None
        result = await self._run_get(get_id, exp_size, dest=buf)
        return None if result is None else result[0]

    async def uart_get_stream(self, get_id: int, push: "_PushCallback | None", exp_size: int | None = None) -> int | None:
        if push is None:
            # Without it _recv_train has neither a push callback nor a destination, so every chunk
            # is counted and dropped: the call returns the byte count of an answer nobody received.
            await self._err(_ERR_BAD_ARG, "uart_get_stream needs a push callback")
            return None
        result = await self._run_get(get_id, exp_size, push=push)
        return None if result is None else result[0]

    async def uart_listen(self, get_callback: "_GetCallback | None" = None, set_callback: "_SetCallback | None" = None) -> ListenResult:
        # Returns the namedtuple on every path, including the failure ones - a bare None here is
        # what makes a caller's three-way unpack raise inside a module contracted never to raise.
        if not await self._gate(ROLE_RESPONDER):
            return _LISTEN_FAILED
        get_cb = self._get_callback if get_callback is None else get_callback
        set_cb = self._set_callback if set_callback is None else set_callback
        if get_cb is None or set_cb is None:
            await self._err(_ERR_BAD_ARG, "uart_listen needs both callbacks")
            return _LISTEN_FAILED
        bus = self._uart
        if bus is None:
            return _LISTEN_FAILED
        self._busy = True
        try:
            async with bus as device:
                # If the peer is requesting something it is definitely up again, so the
                # hold-off is dropped here - the one documented reset besides the deadline itself.
                self._holdoff_active = False
                return await self._listen_unlocked(device, get_cb, set_cb)
        finally:
            self._busy = False

    async def uart_set(self, set_id: int, payload: "Readable | None" = None) -> bool:
        # Thin wrapper over the zero-copy form, as FRAMChunk.write() wraps write_into(): the hot
        # path must not be the one that allocates, and a None payload costs no bytearray;
        # size=None defers len() to uart_set_into(), which type-checks buf first.
        return await self.uart_set_into(set_id, payload, None)

    async def uart_set_into(self, set_id: int, buf: "Readable | None", size: int | None = None) -> bool:
        # buf is borrowed for the call's duration and never retained past it; this
        # instance's own uses are serialized by the session lock.
        if not await self._gate(ROLE_INITIATOR):
            return False
        if not await self._check_cmd_id(set_id) or not await self._check_buffer(buf, writable=False) or not await self._check_size(size, allow_none=True):
            return False
        bus = self._uart
        if bus is None:
            return False
        total = (0 if buf is None else len(buf)) if size is None else size
        if total < 0 or (buf is None and total) or (buf is not None and total > len(buf)):
            await self._err(_ERR_UART_SIZE_MISMATCH, "size", total, "does not fit the supplied buffer")
            return False
        self._busy = True
        try:
            async with bus as device:
                return await self._send_train(device, set_id, buf, total, None)
        finally:
            self._busy = False

    async def uart_set_stream(self, set_id: int, total_size: int, pull: "_PullCallback | None") -> bool:
        # A declared total is required up front: every frame carries the train's CHUNKS, chunk 1
        # included (Part J.3), so a genuinely unknown length cannot be sent.
        if not await self._gate(ROLE_INITIATOR):
            return False
        bus = self._uart
        if bus is None:
            return False
        if not await self._check_cmd_id(set_id) or not await self._check_size(total_size, allow_none=False):
            return False
        if pull is None:
            # Refused here, not left to _send_train: its no-pull branch means "the payload argument
            # carries the data", and this entry point has none - so the train went out as
            # total_size bytes of padding while the call reported success.
            await self._err(_ERR_BAD_ARG, "uart_set_stream needs a pull callback")
            return False
        self._busy = True
        try:
            async with bus as device:
                return await self._send_train(device, set_id, None, total_size, pull)
        finally:
            self._busy = False
