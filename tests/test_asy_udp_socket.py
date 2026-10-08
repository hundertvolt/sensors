import asyncio

# The stubs cover asyncio's public API only; this test reads the private core module's task queue.
import asyncio.core as asyncio_core  # type: ignore[import-not-found]
import select
import socket
import sys
import time

sys.path.insert(0, "digital_twin/unixport")  # the Unix-port UDP address shim (SPECIFICATION.md F.7 row 1)

from _udp_port_redirect import redirect_udp_port
from _unix_port_udp_addr_shim import patch_asy_udp_socket_for_unix_port

import asy_print_log
import asy_udp_socket
from asy_dns_client import DNS_UDP_MAX
from asy_udp_socket import UDPSocket

# UDPSocket takes plain (host, port) tuples; on this Unix build the shim resolves them (once, class-wide).
patch_asy_udp_socket_for_unix_port()

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing isn't available on the real MicroPython test interpreter
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Coroutine, Iterator
    from types import ModuleType
    from typing import Any, NoReturn, TypeVar

    T = TypeVar("T")

# @tunable l1.asy_udp_socket_recv_empty_timeout_ms = 50
_RECV_EMPTY_TIMEOUT_MS = 50
# @tunable l1.asy_udp_socket_attempt_timeout_ms = 200
_ATTEMPT_TIMEOUT_MS = 200
# @tunable l1.asy_udp_socket_exhaust_timeout_ms = 30
_EXHAUST_TIMEOUT_MS = 30
# @tunable l1.asy_udp_socket_peer_recv_timeout_ms = 1000
_PEER_RECV_TIMEOUT_MS = 1000
# @tunable l1.asy_udp_socket_peer_poll_ms = 5
_PEER_POLL_MS = 5
# @tunable l1.asy_udp_socket_reply_timeout_ms = 500
_REPLY_TIMEOUT_MS = 500
# @tunable l1.asy_udp_socket_spoof_wait_ms = 150
_SPOOF_WAIT_MS = 150
# @tunable l1.asy_udp_socket_kernel_queue_s = 0.05
_KERNEL_QUEUE_S = 0.05
# @tunable l1.asy_udp_socket_recv_timeout_ms = 200
_RECV_TIMEOUT_MS = 200
# @tunable l1.asy_udp_socket_in_time_delay_ms = 40
_IN_TIME_DELAY_MS = 40
# @tunable l1.asy_udp_socket_in_time_timeout_ms = 300
_IN_TIME_TIMEOUT_MS = 300
# @tunable l1.asy_udp_socket_too_late_delay_ms = 300
_TOO_LATE_DELAY_MS = 300
# @tunable l1.asy_udp_socket_too_late_timeout_ms = 100
_TOO_LATE_TIMEOUT_MS = 100
# @tunable l1.asy_udp_socket_ready_empty_timeout_ms = 80
_READY_EMPTY_TIMEOUT_MS = 80
# @tunable l1.asy_udp_socket_task_park_s = 0.05
_TASK_PARK_S = 0.05
# @tunable l1.asy_udp_socket_ms_check_timeout_ms = 50
_MS_CHECK_TIMEOUT_MS = 50
# @tunable l1.asy_udp_socket_ms_check_elapsed_max_ms = 2000
_MS_CHECK_ELAPSED_MAX_MS = 2000
# @tunable l1.asy_udp_socket_icmp_delivery_s = 0.2
_ICMP_DELIVERY_S = 0.2
# @tunable l1.asy_udp_socket_icmp_recv_timeout_ms = 5000
_ICMP_RECV_TIMEOUT_MS = 5000
# @tunable l1.asy_udp_socket_icmp_elapsed_max_ms = 1000
_ICMP_ELAPSED_MAX_MS = 1000
# @tunable l1.asy_udp_socket_long_reply_timeout_ms = 1000
_LONG_REPLY_TIMEOUT_MS = 1000
# @tunable l1.asy_udp_socket_unreachable_timeout_ms = 500
_UNREACHABLE_TIMEOUT_MS = 500
# @tunable l1.asy_udp_socket_no_sender_timeout_ms = 100
_NO_SENDER_TIMEOUT_MS = 100
# @tunable l1.asy_udp_socket_first_attempt_s = 0.1
_FIRST_ATTEMPT_S = 0.1
# @tunable l1.asy_udp_socket_retry_cycle_max_ms = 5000
_RETRY_CYCLE_MAX_MS = 5000
# @tunable l1.asy_udp_socket_disconnect_bound_s = 2
_DISCONNECT_BOUND_S = 2
# @tunable l1.asy_udp_socket_connect_bound_s = 3
_CONNECT_BOUND_S = 3
# @tunable l1.asy_udp_socket_enter_sleep_s = 0.1
_ENTER_SLEEP_S = 0.1


def run(coro: "Coroutine[Any, Any, T]") -> "T":  # drives a coroutine to completion for these sync test_* functions
    return asyncio.run(coro)


_HOST = "127.0.0.1"
# Below the OS ephemeral range (32768-60999) so a concurrently-running ephemeral socket can
# never be assigned this port - see scripts/test.sh's own TEST_PARALLELISM comment.
_next_port = 21000


def _make_addr() -> tuple[str, int]:  # a fresh loopback port per call, so tests never contend for the same address
    return (_HOST, _make_port())


def _make_port() -> int:  # a fresh port number only, for tests that build their own addr tuples
    global _next_port
    _next_port += 1
    return _next_port


def _raw(addr: tuple[str, int]) -> tuple[str, int]:
    # This Unix build's raw socket takes getaddrinfo()'s opaque sockaddr, never a tuple (SPECIFICATION.md F.7
    # row 1): only _AdversarialPeer's own socket uses it, every UDPSocket gets the plain tuple.
    return socket.getaddrinfo(addr[0], addr[1])[0][-1]  # type: ignore[return-value]


def _src_const(name: str) -> float:
    # The shipped value, read from the source: a const() is not a module attribute on MicroPython.
    with open("src/asy_udp_socket.py") as f:
        for line in f:
            if line.startswith(name + " = const("):
                return float(line.split("const(", 1)[1].split(")", 1)[0])
    raise AssertionError(name + " not found in src/asy_udp_socket.py")


# ---------------------------------------------------------------------------
# __init__ configuration: every valid combination, plus single and multiple invalid parameter
# recombinations. These only construct the object: no socket call happens until _connect() runs.
# ---------------------------------------------------------------------------


def test_init_accepts_every_valid_mode() -> None:
    for mode in ("client", "server"):
        sock = UDPSocket(("127.0.0.1", 12345), mode=mode)
        assert sock._mode == mode
        assert sock.connected is False
        assert sock._sock is None


def test_init_rejects_a_pre_resolved_sockaddr() -> None:
    # src/ only ever hands over (host, port) tuples; this build's opaque sockaddr is the address shim's
    # business, so a bytes or bytearray address fails at construction like any other non-tuple.
    resolved = socket.getaddrinfo("127.0.0.1", 51500)[0][-1]
    for sockaddr in (bytes(resolved), bytearray(resolved)):  # type: ignore[arg-type]
        try:
            UDPSocket(sockaddr, mode="server")  # type: ignore[arg-type]
            raise AssertionError(f"expected TypeError for addr={sockaddr!r}")
        except TypeError:
            pass


def test_init_rejects_invalid_mode() -> None:
    # An invalid mode used to busy-loop forever inside _connect() with zero await points - a
    # genuine unrecoverable lockup, since the coroutine never yields for even
    # asyncio.wait_for()'s timeout to fire. Validated eagerly here, before _connect() is reachable.
    for bad_mode in ("bogus", "", "CLIENT", "client ", None, 123):
        try:
            UDPSocket(("127.0.0.1", 12345), mode=bad_mode)  # type: ignore[arg-type]
            raise AssertionError(f"expected ValueError for mode={bad_mode!r}")
        except ValueError:
            pass


def test_init_rejects_malformed_addr_tuple() -> None:
    # Bug: a malformed addr tuple (right shape, wrong element types) used to raise an uncaught
    # TypeError from deep inside _connect()'s sock.connect()/bind() call - confirmed directly,
    # bypassing every except OSError clause in the file. Fixed: validated eagerly here.
    for bad_addr in (
        (12345, 80),  # host not a str
        ("127.0.0.1", "80"),  # port not an int
        ("127.0.0.1",),  # wrong length
        ("127.0.0.1", 80, 0, 0),  # wrong length
        (),
    ):
        try:
            UDPSocket(bad_addr, mode="client")  # type: ignore[arg-type]
            raise AssertionError(f"expected TypeError for addr={bad_addr!r}")
        except TypeError:
            pass


def test_init_rejects_addr_of_the_wrong_type_entirely() -> None:
    for bad_addr in (None, 12345, "127.0.0.1", ["127.0.0.1", 80], 3.14, b"\x00" * 16):
        try:
            UDPSocket(bad_addr, mode="client")  # type: ignore[arg-type]
            raise AssertionError(f"expected TypeError for addr={bad_addr!r}")
        except TypeError:
            pass


def test_init_rejects_multiple_invalid_parameters_at_once() -> None:
    # Multiple invalid parameters together must still fail cleanly - not silently succeed, not
    # crash with something other than ValueError/TypeError.
    try:
        UDPSocket(("bad", "addr", "shape"), mode="bogus")  # type: ignore[arg-type]
        raise AssertionError("expected an exception for all-invalid parameters")
    except (TypeError, ValueError):
        pass

    try:
        UDPSocket(12345, mode="nope")  # type: ignore[arg-type]
        raise AssertionError("expected an exception for addr+mode both invalid")
    except (TypeError, ValueError):
        pass

    try:
        UDPSocket(None, mode=42)  # type: ignore[arg-type]
        raise AssertionError("expected an exception for addr+mode both invalid, mode not even a str")
    except (TypeError, ValueError):
        pass


# ---------------------------------------------------------------------------
# Lazy connect + basic client/server round trip
# ---------------------------------------------------------------------------


