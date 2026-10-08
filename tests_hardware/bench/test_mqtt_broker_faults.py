"""Bench tier for the MQTT client (SPECIFICATION.md Part A.11): the real client on the bench board against a mosquitto
on this host's own LAN address, through broker faults, path loss, a client-id takeover, inbound floods, an AP outage
and a reboot at the firmware's own gc threshold, then the broker faults again at MicroPython's default (Part I.4(e))."""

from __future__ import annotations

import contextlib
import json
import signal
import socket
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

import http_client
import pytest
import serial
import tomllib
from error_log_helpers import assert_no_task_ended, code, get_errcount, reset_all_error_logs
from harness import MEMORY_ERROR_MARKERS, REPO_ROOT, restore_board_to_serving, wait_for_script_server, wait_until
from mqtt_probe import Mosquitto, Probe, wait_for

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))  # the repo root, for buildgen

from buildgen.definitions import definitions_for_toml

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from bench_control import BenchBridge
    from harness import Board

COVERS_TWIN_SCENARIOS: tuple[str, ...] = ("ci_suite._run_12_mqtt_broker_faults",)

DEVICE_SCRIPTS = Path(__file__).resolve().parent.parent / "device_scripts"
_BROKER_PORT = 18883  # fixed, so every iptables rule names it; a distribution mosquitto keeps 1883 to itself
_AUTH_PORT = 18884  # the password broker's, beside the anonymous one
_AUTH_DEVICE = ("bench-device", "bench-device-pass")  # a throwaway broker's accounts, not real secrets
_AUTH_OBSERVER = ("bench-observer", "bench-observer-pass")
_STALL_OFFSETS_S = (1.0, 5.0, 9.0, 13.0)  # after a connect, across the 15 s ping interval's phase
_FAULT_COMMENT = "sensors-bench-mqtt-fault"
_OBSERVER_ID = "bench-observer"
_SLOT_PAYLOAD_MAX = 384  # mqtt.out_payload_max: a larger measurement object would be dropped, counted
_MODULE_PLACEHOLDER = "import sensortask_ as sensortask_bench"

# @tunable l4.mqtt_pub_interval_s = 10
_PUB_INTERVAL_S = 10  # MQTTPubInterval's minimum, so the measurement checks wait least
# @tunable l4.mqtt_connect_wait_s = 90.0
_CONNECT_WAIT_S = 90.0  # a connect once the fault is gone, the bench's WiFi latency included
# @tunable mqtt.backoff_max_ms = 60.0
_BACKOFF_CAP_S = 60.0  # the reconnect wait the earlier faults' short sessions may have grown to
# @tunable l4.mqtt_step_wait_s = 20.0
_STEP_WAIT_S = 20.0  # one message's round trip through the broker and the device's status
# @tunable l4.mqtt_outage_s = 5.0
_OUTAGE_S = 5.0  # the killed broker's downtime: the client's first attempts fail inside it
# @tunable l4.mqtt_detect_bound_s = 35.0
_DETECT_BOUND_S = 35.0  # mqtt.ping_interval_ms + mqtt.response_timeout_ms (25 s), plus ticks and WiFi latency
# @tunable l4.mqtt_detect_wait_s = 60.0
_DETECT_WAIT_S = 60.0
# @tunable l4.mqtt_takeover_s = 20.0
_TAKEOVER_S = 20.0
# @tunable l4.mqtt_takeover_max_connects = 5
_TAKEOVER_MAX_CONNECTS = 5  # the doubling backoff allows about four retakes in the window; the minimum would allow ten
# @tunable l4.mqtt_flood_messages = 3000
_FLOOD_MESSAGES = 3000  # about 200 KB through the device's 1 KB receive buffer
# @tunable l4.mqtt_qos1_burst = 500
_QOS1_BURST = 500  # below mosquitto's default 1000-message queue, so the broker delivers every one
# @tunable l4.mqtt_oversize_bytes = 4096
_OVERSIZE_BYTES = 4096  # four times mqtt.rx_buf_bytes
# @tunable l4.mqtt_rest_budget_s = 15.0
_REST_BUDGET_S = 15.0
# @tunable l4.mqtt_ap_outage_s = 30.0
_AP_OUTAGE_S = 30.0
# @tunable l4.mqtt_ap_reconnect_timeout_s = 240.0
_AP_RECONNECT_TIMEOUT_S = 240.0  # past the WiFi service's 60 s retry after a loss, twice
# @tunable l4.mqtt_ap_max_failed_attempts = 6
_AP_MAX_FAILED_ATTEMPTS = 6  # attempts only before the WiFi service reports the loss, then the backoff's 2+4+...+64 s
# @tunable l4.mqtt_reboot_wait_s = 180.0
_REBOOT_WAIT_S = 180.0
# @tunable l4.mqtt_default_gc_script_timeout_s = 600.0
_SCRIPT_TIMEOUT_S = 600.0  # the device script's 420 s window, its boot and mpremote's own overhead
# @tunable l4.mqtt_default_gc_driver_join_s = 60.0
_DRIVER_JOIN_S = 60.0
# @tunable l4.mqtt_poll_s = 1.0
_POLL_S = 1.0
# @tunable l4.mqtt_refused_window_s = 40.0
_REFUSED_WINDOW_S = 40.0  # failed attempts are counted over it: about five at the 2 s doubling backoff
# @tunable l4.mqtt_refused_max_attempts = 6
_REFUSED_MAX_ATTEMPTS = 6  # one over the doubling backoff's count in the window; the minimum alone would allow about 20
# @tunable l4.mqtt_stall_phase_tolerance_s = 1.5
_STALL_PHASE_TOLERANCE_S = 1.5  # the keeper's 100 ms tick, the console's USB latency and this host's scheduling

