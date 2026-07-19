import asyncio
import select
import socket
import time

import asy_udp_socket
from asy_udp_socket import AsyUDPSocket

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing isn't available on the real MicroPython test interpreter
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Coroutine
    from typing import Any, TypeVar

    T = TypeVar("T")


def run(coro: "Coroutine[Any, Any, T]") -> "T":  # drives a coroutine to completion for these sync test_* functions
    return asyncio.run(coro)


_HOST = "127.0.0.1"
_next_port = 51000


def make_addr() -> tuple[str, int]:  # a fresh loopback port per call, so tests never contend for the same address
    global _next_port
    _next_port += 1
    # The MicroPython Unix port's "standard" build (unlike the real rp2 target - see
    # typings/socket.pyi's _Address, which asy_udp_socket.py's addr: tuple[str, int] contract
    # already matches) rejects a plain (host, port) tuple in bind()/connect()/sendto() with
    # "TypeError: object with buffer protocol required" (a known, long-standing Unix-port-only
    # quirk, micropython/micropython#6924). getaddrinfo()'s resolved object is required instead -
    # on this port that's actually an opaque sockaddr bytearray, not a real tuple[str, int], but
    # AsyUDPSocket only ever passes addr through untouched, so it's safe to hand it through here
    # despite the mismatched static type (the rp2 stub types getaddrinfo()'s result as a tuple,
    # matching what the real target actually returns).
    return socket.getaddrinfo(_HOST, _next_port)[0][-1]  # type: ignore[return-value]


def make_port() -> int:  # a fresh port number only, for tests that build their own addr tuples
    global _next_port
    _next_port += 1
    return _next_port


def resolve_addr(host: str, port: int) -> tuple[str, int]:
    # Same Unix-port-only workaround as make_addr() above, for a test-chosen (host, port) - e.g.
    # "0.0.0.0", or a deliberately unreachable address - rather than a fresh loopback port.
    return socket.getaddrinfo(host, port)[0][-1]  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# __init__ configuration: every valid combination, single and multiple invalid parameter
# recombinations. These only construct the object - no real socket call happens until _connect()
# runs, so a plain (unresolved) tuple is safe here even though it can't be handed to this
# project's own MicroPython Unix-port build's connect()/bind()/sendto() (see make_addr() above).
# ---------------------------------------------------------------------------


def test_init_accepts_every_valid_mode_and_conn_tries_combination() -> None:
    for mode in ("client", "server"):
        for conn_tries in (1, 3, 0, -1):  # 0/negative are valid, degenerate "never even try" values
            sock = AsyUDPSocket(("127.0.0.1", 12345), mode=mode, conn_tries=conn_tries)
            assert sock._mode == mode
            assert sock._conn_tries == conn_tries
            assert sock.connected is False
            assert sock.sock is None


def test_init_accepts_a_pre_resolved_bytes_like_addr() -> None:
    # Some platforms' socket.getaddrinfo() returns an opaque sockaddr (bytes/bytearray), not a
    # tuple - confirmed directly on this project's own MicroPython Unix-port test build. This
    # file only ever passes addr through untouched, so construction must accept this shape too,
    # not just the documented tuple[str, int] shape real hardware always uses.
    resolved = socket.getaddrinfo("127.0.0.1", 51500)[0][-1]
    sock = AsyUDPSocket(resolved, mode="server")  # type: ignore[arg-type]
    assert sock._addr == resolved


def test_init_rejects_invalid_mode() -> None:
    # Bug: an invalid mode used to busy-loop forever inside _connect() with zero await points -
    # a genuine unrecoverable lockup (confirmed directly: the process had to be hard-killed even
    # under asyncio.wait_for(), since the offending coroutine never yields control back to the
    # scheduler for the timeout to fire). Fixed: validated eagerly here instead, so the bad value
    # is rejected before _connect() is ever reachable.
    for bad_mode in ("bogus", "", "CLIENT", "client ", None, 123):
        try:
            AsyUDPSocket(("127.0.0.1", 12345), mode=bad_mode)  # type: ignore[arg-type]
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
            AsyUDPSocket(bad_addr, mode="client")  # type: ignore[arg-type]
            raise AssertionError(f"expected TypeError for addr={bad_addr!r}")
        except TypeError:
            pass


def test_init_rejects_addr_of_the_wrong_type_entirely() -> None:
    for bad_addr in (None, 12345, "127.0.0.1", ["127.0.0.1", 80], 3.14):
        try:
            AsyUDPSocket(bad_addr, mode="client")  # type: ignore[arg-type]
            raise AssertionError(f"expected TypeError for addr={bad_addr!r}")
        except TypeError:
            pass


def test_init_rejects_non_int_conn_tries() -> None:
    for bad_conn_tries in (None, "3", 1.5, [1]):
        try:
            AsyUDPSocket(("127.0.0.1", 12345), mode="client", conn_tries=bad_conn_tries)  # type: ignore[arg-type]
            raise AssertionError(f"expected TypeError for conn_tries={bad_conn_tries!r}")
        except TypeError:
            pass


def test_init_rejects_multiple_invalid_parameters_at_once() -> None:
    # Multiple invalid parameters together must still fail cleanly - not silently succeed, not
    # crash with something other than ValueError/TypeError.
    try:
        AsyUDPSocket(("bad", "addr", "shape"), mode="bogus", conn_tries=None)  # type: ignore[arg-type]
        raise AssertionError("expected an exception for all-invalid parameters")
    except (ValueError, TypeError):
        pass

    try:
        AsyUDPSocket(12345, mode="client", conn_tries="nope")  # type: ignore[arg-type]
        raise AssertionError("expected an exception for addr+conn_tries both invalid")
    except (ValueError, TypeError):
        pass

    try:
        AsyUDPSocket(None, mode=42, conn_tries=1.5)  # type: ignore[arg-type]
        raise AssertionError("expected an exception for addr+mode+conn_tries all invalid")
    except (ValueError, TypeError):
        pass


# ---------------------------------------------------------------------------
# Lazy connect + basic client/server round trip
# ---------------------------------------------------------------------------


def test_fresh_client_and_server_round_trip() -> None:
    # Every I/O method must call ready() (which lazily binds/connects via _connect()) before ever
    # touching self.sock - a fresh object must actually send/receive, not return None forever.
    addr = make_addr()

    async def scenario() -> tuple[int | None, bytes | None, bytes | None]:
        server = AsyUDPSocket(addr, mode="server")
        client = AsyUDPSocket(addr, mode="client")
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
    addr = make_addr()

    async def scenario() -> int | None:
        server = AsyUDPSocket(addr, mode="server")
        try:
            await server._connect()
            return await server.sendto(b"hello", addr)  # a bound UDP socket may send to itself
        finally:
            await server.disconnect()

    assert run(scenario()) == 5