def test_fresh_client_and_server_round_trip() -> None:
    # Every I/O method must call ready() (which lazily binds/connects via _connect()) before ever
    # touching self._sock - a fresh object must actually send/receive, not return None forever.
    addr = _make_addr()

    async def scenario() -> tuple[int | None, bytes | None, bytes | None]:
        server = UDPSocket(addr, mode="server")
        client = UDPSocket(addr, mode="client")
        try:
            await server._connect()  # deterministically bind before the client sends
            server_task = asyncio.create_task(server.recvfrom(64))
            sent = await client.write(b"ping")
            data, client_addr = await server_task
            reply_sent = await server.sendto(b"pong", client_addr) if client_addr is not None else None
            assert reply_sent == 4
            reply, _ = await client.recvfrom(64)
            return sent, data, reply
        finally:
            await client.disconnect()
            await server.disconnect()

    sent, data, reply = run(scenario())
    assert sent == 4  # len(b"ping")
    assert data == b"ping"
    assert reply == b"pong"


def test_sendto_returns_byte_count_like_write() -> None:
    # sendto() used to be typed `-> None` while actually returning the underlying int byte count
    # at runtime; now typed (and behaves) consistently with write().
    addr = _make_addr()

    async def scenario() -> int | None:
        server = UDPSocket(addr, mode="server")
        try:
            await server._connect()
            return await server.sendto(b"hello", addr)  # a bound UDP socket may send to itself
        finally:
            await server.disconnect()

    assert run(scenario()) == 5


def test_recvfrom_returns_none_sentinel_on_timeout() -> None:
    addr = _make_addr()

    async def scenario() -> tuple[bytes | None, tuple[str, int] | None]:
        server = UDPSocket(addr, mode="server")
        try:
            return await server.recvfrom(64, timeout_ms=_RECV_EMPTY_TIMEOUT_MS)
        finally:
            await server.disconnect()

    data, from_addr = run(scenario())
    assert data is None
    assert from_addr is None


# ---------------------------------------------------------------------------
# write_and_recvfrom - retry budget
# ---------------------------------------------------------------------------


def test_write_and_recvfrom_retries_until_a_reply_arrives() -> None:
    # Bug: the `for _ in range(tries):` loop used to return on the very first iteration
    # regardless of outcome, so `tries` never actually retried. Prove a reply that only arrives
    # after the first request is dropped still gets picked up within the retry budget.
    addr = _make_addr()

    async def scenario() -> bytes | None:
        server = UDPSocket(addr, mode="server")
        client = UDPSocket(addr, mode="client")
        try:
            await server._connect()

            async def drop_first_then_reply() -> None:
                await server.recvfrom(64)  # dropped - no reply sent
                _, from_addr = await server.recvfrom(64)
                if from_addr is not None:
                    await server.sendto(b"pong", from_addr)

            responder = asyncio.create_task(drop_first_then_reply())
            data, _ = await client.write_and_recvfrom(b"ping", 64, timeout_ms=_ATTEMPT_TIMEOUT_MS, tries=3)
            await responder
            return data
        finally:
            await client.disconnect()
            await server.disconnect()

    assert run(scenario()) == b"pong"


def test_write_and_recvfrom_exhausts_tries_and_returns_none_sentinel() -> None:
    addr = _make_addr()  # nobody listens on this address at all

    async def scenario() -> tuple[bytes | None, tuple[str, int] | None]:
        client = UDPSocket(addr, mode="client")
        try:
            return await client.write_and_recvfrom(b"ping", 64, timeout_ms=_EXHAUST_TIMEOUT_MS, tries=2)
        finally:
            await client.disconnect()

    data, from_addr = run(scenario())
    assert data is None
    assert from_addr is None


def test_a_failed_send_returns_without_waiting_for_a_reply() -> None:
    # A try whose write() failed never sent its request, so nothing can answer it: write_and_recvfrom()
    # moves on at once instead of waiting out timeout_ms for a reply that cannot come.
    addr = _make_addr()

    async def scenario() -> "tuple[tuple[bytes | None, tuple[str, int] | None], int]":
        client = UDPSocket(addr, mode="client")
        try:
            await client._connect()
            assert client._sock is not None
            client._sock = _FailingSocket(client._sock, "write", OSError("injected send failure"))  # type: ignore[assignment]
            t0 = time.ticks_ms()
            result = await client.write_and_recvfrom(b"x", 64, timeout_ms=_REPLY_TIMEOUT_MS, tries=1)
            return result, time.ticks_diff(time.ticks_ms(), t0)
        finally:
            await client.disconnect()

    result, elapsed = run(scenario())
    assert result == (None, None)
    assert elapsed < _REPLY_TIMEOUT_MS // 2, elapsed


def test_a_socket_that_never_connects_does_not_wait_for_a_reply() -> None:
    # write() answers None when ready() could not connect; the try then ends after that one failed attempt
    # and its backoff, instead of a second connect attempt and backoff inside recvfrom().
    sock = UDPSocket(_make_addr(), mode="client")
    original = asy_udp_socket.socket
    asy_udp_socket.socket = _FailingSocketModule(OSError("injected setup failure"))  # type: ignore[assignment]
    try:
        t0 = time.ticks_ms()
        result = run(sock.write_and_recvfrom(b"x", 64, timeout_ms=_REPLY_TIMEOUT_MS, tries=1))
        elapsed = time.ticks_diff(time.ticks_ms(), t0)
    finally:
        asy_udp_socket.socket = original
    backoff_ms = int(_src_const("_RETRY_BACKOFF_S") * 1000)
    assert result == (None, None)
    assert backoff_ms <= elapsed < 2 * backoff_ms, elapsed


# ---------------------------------------------------------------------------
# _connect() retry/self-heal
# ---------------------------------------------------------------------------


class _AdversarialPeer:
    # A genuine, independent UDP endpoint - a real socket.socket(), never an UDPSocket - used
    # to drive real-world edge-case traffic (oversized/zero-length/delayed/burst/off-path
    # datagrams) at an UDPSocket under test over actual loopback packets, not mocks.
    def __init__(self, addr: tuple[str, int]) -> None:
        self.addr = addr
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(_raw(addr))
        self.sock.setblocking(False)

    def send(self, data: bytes, target: tuple[str, int]) -> None:  # to a UDPSocket under test, by its plain tuple
        self.sock.sendto(data, _raw(target))

    async def send_after(self, target: tuple[str, int], data: bytes, delay_ms: int = 0) -> None:
        if delay_ms:
            await asyncio.sleep_ms(delay_ms)
        self.sock.sendto(data, target)

    async def recv(self, bufsize: int, timeout_ms: int = _PEER_RECV_TIMEOUT_MS) -> tuple[bytes, tuple[str, int]]:
        poller = select.poll()
        poller.register(self.sock, select.POLLIN)
        t0 = time.ticks_ms()
        while True:
            # Each event's mask is read: ipoll() returns an iterator, always truthy (extmod/modselect.c, v1.29.0).
            for _, event in poller.ipoll(0):
                if event & select.POLLIN:
                    return self.sock.recvfrom(bufsize)  # type: ignore[return-value]  # AF_INET only, see asy_udp_socket.py
            if time.ticks_diff(time.ticks_ms(), t0) > timeout_ms:
                raise OSError("_AdversarialPeer.recv() timed out")
            await asyncio.sleep_ms(_PEER_POLL_MS)

    def close(self) -> None:
        self.sock.close()


# ---------------------------------------------------------------------------
# Real-world UDP edge cases: truncation, zero-length datagrams, oversized sends, kernel-level
# source filtering, burst ordering, and realistically delayed replies - against a genuine
# independent peer, not just "nobody ever responds".
# ---------------------------------------------------------------------------


def test_recvfrom_silently_truncates_an_oversized_datagram() -> None:
    # POSIX UDP behavior, confirmed against this project's Unix-port build: a datagram larger than
    # the recv buffer is truncated to buf bytes with no error and no signal (MSG_TRUNC/recvmsg()
    # are not exposed). Documented rather than "fixed" - the contract callers must design around.
    addr = _make_addr()
    peer_addr = _make_addr()
    oversized = b"X" * 500

    async def scenario() -> bytes | None:
        server = UDPSocket(addr, mode="server")
        peer = _AdversarialPeer(peer_addr)
        try:
            await server._connect()
            peer.send(oversized, addr)
            data, _ = await server.recvfrom(10, timeout_ms=_REPLY_TIMEOUT_MS)
            return data
        finally:
            peer.close()
            await server.disconnect()

    assert run(scenario()) == b"X" * 10  # truncated, not the full 500 bytes, no exception


def test_recvfrom_treats_a_zero_length_datagram_as_a_real_reply_not_a_timeout() -> None:
    # UDP explicitly allows zero-length payloads (RFC 768). recvfrom() must return (b"", addr) -
    # distinguishable from the (None, None) timeout/error sentinel, since `data is not None` is
    # exactly what write_and_recvfrom() checks to decide a reply arrived.
    addr = _make_addr()
    peer_addr = _make_addr()

    async def scenario() -> bytes | None:
        server = UDPSocket(addr, mode="server")
        peer = _AdversarialPeer(peer_addr)
        try:
            await server._connect()
            peer.send(b"", addr)
            data, _ = await server.recvfrom(64, timeout_ms=_REPLY_TIMEOUT_MS)
            return data
        finally:
            peer.close()
            await server.disconnect()

    data = run(scenario())
    assert data == b""
    assert data is not None


def test_sendto_returns_none_sentinel_for_a_too_large_outgoing_payload() -> None:
    # Confirmed directly: sendto() with a payload over the ~65507-byte max IPv4 UDP payload
    # raises OSError (EMSGSIZE) - must be caught and converted like every other socket failure.
    addr = _make_addr()
    huge = b"X" * 70000

    async def scenario() -> int | None:
        client = UDPSocket(addr, mode="client")
        try:
            return await client.sendto(huge, addr)
        finally:
            await client.disconnect()

    assert run(scenario()) is None


def test_arbitrary_binary_content_round_trips_untouched() -> None:
    # This module is a content-agnostic transport - a datagram with invalid/non-UTF8 bytes, bogus
    # "header" values, etc. must still be delivered byte-for-byte. Validating payload structure
    # (NTP header, DNS query) is the caller's job, not this module's.
    addr = _make_addr()
    garbage = bytes(range(256)) + b"\xff\xfe\x00\x00" + bytes([0xDE, 0xAD, 0xBE, 0xEF]) * 10

    async def scenario() -> bytes | None:
        server = UDPSocket(addr, mode="server")
        client = UDPSocket(addr, mode="client")
        try:
            await server._connect()
            task = asyncio.create_task(server.recvfrom(1024))
            await client.write(garbage)
            data, _ = await task
            return data  # asyncio.Task's stub now preserves recvfrom()'s precise return type
        finally:
            await client.disconnect()
            await server.disconnect()

    assert run(scenario()) == garbage