_E_CONNECT = code("E", "MQTT_CONNECT")
# What this module's faults may log: a failed attempt, a lost connection, a missed PINGRESP, a stalled drain and the
# short-session warning. The history spans tests, so one set: a protocol, refusal or allocation code fails the module.
_EXPECTED_MQTT_CODES = {_E_CONNECT, code("E", "MQTT_LOST"), code("E", "MQTT_NO_PINGRESP"), code("E", "MQTT_STALLED"), code("W", "MQTT_SHORT_SESSIONS")}


@dataclass(frozen=True)
class MqttBench:
    dut_ip: str
    host_ip: str
    broker: Mosquitto
    observer: Probe
    base: str
    client_id: str


def _mqtt_device() -> str:
    # The one device whose TOML carries the client; the bench board runs its image. Read as data, never named here.
    found = [p.stem for p in sorted((REPO_ROOT / "devices").glob("*.toml")) if any(i.get("driver") == "mqtt" for i in tomllib.loads(p.read_text()).get("instance", []))]
    assert len(found) == 1, f"expected exactly one device TOML carrying the MQTT client, found {found}"
    return found[0]


def _sensor_names(device: str) -> list[str]:
    # The modules the client publishes: every sensor, the same set as the website's measurements cards.
    definitions = definitions_for_toml(REPO_ROOT / "devices" / f"{device}.toml", REPO_ROOT / "src")
    section = next(s for s in definitions["sections"] if s["key"] == "measurements")
    return [str(g["key"]) for g in section["groups"]]


def _host_ip_toward(dut_ip: str) -> str:
    # This host's own address on the DUT's network: the source the kernel picks to reach it, br0's on the bench.
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.connect((dut_ip, 80))
        return str(s.getsockname()[0])


def _networking(dut_ip: str) -> dict[str, Any]:
    res = http_client.fetch(dut_ip, 80, "GET", "/status", timeout_s=_REST_BUDGET_S)
    assert res.status_code == 200, f"GET /status returned {res.status_code}: {res.body!r}"
    networking: dict[str, Any] = res.json().get("networking", {})
    return networking


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
    # json.loads() accepts NaN and Infinity, which the device writes as null (Part A.11).
    def refuse(token: str) -> None:
        raise ValueError(f"non-finite JSON token {token}")

    return json.loads(payload, parse_constant=refuse)


def _mqtt_history(dut_ip: str) -> list[dict[str, Any]]:
    entry = get_errcount(dut_ip).get("MQTT", {})
    return [h for h in entry.get("history", []) if h.get("type") in ("E", "W")]