def test_recvfrom_returns_none_sentinel_on_timeout() -> None:
    addr = make_addr()

    async def scenario() -> tuple[bytes | None, tuple[str, int] | None]:
        server = AsyUDPSocket(addr, mode="server")
        try:
            return await server.recvfrom(64, timeout_ms=50)
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
    addr = make_addr()

    async def scenario() -> bytes | None:
        server = AsyUDPSocket(addr, mode="server")
        client = AsyUDPSocket(addr, mode="client")
        try:
            await server._connect()

            async def drop_first_then_reply() -> None:
                await server.recvfrom(64)  # dropped - no reply sent
                _, from_addr = await server.recvfrom(64)
                if from_addr is not None:
                    await server.sendto(b"pong", from_addr)

            responder = asyncio.create_task(drop_first_then_reply())
            data, _ = await client.write_and_recvfrom(b"ping", 64, timeout_ms=200, tries=3)
            await responder
            return data
        finally:
            await client.disconnect()
            await server.disconnect()

    assert run(scenario()) == b"pong"


def test_write_and_recvfrom_exhausts_tries_and_returns_none_sentinel() -> None:
    addr = make_addr()  # nobody listens on this address at all

    async def scenario() -> tuple[bytes | None, tuple[str, int] | None]:
        client = AsyUDPSocket(addr, mode="client")
        try:
            return await client.write_and_recvfrom(b"ping", 64, timeout_ms=30, tries=2)
        finally:
            await client.disconnect()

    data, from_addr = run(scenario())
    assert data is None
    assert from_addr is None


# ---------------------------------------------------------------------------
# _connect() retry/self-heal
# ---------------------------------------------------------------------------


class AdversarialPeer:
    # A genuine, independent UDP endpoint - a real socket.socket(), never an AsyUDPSocket - used
    # to drive real-world edge-case traffic (oversized/zero-length/delayed/burst/off-path
    # datagrams) at an AsyUDPSocket under test over actual loopback packets, not mocks.
    def __init__(self, addr: tuple[str, int]) -> None:
        self.addr = addr
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(addr)
        self.sock.setblocking(False)

    async def send_after(self, target: tuple[str, int], data: bytes, delay_ms: int = 0) -> None:
        if delay_ms:
            await asyncio.sleep_ms(delay_ms)
        self.sock.sendto(data, target)

    async def recv(self, bufsize: int, timeout_ms: int = 1000) -> tuple[bytes, tuple[str, int]]:
        poller = select.poll()
        poller.register(self.sock, select.POLLIN)
        t0 = time.ticks_ms()
        while True:
            if poller.ipoll(0):
                return self.sock.recvfrom(bufsize)
            if time.ticks_diff(time.ticks_ms(), t0) > timeout_ms:
                raise OSError("AdversarialPeer.recv() timed out")
            await asyncio.sleep_ms(5)

    def close(self) -> None:
        self.sock.close()


# ---------------------------------------------------------------------------
# Real-world UDP edge cases: truncation, zero-length datagrams, oversized sends, kernel-level
# source filtering, burst ordering, and realistically delayed replies - against a genuine
# independent peer, not just "nobody ever responds".
# ---------------------------------------------------------------------------


def test_recvfrom_silently_truncates_an_oversized_datagram() -> None:
    # POSIX UDP behavior, confirmed directly against this project's MicroPython Unix-port build:
    # a datagram larger than the recv buffer is truncated to buf bytes with no error and no
    # signal that truncation happened (MSG_TRUNC/recvmsg() aren't exposed by MicroPython's socket
    # module) - this module can't detect or prevent it. Documented in the module docstring, not
    # "fixed" - this proves the actual (not assumed) contract callers must design around.
    addr = make_addr()
    peer_addr = make_addr()
    oversized = b"X" * 500

    async def scenario() -> bytes | None:
        server = AsyUDPSocket(addr, mode="server")
        peer = AdversarialPeer(peer_addr)
        try:
            await server._connect()
            peer.sock.sendto(oversized, addr)
            data, _ = await server.recvfrom(10, timeout_ms=500)
            return data
        finally:
            peer.close()
            await server.disconnect()

    assert run(scenario()) == b"X" * 10  # truncated, not the full 500 bytes, no exception


def test_recvfrom_treats_a_zero_length_datagram_as_a_real_reply_not_a_timeout() -> None:
    # UDP explicitly allows zero-length payloads (RFC 768). recvfrom() must return (b"", addr) -
    # distinguishable from the (None, None) timeout/error sentinel, since `data is not None` is
    # exactly what write_and_recvfrom() checks to decide a reply arrived.
    addr = make_addr()
    peer_addr = make_addr()

    async def scenario() -> bytes | None:
        server = AsyUDPSocket(addr, mode="server")
        peer = AdversarialPeer(peer_addr)
        try:
            await server._connect()
            peer.sock.sendto(b"", addr)
            data, _ = await server.recvfrom(64, timeout_ms=500)
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
    addr = make_addr()
    huge = b"X" * 70000

    async def scenario() -> int | None:
        client = AsyUDPSocket(addr, mode="client")
        try:
            return await client.sendto(huge, addr)
        finally:
            await client.disconnect()

    assert run(scenario()) is None


def test_arbitrary_binary_content_round_trips_untouched() -> None:
    # This module is a content-agnostic transport - a datagram with invalid/non-UTF8 bytes, bogus
    # "header" values, etc. must still be delivered byte-for-byte. Validating payload structure
    # (NTP header, DNS query) is the caller's job, not this module's.
    addr = make_addr()
    garbage = bytes(range(256)) + b"\xff\xfe\x00\x00" + bytes([0xDE, 0xAD, 0xBE, 0xEF]) * 10

    async def scenario() -> bytes | None:
        server = AsyUDPSocket(addr, mode="server")
        client = AsyUDPSocket(addr, mode="client")
        try:
            await server._connect()
            task = asyncio.create_task(server.recvfrom(1024))
            await client.write(garbage)
            data, _ = await task
            return data  # type: ignore[no-any-return]  # asyncio.Task's stub loses recvfrom()'s precise return type
        finally:
            await client.disconnect()
            await server.disconnect()

    assert run(scenario()) == garbage


