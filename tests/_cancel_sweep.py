"""cancel_at_each_await(): a task path cancelled after 0, 1, 2, ... scheduler turns, a fresh fixture and one
_async_harness run() per count, each cancel re-raised, no lock release refused and the invariants holding after it;
assert_unlocked() and SocketLedger (the real sockets given modules open, each closed or not) are what paths share."""

import asyncio
import socket as _socket

from _async_harness import run

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
    from typing import TypeVar

    F = TypeVar("F")
    Step = Callable[[], Coroutine[object, object, object]]


class _ReleaseLedger:
    # For a sweep, asyncio.Lock.release counts each call on a lock not held, the one call it refuses (extmod/asyncio/
    # lock.py:22-23, v1.29.0): a double release a caller swallows, as Lockable.__aexit__ does, ends with the lock free.
    def __init__(self) -> None:
        self.refused = 0
        self._release = asyncio.Lock.release

    def __enter__(self) -> "_ReleaseLedger":
        ledger, real = self, self._release

        def release(self: asyncio.Lock) -> None:  # `self` as in the method it stands in for
            if not self.locked():  # locked() is `state == 1`, the very test release() refuses on
                ledger.refused += 1
            real(self)

        asyncio.Lock.release = release  # type: ignore[method-assign]  # a class attribute swap, restored on exit
        try:
            asyncio.Lock().release()  # the floor: a release refused and counted, or this check could match nothing
        except RuntimeError:
            if self.refused == 1:
                return self
        self.__exit__()
        raise AssertionError("the release ledger did not count a refused release")

    def __exit__(self, *_exc_info: object) -> None:
        asyncio.Lock.release = self._release  # type: ignore[method-assign]

    def assert_balanced(self, where: str) -> None:
        if self.refused:
            raise AssertionError(f"{where}: a lock refused {self.refused} release(s): a double release")


class SocketLedger:
    # For the block each given module's `socket` is this ledger: socket() opens a real one and records it, every other
    # name is the real module's. A closed socket's fileno() is -1 on this port (ports/unix/modsocket.c:148, v1.29.0).
    def __init__(self, *modules: object) -> None:
        self._modules = modules
        self._saved: list[object] = []
        self.opened: list[_socket.socket] = []

    def __enter__(self) -> "SocketLedger":
        self._saved = [module.socket for module in self._modules]  # type: ignore[attr-defined]  # each a module opening sockets
        for module in self._modules:
            module.socket = self  # type: ignore[attr-defined]  # a module attribute swap, restored on exit
        return self

    def __exit__(self, *_exc_info: object) -> None:
        for index, module in enumerate(self._modules):
            module.socket = self._saved[index]  # type: ignore[attr-defined]
        for sock in self.still_open():
            sock.close()  # a failed check's leak ends with the block, not with the process

    def __getattr__(self, name: str) -> object:
        return getattr(_socket, name)

    def assert_closed(self) -> None:
        left = len(self.still_open())
        if left:
            raise AssertionError(f"{left} socket(s) left open")

    def socket(self, *args: int) -> _socket.socket:
        sock = _socket.socket(*args)
        self.opened.append(sock)
        return sock

    def still_open(self) -> "list[_socket.socket]":
        # Drops the closed ones as it reads, so the record holds one sweep count's sockets, not every count's.
        self.opened = [sock for sock in self.opened if sock.fileno() != -1]  # type: ignore[attr-defined]  # the Unix port's (modsocket.c:192); the rp2 stub has none
        return list(self.opened)


async def _cancel_after(build: "Callable[[], Coroutine[object, object, F]]", start: "Callable[[F], Coroutine[object, object, object]]", invariants: "Callable[[F], None]", k: int, turn: "Step | None", teardown: "Callable[[F], Coroutine[object, object, object]] | None", ledger: _ReleaseLedger) -> bool:
    # One count over a fresh fixture, torn down on every path; a teardown failing after the count failed is printed,
    # so the count's own failure is the one raised.
    fixture = await build()
    try:
        completed = await _cancel_one(fixture, start, invariants, k, turn, ledger)
    except BaseException:
        if teardown is not None:
            try:
                await teardown(fixture)
            except Exception as e:  # printed beside the failure raised below, never in its place
                print("the teardown failed too:", repr(e))
        raise
    if teardown is not None:
        await teardown(fixture)
    return completed


async def _cancel_one(fixture: "F", start: "Callable[[F], Coroutine[object, object, object]]", invariants: "Callable[[F], None]", k: int, turn: "Step | None", ledger: _ReleaseLedger) -> bool:
    # True when the path completed within k turns, else it was cancelled there and the invariants held; either way no
    # lock refused a release in the count.
    task = asyncio.create_task(start(fixture))
    for _ in range(k):
        await (asyncio.sleep(0) if turn is None else turn())
    if task.done():
        await task  # a path that ended with a failure raises it here
        ledger.assert_balanced(f"completed after {k} turns")
        return True
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    except Exception as e:
        raise AssertionError(f"cancelled after {k} turns, the path raised {e!r}") from e
    else:
        raise AssertionError(f"cancelled after {k} turns, the path returned instead of raising CancelledError")
    try:
        invariants(fixture)
    except AssertionError as e:
        raise AssertionError(f"cancelled after {k} turns: {e}") from None
    ledger.assert_balanced(f"cancelled after {k} turns")
    return False


def assert_unlocked(**locks: asyncio.Lock) -> None:
    for name in sorted(locks):
        if locks[name].locked():
            raise AssertionError(f"{name} is still locked")


def cancel_at_each_await(build: "Callable[[], Coroutine[object, object, F]]", start: "Callable[[F], Coroutine[object, object, object]]", invariants: "Callable[[F], None]", *, max_steps: int = 200, turn: "Step | None" = None, teardown: "Callable[[F], Coroutine[object, object, object]] | None" = None, endless: bool = False) -> int:
    # The number of counts it cancelled at: the turns the path took to complete, or max_steps for an `endless` path
    # (a server loop). A turn is one sleep(0) unless `turn` is given, e.g. a DrivenTime elapse() shorter than any sleep.
    # Called from a test's synchronous scope.
    with _ReleaseLedger() as ledger:
        for k in range(max_steps):
            ledger.refused = 0
            if run(_cancel_after(build, start, invariants, k, turn, teardown, ledger)):
                return k
    if endless:
        return max_steps
    raise AssertionError(f"the path was still running after {max_steps} turns")
