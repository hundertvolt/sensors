"""The Unix port's zero-timeout poll waits 1 ms whenever a non-fd stream such as a ThreadSafeFlag is registered
(extmod/modselect.c:353-370, v1.29.0); rp2 compiles that branch out and returns at once (:400-412). Skipping the rounds
that wait can only report nothing: digital_twin/README.md, "unix_port_idle_poll.py"."""

import asyncio

# asyncio.core is private: replacing IOQueue's wait is the point (the stubs cover only the public API).
import asyncio.core as _core  # type: ignore[import-not-found]

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import Protocol

    class _IOQueue(Protocol):
        # What the skip reads of asyncio's IOQueue: id(stream) -> [reading task, writing task, stream] (core.py:73).
        map: "dict[int, list[object]]"


_FLAG = asyncio.ThreadSafeFlag
_WAIT_IO_EVENT = _core.IOQueue.wait_io_event  # the real wait, which every round but an idle one still takes


def _poll_unless_idle(queue: "_IOQueue", dt: int) -> None:
    # A clear flag's ioctl(MP_STREAM_POLL) answers 0 (extmod/asyncio/event.py:49-52), so with only clear flags registered
    # a zero-timeout poll reports nothing. Keys, not values(): the loop allocates nothing, as core.py:103 iterates.
    if dt == 0:
        entries = queue.map
        for key in entries:
            stream = entries[key][2]
            if type(stream) is not _FLAG or getattr(stream, "state", True):  # no stub declares `state`; absent reads as set
                break
        else:
            return
    _WAIT_IO_EVENT(queue, dt)


def skip_idle_flag_polls() -> None:
    # Called once at module level by a test file, after the prewarm and the UDP shim; it lasts the process.
    _core.IOQueue.wait_io_event = _poll_unless_idle
