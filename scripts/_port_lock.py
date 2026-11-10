"""scripts/_port_lock.sh's product-fixed port lock for CPython runners: the same flock(2) on the same file, runner and
pid lines, owner chain (SENSORS_PORT_LOCK_OWNER, SENSORS_PORT_LOCKS_HELD) and messages. A held port raises
PortHeldError, which the caller turns into exit 1; the kernel frees a killed holder's lock with its descriptor."""

import contextlib
import fcntl
import os
from collections.abc import Iterator
from pathlib import Path

_PORT_MAX = 65535
_OWNER_VAR = "SENSORS_PORT_LOCK_OWNER"
_HELD_VAR = "SENSORS_PORT_LOCKS_HELD"


def _listed(item: str, variable: str) -> bool:
    return item in os.environ.get(variable, "").split()


class PortHeldError(RuntimeError):
    """A runner outside this process's owner chain holds the port; the message names it."""


@contextlib.contextmanager
def port_lock(port: int, runner: str) -> Iterator[None]:
    """Holds `port` for `runner` while the block runs; children inherit the chain, so they pass without retaking."""
    if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= _PORT_MAX or not runner:
        message = f"port_lock(port, runner) needs a port 1-65535 and a runner name, not {port!r} {runner!r}"
        raise ValueError(message)
    root = Path(os.environ.get("XDG_RUNTIME_DIR") or "/tmp")  # the shell library's own ${XDG_RUNTIME_DIR:-/tmp}
    if not root.is_dir() or not os.access(root, os.W_OK):
        message = f"port_lock: the lock root {root} is not a writable directory"
        raise ValueError(message)
    path, own = root / f"sensors-port-{port}.flock", str(os.getpid())
    fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o644)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            holder = [*os.pread(fd, 4096, 0).decode("utf-8", "replace").splitlines(), "", ""]
            if holder[1] == own or (_listed(holder[1], _OWNER_VAR) and _listed(str(port), _HELD_VAR)):
                yield  # its own process, or the ancestor that took it, releases it
                return
            message = f"port {port} is held by {holder[0] or 'an unnamed runner'} (pid {holder[1] or 'unknown'}) - run the suites one after the other (CLAUDE.md)"
            raise PortHeldError(message) from None
        os.pwrite(fd, f"{runner}\n{own}\n".encode(), 0)  # in place, as the shell library writes it
        before = {name: os.environ.get(name) for name in (_OWNER_VAR, _HELD_VAR)}
        if not _listed(str(port), _HELD_VAR):
            os.environ[_HELD_VAR] = " ".join([*os.environ.get(_HELD_VAR, "").split(), str(port)])
        if not _listed(own, _OWNER_VAR):
            os.environ[_OWNER_VAR] = " ".join([*os.environ.get(_OWNER_VAR, "").split(), own])
        try:
            yield
        finally:
            for name, value in before.items():
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value
    finally:
        os.close(fd)
