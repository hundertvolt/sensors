import sys
p = sys.argv[1]
s = open(p).read()

def rep(old, new, count=1):
    global s
    n = s.count(old)
    assert n == count, (old[:80], n)
    s = s.replace(old, new)

# --- A. imports and the shim
rep('''import select
import socket
import time

import asy_udp_socket
from asy_udp_socket import UDPSocket

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing isn't available on the real MicroPython test interpreter
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Awaitable, Coroutine, Iterator
''', '''import select
import socket
import sys
import time

sys.path.insert(0, "digital_twin/unixport")  # the Unix-port UDP address shim (SPECIFICATION.md F.7 row 1)

from _udp_port_redirect import redirect_udp_port
from _unix_port_udp_addr_shim import patch_asy_udp_socket_for_unix_port

import asy_print_log
import asy_udp_socket
from asy_udp_socket import UDPSocket

# UDPSocket takes plain (host, port) tuples; on this Unix build the shim resolves them (once, class-wide).
patch_asy_udp_socket_for_unix_port()

try:
    from typing import TYPE_CHECKING
except ImportError:  # typing isn't available on the real MicroPython test interpreter
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Coroutine, Iterator
''')

# --- B. address helpers
rep('''def make_addr() -> tuple[str, int]:  # a fresh loopback port per call, so tests never contend for the same address
    global _next_port
    _next_port += 1
    # The Unix port's "standard" build rejects a plain (host, port) tuple in bind()/connect()/
    # sendto() with "TypeError: object with buffer protocol required" (micropython/micropython#6924),
    # unlike the real rp2 target, so getaddrinfo()'s resolved object is required (SPECIFICATION.md F.7 row 1).

    # On this port that object is an opaque sockaddr bytearray rather than a tuple[str, int], but
    # UDPSocket only ever passes addr through untouched, so handing it through is safe despite
    # the mismatched static type.
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
# __init__ configuration: every valid combination, plus single and multiple invalid parameter
# recombinations. These only construct the object - no real socket call happens until _connect()
# runs, so a plain unresolved tuple is safe here (see make_addr() above).
# ---------------------------------------------------------------------------


def test_init_accepts_every_valid_mode_and_conn_tries_combination() -> None:
    for mode in ("client", "server"):
        for conn_tries in (1, 3, 0, -1):  # 0/negative are valid, degenerate "never even try" values
            sock = UDPSocket(("127.0.0.1", 12345), mode=mode, conn_tries=conn_tries)
            assert sock._mode == mode
            assert sock._conn_tries == conn_tries
            assert sock.connected is False
            assert sock._sock is None


def test_init_accepts_a_pre_resolved_bytes_like_addr() -> None:
    # Some platforms' socket.getaddrinfo() returns an opaque sockaddr (bytes/bytearray) rather
    # than a tuple, including this project's own Unix-port test build. This file only passes addr
    # through untouched, so construction must accept that shape too, not just tuple[str, int].
    resolved = socket.getaddrinfo("127.0.0.1", 51500)[0][-1]
    sock = UDPSocket(resolved, mode="server")  # type: ignore[arg-type]
    assert sock._addr == resolved
''', '''def _make_addr() -> tuple[str, int]:  # a fresh loopback port per call, so tests never contend for the same address
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
''')

rep('''    for bad_addr in (None, 12345, "127.0.0.1", ["127.0.0.1", 80], 3.14):''',
    '''    for bad_addr in (None, 12345, "127.0.0.1", ["127.0.0.1", 80], 3.14, b"\\x00" * 16):''')

rep('''def test_init_rejects_non_int_conn_tries() -> None:
    for bad_conn_tries in (None, "3", 1.5, [1]):
        try:
            UDPSocket(("127.0.0.1", 12345), mode="client", conn_tries=bad_conn_tries)  # type: ignore[arg-type]
            raise AssertionError(f"expected TypeError for conn_tries={bad_conn_tries!r}")
        except TypeError:
            pass


''', '')

rep('''        UDPSocket(("bad", "addr", "shape"), mode="bogus", conn_tries=None)  # type: ignore[arg-type]
        raise AssertionError("expected an exception for all-invalid parameters")
    except (TypeError, ValueError):
        pass

    try:
        UDPSocket(12345, mode="client", conn_tries="nope")  # type: ignore[arg-type]
        raise AssertionError("expected an exception for addr+conn_tries both invalid")
    except (TypeError, ValueError):
        pass

    try:
        UDPSocket(None, mode=42, conn_tries=1.5)  # type: ignore[arg-type]
        raise AssertionError("expected an exception for addr+mode+conn_tries all invalid")''',
    '''        UDPSocket(("bad", "addr", "shape"), mode="bogus")  # type: ignore[arg-type]
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
        raise AssertionError("expected an exception for addr+mode both invalid, mode not even a str")''')

s = s.replace("make_addr()", "_make_addr()").replace("__make_addr()", "_make_addr()")
s = s.replace("make_port()", "_make_port()").replace("__make_port()", "_make_port()")
s = s.replace("AdversarialPeer", "_AdversarialPeer").replace("__AdversarialPeer", "_AdversarialPeer")
s = s.replace("unbindable_addr()", "_unbindable_addr()").replace("__unbindable_addr()", "_unbindable_addr()")

open(p, "w").write(s)
