"""Host-side MQTT tools shared by the twin suite and the bench tier (CPython, stdlib only): a mosquitto process the
test owns, on its own port and config, and Probe, a small MQTT 3.1.1 client recording every message it receives, so a
test drives and watches the device's broker traffic with no MQTT CLI tool (SPECIFICATION.md Part A.11)."""

from __future__ import annotations

import shutil
import signal
import socket
import struct
import subprocess
import threading
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

# @tunable l4.mqtt_probe_start_timeout_s = 10.0
_START_TIMEOUT_S = 10.0  # mosquitto listening, or a probe's CONNACK
# @tunable l4.mqtt_probe_retry_s = 0.5
_RETRY_S = 0.5  # a probe's reconnect gap after it lost its broker
# @tunable l4.mqtt_probe_keepalive_s = 20
_KEEPALIVE_S = 20
_PING_EVERY_S = _KEEPALIVE_S / 2
_IO_TIMEOUT_S = 1.0  # one socket read, so a closing probe notices within a second


def free_tcp_port(host: str = "127.0.0.1") -> int:
    with socket.socket() as s:
        s.bind((host, 0))
        return int(s.getsockname()[1])


def mosquitto_binary() -> str | None:
    found = shutil.which("mosquitto")
    if found is not None:
        return found
    for candidate in ("/usr/sbin/mosquitto", "/usr/local/sbin/mosquitto"):
        if shutil.which(candidate) is not None:
            return candidate
    return None