def test_client_mode_filters_datagrams_from_unexpected_sources() -> None:
    # connect() on the client socket isn't just a convenience - the kernel refuses to deliver
    # datagrams from any address other than the connected peer. Prove this directly with a
    # genuine third, independent UDP endpoint acting as an off-path/spoofed sender: it must never
    # be seen by the client, even though it targets the exact same port.
    peer_addr = make_addr()
    attacker_addr = make_addr()

    async def scenario() -> tuple[bytes | None, bytes | None]:
        peer = AdversarialPeer(peer_addr)
        attacker = AdversarialPeer(attacker_addr)
        client = AsyUDPSocket(peer_addr, mode="client")
        try:
            await client._connect()
            await client.write(b"hello")  # lets peer discover the client's real ephemeral address
            _, client_addr = await peer.recv(64)
            assert client_addr is not None

            attacker.sock.sendto(b"spoofed", client_addr)
            spoofed_result, _ = await client.recvfrom(64, timeout_ms=150)

            peer.sock.sendto(b"legit", client_addr)
            legit_result, _ = await client.recvfrom(64, timeout_ms=500)
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
    addr = make_addr()
    peer_addr = make_addr()

    async def scenario() -> list[bytes | None]:
        server = AsyUDPSocket(addr, mode="server")
        peer = AdversarialPeer(peer_addr)
        try:
            await server._connect()
            for i in range(5):
                peer.sock.sendto(f"pkt-{i}".encode(), addr)
            await asyncio.sleep(0.05)  # let the kernel queue all 5 before draining starts
            results = []
            for _ in range(5):
                data, _ = await server.recvfrom(64, timeout_ms=200)
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
    peer_addr = make_addr()

    async def scenario() -> tuple[bytes | None, bytes | None]:
        client = AsyUDPSocket(peer_addr, mode="client")
        peer = AdversarialPeer(peer_addr)
        try:
            await client._connect()
            await client.write(b"hello")  # lets peer discover the client's real ephemeral address
            _, client_addr = await peer.recv(64)
            assert client_addr is not None

            asyncio.create_task(peer.send_after(client_addr, b"in-time", delay_ms=40))
            in_time, _ = await client.recvfrom(64, timeout_ms=300)

            too_late_sender = asyncio.create_task(peer.send_after(client_addr, b"too-late", delay_ms=300))
            too_late, _ = await client.recvfrom(64, timeout_ms=100)
            await too_late_sender  # let the delayed send actually happen before teardown
            return in_time, too_late
        finally:
            peer.close()
            await client.disconnect()

    in_time, too_late = run(scenario())
    assert in_time == b"in-time"
    assert too_late is None


# ---------------------------------------------------------------------------
# ready()'s default wait_time_ms must not busy-spin
# ---------------------------------------------------------------------------


class _RecordingAsyncio:
    # asyncio is a read-only builtin/frozen module on MicroPython (same reason
    # _RaisingSocketModule below replaces asy_udp_socket's own module-level `socket` name instead
    # of monkeypatching the real module) - wraps the real module, recording every sleep_ms()
    # duration while still actually sleeping, so ready()'s own timeout/loop logic keeps working.
    def __init__(self, real: "Any") -> None:
        self._real = real
        self.sleep_ms_calls: list[int] = []

    def sleep_ms(self, ms: int) -> "Any":
        self.sleep_ms_calls.append(ms)
        return self._real.sleep_ms(ms)

    def __getattr__(self, name: str) -> "Any":
        return getattr(self._real, name)


def test_ready_default_wait_time_ms_does_not_busy_spin() -> None:
    # Bug: wait_time_ms defaulted to 0 - confirmed directly this busy-polls ipoll(0)+sleep_ms(0)
    # ~9000x/sec while idle (~180x the rate at 20ms), pure CPU churn on RP2040's single core, for
    # the two real callers (captive_dns.py, async_connect.py) that never override it. Prove the
    # fixed default (20ms) is what ready() actually uses, not just what's documented.
    addr = make_addr()
    recorder = _RecordingAsyncio(asy_udp_socket.asyncio)
    asy_udp_socket.asyncio = recorder  # type: ignore[assignment]
    try:
        sock = AsyUDPSocket(addr, mode="server")
        try:
            run(sock.ready(select.POLLIN, timeout_ms=80))  # nothing ever arrives
        finally:
            run(sock.disconnect())
    finally:
        asy_udp_socket.asyncio = recorder._real

    assert len(recorder.sleep_ms_calls) > 0
    assert all(ms == 20 for ms in recorder.sleep_ms_calls)


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

    def socket(self, af: int, type: int) -> "Any":
        raise MemoryError("simulated allocation failure")


def test_connect_setup_memoryerror_self_heals_instead_of_raising() -> None:
    addr = make_addr()
    sock = AsyUDPSocket(addr, mode="server")
    original_socket = asy_udp_socket.socket
    asy_udp_socket.socket = _MemoryErrorOnceSocketModule()  # type: ignore[assignment]
    try:
        run(sock._connect())  # must not raise despite socket() raising MemoryError
    finally:
        asy_udp_socket.socket = original_socket

    assert sock.connected is False
    assert sock.sock is None

    try:
        run(sock._connect())  # the fault is gone now - should self-heal and succeed
        assert sock.connected is True
    finally:
        run(sock.disconnect())


class _MemoryErrorSocketWrapper:
    # Wraps a real, already-connected/bound socket - sendto()/write()/recvfrom() all raise
    # MemoryError instead of doing real I/O, proving each public method's except clause catches
    # it too, not just OSError. Everything else (close(), used by disconnect()) falls through to
    # the real socket via __getattr__.
    def __init__(self, real: "Any") -> None:
        self._real = real

    def sendto(self, *a: "Any", **k: "Any") -> "Any":
        raise MemoryError("simulated allocation failure")

    def write(self, *a: "Any", **k: "Any") -> "Any":
        raise MemoryError("simulated allocation failure")

    def recvfrom(self, *a: "Any", **k: "Any") -> "Any":
        raise MemoryError("simulated allocation failure")

    def __getattr__(self, name: str) -> "Any":
        return getattr(self._real, name)


def test_write_returns_none_sentinel_on_memoryerror() -> None:
    addr = make_addr()

    async def scenario() -> int | None:
        client = AsyUDPSocket(addr, mode="client")
        try:
            await client._connect()
            assert client.sock is not None
            client.sock = _MemoryErrorSocketWrapper(client.sock)  # type: ignore[assignment]
            return await client.write(b"x")
        finally:
            await client.disconnect()

    assert run(scenario()) is None


