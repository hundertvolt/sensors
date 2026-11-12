"""Tests scripts/_digital_twin_ci_suite.py's Run 14 (the MQTT client against a real broker) without a live twin: which
devices run it, that a device without the client spawns nothing and is filed skipped, that a missing broker fails the
run rather than skipping it, and its hotspot and exerciser-traffic checks over a stubbed device."""

import json
import sys
from pathlib import Path
from types import ModuleType
from typing import NamedTuple

import pytest
from _devices import DEVICE_NAMES, device_toml, devices_with

from buildgen.twin_wiring import compute_twin_wiring
from buildgen.validate import build_model, module_int_const

_BASE = "sensors/SensorStationDev"
_LINK_POLL_MS = 250  # the fixture's generated link poll, so the hold reads it rather than a default


class _Message(NamedTuple):
    # The fields of mqtt_probe.Message the checks read.
    topic: str
    payload: bytes
    retained: bool


class _FakeDevice:
    # The twin and broker behind Run 14's traffic check, also its observer Probe: each GET /status is one exerciser round,
    # its probe echoed and counted; a command the host publishes is counted and shown. `fault` breaks one of those.
    def __init__(self, fault: str = "") -> None:
        self.host, self.port = "127.0.0.1", 1883
        self.fault = fault
        self.link = {"Transfers": 0, "Failures": 0, "Commands": 0}
        self.last_rx: str | None = None
        self.sent: tuple[bytes, int] | None = None
        extra = [_Message(f"{_BASE}/measurements/SCD30", b"{}", retained=False)] if fault == "measurements" else []
        self.messages = [_Message(f"{_BASE}/status", b"online", retained=False), *extra]

    def http(self, _method: str, _path: str, _body: object = None, _timeout: float = 5.0) -> tuple[int, object]:
        if self.fault != "no_echo":
            if self.fault != "unobserved_echo":
                self.messages.append(_Message(f"{_BASE}/link/echo", b"\x00\x00\x00\x01", retained=False))
            if self.fault != "uncounted_echo":
                self.link["Transfers"] += 1
        if self.fault == "failing":
            self.link["Failures"] += 1
        return 200, {"networking": {"MQTTLastRxTopic": self.last_rx}, "sensors": {"MQTTLINK": dict(self.link)}}

    def late_probe(self, *_args: object) -> "_LateProbe":
        # The later subscriber the retained check opens.
        return _LateProbe(retained=self.fault != "unretained")

    def publish(self, topic: str, payload: bytes, qos: int = 0) -> bool:
        self.last_rx = topic
        self.sent = (payload, qos)
        if self.fault != "uncounted_command":
            self.link["Commands"] += 1
        return True

    def received(self, topic: str | None = None) -> list[_Message]:
        return [m for m in self.messages if topic is None or m.topic == topic]


class _LateProbe:
    # A subscriber made after the device's online: the broker hands it the kept message, flagged retained when it is.
    def __init__(self, *, retained: bool) -> None:
        self.retained = retained
        self.closed = False

    def close(self) -> None:
        self.closed = True

    def received(self, _topic: str) -> list[_Message]:
        return [_Message(f"{_BASE}/status", b"online", retained=self.retained)]

    def start(self) -> "_LateProbe":
        return self


def _checks(ci_suite: ModuleType, monkeypatch: pytest.MonkeyPatch) -> tuple[list[str], list[str]]:
    # Every _check() recorded as (passed, failed) messages, each wait spent in one evaluation.
    oks: list[str] = []
    fails: list[str] = []
    monkeypatch.setattr(ci_suite, "_check", lambda *, condition, msg: (oks if condition else fails).append(msg))
    for wait in ("_MQTT_CONNECT_WAIT_S", "_MQTT_STEP_WAIT_S", "_MQTT_ECHO_WAIT_S"):
        monkeypatch.setattr(ci_suite, wait, 0.0)
    return oks, fails


