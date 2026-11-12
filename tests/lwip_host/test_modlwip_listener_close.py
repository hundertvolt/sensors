"""Closing a listening socket through the patched modlwip on build-lwip (SPECIFICATION.md B.14.4): close() returns and
frees the listener, also one whose listen() ran out of heap, so its port binds again without SO_REUSEADDR. Upstream's
close aborts this build on lwIP's LISTEN-state assert, or frees a pbuf pointer the failed listen() left behind."""

import errno

import lwip
import micropython

_HOST = "127.0.0.1"
_PORT = 50100

# Once per process: nothing else on the Unix port initialises lwIP.
lwip.reset()


def _assert_port_free(port: int) -> None:
    # A bind without SO_REUSEADDR is refused with EADDRINUSE while any pcb still holds the port.
    sock = lwip.socket()
    try:
        sock.bind((_HOST, port))
    except OSError as e:
        assert e.errno != errno.EADDRINUSE, f"port {port} is still held after its listener was closed"
        raise
    finally:
        sock.close()


def _listener(port: int, backlog: int) -> "lwip.socket":
    # The shape asyncio.start_server() builds (extmod/asyncio/stream.py): non-blocking, bound, listening.
    sock = lwip.socket()
    sock.setblocking(False)
    sock.bind((_HOST, port))
    sock.listen(backlog)
    return sock


def test_closing_a_listener_with_a_backlog_array_frees_its_port() -> None:
    # backlog > 1 is the firmware's case: listen() allocates the accept queue as an array.
    _listener(_PORT, 4).close()
    _assert_port_free(_PORT)


def test_closing_a_single_slot_listener_frees_its_port() -> None:
    # backlog <= 1 keeps the accept queue in one item, the other branch of the close's queue walk.
    _listener(_PORT + 1, 1).close()
    _assert_port_free(_PORT + 1)


def test_a_restarted_server_listens_again_on_the_closed_listeners_port() -> None:
    # The supervisor's restart path: a new listener on the port a closed one held.
    _listener(_PORT + 2, 4).close()
    _listener(_PORT + 2, 4).close()
    _assert_port_free(_PORT + 2)


def test_closing_a_socket_whose_listen_ran_out_of_heap_frees_its_port() -> None:
    # listen() takes the LISTEN pcb before it allocates the accept queue; a refusal there leaves the socket STATE_NEW.
    sock = lwip.socket()
    sock.bind((_HOST, _PORT + 3))
    refused = False
    micropython.heap_lock()
    try:
        sock.listen(4)
    except MemoryError:
        refused = True
    finally:
        micropython.heap_unlock()
    sock.close()
    assert refused, "listen(4) allocated its accept queue with the heap locked"
    _assert_port_free(_PORT + 3)


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