def test_client_mode_filters_datagrams_from_unexpected_sources() -> None:
    # connect() on the client socket is not just convenience - the kernel refuses to deliver
    # datagrams from any address other than the connected peer. Proven with a genuine third,
    # independent endpoint acting as an off-path sender against the exact same port.

    # This is the Unix-port/BSD-socket half of BACKLOG.md's open question 5; real rp2/lwIP is a
    # different socket implementation and is covered instead by tests_hardware/bench/
    # test_network_resilience.py, which confirmed the same property holds on real hardware.
    peer_addr = _make_addr()
    attacker_addr = _make_addr()

    async def scenario() -> tuple[bytes | None, bytes | None]:
        peer = _AdversarialPeer(peer_addr)
        attacker = _AdversarialPeer(attacker_addr)
        client = UDPSocket(peer_addr, mode="client")
        try:
            await client._connect()
            await client.write(b"hello")  # lets peer discover the client's real ephemeral address
            _, client_addr = await peer.recv(64)
            assert client_addr is not None

            attacker.sock.sendto(b"spoofed", client_addr)
            spoofed_result, _ = await client.recvfrom(64, timeout_ms=_SPOOF_WAIT_MS)

            peer.sock.sendto(b"legit", client_addr)
            legit_result, _ = await client.recvfrom(64, timeout_ms=_REPLY_TIMEOUT_MS)
            return spoofed_result, legit_result
        finally:
            peer.close()
            attacker.close()
            await client.disconnect()

    spoofed_result, legit_result = run(scenario())
    assert spoofed_result is None  # filtered at the kernel level, never delivered
    assert legit_result == b"legit"


def test_recvfrom_drains_a_burst_of_queued_datagrams_in_order() -> None:
    # A flood/burst of datagrams queued before the server ever drains them must come out in the
    # order they were sent, with none lost or merged.
    addr = _make_addr()
    peer_addr = _make_addr()

    async def scenario() -> list[bytes | None]:
        server = UDPSocket(addr, mode="server")
        peer = _AdversarialPeer(peer_addr)
        try:
            await server._connect()
            for i in range(5):
                peer.send(f"pkt-{i}".encode(), addr)
            await asyncio.sleep(_KERNEL_QUEUE_S)  # let the kernel queue all 5 before draining starts
            results = []
            for _ in range(5):
                data, _ = await server.recvfrom(64, timeout_ms=_RECV_TIMEOUT_MS)
                results.append(data)
            return results
        finally:
            peer.close()
            await server.disconnect()

    assert run(scenario()) == [b"pkt-0", b"pkt-1", b"pkt-2", b"pkt-3", b"pkt-4"]


def test_recvfrom_respects_timeout_against_a_realistically_delayed_genuine_reply() -> None:
    # Not just "nobody ever responds" - a genuine independent peer that actually replies, but
    # late. Proves timeout correctness under realistic network-like latency: a reply comfortably
    # inside the window is delivered; one arriving after the window already closed is not.
    peer_addr = _make_addr()

    async def scenario() -> tuple[bytes | None, bytes | None]:
        client = UDPSocket(peer_addr, mode="client")
        peer = _AdversarialPeer(peer_addr)
        try:
            await client._connect()
            await client.write(b"hello")  # lets peer discover the client's real ephemeral address
            _, client_addr = await peer.recv(64)
            assert client_addr is not None

            in_time_sender = asyncio.create_task(peer.send_after(client_addr, b"in-time", delay_ms=_IN_TIME_DELAY_MS))
            in_time, _ = await client.recvfrom(64, timeout_ms=_IN_TIME_TIMEOUT_MS)
            await in_time_sender  # already finished - the reply above is what it sent

            too_late_sender = asyncio.create_task(peer.send_after(client_addr, b"too-late", delay_ms=_TOO_LATE_DELAY_MS))
            too_late, _ = await client.recvfrom(64, timeout_ms=_TOO_LATE_TIMEOUT_MS)
            await too_late_sender  # let the delayed send actually happen before teardown
            return in_time, too_late
        finally:
            peer.close()
            await client.disconnect()

    in_time, too_late = run(scenario())
    assert in_time == b"in-time"
    assert too_late is None


# ---------------------------------------------------------------------------
# ready()'s two poll rates: _POLL_WAIT_MS with a deadline, _POLL_IDLE_MS without one
# ---------------------------------------------------------------------------


class _EnoughRoundsError(Exception):
    pass


class _RecordingAsyncio:
    # asyncio is a frozen Python package whose attributes tests may assign (test_asy_bmp3xx_driver.py patches asyncio.sleep);
    # this wraps it instead so the recording also sees ready()'s own sleep_ms() calls through asy_udp_socket's module-level
    # name, the way _RaisingSocketModule replaces the read-only C `socket`. stop_after > 0 ends a wait with no deadline.
    def __init__(self, real: "ModuleType", stop_after: int = 0) -> None:
        self._real = real
        self.sleep_ms_calls: list[int] = []
        self._stop_after = stop_after

    def sleep_ms(self, ms: int) -> "Awaitable[None]":
        self.sleep_ms_calls.append(ms)
        if self._stop_after and len(self.sleep_ms_calls) >= self._stop_after:
            raise _EnoughRoundsError
        # Bound to its own local first: a module attribute is statically untyped, and this
        # wrapper's own callers (ready()'s poll loop) do await what it hands back.
        sleeper: Awaitable[None] = self._real.sleep_ms(ms)
        return sleeper

    def __getattr__(self, name: str) -> object:
        return getattr(self._real, name)


def _record_ready_sleeps(timeout_ms: int, stop_after: int = 0) -> "list[int]":
    # ready(POLLIN) on a bound socket nothing ever reaches; a wait with no deadline ends at the recorder's stop_after.
    recorder = _RecordingAsyncio(asy_udp_socket.asyncio, stop_after)
    asy_udp_socket.asyncio = recorder  # type: ignore[assignment]
    try:
        sock = UDPSocket(_make_addr(), mode="server")
        try:
            run(sock.ready(select.POLLIN, timeout_ms=timeout_ms))
            assert not stop_after, "ready() returned with nothing to read and no deadline"
        except _EnoughRoundsError:
            pass
        finally:
            run(sock.disconnect())
    finally:
        asy_udp_socket.asyncio = recorder._real
    return recorder.sleep_ms_calls


def test_ready_with_a_deadline_polls_at_the_transaction_rate() -> None:
    # A wait with a deadline sits inside an exchange (DNS, NTP): every round sleeps _POLL_WAIT_MS, never
    # a busy-spin of ipoll(0)+sleep_ms(0) on RP2040's single core.
    sleeps = _record_ready_sleeps(_READY_EMPTY_TIMEOUT_MS)
    assert len(sleeps) > 0
    assert all(ms == _src_const("_POLL_WAIT_MS") for ms in sleeps), sleeps


def test_ready_without_a_deadline_polls_at_the_idle_rate() -> None:
    # A wait with no deadline is a listen whose traffic may not come at all (the captive DNS): every round
    # sleeps the slower _POLL_IDLE_MS (SPECIFICATION.md F.5.9's shape).
    sleeps = _record_ready_sleeps(-1, stop_after=2)
    assert len(sleeps) == 2, sleeps
    assert all(ms == _src_const("_POLL_IDLE_MS") for ms in sleeps), sleeps


# lwIP's per-socket UDP receive queue on rp2: extmod/modlwip.c:299 LWIP_INCOMING_PACKET_QUEUE_LEN, v1.29.0.
_LWIP_UDP_QUEUE_LEN = 4


def test_queued_datagrams_are_read_without_an_idle_sleep() -> None:
    # Every ready() reads ipoll(0) before it sleeps, so a listener drains a full lwIP queue back to back:
    # no poll round sleeps between the queued datagrams, and the whole drain fits inside one _POLL_IDLE_MS.
    addr = _make_addr()
    recorder = _RecordingAsyncio(asy_udp_socket.asyncio)

    async def scenario() -> "tuple[list[bytes | None], int]":
        server = UDPSocket(addr, mode="server")
        peer = _AdversarialPeer(_make_addr())
        try:
            await server._connect()
            for i in range(_LWIP_UDP_QUEUE_LEN):
                peer.send(f"q-{i}".encode(), addr)
            await asyncio.sleep(_KERNEL_QUEUE_S)  # all queued before the drain starts
            asy_udp_socket.asyncio = recorder  # type: ignore[assignment]
            got: list[bytes | None] = []
            t0 = time.ticks_ms()
            for _ in range(_LWIP_UDP_QUEUE_LEN):
                data, _ = await server.recvfrom(64)  # no deadline: the captive DNS listen's call
                got.append(data)
            return got, time.ticks_diff(time.ticks_ms(), t0)
        finally:
            asy_udp_socket.asyncio = recorder._real
            peer.close()
            await server.disconnect()

    got, elapsed = run(scenario())
    assert got == [f"q-{i}".encode() for i in range(_LWIP_UDP_QUEUE_LEN)]
    assert recorder.sleep_ms_calls == [], recorder.sleep_ms_calls
    assert elapsed < _src_const("_POLL_IDLE_MS"), elapsed


class _NeverReadyPoller:
    # Bounded stand-in, never a real select.poll(): its readiness is scripted (never), not polled in
    # real time (CLAUDE.md "Known hang cause"); register()/unregister() accept anything.
    def ipoll(self, _timeout: int) -> "list[tuple[object, int]]":
        return []

    def register(self, *_args: object) -> None:
        pass

    def unregister(self, *_args: object) -> None:
        pass


