"""Every CMD/SIZE/CHUNKS/CUR_CHUNK/UID value in a first-chunk SET, written raw into the twin wire to a listening
responder: legal frames are answered, illegal ones are not (SPECIFICATION.md J.3/J.4). Full set without CRC, boundary
values with CRC16; each field's sweep ends with one clean exchange."""

import asyncio
import sys

sys.path.insert(0, "digital_twin")  # the twin's machine and rp2 ahead of tests/'s: the harness's `from machine import` binds them

import machine
import microtest
from _async_harness import run
from _src_const import src_const
from _uart_comm_harness import Pair, PollRoundClock, accept_set, copied_out, echo_get

from asy_crc_checks import CRC16

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable

    from _uart_comm_hazard_common import CrcMaker

_PAYLOAD = 8
_BAUD = 115200  # J.6's line rate
# @tunable l2.uart_field_sweep_timeout_ms = 30
_TIMEOUT_MS = 30
# A rejected frame is answered by silence, so each verdict waits one window past the responder's own timeout.
# @tunable l2.uart_field_sweep_quiet_window_ms = 45
_QUIET_WINDOW_MS = 45
# @tunable l2.uart_field_sweep_run_limit_s = 120
_RUN_LIMIT_S = 120
_SETTLE_MS = 5  # the responder's last read after the clean exchange's call returned


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
_CMD_SET = _uart_const("CMD_SET")
# The first-chunk SET's verdict per field, as J.3/J.4 state it and tests/test_uart_comm_hazard.py's L1 sweep checks
# the validator against: (offset, legal(value), the boundary values swept with CRC16).
_SWEPT_FIELDS: "dict[str, tuple[int, Callable[[int], bool], tuple[int, ...]]]" = {
    "cmd": (_CMD, lambda v: v == _CMD_SET, (0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0xFF)),
    "size": (_SIZE, lambda v: v == 1, (0, 1, 2, 8, 9, 255)),
    "chunks": (_CHUNKS, lambda v: v >= 2, (0, 1, 2, 255)),
    "cur_chunk": (_CUR, lambda v: v == 1, (0, 1, 2, 255)),
    "uid": (_UID, lambda v: v <= 0xFE, (0x00, 0xFE, 0xFF)),
}

microtest.after_each(machine.reset_test_state)


async def _first_chunk(offset: int, value: int, crc: "CrcMaker") -> bytes:
    # A legal first chunk of a two-chunk SET (UID 1, SIZE 1, CHUNKS 2, CUR 1, command id 0x07) with one field set.
    frame = bytearray(_POS + _PAYLOAD)
    frame[_UID], frame[_CMD], frame[_SIZE], frame[_CHUNKS], frame[_CUR], frame[_POS] = 1, _CMD_SET, 1, 2, 1, 0x07
    frame[offset] = value
    if crc is None:
        return bytes(frame)
    framed = await crc().add(frame)
    assert framed is not None
    return bytes(framed)


def _pair(crc: "CrcMaker") -> Pair:
    # Built at synchronous scope on a new board: the twin's UARTs are static per id, so each pair needs it.
    machine.reset_peripherals()
    maker = (lambda: None) if crc is None else crc
    pair = Pair(payload_size=_PAYLOAD, timeout=_TIMEOUT_MS, get_callback=echo_get(b"v"), set_callback=accept_set(), crc_a=maker(), crc_b=maker())
    # The twin wire takes real time, and Pair's default 9600 baud spends a full frame's wire time twice inside the reply
    # budget: both ends and both wire directions at J.6's line rate (attributes, as an init() would undo the DMA routing).
    pair.fake_a.baudrate = pair.fake_b.baudrate = pair.driver_a.baudrate = pair.driver_b.baudrate = _BAUD
    pair.link.a_to_b.baudrate = pair.link.b_to_a.baudrate = _BAUD
    assert run(pair.setup(), _RUN_LIMIT_S) is True
    return pair


def _sweep(field: str, crc: "CrcMaker") -> None:
    # Each value written from the initiator's side into a listening responder; an ACK on the responder's wire means the
    # frame was taken, read once its listen returned (a taken first chunk's train aborted, a refused one's resync done)
    # and one quiet window passed. Then one clean exchange on the same pair.
    offset, legal, boundaries = _SWEPT_FIELDS[field]
    values = range(256) if crc is None else boundaries
    pair = _pair(crc)
    responder_wire = pair.link.direction_from(pair.fake_b).wire_log
    returned = [0]

    async def listening() -> None:
        while True:
            await pair.responder.uart_listen()
            returned[0] += 1

    async def scenario() -> "tuple[list[str], bytes | None]":
        wrong: list[str] = []
        listener = asyncio.create_task(listening())
        try:
            for value in values:
                frame = await _first_chunk(offset, value, crc)
                responder_wire.clear()
                seen = returned[0]
                pair.fake_a.write(frame)
                await asyncio.sleep_ms(_QUIET_WINDOW_MS)
                while returned[0] == seen:  # bounded by the run's own limit
                    await asyncio.sleep_ms(1)
                pair.link._advance()  # every byte whose wire time has passed delivered: nothing reads the initiator's end
                acked = len(pair.wire_from_responder()) > 0
                if acked != legal(value):
                    wrong.append(f"{field} {value:#04x}: {'acknowledged' if acked else 'not acknowledged'}")
            await pair.initiator.clear()  # the ACKs no initiator read, flushed before the clean exchange
            clean = copied_out(await pair.initiator.uart_get(1))  # answered by the same listening loop
            await asyncio.sleep_ms(_SETTLE_MS)
        finally:
            listener.cancel()
        return wrong, clean

    with PollRoundClock():
        wrong, clean = run(scenario(), _RUN_LIMIT_S)
    assert wrong == [], wrong
    assert clean == b"v", f"the exchange after the {field} sweep answered {clean!r}"


def _register() -> None:
    # One test per field and mode: the full sweep without CRC, the boundary values with CRC16.
    for field in _SWEPT_FIELDS:

        def full(field: str = field) -> None:
            _sweep(field, None)

        def boundaries(field: str = field) -> None:
            _sweep(field, CRC16)

        globals()[f"test_{field}_sweep_nocrc"] = full
        globals()[f"test_{field}_boundaries_crc16"] = boundaries


_register()

if __name__ == "__main__":
    import microtest

    microtest.run(globals())