def _assert_mqtt_logged_only(dut_ip: str, context: str) -> None:
    unexpected = [h for h in _mqtt_history(dut_ip) if h.get("num") not in _EXPECTED_MQTT_CODES]
    assert not unexpected, f"{context}: the MQTT log holds {unexpected!r}, outside the expected {sorted(_EXPECTED_MQTT_CODES)}"


def _enable_mqtt(dut_ip: str, host_ip: str) -> None:
    # This module's shared prerequisite write (config_MQTT.cfg): every test below needs a client pointed at this
    # host's broker. Unchanged values write nothing, so a rerun on an enabled board spends no flash.
    res = http_client.fetch(dut_ip, 80, "PUT", "/networking", {"MQTTEnable": True, "MQTTHost": host_ip, "MQTTPort": _BROKER_PORT, "MQTTPubInterval": _PUB_INTERVAL_S}, timeout_s=_REST_BUDGET_S)
    result = res.json().get("result", {}) if res.status_code == 200 else {}
    assert result and all(v in ("Valid", "Unchanged") for v in result.values()), f"enabling the MQTT client was refused: {res.status_code} {res.body!r}"


def _disable_mqtt(dut_ip: str) -> None:
    # Its undo, so the bench tests after this module see the old baseline: the client says offline and idles.
    res = http_client.fetch(dut_ip, 80, "PUT", "/networking", {"MQTTEnable": False}, timeout_s=_REST_BUDGET_S)
    assert res.status_code == 200 and res.json().get("result", {}).get("MQTTEnable") in ("Valid", "Unchanged"), f"disabling the MQTT client was refused: {res.status_code} {res.body!r}"


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

    def step(name: str, condition: Callable[[], bool], timeout_s: float) -> bool:
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
def _password_broker(m: MqttBench, workdir: Path, password: str) -> Iterator[tuple[Mosquitto, Probe]]:
    # A second broker that admits only its two accounts, the device pointed at it with `password`; this test owns the
    # writes and their undo (the anonymous broker's port and no credentials).
    broker = Mosquitto(workdir, _AUTH_PORT, bind=m.host_ip, users=dict([_AUTH_DEVICE, _AUTH_OBSERVER]))
    broker.start()
    observer = Probe(m.host_ip, _AUTH_PORT, _OBSERVER_ID + "-auth", (f"{m.base}/#",), username=_AUTH_OBSERVER[0], password=_AUTH_OBSERVER[1]).start()
    try:
        assert observer.wait_connected(), f"the bench's own account was refused (log: {broker.log_path})"
        res = http_client.fetch(m.dut_ip, 80, "PUT", "/networking", {"MQTTPort": _AUTH_PORT, "MQTTUser": _AUTH_DEVICE[0], "MQTTPW": password}, timeout_s=_REST_BUDGET_S)
        assert res.status_code == 200 and all(v in ("Valid", "Unchanged") for v in res.json().get("result", {}).values()), f"the credentials were refused at PUT: {res.body!r}"
        yield broker, observer
    finally:
        restore = http_client.fetch(m.dut_ip, 80, "PUT", "/networking", {"MQTTPort": _BROKER_PORT, "MQTTUser": "", "MQTTPW": ""}, timeout_s=_REST_BUDGET_S)
        observer.close()
        broker.stop()
        assert restore.status_code == 200, f"restoring the anonymous broker failed: {restore.body!r}"


def _broker_attempts_from(broker: Mosquitto, dut_ip: str) -> int:
    return broker.log_path.read_text(errors="replace").count(f"New connection from {dut_ip}:")


def _mqtt_counter(dut_ip: str) -> int:
    return int(get_errcount(dut_ip).get("MQTT", {}).get("counter", 0))


class _Console:
    # The board's console with this host's monotonic time per line, read passively while a test runs.
    def __init__(self, device: str) -> None:
        self.lines: list[tuple[float, str]] = []
        self._stop = threading.Event()
        self._port = serial.Serial(device, 115200, timeout=0.2)
        self._thread = threading.Thread(target=self._read, daemon=True)
        self._thread.start()

    def _read(self) -> None:
        while not self._stop.is_set():
            raw = self._port.readline()
            if raw:
                self.lines.append((time.monotonic(), raw.decode("utf-8", errors="replace").rstrip("\r\n")))

    def first_after(self, since: float, text: str, timeout_s: float) -> float | None:
        def hit() -> float | None:
            return next((t for t, line in list(self.lines) if t >= since and text in line), None)

        wait_for(lambda: hit() is not None, timeout_s, 0.05)
        return hit()

    def close(self) -> None:
        self._stop.set()
        self._thread.join(timeout=2.0)
        self._port.close()