def test_a_bounded_ready_leaves_no_poll_task_behind() -> None:
    # The deadline is asyncio.wait_for_ms() around the poll (SPECIFICATION.md F.2): on timeout it
    # cancels the poll, so nothing keeps polling after ready() answered False.
    addr = _make_addr()

    async def scenario() -> "tuple[bool, int, object]":
        sock = UDPSocket(addr, mode="server")
        try:
            await sock._connect()
            sock.poller = _NeverReadyPoller()  # type: ignore[assignment]
            t0 = time.ticks_ms()
            result = await sock.ready(select.POLLIN, timeout_ms=_RECV_EMPTY_TIMEOUT_MS)
            elapsed = time.ticks_diff(time.ticks_ms(), t0)
            await asyncio.sleep_ms(0)  # let a cancelled poll task finish unwinding
            return result, elapsed, asyncio_core._task_queue.peek()
        finally:
            await sock.disconnect()

    result, elapsed, leftover = run(scenario())
    assert result is False
    assert elapsed >= _RECV_EMPTY_TIMEOUT_MS, elapsed
    assert leftover is None, "a poll task outlived ready()'s deadline"


# ---------------------------------------------------------------------------
# MemoryError must be caught everywhere OSError is - confirmed directly it is NOT an OSError
# subclass in MicroPython, and RP2040's 264KB SRAM makes allocation failure realistic.
# ---------------------------------------------------------------------------


class _MemoryErrorOnceSocketModule:
    # Same monkeypatch technique as _RaisingSocketModule below - socket() itself raises
    # MemoryError instead of OSError, proving _connect()'s outer try/except catches it too.
    AF_INET = socket.AF_INET
    SOCK_DGRAM = socket.SOCK_DGRAM
    SOL_SOCKET = socket.SOL_SOCKET
    SO_REUSEADDR = socket.SO_REUSEADDR

    def socket(self, _af: int, _sock_type: int) -> "NoReturn":  # asy_udp_socket.py calls socket() positionally
        raise MemoryError("simulated allocation failure")


def test_connect_setup_memoryerror_self_heals_instead_of_raising() -> None:
    addr = _make_addr()
    sock = UDPSocket(addr, mode="server")
    original_socket = asy_udp_socket.socket
    asy_udp_socket.socket = _MemoryErrorOnceSocketModule()  # type: ignore[assignment]
    try:
        run(sock._connect())  # must not raise despite socket() raising MemoryError
    finally:
        asy_udp_socket.socket = original_socket

    assert sock.connected is False
    assert sock._sock is None

    try:
        run(sock._connect())  # the fault is gone now - should self-heal and succeed
        assert sock.connected is True
    finally:
        run(sock.disconnect())


class _MemoryErrorSocketWrapper:
    # Wraps a real, already-connected/bound socket whose sendto()/write()/recvfrom() raise
    # MemoryError instead of doing I/O, proving each public method's except clause catches that
    # too, not only OSError. Everything else falls through to the real socket via __getattr__.
    def __init__(self, real: "socket.socket") -> None:
        self._real = real

    def sendto(self, *_a: object, **_k: object) -> "NoReturn":
        raise MemoryError("simulated allocation failure")

    def write(self, *_a: object, **_k: object) -> "NoReturn":
        raise MemoryError("simulated allocation failure")

    def recvfrom(self, *_a: object, **_k: object) -> "NoReturn":
        raise MemoryError("simulated allocation failure")

    def __getattr__(self, name: str) -> object:
        return getattr(self._real, name)


def test_write_returns_none_sentinel_on_memoryerror() -> None:
    addr = _make_addr()

    async def scenario() -> int | None:
        client = UDPSocket(addr, mode="client")
        try:
            await client._connect()
            assert client._sock is not None
            client._sock = _MemoryErrorSocketWrapper(client._sock)  # type: ignore[assignment]
            return await client.write(b"x")
        finally:
            await client.disconnect()

    assert run(scenario()) is None


def test_sendto_returns_none_sentinel_on_memoryerror() -> None:
    addr = _make_addr()

    async def scenario() -> int | None:
        server = UDPSocket(addr, mode="server")
        try:
            await server._connect()
            assert server._sock is not None
            server._sock = _MemoryErrorSocketWrapper(server._sock)  # type: ignore[assignment]
            return await server.sendto(b"x", addr)
        finally:
            await server.disconnect()

    assert run(scenario()) is None


def test_recvfrom_returns_none_sentinel_on_memoryerror() -> None:
    addr = _make_addr()
    peer_addr = _make_addr()

    async def scenario() -> tuple[bytes | None, tuple[str, int] | None]:
        server = UDPSocket(addr, mode="server")
        peer = _AdversarialPeer(peer_addr)
        try:
            await server._connect()
            peer.send(b"data", addr)
            await asyncio.sleep(_KERNEL_QUEUE_S)  # a genuinely pending datagram, so recvfrom() actually
            # reaches sock.recvfrom() instead of timing out inside ready() first
            assert server._sock is not None
            server._sock = _MemoryErrorSocketWrapper(server._sock)  # type: ignore[assignment]
            return await server.recvfrom(64, timeout_ms=_RECV_TIMEOUT_MS)
        finally:
            peer.close()
            await server.disconnect()

    assert run(scenario()) == (None, None)


# ---------------------------------------------------------------------------
# A caught MemoryError's own text reaches the console: the class has no logger, and the memory gates
# read console output (CLAUDE.md), so every arm prints it once and still returns its sentinel.
# ---------------------------------------------------------------------------


class _PrintRecorder:
    # Local stand-in for a shared print recorder: shadows print() inside asy_print_log only, where
    # console() prints, so each console line is captured as its joined text; restore() removes the shadow.
    def __init__(self) -> None:
        self.lines: list[str] = []
        asy_print_log.print = self  # type: ignore[attr-defined]

    def __call__(self, *args: object, **_kwargs: object) -> None:
        self.lines.append(" ".join(str(a) for a in args))

    def restore(self) -> None:
        del asy_print_log.print  # type: ignore[attr-defined]


class _FailingSocketModule:
    # The _RaisingSocketModule technique with the exception chosen per case: socket() raises `exc`.
    AF_INET = socket.AF_INET
    SOCK_DGRAM = socket.SOCK_DGRAM
    SOL_SOCKET = socket.SOL_SOCKET
    SO_REUSEADDR = socket.SO_REUSEADDR

    def __init__(self, exc: BaseException) -> None:
        self._exc = exc

    def socket(self, _af: int, _sock_type: int) -> "NoReturn":  # asy_udp_socket.py calls socket() positionally
        raise self._exc


class _FailingSocket:
    # Wraps a real bound or connected socket: the named method raises `exc`, every other call reaches the real one.
    def __init__(self, real: "socket.socket", method: str, exc: BaseException) -> None:
        self._real = real
        self._method = method
        self._exc = exc

    def _call(self, name: str, *args: object) -> object:
        if name == self._method:
            raise self._exc
        real: Callable[..., object] = getattr(self._real, name)
        return real(*args)

    def sendto(self, *args: object) -> object:
        return self._call("sendto", *args)

    def write(self, *args: object) -> object:
        return self._call("write", *args)

    def recvfrom(self, *args: object) -> object:
        return self._call("recvfrom", *args)

    def close(self) -> object:
        return self._call("close")

    def __getattr__(self, name: str) -> object:
        return getattr(self._real, name)


class _FailingPoller:
    # Wraps the socket's real poller (a real fd, never a fake stream): the named method raises `exc`.
    def __init__(self, real: "select.poll", method: str, exc: BaseException) -> None:
        self._real = real
        self._method = method
        self._exc = exc

    def register(self, *args: object) -> None:
        self._real.register(*args)

    def unregister(self, *args: object) -> None:
        if self._method == "unregister":
            raise self._exc
        self._real.unregister(*args)

    def ipoll(self, *args: object) -> "Iterator[tuple[object, int]]":
        if self._method == "ipoll":
            raise self._exc
        return self._real.ipoll(*args)


async def _connect_arm(exc: BaseException) -> object:
    # socket() raises: the attempt fails, the backoff still runs, and the object stays torn down.
    sock = UDPSocket(_make_addr(), mode="server")
    original = asy_udp_socket.socket
    asy_udp_socket.socket = _FailingSocketModule(exc)  # type: ignore[assignment]
    try:
        t0 = time.ticks_ms()
        await sock._connect()
        backoff_waited = time.ticks_diff(time.ticks_ms(), t0) >= int(_src_const("_RETRY_BACKOFF_S") * 1000)
    finally:
        asy_udp_socket.socket = original
    return sock.connected, sock._sock is None, backoff_waited


async def _unregister_arm(exc: BaseException) -> object:
    sock = UDPSocket(_make_addr(), mode="server")
    await sock._connect()
    assert sock.poller is not None
    sock.poller = _FailingPoller(sock.poller, "unregister", exc)  # type: ignore[assignment]
    ok = await sock.disconnect()
    return ok, sock._sock is None, sock.connected


async def _close_arm(exc: BaseException) -> object:
    sock = UDPSocket(_make_addr(), mode="server")
    await sock._connect()
    real = sock._sock
    assert real is not None
    sock._sock = _FailingSocket(real, "close", exc)  # type: ignore[assignment]
    ok = await sock.disconnect()
    real.close()  # the double kept the real socket open
    return ok, sock._sock is None, sock.connected


async def _ready_arm(exc: BaseException) -> object:
    sock = UDPSocket(_make_addr(), mode="server")
    try:
        await sock._connect()
        assert sock.poller is not None
        sock.poller = _FailingPoller(sock.poller, "ipoll", exc)  # type: ignore[assignment]
        return await sock.ready(select.POLLIN, timeout_ms=_RECV_EMPTY_TIMEOUT_MS)
    finally:
        await sock.disconnect()


async def _sendto_arm(exc: BaseException) -> object:
    addr = _make_addr()
    sock = UDPSocket(addr, mode="server")
    try:
        await sock._connect()
        assert sock._sock is not None
        sock._sock = _FailingSocket(sock._sock, "sendto", exc)  # type: ignore[assignment]
        return await sock.sendto(b"x", addr)
    finally:
        await sock.disconnect()


async def _write_arm(exc: BaseException) -> object:
    sock = UDPSocket(_make_addr(), mode="client")
    try:
        await sock._connect()
        assert sock._sock is not None
        sock._sock = _FailingSocket(sock._sock, "write", exc)  # type: ignore[assignment]
        return await sock.write(b"x")
    finally:
        await sock.disconnect()


