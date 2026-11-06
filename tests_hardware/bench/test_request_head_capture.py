"""Bench capture of real clients' request heads against the device's head guard (Part N's web.max_header_lines and
web.max_head_bytes): the bench host's Python, curl and Playwright Chromium each load a page from a local listener that
keeps each head; the largest is the rows' measurement. The board is only read, by the tier's own fixtures."""

import shutil
import socket
import subprocess
import threading
from typing import TYPE_CHECKING

import _load
import http_client
from harness import REPO_ROOT

if TYPE_CHECKING:
    from collections.abc import Callable

COVERS_TWIN_SCENARIOS: tuple[str, ...] = ()

_SERVE = "asy_webserver_service.py"
_ACCEPT_TIMEOUT_S = 5.0
_CLIENT_TIMEOUT_S = 90.0
_REPLY = b"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nContent-Length: 11\r\nConnection: close\r\n\r\n<p>head</p>"
# One page load in Playwright's Chromium, the repository's own browser dependency (package.json), then the browser closes.
_CHROMIUM = (
    "const {chromium}=require('playwright');"
    "(async()=>{const b=await chromium.launch();const p=await b.newPage();await p.goto(process.argv[1]);await b.close();})()"
    ".catch(e=>{console.error(e);process.exit(1);});"
)


class _Listener:
    # Accepts every connection on an ephemeral loopback port and keeps each request head verbatim, to its blank line.
    def __init__(self) -> None:
        self._sock = socket.socket()
        self._sock.bind(("127.0.0.1", 0))
        self._sock.listen(8)
        self._sock.settimeout(_ACCEPT_TIMEOUT_S)
        self.heads: list[bytes] = []
        self.stop = threading.Event()

    def port(self) -> int:
        port: int = self._sock.getsockname()[1]
        return port

    def serve(self) -> None:
        while not self.stop.is_set():
            try:
                conn, _ = self._sock.accept()
            except TimeoutError:
                continue
            with conn:
                conn.settimeout(_ACCEPT_TIMEOUT_S)
                head = b""
                while b"\r\n\r\n" not in head:
                    chunk = conn.recv(4096)
                    if not chunk:
                        break
                    head += chunk
                self.heads.append(head.split(b"\r\n\r\n")[0] + b"\r\n\r\n")
                conn.sendall(_REPLY)

    def close(self) -> None:
        self._sock.close()


def _clients(port: int) -> "dict[str, Callable[[], object]]":
    url = f"http://127.0.0.1:{port}/"
    clients: dict[str, Callable[[], object]] = {"python": lambda: http_client.fetch("127.0.0.1", port, "GET", "/", timeout_s=_CLIENT_TIMEOUT_S)}
    if shutil.which("curl") is not None:
        clients["curl"] = lambda: subprocess.run(["curl", "-s", "-o", "/dev/null", url], check=True, timeout=_CLIENT_TIMEOUT_S)  # noqa: S603, S607 - a fixed argv, the bench host's own curl
    if shutil.which("node") is not None:
        clients["chromium"] = lambda: subprocess.run(["node", "-e", _CHROMIUM, url], cwd=REPO_ROOT, check=True, timeout=_CLIENT_TIMEOUT_S)  # noqa: S603, S607 - a fixed argv, the bench host's own node
    return clients


def test_real_clients_request_heads_fit_the_devices_head_guard(result_note: "Callable[[str], None]") -> None:
    # Header lines exclude the request line, as the guard counts them; bytes run to the blank line. The listener's
    # 127.0.0.1:<port> Host is a few bytes off the device's own address, inside any margin worth having.
    max_lines = int(_load.src_number(_SERVE, "_MAX_HEADER_LINES"))
    max_bytes = int(_load.src_number(_SERVE, "_MAX_HEAD_BYTES"))
    listener = _Listener()
    thread = threading.Thread(target=listener.serve, daemon=True)
    measured: dict[str, tuple[int, int]] = {}
    try:
        thread.start()
        for name, load in _clients(listener.port()).items():
            start = len(listener.heads)
            load()
            heads = listener.heads[start:]
            assert heads, f"{name} sent no request the listener saw"
            measured[name] = (max(head.count(b"\r\n") - 2 for head in heads), max(len(head) for head in heads))
    finally:
        listener.stop.set()
        thread.join(_ACCEPT_TIMEOUT_S * 2)
        listener.close()
    result_note(", ".join(f"{name}: {lines} header lines, {size} B" for name, (lines, size) in measured.items()) + f" (guard: {max_lines} lines, {max_bytes} B)")
    assert "chromium" in measured, "no browser ran: Playwright's Chromium needs node and the repository's node_modules (toolchain/setup_toolchain.py env)"
    over = {name: value for name, value in measured.items() if value[0] > max_lines or value[1] > max_bytes}
    assert not over, f"a real client's head is past the device's guard of {max_lines} header lines and {max_bytes} B: {over}"