def _ctx(ci_suite: ModuleType, tmp_path: Path, *, mqtt: bool) -> object:
    # A pass over a wiring plan listing the client or not, its state and logs under tmp_path, its generated module beside.
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps({"instances": ["fram", "mqtt"] if mqtt else ["fram"]}), encoding="utf-8")
    (tmp_path / "sensortask_fixture.py").write_text(f"_MQTT_LINK_POLL_MS = const({_LINK_POLL_MS})\n", encoding="utf-8")
    return ci_suite.RunContext(micropython_bin="/nonexistent", logs_dir=tmp_path, device="fixture-device", module="sensortask_fixture", wiring_plan_path=plan, instances=(), gc_threshold=-1, routes=("/status",))


def _traffic(ci_suite: ModuleType, monkeypatch: pytest.MonkeyPatch, device: _FakeDevice) -> tuple[list[str], list[str]]:
    # One _check_mqtt_traffic() against the fake device; returns its (passed, failed) messages.
    oks, fails = _checks(ci_suite, monkeypatch)
    monkeypatch.setattr(ci_suite, "_http", device.http)
    monkeypatch.setattr(ci_suite, "Probe", device.late_probe)
    ci_suite._check_mqtt_traffic(device, _BASE)
    return oks, fails


@pytest.fixture
def spawned(ci_suite: ModuleType, monkeypatch: pytest.MonkeyPatch) -> list[str]:
    # Every launch stubbed, with a fresh _FAILURES and summary, so a test sees only its own run.
    log: list[str] = []
    monkeypatch.setattr(ci_suite, "_SUMMARY", ci_suite.Summary("scripts/_digital_twin_ci_suite.py", unit="checks"))
    monkeypatch.setattr(ci_suite, "_FAILURES", [])
    monkeypatch.setattr(ci_suite, "_CHECKS_PER_PASS", {})
    monkeypatch.setattr(ci_suite, "_spawn", lambda _ctx, _args, log_path: log.append(str(log_path)))
    return log


@pytest.mark.parametrize("device", DEVICE_NAMES)
def test_run_14_is_selected_by_the_devices_wiring_plan(ci_suite: ModuleType, repo_root: Path, device: str) -> None:
    # The plan buildgen writes for the device, read as the run reads it: the client listed exactly where the TOML wires it.
    plan = compute_twin_wiring(build_model(device_toml(device), repo_root / "src"))
    assert ci_suite._wires_mqtt(plan) is (device in devices_with("mqtt"))


def test_at_least_one_device_runs_it() -> None:
    # Otherwise CI's matrix would never reach Run 14 and the twin tier would hold the client to nothing.
    assert devices_with("mqtt")


def test_every_device_running_it_carries_the_exerciser() -> None:
    # Run 14's traffic is the exerciser's echo: a device with the client alone would wait for an echo nothing sends.
    assert devices_with("mqtt") == devices_with("mqtt_link")


def test_run_14_is_a_selection_of_its_own(ci_suite: ModuleType) -> None:
    # It reads no state an earlier run leaves, so --only 14 alone is honoured.
    assert ci_suite._run_selection("14") == frozenset({"14"})


def test_the_echo_waits_follow_the_exercisers_own_period(ci_suite: ModuleType, repo_root: Path) -> None:
    # The period read from the exerciser's source, never a copy; the waits span a full round and a stall's detection.
    period_s = module_int_const(repo_root / "src", "asy_mqtt_link_driver.py", "_EXERCISE_PERIOD_MS") / 1000
    assert period_s == ci_suite._MQTT_ECHO_PERIOD_S
    assert 2 * period_s <= ci_suite._MQTT_ECHO_WAIT_S
    assert period_s + ci_suite._MQTT_PINGRESP_DEADLINE_S < ci_suite._MQTT_STALL_WAIT_S


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ({"sensors": {"MQTTLINK": {"Transfers": 3, "Failures": 0, "Commands": 2}}}, 3),
        ({"sensors": {"MQTTLINK": {"Transfers": "3"}}}, -1),
        ({"sensors": {}}, -1),
        ({}, -1),
    ],
)
def test_the_link_counters_come_from_the_mqttlink_maintenance_sensor(ci_suite: ModuleType, monkeypatch: pytest.MonkeyPatch, body: object, expected: int) -> None:
    monkeypatch.setattr(ci_suite, "_http", lambda *_a, **_k: (200, body))
    assert ci_suite._mqtt_link_count("Transfers") == expected