async def _recvfrom_arm(exc: BaseException) -> object:
    addr = _make_addr()
    sock = UDPSocket(addr, mode="server")
    try:
        await sock._connect()
        assert await sock.sendto(b"x", addr) == 1  # a pending datagram, so recvfrom() reaches the socket call
        await asyncio.sleep(_KERNEL_QUEUE_S)
        assert sock._sock is not None
        sock._sock = _FailingSocket(sock._sock, "recvfrom", exc)  # type: ignore[assignment]
        return await sock.recvfrom(64, timeout_ms=_RECV_TIMEOUT_MS)
    finally:
        await sock.disconnect()


# (arm, scenario, the arm's sentinel): _connect() also reports that its backoff ran, the two teardown arms
# disconnect()'s False with the state cleared.
_ARMS: "tuple[tuple[str, Callable[[BaseException], Coroutine[object, object, object]], object], ...]" = (
    ("_connect", _connect_arm, (False, True, True)),
    ("unregister", _unregister_arm, (False, True, False)),
    ("close", _close_arm, (False, True, False)),
    ("ready", _ready_arm, False),
    ("sendto", _sendto_arm, None),
    ("write", _write_arm, None),
    ("recvfrom", _recvfrom_arm, (None, None)),
)


def _arms_off_target(make_exc: "Callable[[str], BaseException]", *, expect_line: bool) -> "list[tuple[str, object, list[str]]]":
    # Every arm whose result is not its sentinel, or whose console lines are not the one expected line (or none),
    # as (name, result, lines); each arm runs from this synchronous scope.
    wrong = []
    for arm, scenario, sentinel in _ARMS:
        recorder = _PrintRecorder()
        try:
            got = run(scenario(make_exc(arm)))
        finally:
            recorder.restore()
        if got != sentinel or recorder.lines != (["UDPSocket injected for " + arm] if expect_line else []):
            wrong.append((arm, got, recorder.lines))
    return wrong


def test_an_allocation_failure_in_each_arm_prints_its_text_and_keeps_the_sentinel() -> None:
    # Injected text worded clear of the memory gates' markers; a real failure's own text is meant to trip them.
    wrong = _arms_off_target(lambda arm: MemoryError("injected for " + arm), expect_line=True)
    assert not wrong, wrong


def test_an_os_error_in_each_arm_prints_nothing_and_keeps_the_sentinel() -> None:
    wrong = _arms_off_target(lambda arm: OSError("injected for " + arm), expect_line=False)
    assert not wrong, wrong


# ---------------------------------------------------------------------------
# disconnect() must clear its own state even when unregister()/close() themselves fail
# ---------------------------------------------------------------------------


class _RaisingUnregisterPoller:
    # unregister() raises - register()/ipoll() still delegate to the real poller so the rest of
    # the object's lifecycle (which already ran before this gets swapped in) is unaffected.
    def __init__(self, real: "select.poll") -> None:
        self._real = real

    def unregister(self, _sock: "socket.socket") -> "NoReturn":  # asy_udp_socket.py calls unregister() positionally
        raise OSError("simulated unregister failure")

    def register(self, *a: object, **k: object) -> None:
        self._real.register(*a, **k)

    def ipoll(self, *a: object, **k: object) -> "Iterator[tuple[Any, ...]]":
        return self._real.ipoll(*a, **k)


def test_disconnect_clears_state_even_when_unregister_raises() -> None:
    # disconnect()'s single try/except used to wrap unregister()+close()+state-clearing together,
    # so a raising unregister() aborted the block before self._sock/self.poller/self.connected were
    # reset - leaving the object stuck half-connected forever, with no self-heal.
    addr = _make_addr()

    async def scenario() -> tuple[bool, bool, bool, bool]:
        sock = UDPSocket(addr, mode="server")
        await sock._connect()
        assert sock.connected
        real_poller = sock.poller
        assert real_poller is not None  # a connected socket always has one
        sock.poller = _RaisingUnregisterPoller(real_poller)  # type: ignore[assignment]
        ok = await sock.disconnect()
        return sock._sock is None, sock.poller is None, sock.connected is False, ok

    sock_cleared, poller_cleared, not_connected, ok = run(scenario())
    assert sock_cleared and poller_cleared and not_connected
    # Step 6 silent-failure-masking finding: disconnect() now reports a failed unregister() via its
    # own return value, since this logger-less class has no other way to signal it to the caller.
    assert ok is False


class _RaisingCloseSocket:
    def __init__(self, real: "socket.socket") -> None:
        self._real = real

    def close(self) -> "NoReturn":
        raise OSError("simulated close failure")

    def __getattr__(self, name: str) -> object:
        return getattr(self._real, name)


def test_disconnect_clears_state_even_when_sock_close_raises() -> None:
    addr = _make_addr()

    async def scenario() -> tuple[bool, bool, bool, bool]:
        sock = UDPSocket(addr, mode="server")
        await sock._connect()
        assert sock.connected
        real_sock = sock._sock
        assert real_sock is not None  # a connected socket always has one
        sock._sock = _RaisingCloseSocket(real_sock)  # type: ignore[assignment]
        ok = await sock.disconnect()
        return sock._sock is None, sock.poller is None, sock.connected is False, ok

    sock_cleared, poller_cleared, not_connected, ok = run(scenario())
    assert sock_cleared and poller_cleared and not_connected
    assert ok is False  # Step 6 finding - see the unregister-raises test above for the full note


# ---------------------------------------------------------------------------
# ready() must survive a concurrent disconnect() on the same instance
# ---------------------------------------------------------------------------


class _DisconnectingPoller:
    # Wraps a real poller but nulls the owning UDPSocket's self.poller the first time ipoll()
    # is called - simulates disconnect() firing concurrently on the same instance from another
    # coroutine while ready()'s poll loop is still in flight.
    def __init__(self, owner: "UDPSocket", real: "select.poll") -> None:
        self.owner = owner
        self._real = real
        self.fired = False

    def register(self, *a: object, **k: object) -> None:
        self._real.register(*a, **k)

    def ipoll(self, *a: object, **k: object) -> "Iterator[tuple[Any, ...]]":
        if not self.fired:
            self.fired = True
            self.owner.poller = None
        return self._real.ipoll(*a, **k)


def test_ready_survives_a_concurrent_disconnect_mid_poll_loop() -> None:
    # ready()'s poll loop only checked `self.poller is None` once, before the loop, so a
    # concurrent disconnect() made the next self.poller.ipoll(0) raise AttributeError.

    # Neither real caller does this today (both use one UDPSocket from a single coroutine at a
    # time), but nothing enforced or documented that constraint - so ready() re-checks every
    # iteration and returns False, matching this file's "never raises" contract.
    addr = _make_addr()

    async def scenario() -> bool:
        sock = UDPSocket(addr, mode="server")
        try:
            await sock._connect()
            real_poller = sock.poller
            assert real_poller is not None  # a connected socket always has one
            sock.poller = _DisconnectingPoller(sock, real_poller)  # type: ignore[assignment]
            return await sock.ready(select.POLLIN, timeout_ms=_RECV_TIMEOUT_MS)
        finally:
            await sock.disconnect()

    assert run(scenario()) is False


# ---------------------------------------------------------------------------
# _connect() retry/self-heal
# ---------------------------------------------------------------------------


def _unbindable_addr() -> tuple[str, int]:
    # 10.255.255.254 is never a local interface address in this environment, so bind() there
    # raises OSError(EADDRNOTAVAIL) - a deterministic forced bind() failure. A same-port "blocker"
    # socket would not work: SO_REUSEADDR, set by _connect() itself, lets a second UDP socket bind.
    return ("10.255.255.254", 51999)


def test_connect_self_heals_after_a_failed_bind() -> None:
    # Bug: once self._sock was created, a failed attempt left _connect() a permanent
    # no-op (self._sock stayed non-None) - the object was stuck forever. It must now tear itself
    # down so a later call gets a fresh attempt.
    bad_addr = _unbindable_addr()
    good_addr = _make_addr()

    async def scenario() -> tuple[bool, bool, bool]:
        contender = UDPSocket(bad_addr, mode="server")
        try:
            await contender._connect()  # its one attempt fails against an unbindable address
            first_connected = contender.connected
            first_sock_cleared = contender._sock is None

            contender._addr = good_addr  # simulate the underlying condition clearing
            await contender._connect()  # should self-heal: fresh attempt now succeeds
            second_connected = contender.connected
            return first_connected, first_sock_cleared, second_connected
        finally:
            await contender.disconnect()

    first_connected, first_sock_cleared, second_connected = run(scenario())
    assert first_connected is False
    assert first_sock_cleared is True
    assert second_connected is True


# ---------------------------------------------------------------------------
# disconnect() / object reuse
# ---------------------------------------------------------------------------


def test_disconnect_is_idempotent_and_resets_state() -> None:
    addr = _make_addr()

    async def scenario() -> tuple[bool, bool, bool, bool, bool]:
        sock = UDPSocket(addr, mode="server")
        await sock._connect()
        assert sock.connected
        first_ok = await sock.disconnect()
        sock_cleared, poller_cleared, not_connected = sock._sock is None, sock.poller is None, sock.connected is False
        second_ok = await sock.disconnect()  # must not raise when already disconnected
        return sock_cleared, poller_cleared, not_connected, first_ok, second_ok

    sock_cleared, poller_cleared, not_connected, first_ok, second_ok = run(scenario())
    assert sock_cleared and poller_cleared and not_connected
    # A clean teardown (nothing raised) reports True; an already-disconnected no-op also reports
    # True (there was nothing to fail at) - only a genuine unregister()/close() failure is False.
    assert first_ok is True
    assert second_ok is True


def test_object_is_reusable_after_disconnect() -> None:
    addr = _make_addr()

    async def scenario() -> tuple[bytes | None, bytes | None]:
        server = UDPSocket(addr, mode="server")
        client = UDPSocket(addr, mode="client")
        try:
            await server._connect()
            first_task = asyncio.create_task(server.recvfrom(64))
            await client.write(b"one")
            first, _ = await first_task
            await server.disconnect()

            await server._connect()  # rebind the same object from scratch
            second_task = asyncio.create_task(server.recvfrom(64))
            await client.write(b"two")
            second, _ = await second_task
            return first, second
        finally:
            await client.disconnect()
            await server.disconnect()

    first, second = run(scenario())
    assert first == b"one"
    assert second == b"two"


