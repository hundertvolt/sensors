"""Bench tier for the MQTT client (SPECIFICATION.md Part A.12): the real client on the bench board against a mosquitto
on this host's own LAN address, through broker faults, path loss, a client-id takeover, inbound floods, an AP outage, a
reboot, the status and session settings at the firmware's gc threshold, then the faults at the gc default (I.4(e))."""

import contextlib
import itertools
import json
import math
import signal
import socket
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import _load
import http_client
import pytest
import serial
from error_log_helpers import assert_no_task_ended, code, errcount_entry, get_errcount, reset_all_error_logs
from harness import DEVICE_SCRIPTS_DIR, MEMORY_ERROR_MARKERS, REPO_ROOT, device_toml, kick_then_reset, parse_facts, recover_by_reset, restore_board_to_serving, wait_for_script_server, wait_until
from mqtt_probe import Mosquitto, Probe, session_present, wait_for

from buildgen.definitions import definitions_for_toml

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from bench_control import BenchBridge
    from harness import Board
    from http_client import JSONObject

COVERS_TWIN_SCENARIOS: tuple[str, ...] = ("ci_suite._run_14_mqtt_broker_faults",)

_BROKER_PORT = 18883  # fixed, so every iptables rule names it; a distribution mosquitto keeps 1883 to itself
_AUTH_PORT = 18884  # the password broker's, beside the anonymous one
_AUTH_DEVICE = ("bench-device", "bench-device-pass")  # a throwaway broker's accounts, not real secrets
_AUTH_OBSERVER = ("bench-observer", "bench-observer-pass")
_STALL_OFFSETS_S = (1.0, 5.0, 9.0, 13.0)  # after a connect, across two of the 10 s publish rounds
_OBSERVER_ID = "bench-observer"
_SLOT_PAYLOAD_MAX = 384  # mqtt.out_payload_max: a larger measurement object would be dropped, counted

_PUB_INTERVAL_S = int(str(_load.field_schema("asy_mqtt_client.py", "MQTTPubInterval")[2]))  # its minimum: the checks wait least
_CONNECT_WAIT_S = 90.0  # a connect once the fault is gone, the bench's WiFi latency included
# @tunable mqtt.backoff_max_ms = 60.0
_BACKOFF_CAP_S = 60.0  # the reconnect wait the earlier faults' short sessions may have grown to
_STEP_WAIT_S = 20.0  # one message's round trip through the broker and the device's status
_OUTAGE_S = 5.0  # the killed broker's downtime: the client's first attempts fail inside it
_DETECT_BOUND_S = 35.0  # the next publish round's ping + mqtt.response_timeout_ms (20 s), plus ticks and WiFi latency
_DETECT_WAIT_S = 60.0
_TAKEOVER_S = 20.0
_TAKEOVER_MAX_CONNECTS = 5  # the doubling backoff allows about four retakes in the window; the minimum would allow ten
_FLOOD_MESSAGES = 3000  # about 200 KB through the device's 1 KB receive buffer
_QOS1_BURST = 500  # below mosquitto's default 1000-message queue, so the broker delivers every one
_OVERSIZE_BYTES = 4096  # four times mqtt.rx_buf_bytes
_REST_BUDGET_S = 15.0
_AP_OUTAGE_S = 30.0
_AP_RECONNECT_TIMEOUT_S = 240.0  # past the WiFi service's 60 s retry after a loss, twice
_AP_MAX_FAILED_ATTEMPTS = 6  # attempts only before the WiFi service reports the loss, then the backoff's 2+4+...+64 s
_REBOOT_WAIT_S = 180.0
_SCRIPT_TIMEOUT_S = 600.0  # the device script's 420 s window, its boot and mpremote's own overhead
_DRIVER_JOIN_S = 60.0
_POLL_S = 1.0
_REFUSED_WINDOW_S = 40.0  # failed attempts are counted over it: about five at the 2 s doubling backoff
_REFUSED_MAX_ATTEMPTS = 6  # one over the doubling backoff's count in the window; the minimum alone would allow about 20
_STALL_PHASE_TOLERANCE_S = 1.5  # the keeper's 100 ms tick, the console's USB latency and this host's scheduling
_STATUS_TOPIC = "bench/availability"  # a status topic outside the device's own tree (owner, 2026-10-13: 'Any full topic')

_E_CONNECT = code("E", "MQTT_CONNECT")
# What this module's broker faults may log: a failed attempt, a lost connection, a missed PINGRESP, a stalled drain and
# the short-session warning; each fault test names them in provokes_log, a protocol, refusal or allocation code fails.
_EXPECTED_MQTT_CODES = {_E_CONNECT, code("E", "MQTT_LOST"), code("E", "MQTT_NO_PINGRESP"), code("E", "MQTT_STALLED"), code("W", "MQTT_SHORT_SESSIONS")}


@dataclass(frozen=True)
class MqttBench:
    dut_ip: str
    host_ip: str
    broker: Mosquitto
    observer: Probe
    base: str
    client_id: str


def _sensor_names(device: str) -> list[str]:
    # The modules the client publishes: every sensor, the same set as the website's measurements cards.
    definitions = json.loads(json.dumps(definitions_for_toml(device_toml(device), REPO_ROOT / "src")))
    section = next(s for s in definitions["sections"] if s["key"] == "measurements")
    return [str(g["key"]) for g in section["groups"]]


def _host_ip_toward(dut_ip: str) -> str:
    # This host's own address on the DUT's network: the source the kernel picks to reach it, br0's on the bench.
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.connect((dut_ip, 80))
        return str(s.getsockname()[0])


def _networking(dut_ip: str) -> "JSONObject":
    return _load.as_object(_load.get_object(dut_ip, "/status", _REST_BUDGET_S).get("networking"), "GET /status networking")


def _count(dut_ip: str, key: str) -> int:
    value = _networking(dut_ip).get(key)
    return value if isinstance(value, int) else -1


def _wait_connected(dut_ip: str, what: str, timeout_s: float = _CONNECT_WAIT_S + _BACKOFF_CAP_S) -> float:
    # Seconds until GET /status shows the client connected; raises with `what` on a timeout.
    started = time.monotonic()
    wait_until(lambda: _networking(dut_ip).get("MQTTConnected") is True, timeout_s=timeout_s, poll_interval_s=_POLL_S, description=f"the MQTT client connected {what}")
    return time.monotonic() - started


def _wait_count_above(dut_ip: str, key: str, floor: int, timeout_s: float, what: str) -> float:
    started = time.monotonic()
    wait_until(lambda: _count(dut_ip, key) > floor, timeout_s=timeout_s, poll_interval_s=_POLL_S, description=what)
    return time.monotonic() - started


def _strict_json(payload: bytes) -> object:
    # json.loads() accepts NaN and Infinity, which the device writes as null (Part A.12).
    def refuse(token: str) -> None:
        raise ValueError(f"non-finite JSON token {token}")

    return json.loads(payload, parse_constant=refuse)


