"""redirect_udp_port(module, real_port, fake_port): for one with-block, module.UDPSocket is a subclass that maps
(host, real_port) to (host, fake_port) before the real constructor runs, so a test server stands in for DNS or NTP
without binding a privileged port; `as redirect` counts the constructor calls in redirect.constructed."""

from asy_udp_socket import UDPSocket

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing has no runtime presence on MicroPython, on-device or in the Unix-port test build
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import Literal

_CLASS = "UDPSocket"  # the module global the redirect shadows


class redirect_udp_port:  # noqa: N801  # a with-block helper, named like contextlib.redirect_stdout
    def __init__(self, module: object, real_port: int, fake_port: int) -> None:
        self.constructed = 0
        self._module = module
        self._real_port = real_port
        self._fake_port = fake_port
        self._saved: object = None

    def __enter__(self) -> "redirect_udp_port":
        redirect = self

        class _Redirected(UDPSocket):
            def __init__(self, addr: tuple[str, int], mode: 'Literal["client", "server"]' = "client") -> None:
                redirect.constructed += 1
                # Anything but a (host, real_port) tuple reaches the real constructor as given, malformed or not.
                if isinstance(addr, tuple) and len(addr) == 2 and addr[1] == redirect._real_port:
                    addr = (addr[0], redirect._fake_port)
                super().__init__(addr, mode=mode)

        self._saved = getattr(self._module, _CLASS)
        setattr(self._module, _CLASS, _Redirected)
        return self

    def __exit__(self, *_exc: object) -> None:
        setattr(self._module, _CLASS, self._saved)