def test_sendto_returns_none_sentinel_on_memoryerror() -> None:
    addr = make_addr()

    async def scenario() -> int | None:
        server = AsyUDPSocket(addr, mode="server")
        try:
            await server._connect()
            assert server.sock is not None
            server.sock = _MemoryErrorSocketWrapper(server.sock)  # type: ignore[assignment]
            return await server.sendto(b"x", addr)
        finally:
            await server.disconnect()

    assert run(scenario()) is None


def test_recvfrom_returns_none_sentinel_on_memoryerror() -> None:
    addr = make_addr()
    peer_addr = make_addr()

    async def scenario() -> tuple[bytes | None, tuple[str, int] | None]:
        server = AsyUDPSocket(addr, mode="server")
        peer = AdversarialPeer(peer_addr)
        try:
            await server._connect()
            peer.sock.sendto(b"data", addr)
            await asyncio.sleep(0.05)  # a genuinely pending datagram, so recvfrom() actually
            # reaches sock.recvfrom() instead of timing out inside ready() first
            assert server.sock is not None
            server.sock = _MemoryErrorSocketWrapper(server.sock)  # type: ignore[assignment]
            return await server.recvfrom(64, timeout_ms=200)
        finally:
            peer.close()
            await server.disconnect()

    assert run(scenario()) == (None, None)


# ---------------------------------------------------------------------------
# disconnect() must clear its own state even when unregister()/close() themselves fail
# ---------------------------------------------------------------------------


class _RaisingUnregisterPoller:
    # unregister() raises - register()/ipoll() still delegate to the real poller so the rest of
    # the object's lifecycle (which already ran before this gets swapped in) is unaffected.
    def __init__(self, real: "Any") -> None:
        self._real = real

    def unregister(self, sock: "Any") -> None:
        raise OSError("simulated unregister failure")

    def register(self, *a: "Any", **k: "Any") -> "Any":
        return self._real.register(*a, **k)

    def ipoll(self, *a: "Any", **k: "Any") -> "Any":
        return self._real.ipoll(*a, **k)


def test_disconnect_clears_state_even_when_unregister_raises() -> None:
    # Bug: disconnect()'s single try/except wrapped unregister()+close()+state-clearing together
    # - a raising unregister() aborted the whole block before self.sock/self.poller/self.connected
    # were ever reset, confirmed directly: the object was left stuck in a broken half-connected
    # state forever, with no self-heal (unlike every other failure path in this file).
    addr = make_addr()

    async def scenario() -> tuple[bool, bool, bool]:
        sock = AsyUDPSocket(addr, mode="server")
        await sock._connect()
        assert sock.connected
        real_poller = sock.poller
        sock.poller = _RaisingUnregisterPoller(real_poller)  # type: ignore[assignment]
        await sock.disconnect()
        return sock.sock is None, sock.poller is None, sock.connected is False

    sock_cleared, poller_cleared, not_connected = run(scenario())
    assert sock_cleared and poller_cleared and not_connected


# ---------------------------------------------------------------------------
# ready() must survive a concurrent disconnect() on the same instance
# ---------------------------------------------------------------------------


class _DisconnectingPoller:
    # Wraps a real poller but nulls the owning AsyUDPSocket's self.poller the first time ipoll()
    # is called - simulates disconnect() firing concurrently on the same instance from another
    # coroutine while ready()'s poll loop is still in flight.
    def __init__(self, owner: "AsyUDPSocket", real: "Any") -> None:
        self.owner = owner
        self._real = real
        self.fired = False

    def register(self, *a: "Any", **k: "Any") -> "Any":
        return self._real.register(*a, **k)

    def ipoll(self, *a: "Any", **k: "Any") -> "Any":
        if not self.fired:
            self.fired = True
            self.owner.poller = None
        return self._real.ipoll(*a, **k)


def test_ready_survives_a_concurrent_disconnect_mid_poll_loop() -> None:
    # Bug: ready()'s poll loop only checked `self.poller is None` once, before the loop - if
    # another coroutine called disconnect() on the same instance mid-loop, the next
    # self.poller.ipoll(0) crashed with AttributeError ('NoneType' has no attribute 'ipoll'),
    # confirmed directly. Neither real caller does this today (both use one AsyUDPSocket from a
    # single coroutine at a time), but nothing in this file enforced or even documented that
    # constraint - fixed defensively instead: ready() now re-checks every iteration and returns
    # False, matching this file's own "never raises" contract instead of relying on callers to
    # never race it.
    addr = make_addr()

    async def scenario() -> bool:
        sock = AsyUDPSocket(addr, mode="server")
        try:
            await sock._connect()
            real_poller = sock.poller
            sock.poller = _DisconnectingPoller(sock, real_poller)  # type: ignore[assignment]
            return await sock.ready(select.POLLIN, timeout_ms=200, wait_time_ms=10)
        finally:
            await sock.disconnect()

    assert run(scenario()) is False


# ---------------------------------------------------------------------------
# _connect() retry/self-heal
# ---------------------------------------------------------------------------


def unbindable_addr() -> tuple[str, int]:
    # 10.255.255.254 is never a local interface address in this environment (confirmed directly:
    # bind() there raises OSError(EADDRNOTAVAIL)) - a deterministic way to force a real bind()
    # failure, unlike a same-port "blocker" socket, which SO_REUSEADDR (set by _connect() itself)
    # lets a second UDP socket bind alongside on Linux, so that approach never actually fails.
    return socket.getaddrinfo("10.255.255.254", 51999)[0][-1]  # type: ignore[return-value]


def test_conn_tries_retries_within_a_single_connect_call() -> None:
    bad_addr = unbindable_addr()
    good_addr = make_addr()

    async def scenario() -> bool:
        contender = AsyUDPSocket(bad_addr, mode="server", conn_tries=3)
        try:

            async def fix_address_soon() -> None:
                await asyncio.sleep(0.6)  # after >=1 failed attempt (0.5s backoff), before conn_tries=3 is exhausted (1.5s)
                contender._addr = good_addr

            fixer = asyncio.create_task(fix_address_soon())
            await contender._connect()  # early attempt(s) fail against bad_addr, then addr is fixed mid-retry
            await fixer
            return contender.connected
        finally:
            await contender.disconnect()

    assert run(scenario())


