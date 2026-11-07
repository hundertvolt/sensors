"""Twin-tier coverage for digital_twin/unix_port_idle_poll.py's _poll_unless_idle(): the zero-timeout rounds it skips
and the rounds that take the real wait (digital_twin/README.md, "unix_port_idle_poll.py")."""

import asyncio
import socket
import sys

sys.path.insert(0, "digital_twin")  # see test_digital_twin_sgp40.py's own comment for why

import unix_port_idle_poll


class _Queue:
    # What _poll_unless_idle() reads of asyncio's IOQueue: map, id(stream) -> [reading task, writing task, stream].
    def __init__(self, *streams: object) -> None:
        self.map: dict[int, list[object]] = {id(stream): [None, None, stream] for stream in streams}


class _Stream:
    # A stream that is no ThreadSafeFlag, with a clear `state` of its own: only the type test sends it to the real wait.
    state = 0


def _clear_flag() -> "asyncio.ThreadSafeFlag":
    flag = asyncio.ThreadSafeFlag()
    flag.clear()
    return flag


def _waits(queue: _Queue, dt: int) -> "list[tuple[object, int]]":
    # The real waits one _poll_unless_idle(queue, dt) round took, as a recording stand-in for IOQueue.wait_io_event.
    calls: list[tuple[object, int]] = []
    real = unix_port_idle_poll._WAIT_IO_EVENT
    unix_port_idle_poll._WAIT_IO_EVENT = lambda q, d: calls.append((q, d))
    try:
        unix_port_idle_poll._poll_unless_idle(queue, dt)
    finally:
        unix_port_idle_poll._WAIT_IO_EVENT = real
    return calls


def test_a_zero_timeout_round_with_only_clear_flags_skips_the_real_wait() -> None:
    assert _waits(_Queue(_clear_flag(), _clear_flag()), 0) == []


def test_a_set_flag_takes_the_real_wait() -> None:
    flag = _clear_flag()
    flag.set()
    queue = _Queue(_clear_flag(), flag)  # after a clear one: every registered stream is looked at, not only the first
    assert _waits(queue, 0) == [(queue, 0)]


def test_a_stream_that_is_no_flag_takes_the_real_wait() -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        for stream in (_Stream(), sock):
            queue = _Queue(_clear_flag(), stream)
            assert _waits(queue, 0) == [(queue, 0)], stream
    finally:
        sock.close()


def test_a_round_with_a_timeout_takes_the_real_wait() -> None:
    # A due task's later wake (dt > 0) and a wait with no task due (-1, core.py:160): only dt 0 is ever skipped.
    for dt in (1, 5, -1):
        queue = _Queue(_clear_flag())
        assert _waits(queue, dt) == [(queue, dt)], dt


def test_an_empty_map_at_a_zero_timeout_is_skipped_as_a_wait_that_would_return_at_once() -> None:
    # The loop waits so with a task due and nothing registered (extmod/asyncio/core.py:158-177, v1.29.0). The real wait
    # finds no event: an empty set counts as all fds (modselect.c:207-208), so :353-364 make t 0 and :370's poll()
    # returns 0 at once, :390 returning it; the skip passes over that and :345's mp_handle_pending(), as py/vm.c:1371 runs.
    assert _waits(_Queue(), 0) == []


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