def test_an_unreadable_status_reads_no_link_counter(ci_suite: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ci_suite, "_http", lambda *_a, **_k: (500, {"sensors": {"MQTTLINK": {"Transfers": 3}}}))
    assert ci_suite._mqtt_link_count("Transfers") == -1


def test_the_traffic_check_passes_on_the_exercisers_round_trip(ci_suite: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    device = _FakeDevice()
    oks, fails = _traffic(ci_suite, monkeypatch, device)
    assert fails == []
    assert len(oks) == 6, oks
    assert device.last_rx == f"{_BASE}/cmd/twin"


# Each fault breaks one traffic check alone. A measurement topic is the removed publisher (owner, 2026-11-12: 'The mqtt
# module has no own interval or the like. Its transmissions are triggered from the outside.').
@pytest.mark.parametrize(
    ("fault", "check"),
    [
        ("unretained", "kept online retained"),
        ("no_echo", "link/echo"),
        ("uncounted_echo", "link/echo"),
        ("unobserved_echo", "link/echo"),
        ("measurements", "measurements/SCD30"),
        ("uncounted_command", "counted as a command"),
        ("failing", "no echo probe failed"),
    ],
)
def test_each_broken_part_fails_its_own_traffic_check(ci_suite: ModuleType, monkeypatch: pytest.MonkeyPatch, fault: str, check: str) -> None:
    _oks, fails = _traffic(ci_suite, monkeypatch, _FakeDevice(fault))
    assert len(fails) == 1, fails
    assert check in fails[0], fails


@pytest.mark.parametrize(
    ("status", "keepalives", "failed"),
    [
        ({"Mode": "AP", "MQTTState": "waiting", "MQTTConnects": 0}, [], 0),
        ({"Mode": "AP", "MQTTState": "waiting", "MQTTConnects": 0}, [190], 1),
        ({"Mode": "AP", "MQTTState": "waiting", "MQTTConnects": 1}, [], 1),
        ({"Mode": "AP", "MQTTState": "connected", "MQTTConnects": 1}, [190], 2),
        ({"Mode": "STA", "MQTTState": "waiting", "MQTTConnects": 0}, [], 2),
    ],
)
def test_the_hotspot_check_holds_the_client_off_the_broker(ci_suite: ModuleType, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, status: dict[str, object], keepalives: list[int], failed: int) -> None:
    # Enabled in the hotspot, the client waits and the broker logs no connect from it, over the generated link polls.
    _oks, fails = _checks(ci_suite, monkeypatch)
    slept: list[float] = []
    monkeypatch.setattr(ci_suite, "_mqtt_status", lambda: status)
    monkeypatch.setattr(ci_suite, "_mqtt_keepalives", lambda _broker, _client_id: keepalives)
    monkeypatch.setattr(ci_suite.time, "sleep", slept.append)
    ci_suite._check_mqtt_hotspot(_ctx(ci_suite, tmp_path, mqtt=True), object(), "SensorStationDev")
    assert len(fails) == failed, fails
    assert slept == [ci_suite._MQTT_HOTSPOT_LINK_POLLS * _LINK_POLL_MS / 1000]


def test_a_device_without_the_client_spawns_nothing(ci_suite: ModuleType, spawned: list[str], tmp_path: Path) -> None:
    ci_suite._run_14_mqtt_broker_faults(_ctx(ci_suite, tmp_path, mqtt=False))
    assert spawned == []
    assert ci_suite._FAILURES == []
    counts = ci_suite._SUMMARY.counts()
    assert (counts.skipped, counts.failed, counts.passed) == (1, 0, 0), counts


def test_a_missing_broker_fails_the_run_rather_than_skipping_it(ci_suite: ModuleType, spawned: list[str], monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(sys.modules[ci_suite.Mosquitto.__module__], "mosquitto_binary", lambda: None)
    ci_suite._run_14_mqtt_broker_faults(_ctx(ci_suite, tmp_path, mqtt=True))
    assert spawned == []
    assert len(ci_suite._FAILURES) == 1
    assert "no broker to test against" in ci_suite._FAILURES[0]
    assert ci_suite._SUMMARY.counts().skipped == 0