def _mqtt_history(dut_ip: str) -> "list[JSONObject]":
    return [h for h in errcount_entry(get_errcount(dut_ip), "MQTT")["history"] if h.get("type") in ("E", "W")]


def _assert_mqtt_logged_only(dut_ip: str, context: str) -> None:
    unexpected = [h for h in _mqtt_history(dut_ip) if h.get("num") not in _EXPECTED_MQTT_CODES]
    assert not unexpected, f"{context}: the MQTT log holds {unexpected!r}, outside the expected {sorted(_EXPECTED_MQTT_CODES)}"


def _enable_mqtt(dut_ip: str, host_ip: str) -> None:
    # This module's shared prerequisite write (config_MQTT.cfg): every test below needs a client pointed at this
    # host's broker. Unchanged values write nothing, so a rerun on an enabled board spends no flash.
    res = http_client.fetch(dut_ip, 80, "PUT", "/networking", {"MQTTEnable": True, "MQTTHost": host_ip, "MQTTPort": _BROKER_PORT, "MQTTPubInterval": _PUB_INTERVAL_S}, timeout_s=_REST_BUDGET_S)
    _assert_taken(res, "enabling the MQTT client")


def _disable_mqtt(dut_ip: str) -> None:
    # Its undo, so the bench tests after this module see the old baseline: the client says offline and idles.
    res = http_client.fetch(dut_ip, 80, "PUT", "/networking", {"MQTTEnable": False}, timeout_s=_REST_BUDGET_S)
    _assert_taken(res, "disabling the MQTT client")


def _assert_taken(res: "http_client.HttpResponse", what: str) -> None:
    # A PUT /networking answer every field of which was taken; the bodies stay literal at the call, for the wear guard.
    result = _load.as_object(res.json().get("result"), f"{what}: the PUT's result") if res.status_code == 200 else {}
    assert result and all(v in ("Valid", "Unchanged") for v in result.values()), f"{what} was refused: {res.status_code} {res.body!r}"


def _drive_faults(m: MqttBench, stop: threading.Event, steps: list[str]) -> None:
    # The host half of the default-gc test: one pass of the broker faults against the script's own server.
    def mqtt_connected() -> bool | None:
        # None when the status read itself failed, so a REST hiccup never reads as a lost session.
        try:
            return _networking(m.dut_ip).get("MQTTConnected") is True
        except (OSError, AssertionError, http_client.HTTP_ERROR):
            return None

    def connected() -> bool:
        return mqtt_connected() is True

    def step(name: str, condition: "Callable[[], bool]", timeout_s: float) -> bool:
        ok = not stop.is_set() and wait_for(lambda: stop.is_set() or condition(), timeout_s) and not stop.is_set()
        steps.append(name if ok else f"{name}: timed out")
        return ok

    if not wait_for_script_server(m.dut_ip, stop) or not step("connected", connected, _CONNECT_WAIT_S):
        return
    m.broker.stop(signal.SIGKILL)
    stop.wait(_OUTAGE_S)
    m.broker.start()
    if not step("reconnected after kill", connected, _CONNECT_WAIT_S + _BACKOFF_CAP_S):
        return
    m.broker.send(signal.SIGSTOP)
    detected = step("stall detected", lambda: mqtt_connected() is False, _DETECT_WAIT_S)
    m.broker.send(signal.SIGCONT)
    if not detected or not step("reconnected after stall", connected, _CONNECT_WAIT_S + _BACKOFF_CAP_S):
        return
    for i in range(_FLOOD_MESSAGES):
        m.observer.publish(f"{m.base}/cmd/flood", b"%040d" % i)
    for i in range(_QOS1_BURST):
        m.observer.publish(f"{m.base}/cmd/qos1", b"%08d" % i, qos=1)
    if not step("connected after floods", connected, _STEP_WAIT_S):
        return
    thief = Probe(m.host_ip, _BROKER_PORT, m.client_id, ()).start()
    stop.wait(_TAKEOVER_S)
    thief.close()
    if step("reconnected after takeover", connected, _CONNECT_WAIT_S + _BACKOFF_CAP_S):
        steps.append("done")


@contextlib.contextmanager
def _password_broker(m: MqttBench, workdir: Path, password: str) -> "Iterator[tuple[Mosquitto, Probe]]":
    # A second broker that admits only its two accounts, the device pointed at it with `password`; this test owns the
    # writes and their undo (the anonymous broker's port and no credentials).
    broker = Mosquitto(workdir, _AUTH_PORT, bind=m.host_ip, users=dict([_AUTH_DEVICE, _AUTH_OBSERVER]))
    broker.start()
    observer = Probe(m.host_ip, _AUTH_PORT, _OBSERVER_ID + "-auth", (f"{m.base}/#",), username=_AUTH_OBSERVER[0], password=_AUTH_OBSERVER[1]).start()
    try:
        assert observer.wait_connected(), f"the bench's own account was refused (log: {broker.log_path})"
        res = http_client.fetch(m.dut_ip, 80, "PUT", "/networking", {"MQTTPort": _AUTH_PORT, "MQTTUser": _AUTH_DEVICE[0], "MQTTPW": password}, timeout_s=_REST_BUDGET_S)
        _assert_taken(res, "the credentials")
        yield broker, observer
    finally:
        restore = http_client.fetch(m.dut_ip, 80, "PUT", "/networking", {"MQTTPort": _BROKER_PORT, "MQTTUser": "", "MQTTPW": ""}, timeout_s=_REST_BUDGET_S)
        observer.close()
        broker.stop()
        assert restore.status_code == 200, f"restoring the anonymous broker failed: {restore.body!r}"


def _broker_attempts_from(broker: Mosquitto, dut_ip: str) -> int:
    return broker.log_path.read_text(errors="replace").count(f"New connection from {dut_ip}:")


def _mqtt_counter(dut_ip: str) -> int:
    return errcount_entry(get_errcount(dut_ip), "MQTT")["counter"]


class _Console:
    # The board's console lines, each with this host's monotonic time, as _console() reads them.
    def __init__(self) -> None:
        self.lines: list[tuple[float, str]] = []

    def first_after(self, since: float, text: str, timeout_s: float) -> float | None:
        def hit() -> float | None:
            return next((t for t, line in list(self.lines) if t >= since and text in line), None)

        wait_for(lambda: hit() is not None, timeout_s, 0.05)
        return hit()


@contextlib.contextmanager
def _console(device: str) -> "Iterator[_Console]":
    # The board's console read passively while a test runs; its reader stopped and joined, its port closed, on every path.
    console = _Console()
    stop = threading.Event()
    with serial.Serial(device, 115200, timeout=0.2) as port:

        def read() -> None:
            while not stop.is_set():
                raw = port.readline()
                if raw:
                    console.lines.append((time.monotonic(), raw.decode("utf-8", errors="replace").rstrip("\r\n")))

        reader = threading.Thread(target=read, name="mqtt-console")
        try:
            reader.start()
            yield console
        finally:
            stop.set()
            reader.join(timeout=2.0)