@pytest.fixture(scope="module")
def mqtt_bench(bench: BenchBridge, dut_ip: str, tmp_path_factory: pytest.TempPathFactory) -> Iterator[MqttBench]:
    if "MQTTState" not in _networking(dut_ip):
        pytest.fail(f"this firmware carries no MQTT client - flash the {_mqtt_device()} image built from this branch (tests_hardware/README.md)")
    # The FRAM logs are evidence a reset erases (CLAUDE.md), so whatever they hold is recorded first.
    logged = {name: entry for name, entry in get_errcount(dut_ip).items() if entry.get("counter")}
    print(f"[HW] FRAM-backed logs before this module's ResetErrors: {json.dumps(logged)}")
    reset_all_error_logs(dut_ip)
    host_ip = _host_ip_toward(dut_ip)
    broker = Mosquitto(tmp_path_factory.mktemp("mqtt"), _BROKER_PORT, bind=host_ip)
    observer: Probe | None = None
    try:
        broker.start()
        _enable_mqtt(dut_ip, host_ip)
        cfg = http_client.fetch(dut_ip, 80, "GET", "/networking", timeout_s=_REST_BUDGET_S).json()
        client_id = str(cfg["MQTTClientId"])
        observer = Probe(host_ip, _BROKER_PORT, _OBSERVER_ID, (f"{cfg['MQTTPrefix']}/{client_id}/#",)).start()
        assert observer.wait_connected(), f"the bench's own observer could not connect to {host_ip}:{_BROKER_PORT} (log: {broker.log_path})"
        yield MqttBench(dut_ip, host_ip, broker, observer, f"{cfg['MQTTPrefix']}/{client_id}", client_id)
    finally:
        for reset in (False, True):
            bench.unblock_tcp_port_from(dut_ip, _BROKER_PORT, reset=reset, comment=_FAULT_COMMENT)
        try:
            _disable_mqtt(dut_ip)
        finally:
            if observer is not None:
                observer.close()
            broker.stop()
            print(f"[HW] mosquitto log: {broker.log_path}")


def test_the_client_connects_and_announces_itself_online(mqtt_bench: MqttBench, result_note: Callable[..., None]) -> None:
    m = mqtt_bench
    took = _wait_connected(m.dut_ip, "after the enabling PUT")
    status = _networking(m.dut_ip)
    assert status["MQTTBroker"] == m.host_ip, f"connected to {status['MQTTBroker']!r}, not this host's {m.host_ip}"
    online = wait_for(lambda: any(msg.payload == b"online" for msg in m.observer.received(f"{m.base}/status")), _STEP_WAIT_S)
    assert online, f"no online on {m.base}/status: {m.observer.received()!r}"
    result_note(f"connected within {took:.1f}s of the first poll; MQTTState {status['MQTTState']!r}")


def test_every_sensor_publishes_strict_json_on_its_own_topic(mqtt_bench: MqttBench, result_note: Callable[..., None]) -> None:
    m = mqtt_bench
    names = _sensor_names(_mqtt_device())
    arrived = wait_for(lambda: all(m.observer.received(f"{m.base}/measurements/{n}") for n in names), _PUB_INTERVAL_S * 3)
    assert arrived, f"not every sensor published within three intervals: {[n for n in names if not m.observer.received(f'{m.base}/measurements/{n}')]}"
    meas = http_client.fetch(m.dut_ip, 80, "GET", "/measurements", timeout_s=_REST_BUDGET_S).json()
    largest = 0
    for name in names:
        payload = m.observer.received(f"{m.base}/measurements/{name}")[-1].payload
        largest = max(largest, len(payload))
        parsed = _strict_json(payload)
        assert isinstance(parsed, dict) and set(parsed) == set(meas[name]), f"{name}: {parsed!r} does not carry /measurements' keys {sorted(meas[name])}"
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


def test_a_killed_broker_is_reconnected_after_its_restart(mqtt_bench: MqttBench, result_note: Callable[..., None]) -> None:
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