# ---------------------------------------------------------------------------
# Cancellation must not be swallowed by this file's `except OSError` blocks
# ---------------------------------------------------------------------------


def test_cancellation_propagates_out_of_recvfrom() -> None:
    addr = _make_addr()

    async def scenario() -> bool:
        server = UDPSocket(addr, mode="server")
        try:
            task = asyncio.create_task(server.recvfrom(64))  # nothing ever arrives - waits forever
            await asyncio.sleep(_TASK_PARK_S)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                return True
            else:
                return False  # should never get here
        finally:
            await server.disconnect()

    assert run(scenario())


# ---------------------------------------------------------------------------
# ready()'s poll rates must be milliseconds, not seconds
# ---------------------------------------------------------------------------


def test_ready_sleeps_milliseconds_not_seconds() -> None:
    # Bug: ready() used to call asyncio.sleep() (seconds), not asyncio.sleep_ms(), so a 20 ms rate slept 20
    # real seconds per round. Both rates reach sleep_ms() as whole milliseconds (20 and 100, never 0.02 or
    # 0.1), and a bounded call completes in tens of milliseconds, not multiple real seconds.
    t0 = time.ticks_ms()
    with_deadline = _record_ready_sleeps(_MS_CHECK_TIMEOUT_MS)
    elapsed = time.ticks_diff(time.ticks_ms(), t0)
    without_deadline = _record_ready_sleeps(-1, stop_after=1)
    assert with_deadline and all(isinstance(ms, int) and ms == _src_const("_POLL_WAIT_MS") for ms in with_deadline), with_deadline
    assert without_deadline == [_src_const("_POLL_IDLE_MS")] and isinstance(without_deadline[0], int), without_deadline
    assert elapsed < _MS_CHECK_ELAPSED_MAX_MS  # generously below the 10000ms+ the old seconds-interpretation bug would take


# ---------------------------------------------------------------------------
# _connect()'s own setup code (socket()/setsockopt()/poll()/register()) must not raise
# ---------------------------------------------------------------------------


class _RaisingSocketModule:
    # MicroPython's real `socket` module is a read-only builtin, so this replaces
    # asy_udp_socket's own module-level `socket` name. Mirrors the constants that module
    # references, but socket() always raises - resource exhaustion at the first setup step.
    AF_INET = socket.AF_INET
    SOCK_DGRAM = socket.SOCK_DGRAM
    SOL_SOCKET = socket.SOL_SOCKET
    SO_REUSEADDR = socket.SO_REUSEADDR

    def socket(self, _af: int, _sock_type: int) -> "NoReturn":  # asy_udp_socket.py calls socket() positionally
        raise OSError("simulated resource exhaustion")


def test_connect_setup_failure_self_heals_instead_of_raising() -> None:
    # Bug: socket()/setsockopt()/poll()/register() ran with zero exception handling - violated
    # this file's own "never raises" contract, and would have leaked a half-initialized socket.
    addr = _make_addr()
    sock = UDPSocket(addr, mode="server")
    original_socket = asy_udp_socket.socket
    asy_udp_socket.socket = _RaisingSocketModule()  # type: ignore[assignment]  # deliberate monkeypatch, not a real caller mismatch
    try:
        run(sock._connect())  # must not raise despite socket() failing
    finally:
        asy_udp_socket.socket = original_socket

    assert sock.connected is False
    assert sock._sock is None

    try:
        run(sock._connect())  # the fault is gone now - should self-heal and succeed
        assert sock.connected is True
    finally:
        run(sock.disconnect())


# ---------------------------------------------------------------------------
# ready() must notice POLLERR/POLLHUP, not just its own requested mask
# ---------------------------------------------------------------------------


def test_recvfrom_detects_pollerr_instead_of_waiting_out_the_full_timeout() -> None:
    # Confirmed empirically: a connected UDP client socket with a pending ICMP port-unreachable
    # reports POLLOUT|POLLERR, never POLLIN, and ready(POLLIN) used to check only `event & mask`,
    # waiting out the full timeout for a failure the kernel already knew about.
    addr = _make_addr()  # nobody ever binds/listens on this address

    async def scenario() -> tuple[bytes | None, int]:
        client = UDPSocket(addr, mode="client")
        try:
            sent = await client.write(b"ping")
            assert sent == 4
            await asyncio.sleep(_ICMP_DELIVERY_S)  # let the kernel deliver the ICMP unreachable
            t0 = time.ticks_ms()
            data, _ = await client.recvfrom(64, timeout_ms=_ICMP_RECV_TIMEOUT_MS)  # generously long if the old bug were still present
            return data, time.ticks_diff(time.ticks_ms(), t0)
        finally:
            await client.disconnect()

    data, elapsed = run(scenario())
    assert data is None  # recvfrom() itself still raises OSError, correctly converted to the sentinel
    assert elapsed < _ICMP_ELAPSED_MAX_MS  # detected via POLLERR promptly, not by waiting out the 5000ms timeout


# ---------------------------------------------------------------------------
# Integration-level: real-world call patterns of the upstream callers - an NTP-shaped round trip
# through write_and_recvfrom(), the call asy_dns_client.py's resolver makes, and asy_captive_dns.py's
# CaptiveDNS - plus how a real UDP fault propagates up through each processing path.

# These mirror each caller's documented, stable call shape (mode, buffer sizes, timeout/tries,
# acquire-use-release) rather than importing implementation details - proving the contract is
# robust protects a future refactored caller too, not just today's.
# ---------------------------------------------------------------------------


def test_ntp_client_pattern_end_to_end_success() -> None:
    # An NTP-shaped exchange through write_and_recvfrom(), with disconnect() on the success path
    # AND unconditionally again in finally - proving that double disconnect() is safe in this
    # usage shape, and that a caller's broad except Exception backstop is never needed.
    server_addr = _make_addr()
    ntp_request = b"\x1b" + bytearray(47)
    ntp_reply = b"\x1c" + bytearray(47)  # a realistic 48-byte NTP-shaped reply

    async def responder(peer: _AdversarialPeer) -> None:
        _, from_addr = await peer.recv(1024, timeout_ms=_PEER_RECV_TIMEOUT_MS)
        assert from_addr is not None
        peer.sock.sendto(ntp_reply, from_addr)

    async def scenario() -> tuple[bytes | None, bool]:
        peer = _AdversarialPeer(server_addr)
        exception_hit = False
        cli = None
        msg: bytes | None = None
        try:
            responder_task = asyncio.create_task(responder(peer))
            cli = UDPSocket(server_addr, mode="client")
            msg, add = await cli.write_and_recvfrom(ntp_request, 1024, timeout_ms=_LONG_REPLY_TIMEOUT_MS, tries=1)
            del add
            await cli.disconnect()
            await responder_task
        except Exception:
            cli = msg = None
            exception_hit = True
        finally:
            if cli is not None:
                await cli.disconnect()
            peer.close()
        return msg, exception_hit

    msg, exception_hit = run(scenario())
    assert msg == ntp_reply
    assert exception_hit is False  # asy_udp_socket.py's own contract never needed this backstop


def test_ntp_client_pattern_no_server_reachable() -> None:
    # The same call shape against an address nobody listens on - a real network fault (ICMP
    # port-unreachable, exactly like an offline NTP server) - proving msg ends up None, matching
    # the real "if msg is None: retry" branch downstream, with no broad except needed.
    server_addr = _make_addr()  # nobody ever binds/listens here
    ntp_request = b"\x1b" + bytearray(47)

    async def scenario() -> tuple[bytes | None, bool]:
        exception_hit = False
        cli = None
        msg: bytes | None = None
        try:
            cli = UDPSocket(server_addr, mode="client")
            msg, add = await cli.write_and_recvfrom(ntp_request, 1024, timeout_ms=_UNREACHABLE_TIMEOUT_MS, tries=1)
            del add
            await cli.disconnect()
        except Exception:
            cli = msg = None
            exception_hit = True
        finally:
            if cli is not None:
                await cli.disconnect()
        return msg, exception_hit

    msg, exception_hit = run(scenario())
    assert msg is None
    assert exception_hit is False


def test_ntp_client_pattern_garbage_reply_is_delivered_not_rejected() -> None:
    # Content-agnostic transport, exercised through the same NTP-shaped call: a "server" that
    # replies with garbage (not a valid 48-byte NTP packet at all) must still be delivered
    # faithfully - validating NTP structure is asy_ntp_client.py's own job, not this module's.
    server_addr = _make_addr()
    ntp_request = b"\x1b" + bytearray(47)
    garbage_reply = b"\x00\x01\x02not-an-ntp-packet-at-all" * 3

    async def responder(peer: _AdversarialPeer) -> None:
        _, from_addr = await peer.recv(1024, timeout_ms=_PEER_RECV_TIMEOUT_MS)
        assert from_addr is not None
        peer.sock.sendto(garbage_reply, from_addr)

    async def scenario() -> bytes | None:
        peer = _AdversarialPeer(server_addr)
        cli = UDPSocket(server_addr, mode="client")
        try:
            responder_task = asyncio.create_task(responder(peer))
            msg, _ = await cli.write_and_recvfrom(ntp_request, 1024, timeout_ms=_LONG_REPLY_TIMEOUT_MS, tries=1)
            await responder_task
            return msg
        finally:
            await cli.disconnect()
            peer.close()

    assert run(scenario()) == garbage_reply


def test_dns_server_pattern_bound_to_all_interfaces_end_to_end() -> None:
    # Mirrors asy_captive_dns.py's exact call shape: a server-mode socket bound to ("0.0.0.0", port),
    # recvfrom(DNS_UDP_MAX), conditional sendto(response, addr) - including the real bind-any-interface
    # then receive-via-127.0.0.1 path that every other test in this file skips.
    port = _make_port()
    server_addr = ("0.0.0.0", port)
    client_addr = _make_addr()
    query = b"\x00\x01fake-dns-query"
    response = b"\x00\x01fake-dns-response"

    async def scenario() -> tuple[bytes | None, tuple[str, int] | None, bytes]:
        server = UDPSocket(server_addr, mode="server")
        client = _AdversarialPeer(client_addr)
        try:
            await server._connect()
            client.send(query, ("127.0.0.1", port))
            data, addr = await server.recvfrom(DNS_UDP_MAX, timeout_ms=_LONG_REPLY_TIMEOUT_MS)
            if data is not None and addr is not None:  # asy_captive_dns.py's exact guard
                await server.sendto(response, addr)
            reply, _ = await client.recv(4096, timeout_ms=_LONG_REPLY_TIMEOUT_MS)
            return data, addr, reply
        finally:
            client.close()
            await server.disconnect()

    data, addr, reply = run(scenario())
    assert data == query
    assert addr == client_addr  # the sender, as the (host, port) tuple every received address is
    assert reply == response


