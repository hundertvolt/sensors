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
_CREDENTIALS = ("bench-user", "bench-secret")  # a throwaway broker's only account, not a real secret


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


@pytest.mark.skipif(mqtt_probe.mosquitto_binary() is None, reason="mosquitto is not installed")
def test_a_password_broker_admits_only_a_probe_with_its_credentials(tmp_path: Path) -> None:
    # The bench's password-broker tests rest on both halves: anonymous refused, the right credentials admitted.
    broker = mqtt_probe.Mosquitto(tmp_path, mqtt_probe.free_tcp_port(), users=dict([_CREDENTIALS]))
    broker.start()
    probes = [
        mqtt_probe.Probe("127.0.0.1", broker.port, "anonymous-probe", ()).start(),
        mqtt_probe.Probe("127.0.0.1", broker.port, "wrong-probe", (), username=_CREDENTIALS[0], password=_CREDENTIALS[1][::-1]).start(),
        mqtt_probe.Probe("127.0.0.1", broker.port, "right-probe", (), username=_CREDENTIALS[0], password=_CREDENTIALS[1]).start(),
    ]
    try:
        assert probes[2].wait_connected(5.0), f"the right credentials were refused (log: {broker.log_path.read_text()})"
        assert not probes[0].wait_connected(1.0), "an anonymous probe was admitted"
        assert not probes[1].wait_connected(1.0), "a wrong password was admitted"
    finally:
        for probe in probes:
            probe.close()
        broker.stop()


@pytest.mark.skipif(mqtt_probe.mosquitto_binary() is None, reason="mosquitto is not installed")
@pytest.mark.parametrize(("euid", "stays"), [(0, True), (1000, False)])
def test_a_broker_started_as_root_keeps_root_to_read_its_password_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, euid: int, *, stays: bool) -> None:
    # Root's mosquitto otherwise drops to its own user, which cannot open the password file in a root-only tmp_path.
    monkeypatch.setattr(mqtt_probe.os, "geteuid", lambda: euid)
    broker = mqtt_probe.Mosquitto(tmp_path, mqtt_probe.free_tcp_port(), users=dict([_CREDENTIALS]))
    assert ("user root" in broker.conf.read_text().splitlines()) is stays
