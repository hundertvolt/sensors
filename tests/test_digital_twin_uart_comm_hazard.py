"""UARTComm hazards across the twin's wire-timed crossover (SPECIFICATION.md J.7): two initiations on one instance,
clear() racing a transaction, both ends transmitting. Each check runs with no CRC and with CRC16; the pair is
tests/_uart_comm_harness.py's own, here on the twin's UART, UARTLink and bounded LinkPoller."""

import asyncio
import sys

sys.path.insert(0, "digital_twin")  # the twin's machine and rp2 ahead of tests/'s: the harness's `from machine import` binds them

import machine
import microtest
from _async_harness import run
from _error_codes import code
from _src_const import src_const, src_int
from _uart_comm_harness import ERROR_LEVEL, Pair, PollRoundClock, accept_set, echo_get, frames
from _uart_comm_hazard_common import register_both_crc_modes

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Coroutine
    from typing import TypeVar

    from _uart_comm_hazard_common import CrcMaker

    T = TypeVar("T")

_PAYLOAD = 48
_BAUD = 115200  # J.6's line rate
# @tunable l2.uart_comm_hazard_timeout_ms = 100
_TIMEOUT_MS = 100
# @tunable l2.uart_comm_hazard_run_limit_s = 30
_RUN_LIMIT_S = 30
# @tunable l2.uart_comm_hazard_recovery_attempts = 2
_RECOVERY_ATTEMPTS = 2
# @tunable l2.uart_comm_hazard_settle_ms = 5
_SETTLE_MS = 5  # the responder's last read after the initiator's call returned (tests/test_uart_comm_hazard.py's)
# @tunable l2.uart_comm_hazard_wire_poll_ms = 1
_WIRE_POLL_MS = 1  # a real look at the initiator's wire log


def _uart_const(name: str) -> int:
    # One frame-layout or command const() of src/asy_uart_comm.py, read from its source (a const() is no attribute).
    value = src_const("src/asy_uart_comm.py", name)
    assert isinstance(value, int), name
    return value


_UID = _uart_const("_MSG_UID")
_CMD = _uart_const("_MSG_CMD")
_SIZE = _uart_const("_MSG_SIZE")
_CHUNKS = _uart_const("_MSG_CHUNKS")
_CUR = _uart_const("_MSG_CUR_CHUNK")
_POS = _uart_const("_MSG_PAYLOAD")
_CMD_GET: int = src_int("src/asy_uart_comm.py", "_CMD_GET")
_TRAIN = bytes(range(3 * _PAYLOAD - 4))  # a SET of three data chunks: a train with a middle to cut into
_CLEAR_POINTS = ("before_the_first_frame", "mid_train", "after_the_last_ack")

microtest.after_each(machine.reset_test_state)


async def _get_frame(crc: "CrcMaker") -> bytes:
    # A first-chunk GET as a peer starting its own transaction would send it, CRC appended by the bus's own CRC kind.
    frame = bytearray(_POS + _PAYLOAD)
    frame[_UID] = 1
    frame[_CMD] = _CMD_GET
    frame[_SIZE] = 1
    frame[_CHUNKS] = 1
    frame[_CUR] = 1
    if crc is None:
        return bytes(frame)
    framed = await crc().add(frame)
    assert framed is not None
    return bytes(framed)


def _check_both_ends_transmitting(crc: "CrcMaker") -> None:
    # A GET written raw from the responder's side while the initiator awaits its ACK: the initiator logs the
    # peer-initiated code and fails that SET; both ends quiesce and the link works again within two attempts.
    pair = _pair(crc)

    async def scenario() -> "tuple[bool, list[bool]]":
        stray = await _get_frame(crc)
        transfer = asyncio.create_task(pair.initiator.uart_set(1, b"x"))
        while len(pair.wire_from_initiator()) < _frame_len(crc):  # its frame is out: it now awaits the ACK
            await asyncio.sleep_ms(_WIRE_POLL_MS)
        pair.fake_b.write(stray)
        first = await transfer
        await pair.responder.clear()
        attempts: list[bool] = []
        for attempt in range(_RECOVERY_ATTEMPTS):
            listener = asyncio.create_task(pair.responder.uart_listen())
            attempts.append(await pair.initiator.uart_set(2 + attempt, b"y"))
            await asyncio.sleep_ms(_SETTLE_MS)
            listener.cancel()
            if attempts[-1]:
                break
        return first, attempts

    first, attempts = _paced(scenario())
    assert first is False, "a SET answered by a peer's GET reported success"
    assert attempts[-1] is True, f"no recovery within {_RECOVERY_ATTEMPTS} attempts: {attempts}"
    assert code("E", "UART_PEER_INITIATED") in _errnos(pair, pair.initiator.name), _errnos(pair, pair.initiator.name)


def _check_clear_racing_a_transaction_after_the_last_ack(crc: "CrcMaker") -> None:
    _clear_racing(crc, _CLEAR_POINTS[2])