def test_dns_server_pattern_recvfrom_never_returns_a_mismatched_pair() -> None:
    # asy_captive_dns.py's guard is `if data is not None and addr is not None:`, implicitly assuming
    # the two are always both set or both None. This confirms that holds: recvfrom() never returns
    # (bytes, None) or (None, tuple) in either the timeout or the success path.
    addr = _make_addr()
    peer_addr = _make_addr()

    async def scenario() -> tuple[tuple[bytes | None, tuple[str, int] | None], tuple[bytes | None, tuple[str, int] | None]]:
        server = UDPSocket(addr, mode="server")
        peer = _AdversarialPeer(peer_addr)
        try:
            await server._connect()
            timeout_result = await server.recvfrom(64, timeout_ms=_NO_SENDER_TIMEOUT_MS)  # nobody sends - timeout path
            peer.send(b"real query", addr)
            success_result = await server.recvfrom(64, timeout_ms=_REPLY_TIMEOUT_MS)  # success path
            return timeout_result, success_result
        finally:
            peer.close()
            await server.disconnect()

    timeout_result, success_result = run(scenario())
    assert timeout_result == (None, None)
    assert (success_result[0] is None) == (success_result[1] is None)  # always paired, never mismatched
    assert success_result[0] == b"real query"


def test_dns_server_pattern_sendto_failure_does_not_corrupt_subsequent_serving() -> None:
    # asy_captive_dns.py checks sendto()'s result and persists a failed reply as DNS_REPLY_DROPPED, one
    # level above this module.

    # What this module is responsible for is that such a failure cannot corrupt the server socket
    # for the next, unrelated query in the same long-lived CaptiveDNS loop.
    addr = _make_addr()
    unreachable_client_addr = ("10.255.255.254", 12345)  # never routable in this environment
    real_peer_addr = _make_addr()

    async def scenario() -> bytes | None:
        server = UDPSocket(addr, mode="server")
        peer = _AdversarialPeer(real_peer_addr)
        try:
            await server._connect()
            await server.sendto(b"reply to nobody", unreachable_client_addr)  # never raises either way

            peer.send(b"next real query", addr)
            _data, from_addr = await server.recvfrom(64, timeout_ms=_REPLY_TIMEOUT_MS)
            assert from_addr is not None
            await server.sendto(b"real reply", from_addr)
            reply, _ = await peer.recv(64, timeout_ms=_REPLY_TIMEOUT_MS)
            return reply
        finally:
            peer.close()
            await server.disconnect()

    assert run(scenario()) == b"real reply"  # the server socket kept working for the next query


# ---------------------------------------------------------------------------
# Fifth pass: __init__'s validation only runs at construction, so a direct post-construction
# mutation of _addr can still reach the shapes it was meant to prevent. Closed by
# widening every touching except clause to catch TypeError, not by re-validating on each access.
# ---------------------------------------------------------------------------


def test_connect_self_heals_when_addr_mutated_to_a_malformed_value() -> None:
    # Mutating ._addr directly after construction bypasses __init__'s validation and used to
    # raise an uncaught TypeError from sock.connect()/bind(), reintroducing the very bug that
    # eager validation closed. _connect()'s connect()/bind() try now also catches TypeError.
    addr = _make_addr()
    sock = UDPSocket(addr, mode="client")
    sock._addr = (12345, 80)  # type: ignore[assignment]  # malformed - host is an int, not a str
    try:
        run(sock._connect())  # must not raise
        assert sock.connected is False
    finally:
        run(sock.disconnect())


def test_connect_treats_a_mutated_mode_as_server_like_without_crashing() -> None:
    # Not a bug: _connect()'s mode branch is a plain if/else since __init__ guarantees only
    # "client"/"server" reach it. A mutated ._mode bypasses that, but the binary shape falls
    # through to bind() rather than hanging the way the old three-way branch did.
    addr = _make_addr()
    sock = UDPSocket(addr, mode="client")
    sock._mode = "bogus"  # type: ignore[assignment]
    try:
        run(sock._connect())
        assert sock.connected is True  # treated as bind(), which succeeds on a fresh address
    finally:
        run(sock.disconnect())


def test_sendto_returns_none_sentinel_for_a_malformed_explicit_addr() -> None:
    # Same class of bug as ._addr mutation above, but for sendto()'s own per-call addr parameter -
    # confirmed directly this used to raise an uncaught TypeError too.
    addr = _make_addr()

    async def scenario() -> int | None:
        server = UDPSocket(addr, mode="server")
        try:
            await server._connect()
            return await server.sendto(b"x", (12345, 80))  # type: ignore[arg-type]
        finally:
            await server.disconnect()

    assert run(scenario()) is None


def test_recvfrom_returns_none_sentinel_for_a_malformed_buf_with_real_pending_data() -> None:
    # Confirmed directly: a wrong-typed buf (e.g. a str) only raises once a real datagram is
    # actually pending and ready() lets the real recvfrom() call through - a timeout-path test
    # (nothing ever sent) would never actually reach the buggy call at all.
    addr = _make_addr()
    peer_addr = _make_addr()

    async def scenario() -> tuple[bytes | None, tuple[str, int] | None]:
        server = UDPSocket(addr, mode="server")
        peer = _AdversarialPeer(peer_addr)
        try:
            await server._connect()
            peer.send(b"real data", addr)
            await asyncio.sleep(_KERNEL_QUEUE_S)
            return await server.recvfrom("not an int", timeout_ms=_RECV_TIMEOUT_MS)  # type: ignore[arg-type]
        finally:
            peer.close()
            await server.disconnect()

    assert run(scenario()) == (None, None)


# ---------------------------------------------------------------------------
# Fifth pass: _connect()/disconnect() concurrency - a per-instance asyncio.Lock serializes them
# against each other, so a concurrent disconnect() can't crash an in-flight retry, and a
# concurrent caller joins an in-flight connect instead of getting a premature "not ready".
# ---------------------------------------------------------------------------


def test_disconnect_no_longer_crashes_a_concurrent_in_flight_connect_retry() -> None:
    # Before the connect-lock, a disconnect() concurrent with another coroutine's in-flight
    # _connect() retry could null self._sock/self.poller out from under it. disconnect() now takes
    # the same lock, waiting for the attempt (bounded by one backoff) instead.
    bad_addr = _unbindable_addr()

    async def scenario() -> tuple[bool, int]:
        sock = UDPSocket(bad_addr, mode="server")
        try:
            t0 = time.ticks_ms()
            connect_task = asyncio.create_task(sock._connect())
            await asyncio.sleep(_FIRST_ATTEMPT_S)  # let it fail its first attempt and start backing off
            await sock.disconnect()  # must not raise, and must not crash connect_task either
            await connect_task
            elapsed = time.ticks_diff(time.ticks_ms(), t0)
            return sock.connected, elapsed
        finally:
            await sock.disconnect()

    connected, elapsed = run(scenario())
    assert connected is False  # bad_addr never becomes bindable
    # disconnect() waited out the one backoff the failed attempt holds the lock for
    assert elapsed >= int(_src_const("_RETRY_BACKOFF_S") * 1000) - int(_FIRST_ATTEMPT_S * 1000), elapsed
    assert elapsed < _RETRY_CYCLE_MAX_MS  # ...but didn't hang forever either


def test_concurrent_caller_joins_an_in_flight_connect_instead_of_a_premature_none() -> None:
    # A coroutine calling a public method while another's _connect() was mid-retry used to get a
    # spurious None immediately instead of waiting. B's sendto() must block until A's attempt
    # resolves, then genuinely succeed on the fresh attempt it makes once A's has failed.
    bad_addr = _unbindable_addr()
    good_addr = _make_addr()

    async def scenario() -> tuple[bool, int | None]:
        sock = UDPSocket(bad_addr, mode="server")
        try:
            a_task = asyncio.create_task(sock._connect())
            await asyncio.sleep(_FIRST_ATTEMPT_S)  # A has failed its first attempt, is backing off
            sock._addr = good_addr  # the fault clears while A still holds the lock
            b_task = asyncio.create_task(sock.sendto(b"x", good_addr))
            await a_task
            b_result = await b_task
            return sock.connected, b_result
        finally:
            await sock.disconnect()

    connected, b_result = run(scenario())
    assert connected is True
    assert b_result == 1  # len(b"x") - B's call succeeded once A's retry succeeded, not None


def test_cancelling_a_task_that_holds_the_connect_lock_releases_it() -> None:
    # Locks plus cancellation are a classic deadlock source, and this file gained its first lock:
    # `async with`'s __aexit__ must still run and release when the holding task is cancelled
    # mid-retry, or every future caller on this instance hangs forever.
    bad_addr = _unbindable_addr()

    async def scenario() -> tuple[bool, bool]:
        sock = UDPSocket(bad_addr, mode="server")
        a_task = asyncio.create_task(sock._connect())
        await asyncio.sleep(_FIRST_ATTEMPT_S)  # A has failed once, is inside its backoff sleep, holding the lock
        a_task.cancel()
        cancelled_cleanly = False
        try:
            await a_task
        except asyncio.CancelledError:
            cancelled_cleanly = True

        try:
            await asyncio.wait_for(sock.disconnect(), _DISCONNECT_BOUND_S)
            lock_was_released = True
        except asyncio.TimeoutError:
            lock_was_released = False
        return cancelled_cleanly, lock_was_released

    cancelled_cleanly, lock_was_released = run(scenario())
    assert cancelled_cleanly
    assert lock_was_released