def test_a_stalled_broker_is_detected_by_the_pingresp_deadline(mqtt_bench: MqttBench, result_note: Callable[..., None]) -> None:
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


def test_a_silent_path_loss_is_detected_and_recovered(mqtt_bench: MqttBench, bench: BenchBridge, result_note: Callable[..., None]) -> None:
    # The case lwIP alone never sees: no FIN, no RST, both directions dropped on this host. WiFi and REST stay up.
    m = mqtt_bench
    _wait_connected(m.dut_ip, "before the path loss")
    teardowns = _count(m.dut_ip, "MQTTTeardowns")
    bench.block_tcp_port_from(m.dut_ip, _BROKER_PORT, comment=_FAULT_COMMENT)
    try:
        took = _wait_count_above(m.dut_ip, "MQTTTeardowns", teardowns, _DETECT_WAIT_S, "the client ending a connection whose path is gone")
        assert http_client.fetch(m.dut_ip, 80, "GET", "/status", timeout_s=_REST_BUDGET_S).status_code == 200
    finally:
        bench.unblock_tcp_port_from(m.dut_ip, _BROKER_PORT, comment=_FAULT_COMMENT)
    assert took <= _DETECT_BOUND_S, f"a silent path loss took {took:.1f}s to detect, past {_DETECT_BOUND_S:g}s"
    reason = _networking(m.dut_ip).get("MQTTLastReason")
    back = _wait_connected(m.dut_ip, "once the path was restored")
    result_note(f"path loss detected in {took:.1f}s ({reason!r}); reconnected {back:.1f}s after the restore")


def test_a_reset_path_ends_the_connection_and_attempts_stay_bounded(mqtt_bench: MqttBench, bench: BenchBridge, result_note: Callable[..., None]) -> None:
    m = mqtt_bench
    _wait_connected(m.dut_ip, "before the reset path")
    connects, teardowns = _count(m.dut_ip, "MQTTConnects"), _count(m.dut_ip, "MQTTTeardowns")
    bench.block_tcp_port_from(m.dut_ip, _BROKER_PORT, reset=True, comment=_FAULT_COMMENT)
    try:
        took = _wait_count_above(m.dut_ip, "MQTTTeardowns", teardowns, _DETECT_WAIT_S, "the client ending a connection answered with resets")
        time.sleep(_TAKEOVER_S)  # an absence: refused attempts must not turn into connections
        assert _count(m.dut_ip, "MQTTConnects") == connects, "a connection succeeded through a path answering every segment with a reset"
    finally:
        bench.unblock_tcp_port_from(m.dut_ip, _BROKER_PORT, reset=True, comment=_FAULT_COMMENT)
    back = _wait_connected(m.dut_ip, "once the resets stopped")
    result_note(f"reset path ended the connection in {took:.1f}s; reconnected {back:.1f}s after the restore")


def test_a_duplicate_client_id_is_bounded_by_the_backoff(mqtt_bench: MqttBench, result_note: Callable[..., None]) -> None:
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


def test_an_inbound_flood_leaves_rest_serving_and_the_session_up(mqtt_bench: MqttBench, result_note: Callable[..., None]) -> None:
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


def test_an_inbound_qos1_burst_is_acknowledged_in_full(mqtt_bench: MqttBench, result_note: Callable[..., None]) -> None:
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
def test_the_broker_is_found_by_the_bench_hosts_local_name(mqtt_bench: MqttBench, result_note: Callable[..., None]) -> None:
    # The DUT asks for this host's .local name with a one-shot mDNS query, answered by this host's Avahi (Part A.11).
    # The test owns both writes: the name, then this host's IP back.
    m = mqtt_bench
    name = f"{socket.gethostname()}.local"
    _wait_connected(m.dut_ip, "before switching to the .local name")
    connects = _count(m.dut_ip, "MQTTConnects")
    try:
        res = http_client.fetch(m.dut_ip, 80, "PUT", "/networking", {"MQTTHost": name}, timeout_s=_REST_BUDGET_S)
        assert res.status_code == 200 and res.json().get("result", {}).get("MQTTHost") == "Valid", f"{name} was refused: {res.body!r}"
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
    web = get_errcount(m.dut_ip).get("WEBSERVER", {})
    assert not web.get("counter"), f"the web server logged during the MQTT faults: {web!r}"
    _assert_mqtt_logged_only(m.dut_ip, "MQTT broker faults")