@pytest.fixture(scope="module")
def mqtt_bench(bench_device_name: str, dut_ip: str, tmp_path_factory: pytest.TempPathFactory) -> "Iterator[MqttBench]":
    if "MQTTState" not in _networking(dut_ip):
        pytest.fail(f"this firmware carries no MQTT client - the bench device {bench_device_name} wires none, or its image predates it (tests_hardware/README.md)")
    reset_all_error_logs(dut_ip, "mqtt_bench")  # the verbatim /status goes to the run's evidence first
    host_ip = _host_ip_toward(dut_ip)
    broker = Mosquitto(tmp_path_factory.mktemp("mqtt"), _BROKER_PORT, bind=host_ip)
    observer: Probe | None = None
    try:
        broker.start()
        _enable_mqtt(dut_ip, host_ip)
        cfg = _load.get_object(dut_ip, "/networking", _REST_BUDGET_S)
        client_id = str(cfg["MQTTClientId"])
        observer = Probe(host_ip, _BROKER_PORT, _OBSERVER_ID, (f"{cfg['MQTTPrefix']}/{client_id}/#",)).start()
        assert observer.wait_connected(), f"the bench's own observer could not connect to {host_ip}:{_BROKER_PORT} (log: {broker.log_path})"
        yield MqttBench(dut_ip, host_ip, broker, observer, f"{cfg['MQTTPrefix']}/{client_id}", client_id)
    finally:
        try:
            _disable_mqtt(dut_ip)
        finally:
            if observer is not None:
                observer.close()
            broker.stop()
            print(f"[HW] mosquitto log: {broker.log_path}")


def test_the_client_connects_and_announces_itself_online(mqtt_bench: MqttBench, result_note: "_load.Note") -> None:
    m = mqtt_bench
    took = _wait_connected(m.dut_ip, "after the enabling PUT")
    status = _networking(m.dut_ip)
    assert status["MQTTBroker"] == m.host_ip, f"connected to {status['MQTTBroker']!r}, not this host's {m.host_ip}"
    online = wait_for(lambda: any(msg.payload == b"online" for msg in m.observer.received(f"{m.base}/status")), _STEP_WAIT_S)
    assert online, f"no online on {m.base}/status: {m.observer.received()!r}"
    result_note(f"connected within {took:.1f}s of the first poll; MQTTState {status['MQTTState']!r}")


def test_every_sensor_publishes_strict_json_on_its_own_topic(mqtt_bench: MqttBench, bench_device_name: str, result_note: "_load.Note") -> None:
    m = mqtt_bench
    names = _sensor_names(bench_device_name)
    arrived = wait_for(lambda: all(m.observer.received(f"{m.base}/measurements/{n}") for n in names), _PUB_INTERVAL_S * 3)
    assert arrived, f"not every sensor published within three intervals: {[n for n in names if not m.observer.received(f'{m.base}/measurements/{n}')]}"
    meas = _load.get_object(m.dut_ip, "/measurements", _REST_BUDGET_S)
    largest = 0
    for name in names:
        payload = m.observer.received(f"{m.base}/measurements/{name}")[-1].payload
        largest = max(largest, len(payload))
        parsed = _strict_json(payload)
        keys = set(_load.as_object(meas.get(name), f"GET /measurements {name}"))
        assert isinstance(parsed, dict) and set(parsed) == keys, f"{name}: {parsed!r} does not carry /measurements' keys {sorted(keys)}"
    published = {msg.topic.rsplit("/", 1)[-1] for msg in m.observer.received() if msg.topic.startswith(f"{m.base}/measurements/")}
    assert published == set(names), f"published {sorted(published)}, expected the sensors {names}"
    assert _count(m.dut_ip, "MQTTTxDropped") == 0, f"messages were dropped: {_networking(m.dut_ip)!r}"
    assert largest <= _SLOT_PAYLOAD_MAX
    result_note(f"largest measurement payload {largest} B of the {_SLOT_PAYLOAD_MAX} B slot")


def test_an_inbound_command_is_received_and_shown(mqtt_bench: MqttBench) -> None:
    m = mqtt_bench
    _wait_connected(m.dut_ip, "before the command")
    before = _count(m.dut_ip, "MQTTRxMsgs")
    assert m.observer.publish(f"{m.base}/cmd/bench", b"hello", qos=1)
    wait_until(lambda: _networking(m.dut_ip).get("MQTTLastRxTopic") == f"{m.base}/cmd/bench", timeout_s=_STEP_WAIT_S, poll_interval_s=_POLL_S, description="the command topic shown in GET /status")
    assert _count(m.dut_ip, "MQTTRxMsgs") > before


@pytest.mark.provokes_log(
    "the killed broker's lost connection, the attempts while it is down and a shortened session",
    ("MQTT", "E", "MQTT_CONNECT"),
    ("MQTT", "E", "MQTT_LOST"),
    ("MQTT", "E", "MQTT_NO_PINGRESP"),
    ("MQTT", "E", "MQTT_STALLED"),
    ("MQTT", "W", "MQTT_SHORT_SESSIONS"),
)
def test_a_killed_broker_is_reconnected_after_its_restart(mqtt_bench: MqttBench, result_note: "_load.Note") -> None:
    m = mqtt_bench
    _wait_connected(m.dut_ip, "before the kill")
    connects = _count(m.dut_ip, "MQTTConnects")
    m.broker.stop(signal.SIGKILL)
    time.sleep(_OUTAGE_S)  # an absence: no probe can observe the broker being gone longer
    m.broker.start()
    took = _wait_count_above(m.dut_ip, "MQTTConnects", connects, _CONNECT_WAIT_S + _BACKOFF_CAP_S, "a new connection after the broker restarted")
    assert m.observer.wait_connected(), "the observer did not reconnect to the restarted broker"
    _assert_mqtt_logged_only(m.dut_ip, "broker kill")
    result_note(f"reconnected {took:.1f}s after the restart (outage {_OUTAGE_S:g}s)")


@pytest.mark.provokes_log(
    "the stalled broker's missed PINGRESP or stalled drain, and the reconnect's attempts",
    ("MQTT", "E", "MQTT_CONNECT"),
    ("MQTT", "E", "MQTT_LOST"),
    ("MQTT", "E", "MQTT_NO_PINGRESP"),
    ("MQTT", "E", "MQTT_STALLED"),
    ("MQTT", "W", "MQTT_SHORT_SESSIONS"),
)
def test_a_stalled_broker_is_detected_by_the_pingresp_deadline(mqtt_bench: MqttBench, result_note: "_load.Note") -> None:
    m = mqtt_bench
    _wait_connected(m.dut_ip, "before the stall")
    pings = _count(m.dut_ip, "MQTTPingTimeouts")
    m.broker.send(signal.SIGSTOP)
    try:
        took = _wait_count_above(m.dut_ip, "MQTTPingTimeouts", pings, _DETECT_WAIT_S, "the PINGRESP deadline ending the stalled connection")
    finally:
        m.broker.send(signal.SIGCONT)
    assert took <= _DETECT_BOUND_S, f"a stalled broker took {took:.1f}s to detect, past {_DETECT_BOUND_S:g}s"
    back = _wait_connected(m.dut_ip, "once the stalled broker resumed")
    result_note(f"stall detected in {took:.1f}s; reconnected {back:.1f}s after the resume")