def test_cancelling_a_task_waiting_on_the_connect_lock_leaves_it_healthy() -> None:
    # The other half of the same concern: B blocked *waiting* to acquire the lock (not holding
    # it) gets cancelled - confirms this doesn't corrupt the lock's internal waiter state, so a
    # later caller can still acquire it once the current holder finishes.
    bad_addr = _unbindable_addr()

    async def scenario() -> tuple[bool, bool]:
        sock = UDPSocket(bad_addr, mode="server")
        a_task = asyncio.create_task(sock._connect())
        await asyncio.sleep(_FIRST_ATTEMPT_S)
        b_task = asyncio.create_task(sock.disconnect())  # blocks waiting for the lock A holds
        await asyncio.sleep(_TASK_PARK_S)  # let B actually start waiting
        b_task.cancel()
        b_cancelled_cleanly = False
        try:
            await b_task
        except asyncio.CancelledError:
            b_cancelled_cleanly = True

        try:
            await asyncio.wait_for(a_task, _CONNECT_BOUND_S)
            a_completed = True
        except asyncio.TimeoutError:
            a_completed = False
        try:
            await asyncio.wait_for(sock.disconnect(), _DISCONNECT_BOUND_S)
            lock_still_healthy = True
        except asyncio.TimeoutError:
            lock_still_healthy = False
        return b_cancelled_cleanly and a_completed, lock_still_healthy

    a_side_ok, lock_still_healthy = run(scenario())
    assert a_side_ok
    assert lock_still_healthy


# ---------------------------------------------------------------------------
# Fifth pass: already-correct boundary/misuse behaviors, confirmed directly, previously untested
# ---------------------------------------------------------------------------


def test_write_on_an_unconnected_server_mode_socket_returns_none_sentinel() -> None:
    # write() semantically requires a connected socket, so calling it on a bound-but-unconnected
    # server-mode socket is a caller misuse this file deliberately does not guard structurally
    # (BACKLOG.md). The real ENOTCONN-style OSError is caught like any other socket failure.
    addr = _make_addr()

    async def scenario() -> int | None:
        server = UDPSocket(addr, mode="server")
        try:
            await server._connect()
            assert server.connected
            return await server.write(b"x")
        finally:
            await server.disconnect()

    assert run(scenario()) is None


def test_sendto_empty_bytes_succeeds() -> None:
    # UDP allows a zero-length outgoing datagram, symmetric to the zero-length *receive* case
    # already covered - confirmed directly this just works, no exception.
    addr = _make_addr()

    async def scenario() -> int | None:
        server = UDPSocket(addr, mode="server")
        try:
            await server._connect()
            return await server.sendto(b"", _make_addr())
        finally:
            await server.disconnect()

    assert run(scenario()) == 0


def test_recvfrom_buf_zero_returns_empty_bytes_not_the_timeout_sentinel() -> None:
    # An extreme instance of the documented truncation contract, not a new behavior: buf=0
    # against a genuinely pending datagram returns (b"", addr), not the (None, None) timeout
    # sentinel - distinguishing "nothing because buf=0" from "nothing because nothing arrived".
    addr = _make_addr()
    peer_addr = _make_addr()

    async def scenario() -> bytes | None:
        server = UDPSocket(addr, mode="server")
        peer = _AdversarialPeer(peer_addr)
        try:
            await server._connect()
            peer.send(b"real data", addr)
            await asyncio.sleep(_KERNEL_QUEUE_S)
            data, _ = await server.recvfrom(0, timeout_ms=_RECV_TIMEOUT_MS)
            return data
        finally:
            peer.close()
            await server.disconnect()

    assert run(scenario()) == b""


def test_disconnect_on_a_fresh_never_connected_object_is_a_clean_no_op() -> None:
    addr = _make_addr()

    async def scenario() -> tuple[bool, bool]:
        sock = UDPSocket(addr, mode="client")
        await sock.disconnect()  # _connect() was never called - must not raise
        return sock._sock is None, sock.connected is False

    sock_is_none, not_connected = run(scenario())
    assert sock_is_none and not_connected


def test_write_and_recvfrom_tries_zero_returns_immediately() -> None:
    addr = _make_addr()

    async def scenario() -> tuple[bytes | None, tuple[str, int] | None]:
        sock = UDPSocket(addr, mode="client")
        try:
            return await sock.write_and_recvfrom(b"x", 64, timeout_ms=50, tries=0)
        finally:
            await sock.disconnect()

    assert run(scenario()) == (None, None)


# ---------------------------------------------------------------------------
# Sixth pass: ready()'s mask/timeout_ms and write_and_recvfrom()'s tries were never
# guarded against a malformed caller-supplied value, and raised an uncaught TypeError past every
# except clause - the raise is inside ready(), which callers await before their own try begins.
# ---------------------------------------------------------------------------


def test_ready_returns_false_sentinel_for_a_malformed_timeout_ms() -> None:
    # `if (timeout_ms > 0) and ...` inside ready()'s poll loop raised an uncaught TypeError for
    # timeout_ms=None. Only reachable once the first ipoll(0) finds nothing matching mask (a
    # fresh server socket polled for POLLIN), since a matching first iteration returns early.
    addr = _make_addr()

    async def scenario() -> bool:
        sock = UDPSocket(addr, mode="server")
        try:
            await sock._connect()
            return await sock.ready(select.POLLIN, timeout_ms=None)  # type: ignore[arg-type]
        finally:
            await sock.disconnect()

    assert run(scenario()) is False


def test_ready_returns_false_sentinel_for_a_malformed_mask() -> None:
    # `event & (mask | select.POLLERR | select.POLLHUP)` raised an uncaught TypeError for
    # mask=None. Uses a fresh server socket, immediately POLLOUT-ready so ipoll(0)'s first result
    # is non-empty, to reach that expression on the first iteration without a pending datagram.
    addr = _make_addr()

    async def scenario() -> bool:
        sock = UDPSocket(addr, mode="server")
        try:
            await sock._connect()
            return await sock.ready(None, timeout_ms=200)  # type: ignore[arg-type]
        finally:
            await sock.disconnect()

    assert run(scenario()) is False


def test_ready_cancellation_still_propagates_through_the_new_try_except() -> None:
    # The fix above wraps ready()'s whole per-iteration loop body, including its
    # asyncio.sleep_ms() await point, in try/except (OSError, MemoryError, TypeError) - it must
    # not start swallowing asyncio.CancelledError, a BaseException subclass not in that tuple.
    addr = _make_addr()

    async def scenario() -> bool:
        sock = UDPSocket(addr, mode="server")
        try:
            await sock._connect()
            task = asyncio.create_task(sock.ready(select.POLLIN, timeout_ms=-1))  # waits forever
            await asyncio.sleep(_ENTER_SLEEP_S)  # let it enter the sleep_ms() inside the new try block
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                return True
            else:
                return False  # should never get here
        finally:
            await sock.disconnect()

    assert run(scenario())


def test_recvfrom_propagates_readys_false_sentinel_for_a_malformed_timeout_ms() -> None:
    # The bug above was not only reachable through ready() directly: sendto()/write()/recvfrom()
    # each await self.ready(...) before their own try block starts, so the crash bypassed their
    # except clauses. Confirms the real entry point callers use, recvfrom(), is fixed too.

    # Nothing must be sent here: a pending datagram would make the first ipoll(0) match POLLIN and
    # return before timeout_ms is ever compared, so only the still-waiting path reaches it.
    addr = _make_addr()

    async def scenario() -> tuple[bytes | None, tuple[str, int] | None]:
        server = UDPSocket(addr, mode="server")
        try:
            await server._connect()
            return await server.recvfrom(64, timeout_ms=None)  # type: ignore[arg-type]
        finally:
            await server.disconnect()

    assert run(scenario()) == (None, None)


def test_write_and_recvfrom_returns_none_sentinel_for_a_malformed_tries() -> None:
    # Bug: `for _ in range(tries):` raised an uncaught TypeError for e.g. tries=None or tries="3" -
    # confirmed directly, and write_and_recvfrom() had no try/except of its own to catch it.
    addr = _make_addr()

    async def scenario(bad_tries: "Any") -> tuple[bytes | None, tuple[str, int] | None]:
        sock = UDPSocket(addr, mode="client")
        try:
            return await sock.write_and_recvfrom(b"x", 64, timeout_ms=50, tries=bad_tries)
        finally:
            await sock.disconnect()

    for bad_tries in (None, "3", [1]):
        assert run(scenario(bad_tries)) == (None, None)



# ---------------------------------------------------------------------------
# redirect_udp_port(): the shared stand-in for a privileged port (DNS 53, NTP 123) in other files' tests
# ---------------------------------------------------------------------------


def test_the_port_redirect_maps_only_its_port_and_counts_constructions() -> None:
    original = asy_udp_socket.UDPSocket
    with redirect_udp_port(asy_udp_socket, 53, 23053) as redirect:
        redirected = asy_udp_socket.UDPSocket
        assert redirected is not original
        mapped = redirected(("127.0.0.1", 53), mode="client")
        other = redirected(("127.0.0.1", 54))
        try:
            redirected(b"\x00" * 16)  # type: ignore[arg-type]
            raise AssertionError("a sockaddr passed the redirect")
        except TypeError:
            pass  # reached the real constructor as given
        assert isinstance(mapped, UDPSocket)
        assert (mapped._addr, mapped._mode) == (("127.0.0.1", 23053), "client")
        assert other._addr == ("127.0.0.1", 54)
        assert redirect.constructed == 3
    assert asy_udp_socket.UDPSocket is original


def test_the_port_redirect_restores_the_module_after_an_exception() -> None:
    original = asy_udp_socket.UDPSocket
    try:
        with redirect_udp_port(asy_udp_socket, 123, 23123):
            raise ValueError("raised inside the block")
    except ValueError:
        pass
    assert asy_udp_socket.UDPSocket is original


def test_a_redirected_socket_reaches_the_fake_port() -> None:
    server_addr = _make_addr()

    async def scenario() -> "tuple[int | None, bytes | None]":
        server = UDPSocket(server_addr, mode="server")
        with redirect_udp_port(asy_udp_socket, 53, server_addr[1]):
            client = asy_udp_socket.UDPSocket(("127.0.0.1", 53), mode="client")
        try:
            await server._connect()
            sent = await client.write(b"query")
            data, _ = await server.recvfrom(64, timeout_ms=_REPLY_TIMEOUT_MS)
            return sent, data
        finally:
            await client.disconnect()
            await server.disconnect()

    assert run(scenario()) == (5, b"query")


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