def _check_clear_racing_a_transaction_before_the_first_frame(crc: "CrcMaker") -> None:
    _clear_racing(crc, _CLEAR_POINTS[0])


def _check_clear_racing_a_transaction_mid_train(crc: "CrcMaker") -> None:
    _clear_racing(crc, _CLEAR_POINTS[1])


def _check_two_initiations_on_one_instance(crc: "CrcMaker") -> None:
    # Two tasks starting a SET on the initiator at once: one completes, the other is refused with its sentinel and the
    # re-entrant code; the wire carries only the first's whole frames.
    pair = _pair(crc)

    async def scenario() -> "list[bool]":
        listener = asyncio.create_task(pair.responder.uart_listen())
        first = asyncio.create_task(pair.initiator.uart_set(1, b"aaaa"))
        second = asyncio.create_task(pair.initiator.uart_set(2, b"bbbb"))
        results = [await first, await second]
        await asyncio.sleep_ms(_SETTLE_MS)
        listener.cancel()
        return results

    results = _paced(scenario())
    assert sorted(results) == [False, True], results
    assert _errnos(pair, pair.initiator.name).count(code("E", "UART_REENTRANT")) == 1, _errnos(pair, pair.initiator.name)
    _well_formed(pair, crc)


def _clear_racing(crc: "CrcMaker", point: str) -> None:
    # clear() on the responder at `point` of a three-chunk SET: the SET answers True or False, never hangs, and the next
    # SET after it succeeds.
    pair = _pair(crc)

    async def scenario() -> "tuple[bool, bool]":
        if point == "before_the_first_frame":
            await pair.responder.clear()
        listener = asyncio.create_task(pair.responder.uart_listen())
        transfer = asyncio.create_task(pair.initiator.uart_set(1, _TRAIN))
        if point == "mid_train":
            while len(pair.wire_from_initiator()) < 2 * _frame_len(crc):  # the second data chunk is on the wire
                await asyncio.sleep_ms(_WIRE_POLL_MS)
            await pair.responder.clear()
        sent = await transfer
        if point == "after_the_last_ack":
            await pair.responder.clear()
        await asyncio.sleep_ms(_SETTLE_MS)
        listener.cancel()
        listener = asyncio.create_task(pair.responder.uart_listen())
        again = await pair.initiator.uart_set(2, b"after")
        await asyncio.sleep_ms(_SETTLE_MS)
        listener.cancel()
        return sent, again

    sent, again = _paced(scenario())
    assert sent in (True, False), sent
    assert again is True, f"the SET after clear() at {point} failed"
    _well_formed(pair, crc)


def _errnos(pair: Pair, name: str) -> "list[int]":
    comm = pair.initiator if name == pair.initiator.name else pair.responder
    entry = run(comm.get_error_counter(), _RUN_LIMIT_S)[name]
    return [entry["ErrNum"][i] for i in range(len(entry["ErrNum"])) if entry["ErrType"][i] == "E"]


def _frame_len(crc: "CrcMaker") -> int:
    return _POS + _PAYLOAD + (0 if crc is None else crc().length())


def _paced(coro: "Coroutine[object, object, T]") -> "T":
    # On the poll-round clock (SPECIFICATION.md J.7): both ends share this interpreter, so on the wall clock a host
    # stall would spend the peer's reply budget and fail a correct exchange.
    with PollRoundClock():
        return run(coro, _RUN_LIMIT_S)


def _pair(crc: "CrcMaker") -> Pair:
    # Built at synchronous scope on a new board: the twin's UARTs are static per id, so each pair needs it.
    machine.reset_peripherals()
    maker = (lambda: None) if crc is None else crc
    pair = Pair(payload_size=_PAYLOAD, timeout=_TIMEOUT_MS, get_callback=echo_get(b"v"), set_callback=accept_set(), crc_a=maker(), crc_b=maker(), debug=ERROR_LEVEL)
    # The twin wire takes real time, and Pair's default 9600 baud spends a full frame's wire time twice inside the reply
    # budget: both ends and both wire directions at J.6's line rate (attributes, as an init() would undo the DMA routing).
    pair.fake_a.baudrate = pair.fake_b.baudrate = pair.driver_a.baudrate = pair.driver_b.baudrate = _BAUD
    pair.link.a_to_b.baudrate = pair.link.b_to_a.baudrate = _BAUD
    assert run(pair.setup(), _RUN_LIMIT_S) is True
    return pair


def _well_formed(pair: Pair, crc: "CrcMaker") -> None:
    # The initiator's wire carries whole frames only, each internally consistent.
    pair.link.settle()
    emitted = pair.wire_from_initiator()
    assert len(emitted) % _frame_len(crc) == 0, f"{len(emitted)} bytes on the initiator's wire: a partial frame"
    for frame in frames(emitted, _frame_len(crc)):
        assert 1 <= frame[_CUR] <= frame[_CHUNKS], frame


register_both_crc_modes(globals(), {}, ())

if __name__ == "__main__":
    import microtest

    microtest.run(globals())