def test_connect_self_heals_after_conn_tries_exhausted() -> None:
    # Bug: once self.sock was created, a fully-exhausted conn_tries left _connect() a permanent
    # no-op (self.sock stayed non-None) - the object was stuck forever. It must now tear itself
    # down so a later call gets a fresh attempt.
    bad_addr = unbindable_addr()
    good_addr = make_addr()

    async def scenario() -> tuple[bool, bool, bool]:
        contender = AsyUDPSocket(bad_addr, mode="server", conn_tries=1)
        try:
            await contender._connect()  # exhausts its single try against an unbindable address
            first_connected = contender.connected
            first_sock_cleared = contender.sock is None

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
    addr = make_addr()

    async def scenario() -> tuple[bool, bool, bool]:
        sock = AsyUDPSocket(addr, mode="server")
        await sock._connect()
        assert sock.connected
        await sock.disconnect()
        state = (sock.sock is None, sock.poller is None, sock.connected is False)
        await sock.disconnect()  # must not raise when already disconnected
        return state

    sock_cleared, poller_cleared, not_connected = run(scenario())
    assert sock_cleared and poller_cleared and not_connected


def test_object_is_reusable_after_disconnect() -> None:
    addr = make_addr()

    async def scenario() -> tuple[bytes | None, bytes | None]:
        server = AsyUDPSocket(addr, mode="server")
        client = AsyUDPSocket(addr, mode="client")
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
    addr = make_addr()

    async def scenario() -> bool:
        server = AsyUDPSocket(addr, mode="server")
        try:
            task = asyncio.create_task(server.recvfrom(64))  # nothing ever arrives - waits forever
            await asyncio.sleep(0.05)
            task.cancel()
            try:
                await task
                return False  # should never get here
            except asyncio.CancelledError:
                return True
        finally:
            await server.disconnect()

    assert run(scenario())


# ---------------------------------------------------------------------------
# ready()'s wait_time_ms must be milliseconds, not seconds
# ---------------------------------------------------------------------------


def test_ready_wait_time_ms_is_milliseconds_not_seconds() -> None:
    # Bug: ready() used to call asyncio.sleep(wait_time_ms) (seconds), not asyncio.sleep_ms() -
    # a wait_time_ms=10 would sleep 10 real seconds per poll cycle instead of 10ms. Prove a
    # bounded-timeout call actually completes in tens of milliseconds, not multiple real seconds.
    addr = make_addr()

    async def scenario() -> int:
        sock = AsyUDPSocket(addr, mode="server")
        try:
            t0 = time.ticks_ms()
            result = await sock.ready(select.POLLIN, timeout_ms=50, wait_time_ms=10)
            assert result is False  # nothing ever arrives
            return time.ticks_diff(time.ticks_ms(), t0)
        finally:
            await sock.disconnect()

    elapsed = run(scenario())
    assert elapsed < 2000  # generously below the 10000ms+ the old seconds-interpretation bug would take


# ---------------------------------------------------------------------------
# _connect()'s own setup code (socket()/setsockopt()/poll()/register()) must not raise
# ---------------------------------------------------------------------------


class _RaisingSocketModule:
    # MicroPython's real `socket` module is a read-only builtin (same reason
    # test_system_service.py's own time-module fakes exist - see that file) - can't monkeypatch
    # an attribute onto it, so this replaces asy_udp_socket's own module-level `socket` name
    # instead. Mirrors the real module's constants asy_udp_socket.py references, but socket()
    # itself always raises - simulates a resource-exhaustion failure (e.g. out of file
    # descriptors) at the very first setup step, before the connect/bind retry loop ever runs.
    AF_INET = socket.AF_INET
    SOCK_DGRAM = socket.SOCK_DGRAM
    SOL_SOCKET = socket.SOL_SOCKET
    SO_REUSEADDR = socket.SO_REUSEADDR

    def socket(self, af: int, type: int) -> "Any":
        raise OSError("simulated resource exhaustion")


def test_connect_setup_failure_self_heals_instead_of_raising() -> None:
    # Bug: socket()/setsockopt()/poll()/register() ran with zero exception handling - violated
    # this file's own "never raises" contract, and would have leaked a half-initialized socket.
    addr = make_addr()
    sock = AsyUDPSocket(addr, mode="server")
    original_socket = asy_udp_socket.socket
    asy_udp_socket.socket = _RaisingSocketModule()  # type: ignore[assignment]  # deliberate monkeypatch, not a real caller mismatch
    try:
        run(sock._connect())  # must not raise despite socket() failing
    finally:
        asy_udp_socket.socket = original_socket

    assert sock.connected is False
    assert sock.sock is None

    try:
        run(sock._connect())  # the fault is gone now - should self-heal and succeed
        assert sock.connected is True
    finally:
        run(sock.disconnect())


# ---------------------------------------------------------------------------
# ready() must notice POLLERR/POLLHUP, not just its own requested mask
# ---------------------------------------------------------------------------


def test_recvfrom_detects_pollerr_instead_of_waiting_out_the_full_timeout() -> None:
    # Confirmed empirically (not just reasoned about): a connected UDP client socket with a
    # pending ICMP port-unreachable reports POLLOUT|POLLERR, never POLLIN - ready(POLLIN) used to
    # check only `event & mask` and would ignore POLLERR entirely, waiting out the full timeout
    # for a failure the kernel already knew about. Connect to an address nobody listens on, send,
    # then prove recvfrom() returns promptly (well under its timeout) instead of stalling.
    addr = make_addr()  # nobody ever binds/listens on this address

    async def scenario() -> tuple[bytes | None, int]:
        client = AsyUDPSocket(addr, mode="client")
        try:
            sent = await client.write(b"ping")
            assert sent == 4
            await asyncio.sleep(0.2)  # let the kernel deliver the ICMP unreachable
            t0 = time.ticks_ms()
            data, _ = await client.recvfrom(64, timeout_ms=5000)  # generously long if the old bug were still present
            return data, time.ticks_diff(time.ticks_ms(), t0)
        finally:
            await client.disconnect()

    data, elapsed = run(scenario())
    assert data is None  # recvfrom() itself still raises OSError, correctly converted to the sentinel
    assert elapsed < 1000  # detected via POLLERR promptly, not by waiting out the 5000ms timeout


# ---------------------------------------------------------------------------
# async with support
# ---------------------------------------------------------------------------