@pytest.mark.provokes_log(
    "the dropped path's missed PINGRESP or stalled drain, and the attempts until it is restored",
    ("MQTT", "E", "MQTT_CONNECT"),
    ("MQTT", "E", "MQTT_LOST"),
    ("MQTT", "E", "MQTT_NO_PINGRESP"),
    ("MQTT", "E", "MQTT_STALLED"),
    ("MQTT", "W", "MQTT_SHORT_SESSIONS"),
)
def test_a_silent_path_loss_is_detected_and_recovered(mqtt_bench: MqttBench, bench: "BenchBridge", result_note: "_load.Note") -> None:
    # The case lwIP alone never sees: no FIN, no RST, both directions dropped on this host. WiFi and REST stay up.
    m = mqtt_bench
    _wait_connected(m.dut_ip, "before the path loss")
    teardowns = _count(m.dut_ip, "MQTTTeardowns")
    bench.block_tcp_port_from(m.dut_ip, _BROKER_PORT)
    try:
        took = _wait_count_above(m.dut_ip, "MQTTTeardowns", teardowns, _DETECT_WAIT_S, "the client ending a connection whose path is gone")
        assert http_client.fetch(m.dut_ip, 80, "GET", "/status", timeout_s=_REST_BUDGET_S).status_code == 200
    finally:
        bench.unblock_tcp_port_from(m.dut_ip, _BROKER_PORT)
    assert took <= _DETECT_BOUND_S, f"a silent path loss took {took:.1f}s to detect, past {_DETECT_BOUND_S:g}s"
    reason = _networking(m.dut_ip).get("MQTTLastReason")
    back = _wait_connected(m.dut_ip, "once the path was restored")
    result_note(f"path loss detected in {took:.1f}s ({reason!r}); reconnected {back:.1f}s after the restore")


@pytest.mark.provokes_log(
    "the reset path's lost connection and its refused attempts",
    ("MQTT", "E", "MQTT_CONNECT"),
    ("MQTT", "E", "MQTT_LOST"),
    ("MQTT", "E", "MQTT_NO_PINGRESP"),
    ("MQTT", "E", "MQTT_STALLED"),
    ("MQTT", "W", "MQTT_SHORT_SESSIONS"),
)
def test_a_reset_path_ends_the_connection_and_attempts_stay_bounded(mqtt_bench: MqttBench, bench: "BenchBridge", result_note: "_load.Note") -> None:
    m = mqtt_bench
    _wait_connected(m.dut_ip, "before the reset path")
    connects, teardowns = _count(m.dut_ip, "MQTTConnects"), _count(m.dut_ip, "MQTTTeardowns")
    bench.block_tcp_port_from(m.dut_ip, _BROKER_PORT, reset=True)
    try:
        took = _wait_count_above(m.dut_ip, "MQTTTeardowns", teardowns, _DETECT_WAIT_S, "the client ending a connection answered with resets")
        time.sleep(_TAKEOVER_S)  # an absence: refused attempts must not turn into connections
        assert _count(m.dut_ip, "MQTTConnects") == connects, "a connection succeeded through a path answering every segment with a reset"
    finally:
        bench.unblock_tcp_port_from(m.dut_ip, _BROKER_PORT, reset=True)
    back = _wait_connected(m.dut_ip, "once the resets stopped")
    result_note(f"reset path ended the connection in {took:.1f}s; reconnected {back:.1f}s after the restore")


@pytest.mark.provokes_log(
    "each takeover by the duplicate ends a short session",
    ("MQTT", "E", "MQTT_CONNECT"),
    ("MQTT", "E", "MQTT_LOST"),
    ("MQTT", "E", "MQTT_NO_PINGRESP"),
    ("MQTT", "E", "MQTT_STALLED"),
    ("MQTT", "W", "MQTT_SHORT_SESSIONS"),
)
def test_a_duplicate_client_id_is_bounded_by_the_backoff(mqtt_bench: MqttBench, result_note: "_load.Note") -> None:
    m = mqtt_bench
    _wait_connected(m.dut_ip, "before the takeover")
    connects, teardowns = _count(m.dut_ip, "MQTTConnects"), _count(m.dut_ip, "MQTTTeardowns")
    thief = Probe(m.host_ip, _BROKER_PORT, m.client_id, ()).start()
    try:
        time.sleep(_TAKEOVER_S)  # the window both clients fight in; the device's retakes are what is counted
    finally:
        thief.close()
    retakes = _count(m.dut_ip, "MQTTConnects") - connects
    assert _count(m.dut_ip, "MQTTTeardowns") > teardowns, "the duplicate client id never took the session over"
    assert retakes <= _TAKEOVER_MAX_CONNECTS, f"{retakes} retakes in {_TAKEOVER_S:g}s: the backoff did not grow across short sessions"
    back = _wait_connected(m.dut_ip, "once the duplicate client left")
    _assert_mqtt_logged_only(m.dut_ip, "client-id takeover")
    result_note(f"{retakes} retakes in {_TAKEOVER_S:g}s against {thief.connects} by the duplicate; reconnected {back:.1f}s after it left")


