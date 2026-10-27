"""FailNextUdpSetup(step, mode): in one with-block the next product UDPSocket setup fails at `step`: "socket" (socket()
raises ENOMEM, as an rp2 pcb allocation can) or "address" (a `mode` socket's connect()/bind() gets the shim's refused
sockaddr, which the host kernel rejects with EINVAL). `made` keeps each socket made; closed() says which are closed."""

import errno
import socket

import _unix_port_udp_addr_shim

import asy_udp_socket

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine

    _Connect = Callable[[asy_udp_socket.UDPSocket], Coroutine[object, object, None]]


class _SocketModule:
    # asy_udp_socket's `socket` inside the block: the names _connect() reads, socket() failing at the armed "socket" step.
    AF_INET = socket.AF_INET
    SOCK_DGRAM = socket.SOCK_DGRAM
    SOL_SOCKET = socket.SOL_SOCKET
    SO_REUSEADDR = socket.SO_REUSEADDR

    def __init__(self, fault: "FailNextUdpSetup") -> None:
        self._fault = fault

    def socket(self, family: int, kind: int) -> socket.socket:
        if self._fault.take("socket"):
            raise OSError(errno.ENOMEM)
        made = socket.socket(family, kind)
        self._fault.made.append(made)
        return made


class FailNextUdpSetup:
    def __init__(self, step: str, mode: str = "client") -> None:
        if step not in ("socket", "address"):
            raise ValueError(f"step must be 'socket' or 'address', got {step!r}")
        self.step = step
        self.mode = mode
        self.fired = 0  # how many setups the fault failed: one, once the product has set a socket up
        self.made: list[socket.socket] = []
        self._saved: tuple[object, _Connect] | None = None

    def __enter__(self) -> "FailNextUdpSetup":
        real = _unix_port_udp_addr_shim._real_connect
        fault = self

        async def connect(self: asy_udp_socket.UDPSocket) -> None:
            # The product's own _connect() for the socket `self`, below the shim's address handling; the armed call's
            # address is swapped for the refused sockaddr and put back after.
            if self._mode != fault.mode or not fault.take("address"):
                await real(self)
                return
            kept = self._addr
            self._addr = _unix_port_udp_addr_shim._REFUSED_SOCKADDR  # type: ignore[assignment]  # a sockaddr, as the shim's own swap
            try:
                await real(self)
            finally:
                self._addr = kept

        self._saved = (asy_udp_socket.socket, real)
        asy_udp_socket.socket = _SocketModule(self)  # type: ignore[assignment]  # a module-global swap, put back on exit
        _unix_port_udp_addr_shim._real_connect = connect
        return self

    def __exit__(self, *_exc: object) -> None:
        if self._saved is not None:
            asy_udp_socket.socket, _unix_port_udp_addr_shim._real_connect = self._saved  # type: ignore[assignment]

    def closed(self) -> list[bool]:
        # Per socket made, oldest first: True once closed (a closed Unix-port socket's fileno() reads -1).
        return [made.fileno() == -1 for made in self.made]  # type: ignore[attr-defined]  # the Unix port's socket has it, rp2's none

    def take(self, step: str) -> bool:
        # True once, for the first setup reaching the armed step.
        if self.fired or step != self.step:
            return False
        self.fired = 1
        return True