@pytest.mark.persistence_write("networking/mqtt")
def test_a_password_broker_admits_the_stored_credentials(mqtt_bench: MqttBench, tmp_path: Path, result_note: Callable[..., None]) -> None:
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
def test_a_wrong_password_is_refused_logged_and_retried_on_the_backoff(mqtt_bench: MqttBench, tmp_path: Path, result_note: Callable[..., None]) -> None:
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
    result_note(f"{attempts} refused attempts in {_REFUSED_WINDOW_S:g}s, {_mqtt_counter(m.dut_ip) - logged} MQTT log entries, codes {sorted({int(h['num']) for h in _mqtt_history(m.dut_ip)})}; connected {fixed:.1f}s after the correction ({window:.0f}s in all)")


@pytest.mark.persistence_write("networking/mqtt")
@pytest.mark.parametrize("name", ["no-such-broker.invalid", "no-such-broker.local"])
def test_an_unresolvable_broker_name_is_logged_and_retried_on_the_backoff(mqtt_bench: MqttBench, name: str, result_note: Callable[..., None]) -> None:
    # .invalid never resolves (RFC 6761): the router answers NXDOMAIN; nobody answers the .local name's mDNS query.
    m = mqtt_bench
    _wait_connected(m.dut_ip, f"before switching to {name}")
    connects = _count(m.dut_ip, "MQTTConnects")
    reset_all_error_logs(m.dut_ip)
    try:
        res = http_client.fetch(m.dut_ip, 80, "PUT", "/networking", {"MQTTHost": name}, timeout_s=_REST_BUDGET_S)
        assert res.status_code == 200 and res.json().get("result", {}).get("MQTTHost") == "Valid", f"{name} was refused at PUT: {res.body!r}"
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


@pytest.mark.parametrize("offset_s", _STALL_OFFSETS_S)
def test_stall_detection_follows_the_ping_schedule(mqtt_bench: MqttBench, board: Board, offset_s: float, result_note: Callable[..., None]) -> None:
    # PINGREQ goes out every 15 s from the connect, its PINGRESP due 10 s later: a stall `offset_s` after a connect is
    # detected at (15 - offset_s) + 10 s. The board's own console times both ends; a killed broker makes the connect.
    m = mqtt_bench
    _wait_connected(m.dut_ip, "before the stall sweep's connect")
    console = _Console(board.device)
    try:
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
    finally:
        console.close()
    assert detected is not None, f"no PINGRESP deadline on the console within {_DETECT_WAIT_S:g}s of a stall {offset_s:g}s after the connect"
    took, expected = detected - stalled, 25.0 - offset_s
    assert abs(took - expected) <= _STALL_PHASE_TOLERANCE_S, f"a stall {offset_s:g}s after the connect was detected in {took:.2f}s, expected {expected:.1f}s"
    back = _wait_connected(m.dut_ip, "once the stalled broker resumed")
    assert m.observer.wait_connected(), "the observer did not come back"
    result_note(f"stall {offset_s:g}s after the connect: detected in {took:.2f}s (expected {expected:.1f}s); reconnected {back:.1f}s after the resume")


def test_an_ap_outage_pauses_the_client_and_it_returns_with_the_link(mqtt_bench: MqttBench, board: Board, bench: BenchBridge, result_note: Callable[..., None]) -> None:
    # MQTT never drives WiFi (Part A.11): the client waits out the outage without logging per attempt, then reconnects.
    m = mqtt_bench
    _wait_connected(m.dut_ip, "before the AP outage")
    reset_all_error_logs(m.dut_ip)
    bench.ap_down()
    try:
        time.sleep(_AP_OUTAGE_S)  # an absence: the DUT is unreachable for its whole length
    finally:
        bench.ap_up()
        bench.kick_all_stations()  # stale AP-side entries stop the DUT reassociating (README)
    try:
        back = _wait_connected(m.dut_ip, "after the AP came back", timeout_s=_AP_RECONNECT_TIMEOUT_S)
        note, recovery = f"reconnected {back:.1f}s after the AP came back", False
    except TimeoutError:  # the CYW43 false-positive the WiFi tests document; a hard reset is a genuine pass (CLAUDE.md)
        bench.kick_all_stations()
        board.hard_reset()
        back = _wait_connected(m.dut_ip, "after a recovery hard reset", timeout_s=_REBOOT_WAIT_S)
        note, recovery = f"reconnected {back:.1f}s after a recovery hard reset", True
    attempts = sum(1 for h in _mqtt_history(m.dut_ip) if h.get("num") == _E_CONNECT)
    assert attempts <= _AP_MAX_FAILED_ATTEMPTS, f"{attempts} failed attempts logged across the outage: {_mqtt_history(m.dut_ip)!r}"
    assert_no_task_ended(m.dut_ip, "AP outage")  # on both paths: FRAM keeps SYSTEM across the hard reset
    _assert_mqtt_logged_only(m.dut_ip, "AP outage")
    result_note(f"{note}; {attempts} failed attempt(s) logged", recovery=recovery)