def test_an_inbound_flood_leaves_rest_serving_and_the_session_up(mqtt_bench: MqttBench, result_note: "_load.Note") -> None:
    # A QoS 1 marker closes the flood: the broker may shed QoS 0 for a slow reader, never the marker, so the
    # marker arriving proves the device read through everything the broker passed on, framing intact.
    m = mqtt_bench
    _wait_connected(m.dut_ip, "before the flood")
    received, teardowns = _count(m.dut_ip, "MQTTRxMsgs"), _count(m.dut_ip, "MQTTTeardowns")
    latencies: list[float] = []
    for i in range(_FLOOD_MESSAGES):
        assert m.observer.publish(f"{m.base}/cmd/flood", b"%040d" % i), f"the observer lost its broker at message {i}"
        if i % (_FLOOD_MESSAGES // 10) == 0:
            started = time.monotonic()
            assert http_client.fetch(m.dut_ip, 80, "GET", "/status", timeout_s=_REST_BUDGET_S).status_code == 200
            latencies.append(time.monotonic() - started)
    assert m.observer.publish(f"{m.base}/cmd/flood-end", b"end", qos=1)
    wait_until(lambda: _networking(m.dut_ip).get("MQTTLastRxTopic") == f"{m.base}/cmd/flood-end", timeout_s=_DETECT_WAIT_S, poll_interval_s=_POLL_S, description="the flood's closing marker received")
    taken = _count(m.dut_ip, "MQTTRxMsgs") - received
    assert _count(m.dut_ip, "MQTTTeardowns") == teardowns, f"the flood ended the session: {_networking(m.dut_ip)!r}"
    result_note(f"{taken} of {_FLOOD_MESSAGES + 1} messages taken; GET /status under the flood: max {max(latencies):.2f}s, median {sorted(latencies)[len(latencies) // 2]:.2f}s")


def test_an_inbound_qos1_burst_is_acknowledged_in_full(mqtt_bench: MqttBench, result_note: "_load.Note") -> None:
    m = mqtt_bench
    _wait_connected(m.dut_ip, "before the QoS 1 burst")
    received, teardowns = _count(m.dut_ip, "MQTTRxMsgs"), _count(m.dut_ip, "MQTTTeardowns")
    started = time.monotonic()
    sent = sum(1 for i in range(_QOS1_BURST) if m.observer.publish(f"{m.base}/cmd/qos1", b"%08d" % i, qos=1))
    assert sent == _QOS1_BURST, f"the observer sent {sent} of {_QOS1_BURST}"
    wait_until(lambda: _count(m.dut_ip, "MQTTRxMsgs") - received >= _QOS1_BURST, timeout_s=_DETECT_WAIT_S, poll_interval_s=_POLL_S, description="every QoS 1 message delivered and acknowledged")
    took = time.monotonic() - started
    assert _count(m.dut_ip, "MQTTRxMsgs") - received == _QOS1_BURST, "a QoS 1 message was delivered twice: a PUBACK went missing"
    assert _count(m.dut_ip, "MQTTTeardowns") == teardowns, f"the burst ended the session: {_networking(m.dut_ip)!r}"
    result_note(f"{_QOS1_BURST} QoS 1 messages acknowledged in {took:.1f}s")


def test_an_oversized_inbound_message_is_discarded_and_framing_kept(mqtt_bench: MqttBench) -> None:
    m = mqtt_bench
    _wait_connected(m.dut_ip, "before the oversized message")
    dropped, teardowns = _count(m.dut_ip, "MQTTRxDropped"), _count(m.dut_ip, "MQTTTeardowns")
    assert m.observer.publish(f"{m.base}/cmd/big", b"x" * _OVERSIZE_BYTES)
    assert m.observer.publish(f"{m.base}/cmd/after", b"ok")
    wait_until(lambda: _networking(m.dut_ip).get("MQTTLastRxTopic") == f"{m.base}/cmd/after", timeout_s=_STEP_WAIT_S, poll_interval_s=_POLL_S, description="the message after the oversized one received intact")
    assert _count(m.dut_ip, "MQTTRxDropped") > dropped, "the oversized message was not counted as dropped"
    assert _count(m.dut_ip, "MQTTTeardowns") == teardowns, "the oversized message ended the session"


@pytest.mark.persistence_write("networking/mqtt")
def test_the_broker_is_found_by_the_bench_hosts_local_name(mqtt_bench: MqttBench, result_note: "_load.Note") -> None:
    # The DUT asks for this host's .local name with a one-shot mDNS query, answered by this host's Avahi (Part A.12).
    # The test owns both writes: the name, then this host's IP back.
    m = mqtt_bench
    name = f"{socket.gethostname()}.local"
    _wait_connected(m.dut_ip, "before switching to the .local name")
    connects = _count(m.dut_ip, "MQTTConnects")
    try:
        res = http_client.fetch(m.dut_ip, 80, "PUT", "/networking", {"MQTTHost": name}, timeout_s=_REST_BUDGET_S)
        assert res.status_code == 200 and _load.as_object(res.json().get("result"), "PUT /networking result").get("MQTTHost") == "Valid", f"{name} was refused: {res.body!r}"
        took = _wait_count_above(m.dut_ip, "MQTTConnects", connects, _CONNECT_WAIT_S, f"a connection through {name} (is avahi-daemon running here and publishing that name?)")
        broker = _networking(m.dut_ip).get("MQTTBroker")
        assert broker == m.host_ip, f"{name} resolved to {broker!r}, not this host's {m.host_ip}"
    finally:
        restore = http_client.fetch(m.dut_ip, 80, "PUT", "/networking", {"MQTTHost": m.host_ip}, timeout_s=_REST_BUDGET_S)
        assert restore.status_code == 200, f"restoring MQTTHost failed: {restore.body!r}"
    _wait_connected(m.dut_ip, "after MQTTHost went back to the IP")
    result_note(f"{name} resolved to {broker} and connected within {took:.1f}s")


def test_no_task_ended_and_only_expected_codes_were_logged(mqtt_bench: MqttBench) -> None:
    # The broker faults above, read before the AP outage below clears the logs: no supervised task ended, the web
    # server logged nothing, and MQTT logged only what its faults explain.
    m = mqtt_bench
    assert_no_task_ended(m.dut_ip, "MQTT broker faults")
    web = errcount_entry(get_errcount(m.dut_ip), "WEBSERVER")
    assert not web["counter"], f"the web server logged during the MQTT faults: {web!r}"
    _assert_mqtt_logged_only(m.dut_ip, "MQTT broker faults")


@pytest.mark.persistence_write("networking/mqtt")
def test_a_password_broker_admits_the_stored_credentials(mqtt_bench: MqttBench, tmp_path: Path, result_note: "_load.Note") -> None:
    # MQTTUser/MQTTPW reach the CONNECT; GET /networking never shows the password back.
    m = mqtt_bench
    _wait_connected(m.dut_ip, "before switching to the password broker")
    connects = _count(m.dut_ip, "MQTTConnects")
    with _password_broker(m, tmp_path, _AUTH_DEVICE[1]) as (broker, observer):
        took = _wait_count_above(m.dut_ip, "MQTTConnects", connects, _CONNECT_WAIT_S, "a connection to the password broker")
        online = wait_for(lambda: any(msg.payload == b"online" for msg in observer.received(f"{m.base}/status")), _STEP_WAIT_S)
        assert online, f"no online on the password broker: {observer.received()!r}"
        shown = http_client.fetch(m.dut_ip, 80, "GET", "/networking", timeout_s=_REST_BUDGET_S).json()
        assert shown.get("MQTTUser") == _AUTH_DEVICE[0] and shown.get("MQTTPW") != _AUTH_DEVICE[1], f"GET /networking: user {shown.get('MQTTUser')!r}, password shown in clear"
        anonymous = Probe(m.host_ip, _AUTH_PORT, "bench-anonymous", ()).start()
        refused = not anonymous.wait_connected(3.0)
        anonymous.close()
        assert refused, "the password broker admitted an anonymous client, so this test proves nothing"
        assert "bench-device" in broker.log_path.read_text(errors="replace")
    back = _wait_connected(m.dut_ip, "back on the anonymous broker")
    result_note(f"connected to the password broker in {took:.1f}s; password masked as {shown.get('MQTTPW')!r}; back on the anonymous broker in {back:.1f}s")


@pytest.mark.persistence_write("networking/mqtt")
@pytest.mark.provokes_log("the wrong password's refused CONNACKs, which the test asserts as MQTT_REFUSED", ("MQTT", "E", "MQTT_REFUSED"))
def test_a_wrong_password_is_refused_logged_and_retried_on_the_backoff(mqtt_bench: MqttBench, tmp_path: Path, result_note: "_load.Note") -> None:
    m = mqtt_bench
    _wait_connected(m.dut_ip, "before the wrong password")
    connects, logged = _count(m.dut_ip, "MQTTConnects"), _mqtt_counter(m.dut_ip)
    with _password_broker(m, tmp_path, _AUTH_DEVICE[1][::-1]) as (broker, _observer):
        started = time.monotonic()
        time.sleep(_REFUSED_WINDOW_S)  # an absence: no refused attempt may become a connection
        attempts = _broker_attempts_from(broker, m.dut_ip)
        status = _networking(m.dut_ip)
        assert status.get("MQTTConnected") is False and _count(m.dut_ip, "MQTTConnects") == connects, f"connected with a wrong password: {status!r}"
        assert 1 <= attempts <= _REFUSED_MAX_ATTEMPTS, f"{attempts} attempts in {_REFUSED_WINDOW_S:g}s: the backoff did not bound the refused retries"
        refused = [h for h in _mqtt_history(m.dut_ip) if h.get("num") == code("E", "MQTT_REFUSED")]
        assert refused, f"no MQTT_REFUSED logged: {_mqtt_history(m.dut_ip)!r}"
        res = http_client.fetch(m.dut_ip, 80, "PUT", "/networking", {"MQTTPW": _AUTH_DEVICE[1]}, timeout_s=_REST_BUDGET_S)
        assert res.status_code == 200, f"correcting the password failed: {res.body!r}"
        fixed = _wait_count_above(m.dut_ip, "MQTTConnects", connects, _CONNECT_WAIT_S, "a connection once the password was corrected")
        window = time.monotonic() - started
    _wait_connected(m.dut_ip, "back on the anonymous broker")
    codes = sorted({num for h in _mqtt_history(m.dut_ip) if isinstance(num := h.get("num"), int)})
    result_note(f"{attempts} refused attempts in {_REFUSED_WINDOW_S:g}s, {_mqtt_counter(m.dut_ip) - logged} MQTT log entries, codes {codes}; connected {fixed:.1f}s after the correction ({window:.0f}s in all)")


@pytest.mark.persistence_write("networking/mqtt")
@pytest.mark.provokes_log("the unresolvable name's attempts, which the test asserts as MQTT_DNS alone", ("MQTT", "E", "MQTT_DNS"))
@pytest.mark.parametrize("name", ["no-such-broker.invalid", "no-such-broker.local"])
def test_an_unresolvable_broker_name_is_logged_and_retried_on_the_backoff(mqtt_bench: MqttBench, name: str, request: pytest.FixtureRequest, result_note: "_load.Note") -> None:
    # .invalid never resolves (RFC 6761): the router answers NXDOMAIN; nobody answers the .local name's mDNS query.
    m = mqtt_bench
    _wait_connected(m.dut_ip, f"before switching to {name}")
    connects = _count(m.dut_ip, "MQTTConnects")
    reset_all_error_logs(m.dut_ip, request.node.name)
    try:
        res = http_client.fetch(m.dut_ip, 80, "PUT", "/networking", {"MQTTHost": name}, timeout_s=_REST_BUDGET_S)
        assert res.status_code == 200 and _load.as_object(res.json().get("result"), "PUT /networking result").get("MQTTHost") == "Valid", f"{name} was refused at PUT: {res.body!r}"
        started = time.monotonic()
        wait_until(lambda: any(h.get("num") == code("E", "MQTT_DNS") for h in _mqtt_history(m.dut_ip)), timeout_s=_DETECT_WAIT_S, poll_interval_s=_POLL_S, description=f"MQTT_DNS logged for {name}")
        first = time.monotonic() - started
        time.sleep(max(0.0, _REFUSED_WINDOW_S - first))  # an absence: no attempt may connect
        failures = _mqtt_counter(m.dut_ip)
        assert _count(m.dut_ip, "MQTTConnects") == connects and _networking(m.dut_ip).get("MQTTConnected") is False
        assert 1 <= failures <= _REFUSED_MAX_ATTEMPTS, f"{failures} MQTT log entries in {_REFUSED_WINDOW_S:g}s for an unresolvable name"
        unexpected = [h for h in _mqtt_history(m.dut_ip) if h.get("num") != code("E", "MQTT_DNS")]
        assert not unexpected, f"an unresolvable name logged more than MQTT_DNS: {unexpected!r}"
        assert http_client.fetch(m.dut_ip, 80, "GET", "/status", timeout_s=_REST_BUDGET_S).status_code == 200
    finally:
        restore = http_client.fetch(m.dut_ip, 80, "PUT", "/networking", {"MQTTHost": m.host_ip}, timeout_s=_REST_BUDGET_S)
        assert restore.status_code == 200, f"restoring MQTTHost failed: {restore.body!r}"
    back = _wait_connected(m.dut_ip, "after MQTTHost went back to the IP")
    result_note(f"{name}: MQTT_DNS first logged {first:.1f}s after the PUT, {failures} entries in {_REFUSED_WINDOW_S:g}s; reconnected {back:.1f}s after the restore")


@pytest.mark.provokes_log(
    "each sweep kills and restarts the broker, then stalls it into a missed PINGRESP",
    ("MQTT", "E", "MQTT_CONNECT"),
    ("MQTT", "E", "MQTT_LOST"),
    ("MQTT", "E", "MQTT_NO_PINGRESP"),
    ("MQTT", "E", "MQTT_STALLED"),
    ("MQTT", "W", "MQTT_SHORT_SESSIONS"),
)
@pytest.mark.parametrize("offset_s", _STALL_OFFSETS_S)
def test_stall_detection_follows_the_publish_rounds(mqtt_bench: MqttBench, board: "Board", offset_s: float, result_note: "_load.Note") -> None:
    # A round every 10 s from the connect, each confirmed by a PINGREQ whose PINGRESP is due 10 s later (the idle interval,
    # 180 s, never falls due): a stall `offset_s` after a connect is detected 10 s after the next round. The console times it.
    m = mqtt_bench
    _wait_connected(m.dut_ip, "before the stall sweep's connect")
    with _console(board.device) as console:
        killed = time.monotonic()
        m.broker.stop(signal.SIGKILL)
        time.sleep(_OUTAGE_S)  # an absence, as in the kill test
        m.broker.start()
        connected = console.first_after(killed, "MQTT Connected to", _CONNECT_WAIT_S + _BACKOFF_CAP_S)
        assert connected is not None, "no connect line on the console after the broker restarted"
        time.sleep(max(0.0, connected + offset_s - time.monotonic()))
        stalled = time.monotonic()
        m.broker.send(signal.SIGSTOP)
        try:
            detected = console.first_after(stalled, "No PINGRESP", _DETECT_WAIT_S)
        finally:
            m.broker.send(signal.SIGCONT)
    assert detected is not None, f"no PINGRESP deadline on the console within {_DETECT_WAIT_S:g}s of a stall {offset_s:g}s after the connect"
    took, expected = detected - stalled, math.ceil(offset_s / _PUB_INTERVAL_S) * _PUB_INTERVAL_S - offset_s + 10.0
    assert abs(took - expected) <= _STALL_PHASE_TOLERANCE_S, f"a stall {offset_s:g}s after the connect was detected in {took:.2f}s, expected {expected:.1f}s"
    back = _wait_connected(m.dut_ip, "once the stalled broker resumed")
    assert m.observer.wait_connected(), "the observer did not come back"
    result_note(f"stall {offset_s:g}s after the connect: detected in {took:.2f}s (expected {expected:.1f}s); reconnected {back:.1f}s after the resume")


@pytest.mark.provokes_log(
    "the outage's WLAN warnings and NTP attempts as the WiFi outage test has them, and the client's attempts and lost"
    " connection, which the test bounds",
    ("WIFI", "W", "WLAN_NO_AP"),
    ("WIFI", "W", "WLAN_AUTH_FAILED"),
    ("NTP", "E", "NTP_DNS"),
    ("NTP", "E", "NTP_NOT_SENT"),
    ("NTP", "E", "NTP_NO_REPLY"),
    ("NTP", "E", "NTP_RETRIES"),
    ("MQTT", "E", "MQTT_CONNECT"),
    ("MQTT", "E", "MQTT_LOST"),
    ("MQTT", "E", "MQTT_NO_PINGRESP"),
    ("MQTT", "E", "MQTT_STALLED"),
    ("MQTT", "W", "MQTT_SHORT_SESSIONS"),
)
def test_an_ap_outage_pauses_the_client_and_it_returns_with_the_link(mqtt_bench: MqttBench, board: "Board", bench: "BenchBridge", request: pytest.FixtureRequest, result_note: "_load.Note") -> None:
    # MQTT never drives WiFi (Part A.12): the client waits out the outage without logging per attempt, then reconnects.
    m = mqtt_bench
    _wait_connected(m.dut_ip, "before the AP outage")
    reset_all_error_logs(m.dut_ip, request.node.name)
    bench.ap_down()
    try:
        time.sleep(_AP_OUTAGE_S)  # an absence: the DUT is unreachable for its whole length
    finally:
        bench.ap_up()
        bench.kick_all_stations()  # stale AP-side entries stop the DUT reassociating (README)
    started = time.monotonic()
    # The CYW43 false positive the WiFi tests document: one recovery reset, reported, is a genuine pass (CLAUDE.md).
    recover_by_reset(board, bench, lambda: _networking(m.dut_ip).get("MQTTConnected") is True, first_wait_s=_AP_RECONNECT_TIMEOUT_S, retry_wait_s=_REBOOT_WAIT_S, skipped="the passive reconnect with the link", note=result_note, description="the MQTT client connected after the AP came back")
    back = time.monotonic() - started
    attempts = sum(1 for h in _mqtt_history(m.dut_ip) if h.get("num") == _E_CONNECT)
    assert attempts <= _AP_MAX_FAILED_ATTEMPTS, f"{attempts} failed attempts logged across the outage: {_mqtt_history(m.dut_ip)!r}"
    assert_no_task_ended(m.dut_ip, "AP outage")  # on both paths: FRAM keeps SYSTEM across the hard reset
    _assert_mqtt_logged_only(m.dut_ip, "AP outage")
    result_note(f"connected {back:.1f}s after the AP came back; {attempts} failed attempt(s) logged")


def test_a_reboot_reconnects_from_the_stored_settings(mqtt_bench: MqttBench, board: "Board", bench: "BenchBridge", result_note: "_load.Note") -> None:
    m = mqtt_bench
    _wait_connected(m.dut_ip, "before the reboot")
    seen = len(m.observer.received(f"{m.base}/status"))
    kick_then_reset(board, bench)
    back = _wait_connected(m.dut_ip, "after the reboot", timeout_s=_REBOOT_WAIT_S)
    fresh = wait_for(lambda: any(msg.payload == b"online" and not msg.retained for msg in m.observer.received(f"{m.base}/status")[seen:]), _STEP_WAIT_S)
    assert fresh, f"no fresh online after the reboot: {m.observer.received(f'{m.base}/status')[seen:]!r}"
    will = any(msg.payload == b"offline" for msg in m.observer.received(f"{m.base}/status")[seen:])
    result_note(f"connected {back:.1f}s after the reset; the broker {'published' if will else 'did not publish'} the will on the takeover")


@pytest.mark.provokes_log(
    "the script's own boot of the graph meets the same broker faults as the tests above, on the production loggers",
    ("MQTT", "E", "MQTT_CONNECT"),
    ("MQTT", "E", "MQTT_LOST"),
    ("MQTT", "E", "MQTT_NO_PINGRESP"),
    ("MQTT", "E", "MQTT_STALLED"),
    ("MQTT", "W", "MQTT_SHORT_SESSIONS"),
)
def test_the_broker_faults_run_clean_at_micropythons_default_gc(mqtt_bench: MqttBench, board: "Board", bench: "BenchBridge", result_note: "_load.Note") -> None:
    # The firmware's own graph at gc.threshold(-1) while this host kills, stalls, floods and takes over the session:
    # not one allocation failure (Part I.4(e)). The harness renders the bench device's module into the script.
    m = mqtt_bench
    stop = threading.Event()
    steps: list[str] = []
    driver = threading.Thread(target=_drive_faults, args=(m, stop, steps), name="mqtt-fault-driver")
    try:
        driver.start()
        output = board.run_isolated(DEVICE_SCRIPTS_DIR / "mqtt_at_default_gc.py", timeout_s=_SCRIPT_TIMEOUT_S)
    finally:
        stop.set()
        alive = _load.join([driver], _DRIVER_JOIN_S)
        m.broker.send(signal.SIGCONT)
        restore_board_to_serving(board, bench, m.dut_ip)
    assert not alive, "the fault driver outlived its test"
    facts = parse_facts(output)
    assert facts.get("gc_threshold") == -1, f"the script did not run at the reactive default: {facts}"
    assert not any(marker in output for marker in MEMORY_ERROR_MARKERS), f"allocation failure at the reactive default (I.4(e)): {output[-2500:]}"
    assert "UNRETRIEVED TASK EXCEPTION" not in output, output[-2500:]
    assert steps and steps[-1] == "done", f"the fault timeline did not finish inside the script's window: {steps}"
    # At the reactive default free memory sinks until an allocation forces a collect, so the lowest sample is only how
    # near a collect it landed, never a margin: the note keeps every sample and counts the collects they straddle.
    samples = facts.get("mem_free")
    assert isinstance(samples, list), f"the script reported no heap samples: {facts}"
    free = [v for v in samples if isinstance(v, int)]
    rises = sum(1 for before, after in itertools.pairwise(free) if after > before)
    result_note(f"timeline {steps}; free heap at the reactive default over {len(free)} samples, {rises} collects between them: {free} B")
    _wait_connected(m.dut_ip, "after the board went back to its own firmware", timeout_s=_REBOOT_WAIT_S)


@pytest.mark.persistence_write("networking/mqtt")
def test_the_status_settings_shape_the_online_message_and_the_will_the_broker_fires(mqtt_bench: MqttBench, board: "Board", bench: "BenchBridge", result_note: "_load.Note") -> None:
    # The test owns both writes, the settings and the defaults back. A reboot drops the board without a DISCONNECT, so
    # the broker publishes the configured will, at its keepalive deadline or at the clean session's takeover.
    m = mqtt_bench
    watch = Probe(m.host_ip, _BROKER_PORT, "bench-status", (_STATUS_TOPIC,)).start()
    try:
        assert watch.wait_connected(), "the status topic's watcher could not connect"
        res = http_client.fetch(m.dut_ip, 80, "PUT", "/networking", {"MQTTWillTopic": _STATUS_TOPIC, "MQTTOnlineMsg": "up", "MQTTWillMsg": "down", "MQTTWillQoS": 0, "MQTTWillRetain": False}, timeout_s=_REST_BUDGET_S)
        _assert_taken(res, "the status settings")
        up = wait_for(lambda: any(msg.payload == b"up" and not msg.retained for msg in watch.received(_STATUS_TOPIC)), _CONNECT_WAIT_S)
        assert up, f"no online message on {_STATUS_TOPIC}: {watch.received(_STATUS_TOPIC)!r}"
        offline = [msg.payload for msg in m.observer.received(f"{m.base}/status")]
        assert offline[-1:] == [b"offline"], f"the old status topic was not set offline before the reconnect: {offline!r}"
        seen = len(watch.received(_STATUS_TOPIC))
        kick_then_reset(board, bench)
        back = _wait_connected(m.dut_ip, "after the reboot", timeout_s=_REBOOT_WAIT_S)
        will = wait_for(lambda: any(msg.payload == b"down" for msg in watch.received(_STATUS_TOPIC)[seen:]), _STEP_WAIT_S)
        assert will, f"the broker never published the configured will: {watch.received(_STATUS_TOPIC)[seen:]!r}"
    finally:
        watch.close()
        res = http_client.fetch(m.dut_ip, 80, "PUT", "/networking", {"MQTTWillTopic": "", "MQTTOnlineMsg": "online", "MQTTWillMsg": "offline", "MQTTWillQoS": 1, "MQTTWillRetain": True}, timeout_s=_REST_BUDGET_S)
        _assert_taken(res, "restoring the status settings to their defaults")
    _wait_connected(m.dut_ip, "after the status settings went back")
    result_note(f"online and will on {_STATUS_TOPIC}; reconnected {back:.1f}s after the reset")


@pytest.mark.persistence_write("networking/mqtt")
def test_a_persistent_session_delivers_a_command_sent_while_the_board_rebooted(mqtt_bench: MqttBench, board: "Board", bench: "BenchBridge", result_note: "_load.Note") -> None:
    # The broker keeps the session across the reboot and holds the QoS 1 command for it (owner, 2026-10-13: 'Setting,
    # default off (Recommended)'); the test owns the switch and puts it back off.
    m = mqtt_bench
    try:
        res = http_client.fetch(m.dut_ip, 80, "PUT", "/networking", {"MQTTPersistent": True}, timeout_s=_REST_BUDGET_S)
        _assert_taken(res, "the persistent session")
        _wait_connected(m.dut_ip, "with a persistent session")
        kick_then_reset(board, bench)
        assert m.observer.publish(f"{m.base}/cmd/queued", b"while-away", qos=1), "the observer lost its broker"
        back = _wait_connected(m.dut_ip, "after the reboot", timeout_s=_REBOOT_WAIT_S)
        wait_until(lambda: _networking(m.dut_ip).get("MQTTLastRxTopic") == f"{m.base}/cmd/queued", timeout_s=_STEP_WAIT_S, poll_interval_s=_POLL_S, description="the command queued during the reboot delivered")
    finally:
        res = http_client.fetch(m.dut_ip, 80, "PUT", "/networking", {"MQTTPersistent": False}, timeout_s=_REST_BUDGET_S)
        _assert_taken(res, "switching the persistent session off")
    _wait_connected(m.dut_ip, "after the persistent session was switched off")  # its clean connect discards the session
    result_note(f"the queued command arrived after the reboot; reconnected {back:.1f}s after the reset")


@pytest.mark.persistence_write("networking/mqtt")
def test_a_changed_client_id_retires_the_old_persistent_session(mqtt_bench: MqttBench, result_note: "_load.Note") -> None:
    # The keeper ends the old identity's session with one clean connect before it connects as the new one (owner,
    # 2026-10-13: 'Retire it (Recommended)'); the test owns the writes and puts the client id and the switch back.
    m = mqtt_bench
    moved_id = f"{m.client_id[:21]}-b"  # a 1-23 byte host label, never the old id
    try:
        res = http_client.fetch(m.dut_ip, 80, "PUT", "/networking", {"MQTTPersistent": True}, timeout_s=_REST_BUDGET_S)
        _assert_taken(res, "the persistent session")
        _wait_connected(m.dut_ip, "with a persistent session")
        connects = _count(m.dut_ip, "MQTTConnects")
        res = http_client.fetch(m.dut_ip, 80, "PUT", "/networking", {"MQTTClientId": moved_id}, timeout_s=_REST_BUDGET_S)
        _assert_taken(res, "the new client id")
        took = _wait_count_above(m.dut_ip, "MQTTConnects", connects, _CONNECT_WAIT_S, "a connection under the new client id")
        _wait_connected(m.dut_ip, "under the new client id")
        assert not session_present(m.host_ip, _BROKER_PORT, m.client_id), f"the broker still holds {m.client_id}'s session"
    finally:
        res = http_client.fetch(m.dut_ip, 80, "PUT", "/networking", {"MQTTClientId": m.client_id, "MQTTPersistent": False}, timeout_s=_REST_BUDGET_S)
        _assert_taken(res, "restoring the client id")
    _wait_connected(m.dut_ip, "under the old client id again")
    assert not session_present(m.host_ip, _BROKER_PORT, moved_id), f"the broker still holds {moved_id}'s session after the switch went off"
    result_note(f"retired {m.client_id}'s session and reconnected as {moved_id} within {took:.1f}s")


def test_disabling_the_client_publishes_offline_and_ends_the_session(mqtt_bench: MqttBench) -> None:
    # Last: the fixture's own disable then writes nothing. A DISCONNECT drops the will, so the client says offline itself.
    m = mqtt_bench
    _wait_connected(m.dut_ip, "before disabling it")
    seen = len(m.observer.received(f"{m.base}/status"))
    _disable_mqtt(m.dut_ip)
    offline = wait_for(lambda: any(msg.payload == b"offline" for msg in m.observer.received(f"{m.base}/status")[seen:]), _STEP_WAIT_S)
    assert offline, f"no offline on {m.base}/status after disabling: {m.observer.received(f'{m.base}/status')[seen:]!r}"
    wait_until(lambda: _networking(m.dut_ip).get("MQTTState") == "disabled", timeout_s=_STEP_WAIT_S, poll_interval_s=_POLL_S, description="MQTTState disabled")
    assert _networking(m.dut_ip).get("MQTTLastReason") == "reconfigured"
