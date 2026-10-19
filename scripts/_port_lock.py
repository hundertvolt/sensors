"""scripts/_port_lock.sh's product-fixed port lock for CPython runners: the same lock directory, pid and runner files,
owner chain (SENSORS_PORT_LOCK_OWNER, SENSORS_PORT_LOCKS_HELD) and messages. A held port raises PortHeldError, which
the caller turns into exit 1; the next taker takes over the lock of a holder killed before its release ran."""

import contextlib
import os
import re
import shutil
import time
from collections.abc import Callable, Iterator
from pathlib import Path

_ATTEMPTS = 10
_PORT_MAX = 65535
# A holder writes its pid right after its mkdir: a lock without one is waited for this long before it reads as dead.
_PID_WAITS = 20
_PID_WAIT_S = 0.05
_OWNER_VAR = "SENSORS_PORT_LOCK_OWNER"
_HELD_VAR = "SENSORS_PORT_LOCKS_HELD"
_PID = re.compile(r"[1-9][0-9]*")
_takes: dict[Path, int] = {}  # each lock this process took, with its count of unreleased takes


def _alive(pid: str) -> bool:
    # kill(pid, 0) fails with EPERM on another user's live process, which /proc still shows.
    if not _PID.fullmatch(pid):
        return False
    try:
        os.kill(int(pid), 0)
    except PermissionError:
        return True
    except (OSError, OverflowError):
        return Path(f"/proc/{pid}").is_dir()
    return True


def _clear_stale(lock: Path) -> None:
    # Only the taker whose mkdir of <lock>/takeover succeeds moves a dead holder's lock away, and only once its pid is
    # still dead after the wait; the rename makes the lock vanish at once rather than file by file.
    try:
        (lock / "takeover").mkdir()
    except OSError:
        time.sleep(_PID_WAIT_S)
        return
    if _alive(_pid_of(lock)):
        with contextlib.suppress(OSError):
            (lock / "takeover").rmdir()
        return
    stale = lock.with_name(f"{lock.name}.stale.{os.getpid()}")
    try:
        lock.rename(stale)
    except OSError:
        return  # another taker moved it first
    shutil.rmtree(stale, ignore_errors=True)


def _listed(item: str, variable: str) -> bool:
    return item in os.environ.get(variable, "").split()


def _pid_of(lock: Path) -> str:
    # The pid a lock records, waited for while its holder may still be writing it; "" for none.
    for tries in range(_PID_WAITS + 1):
        pid = _read(lock / "pid") or ""
        if _PID.fullmatch(pid) or not lock.is_dir() or tries == _PID_WAITS:
            return pid
        time.sleep(_PID_WAIT_S)
    return ""


def _read(path: Path) -> str | None:
    # A file's text without its trailing newlines, as bash's $(cat) reads it, or None when it cannot be read.
    try:
        return path.read_text(encoding="utf-8").rstrip("\n")
    except (OSError, UnicodeDecodeError):
        return None


def _release(lock: Path) -> None:
    # Removes one lock this process holds once its last take is released, and only while it still records this process.
    count = _takes.get(lock, 0)
    if count > 1:
        _takes[lock] = count - 1
        return
    _takes.pop(lock, None)
    if _read(lock / "pid") != str(os.getpid()):
        return
    released = lock.with_name(f"{lock.name}.released.{os.getpid()}")
    try:
        lock.rename(released)
    except OSError:
        return
    shutil.rmtree(released, ignore_errors=True)


def _take(lock: Path, port: int, runner: str) -> Callable[[], None]:
    # Takes the lock or passes it as the shell library does; returns what undoes this take.
    own = str(os.getpid())
    for _ in range(_ATTEMPTS):
        try:
            lock.mkdir()
        except OSError:
            pid = _pid_of(lock)
            if _alive(pid):
                if pid == own:
                    _takes[lock] = _takes.get(lock, 0) + 1
                    return lambda: _release(lock)
                if _listed(pid, _OWNER_VAR) and _listed(str(port), _HELD_VAR):
                    return lambda: None  # the ancestor that took it releases it
                holder = _read(lock / "runner") or "an unnamed runner"
                message = f"port {port} is held by {holder} (pid {pid}) - run the suites one after the other (CLAUDE.md)"
                raise PortHeldError(message) from None
            if lock.is_dir():
                _clear_stale(lock)
            continue
        try:
            (lock / "runner").write_text(f"{runner}\n", encoding="utf-8")
            (lock / "pid").write_text(f"{own}\n", encoding="utf-8")
        except OSError:
            continue  # the lock moved away while it was written: take it again
        if _read(lock / "pid") != own:
            continue
        before = {name: os.environ.get(name) for name in (_OWNER_VAR, _HELD_VAR)}
        if not _listed(str(port), _HELD_VAR):
            os.environ[_HELD_VAR] = " ".join([*os.environ.get(_HELD_VAR, "").split(), str(port)])
        if not _listed(own, _OWNER_VAR):
            os.environ[_OWNER_VAR] = " ".join([*os.environ.get(_OWNER_VAR, "").split(), own])
        _takes[lock] = 1
        return lambda: _undo(lock, before)
    message = f"port {port}: its lock {lock} could not be taken in {_ATTEMPTS} attempts - if no runner holds the port, remove that directory"
    raise PortHeldError(message)


def _undo(lock: Path, before: dict[str, str | None]) -> None:
    # Releases a take that created the lock and puts the chain back as it was before it.
    _release(lock)
    for name, value in before.items():
        if value is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = value


class PortHeldError(RuntimeError):
    """A live runner outside this process's owner chain holds the port; the message names it."""


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
    release = _take(root / f"sensors-port-{port}.lock", port, runner)
    try:
        yield
    finally:
        release()