def test_async_context_manager_disconnects_on_exit() -> None:
    addr = make_addr()

    async def scenario() -> tuple[bool, AsyUDPSocket]:
        async with AsyUDPSocket(addr, mode="server") as sock:
            await sock._connect()
            still_connected_inside = sock.connected
        return still_connected_inside, sock

    still_connected_inside, sock = run(scenario())
    assert still_connected_inside is True
    assert sock.sock is None
    assert sock.connected is False


def test_async_context_manager_disconnects_even_on_exception() -> None:
    addr = make_addr()

    async def scenario() -> AsyUDPSocket:
        sock = AsyUDPSocket(addr, mode="server")
        try:
            async with sock:
                await sock._connect()
                raise ValueError("boom")
        except ValueError:
            pass
        return sock

    sock = run(scenario())
    assert sock.sock is None
    assert sock.connected is False


# ---------------------------------------------------------------------------
# Integration-level: exact real-world call patterns, informed by (not importing - improved-
# quality/ stays out of scope per CLAUDE.md) the current upstream callers async_connect.py's NTP
# client and captive_dns.py's DNSServer, plus how a real UDP fault propagates up through each
# processing path. These mirror each caller's documented, stable call shape (mode, buffer sizes,
# timeout/tries, acquire-use-release pattern) rather than importing WIP implementation details
# that could change during the refactor - proving the *contract* is robust protects any future
# refactored caller too, not just today's.
# ---------------------------------------------------------------------------


def test_ntp_client_pattern_end_to_end_success() -> None:
    # Mirrors async_connect.py's exact NTP call shape: AsyUDPSocket(addr, mode="client"),
    # write_and_recvfrom(48-byte NTP request, 1024-byte buffer, timeout_ms=...), disconnect()
    # called once on the success path AND unconditionally again in finally - proving that
    # double-disconnect() (already proven idempotent in isolation) is genuinely safe in this
    # exact real usage shape too, and that the caller's broad `except Exception` backstop is
    # never actually needed.
    server_addr = make_addr()
    ntp_request = b"\x1b" + bytearray(47)
    ntp_reply = b"\x1c" + bytearray(47)  # a realistic 48-byte NTP-shaped reply

    async def responder(peer: AdversarialPeer) -> None:
        _, from_addr = await peer.recv(1024, timeout_ms=1000)
        assert from_addr is not None
        peer.sock.sendto(ntp_reply, from_addr)

    async def scenario() -> tuple[bytes | None, bool]:
        peer = AdversarialPeer(server_addr)
        exception_hit = False
        cli = None
        msg: bytes | None = None
        try:
            responder_task = asyncio.create_task(responder(peer))
            cli = AsyUDPSocket(server_addr, mode="client")
            msg, add = await cli.write_and_recvfrom(ntp_request, 1024, timeout_ms=1000)
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
    # Mirrors the exact same call shape against an address nobody listens on (a real network
    # fault: ICMP port-unreachable, exactly like a genuinely offline NTP server) - proving msg
    # ends up None (matching the real "if msg is None: retry" branch downstream) without ever
    # needing the caller's broad except Exception backstop.
    server_addr = make_addr()  # nobody ever binds/listens here
    ntp_request = b"\x1b" + bytearray(47)

    async def scenario() -> tuple[bytes | None, bool]:
        exception_hit = False
        cli = None
        msg: bytes | None = None
        try:
            cli = AsyUDPSocket(server_addr, mode="client")
            msg, add = await cli.write_and_recvfrom(ntp_request, 1024, timeout_ms=500)
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
    # Content-agnostic transport, exercised through the exact real call shape: a "server" that
    # replies with garbage (not a valid 48-byte NTP packet at all) must still be delivered
    # faithfully - validating NTP structure is async_connect.py's own job, not this module's.
    server_addr = make_addr()
    ntp_request = b"\x1b" + bytearray(47)
    garbage_reply = b"\x00\x01\x02not-an-ntp-packet-at-all" * 3

    async def responder(peer: AdversarialPeer) -> None:
        _, from_addr = await peer.recv(1024, timeout_ms=1000)
        assert from_addr is not None
        peer.sock.sendto(garbage_reply, from_addr)

    async def scenario() -> bytes | None:
        peer = AdversarialPeer(server_addr)
        cli = AsyUDPSocket(server_addr, mode="client")
        try:
            responder_task = asyncio.create_task(responder(peer))
            msg, _ = await cli.write_and_recvfrom(ntp_request, 1024, timeout_ms=1000)
            await responder_task
            return msg
        finally:
            await cli.disconnect()
            peer.close()

    assert run(scenario()) == garbage_reply


def test_dns_server_pattern_bound_to_all_interfaces_end_to_end() -> None:
    # Mirrors captive_dns.py's exact DNSServer call shape: AsyUDPSocket(("0.0.0.0", port),
    # mode="server"), recvfrom(4096), conditional sendto(response, addr) - including the real
    # 0.0.0.0-bind-then-receive-via-127.0.0.1-targeted-traffic path (every other test in this
    # file binds and targets 127.0.0.1 directly, never exercising a real "any interface" bind).
    port = make_port()
    server_addr = resolve_addr("0.0.0.0", port)
    client_target_addr = resolve_addr("127.0.0.1", port)
    query = b"\x00\x01fake-dns-query"
    response = b"\x00\x01fake-dns-response"

    async def scenario() -> tuple[bytes | None, tuple[str, int] | None, bytes]:
        server = AsyUDPSocket(server_addr, mode="server")
        client = AdversarialPeer(make_addr())
        try:
            await server._connect()
            client.sock.sendto(query, client_target_addr)
            data, addr = await server.recvfrom(4096, timeout_ms=1000)
            if data is not None and addr is not None:  # captive_dns.py's exact guard
                await server.sendto(response, addr)
            reply, _ = await client.recv(4096, timeout_ms=1000)
            return data, addr, reply
        finally:
            client.close()
            await server.disconnect()

    data, addr, reply = run(scenario())
    assert data == query
    # addr's exact representation is platform-opaque on this Unix-port build too (recvfrom()'s
    # returned address is a raw bytearray sockaddr here, not a (host, port) tuple - the same
    # quirk make_addr()/resolve_addr() already work around for getaddrinfo()) - only its
    # existence (used to route the reply below) is this test's concern, not its shape.
    assert addr is not None
    assert reply == response


