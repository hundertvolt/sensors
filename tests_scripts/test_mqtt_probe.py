"""tests_hardware/mqtt_probe.py's Probe, against a one-connection fake broker: an idle probe keeps its own session
alive. The bench observation of 2026-10-08 saw mosquitto drop a quiet probe every 30-60 s and lose messages."""

import socket
import sys
import threading
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tests_hardware"))

import mqtt_probe

_PINGREQ = b"\xc0\x00"


def _fake_broker(server: socket.socket, seen: "list[bytes]", done: threading.Event) -> None:
    # Answers the CONNECT with a CONNACK, then only records what the probe sends: no traffic ever reaches the probe.
    conn, _addr = server.accept()
    with conn:
        conn.settimeout(0.2)
        conn.recv(256)
        conn.sendall(b"\x20\x02\x00\x00")
        while not done.is_set():
            try:
                data = conn.recv(256)
            except TimeoutError:
                continue
            if not data:
                return
            seen.append(data)


def test_an_idle_probe_pings_within_its_keepalive(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(mqtt_probe, "_PING_EVERY_S", 0.3)
    monkeypatch.setattr(mqtt_probe, "_IO_TIMEOUT_S", 0.1)
    server = socket.create_server(("127.0.0.1", 0))
    seen: list[bytes] = []
    done = threading.Event()
    broker = threading.Thread(target=_fake_broker, args=(server, seen, done), daemon=True)
    broker.start()
    probe = mqtt_probe.Probe("127.0.0.1", server.getsockname()[1], "idle-probe", ()).start()
    try:
        assert probe.wait_connected(5.0)
        assert mqtt_probe.wait_for(lambda: _PINGREQ in b"".join(seen), 3.0), f"an idle probe sent no PINGREQ: {seen!r}"
        assert probe.connects == 1
    finally:
        done.set()
        probe.close()
        server.close()
        broker.join(timeout=2.0)


def test_a_packet_split_across_reads_still_arrives_whole(monkeypatch: pytest.MonkeyPatch) -> None:
    # The idle timeout may only end a wait between packets: one paused mid-packet must still be read to its end.
    monkeypatch.setattr(mqtt_probe, "_IO_TIMEOUT_S", 0.1)
    left, right = socket.socketpair()
    probe = mqtt_probe.Probe("127.0.0.1", 1, "split-probe", ())
    left.settimeout(0.1)
    publish = b"\x30\x07\x00\x03a/bxy"

    def _slow_writer() -> None:
        right.sendall(publish[:4])
        time.sleep(0.35)
        right.sendall(publish[4:])

    writer = threading.Thread(target=_slow_writer, daemon=True)
    writer.start()
    try:
        assert probe._read_packet(left) == (0x30, b"\x00\x03a/bxy")
    finally:
        writer.join(timeout=2.0)
        left.close()
        right.close()
