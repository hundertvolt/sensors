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
                contender.addr = good_addr

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

            contender.addr = good_addr  # simulate the underlying condition clearing
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


if __name__ == "__main__":
    import microtest

    microtest.run(globals())