def test_dns_server_pattern_recvfrom_never_returns_a_mismatched_pair() -> None:
    # captive_dns.py's exact guard is `if data is not None and addr is not None:` - implicitly
    # assuming these are always both-set or both-None together. Confirm that assumption actually
    # holds: recvfrom() never returns (bytes, None) or (None, tuple) in either the timeout or the
    # success path.
    addr = make_addr()
    peer_addr = make_addr()

    async def scenario() -> tuple[tuple[bytes | None, tuple[str, int] | None], tuple[bytes | None, tuple[str, int] | None]]:
        server = AsyUDPSocket(addr, mode="server")
        peer = AdversarialPeer(peer_addr)
        try:
            await server._connect()
            timeout_result = await server.recvfrom(64, timeout_ms=100)  # nobody sends - timeout path
            peer.sock.sendto(b"real query", addr)
            success_result = await server.recvfrom(64, timeout_ms=500)  # success path
            return timeout_result, success_result
        finally:
            peer.close()
            await server.disconnect()

    timeout_result, success_result = run(scenario())
    assert timeout_result == (None, None)
    assert (success_result[0] is None) == (success_result[1] is None)  # always paired, never mismatched
    assert success_result[0] == b"real query"


def test_dns_server_pattern_sendto_failure_does_not_corrupt_subsequent_serving() -> None:
    # captive_dns.py discards sendto()'s return value entirely (`await self.udps.sendto(packet,
    # addr)`) - a failed reply (e.g. the resolving client's route disappearing mid-response) is
    # silently swallowed one level above this module, never observed or logged by the real caller
    # today (flagged in BACKLOG.md - out of scope to fix inside captive_dns.py itself). What this
    # module IS responsible for: proving that failure can't corrupt the *server socket* for the
    # next, unrelated query in the same long-lived DNSServer loop - this is exactly "how a real
    # UDP fault could propagate up through the processing path" for this caller's shape.
    addr = make_addr()
    unreachable_client_addr = resolve_addr("10.255.255.254", 12345)  # never routable in this environment
    real_peer_addr = make_addr()

    async def scenario() -> bytes | None:
        server = AsyUDPSocket(addr, mode="server")
        peer = AdversarialPeer(real_peer_addr)
        try:
            await server._connect()
            await server.sendto(b"reply to nobody", unreachable_client_addr)  # never raises either way

            peer.sock.sendto(b"next real query", addr)
            data, from_addr = await server.recvfrom(64, timeout_ms=500)
            assert from_addr is not None
            await server.sendto(b"real reply", from_addr)
            reply, _ = await peer.recv(64, timeout_ms=500)
            return reply
        finally:
            peer.close()
            await server.disconnect()

    assert run(scenario()) == b"real reply"  # the server socket kept working for the next query


# ---------------------------------------------------------------------------
# Fifth pass: __init__'s validation only runs once, at construction - a direct post-construction
# mutation of _addr/_conn_tries (private, but Python doesn't truly enforce that) can still put the
# object into the exact same shapes the validation was meant to prevent. Confirmed directly, then
# fixed by widening every touching except clause to catch TypeError too, not by re-validating on
# every access.
# ---------------------------------------------------------------------------


def test_connect_self_heals_when_addr_mutated_to_a_malformed_value() -> None:
    # Bug: mutating ._addr directly after construction (bypassing __init__'s validation entirely)
    # used to raise an uncaught TypeError from sock.connect()/bind(), reintroducing the exact bug
    # __init__'s eager validation was meant to close, just through a different door. Confirmed
    # directly. Fixed: _connect()'s connect()/bind() try now also catches TypeError.
    addr = make_addr()
    sock = AsyUDPSocket(addr, mode="client")
    sock._addr = (12345, 80)  # type: ignore[assignment]  # malformed - host is an int, not a str
    try:
        run(sock._connect())  # must not raise
        assert sock.connected is False
    finally:
        run(sock.disconnect())


def test_connect_self_heals_when_conn_tries_mutated_to_a_non_int() -> None:
    # Bug: mutating ._conn_tries to None used to raise an uncaught TypeError - but not from inside
    # the per-attempt try/except (which already caught TypeError): `tries < self._conn_tries` is
    # the while loop's own *condition*, evaluated before the inner try is ever entered, so only
    # the outer try/except covers it - confirmed directly this was still uncaught even after the
    # inner-try fix, because the outer except hadn't been widened yet. Fixed: the outer except now
    # also catches TypeError.
    addr = make_addr()
    sock = AsyUDPSocket(addr, mode="server")
    sock._conn_tries = None  # type: ignore[assignment]
    try:
        run(sock._connect())  # must not raise
        assert sock.connected is False
    finally:
        run(sock.disconnect())


def test_connect_treats_a_mutated_mode_as_server_like_without_crashing() -> None:
    # Not a bug: _connect()'s mode branch is a plain if/else (client vs. everything else) since
    # __init__ already guarantees only "client"/"server" reach it - a mutated ._mode bypasses that
    # guarantee, but the binary branch shape means it just falls through to the bind() (server-
    # like) path rather than hanging the way the old three-way branch with a dead else did.
    # Documented behavior, confirmed directly, not something worth guarding against further.
    addr = make_addr()
    sock = AsyUDPSocket(addr, mode="client")
    sock._mode = "bogus"  # type: ignore[assignment]
    try:
        run(sock._connect())
        assert sock.connected is True  # treated as bind(), which succeeds on a fresh address
    finally:
        run(sock.disconnect())


def test_sendto_returns_none_sentinel_for_a_malformed_explicit_addr() -> None:
    # Same class of bug as ._addr mutation above, but for sendto()'s own per-call addr parameter -
    # confirmed directly this used to raise an uncaught TypeError too.
    addr = make_addr()

    async def scenario() -> int | None:
        server = AsyUDPSocket(addr, mode="server")
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
    addr = make_addr()
    peer_addr = make_addr()

    async def scenario() -> tuple[bytes | None, tuple[str, int] | None]:
        server = AsyUDPSocket(addr, mode="server")
        peer = AdversarialPeer(peer_addr)
        try:
            await server._connect()
            peer.sock.sendto(b"real data", addr)
            await asyncio.sleep(0.05)
            return await server.recvfrom("not an int", timeout_ms=200)  # type: ignore[arg-type]
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
    # Bug: before the connect-lock, a disconnect() call concurrent with another coroutine's
    # in-flight _connect() retry could null self.sock/self.poller out from under it - confirmed
    # directly this crashed with an uncaught AttributeError ('NoneType' has no attribute 'bind')
    # on the retry's next connect()/bind() call. Fixed: disconnect() now takes the same lock, so
    # it waits for the in-flight attempt to finish (bounded by conn_tries * the retry backoff)
    # instead of tearing it down mid-flight.
    bad_addr = unbindable_addr()

    async def scenario() -> tuple[bool, int]:
        sock = AsyUDPSocket(bad_addr, mode="server", conn_tries=3)
        try:
            t0 = time.ticks_ms()
            connect_task = asyncio.create_task(sock._connect())
            await asyncio.sleep(0.1)  # let it fail its first attempt and start backing off
            await sock.disconnect()  # must not raise, and must not crash connect_task either
            await connect_task
            elapsed = time.ticks_diff(time.ticks_ms(), t0)
            return sock.connected, elapsed
        finally:
            await sock.disconnect()

    connected, elapsed = run(scenario())
    assert connected is False  # bad_addr never becomes bindable
    assert elapsed >= 1000  # disconnect() genuinely waited for the ~1.5s (3 tries) retry cycle
    assert elapsed < 5000  # ...but didn't hang forever either