class Mosquitto:
    # A broker this test starts, signals and stops itself: anonymous, no persistence, logging to the work dir.
    def __init__(self, workdir: Path, port: int, bind: str = "127.0.0.1") -> None:
        binary = mosquitto_binary()
        if binary is None:
            raise FileNotFoundError("mosquitto is not installed - toolchain/versions.toml's apt_packages carries it (setup_toolchain.py setup)")
        self.binary = binary
        self.port = port
        self.bind = bind
        workdir.mkdir(parents=True, exist_ok=True)
        self.conf = workdir / f"mosquitto_{port}.conf"
        self.log_path = workdir / f"mosquitto_{port}.log"
        self.conf.write_text(
            f"listener {port} {bind}\nallow_anonymous true\npersistence false\nconnection_messages true\n"
            "log_type error\nlog_type warning\nlog_type notice\nlog_type information\n",
        )
        self.proc: subprocess.Popen[bytes] | None = None

    def is_running(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def send(self, sig: int) -> None:
        if self.is_running() and self.proc is not None:
            self.proc.send_signal(sig)

    def start(self) -> None:
        log = open(self.log_path, "ab")
        self.proc = subprocess.Popen([self.binary, "-c", str(self.conf)], stdout=log, stderr=subprocess.STDOUT)  # noqa: S603 - fixed argv
        log.close()
        deadline = time.monotonic() + _START_TIMEOUT_S
        while time.monotonic() < deadline:
            try:
                socket.create_connection((self.bind, self.port), 0.5).close()
            except OSError:
                time.sleep(0.1)
            else:
                return
        raise TimeoutError(f"mosquitto did not listen on {self.bind}:{self.port} within {_START_TIMEOUT_S}s (log: {self.log_path})")

    def stop(self, sig: int = signal.SIGTERM) -> None:
        if self.proc is None:
            return
        if self.proc.poll() is None:
            self.proc.send_signal(signal.SIGCONT)  # a stalled broker cannot act on its signal otherwise
            self.proc.send_signal(sig)
            try:
                self.proc.wait(10)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait()
        self.proc = None


@dataclass(frozen=True)
class Message:
    at: float  # time.monotonic() of its arrival
    topic: str
    payload: bytes
    retained: bool


def _str(data: bytes) -> bytes:
    return struct.pack("!H", len(data)) + data


def _length(value: int) -> bytes:
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        out.append(byte | 0x80 if value else byte)
        if not value:
            return bytes(out)


def _packet(first: int, body: bytes) -> bytes:
    return bytes([first]) + _length(len(body)) + body


class Probe:
    # One clean-session MQTT connection whose reader thread records every PUBLISH; it reconnects after a loss
    # until close(). With the device's own client id it is the takeover a duplicate client causes.
    def __init__(self, host: str, port: int, client_id: str, subscribe: tuple[str, ...] = ("#",)) -> None:
        self.host = host
        self.port = port
        self.client_id = client_id
        self.subscribe = subscribe
        self.messages: list[Message] = []
        self.connects = 0
        self._lock = threading.Lock()
        self._sock: socket.socket | None = None
        self._send_lock = threading.Lock()
        self._closed = threading.Event()
        self._connected = threading.Event()
        self._pid = 0
        self._thread = threading.Thread(target=self._run, daemon=True)

    def _connect_once(self) -> socket.socket:
        sock = socket.create_connection((self.host, self.port), _START_TIMEOUT_S)
        sock.settimeout(_START_TIMEOUT_S)
        body = _str(b"MQTT") + bytes([4, 0x02]) + struct.pack("!H", _KEEPALIVE_S) + _str(self.client_id.encode())
        sock.sendall(_packet(0x10, body))
        first, payload = self._read_packet(sock)
        if first != 0x20 or len(payload) != 2 or payload[1] != 0:
            sock.close()
            raise ConnectionError(f"CONNACK refused or malformed: {first:#x} {payload!r}")
        filters = b"".join(_str(f.encode()) + b"\x01" for f in self.subscribe)
        if filters:
            sock.sendall(_packet(0x82, struct.pack("!H", self._next_pid()) + filters))
        sock.settimeout(_IO_TIMEOUT_S)
        return sock

    def _next_pid(self) -> int:
        self._pid = self._pid % 65535 + 1
        return self._pid

    def _on_packet(self, sock: socket.socket, first: int, body: bytes) -> None:
        if first & 0xF0 != 0x30:
            return
        qos = (first >> 1) & 3
        tlen = struct.unpack("!H", body[:2])[0]
        topic = body[2 : 2 + tlen].decode(errors="replace")
        start = 2 + tlen
        if qos:
            self._send(sock, _packet(0x40, body[start : start + 2]))
            start += 2
        with self._lock:
            self.messages.append(Message(time.monotonic(), topic, body[start:], bool(first & 1)))

    def _read_exact(self, sock: socket.socket, n: int) -> bytes:
        data = b""
        while len(data) < n:
            try:
                chunk = sock.recv(n - len(data))
            except TimeoutError:
                if self._closed.is_set():
                    raise ConnectionError("probe closed") from None
                continue
            if not chunk:
                raise ConnectionError("broker closed the connection")
            data += chunk
        return data

    def _read_packet(self, sock: socket.socket) -> tuple[int, bytes]:
        first = self._read_exact(sock, 1)[0]
        value = 0
        shift = 0
        while True:
            byte = self._read_exact(sock, 1)[0]
            value |= (byte & 0x7F) << shift
            shift += 7
            if not byte & 0x80:
                break
        return first, self._read_exact(sock, value) if value else b""

    def _run(self) -> None:
        while not self._closed.is_set():
            try:
                sock = self._connect_once()
            except OSError:
                self._closed.wait(_RETRY_S)
                continue
            self._sock = sock
            self.connects += 1
            self._connected.set()
            last_ping = time.monotonic()
            try:
                while not self._closed.is_set():
                    if time.monotonic() - last_ping > _PING_EVERY_S:
                        self._send(sock, b"\xc0\x00")
                        last_ping = time.monotonic()
                    try:
                        first, body = self._read_packet(sock)
                    except TimeoutError:
                        continue
                    self._on_packet(sock, first, body)
            except OSError:
                pass
            finally:
                self._connected.clear()
                self._sock = None
                sock.close()
            self._closed.wait(_RETRY_S)

    def _send(self, sock: socket.socket, data: bytes) -> None:
        with self._send_lock:
            sock.sendall(data)

    def close(self) -> None:
        self._closed.set()
        sock = self._sock
        if sock is not None:
            try:
                self._send(sock, b"\xe0\x00")
            except OSError:
                pass
        self._thread.join(timeout=5)

    def is_connected(self) -> bool:
        return self._connected.is_set()

    def publish(self, topic: str, payload: bytes, qos: int = 0, *, retain: bool = False) -> bool:
        # True when the packet went out; a lost connection answers False rather than raising.
        sock = self._sock
        if sock is None:
            return False
        body = _str(topic.encode()) + (struct.pack("!H", self._next_pid()) if qos else b"") + payload
        try:
            self._send(sock, _packet(0x30 | (qos << 1) | (1 if retain else 0), body))
        except OSError:
            return False
        return True

    def received(self, topic: str | None = None) -> list[Message]:
        with self._lock:
            return [m for m in self.messages if topic is None or m.topic == topic]

    def start(self) -> Probe:
        self._thread.start()
        return self

    def wait_connected(self, timeout_s: float = _START_TIMEOUT_S) -> bool:
        return self._connected.wait(timeout_s)


def wait_for(predicate: Callable[[], bool], timeout_s: float, poll_s: float = 0.25) -> bool:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(poll_s)
    return predicate()