def test_a_reboot_reconnects_from_the_stored_settings(mqtt_bench: MqttBench, board: Board, bench: BenchBridge, result_note: Callable[..., None]) -> None:
    m = mqtt_bench
    _wait_connected(m.dut_ip, "before the reboot")
    seen = len(m.observer.received(f"{m.base}/status"))
    bench.kick_all_stations()
    board.hard_reset()
    back = _wait_connected(m.dut_ip, "after the reboot", timeout_s=_REBOOT_WAIT_S)
    fresh = wait_for(lambda: any(msg.payload == b"online" and not msg.retained for msg in m.observer.received(f"{m.base}/status")[seen:]), _STEP_WAIT_S)
    assert fresh, f"no fresh online after the reboot: {m.observer.received(f'{m.base}/status')[seen:]!r}"
    will = any(msg.payload == b"offline" for msg in m.observer.received(f"{m.base}/status")[seen:])
    result_note(f"connected {back:.1f}s after the reset; the broker {'published' if will else 'did not publish'} the will on the takeover")


def test_the_broker_faults_run_clean_at_micropythons_default_gc(mqtt_bench: MqttBench, board: Board, bench: BenchBridge, tmp_path: Path, result_note: Callable[..., None]) -> None:
    # The firmware's own graph at gc.threshold(-1) while this host kills, stalls, floods and takes over the session:
    # not one allocation failure (Part I.4(e)). The script is handed the bench device's module, never a name here.
    m = mqtt_bench
    script = tmp_path / "mqtt_at_default_gc.py"
    source = (DEVICE_SCRIPTS / "mqtt_at_default_gc.py").read_text()
    assert source.count(_MODULE_PLACEHOLDER) == 1, "the device script's module placeholder moved"
    script.write_text(source.replace(_MODULE_PLACEHOLDER, f"import sensortask_{_mqtt_device()} as sensortask_bench"))
    stop = threading.Event()
    steps: list[str] = []
    driver = threading.Thread(target=_drive_faults, args=(m, stop, steps), daemon=True)
    driver.start()
    try:
        output = board.run_isolated(script, timeout_s=_SCRIPT_TIMEOUT_S)
    finally:
        stop.set()
        driver.join(timeout=_DRIVER_JOIN_S)
        m.broker.send(signal.SIGCONT)
        restore_board_to_serving(board, bench, m.dut_ip)
    assert not driver.is_alive(), "the fault driver outlived its test"
    assert "GC_THRESHOLD=-1" in output, f"the script did not run at the reactive default: {output[-1500:]}"
    assert "RESULT: PASS" in output, output[-2000:]
    assert not any(marker in output for marker in MEMORY_ERROR_MARKERS), f"allocation failure at the reactive default (I.4(e)): {output[-2500:]}"
    assert "UNRETRIEVED TASK EXCEPTION" not in output, output[-2500:]
    assert steps and steps[-1] == "done", f"the fault timeline did not finish inside the script's window: {steps}"
    free = [int(line.split("free=")[1].split()[0]) for line in output.splitlines() if line.startswith("MEM_SAMPLE")]
    result_note(f"timeline {steps}; free heap min {min(free) if free else None} B over {len(free)} samples")
    _wait_connected(m.dut_ip, "after the board went back to its own firmware", timeout_s=_REBOOT_WAIT_S)


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