def test_concurrent_caller_joins_an_in_flight_connect_instead_of_a_premature_none() -> None:
    # Confirmed directly (before this fix): a coroutine calling a public method while another
    # coroutine's _connect() was mid-retry got a spurious None immediately, instead of waiting for
    # the in-flight attempt. Proves the fixed behavior: B's sendto() blocks until A's connect
    # resolves, then genuinely succeeds once A's retry succeeds - not a redundant retry of its own.
    bad_addr = unbindable_addr()
    good_addr = make_addr()

    async def scenario() -> tuple[bool, int | None]:
        sock = AsyUDPSocket(bad_addr, mode="server", conn_tries=3)
        try:
            a_task = asyncio.create_task(sock._connect())
            await asyncio.sleep(0.1)  # A has failed its first attempt, is backing off

            async def fix_address_soon() -> None:
                await asyncio.sleep(0.5)
                sock._addr = good_addr

            fixer = asyncio.create_task(fix_address_soon())
            b_task = asyncio.create_task(sock.sendto(b"x", good_addr))
            await a_task
            await fixer
            b_result = await b_task
            return sock.connected, b_result
        finally:
            await sock.disconnect()

    connected, b_result = run(scenario())
    assert connected is True
    assert b_result == 1  # len(b"x") - B's call succeeded once A's retry succeeded, not None


def test_cancelling_a_task_that_holds_the_connect_lock_releases_it() -> None:
    # Locks + cancellation are a classic deadlock source, and this file just gained its first
    # lock - verified directly rather than assumed: async with's __aexit__ must still run (and
    # release the lock) when the task holding it is cancelled mid-retry, or every future caller
    # on this instance would hang forever waiting for a lock nobody will ever release.
    bad_addr = unbindable_addr()

    async def scenario() -> tuple[bool, bool]:
        sock = AsyUDPSocket(bad_addr, mode="server", conn_tries=5)
        a_task = asyncio.create_task(sock._connect())
        await asyncio.sleep(0.1)  # A has failed once, is inside its backoff sleep, holding the lock
        a_task.cancel()
        cancelled_cleanly = False
        try:
            await a_task
        except asyncio.CancelledError:
            cancelled_cleanly = True

        try:
            await asyncio.wait_for(sock.disconnect(), 2)
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
    bad_addr = unbindable_addr()

    async def scenario() -> tuple[bool, bool]:
        sock = AsyUDPSocket(bad_addr, mode="server", conn_tries=3)
        a_task = asyncio.create_task(sock._connect())
        await asyncio.sleep(0.1)
        b_task = asyncio.create_task(sock.disconnect())  # blocks waiting for the lock A holds
        await asyncio.sleep(0.05)  # let B actually start waiting
        b_task.cancel()
        b_cancelled_cleanly = False
        try:
            await b_task
        except asyncio.CancelledError:
            b_cancelled_cleanly = True

        try:
            await asyncio.wait_for(a_task, 3)
            a_completed = True
        except asyncio.TimeoutError:
            a_completed = False
        try:
            await asyncio.wait_for(sock.disconnect(), 2)
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
    # write() semantically requires a connected socket (unlike sendto(), which takes an explicit
    # destination) - calling it on a bound-but-unconnected server-mode socket is a caller misuse
    # this file deliberately doesn't guard against structurally (see BACKLOG.md's second pass:
    # "no structural guard... guarding against a misuse that doesn't happen would just add
    # complexity"), but that reasoning was never actually verified to be non-crashing. Confirmed
    # directly here: the real ENOTCONN-style OSError is caught like any other socket failure.
    addr = make_addr()

    async def scenario() -> int | None:
        server = AsyUDPSocket(addr, mode="server")
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
    addr = make_addr()

    async def scenario() -> int | None:
        server = AsyUDPSocket(addr, mode="server")
        try:
            await server._connect()
            return await server.sendto(b"", make_addr())
        finally:
            await server.disconnect()

    assert run(scenario()) == 0


def test_recvfrom_buf_zero_returns_empty_bytes_not_the_timeout_sentinel() -> None:
    # An extreme instance of the already-documented truncation contract, not a new behavior -
    # confirmed directly: buf=0 against a genuinely pending datagram returns (b"", addr), not the
    # (None, None) timeout sentinel, distinguishing "received nothing because buf=0" from
    # "received nothing because nothing arrived".
    addr = make_addr()
    peer_addr = make_addr()

    async def scenario() -> bytes | None:
        server = AsyUDPSocket(addr, mode="server")
        peer = AdversarialPeer(peer_addr)
        try:
            await server._connect()
            peer.sock.sendto(b"real data", addr)
            await asyncio.sleep(0.05)
            data, _ = await server.recvfrom(0, timeout_ms=200)
            return data
        finally:
            peer.close()
            await server.disconnect()

    assert run(scenario()) == b""


def test_disconnect_on_a_fresh_never_connected_object_is_a_clean_no_op() -> None:
    addr = make_addr()

    async def scenario() -> tuple[bool, bool]:
        sock = AsyUDPSocket(addr, mode="client")
        await sock.disconnect()  # _connect() was never called - must not raise
        return sock.sock is None, sock.connected is False

    sock_is_none, not_connected = run(scenario())
    assert sock_is_none and not_connected


def test_write_and_recvfrom_tries_zero_returns_immediately() -> None:
    addr = make_addr()

    async def scenario() -> tuple[bytes | None, tuple[str, int] | None]:
        sock = AsyUDPSocket(addr, mode="client")
        try:
            return await sock.write_and_recvfrom(b"x", 64, timeout_ms=50, tries=0)
        finally:
            await sock.disconnect()

    assert run(scenario()) == (None, None)


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
