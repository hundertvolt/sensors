"""Workaround for a confirmed MicroPython Unix-port-only crash: `modsocket.c`'s `socket_write()` calls the raw libc `write()` syscall directly (no `MSG_NOSIGNAL`), so writing to a socket whose peer has already reset/closed its end raises the POSIX `SIGPIPE` signal - and since this pinned Unix-port build has no `signal` module (`import signal` raises `ImportError`, confirmed directly), nothing catches it, so the default disposition (terminate the whole process) kills the interpreter outright instead of `write()` returning a normal `OSError(EPIPE)` for MicroPython's own exception machinery to handle. `WebserverService._serve()` (`src/asy_webserver_service.py`) already has an `except OSError` clause specifically anticipating "a genuine, real socket-level failure (e.g. a broken pipe)" - this bug is exactly why that branch could never actually be reached until now: keep-alive (WEBSITE_PLAN.md's session-5 follow-up) is the first thing in this codebase where the server itself writes a *second* response after a request/response cycle already completed, which is also the first time a peer that only ever intended one request (closes its own socket right after reading the first reply, per ordinary HTTP client behavior) is reliably already gone by the time the server's own write() runs.
Confirmed Unix-port-only, the same way as `unix_port_poll_prewarm.py`'s own segfault: real rp2 firmware's socket layer wraps lwIP directly, with no raw libc `write()`/POSIX signal delivery mechanism at all - a send to an already-reset lwIP connection returns a normal lwIP error code, translated into an ordinary `OSError` on that platform already, never a signal. Call `ignore_sigpipe()` as an early statement of any entry point (or test file) that drives real, possibly-peer-closed sockets against `WebserverService` under the Unix port - before that point, any such write is one dropped/reset client away from crashing the whole test run rather than degrading to the single connection's own, already-handled `OSError` path."""

# ffi is a Unix-port-only module (dlopen/FFI has no meaning on a microcontroller with no dynamic
# linking) - never imported by src/ or any real-firmware entry point, matching
# unix_port_poll_prewarm.py's own scoping.
import ffi  # type: ignore[import-not-found]

_SIGPIPE = 13  # POSIX-standard signal number on every platform this project's CI/dev machines run
# on (Linux x86_64/arm64) - confirmed directly, not looked up via a symbolic constant, since the
# `signal` module itself (which would normally provide signal.SIGPIPE) isn't available here either.
_SIG_IGN = 1  # POSIX-standard "ignore this signal" handler constant, same platform scope as above.


def ignore_sigpipe() -> None:
    """Install a process-wide `SIG_IGN` handler for `SIGPIPE` via a direct libc `signal()` FFI call - confirmed directly (a real closed-peer write raises a clean `OSError(EPIPE)` afterward, not a crash) rather than assumed from general POSIX knowledge."""
    libc = ffi.open("libc.so.6")
    signal_fn = libc.func("i", "signal", "ii")
    signal_fn(_SIGPIPE, _SIG_IGN)
